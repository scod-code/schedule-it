import stripe
from app.config import settings

stripe.api_key = settings.stripe_secret_key


def create_checkout_session(job_id: str) -> str:
    """Creates a Stripe Checkout Session, returns the session URL."""
    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        line_items=[{"price": settings.stripe_price_id, "quantity": 1}],
        mode="payment",
        success_url=f"{settings.base_url}/success?session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{settings.base_url}/preview/{job_id}",
        metadata={"job_id": job_id},
    )
    return session.url


def verify_webhook(payload: bytes, sig_header: str) -> dict:
    """Verifies Stripe webhook signature, returns the event dict."""
    event = stripe.Webhook.construct_event(
        payload, sig_header, settings.stripe_webhook_secret
    )
    return event
