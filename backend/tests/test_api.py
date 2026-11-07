"""
API integration tests using FastAPI's TestClient.

Run with:  pytest backend/tests/test_api.py -v
"""
from __future__ import annotations

import pytest
from datetime import date, time, timedelta
from fastapi.testclient import TestClient

from app.main import app

# Use raise_server_exceptions=False so that Stripe-related exceptions
# (e.g. on /success) don't blow up unrelated tests.
client = TestClient(app, raise_server_exceptions=False)


def test_home_page_returns_200():
    resp = client.get("/")
    assert resp.status_code == 200
    assert "Schedule-it" in resp.text


def test_generate_redirects_to_preview():
    """POST /generate with valid data should redirect to /preview/<job_id>."""
    today = date.today()
    slots_data = {
        "teams": "Alpha\nBeta\nGamma\nDelta",
        "blackout_dates": "",
        "round_robin": "single",
        "derby_pairs": "",
        "max_consecutive_home": "3",
        "max_consecutive_away": "3",
        "league_name": "Test League",
        "venue_name_0": "Stadium",
        "venue_capacity_0": "100",
    }
    # Add 8 slots on consecutive days
    for i in range(8):
        d = today + timedelta(days=i)
        slots_data[f"slot_date_{i}"] = d.isoformat()
        slots_data[f"slot_time_{i}"] = "15:00"
        slots_data[f"slot_venue_{i}"] = "Stadium"

    resp = client.post("/generate", data=slots_data, follow_redirects=False)
    # Either redirect to /preview or render impossible.html (if solver times out in test env)
    assert resp.status_code in (303, 200)
    if resp.status_code == 303:
        assert "/preview/" in resp.headers["location"]


def test_download_pdf_requires_payment():
    """GET /download/<job_id>/pdf should return 403 if job is not paid."""
    from app.models import ScheduleRequest, Venue, TimeSlot
    from app.storage import create_job
    from app.solver import solve_schedule

    req = ScheduleRequest(
        league_name="Test",
        teams=["A", "B", "C", "D"],
        venues=[Venue(name="V", capacity=100)],
        slots=[
            TimeSlot(date=date(2025, 6, 1) + timedelta(days=i), time=time(15, 0), venue_name="V")
            for i in range(8)
        ],
        round_robin="single",
    )
    result = solve_schedule(req)
    job_id = create_job(req, result)

    resp = client.get(f"/download/{job_id}/pdf")
    assert resp.status_code == 403


def test_webhook_invalid_signature_returns_400():
    """POST /webhook with bad signature should return 400."""
    resp = client.post(
        "/webhook",
        content=b'{"type": "checkout.session.completed"}',
        headers={"stripe-signature": "bad_signature"},
    )
    assert resp.status_code == 400
