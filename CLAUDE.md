# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AI-powered debt collection agent with multi-channel outreach, intent detection, compliance-aware scheduling, and a skill-based ReAct agent architecture.

## Development Commands

All Python commands must use `uv run` prefix:

```bash
# Install dependencies
uv sync

# Run all tests
uv run pytest tests/ -q

# Run a single test file
uv run pytest tests/test_integration.py -q

# Run linter
cd /Users/geoqiao/self_project/collect-agent && uv run ruff check src/ tests/

# Auto-fix lint issues
cd /Users/geoqiao/self_project/collect-agent && uv run ruff check src/ tests/ --fix

# Run demo workflow
uv run collect-agent --action=demo

# Run scheduled outreach scan
uv run collect-agent --action=scan

# Send a specific event
uv run collect-agent --action=event --user-id=u001 --event-type=USER_LOGIN
```

Dependencies are managed exclusively via `uv add <package>` and `uv add --dev <package>`. Do not edit `pyproject.toml` or `uv.lock` manually.

## High-Level Architecture

### Two Session Architectures (Migration in Progress)

The codebase has two session implementations:

1. **`AgentSession`** (`src/collect_agent/agent/session.py`) — The new primary session. It is a skill-based ReAct agent that handles events by delegating to `SkillExecutor`, which drives an LLM through a reasoning loop using available tools.

2. **`CollectionSession`** (`src/collect_agent/session/session.py`) — Legacy session using static strategy dictionaries (`STRATEGIES` in `src/collect_agent/strategy/strategies.py`) and keyword-based intent detection (`IntentDetector`). It is deprecated and kept for backward compatibility only. `SessionManager.get_or_create()` creates `AgentSession` by default.

### Skill-Based Agent Architecture

Skills (`src/collect_agent/skills/`) are **declarative configuration only** — they define a name, trigger intents, a prompt template, and a list of available `Tool` instances. They contain **no hard-coded execution logic**.

Execution is fully delegated to `SkillExecutor` (`src/collect_agent/skills/executor.py`), which:
1. Loads the skill's system prompt from `src/collect_agent/prompts/templates/skills/`
2. Injects tool schemas (XML format via `Tool.to_xml_description()`)
3. Runs a ReAct loop with the LLM, up to `skill.max_react_steps`
4. Parses `<action>` tags, calls tools via `ToolRegistry`, and feeds results back

Default skills: `OnboardSkill`, `PaymentGuidanceSkill`, `NegotiationSkill`, `ReEngageSkill`, `DisputeSkill`, `ComplaintSkill`, `CrisisSkill`, `StopSkill`, `TroubleshootSkill`, `FollowUpSkill`.

### State Machine

`AgentSessionState` (`src/collect_agent/core/constants.py`) has two classes of states:

- **Flowing states** (`NORMAL`, `PENDING_ESCALATE`): Can transition freely between each other.
- **One-way doors** (`ESCALATED`, `STOPPED`, `CRISIS`, `DISPUTED`): Irreversible. Once entered, the session is locked. All subsequent user messages receive a fixed template response (defined in `AgentSession._FIXED_TEMPLATES`) regardless of intent.

Terminal states: `RESOLVED`, `PAUSED`.

### Event-Driven Flow

`EventRouter` (`src/collect_agent/events/router.py`) routes `Event` objects to the correct `AgentSession`. Events are typed via `EventType` enum (SCHEDULED_OUTREACH, USER_REPLIED, SILENCE_TIMEOUT, USER_PAYMENT_SUCCESS, etc.).

The CLI (`src/collect_agent/cli.py`) and scheduler (`src/collect_agent/scheduler.py`) are the main event producers.

### Intent Recognition

`IntentRecognizer` (`src/collect_agent/intent/recognizer.py`) categorizes user messages into `IntentCategory` (COOPERATION, NEGOTIATION, AVOIDANCE, DISPUTE, COMPLAINT, STOP, CRISIS). If the session is in a locked one-way door state, `recognize_with_guardrails()` is used to prevent state transitions.

### Compliance & Quota

Before any outbound outreach, `ComplianceChecker` verifies valid hours and audits content for forbidden words. `QuotaManager` enforces daily per-channel limits. `Orchestrator` handles channel arbitration (priority: VOICE > CHATBOT > PUSH) via per-user `InteractionLock`.

Sensitive occupations (lawyer, judge, police, journalist, etc.) bypass negotiation and always receive the `standard_reminder` strategy.

### LLM Abstraction

`LLMClient` base class (`src/collect_agent/llm/base.py`) with implementations:
- `MockLLMClient` — for tests, returns deterministic responses
- `ClaudeClient` — Anthropic API
- `OpenAIClient` — OpenAI API
- `DeepSeekClient` — DeepSeek API

API keys are resolved from environment variables (`DEEPSEEK_API_KEY`, `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`) via `create_llm_client()`. The provider is configured in `config.yaml`.

### Storage

- `SQLiteStore` — production persistence
- `MemoryStore` — in-memory, for testing

### Tools

Tools (`src/collect_agent/tools/`) are abstract `Tool` subclasses with JSON Schema descriptions for LLM function calling. Categories: billing, messaging, compliance, promises, user. All tools are registered in `ToolRegistry`.

## Key Configuration

`config.yaml` configures:
- `llm`: provider, model, temperature, max_tokens
- `compliance`: valid_hours, max_call_per_hour, min_call_interval_minutes
- `quota`: daily limits per channel
- `storage`: db_path
