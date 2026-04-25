from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.retrieval.retrieval_service import (
    RetrievalService,
    SUPPORTED_MODES,
    build_eval_record,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run manual retrieval evaluation over seed queries and save JSON/Markdown outputs."
    )
    parser.add_argument(
        "--queries-path",
        type=Path,
        default=PROJECT_ROOT / "data" / "eval" / "seed_queries.json",
        help="Path to seed query JSON",
    )
    parser.add_argument(
        "--index-dir",
        type=Path,
        default=PROJECT_ROOT / "data" / "index",
        help="Directory containing retrieval index assets",
    )
    parser.add_argument(
        "--mode",
        default="hybrid",
        choices=sorted(SUPPORTED_MODES),
        help="Retrieval mode to evaluate",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=5,
        help="Top-k retrieval results per query",
    )
    parser.add_argument(
        "--preview-chars",
        type=int,
        default=220,
        help="Maximum characters for text preview",
    )
    parser.add_argument(
        "--json-output",
        type=Path,
        default=PROJECT_ROOT / "data" / "eval" / "retrieval_eval_results.json",
        help="Path to JSON evaluation output",
    )
    parser.add_argument(
        "--markdown-output",
        type=Path,
        default=PROJECT_ROOT / "data" / "eval" / "retrieval_eval_results.md",
        help="Path to Markdown evaluation output",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level",
    )
    return parser.parse_args()


def load_seed_queries(queries_path: Path) -> list[dict[str, Any]]:
    data = json.loads(queries_path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("seed_queries.json must contain a JSON array")
    for item in data:
        if not isinstance(item, dict) or "query" not in item or "category" not in item:
            raise ValueError("Each seed query must include 'query' and 'category'")
    return data


def run_eval(
    *,
    queries: list[dict[str, Any]],
    service: RetrievalService,
    mode: str,
    top_k: int,
    preview_chars: int,
) -> list[dict[str, Any]]:
    eval_rows: list[dict[str, Any]] = []

    for query_index, query_item in enumerate(queries, start=1):
        query_text = str(query_item["query"]).strip()
        category = str(query_item["category"]).strip()
        logging.getLogger(__name__).info(
            "[%s/%s] Running %s retrieval for seed query: %s",
            query_index,
            len(queries),
            mode,
            query_text,
        )
        results = service.search(query_text, mode=mode, top_k=top_k)
        query_route = results[0].get("query_route") if results else None
        eval_rows.append(
            {
                "query": query_text,
                "category": category,
                "retrieval_mode": mode,
                "top_k": top_k,
                "query_route": query_route,
                "results": [
                    build_eval_record(
                        query=query_text,
                        retrieval_mode=mode,
                        rank=rank,
                        result=result,
                        preview_chars=preview_chars,
                    )
                    for rank, result in enumerate(results, start=1)
                ],
            }
        )

    return eval_rows


def write_json_output(rows: list[dict[str, Any]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(rows, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    logging.getLogger(__name__).info("Wrote JSON eval output to %s", output_path)


def write_markdown_output(rows: list[dict[str, Any]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = [
        "# Retrieval Eval Results",
        "",
        f"- Query count: {len(rows)}",
        f"- Retrieval mode: {rows[0]['retrieval_mode'] if rows else 'n/a'}",
        f"- Top-k per query: {rows[0]['top_k'] if rows else 'n/a'}",
        "",
    ]

    for query_index, row in enumerate(rows, start=1):
        lines.append(f"## Query {query_index}")
        lines.append("")
        lines.append(f"- Query: {row['query']}")
        lines.append(f"- Category: {row['category']}")
        lines.append(f"- Retrieval mode: {row['retrieval_mode']}")
        if row.get("query_route"):
            route = row["query_route"]
            lines.append(f"- Routed intent: {route.get('intent')}")
            lines.append(f"- Preferred sources: {', '.join(route.get('preferred_sources', [])) or 'n/a'}")
            lines.append(f"- Preferred doc types: {', '.join(route.get('preferred_doc_types', [])) or 'n/a'}")
        lines.append("")

        if not row["results"]:
            lines.append("_No results found._")
            lines.append("")
            continue

        for result in row["results"]:
            section_path = " > ".join(result.get("section_path", []))
            lines.append(f"### Rank {result['rank']}")
            lines.append("")
            lines.append(f"- Score: {result['score']:.4f}")
            lines.append(f"- Title: {result['title']}")
            lines.append(f"- Source: {result['source']}")
            lines.append(f"- Version: {result['version']}")
            lines.append(f"- Section path: {section_path}")
            lines.append(f"- URL: {result['url']}")
            lines.append(f"- Preview: {result['text_preview']}")
            lines.append("")

    output_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    logging.getLogger(__name__).info("Wrote Markdown eval output to %s", output_path)


def main() -> None:
    args = parse_args()
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    queries = load_seed_queries(args.queries_path)
    service = RetrievalService.from_index_dir(args.index_dir)
    rows = run_eval(
        queries=queries,
        service=service,
        mode=args.mode,
        top_k=args.top_k,
        preview_chars=args.preview_chars,
    )

    write_json_output(rows, args.json_output)
    write_markdown_output(rows, args.markdown_output)


if __name__ == "__main__":
    main()
