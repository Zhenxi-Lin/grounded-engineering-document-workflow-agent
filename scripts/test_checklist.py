from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.llm_client import LLMClient
from app.workflows.checklist import build_checklist_workflow


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run grounded checklist extraction over the local engineering document corpus."
    )
    parser.add_argument(
        "query",
        help="Checklist query to evaluate",
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
        default=6,
        help="Number of retrieved chunks to use for checklist evidence",
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
        help="Disable LLM synthesis and use the rule-based checklist fallback only",
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
        prefixes=("GROUNDED_CHECKLIST_LLM", "GROUNDED_QA_LLM", "OPENAI")
    )
    workflow = build_checklist_workflow(
        index_dir=args.index_dir,
        evidence_top_k=args.evidence_top_k,
        llm_client=llm_client,
        enable_llm_synthesis=not args.disable_llm,
    )
    checklist = workflow.build_checklist(query=args.query)
    print(json.dumps(checklist.to_dict(), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
