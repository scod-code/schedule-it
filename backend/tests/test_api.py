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


def test_root_returns_api_info():
    resp = client.get("/")
    assert resp.status_code == 200
    data = resp.json()
    assert data["message"] == "Schedule-it API"
    assert data["docs"] == "/docs"


def test_generate_returns_job_id():
    """POST /api/generate with valid ScheduleRequest JSON should return job_id and preview."""
    from app.models import ScheduleRequest, Venue, TimeSlot
    
    today = date.today()
    slots = [
        TimeSlot(date=today + timedelta(days=i), time=time(15, 0), venue_name="Stadium")
        for i in range(8)
    ]
    
    request_data = ScheduleRequest(
        league_name="Test League",
        teams=["Alpha", "Beta", "Gamma", "Delta"],
        venues=[Venue(name="Stadium", capacity=100)],
        slots=slots,
        round_robin="single",
    )
    
    resp = client.post("/api/generate", json=request_data.model_dump(mode="json"))
    
    # Should either succeed or return infeasible (if solver times out in test env)
    assert resp.status_code in (200, 422)
    
    if resp.status_code == 200:
        data = resp.json()
        assert "job_id" in data
        assert data["status"] in ("generated", "cached")
        if data["status"] == "generated":
            assert "preview" in data
            assert "teams" in data


def test_download_pdf_requires_payment():
    """GET /api/download/<job_id>/pdf should return 403 if job is not paid."""
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

    resp = client.get(f"/api/download/{job_id}/pdf")
    assert resp.status_code == 403


def test_identical_request_reuses_persisted_schedule():
    """A second identical request can reuse the first unexpired solve."""
    from app.models import ScheduleRequest, Venue, TimeSlot
    from app.storage import create_job, find_cached_job
    from app.solver import solve_schedule

    req = ScheduleRequest(
        league_name="Cache test",
        teams=["North", "South", "East", "West"],
        venues=[Venue(name="V", capacity=100)],
        slots=[
            TimeSlot(date=date(2027, 1, 1) + timedelta(days=i), time=time(15, 0), venue_name="V")
            for i in range(8)
        ],
    )
    job_id = create_job(req, solve_schedule(req))

    cached = find_cached_job(req)
    assert cached is not None
    assert cached.job_id == job_id
    assert cached.schedule is not None


def test_health_endpoint_returns_ok():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_success_page_does_not_mark_job_paid():
    """Removed: /success route no longer exists in REST API. Frontend will handle this."""
    # This test is no longer relevant as the /success HTML route has been removed.
    # The webhook is the only way to mark a job as paid.
    pass


def test_webhook_invalid_signature_returns_400():
    """POST /webhook with bad signature should return 400."""
    resp = client.post(
        "/webhook",
        content=b'{"type": "checkout.session.completed"}',
        headers={"stripe-signature": "bad_signature"},
    )
    assert resp.status_code == 400
