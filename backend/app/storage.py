"""Persistent SQLite storage for schedules and webhook delivery state."""

import asyncio
import hashlib
import json
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Optional

from app.config import settings
from app.models import ScheduleRequest, ScheduleResult


@dataclass
class Job:
    job_id: str
    created_at: datetime
    paid: bool
    request: ScheduleRequest
    schedule: Optional[ScheduleResult]
    expires_at: datetime
    stripe_session_id: Optional[str] = None


def _database_path() -> Path:
    directory = Path(settings.jobs_dir)
    directory.mkdir(parents=True, exist_ok=True)
    return directory / "schedule-it.sqlite3"


def _connection() -> sqlite3.Connection:
    connection = sqlite3.connect(_database_path())
    connection.row_factory = sqlite3.Row
    return connection


def initialise_storage() -> None:
    with _connection() as connection:
        connection.executescript("""
            CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY, request_hash TEXT NOT NULL,
                request_json TEXT NOT NULL, result_json TEXT,
                created_at TEXT NOT NULL, expires_at TEXT NOT NULL,
                paid INTEGER NOT NULL DEFAULT 0, stripe_session_id TEXT
            );
            CREATE INDEX IF NOT EXISTS jobs_request_hash_expires_idx
                ON jobs(request_hash, expires_at);
            CREATE INDEX IF NOT EXISTS jobs_expires_at_idx ON jobs(expires_at);
            CREATE TABLE IF NOT EXISTS processed_webhooks (
                event_id TEXT PRIMARY KEY, processed_at TEXT NOT NULL
            );
        """)


def request_hash(request: ScheduleRequest) -> str:
    payload = json.dumps(request.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _now() -> datetime:
    return datetime.now(UTC)


def _deserialize_job(row: sqlite3.Row) -> Job:
    return Job(
        job_id=row["id"], created_at=datetime.fromisoformat(row["created_at"]),
        paid=bool(row["paid"]),
        request=ScheduleRequest.model_validate_json(row["request_json"]),
        schedule=ScheduleResult.model_validate_json(row["result_json"]) if row["result_json"] else None,
        expires_at=datetime.fromisoformat(row["expires_at"]),
        stripe_session_id=row["stripe_session_id"],
    )


def create_job(request: ScheduleRequest, schedule: Optional[ScheduleResult] = None) -> str:
    job_id = str(uuid.uuid4())
    now = _now()
    with _connection() as connection:
        connection.execute(
            """INSERT INTO jobs (id, request_hash, request_json, result_json, created_at, expires_at, paid)
               VALUES (?, ?, ?, ?, ?, ?, 0)""",
            (job_id, request_hash(request), request.model_dump_json(),
             schedule.model_dump_json() if schedule else None, now.isoformat(),
             (now + timedelta(days=settings.data_retention_days)).isoformat()),
        )
    return job_id


def find_cached_job(request: ScheduleRequest) -> Optional[Job]:
    with _connection() as connection:
        row = connection.execute(
            """SELECT * FROM jobs WHERE request_hash = ? AND expires_at > ?
               AND result_json IS NOT NULL ORDER BY created_at DESC LIMIT 1""",
            (request_hash(request), _now().isoformat()),
        ).fetchone()
    return _deserialize_job(row) if row else None


def get_job(job_id: str) -> Optional[Job]:
    with _connection() as connection:
        row = connection.execute("SELECT * FROM jobs WHERE id = ? AND expires_at > ?", (job_id, _now().isoformat())).fetchone()
    return _deserialize_job(row) if row else None


def mark_paid(job_id: str, stripe_session_id: str) -> bool:
    with _connection() as connection:
        updated = connection.execute(
            "UPDATE jobs SET paid = 1, stripe_session_id = ? WHERE id = ? AND expires_at > ?",
            (stripe_session_id, job_id, _now().isoformat()),
        ).rowcount
    return bool(updated)


def record_webhook_event(event_id: str) -> bool:
    """Record an event once; False means Stripe retried an existing delivery."""
    try:
        with _connection() as connection:
            connection.execute("INSERT INTO processed_webhooks (event_id, processed_at) VALUES (?, ?)", (event_id, _now().isoformat()))
        return True
    except sqlite3.IntegrityError:
        return False


def webhook_event_processed(event_id: str) -> bool:
    with _connection() as connection:
        return connection.execute(
            "SELECT 1 FROM processed_webhooks WHERE event_id = ?", (event_id,)
        ).fetchone() is not None


def cleanup_expired() -> int:
    with _connection() as connection:
        return connection.execute("DELETE FROM jobs WHERE expires_at <= ?", (_now().isoformat(),)).rowcount


async def background_cleanup() -> None:
    while True:
        await asyncio.sleep(3600)
        cleanup_expired()


# Make direct storage use (including scripts and tests) safe before FastAPI's
# lifespan handler has started.
initialise_storage()
