import urllib.parse
import asyncio
from contextlib import asynccontextmanager
from datetime import date, time
from typing import Optional, List

import stripe
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError

from app.config import settings
from app.models import ScheduleRequest, Venue, TimeSlot
from app.storage import create_job, get_job, mark_paid, background_cleanup
from app.solver import solve_schedule
from app.exporter import generate_pdf, generate_csv, generate_ics_per_team
from app.payments import create_checkout_session, verify_webhook


# ---------------------------------------------------------------------------
# Lifespan: start background cleanup and configure Stripe
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    asyncio.create_task(background_cleanup())
    stripe.api_key = settings.stripe_secret_key
    yield


app = FastAPI(lifespan=lifespan)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(
        "index.html", {"request": request, "venue_count": 1, "slot_count": 1}
    )


@app.get("/htmx/venue-row", response_class=HTMLResponse)
async def htmx_venue_row(index: int):
    html = f"""<div class="venue-row" id="venue-row-{index}">
  <input type="text" name="venue_name_{index}" placeholder="Venue name" required class="input-field">
  <input type="number" name="venue_capacity_{index}" placeholder="Capacity" min="1" value="100" class="input-field input-small">
  <button type="button" class="btn-remove" onclick="this.closest('.venue-row').remove()">✕</button>
</div>"""
    return HTMLResponse(html)


@app.get("/htmx/slot-row", response_class=HTMLResponse)
async def htmx_slot_row(index: int):
    html = f"""<div class="slot-row" id="slot-row-{index}">
  <input type="date" name="slot_date_{index}" required class="input-field">
  <input type="time" name="slot_time_{index}" required class="input-field">
  <input type="text" name="slot_venue_{index}" placeholder="Venue name" required class="input-field">
  <button type="button" class="btn-remove" onclick="this.closest('.slot-row').remove()">✕</button>
</div>"""
    return HTMLResponse(html)


@app.post("/generate")
async def generate(request: Request):
    form = await request.form()

    # --- Teams ---
    teams_raw: str = form.get("teams", "")
    teams: List[str] = [t.strip() for t in teams_raw.splitlines() if t.strip()]

    # --- Blackout dates ---
    blackout_raw: str = form.get("blackout_dates", "")
    blackout_dates: List[date] = []
    for line in blackout_raw.splitlines():
        line = line.strip()
        if line:
            try:
                blackout_dates.append(date.fromisoformat(line))
            except ValueError:
                pass  # skip malformed dates

    # --- Round robin type ---
    round_robin: str = form.get("round_robin", "single")
    if round_robin not in ("single", "double"):
        round_robin = "single"

    # --- Derby pairs ---
    derby_raw: str = form.get("derby_pairs", "")
    derby_pairs: List[tuple] = []
    for line in derby_raw.splitlines():
        line = line.strip()
        if " vs " in line:
            parts = line.split(" vs ", 1)
            a, b = parts[0].strip(), parts[1].strip()
            if a and b:
                derby_pairs.append((a, b))

    # --- Consecutive limits ---
    try:
        max_consecutive_home = int(form.get("max_consecutive_home", 3))
    except (ValueError, TypeError):
        max_consecutive_home = 3

    try:
        max_consecutive_away = int(form.get("max_consecutive_away", 3))
    except (ValueError, TypeError):
        max_consecutive_away = 3

    # --- Venues ---
    venues: List[Venue] = []
    i = 0
    while f"venue_name_{i}" in form:
        name = form.get(f"venue_name_{i}", "").strip()
        if name:
            try:
                capacity = int(form.get(f"venue_capacity_{i}", 100))
            except (ValueError, TypeError):
                capacity = 100
            venues.append(Venue(name=name, capacity=capacity))
        i += 1

    # --- Time slots ---
    slots: List[TimeSlot] = []
    i = 0
    while f"slot_date_{i}" in form:
        slot_date_str = form.get(f"slot_date_{i}", "").strip()
        slot_time_str = form.get(f"slot_time_{i}", "").strip()
        slot_venue_str = form.get(f"slot_venue_{i}", "").strip()
        if slot_date_str and slot_time_str and slot_venue_str:
            try:
                parsed_date = date.fromisoformat(slot_date_str)
                parsed_time = time.fromisoformat(slot_time_str)
                slots.append(TimeSlot(
                    date=parsed_date,
                    time=parsed_time,
                    venue_name=slot_venue_str,
                ))
            except ValueError:
                pass  # skip malformed slots
        i += 1

    # --- Build and validate ScheduleRequest ---
    try:
        req = ScheduleRequest(
            teams=teams,
            venues=venues,
            slots=slots,
            round_robin=round_robin,
            blackout_dates=blackout_dates,
            max_consecutive_home=max_consecutive_home,
            max_consecutive_away=max_consecutive_away,
            derby_pairs=derby_pairs,
        )
    except ValidationError as exc:
        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "error": str(exc),
                "venue_count": max(len(venues), 1),
                "slot_count": max(len(slots), 1),
            },
            status_code=400,
        )

    # --- Solve ---
    result = solve_schedule(req)

    if result.metrics.status == "INFEASIBLE":
        return templates.TemplateResponse(
            "impossible.html",
            {"request": request, "reason": result.infeasibility_reason},
        )

    # --- Store job and redirect to preview ---
    job_id = create_job(request=req, schedule=result)
    return RedirectResponse(f"/preview/{job_id}", status_code=303)


@app.get("/preview/{job_id}", response_class=HTMLResponse)
async def preview(request: Request, job_id: str):
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found or expired")

    preview_matches = [m for m in job.schedule.matches if m.round_num <= 5]
    remaining = job.schedule.total_matches - len(preview_matches)

    return templates.TemplateResponse(
        "preview.html",
        {
            "request": request,
            "job": job,
            "preview_matches": preview_matches,
            "remaining": remaining,
            "metrics": job.schedule.metrics,
        },
    )


@app.get("/checkout/{job_id}")
async def checkout(job_id: str):
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found or expired")

    url = create_checkout_session(job_id)
    return RedirectResponse(url, status_code=303)


@app.post("/webhook")
async def webhook(request: Request):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    try:
        event = verify_webhook(payload, sig_header)
    except (ValueError, stripe.error.SignatureVerificationError):
        raise HTTPException(status_code=400, detail="Invalid webhook signature")

    if event["type"] == "checkout.session.completed":
        session_obj = event["data"]["object"]
        job_id = session_obj["metadata"]["job_id"]
        session_id = session_obj["id"]
        mark_paid(job_id, session_id)

    return {"status": "ok"}


@app.get("/success", response_class=HTMLResponse)
async def success(request: Request, session_id: str):
    session = stripe.checkout.Session.retrieve(session_id)
    job_id = session.metadata["job_id"]

    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found or expired")

    if not job.paid:
        mark_paid(job.job_id, session_id)

    return templates.TemplateResponse(
        "success.html",
        {
            "request": request,
            "job": job,
            "teams": job.request.teams,
        },
    )


@app.get("/download/{job_id}/{format:path}")
async def download(job_id: str, format: str):
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found or expired")

    if not job.paid:
        raise HTTPException(status_code=403, detail="Payment required")

    if format == "pdf":
        content = generate_pdf(job.schedule)
        media_type = "application/pdf"
        filename = "schedule.pdf"

    elif format == "csv":
        content = generate_csv(job.schedule)
        media_type = "text/csv"
        filename = "schedule.csv"

    elif format.startswith("ics/"):
        team_name = urllib.parse.unquote(format[4:])
        ics_files = generate_ics_per_team(job.schedule)
        if team_name not in ics_files:
            raise HTTPException(status_code=404, detail=f"Team '{team_name}' not found")
        content = ics_files[team_name]
        media_type = "text/calendar"
        filename = f"{team_name}.ics"

    else:
        raise HTTPException(status_code=404, detail="Unknown download format")

    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.get("/privacy", response_class=HTMLResponse)
async def privacy(request: Request):
    return templates.TemplateResponse("privacy.html", {"request": request})


@app.get("/terms", response_class=HTMLResponse)
async def terms(request: Request):
    return templates.TemplateResponse("terms.html", {"request": request})


@app.get("/refund", response_class=HTMLResponse)
async def refund(request: Request):
    return templates.TemplateResponse("refund.html", {"request": request})
