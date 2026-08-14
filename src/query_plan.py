"""Deterministic query planning and evidence coverage for Libras.

The planner derives generic linguistic and structural signals.  It never maps a
specific user wording to a specific document; the same plan works for manuals,
procedures and source-code artifacts.
"""

from __future__ import annotations

import hashlib
import re
import unicodedata
from dataclasses import dataclass

from document_index import tokenize


_QUESTION_SPLIT = re.compile(
    r"\s+(?:y|ademas|tambien)\s+(?=(?:que|que\s+debo|como|cual|donde|cuando|hay\s+que)\b)",
    re.IGNORECASE,
)
_EXPLICIT_PRODUCT = re.compile(
    r"\b(?:producto|modulo|sistema|aplicacion)\s+(?:de\s+)?([\w.-]+)", re.IGNORECASE
)
_EXPLICIT_ARTIFACT = re.compile(
    r"\b(?:script|sql|procedimiento|manual|readme|configuracion|reporte|plantilla)\b",
    re.IGNORECASE,
)
_ARTIFACT_ROLE_BY_TERM = {
    "script": "script",
    "sql": "script",
    "procedimiento": "procedimiento",
    "manual": "manual",
    "readme": "configuracion",
    "configuracion": "configuracion",
    "reporte": "reporte",
    "plantilla": "plantilla",
}
_STOP_CONCEPTS = {
    "como", "cual", "cuanto", "donde", "cuando", "dame", "dime", "puedo",
    "puede", "pueden", "podria", "podrian", "debo", "deben", "deberia",
    "informacion", "documentacion", "detalle", "detalles", "tema", "sobre",
    "para", "despues", "antes", "tambien", "ademas", "existe", "hay",
    "que", "se", "pueden", "puede", "ejemplo", "ejemplos", "tipo", "tipos",
    "relacion", "relacionan", "ambos", "confirmar", "confirmacion", "quedo",
    "funcionando", "funciona", "correctamente", "revisar", "revisa", "paga",
    "comunicacion", "comunic", "precaucion", "precauciones", "tomar",
    # Libras is an Evolution-only knowledge base. Mentioning the platform is
    # useful for retrieval, but a page need not repeat that brand to directly
    # support a product-specific operation.
    "evolution",
    # Normalized forms emitted by ``concept_key``/the document tokenizer.
    "relacion", "ambo", "confirm", "quedo", "funcion", "correcta", "revis", "exist",
}
_BACKGROUND_PREFIX = re.compile(r"^(?:despues|luego|tras|al)\b[^,;?]{1,700}[,;]\s*", re.IGNORECASE)
_MODAL_ACTIONS = {"puede", "pueden", "podria", "podrian", "debe", "deben"}
_QUALIFIER_CONCEPTS = {"sensibl", "personal", "confidencial", "oficial", "nuevo", "actual"}
# These words describe a recurring question shape rather than a product or a
# document: operational guidance requested before an installation/update. A
# compact expansion lets lexical search retrieve preparation/checklist pages
# even when the user only says "precauciones".
_PREINSTALLATION_OPERATION_CONCEPTS = {"instal", "actualiz"}
_PREINSTALLATION_CUE_CONCEPTS = {"antes", "precaucion", "previo"}
_PREINSTALLATION_RETRIEVAL_QUERY = (
    "instalacion actualizacion recomendaciones iniciales respaldo preparacion"
)


def concept_key(token: str) -> str:
    """Return a conservative Spanish morphological key for retrieval.

    This intentionally keeps enough of a word to distinguish technical names
    while connecting ordinary forms such as ``ofuscan``/``ofuscación`` and
    ``configurar``/``configuración`` without a document-specific alias list.
    """
    normalized = unicodedata.normalize("NFKD", token or "").lower()
    normalized = "".join(char for char in normalized if not unicodedata.combining(char))
    normalized = re.sub(r"[^a-z0-9]", "", normalized)
    if len(normalized) < 5:
        return normalized
    # Broad functional equivalence, independent from products, documents or
    # customer vocabulary. It bridges a common Spanish paraphrase while the
    # subsequent evidence verifier still requires the remaining target terms.
    if normalized.startswith("gestion") or normalized.startswith("gestionar"):
        return "administr"
    # Spanish verbs ending in ``-ificar`` commonly conjugate as ``-ifique``.
    # Preserve their shared functional stem (modificar/modifique -> modific)
    # without introducing document-specific aliases.
    if normalized.endswith("fique") and len(normalized) > 6:
        return f"{normalized[:-5]}fic"
    # Keep ordinary masculine/feminine variants on the same conservative stem
    # (for example, ``negativa``/``negativo``). This is applied before plural
    # handling so both forms converge without a vocabulary-specific alias.
    if normalized.endswith(("a", "o")) and len(normalized) > 6:
        return normalized[:-1]
    for suffix in ("aciones", "acion", "iciones", "icion", "amientos", "amiento"):
        if normalized.endswith(suffix) and len(normalized) - len(suffix) >= 5:
            return normalized[: -len(suffix)]
    for suffix in ("ando", "iendo", "aran", "eran", "iran", "aron", "eron", "iran"):
        if normalized.endswith(suffix) and len(normalized) - len(suffix) >= 5:
            return normalized[: -len(suffix)]
    for suffix in ("ar", "er", "ir", "an", "en", "as", "es", "os"):
        if normalized.endswith(suffix) and len(normalized) - len(suffix) >= 5:
            return normalized[: -len(suffix)]
    return normalized


def concept_keys(text: str) -> tuple[str, ...]:
    return tuple(dict.fromkeys(key for key in (concept_key(token) for token in tokenize(text)) if key))


def _actions(text: str) -> tuple[str, ...]:
    normalized = " ".join((text or "").lower().split())
    actions: list[str] = []
    for token in tokenize(normalized):
        if token.endswith(("ar", "er", "ir")) and len(token) >= 7:
            actions.append(concept_key(token))
    for verb in re.findall(r"\b(?:como|cómo)\s+se\s+([a-záéíóúñ]+(?:an|en))\b", normalized):
        if verb not in _MODAL_ACTIONS:
            actions.append(concept_key(verb))
    return tuple(
        dict.fromkeys(
            action for action in actions if len(action) >= 4 and action not in _STOP_CONCEPTS
        )
    )


def _content_concepts(text: str) -> tuple[str, ...]:
    return tuple(
        dict.fromkeys(
            key
            for token, key in ((token, concept_key(token)) for token in tokenize(text))
            if token not in _STOP_CONCEPTS and key not in _STOP_CONCEPTS and len(key) >= 3
        )
    )


@dataclass(frozen=True)
class QueryRequirement:
    identifier: str
    text: str
    concepts: tuple[str, ...]
    actions: tuple[str, ...]


@dataclass(frozen=True)
class QueryPlan:
    raw_message: str
    requirements: tuple[QueryRequirement, ...]
    retrieval_queries: tuple[str, ...]
    product: str | None
    version: str | None
    artifact_role: str | None
    query_hash: str

    @property
    def requirement_ids(self) -> tuple[str, ...]:
        return tuple(requirement.identifier for requirement in self.requirements)


def build_query_plan(user_message: str) -> QueryPlan:
    raw_message = " ".join((user_message or "").strip().split())
    # Preserve technical identifiers from a background clause (for example an
    # acronym named before a comma).  The clause itself may be contextual, but
    # its identifier is still a strong retrieval anchor and must not disappear
    # merely because the requested action follows it.
    background_anchors = tuple(dict.fromkeys(
        concept_key(token)
        for token in re.findall(r"\b(?:[A-Z][A-Z0-9_-]{2,}|[A-Za-z][\w.-]*[_.-][\w.-]+)\b", raw_message)
        if concept_key(token)
    ))
    normalized = unicodedata.normalize("NFKD", raw_message).lower()
    normalized = "".join(char for char in normalized if not unicodedata.combining(char))
    # A temporal/background clause narrows the user's situation but is not
    # necessarily a fact the document must restate to answer the question.
    normalized = _BACKGROUND_PREFIX.sub("", normalized)
    clauses = [clause.strip(" .;:¿?") for clause in _QUESTION_SPLIT.split(normalized) if clause.strip(" .;:¿?")]
    if not clauses:
        clauses = [normalized]
    requirements_list: list[QueryRequirement] = []
    requirement_number = 1
    for clause in clauses:
        concepts = _content_concepts(clause)
        qualifiers = tuple(concept for concept in concepts if concept in _QUALIFIER_CONCEPTS)
        primary_concepts = tuple(concept for concept in concepts if concept not in qualifiers) or concepts
        requirements_list.append(
            QueryRequirement(
                identifier=f"r{requirement_number}",
                text=clause,
                concepts=primary_concepts,
                actions=_actions(clause),
            )
        )
        requirement_number += 1
        for qualifier in qualifiers:
            requirements_list.append(
                QueryRequirement(
                    identifier=f"r{requirement_number}",
                    text=f"el calificador '{qualifier}' de la consulta",
                    concepts=(qualifier,),
                    actions=(),
                )
            )
            requirement_number += 1
    if background_anchors and requirements_list:
        first = requirements_list[0]
        merged_concepts = tuple(dict.fromkeys((*first.concepts, *background_anchors)))
        requirements_list[0] = QueryRequirement(
            identifier=first.identifier,
            text=f"{first.text} ({' '.join(background_anchors)})",
            concepts=merged_concepts,
            actions=first.actions,
        )
    requirements = tuple(requirements_list)
    all_concepts = tuple(dict.fromkeys(concept for requirement in requirements for concept in requirement.concepts))
    all_actions = tuple(dict.fromkeys(action for requirement in requirements for action in requirement.actions))
    lexical_query = " ".join((*all_concepts, *all_actions))
    explicit_identifiers = re.findall(r"[A-Za-z][\w.-]*(?:\.[A-Za-z0-9]{2,5})?", raw_message)
    identifier_query = " ".join(
        identifier for identifier in explicit_identifiers if any(marker in identifier for marker in ("_", ".", "-"))
    )
    raw_concepts = set(concept_keys(raw_message))
    preinstallation_query = (
        _PREINSTALLATION_RETRIEVAL_QUERY
        if _PREINSTALLATION_OPERATION_CONCEPTS.issubset(raw_concepts)
        and raw_concepts.intersection(_PREINSTALLATION_CUE_CONCEPTS)
        else ""
    )
    queries = tuple(
        dict.fromkeys(
            query
            for query in (raw_message, lexical_query, identifier_query, preinstallation_query)
            if query
        )
    )
    product_match = _EXPLICIT_PRODUCT.search(normalized)
    artifact_match = _EXPLICIT_ARTIFACT.search(normalized)
    version_match = re.search(r"(?<![\d.])(\d+(?:\.\d+){2,})(?!\d|\.\d)", raw_message)
    return QueryPlan(
        raw_message=raw_message,
        requirements=requirements,
        retrieval_queries=queries,
        product=product_match.group(1) if product_match else None,
        version=version_match.group(1) if version_match else None,
        artifact_role=_ARTIFACT_ROLE_BY_TERM.get(artifact_match.group(0).casefold()) if artifact_match else None,
        query_hash=hashlib.sha256(raw_message.encode("utf-8")).hexdigest()[:16],
    )


def requirement_is_covered(requirement: QueryRequirement, text: str) -> bool:
    """Check direct support in one local evidence window.

    A page may mention an action and a subject in unrelated sections.  Counting
    tokens across the full page would turn that coincidence into a citation, so
    every requirement must fit in one sentence/line or a pair of adjacent
    sentences.  Source-code blocks without sentence punctuation remain a
    single useful window.
    """
    compact = " ".join((text or "").split())
    units = [
        unit.strip()
        for unit in re.split(r"(?<=[.!?;])\s+|\n+", text or "")
        if unit.strip()
    ]
    if not units:
        units = [compact]
    windows = list(units)
    windows.extend(
        f"{left} {right}"
        for left, right in zip(units, units[1:])
        if len(left) + len(right) <= 1_200
    )
    # A source-code artifact often deliberately places its identifier, target
    # table and corrective condition on different lines.  Treating the whole
    # bounded script fragment as one evidence window preserves those anchors
    # without making separate prose sections of a manual appear related.
    if "artefacto de tipo script" in compact.casefold():
        windows.append(compact)
    for window in windows:
        available = set(concept_keys(window))
        concept_matches = set(requirement.concepts).intersection(available)
        # All remaining concepts are intentional anchors after generic and
        # background terms have been removed by the planner.  Requiring each
        # one prevents a generic "modificar parámetros" passage from being
        # cited as evidence about a specific module or process.
        minimum_concepts = len(requirement.concepts)
        if len(concept_matches) < minimum_concepts:
            continue
        if requirement.actions and not set(requirement.actions).intersection(available):
            continue
        return True
    return False


def covered_requirements(plan: QueryPlan, text: str) -> tuple[str, ...]:
    return tuple(
        requirement.identifier
        for requirement in plan.requirements
        if requirement_is_covered(requirement, text)
    )
