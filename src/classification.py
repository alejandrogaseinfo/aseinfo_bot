import json
import re
from urllib.parse import unquote, urlparse

from document_index import has_requested_action_coverage, tokenize
from models import BotDecision, EvidenceSource
from query_plan import build_query_plan


SYSTEM_PROMPT = """
Usted es Libras, un asistente formal del equipo de desarrollo.
Responde siempre en espanol, con tono tecnico y prudente.
No invente tickets, estados, causas, fechas, versiones ni soluciones.
Clasifique cada caso en uno de estos estados:
- resuelto
- en_progreso
- similar_del_pasado
- sin_evidencia

Debe devolver un JSON valido con esta estructura exacta:
{
  "estado": "resuelto | en_progreso | similar_del_pasado | sin_evidencia",
  "confianza": "alta | media | baja",
  "resumen": "string",
  "siguiente_accion": "string",
  "requiere_escalamiento": true
}

Reglas:
- Para preguntas factuales sobre políticas, procedimientos o manuales, use "resuelto" cuando la evidencia responda directamente a la pregunta. En ese caso, el campo "resumen" debe responder la pregunta con los valores, condiciones o fórmulas explícitamente documentados.
- Use "resuelto" para incidentes solo si la evidencia muestra una solucion o instruccion documentada.
- Use "en_progreso" solo si la evidencia muestra seguimiento activo.
- Use "similar_del_pasado" solo si la evidencia es historica o analogica.
- Use "sin_evidencia" si la evidencia es insuficiente o inexistente.
- Si faltan pruebas solidas, marque requiere_escalamiento=true.
""".strip()
VERSION_PATTERN = re.compile(r"(?<![\d.])(\d+(?:\.\d+){2,})(?!\d|\.\d)")
SOFTWARE_REQUIREMENTS_PATTERN = re.compile(
    r"\b(?:pre\s*)?requisitos?\b.{0,48}\b(?:software|instalaci[oó]n)\b|"
    r"\b(?:software|instalaci[oó]n)\b.{0,48}\b(?:pre\s*)?requisitos?\b",
    re.IGNORECASE,
)
DOCUMENT_VERSION_PROCEDURE_PATTERN = re.compile(
    r"\b(?:crear|generar|registrar|agregar|subir|nueva)\w*\b.{0,64}"
    r"\bversi[oó]n\b.{0,64}\bdocument\w*\b|"
    r"\bdocument\w*\b.{0,64}\b(?:crear|generar|registrar|agregar|subir|nueva)\w*\b"
    r".{0,64}\bversi[oó]n\b",
    re.IGNORECASE,
)
PARAMETER_LIST_REQUEST_PATTERN = re.compile(
    r"\bqu[eé]\s+par[aá]metros?\b|\bpar[aá]metros?\s+se\s+pued\w*\b",
    re.IGNORECASE,
)
PARAMETER_EVIDENCE_PATTERN = re.compile(
    r"\bpar[aá]metr\w*\b.{0,240}"
    r"\b(?:c[oó]digo|nombre|valor|rango|porcentaje|tipo)\b\s*[:=-]|"
    # Algunos manuales nombran el parámetro directamente (camel case) o
    # describen los campos configurables sin una tabla ``nombre: valor``.
    # Exigimos un identificador o un campo concreto para no aceptar una mera
    # mención relacionada con incapacidades.
    r"\b(?:prorroga|incapacidades)[a-z0-9]+\b|"
    r"\b(?:rango\s+de\s+(?:los\s+)?d[ií]as|%\s*(?:de\s+)?(?:descuento|subsidio)|"
    r"tipo\s+de\s+(?:ingreso|descuento))\b",
    re.IGNORECASE,
)
AMBIGUOUS_EXTENSION_PATTERN = re.compile(
    r"\bpr[oó]rroga\b(?!\s+de\s+(?:contratos?|incapacidades?))",
    re.IGNORECASE,
)
EXAMPLE_REQUEST_PATTERN = re.compile(r"\b(?:dame|indica|muestra|lista)\b.{0,48}\bejempl\w*\b|\bejempl\w*\b", re.IGNORECASE)
INCAPACITY_CLASSIFICATION_PATTERN = re.compile(
    r"\b(?:c[oó]mo|como)\s+se\s+clasific\w*\b.{0,80}\bincapac\w*\b|"
    r"\bclasificaci[oó]n\b.{0,80}\bincapac\w*\b",
    re.IGNORECASE,
)
CALCULATION_REQUEST_PATTERN = re.compile(
    r"\b(?:calcul\w*|f[oó]rmula|equival\w*|cu[aá]nt[oa]s?)\b.{0,96}\baguinaldo\b|"
    r"\baguinaldo\b.{0,96}\b(?:calcul\w*|f[oó]rmula|equival\w*|cu[aá]nt[oa]s?)\b",
    re.IGNORECASE,
)
CALCULATION_EVIDENCE_PATTERN = re.compile(
    r"\baguinaldo\b.{0,160}\b(?:f[oó]rmula|equival\w*|proporcional\w*|"
    r"salario\s+(?:diario|base)|d[ií]as?\s+(?:de\s+salario|laborad\w*|trabajad\w*)|"
    r"divid\w*|multiplic\w*|por\s+cada)\b|"
    r"\b(?:f[oó]rmula|equival\w*|proporcional\w*|salario\s+(?:diario|base)|"
    r"d[ií]as?\s+(?:de\s+salario|laborad\w*|trabajad\w*)|divid\w*|multiplic\w*|"
    r"por\s+cada)\b.{0,160}\baguinaldo\b",
    re.IGNORECASE,
)
POST_UPDATE_VALIDATION_REQUEST_PATTERN = re.compile(
    r"\b(?:despu[eé]s|posterior|luego|una\s+vez)\b.{0,96}\b(?:actualiz\w*|instal\w*)\b"
    r".{0,96}\b(?:valid\w*|verif\w*|confirm\w*|revis\w*)\b|"
    r"\b(?:valid\w*|verif\w*|confirm\w*|revis\w*)\b.{0,96}"
    r"\b(?:despu[eé]s|posterior|luego|una\s+vez)\b.{0,96}\b(?:actualiz\w*|instal\w*)\b",
    re.IGNORECASE,
)
POST_UPDATE_VALIDATION_EVIDENCE_PATTERN = re.compile(
    r"\b(?:despu[eé]s|posterior|luego|una\s+vez)\b.{0,120}\b(?:actualiz\w*|instal\w*)\b"
    r".{0,160}\b(?:valid\w*|verif\w*|confirm\w*|revis\w*)\b|"
    r"\b(?:valid\w*|verif\w*|confirm\w*|revis\w*)\b.{0,120}"
    r"\b(?:despu[eé]s|posterior|luego|una\s+vez)\b.{0,120}\b(?:actualiz\w*|instal\w*)\b",
    re.IGNORECASE,
)
POST_REINSTALLATION_VALIDATION_REQUEST_PATTERN = re.compile(
    r"\b(?:despu[eé]s|luego|tras)\b.{0,96}\breinstal\w*\b.{0,96}"
    r"\b(?:valid\w*|verif\w*|confirm\w*|revis\w*)\b|"
    r"\b(?:valid\w*|verif\w*|confirm\w*|revis\w*)\b.{0,96}"
    r"\b(?:despu[eé]s|luego|tras)\b.{0,96}\breinstal\w*\b",
    re.IGNORECASE,
)
KEY_VAULT_PATTERN = re.compile(r"\bkey\s+vault\b", re.IGNORECASE)
DIAGNOSTIC_LIST_REQUEST_PATTERN = re.compile(
    r"\b(?:servicios?|validaciones?|comprobaciones?)\b.{0,72}"
    r"\b(?:revis|valid|verif|confirm)\w*\b|"
    r"\b(?:revis|valid|verif|confirm)\w*\b.{0,72}"
    r"\b(?:servicios?|validaciones?|comprobaciones?)\b",
    re.IGNORECASE,
)
DIAGNOSTIC_CHECK_PATTERN = re.compile(
    r"\b(?:revis\w*|valid\w*|verif\w*|confirm\w*|asegur\w*)\b",
    re.IGNORECASE,
)
INCOMPLETE_DIAGNOSTIC_HEADING_PATTERN = re.compile(
    r"\b(?:estos|los)\s+servicios?\s+est[aá]n\s+(?:corriendo|en\s+ejecuci[oó]n)\.?$",
    re.IGNORECASE,
)
DOWNLOAD_FAILURE_PATTERN = re.compile(
    r"\b(?:no\s+(?:logra|puede|permite)|falla|error|problema)\b.{0,72}"
    r"\b(?:descarg\w*|baj\w*)\b|"
    r"\b(?:descarg\w*|baj\w*)\b.{0,72}"
    r"\b(?:no\s+(?:logra|puede|permite)|falla|error|problema)\b",
    re.IGNORECASE,
)
DOWNLOAD_DIAGNOSTIC_EVIDENCE_PATTERN = re.compile(
    r"\b(?:falla|error|problema|revis\w*|verif\w*|valid\w*)\b",
    re.IGNORECASE,
)
PROCEDURE_STEP_MARKER = re.compile(
    r"\b(?:haga clic|seleccione|selecciona|digite|ingrese|elija|marque|abra|presione|"
    r"seleccionar|confirme|renombre|renombrar|"
    r"importe|importar|ejecute)\b",
    re.IGNORECASE,
)
PROCEDURE_NOISE_BOUNDARY = re.compile(
    r"\b(?:info|warn(?:ing)?|error|exception|stack\s+trace|connection\s+string|"
    r"cadena\s+de\s+conexi[oó]n|server\s*=|data\s+source\s*=)\b|"
    r"\b20\d{2}[-/]\d{2}[-/]\d{2}\b",
    re.IGNORECASE,
)
MAX_PROCEDURE_STEPS_IN_RESPONSE = 6
MIN_SECONDARY_PROCEDURE_STEPS = 2
UNDERSPECIFIED_QUERY_PATTERNS = (
    re.compile(r"^(?:que|qué)\s+(?:se\s+)?(?:debe|hay\s+que)\s+(?:revisar|hacer|validar|verificar)\??$", re.IGNORECASE),
    re.compile(r"^(?:no\s+(?:me\s+)?funciona|no\s+sirve|tengo\s+un\s+problema)\.?$", re.IGNORECASE),
)
PROCEDURAL_SCAFFOLD_TOKENS = {
    "como", "pued", "puede", "pueden", "debe", "deben", "parametro", "modific",
    "configur", "clasific", "arreglar", "script", "evolution", "revis", "valid",
    "verific", "confirm", "hacer", "procedimiento",
}


def _combined_evidence_text(evidence: list[EvidenceSource]) -> str:
    return " ".join(
        f"{source.titulo} {source.fragmento} {source.ubicacion}".lower()
        for source in evidence
    )


def is_underspecified_query(user_message: str) -> bool:
    """Identify generic support utterances that need context before search."""
    normalized = " ".join((user_message or "").casefold().split()).strip()
    normalized = normalized.strip("¿¡")
    if not normalized:
        return True
    return any(pattern.fullmatch(normalized) for pattern in UNDERSPECIFIED_QUERY_PATTERNS)


def needs_extension_subject_context(user_message: str) -> bool:
    """Ask for the prórroga domain before retrieving an ambiguous question."""
    return bool(AMBIGUOUS_EXTENSION_PATTERN.search(user_message or ""))


def is_direct_document_question(user_message: str, evidence: list[EvidenceSource]) -> bool:
    """Identify a factual question directly covered by a retrieved document.

    This prevents a policy/manual from being treated as a historical incident
    merely because it is not a bug fix. It intentionally does not require the
    user to say "manual" or "política": normal users ask the factual question
    directly.
    """
    query_tokens = set(tokenize(user_message or ""))
    if not query_tokens:
        return False

    normalized_question = (user_message or "").strip().lower()
    question_markers = (
        "?",
        "cuál",
        "cual",
        "cómo",
        "como",
        "qué",
        "que ",
        "cuánt",
        "cuant",
        "dónde",
        "donde",
    )
    direct_request_markers = (
        "dame ",
        "indica ",
        "muestra ",
        "enumera ",
        "lista ",
    )
    if not any(marker in normalized_question for marker in (*question_markers, *direct_request_markers)):
        return False

    for source in evidence:
        if source.tipo not in {"sharepoint", "azure_ai_search", "documento", "setup"}:
            continue
        # La estrategia v2 ya verificó cobertura requisito por requisito con
        # texto directo. No vuelva a degradarla a una coincidencia de tokens.
        if source.covered_requirements:
            return True
        source_tokens = set(tokenize(f"{source.titulo} {source.fragmento}"))
        required_overlap = 2 if len(query_tokens) <= 4 else 3
        if len(query_tokens.intersection(source_tokens)) >= required_overlap:
            return True
    return False


def _procedure_steps(text: str) -> list[str]:
    """Extract ordered imperative steps that are explicitly present in a fragment."""
    compact = " ".join((text or "").split())
    if not compact:
        return []
    matches = list(PROCEDURE_STEP_MARKER.finditer(compact))
    steps: list[str] = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(compact)
        step = compact[match.start() : end]
        # Los fragmentos indexados pueden incluir trazas o cadenas de conexión
        # después del último paso. No son instrucciones y no deben llegar al chat.
        step = PROCEDURE_NOISE_BOUNDARY.split(step, maxsplit=1)[0].strip(" .;:")
        if len(step) >= 8 and step not in steps:
            steps.append(step)
    return steps


def _is_procedural_request(user_message: str) -> bool:
    normalized = " ".join((user_message or "").casefold().split())
    return bool(
        re.search(
            r"(?:cómo|como)\s+(?:se\s+)?[a-záéíóúñ]+|"
            r"(?:qué|que)\s+se\s+debe\s+(?:hacer|revisar)|"
            r"\bpasos?\b|\bprocedimiento\b",
            normalized,
        )
    )


def _normalized_step(step: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", step.casefold()).strip()


def _steps_are_equivalent(left: str, right: str) -> bool:
    """Treat minor wording changes as the same documented procedural step."""
    left_tokens = set(tokenize(left))
    right_tokens = set(tokenize(right))
    if not left_tokens or not right_tokens:
        return _normalized_step(left) == _normalized_step(right)
    overlap = len(left_tokens.intersection(right_tokens))
    union = len(left_tokens.union(right_tokens))
    return overlap / union >= 0.75


def _contains_equivalent_step(step: str, existing: list[str]) -> bool:
    return any(_steps_are_equivalent(step, candidate) for candidate in existing)


def _focused_procedure_evidence(
    user_message: str, evidence: list[EvidenceSource]
) -> list[EvidenceSource]:
    """Keep one primary source and meaningful secondary procedural evidence.

    A secondary fragment from the legacy index has no explicit requirement
    mapping, so it is treated as duplicate-risk and omitted. The v2 index may
    contribute a secondary source only when it carries explicit covered
    requirements and at least two new procedural steps.
    """
    if EXAMPLE_REQUEST_PATTERN.search(user_message or ""):
        examples = [
            source for source in evidence
            if re.search(r"\bejempl\w*\b", source.fragmento or "", re.IGNORECASE)
        ]
        return examples[:1] or evidence[:1]

    if INCAPACITY_CLASSIFICATION_PATTERN.search(user_message or ""):
        classifications = [
            source for source in evidence
            if re.search(r"\bclasific\w*\b|seg[uú]n\s+su\s+(?:duraci[oó]n|magnitud|cualidad)", source.fragmento or "", re.IGNORECASE)
        ]
        return classifications[:1] or evidence[:1]

    if not _is_procedural_request(user_message):
        return evidence

    # When the index includes a dedicated solution instruction plus an
    # incidental configuration document, keep the solution artifact as the
    # procedural source. Diagnostic requests retain their complementary
    # checks from multiple pages.
    if not DIAGNOSTIC_LIST_REQUEST_PATTERN.search(user_message or ""):
        solution_sources = [
            source for source in evidence if "/soluciones/" in unquote(urlparse(source.ubicacion).path).casefold()
        ]
        if solution_sources:
            return [solution_sources[0]]

    candidates = [
        (
            source,
            _procedure_steps(source.fragmento),
            index,
            len(
                set(tokenize(user_message or ""))
                & set(tokenize(f"{source.titulo} {source.fragmento}"))
            ),
        )
        for index, source in enumerate(evidence)
    ]
    candidates = [candidate for candidate in candidates if candidate[1]]
    if not candidates or max(len(steps) for _, steps, _, _ in candidates) < 3:
        return evidence

    best_source, best_steps, _, _ = max(
        candidates,
        key=lambda item: (item[3], len(item[1]), -item[2]),
    )
    selected = [best_source]
    covered_steps = list(best_steps)
    for source, steps, _, _ in candidates:
        if source is best_source:
            continue
        new_steps = [step for step in steps if not _contains_equivalent_step(step, covered_steps)]
        if (
            source.covered_requirements
            and len(new_steps) >= MIN_SECONDARY_PROCEDURE_STEPS
        ):
            selected.append(source)
            covered_steps.extend(new_steps)
    return selected


def _unique_procedure_steps(evidence: list[EvidenceSource]) -> list[str]:
    steps: list[str] = []
    for source in evidence:
        for step in _procedure_steps(source.fragmento):
            if _contains_equivalent_step(step, steps):
                continue
            steps.append(step)
    return steps


def _is_code_evidence(source: EvidenceSource) -> bool:
    """Identify executable artifacts that should not be pasted as chat prose."""
    document_type = (source.document_type or "").casefold()
    title = (source.titulo or "").casefold()
    return document_type in {"sql", "code", "script"} or ".sql" in title


def _diagnostic_checks(evidence: list[EvidenceSource]) -> list[str]:
    """Extract complete, directly stated validation checks from evidence."""
    checks: list[str] = []
    for source in evidence:
        for sentence in re.split(r"(?<=[.!?])\s+|\n+", source.fragmento or ""):
            compact = " ".join(sentence.split()).strip(" -;,")
            if (
                len(compact) < 12
                or compact.endswith(":")
                or not DIAGNOSTIC_CHECK_PATTERN.search(compact)
                or INCOMPLETE_DIAGNOSTIC_HEADING_PATTERN.search(compact)
            ):
                continue
            if not _contains_equivalent_step(compact, checks):
                checks.append(compact)
    return checks


def _grounded_document_summary(user_message: str, evidence: list[EvidenceSource]) -> str:
    """Return a concise answer made only from the most relevant evidence text."""
    focused_evidence = _focused_procedure_evidence(user_message, evidence)
    if focused_evidence and all(_is_code_evidence(source) for source in focused_evidence):
        descriptions = [source.descripcion.strip() for source in focused_evidence if source.descripcion.strip()]
        if descriptions:
            source = focused_evidence[0]
            script_name = source.titulo.split(" — ", 1)[0]
            description = descriptions[0].rstrip(".")
            if (source.document_type or "").casefold() == "sql" or script_name.casefold().endswith(".sql"):
                return f"El script {script_name} es un procedimiento almacenado que {description}."
            return f"El script {script_name} tiene la siguiente descripción: {description}."
        return (
            "La evidencia recuperada es un script técnico relacionado con la consulta. "
            "No reproduzco código ejecutable completo en el chat; revise el archivo citado "
            "y ejecútelo únicamente siguiendo el procedimiento de control de cambios aplicable."
        )
    diagnostic_checks = _diagnostic_checks(focused_evidence)
    if diagnostic_checks and DIAGNOSTIC_CHECK_PATTERN.search(user_message or ""):
        return "Según la documentación, valide lo siguiente:\n" + "\n".join(
            f"{index}. {check}"
            for index, check in enumerate(diagnostic_checks[:4], start=1)
        )
    if INCAPACITY_CLASSIFICATION_PATTERN.search(user_message or ""):
        classification_text = " ".join(
            " ".join((source.fragmento or "").split()) for source in focused_evidence
        )
        categories = []
        for label, pattern in (
            ("duración", r"seg[uú]n\s+su\s+duraci[oó]n.{0,220}?(?:permanentes?\s+y\s+temporales?|temporales?\s+y\s+permanentes?)"),
            ("magnitud", r"seg[uú]n\s+su\s+magnitud.{0,220}?(?:parciales?\s+y\s+totales?|totales?\s+y\s+parciales?)"),
            ("cualidad", r"seg[uú]n\s+su\s+cualidad.{0,220}?(?:f[ií]sicas?\s+y\s+ps[ií]quicas?|ps[ií]quicas?\s+y\s+f[ií]sicas?)"),
        ):
            match = re.search(pattern, classification_text, re.IGNORECASE)
            if match:
                categories.append(match.group(0).rstrip(". "))
        if categories:
            return "Según la documentación, las incapacidades se clasifican así: " + "; ".join(categories) + "."

    if EXAMPLE_REQUEST_PATTERN.search(user_message or ""):
        for source in focused_evidence:
            text = " ".join((source.fragmento or "").split())
            match = re.search(r"\bejempl\w*[^:]{0,120}:\s*(.+?)(?=\b(?:del\s+[aá]rea|haga\s+clic|seleccione|digite)\b|$)", text, re.IGNORECASE)
            if match:
                examples = match.group(1).strip(" .;:")
                if examples:
                    return f"Según la documentación, los ejemplos son: {examples}."

    if PARAMETER_LIST_REQUEST_PATTERN.search(user_message or ""):
        parameters: list[tuple[str, str]] = []
        for source in focused_evidence:
            text = " ".join((source.fragmento or "").split())
            matches = list(re.finditer(
                r"\b(?:ProrrogaContrato|Incapacidades)[A-Za-z0-9]+\b", text
            ))
            for index, match in enumerate(matches):
                name = match.group(0)
                end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
                detail = text[match.end():end]
                detail = re.sub(r"^(?:\s*[:.-]\s*)", "", detail).strip()
                detail = re.split(r"\b(?:Ejemplo\d*|Del\s+[aá]rea|Haga\s+clic|Seleccione)\b", detail, maxsplit=1, flags=re.IGNORECASE)[0]
                detail = detail[:210].rsplit(" ", 1)[0] if len(detail) > 210 else detail
                pair = (name, detail.rstrip(". "))
                if pair not in parameters:
                    parameters.append(pair)
        if parameters:
            lines = [
                f"- {name}" + (f": {detail}." if detail else ".")
                for name, detail in parameters[:6]
            ]
            return "Según la documentación, los parámetros identificados son:\n" + "\n".join(lines)

    # A page heading such as ``Proceso para ... 1`` is a retrieval hit, not a
    # usable procedure. Do not turn a title or table-of-contents fragment into
    # an operational instruction; the caller will classify it as insufficient.
    if _is_procedural_request(user_message):
        combined = " ".join(" ".join((source.fragmento or "").split()) for source in focused_evidence)
        if not _procedure_steps(combined) and re.fullmatch(
            r"(?:p[aá]gina\s+\d+\s+)?(?:proceso|procedimiento)\s+.+?\s+\d+\.?",
            combined.strip(),
            re.IGNORECASE,
        ):
            return "Se recuperó documentación relacionada, pero no contiene pasos suficientes para responder con seguridad."

    procedure_steps = _unique_procedure_steps(focused_evidence)
    if _is_procedural_request(user_message) and len(procedure_steps) >= 3:
        return "Según la documentación, los pasos son:\n" + "\n".join(
            f"{index}. {step}"
            for index, step in enumerate(
                procedure_steps[:MAX_PROCEDURE_STEPS_IN_RESPONSE], start=1
            )
        )

    query_tokens = set(tokenize(user_message))
    candidates: list[tuple[int, str]] = []
    for source in focused_evidence:
        text = " ".join((source.fragmento or "").split())
        text = re.sub(r"^Página\s+\d+\s+", "", text, flags=re.IGNORECASE)
        if not text:
            continue
        sentences = [
            sentence.strip()
            for sentence in re.split(r"(?<=[.!?])\s+", text)
            if sentence.strip()
        ] or [text]
        for sentence in sentences:
            candidates.append((len(query_tokens.intersection(tokenize(sentence))), sentence))

    if not candidates:
        return "Se recuperó documentación relacionada, pero el fragmento no contiene un detalle suficiente para responder con seguridad."
    _, excerpt = max(candidates, key=lambda item: item[0])
    if len(excerpt) > 520:
        excerpt = f"{excerpt[:520].rsplit(' ', 1)[0]}..."
    # When a release note is the direct source, retain its explicit product
    # version in the answer even if the excerpt starts at the change sentence.
    # This is derived from indexed title/content metadata, never inferred from
    # the requested wording.
    release_versions = []
    for source in focused_evidence:
        identity = f"{source.titulo} {source.document_version}"
        if "readme" not in identity.casefold():
            continue
        for match in VERSION_PATTERN.findall(identity):
            if match not in release_versions:
                release_versions.append(match)
    if release_versions and not any(version in excerpt for version in release_versions):
        excerpt = f"Evolution {release_versions[0]}: {excerpt}"
    return f"Según la documentación: {excerpt}"


def _requested_version(user_message: str) -> str | None:
    match = VERSION_PATTERN.search(user_message or "")
    return match.group(1) if match else None


def has_explicit_version_request(user_message: str) -> bool:
    return _requested_version(user_message) is not None


def _version_document_summary(version: str, evidence: list[EvidenceSource]) -> str:
    """Answer a version lookup from its cited text without inventing changes."""
    details = " ".join(source.fragmento.strip() for source in evidence[:2] if source.fragmento.strip())
    details = " ".join(details.split())
    unconfirmed = any(source.version_confirmed is False for source in evidence)
    if not details:
        if unconfirmed:
            return (
                "La documentación recuperada está relacionada con la consulta, "
                "pero no confirma explícitamente su correspondencia con la versión "
                f"solicitada ({version}) y el fragmento no contiene detalles suficientes."
            )
        return f"Se encontró documentación para Evolution {version}, pero el fragmento recuperado no contiene detalles suficientes."
    if len(details) > 900:
        details = f"{details[:900].rsplit(' ', 1)[0]}..."
    if unconfirmed:
        return (
            "La documentación recuperada indica lo siguiente, pero no confirma "
            f"explícitamente que corresponda a Evolution {version}: {details}"
        )
    return f"Para Evolution {version}, la documentación indica: {details}"


def _version_answer_is_none(user_message: str, evidence: list[EvidenceSource]) -> bool:
    """Keep an explicit 'Ninguno' result concise instead of expanding a heading."""
    asks_for_software_requirements = bool(
        re.search(r"nuevos?\s+requisitos?\s+de\s+software", user_message or "", re.IGNORECASE)
    )
    if not asks_for_software_requirements:
        return False
    return any(
        re.search(
            r"nuevos?\s+requisitos?\s+de\s+software.{0,120}\bninguno\b",
            source.fragmento,
            re.IGNORECASE | re.DOTALL,
        )
        for source in evidence
    )


def _evidence_covers_requested_facet(
    user_message: str, evidence: list[EvidenceSource]
) -> bool:
    """Reject evidence that answers an adjacent question instead of the asked facet.

    Version Readmes often contain both a changelog and installation requirements.
    Likewise, a document may mention a ``DocumentoGestionado`` type without
    documenting how to create a new version.  These high-risk forms need a
    local anchor in the fragment before it can be rendered as an answer.
    """
    normalized_question = user_message or ""
    fragments = "\n".join(source.fragmento or "" for source in evidence)
    if _is_procedural_request(normalized_question):
        compact_fragments = " ".join(fragments.split())
        if not _procedure_steps(compact_fragments) and re.fullmatch(
            r"(?:p[aá]gina\s+\d+\s+)?(?:proceso|procedimiento)\s+.+?\s+\d+\.?",
            compact_fragments,
            re.IGNORECASE,
        ):
            return False
    if SOFTWARE_REQUIREMENTS_PATTERN.search(normalized_question):
        return bool(SOFTWARE_REQUIREMENTS_PATTERN.search(fragments))
    if DOCUMENT_VERSION_PROCEDURE_PATTERN.search(normalized_question):
        return bool(DOCUMENT_VERSION_PROCEDURE_PATTERN.search(fragments))
    if PARAMETER_LIST_REQUEST_PATTERN.search(normalized_question):
        return bool(PARAMETER_EVIDENCE_PATTERN.search(fragments))
    if CALCULATION_REQUEST_PATTERN.search(normalized_question):
        return bool(CALCULATION_EVIDENCE_PATTERN.search(fragments))
    if POST_UPDATE_VALIDATION_REQUEST_PATTERN.search(normalized_question):
        return bool(POST_UPDATE_VALIDATION_EVIDENCE_PATTERN.search(fragments))
    if POST_REINSTALLATION_VALIDATION_REQUEST_PATTERN.search(normalized_question):
        return bool(_diagnostic_checks(evidence))
    if KEY_VAULT_PATTERN.search(normalized_question):
        return bool(KEY_VAULT_PATTERN.search(fragments))
    if DIAGNOSTIC_LIST_REQUEST_PATTERN.search(normalized_question):
        return bool(_diagnostic_checks(evidence))
    if DOWNLOAD_FAILURE_PATTERN.search(normalized_question):
        # A navigation path for downloading is not an incident diagnostic. It
        # must explicitly describe a failure check before we advise what to
        # review when a permitted user cannot download a document.
        return bool(DOWNLOAD_DIAGNOSTIC_EVIDENCE_PATTERN.search(fragments))
    return True


def requires_explicit_facet_evidence(user_message: str) -> bool:
    """Identify questions that must not be upgraded from adjacent evidence.

    A model may summarize a broadly related fragment fluently, but these
    requests require a concrete list, formula, post-change check or named
    platform component. When rules cannot establish that facet, Libras must
    abstain instead of letting the model infer it.
    """
    question = user_message or ""
    return bool(
        PARAMETER_LIST_REQUEST_PATTERN.search(question)
        or CALCULATION_REQUEST_PATTERN.search(question)
        or POST_UPDATE_VALIDATION_REQUEST_PATTERN.search(question)
        or POST_REINSTALLATION_VALIDATION_REQUEST_PATTERN.search(question)
        or KEY_VAULT_PATTERN.search(question)
    )


def requires_deterministic_grounded_answer(user_message: str) -> bool:
    """Keep high-risk evidence facets out of a free-form model summary."""
    return requires_explicit_facet_evidence(user_message)


def _v2_evidence_assessment(
    user_message: str, evidence: list[EvidenceSource]
) -> tuple[list[EvidenceSource], tuple[str, ...], tuple[str, ...]] | None:
    """Return v2 direct evidence and coverage, when the retrieval used it.

    The attribute is deliberately the contract between retrieval and response:
    a source is citable only after direct evidence has covered at least one
    requirement.  Legacy sources do not carry that attribute and retain their
    existing behaviour until the strategy flag is enabled.
    """
    if not any(source.covered_requirements for source in evidence):
        return None

    plan = build_query_plan(user_message)
    covered = {
        requirement
        for source in evidence
        for requirement in source.covered_requirements
    }
    direct_sources = [
        source
        for source in evidence
        if source.covered_requirements and source.evidence_kind != "navigation"
    ]
    missing = tuple(
        requirement.identifier
        for requirement in plan.requirements
        if requirement.identifier not in covered
    )
    return direct_sources, tuple(sorted(covered)), missing


def _has_concrete_documentary_evidence(
    user_message: str, evidence: list[EvidenceSource]
) -> bool:
    """Allow grounded answers when action and a substantive topic both match.

    Filename-heavy procedures and manuals often use a different wording from
    the user's question. Action coverage remains the safety gate; the topic
    overlap prevents a generic instruction from turning tangential evidence
    into an answer.
    """
    query_topics = set(tokenize(user_message)) - PROCEDURAL_SCAFFOLD_TOKENS
    if not query_topics:
        return False
    return any(
        has_requested_action_coverage(
            user_message, f"{source.titulo} {source.fragmento}"
        )
        and query_topics.intersection(tokenize(f"{source.titulo} {source.fragmento}"))
        for source in evidence
    )


def _partial_requirement_text(user_message: str, missing: tuple[str, ...]) -> str:
    plan = build_query_plan(user_message)
    missing_texts = [
        requirement.text
        for requirement in plan.requirements
        if requirement.identifier in missing
    ]
    return "; ".join(missing_texts)


def classify_case_by_rules(
    user_message: str,
    evidence: list[EvidenceSource],
) -> BotDecision:
    query = (user_message or "").lower()
    evidence_text = _combined_evidence_text(evidence)

    if not evidence:
        return BotDecision(
            estado="sin_evidencia",
            confianza="baja",
            resumen="No se encontro evidencia suficiente en las fuentes documentales consultadas.",
            fuentes=[],
            siguiente_accion="Escale el caso al equipo de desarrollo para una revision manual.",
            requiere_escalamiento=True,
        )

    if not _evidence_covers_requested_facet(user_message, evidence):
        return BotDecision(
            estado="sin_evidencia",
            confianza="baja",
            resumen=(
                "No se encontro evidencia directa para el detalle solicitado en las "
                "fuentes documentales consultadas."
            ),
            fuentes=[],
            siguiente_accion=(
                "Revise si existe un procedimiento o Readme que documente "
                "explícitamente ese detalle antes de aplicarlo."
            ),
            requiere_escalamiento=True,
        )

    v2_assessment = _v2_evidence_assessment(user_message, evidence)
    if v2_assessment is not None:
        direct_sources, _covered, missing = v2_assessment
        if not direct_sources:
            return BotDecision(
                estado="sin_evidencia",
                confianza="baja",
                resumen="No se encontro evidencia directa suficiente en las fuentes documentales consultadas.",
                fuentes=[],
                siguiente_accion="Escale el caso al equipo de desarrollo para una revision manual.",
                requiere_escalamiento=True,
            )

        answer_sources = _focused_procedure_evidence(user_message, direct_sources)
        summary = _grounded_document_summary(user_message, answer_sources)
        if missing:
            return BotDecision(
                estado="resuelto",
                confianza="media",
                resumen=(
                    f"{summary}\n\n"
                    "No encontré evidencia directa para esta parte de la consulta: "
                    f"{_partial_requirement_text(user_message, missing)}."
                ),
                fuentes=answer_sources,
                siguiente_accion=(
                    "Revise el documento citado para la parte confirmada y escale "
                    "la parte no documentada para una revision manual."
                ),
                requiere_escalamiento=True,
            )

        return BotDecision(
            estado="resuelto",
            confianza="alta",
            resumen=summary,
                fuentes=answer_sources,
            siguiente_accion="Revise el documento citado para validar el detalle aplicable a su caso.",
            requiere_escalamiento=False,
        )

    action_covered = any(
        has_requested_action_coverage(
            user_message, f"{source.titulo} {source.fragmento}"
        )
        for source in evidence
    )
    parameter_facet_covered = bool(
        PARAMETER_LIST_REQUEST_PATTERN.search(user_message or "")
        and PARAMETER_EVIDENCE_PATTERN.search(evidence_text)
    )
    if not action_covered and not parameter_facet_covered:
        return BotDecision(
            estado="sin_evidencia",
            confianza="baja",
            resumen="No se encontro evidencia suficiente en las fuentes documentales consultadas.",
            fuentes=[],
            siguiente_accion="Escale el caso al equipo de desarrollo para una revision manual.",
            requiere_escalamiento=True,
        )

    requested_version = _requested_version(user_message)
    if requested_version:
        summary = (
            "Ninguno."
            if _version_answer_is_none(user_message, evidence)
            else _version_document_summary(requested_version, evidence)
        )
        return BotDecision(
            estado="resuelto",
            confianza="alta",
            resumen=summary,
            fuentes=evidence,
            siguiente_accion="Revise el Readme citado antes de aplicar los cambios de esa versión.",
            requiere_escalamiento=False,
        )

    if is_direct_document_question(user_message, evidence) or _has_concrete_documentary_evidence(
        user_message, evidence
    ):
        answer_sources = _focused_procedure_evidence(user_message, evidence)
        return BotDecision(
            estado="resuelto",
            confianza="alta",
            resumen=_grounded_document_summary(user_message, answer_sources),
            fuentes=answer_sources,
            siguiente_accion="Revise el documento citado para validar el detalle aplicable a su caso.",
            requiere_escalamiento=False,
        )

    resolved_markers = [
        "advertencia",
        "antes de instalar",
        "ejecutar el script",
        "resolucion",
        "corrige",
        "correccion",
        "hotfix",
    ]
    in_progress_markers = [
        "seguimiento activo",
        "ticket activo",
        "reportado",
        "en progreso",
        "pendiente de confirmacion",
    ]
    historical_markers = [
        "historico",
        "antecedente",
        "referencia",
        "caso historico",
        "puede servir como antecedente",
    ]

    if any(marker in evidence_text for marker in resolved_markers):
        return BotDecision(
            estado="resuelto",
            confianza="alta",
            resumen="Se encontro documentacion que describe el problema y una accion concreta de correccion o validacion previa a la instalacion.",
            fuentes=evidence,
            siguiente_accion="Aplique la instruccion documentada indicada en la evidencia y repita la prueba antes de escalar el caso.",
            requiere_escalamiento=False,
        )

    if any(marker in evidence_text for marker in in_progress_markers):
        return BotDecision(
            estado="en_progreso",
            confianza="media",
            resumen="La evidencia indica que el caso ya fue reportado y tiene seguimiento activo.",
            fuentes=evidence,
            siguiente_accion="Valide si su caso coincide con la evidencia encontrada y de seguimiento al ticket activo.",
            requiere_escalamiento=False,
        )

    if any(marker in evidence_text for marker in historical_markers) or any(
        marker in query for marker in ["oracle", "similar", "antecedente", "pasado"]
    ):
        return BotDecision(
            estado="similar_del_pasado",
            confianza="media",
            resumen="No se identifico una resolucion actual confirmada, pero si antecedentes tecnicos que pueden orientar el analisis.",
            fuentes=evidence,
            siguiente_accion="Compare el contexto actual con el antecedente recuperado antes de asumir que se trata de la misma causa.",
            requiere_escalamiento=True,
        )

    return BotDecision(
        estado="sin_evidencia",
        confianza="baja",
        resumen="Se recupero informacion relacionada, pero no es suficiente para confirmar una resolucion o seguimiento activo con seguridad.",
        fuentes=evidence,
        siguiente_accion="Escale el caso al equipo de desarrollo si el problema persiste o si necesita confirmacion tecnica adicional.",
        requiere_escalamiento=True,
    )


def classify_case(
    user_message: str,
    evidence: list[EvidenceSource],
    client,
    model: str,
) -> BotDecision:
    evidence_lines = []
    for source in evidence:
        evidence_lines.append(
            f"- tipo: {source.tipo}; titulo: {source.titulo}; ubicacion: {source.ubicacion}; fragmento: {source.fragmento}"
        )

    evidence_block = "\n".join(evidence_lines) if evidence_lines else "- sin evidencia recuperada"

    response = client.chat.completions.create(
        model=model,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"Consulta del usuario:\n{user_message}\n\n"
                    f"Evidencia recuperada:\n{evidence_block}\n\n"
                    "Clasifique el caso y resuma el siguiente paso."
                ),
            },
        ],
    )

    content = response.choices[0].message.content or "{}"
    payload = json.loads(content)

    estado = payload.get("estado", "sin_evidencia")
    confianza = payload.get("confianza", "baja")
    if estado == "sin_evidencia":
        confianza = "baja"

    return BotDecision(
        estado=estado,
        confianza=confianza,
        resumen=payload.get("resumen", "No fue posible clasificar el caso con confianza."),
        fuentes=evidence,
        siguiente_accion=payload.get(
            "siguiente_accion",
            "Escale el caso al equipo de desarrollo para revision manual.",
        ),
        requiere_escalamiento=payload.get("requiere_escalamiento", True),
    )
