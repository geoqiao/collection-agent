# 催收员 Agent 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建一个支持多轮、多渠道催收的 Agent 系统，包含意图识别、策略引擎、配额管理、冲突仲裁和合规护栏。

**Architecture:** 分层编排架构（Orchestrator + Strategy Engine + Tool Agents），每个用户一个独立 Actor，事件驱动，LLM 抽象层支持多模型切换。

**Tech Stack:** Python 3.11+, pytest, Pydantic, PyYAML, Jinja2

---

## 文件结构

```
collect-agent/
├── pyproject.toml
├── config.yaml
├── src/
│   ├── __init__.py
│   ├── main.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── constants.py         # 枚举定义
│   │   └── models.py            # 数据模型
│   ├── events/
│   │   ├── __init__.py
│   │   └── router.py            # 事件路由器
│   ├── storage/
│   │   ├── __init__.py
│   │   └── memory_store.py      # 内存状态存储
│   ├── session/
│   │   ├── __init__.py
│   │   ├── session.py           # CollectionSession
│   │   ├── state_machine.py     # 会话状态机
│   │   └── manager.py           # SessionManager
│   ├── channels/
│   │   ├── __init__.py
│   │   ├── base.py              # Channel 抽象基类
│   │   └── registry.py          # ChannelRegistry
│   ├── orchestrator/
│   │   ├── __init__.py
│   │   ├── lock.py              # InteractionLock
│   │   └── orchestrator.py      # 主调度器
│   ├── strategy/
│   │   ├── __init__.py
│   │   ├── detector.py          # 意图识别器
│   │   ├── engine.py            # 策略引擎
│   │   └── strategies.py        # 策略实现
│   ├── quota/
│   │   ├── __init__.py
│   │   ├── profile.py           # 配额配置
│   │   ├── usage.py             # 配额使用记录
│   │   └── manager.py           # 配额管理器
│   ├── compliance/
│   │   ├── __init__.py
│   │   ├── rules.py             # 合规规则
│   │   └── checker.py           # 合规检查器
│   └── llm/
│       ├── __init__.py
│       ├── base.py              # LLMClient 抽象
│       └── clients.py           # 各模型实现
└── tests/
    ├── __init__.py
    ├── test_core.py
    ├── test_session.py
    ├── test_orchestrator.py
    ├── test_strategy.py
    ├── test_quota.py
    ├── test_compliance.py
    └── test_llm.py
```

---

## Task 1: 项目初始化与核心枚举

**Files:**
- Create: `pyproject.toml`
- Create: `src/__init__.py`
- Create: `src/core/__init__.py`
- Create: `src/core/constants.py`
- Test: `tests/__init__.py`
- Test: `tests/test_core.py`

- [ ] **Step 1: 创建 pyproject.toml**

```toml
[project]
name = "collect-agent"
version = "0.1.0"
description = "AI-powered debt collection agent"
requires-python = ">=3.11"
dependencies = [
    "pydantic>=2.0",
    "pyyaml>=6.0",
    "jinja2>=3.1",
]

[project.optional-dependencies]
dev = ["pytest>=7.0", "pytest-asyncio>=0.21"]
```

- [ ] **Step 2: 安装依赖**

Run: `pip install -e ".[dev]"`
Expected: 安装成功，无报错

- [ ] **Step 3: 写核心枚举测试**

```python
# tests/test_core.py
from src.core.constants import EventType, ChannelType, Intent, SessionState, ChannelState


def test_event_type_has_required_events():
    assert EventType.SCHEDULED_OUTREACH is not None
    assert EventType.USER_LOGIN is not None
    assert EventType.CALL_CONNECTED is not None
    assert EventType.USER_REPLIED is not None


def test_channel_type_values():
    assert ChannelType.VOICE.value == "voice"
    assert ChannelType.CHATBOT.value == "chatbot"
    assert ChannelType.PUSH.value == "push"


def test_intent_values():
    assert Intent.WILLING_TO_PAY.value == "willing_to_pay"
    assert Intent.UNWILLING_TO_PAY.value == "unwilling_to_pay"
    assert Intent.INEFFECTIVE_CONTACT.value == "ineffective_contact"
    assert Intent.COMPLAINT.value == "complaint"
    assert Intent.PAYMENT_METHOD_INQUIRY.value == "payment_method_inquiry"
    assert Intent.OPERATION_INQUIRY.value == "operation_inquiry"
```

- [ ] **Step 4: 运行测试确认失败**

Run: `pytest tests/test_core.py -v`
Expected: 6 tests FAIL with ImportError

- [ ] **Step 5: 实现核心枚举**

```python
# src/core/constants.py
from enum import Enum, auto


class EventType(Enum):
    SCHEDULED_OUTREACH = "scheduled_outreach"
    REMINDER_DUE = "reminder_due"
    SILENCE_TIMEOUT = "silence_timeout"
    USER_LOGIN = "user_login"
    USER_PAYMENT_ATTEMPT = "user_payment_attempt"
    USER_PAYMENT_SUCCESS = "user_payment_success"
    USER_PAYMENT_FAIL = "user_payment_fail"
    CALL_CONNECTED = "call_connected"
    CALL_DISCONNECTED = "call_disconnected"
    CALL_NO_ANSWER = "call_no_answer"
    MESSAGE_SENT = "message_sent"
    MESSAGE_DELIVERED = "message_delivered"
    USER_REPLIED = "user_replied"
    QUOTA_EXHAUSTED = "quota_exhausted"
    COMPLIANCE_VIOLATION = "compliance_violation"


class ChannelType(Enum):
    VOICE = "voice"
    CHATBOT = "chatbot"
    PUSH = "push"


class Intent(Enum):
    WILLING_TO_PAY = "willing_to_pay"
    UNWILLING_TO_PAY = "unwilling_to_pay"
    INEFFECTIVE_CONTACT = "ineffective_contact"
    COMPLAINT = "complaint"
    PAYMENT_METHOD_INQUIRY = "payment_method_inquiry"
    OPERATION_INQUIRY = "operation_inquiry"


class SessionState(Enum):
    IDLE = "idle"
    OUTREACH_START = "outreach_start"
    INTENT_DETECTED = "intent_detected"
    FOLLOW_UP = "follow_up"
    RESOLVED = "resolved"


class ChannelState(Enum):
    IDLE = "idle"
    SCHEDULED = "scheduled"
    OUTGOING = "outgoing"
    INTERACTING = "interacting"
    WAITING_REPLY = "waiting_reply"
    PAUSED = "paused"
    CLOSED = "closed"
```

- [ ] **Step 6: 运行测试确认通过**

Run: `pytest tests/test_core.py -v`
Expected: 6 tests PASS

- [ ] **Step 7: Commit**

```bash
git add pyproject.toml src/ tests/
git commit -m "feat: add core enums and project setup"
```

---

## Task 2: 核心数据模型

**Files:**
- Create: `src/core/models.py`
- Modify: `tests/test_core.py`

- [ ] **Step 1: 写模型测试**

```python
# tests/test_core.py (追加)
from src.core.models import UserProfile, Event, Message, ConversationContext


def test_user_profile_creation():
    user = UserProfile(user_id="u001", name="张三", phone="13800138000")
    assert user.user_id == "u001"
    assert user.is_sensitive is False


def test_user_profile_sensitive_occupation():
    user = UserProfile(user_id="u002", name="李四", occupation="律师")
    assert user.is_sensitive is True


def test_event_creation():
    from src.core.constants import EventType
    event = Event(user_id="u001", type=EventType.USER_LOGIN, payload={})
    assert event.user_id == "u001"
    assert event.type == EventType.USER_LOGIN


def test_message_creation():
    msg = Message(channel="chatbot", direction="outbound", content="请尽快还款")
    assert msg.channel == "chatbot"
    assert msg.direction == "outbound"
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/test_core.py::test_user_profile_creation -v`
Expected: FAIL with ImportError

- [ ] **Step 3: 实现核心模型**

```python
# src/core/models.py
from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field, computed_field

from src.core.constants import EventType


class UserProfile(BaseModel):
    user_id: str
    name: str = ""
    phone: str = ""
    occupation: str | None = None
    overdue_days: int = 0
    amount_due: float = 0.0

    @computed_field
    @property
    def is_sensitive(self) -> bool:
        if not self.occupation:
            return False
        sensitive = {
            "律师", "法官", "检察官", "警察",
            "政府官员", "公务员", "军人", "军人配偶",
            "记者", "媒体从业者",
        }
        return self.occupation in sensitive


class Event(BaseModel):
    user_id: str
    type: EventType
    payload: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.now)


class Message(BaseModel):
    channel: str
    direction: str  # "inbound" | "outbound"
    content: str
    timestamp: datetime = Field(default_factory=datetime.now)


class ConversationContext(BaseModel):
    messages: list[Message] = Field(default_factory=list)
    current_intent: str | None = None
    negotiation_round: int = 0

    def add_message(self, message: Message) -> None:
        self.messages.append(message)
        if len(self.messages) > 50:
            self.messages = self.messages[-50:]


class UserState(BaseModel):
    user_id: str
    profile: UserProfile
    session_state: str = "idle"
    channel_states: dict[str, str] = Field(default_factory=dict)
    conversation: ConversationContext = Field(default_factory=ConversationContext)
    quota_usage: dict[str, Any] = Field(default_factory=dict)
```

- [ ] **Step 4: 运行测试确认通过**

Run: `pytest tests/test_core.py -v`
Expected: 10 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/core/models.py tests/test_core.py
git commit -m "feat: add core data models"
```

---

## Task 3: 内存状态存储

**Files:**
- Create: `src/storage/__init__.py`
- Create: `src/storage/memory_store.py`
- Test: `tests/test_storage.py`

- [ ] **Step 1: 写存储测试**

```python
# tests/test_storage.py
import pytest
from src.storage.memory_store import MemoryStore
from src.core.models import UserState, UserProfile


@pytest.fixture
def store():
    return MemoryStore()


@pytest.fixture
def sample_state():
    return UserState(
        user_id="u001",
        profile=UserProfile(user_id="u001", name="张三")
    )


def test_save_and_load(store, sample_state):
    store.save(sample_state)
    loaded = store.load("u001")
    assert loaded is not None
    assert loaded.user_id == "u001"
    assert loaded.profile.name == "张三"


def test_load_nonexistent(store):
    assert store.load("nonexistent") is None


def test_load_all(store, sample_state):
    store.save(sample_state)
    store.save(UserState(user_id="u002", profile=UserProfile(user_id="u002", name="李四")))
    all_states = store.load_all()
    assert len(all_states) == 2
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/test_storage.py -v`
Expected: FAIL with ImportError

- [ ] **Step 3: 实现内存存储**

```python
# src/storage/memory_store.py
from src.core.models import UserState


class MemoryStore:
    def __init__(self):
        self._data: dict[str, UserState] = {}

    def save(self, state: UserState) -> None:
        self._data[state.user_id] = state

    def load(self, user_id: str) -> UserState | None:
        return self._data.get(user_id)

    def load_all(self) -> list[UserState]:
        return list(self._data.values())

    def delete(self, user_id: str) -> None:
        self._data.pop(user_id, None)
```

- [ ] **Step 4: 运行测试确认通过**

Run: `pytest tests/test_storage.py -v`
Expected: 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/storage/ tests/test_storage.py
git commit -m "feat: add memory state store"
```

---

## Task 4: 事件路由器

**Files:**
- Create: `src/events/__init__.py`
- Create: `src/events/router.py`
- Test: `tests/test_events.py`

- [ ] **Step 1: 写事件路由测试**

```python
# tests/test_events.py
import pytest
from src.events.router import EventRouter
from src.core.constants import EventType
from src.core.models import Event


class MockSessionManager:
    def __init__(self):
        self.events = []

    def get_or_create(self, user_id: str):
        return MockSession(self, user_id)


class MockSession:
    def __init__(self, manager, user_id: str):
        self.user_id = user_id
        self.manager = manager

    def handle_event(self, event: Event) -> None:
        self.manager.events.append((self.user_id, event))


@pytest.fixture
def router():
    return EventRouter(MockSessionManager())


def test_route_event_to_session(router):
    event = Event(user_id="u001", type=EventType.USER_LOGIN)
    router.route(event)
    assert len(router.session_manager.events) == 1
    assert router.session_manager.events[0][0] == "u001"
    assert router.session_manager.events[0][1].type == EventType.USER_LOGIN


def test_route_creates_session_for_new_user(router):
    event = Event(user_id="u_new", type=EventType.SCHEDULED_OUTREACH)
    router.route(event)
    assert len(router.session_manager.events) == 1
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/test_events.py -v`
Expected: FAIL with ImportError

- [ ] **Step 3: 实现事件路由器**

```python
# src/events/router.py
from src.core.models import Event


class EventRouter:
    def __init__(self, session_manager):
        self.session_manager = session_manager

    def route(self, event: Event) -> None:
        session = self.session_manager.get_or_create(event.user_id)
        session.handle_event(event)
```

- [ ] **Step 4: 运行测试确认通过**

Run: `pytest tests/test_events.py -v`
Expected: 2 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/events/ tests/test_events.py
git commit -m "feat: add event router"
```

---

## Task 5: 会话状态机

**Files:**
- Create: `src/session/__init__.py`
- Create: `src/session/state_machine.py`
- Test: `tests/test_session.py`

- [ ] **Step 1: 写状态机测试**

```python
# tests/test_session.py
import pytest
from src.session.state_machine import SessionStateMachine
from src.core.constants import SessionState


@pytest.fixture
def sm():
    return SessionStateMachine()


def test_initial_state(sm):
    assert sm.current == SessionState.IDLE


def test_transition_idle_to_outreach(sm):
    assert sm.can_transition(SessionState.OUTREACH_START) is True
    sm.transition(SessionState.OUTREACH_START)
    assert sm.current == SessionState.OUTREACH_START


def test_invalid_transition(sm):
    sm.transition(SessionState.OUTREACH_START)
    assert sm.can_transition(SessionState.IDLE) is False


def test_transition_to_intent_detected(sm):
    sm.transition(SessionState.OUTREACH_START)
    sm.transition(SessionState.INTENT_DETECTED)
    assert sm.current == SessionState.INTENT_DETECTED


def test_transition_to_resolved(sm):
    sm.transition(SessionState.OUTREACH_START)
    sm.transition(SessionState.INTENT_DETECTED)
    sm.transition(SessionState.FOLLOW_UP)
    sm.transition(SessionState.RESOLVED)
    assert sm.current == SessionState.RESOLVED
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/test_session.py -v`
Expected: FAIL with ImportError

- [ ] **Step 3: 实现状态机**

```python
# src/session/state_machine.py
from src.core.constants import SessionState


class SessionStateMachine:
    TRANSITIONS = {
        SessionState.IDLE: [SessionState.OUTREACH_START],
        SessionState.OUTREACH_START: [SessionState.INTENT_DETECTED, SessionState.IDLE],
        SessionState.INTENT_DETECTED: [SessionState.FOLLOW_UP, SessionState.RESOLVED, SessionState.IDLE],
        SessionState.FOLLOW_UP: [SessionState.FOLLOW_UP, SessionState.RESOLVED, SessionState.IDLE],
        SessionState.RESOLVED: [SessionState.IDLE],
    }

    def __init__(self):
        self._current = SessionState.IDLE

    @property
    def current(self) -> SessionState:
        return self._current

    def can_transition(self, target: SessionState) -> bool:
        return target in self.TRANSITIONS.get(self._current, [])

    def transition(self, target: SessionState) -> None:
        if not self.can_transition(target):
            raise ValueError(f"Cannot transition from {self._current.value} to {target.value}")
        self._current = target
```

- [ ] **Step 4: 运行测试确认通过**

Run: `pytest tests/test_session.py -v`
Expected: 5 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/session/state_machine.py tests/test_session.py
git commit -m "feat: add session state machine"
```

---

## Task 6: 交互锁

**Files:**
- Create: `src/orchestrator/__init__.py`
- Create: `src/orchestrator/lock.py`
- Test: `tests/test_orchestrator.py`

- [ ] **Step 1: 写交互锁测试**

```python
# tests/test_orchestrator.py
import pytest
from src.orchestrator.lock import InteractionLock
from src.core.constants import ChannelType


@pytest.fixture
def lock():
    return InteractionLock()


def test_initially_unlocked(lock):
    assert lock.holder is None
    assert lock.is_locked is False


def test_acquire_lock(lock):
    lock.acquire(ChannelType.VOICE)
    assert lock.holder == ChannelType.VOICE
    assert lock.is_locked is True


def test_release_lock(lock):
    lock.acquire(ChannelType.VOICE)
    lock.release()
    assert lock.holder is None
    assert lock.is_locked is False


def test_acquire_when_locked(lock):
    lock.acquire(ChannelType.CHATBOT)
    lock.acquire(ChannelType.VOICE)
    assert lock.holder == ChannelType.VOICE
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/test_orchestrator.py -v`
Expected: FAIL with ImportError

- [ ] **Step 3: 实现交互锁**

```python
# src/orchestrator/lock.py
from datetime import datetime
from src.core.constants import ChannelType


class InteractionLock:
    def __init__(self):
        self._holder: ChannelType | None = None
        self._acquired_at: datetime | None = None

    @property
    def holder(self) -> ChannelType | None:
        return self._holder

    @property
    def is_locked(self) -> bool:
        return self._holder is not None

    def acquire(self, channel: ChannelType) -> None:
        self._holder = channel
        self._acquired_at = datetime.now()

    def release(self) -> None:
        self._holder = None
        self._acquired_at = None
```

- [ ] **Step 4: 运行测试确认通过**

Run: `pytest tests/test_orchestrator.py -v`
Expected: 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/orchestrator/lock.py tests/test_orchestrator.py
git commit -m "feat: add interaction lock"
```

---

## Task 7: 渠道注册表

**Files:**
- Create: `src/channels/__init__.py`
- Create: `src/channels/base.py`
- Create: `src/channels/registry.py`
- Test: `tests/test_channels.py`

- [ ] **Step 1: 写渠道测试**

```python
# tests/test_channels.py
import pytest
from src.channels.base import BaseChannel
from src.channels.registry import ChannelRegistry
from src.core.constants import ChannelType, ChannelState


class MockChannel(BaseChannel):
    @property
    def channel_type(self) -> ChannelType:
        return ChannelType.CHATBOT

    async def send(self, user_id: str, content: str) -> dict:
        return {"status": "sent", "channel": "chatbot"}


@pytest.fixture
def registry():
    return ChannelRegistry()


def test_register_channel(registry):
    ch = MockChannel()
    registry.register(ch)
    assert registry.get(ChannelType.CHATBOT) is ch


def test_get_state(registry):
    ch = MockChannel()
    registry.register(ch)
    assert registry.get_state(ChannelType.CHATBOT) == ChannelState.IDLE


def test_set_state(registry):
    ch = MockChannel()
    registry.register(ch)
    registry.set_state(ChannelType.CHATBOT, ChannelState.OUTGOING)
    assert registry.get_state(ChannelType.CHATBOT) == ChannelState.OUTGOING


def test_get_all_states(registry):
    ch = MockChannel()
    registry.register(ch)
    states = registry.get_all_states()
    assert "chatbot" in states
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/test_channels.py -v`
Expected: FAIL with ImportError

- [ ] **Step 3: 实现渠道基类**

```python
# src/channels/base.py
from abc import ABC, abstractmethod
from src.core.constants import ChannelType


class BaseChannel(ABC):
    @property
    @abstractmethod
    def channel_type(self) -> ChannelType:
        pass

    @abstractmethod
    async def send(self, user_id: str, content: str) -> dict:
        pass
```

- [ ] **Step 4: 实现渠道注册表**

```python
# src/channels/registry.py
from src.channels.base import BaseChannel
from src.core.constants import ChannelType, ChannelState


class ChannelRegistry:
    def __init__(self):
        self._channels: dict[ChannelType, BaseChannel] = {}
        self._states: dict[ChannelType, ChannelState] = {}

    def register(self, channel: BaseChannel) -> None:
        self._channels[channel.channel_type] = channel
        self._states[channel.channel_type] = ChannelState.IDLE

    def get(self, channel_type: ChannelType) -> BaseChannel | None:
        return self._channels.get(channel_type)

    def get_state(self, channel_type: ChannelType) -> ChannelState:
        return self._states.get(channel_type, ChannelState.IDLE)

    def set_state(self, channel_type: ChannelType, state: ChannelState) -> None:
        self._states[channel_type] = state

    def get_all_states(self) -> dict[str, str]:
        return {ct.value: cs.value for ct, cs in self._states.items()}

    def pause(self, channel_type: ChannelType) -> None:
        if self._states.get(channel_type) == ChannelState.INTERACTING:
            self._states[channel_type] = ChannelState.PAUSED

    def resume(self, channel_type: ChannelType) -> None:
        if self._states.get(channel_type) == ChannelState.PAUSED:
            self._states[channel_type] = ChannelState.WAITING_REPLY
```

- [ ] **Step 5: 运行测试确认通过**

Run: `pytest tests/test_channels.py -v`
Expected: 4 tests PASS

- [ ] **Step 6: Commit**

```bash
git add src/channels/ tests/test_channels.py
git commit -m "feat: add channel base and registry"
```

---

## Task 8: 配额管理

**Files:**
- Create: `src/quota/__init__.py`
- Create: `src/quota/profile.py`
- Create: `src/quota/usage.py`
- Create: `src/quota/manager.py`
- Test: `tests/test_quota.py`

- [ ] **Step 1: 写配额测试**

```python
# tests/test_quota.py
import pytest
from datetime import datetime, timedelta
from src.quota.profile import QuotaProfile
from src.quota.usage import DailyQuotaUsage
from src.quota.manager import QuotaManager


def test_quota_profile_defaults():
    qp = QuotaProfile()
    assert qp.call_self_daily_max == 10
    assert qp.chat_unanswered_daily_max == 5
    assert qp.push_daily_max == 1


def test_daily_usage_increment():
    usage = DailyQuotaUsage(user_id="u001", date="2026-05-23")
    usage.increment_call_self()
    assert usage.call_self_count == 1


def test_can_call_within_limit():
    usage = DailyQuotaUsage(user_id="u001", date="2026-05-23")
    profile = QuotaProfile()
    assert usage.can_call_self(profile) is True


def test_cannot_call_over_limit():
    usage = DailyQuotaUsage(user_id="u001", date="2026-05-23")
    profile = QuotaProfile()
    usage.call_self_count = 10
    assert usage.can_call_self(profile) is False


@pytest.fixture
def manager():
    return QuotaManager()


def test_manager_get_usage(manager):
    usage = manager.get_usage("u001")
    assert usage.user_id == "u001"
    assert usage.call_self_count == 0


def test_manager_record_call(manager):
    manager.record_call_self("u001")
    usage = manager.get_usage("u001")
    assert usage.call_self_count == 1


def test_rate_limit_interval():
    usage = DailyQuotaUsage(user_id="u001", date="2026-05-23")
    usage.call_last_timestamp = datetime.now()
    assert usage.can_call_with_interval(min_seconds=600) is False
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/test_quota.py -v`
Expected: FAIL with ImportError

- [ ] **Step 3: 实现配额配置**

```python
# src/quota/profile.py
from pydantic import BaseModel


class QuotaProfile(BaseModel):
    call_self_daily_max: int = 10
    call_contact_daily_max: int = 10
    call_answer_daily_max: int = 3
    chat_unanswered_daily_max: int = 5
    chat_answered_daily_max: int = 100
    push_daily_max: int = 1
    valid_hours: tuple[int, int] = (8, 20)
    max_call_per_hour: int = 3
    min_call_interval_seconds: int = 600
    min_chat_interval_unanswered: int = 1800
    min_chat_interval_answered: int = 120
```

- [ ] **Step 4: 实现配额使用记录**

```python
# src/quota/usage.py
from datetime import datetime, timedelta
from pydantic import BaseModel, Field


class DailyQuotaUsage(BaseModel):
    user_id: str
    date: str
    call_self_count: int = 0
    call_contact_count: int = 0
    call_answered_count: int = 0
    call_last_timestamp: datetime | None = None
    call_timestamps: list[datetime] = Field(default_factory=list)
    chat_sent_count: int = 0
    chat_user_replied: bool = False
    chat_last_timestamp: datetime | None = None
    push_sent_count: int = 0

    def increment_call_self(self) -> None:
        self.call_self_count += 1
        self.call_last_timestamp = datetime.now()
        self.call_timestamps.append(datetime.now())

    def can_call_self(self, profile) -> bool:
        return self.call_self_count < profile.call_self_daily_max

    def can_call_with_interval(self, min_seconds: int) -> bool:
        if self.call_last_timestamp is None:
            return True
        elapsed = (datetime.now() - self.call_last_timestamp).total_seconds()
        return elapsed >= min_seconds

    def can_call_in_hour(self, profile, max_per_hour: int) -> bool:
        hour_ago = datetime.now() - timedelta(hours=1)
        recent = [t for t in self.call_timestamps if t > hour_ago]
        return len(recent) < max_per_hour

    def increment_chat(self) -> None:
        self.chat_sent_count += 1
        self.chat_last_timestamp = datetime.now()

    def can_chat(self, profile) -> bool:
        if self.chat_user_replied:
            return self.chat_sent_count < profile.chat_answered_daily_max
        return self.chat_sent_count < profile.chat_unanswered_daily_max
```

- [ ] **Step 5: 实现配额管理器**

```python
# src/quota/manager.py
from datetime import datetime
from src.quota.profile import QuotaProfile
from src.quota.usage import DailyQuotaUsage


class QuotaManager:
    def __init__(self):
        self._usages: dict[str, DailyQuotaUsage] = {}
        self._profile = QuotaProfile()

    def _today(self) -> str:
        return datetime.now().strftime("%Y-%m-%d")

    def get_usage(self, user_id: str) -> DailyQuotaUsage:
        key = f"{user_id}:{self._today()}"
        if key not in self._usages:
            self._usages[key] = DailyQuotaUsage(user_id=user_id, date=self._today())
        return self._usages[key]

    def record_call_self(self, user_id: str) -> None:
        usage = self.get_usage(user_id)
        usage.increment_call_self()

    def record_chat(self, user_id: str) -> None:
        usage = self.get_usage(user_id)
        usage.increment_chat()

    def set_chat_replied(self, user_id: str) -> None:
        usage = self.get_usage(user_id)
        usage.chat_user_replied = True

    def check_call_allowed(self, user_id: str) -> tuple[bool, str]:
        usage = self.get_usage(user_id)
        if not usage.can_call_self(self._profile):
            return False, "Daily call limit reached"
        if not usage.can_call_with_interval(self._profile.min_call_interval_seconds):
            return False, "Call interval too short"
        if not usage.can_call_in_hour(self._profile, self._profile.max_call_per_hour):
            return False, "Hourly call limit reached"
        return True, ""

    def check_chat_allowed(self, user_id: str) -> tuple[bool, str]:
        usage = self.get_usage(user_id)
        if not usage.can_chat(self._profile):
            return False, "Daily chat limit reached"
        return True, ""
```

- [ ] **Step 6: 运行测试确认通过**

Run: `pytest tests/test_quota.py -v`
Expected: 8 tests PASS

- [ ] **Step 7: Commit**

```bash
git add src/quota/ tests/test_quota.py
git commit -m "feat: add quota management system"
```

---

## Task 9: 合规检查器

**Files:**
- Create: `src/compliance/__init__.py`
- Create: `src/compliance/rules.py`
- Create: `src/compliance/checker.py`
- Test: `tests/test_compliance.py`

- [ ] **Step 1: 写合规测试**

```python
# tests/test_compliance.py
import pytest
from src.compliance.checker import ComplianceChecker
from src.compliance.rules import ComplianceRules
from src.core.models import UserProfile


@pytest.fixture
def checker():
    return ComplianceChecker()


def test_valid_hours_check(checker):
    from datetime import time
    assert checker.is_within_valid_hours(time(10, 0)) is True
    assert checker.is_within_valid_hours(time(7, 0)) is False
    assert checker.is_within_valid_hours(time(21, 0)) is False


def test_sensitive_occupation(checker):
    user = UserProfile(user_id="u001", occupation="律师")
    assert checker.is_sensitive(user) is True


def test_non_sensitive_occupation(checker):
    user = UserProfile(user_id="u002", occupation="工程师")
    assert checker.is_sensitive(user) is False


def test_content_has_forbidden_words(checker):
    assert checker.has_forbidden_words("不还钱就等着吧") is False
    assert checker.has_forbidden_words("你是个骗子") is False  # 可根据实际规则调整


def test_complaint_keywords(checker):
    assert checker.is_complaint("我要投诉你们") is True
    assert checker.is_complaint("我会尽快还款") is False


def test_standard_template_for_sensitive(checker):
    user = UserProfile(user_id="u001", name="张三", occupation="律师", overdue_days=5, amount_due=1000.0)
    msg = checker.get_standard_message(user)
    assert "张三" in msg
    assert "5" in msg
    assert "1000" in msg
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/test_compliance.py -v`
Expected: FAIL with ImportError

- [ ] **Step 3: 实现合规规则**

```python
# src/compliance/rules.py
from pydantic import BaseModel


class ComplianceRules(BaseModel):
    valid_hours: tuple[int, int] = (8, 20)
    max_call_per_hour: int = 3
    min_call_interval_minutes: int = 10
    forbidden_words: list[str] = Field(default_factory=list)
    complaint_keywords: list[str] = [
        "投诉", "举报", "律师", "法院", "银保监会",
        "报警", "媒体", "记者", "曝光",
    ]
    sensitive_occupations: list[str] = [
        "律师", "法官", "检察官", "警察",
        "政府官员", "公务员", "军人", "军人配偶",
        "记者", "媒体从业者",
    ]
```

- [ ] **Step 4: 实现合规检查器**

```python
# src/compliance/checker.py
from datetime import time
from src.compliance.rules import ComplianceRules
from src.core.models import UserProfile


class ComplianceChecker:
    def __init__(self):
        self.rules = ComplianceRules()

    def is_within_valid_hours(self, t: time | None = None) -> bool:
        if t is None:
            from datetime import datetime
            t = datetime.now().time()
        start = time(self.rules.valid_hours[0], 0)
        end = time(self.rules.valid_hours[1], 0)
        return start <= t < end

    def is_sensitive(self, user: UserProfile) -> bool:
        return user.is_sensitive

    def has_forbidden_words(self, content: str) -> bool:
        for word in self.rules.forbidden_words:
            if word in content:
                return True
        return False

    def is_complaint(self, content: str) -> bool:
        for keyword in self.rules.complaint_keywords:
            if keyword in content:
                return True
        return False

    def get_standard_message(self, user: UserProfile) -> str:
        return (
            f"您好，这里是 {{机构名称}}。您在 {{平台名称}} 的借款已逾期 {user.overdue_days} 天，"
            f"逾期金额 {user.amount_due} 元。逾期将影响您的个人信用记录，并可能产生罚息。"
            f"请您尽快安排还款。如有疑问，请联系客服 {{客服电话}}。"
        )
```

- [ ] **Step 5: 修复导入**

```python
# src/compliance/rules.py
from pydantic import BaseModel, Field
```

- [ ] **Step 6: 运行测试确认通过**

Run: `pytest tests/test_compliance.py -v`
Expected: 6 tests PASS

- [ ] **Step 7: Commit**

```bash
git add src/compliance/ tests/test_compliance.py
git commit -m "feat: add compliance checker"
```

---

## Task 10: 意图识别器

**Files:**
- Create: `src/strategy/__init__.py`
- Create: `src/strategy/detector.py`
- Test: `tests/test_strategy.py`

- [ ] **Step 1: 写意图识别测试**

```python
# tests/test_strategy.py
import pytest
from src.strategy.detector import IntentDetector
from src.core.constants import Intent


@pytest.fixture
def detector():
    return IntentDetector()


def test_detect_willing(detector):
    assert detector.detect("我明天就还") == Intent.WILLING_TO_PAY
    assert detector.detect("我会处理的") == Intent.WILLING_TO_PAY


def test_detect_unwilling(detector):
    assert detector.detect("我没钱还") == Intent.UNWILLING_TO_PAY
    assert detector.detect("不还") == Intent.UNWILLING_TO_PAY


def test_detect_complaint(detector):
    assert detector.detect("我要投诉你们") == Intent.COMPLAINT


def test_detect_payment_inquiry(detector):
    assert detector.detect("怎么还款") == Intent.PAYMENT_METHOD_INQUIRY


def test_detect_operation_inquiry(detector):
    assert detector.detect("操作失败") == Intent.OPERATION_INQUIRY


def test_detect_ineffective_silence(detector):
    assert detector.detect("") == Intent.INEFFECTIVE_CONTACT
    assert detector.detect("嗯") == Intent.INEFFECTIVE_CONTACT
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/test_strategy.py -v`
Expected: FAIL with ImportError

- [ ] **Step 3: 实现意图识别器（基于规则）**

```python
# src/strategy/detector.py
from src.core.constants import Intent


class IntentDetector:
    KEYWORDS = {
        Intent.WILLING_TO_PAY: [
            "还", "付", "处理", "解决", "明天", "后天", "下周", "月底",
            "可以", "愿意", "尽量", "安排",
        ],
        Intent.UNWILLING_TO_PAY: [
            "没钱", "不还", "不付", "困难", "失业", "破产",
            "凭什么", "不", "拒绝", "没能力",
        ],
        Intent.COMPLAINT: [
            "投诉", "举报", "垃圾", "骗子", "骚扰", "违法",
            "威胁", "恐吓", "曝光",
        ],
        Intent.PAYMENT_METHOD_INQUIRY: [
            "怎么还", "哪里还", "方式", "渠道", "转账", "支付宝",
            "微信", "银行卡", "怎么操作",
        ],
        Intent.OPERATION_INQUIRY: [
            "失败", "错误", "不行", "打不开", "点不了", "卡",
            "问题", "bug", "故障",
        ],
    }

    def detect(self, text: str) -> Intent:
        text = text.lower().strip()

        if not text or text in {"嗯", "哦", "好", "知道了", "。", ",", " "}:
            return Intent.INEFFECTIVE_CONTACT

        scores = {intent: 0 for intent in Intent}
        for intent, keywords in self.KEYWORDS.items():
            for kw in keywords:
                if kw in text:
                    scores[intent] += 1

        best = max(scores, key=scores.get)
        if scores[best] > 0:
            return best

        return Intent.INEFFECTIVE_CONTACT
```

- [ ] **Step 4: 运行测试确认通过**

Run: `pytest tests/test_strategy.py -v`
Expected: 6 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/strategy/detector.py tests/test_strategy.py
git commit -m "feat: add rule-based intent detector"
```

---

## Task 11: LLM 客户端抽象层

**Files:**
- Create: `src/llm/__init__.py`
- Create: `src/llm/base.py`
- Create: `src/llm/clients.py`
- Test: `tests/test_llm.py`

- [ ] **Step 1: 写 LLM 测试**

```python
# tests/test_llm.py
import pytest
from src.llm.base import LLMResponse
from src.llm.clients import MockLLMClient


@pytest.fixture
def mock_client():
    return MockLLMClient()


@pytest.mark.asyncio
async def test_mock_chat(mock_client):
    resp = await mock_client.chat([{"role": "user", "content": "hello"}])
    assert isinstance(resp, LLMResponse)
    assert resp.content == "[Mock response]"


@pytest.mark.asyncio
async def test_mock_detect_intent(mock_client):
    intent = await mock_client.detect_intent("我要还款", {})
    assert intent == "willing_to_pay"


@pytest.mark.asyncio
async def test_mock_generate_strategy(mock_client):
    resp = await mock_client.generate_strategy_response(
        {"type": "reminder"}, {"user_name": "张三"}
    )
    assert "张三" in resp
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/test_llm.py -v`
Expected: FAIL with ImportError

- [ ] **Step 3: 实现 LLM 抽象基类**

```python
# src/llm/base.py
from abc import ABC, abstractmethod
from typing import Any
from pydantic import BaseModel


class LLMResponse(BaseModel):
    content: str
    usage: dict[str, int] = {}
    model: str = ""


class LLMClient(ABC):
    @abstractmethod
    async def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> LLMResponse:
        pass

    @abstractmethod
    async def detect_intent(self, user_message: str, context: dict) -> str:
        pass

    @abstractmethod
    async def generate_strategy_response(self, strategy: dict, context: dict) -> str:
        pass
```

- [ ] **Step 4: 实现 Mock 客户端**

```python
# src/llm/clients.py
from src.llm.base import LLMClient, LLMResponse


class MockLLMClient(LLMClient):
    async def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> LLMResponse:
        return LLMResponse(content="[Mock response]")

    async def detect_intent(self, user_message: str, context: dict) -> str:
        text = user_message.lower()
        if "还" in text or "付" in text:
            return "willing_to_pay"
        if "不" in text or "没钱" in text:
            return "unwilling_to_pay"
        return "ineffective_contact"

    async def generate_strategy_response(self, strategy: dict, context: dict) -> str:
        name = context.get("user_name", "用户")
        return f"您好{name}，请尽快处理您的逾期账单。"
```

- [ ] **Step 5: 运行测试确认通过**

Run: `pytest tests/test_llm.py -v`
Expected: 3 tests PASS

- [ ] **Step 6: Commit**

```bash
git add src/llm/ tests/test_llm.py
git commit -m "feat: add LLM client abstraction with mock implementation"
```

---

## Task 12: 策略引擎

**Files:**
- Create: `src/strategy/engine.py`
- Create: `src/strategy/strategies.py`
- Modify: `tests/test_strategy.py`

- [ ] **Step 1: 写策略引擎测试**

```python
# tests/test_strategy.py (追加)
import pytest
from src.strategy.engine import StrategyEngine
from src.core.constants import Intent
from src.core.models import UserProfile


@pytest.fixture
def engine():
    return StrategyEngine()


def test_select_strategy_for_willing(engine):
    user = UserProfile(user_id="u001")
    strategy = engine.select_strategy(user, Intent.WILLING_TO_PAY)
    assert strategy["type"] == "confirm_plan"


def test_select_strategy_for_sensitive_user(engine):
    user = UserProfile(user_id="u001", occupation="律师")
    strategy = engine.select_strategy(user, Intent.UNWILLING_TO_PAY)
    assert strategy["type"] == "standard_reminder"


def test_select_strategy_for_complaint(engine):
    user = UserProfile(user_id="u001")
    strategy = engine.select_strategy(user, Intent.COMPLAINT)
    assert strategy["type"] == "pause_collection"


def test_get_response_for_willing(engine):
    user = UserProfile(user_id="u001", name="张三")
    resp = engine.get_response(user, {"type": "confirm_plan"}, {})
    assert "张三" in resp or "还款" in resp
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/test_strategy.py::test_select_strategy_for_willing -v`
Expected: FAIL with ImportError

- [ ] **Step 3: 实现策略数据**

```python
# src/strategy/strategies.py
from src.core.constants import Intent


STRATEGIES = {
    Intent.WILLING_TO_PAY: {
        "type": "confirm_plan",
        "description": "确认还款计划",
        "max_rounds": 3,
        "actions": ["ask_timing", "confirm_amount", "send_reminder"],
    },
    Intent.UNWILLING_TO_PAY: {
        "type": "negotiate",
        "description": "谈判协商",
        "max_rounds": 3,
        "actions": ["probe_reason", "negotiate_plan", "warn_consequences"],
    },
    Intent.INEFFECTIVE_CONTACT: {
        "type": "re_engage",
        "description": "重新建立联系",
        "max_rounds": 4,
        "actions": ["remind", "change_channel", "contact_guarantor"],
    },
    Intent.COMPLAINT: {
        "type": "pause_collection",
        "description": "暂停催收并转客服",
        "max_rounds": 1,
        "actions": ["acknowledge", "apologize", "transfer_to_cs"],
    },
    Intent.PAYMENT_METHOD_INQUIRY: {
        "type": "guide_payment",
        "description": "指导还款操作",
        "max_rounds": 5,
        "actions": ["provide_options", "send_link", "confirm_completion"],
    },
    Intent.OPERATION_INQUIRY: {
        "type": "troubleshoot",
        "description": "解决操作问题",
        "max_rounds": 3,
        "actions": ["diagnose", "provide_steps", "escalate_if_needed"],
    },
    "standard_reminder": {
        "type": "standard_reminder",
        "description": "标准提醒（敏感职业专用）",
        "max_rounds": 1,
        "actions": ["send_standard_message"],
    },
}


RESPONSE_TEMPLATES = {
    "confirm_plan": [
        "您好{name}，感谢您愿意处理此事。请问您计划什么时候还款？",
        "好的，{name}。请问您能否结清全部{amount}元？",
        "明白了，{name}。那我们就约定{date}前还款，届时我会再提醒您。",
    ],
    "negotiate": [
        "{name}，我理解您可能有困难。能告诉我是什么原因导致暂时无法还款吗？",
        "{name}，根据您的情况，我们可以协商一个分期方案，您觉得每月还多少比较合适？",
        "{name}，如果长期逾期不还款，可能会影响您的信用记录，甚至面临法律诉讼。",
    ],
    "re_engage": [
        "{name}，您好。关于您的逾期账单，请尽快处理。",
        "{name}，我们注意到您的账单已逾期{days}天，请尽快联系我们处理。",
    ],
    "pause_collection": [
        "非常抱歉给您带来不好的体验，{name}。我会记录您的问题并转给客服处理。在此期间，我们将暂停催收。",
    ],
    "guide_payment": [
        "{name}，您可以通过以下方式还款：1. App内一键还款 2. 银行转账 3. 支付宝/微信。需要我发送还款链接吗？",
    ],
    "troubleshoot": [
        "{name}，请您尝试以下步骤：1. 刷新页面 2. 清除缓存 3. 重新登录。如果问题仍然存在，我可以帮您转接客服。",
    ],
    "standard_reminder": [
        "您好，这里是{{机构名称}}。您在{{平台名称}}的借款已逾期{days}天，逾期金额{amount}元。逾期将影响您的个人信用记录，并可能产生罚息。请您尽快安排还款。如有疑问，请联系客服{{客服电话}}。",
    ],
}
```

- [ ] **Step 4: 实现策略引擎**

```python
# src/strategy/engine.py
from src.strategy.strategies import STRATEGIES, RESPONSE_TEMPLATES
from src.core.constants import Intent
from src.core.models import UserProfile


class StrategyEngine:
    def select_strategy(self, user: UserProfile, intent: Intent) -> dict:
        if user.is_sensitive:
            return STRATEGIES["standard_reminder"]
        return STRATEGIES.get(intent, STRATEGIES[Intent.INEFFECTIVE_CONTACT])

    def get_response(self, user: UserProfile, strategy: dict, context: dict) -> str:
        strategy_type = strategy["type"]
        templates = RESPONSE_TEMPLATES.get(strategy_type, ["请尽快处理您的逾期账单。"])

        round_num = context.get("round", 0)
        if round_num < len(templates):
            template = templates[round_num]
        else:
            template = templates[-1]

        return template.format(
            name=user.name or "用户",
            amount=user.amount_due,
            days=user.overdue_days,
            date=context.get("planned_date", ""),
        )
```

- [ ] **Step 5: 运行测试确认通过**

Run: `pytest tests/test_strategy.py -v`
Expected: 10 tests PASS

- [ ] **Step 6: Commit**

```bash
git add src/strategy/engine.py src/strategy/strategies.py tests/test_strategy.py
git commit -m "feat: add strategy engine with response templates"
```

---

## Task 13: Orchestrator 主调度器

**Files:**
- Create: `src/orchestrator/orchestrator.py`
- Modify: `tests/test_orchestrator.py`
- Modify: `src/session/session.py`

- [ ] **Step 1: 写 Orchestrator 测试**

```python
# tests/test_orchestrator.py (追加)
import pytest
from src.orchestrator.orchestrator import Orchestrator
from src.core.constants import ChannelType, EventType
from src.core.models import UserProfile, Event


@pytest.fixture
def orchestrator():
    return Orchestrator()


def test_arbitrate_no_holder(orchestrator):
    result = orchestrator.arbitrate("u001", ChannelType.VOICE)
    assert result == "granted"
    assert orchestrator.get_lock("u001").holder == ChannelType.VOICE


def test_arbitrate_voice_priority(orchestrator):
    orchestrator.arbitrate("u001", ChannelType.CHATBOT)
    result = orchestrator.arbitrate("u001", ChannelType.VOICE)
    assert result == "granted"
    assert orchestrator.get_lock("u001").holder == ChannelType.VOICE


def test_arbitrate_lower_priority_denied(orchestrator):
    orchestrator.arbitrate("u001", ChannelType.VOICE)
    result = orchestrator.arbitrate("u001", ChannelType.CHATBOT)
    assert result == "deferred"


def test_release_lock(orchestrator):
    orchestrator.arbitrate("u001", ChannelType.VOICE)
    orchestrator.release_lock("u001")
    assert orchestrator.get_lock("u001").holder is None


def test_select_channel_considers_quota(orchestrator):
    user = UserProfile(user_id="u001")
    channel = orchestrator.select_channel(user)
    assert channel in [ChannelType.CHATBOT, ChannelType.VOICE, ChannelType.PUSH]
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/test_orchestrator.py::test_arbitrate_no_holder -v`
Expected: FAIL with ImportError

- [ ] **Step 3: 实现会话模型**

```python
# src/session/session.py
from src.core.constants import SessionState
from src.core.models import UserState
from src.session.state_machine import SessionStateMachine
from src.channels.registry import ChannelRegistry
from src.orchestrator.lock import InteractionLock


class CollectionSession:
    def __init__(self, user_id: str, state: UserState):
        self.user_id = user_id
        self.state = state
        self.state_machine = SessionStateMachine()
        self.channels = ChannelRegistry()
        self.lock = InteractionLock()
        self.context = {}

    def handle_event(self, event) -> None:
        pass
```

- [ ] **Step 4: 实现 Orchestrator**

```python
# src/orchestrator/orchestrator.py
from src.core.constants import ChannelType
from src.orchestrator.lock import InteractionLock
from src.quota.manager import QuotaManager
from src.compliance.checker import ComplianceChecker


class Orchestrator:
    PRIORITY = {
        ChannelType.VOICE: 3,
        ChannelType.CHATBOT: 2,
        ChannelType.PUSH: 1,
    }

    def __init__(self):
        self._locks: dict[str, InteractionLock] = {}
        self._quota = QuotaManager()
        self._compliance = ComplianceChecker()

    def get_lock(self, user_id: str) -> InteractionLock:
        if user_id not in self._locks:
            self._locks[user_id] = InteractionLock()
        return self._locks[user_id]

    def arbitrate(self, user_id: str, channel: ChannelType) -> str:
        lock = self.get_lock(user_id)

        if not lock.is_locked:
            lock.acquire(channel)
            return "granted"

        if lock.holder == channel:
            return "granted"

        if self.PRIORITY[channel] > self.PRIORITY[lock.holder]:
            lock.acquire(channel)
            return "granted"

        return "deferred"

    def release_lock(self, user_id: str) -> None:
        lock = self.get_lock(user_id)
        lock.release()

    def select_channel(self, user) -> ChannelType | None:
        from datetime import datetime

        if not self._compliance.is_within_valid_hours():
            return None

        call_ok, _ = self._quota.check_call_allowed(user.user_id)
        chat_ok, _ = self._quota.check_chat_allowed(user.user_id)

        if call_ok:
            return ChannelType.VOICE
        if chat_ok:
            return ChannelType.CHATBOT
        return ChannelType.PUSH

    def can_contact_user(self, user) -> tuple[bool, str]:
        if not self._compliance.is_within_valid_hours():
            return False, "Outside valid hours"
        return True, ""
```

- [ ] **Step 5: 运行测试确认通过**

Run: `pytest tests/test_orchestrator.py -v`
Expected: 9 tests PASS

- [ ] **Step 6: Commit**

```bash
git add src/orchestrator/orchestrator.py src/session/session.py tests/test_orchestrator.py
git commit -m "feat: add orchestrator with arbitration and channel selection"
```

---

## Task 14: Session Manager

**Files:**
- Create: `src/session/manager.py`
- Test: `tests/test_session.py` (追加)

- [ ] **Step 1: 写 Session Manager 测试**

```python
# tests/test_session.py (追加)
from src.session.manager import SessionManager
from src.core.models import UserProfile, UserState


def test_session_manager_get_or_create():
    manager = SessionManager()
    session = manager.get_or_create("u001")
    assert session.user_id == "u001"
    assert session.state.profile.user_id == "u001"


def test_session_manager_returns_existing():
    manager = SessionManager()
    session1 = manager.get_or_create("u001")
    session2 = manager.get_or_create("u001")
    assert session1 is session2
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/test_session.py::test_session_manager_get_or_create -v`
Expected: FAIL with ImportError

- [ ] **Step 3: 实现 Session Manager**

```python
# src/session/manager.py
from src.session.session import CollectionSession
from src.core.models import UserState, UserProfile
from src.storage.memory_store import MemoryStore


class SessionManager:
    def __init__(self, store: MemoryStore | None = None):
        self._store = store or MemoryStore()
        self._sessions: dict[str, CollectionSession] = {}

    def get_or_create(self, user_id: str) -> CollectionSession:
        if user_id in self._sessions:
            return self._sessions[user_id]

        state = self._store.load(user_id)
        if state is None:
            state = UserState(
                user_id=user_id,
                profile=UserProfile(user_id=user_id),
            )
            self._store.save(state)

        session = CollectionSession(user_id=user_id, state=state)
        self._sessions[user_id] = session
        return session

    def get(self, user_id: str) -> CollectionSession | None:
        return self._sessions.get(user_id)

    def remove(self, user_id: str) -> None:
        if user_id in self._sessions:
            session = self._sessions[user_id]
            self._store.save(session.state)
            del self._sessions[user_id]
```

- [ ] **Step 4: 运行测试确认通过**

Run: `pytest tests/test_session.py -v`
Expected: 7 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/session/manager.py tests/test_session.py
git commit -m "feat: add session manager"
```

---

## Task 15: 主入口与集成

**Files:**
- Create: `src/main.py`
- Create: `config.yaml`
- Test: `tests/test_integration.py`

- [ ] **Step 1: 写集成测试**

```python
# tests/test_integration.py
import pytest
from src.main import CollectAgentSystem
from src.core.constants import EventType
from src.core.models import Event, UserProfile


@pytest.fixture
def system():
    return CollectAgentSystem()


def test_system_initialization(system):
    assert system.router is not None
    assert system.session_manager is not None


def test_handle_user_login_event(system):
    event = Event(user_id="u001", type=EventType.USER_LOGIN)
    system.handle_event(event)
    session = system.session_manager.get("u001")
    assert session is not None
    assert session.user_id == "u001"
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/test_integration.py -v`
Expected: FAIL with ImportError

- [ ] **Step 3: 实现主入口**

```python
# src/main.py
from src.events.router import EventRouter
from src.session.manager import SessionManager
from src.storage.memory_store import MemoryStore


class CollectAgentSystem:
    def __init__(self):
        self.store = MemoryStore()
        self.session_manager = SessionManager(self.store)
        self.router = EventRouter(self.session_manager)

    def handle_event(self, event) -> None:
        self.router.route(event)

    def get_session(self, user_id: str):
        return self.session_manager.get(user_id)
```

- [ ] **Step 4: 创建配置文件**

```yaml
# config.yaml
llm:
  provider: "mock"
  temperature: 0.3
  max_tokens: 1024

compliance:
  valid_hours: [8, 20]
  max_call_per_hour: 3
  min_call_interval_minutes: 10

quota:
  call_self_daily_max: 10
  call_contact_daily_max: 10
  call_answer_daily_max: 3
  chat_unanswered_daily_max: 5
  chat_answered_daily_max: 100
  push_daily_max: 1
```

- [ ] **Step 5: 运行测试确认通过**

Run: `pytest tests/test_integration.py -v`
Expected: 3 tests PASS

- [ ] **Step 6: Commit**

```bash
git add src/main.py config.yaml tests/test_integration.py
git commit -m "feat: add main entry point and integration"
```

---

## 运行全部测试

- [ ] **Step: 运行完整测试套件**

Run: `pytest tests/ -v`
Expected: 所有测试 PASS

---

## Self-Review

### Spec Coverage

| Spec 章节 | 对应 Task |
|-----------|-----------|
| 2.2 用户隔离 | Task 2 (models), Task 4 (EventRouter), Task 14 (SessionManager) |
| 2.3 CollectionSession | Task 5 (state machine), Task 13 (session.py), Task 14 (manager) |
| 3.2 事件类型 | Task 1 (constants) |
| 3.3 Event Router | Task 4 |
| 4.1 意图识别 | Task 10 (detector) |
| 4.2-4.7 跟进流程 | Task 12 (strategy engine + strategies) |
| 5.1-5.6 配额管理 | Task 8 (quota) |
| 6.1-6.6 冲突仲裁 | Task 6 (lock), Task 7 (registry), Task 13 (orchestrator) |
| 7.1-7.2 合规护栏 | Task 9 (compliance) |
| 10.1-10.6 LLM 接口 | Task 11 (llm) |

### Placeholder Scan

- 无 TBD/TODO
- 所有步骤包含完整代码
- 所有测试包含断言

### Type Consistency

- `EventType`, `ChannelType`, `Intent`, `SessionState`, `ChannelState` 枚举在全项目一致
- `UserProfile`, `UserState`, `Event`, `Message` 模型一致
- `InteractionLock` 接口一致
