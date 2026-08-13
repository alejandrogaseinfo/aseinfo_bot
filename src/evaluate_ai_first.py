"""A/B evaluation for the experimental AI-first pipeline."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

from openai import OpenAI

from ai_first import judge_ai_first_candidates, mark_confirmed_versions, retrieve_ai_first_candidates
from azure_search import retrieve_azure_search_evidence
from classification import classify_case_by_rules, has_explicit_version_request
from config import Config, load_project_environment
from formatting import format_user_response
from grounded_response import generate_grounded_response
from handler import _ambiguous_release_version_response
from intent import classify_intent


DEFAULT_CASES = Path(__file__).resolve().parents[1] / "output" / "revision-humana-redactor-20260812-postfix6.json"
DEFAULT_OUTPUT = Path(__file__).resolve().parents[1] / "output" / "revision-humana-ai-first-20260812.json"


def _client(config: Config) -> OpenAI:
    return OpenAI(
        api_key=config.openai_api_key or "ollama",
        base_url=config.resolved_openai_base_url,
    )


def _load_cases(path: Path) -> list[dict]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, dict) and isinstance(payload.get("results"), list):
        return [
            {"case_id": item["case_id"], "question": item["question"]}
            for item in payload["results"]
        ]
    if isinstance(payload, list):
        return payload
    raise ValueError("El corpus no contiene una lista de casos OPS.")


def _result_base(case: dict, started: float) -> dict:
    return {
        "case_id": case["case_id"],
        "question": case["question"],
        "latency_ms": round((time.perf_counter() - started) * 1000, 2),
        "response": "",
        "sources": [],
        "judge_selected_sources": [],
        "evidence_count": 0,
        "fallback": False,
        "grounded_used": False,
        "judge_abstained": False,
        "validator_rejections": {},
    }


def _source_titles(sources) -> list[str]:
    return [str(source.titulo) for source in sources]


def _run_legacy(question: str, config: Config, client: OpenAI, grounded: bool, case: dict) -> dict:
    started = time.perf_counter()
    result = _result_base(case, started)
    trace = retrieve_azure_search_evidence(question, config, return_trace=True)
    sources = list(trace.sources)
    if trace.requires_version_context:
        response = _ambiguous_release_version_response()
        result["fallback"] = False
    else:
        decision = classify_case_by_rules(question, sources)
        if grounded and sources and decision.estado == "resuelto" and not has_explicit_version_request(question):
            draft = generate_grounded_response(
                question,
                decision.fuentes,
                client=client,
                model=config.grounded_response_model_name,
            )
            if draft and draft.response:
                decision.resumen = draft.response
                decision.fuentes = draft.sources
                result["grounded_used"] = True
            else:
                result["fallback"] = True
        response = format_user_response(decision, config=config)
        sources = decision.fuentes
    result.update(
        {
            "response": response,
            "sources": _source_titles(sources),
            "evidence_count": len(sources),
            "candidate_count": trace.candidate_count,
            "retrieval_rejected": trace.rejected_reasons,
            "requires_version_context": trace.requires_version_context,
        }
    )
    result["latency_ms"] = round((time.perf_counter() - started) * 1000, 2)
    return result


def _run_ai_first(question: str, config: Config, client: OpenAI, grounded: bool, case: dict) -> dict:
    started = time.perf_counter()
    result = _result_base(case, started)
    try:
        intent = classify_intent(
            question,
            client=client,
            model=config.openai_intent_model_name,
        )
        result["intent"] = intent.name if intent else "unavailable"
    except Exception:
        result["intent"] = "unavailable"
    retrieval = retrieve_ai_first_candidates(
        question,
        config,
        client=client,
        limit=config.ai_first_candidate_limit,
    )
    judge = judge_ai_first_candidates(
        question,
        retrieval,
        client=client,
        model=config.ai_first_judge_model_name,
    )
    sources = mark_confirmed_versions(judge)
    result["judge_selected_sources"] = _source_titles(sources)
    result["selected_evidence_count"] = len(sources)
    result.update(
        {
            "candidate_count": retrieval.raw_candidate_count,
            "sanitized_candidate_count": len(retrieval.candidates),
            "retrieval_rejected": retrieval.rejected_reasons,
            "judge_abstained": judge.abstained,
            "validator_rejections": judge.validator_rejections,
        }
    )
    decision = classify_case_by_rules(question, sources)
    if grounded and sources:
        draft = generate_grounded_response(
            question,
            sources,
            client=client,
            model=config.grounded_response_model_name,
        )
        if draft and draft.response:
            decision.resumen = draft.response
            decision.fuentes = draft.sources
            decision.estado = "resuelto"
            result["grounded_used"] = True
            sources = draft.sources
        elif draft and not draft.sources:
            decision.fuentes = []
            decision.estado = "sin_evidencia"
            result["fallback"] = True
        else:
            result["fallback"] = True
    response = format_user_response(decision, config=config)
    result.update(
        {
            "response": response,
            "sources": _source_titles(decision.fuentes),
            "evidence_count": len(decision.fuentes),
        }
    )
    result["latency_ms"] = round((time.perf_counter() - started) * 1000, 2)
    return result


def _config_for_variant(grounded: bool, ai_first: bool) -> Config:
    os.environ["LIBRAS_ENV"] = "local"
    os.environ["USE_AZURE_SEARCH_IN_LOCAL"] = "true"
    os.environ["ALLOW_LOCAL_DOCUMENT_FALLBACK"] = "false"
    os.environ["REQUIRE_AZURE_SEARCH"] = "true"
    os.environ["RETRIEVAL_STRATEGY"] = "legacy"
    os.environ["USE_LLM_EVIDENCE_VERIFIER"] = "false"
    os.environ["USE_LLM_GROUNDED_RESPONSE"] = "true" if grounded else "false"
    os.environ["USE_AI_FIRST_EXPERIMENTAL"] = "true" if ai_first else "false"
    config = Config(os.environ)
    config.use_ai_first_experimental = ai_first
    config.use_llm_grounded_response = grounded
    config.allow_local_document_fallback = False
    config.retrieval_strategy = "legacy"
    config.use_llm_evidence_verifier = False
    return config


def evaluate(cases: list[dict], config: Config, client: OpenAI) -> dict:
    variants = {
        "legacy_redactor_off": (False, False),
        "legacy_redactor_on": (True, False),
        "ai_first_redactor_off": (False, True),
        "ai_first_redactor_on": (True, True),
    }
    reports: dict[str, list[dict]] = {}
    for name, (grounded, ai_first) in variants.items():
        variant_config = _config_for_variant(grounded, ai_first)
        reports[name] = []
        for case in cases:
            if ai_first:
                reports[name].append(_run_ai_first(case["question"], variant_config, client, grounded, case))
            else:
                reports[name].append(_run_legacy(case["question"], variant_config, client, grounded, case))

    def summary(items: list[dict]) -> dict:
        latencies = sorted(float(item["latency_ms"]) for item in items)
        p95_index = max(0, min(len(latencies) - 1, int(round(len(latencies) * 0.95)) - 1))
        return {
            "case_count": len(items),
            "latency_ms_avg": round(sum(latencies) / len(latencies), 2) if latencies else 0,
            "latency_ms_p95": round(latencies[p95_index], 2) if latencies else 0,
            "latency_ms_max": round(max(latencies), 2) if latencies else 0,
            "judge_abstained_count": sum(bool(item.get("judge_abstained")) for item in items),
            "grounded_used_count": sum(bool(item.get("grounded_used")) for item in items),
            "fallback_count": sum(bool(item.get("fallback")) for item in items),
            "zero_evidence_count": sum(int(item.get("evidence_count", 0)) == 0 for item in items),
        }

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "case_count": len(cases),
        "configuration": {
            "retrieval_strategy": "legacy",
            "index": config.azure_search_index_name,
            "host": config.azure_search_endpoint.replace("https://", "").replace("http://", ""),
            "fallback": False,
            "evidence_verifier_production": False,
            "grounded_production": False,
            "experimental_flag": "USE_AI_FIRST_EXPERIMENTAL",
            "azure_search_use_entra_id": config.azure_search_use_entra_id,
        },
        "summary": {name: summary(items) for name, items in reports.items()},
        "comparison": {
            "legacy_vs_ai_first_off_avg_delta_ms": round(
                summary(reports["ai_first_redactor_off"])["latency_ms_avg"]
                - summary(reports["legacy_redactor_off"])["latency_ms_avg"],
                2,
            ),
            "legacy_vs_ai_first_on_avg_delta_ms": round(
                summary(reports["ai_first_redactor_on"])["latency_ms_avg"]
                - summary(reports["legacy_redactor_on"])["latency_ms_avg"],
                2,
            ),
        },
        "notes": [
            "AI-first usa candidatos sanitizados recuperados exclusivamente de Azure AI Search; no usa fallback local.",
            "El juez y el redactor se ejecutaron localmente contra el índice productivo en modo de solo lectura.",
            "La bandera experimental no se activó en producción ni se desplegó este cambio.",
        ],
        "results": {
            name: items for name, items in reports.items()
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    load_project_environment()
    config = _config_for_variant(False, False)
    client = _client(config)
    report = evaluate(_load_cases(args.cases), config, client)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
