import json
import sqlite3
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


class QuotaStorage:
    def __init__(self, db_path: str = "collect_agent.db"):
        self._db_path = db_path
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self) -> None:
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS daily_quota (
                user_id TEXT,
                date TEXT,
                call_self_count INTEGER DEFAULT 0,
                call_contact_count INTEGER DEFAULT 0,
                call_answered_count INTEGER DEFAULT 0,
                call_last_timestamp TEXT,
                call_timestamps TEXT,
                chat_sent_count INTEGER DEFAULT 0,
                chat_user_replied INTEGER DEFAULT 0,
                chat_last_timestamp TEXT,
                push_sent_count INTEGER DEFAULT 0,
                PRIMARY KEY (user_id, date)
            )
            """
        )
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    def __del__(self) -> None:
        try:
            self.close()
        except Exception:
            pass

    def save_usage(self, usage: DailyQuotaUsage) -> None:
        call_timestamps_json = json.dumps(
            [t.isoformat() for t in usage.call_timestamps], ensure_ascii=False
        )
        self._conn.execute(
            """
            INSERT INTO daily_quota (
                user_id, date, call_self_count, call_contact_count, call_answered_count,
                call_last_timestamp, call_timestamps, chat_sent_count, chat_user_replied,
                chat_last_timestamp, push_sent_count
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id, date) DO UPDATE SET
                call_self_count = excluded.call_self_count,
                call_contact_count = excluded.call_contact_count,
                call_answered_count = excluded.call_answered_count,
                call_last_timestamp = excluded.call_last_timestamp,
                call_timestamps = excluded.call_timestamps,
                chat_sent_count = excluded.chat_sent_count,
                chat_user_replied = excluded.chat_user_replied,
                chat_last_timestamp = excluded.chat_last_timestamp,
                push_sent_count = excluded.push_sent_count
            """,
            (
                usage.user_id,
                usage.date,
                usage.call_self_count,
                usage.call_contact_count,
                usage.call_answered_count,
                usage.call_last_timestamp.isoformat() if usage.call_last_timestamp else None,
                call_timestamps_json,
                usage.chat_sent_count,
                int(usage.chat_user_replied),
                usage.chat_last_timestamp.isoformat() if usage.chat_last_timestamp else None,
                usage.push_sent_count,
            ),
        )
        self._conn.commit()

    def load_usage(self, user_id: str, date: str) -> DailyQuotaUsage | None:
        row = self._conn.execute(
            "SELECT * FROM daily_quota WHERE user_id = ? AND date = ?",
            (user_id, date),
        ).fetchone()

        if row is None:
            return None

        return self._row_to_usage(row)

    def load_all_for_date(self, date: str) -> list[DailyQuotaUsage]:
        rows = self._conn.execute(
            "SELECT * FROM daily_quota WHERE date = ?", (date,)
        ).fetchall()

        return [self._row_to_usage(row) for row in rows]

    def reset_for_new_day(self, user_id: str, date: str) -> DailyQuotaUsage:
        usage = DailyQuotaUsage(user_id=user_id, date=date)
        self.save_usage(usage)
        return usage

    def _row_to_usage(self, row: sqlite3.Row) -> DailyQuotaUsage:
        timestamps_data = json.loads(row["call_timestamps"] or "[]")
        call_timestamps = [datetime.fromisoformat(t) for t in timestamps_data]

        return DailyQuotaUsage(
            user_id=row["user_id"],
            date=row["date"],
            call_self_count=row["call_self_count"] or 0,
            call_contact_count=row["call_contact_count"] or 0,
            call_answered_count=row["call_answered_count"] or 0,
            call_last_timestamp=datetime.fromisoformat(row["call_last_timestamp"])
            if row["call_last_timestamp"]
            else None,
            call_timestamps=call_timestamps,
            chat_sent_count=row["chat_sent_count"] or 0,
            chat_user_replied=bool(row["chat_user_replied"]),
            chat_last_timestamp=datetime.fromisoformat(row["chat_last_timestamp"])
            if row["chat_last_timestamp"]
            else None,
            push_sent_count=row["push_sent_count"] or 0,
        )