# AGENTS.md

## Project
Grounded Engineering Document Workflow Agent

## Goal
Build a practical AI workflow system over engineering documents that supports:
- grounded question answering
- document / procedure comparison
- checklist extraction

This project should become a strong resume-level portfolio project.

---

## My Background
I am a master's student in Control Engineering.

My background includes:
- Python
- C/C++
- PyTorch
- reinforcement learning
- multi-agent systems
- computer vision
- embedded systems / control

I am transitioning toward:
- Applied AI
- LLM applications
- AI engineering
- workflow / agent systems

---

## Current Strategy
Prioritize:
1. working MVP first
2. clear structure
3. easy debugging
4. easy explanation in interviews
5. portfolio value

Do not optimize for:
- unnecessary complexity
- fancy abstractions
- over-engineering
- advanced multi-agent designs too early

---

## Scope for MVP
The MVP should support only:
1. grounded Q&A
2. document compare
3. checklist extraction

Out of scope for MVP:
- multi-agent systems
- complicated memory
- cloud deployment
- enterprise auth
- autonomous planning
- fancy frontend
- heavy infrastructure

---

## Preferred Document Domain
Focus mainly on:
- robotics documentation
- ROS / PX4 / MoveIt / Isaac ROS style engineering docs

Embodied AI or general AI docs can be added later as a small extension, not the main scope.

---

## Coding Rules
- prefer small, modular Python files
- use type hints
- add basic logging and error handling
- keep dependencies minimal
- use environment variables for secrets
- avoid hardcoding credentials
- write readable code over clever code
- keep functions easy to test
- preserve metadata clearly

---

## Architecture Rules
Prefer a workflow-first design, not a free-form autonomous agent.

Use explicit steps:
1. ingestion
2. cleaning
3. chunking
4. retrieval
5. reranking
6. structured generation
7. citation / grounding
8. API / demo

Always keep outputs structured and inspectable.

---

## Retrieval Rules
For early versions:
- prefer simple and reliable baselines
- preserve title, section, source, version, and URL metadata
- do not lose step boundaries in procedure-like documents
- support citation-friendly outputs

---

## LLM Rules
- use structured outputs
- keep prompts short and task-specific
- avoid overly creative prompting
- prefer deterministic, stable behavior
- if evidence is insufficient, abstain instead of guessing
- do not generate unsupported claims confidently

---

## UI and API Rules
For the first demo:
- FastAPI is enough for backend
- Streamlit is enough for frontend
- no need for a complex frontend stack

---

## How to Help Me
When implementing a task:
1. choose the smallest useful version first
2. keep files and modules clean
3. explain assumptions briefly
4. do not expand scope on your own
5. suggest optional upgrades separately

When responding with code:
- say what the code does
- state which file(s) it belongs to
- provide runnable code
- explain how to run it
- suggest the next smallest useful step

---

## Collaboration Style
Act like a practical engineering mentor:
- direct
- grounded
- efficient
- resume-oriented

Priority order:
1. working
2. understandable
3. demoable
4. extensible
5. resume-valuable
