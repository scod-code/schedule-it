"""
FastAPI application entry point.

Routes
------
GET  /                      — landing page / form
POST /solve                 — submit constraints, solve, redirect to preview
GET  /preview/{job_id}      — show free preview (first 3 fixtures) + pay button
POST /pay/{job_id}          — create Stripe Checkout Session, redirect
GET  /success               — post-payment landing; verifies session, unlocks downloads
GET  /download/{job_id}/pdf — download full PDF (paid jobs only)
GET  /download/{job_id}/csv — download full CSV (paid jobs only)
GET  /download/{job_id}/ics/{team} — download ICS for one team (paid jobs only)
POST /webhook               — Stripe webhook
GET  /impossible/{job_id}   — shown when constraints are infeasible
GET  /privacy               — privacy policy
GET  /terms                 — terms of service
GET  /refund                — refund policy
"""
from __future__ import annotations

import logging
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from urllib.parse import quote

from fastapi import BackgroundTasks, FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .config import get_settings
from .exporter import to_csv, to_ics_per_team, to_pdf
from .models import JobRecord, JobStatus, RoundRobinType, ScheduleRequest, Team, TimeSlot, Venue
from .payments import create_checkout_session, handle_webhook
from .solver import solve
from .storage import load_job, purge_old_jobs, save_job

logger = logging.getLogger(__name__)

BASE_DIR = __import__("pathlib").Path(__file__).resolve().parent.parent


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Purge old jobs on startup
    purge_old_jobs()
    yield


app = FastAPI(title="Schedule-it", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _require_paid_job(job_id: str) -> JobRecord:
    job = load_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status != JobStatus.paid:
        raise HTTPException(status_code=402, detail="Payment required")
    return job


# ---------------------------------------------------------------------------
# Pages
# ---------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/solve", response_class=HTMLResponse)
async def solve_route(
    request: Request,
    background_tasks: BackgroundTasks,
    league_name: str = Form(...),
    teams_raw: str = Form(..., alias="teams"),
    venues_raw: str = Form(..., alias="venues"),
    slots_raw: str = Form(..., alias="slots"),
    round_robin: str = Form("single"),
    max_consecutive: int = Form(3),
):
    """
    Parse the submitted form, run the solver, persist the job, redirect to
    /preview or /impossible.

    Form fields (all plain text, newline-separated):
      teams   — "TeamName,HomeVenue[,blackout_date1,blackout_date2,...]" one per line
      venues  — "VenueName[,capacity]" one per line
      slots   — "SlotLabel,YYYY-MM-DD" one per line
    """
    settings = get_settings()
    job_id = str(uuid.uuid4())

    # --- Parse teams ---
    team_list: list[Team] = []
    for line in teams_raw.strip().splitlines():
        parts = [p.strip() for p in line.split(",")]
        if len(parts) < 2:
            continue
        team_list.append(
            Team(
                name=parts[0],
                home_venue=parts[1],
                blackout_dates=parts[2:] if len(parts) > 2 else [],
            )
        )

    # --- Parse venues ---
    venue_list: list[Venue] = []
    for line in venues_raw.strip().splitlines():
        parts = [p.strip() for p in line.split(",")]
        if not parts[0]:
            continue
        cap = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 1
        venue_list.append(Venue(name=parts[0], capacity=cap))

    # --- Parse slots ---
    slot_list: list[TimeSlot] = []
    for line in slots_raw.strip().splitlines():
        parts = [p.strip() for p in line.split(",")]
        if len(parts) < 2:
            continue
        slot_list.append(TimeSlot(label=parts[0], date=parts[1]))

    if not team_list or not venue_list or not slot_list:
        raise HTTPException(status_code=422, detail="Teams, venues, and slots are all required.")

    sched_request = ScheduleRequest(
        league_name=league_name,
        teams=team_list,
        venues=venue_list,
        slots=slot_list,
        round_robin=RoundRobinType(round_robin),
        max_consecutive_home_away=max_consecutive,
    )

    # Run the solver (synchronous; fast enough for the 10-second limit)
    result = solve(sched_request, job_id, time_limit=settings.solver_time_limit_seconds)

    status = JobStatus.solved if result.metrics.feasible else JobStatus.impossible

    job = JobRecord(
        job_id=job_id,
        status=status,
        request=sched_request,
        result=result,
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    save_job(job)

    if not result.metrics.feasible:
        return RedirectResponse(f"/impossible/{job_id}", status_code=303)
    return RedirectResponse(f"/preview/{job_id}", status_code=303)


@app.get("/preview/{job_id}", response_class=HTMLResponse)
async def preview(request: Request, job_id: str):
    job = load_job(job_id)
    if job is None or job.result is None:
        raise HTTPException(status_code=404, detail="Job not found")

    # Show only the first 3 fixtures as the free preview
    preview_matches = job.result.matches[:3]
    total_matches = len(job.result.matches)
    paid = job.status == JobStatus.paid

    return templates.TemplateResponse(
        "preview.html",
        {
            "request": request,
            "job": job,
            "preview_matches": preview_matches,
            "total_matches": total_matches,
            "paid": paid,
            "metrics": job.result.metrics,
        },
    )


@app.post("/pay/{job_id}")
async def pay(job_id: str):
    job = load_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status == JobStatus.paid:
        return RedirectResponse(f"/preview/{job_id}", status_code=303)
    if job.status != JobStatus.solved:
        raise HTTPException(status_code=400, detail="Job is not in a payable state")

    checkout_url = create_checkout_session(job_id)
    return RedirectResponse(checkout_url, status_code=303)


@app.get("/success", response_class=HTMLResponse)
async def success(request: Request, session_id: str):
    # Find job by stripe session id
    # (Webhook is the authoritative mark-as-paid path; this page just gives
    #  the user a nice confirmation and download links.)
    from .storage import _jobs_dir
    job = None
    for p in _jobs_dir().glob("*.json"):
        candidate = load_job(p.stem)
        if candidate and candidate.stripe_session_id == session_id:
            job = candidate
            break

    if job is None:
        raise HTTPException(status_code=404, detail="Session not found")

    # Ensure job is marked paid (in case webhook hasn't arrived yet)
    if job.status != JobStatus.paid:
        job.status = JobStatus.paid
        job.paid_at = datetime.now(timezone.utc).isoformat()
        save_job(job)

    teams = [m.home_team for m in (job.result.matches if job.result else [])]
    # Deduplicate while preserving order
    seen: set[str] = set()
    unique_teams: list[str] = []
    if job.result:
        for m in job.result.matches:
            for t in (m.home_team, m.away_team):
                if t not in seen:
                    seen.add(t)
                    unique_teams.append(t)

    return templates.TemplateResponse(
        "success.html",
        {
            "request": request,
            "job": job,
            "teams": unique_teams,
        },
    )


@app.get("/impossible/{job_id}", response_class=HTMLResponse)
async def impossible(request: Request, job_id: str):
    job = load_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return templates.TemplateResponse("impossible.html", {"request": request, "job": job})


# ---------------------------------------------------------------------------
# Downloads (paid only)
# ---------------------------------------------------------------------------

@app.get("/download/{job_id}/pdf")
async def download_pdf(job_id: str):
    job = _require_paid_job(job_id)
    assert job.result is not None
    pdf_bytes = to_pdf(job.result)
    filename = f"{job.result.league_name.replace(' ', '_')}_fixtures.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.get("/download/{job_id}/csv")
async def download_csv(job_id: str):
    job = _require_paid_job(job_id)
    assert job.result is not None
    csv_bytes = to_csv(job.result)
    filename = f"{job.result.league_name.replace(' ', '_')}_fixtures.csv"
    return Response(
        content=csv_bytes,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.get("/download/{job_id}/ics/{team_name}")
async def download_ics(job_id: str, team_name: str):
    job = _require_paid_job(job_id)
    assert job.result is not None
    calendars = to_ics_per_team(job.result)
    if team_name not in calendars:
        raise HTTPException(status_code=404, detail="Team not found")
    filename = f"{team_name.replace(' ', '_')}_fixtures.ics"
    return Response(
        content=calendars[team_name],
        media_type="text/calendar",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ---------------------------------------------------------------------------
# Stripe webhook
# ---------------------------------------------------------------------------

@app.post("/webhook")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")
    result = handle_webhook(payload, sig_header)
    if result["status"] == "invalid_signature":
        raise HTTPException(status_code=400, detail="Invalid signature")
    return {"received": True}


# ---------------------------------------------------------------------------
# Static policy pages
# ---------------------------------------------------------------------------

@app.get("/privacy", response_class=HTMLResponse)
async def privacy(request: Request):
    return templates.TemplateResponse("privacy.html", {"request": request})


@app.get("/terms", response_class=HTMLResponse)
async def terms(request: Request):
    return templates.TemplateResponse("terms.html", {"request": request})


@app.get("/refund", response_class=HTMLResponse)
async def refund(request: Request):
    return templates.TemplateResponse("refund.html", {"request": request})
