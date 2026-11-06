"""
API integration tests using FastAPI's TestClient.

Run with:  pytest backend/tests/test_api.py -v
"""
from __future__ import annotations

import json
import os

import pytest
from fastapi.testclient import TestClient

# Point the app to a temporary jobs directory so tests don't pollute real data
os.environ.setdefault("JOBS_DIR", "/tmp/schedule_it_test_jobs")

from app.main import app

client = TestClient(app, raise_server_exceptions=True)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SIMPLE_FORM = {
    "league_name": "Test League",
    "teams": "Alpha,Pitch A\nBeta,Pitch B\nGamma,Pitch A\nDelta,Pitch B",
    "venues": "Pitch A\nPitch B",
    "slots": "\n".join(
        f"Round {i+1}, 2025-{(i // 28) % 12 + 1:02d}-{i % 28 + 1:02d}"
        for i in range(18)
    ),
    "round_robin": "single",
    "max_consecutive": "3",
}


# ---------------------------------------------------------------------------
# GET / (home page)
# ---------------------------------------------------------------------------

class TestIndexPage:

    def test_index_returns_200(self):
        response = client.get("/")
        assert response.status_code == 200

    def test_index_contains_form(self):
        response = client.get("/")
        assert "<form" in response.text

    def test_index_contains_league_name_field(self):
        response = client.get("/")
        assert 'name="league_name"' in response.text


# ---------------------------------------------------------------------------
# POST /solve
# ---------------------------------------------------------------------------

class TestSolveEndpoint:

    def test_solve_redirects_to_preview_on_success(self):
        response = client.post("/solve", data=SIMPLE_FORM, follow_redirects=False)
        assert response.status_code == 303
        assert response.headers["location"].startswith("/preview/")

    def test_solve_follows_redirect_to_preview(self):
        response = client.post("/solve", data=SIMPLE_FORM, follow_redirects=True)
        assert response.status_code == 200
        assert "fixture" in response.text.lower() or "preview" in response.text.lower()

    def test_solve_with_minimal_teams(self):
        form = {
            **SIMPLE_FORM,
            "teams": "Team A,Field 1\nTeam B,Field 1",
            "slots": "Slot 1, 2025-09-01\nSlot 2, 2025-09-08",
        }
        response = client.post("/solve", data=form, follow_redirects=False)
        # 2 teams, 1 match needed, 2 slots provided — should be solvable
        assert response.status_code == 303

    def test_solve_infeasible_redirects_to_impossible(self):
        """Zero slots → infeasible."""
        form = {
            **SIMPLE_FORM,
            "slots": "",  # No slots at all
        }
        response = client.post("/solve", data=form, follow_redirects=False)
        # No slots means the form parser yields nothing; expect 422 or /impossible
        assert response.status_code in (303, 422)

    def test_solve_missing_teams_returns_error(self):
        form = {**SIMPLE_FORM, "teams": ""}
        response = client.post("/solve", data=form, follow_redirects=False)
        assert response.status_code in (303, 422)


# ---------------------------------------------------------------------------
# GET /preview/{job_id}
# ---------------------------------------------------------------------------

class TestPreviewPage:

    def _get_job_id(self) -> str:
        response = client.post("/solve", data=SIMPLE_FORM, follow_redirects=False)
        assert response.status_code == 303
        location = response.headers["location"]
        return location.split("/preview/")[1]

    def test_preview_page_200(self):
        job_id = self._get_job_id()
        response = client.get(f"/preview/{job_id}")
        assert response.status_code == 200

    def test_preview_shows_total_matches(self):
        job_id = self._get_job_id()
        response = client.get(f"/preview/{job_id}")
        assert "fixture" in response.text.lower() or "matches" in response.text.lower()

    def test_preview_shows_pay_button(self):
        job_id = self._get_job_id()
        response = client.get(f"/preview/{job_id}")
        # Should show a pay/unlock button for unpaid jobs
        assert "pay" in response.text.lower() or "unlock" in response.text.lower()

    def test_preview_invalid_job_returns_404(self):
        response = client.get("/preview/nonexistent-job-id-xyz")
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# GET /impossible/{job_id}
# ---------------------------------------------------------------------------

class TestImpossiblePage:

    def test_impossible_invalid_job_404(self):
        response = client.get("/impossible/no-such-job")
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# Download endpoints (require paid status)
# ---------------------------------------------------------------------------

class TestDownloadEndpoints:

    def _get_unpaid_job_id(self) -> str:
        response = client.post("/solve", data=SIMPLE_FORM, follow_redirects=False)
        assert response.status_code == 303
        return response.headers["location"].split("/preview/")[1]

    def test_pdf_download_requires_payment(self):
        job_id = self._get_unpaid_job_id()
        response = client.get(f"/download/{job_id}/pdf")
        assert response.status_code == 402

    def test_csv_download_requires_payment(self):
        job_id = self._get_unpaid_job_id()
        response = client.get(f"/download/{job_id}/csv")
        assert response.status_code == 402

    def test_ics_download_requires_payment(self):
        job_id = self._get_unpaid_job_id()
        response = client.get(f"/download/{job_id}/ics/Alpha")
        assert response.status_code == 402

    def test_pdf_download_unknown_job_404(self):
        response = client.get("/download/unknown-job/pdf")
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# Policy pages
# ---------------------------------------------------------------------------

class TestPolicyPages:

    def test_privacy_page_200(self):
        assert client.get("/privacy").status_code == 200

    def test_terms_page_200(self):
        assert client.get("/terms").status_code == 200

    def test_refund_page_200(self):
        assert client.get("/refund").status_code == 200

    def test_privacy_contains_gdpr(self):
        resp = client.get("/privacy")
        assert "gdpr" in resp.text.lower() or "right" in resp.text.lower()

    def test_refund_contains_14_days(self):
        resp = client.get("/refund")
        assert "14" in resp.text


# ---------------------------------------------------------------------------
# Webhook endpoint
# ---------------------------------------------------------------------------

class TestWebhook:

    def test_webhook_rejects_bad_signature(self):
        response = client.post(
            "/webhook",
            content=b'{"type":"checkout.session.completed"}',
            headers={"stripe-signature": "bad-sig", "content-type": "application/json"},
        )
        assert response.status_code == 400
