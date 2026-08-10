import json
import os
import sys
import traceback
import asyncio
from pathlib import Path

from dotenv import load_dotenv
from microsoft_agents.activity import ActivityTypes, load_configuration_from_env
from microsoft_agents.authentication.msal import MsalConnectionManager
from microsoft_agents.hosting.aiohttp import CloudAdapter
from microsoft_agents.hosting.core import (
    AgentApplication,
    ApplicationOptions,
    MemoryStorage,
    TurnContext,
    TurnState,
)
from openai import OpenAI

from config import Config
from conversation_state import ConversationStateStore
from guided_experience import (
    build_welcome_activity,
    command_from_text,
    guided_action_from_activity,
    guided_prompt,
    topic_hint,
)
from handler import (
    extract_conversation_metadata,
    extract_conversation_subject,
    is_persistable_user_message,
    process_user_message,
)
from conversation_mapping_store import build_conversation_mapping_store, mapping_key
from openai_conversations import OpenAIConversationAdapter


def load_environment() -> None:
    load_dotenv()

    project_root = Path(__file__).resolve().parent.parent
    env_name = os.environ.get("TEAMSFX_ENV", "local")
    candidate_files = [
        project_root / "env" / ".env.local.user",
        project_root / "env" / f".env.{env_name}.user",
    ]

    for candidate in candidate_files:
        if candidate.exists():
            # User-scoped settings must supersede development defaults when
            # the production environment is selected.
            load_dotenv(candidate, override=True)


load_environment()

config = Config(os.environ)
agents_sdk_config = load_configuration_from_env(os.environ)

client_options = {
    "api_key": config.openai_api_key or "ollama",
    "base_url": config.resolved_openai_base_url,
}
client = OpenAI(**client_options)


def is_supports_files_enabled() -> bool:
    candidates = [
        os.path.join(os.getcwd(), "appPackage", "manifest.json"),
        os.path.join(os.path.dirname(__file__), "..", "appPackage", "manifest.json"),
        os.path.join(os.path.dirname(__file__), "..", "..", "appPackage", "manifest.json"),
    ]
    for manifest_path in candidates:
        if os.path.exists(manifest_path):
            try:
                with open(manifest_path, "r", encoding="utf-8") as file_handle:
                    manifest = json.load(file_handle)
                bots = manifest.get("bots", [])
                if isinstance(bots, list):
                    return any(bot.get("supportsFiles") is True for bot in bots)
            except (json.JSONDecodeError, OSError):
                continue
    return False


storage = MemoryStorage()
connection_manager = MsalConnectionManager(**agents_sdk_config)
adapter = CloudAdapter(connection_manager=connection_manager)

agent_app = AgentApplication[TurnState](
    options=ApplicationOptions(storage=storage, adapter=adapter),
    connection_manager=connection_manager,
    **agents_sdk_config,
)

_supports_files_warning = (
    'Aviso: La opcion "supportsFiles" esta habilitada en el manifest, pero el manejo de archivos no esta soportado por Custom Engine Agents en este momento. Revise la documentacion oficial de problemas conocidos.'
    if is_supports_files_enabled()
    else ""
)
_supports_files_warned = False
_thread_state = ConversationStateStore(
    ttl_seconds=config.thread_context_ttl_seconds,
    max_conversations=config.thread_context_max_conversations,
)
_conversation_mapping_store = build_conversation_mapping_store(config)
_conversation_adapter = (
    OpenAIConversationAdapter(
        client, timeout_seconds=config.conversation_mapping_timeout_seconds
    )
    if config.use_openai_conversations and config.openai_conversations_supported
    else None
)


def _conversation_id(context: TurnContext) -> str:
    return str(getattr(getattr(context.activity, "conversation", None), "id", ""))


def _tenant_id(context: TurnContext) -> str:
    channel_data = getattr(context.activity, "channel_data", None)
    if isinstance(channel_data, dict):
        tenant = channel_data.get("tenant")
        if isinstance(tenant, dict):
            return str(tenant.get("id") or "")
    tenant = getattr(channel_data, "tenant", None)
    return str(getattr(tenant, "id", "") or "")


async def _ensure_openai_conversation(context: TurnContext) -> tuple[str, str] | None:
    if not (_conversation_mapping_store and _conversation_adapter):
        return None
    teams_id = _conversation_id(context)
    if not teams_id:
        return None
    key = mapping_key(_tenant_id(context), teams_id)
    existing = await asyncio.to_thread(_conversation_mapping_store.get, key)
    if existing:
        await asyncio.to_thread(_conversation_mapping_store.touch, key)
        return key, existing.openai_conversation_id
    created_id = await asyncio.to_thread(_conversation_adapter.create)
    mapping = await asyncio.to_thread(
        _conversation_mapping_store.create_if_absent, key, created_id
    )
    if mapping.openai_conversation_id != created_id:
        # Another worker won the race. Do not leak the unused OpenAI object.
        try:
            await asyncio.to_thread(_conversation_adapter.delete, created_id)
        except Exception:
            traceback.print_exc()
    return key, mapping.openai_conversation_id


async def _delete_openai_conversation(context: TurnContext) -> bool:
    if not (_conversation_mapping_store and _conversation_adapter):
        return True
    teams_id = _conversation_id(context)
    if not teams_id:
        return True
    key = mapping_key(_tenant_id(context), teams_id)
    mapping = await asyncio.to_thread(_conversation_mapping_store.get, key)
    if not mapping:
        return True
    try:
        await asyncio.to_thread(
            _conversation_adapter.delete, mapping.openai_conversation_id
        )
        await asyncio.to_thread(_conversation_mapping_store.delete, key)
        return True
    except Exception:
        traceback.print_exc()
        return False


def _is_documentary_response(answer: str) -> bool:
    return "\n\nFuente:" in answer or "\n\nFuentes:" in answer


@agent_app.conversation_update("membersAdded")
async def on_members_added(context: TurnContext, _state: TurnState):
    global _supports_files_warned
    if config.use_guided_start:
        await context.send_activity(build_welcome_activity())
    else:
        await context.send_activity(
            "Hola. Soy Libras, asistente de base de conocimiento y resolucion de errores para soporte tecnico."
        )
    if _supports_files_warning and not _supports_files_warned:
        _supports_files_warned = True
        await context.send_activity(_supports_files_warning)


@agent_app.activity(ActivityTypes.message)
async def on_message(context: TurnContext, _state: TurnState):
    global _supports_files_warned
    if _supports_files_warning and not _supports_files_warned:
        _supports_files_warned = True
        await context.send_activity(_supports_files_warning)

    user_message = context.activity.text or ""
    conversation_id = _conversation_id(context)
    guided_action = (
        guided_action_from_activity(context.activity)
        if config.use_guided_start
        else None
    )
    if guided_action:
        if config.use_ephemeral_thread_context:
            _thread_state.set_topic(conversation_id, topic_hint(guided_action))
        await context.send_activity(guided_prompt(guided_action))
        return
    slash_command = (
        command_from_text(user_message) if config.use_slash_commands else None
    )
    if slash_command:
        command_action, command_remainder = slash_command
        if command_action == "new":
            if not await _delete_openai_conversation(context):
                await context.send_activity(
                    "No pude borrar el contexto remoto todavía. "
                    "Vuelve a intentar /nuevo antes de continuar."
                )
                return
            if config.use_ephemeral_thread_context:
                _thread_state.clear(conversation_id)
            if config.use_guided_start:
                await context.send_activity(build_welcome_activity())
            else:
                await context.send_activity(
                    "Listo. Empezamos un hilo nuevo. Escribe tu pregunta."
                )
            return
        if config.use_ephemeral_thread_context:
            _thread_state.set_topic(conversation_id, topic_hint(command_action))
        if not command_remainder:
            await context.send_activity(guided_prompt(command_action))
            return
        user_message = command_remainder
    previous_documentary_response = None
    conversation_topic = None
    previous_subject = None
    previous_version = None
    previous_source_label = None
    openai_conversation_id = None
    conversation_trace = {}
    if (
        config.use_openai_conversations
        and config.openai_conversations_supported
        and is_persistable_user_message(user_message)
    ):
        try:
            conversation_info = await _ensure_openai_conversation(context)
            if conversation_info:
                _conversation_key, openai_conversation_id = conversation_info
                if not previous_documentary_response:
                    previous_documentary_response = await asyncio.to_thread(
                        _conversation_adapter.last_assistant_text,
                        openai_conversation_id,
                    )
        except Exception:
            traceback.print_exc()
            await context.send_activity(
                "No pude preparar el contexto persistente del chat. "
                "Intenta nuevamente en unos segundos."
            )
            return
    if config.use_ephemeral_thread_context:
        state = _thread_state.get(conversation_id)
        if state.previous_documentary_response:
            previous_documentary_response = state.previous_documentary_response
        conversation_topic = state.topic
        previous_subject = state.subject
        previous_version = state.version
        previous_source_label = state.source_label
    answer = await process_user_message(
        user_message,
        client,
        config,
        previous_documentary_response=previous_documentary_response,
        conversation_topic=conversation_topic,
        previous_subject=previous_subject,
        previous_version=previous_version,
        previous_source_label=previous_source_label,
        conversation_adapter=_conversation_adapter,
        openai_conversation_id=openai_conversation_id,
        conversation_trace=conversation_trace,
    )
    if (
        config.use_openai_conversations
        and openai_conversation_id
        and not conversation_trace.get("blocked")
        and not conversation_trace.get("recorded")
    ):
        try:
            await asyncio.to_thread(
                _conversation_adapter.append_turn,
                openai_conversation_id,
                user_message,
                answer,
            )
        except Exception:
            traceback.print_exc()
            await context.send_activity(
                "La respuesta se generó, pero no pude guardar el contexto del chat. "
                "Intenta nuevamente antes de continuar."
            )
            return
    if config.use_ephemeral_thread_context and is_persistable_user_message(user_message):
        metadata = extract_conversation_metadata(user_message, answer)
        _thread_state.record_response(
            conversation_id,
            answer,
            is_documentary=_is_documentary_response(answer),
            subject=extract_conversation_subject(user_message),
            **metadata,
        )
    await context.send_activity(answer)


@agent_app.error
async def on_error(context: TurnContext, error: Exception):
    print(f"\n[on_turn_error] unhandled error: {error}", file=sys.stderr)
    traceback.print_exc()
    await context.send_activity(
        "Ocurrio un error al procesar la solicitud. Escale el caso al equipo de desarrollo si el problema persiste."
    )
