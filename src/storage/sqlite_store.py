import json
import sqlite3
from datetime import datetime
from types import TracebackType
from typing import Self

from src.core.models import ConversationContext, Message, UserProfile, UserState


class SQLiteStore:
    def __init__(self, db_path: str = "collect_agent.db"):
        self._db_path = db_path
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self) -> None:
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
        # Migrate: add context column if missing
        try:
            self._conn.execute("SELECT context FROM user_states LIMIT 1")
        except sqlite3.OperationalError:
            self._conn.execute("ALTER TABLE user_states ADD COLUMN context TEXT")
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
        try:
            self.close()
        except Exception:
            pass

    def save(self, state: UserState, context_manager=None) -> None:
        profile = state.profile
        conversation_json = json.dumps(state.conversation.model_dump(mode="json"), ensure_ascii=False)
        quota_usage_json = json.dumps(state.quota_usage, ensure_ascii=False)
        channel_states_json = json.dumps(state.channel_states, ensure_ascii=False)

        paused_until_str = state.paused_until.isoformat() if state.paused_until else None
        context_json = json.dumps(context_manager.to_dict(), ensure_ascii=False) if context_manager else None

        self._conn.execute(
            """
            INSERT INTO user_states (
                user_id, name, phone, occupation, overdue_days, amount_due,
                session_state, channel_states, conversation, quota_usage, paused_until, context, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                updated_at = excluded.updated_at
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

        paused_until = None
        if row["paused_until"]:
            paused_until = datetime.fromisoformat(row["paused_until"])

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
            paused_until=paused_until,
        )

    def load_context_manager(self, user_id: str):
        from src.context.manager import ContextManager
        row = self._conn.execute(
            "SELECT context FROM user_states WHERE user_id = ?", (user_id,)
        ).fetchone()
        if row is None or not row["context"]:
            return None
        data = json.loads(row["context"])
        return ContextManager.from_dict(data)
