"""
Lemon Squeezy v1 REST API client.

Lemon Squeezy is a Merchant of Record — they handle tax, fraud, refunds globally.
We just create a checkout URL and redirect the user.

Supports: cards (Visa/MC/Amex), Apple Pay, Google Pay (auto for Saudi 🇸🇦),
PayPal, Klarna/Afterpay (auto for supported regions).
"""
import os
import logging
import httpx
from typing import Dict, Any, Optional

log = logging.getLogger("zenrex.pricing.lemonsqueezy")

LS_BASE = "https://api.lemonsqueezy.com/v1"


def _headers() -> Dict[str, str]:
    key = os.environ.get("LEMONSQUEEZY_API_KEY")
    if not key:
        raise RuntimeError("LEMONSQUEEZY_API_KEY not configured")
    return {
        "Authorization": f"Bearer {key}",
        "Accept": "application/vnd.api+json",
        "Content-Type": "application/vnd.api+json",
    }


async def create_checkout(
    amount_usd: float,
    product_name: str,
    customer_email: str,
    customer_name: str,
    custom_data: Dict[str, Any],
    redirect_url: str,
) -> Dict[str, Any]:
    """Creates a Lemon Squeezy hosted checkout. Returns {checkout_id, checkout_url}.
    
    We use the "Custom Price" mode so each order can have a dynamic amount.
    """
    store_id = os.environ.get("LEMONSQUEEZY_STORE_ID")
    if not store_id:
        raise RuntimeError("LEMONSQUEEZY_STORE_ID not configured")

    # Find any active variant on this store to use as base (we override the price)
    async with httpx.AsyncClient(timeout=20) as c:
        # 1. List products → pick first one → fetch its variants
        rp = await c.get(
            f"{LS_BASE}/products?filter[store_id]={store_id}&page[size]=1",
            headers=_headers(),
        )
        prods = rp.json().get("data", []) if rp.status_code == 200 else []
        if not prods:
            raise RuntimeError(
                "No product exists on Lemon Squeezy store. "
                "Please create one at https://app.lemonsqueezy.com/products"
            )
        pid = prods[0]["id"]
        rv = await c.get(f"{LS_BASE}/products/{pid}/variants", headers=_headers())
        if rv.status_code != 200 or not rv.json().get("data"):
            raise RuntimeError(f"No variants found for product {pid}")
        variant_id = rv.json()["data"][0]["id"]

        # 2. Create the checkout with custom price (in cents)
        amount_cents = int(round(float(amount_usd) * 100))
        payload = {
            "data": {
                "type": "checkouts",
                "attributes": {
                    "custom_price": amount_cents,
                    "product_options": {
                        "name": product_name[:100],
                        "redirect_url": redirect_url,
                        "receipt_button_text": "العودة إلى Zenrex",
                        "receipt_thank_you_note": "شكراً لاشتراكك في Zenrex!",
                    },
                    "checkout_options": {
                        "embed": False,
                        "media": False,
                        "logo": True,
                    },
                    "checkout_data": {
                        "email": customer_email,
                        "name": customer_name,
                        "custom": custom_data,
                    },
                },
                "relationships": {
                    "store": {"data": {"type": "stores", "id": str(store_id)}},
                    "variant": {"data": {"type": "variants", "id": str(variant_id)}},
                },
            }
        }
        r2 = await c.post(f"{LS_BASE}/checkouts", headers=_headers(), json=payload)
        if r2.status_code not in (200, 201):
            log.error(f"LS create checkout failed: {r2.status_code} {r2.text[:400]}")
            raise RuntimeError(f"Lemon Squeezy checkout failed: {r2.text[:200]}")
        data = r2.json()["data"]
        return {
            "checkout_id": data["id"],
            "checkout_url": data["attributes"]["url"],
        }


async def _ensure_default_product(store_id: str) -> str:
    """Create a generic 'Zenrex Credits' product if none exists yet."""
    async with httpx.AsyncClient(timeout=20) as c:
        payload = {
            "data": {
                "type": "products",
                "attributes": {
                    "name": "Zenrex Credits",
                    "description": "Universal Zenrex credits pack — custom amount per order",
                    "price": 100,  # $1 baseline, overridden per checkout
                    "status": "published",
                },
                "relationships": {"store": {"data": {"type": "stores", "id": str(store_id)}}},
            }
        }
        # Lemon Squeezy auto-creates a variant when product is created
        r = await c.post(f"{LS_BASE}/products", headers=_headers(), json=payload)
        if r.status_code in (200, 201):
            product_id = r.json()["data"]["id"]
            # Get the auto-created variant
            v = await c.get(f"{LS_BASE}/variants?filter[product_id]={product_id}", headers=_headers())
            return v.json()["data"][0]["id"]
        raise RuntimeError("Failed to create default product")


async def get_order(order_id: str) -> Dict[str, Any]:
    """Fetch order details to verify payment status."""
    async with httpx.AsyncClient(timeout=15) as c:
        r = await c.get(f"{LS_BASE}/orders/{order_id}", headers=_headers())
        if r.status_code != 200:
            raise RuntimeError(f"LS get order failed: {r.status_code}")
        return r.json()["data"]


async def list_recent_orders(limit: int = 10) -> list:
    """List recent orders from store."""
    store_id = os.environ.get("LEMONSQUEEZY_STORE_ID")
    async with httpx.AsyncClient(timeout=15) as c:
        r = await c.get(
            f"{LS_BASE}/orders?filter[store_id]={store_id}&page[size]={limit}&sort=-created_at",
            headers=_headers(),
        )
        if r.status_code != 200:
            return []
        return r.json().get("data", [])
