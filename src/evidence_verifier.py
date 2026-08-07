"""Bounded semantic verification of already-retrieved document fragments."""

from __future__ import annotations

import json

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

Devuelve solamente JSON con: {"verdicts":[{"candidate_id":"...",
"requirements":["r1"]}]}. Usa solo candidate_id y requisitos recibidos.
""".strip()


def verify_semantic_evidence(
    plan: QueryPlan,
    candidates: list[dict],
    client,
    model: str,
) -> dict[str, tuple[str, ...]]:
    """Fail closed when a model response is unavailable or malformed."""
    if not candidates or client is None:
        return {}
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
                        "candidates": candidates,
                    },
                    ensure_ascii=False,
                ),
            },
        ],
    )
    content = response.choices[0].message.content or "{}"
    payload = json.loads(content)
    raw_verdicts = payload.get("verdicts")
    if not isinstance(raw_verdicts, list):
        return {}
    allowed_candidates = {str(candidate["candidate_id"]) for candidate in candidates}
    allowed_requirements = set(plan.requirement_ids)
    verdicts: dict[str, tuple[str, ...]] = {}
    for raw_verdict in raw_verdicts:
        if not isinstance(raw_verdict, dict):
            continue
        candidate_id = str(raw_verdict.get("candidate_id") or "")
        requirements = raw_verdict.get("requirements")
        if candidate_id not in allowed_candidates or not isinstance(requirements, list):
            continue
        approved = tuple(
            dict.fromkeys(
                str(requirement)
                for requirement in requirements
                if str(requirement) in allowed_requirements
            )
        )
        if approved:
            verdicts[candidate_id] = approved
    return verdicts
