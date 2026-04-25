from __future__ import annotations

import argparse
import json
import logging
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.llm_client import LLMClient
from app.workflows.ask import build_grounded_qa_workflow
from app.workflows.checklist import build_checklist_workflow
from app.workflows.compare import build_compare_workflow


LOGGER = logging.getLogger(__name__)
SUPPORTED_WORKFLOWS = {"ask", "compare", "checklist"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run manual workflow evaluation for Ask, Compare, and Checklist flows."
    )
    parser.add_argument(
        "--eval-set",
        type=Path,
        default=PROJECT_ROOT / "data" / "eval" / "manual_eval_set.json",
        help="Path to manual evaluation case JSON",
    )
    parser.add_argument(
        "--index-dir",
        type=Path,
        default=PROJECT_ROOT / "data" / "index",
        help="Directory containing retrieval index assets",
    )
    parser.add_argument(
        "--json-output",
        type=Path,
        default=PROJECT_ROOT / "data" / "eval" / "manual_eval_report.json",
        help="Path to JSON evaluation report",
    )
    parser.add_argument(
        "--markdown-output",
        type=Path,
        default=PROJECT_ROOT / "data" / "eval" / "manual_eval_report.md",
        help="Path to Markdown evaluation report",
    )
    parser.add_argument(
        "--disable-llm",
        action="store_true",
        help="Disable LLM synthesis and use rule-based or extractive paths only",
    )
    parser.add_argument(
        "--qa-top-k",
        type=int,
        default=4,
        help="Evidence top-k for Ask workflow",
    )
    parser.add_argument(
        "--compare-top-k",
        type=int,
        default=8,
        help="Evidence top-k for Compare workflow",
    )
    parser.add_argument(
        "--checklist-top-k",
        type=int,
        default=6,
        help="Evidence top-k for Checklist workflow",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level",
    )
    return parser.parse_args()


def configure_stdout() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")


def load_eval_cases(eval_set_path: Path) -> list[dict[str, Any]]:
    data = json.loads(eval_set_path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("manual_eval_set.json must contain a JSON array")

    normalized_cases: list[dict[str, Any]] = []
    for index, item in enumerate(data, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"Eval case #{index} must be a JSON object")
        workflow = str(item.get("workflow", "")).strip().lower()
        query = str(item.get("query", "")).strip()
        if workflow not in SUPPORTED_WORKFLOWS:
            raise ValueError(f"Unsupported workflow in eval case #{index}: {workflow}")
        if not query:
            raise ValueError(f"Eval case #{index} is missing a non-empty query")
        normalized_cases.append(
            {
                "case_id": str(item.get("case_id", f"case_{index:02d}")).strip(),
                "workflow": workflow,
                "category": str(item.get("category", "")).strip(),
                "query": query,
                "expected_status": str(item.get("expected_status", "")).strip(),
                "expected_focus": str(item.get("expected_focus", "")).strip(),
                "review_notes": str(item.get("review_notes", "")).strip(),
            }
        )
    return normalized_cases


def build_workflows(
    *,
    index_dir: Path,
    disable_llm: bool,
    qa_top_k: int,
    compare_top_k: int,
    checklist_top_k: int,
) -> dict[str, Any]:
    ask_llm = None if disable_llm else LLMClient.from_env(prefixes=("GROUNDED_QA_LLM", "OPENAI"))
    compare_llm = None if disable_llm else LLMClient.from_env(
        prefixes=("GROUNDED_COMPARE_LLM", "GROUNDED_QA_LLM", "OPENAI")
    )
    checklist_llm = None if disable_llm else LLMClient.from_env(
        prefixes=("GROUNDED_CHECKLIST_LLM", "GROUNDED_QA_LLM", "OPENAI")
    )

    return {
        "ask": build_grounded_qa_workflow(
            index_dir=index_dir,
            evidence_top_k=qa_top_k,
            llm_client=ask_llm,
            enable_llm_synthesis=not disable_llm,
        ),
        "compare": build_compare_workflow(
            index_dir=index_dir,
            evidence_top_k=compare_top_k,
            llm_client=compare_llm,
            enable_llm_synthesis=not disable_llm,
        ),
        "checklist": build_checklist_workflow(
            index_dir=index_dir,
            evidence_top_k=checklist_top_k,
            llm_client=checklist_llm,
            enable_llm_synthesis=not disable_llm,
        ),
    }


def run_eval_cases(
    *,
    cases: list[dict[str, Any]],
    workflows: dict[str, Any],
    llm_enabled: bool,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    for case_index, case in enumerate(cases, start=1):
        LOGGER.info(
            "[%s/%s] Running %s case %s",
            case_index,
            len(cases),
            case["workflow"],
            case["case_id"],
        )
        result_payload = run_single_case(case=case, workflows=workflows)
        citations = result_payload.get("citations", [])
        rows.append(
            {
                **case,
                "llm_enabled": llm_enabled,
                "result": result_payload,
                "actual_status": str(result_payload.get("status", "")).strip(),
                "citation_count": len(citations),
                "manual_label": "",
                "manual_comment": "",
            }
        )

    return rows


def run_single_case(*, case: dict[str, Any], workflows: dict[str, Any]) -> dict[str, Any]:
    workflow_name = case["workflow"]
    query = case["query"]

    if workflow_name == "ask":
        return workflows["ask"].answer(query).to_dict()
    if workflow_name == "compare":
        return workflows["compare"].compare(query).to_dict()
    if workflow_name == "checklist":
        return workflows["checklist"].build_checklist(query=query).to_dict()
    raise ValueError(f"Unsupported workflow: {workflow_name}")


def build_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    workflow_counter = Counter(row["workflow"] for row in rows)
    status_counter = Counter(row["actual_status"] for row in rows)
    workflow_status_counter = Counter((row["workflow"], row["actual_status"]) for row in rows)

    return {
        "case_count": len(rows),
        "workflow_breakdown": dict(sorted(workflow_counter.items())),
        "status_breakdown": dict(sorted(status_counter.items())),
        "workflow_status_breakdown": {
            f"{workflow}:{status}": count
            for (workflow, status), count in sorted(workflow_status_counter.items())
        },
    }


def build_report_payload(
    *,
    rows: list[dict[str, Any]],
    llm_enabled: bool,
    eval_set_path: Path,
    index_dir: Path,
) -> dict[str, Any]:
    return {
        "run_metadata": {
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "llm_enabled": llm_enabled,
            "eval_set_path": str(eval_set_path),
            "index_dir": str(index_dir),
        },
        "summary": build_summary(rows),
        "cases": rows,
    }


def write_json_output(report: dict[str, Any], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    LOGGER.info("Wrote JSON manual eval report to %s", output_path)


def write_markdown_output(report: dict[str, Any], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    summary = report["summary"]
    metadata = report["run_metadata"]
    rows = report["cases"]

    lines: list[str] = [
        "# Manual Workflow Evaluation Report",
        "",
        f"- Generated at: {metadata['generated_at']}",
        f"- LLM enabled: {metadata['llm_enabled']}",
        f"- Case count: {summary['case_count']}",
        f"- Workflow breakdown: {format_counter_dict(summary['workflow_breakdown'])}",
        f"- Status breakdown: {format_counter_dict(summary['status_breakdown'])}",
        "",
    ]

    for row in rows:
        result = row["result"]
        lines.append(f"## {row['case_id']} - {row['workflow']}")
        lines.append("")
        lines.append(f"- Query: {row['query']}")
        lines.append(f"- Category: {row['category'] or 'n/a'}")
        lines.append(f"- Expected status: {row['expected_status'] or 'n/a'}")
        lines.append(f"- Actual status: {row['actual_status'] or 'n/a'}")
        lines.append(f"- Confidence: {result.get('confidence', 0.0):.3f}")
        lines.append(f"- Citation count: {row['citation_count']}")
        lines.append(f"- Expected focus: {row['expected_focus'] or 'n/a'}")
        lines.append("- Manual label: ")
        lines.append("- Manual comment: ")
        lines.append("")

        append_result_body(lines, row["workflow"], result)
        append_citations(lines, result.get("citations", []))
        lines.append("")

    output_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    LOGGER.info("Wrote Markdown manual eval report to %s", output_path)


def append_result_body(lines: list[str], workflow: str, result: dict[str, Any]) -> None:
    if workflow == "ask":
        lines.append("### Answer")
        lines.append("")
        lines.append(result.get("answer", ""))
        lines.append("")
        return

    if workflow == "compare":
        lines.append("### Summary")
        lines.append("")
        lines.append(result.get("summary", ""))
        lines.append("")
        append_markdown_list(lines, "Common points", result.get("common_points", []))
        append_markdown_list(lines, "Differences", result.get("differences", []))
        append_markdown_list(lines, "Risks or implications", result.get("risks_or_implications", []))
        return

    if workflow == "checklist":
        lines.append("### Checklist Title")
        lines.append("")
        lines.append(result.get("checklist_title", ""))
        lines.append("")
        append_markdown_list(lines, "Prerequisites", result.get("prerequisites", []))
        append_markdown_list(lines, "Ordered steps", result.get("ordered_steps", []), ordered=True)
        append_markdown_list(lines, "Warnings", result.get("warnings", []))
        append_markdown_list(lines, "Validation checks", result.get("validation_checks", []))


def append_markdown_list(
    lines: list[str],
    title: str,
    items: list[Any],
    *,
    ordered: bool = False,
) -> None:
    lines.append(f"### {title}")
    lines.append("")
    if not items:
        lines.append("_None_")
        lines.append("")
        return

    for index, item in enumerate(items, start=1):
        prefix = f"{index}. " if ordered else "- "
        lines.append(f"{prefix}{item}")
    lines.append("")


def append_citations(lines: list[str], citations: list[dict[str, Any]]) -> None:
    lines.append("### Citations")
    lines.append("")
    if not citations:
        lines.append("_No citations_")
        lines.append("")
        return

    for citation in citations:
        section_path = " > ".join(citation.get("section_path", []))
        lines.append(
            f"- `{citation.get('chunk_id', '')}` | {citation.get('source', '')} | "
            f"{citation.get('title', '')} | score={citation.get('score', 0.0)}"
        )
        lines.append(f"  URL: {citation.get('url', '')}")
        lines.append(f"  Section: {section_path or 'n/a'}")
        lines.append(f"  Snippet: {citation.get('snippet', '')}")
    lines.append("")


def format_counter_dict(values: dict[str, Any]) -> str:
    if not values:
        return "n/a"
    return ", ".join(f"{key}={value}" for key, value in values.items())


def main() -> None:
    args = parse_args()
    configure_stdout()
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    cases = load_eval_cases(args.eval_set)
    workflows = build_workflows(
        index_dir=args.index_dir,
        disable_llm=args.disable_llm,
        qa_top_k=args.qa_top_k,
        compare_top_k=args.compare_top_k,
        checklist_top_k=args.checklist_top_k,
    )
    rows = run_eval_cases(
        cases=cases,
        workflows=workflows,
        llm_enabled=not args.disable_llm,
    )
    report = build_report_payload(
        rows=rows,
        llm_enabled=not args.disable_llm,
        eval_set_path=args.eval_set,
        index_dir=args.index_dir,
    )
    write_json_output(report, args.json_output)
    write_markdown_output(report, args.markdown_output)


if __name__ == "__main__":
    main()
