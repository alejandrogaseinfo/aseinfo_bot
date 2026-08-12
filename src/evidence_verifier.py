"""Bounded semantic verification of already-retrieved document fragments."""

from __future__ import annotations

import json
import re

from query_plan import QueryPlan


SYSTEM_PROMPT = """
Eres un verificador de evidencia documental. Evalúa únicamente los fragmentos
proporcionados; no uses conocimiento externo ni completes información faltante.
Para cada candidato, marca un requisito solo si su fragmento lo sustenta de
forma directa, incluso cuando use una paráfrasis funcional clara.

Reglas estrictas:
- una portada, índice, tabla de contenido, lista de enlaces o mención aislada
  nunca sustenta un hecho;
- términos repartidos entre temas independientes no son evidencia;
- el título de un artefacto de código puede identificar la operación del
  artefacto, pero no demuestra calificadores no documentados;
- ante duda, no incluyas el requisito.

Devuelve solamente JSON con exactamente este contrato:
{"verdicts":[{"candidate_id":"...","requirements":["r1"],"confidence":0.0}]}.
Usa solo candidate_id y requisitos recibidos. Si no hay evidencia directa,
devuelve {"verdicts":[]}.
""".strip()

_SECRET_PATTERNS = (
    re.compile(r"(?i)\b(password|passwd|secret|api[_ -]?key|token)\s*[:=]\s*[^\s,;]+"),
    re.compile(r"(?i)\b(bearer)\s+[a-z0-9._~+/-]{12,}"),
)
_INJECTION_PATTERN = re.compile(
    r"(?i)(ignore\s+(?:all\s+)?(?:previous|prior|above)\s+instructions?|"
    r"disregard\s+(?:all\s+)?instructions?|reveal\s+(?:the\s+)?(?:system|developer)\s+prompt|"
    r"(?:system|developer)\s+message\s*:)"
)
MIN_CONFIDENCE = 0.80


def _redact(value):
    """Remove credential-shaped values before document text leaves retrieval."""
    if isinstance(value, str):
        for pattern in _SECRET_PATTERNS:
            value = pattern.sub(lambda match: f"{match.group(1) if match.lastindex else 'credencial'}: [REDACTED]", value)
        return value
    if isinstance(value, list):
        return [_redact(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _redact(item) for key, item in value.items()}
    return value


def verify_semantic_evidence(
    plan: QueryPlan,
    candidates: list[dict],
    client,
    model: str,
) -> dict[str, tuple[str, ...]]:
    """Fail closed when a model response is unavailable or malformed."""
    if not candidates or client is None:
        return {}
    # Treat prompt injection in a retrieved fragment as an untrusted-input
    # failure, rather than asking the model to judge it.
    serialized_candidates = _redact(candidates)
    if _INJECTION_PATTERN.search(json.dumps(serialized_candidates, ensure_ascii=False)):
        return {}
    try:
        response = client.chat.completions.create(
            model=model,
            temperature=0,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "requirements": [
                                {"id": requirement.identifier, "text": requirement.text}
                                for requirement in plan.requirements
                            ],
                            "candidates": serialized_candidates,
                        },
                        ensure_ascii=False,
                    ),
                },
            ],
        )
        content = response.choices[0].message.content or "{}"
        payload = json.loads(content)
    except Exception:
        # Network errors, malformed JSON and provider schema changes must not
        # promote an unverified fragment to documentary evidence.
        return {}
    if not isinstance(payload, dict) or set(payload) != {"verdicts"}:
        return {}
    raw_verdicts = payload.get("verdicts")
    if not isinstance(raw_verdicts, list):
        return {}
    allowed_candidates = {str(candidate["candidate_id"]) for candidate in candidates}
    allowed_requirements = set(plan.requirement_ids)
    verdicts: dict[str, tuple[str, ...]] = {}
    for raw_verdict in raw_verdicts:
        if not isinstance(raw_verdict, dict) or set(raw_verdict) != {"candidate_id", "requirements", "confidence"}:
            return {}
        candidate_id = str(raw_verdict.get("candidate_id") or "")
        requirements = raw_verdict.get("requirements")
        confidence = raw_verdict.get("confidence")
        if (candidate_id not in allowed_candidates or not isinstance(requirements, list)
                or isinstance(confidence, bool) or not isinstance(confidence, (int, float))
                or not MIN_CONFIDENCE <= confidence <= 1):
            return {}
        approved = tuple(
            dict.fromkeys(
                str(requirement)
                for requirement in requirements
                if str(requirement) in allowed_requirements
            )
        )
        if len(approved) != len(requirements):
            return {}
        if approved:
            verdicts[candidate_id] = approved
    return verdicts
