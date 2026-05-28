# Collect Agent 重构 Spec v2.0

> 基于 pi / OpenClaw 架构启示 + 提示词工程最佳实践 + MVP 目标

---

## 1. 项目定位

**目标**：在完全合规的前提下，推动用户确认还款意向或完成还款。

这是一个**目标导向的受限 ReAct Agent**（Goal-Directed Constrained ReAct Agent）。

与通用 Agent（如 pi、OpenClaw）的核心区别：
- 通用 Agent 的 objective 由用户定义
- 催收 Agent 的 objective 由系统预设，且必须受合规约束

---

## 2. 架构设计

### 2.1 四层 Guardrails（来自提示词工程最佳实践）

```
用户消息 / 系统事件
  ↓
Layer 0 — Harness 业务规则门（代码强制，不经过 LLM）
  ├── 时间窗口检查
  ├── 频次配额检查
  ├── 已暂停 / 已结清 / 已锁定检查
  └── STOP/CRISIS keyword 0 延迟拦截
  ↓
Layer 1 — Agent 核心（单轮 LLM 决策）
  ├── Context 构建（多信号聚合）
  ├── Decide：意图识别 + Skill 选择（一次 LLM 调用）
  └── Execute：ReAct Loop（tool_call / reply / escalate）
  ↓
Layer 2 — 输出 Guardrails
  ├── 黑名单关键词过滤（audit_content）
  ├── 事实核查：金额/日期必须与注入事实匹配
  └── 降级模板库（拦截时使用）
  ↓
Layer 3 — 日志与审计
  ├── 完整对话日志（含 thinking）
  ├── 合规事件告警
  └── Prompt 版本追踪
  ↓
用户看到消息
```

### 2.2 核心组件

```
┌─────────────────────────────────────────────────────────────┐
│                         Harness 层                           │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │ 时间检查     │  │ 频次配额     │  │ 敏感职业强制路由      │  │
│  │ 已暂停检查   │  │ 已结清检查   │  │ STOP/CRISIS keyword │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
└────────────────────┬────────────────────────────────────────┘
                     │ 不通过 → 直接拒绝
                     ▼ 通过
┌─────────────────────────────────────────────────────────────┐
│                      Agent 核心层                            │
│                                                              │
│  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐   │
│  │  Context    │────▶│   Decide    │────▶│   Execute   │   │
│  │  多信号构建   │     │  意图+选Skill │     │  ReAct Loop │   │
│  └─────────────┘     └─────────────┘     └─────────────┘   │
│         │                      │                  │          │
│         │ 用户文本/行为/状态    │ 一次LLM调用      │ tool/reply │
│         │ 上轮触达结果/历史    │ JSON输出         │ escalate   │
│         │                      │                  │          │
└─────────┼──────────────────────┼──────────────────┼──────────┘
          │                      │                  │
          ▼                      ▼                  ▼
┌─────────────────────────────────────────────────────────────┐
│                      Skill 层（Markdown）                     │
│  onboard.md | negotiation.md | complaint.md | crisis.md ...  │
│  每个文件：目标 + 执行流程 + 约束 + 可用工具列表                 │
└─────────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────┐
│                      Tool 层（函数）                          │
│  @tool query_bill | @tool pause_collection | @tool escalate  │
│  真实副作用：写数据库、调用外部API、生成工单                   │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. 组件 Spec

### 3.1 Harness（硬规则守卫）

像 OpenClaw 的 Gateway policy，代码强制，不经过 LLM。

```python
@dataclass
class HarnessResult:
    block: bool
    reason: str = ""
    force_intent: IntentCategory | None = None  # 强制注入意图（如 STOP）
    force_response: str = ""  # 强制返回固定模板
```

检查项：
1. 时间窗口：`compliance.is_within_valid_hours()`
2. 配额上限：`quota.is_exceeded(user_id, channel)`
3. 已暂停：`paused_until > now`
4. 已结清/已锁定：`session_state in ("resolved", "stopped")`
5. STOP keyword：`["停止", "退订", "不要再打"]`
6. CRISIS keyword：`["自杀", "不想活了", "活不下去"]`

### 3.2 Context（多信号输入）

聚合所有信号，格式化为 LLM 可理解的多信号文本。

```python
@dataclass
class Context:
    user_message: str | None = None
    profile: UserProfile = field(default_factory=UserProfile)
    session_state: str = "normal"
    negotiation_round: int = 0
    intent_history: list[str] = field(default_factory=list)
    recent_events: list[Event] = field(default_factory=list)
    last_outreach: OutreachResult | None = None
    messages: list[Message] = field(default_factory=list)
    facts: dict[str, Any] = field(default_factory=dict)
```

`to_prompt()` 输出格式（中文 + XML/Markdown 标签）：

```
【用户画像】逾期5天，金额¥1000，职业未知，敏感职业：否
【会话状态】normal，协商轮数0
【近期行为】
  - USER_PAYMENT_SUCCESS: {"amount": 500}
【上轮触达】您好，您的账单已逾期5天...，用户反应：无回复
【最近对话】
  [催收方] 您好...
  [用户] 我会还的
【本轮消息】我现在手头紧，能不能延期？

## 注入事实
<facts>
  <user_name>张三</user_name>
  <due_amount>1000.00</due_amount>
  <overdue_days>5</overdue_days>
</facts>

## 可选 Skills
- negotiation: 与用户协商还款计划或延期
- payment_guidance: 引导用户完成还款操作
- reengage: 用户沉默后重新建立联系
```

### 3.3 Decide（意图识别 + Skill 选择）

**一次 LLM 调用**，输出 JSON（DeepSeek JSON mode）。

System Prompt 结构：
1. **宪法规则**（顶层约束）
2. **意图路由表**（A/B/C/D/E/STOP/CRISIS 定义）
3. **可选 Skills 列表**（name + description）
4. **输出格式**（JSON schema）
5. **CoT SOP**（推理步骤要求）

JSON 输出格式：

```json
{
  "intent": "NEGOTIATION",
  "confidence": "high",
  "escalation": false,
  "emotion": "negative",
  "selected_skill": "negotiation",
  "thinking": "用户明确表示'手头紧'和'延期'，属于协商意图。历史记录显示此前承诺还款但未履行，需保持施压但提供协商空间。"
}
```

**约束**：
- prompt 中必须包含 "json" 字样（DeepSeek 要求）
- 提供明确的 JSON schema 示例
- temperature = 0.0
- response_format = {"type": "json_object"}

### 3.4 Skill（Markdown 配置）

像 pi 的 SKILL.md，按需加载。

目录结构：

```
src/collect_agent/skills/
├── onboard.md
├── negotiation.md
├── complaint.md
├── crisis.md
├── stop.md
├── reengage.md
├── standard.md      # 敏感职业强制路由
└── followup.md
```

Markdown 格式（YAML frontmatter + Markdown body）：

```markdown
---
name: complaint
description: 用户表达不满或威胁投诉时使用。先暂停催收，安抚情绪，提供客服联系方式。
tools: [pause_collection, escalate_to_human]
max_steps: 3
---

# 投诉处理 Skill

## 目标
在避免监管风险的前提下，妥善处理用户投诉，保留后续沟通空间。

## 执行流程（必须按顺序）
1. **调用 `pause_collection`**，暂停 7 天
2. 向用户真诚道歉，不要辩解
3. 提供官方客服热线和邮箱
4. 告知后续将由投诉专员联系

## 约束
- ❌ 禁止反驳用户
- ❌ 禁止继续施压还款
- ❌ 禁止承诺具体处理结果
- ✅ 语气必须诚恳、专业

## 输出格式
必须以 JSON 输出动作：
```json
{
  "type": "tool_call|reply|escalate",
  "thinking": "你的推理过程",
  ...
}
```
```

### 3.5 Tool（函数 + 装饰器）

像 pi 的 tool，用 Python type hints 自动推导 schema。

```python
@tool(
    name="pause_collection",
    description="暂停对用户的催收触达指定天数",
)
async def pause_collection(
    user_id: str,
    days: int,
    reason: str,
    store: Store,
) -> ToolResult:
    state = store.load(user_id)
    state.paused_until = datetime.now() + timedelta(days=days)
    store.save(state)
    return ToolResult(success=True, data={...})
```

**关键要求**：
- 必须有真实副作用（写数据库、调用 API）
- 禁止 mock 返回
- Schema 从 type hints 自动生成

### 3.6 ReAct Loop（简化，无 end）

支持的动作类型：
- `tool_call` → 调用工具，继续循环
- `reply` → 生成回复，终止循环
- `escalate` → 升级人工，终止循环

**禁止 `end`**。催收 Agent 不存在"自然结束"。

每步输出格式（JSON）：

```json
{
  "type": "tool_call",
  "thinking": "用户要求延期，我需要先查询账单详情",
  "name": "query_bill",
  "parameters": {"user_id": "u001"}
}
```

```json
{
  "type": "reply",
  "thinking": "已确认账单金额，用户经济困难，提供分期方案",
  "text": "理解您的困难。根据您的账单，逾期金额 1000 元，已逾期 5 天。我们可以为您申请分期还款，分 3 期每期 340 元。您看可以吗？"
}
```

### 3.7 状态机（简化）

```python
STATES = {"normal", "escalated", "stopped", "crisis", "disputed", "resolved"}
LOCKED_STATES = {"escalated", "stopped", "crisis", "disputed"}

# 转换规则
# - locked → 只能到 resolved
# - normal → 任意
# - resolved → 无出边
```

**关键设计**：
- `UserState` 是唯一真相
- `StateMachine` 是其派生视图
- 状态转换必须经过 `_transition()` 单一入口

---

## 4. Prompt 工程规范

### 4.1 System Prompt 核心结构

```markdown
# 角色
你是专业的债务催收助手。你的唯一目标是：在完全合规的前提下，推动用户确认还款意向或完成还款。

# 宪法规则（绝对不可违反）
1. 禁止任何威胁、恐吓或羞辱性语言
2. 禁止编造或猜测金额、日期、逾期天数 — 必须仅从 <facts> 读取
3. STOP / 投诉 / 危机 / 争议触发后，立即停止催收话术
4. 每轮必须重新评估用户意图
5. 回复语气必须在"温和提醒"范围内

# 意图路由表
- A（合作）：愿意还款或询问还款方式 → 引导还款
- B（协商）：表示困难，希望延期或分期 → 共情，提供方案
- C（回避）：回避问题，不愿深入讨论 → 简短确认，不持续施压
- D（争议）：质疑账单真实性或金额 → 道歉，移交人工
- E（投诉/威胁）：表达不满，威胁投诉 → 暂停，安抚，移交
- STOP：明确要求停止联系 → 确认退出
- CRISIS：提及自杀、重病等 → 安慰，立即人工告警

# 可选 Skills
{{skills_description}}

# 输出格式
你必须以 JSON 格式输出，包含以下字段：
- intent: 意图类别
- confidence: high|medium|low
- escalation: true|false
- emotion: positive|neutral|negative|angry
- selected_skill: 选择的 skill 名称
- thinking: 你的推理过程（必须引用具体信号）

示例：
{{json_example}}
```

### 4.2 上下文注入规范

使用 XML 标签包裹结构化数据，中文 LLM 对显式标签的理解更稳定：

```xml
<facts>
  <user_name>张三</user_name>
  <due_amount>1000.00</due_amount>
  <overdue_days>5</overdue_days>
</facts>

<session_context>
  <state>normal</state>
  <negotiation_round>2</negotiation_round>
</session_context>

<recent_history>
  <message direction="outbound" channel="chatbot">您好...</message>
  <message direction="inbound" channel="chatbot">我会还的</message>
</recent_history>
```

### 4.3 CoT SOP（每轮推理步骤）

```markdown
## 思考流程（每轮必须执行）
1. 当前 session_state 是什么？如果是 locked 状态，立即使用固定模板
2. 读取最近 3 轮对话。用户情绪是否显著转变？
3. 本轮核心意图是什么？基于所有信号综合判断，不是只看文本
4. 该意图是否触发单向门（D/E/STOP/CRISIS）？
5. 如需回复，回复中的金额和日期是否与 <facts> 完全匹配？
6. 回复语气是否在"温和提醒"范围内？
7. 选择哪个 skill 最合适？从可选 skills 中选择
```

---

## 5. 数据模型

### 5.1 UserState（唯一真相）

```python
class UserState(BaseModel):
    user_id: str
    profile: UserProfile
    session_state: str = "normal"
    channel_states: dict[str, str] = Field(default_factory=dict)
    conversation: ConversationContext = Field(default_factory=ConversationContext)
    quota_usage: dict[str, Any] = Field(default_factory=dict)
    paused_until: datetime | None = None
    # 新增
    intent_history: list[str] = Field(default_factory=list)
    last_outreach_at: datetime | None = None
    dnc: bool = False  # Do Not Contact
```

### 5.2 ConversationContext

```python
class ConversationContext(BaseModel):
    messages: list[Message] = Field(default_factory=list)
    current_intent: str | None = None
    negotiation_round: int = 0
    
    def add_message(self, message: Message) -> None:
        self.messages.append(message)
        if len(self.messages) > 50:
            self.messages = self.messages[-50:]
```

---

## 6. 关键设计决策

| 决策 | 选择 | 理由 |
|---|---|---|
| Skill 格式 | Markdown + YAML frontmatter | 像 pi SKILL.md，声明式配置，无需 Python class |
| Tool 定义 | 函数 + `@tool` 装饰器 | 自动推导 schema，减少 boilerplate |
| ReAct 输出 | JSON（非 XML） | DeepSeek 支持 JSON mode，`json.loads` 比 XML 解析鲁棒 |
| 意图识别 | 一次 LLM 调用（意图 + skill 选择） | 减少调用次数，降低成本 |
| 状态管理 | UserState 唯一真相 | 避免双写，数据一致性 |
| 结束条件 | 无 `end` action | 催收不存在"自然结束"，只有目标达成或强制终止 |
| STOP/CRISIS | Keyword 0 延迟拦截 | 合规要求，不能等待 LLM |
| 敏感职业 | Harness 强制路由到 standard skill | 绕过 LLM 选择，避免合规风险 |
| 输出审计 | `audit_content()` 强制调用 | LLM 输出后必须经过黑名单过滤 |

---

## 7. 与 pi / OpenClaw 的对比

| 维度 | pi / OpenClaw | 催收 Agent v2 |
|---|---|---|
| Objective | 用户定义（编码、搜索、分析） | 系统预设（合规催收） |
| Skill | SKILL.md 按需加载 | Markdown 配置，LLM 自主选择 |
| Tool | 文件操作、bash、网络 | 业务操作（暂停、升级、查询账单） |
| 结束条件 | 用户满意或任务完成 | 结清 / STOP / 危机 / 升级 |
| Guardrails | 最小化（无权限弹窗） | 多层硬规则（频次/时间/敏感词） |
| 状态机 | 无（纯对话） | 有（单向门锁定） |
| 副作用 | 可逆（文件可恢复） | 不可逆（DNC 名单、工单） |
