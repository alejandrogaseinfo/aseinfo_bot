"""Evaluate Libras retrieval and deterministic answer rules against a corpus.

The evaluator does not call the answer-generation model, modify Azure AI
Search or print question text, so it can compare production behavior without
exposing the corpus in logs.
"""

from __future__ import annotations

import argparse
import json
import math
import os
from time import perf_counter
import unicodedata
from pathlib import Path
from typing import Callable

from config import Config, load_project_environment
from classification import classify_case_by_rules, is_underspecified_query
from models import RetrievalTrace
from retrieval import retrieve_evidence


VALID_EXPECTATIONS = {"evidence", "sin_evidencia", "solicita_contexto"}
VALID_CATEGORIES = {
    "procedural",
    "conceptual",
    "diagnostic",
    "out_of_scope",
    "insufficient",
}


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
        category = str(raw_case.get("category") or "uncategorized").strip()
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
        if expected in {"sin_evidencia", "solicita_contexto"} and expected_titles:
            raise ValueError(f"El caso {case_id} no debe declarar títulos esperados.")
        if category != "uncategorized" and category not in VALID_CATEGORIES:
            raise ValueError(f"category no es válido para {case_id}.")
        seen_ids.add(case_id)
        cases.append(
            {
                "id": case_id,
                "message": message,
                "expected": expected,
                "expected_title_contains": expected_titles,
                "split": str(raw_case.get("split") or "regression").strip(),
                "artifact_role": str(raw_case.get("artifact_role") or "").strip(),
                "category": category,
            }
        )
    return cases


def evaluate_cases(cases: list[dict], retriever: Callable[[str], list | RetrievalTrace]) -> dict:
    """Measure evidence presence, expected-document recall, and latency."""
    results: list[dict] = []
    for case in cases:
        started_at = perf_counter()
        retrieval = [] if is_underspecified_query(case["message"]) else retriever(case["message"])
        latency_ms = round((perf_counter() - started_at) * 1000, 2)
        trace = retrieval if isinstance(retrieval, RetrievalTrace) else None
        evidence = trace.sources if trace else retrieval
        decision = classify_case_by_rules(case["message"], evidence)
        titles = list(dict.fromkeys(source.titulo for source in evidence))
        normalized_titles = [_normalized(title) for title in titles]
        expected_titles = [_normalized(title) for title in case["expected_title_contains"]]
        requires_context = bool(trace and trace.requires_version_context)
        answer_state = (
            "solicita_contexto"
            if requires_context
            else decision.estado
        )
        if case["expected"] == "sin_evidencia":
            passed = not evidence
        elif case["expected"] == "solicita_contexto":
            # This is a distinct safe result: Azure found incompatible release
            # documents and the handler must ask for the exact version instead
            # of selecting one by rank. It is not an abstention caused by a
            # missing document.
            passed = requires_context and not evidence
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
                "latency_ms": latency_ms,
                "evidence_count": len(evidence),
                "source_count": len(decision.fuentes),
                "answer_state": answer_state,
                "answer_passed": (
                    decision.estado == "resuelto"
                    if case["expected"] == "evidence"
                    else (
                        answer_state == "solicita_contexto"
                        if case["expected"] == "solicita_contexto"
                        else answer_state == "sin_evidencia"
                    )
                ),
                "retrieved_titles": titles,
                "candidate_count": trace.candidate_count if trace else None,
                "direct_evidence_count": trace.direct_evidence_count if trace else None,
                "requirement_count": trace.requirement_count if trace else None,
                "covered_requirement_count": trace.covered_requirement_count if trace else None,
                "rejected_reasons": trace.rejected_reasons if trace else {},
                "stage_counts": trace.stage_counts if trace else {},
                "split": case.get("split", "regression"),
                "artifact_role": case.get("artifact_role", ""),
                "category": case.get("category", "uncategorized"),
            }
        )

    passed_count = sum(result["passed"] for result in results)
    expected_evidence = [result for result in results if result["expected"] == "evidence"]
    expected_no_evidence = [result for result in results if result["expected"] == "sin_evidencia"]
    expected_context_requests = [
        result for result in results if result["expected"] == "solicita_contexto"
    ]
    traced_results = [result for result in results if result["candidate_count"] is not None]
    traced_evidence = [
        result for result in traced_results if result["expected"] == "evidence"
    ]
    latencies = [result["latency_ms"] for result in results]
    sorted_latencies = sorted(latencies)
    p95_index = max(0, math.ceil(len(sorted_latencies) * 0.95) - 1) if sorted_latencies else 0
    answer_evidence = [result for result in results if result["expected"] == "evidence"]
    answer_abstentions = [result for result in results if result["expected"] == "sin_evidencia"]
    category_summary: dict[str, dict] = {}
    for category in sorted({result["category"] for result in results}):
        category_results = [result for result in results if result["category"] == category]
        category_summary[category] = {
            "case_count": len(category_results),
            "pass_rate": sum(result["passed"] for result in category_results) / len(category_results),
            "answer_pass_rate": sum(result["answer_passed"] for result in category_results) / len(category_results),
            "latency_ms_p95": sorted(result["latency_ms"] for result in category_results)[
                max(0, math.ceil(len(category_results) * 0.95) - 1)
            ],
        }
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
            "correct_context_request_rate": (
                sum(result["passed"] for result in expected_context_requests)
                / len(expected_context_requests)
                if expected_context_requests
                else None
            ),
            "candidate_document_recall": (
                sum(result["passed"] for result in traced_evidence) / len(traced_evidence)
                if traced_evidence
                else None
            ),
            "direct_evidence_rate": (
                sum(result["direct_evidence_count"] > 0 for result in traced_evidence)
                / len(traced_evidence)
                if traced_evidence
                else None
            ),
            "subquestion_coverage_rate": (
                sum(
                    result["covered_requirement_count"] / result["requirement_count"]
                    for result in traced_evidence
                    if result["requirement_count"]
                )
                / sum(1 for result in traced_evidence if result["requirement_count"])
                if any(result["requirement_count"] for result in traced_evidence)
                else None
            ),
            "retrieval_latency_ms_avg": (
                sum(latencies) / len(latencies) if latencies else None
            ),
            "retrieval_latency_ms_p95": (
                sorted_latencies[p95_index] if sorted_latencies else None
            ),
            "retrieval_latency_ms_max": max(latencies) if latencies else None,
            "answer_resolution_rate": (
                sum(result["answer_state"] == "resuelto" for result in answer_evidence)
                / len(answer_evidence)
                if answer_evidence
                else None
            ),
            "answer_correct_abstention_rate": (
                sum(result["answer_state"] == "sin_evidencia" for result in answer_abstentions)
                / len(answer_abstentions)
                if answer_abstentions
                else None
            ),
            "answer_context_request_rate": (
                sum(
                    result["answer_state"] == "solicita_contexto"
                    for result in expected_context_requests
                )
                / len(expected_context_requests)
                if expected_context_requests
                else None
            ),
            "single_source_rate": (
                sum(result["source_count"] == 1 for result in answer_evidence)
                / len(answer_evidence)
                if answer_evidence
                else None
            ),
            "by_category": category_summary,
        },
        "results": results,
    }


def evaluate_strategy_variants(
    cases: list[dict],
    strategies: dict[str, Callable[[str], list | RetrievalTrace]],
) -> dict[str, dict]:
    """Run identical reviewed cases through named retrieval strategies.

    The function is deliberately callback-based: local tests can compare
    deterministic variants without Azure credentials, while a read-only
    evaluation can inject production-compatible retrievers later. It never
    changes the index or calls answer generation.
    """
    if not strategies:
        raise ValueError("Se requiere al menos una estrategia de recuperación.")
    return {
        str(name): evaluate_cases(cases, retriever)
        for name, retriever in strategies.items()
    }


def comparison_summary(reports: dict[str, dict]) -> dict[str, dict]:
    """Extract comparable quality metrics without exposing case contents."""
    return {
        name: {
            key: report.get("summary", {}).get(key)
            for key in (
                "case_count",
                "pass_rate",
                "evidence_recall",
                "correct_abstention_rate",
                "correct_context_request_rate",
                "candidate_document_recall",
                "direct_evidence_rate",
                "retrieval_latency_ms_avg",
                "retrieval_latency_ms_p95",
                "answer_resolution_rate",
                "answer_correct_abstention_rate",
                "answer_context_request_rate",
            )
        }
        for name, report in reports.items()
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
        lambda message: retrieve_evidence(message, config=config, return_trace=True),
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
