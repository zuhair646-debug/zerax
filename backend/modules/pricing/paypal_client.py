"""
PayPal v2 REST API client — LIVE mode.
Uses raw httpx instead of paypalrestsdk for cleaner async + v2 API.

Flow:
1. create_order(amount, currency, return_url, cancel_url) → returns order_id + approval link
2. User pays on PayPal
3. capture_order(order_id) → returns capture response (status=COMPLETED)
"""
import os
import logging
import httpx
from typing import Dict, Any, Optional

log = logging.getLogger("zitex.pricing.paypal")

PAYPAL_BASE_LIVE = "https://api-m.paypal.com"
PAYPAL_BASE_SANDBOX = "https://api-m.sandbox.paypal.com"


def _paypal_base() -> str:
    mode = os.environ.get("PAYPAL_MODE", "live").lower()
    return PAYPAL_BASE_SANDBOX if mode == "sandbox" else PAYPAL_BASE_LIVE


async def _get_token() -> str:
    client_id = os.environ.get("PAYPAL_CLIENT_ID")
    secret = os.environ.get("PAYPAL_SECRET")
    if not client_id or not secret:
        raise RuntimeError("PAYPAL_CLIENT_ID / PAYPAL_SECRET not configured")
    async with httpx.AsyncClient(timeout=15) as c:
        r = await c.post(
            f"{_paypal_base()}/v1/oauth2/token",
            auth=(client_id, secret),
            data={"grant_type": "client_credentials"},
            headers={"Accept": "application/json"},
        )
        if r.status_code != 200:
            log.error(f"PayPal auth failed: {r.status_code} {r.text[:300]}")
            raise RuntimeError(f"PayPal auth failed: {r.status_code}")
        return r.json()["access_token"]


async def create_order(
    amount_usd: float,
    return_url: str,
    cancel_url: str,
    description: str = "Zitex Purchase",
    custom_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Creates a v2 order. Returns {order_id, approval_url}."""
    token = await _get_token()
    payload = {
        "intent": "CAPTURE",
        "purchase_units": [{
            "amount": {
                "currency_code": "USD",
                "value": f"{float(amount_usd):.2f}",
            },
            "description": description[:120],
            **({"custom_id": custom_id} if custom_id else {}),
        }],
        "application_context": {
            "brand_name": "Zitex",
            "shipping_preference": "NO_SHIPPING",
            "user_action": "PAY_NOW",
            "return_url": return_url,
            "cancel_url": cancel_url,
        },
    }
    async with httpx.AsyncClient(timeout=20) as c:
        r = await c.post(
            f"{_paypal_base()}/v2/checkout/orders",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "Prefer": "return=representation",
            },
            json=payload,
        )
        if r.status_code not in (200, 201):
            log.error(f"PayPal create order failed: {r.status_code} {r.text[:500]}")
            raise RuntimeError(f"PayPal create order failed: {r.text[:200]}")
        data = r.json()
        approval = next((l["href"] for l in data.get("links", []) if l.get("rel") == "approve"), None)
        return {
            "order_id": data["id"],
            "status": data.get("status"),
            "approval_url": approval,
            "raw": data,
        }


async def capture_order(order_id: str) -> Dict[str, Any]:
    """Captures (charges) an approved order. Returns capture details."""
    token = await _get_token()
    async with httpx.AsyncClient(timeout=20) as c:
        r = await c.post(
            f"{_paypal_base()}/v2/checkout/orders/{order_id}/capture",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
        )
        if r.status_code not in (200, 201):
            log.error(f"PayPal capture failed: {r.status_code} {r.text[:500]}")
            raise RuntimeError(f"PayPal capture failed: {r.text[:200]}")
        return r.json()


async def get_order(order_id: str) -> Dict[str, Any]:
    """Fetches order details from PayPal."""
    token = await _get_token()
    async with httpx.AsyncClient(timeout=15) as c:
        r = await c.get(
            f"{_paypal_base()}/v2/checkout/orders/{order_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        if r.status_code != 200:
            raise RuntimeError(f"PayPal get order failed: {r.status_code}")
        return r.json()
