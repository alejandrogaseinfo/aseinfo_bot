"""Evaluate Libras's real LLM intent router against a controlled corpus.

This command calls only the configured intent model. It does not invoke
SharePoint, Azure AI Search, retrieval, or answer generation.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Callable

from openai import OpenAI

from config import Config, load_project_environment
from intent import IntentResult, classify_intent


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CASES_PATH = PROJECT_ROOT / "tests" / "fixtures" / "intent_routing_cases.json"
EXPECTED_FIELDS = {"id", "message", "intent", "conversation_purpose", "requires_context"}


def load_cases(path: Path) -> list[dict]:
    """Load and validate the versioned, non-sensitive evaluation corpus."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list) or not payload:
        raise ValueError("El corpus de intención debe ser una lista no vacía.")
    seen_ids: set[str] = set()
    for case in payload:
        if not isinstance(case, dict) or not EXPECTED_FIELDS.issubset(case):
            raise ValueError("Cada caso debe incluir id, message, intent, conversation_purpose y requires_context.")
        if not all(isinstance(case[field], str) and case[field].strip() for field in EXPECTED_FIELDS - {"requires_context"}):
            raise ValueError(f"El caso {case.get('id', '<sin id>')} contiene texto inválido.")
        if not isinstance(case["requires_context"], bool):
            raise ValueError(f"El caso {case['id']} requiere requires_context booleano.")
        if case["id"] in seen_ids:
            raise ValueError(f"El ID de caso está repetido: {case['id']}.")
        seen_ids.add(case["id"])
    return payload


def resolve_action(intent: str | None, purpose: str | None, requires_context: bool | None) -> str:
    """Map router fields to the user-visible action chosen by the application."""
    if purpose == "capacidad":
        return "capability"
    if purpose == "alcance":
        return "scope"
    if intent == "saludo":
        return "greeting"
    if intent == "ayuda":
        return "help"
    if intent in {"reporte_error", "consulta_ambigua"} and requires_context:
        return "clarify"
    return "retrieve"


def evaluate_cases(
    cases: list[dict], classifier: Callable[[str], IntentResult | None]
) -> list[dict]:
    """Return a result per case, keeping comparison logic testable and deterministic."""
    results: list[dict] = []
    for case in cases:
        error = None
        try:
            actual = classifier(case["message"])
        except Exception as exc:  # Evaluation must report a failed case, not abort the run.
            actual = None
            error = f"{type(exc).__name__}: {exc}"
        actual_payload = {
            "intent": actual.name if actual else None,
            "conversation_purpose": actual.conversation_purpose if actual else None,
            "requires_context": actual.requires_context if actual else None,
        }
        expected_payload = {
            field: case[field]
            for field in ("intent", "conversation_purpose", "requires_context")
        }
        expected_action = resolve_action(
            expected_payload["intent"],
            expected_payload["conversation_purpose"],
            expected_payload["requires_context"],
        )
        actual_action = resolve_action(
            actual_payload["intent"],
            actual_payload["conversation_purpose"],
            actual_payload["requires_context"],
        )
        results.append(
            {
                "id": case["id"],
                "passed": actual_action == expected_action,
                "exact_match": actual_payload == expected_payload,
                "expected": expected_payload,
                "actual": actual_payload,
                "expected_action": expected_action,
                "actual_action": actual_action,
                "error": error,
            }
        )
    return results


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Evalúa el clasificador LLM de intención sin consultar la base documental."
    )
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES_PATH)
    parser.add_argument(
        "--max-failures",
        type=int,
        default=10,
        help="Máximo de discrepancias a mostrar; el total siempre se informa.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=None,
        help="Timeout por llamada al modelo; por defecto usa INTENT_TIMEOUT_SECONDS.",
    )
    args = parser.parse_args()

    load_project_environment()
    config = Config(os.environ)
    if not config.model_endpoint_configured:
        raise SystemExit("Falta configurar un proveedor de modelo válido para ejecutar la evaluación.")
    cases = load_cases(args.cases)
    client = OpenAI(
        api_key=config.openai_api_key,
        base_url=config.resolved_openai_base_url,
        timeout=args.timeout or config.intent_timeout_seconds,
        max_retries=0,
    )
    results = evaluate_cases(
        cases,
        lambda message: classify_intent(message, client, config.openai_intent_model_name),
    )
    failures = [result for result in results if not result["passed"]]
    exact_failures = [result for result in results if not result["exact_match"]]
    passed = len(results) - len(failures)
    exact_matches = sum(result["exact_match"] for result in results)
    print(
        f"Router de intención: acción correcta en {passed}/{len(results)} casos; "
        f"coincidencia exacta en {exact_matches}/{len(results)}."
    )
    for result in failures[: max(args.max_failures, 0)]:
        print(
            f"[ACCION INCORRECTA {result['id']}] esperado={result['expected']} actual={result['actual']}"
            f" action={result['expected_action']}->{result['actual_action']}"
            + (f" error={result['error']}" if result["error"] else "")
        )
    equivalent_limit = max(args.max_failures, 0)
    equivalent_results = [result for result in exact_failures if result["passed"]]
    for result in equivalent_results[:equivalent_limit]:
        print(
            f"[DIFERENCIA EQUIVALENTE {result['id']}] esperado={result['expected']} "
            f"actual={result['actual']} action={result['actual_action']}"
        )
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
