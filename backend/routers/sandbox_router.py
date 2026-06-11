"""
Zenrex Sandbox Payments & Shipping Router
==========================================
Provides full end-to-end test (sandbox) flows for every payment gateway and
shipping provider so merchants can run REAL orders against fake keys.

Concept:
  • Each merchant has a `payment_configs` entry per gateway (mode + keys)
  • In `sandbox` mode → Zenrex simulates the PSP flow (checkout page, callback)
  • In `live` mode → Zenrex forwards to the real PSP using merchant's keys
  • Same applies to shipping providers (Aramex/SMSA/DHL)

This lets merchants launch a fully working site BEFORE getting real keys.
When they swap to live, only the keys change — UI/flow stay identical.

Owner: Zenrex Platform (Feb 2026)
"""
from __future__ import annotations

import os
import json
import logging
import secrets
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field

from routers.store_router import merchant_user, customer_user, db as _db

log = logging.getLogger("sandbox_router")
router = APIRouter(prefix="/api/sandbox", tags=["sandbox"])
db = _db


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _gen_id(prefix: str) -> str:
    return f"{prefix}_{secrets.token_urlsafe(10)}"


# ═══════════════════════════════════════════════════════════════════════════
# PAYMENT GATEWAYS (catalog with sandbox & live key templates)
# ═══════════════════════════════════════════════════════════════════════════
PAYMENT_GATEWAYS = {
    "tabby": {
        "name": "تابي · Tabby",
        "country": "sa",
        "type": "bnpl",
        "logo": "🟢",
        "color": "#3bcd5a",
        "description": "اقسط على 4 دفعات بدون فوائد",
        "sandbox_keys": {
            "public_key": "pk_test_zenrex_tabby_sandbox_2026",
            "secret_key": "sk_test_zenrex_tabby_sandbox_2026",
        },
        "live_keys_needed": ["public_key", "secret_key", "merchant_code"],
        "dashboard_url": "https://merchant.tabby.ai",
    },
    "tamara": {
        "name": "تمارا · Tamara",
        "country": "sa",
        "type": "bnpl",
        "logo": "🟣",
        "color": "#aa00ff",
        "description": "اشتري الآن وادفع لاحقاً",
        "sandbox_keys": {
            "api_token": "tamara_test_zenrex_sandbox_2026",
            "notification_token": "tamara_notify_zenrex_sandbox_2026",
        },
        "live_keys_needed": ["api_token", "notification_token"],
        "dashboard_url": "https://partners.tamara.co",
    },
    "mada": {
        "name": "مدى · Mada",
        "country": "sa",
        "type": "card",
        "logo": "🟦",
        "color": "#005baa",
        "description": "بطاقات مدى المحلية",
        "sandbox_keys": {
            "merchant_id": "MADA_TEST_ZRX_2026",
            "terminal_id": "T_TEST_ZRX_2026",
        },
        "live_keys_needed": ["merchant_id", "terminal_id", "secret_key"],
        "dashboard_url": "https://www.saudipayments.com",
    },
    "stcpay": {
        "name": "STC Pay",
        "country": "sa",
        "type": "wallet",
        "logo": "🟪",
        "color": "#4f008c",
        "description": "محفظة STC Pay الإلكترونية",
        "sandbox_keys": {
            "merchant_id": "STCPAY_TEST_ZRX",
            "api_key": "stcpay_test_zenrex_2026",
        },
        "live_keys_needed": ["merchant_id", "api_key"],
        "dashboard_url": "https://business.stcpay.com.sa",
    },
    "hyperpay": {
        "name": "HyperPay",
        "country": "sa",
        "type": "gateway",
        "logo": "🟧",
        "color": "#ff6b35",
        "description": "بوابة دفع شاملة (Visa/Mastercard/Mada)",
        "sandbox_keys": {
            "entity_id": "8a8294174e735d0c014e78cf26461790",
            "access_token": "OGE4Mjk0MTc0ZTczNWQwYzAxNGU3OGNmMjY2YzAwMDA=",
        },
        "live_keys_needed": ["entity_id", "access_token"],
        "dashboard_url": "https://wpwlhc.hyperpay.com",
    },
    "moyasar": {
        "name": "ميسر · Moyasar",
        "country": "sa",
        "type": "gateway",
        "logo": "🟢",
        "color": "#1FB373",
        "description": "بوابة دفع سعودية متكاملة",
        "sandbox_keys": {
            "publishable_key": "pk_test_zenrex_moyasar_sandbox",
            "secret_key": "sk_test_zenrex_moyasar_sandbox",
        },
        "live_keys_needed": ["publishable_key", "secret_key"],
        "dashboard_url": "https://dashboard.moyasar.com",
    },
    "stripe": {
        "name": "Stripe",
        "country": "global",
        "type": "gateway",
        "logo": "🟣",
        "color": "#635bff",
        "description": "بوابة الدفع العالمية",
        "sandbox_keys": {
            "publishable_key": "pk_test_zenrex_stripe_sandbox_2026",
            "secret_key": "sk_test_zenrex_stripe_sandbox_2026",
        },
        "live_keys_needed": ["publishable_key", "secret_key"],
        "dashboard_url": "https://dashboard.stripe.com",
    },
    "paypal": {
        "name": "PayPal",
        "country": "global",
        "type": "wallet",
        "logo": "🟦",
        "color": "#003087",
        "description": "محفظة PayPal العالمية",
        "sandbox_keys": {
            "client_id": "AYpv-paypal-sandbox-zenrex-2026",
            "client_secret": "EHqyt-paypal-sandbox-zenrex-2026",
        },
        "live_keys_needed": ["client_id", "client_secret"],
        "dashboard_url": "https://developer.paypal.com",
    },
    "applepay": {
        "name": "Apple Pay",
        "country": "global",
        "type": "wallet",
        "logo": "⚫",
        "color": "#000000",
        "description": "الدفع عبر Apple Pay (يتطلب HyperPay/Moyasar)",
        "sandbox_keys": {"merchant_identifier": "merchant.com.zenrex.sandbox"},
        "live_keys_needed": ["merchant_identifier", "domain_verification_file"],
        "dashboard_url": "https://developer.apple.com/apple-pay",
    },
    "cod": {
        "name": "الدفع عند الاستلام",
        "country": "sa",
        "type": "cash",
        "logo": "💵",
        "color": "#10b981",
        "description": "كاش عند التسليم",
        "sandbox_keys": {},
        "live_keys_needed": [],
        "dashboard_url": "",
    },
}

# ═══════════════════════════════════════════════════════════════════════════
# SHIPPING PROVIDERS (catalog)
# ═══════════════════════════════════════════════════════════════════════════
SHIPPING_PROVIDERS = {
    "aramex": {
        "name": "أرامكس · Aramex",
        "country": "sa",
        "logo": "🟥",
        "color": "#dc2626",
        "tracking_url": "https://www.aramex.com/track/results?ShipmentNumber={tracking}",
        "sandbox_keys": {"username": "aramex_test_zenrex_2026", "password": "aramex_sandbox_pwd"},
        "live_keys_needed": ["username", "password", "account_number"],
        "base_fee_sar": 15,
        "per_kg_sar": 5,
        "delivery_days": "1-3",
    },
    "smsa": {
        "name": "سمسا · SMSA",
        "country": "sa",
        "logo": "🟦",
        "color": "#1e40af",
        "tracking_url": "https://www.smsaexpress.com/track?trackingNumber={tracking}",
        "sandbox_keys": {"api_key": "smsa_test_zenrex_sandbox_2026"},
        "live_keys_needed": ["api_key", "passkey"],
        "base_fee_sar": 12,
        "per_kg_sar": 4,
        "delivery_days": "1-2",
    },
    "naqel": {
        "name": "ناقل · Naqel",
        "country": "sa",
        "logo": "🟧",
        "color": "#f97316",
        "tracking_url": "https://www.naqelexpress.com/track/{tracking}",
        "sandbox_keys": {"client_id": "naqel_test_zenrex", "client_secret": "naqel_sandbox_secret"},
        "live_keys_needed": ["client_id", "client_secret"],
        "base_fee_sar": 14,
        "per_kg_sar": 4.5,
        "delivery_days": "1-3",
    },
    "dhl": {
        "name": "DHL Express",
        "country": "global",
        "logo": "🟨",
        "color": "#fbbf24",
        "tracking_url": "https://www.dhl.com/track?tracking-id={tracking}",
        "sandbox_keys": {"api_key": "dhl_test_zenrex_sandbox", "api_secret": "dhl_sandbox_secret"},
        "live_keys_needed": ["api_key", "api_secret", "account_number"],
        "base_fee_sar": 45,
        "per_kg_sar": 12,
        "delivery_days": "3-7",
    },
    "jt_express": {
        "name": "J&T Express",
        "country": "sa",
        "logo": "🟧",
        "color": "#ea580c",
        "tracking_url": "https://www.jtexpress.sa/index/query/gzquery.html?bills={tracking}",
        "sandbox_keys": {"api_key": "jt_test_zenrex_sandbox"},
        "live_keys_needed": ["api_key", "customer_code"],
        "base_fee_sar": 13,
        "per_kg_sar": 4,
        "delivery_days": "1-3",
    },
    "zenrex_fleet": {
        "name": "أسطول Zenrex الداخلي",
        "country": "sa",
        "logo": "🚗",
        "color": "#7c3aed",
        "tracking_url": "/track/{tracking}",
        "sandbox_keys": {},
        "live_keys_needed": [],
        "base_fee_sar": 10,
        "per_kg_sar": 2,
        "delivery_days": "same-day",
    },
}


# ───────────────────────────────────────────────────────────────────────────
# CATALOG ENDPOINTS
# ───────────────────────────────────────────────────────────────────────────
@router.get("/payment-gateways")
async def list_payment_gateways():
    """Public catalog with sandbox+live key templates."""
    items = []
    for k, v in PAYMENT_GATEWAYS.items():
        items.append({
            "id": k,
            "name": v["name"],
            "country": v["country"],
            "type": v["type"],
            "logo": v["logo"],
            "color": v["color"],
            "description": v["description"],
            "sandbox_keys": v["sandbox_keys"],  # public — these are FAKE
            "live_keys_needed": v["live_keys_needed"],
            "dashboard_url": v["dashboard_url"],
        })
    return {"items": items, "count": len(items)}


@router.get("/shipping-providers")
async def list_shipping_providers():
    items = []
    for k, v in SHIPPING_PROVIDERS.items():
        items.append({
            "id": k,
            "name": v["name"],
            "country": v["country"],
            "logo": v["logo"],
            "color": v["color"],
            "sandbox_keys": v["sandbox_keys"],
            "live_keys_needed": v["live_keys_needed"],
            "base_fee_sar": v["base_fee_sar"],
            "per_kg_sar": v["per_kg_sar"],
            "delivery_days": v["delivery_days"],
            "tracking_url_template": v["tracking_url"],
        })
    return {"items": items, "count": len(items)}


# ───────────────────────────────────────────────────────────────────────────
# MERCHANT CONFIG (per-gateway / per-shipping enable + keys + mode)
# ───────────────────────────────────────────────────────────────────────────
class GatewayConfigIn(BaseModel):
    gateway_id: str
    enabled: bool = True
    mode: str = "sandbox"  # sandbox | live
    keys: Dict[str, str] = {}


class ShippingConfigIn(BaseModel):
    provider_id: str
    enabled: bool = True
    mode: str = "sandbox"
    keys: Dict[str, str] = {}
    custom_base_fee: Optional[float] = None
    custom_per_kg: Optional[float] = None


@router.get("/merchant/payment-configs")
async def get_merchant_payment_configs(u: dict = Depends(merchant_user)):
    rows = await db.merchant_payment_configs.find({"merchant_id": u["user_id"]}, {"_id": 0}).to_list(50)
    return {"items": rows}


@router.put("/merchant/payment-config")
async def upsert_merchant_payment_config(body: GatewayConfigIn, u: dict = Depends(merchant_user)):
    if body.gateway_id not in PAYMENT_GATEWAYS:
        raise HTTPException(status_code=400, detail="Unknown gateway")
    if body.mode not in {"sandbox", "live"}:
        raise HTTPException(status_code=400, detail="mode must be sandbox or live")
    # If sandbox, auto-fill the universal sandbox keys
    keys = body.keys or (PAYMENT_GATEWAYS[body.gateway_id]["sandbox_keys"] if body.mode == "sandbox" else {})
    doc = {
        "merchant_id": u["user_id"],
        "gateway_id": body.gateway_id,
        "enabled": body.enabled,
        "mode": body.mode,
        "keys": keys,
        "updated_at": _now_iso(),
    }
    await db.merchant_payment_configs.update_one(
        {"merchant_id": u["user_id"], "gateway_id": body.gateway_id},
        {"$set": doc, "$setOnInsert": {"created_at": _now_iso()}},
        upsert=True,
    )
    return await db.merchant_payment_configs.find_one(
        {"merchant_id": u["user_id"], "gateway_id": body.gateway_id}, {"_id": 0}
    )


@router.get("/merchant/shipping-configs")
async def get_merchant_shipping_configs(u: dict = Depends(merchant_user)):
    rows = await db.merchant_shipping_configs.find({"merchant_id": u["user_id"]}, {"_id": 0}).to_list(50)
    return {"items": rows}


@router.put("/merchant/shipping-config")
async def upsert_merchant_shipping_config(body: ShippingConfigIn, u: dict = Depends(merchant_user)):
    if body.provider_id not in SHIPPING_PROVIDERS:
        raise HTTPException(status_code=400, detail="Unknown shipping provider")
    if body.mode not in {"sandbox", "live"}:
        raise HTTPException(status_code=400, detail="mode must be sandbox or live")
    keys = body.keys or (SHIPPING_PROVIDERS[body.provider_id]["sandbox_keys"] if body.mode == "sandbox" else {})
    doc = {
        "merchant_id": u["user_id"],
        "provider_id": body.provider_id,
        "enabled": body.enabled,
        "mode": body.mode,
        "keys": keys,
        "custom_base_fee": body.custom_base_fee,
        "custom_per_kg": body.custom_per_kg,
        "updated_at": _now_iso(),
    }
    await db.merchant_shipping_configs.update_one(
        {"merchant_id": u["user_id"], "provider_id": body.provider_id},
        {"$set": doc, "$setOnInsert": {"created_at": _now_iso()}},
        upsert=True,
    )
    return await db.merchant_shipping_configs.find_one(
        {"merchant_id": u["user_id"], "provider_id": body.provider_id}, {"_id": 0}
    )


# ───────────────────────────────────────────────────────────────────────────
# CUSTOMER-FACING: get enabled options at checkout
# ───────────────────────────────────────────────────────────────────────────
@router.get("/checkout-options")
async def get_checkout_options(merchant_id: Optional[str] = None):
    """Returns enabled payment + shipping options for the storefront."""
    p_q = {"enabled": True}
    s_q = {"enabled": True}
    if merchant_id:
        p_q["merchant_id"] = merchant_id
        s_q["merchant_id"] = merchant_id
    pay_rows = await db.merchant_payment_configs.find(p_q, {"_id": 0, "keys": 0}).to_list(50)
    ship_rows = await db.merchant_shipping_configs.find(s_q, {"_id": 0, "keys": 0}).to_list(50)
    # Enrich with catalog data
    payments = []
    for r in pay_rows:
        g = PAYMENT_GATEWAYS.get(r["gateway_id"], {})
        payments.append({**r, "name": g.get("name"), "logo": g.get("logo"), "color": g.get("color"), "type": g.get("type"), "description": g.get("description")})
    shipping = []
    for r in ship_rows:
        s = SHIPPING_PROVIDERS.get(r["provider_id"], {})
        base = r.get("custom_base_fee") if r.get("custom_base_fee") is not None else s.get("base_fee_sar", 15)
        per_kg = r.get("custom_per_kg") if r.get("custom_per_kg") is not None else s.get("per_kg_sar", 5)
        shipping.append({**r, "name": s.get("name"), "logo": s.get("logo"), "color": s.get("color"), "base_fee_sar": base, "per_kg_sar": per_kg, "delivery_days": s.get("delivery_days")})
    return {"payments": payments, "shipping": shipping}


# ───────────────────────────────────────────────────────────────────────────
# SANDBOX CHECKOUT FLOW (the magic — simulates real PSP flow end-to-end)
# ───────────────────────────────────────────────────────────────────────────
class InitCheckoutIn(BaseModel):
    gateway_id: str
    order_id: str
    amount: float
    currency: str = "SAR"
    customer_name: str = ""
    customer_email: str = ""
    customer_phone: str = ""
    return_url: str = ""  # frontend page to return to after payment
    metadata: Dict[str, Any] = {}


@router.post("/payment/init")
async def init_payment_checkout(body: InitCheckoutIn, request: Request):
    """
    Creates a payment session.
    SANDBOX mode → returns a Zenrex-hosted checkout URL that simulates the PSP
    LIVE mode → would forward to real PSP (TODO when merchant brings real keys)
    """
    if body.gateway_id not in PAYMENT_GATEWAYS:
        raise HTTPException(status_code=400, detail="Unknown gateway")

    session_id = _gen_id("pay")
    base_url = str(request.base_url).rstrip("/")
    checkout_url = f"{base_url}/api/sandbox/payment/checkout/{session_id}"

    session = {
        "id": session_id,
        "gateway_id": body.gateway_id,
        "order_id": body.order_id,
        "amount": body.amount,
        "currency": body.currency,
        "customer": {"name": body.customer_name, "email": body.customer_email, "phone": body.customer_phone},
        "return_url": body.return_url,
        "metadata": body.metadata,
        "status": "pending",  # pending → paid | failed | cancelled
        "mode": "sandbox",
        "checkout_url": checkout_url,
        "created_at": _now_iso(),
        "expires_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
    }
    await db.payment_sessions.insert_one(dict(session))
    session.pop("_id", None)
    return session


@router.get("/payment/checkout/{session_id}", response_class=HTMLResponse)
async def sandbox_checkout_page(session_id: str):
    """Renders a beautiful sandbox checkout page that mimics the real PSP."""
    s = await db.payment_sessions.find_one({"id": session_id}, {"_id": 0})
    if not s:
        return HTMLResponse("<h1 style='text-align:center;padding:40px;font-family:system-ui'>⚠️ جلسة دفع غير موجودة</h1>", status_code=404)
    g = PAYMENT_GATEWAYS.get(s["gateway_id"], {})
    color = g.get("color", "#7c3aed")
    name = g.get("name", s["gateway_id"])
    logo = g.get("logo", "💳")
    cust = s.get("customer", {})
    amount_str = f"{s['amount']:.2f} {s['currency']}"
    return_url = s.get("return_url") or f"/api/sandbox/payment/result/{session_id}"
    html = f"""<!doctype html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{name} · صفحة الدفع (تجريبي)</title>
<style>
  *{{box-sizing:border-box;margin:0;padding:0}}
  body{{font-family:'Tajawal','Segoe UI',Arial,sans-serif;background:linear-gradient(135deg,#0f172a,#1e293b);min-height:100vh;display:flex;align-items:center;justify-content:center;padding:20px;color:#fff}}
  .card{{background:#fff;color:#1f2937;border-radius:20px;max-width:480px;width:100%;overflow:hidden;box-shadow:0 30px 80px rgba(0,0,0,.4)}}
  .hdr{{background:linear-gradient(135deg,{color},{color}cc);padding:30px 28px;color:#fff;text-align:center}}
  .hdr .logo{{font-size:54px;margin-bottom:8px}}
  .hdr h1{{font-size:24px;font-weight:900;margin-bottom:4px}}
  .hdr .sub{{font-size:12px;opacity:.9}}
  .body{{padding:28px}}
  .row{{display:flex;justify-content:space-between;padding:10px 0;border-bottom:1px dashed #e5e7eb;font-size:13px}}
  .row b{{color:#374151;font-weight:800}}
  .total{{margin-top:18px;background:#f9fafb;border-radius:12px;padding:14px 16px;display:flex;justify-content:space-between;align-items:center}}
  .total .amt{{font-size:24px;font-weight:900;color:{color}}}
  .badge{{background:#fef3c7;color:#92400e;padding:6px 14px;border-radius:99px;font-size:11px;font-weight:900;display:inline-block;margin-top:14px}}
  .actions{{margin-top:24px;display:flex;flex-direction:column;gap:10px}}
  .btn{{padding:14px 18px;border-radius:12px;font-family:inherit;font-weight:900;font-size:14px;cursor:pointer;border:none;display:flex;align-items:center;justify-content:center;gap:8px;transition:transform .12s}}
  .btn:hover{{transform:translateY(-1px)}}
  .btn-pay{{background:linear-gradient(135deg,{color},{color}cc);color:#fff;box-shadow:0 8px 18px {color}40}}
  .btn-fail{{background:#fef2f2;color:#dc2626;border:1px solid #fecaca}}
  .btn-cancel{{background:#f3f4f6;color:#6b7280}}
  .foot{{text-align:center;padding:14px;background:#f9fafb;color:#9ca3af;font-size:10px;border-top:1px solid #f3f4f6}}
  .secured{{font-size:11px;color:#10b981;margin-top:14px;text-align:center;display:flex;align-items:center;justify-content:center;gap:6px}}
</style>
</head>
<body>
  <div class="card" data-testid="sandbox-checkout">
    <div class="hdr">
      <div class="logo">{logo}</div>
      <h1>{name}</h1>
      <div class="sub">صفحة الدفع الآمنة</div>
      <div class="badge">⚡ وضع تجريبي · Sandbox</div>
    </div>
    <div class="body">
      <div class="row"><span>رقم الطلب</span><b>#{s['order_id'][:14]}</b></div>
      <div class="row"><span>اسم العميل</span><b>{cust.get('name') or '—'}</b></div>
      <div class="row"><span>جوال</span><b>{cust.get('phone') or '—'}</b></div>
      <div class="row"><span>طريقة الدفع</span><b>{name}</b></div>
      <div class="total">
        <span><b>الإجمالي المستحق</b></span>
        <span class="amt">{amount_str}</span>
      </div>
      <div class="secured">🔒 محمي · جلسة تنتهي خلال ساعة</div>
      <div class="actions">
        <button class="btn btn-pay" data-testid="sandbox-pay-success" onclick="finish('paid')">✓ ادفع {amount_str} (تجريبي ناجح)</button>
        <button class="btn btn-fail" data-testid="sandbox-pay-fail" onclick="finish('failed')">✗ محاكاة فشل دفع</button>
        <button class="btn btn-cancel" data-testid="sandbox-pay-cancel" onclick="finish('cancelled')">إلغاء العملية</button>
      </div>
    </div>
    <div class="foot">
      🛡️ صفحة محاكاة Zenrex Sandbox · لن يتم خصم أي مبلغ حقيقي<br>
      عند تفعيل المفاتيح الحقيقية، ستنتقل هذه الصفحة إلى {name} مباشرة
    </div>
  </div>
<script>
async function finish(outcome) {{
  try {{
    const r = await fetch('/api/sandbox/payment/complete/{session_id}', {{
      method: 'POST',
      headers: {{'Content-Type':'application/json'}},
      body: JSON.stringify({{outcome}})
    }});
    const d = await r.json();
    const ret = {json.dumps(return_url)};
    const sep = ret.includes('?') ? '&' : '?';
    window.location.href = ret + sep + 'session=' + {json.dumps(session_id)} + '&status=' + outcome;
  }} catch(e) {{
    alert('خطأ: ' + e.message);
  }}
}}
</script>
</body></html>"""
    return HTMLResponse(html)


class CompletePaymentIn(BaseModel):
    outcome: str  # paid | failed | cancelled


@router.post("/payment/complete/{session_id}")
async def complete_sandbox_payment(session_id: str, body: CompletePaymentIn):
    if body.outcome not in {"paid", "failed", "cancelled"}:
        raise HTTPException(status_code=400, detail="Invalid outcome")
    s = await db.payment_sessions.find_one({"id": session_id})
    if not s:
        raise HTTPException(status_code=404, detail="Session not found")
    await db.payment_sessions.update_one(
        {"id": session_id},
        {"$set": {"status": body.outcome, "completed_at": _now_iso()}},
    )
    # Update the linked order
    if s.get("order_id"):
        await db.store_orders.update_one(
            {"id": s["order_id"]},
            {
                "$set": {"payment_status": body.outcome, "updated_at": _now_iso()},
                "$push": {"timeline": {"status": f"payment_{body.outcome}", "at": _now_iso(), "session_id": session_id}},
            },
        )
    return {"ok": True, "status": body.outcome, "session_id": session_id}


@router.get("/payment/result/{session_id}", response_class=HTMLResponse)
async def payment_result_page(session_id: str):
    """Default fallback return page when merchant didn't specify return_url."""
    s = await db.payment_sessions.find_one({"id": session_id}, {"_id": 0})
    if not s:
        return HTMLResponse("<h1>جلسة غير موجودة</h1>", status_code=404)
    icon = {"paid": "✅", "failed": "❌", "cancelled": "⚠️", "pending": "⏳"}.get(s["status"], "❓")
    color = {"paid": "#10b981", "failed": "#dc2626", "cancelled": "#f59e0b", "pending": "#6366f1"}.get(s["status"], "#6b7280")
    msg = {"paid": "تم الدفع بنجاح", "failed": "فشلت عملية الدفع", "cancelled": "تم إلغاء العملية", "pending": "في انتظار الدفع"}.get(s["status"], "—")
    return HTMLResponse(f"""<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8"><title>{msg}</title>
<style>body{{font-family:system-ui;background:#0f172a;color:#fff;display:flex;align-items:center;justify-content:center;min-height:100vh;margin:0}}
.card{{background:#fff;color:#1f2937;border-radius:20px;padding:50px 40px;text-align:center;max-width:420px;width:90%}}
.icon{{font-size:72px;margin-bottom:14px}}h1{{color:{color};margin-bottom:8px}}p{{color:#6b7280;font-size:13px}}</style></head>
<body><div class="card"><div class="icon">{icon}</div><h1>{msg}</h1>
<p>طلب: <b>#{s['order_id'][:14]}</b></p>
<p>المبلغ: <b>{s['amount']:.2f} {s['currency']}</b></p>
<p style="margin-top:20px;font-size:11px;color:#9ca3af">جلسة تجريبية · {s['gateway_id']}</p></div></body></html>""")


# ───────────────────────────────────────────────────────────────────────────
# SANDBOX SHIPPING (rate quote + label + tracking)
# ───────────────────────────────────────────────────────────────────────────
class ShippingQuoteIn(BaseModel):
    provider_id: str
    from_city: str = "الرياض"
    to_city: str
    weight_kg: float = 1.0
    declared_value_sar: float = 100


@router.post("/shipping/quote")
async def shipping_quote(body: ShippingQuoteIn):
    if body.provider_id not in SHIPPING_PROVIDERS:
        raise HTTPException(status_code=400, detail="Unknown provider")
    p = SHIPPING_PROVIDERS[body.provider_id]
    cost = round(p["base_fee_sar"] + (body.weight_kg * p["per_kg_sar"]), 2)
    return {
        "provider_id": body.provider_id,
        "provider_name": p["name"],
        "from_city": body.from_city,
        "to_city": body.to_city,
        "weight_kg": body.weight_kg,
        "cost_sar": cost,
        "delivery_days": p["delivery_days"],
        "currency": "SAR",
        "mode": "sandbox",
    }


class ShippingLabelIn(BaseModel):
    provider_id: str
    order_id: str
    from_address: Dict[str, Any]
    to_address: Dict[str, Any]
    weight_kg: float = 1.0
    items_description: str = ""


@router.post("/shipping/create-label")
async def shipping_create_label(body: ShippingLabelIn):
    if body.provider_id not in SHIPPING_PROVIDERS:
        raise HTTPException(status_code=400, detail="Unknown provider")
    p = SHIPPING_PROVIDERS[body.provider_id]
    tracking_no = f"{body.provider_id.upper()[:3]}{secrets.token_hex(5).upper()}"
    label = {
        "id": _gen_id("ship"),
        "provider_id": body.provider_id,
        "order_id": body.order_id,
        "tracking_number": tracking_no,
        "tracking_url": p["tracking_url"].replace("{tracking}", tracking_no),
        "from_address": body.from_address,
        "to_address": body.to_address,
        "weight_kg": body.weight_kg,
        "items_description": body.items_description,
        "status": "label_created",  # label_created → picked_up → in_transit → out_for_delivery → delivered
        "mode": "sandbox",
        "label_pdf_url": f"/api/sandbox/shipping/label/{tracking_no}.pdf",
        "created_at": _now_iso(),
        "events": [{"status": "label_created", "at": _now_iso(), "location": body.from_address.get("city", "—")}],
    }
    await db.shipping_labels.insert_one(dict(label))
    label.pop("_id", None)
    # Link to order
    await db.store_orders.update_one(
        {"id": body.order_id},
        {"$set": {"tracking_number": tracking_no, "shipping_provider": body.provider_id, "shipping_status": "label_created"}},
    )
    return label


@router.get("/shipping/track/{tracking_number}")
async def shipping_track(tracking_number: str):
    label = await db.shipping_labels.find_one({"tracking_number": tracking_number}, {"_id": 0})
    if not label:
        raise HTTPException(status_code=404, detail="Tracking number not found")
    return label


class AdvanceShipmentIn(BaseModel):
    tracking_number: str
    new_status: str  # picked_up | in_transit | out_for_delivery | delivered


@router.post("/shipping/advance")
async def advance_shipment(body: AdvanceShipmentIn):
    """Sandbox helper to manually advance a shipment status (simulates carrier events)."""
    valid = {"picked_up", "in_transit", "out_for_delivery", "delivered"}
    if body.new_status not in valid:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of {valid}")
    label = await db.shipping_labels.find_one({"tracking_number": body.tracking_number})
    if not label:
        raise HTTPException(status_code=404, detail="Tracking number not found")
    event = {"status": body.new_status, "at": _now_iso(), "location": "محاكاة Zenrex Sandbox"}
    await db.shipping_labels.update_one(
        {"tracking_number": body.tracking_number},
        {"$set": {"status": body.new_status, "updated_at": _now_iso()}, "$push": {"events": event}},
    )
    if label.get("order_id"):
        order_set = {"shipping_status": body.new_status, "updated_at": _now_iso()}
        if body.new_status == "delivered":
            order_set["status"] = "delivered"
        await db.store_orders.update_one({"id": label["order_id"]}, {"$set": order_set, "$push": {"timeline": {"status": f"shipping_{body.new_status}", "at": _now_iso()}}})
    return {"ok": True, "status": body.new_status, "events_count": len(label.get("events", [])) + 1}


# ───────────────────────────────────────────────────────────────────────────
# HEALTH + BULK SANDBOX ENABLE
# ───────────────────────────────────────────────────────────────────────────
@router.post("/merchant/enable-all-sandbox")
async def enable_all_sandbox(u: dict = Depends(merchant_user)):
    """One-click — enables ALL gateways + shipping in sandbox mode with built-in fake keys."""
    pay_count = 0
    ship_count = 0
    for gid, g in PAYMENT_GATEWAYS.items():
        await db.merchant_payment_configs.update_one(
            {"merchant_id": u["user_id"], "gateway_id": gid},
            {"$set": {"merchant_id": u["user_id"], "gateway_id": gid, "enabled": True, "mode": "sandbox", "keys": g["sandbox_keys"], "updated_at": _now_iso()}, "$setOnInsert": {"created_at": _now_iso()}},
            upsert=True,
        )
        pay_count += 1
    for sid, s in SHIPPING_PROVIDERS.items():
        await db.merchant_shipping_configs.update_one(
            {"merchant_id": u["user_id"], "provider_id": sid},
            {"$set": {"merchant_id": u["user_id"], "provider_id": sid, "enabled": True, "mode": "sandbox", "keys": s["sandbox_keys"], "updated_at": _now_iso()}, "$setOnInsert": {"created_at": _now_iso()}},
            upsert=True,
        )
        ship_count += 1
    return {"ok": True, "payments_enabled": pay_count, "shipping_enabled": ship_count, "mode": "sandbox"}


@router.get("/health")
async def health():
    return {
        "ok": True,
        "payment_gateways_available": len(PAYMENT_GATEWAYS),
        "shipping_providers_available": len(SHIPPING_PROVIDERS),
        "active_sessions": await db.payment_sessions.count_documents({"status": "pending"}),
        "total_shipments": await db.shipping_labels.count_documents({}),
    }
