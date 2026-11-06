"""
Stripe payment helpers.

Flow:
  1. POST /pay/{job_id}        → creates a Checkout Session, redirects user to Stripe
  2. Stripe redirects to       → GET /success?session_id=...
  3. Stripe posts webhook to   → POST /webhook  (server-side confirmation, idempotent)
"""
from __future__ import annotations

import logging

import stripe

from .config import get_settings
from .storage import load_job, save_job
from .models import JobStatus

logger = logging.getLogger(__name__)


def create_checkout_session(job_id: str) -> str:
    """
    Create a Stripe Checkout Session for a solved job.
    Returns the session URL to redirect the user to.
    """
    settings = get_settings()
    stripe.api_key = settings.stripe_secret_key

    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        line_items=[
            {
                "price": settings.stripe_price_id,
                "quantity": 1,
            }
        ],
        mode="payment",
        success_url=f"{settings.app_base_url}/success?session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{settings.app_base_url}/preview/{job_id}",
        metadata={"job_id": job_id},
    )

    # Persist the session id so the webhook can look up the job
    job = load_job(job_id)
    if job:
        job.stripe_session_id = session.id
        save_job(job)

    return session.url  # type: ignore[return-value]


def handle_webhook(payload: bytes, sig_header: str) -> dict:
    """
    Verify the Stripe webhook signature and process the event.
    Returns a dict with "status" key for the HTTP response.
    Idempotent: calling it twice for the same session is safe.
    """
    settings = get_settings()
    stripe.api_key = settings.stripe_secret_key

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.stripe_webhook_secret
        )
    except stripe.error.SignatureVerificationError as exc:
        logger.warning("Stripe webhook signature verification failed: %s", exc)
        return {"status": "invalid_signature"}
    except Exception as exc:
        logger.error("Stripe webhook error: %s", exc)
        return {"status": "error"}

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        job_id = session.get("metadata", {}).get("job_id")
        if job_id:
            _mark_paid(job_id, session["id"])

    return {"status": "ok"}


def _mark_paid(job_id: str, session_id: str) -> None:
    """Mark a job as paid exactly once."""
    from datetime import datetime, timezone

    job = load_job(job_id)
    if job is None:
        logger.error("Webhook: job %s not found", job_id)
        return
    if job.status == JobStatus.paid:
        logger.info("Webhook: job %s already marked paid, skipping", job_id)
        return

    job.status = JobStatus.paid
    job.paid_at = datetime.now(timezone.utc).isoformat()
    save_job(job)
    logger.info("Job %s marked as paid via session %s", job_id, session_id)
