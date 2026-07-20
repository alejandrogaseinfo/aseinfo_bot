import json
import os
import sys
import traceback
from pathlib import Path

from dotenv import load_dotenv
from microsoft_agents.activity import ActivityTypes, load_configuration_from_env
from microsoft_agents.authentication.msal import MsalConnectionManager
from microsoft_agents.hosting.aiohttp import CloudAdapter
from microsoft_agents.hosting.core import (
    AgentApplication,
    MemoryStorage,
    TurnContext,
    TurnState,
)
from openai import OpenAI

from config import Config
from handler import process_user_message


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
            load_dotenv(candidate, override=False)


load_environment()

config = Config(os.environ)
agents_sdk_config = load_configuration_from_env(os.environ)

client_options = {"api_key": config.openai_api_key or "ollama"}
if config.openai_base_url:
    client_options["base_url"] = config.openai_base_url
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
    storage=storage,
    adapter=adapter,
    **agents_sdk_config,
)

_supports_files_warning = (
    'Aviso: La opcion "supportsFiles" esta habilitada en el manifest, pero el manejo de archivos no esta soportado por Custom Engine Agents en este momento. Revise la documentacion oficial de problemas conocidos.'
    if is_supports_files_enabled()
    else ""
)
_supports_files_warned = False


@agent_app.conversation_update("membersAdded")
async def on_members_added(context: TurnContext, _state: TurnState):
    global _supports_files_warned
    await context.send_activity(
        "Hola. Soy Chat-Salvador, asistente de base de conocimiento y resolucion de errores para soporte tecnico."
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
    answer = await process_user_message(user_message, client, config)
    await context.send_activity(answer)


@agent_app.error
async def on_error(context: TurnContext, error: Exception):
    print(f"\n[on_turn_error] unhandled error: {error}", file=sys.stderr)
    traceback.print_exc()
    await context.send_activity(
        "Ocurrio un error al procesar la solicitud. Escale el caso al equipo de desarrollo si el problema persiste."
    )
