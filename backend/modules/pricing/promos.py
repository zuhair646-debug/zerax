"""
Promo code engine — validates + applies discount + records usage.
"""
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional

log = logging.getLogger("zitex.pricing.promos")


async def validate_and_apply_promo(
    db,
    code: str,
    base_amount_usd: float,
    user_id: str,
    item_type: str,  # "subscription" | "pack"
) -> Dict[str, Any]:
    """Validates promo. Returns {valid, discount_usd, final_usd, message, promo_doc}."""
    if not code:
        return {"valid": False, "discount_usd": 0, "final_usd": base_amount_usd, "message": ""}

    code = code.strip().upper()
    promo = await db.promo_codes.find_one({"code": code, "active": True})
    if not promo:
        return {"valid": False, "discount_usd": 0, "final_usd": base_amount_usd,
                "message": "كود الخصم غير موجود أو غير مفعّل"}

    # Min order check
    if base_amount_usd < float(promo.get("min_order_usd", 0)):
        return {"valid": False, "discount_usd": 0, "final_usd": base_amount_usd,
                "message": f"الحد الأدنى للطلب ${promo.get('min_order_usd', 0)} لاستخدام الكود"}

    # Applies-to check
    applies = promo.get("applies_to", "all")
    if applies != "all" and applies != item_type:
        return {"valid": False, "discount_usd": 0, "final_usd": base_amount_usd,
                "message": f"هذا الكود لا ينطبق على {('الاشتراك' if item_type == 'subscription' else 'حزم الشحن')}"}

    # Max uses (global)
    if promo.get("max_uses") and int(promo.get("uses_count", 0)) >= int(promo["max_uses"]):
        return {"valid": False, "discount_usd": 0, "final_usd": base_amount_usd,
                "message": "تم استنفاذ الحد الأقصى من استخدامات هذا الكود"}

    # Max uses per user
    per_user_max = int(promo.get("max_uses_per_user", 0))
    if per_user_max > 0:
        user_usage = await db.promo_redemptions.count_documents({
            "promo_code": code, "user_id": user_id,
        })
        if user_usage >= per_user_max:
            return {"valid": False, "discount_usd": 0, "final_usd": base_amount_usd,
                    "message": "استخدمت هذا الكود من قبل"}

    # Compute discount
    discount = 0.0
    ptype = promo.get("type", "percent")
    if ptype == "percent":
        discount = base_amount_usd * (float(promo["value"]) / 100.0)
    elif ptype == "fixed":
        discount = float(promo["value"])

    # Cap
    max_disc = promo.get("max_discount_usd")
    if max_disc and discount > float(max_disc):
        discount = float(max_disc)
    if discount > base_amount_usd:
        discount = base_amount_usd

    final = max(0, base_amount_usd - discount)
    return {
        "valid": True,
        "discount_usd": round(discount, 2),
        "final_usd": round(final, 2),
        "message": f"تم تطبيق الخصم: -${round(discount, 2)}",
        "promo_doc": promo,
    }


async def redeem_promo(db, code: str, user_id: str, order_id: str, discount_usd: float):
    """Marks promo as used by this user — call after successful payment capture."""
    code = code.strip().upper()
    await db.promo_redemptions.insert_one({
        "promo_code": code,
        "user_id": user_id,
        "order_id": order_id,
        "discount_usd": float(discount_usd),
        "ts": datetime.now(timezone.utc).isoformat(),
    })
    await db.promo_codes.update_one(
        {"code": code},
        {"$inc": {"uses_count": 1}},
    )
