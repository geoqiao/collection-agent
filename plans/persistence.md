# Agent 持久化架构改造计划

## Context

当前 `SessionManager` 将 `AgentSession` 实例常驻内存 (`self._sessions: dict[str, AgentSession]`)，导致：

1. 进程重启丢失所有 session 状态
2. 内存膨胀（AgentSession 包含 LLM client, SkillRegistry 等重量级对象）
3. 无法水平扩展
4. `last_outreach_at` / `last_interaction_at` 仅存内存，重启丢失
5. `SilenceTimeoutTracker._emitted_tiers` 也是内存字典，重启后重复触发

## Approach

### Phase 1: Session 按需加载 + 状态持久化

1. **SessionManager 共享重量级依赖**
   - 将 SkillRegistry, SkillExecutor, Decider, Harness 提升为 SessionManager 的属性（只创建一次）
   - AgentSession 改为轻量包装，只持有引用
   - `get_or_create()` 每次从 store 加载 state，新建轻量 AgentSession

2. **AgentSession 内存状态迁移到 UserState**
   - `last_outreach_at` → `UserState.last_outreach_at`
   - `last_interaction_at` → `UserState.last_interaction_at`
   - `silence_timeout_emitted` → `UserState.silence_timeout_emitted`（列表）

3. **SQLiteStore Schema 升级**
   - 保存 `last_outreach_at`, `last_interaction_at`, `dnc`, `dispute_status`, `willing_to_pay_at`, `silence_timeout_emitted`
   - 新增 `scheduled_tasks` 表（Phase 2 用）
   - 自动迁移：列不存在时 ALTER TABLE ADD COLUMN

4. **SilenceTimeoutTracker 持久化**
   - 从 `UserState.silence_timeout_emitted` 读取/写入
   - 不再依赖内存 `_emitted_tiers`

### Phase 2: 统一任务队列 + Heartbeat 扫描

1. **ScheduledTask 模型**

   ```python
   class ScheduledTask(BaseModel):
       task_id: str
       user_id: str
       task_type: str          # "payment_follow_up", "reminder", "silence_timeout"
       scheduled_at: datetime  # 应执行时间
       payload: dict = {}
       status: str = "pending" # pending | done | cancelled
   ```

2. **工具层增加 `schedule_task` / `cancel_task`**
   - `record_willing_to_pay` 不再直接写 `willing_to_pay_at`，而是创建 `ScheduledTask`
   - 其他需要延迟触发的逻辑统一走任务队列

3. **Scheduler 统一 Heartbeat**

   ```python
   async def run_heartbeat(self, interval_seconds: int = 600):
       while True:
           await asyncio.sleep(interval_seconds)
           await self._scan_and_execute_tasks()  # 统一扫描所有 pending tasks
   ```

   - 取代 `check_payment_follow_ups()` 的直接全表扫描
   - 取代 `check_silence_timeouts()` 的内存 session 遍历

4. **删除 `SessionManager._sessions` 内存缓存**
   - 可选：用 `functools.lru_cache` 或 TTL cache 做短期缓存（默认关闭）

## Files to modify

| 文件                         | 改动                                                                                                      |
| ---------------------------- | --------------------------------------------------------------------------------------------------------- |
| `core/models.py`             | UserState 增加 `last_outreach_at`, `last_interaction_at`, `silence_timeout_emitted`；新增 `ScheduledTask` |
| `storage/sqlite_store.py`    | Schema 升级（新列 + tasks 表）；save/load 覆盖新字段                                                      |
| `storage/memory_store.py`    | 增加 task 存储接口                                                                                        |
| `session/manager.py`         | 共享依赖，按需加载，移除常驻缓存                                                                          |
| `agent/session.py`           | 从 UserState 读写内存状态                                                                                 |
| `session/timeout_tracker.py` | 持久化 emitted_tiers                                                                                      |
| `scheduler.py`               | 统一 heartbeat + task 扫描                                                                                |
| `tools/ops.py`               | `record_willing_to_pay` 改为创建 ScheduledTask                                                            |
| `main.py`                    | 暴露 `run_heartbeat()` 入口                                                                               |
| `tests/`                     | 更新测试适配新架构                                                                                        |

## Reuse

- 现有 `SQLiteStore` 的 `_init_db()` 迁移模式（已有 ALTER TABLE ADD COLUMN 逻辑）
- 现有 `EventRouter` 事件路由机制不变
- 现有 `SkillExecutor` ReAct 循环不变

## Verification

1. `uv run ruff check src/ tests/` — 静态检查
2. `uv run pytest tests/ -q` — 全部测试通过
3. 手动验证：重启进程后，`last_outreach_at` 和 `silence_timeout_emitted` 可从数据库恢复
