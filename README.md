# AOrchestra — Open Implementation

Reproduction and extension of [AOrchestra: Automating Sub-Agent Creation for Agentic Orchestration](https://arxiv.org/abs/2602.03786) (Ruan et al., 2026).

## Core Concept

Any agent is a dynamically instantiable 4-tuple:

```
Φ = (Instruction, Context, Tools, Model)
```

An **Orchestrator** decomposes complex tasks into subtasks, creates specialized sub-agents on-the-fly via `Delegate(Φ)`, and terminates with `Finish(y)`.

## Architecture

```
User Goal → Orchestrator → Delegate(Φ₁) → Sub-Agent₁ → observation₁
                         → Delegate(Φ₂) → Sub-Agent₂ → observation₂
                         → ...
                         → Finish(answer)
```

## Stack

- Python 3.12+
- LangChain / LangGraph for agent orchestration
- GLM-4.7 via Z.ai as default LLM backend
- Pluggable model selection (cheap → expensive routing)
