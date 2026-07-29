import asyncio
import re
from collections.abc import Callable
from time import perf_counter

from classification import classify_case, classify_case_by_rules
from conversation import generate_conversational_response
from document_index import tokenize
from formatting import format_user_response
from intent import IntentResult, classify_intent
from logging_utils import get_logger
from models import BotDecision
from retrieval import retrieve_evidence

logger = get_logger()


HELP_COMMANDS = {
    "ayuda",
    "necesito ayuda",
    "quiero ayuda",
    "ayudame",
    "ayúdame",
    "consultar_documentacion",
    "consultar procedimiento",
    "consultar_procedimiento",
    "consultar actualizacion",
    "consultar_actualizacion",
}
GREETING_COMMANDS = {
    "hola",
    "buenas",
    "buenos dias",
    "buenas tardes",
    "buenas noches",
}
GREETING_TOKENS = {"hola", "buenas", "buenos", "buenas"}
HELP_TOKENS = {"ayuda", "orientar", "orientacion", "guiar", "guia"}
# Tokens use the lightweight normalization in ``document_index``: ``puedes``
# becomes ``pued`` and the camel-case product name ``ClickUp`` becomes
# ``click`` + ``up`` before stop-word filtering.
CAPABILITY_TOKENS = {"pued", "consultar"}
UNAVAILABLE_INTEGRATIONS = {"click"}
GENERIC_ISSUE_TOKENS = {
    "error",
    "problema",
    "falla",
    "fallo",
    "correg",
    "corrige",
    "corregir",
    "correccion",
    "solucion",
    "resolver",
    "arreglar",
}
DOCUMENTARY_TOKENS = {
    "actualizacion",
    "afp",
    "aguinaldo",
    "bono",
    "documentacion",
    "documento",
    "hotfix",
    "impuesto",
    "isr",
    "isss",
    "manual",
    "pago",
    "planilla",
    "politica",
    "procedimiento",
    "renta",
    "salario",
    "vacacion",
}


def _is_summary_follow_up(user_message: str) -> bool:
    normalized = _normalize_command(user_message)
    return "resum" in normalized and (
        "paso" in normalized or "lista" in normalized
    )


def _summarize_previous_documentary_response(previous_response: str) -> str:
    """Produce a short, deterministic summary without adding new claims."""
    body, separator, source_details = previous_response.partition("\n\nFuente")
    numbered_steps = [
        step.strip()
        for step in re.findall(r"(?:^|\s)\d+\.\s*(.*?)(?=\s+\d+\.|$)", body)
        if step.strip()
    ]
    if len(numbered_steps) >= 2:
        bullets = numbered_steps[:4]
    else:
        sentences = [
            sentence.strip(" -")
            for sentence in re.split(r"(?<=[.!?])\s+", body.strip())
            if sentence.strip(" -")
        ]
        bullets = sentences[:4] or [body.strip()]
    response = "Resumen de la respuesta anterior:\n" + "\n".join(
        f"- {bullet}" for bullet in bullets
    )
    if separator:
        response += f"\n\nFuente{source_details}"
    return response


def _normalize_command(user_message: str) -> str:
    return " ".join((user_message or "").strip().lower().replace("/", " ").split())


def _direct_response(user_message: str) -> str | None:
    """Handle explicit bot commands that do not require model interpretation."""
    command = _normalize_command(user_message)
    if command in HELP_COMMANDS:
        return _help_response()

    query_tokens = set(tokenize(user_message or ""))
    if query_tokens.intersection(UNAVAILABLE_INTEGRATIONS):
        return (
            "ClickUp todavía no está integrado con Libras. Puedo consultar únicamente "
            "la documentación técnica aprobada disponible para este asistente."
        )

    # Keep the opening capability question deterministic.  The intent model can
    # treat it as an underspecified support request, which makes the bot ask for
    # an error context instead of explaining its scope.
    if (
        CAPABILITY_TOKENS.issubset(query_tokens)
        and not query_tokens.intersection(DOCUMENTARY_TOKENS)
        and len(query_tokens) <= 4
    ):
        return _capability_response()

    return None


def _fallback_conversational_response(user_message: str) -> str | None:
    """Keep safe local conversation when the model is unavailable."""
    command = _normalize_command(user_message)
    if command in GREETING_COMMANDS:
        return (
            "Hola, soy Libras. Puedo ayudarte a consultar documentación técnica aprobada. "
            "Escribe `ayuda` para ver cómo formular una consulta."
        )

    query_tokens = set(tokenize(user_message or ""))
    if query_tokens.intersection(GREETING_TOKENS) and query_tokens.intersection(HELP_TOKENS):
        return _help_response()
    if query_tokens.intersection(GENERIC_ISSUE_TOKENS) and not (
        query_tokens.difference(GENERIC_ISSUE_TOKENS)
    ):
        return (
            "Necesito más contexto para orientar la consulta: indique producto o módulo, versión, "
            "mensaje de error y los pasos que lo provocan."
        )

    return None


def _help_response() -> str:
    return (
        "Puedo consultar la documentación técnica aprobada disponible para Libras. "
        "Indique el producto o módulo, la versión y su pregunta. Para reportar un error, "
        "incluya el mensaje exacto, los pasos que lo provocan y, si aplica, el hotfix relacionado."
    )


def _capability_response() -> str:
    return (
        "Puedo consultar la documentación técnica aprobada disponible para Libras, "
        "incluidos procedimientos, manuales, hotfixes y actualizaciones. "
        "Indique el producto o módulo, la versión y su pregunta para buscar evidencia."
    )


def _looks_like_documentary_question(user_message: str) -> bool:
    """Keep a concrete document question out of the conversational short-cut."""
    query_tokens = set(tokenize(user_message or ""))
    return bool(query_tokens.intersection(DOCUMENTARY_TOKENS))


def _intent_response(intent: IntentResult, user_message: str = "") -> str | None:
    if intent.name == "saludo":
        return (
            "Hola, soy Libras. Puedo ayudarte a consultar documentación técnica aprobada. "
            "Escribe `ayuda` para ver cómo formular una consulta."
        )
    if intent.name == "ayuda":
        return _help_response()
    if intent.name in {"reporte_error", "consulta_ambigua"} and intent.requires_context:
        # The intent model can confuse a factual policy question with an
        # underspecified support case (for example, "planillas en El Salvador").
        # Let retrieval decide whether there is evidence instead of discarding
        # a concrete documentary query before it reaches Azure AI Search.
        if _looks_like_documentary_question(user_message):
            return None
        return (
            "Necesito más contexto para orientar la consulta: indique producto o módulo, versión, "
            "mensaje de error y los pasos que lo provocan."
        )
    return None


async def _run_blocking_with_timeout(
    operation: Callable,
    *args,
    timeout_seconds: float,
    **kwargs,
):
    """Keep synchronous SDK calls from blocking the Teams event loop."""
    return await asyncio.wait_for(
        asyncio.to_thread(operation, *args, **kwargs),
        timeout=timeout_seconds,
    )


async def process_user_message(
    user_message: str,
    client,
    config,
    previous_documentary_response: str | None = None,
) -> str:
    started_at = perf_counter()
    if previous_documentary_response and _is_summary_follow_up(user_message):
        return _summarize_previous_documentary_response(previous_documentary_response)

    direct_response = _direct_response(user_message)
    if direct_response:
        logger.info("query_completed duration_ms=0 evidence_count=0 source_types=none decision_state=solicita_contexto escalated=False")
        return direct_response

    intent = None
    if getattr(config, "use_llm_intent_classifier", False) and getattr(
        config, "model_endpoint_configured", True
    ):
        try:
            intent = await _run_blocking_with_timeout(
                classify_intent,
                user_message,
                client=client,
                model=config.openai_intent_model_name,
                timeout_seconds=config.intent_timeout_seconds,
            )
            intent_response = _intent_response(intent, user_message) if intent else None
            if intent_response:
                try:
                    conversational_response = await _run_blocking_with_timeout(
                        generate_conversational_response,
                        user_message,
                        intent,
                        client=client,
                        model=config.openai_intent_model_name,
                        timeout_seconds=config.conversation_timeout_seconds,
                    )
                    if conversational_response:
                        logger.info(
                            "query_completed duration_ms=%s evidence_count=0 source_types=none decision_state=conversation_%s escalated=False",
                            round((perf_counter() - started_at) * 1000),
                            intent.name,
                        )
                        return conversational_response
                except TimeoutError:
                    logger.warning(
                        "La respuesta conversacional superó el límite de %.1f segundos.",
                        config.conversation_timeout_seconds,
                    )
                except Exception:
                    logger.exception("Falló la respuesta conversacional. Se usarán reglas locales.")
                logger.info(
                    "query_completed duration_ms=%s evidence_count=0 source_types=none decision_state=intent_%s escalated=False",
                    round((perf_counter() - started_at) * 1000),
                    intent.name,
                )
                return intent_response
        except TimeoutError:
            logger.warning("La clasificación de intención superó el límite de %.1f segundos.", config.intent_timeout_seconds)
        except Exception:
            logger.exception("Falló la clasificación de intención. Se usarán reglas locales.")

    fallback_conversational_response = _fallback_conversational_response(user_message)
    if fallback_conversational_response:
        logger.info("query_completed duration_ms=0 evidence_count=0 source_types=none decision_state=solicita_contexto escalated=False")
        return fallback_conversational_response

    try:
        evidence = await _run_blocking_with_timeout(
            retrieve_evidence,
            user_message,
            client=client,
            config=config,
            timeout_seconds=config.retrieval_timeout_seconds,
        )
    except TimeoutError:
        logger.warning(
            "La recuperación documental superó el límite de %.1f segundos.",
            config.retrieval_timeout_seconds,
        )
        evidence = []
    except Exception:
        logger.exception("Falló la recuperación documental.")
        evidence = []

    logger.info("Consulta recibida. Evidencias recuperadas: %s", len(evidence))
    fallback_decision = classify_case_by_rules(user_message, evidence)

    if getattr(config, "model_endpoint_configured", True):
        try:
            decision = await _run_blocking_with_timeout(
                classify_case,
                user_message=user_message,
                evidence=evidence,
                client=client,
                model=config.openai_model_name,
                timeout_seconds=config.classification_timeout_seconds,
            )
        except TimeoutError:
            logger.warning(
                "La clasificación superó el límite de %.1f segundos. Se aplicarán reglas locales.",
                config.classification_timeout_seconds,
            )
            decision = fallback_decision
        except Exception:
            logger.exception("Fallo la clasificacion del caso con OpenAI. Se aplicara clasificacion por reglas.")
            decision = fallback_decision
    else:
        decision = fallback_decision

    if (
        decision.estado == "sin_evidencia" and fallback_decision.estado != "sin_evidencia"
    ) or (
        decision.estado == "similar_del_pasado" and fallback_decision.estado == "resuelto"
    ):
        logger.info(
            "Se sustituye clasificación del modelo por la política local. estado_modelo=%s estado_reglas=%s",
            decision.estado,
            fallback_decision.estado,
        )
        decision = fallback_decision

    source_types = sorted({source.tipo for source in decision.fuentes})
    logger.info(
        "query_completed duration_ms=%s evidence_count=%s source_types=%s decision_state=%s escalated=%s",
        round((perf_counter() - started_at) * 1000),
        len(decision.fuentes),
        ",".join(source_types) or "none",
        decision.estado,
        decision.requiere_escalamiento,
    )
    return format_user_response(decision, config=config)
