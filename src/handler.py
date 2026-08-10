import asyncio
import re
import unicodedata
from collections.abc import Callable
from time import perf_counter

from classification import (
    classify_case,
    classify_case_by_rules,
    has_explicit_version_request,
    is_underspecified_query,
    needs_extension_subject_context,
    is_direct_document_question,
    requires_deterministic_grounded_answer,
    requires_explicit_facet_evidence,
)
from conversation import generate_conversational_response
from context_guard import evaluate_context_guard
from document_index import tokenize
from formatting import format_user_response
from intent import IntentResult, classify_intent
from logging_utils import get_logger
from models import BotDecision, EvidenceSource
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
CAPABILITY_SELF_DESCRIPTION_TOKENS = {
    "ayud",
    "ayudar",
    "apoy",
    "apoyar",
    "hacer",
    "servir",
    "funcion",
    "funcionar",
    "ofrec",
    "ofrecer",
}
SCOPE_FALLBACK_TOKENS = {"carpeta", "biblioteca", "alcance", "fuente"}
SCOPE_ACTION_TOKENS = {"pued", "buscar", "consultar", "tien", "disponibl"}
SCOPE_QUESTION_PATTERN = re.compile(
    r"\b(?:sobre\s+que|en\s+que|cuales?)\s+"
    r"(?:carpetas?|bibliotecas?|fuentes?)\s+"
    r"(?:puedes?|puedo|tienes?)\s+(?:buscar|consultar)|"
    r"\b(?:que\s+)?(?:carpetas?|bibliotecas?|fuentes?)\s+"
    r"(?:puedes?|tienes?)\s+(?:buscar|consultar)|"
    r"\bdonde\s+(?:puedo|puedes?)\s+(?:buscar|consultar)|"
    r"\b(?:que|cuales?)\s+(?:fuentes?|bibliotecas?|carpetas?)\s+"
    r"(?:estas?|est[aá]s?)\s+(?:usando|consultando)|"
    r"\bde\s+d[oó]nde\s+(?:obtienes?|sacas?)\s+(?:la\s+)?informaci[oó]n"
)
SCOPE_DOCUMENTATION_PATTERN = re.compile(
    r"\bdonde\s+(?:puedo|puedes?)\s+consultar\s+(?:la\s+)?documentacion\b"
)
CAPABILITY_QUESTION_PATTERN = re.compile(
    r"\b(?:en\s+que|que\s+tipo\s+de)\s+"
    r"(?:tipo(?:s)?\s+de\s+)?(?:informacion|temas?|consultas?|documentos?)\s+"
    r"(?:puedes?\s+)?(?:ayudar(?:me)?|apoyar(?:me)?|atender|manejar)\b|"
    r"\b(?:que|qu[eé])\s+(?:te|me)\s+puedo\s+preguntar\b|"
    r"\b(?:que|qu[eé])\s+(?:tipo|clase)\s+de\s+(?:informaci[oó]n|temas?)\s+"
    r"(?:puedes?|sabes?|manejas?)\b"
)
IDENTITY_QUESTION_PATTERN = re.compile(
    r"\b(?:cual|que)\s+es\s+mi\s+nombre\b|"
    r"\bcomo\s+me\s+llamo\b|"
    r"\brecuerdas?\s+mi\s+nombre\b|"
    r"\bdime\s+mi\s+nombre\b"
)
SENSITIVE_SECRET_PATTERN = re.compile(
    r"\b(?:api[\s_-]*keys?|clave(?:s)?[\s_-]*(?:api|privada)|password|contrasena|"
    r"tokens?|secret(?:o|os|s)?|credencial(?:es)?|credential(?:s)?|"
    r"connection[\s_-]*string|"
    r"cadena[\s_-]*de[\s_-]*conexion)\b"
)
SECRET_DISCLOSURE_PATTERN = re.compile(
    r"\b(?:dame|darme|muestra(?:me)?|mostrar(?:me)?|ensena(?:me)?|revela(?:me)?|"
    r"pasa(?:me)?|pasar(?:me)?|compart(?:e|ir)(?:me)?|facilita(?:me)?|"
    r"facilitar(?:me)?|proporciona|proporcionar(?:me)?|envia|enviar(?:me)?|"
    r"entrega|entregar(?:me)?|extrae|lista|listar|imprime|expone|devuelve|"
    r"cual(?:es)?|que[\s_-]*valor|valor[\s_-]*de|provide|show|reveal|share|"
    r"give|list|extract|print|return|value)\b"
)
CUSTOMER_CONFIDENTIAL_PATTERN = re.compile(
    # A contract is a valid technical domain concept in Evolution. Treat it
    # as confidential only when the request connects it to a client record or
    # a financial/customer attribute; otherwise a question such as "prórroga
    # de contratos" must reach documentary retrieval.
    r"\bcliente(?:s)?\b.{0,80}\b(?:dato(?:s)?[\s_-]*de[\s_-]*contacto|"
    r"contrato(?:s)?|pago(?:s)?|atrasad\w*|mora|saldo(?:s)?|deuda(?:s)?|factura(?:s)?)\b|"
    r"\b(?:dato(?:s)?[\s_-]*de[\s_-]*contacto|contrato(?:s)?|pago(?:s)?|"
    r"atrasad\w*|mora|saldo(?:s)?|deuda(?:s)?|factura(?:s)?)\b.{0,80}\bcliente(?:s)?\b"
)
PERSONAL_CONFIDENTIAL_PATTERN = re.compile(
    r"\b(?:salario(?:s)?|cuenta(?:s)?[\s_-]*bancaria(?:s)?|numero[\s_-]*de[\s_-]*identificacion|"
    r"telefono(?:s)?|correo(?:s)?[\s_-]*personal(?:es)?|dato(?:s)?[\s_-]*personales?)\b"
)
SITE_INVENTORY_PATTERN = re.compile(
    r"\b(?:enumera|enumerar|lista|listar|muestra|mostrar|dame|comparte|"
    r"compartir|inventario)\b.{0,80}"
    r"\b(?:todos?[\s_-]*los?[\s_-]*)?(?:archivo(?:s)?|documento(?:s)?)\b.{0,80}"
    r"\b(?:sitio|sharepoint|soporte[\s_-]*regional)\b"
)
# These libraries are deliberately outside the pilot scope.  Retrieval already
# filters documents by their approved provenance, but a user can name an
# excluded library directly.  Reject that request before search so a loosely
# related result from an approved library is not presented as an answer.
RESTRICTED_LIBRARY_PATTERN = re.compile(
    r"\b(?:hojas?[\s_-]*de[\s_-]*servicio|teams?[\s_-]*wiki[\s_-]*data)\b"
)
# This is intentionally a high-confidence deterministic pattern. Broader
# prompt-injection detection remains a semantic guard concern, but explicit
# attempts to discard Libras's own instructions must never be routed as a
# generic support question while that guard is unavailable or in observation.
INSTRUCTION_OVERRIDE_PATTERN = re.compile(
    r"\b(?:ignora|olvida|ignore|forget)\s+(?:todas?\s+|all\s+|previous\s+)?"
    r"(?:las?\s+)?(?:instrucciones|reglas|politicas|indicaciones|instructions|rules)\b"
)
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
SPECIFIC_ISSUE_FILLER_TOKENS = {
    "tengo",
    "tien",
    "hay",
    "present",
    "aparec",
    "ocurr",
    "suced",
    "sal",
}


def _is_summary_follow_up(user_message: str) -> bool:
    normalized = _normalized_sensitive_text(user_message)
    return bool(
        re.search(
            r"\bresum\w*\b|\bpuntos?\s+principales?\b|"
            r"\bexplica(?:me|r|rlo|rla)?\b.{0,40}\b(?:sencilla|simple)\b",
            normalized,
        )
    )


def _summarize_previous_documentary_response(previous_response: str) -> str:
    """Produce a short, deterministic summary without adding new claims."""
    body, separator, source_details = previous_response.partition("\n\nFuente")
    numbered_steps = [
        re.sub(r"^\s*\d+\.\s+", "", line).strip()
        for line in body.splitlines()
        if re.match(r"^\s*\d+\.\s+", line)
    ]
    if len(numbered_steps) >= 2:
        bullets = numbered_steps[:4]
    else:
        sentences = [
            sentence.strip(" -")
            for sentence in re.split(
                r"(?<=[.!?])\s+(?=[A-ZÁÉÍÓÚÜ¿¡])", body.strip()
            )
            if sentence.strip(" -")
        ]
        bullets = sentences[:4] or [body.strip()]
    response = "Resumen de la respuesta anterior:\n" + "\n".join(
        f"- {bullet}" for bullet in bullets
    )
    if separator:
        response += f"\n\nFuente{source_details}"
    return response


VERSION_REFERENCE_PATTERN = re.compile(
    r"\b(?:esa|dicha|la mencionada|la anterior)\s+"
    r"(?:versi[oó]n|actualizaci[oó]n|release|edici[oó]n)\b|"
    r"\b(?:en|de)\s+esa\b"
)
DOCUMENT_REFERENCE_PATTERN = re.compile(
    r"\b(?:ese|esa|dicho|dicha|el|la)\s+"
    r"(?:documento|archivo|readme|manual|hotfix|release|cambio|actualizacion)\b|"
    r"\b(?:esos|esas|dichos|dichas)\s+"
    r"(?:cambios|mejoras|novedades|detalles|puntos)\b"
)
PRONOUN_DOCUMENT_REFERENCE_PATTERN = re.compile(
    r"\b(?:esos|esas|estos|estas|los\s+anteriores|las\s+anteriores|"
    r"los\s+mismos|las\s+mismas)\b"
)
CHANGE_REQUEST_PATTERN = re.compile(
    r"\b(?:cambios?|modificaciones?|mejoras?|novedades?|correcciones?)\b"
)
VERSION_PATTERN = re.compile(r"\b\d+(?:\.\d+){2,}\b")
EXPLICIT_PRODUCT_PATTERN = re.compile(
    r"\b(?:producto|modulo|sistema|aplicacion)\s+(?:de\s+)?"
    r"([a-z0-9][a-z0-9._-]*)\b"
)
NON_PRODUCT_WORDS = {"o", "un", "una", "el", "la", "los", "las", "este", "esta"}
SOURCE_LABEL_PATTERN = re.compile(r"(?:^|\n)Fuentes?:\s*([^\n]+)", re.IGNORECASE)


def _resolve_documentary_follow_up(
    user_message: str,
    previous_documentary_response: str | None,
    previous_subject: str | None = None,
    previous_version: str | None = None,
    previous_source_label: str | None = None,
) -> str:
    """Resolve a narrow document follow-up without sending full chat history.

    The previous answer is already restricted to a cited documentary response.
    If the user refers to the previous version, document, hotfix, or release,
    carry only its explicit dotted version into retrieval. This prevents a
    generic query from matching neighboring hotfixes while keeping the
    original wording for the response shown to the user.
    """
    normalized_message = _normalized_sensitive_text(user_message)
    if PRONOUN_DOCUMENT_REFERENCE_PATTERN.search(normalized_message):
        reference = previous_subject or previous_source_label
        if reference:
            return f"{user_message} (referencia contextual: {reference})"
    if not (
        VERSION_REFERENCE_PATTERN.search(normalized_message)
        or DOCUMENT_REFERENCE_PATTERN.search(normalized_message)
    ):
        return user_message
    version = previous_version
    if not version and previous_documentary_response:
        previous_versions = VERSION_PATTERN.findall(previous_documentary_response)
        version = previous_versions[0] if previous_versions else None
    if not version:
        return user_message
    if version in user_message:
        return user_message
    return f"{user_message} (referencia contextual: versión {version})"


def extract_conversation_subject(user_message: str) -> str | None:
    """Extract a small, non-transcript subject for same-chat references."""
    normalized = _normalized_sensitive_text(user_message)
    if re.search(r"\b(?:documentos?|tipos?\s+de\s+documentos?)\b", normalized) and re.search(
        r"\b(?:administr|gestion|maneja|manejan)\w*\b", normalized
    ):
        product = "Evolution" if re.search(r"\bevolution\b", normalized) else ""
        return f"documentos gestionados{f' en {product}' if product else ''}"
    return None


def extract_conversation_metadata(user_message: str, answer: str = "") -> dict[str, str]:
    """Extract bounded labels useful for a same-chat follow-up.

    These labels intentionally omit the message transcript, URLs and document
    fragments. They exist only in process memory and expire with the chat state.
    """
    normalized = _normalized_sensitive_text(user_message)
    product_match = EXPLICIT_PRODUCT_PATTERN.search(normalized)
    product = None
    if product_match and product_match.group(1) not in NON_PRODUCT_WORDS:
        product = product_match.group(1)
    elif re.search(r"\bevolution\b", normalized):
        product = "Evolution"

    versions = VERSION_PATTERN.findall(user_message)
    if not versions and answer:
        versions = VERSION_PATTERN.findall(answer)
    metadata: dict[str, str] = {}
    if product:
        metadata["product"] = product
    if versions:
        metadata["version"] = versions[0]
    if re.search(r"\b(?:procedimiento|pasos?|configur|instal|como\s+(?:hacer|realizar))\b", normalized):
        metadata["query_type"] = "procedimiento"
    elif re.search(r"\b(?:actualizaci[oó]n|hotfix|release|cambios?|novedades?)\b", normalized):
        metadata["query_type"] = "actualización"
    elif re.search(r"\b(?:versi[oó]n|versiones)\b", normalized):
        metadata["query_type"] = "versión"
    elif re.search(r"\b(?:error|falla|problema)\b", normalized):
        metadata["query_type"] = "error"

    source_match = SOURCE_LABEL_PATTERN.search(answer)
    if source_match:
        # This is the formatted title shown by Libras, not a document URL.
        metadata["source_label"] = source_match.group(1).strip()[:240]
    return metadata


def _enrich_change_request(user_message: str) -> str:
    """Add retrieval-only synonyms for a request about documented changes."""
    if not CHANGE_REQUEST_PATTERN.search(_normalized_sensitive_text(user_message)):
        return user_message
    return f"{user_message} (detalle técnico: mejoras modificaciones correcciones)"


def _enrich_classification_request(user_message: str) -> str:
    """Bias incapacity-classification searches toward the authoritative personnel manual."""
    normalized = _normalized_sensitive_text(user_message)
    if not (
        re.search(r"\bincapacidad(?:es)?\b", normalized)
        and re.search(r"\bclasific\w*\b", normalized)
    ):
        return user_message
    return (
        f"{user_message} (clasificación documental: duración permanentes temporales "
        "cualidad físicas psíquicas Acciones de personal)"
    )


def _evidence_matches_explicit_product(
    user_message: str,
    evidence: list[EvidenceSource],
) -> bool:
    """Require a named product to be present in evidence before answering.

    This applies only to phrases such as "producto Inexistente". It prevents a
    loosely related Readme from being presented as evidence for a product the
    index does not contain.
    """
    normalized_message = _normalized_sensitive_text(user_message)
    match = EXPLICIT_PRODUCT_PATTERN.search(normalized_message)
    if not match or match.group(1) in NON_PRODUCT_WORDS:
        return True
    requested_product = match.group(1)
    return any(
        requested_product in set(
            tokenize(f"{source.titulo} {source.fragmento} {source.ubicacion}")
        )
        for source in evidence
    )


def _filter_contextual_version_evidence(
    retrieval_message: str,
    evidence: list[EvidenceSource],
) -> list[EvidenceSource]:
    """Keep a documentary follow-up inside the version carried from the prior turn."""
    match = re.search(
        r"referencia contextual:\s+version\s+(\d+(?:\.\d+){2,})",
        _normalized_sensitive_text(retrieval_message),
    )
    if not match:
        return evidence
    version = match.group(1)
    version_pattern = re.compile(rf"(?<!\d){re.escape(version)}(?!\d)")
    any_version_pattern = re.compile(r"(?<!\d)\d+(?:\.\d+){2,}(?!\d)")

    def belongs_to_contextual_version(source: EvidenceSource) -> bool:
        identity = " ".join((source.titulo, source.ubicacion))
        identity_versions = set(any_version_pattern.findall(identity))
        if identity_versions and version not in identity_versions:
            return False
        return version_pattern.search(
            " ".join(
                (
                    source.titulo,
                    source.ubicacion,
                    source.fragmento,
                    source.document_version,
                )
            )
        ) is not None

    return [
        source
        for source in evidence
        if belongs_to_contextual_version(source)
    ]


def _normalize_command(user_message: str) -> str:
    return " ".join((user_message or "").strip().lower().replace("/", " ").split())


def _is_sensitive_secret_request(user_message: str) -> bool:
    """Reject requests that try to obtain credentials before any retrieval."""
    normalized = unicodedata.normalize("NFKD", user_message or "").lower()
    normalized = "".join(
        character for character in normalized if not unicodedata.combining(character)
    )
    return bool(
        SENSITIVE_SECRET_PATTERN.search(normalized)
        and SECRET_DISCLOSURE_PATTERN.search(normalized)
    )


def _normalized_sensitive_text(user_message: str) -> str:
    normalized = unicodedata.normalize("NFKD", user_message or "").lower()
    return "".join(
        character for character in normalized if not unicodedata.combining(character)
    )


def _is_confidential_data_request(user_message: str) -> bool:
    """Block requests for customer, personal, financial, or site inventory data."""
    normalized = _normalized_sensitive_text(user_message)
    return bool(
        CUSTOMER_CONFIDENTIAL_PATTERN.search(normalized)
        or PERSONAL_CONFIDENTIAL_PATTERN.search(normalized)
        or SITE_INVENTORY_PATTERN.search(normalized)
    )


def _requests_restricted_library(user_message: str) -> bool:
    """Reject direct requests for libraries that are not in the bot scope."""
    return bool(RESTRICTED_LIBRARY_PATTERN.search(_normalized_sensitive_text(user_message)))


def _attempts_instruction_override(user_message: str) -> bool:
    """Reject explicit instruction override attempts before any model call."""
    return bool(INSTRUCTION_OVERRIDE_PATTERN.search(_normalized_sensitive_text(user_message)))


def _sensitive_secret_response() -> str:
    return (
        "No puedo proporcionar, buscar ni mostrar claves API, contraseñas, tokens, "
        "secretos o credenciales. Estos valores se administran de forma segura y no "
        "están disponibles a través de Libras. Solicite el acceso por el canal "
        "corporativo correspondiente."
    )


def _confidential_data_response() -> str:
    return (
        "No puedo buscar, enumerar ni divulgar datos confidenciales, incluyendo "
        "datos de clientes, contratos, información personal, estados financieros "
        "o inventarios del sitio. Libras solo responde consultas técnicas con "
        "evidencia autorizada dentro de su alcance."
    )


def _restricted_library_response() -> str:
    return (
        "No puedo consultar esa biblioteca porque está fuera del alcance autorizado "
        "de Libras. Puedo responder únicamente con documentación técnica de las "
        "bibliotecas aprobadas para el piloto."
    )


def _out_of_scope_response() -> str:
    """Close non-documentary requests before retrieval or answer generation."""
    return (
        "No puedo responder esa consulta porque está fuera del alcance de Libras. "
        "Solo atiendo preguntas técnicas basadas en la documentación autorizada."
    )


def _context_guard_response() -> str:
    """Avoid disclosing guard internals or echoing a risky request."""
    return (
        "Por seguridad, no puedo procesar esta solicitud. Libras solo atiende "
        "consultas técnicas sobre la documentación aprobada dentro de su alcance."
    )


def _identity_response() -> str:
    return (
        "No puedo confirmar tu nombre porque Libras no conserva nombres ni el "
        "historial completo del chat. Si necesitas usarlo en una consulta, "
        "indícalo nuevamente en ese mensaje."
    )


def _underspecified_query_response(conversation_topic: str | None = None) -> str:
    topic_prompts = {
        "consulta de versión": (
            "Para consultar una versión, indica el producto o módulo, la versión "
            "y qué deseas revisar."
        ),
        "consulta de procedimiento": (
            "Para consultar un procedimiento, indica el producto o módulo, la versión "
            "y la tarea o configuración que necesitas revisar."
        ),
        "consulta de actualización": (
            "Para revisar una actualización, indica el producto o módulo, la versión "
            "y el componente o cambio que deseas consultar."
        ),
        "reporte de error técnico": (
            "Para revisar un error, indica el producto o módulo, la versión, el mensaje "
            "exacto y los pasos que provocan el problema."
        ),
    }
    if conversation_topic in topic_prompts:
        return topic_prompts[conversation_topic]
    return (
        "Necesito más contexto para orientar la consulta: indique el producto o módulo, "
        "la versión, el mensaje o comportamiento observado y qué desea revisar."
    )


def _is_generic_topic_question(user_message: str) -> bool:
    normalized = _normalized_sensitive_text(user_message)
    return bool(
        re.search(
            r"\b(?:como|que)\s+(?:se\s+)?(?:hace|debo\s+hacer|puedo\s+hacer)\b|"
            r"\bnecesito\s+ayuda\b",
            normalized,
        )
    )


def _ambiguous_extension_response() -> str:
    return (
        "¿Te refieres a la prórroga de contratos o a una prórroga de incapacidades? "
        "Indica cuál de las dos para consultar los parámetros documentados sin asumir el contexto."
    )


def _is_scope_question(user_message: str, query_tokens: set[str]) -> bool:
    """Recognize clear questions about Libras's document scope before the LLM."""
    normalized = _normalized_sensitive_text(user_message)
    if SCOPE_DOCUMENTATION_PATTERN.search(normalized):
        return True
    if SCOPE_QUESTION_PATTERN.search(normalized):
        return True
    return bool(SCOPE_QUESTION_PATTERN.search(normalized)) and bool(
        query_tokens.intersection(SCOPE_FALLBACK_TOKENS)
        and query_tokens.intersection(SCOPE_ACTION_TOKENS)
    )


def _is_capability_question(user_message: str, query_tokens: set[str]) -> bool:
    """Recognize self-description questions without mistaking them for document requests."""
    if _is_scope_question(user_message, query_tokens):
        return False
    if CAPABILITY_QUESTION_PATTERN.search(_normalized_sensitive_text(user_message)):
        return True
    return bool(
        (
            query_tokens.intersection(CAPABILITY_SELF_DESCRIPTION_TOKENS)
            or CAPABILITY_TOKENS.issubset(query_tokens)
        )
        and not query_tokens.intersection(DOCUMENTARY_TOKENS)
        and not query_tokens.intersection(GENERIC_ISSUE_TOKENS)
    )


def _is_self_description_question(user_message: str, query_tokens: set[str]) -> bool:
    """Accept LLM self-description routes only when the bot is the subject."""
    normalized = _normalized_sensitive_text(user_message)
    return bool(re.search(r"\b(?:libras|bot|asistente)\b", normalized)) or _is_capability_question(
        user_message, query_tokens
    )


def _direct_response(user_message: str, config=None) -> str | None:
    """Handle explicit bot commands that do not require model interpretation."""
    command = _normalize_command(user_message)
    if command in HELP_COMMANDS:
        return _help_response()

    query_tokens = set(tokenize(user_message or ""))
    if IDENTITY_QUESTION_PATTERN.search(_normalized_sensitive_text(user_message)):
        return _identity_response()
    if query_tokens.intersection(UNAVAILABLE_INTEGRATIONS):
        return (
            "ClickUp todavía no está integrado con Libras. Puedo consultar únicamente "
            "la documentación técnica aprobada disponible para este asistente."
        )

    # These questions describe Libras itself, not the indexed content. Handle
    # clear forms before the LLM so they can never be redirected to retrieval.
    if _is_scope_question(user_message, query_tokens):
        return _scope_response(config)
    if _is_capability_question(user_message, query_tokens):
        return _capability_response()

    return None


def _fallback_conversational_response(user_message: str, config=None) -> str | None:
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
    # These are intentionally a small fallback, not the primary language
    # understanding mechanism. The LLM router handles broader paraphrases.
    if _is_scope_question(user_message, query_tokens):
        return _scope_response(config)
    if _is_capability_question(user_message, query_tokens):
        return _capability_response()
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
        "Puedo consultar la documentación técnica autorizada de las bibliotecas del sitio, "
        "incluida la carpeta SOLUCIONES. "
        "Indique el producto o módulo, la versión y su pregunta. Para reportar un error, "
        "incluya el mensaje exacto y los pasos que lo provocan."
    )


def _capability_response() -> str:
    return (
        "Puedo consultar documentación técnica autorizada sobre:\n"
        "- Versiones, actualizaciones y mejoras de Evolution.\n"
        "- Procedimientos y configuraciones documentadas.\n"
        "- Errores, correcciones y validaciones documentadas.\n"
        "- Manuales técnicos y scripts con descripción documental.\n\n"
        "La información proviene únicamente de fuentes documentales autorizadas, "
        "incluida la carpeta SOLUCIONES.\n"
        "Indique el producto o módulo, la versión y la pregunta específica que desea resolver."
    )


def _scope_response(config=None) -> str:
    """Describe only operator-configured, user-visible document sources."""
    source_labels = tuple(getattr(config, "sharepoint_source_labels", ()) or ())
    if source_labels:
        return (
            "Puedo buscar en las siguientes fuentes documentales autorizadas: "
            f"{', '.join(source_labels)}. "
            "No consulto bibliotecas ni sistemas fuera de ese alcance."
        )
    return (
        "Puedo buscar únicamente en las bibliotecas y carpetas documentales "
        "autorizadas del sitio, incluida la carpeta SOLUCIONES y sus subcarpetas. "
        "No consulto bibliotecas ni sistemas fuera de ese alcance."
    )


def _looks_like_documentary_question(user_message: str) -> bool:
    """Keep a concrete document question out of the conversational short-cut.

    A user normally reports a known support case by its symptom, not by the
    generic file name stored below that case's SharePoint folder.  Three
    specific terms beyond the error wording are enough to try documented
    retrieval; vague reports such as "no funciona" still ask for context.
    """
    query_tokens = set(tokenize(user_message or ""))
    if query_tokens.intersection(DOCUMENTARY_TOKENS):
        return True
    specific_issue_terms = query_tokens.difference(
        GENERIC_ISSUE_TOKENS | SPECIFIC_ISSUE_FILLER_TOKENS
    )
    return bool(query_tokens.intersection(GENERIC_ISSUE_TOKENS)) and len(
        specific_issue_terms
    ) >= 3


def _intent_response(intent: IntentResult, config=None, user_message: str = "") -> str | None:
    query_tokens = set(tokenize(user_message or ""))
    if intent.conversation_purpose == "capacidad":
        if not _is_self_description_question(user_message, query_tokens):
            return None
        return _capability_response()
    if intent.conversation_purpose == "alcance":
        if not (
            _is_scope_question(user_message, query_tokens)
            or _is_self_description_question(user_message, query_tokens)
        ):
            return None
        return _scope_response(config)
    if intent.name == "saludo":
        return (
            "Hola, soy Libras. Puedo ayudarte a consultar documentación técnica aprobada. "
            "Escribe `ayuda` para ver cómo formular una consulta."
        )
    if intent.name == "ayuda":
        return _help_response()
    if intent.name == "fuera_alcance":
        return _out_of_scope_response()
    if intent.name == "consulta_ambigua" and intent.requires_context:
        # The intent model can confuse a factual policy question with an
        # underspecified support case (for example, "planillas en El Salvador").
        # Let retrieval decide whether there is evidence instead of discarding
        # a concrete documentary query before it reaches Azure AI Search.
        if _looks_like_documentary_question(user_message):
            return None
        return (
            "No tengo evidencia sobre ese tema en la documentación técnica autorizada "
            "de Libras. Puedo ayudar con consultas sobre productos, módulos, versiones "
            "o procedimientos documentados."
        )
    if intent.name == "reporte_error" and intent.requires_context:
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
    grace_seconds: float = 0,
    **kwargs,
):
    """Keep synchronous SDK calls from blocking the Teams event loop."""
    operation_task = asyncio.create_task(asyncio.to_thread(operation, *args, **kwargs))
    try:
        return await asyncio.wait_for(
            asyncio.shield(operation_task),
            timeout=timeout_seconds,
        )
    except TimeoutError:
        grace_seconds = max(0.0, float(grace_seconds or 0))
        if grace_seconds:
            try:
                result = await asyncio.wait_for(
                    asyncio.shield(operation_task),
                    timeout=grace_seconds,
                )
            except TimeoutError:
                operation_task.add_done_callback(_consume_background_task_result)
                raise
            logger.info(
                "La operación terminó dentro de la ventana adicional de %.1f segundos.",
                grace_seconds,
            )
            return result
        operation_task.add_done_callback(_consume_background_task_result)
        raise


def _consume_background_task_result(task: asyncio.Task) -> None:
    """Consume a late worker result so it cannot produce an unhandled error."""
    if task.cancelled():
        return
    try:
        task.exception()
    except Exception:
        # The original request already returned its safe fallback. There is no
        # useful response path left for a late worker exception.
        return


def is_persistable_user_message(user_message: str) -> bool:
    """Avoid creating durable state for preflight-rejected input."""
    return not (
        _is_sensitive_secret_request(user_message)
        or _is_confidential_data_request(user_message)
        or _requests_restricted_library(user_message)
        or _attempts_instruction_override(user_message)
    )


async def process_user_message(
    user_message: str,
    client,
    config,
    previous_documentary_response: str | None = None,
    conversation_topic: str | None = None,
    previous_subject: str | None = None,
    previous_version: str | None = None,
    previous_source_label: str | None = None,
    conversation_adapter=None,
    openai_conversation_id: str | None = None,
    conversation_trace: dict | None = None,
) -> str:
    started_at = perf_counter()

    def mark_trace(*, blocked: bool = False, recorded: bool = False) -> None:
        if conversation_trace is not None:
            conversation_trace["blocked"] = blocked
            conversation_trace["recorded"] = recorded

    if _is_sensitive_secret_request(user_message):
        mark_trace(blocked=True)
        logger.warning(
            "query_completed duration_ms=0 evidence_count=0 source_types=none "
            "decision_state=solicitud_sensible_rechazada escalated=True"
        )
        return _sensitive_secret_response()

    if _is_confidential_data_request(user_message):
        mark_trace(blocked=True)
        logger.warning(
            "query_completed duration_ms=0 evidence_count=0 source_types=none "
            "decision_state=solicitud_confidencial_rechazada escalated=True"
        )
        return _confidential_data_response()

    if _requests_restricted_library(user_message):
        mark_trace(blocked=True)
        logger.warning(
            "query_completed duration_ms=0 evidence_count=0 source_types=none "
            "decision_state=biblioteca_fuera_de_alcance_rechazada escalated=False"
        )
        return _restricted_library_response()

    if _attempts_instruction_override(user_message):
        mark_trace(blocked=True)
        logger.warning(
            "query_completed duration_ms=0 evidence_count=0 source_types=none "
            "decision_state=instruction_override_rejected escalated=True"
        )
        return _context_guard_response()

    if previous_documentary_response and _is_summary_follow_up(user_message):
        return _summarize_previous_documentary_response(previous_documentary_response)

    if not previous_documentary_response and _is_summary_follow_up(user_message):
        logger.info(
            "query_completed duration_ms=0 evidence_count=0 source_types=none "
            "decision_state=resumen_sin_contexto escalated=False"
        )
        return (
            "Todavía no hay una respuesta documental en este hilo para resumir. "
            "Indica primero el producto, la versión y el procedimiento que deseas consultar."
        )

    direct_response = _direct_response(user_message, config)
    if direct_response:
        logger.info("query_completed duration_ms=0 evidence_count=0 source_types=none decision_state=solicita_contexto escalated=False")
        return direct_response

    if is_underspecified_query(user_message) or (
        conversation_topic and _is_generic_topic_question(user_message)
    ):
        logger.info(
            "query_completed duration_ms=0 evidence_count=0 source_types=none "
            "decision_state=solicita_contexto escalated=False"
        )
        return _underspecified_query_response(conversation_topic)

    if needs_extension_subject_context(user_message):
        logger.info(
            "query_completed duration_ms=0 evidence_count=0 source_types=none "
            "decision_state=solicita_contexto_prorroga escalated=False"
        )
        return _ambiguous_extension_response()

    retrieval_message = _enrich_change_request(
        _enrich_classification_request(
            _resolve_documentary_follow_up(
            user_message,
            previous_documentary_response,
            previous_subject,
            previous_version,
            previous_source_label,
        )
        )
    )
    if (
        getattr(config, "use_context_guard", False)
        and getattr(config, "model_endpoint_configured", True)
    ):
        guard_mode = getattr(config, "context_guard_mode", "observe")
        failure_policy = getattr(config, "context_guard_failure_policy", "block")
        try:
            guard_decision = await _run_blocking_with_timeout(
                evaluate_context_guard,
                retrieval_message,
                client=client,
                model=getattr(config, "context_guard_model_name", config.openai_intent_model_name),
                timeout_seconds=getattr(config, "context_guard_timeout_seconds", 2),
            )
            if not guard_decision.allows_request:
                if guard_mode == "enforce":
                    mark_trace(blocked=True)
                logger.warning(
                    "context_guard decision=%s reason_code=%s confidence=%s mode=%s",
                    guard_decision.decision,
                    guard_decision.reason_code,
                    guard_decision.confidence,
                    guard_mode,
                )
                if guard_mode == "enforce":
                    logger.warning(
                        "query_completed duration_ms=%s evidence_count=0 source_types=none "
                        "decision_state=context_guard_blocked escalated=True",
                        round((perf_counter() - started_at) * 1000),
                    )
                    return _context_guard_response()
        except TimeoutError:
            logger.warning(
                "ContextGuard superó el límite de %.1f segundos.",
                getattr(config, "context_guard_timeout_seconds", 2),
            )
            if guard_mode == "enforce" and failure_policy == "block":
                mark_trace(blocked=True)
                return _context_guard_response()
        except Exception:
            logger.exception("Falló ContextGuard; se aplicará su política de fallo configurada.")
            if guard_mode == "enforce" and failure_policy == "block":
                mark_trace(blocked=True)
                return _context_guard_response()

    intent = None
    if getattr(config, "use_llm_intent_classifier", False) and getattr(
        config, "model_endpoint_configured", True
    ):
        try:
            intent = await _run_blocking_with_timeout(
                classify_intent,
                retrieval_message,
                client=client,
                model=config.openai_intent_model_name,
                timeout_seconds=config.intent_timeout_seconds,
            )
            intent_response = _intent_response(intent, config, retrieval_message) if intent else None
            if intent_response:
                if intent.conversation_purpose in {"capacidad", "alcance"} or intent.name == "fuera_alcance":
                    logger.info(
                        "query_completed duration_ms=%s evidence_count=0 source_types=none decision_state=intent_%s escalated=False",
                        round((perf_counter() - started_at) * 1000),
                        intent.name if intent.name == "fuera_alcance" else intent.conversation_purpose,
                    )
                    return intent_response
                try:
                    conversational_response = await _run_blocking_with_timeout(
                        generate_conversational_response,
                        user_message,
                        intent,
                        client=client,
                        model=config.openai_intent_model_name,
                        timeout_seconds=getattr(config, "conversation_timeout_seconds", 4),
                        conversation_adapter=conversation_adapter,
                        openai_conversation_id=openai_conversation_id,
                    )
                    if conversational_response:
                        mark_trace(recorded=bool(conversation_adapter and openai_conversation_id))
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

    fallback_conversational_response = _fallback_conversational_response(user_message, config)
    if fallback_conversational_response:
        logger.info("query_completed duration_ms=0 evidence_count=0 source_types=none decision_state=solicita_contexto escalated=False")
        return fallback_conversational_response

    try:
        evidence = await _run_blocking_with_timeout(
            retrieve_evidence,
            retrieval_message,
            client=client,
            config=config,
            timeout_seconds=config.retrieval_timeout_seconds,
            grace_seconds=getattr(config, "retrieval_grace_seconds", 0),
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

    if evidence and not _evidence_matches_explicit_product(retrieval_message, evidence):
        logger.info("La evidencia no contiene el producto solicitado explícitamente.")
        decision = classify_case_by_rules(retrieval_message, [])
        logger.info(
            "query_completed duration_ms=%s evidence_count=0 source_types=none "
            "decision_state=%s escalated=%s",
            round((perf_counter() - started_at) * 1000),
            decision.estado,
            decision.requiere_escalamiento,
        )
        return format_user_response(decision, config=config)

    evidence = _filter_contextual_version_evidence(retrieval_message, evidence)
    logger.info("Consulta recibida. Evidencias recuperadas: %s", len(evidence))
    fallback_decision = classify_case_by_rules(retrieval_message, evidence)

    # Version lookups have an exact retrieval boundary and are rendered from
    # the cited fragments. Keeping that deterministic prevents the classifier
    # from replacing the documented details with a generic incident summary.
    if has_explicit_version_request(retrieval_message):
        decision = fallback_decision
    elif (
        is_direct_document_question(retrieval_message, evidence)
        or requires_deterministic_grounded_answer(retrieval_message)
    ):
        # Direct document answers are rendered deterministically from the
        # retrieved fragment. This prevents a generic or invented model
        # summary from replacing evidence the user can verify.
        decision = fallback_decision
    elif getattr(config, "model_endpoint_configured", True):
        try:
            decision = await _run_blocking_with_timeout(
                classify_case,
                user_message=retrieval_message,
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
        fallback_decision.estado == "sin_evidencia"
        and decision.estado != "sin_evidencia"
        and requires_explicit_facet_evidence(retrieval_message)
    ) or (
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
