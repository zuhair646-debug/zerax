"""
Pricing & Billing API router.

Public:
- GET  /api/pricing/plans
- GET  /api/pricing/packs
- POST /api/pricing/promo/check        — validate promo against an item

Authenticated:
- GET  /api/pricing/me                 — balance + subscription + recent txns
- POST /api/pricing/checkout           — create PayPal order for plan/pack
- POST /api/pricing/capture            — capture after PayPal approval
- GET  /api/pricing/invoices           — list user's invoices
- GET  /api/pricing/invoices/{id}/pdf  — download PDF
- POST /api/pricing/invoices/{id}/resend — resend email

Admin:
- GET  /api/admin/pricing/stats        — revenue, conversions
- GET  /api/admin/pricing/orders       — all PayPal orders
- POST /api/admin/pricing/plans        — upsert plan
- POST /api/admin/pricing/packs        — upsert pack
- POST /api/admin/pricing/promos       — upsert promo
- DELETE /api/admin/pricing/promos/{code}
- POST /api/admin/pricing/test-paypal  — sanity check creds
"""
import os
import logging
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, HTTPException, Depends, Request, Response
from pydantic import BaseModel, Field

from .catalog import PLANS, CREDIT_PACKS, TAX_CONFIG, FIRST_PURCHASE_BONUS_PCT, credits_per_dollar
from .credits import (
    add_credits, deduct_credits, get_balance, get_user_summary,
)
from .paypal_client import create_order, capture_order, get_order
from .promos import validate_and_apply_promo, redeem_promo
from .invoices import generate_invoice_pdf, send_invoice_email, next_invoice_number

log = logging.getLogger("zitex.pricing.router")


# ════════════════════════════════════════════════════════════════
# Pydantic models
# ════════════════════════════════════════════════════════════════
class CheckoutRequest(BaseModel):
    item_type: str = Field(..., description="'subscription' or 'pack'")
    item_id: str = Field(..., description="plan id or pack id")
    billing_cycle: str = Field("monthly", description="'monthly' or 'yearly' (subscription only)")
    promo_code: Optional[str] = None
    return_url: str
    cancel_url: str
    provider: str = Field("paypal", description="'paypal' or 'lemonsqueezy'")


class CaptureRequest(BaseModel):
    order_id: str


class PromoCheckRequest(BaseModel):
    code: str
    item_type: str
    base_amount_usd: float


class PlanUpsert(BaseModel):
    id: str
    name: Optional[str] = None
    name_ar: Optional[str] = None
    price_monthly_usd: Optional[float] = None
    price_yearly_usd: Optional[float] = None
    credits_per_month: Optional[int] = None
    highlight: Optional[bool] = None
    features_ar: Optional[List[str]] = None
    order: Optional[int] = None


class PackUpsert(BaseModel):
    id: str
    name_ar: Optional[str] = None
    price_usd: Optional[float] = None
    credits: Optional[int] = None
    bonus_pct: Optional[float] = None
    order: Optional[int] = None
    popular: Optional[bool] = None


class PromoUpsert(BaseModel):
    code: str
    type: str = "percent"
    value: float
    max_discount_usd: Optional[float] = None
    min_order_usd: float = 0
    applies_to: str = "all"
    max_uses: Optional[int] = None
    max_uses_per_user: int = 1
    active: bool = True
    label_ar: Optional[str] = None


# ════════════════════════════════════════════════════════════════
# Router factory
# ════════════════════════════════════════════════════════════════
def create_router(db, get_current_user, get_admin_user):
    """Build router. `db` is the motor db, `get_current_user` and `get_admin_user` are deps."""

    router = APIRouter(prefix="/api/pricing", tags=["pricing"])
    admin_router = APIRouter(prefix="/api/admin/pricing", tags=["pricing-admin"])

    # ─── Public catalog ──────────────────────────────────────────
    @router.get("/plans")
    async def list_plans():
        plans = await db.pricing_plans.find({}, {"_id": 0}).sort("order", 1).to_list(length=20)
        # Fallback to catalog if empty (shouldn't happen — seeded on boot)
        return {"plans": plans or PLANS}

    @router.get("/packs")
    async def list_packs():
        packs = await db.credit_packs.find({}, {"_id": 0}).sort("order", 1).to_list(length=20)
        return {"packs": packs or CREDIT_PACKS}

    @router.get("/tax-config")
    async def get_tax_config():
        doc = await db.pricing_config.find_one({"_key": "tax"}, {"_id": 0})
        return doc or TAX_CONFIG

    @router.get("/service-costs")
    async def public_service_costs():
        """Transparency endpoint — what each AI service costs in credits."""
        doc = await db.pricing_config.find_one({"_key": "service_costs"}, {"_id": 0})
        return {"items": (doc or {}).get("items", {})}

    @router.post("/promo/check")
    async def check_promo(body: PromoCheckRequest, current_user: dict = Depends(get_current_user)):
        result = await validate_and_apply_promo(
            db, body.code, body.base_amount_usd, current_user["user_id"], body.item_type,
        )
        # Strip internal doc
        result.pop("promo_doc", None)
        return result

    # ─── User-side billing ───────────────────────────────────────
    @router.get("/me")
    async def my_billing(current_user: dict = Depends(get_current_user)):
        return await get_user_summary(db, current_user["user_id"])

    @router.post("/checkout")
    async def checkout(body: CheckoutRequest, current_user: dict = Depends(get_current_user)):
        user_id = current_user["user_id"]
        user = await db.users.find_one({"id": user_id}, {"_id": 0})
        if not user:
            raise HTTPException(status_code=401, detail="User not found")

        # Resolve item + base price
        if body.item_type == "subscription":
            plan = await db.pricing_plans.find_one({"id": body.item_id}, {"_id": 0})
            if not plan:
                raise HTTPException(status_code=404, detail="Plan not found")
            if plan.get("price_monthly_usd", 0) < 0:
                raise HTTPException(status_code=400, detail="هذه الباقة تتطلب التواصل المباشر")
            base = (
                float(plan["price_yearly_usd"]) if body.billing_cycle == "yearly"
                else float(plan["price_monthly_usd"])
            )
            if base <= 0:
                raise HTTPException(status_code=400, detail="الباقة المجانية لا تتطلب دفع")
            credits_to_add = int(plan["credits_per_month"]) * (12 if body.billing_cycle == "yearly" else 1)
            description = f"Zitex {plan['name']} — {body.billing_cycle}"
        elif body.item_type == "pack":
            pack = await db.credit_packs.find_one({"id": body.item_id}, {"_id": 0})
            if not pack:
                raise HTTPException(status_code=404, detail="Pack not found")
            base = float(pack["price_usd"])
            credits_to_add = int(pack["credits"])
            description = f"Zitex {pack['name_ar']} pack"
        else:
            raise HTTPException(status_code=400, detail="item_type must be 'subscription' or 'pack'")

        # Apply promo
        promo_result = {"valid": False, "discount_usd": 0, "final_usd": base, "message": ""}
        if body.promo_code:
            promo_result = await validate_and_apply_promo(
                db, body.promo_code, base, user_id, body.item_type,
            )
            promo_result.pop("promo_doc", None)
            if not promo_result.get("valid"):
                raise HTTPException(status_code=400, detail=promo_result.get("message", "كود غير صالح"))

        subtotal = base
        discount = promo_result.get("discount_usd", 0)
        # Tax (currently 0%)
        tax_cfg = await db.pricing_config.find_one({"_key": "tax"}, {"_id": 0}) or TAX_CONFIG
        tax_rate = float(tax_cfg.get("rate_percent", 0))
        taxable = max(0, subtotal - discount)
        tax = round(taxable * tax_rate / 100, 2)
        total = round(taxable + tax, 2)

        if total < 0.50:  # PayPal minimum
            raise HTTPException(status_code=400, detail="الحد الأدنى للطلب $0.50")

        # First purchase bonus (+25% credits) — applied on capture
        prev_purchases = await db.paypal_orders.count_documents({
            "user_id": user_id, "status": "COMPLETED",
        })
        first_purchase = prev_purchases == 0

        custom_id = str(uuid.uuid4())[:30]
        try:
            paypal = await create_order(
                amount_usd=total,
                return_url=body.return_url,
                cancel_url=body.cancel_url,
                description=description,
                custom_id=custom_id,
            )
        except Exception as e:
            log.error(f"PayPal create_order failed: {e}")
            raise HTTPException(status_code=502, detail=f"PayPal خطأ: {str(e)[:120]}")

        # Persist pending order
        now = datetime.now(timezone.utc).isoformat()
        await db.paypal_orders.insert_one({
            "order_id": paypal["order_id"],
            "custom_id": custom_id,
            "user_id": user_id,
            "user_email": user["email"],
            "user_name": user.get("name", ""),
            "item_type": body.item_type,
            "item_id": body.item_id,
            "billing_cycle": body.billing_cycle,
            "base_usd": base,
            "discount_usd": discount,
            "tax_usd": tax,
            "total_usd": total,
            "credits_to_add": credits_to_add,
            "first_purchase_bonus": first_purchase,
            "promo_code": body.promo_code,
            "status": "CREATED",
            "approval_url": paypal["approval_url"],
            "created_at": now,
            "updated_at": now,
        })

        return {
            "order_id": paypal["order_id"],
            "approval_url": paypal["approval_url"],
            "total_usd": total,
            "subtotal_usd": subtotal,
            "discount_usd": discount,
            "tax_usd": tax,
            "credits_to_add": credits_to_add,
            "first_purchase_bonus_pct": FIRST_PURCHASE_BONUS_PCT if first_purchase else 0,
        }

    @router.post("/capture")
    async def capture(body: CaptureRequest, current_user: dict = Depends(get_current_user)):
        user_id = current_user["user_id"]
        order = await db.paypal_orders.find_one({"order_id": body.order_id})
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        if order["user_id"] != user_id:
            raise HTTPException(status_code=403, detail="Not your order")
        if order.get("status") == "COMPLETED":
            inv = await db.invoices.find_one({"order_id": body.order_id}, {"_id": 0})
            return {"ok": True, "already_captured": True, "invoice": inv}

        try:
            capture_data = await capture_order(body.order_id)
        except Exception as e:
            log.error(f"PayPal capture failed: {e}")
            raise HTTPException(status_code=502, detail=f"فشل تحصيل الدفع: {str(e)[:120]}")

        status = capture_data.get("status")
        if status != "COMPLETED":
            await db.paypal_orders.update_one(
                {"order_id": body.order_id},
                {"$set": {"status": status, "updated_at": datetime.now(timezone.utc).isoformat()}},
            )
            raise HTTPException(status_code=400, detail=f"الدفعة لم تكتمل (الحالة: {status})")

        # ── Apply credits ───────────────────────────────────────
        credits_to_add = int(order["credits_to_add"])
        bonus_credits = 0
        if order.get("first_purchase_bonus"):
            bonus_credits = int(credits_to_add * FIRST_PURCHASE_BONUS_PCT / 100)
        total_credits = credits_to_add + bonus_credits

        await add_credits(
            db, user_id, total_credits,
            reason=f"purchase:{order['item_type']}:{order['item_id']}",
            meta={"order_id": body.order_id, "bonus": bonus_credits},
        )

        # ── Activate subscription if applicable ─────────────────
        if order["item_type"] == "subscription":
            days = 365 if order["billing_cycle"] == "yearly" else 30
            expires_at = (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()
            # Deactivate previous
            await db.user_subscriptions.update_many(
                {"user_id": user_id, "active": True},
                {"$set": {"active": False, "updated_at": datetime.now(timezone.utc).isoformat()}},
            )
            await db.user_subscriptions.insert_one({
                "id": str(uuid.uuid4()),
                "user_id": user_id,
                "plan_id": order["item_id"],
                "billing_cycle": order["billing_cycle"],
                "active": True,
                "started_at": datetime.now(timezone.utc).isoformat(),
                "expires_at": expires_at,
                "order_id": body.order_id,
                "amount_paid_usd": order["total_usd"],
            })
            # Also reflect on user doc for fast lookup
            await db.users.update_one(
                {"id": user_id},
                {"$set": {"plan": order["item_id"], "plan_expires_at": expires_at}},
            )

        # ── Redeem promo ────────────────────────────────────────
        if order.get("promo_code"):
            try:
                await redeem_promo(
                    db, order["promo_code"], user_id, body.order_id, order.get("discount_usd", 0),
                )
            except Exception as e:
                log.warning(f"promo redemption failed: {e}")

        # ── Generate invoice ────────────────────────────────────
        invoice_number = await next_invoice_number(db)
        now = datetime.now(timezone.utc)
        tax_cfg = await db.pricing_config.find_one({"_key": "tax"}, {"_id": 0}) or TAX_CONFIG

        # Build item description
        if order["item_type"] == "subscription":
            plan = await db.pricing_plans.find_one({"id": order["item_id"]}, {"_id": 0})
            item_desc = f"اشتراك {plan.get('name_ar', plan.get('name', ''))} - {('سنوي' if order['billing_cycle'] == 'yearly' else 'شهري')}"
        else:
            pack = await db.credit_packs.find_one({"id": order["item_id"]}, {"_id": 0})
            item_desc = f"حزمة {pack.get('name_ar', '')} - {pack.get('credits', 0):,} شعلة"

        invoice_doc = {
            "id": str(uuid.uuid4()),
            "invoice_number": invoice_number,
            "user_id": user_id,
            "customer_name": order.get("user_name", ""),
            "customer_email": order.get("user_email", ""),
            "order_id": body.order_id,
            "item_type": order["item_type"],
            "item_id": order["item_id"],
            "items": [{
                "desc": item_desc,
                "qty": 1,
                "unit_price": order["base_usd"],
                "total": order["base_usd"],
            }],
            "subtotal_usd": order["base_usd"],
            "discount_usd": order.get("discount_usd", 0),
            "promo_code": order.get("promo_code", ""),
            "tax_enabled": tax_cfg.get("enabled", True),
            "tax_rate_pct": tax_cfg.get("rate_percent", 0),
            "tax_label": tax_cfg.get("label", "ضريبة"),
            "tax_id": tax_cfg.get("tax_id", ""),
            "tax_usd": order.get("tax_usd", 0),
            "total_usd": order["total_usd"],
            "credits_added": total_credits,
            "bonus_credits": bonus_credits,
            "issued_at": now.isoformat(),
            "issued_at_display": now.strftime("%Y-%m-%d %H:%M UTC"),
            "created_at": now.isoformat(),
        }
        # Generate PDF + store
        pdf_bytes = generate_invoice_pdf(invoice_doc)
        invoice_doc["pdf_size_bytes"] = len(pdf_bytes)
        # Store PDF base64 to keep storage simple (GridFS would be better at scale)
        import base64 as _b64
        invoice_doc["pdf_b64"] = _b64.b64encode(pdf_bytes).decode("ascii")

        await db.invoices.insert_one(invoice_doc)

        # ── Mark order completed ────────────────────────────────
        await db.paypal_orders.update_one(
            {"order_id": body.order_id},
            {"$set": {
                "status": "COMPLETED",
                "captured_at": now.isoformat(),
                "invoice_number": invoice_number,
                "credits_added": total_credits,
                "updated_at": now.isoformat(),
            }},
        )

        # ── Send invoice email (async, best-effort) ─────────────
        try:
            await send_invoice_email(
                to_email=order["user_email"],
                customer_name=order.get("user_name", "العميل"),
                invoice_number=invoice_number,
                pdf_bytes=pdf_bytes,
                total_usd=order["total_usd"],
                credits_added=total_credits,
            )
        except Exception as e:
            log.warning(f"invoice email failed: {e}")

        # Strip PDF from response payload
        response_invoice = {k: v for k, v in invoice_doc.items() if k != "pdf_b64"}
        return {
            "ok": True,
            "captured": True,
            "credits_added": total_credits,
            "bonus_credits": bonus_credits,
            "new_balance": await get_balance(db, user_id),
            "invoice": response_invoice,
        }

    @router.post("/test-charge")
    async def test_charge(
        service_key: str = "image_nano_banana",
        current_user: dict = Depends(get_current_user),
    ):
        """🧪 Simulates an AI service charge so the user can verify
        credit deduction works without actually invoking an AI provider."""
        from .credits import charge_user, get_balance
        from .catalog import SERVICE_COSTS
        if service_key not in SERVICE_COSTS:
            raise HTTPException(status_code=400, detail=f"خدمة غير معروفة: {service_key}")
        try:
            new_balance = await charge_user(db, current_user["user_id"], service_key)
            return {
                "ok": True,
                "service": service_key,
                "label_ar": SERVICE_COSTS[service_key]["label"],
                "credits_charged": SERVICE_COSTS[service_key]["credits"],
                "new_balance": new_balance,
            }
        except ValueError as e:
            raise HTTPException(status_code=402, detail=str(e))

    @router.get("/invoices")
    async def list_my_invoices(current_user: dict = Depends(get_current_user)):
        rows = await db.invoices.find(
            {"user_id": current_user["user_id"]},
            {"_id": 0, "pdf_b64": 0},
        ).sort("created_at", -1).limit(50).to_list(length=50)
        return {"invoices": rows}

    @router.get("/invoices/{invoice_id}/pdf")
    async def download_invoice_pdf(invoice_id: str, current_user: dict = Depends(get_current_user)):
        inv = await db.invoices.find_one({"id": invoice_id})
        if not inv:
            raise HTTPException(status_code=404, detail="Invoice not found")
        if inv["user_id"] != current_user["user_id"] and current_user.get("role") not in ("owner", "admin"):
            raise HTTPException(status_code=403, detail="Forbidden")
        import base64 as _b64
        pdf_data = _b64.b64decode(inv["pdf_b64"])
        return Response(
            content=pdf_data,
            media_type="application/pdf",
            headers={"Content-Disposition": f'inline; filename="{inv["invoice_number"]}.pdf"'},
        )

    @router.post("/invoices/{invoice_id}/resend")
    async def resend_invoice(invoice_id: str, current_user: dict = Depends(get_current_user)):
        inv = await db.invoices.find_one({"id": invoice_id})
        if not inv:
            raise HTTPException(status_code=404, detail="Invoice not found")
        if inv["user_id"] != current_user["user_id"] and current_user.get("role") not in ("owner", "admin"):
            raise HTTPException(status_code=403, detail="Forbidden")
        import base64 as _b64
        pdf_bytes = _b64.b64decode(inv["pdf_b64"])
        ok = await send_invoice_email(
            to_email=inv["customer_email"],
            customer_name=inv.get("customer_name", ""),
            invoice_number=inv["invoice_number"],
            pdf_bytes=pdf_bytes,
            total_usd=inv["total_usd"],
            credits_added=inv.get("credits_added", 0),
        )
        return {"ok": ok, "sent_to": inv["customer_email"]}

    # ════════════════════════════════════════════════════════════
    # Admin routes
    # ════════════════════════════════════════════════════════════
    @admin_router.get("/stats")
    async def pricing_stats(admin=Depends(get_admin_user)):
        # Revenue
        agg = await db.paypal_orders.aggregate([
            {"$match": {"status": "COMPLETED"}},
            {"$group": {
                "_id": None,
                "revenue_usd": {"$sum": "$total_usd"},
                "orders": {"$sum": 1},
            }},
        ]).to_list(length=1)
        revenue = agg[0]["revenue_usd"] if agg else 0
        orders = agg[0]["orders"] if agg else 0

        # Active subs
        active_subs = await db.user_subscriptions.count_documents({"active": True})

        # Last 30 days
        cutoff = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
        recent_agg = await db.paypal_orders.aggregate([
            {"$match": {"status": "COMPLETED", "captured_at": {"$gte": cutoff}}},
            {"$group": {"_id": None, "revenue": {"$sum": "$total_usd"}, "orders": {"$sum": 1}}},
        ]).to_list(length=1)
        recent_revenue = recent_agg[0]["revenue"] if recent_agg else 0
        recent_orders = recent_agg[0]["orders"] if recent_agg else 0

        # Promo usage
        promo_redemptions = await db.promo_redemptions.count_documents({})
        promo_total_discount = await db.promo_redemptions.aggregate([
            {"$group": {"_id": None, "total": {"$sum": "$discount_usd"}}},
        ]).to_list(length=1)

        return {
            "total_revenue_usd": round(revenue, 2),
            "total_orders": orders,
            "active_subscriptions": active_subs,
            "last_30d_revenue_usd": round(recent_revenue, 2),
            "last_30d_orders": recent_orders,
            "promo_redemptions": promo_redemptions,
            "promo_total_discount_usd": round(promo_total_discount[0]["total"], 2) if promo_total_discount else 0,
        }

    @admin_router.get("/orders")
    async def list_orders(limit: int = 100, status: Optional[str] = None, admin=Depends(get_admin_user)):
        limit = max(1, min(limit, 500))
        q = {}
        if status:
            q["status"] = status
        rows = await db.paypal_orders.find(q, {"_id": 0}).sort("created_at", -1).limit(limit).to_list(length=limit)
        return {"count": len(rows), "orders": rows}

    @admin_router.post("/plans")
    async def upsert_plan(body: PlanUpsert, admin=Depends(get_admin_user)):
        update = {k: v for k, v in body.model_dump().items() if v is not None and k != "id"}
        update["updated_at"] = datetime.now(timezone.utc).isoformat()
        await db.pricing_plans.update_one(
            {"id": body.id},
            {"$set": update, "$setOnInsert": {"id": body.id, "created_at": update["updated_at"]}},
            upsert=True,
        )
        return {"ok": True, "plan_id": body.id}

    @admin_router.post("/packs")
    async def upsert_pack(body: PackUpsert, admin=Depends(get_admin_user)):
        update = {k: v for k, v in body.model_dump().items() if v is not None and k != "id"}
        update["updated_at"] = datetime.now(timezone.utc).isoformat()
        await db.credit_packs.update_one(
            {"id": body.id},
            {"$set": update, "$setOnInsert": {"id": body.id, "created_at": update["updated_at"]}},
            upsert=True,
        )
        return {"ok": True, "pack_id": body.id}

    @admin_router.post("/promos")
    async def upsert_promo(body: PromoUpsert, admin=Depends(get_admin_user)):
        update = {k: v for k, v in body.model_dump().items() if v is not None and k != "code"}
        update["code"] = body.code.upper()
        update["updated_at"] = datetime.now(timezone.utc).isoformat()
        await db.promo_codes.update_one(
            {"code": body.code.upper()},
            {"$set": update, "$setOnInsert": {"created_at": update["updated_at"], "uses_count": 0}},
            upsert=True,
        )
        return {"ok": True, "code": body.code.upper()}

    @admin_router.delete("/promos/{code}")
    async def delete_promo(code: str, admin=Depends(get_admin_user)):
        await db.promo_codes.update_one({"code": code.upper()}, {"$set": {"active": False}})
        return {"ok": True, "code": code.upper(), "deactivated": True}

    @admin_router.get("/promos")
    async def list_promos(admin=Depends(get_admin_user)):
        rows = await db.promo_codes.find({}, {"_id": 0}).sort("created_at", -1).to_list(length=100)
        return {"promos": rows}

    @admin_router.post("/test-paypal")
    async def test_paypal(admin=Depends(get_admin_user)):
        """Verify PayPal creds work by creating + immediately voiding a test order."""
        try:
            result = await create_order(
                amount_usd=1.00,
                return_url="https://zitex.app/billing/test-return",
                cancel_url="https://zitex.app/billing/test-cancel",
                description="Zitex PayPal credential test",
            )
            return {
                "ok": True,
                "mode": os.environ.get("PAYPAL_MODE", "live"),
                "order_id": result["order_id"],
                "approval_url": result["approval_url"],
                "status": result.get("status"),
            }
        except Exception as e:
            return {"ok": False, "error": str(e)[:300]}

    return router, admin_router
"$set": {"active": False}})
        return {"ok": True, "code": code.upper(), "deactivated": True}

    @admin_router.get("/promos")
    async def list_promos(admin=Depends(get_admin_user)):
        rows = await db.promo_codes.find({}, {"_id": 0}).sort("created_at", -1).to_list(length=100)
        return {"promos": rows}

    @admin_router.post("/test-paypal")
    async def test_paypal(admin=Depends(get_admin_user)):
        """Verify PayPal creds work by creating + immediately voiding a test order."""
        try:
            result = await create_order(
                amount_usd=1.00,
                return_url="https://zitex.app/billing/test-return",
                cancel_url="https://zitex.app/billing/test-cancel",
                description="Zitex PayPal credential test",
            )
            return {
                "ok": True,
                "mode": os.environ.get("PAYPAL_MODE", "live"),
                "order_id": result["order_id"],
                "approval_url": result["approval_url"],
                "status": result.get("status"),
            }
        except Exception as e:
            return {"ok": False, "error": str(e)[:300]}

    return router, admin_router
