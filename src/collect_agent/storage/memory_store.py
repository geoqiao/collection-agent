from collect_agent.core.models import ScheduledTask, UserState


class MemoryStore:
    def __init__(self):
        self._data: dict[str, UserState] = {}
        self._tasks: dict[str, ScheduledTask] = {}

    def save(self, state: UserState) -> None:
        self._data[state.user_id] = state

    def load(self, user_id: str) -> UserState | None:
        return self._data.get(user_id)

    def load_all(self) -> list[UserState]:
        return list(self._data.values())

    def delete(self, user_id: str) -> None:
        self._data.pop(user_id, None)

    # --- Task storage ---

    def save_task(self, task: ScheduledTask) -> None:
        self._tasks[task.task_id] = task

    def load_pending_tasks(self, before=None) -> list[ScheduledTask]:
        from datetime import datetime

        now = before or datetime.now()
        return [
            t
            for t in self._tasks.values()
            if t.status == "pending" and t.scheduled_at <= now
        ]

    def load_tasks_for_user(self, user_id: str) -> list[ScheduledTask]:
        return [t for t in self._tasks.values() if t.user_id == user_id]

    def cancel_task(self, task_id: str) -> bool:
        task = self._tasks.get(task_id)
        if task is None:
            return False
        task.status = "cancelled"
        return True

    def complete_task(self, task_id: str) -> bool:
        task = self._tasks.get(task_id)
        if task is None:
            return False
        task.status = "done"
        return True
