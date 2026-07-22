import asyncio
from collections.abc import Callable

from classification import classify_case, classify_case_by_rules
from formatting import format_user_response
from logging_utils import get_logger
from models import BotDecision
from retrieval import retrieve_evidence

logger = get_logger()


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


async def process_user_message(user_message: str, client, config) -> str:
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

    return format_user_response(decision, config=config)
