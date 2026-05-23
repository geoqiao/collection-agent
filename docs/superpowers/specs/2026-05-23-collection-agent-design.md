# 催收员 Agent 系统设计文档

**日期**: 2026-05-23  
**版本**: v1.0  
**状态**: 设计评审中

---

## 1. 概述

### 1.1 目标

构建一个智能化的催收员 Agent，能够持续多天对逾期客户进行多轮、多渠道的催收。Agent 根据用户实时状态自主决策催收策略，同时严格遵守合规边界。

### 1.2 核心特性

- **自主决策**: Agent 根据用户状态（逾期天数、还款行为、对话内容）自主选择催收渠道和话术
- **多渠道协调**: 支持 Chatbot（WhatsApp/SMS）、语音电话、App Push 三种渠道，避免冲突
- **多轮跟进**: 针对不同用户意图（愿意还款、拒绝还款、无效沟通等）设计专门的多轮跟进流程
- **合规护栏**: 双层合规检查（调度前 + 输出前），敏感职业特殊处理
- **持久化**: 支持跨天催收，每个用户的状态独立持久化

### 1.3 非目标（初始版本）

- 不实现与外部系统的真实接口（WhatsApp API、电话网关等），使用 Mock/模拟工具
- 不考虑用户主动进线（转客服处理）
- 不考虑复杂的风控模型集成

---

## 2. 整体架构

### 2.1 架构原则

**分层编排（Layered Orchestration）**：

- **Orchestrator（主 Agent）**: 唯一职责是会话生命周期管理——决定"现在该不该催收、用什么渠道、是否冲突"
- **Strategy Engine（策略引擎）**: 根据用户意图和逾期状态，选择跟进策略（谈判、提醒、警告等）
- **Tool Agents**: Chatbot、Voicebot 等，只负责生成具体渠道的内容，不决策

### 2.2 用户隔离机制

**每个用户一个独立的 CollectionSession（Actor）**：

```
Event Sources (Cron / Login / Payment / Silence / Reply ...)
         │
         ▼
    Event Router ───────────────┐
    (按 user_id 路由)            │
         │                      │
    ┌────┴────┐            ┌────┴────┐
    ▼         ▼            ▼         ▼
 Session   Session      Session   Session
 User-A    User-B       User-C    User-D
 (Actor)   (Actor)      (Actor)   (Actor)
    │         │            │         │
    └─────────┴────────────┴─────────┘
                   │
                   ▼
         ┌─────────────────┐
         │  Shared Infra   │
         │  - State Store  │
         │  - LLM Client   │
         │  - Compliance   │
         │  - Metrics      │
         └─────────────────┘
```

**隔离保证**：

- **状态隔离**: 每个用户的逾期天数、对话历史、催收记录独立存储
- **事件隔离**: Event Router 严格按 `user_id` 分发
- **决策隔离**: Orchestrator 每个 Session 独立运行
- **计数隔离**: 所有频次限制在每个用户维度独立计算

### 2.3 CollectionSession 内部结构

```python
class CollectionSession:
    user_id: str
    state_machine: SessionStateMachine      # 当前阶段
    channel_registry: ChannelRegistry       # 活跃渠道状态
    interaction_lock: InteractionLock       # 交互权持有者
    context_window: ContextWindow           # 对话历史
    quota_usage: DailyQuotaUsage            # 当日配额使用
    strategy_engine: StrategyEngine         # 策略引擎实例
    orchestrator: Orchestrator              # 会话调度器
```

---

## 3. 触发机制

### 3.1 混合触发模式

**定时主动触发**：

- 系统定时扫描所有逾期客户
- Agent 自主判断谁需要催收、用什么渠道

**事件触发**：

- 用户登录 App
- 用户还款失败
- 用户回复消息
- 静默超时（10分钟/1小时/1天/3天）

### 3.2 事件类型

```python
class EventType(Enum):
    # 定时触发
    SCHEDULED_OUTREACH = "scheduled_outreach"
    REMINDER_DUE = "reminder_due"
    SILENCE_TIMEOUT = "silence_timeout"

    # 用户行为
    USER_LOGIN = "user_login"
    USER_PAYMENT_ATTEMPT = "user_payment_attempt"
    USER_PAYMENT_SUCCESS = "user_payment_success"
    USER_PAYMENT_FAIL = "user_payment_fail"

    # 渠道反馈
    CALL_CONNECTED = "call_connected"
    CALL_DISCONNECTED = "call_disconnected"
    CALL_NO_ANSWER = "call_no_answer"
    MESSAGE_SENT = "message_sent"
    MESSAGE_DELIVERED = "message_delivered"
    USER_REPLIED = "user_replied"

    # 系统
    QUOTA_EXHAUSTED = "quota_exhausted"
    COMPLIANCE_VIOLATION = "compliance_violation"
```

### 3.3 Event Router

```python
class EventRouter:
    def route(self, event: Event):
        session = self.session_manager.get_or_create(event.user_id)
        session.handle_event(event)
```

---

## 4. 意图分类与跟进流程

### 4.1 意图识别

每个用户消息或事件进入 Session 后，首先经过 **Intent Detector**。

| 意图 | 触发条件 |
|------|---------|
| `WILLING_TO_PAY` | 用户明确表示愿意还款 |
| `UNWILLING_TO_PAY` | 用户明确表示拒绝或推脱 |
| `INEFFECTIVE_CONTACT` | 静默超时、敷衍回复、渠道失败 |
| `COMPLAINT` | 用户表达不满、威胁投诉 |
| `PAYMENT_METHOD_INQUIRY` | 询问还款方式 |
| `OPERATION_INQUIRY` | 操作失败、技术问题 |

### 4.2 愿意还款 (WILLING_TO_PAY)

```
[WILLING_DETECTED]
      │
      ▼
[CONFIRM_PLAN] ──用户给出具体计划？──┬──YES──► [PLAN_CONFIRMED]
      │                              │
      │                              └──NO──► [PROBE_TIMING]
      │                                           │
      │◄────────用户给出时间───────────────────────┘
      │
      ▼
[PLAN_CONFIRMED] ──到约定时间？──┬──YES──► [CHECK_PAYMENT]
      │                          │
      └──NO──► [REMIND_24H] ────┘
                    │
                    ▼
          [CHECK_PAYMENT] ──已还款？──┬──YES──► [CLOSE_SUCCESS]
                    │                 │
                    └──NO──► [FOLLOW_UP] ──► 转 UNWILLING_TO_PAY 或 INEFFECTIVE_CONTACT
```

**规则**：

- 必须拿到具体还款承诺（时间+金额）
- 承诺前发送还款链接/指引
- 到期前24小时提醒一次
- 到期未还，重新评估意图

### 4.3 不愿意还款 (UNWILLING_TO_PAY)

```
[UNWILLING_DETECTED]
      │
      ▼
[PROBE_REASON] ──用户给出原因？──┬──YES──► [REASON_CATEGORY]
      │                          │
      └──NO──► [ASK_OPENLY] ────┘
                    │
                    ▼
          [REASON_CATEGORY]
                    │
      ┌─────────────┼─────────────┐
      ▼             ▼             ▼
  [FINANCIAL]   [DISPUTED]    [REFUSAL]
  经济困难       有争议/质疑     恶意拖欠
      │             │             │
      ▼             ▼             ▼
[NEGOTIATE]   [EXPLAIN_CLARIFY] [WARN_SERIOUS]
  协商分期       解释账单         告知后果
      │             │             │
      └─────────────┴─────────────┘
                    │
                    ▼
          [EVALUATE_RESPONSE]
                    │
      ┌─────────────┼─────────────┐
      ▼             ▼             ▼
  [AGREED]     [STALLING]    [STILL_REFUSE]
     │              │              │
     ▼              ▼              ▼
  转 WILLING    继续谈判(最多3轮)  [ESCALATE]
                              升级/联系人/法律告知
```

**规则**：

- 谈判最多 **3 轮**
- 每轮必须尝试引导到还款承诺
- 恶意拖欠直接走警告流程

### 4.4 无效沟通 (INEFFECTIVE_CONTACT)

```
[INEFFECTIVE_DETECTED]
      │
      ▼
[IDENTIFY_TYPE] ──静默？──┬──YES──► [SILENCE_HANDLING]
      │                    │
      ├──渠道失败？──► [CHANNEL_RETRY]
      │
      └──敷衍？──► [RE_ENGAGE]
                        │
      ┌─────────────────┼─────────────────┐
      ▼                 ▼                 ▼
[SILENCE_HANDLING] [CHANNEL_RETRY]    [RE_ENGAGE]
      │                 │                 │
      ▼                 ▼                 ▼
  10分钟：提醒      换渠道重试(最多2次)   换个问题/角度
  1小时：再次提醒        │              重新建立对话
  1天：换渠道          ▼
  3天：联系人      [ALL_CHANNELS_FAIL]
                      │
                      ▼
              [CONTACT_GUARANTOR]
              （仅在本人所有渠道失败且符合规则时）
```

**规则**：

- 静默分层：10分钟 → 1小时 → 1天 → 3天
- 渠道失败最多重试2次
- 联系人触发：所有本人渠道失败 + 逾期超过阈值

### 4.5 投诉 (COMPLAINT)

```
[COMPLAINT_DETECTED]
      │
      ▼
[ACKNOWLEDGE] ──情绪激烈？──┬──YES──► [DE_ESCALATE]
      │                      │
      └──NO──► [CLARIFY_ISSUE]
                    │
                    ▼
          [DE_ESCALATE] / [CLARIFY_ISSUE]
                    │
                    ▼
          [DETERMINE_SEVERITY]
                    │
      ┌─────────────┴─────────────┐
      ▼                           ▼
  [MILD]                       [SERIOUS]
  一般不满                      威胁投诉/监管
      │                           │
      ▼                           ▼
  [APOLOGIZE+RESOLVE]      [TRANSFER_TO_CS]
  道歉并尝试解决               立即转客服
      │                           │
      └──► [PAUSE_COLLECTION] ◄───┘
              （暂停催收24-72小时）
                    │
                    ▼
          [RESUME_OR_CLOSE]
```

**规则**：

- 投诉必须**立即暂停催收**
- 激烈投诉直接转客服
- 记录投诉内容

### 4.6 还款方式咨询 (PAYMENT_METHOD_INQUIRY)

```
[INQUIRY_DETECTED]
      │
      ▼
[PROVIDE_OPTIONS]
      │
      ▼
[GUIDE_SELECTION] ──用户选择？──┬──YES──► [SEND_LINK/STEPS]
      │                         │
      └──NO──► [ASK_PREFERENCE]─┘
                    │
                    ▼
          [SEND_LINK/STEPS]
                    │
                    ▼
          [CONFIRM_COMPLETION] ──完成？──┬──YES──► [VERIFY_PAYMENT]
                    │                    │
                    └──NO──► [ASSIST_FURTHER]
                                  │
                                  ▼
                        [OPERATION_INQUIRY 流程]
```

### 4.7 操作问题咨询 (OPERATION_INQUIRY)

```
[OPERATION_DETECTED]
      │
      ▼
[DIAGNOSE_ISSUE]
      │
      ▼
[PROVIDE_STEPS] ──解决？──┬──YES──► [CONFIRM_SUCCESS]
      │                   │
      └──NO──► [ESCALATE_TO_CS]
                  （复杂技术问题转客服）
```

### 4.8 状态转换总图

```
                    ┌─────────────────┐
         ┌─────────►│    IDLE/INIT    │◄────────┐
         │          │  (等待/定时触发) │         │
         │          └────────┬────────┘         │
         │                   │ 事件/定时         │
         │                   ▼                  │
         │          ┌─────────────────┐         │
         │          │  OUTREACH_START │         │
         │          │   (选择渠道)     │         │
         │          └────────┬────────┘         │
         │                   │                  │
         │         ┌─────────┼─────────┐        │
         │         ▼         ▼         ▼        │
         │      [Chat]   [Voice]   [Push]       │
         │         │         │         │         │
         │         └─────────┴─────────┘        │
         │                   │                  │
         │                   ▼                  │
         │          ┌─────────────────┐         │
         └──────────┤ INTENT_DETECTED │         │
                    │   (意图识别)     │         │
                    └────────┬────────┘         │
                             │                  │
           ┌─────────────────┼─────────────────┐
           ▼                 ▼                 ▼
      [WILLING]        [UNWILLING]      [INEFFECTIVE]
           │                 │                 │
           ▼                 ▼                 ▼
      [跟进A]            [跟进B]           [跟进C]
           │                 │                 │
           └─────────────────┴─────────────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │  RESOLVE/CLOSE  │
                    │  或 RETURN_IDLE  │
                    └─────────────────┘
```

**投诉作为中断**：任何状态下检测到 `COMPLAINT`，立即暂停当前流程。

---

## 5. 配额管理与最小间隔机制

### 5.1 配额模型

```python
class QuotaProfile:
    # 电话
    call_self_daily_max: int = 10
    call_contact_daily_max: int = 10
    call_answer_daily_max: int = 3

    # Chatbot/WhatsApp
    chat_unanswered_daily_max: int = 5
    chat_answered_daily_max: int = 100

    # Push
    push_daily_max: int = 1

    # 合规时间
    valid_hours: tuple = (8, 20)
```

### 5.2 滑动窗口限速

| 渠道 | 滑动窗口规则 |
|------|-------------|
| 电话 | 每小时内最多3通；连续两通电话间隔 >= 10分钟 |
| Chatbot | 用户未回复状态下，每条消息间隔 >= 30分钟；用户回复后，每条间隔 >= 2分钟 |
| Push | 每天仅1个，无间隔问题 |

```python
class RateLimitRule:
    window_seconds: int
    max_actions: int
    min_interval_seconds: int
```

### 5.3 配额检查流程

```
Orchestrator 决定: "现在要给 User-A 打电话"
              │
              ▼
    ┌─────────────────────┐
    │  1. 合规时间检查     │──不在 8:00-20:00？──► 拒绝，延迟到下一个合规时间
    └─────────────────────┘
              │
              ▼
    ┌─────────────────────┐
    │  2. 配额检查         │──已达当日上限？──► 拒绝，转其他渠道或暂停
    └─────────────────────┘
              │
              ▼
    ┌─────────────────────┐
    │  3. 间隔检查         │──距离上次同渠道太近？──► 拒绝，计算下次可执行时间
    └─────────────────────┘
              │
              ▼
           允许执行
              │
              ▼
    执行工具调用 ──► 记录用量 ──► 更新配额状态
```

### 5.4 动态配额调整

用户回复 Chatbot 后，配额从 `chat_unanswered_daily_max` 提升到 `chat_answered_daily_max`：

```
状态: USER_UNANSWERED ──► 用户回复 ──► 状态: USER_ANSWERED
     配额: 5条/天                    配额: 100条/天
     间隔: >=30分钟                   间隔: >=2分钟
```

### 5.5 配额耗尽降级策略

| 渠道耗尽 | 降级方案 |
|---------|---------|
| 电话本人 | 尝试 Chatbot → 尝试 Push → 暂停 |
| Chatbot（未回复） | 已发5条无回复 → 换电话 → 或标记静默 |
| Chatbot（已回复） | 极少耗尽（100条），若耗尽暂停 |
| Push | 仅1条，耗尽后无降级 |

### 5.6 配额数据存储

```python
class DailyQuotaUsage:
    user_id: str
    date: str

    call_self_count: int = 0
    call_contact_count: int = 0
    call_answered_count: int = 0
    call_last_timestamp: datetime | None = None

    chat_sent_count: int = 0
    chat_user_replied: bool = False
    chat_last_timestamp: datetime | None = None

    push_sent_count: int = 0
```

---

## 6. Orchestrator 会话冲突仲裁

### 6.1 渠道状态

```python
class ChannelState(Enum):
    IDLE = "idle"
    SCHEDULED = "scheduled"
    OUTGOING = "outgoing"
    INTERACTING = "interacting"
    WAITING_REPLY = "waiting_reply"
    PAUSED = "paused"
    CLOSED = "closed"
```

### 6.2 交互权（Interaction Lock）

```python
class InteractionLock:
    holder: ChannelType | None
    acquired_at: datetime
    context_snapshot: dict
```

**获得交互权条件**：

- 用户接听电话
- 用户回复 Chatbot/WhatsApp 消息
- 用户点击 Push 通知

**释放交互权条件**：

- 电话挂断
- Chatbot 10分钟无新消息
- 用户明确表示"结束对话"

### 6.3 冲突场景决策表

| 场景 | 状态变化 | 仲裁结果 |
|------|---------|---------|
| **S1**: 电话 `OUTGOING`，用户回复 WhatsApp | 电话拨号中，WhatsApp 要变 `INTERACTING` | WhatsApp 获得交互权，电话继续拨号但不转入 `INTERACTING`（如后续接通，抢走交互权） |
| **S2**: WhatsApp `INTERACTING`，电话拨入且用户接听 | WhatsApp 正在交互，电话要变 `INTERACTING` | **电话优先**，WhatsApp 强制变为 `PAUSED` |
| **S3**: 电话 `INTERACTING`，用户回复 WhatsApp | 电话正在交互，WhatsApp 要变 `INTERACTING` | WhatsApp 变为 `PAUSED`，电话保持交互权 |
| **S4**: 电话挂断，WhatsApp 处于 `PAUSED` | 电话释放交互权 | 检查 WhatsApp 是否有未处理消息 → 有则恢复 `INTERACTING`，无则变 `WAITING_REPLY` |
| **S5**: WhatsApp 和 Push 同时 `OUTGOING` | 两者都不涉及交互权 | **允许并行** |
| **S6**: 两个渠道同时满足交互条件 | 同时竞争交互权 | **电话 > Chatbot > Push** 优先级裁决 |

### 6.4 仲裁算法

```python
def arbitrate(session: CollectionSession, channel: ChannelType, event: Event):
    current_holder = session.interaction_lock.holder

    if current_holder is None:
        session.interaction_lock.acquire(channel)
        return GRANTED

    if current_holder == channel:
        return GRANTED

    if PRIORITY[channel] > PRIORITY[current_holder]:
        session.channels[current_holder].pause()
        session.interaction_lock.acquire(channel)
        return GRANTED
    else:
        return DEFERRED

PRIORITY = {
    ChannelType.VOICE: 3,
    ChannelType.CHATBOT: 2,
    ChannelType.PUSH: 1,
}
```

### 6.5 电话挂断后的衔接

```
电话挂断
   │
   ▼
检查 PAUSED 渠道列表
   │
   ├─ WhatsApp 有未读用户消息？
   │   └─ YES → WhatsApp 恢复 INTERACTING
   │            └── 生成回复："抱歉刚才在通话，关于您提到的..."
   │
   ├─ WhatsApp 无未读消息，但处于 WAITING_REPLY？
   │   └─ YES → 保持 WAITING_REPLY
   │
   ├─ 其他渠道有未处理事件？
   │   └─ YES → 按优先级依次恢复评估
   │
   └─ 无 PAUSED 渠道
        └─ Session 回到 IDLE
```

### 6.6 渠道并发规则

| 组合 | 是否允许并发 | 交互权归属 |
|------|------------|-----------|
| 电话 + WhatsApp（均未交互） | 允许 | 无归属 |
| 电话（交互中）+ WhatsApp | 允许，WhatsApp 暂停 | 电话独占 |
| WhatsApp（交互中）+ 电话 | 允许，WhatsApp 暂停 | 电话抢占 |
| Push + 任何渠道 | 允许 | Push 不争夺交互权 |
| 两个电话 | 不允许 | 同一渠道互斥 |

---

## 7. 合规护栏

### 7.1 双层检查

**Layer 1: Orchestrator 调度前**

- 合规时间窗口（8:00-20:00）
- 配额检查（频次上限）
- 联系人规则（本人优先）

**Layer 2: Tool Agent 输出前**

- 内容审核（威胁、侮辱、恐吓语言拦截）
- 敏感信息保护
- 投诉关键词检测（立即转人工）

### 7.2 敏感职业特殊处理

```python
SENSITIVE_OCCUPATIONS = [
    "律师", "法官", "检察官", "警察",
    "政府官员", "公务员", "军人", "军人配偶",
    "记者", "媒体从业者",
]
```

**限制对比**：

| 限制项 | 普通用户 | 敏感职业用户 |
|--------|---------|------------|
| 催收话术 | 自主生成，可谈判 | **仅允许标准话术模板** |
| 谈判/施压 | 允许（3轮限制） | **禁止** |
| 联系联系人 | 本人无法联系时可拨打 | **禁止** |
| 电话频次 | 每天10通 | **每天最多2通** |
| Chatbot 频次 | 未回复5条/回复后100条 | 未回复**2条**/回复后**10条** |
| 内容审核 | 标准审核 | **更严格审核** |

**标准话术模板**：

```
您好，这里是 {机构名称}。您在 {平台名称} 的借款已逾期 {天数} 天，
逾期金额 {金额} 元。逾期将影响您的个人信用记录，并可能产生罚息。
请您尽快安排还款。如有疑问，请联系客服 {客服电话}。
```

**策略引擎拦截**：

```python
def select_strategy(user: UserProfile, intent: Intent) -> Strategy:
    if user.is_sensitive:
        return StandardReminderStrategy()  # 强制标准提醒
    return intent_based_strategy(intent)
```

---

## 8. 状态持久化

### 8.1 持久化范围

```python
class UserState:
    user_id: str
    overdue_days: int
    amount_due: float
    session_state: SessionState
    intent_history: List[IntentRecord]
    channel_states: Dict[ChannelType, ChannelState]
    interaction_lock: InteractionLock | None
    daily_quota: DailyQuotaUsage
    conversation_history: List[Message]
```

### 8.2 持久化时机

- 每次状态转换后
- 每次工具调用前后
- 交互权变更时
- 自然日切换时（配额重置）

---

## 9. 错误处理与边界情况

### 9.1 渠道故障

- 渠道调用失败 → 重试1次 → 换渠道 → 记录失败
- 所有渠道均失败 → 标记为"硬失败"，次日再试

### 9.2 LLM 故障

- LLM 调用超时/失败 → 使用兜底话术模板
- 内容生成违规 → 拒绝输出，使用标准话术

### 9.3 状态不一致

- Session 恢复时校验状态一致性
- 发现不一致 → 回退到最近一致状态点

---

## 10. LLM 接口层

### 10.1 设计目标

系统需要支持调用外部大模型 API（Claude、OpenAI、DeepSeek 等）来生成催收话术、识别意图、驱动策略决策。LLM 接口层提供统一抽象，便于切换不同模型进行测试和对比。

### 10.2 抽象接口

```python
class LLMClient(ABC):
    @abstractmethod
    async def chat(
        self,
        messages: List[Message],
        tools: List[Tool] | None = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> LLMResponse:
        """通用对话接口"""

    @abstractmethod
    async def detect_intent(
        self,
        user_message: str,
        context: dict,
    ) -> Intent:
        """意图识别专用接口"""

    @abstractmethod
    async def generate_strategy_response(
        self,
        strategy: Strategy,
        context: dict,
    ) -> str:
        """策略响应生成"""
```

### 10.3 内置实现

| 实现类 | 说明 |
|--------|------|
| `ClaudeClient` | Claude API 适配 |
| `OpenAIClient` | OpenAI / 兼容 API 适配 |
| `DeepSeekClient` | DeepSeek API 适配 |
| `MiniMaxClient` | MiniMax API 适配 |
| `KimiClient` | Kimi (Moonshot) API 适配 |
| `MockLLMClient` | 模拟 LLM，返回预设响应，用于单元测试 |

### 10.4 配置切换

```python
# config.yaml
llm:
  provider: "claude"  # 可选: claude / openai / deepseek / minimax / kimi / mock
  model: "claude-sonnet-4-6"
  api_key: "${CLAUDE_API_KEY}"
  temperature: 0.3    # 催收场景低温度，减少随机性
  max_tokens: 1024
```

### 10.5 Prompt 管理

- 意图识别、策略生成、话术生成的 Prompt 独立管理
- 支持 Prompt 模板化（Jinja2）
- 支持 A/B 测试不同 Prompt 版本

### 10.6 兜底机制

- LLM 调用超时（默认 30s）→ 重试 1 次 → 仍失败则使用标准话术模板
- LLM 返回内容违规 → 触发合规拦截 → 使用标准话术模板
- 记录 LLM 调用日志（输入、输出、耗时、token 用量）

---

## 11. 技术栈

- **语言**: Python（自研框架，参考 LangGraph / Claude Code 架构思想）
- **LLM**: Claude API / OpenAI API（通过 LLMClient 抽象层切换）
- **状态存储**: JSON 文件 / SQLite（初始版本）
- **调度**: 定时任务（APScheduler）+ 事件驱动
- **工具接口**: Mock 实现（初始版本）
- **Prompt 模板**: Jinja2

---

## 12. 附录

### 12.1 术语表

| 术语 | 说明 |
|------|------|
| CollectionSession | 单个用户的催收会话 Actor |
| Orchestrator | 主调度器，管理会话生命周期 |
| Strategy Engine | 策略引擎，根据意图选择跟进策略 |
| Interaction Lock | 交互权，同一时间只有一个渠道持有 |
| Intent Detector | 意图识别器，分类用户消息/事件 |

### 12.2 变更记录

| 日期 | 版本 | 变更内容 |
|------|------|---------|
| 2026-05-23 | v1.0 | 初始设计 |
