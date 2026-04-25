from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import streamlit as st


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.llm_client import LLMClient
from app.workflows.ask import build_grounded_qa_workflow
from app.workflows.checklist import build_checklist_workflow
from app.workflows.compare import build_compare_workflow


DEFAULT_INDEX_DIR = PROJECT_ROOT / "data" / "index"


@st.cache_resource(show_spinner=False)
def load_workflows(
    *,
    index_dir: str,
    ask_top_k: int,
    compare_top_k: int,
    checklist_top_k: int,
    enable_llm: bool,
) -> dict[str, Any]:
    ask_llm = None if not enable_llm else LLMClient.from_env(prefixes=("GROUNDED_QA_LLM", "OPENAI"))
    compare_llm = None if not enable_llm else LLMClient.from_env(
        prefixes=("GROUNDED_COMPARE_LLM", "GROUNDED_QA_LLM", "OPENAI")
    )
    checklist_llm = None if not enable_llm else LLMClient.from_env(
        prefixes=("GROUNDED_CHECKLIST_LLM", "GROUNDED_QA_LLM", "OPENAI")
    )

    return {
        "ask": build_grounded_qa_workflow(
            index_dir=Path(index_dir),
            evidence_top_k=ask_top_k,
            llm_client=ask_llm,
            enable_llm_synthesis=enable_llm,
        ),
        "compare": build_compare_workflow(
            index_dir=Path(index_dir),
            evidence_top_k=compare_top_k,
            llm_client=compare_llm,
            enable_llm_synthesis=enable_llm,
        ),
        "checklist": build_checklist_workflow(
            index_dir=Path(index_dir),
            evidence_top_k=checklist_top_k,
            llm_client=checklist_llm,
            enable_llm_synthesis=enable_llm,
        ),
    }


def render_citations(citations: list[dict[str, Any]]) -> None:
    st.subheader("Citations")
    if not citations:
        st.info("No citations returned.")
        return

    for index, citation in enumerate(citations, start=1):
        section_path = " > ".join(citation.get("section_path", []))
        label = (
            f"{index}. {citation.get('source', '')} | {citation.get('title', '')} "
            f"| score={citation.get('score', 0.0):.3f}"
        )
        with st.expander(label):
            st.markdown(f"**Chunk ID**: `{citation.get('chunk_id', '')}`")
            st.markdown(f"**Version**: {citation.get('version', '') or 'n/a'}")
            st.markdown(f"**Section Path**: {section_path or 'n/a'}")
            st.markdown(f"**URL**: {citation.get('url', '')}")
            st.markdown(f"**Snippet**: {citation.get('snippet', '')}")


def render_status_row(*, status: str, confidence: float, citations: list[dict[str, Any]]) -> None:
    col1, col2, col3 = st.columns(3)
    col1.metric("Status", status)
    col2.metric("Confidence", f"{confidence:.3f}")
    col3.metric("Citations", str(len(citations)))


def render_ask_result(result: dict[str, Any]) -> None:
    render_status_row(
        status=result.get("status", ""),
        confidence=float(result.get("confidence", 0.0)),
        citations=result.get("citations", []),
    )
    st.subheader("Answer")
    st.write(result.get("answer", ""))
    render_citations(result.get("citations", []))
    with st.expander("Raw JSON"):
        st.json(result)


def render_compare_result(result: dict[str, Any]) -> None:
    render_status_row(
        status=result.get("status", ""),
        confidence=float(result.get("confidence", 0.0)),
        citations=result.get("citations", []),
    )
    st.subheader("Summary")
    st.write(result.get("summary", ""))
    render_text_list("Common Points", result.get("common_points", []))
    render_text_list("Differences", result.get("differences", []))
    render_text_list("Risks or Implications", result.get("risks_or_implications", []))
    render_citations(result.get("citations", []))
    with st.expander("Raw JSON"):
        st.json(result)


def render_checklist_result(result: dict[str, Any]) -> None:
    render_status_row(
        status=result.get("status", ""),
        confidence=float(result.get("confidence", 0.0)),
        citations=result.get("citations", []),
    )
    st.subheader("Checklist Title")
    st.write(result.get("checklist_title", ""))
    render_text_list("Prerequisites", result.get("prerequisites", []))
    render_text_list("Ordered Steps", result.get("ordered_steps", []), ordered=True)
    render_text_list("Warnings", result.get("warnings", []))
    render_text_list("Validation Checks", result.get("validation_checks", []))
    render_citations(result.get("citations", []))
    with st.expander("Raw JSON"):
        st.json(result)


def render_text_list(title: str, items: list[Any], *, ordered: bool = False) -> None:
    st.subheader(title)
    if not items:
        st.caption("None")
        return

    for index, item in enumerate(items, start=1):
        prefix = f"{index}. " if ordered else "- "
        st.markdown(f"{prefix}{item}")


def main() -> None:
    st.set_page_config(
        page_title="Grounded Engineering Document Workflow Agent",
        layout="wide",
    )
    st.title("Grounded Engineering Document Workflow Agent")
    st.caption("Grounded Ask / Compare / Checklist demo over robotics engineering documentation.")

    with st.sidebar:
        st.header("Settings")
        index_dir = st.text_input("Index Directory", value=str(DEFAULT_INDEX_DIR))
        enable_llm = st.toggle("Enable LLM synthesis", value=True)
        ask_top_k = st.slider("Ask top-k", min_value=3, max_value=6, value=4)
        compare_top_k = st.slider("Compare top-k", min_value=6, max_value=12, value=8)
        checklist_top_k = st.slider("Checklist top-k", min_value=4, max_value=10, value=6)
        st.caption(
            "If no API key or model is configured in the environment or .env, the workflows fall back to non-LLM behavior."
        )

    workflows = load_workflows(
        index_dir=index_dir,
        ask_top_k=ask_top_k,
        compare_top_k=compare_top_k,
        checklist_top_k=checklist_top_k,
        enable_llm=enable_llm,
    )

    ask_tab, compare_tab, checklist_tab = st.tabs(["Ask", "Compare", "Checklist"])

    with ask_tab:
        st.write("Ask a grounded engineering question over the indexed documentation.")
        ask_query = st.text_area(
            "Ask Query",
            value="How do I create a ROS 2 workspace and build packages with colcon for a new project?",
            height=100,
            key="ask_query",
        )
        if st.button("Run Ask", use_container_width=True):
            with st.spinner("Running grounded Q&A..."):
                result = workflows["ask"].answer(ask_query).to_dict()
            render_ask_result(result)

    with compare_tab:
        st.write("Compare two engineering procedures or concepts using grounded evidence.")
        compare_query = st.text_area(
            "Compare Query",
            value="Compare ROS 2 official workspace creation guidance with Isaac ROS workspace setup guidance",
            height=100,
            key="compare_query",
        )
        if st.button("Run Compare", use_container_width=True):
            with st.spinner("Running grounded comparison..."):
                result = workflows["compare"].compare(compare_query).to_dict()
            render_compare_result(result)

    with checklist_tab:
        st.write("Convert setup or troubleshooting evidence into a grounded checklist.")
        checklist_query = st.text_area(
            "Checklist Query",
            value="Create a troubleshooting checklist for PX4 flash overflow build errors",
            height=100,
            key="checklist_query",
        )
        if st.button("Run Checklist", use_container_width=True):
            with st.spinner("Running grounded checklist extraction..."):
                result = workflows["checklist"].build_checklist(query=checklist_query).to_dict()
            render_checklist_result(result)


if __name__ == "__main__":
    main()
