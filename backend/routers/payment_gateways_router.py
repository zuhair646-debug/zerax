"""
Zerax Payment Gateways API
==========================
Exposes the global gateways catalog so the merchant can:
  1. Browse all available gateways per country
  2. Enable/disable specific gateways for their store (in-memory toggle)
  3. Preview the customer-facing installment widget (BNPL) for a given amount
  4. Get the country profile (recommended gateways + VAT + invoice standard + shipping partners)

All endpoints return JSON; integrations are scaffolded — real provider SDKs
are wired in later by replacing the relevant `pay_*` adapters.
"""
import uuid
import logging
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from modules.payments.gateways_catalog import (
    GATEWAYS, COUNTRY_PROFILES, gateways_for_country, gateway_by_id, country_profile,
)
from modules.payments.gateway_enrichment import enrich, UNIVERSAL_IDS

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/payments", tags=["payments"])

# In-memory merchant config (which gateways the merchant has enabled)
ENABLED_GATEWAYS: dict = {
    # default: enable Saudi MENA stack for the demo merchant
    "demo": {"country": "SA", "enabled": ["mada", "tabby", "tamara", "stc_pay_checkout", "apple_pay", "cod"]},
}


class ToggleIn(BaseModel):
    merchant_id: str = "demo"
    gateway_id: str
    enable: bool = True


@router.get("/catalog")
async def list_catalog():
    """Return the full gateway catalog (all countries, all types), enriched."""
    enriched = [enrich(g) for g in GATEWAYS]
    return {"count": len(enriched), "gateways": enriched, "universal_ids": list(UNIVERSAL_IDS)}


@router.get("/countries")
async def list_country_profiles():
    """Return all country profiles with recommended gateways."""
    return {"count": len(COUNTRY_PROFILES), "profiles": COUNTRY_PROFILES}


@router.get("/by-country")
async def by_country(country: str):
    """List gateways available in a given ISO-3166 country code.
    Always includes universal gateways (Stripe/PayPal/Apple/Google/COD/Bank/USDC)
    alongside the country-specific ones — sorted so locals appear first.
    """
    cc = country.upper()
    profile = country_profile(country) or {
        "name_ar": cc, "currency": "USD", "vat_pct": 0,
        "invoice_standard": "Standard tax invoice", "shipping_partners": [],
        "recommended_gateways": [], "regulator": "—",
    }
    # Country-specific (with wildcard) + universal merged + de-duped
    base = gateways_for_country(country)
    seen = {g["id"] for g in base}
    for g in GATEWAYS:
        if g["id"] in UNIVERSAL_IDS and g["id"] not in seen:
            base.append(g); seen.add(g["id"])
    # Sort: country-local first (not universal), then universals; bnpl before card before wallet…
    type_order = {"bnpl":1,"card":2,"wallet":3,"qr":4,"bank":5,"crypto":6,"cod":7}
    base.sort(key=lambda g: (1 if g["id"] in UNIVERSAL_IDS else 0, type_order.get(g["type"], 9)))
    enriched = [enrich(g) for g in base]
    return {
        "country": cc, "profile": profile,
        "available_count": len(enriched), "universal_count": sum(1 for g in enriched if g["is_universal"]),
        "gateways": enriched,
    }


@router.get("/gateway/{gateway_id}")
async def get_gateway(gateway_id: str):
    g = gateway_by_id(gateway_id)
    if not g:
        raise HTTPException(status_code=404, detail="gateway not found")
    return enrich(g)


@router.post("/checkout-preview")
async def checkout_preview(gateway_id: str, amount: float, currency: str = "SAR"):
    """
    Simulates a checkout for a given gateway + amount.
    For BNPL: returns the installment split and per-installment amount.
    For others: returns 1-shot payment summary.
    Useful for showing live preview widgets on PDPs.
    """
    g = gateway_by_id(gateway_id)
    if not g:
        raise HTTPException(status_code=404, detail="gateway not found")

    if amount < g["min_amount"]:
        return {"eligible": False, "reason": f"المبلغ أقل من الحد الأدنى ({g['min_amount']} {currency})"}
    if amount > g["max_amount"]:
        return {"eligible": False, "reason": f"المبلغ أكبر من الحد الأعلى ({g['max_amount']} {currency})"}

    out = {
        "eligible": True,
        "gateway": gateway_id,
        "name_ar": g["name_ar"], "name_en": g["name_en"],
        "type": g["type"], "amount": amount, "currency": currency,
        "badge": g["badge"], "checkout": g["checkout"],
    }

    if g["type"] == "bnpl" and g.get("installments"):
        default_plan = next((p for p in g["installments"]["plans"] if p["count"] == g["installments"]["default"]), g["installments"]["plans"][0])
        plans_out = []
        for plan in g["installments"]["plans"]:
            n = plan["count"]
            interest = plan.get("interest", 0)
            total = amount * (1 + interest / 100)
            per = round(total / n, 2)
            plans_out.append({
                **plan,
                "per_installment": per,
                "total_with_interest": round(total, 2),
                "label_ar": f"{n} دفعات × {per} {currency}" + (f" (فائدة {interest}%)" if interest else ""),
            })
        out["installments"] = plans_out
        out["default_plan"] = {**default_plan, "per_installment": round(amount / default_plan["count"], 2)}

    return out


@router.post("/toggle")
async def toggle_gateway(payload: ToggleIn):
    cfg = ENABLED_GATEWAYS.setdefault(payload.merchant_id, {"country": "SA", "enabled": []})
    if payload.enable and payload.gateway_id not in cfg["enabled"]:
        cfg["enabled"].append(payload.gateway_id)
    elif not payload.enable and payload.gateway_id in cfg["enabled"]:
        cfg["enabled"].remove(payload.gateway_id)
    return cfg


@router.get("/enabled")
async def get_enabled(merchant_id: str = "demo"):
    cfg = ENABLED_GATEWAYS.get(merchant_id, {"country": "SA", "enabled": []})
    enabled_full = [gateway_by_id(gid) for gid in cfg["enabled"] if gateway_by_id(gid)]
    return {"merchant_id": merchant_id, "country": cfg["country"], "enabled": enabled_full}


@router.get("/health")
async def health():
    return {"status": "ok", "gateways_count": len(GATEWAYS), "countries_count": len(COUNTRY_PROFILES)}
