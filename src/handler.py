from classification import classify_case, classify_case_by_rules
from formatting import format_user_response
from logging_utils import get_logger
from models import BotDecision
from retrieval import retrieve_evidence

logger = get_logger()


async def process_user_message(user_message: str, client, config) -> str:
    evidence = retrieve_evidence(user_message, client=client, config=config)
    logger.info("Consulta recibida. Evidencias recuperadas: %s", len(evidence))
    fallback_decision = classify_case_by_rules(user_message, evidence)

    try:
        decision = classify_case(
            user_message=user_message,
            evidence=evidence,
            client=client,
            model=config.openai_model_name,
        )
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
