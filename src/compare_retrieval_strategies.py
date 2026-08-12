"""Compara variantes acotadas de recuperación sin modificar Azure AI Search.

El comando reutiliza el mismo corpus y la misma ruta de respuesta de Libras.
Solo cambia límites locales del pool; no activa Azure Semantic Search, no
reindexa y no llama al modelo evaluador LLM.
"""

from __future__ import annotations

import argparse
import copy
import json
import os
from pathlib import Path

from config import Config, load_project_environment
from evaluate_retrieval_quality import (
    comparison_summary,
    evaluate_strategy_variants,
    load_cases,
)
from retrieval import retrieve_evidence


def build_strategy_configs(config: Config) -> dict[str, Config]:
    """Return read-only configuration copies for the three A/B/C variants."""
    variants = {
        "actual_legacy": (60, 20),
        "candidatos_ampliados": (100, 40),
        "ampliados_reranking_determinista": (100, 20),
    }
    result: dict[str, Config] = {}
    for name, (merged_limit, rerank_limit) in variants.items():
        variant = copy.copy(config)
        variant.retrieval_strategy = "legacy"
        variant.azure_search_use_semantic = False
        variant.retrieval_merged_pool_limit = merged_limit
        variant.retrieval_rerank_pool_limit = rerank_limit
        result[name] = variant
    return result


def compare_cases(cases: list[dict], config: Config) -> dict:
    configs = build_strategy_configs(config)
    reports = evaluate_strategy_variants(
        cases,
        {
            name: (lambda message, variant=variant: retrieve_evidence(
                message, config=variant, return_trace=True
            ))
            for name, variant in configs.items()
        },
    )
    return {
        "summary": comparison_summary(reports),
        "reports": reports,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Compara variantes legacy de recuperación en modo solo lectura."
    )
    parser.add_argument("--cases", required=True, help="Corpus JSON revisado.")
    parser.add_argument(
        "--output",
        default="output/comparacion-recuperacion-estrategias.json",
        help="Archivo JSON de resultados.",
    )
    parser.add_argument(
        "--use-current-environment",
        action="store_true",
        help="No carga archivos .env; usa solo variables ya definidas.",
    )
    args = parser.parse_args()
    if not args.use_current_environment:
        load_project_environment()
    config = Config(os.environ)
    if not config.azure_search_enabled:
        raise RuntimeError(
            "La comparación requiere Azure AI Search habilitado en esta configuración."
        )

    result = compare_cases(load_cases(Path(args.cases).resolve()), config)
    output_path = Path(args.output).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result["summary"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
