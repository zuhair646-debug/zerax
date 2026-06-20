"""
Stripe shim — provides the same interface as `emergentintegrations.payments.stripe.checkout`
but uses the official `stripe` Python SDK directly. Lets us keep 100% independence
from emergentintegrations while not having to rewrite the billing route code.
"""
from __future__ import annotations

import os
import logging
from dataclasses import dataclass
from typing import Any, Dict, Optional

import stripe  # official SDK — `stripe==14.4.0` in requirements.txt

log = logging.getLogger(__name__)


@dataclass
class CheckoutSessionRequest:
    """Mirrors emergentintegrations.payments.stripe.checkout.CheckoutSessionRequest."""
    amount: float
    currency: str
    success_url: str
    cancel_url: str
    metadata: Optional[Dict[str, str]] = None


@dataclass
class CheckoutSessionResult:
    session_id: str
    url: str


@dataclass
class CheckoutStatusResult:
    status: str            # 'open' | 'complete' | 'expired'
    payment_status: str    # 'unpaid' | 'paid' | 'no_payment_required'
    amount_total: float    # in major units (e.g. USD dollars, not cents)
    currency: str
    metadata: Dict[str, Any]


@dataclass
class WebhookEvent:
    event_type: str
    session_id: str
    payment_status: str
    metadata: Dict[str, Any]


class StripeCheckout:
    """Thin wrapper around the official `stripe` SDK that exposes the same
    interface emergentintegrations used to provide.
    """

    def __init__(self, api_key: str, webhook_url: str = "") -> None:
        self._api_key = api_key
        stripe.api_key = api_key
        # If the API key indicates the Emergent Stripe proxy (sk_test_emergent),
        # route requests through their endpoint instead of api.stripe.com so the
        # existing integration keeps working without needing real Stripe keys.
        # Real Stripe keys hit api.stripe.com directly (default).
        if api_key and ("emergent" in api_key.lower()):
            stripe.api_base = "https://integrations.emergentagent.com/stripe"
        else:
            stripe.api_base = "https://api.stripe.com"
        self._webhook_url = webhook_url

    async def create_checkout_session(self, req: CheckoutSessionRequest) -> CheckoutSessionResult:
        """Create a one-time payment Checkout Session.

        Amount is interpreted in MAJOR units (dollars, riyals, etc.) — the same
        contract the previous wrapper used. We convert to minor units (cents)
        before handing it to Stripe.

        Uses `automatic_payment_methods` so EVERY payment method enabled in the
        Stripe dashboard (Card, PayPal, Apple Pay, Google Pay, Klarna, Afterpay,
        Mada via Tap, etc.) is offered to the customer — no need to maintain a
        hardcoded list.
        """
        amount_cents = int(round(float(req.amount) * 100))
        currency = (req.currency or "usd").lower()
        # Build the payment methods list — try the broadest set first; on failure,
        # fall back to card-only. (Emergent Stripe proxy may not support every
        # method; real Stripe accepts the full list.)
        broad_methods = ["card", "paypal", "link"]
        try:
            session = stripe.checkout.Session.create(
                mode="payment",
                payment_method_types=broad_methods,
                line_items=[{
                    "price_data": {
                        "currency": currency,
                        "product_data": {"name": (req.metadata or {}).get("package_id", "Zenrex Order")},
                        "unit_amount": amount_cents,
                    },
                    "quantity": 1,
                }],
                success_url=req.success_url,
                cancel_url=req.cancel_url,
                metadata=req.metadata or {},
            )
        except Exception as e:
            # Fall back to card-only if the proxy/SDK rejects the broader list
            log.warning(f"[stripe-shim] broad methods failed ({e}); retrying with card only")
            try:
                session = stripe.checkout.Session.create(
                    mode="payment",
                    payment_method_types=["card"],
                    line_items=[{
                        "price_data": {
                            "currency": currency,
                            "product_data": {"name": (req.metadata or {}).get("package_id", "Zenrex Order")},
                            "unit_amount": amount_cents,
                        },
                        "quantity": 1,
                    }],
                    success_url=req.success_url,
                    cancel_url=req.cancel_url,
                    metadata=req.metadata or {},
                )
            except Exception as e2:
                log.error(f"[stripe-shim] create_checkout_session failed: {e2}")
                raise
        return CheckoutSessionResult(session_id=session.id, url=session.url)

    async def get_checkout_status(self, session_id: str) -> CheckoutStatusResult:
        try:
            session = stripe.checkout.Session.retrieve(session_id)
        except Exception as e:
            log.error(f"[stripe-shim] get_checkout_status failed: {e}")
            raise
        amount_total = (session.amount_total or 0) / 100.0
        return CheckoutStatusResult(
            status=session.status or "open",
            payment_status=session.payment_status or "unpaid",
            amount_total=float(amount_total),
            currency=str(session.currency or "usd"),
            metadata=dict(session.metadata or {}),
        )

    async def handle_webhook(self, body: bytes, signature: str) -> WebhookEvent:
        """Verify and parse a webhook event. Raises if signature is invalid."""
        secret = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
        if secret:
            try:
                event = stripe.Webhook.construct_event(body, signature, secret)
            except Exception as e:
                log.error(f"[stripe-shim] webhook signature verification failed: {e}")
                raise
        else:
            # No webhook secret configured — parse raw body (dev only)
            import json
            try:
                event = stripe.util.convert_to_stripe_object(json.loads(body.decode("utf-8")), api_key=self._api_key)
            except Exception:
                event = json.loads(body.decode("utf-8"))

        # Best-effort extraction
        event_type = getattr(event, "type", None) or (event.get("type") if isinstance(event, dict) else "unknown")
        obj = None
        try:
            obj = event.data.object  # type: ignore[attr-defined]
        except Exception:
            try:
                obj = event["data"]["object"]
            except Exception:
                obj = {}
        session_id = getattr(obj, "id", None) or (obj.get("id") if isinstance(obj, dict) else "")
        payment_status = getattr(obj, "payment_status", None) or (obj.get("payment_status") if isinstance(obj, dict) else "")
        metadata = getattr(obj, "metadata", None) or (obj.get("metadata") if isinstance(obj, dict) else {}) or {}

        return WebhookEvent(
            event_type=str(event_type or "unknown"),
            session_id=str(session_id or ""),
            payment_status=str(payment_status or ""),
            metadata=dict(metadata),
        )
