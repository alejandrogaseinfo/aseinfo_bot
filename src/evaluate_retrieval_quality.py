"""Evaluate Libras retrieval against a reviewed, versioned quality corpus.

The evaluator calls retrieval only. It does not call the answer-generation
model, modify Azure AI Search or print question text, so it can be used to
compare an index candidate with production without exposing the corpus in logs.
"""

from __future__ import annotations

import argparse
import json
import os
import unicodedata
from pathlib import Path
from typing import Callable

from config import Config, load_project_environment
from retrieval import retrieve_evidence


VALID_EXPECTATIONS = {"evidence", "sin_evidencia"}


def _normalized(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value or "")
    return "".join(character for character in decomposed if not unicodedata.combining(character)).casefold()


def load_cases(path: Path) -> list[dict]:
    """Load reviewed cases without accepting ambiguous expected outcomes."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("El corpus debe ser una lista JSON de casos.")

    seen_ids: set[str] = set()
    cases: list[dict] = []
    for raw_case in payload:
        if not isinstance(raw_case, dict):
            raise ValueError("Cada caso del corpus debe ser un objeto JSON.")
        case_id = str(raw_case.get("id") or "").strip()
        message = str(raw_case.get("message") or "").strip()
        expected = str(raw_case.get("expected") or "").strip()
        expected_titles = raw_case.get("expected_title_contains", [])
        if not case_id or not message or expected not in VALID_EXPECTATIONS:
            raise ValueError("Cada caso requiere id, message y expected válido.")
        if case_id in seen_ids:
            raise ValueError(f"El id de caso está repetido: {case_id}")
        if not isinstance(expected_titles, list) or not all(
            isinstance(title, str) and title.strip() for title in expected_titles
        ):
            raise ValueError(f"expected_title_contains no es válido para {case_id}.")
        if expected == "evidence" and not expected_titles:
            raise ValueError(
                f"El caso {case_id} requiere expected_title_contains para evitar una aprobación ambigua."
            )
        if expected == "sin_evidencia" and expected_titles:
            raise ValueError(f"El caso {case_id} no debe declarar títulos esperados.")
        seen_ids.add(case_id)
        cases.append(
            {
                "id": case_id,
                "message": message,
                "expected": expected,
                "expected_title_contains": expected_titles,
            }
        )
    return cases


def evaluate_cases(
    cases: list[dict], retriever: Callable[[str], list]
) -> dict:
    """Measure evidence presence and expected-document recall for each case."""
    results: list[dict] = []
    for case in cases:
        evidence = retriever(case["message"])
        titles = list(dict.fromkeys(source.titulo for source in evidence))
        normalized_titles = [_normalized(title) for title in titles]
        expected_titles = [_normalized(title) for title in case["expected_title_contains"]]
        if case["expected"] == "sin_evidencia":
            passed = not evidence
        else:
            passed = bool(evidence) and all(
                any(expected_title in title for title in normalized_titles)
                for expected_title in expected_titles
            )
        results.append(
            {
                "id": case["id"],
                "expected": case["expected"],
                "passed": passed,
                "evidence_count": len(evidence),
                "retrieved_titles": titles,
            }
        )

    passed_count = sum(result["passed"] for result in results)
    expected_evidence = [result for result in results if result["expected"] == "evidence"]
    expected_no_evidence = [result for result in results if result["expected"] == "sin_evidencia"]
    return {
        "summary": {
            "case_count": len(results),
            "passed_count": passed_count,
            "pass_rate": passed_count / len(results) if results else 0.0,
            "evidence_recall": (
                sum(result["passed"] for result in expected_evidence) / len(expected_evidence)
                if expected_evidence
                else None
            ),
            "correct_abstention_rate": (
                sum(result["passed"] for result in expected_no_evidence) / len(expected_no_evidence)
                if expected_no_evidence
                else None
            ),
        },
        "results": results,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Evalúa recuperación documental de Libras.")
    parser.add_argument("--cases", required=True, help="Corpus JSON revisado.")
    parser.add_argument(
        "--output",
        default="output/evaluacion-recuperacion-libras.json",
        help="Archivo JSON con el resultado de la evaluación.",
    )
    parser.add_argument(
        "--use-current-environment",
        action="store_true",
        help=(
            "Usa únicamente las variables ya definidas en esta terminal; evita "
            "cargar archivos .env locales de desarrollo."
        ),
    )
    args = parser.parse_args()
    cases = load_cases(Path(args.cases).resolve())
    if not args.use_current_environment:
        load_project_environment()
    config = Config(os.environ)
    if not config.azure_search_enabled:
        raise RuntimeError("La evaluación requiere Azure AI Search habilitado en esta configuración.")

    report = evaluate_cases(
        cases,
        lambda message: retrieve_evidence(message, config=config),
    )
    output_path = Path(args.output).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    summary = report["summary"]
    print(
        "Evaluación completada: "
        f"{summary['passed_count']}/{summary['case_count']} casos aprobados; "
        f"recall={summary['evidence_recall']}; abstención={summary['correct_abstention_rate']}."
    )


if __name__ == "__main__":
    main()
