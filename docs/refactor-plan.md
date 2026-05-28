# Collect Agent 重构 Plan v2.0

> 基于 [refactor-spec.md](refactor-spec.md) 执行

---

## Phase 1: 删除 Legacy（目标：半天）

### 1.1 删除文件清单

| 文件/目录 | 原因 |
|---|---|
| `src/collect_agent/session/session.py` | Legacy `CollectionSession`，已弃用 |
| `src/collect_agent/session/enhanced_state_machine.py` | 被简化状态常量取代 |
| `src/collect_agent/session/state_machine.py` | 被简化状态常量取代 |
| `src/collect_agent/strategy/` | 旧策略引擎，已被 Skill 架构取代 |
| `src/collect_agent/skills/*_skill.py`（10 个） | 过度设计的 class，改为 Markdown |
| `src/collect_agent/prompts/engine.py` | 六层拼装过度复杂，改为 jinja2 直接渲染 |
| `src/collect_agent/tools/base.py` | ABC 子类被函数+装饰器取代 |
| `src/collect_agent/tools/*.py`（除 registry） | 被 ops.py 取代 |
| `src/collect_agent/intent/recognizer.py` | 被 Decider 取代 |
| `src/collect_agent/intent/models.py` | 合并到 `core/models.py` |

### 1.2 保留文件清单

| 文件 | 保留原因 |
|---|---|
| `src/collect_agent/core/models.py` | `UserState`, `Event`, `Message` 等 |
| `src/collect_agent/core/constants.py` | `EventType`, `ChannelType` |
| `src/collect_agent/core/exceptions.py` | 自定义异常 |
| `src/collect_agent/config/` | 配置管理 |
| `src/collect_agent/llm/` | LLM 客户端（需简化 `detect_intent` / `generate_strategy`） |
| `src/collect_agent/storage/` | 存储层 |
| `src/collect_agent/compliance/` | 合规检查 |
| `src/collect_agent/quota/` | 配额管理 |
| `src/collect_agent/orchestrator/` | 通道仲裁 |
| `src/collect_agent/events/router.py` | 事件路由 |
| `src/collect_agent/scheduler.py` | 调度器（需简化） |
| `src/collect_agent/cli.py` | CLI |
| `src/collect_agent/main.py` | 系统入口（需重写） |

### 1.3 新建目录结构

```
src/collect_agent/
├── core/
│   ├── __init__.py
│   ├── constants.py      # 保留
│   ├── exceptions.py     # 保留
│   ├── models.py         # 保留，新增 intent_history, dnc
│   └── context.py        # NEW: Context, OutreachResult
├── config/               # 保留
├── llm/                  # 保留，简化
├── storage/              # 保留
├── compliance/           # 保留，增强 audit_content 调用
├── quota/                # 保留
├── orchestrator/         # 保留
├── events/
│   └── router.py         # 保留
├── harness.py            # NEW: Harness, HarnessResult
├── decider.py            # NEW: Decider（意图识别 + Skill 选择）
├── agent/
│   └── session.py        # REWRITE: AgentSession v2
├── skills/
│   ├── __init__.py
│   ├── base.py           # REWRITE: Skill dataclass, SkillLoader
│   ├── loader.py         # NEW: 加载 Markdown skill
│   ├── registry.py       # REWRITE: 简化，去 triggers
│   └── executor.py       # REWRITE: JSON ReAct，无 end
│   # skill markdown 文件移到 prompts/templates/skills/ 或单独目录
├── tools/
│   ├── __init__.py
│   ├── registry.py       # REWRITE: @tool 装饰器 + 注册表
│   └── ops.py            # NEW: 所有 tool 函数（真实副作用）
├── prompts/
│   └── templates/        # 保留，改为 jinja2 模板
│       ├── skills/
│       │   ├── onboard.md
│       │   ├── negotiation.md
│       │   ├── complaint.md
│       │   ├── crisis.md
│       │   ├── stop.md
│       │   ├── reengage.md
│       │   ├── standard.md
│       │   └── followup.md
│       ├── system_prompt.j2   # NEW: 主 system prompt 模板
│       └── decider_prompt.j2  # NEW: Decide 阶段 prompt 模板
├── scheduler.py          # 简化
├── main.py               # 重写
└── cli.py                # 保留
```

---

## Phase 2: 新建核心（目标：1 天）

### 2.1 `harness.py`

实现 Harness 硬规则守卫：
- `Harness.check(event, state) -> HarnessResult`
- STOP/CRISIS keyword 拦截
- 时间、配额、暂停、状态检查

### 2.2 `core/context.py`

实现 Context dataclass：
- 多信号聚合
- `to_prompt()` 格式化输出（中文 + XML 标签）

### 2.3 `decider.py`

实现 Decider（一次 LLM 调用）：
- 构建 system prompt（宪法规则 + 意图路由表 + skills 列表 + JSON schema）
- 构建 user prompt（Context.to_prompt()）
- 调用 LLM with `response_format={"type": "json_object"}`
- 解析 JSON 输出为 `Decision`

### 2.4 `skills/loader.py`

实现 SkillLoader：
- 解析 Markdown + YAML frontmatter
- 加载 `name`, `description`, `tools`, `max_steps`
- 加载 Markdown body 作为 system prompt 补充

### 2.5 `skills/base.py`

简化 Skill dataclass：
```python
@dataclass
class Skill:
    name: str
    description: str
    tools: list[str]
    max_steps: int = 3
    content: str = ""  # Markdown body
```

### 2.6 `skills/registry.py`

简化 SkillRegistry：
- 删除 `triggers`
- 删除 `select_skill`
- 保留 `register`, `get`, `list`

### 2.7 `tools/registry.py`

实现 `@tool` 装饰器：
- 从函数签名自动推导 JSON Schema（使用 `inspect.signature` + `typing.get_type_hints`）
- 注册到全局注册表
- 支持依赖注入（`store`, `compliance_checker` 等）

### 2.8 `tools/ops.py`

实现所有 tool 函数（真实副作用）：
- `query_bill`
- `pause_collection`（写 `paused_until`）
- `escalate_to_human`（写工单表）
- `welfare_alert`
- `add_to_dnc`（写 `dnc` 字段）
- `query_user_history`
- `schedule_reminder`
- `send_payment_link`
- `record_promise`
- `check_payment_status`

### 2.9 Prompt 模板

- `system_prompt.j2`: 宪法规则 + 意图路由表 + CoT SOP
- `decider_prompt.j2`: 可选 skills 列表 + JSON 示例
- 各 skill `.md` 文件

---

## Phase 3: 重写 AgentSession（目标：半天）

### 3.1 统一事件处理入口

```python
async def handle_event(self, event: Event) -> SkillResult:
    # 1. Harness 检查
    harness_result = await self.harness.check(event, self.state)
    if harness_result.block:
        return self._build_blocked_result(harness_result)
    
    # 2. 构建 Context
    context = self._build_context(event)
    
    # 3. Decide（意图 + Skill 选择）
    if harness_result.force_intent:
        decision = Decision(
            intent=harness_result.force_intent,
            selected_skill=self._intent_to_skill(harness_result.force_intent),
            confidence="high",
            escalation=harness_result.force_intent in ("CRISIS", "COMPLAINT", "DISPUTE"),
            reasoning="Harness forced",
        )
    else:
        decision = await self.decider.decide(context)
    
    # 4. 加载 Skill
    skill = self.skill_registry.get(decision.selected_skill)
    if not skill:
        skill = self._fallback_skill(decision.intent)
    
    # 5. 记录用户消息
    if event.type == EventType.USER_REPLIED:
        self._record_message("chatbot", "inbound", event.payload.get("message", ""))
        self.state.conversation.negotiation_round += 1
    
    # 6. Execute（ReAct）
    result = await self.skill_executor.execute(skill, context, self.state)
    
    # 7. 输出审计
    if result.response_text:
        clean, reason = self.compliance.audit_content(result.response_text)
        if not clean:
            result.response_text = self._fallback_for_violation(reason)
            result.status = "error"
    
    # 8. 记录回复
    if result.response_text:
        self._record_message("chatbot", "outbound", result.response_text)
    
    # 9. 处理结果（状态转换、保存）
    self._process_result(result, decision)
    
    return result
```

### 3.2 删除的方法

- `_handle_user_event` → 合并到 `handle_event`
- `_handle_outreach_event` → 合并到 `handle_event`
- `_handle_payment_success` → 保留但简化
- `_handle_silence_timeout` → 合并到 `handle_event`

---

## Phase 4: 真实副作用（目标：半天）

### 4.1 SQLite 存储增强

新增表/字段：
- `UserState.dnc: bool` — DNC 标记
- `UserState.intent_history: list[str]` — JSON 序列化
- `UserState.last_outreach_at: datetime`
- `tickets` 表 — 工单记录
- `welfare_alerts` 表 — 危机告警记录

### 4.2 Tool 副作用实现

| Tool | 副作用 |
|---|---|
| `pause_collection` | `state.paused_until = now + days` |
| `add_to_dnc` | `state.dnc = True` |
| `escalate_to_human` | 写入 `tickets` 表 |
| `welfare_alert` | 写入 `welfare_alerts` 表 |
| `record_promise` | 写入 `promises` 表 |
| `schedule_reminder` | 写入 `reminders` 表 |

### 4.3 输出合规审计

确保 `AgentSession._process_result` 中调用 `audit_content()`：
- 拦截黑名单词汇
- 替换为降级模板
- 记录审计日志

---

## Phase 5: 测试（目标：半天）

### 5.1 测试策略

- **单元测试**：Harness、Decider（mock LLM）、Tool 副作用
- **集成测试**：端到端 flow（MemoryStore 隔离）
- **E2E**：删除真实 LLM 依赖，改用 MockLLMClient

### 5.2 测试文件

| 文件 | 测试内容 |
|---|---|
| `tests/test_harness.py` | 时间、配额、keyword 拦截 |
| `tests/test_decider.py` | mock LLM 输出解析 |
| `tests/test_tools.py` | 真实副作用验证 |
| `tests/test_agent_session.py` | 完整 flow |
| `tests/test_skills.py` | Markdown 加载 |

### 5.3 删除/修改的测试

- 删除 `scripts/e2e_tests/` 或改为可选
- 删除 `test_strategy.py`, `test_chatbot_agent.py`（legacy）
- 更新 `test_integration.py` 使用 MemoryStore

---

## 执行顺序

```
Phase 1 ──▶ Phase 2 ──▶ Phase 3 ──▶ Phase 4 ──▶ Phase 5
 删除       新建核心    重写Agent    真实副作用    测试
           (可并行)    (依赖P2)    (依赖P3)     (依赖P4)
```

**关键路径**：P1 → P2 → P3 → P4 → P5

**可并行项**：
- P2 中 Prompt 模板编写可与代码开发并行
- P4 中数据库 schema 变更可与 P3 并行准备

---

## 验收标准

| 检查项 | 标准 |
|---|---|
| 代码量 | < 50 个 Python 文件（当前 80+） |
| 单元测试 | 全部通过（201+ tests） |
| 核心 flow | `uv run collect-agent --action=demo` 正常运行 |
| 合规审计 | LLM 输出必须经过 `audit_content` |
| STOP 拦截 | keyword 触发后 0 延迟，不调用 LLM |
| 敏感职业 | 自动路由到 standard skill，不经过 LLM 选择 |
| Tool 副作用 | `pause_collection` 真正写入数据库 |
| 状态一致性 | `UserState` 是唯一真相，无双写 |
