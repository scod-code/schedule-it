import uuid
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Optional
from dataclasses import dataclass, field
from app.models import ScheduleRequest, ScheduleResult


@dataclass
class Job:
    job_id: str
    created_at: datetime
    paid: bool
    request: ScheduleRequest
    schedule: Optional[ScheduleResult] = None
    expires_at: datetime = field(
        default_factory=lambda: datetime.utcnow() + timedelta(days=30)
    )
    stripe_session_id: Optional[str] = None


jobs: Dict[str, Job] = {}


def create_job(
    request: ScheduleRequest, schedule: Optional[ScheduleResult] = None
) -> str:
    job_id = str(uuid.uuid4())
    jobs[job_id] = Job(
        job_id=job_id,
        created_at=datetime.utcnow(),
        paid=False,
        request=request,
        schedule=schedule,
    )
    return job_id


def get_job(job_id: str) -> Optional[Job]:
    job = jobs.get(job_id)
    if job and datetime.utcnow() > job.expires_at:
        del jobs[job_id]
        return None
    return job


def mark_paid(job_id: str, stripe_session_id: str) -> bool:
    job = get_job(job_id)
    if not job:
        return False
    if not job.paid:
        job.paid = True
        job.stripe_session_id = stripe_session_id
    return True


def cleanup_expired() -> int:
    now = datetime.utcnow()
    expired = [jid for jid, j in jobs.items() if now > j.expires_at]
    for jid in expired:
        del jobs[jid]
    return len(expired)


async def background_cleanup() -> None:
    while True:
        await asyncio.sleep(3600)  # run every hour
        cleanup_expired()
