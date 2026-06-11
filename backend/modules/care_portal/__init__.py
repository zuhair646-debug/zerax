"""
Zenrex Care Portal — Post-delivery client dashboard
====================================================
After a Ready Site is delivered, the client (merchant) gets a Care Portal at
/care/{project_id} where they can:
  • View live preview of their site
  • Edit basic content via AI assistant
  • Manage subscription / payment keys / ZATCA config
  • UPGRADE: Convert their site to a Mobile App (paid feature) ✨

Endpoints (all under /api/care):
  GET  /project/{id}                 — project info + entitlements
  POST /upgrade/mobile-app           — purchase + enable Mobile App conversion
  GET  /pwa-status/{id}              — current PWA enabled state
  POST /toggle-pwa/{id}              — owner-only override (admin)
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# Subscription pricing (SAR / month)
MOBILE_APP_MONTHLY_SAR = 99
MOBILE_APP_YEARLY_SAR = 950  # ~20% discount

# Credits-based pricing (alternative for users with credits)
MOBILE_APP_MONTHLY_CREDITS = 990


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _now_dt():
    return datetime.now(timezone.utc)


class UpgradeIn(BaseModel):
    project_id: str
    plan: str  # 'monthly' | 'yearly'
    pay_with: str = "credits"  # 'credits' | 'stripe'


def create_care_router(db, get_current_user) -> APIRouter:
    router = APIRouter(prefix="/api/care", tags=["care-portal"])

    async def _get_project_owned(project_id: str, user_id: str) -> Dict[str, Any]:
        project = await db.ready_sites_projects.find_one(
            {"id": project_id, "user_id": user_id}, {"_id": 0}
        )
        if not project:
            raise HTTPException(404, "المشروع غير موجود أو لا تملك صلاحية")
        return project

    async def _deduct_credits(uid: str, amount: int, reason: str) -> bool:
        r = await db.users.update_one(
            {"id": uid, "credits": {"$gte": amount}},
            {"$inc": {"credits": -amount},
             "$push": {"credit_history": {"amount": -amount, "reason": reason, "timestamp": _now()}}}
        )
        return r.modified_count > 0

    # ---- Get project + entitlements ----
    @router.get("/project/{project_id}")
    async def get_project(project_id: str, user=Depends(get_current_user)):
        project = await _get_project_owned(project_id, user["user_id"])
        ent = project.get("entitlements", {}) or {}
        mobile_app = ent.get("mobile_app", {}) or {}
        is_active = mobile_app.get("active") and mobile_app.get("expires_at", "") > _now()
        return {
            "id": project["id"],
            "name": project.get("name"),
            "slug": project.get("slug"),
            "template_mode": project.get("template_mode"),
            "market_id": project.get("market_id"),
            "preview_url": f"/api/ready-sites/preview/{project_id}",
            "created_at": project.get("created_at"),
            "version": project.get("version", 1),
            "entitlements": {
                "mobile_app": {
                    "active": bool(is_active),
                    "plan": mobile_app.get("plan"),
                    "activated_at": mobile_app.get("activated_at"),
                    "expires_at": mobile_app.get("expires_at"),
                    "pricing": {
                        "monthly_sar": MOBILE_APP_MONTHLY_SAR,
                        "yearly_sar": MOBILE_APP_YEARLY_SAR,
                        "monthly_credits": MOBILE_APP_MONTHLY_CREDITS,
                    },
                }
            },
        }

    # ---- Upgrade: enable Mobile App conversion ----
    @router.post("/upgrade/mobile-app")
    async def upgrade_mobile_app(payload: UpgradeIn, user=Depends(get_current_user)):
        project = await _get_project_owned(payload.project_id, user["user_id"])

        if payload.plan not in ("monthly", "yearly"):
            raise HTTPException(400, "الخطة غير صالحة (اختر monthly أو yearly)")

        cost_credits = MOBILE_APP_MONTHLY_CREDITS if payload.plan == "monthly" else MOBILE_APP_MONTHLY_CREDITS * 10
        cost_sar = MOBILE_APP_MONTHLY_SAR if payload.plan == "monthly" else MOBILE_APP_YEARLY_SAR
        days = 31 if payload.plan == "monthly" else 365

        if payload.pay_with == "credits":
            ok = await _deduct_credits(
                user["user_id"], cost_credits,
                f"mobile_app_upgrade_{payload.plan}_{payload.project_id}"
            )
            if not ok:
                raise HTTPException(402, f"رصيد النقاط غير كافٍ ({cost_credits} نقطة مطلوبة)")
            payment_method = "credits"
            paid_amount = cost_credits
        else:
            # Stripe / Mada path would create a checkout session here and return URL.
            # For now we return a marker so frontend can show "redirecting to payment"
            raise HTTPException(501, "الدفع عبر Stripe قيد التطوير — استخدم النقاط حالياً")

        expires_at = (_now_dt() + timedelta(days=days)).isoformat()
        await db.ready_sites_projects.update_one(
            {"id": payload.project_id, "user_id": user["user_id"]},
            {
                "$set": {
                    "entitlements.mobile_app": {
                        "active": True,
                        "plan": payload.plan,
                        "payment_method": payment_method,
                        "paid_amount": paid_amount,
                        "paid_currency": "credits" if payment_method == "credits" else "SAR",
                        "activated_at": _now(),
                        "expires_at": expires_at,
                    },
                    "updated_at": _now(),
                },
                "$push": {
                    "billing_history": {
                        "type": "mobile_app_upgrade",
                        "plan": payload.plan,
                        "amount": paid_amount,
                        "method": payment_method,
                        "timestamp": _now(),
                    }
                },
            },
        )

        return {
            "ok": True,
            "plan": payload.plan,
            "expires_at": expires_at,
            "mobile_app_url": f"/install/{payload.project_id}",
            "message": "✓ تم تفعيل تحويل الموقع إلى تطبيق! زوار موقعك سيرون زر التثبيت تلقائياً.",
        }

    # ---- Public: PWA status for a project (used by site's auto-install script) ----
    @router.get("/pwa-status/{project_id}")
    async def pwa_status(project_id: str):
        project = await db.ready_sites_projects.find_one(
            {"id": project_id},
            {"_id": 0, "id": 1, "name": 1, "entitlements": 1, "branding": 1},
        )
        if not project:
            raise HTTPException(404, "Project not found")
        ent = (project.get("entitlements") or {}).get("mobile_app") or {}
        is_active = ent.get("active") and ent.get("expires_at", "") > _now()
        brand = project.get("branding", {}) or {}
        return {
            "project_id": project_id,
            "name": project.get("name"),
            "pwa_enabled": bool(is_active),
            "expires_at": ent.get("expires_at") if is_active else None,
            "primary_color": brand.get("primary_color") or "#7c3aed",
        }

    return router
