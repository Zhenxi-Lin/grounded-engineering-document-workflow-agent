# Grounded Engineering Document Workflow Agent

A practical workflow-first RAG project for robotics engineering documentation.

This project builds a grounded document workflow system over official engineering docs and currently supports:

- grounded Q&A
- document and procedure comparison
- checklist extraction

The current MVP focuses on ROS 2, PX4, MoveIt, and Isaac ROS documentation, with structured outputs, citation-preserving retrieval, and insufficient-evidence fallback.

## Why this project

Many engineering tasks are not open-ended chat tasks. They are workflow tasks:

- answer a technical question from documentation
- compare two procedures or setup paths
- turn a troubleshooting or setup document into an actionable checklist

This project is designed as a practical AI engineering portfolio project, so the emphasis is on:

- working MVP first
- grounded outputs with citations
- clear module boundaries
- inspectable intermediate artifacts
- easy demo and easy explanation in interviews

## Current scope

Implemented:

- ingestion pipeline for a first batch of engineering docs
- HTML crawling, cleaning, tagging, chunking, and indexing
- BM25 retrieval
- dense retrieval using TF-IDF + SVD embeddings
- hybrid retrieval with metadata-aware reranking
- grounded Q&A
- grounded comparison workflow
- grounded checklist workflow
- optional LLM synthesis layers for Ask, Compare, and Checklist
- citation validation and insufficient-evidence fallback
- lightweight manual evaluation runner
- Streamlit demo

Out of scope for this MVP:

- autonomous multi-agent planning
- cloud deployment
- complex frontend stack
- production auth and infrastructure

## Current data snapshot

Current local corpus snapshot in this repo:

- 4 official documentation sources
- 29 processed documents
- 29 tagged documents
- 450 retrieval chunks
- 9 manual workflow evaluation cases

Primary sources:

- ROS 2 official docs
- PX4 official docs
- MoveIt docs
- Isaac ROS docs

## Architecture

The system follows an explicit workflow pipeline rather than a free-form autonomous agent design:

1. ingestion
2. cleaning
3. chunking
4. retrieval
5. reranking
6. structured generation
7. citation and grounding
8. demo and evaluation

High-level module map:

- `app/ingestion/`
  - crawl, extract, tag, and chunk engineering documentation
- `app/retrieval/`
  - BM25, dense, hybrid retrieval, query routing, ranking
- `app/workflows/`
  - `ask.py`, `compare.py`, `checklist.py`
- `app/prompts/`
  - grounded prompt templates for LLM synthesis
- `app/models/`
  - structured output schemas
- `app/ui/demo.py`
  - Streamlit demo
- `scripts/`
  - indexing, testing, evaluation, and batch runners

## Retrieval and groundedness design

This project is intentionally built around grounded, inspectable evidence flow.

### Retrieval stack

- BM25 over chunk text
- dense retrieval using local TF-IDF + TruncatedSVD vectors
- hybrid retrieval with reciprocal-rank style fusion
- rule-based query routing for likely source and document type
- metadata-aware reranking using:
  - source
  - doc_type
  - topic
  - section_path

### Preserved metadata

Each chunk and citation preserves:

- title
- source
- version
- section_path
- URL
- score
- snippet

This makes outputs easier to debug and easier to explain in a demo.

### Groundedness rules

All three workflows are designed around the same principles:

- retrieve evidence first
- synthesize only from retrieved evidence
- validate citation ids when LLM output is used
- return `insufficient_evidence` instead of guessing
- keep structured outputs small and inspectable

## Workflow overview

### 1. Grounded Q&A

File:

- `app/workflows/ask.py`

Input:

- a user engineering question

Output:

- `query`
- `answer`
- `status`
- `confidence`
- `citations`

Behavior:

- uses the existing hybrid retrieval pipeline
- uses top evidence chunks as support
- can answer through a non-LLM extractive path
- can optionally add LLM grounded synthesis on top
- validates citation ids before returning the final answer

### 2. Grounded Compare

File:

- `app/workflows/compare.py`

Input:

- a comparison query such as `Compare A with B`

Output:

- `query`
- `summary`
- `common_points`
- `differences`
- `risks_or_implications`
- `status`
- `confidence`
- `citations`

Behavior:

- parses comparison targets with transparent rules
- retrieves shared and side-specific evidence
- groups evidence into the two sides when possible
- supports a non-LLM rule-based comparison path
- supports optional LLM grounded comparison synthesis

### 3. Grounded Checklist Extraction

File:

- `app/workflows/checklist.py`

Input:

- a checklist-oriented query
- or a pre-retrieved evidence set

Output:

- `query`
- `checklist_title`
- `prerequisites`
- `ordered_steps`
- `warnings`
- `validation_checks`
- `status`
- `confidence`
- `citations`

Behavior:

- retrieves procedural, setup, or troubleshooting evidence
- prefers high-value sections such as setup, installation, and troubleshooting
- builds a simple rule-based checklist baseline
- optionally applies LLM grounded checklist synthesis
- falls back safely if evidence or LLM output is weak

## With and without LLM

One of the main design goals is to keep the system useful even without an external model.

### Without LLM

The system still supports:

- hybrid retrieval
- reranking
- citations
- insufficient-evidence fallback
- rule-based or extractive grounded outputs

This is useful for:

- local debugging
- deterministic demos
- showing the non-LLM baseline in interviews

### With LLM

The LLM is used only for final grounded synthesis, not for retrieval.

This means:

- retrieval logic stays unchanged
- evidence comes from the same hybrid pipeline
- citations are still validated
- outputs remain structured

Environment variables can be provided through system env or a project-root `.env`.

Examples:

```env
GROUNDED_QA_LLM_API_KEY=your_api_key
GROUNDED_QA_LLM_MODEL=deepseek-chat
GROUNDED_QA_LLM_BASE_URL=https://api.deepseek.com

GROUNDED_COMPARE_LLM_API_KEY=your_api_key
GROUNDED_COMPARE_LLM_MODEL=deepseek-chat
GROUNDED_COMPARE_LLM_BASE_URL=https://api.deepseek.com

GROUNDED_CHECKLIST_LLM_API_KEY=your_api_key
GROUNDED_CHECKLIST_LLM_MODEL=deepseek-chat
GROUNDED_CHECKLIST_LLM_BASE_URL=https://api.deepseek.com
```

## Evaluation

### Retrieval evaluation

The repo already includes:

- `data/eval/seed_queries.json`
- `scripts/run_retrieval_eval.py`
- `data/eval/retrieval_eval_results.json`
- `data/eval/retrieval_eval_results.md`

This supports manual inspection of retrieval quality over seed queries.

### Workflow manual evaluation

New finishing assets added in this step:

- `data/eval/manual_eval_set.json`
- `scripts/run_manual_eval.py`
- `data/eval/manual_eval_report.json`
- `data/eval/manual_eval_report.md`

The manual eval set currently contains:

- 3 Ask cases
- 3 Compare cases
- 3 Checklist cases

Current local non-LLM batch run summary:

- 9 / 9 cases returned grounded outputs
- Ask: 3 grounded answers
- Compare: 3 grounded comparisons
- Checklist: 3 grounded checklists

Run the manual evaluation:

```bash
python scripts/run_manual_eval.py --disable-llm --log-level INFO
```

Run the same evaluation with optional LLM synthesis enabled:

```bash
python scripts/run_manual_eval.py --log-level INFO
```

## Demo

The project now includes a lightweight Streamlit demo:

- `app/ui/demo.py`

Features:

- three tabs: Ask, Compare, Checklist
- clearly rendered structured outputs
- citation display with source, title, section path, URL, and snippet
- optional LLM synthesis toggle
- minimal UI intended for project demos rather than product polish

Run it with:

```bash
streamlit run app/ui/demo.py
```

If `streamlit` is not installed yet:

```bash
pip install streamlit
```

## Example outputs

### Example Ask output

Query:

```text
How do I create a ROS 2 workspace and build packages with colcon for a new project?
```

Example grounded answer:

```json
{
  "status": "grounded_answer",
  "confidence": 0.9,
  "answer": "Based on the retrieved documentation, the main procedure is: 1. ... source your main ROS 2 distro install as your underlay ... 2. ... create and build packages in a new workspace ..."
}
```

### Example Compare output

Query:

```text
Compare PX4 first simulator build setup with PX4 ROS 2 offboard control example setup
```

Example grounded comparison:

```json
{
  "status": "grounded_comparison",
  "confidence": 0.88,
  "summary": "The retrieved evidence compares PX4 first simulator build setup and PX4 ROS 2 offboard control example setup."
}
```

### Example Checklist output

Query:

```text
Create a checklist for running the PX4 ROS 2 offboard control example
```

Example grounded checklist:

```json
{
  "status": "grounded_checklist",
  "confidence": 0.9,
  "checklist_title": "Create a checklist for running the PX4 ROS 2 offboard control example"
}
```

## How to run the main pipeline

### Data preparation

```bash
python scripts/crawl_docs.py
python scripts/extract_docs.py
python scripts/tag_docs.py
python scripts/build_chunks.py
python scripts/build_index.py
```

### Workflow tests

```bash
python scripts/test_grounded_qa.py "What is NITROS in Isaac ROS?"
python scripts/test_compare.py "Compare MoveIt and Isaac ROS"
python scripts/test_checklist.py "Create a troubleshooting checklist for PX4 flash overflow build errors"
```

### Retrieval test

```bash
python scripts/test_retrieval.py --mode hybrid --top-k 5 "ROS 2 offboard control example"
```

## Project strengths for portfolio use

This project is a good portfolio piece because it demonstrates:

- end-to-end AI workflow design, not just prompting
- document ingestion and retrieval engineering
- grounded generation with citation validation
- hybrid retrieval and rule-based reranking
- explicit abstention through insufficient-evidence handling
- modular Python code that is easy to explain in an interview

## Current limitations

- the current corpus is intentionally small and high-value, not a full-site crawl
- manual evaluation is still lightweight and human-reviewed
- no API layer or deployment package yet
- no checklist post-editing or interactive reviewer loop yet
- the compare and checklist baselines are still intentionally simple

## Next practical upgrades

- add a FastAPI backend for demo-ready serving
- add a reviewer-oriented debug dump for evidence and synthesis traces
- expand the manual eval set with explicit relevance labels
- improve checklist step extraction from long procedural sections
- add small benchmark metrics over the manual eval set
