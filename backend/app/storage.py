"""
File-based job storage.

Each job is stored as a JSON file under <jobs_dir>/<job_id>.json.
This keeps the stack dependency-free (no database required) while remaining
straightforward to swap for Redis or Postgres later.

Data retention: a background task (called from the app lifespan) deletes
files older than `data_retention_days` days.
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from .config import get_settings
from .models import JobRecord

logger = logging.getLogger(__name__)


def _jobs_dir() -> Path:
    settings = get_settings()
    path = Path(settings.jobs_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _job_path(job_id: str) -> Path:
    # Sanitise: only allow alphanumeric + hyphens to prevent path traversal
    safe_id = "".join(c for c in job_id if c.isalnum() or c == "-")
    return _jobs_dir() / f"{safe_id}.json"


def save_job(job: JobRecord) -> None:
    """Persist a JobRecord to disk (overwrites if exists)."""
    path = _job_path(job.job_id)
    path.write_text(job.model_dump_json(), encoding="utf-8")


def load_job(job_id: str) -> Optional[JobRecord]:
    """Load a JobRecord from disk. Returns None if not found."""
    path = _job_path(job_id)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return JobRecord(**data)
    except Exception as exc:
        logger.error("Failed to load job %s: %s", job_id, exc)
        return None


def delete_job(job_id: str) -> None:
    """Delete a job file if it exists."""
    path = _job_path(job_id)
    if path.exists():
        path.unlink()


def purge_old_jobs() -> int:
    """
    Delete job files older than `data_retention_days` days.
    Returns the number of files deleted.
    """
    settings = get_settings()
    cutoff = datetime.now(timezone.utc) - timedelta(days=settings.data_retention_days)
    deleted = 0
    for p in _jobs_dir().glob("*.json"):
        try:
            mtime = datetime.fromtimestamp(p.stat().st_mtime, tz=timezone.utc)
            if mtime < cutoff:
                p.unlink()
                deleted += 1
        except Exception as exc:
            logger.warning("Could not purge %s: %s", p, exc)
    logger.info("Purged %d old job files", deleted)
    return deleted
