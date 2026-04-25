from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.core.compare_parser import parse_comparison_query
from app.llm_client import LLMClient
from app.workflows.compare import build_compare_workflow


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run grounded comparison over the local engineering document corpus."
    )
    parser.add_argument(
        "query",
        help="Comparison query to evaluate",
    )
    parser.add_argument(
        "--index-dir",
        type=Path,
        default=PROJECT_ROOT / "data" / "index",
        help="Directory containing retrieval index assets",
    )
    parser.add_argument(
        "--evidence-top-k",
        type=int,
        default=8,
        help="Number of retrieved chunks to use for comparison evidence",
    )
    parser.add_argument(
        "--log-level",
        default="WARNING",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level",
    )
    parser.add_argument(
        "--disable-llm",
        action="store_true",
        help="Disable LLM synthesis and use the rule-based comparison fallback only",
    )
    parser.add_argument(
        "--show-parse",
        action="store_true",
        help="Print parser output before running the comparison workflow",
    )
    return parser.parse_args()


def configure_stdout() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")


def main() -> None:
    args = parse_args()
    configure_stdout()
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    llm_client = None if args.disable_llm else LLMClient.from_env(
        prefixes=("GROUNDED_COMPARE_LLM", "GROUNDED_QA_LLM", "OPENAI")
    )
    if args.show_parse:
        parse_result = parse_comparison_query(args.query)
        print(json.dumps(
            {
                "raw_query": parse_result.raw_query,
                "side_a": parse_result.side_a,
                "side_b": parse_result.side_b,
                "pattern_name": parse_result.pattern_name,
                "failure_reason": parse_result.failure_reason,
                "success": parse_result.success,
            },
            indent=2,
            ensure_ascii=False,
        ))
        print()

    workflow = build_compare_workflow(
        index_dir=args.index_dir,
        evidence_top_k=args.evidence_top_k,
        llm_client=llm_client,
        enable_llm_synthesis=not args.disable_llm,
    )
    comparison = workflow.compare(args.query)
    print(json.dumps(comparison.to_dict(), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
