# Collect Agent

AI-powered debt collection agent with multi-channel outreach, intent detection, and compliance-aware scheduling.

## Install

```bash
uv sync
```

## Run Tests

```bash
uv run pytest tests/ -q
```

## Run Demo

```bash
uv run python src/cli.py --action=demo
```

## Run Scheduled Outreach

```bash
uv run python src/cli.py --action=scan
```

## Send an Event

```bash
uv run python src/cli.py --action=event --user-id=u001 --event-type=USER_LOGIN
```

## Architecture

- **Core**: Event-driven state machine (`Event`, `UserState`, `SessionState`)
- **Session**: `CollectionSession` handles events, orchestrates channels, detects intent
- **Scheduler**: `OutreachScheduler` scans overdue users and triggers outreach
- **Router**: `EventRouter` routes events to the correct session
- **Channels**: Chatbot, Voice, Push with state tracking
- **Strategy**: Rule-based strategy engine with LLM fallback
- **LLM**: Supports Mock, Claude, OpenAI, DeepSeek clients
- **Compliance**: Valid hours, call limits, forbidden words
- **Quota**: Daily limits per channel
- **Storage**: SQLite persistence with `MemoryStore` for testing
- **CLI**: `src/cli.py` with `--action={scan,event,demo}`
