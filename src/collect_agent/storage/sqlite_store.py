import contextlib
import json
import sqlite3
from datetime import datetime
from types import TracebackType
from typing import Self

from collect_agent.core.models import (
    ConversationContext,
    Message,
    ScheduledTask,
    UserProfile,
    UserState,
)


class SQLiteStore:
    def __init__(self, db_path: str = "collect_agent.db"):
        self._db_path = db_path
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self) -> None:
        # user_states table
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS user_states (
                user_id TEXT PRIMARY KEY,
                name TEXT,
                phone TEXT,
                occupation TEXT,
                overdue_days INTEGER DEFAULT 0,
                amount_due REAL DEFAULT 0.0,
                session_state TEXT DEFAULT 'idle',
                channel_states TEXT,
                conversation TEXT,
                quota_usage TEXT,
                paused_until TEXT,
                context TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        self._conn.commit()

        # Migrate: add columns if missing
        existing_cols = {
            r[1]
            for r in self._conn.execute("PRAGMA table_info(user_states)").fetchall()
        }
        migrations = [
            ("context", "TEXT"),
            ("intent_history", "TEXT"),
            ("last_outreach_at", "TEXT"),
            ("last_interaction_at", "TEXT"),
            ("dnc", "INTEGER DEFAULT 0"),
            ("dispute_status", "TEXT"),
            ("willing_to_pay_at", "TEXT"),
            ("silence_timeout_emitted", "TEXT"),
        ]
        for col_name, col_type in migrations:
            if col_name not in existing_cols:
                self._conn.execute(
                    f"ALTER TABLE user_states ADD COLUMN {col_name} {col_type}"
                )
                self._conn.commit()

        # scheduled_tasks table
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS scheduled_tasks (
                task_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                task_type TEXT NOT NULL,
                scheduled_at TEXT NOT NULL,
                payload TEXT,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self.close()

    def __del__(self) -> None:
        with contextlib.suppress(Exception):
            self.close()

    def save(self, state: UserState, context_manager=None) -> None:
        profile = state.profile
        conversation_json = json.dumps(
            state.conversation.model_dump(mode="json"), ensure_ascii=False
        )
        quota_usage_json = json.dumps(state.quota_usage, ensure_ascii=False)
        channel_states_json = json.dumps(state.channel_states, ensure_ascii=False)
        intent_history_json = json.dumps(state.intent_history, ensure_ascii=False)
        silence_timeout_emitted_json = json.dumps(
            state.silence_timeout_emitted, ensure_ascii=False
        )

        paused_until_str = (
            state.paused_until.isoformat() if state.paused_until else None
        )
        last_outreach_at_str = (
            state.last_outreach_at.isoformat() if state.last_outreach_at else None
        )
        last_interaction_at_str = (
            state.last_interaction_at.isoformat() if state.last_interaction_at else None
        )
        willing_to_pay_at_str = (
            state.willing_to_pay_at.isoformat() if state.willing_to_pay_at else None
        )
        context_json = (
            json.dumps(context_manager.to_dict(), ensure_ascii=False)
            if context_manager
            else None
        )

        self._conn.execute(
            """
            INSERT INTO user_states (
                user_id, name, phone, occupation, overdue_days, amount_due,
                session_state, channel_states, conversation, quota_usage, paused_until,
                context, updated_at, intent_history, last_outreach_at, last_interaction_at,
                dnc, dispute_status, willing_to_pay_at, silence_timeout_emitted
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                name = excluded.name,
                phone = excluded.phone,
                occupation = excluded.occupation,
                overdue_days = excluded.overdue_days,
                amount_due = excluded.amount_due,
                session_state = excluded.session_state,
                channel_states = excluded.channel_states,
                conversation = excluded.conversation,
                quota_usage = excluded.quota_usage,
                paused_until = excluded.paused_until,
                context = excluded.context,
                updated_at = excluded.updated_at,
                intent_history = excluded.intent_history,
                last_outreach_at = excluded.last_outreach_at,
                last_interaction_at = excluded.last_interaction_at,
                dnc = excluded.dnc,
                dispute_status = excluded.dispute_status,
                willing_to_pay_at = excluded.willing_to_pay_at,
                silence_timeout_emitted = excluded.silence_timeout_emitted
            """,
            (
                state.user_id,
                profile.name,
                profile.phone,
                profile.occupation,
                profile.overdue_days,
                profile.amount_due,
                state.session_state,
                channel_states_json,
                conversation_json,
                quota_usage_json,
                paused_until_str,
                context_json,
                datetime.now().isoformat(),
                intent_history_json,
                last_outreach_at_str,
                last_interaction_at_str,
                1 if state.dnc else 0,
                state.dispute_status,
                willing_to_pay_at_str,
                silence_timeout_emitted_json,
            ),
        )
        self._conn.commit()

    def load(self, user_id: str) -> UserState | None:
        row = self._conn.execute(
            "SELECT * FROM user_states WHERE user_id = ?", (user_id,)
        ).fetchone()

        if row is None:
            return None

        return self._row_to_state(row)

    def load_all(self) -> list[UserState]:
        rows = self._conn.execute("SELECT * FROM user_states").fetchall()
        return [self._row_to_state(row) for row in rows]

    def delete(self, user_id: str) -> None:
        self._conn.execute("DELETE FROM user_states WHERE user_id = ?", (user_id,))
        self._conn.commit()

    def save_task(self, task: ScheduledTask) -> None:
        self._conn.execute(
            """
            INSERT INTO scheduled_tasks (
                task_id, user_id, task_type, scheduled_at, payload, status, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(task_id) DO UPDATE SET
                user_id = excluded.user_id,
                task_type = excluded.task_type,
                scheduled_at = excluded.scheduled_at,
                payload = excluded.payload,
                status = excluded.status
            """,
            (
                task.task_id,
                task.user_id,
                task.task_type,
                task.scheduled_at.isoformat(),
                json.dumps(task.payload, ensure_ascii=False),
                task.status,
                datetime.now().isoformat(),
            ),
        )
        self._conn.commit()

    def load_pending_tasks(self, before: datetime | None = None) -> list[ScheduledTask]:
        if before is None:
            rows = self._conn.execute(
                "SELECT * FROM scheduled_tasks WHERE status = 'pending' ORDER BY scheduled_at"
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT * FROM scheduled_tasks WHERE status = 'pending' AND scheduled_at <= ? ORDER BY scheduled_at",
                (before.isoformat(),),
            ).fetchall()
        return [self._row_to_task(row) for row in rows]

    def load_tasks_for_user(self, user_id: str) -> list[ScheduledTask]:
        rows = self._conn.execute(
            "SELECT * FROM scheduled_tasks WHERE user_id = ? ORDER BY scheduled_at",
            (user_id,),
        ).fetchall()
        return [self._row_to_task(row) for row in rows]

    def cancel_task(self, task_id: str) -> bool:
        cursor = self._conn.execute(
            "UPDATE scheduled_tasks SET status = 'cancelled' WHERE task_id = ?",
            (task_id,),
        )
        self._conn.commit()
        return cursor.rowcount > 0

    def complete_task(self, task_id: str) -> bool:
        cursor = self._conn.execute(
            "UPDATE scheduled_tasks SET status = 'done' WHERE task_id = ?",
            (task_id,),
        )
        self._conn.commit()
        return cursor.rowcount > 0

    def _row_to_state(self, row: sqlite3.Row) -> UserState:
        conversation_data = json.loads(row["conversation"] or "{}")
        messages_data = conversation_data.get("messages", [])
        messages = [
            Message(
                channel=m["channel"],
                direction=m["direction"],
                content=m["content"],
                timestamp=datetime.fromisoformat(m["timestamp"]),
            )
            for m in messages_data
        ]
        conversation = ConversationContext(
            messages=messages,
            current_intent=conversation_data.get("current_intent"),
            negotiation_round=conversation_data.get("negotiation_round", 0),
        )

        def _parse_dt(val):
            return datetime.fromisoformat(val) if val else None

        return UserState(
            user_id=row["user_id"],
            profile=UserProfile(
                user_id=row["user_id"],
                name=row["name"] or "",
                phone=row["phone"] or "",
                occupation=row["occupation"],
                overdue_days=row["overdue_days"] or 0,
                amount_due=row["amount_due"] or 0.0,
            ),
            session_state=row["session_state"] or "idle",
            channel_states=json.loads(row["channel_states"] or "{}"),
            conversation=conversation,
            quota_usage=json.loads(row["quota_usage"] or "{}"),
            paused_until=_parse_dt(row["paused_until"]),
            intent_history=json.loads(row["intent_history"] or "[]"),
            last_outreach_at=_parse_dt(row["last_outreach_at"]),
            last_interaction_at=_parse_dt(row["last_interaction_at"]),
            dnc=bool(row["dnc"]) if row["dnc"] is not None else False,
            dispute_status=row["dispute_status"],
            willing_to_pay_at=_parse_dt(row["willing_to_pay_at"]),
            silence_timeout_emitted=json.loads(row["silence_timeout_emitted"] or "[]"),
        )

    def _row_to_task(self, row: sqlite3.Row) -> ScheduledTask:
        return ScheduledTask(
            task_id=row["task_id"],
            user_id=row["user_id"],
            task_type=row["task_type"],
            scheduled_at=datetime.fromisoformat(row["scheduled_at"]),
            payload=json.loads(row["payload"] or "{}"),
            status=row["status"],
        )
