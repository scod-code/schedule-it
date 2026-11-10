import re
import urllib.parse
import asyncio
from contextlib import asynccontextmanager
from typing import Optional

import stripe
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse, Response
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.models import ScheduleRequest
from app.storage import (
    create_job, find_cached_job, get_job, mark_paid, record_webhook_event,
    background_cleanup, initialise_storage,
)
from app.solver import solve_schedule
from app.exporter import generate_pdf, generate_csv, generate_ics_per_team
from app.payments import create_checkout_session, verify_webhook


# ---------------------------------------------------------------------------
# Lifespan: start background cleanup and configure Stripe
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    initialise_storage()
    asyncio.create_task(background_cleanup())
    stripe.api_key = settings.stripe_secret_key
    yield


app = FastAPI(lifespan=lifespan)

# Add CORS middleware for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/")
async def root():
    """Root route for API info."""
    return {"message": "Schedule-it API", "docs": "/docs"}


@app.post("/api/generate")
async def generate(request: ScheduleRequest):
    """
    Generate a schedule from a ScheduleRequest.
    Returns job_id, status, preview, and teams if successful.
    Returns 422 with infeasibility reason if schedule cannot be generated.
    """
    # Check for cached job
    cached_job = find_cached_job(request)
    if cached_job:
        return {
            "job_id": cached_job.job_id,
            "status": "cached",
        }
    
    # Solve schedule in background thread (CPU-bound)
    result = await asyncio.to_thread(solve_schedule, request)
    
    # Check if infeasible
    if result.metrics.status == "INFEASIBLE":
        return JSONResponse(
            status_code=422,
            content={
                "status": "infeasible",
                "reason": result.infeasibility_reason,
            }
        )
    
    # Create job and return preview
    job_id = create_job(request=request, schedule=result)
    
    # Build preview: first 5 rounds
    preview_matches = [m for m in result.matches if m.round_num <= 5]
    remaining_count = result.total_matches - len(preview_matches)
    
    return {
        "job_id": job_id,
        "status": "generated",
        "preview": {
            "matches": [m.model_dump() for m in preview_matches],
            "remaining_count": remaining_count,
            "quality_metrics": result.metrics.model_dump(),
        },
        "teams": request.teams,
    }


@app.get("/api/jobs/{job_id}")
async def get_job_info(job_id: str):
    """Get job metadata by job_id."""
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found or expired")
    
    return {
        "job_id": job.job_id,
        "paid": job.paid,
        "teams": job.request.teams,
        "created_at": job.created_at.isoformat(),
    }


@app.post("/api/checkout/{job_id}")
async def checkout(job_id: str):
    """Create a Stripe checkout session for a job."""
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found or expired")
    
    checkout_url = create_checkout_session(job_id)
    return {"checkout_url": checkout_url}


@app.post("/webhook")
async def webhook(request: Request):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    try:
        event = verify_webhook(payload, sig_header)
    except (ValueError, stripe.error.SignatureVerificationError):
        raise HTTPException(status_code=400, detail="Invalid webhook signature")

    event_id = event.get("id")
    if event_id:
        # A successful prior delivery can be acknowledged immediately. New
        # events are recorded only after their side effects complete, so a
        # transient database error does not permanently consume the retry.
        from app.storage import webhook_event_processed
        if webhook_event_processed(event_id):
            return {"status": "already_processed"}

    if event["type"] == "checkout.session.completed":
        session_obj = event["data"]["object"]
        job_id = session_obj["metadata"]["job_id"]
        session_id = session_obj["id"]
        mark_paid(job_id, session_id)

    if event_id:
        record_webhook_event(event_id)

    return {"status": "ok"}


@app.get("/api/download/{job_id}/pdf")
async def download_pdf(job_id: str):
    """Download schedule as PDF (requires payment)."""
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found or expired")

    if not job.paid:
        raise HTTPException(status_code=403, detail="Payment required")

    content = generate_pdf(job.schedule)
    return Response(
        content=content,
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="schedule.pdf"'},
    )


@app.get("/api/download/{job_id}/csv")
async def download_csv(job_id: str):
    """Download schedule as CSV (requires payment)."""
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found or expired")

    if not job.paid:
        raise HTTPException(status_code=403, detail="Payment required")

    content = generate_csv(job.schedule)
    return Response(
        content=content,
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="schedule.csv"'},
    )


@app.get("/api/download/{job_id}/ics/{team_name}")
async def download_ics(job_id: str, team_name: str):
    """Download schedule as ICS for a specific team (requires payment)."""
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found or expired")

    if not job.paid:
        raise HTTPException(status_code=403, detail="Payment required")

    ics_files = generate_ics_per_team(job.schedule)
    if team_name not in ics_files:
        raise HTTPException(status_code=404, detail=f"Team '{team_name}' not found")
    
    content = ics_files[team_name]
    # Sanitise team_name before embedding in the Content-Disposition header.
    # Strip every character outside the safe ASCII set to prevent header
    # injection via a crafted team name (e.g. one containing '"' or ';\n').
    safe_team = re.sub(r'[^A-Za-z0-9 _\-]', '_', team_name)
    return Response(
        content=content,
        media_type="text/calendar",
        headers={"Content-Disposition": f'attachment; filename="{safe_team}.ics"'},
    )
