"""
Seed default plans / packs / promos into MongoDB on first boot.
Re-seedable: only inserts records that don't already exist.
"""
import logging
from datetime import datetime, timezone

from .catalog import PLANS, CREDIT_PACKS, DEFAULT_PROMOS, TAX_CONFIG, SERVICE_COSTS

log = logging.getLogger("zitex.pricing.seeds")


async def seed_pricing_defaults(db):
    """Idempotent seed — safe to call on every boot."""
    now = datetime.now(timezone.utc).isoformat()

    # Plans — always sync new fields (pay_later_eligible etc.) without overwriting admin price changes
    for plan in PLANS:
        exists = await db.pricing_plans.find_one({"id": plan["id"]})
        if not exists:
            await db.pricing_plans.insert_one({**plan, "created_at": now, "updated_at": now})
            log.info(f"  ✓ Seeded plan: {plan['id']}")
        else:
            # Sync new keys without overwriting existing values
            patch = {k: v for k, v in plan.items() if k not in exists}
            # Always update pay_later_eligible + features_ar (catalog-driven)
            if "pay_later_eligible" in plan:
                patch["pay_later_eligible"] = plan["pay_later_eligible"]
            if "features_ar" in plan:
                patch["features_ar"] = plan["features_ar"]
            if patch:
                patch["updated_at"] = now
                await db.pricing_plans.update_one({"id": plan["id"]}, {"$set": patch})
                log.info(f"  ⟳ Synced plan keys: {plan['id']} ({list(patch.keys())})")

    # Credit packs — same logic
    for pack in CREDIT_PACKS:
        exists = await db.credit_packs.find_one({"id": pack["id"]})
        if not exists:
            await db.credit_packs.insert_one({**pack, "created_at": now, "updated_at": now})
            log.info(f"  ✓ Seeded pack: {pack['id']}")
        else:
            patch = {k: v for k, v in pack.items() if k not in exists}
            if "pay_later_eligible" in pack:
                patch["pay_later_eligible"] = pack["pay_later_eligible"]
            if patch:
                patch["updated_at"] = now
                await db.credit_packs.update_one({"id": pack["id"]}, {"$set": patch})
                log.info(f"  ⟳ Synced pack keys: {pack['id']} ({list(patch.keys())})")

    # Promos
    for promo in DEFAULT_PROMOS:
        exists = await db.promo_codes.find_one({"code": promo["code"]})
        if not exists:
            await db.promo_codes.insert_one({
                **promo,
                "uses_count": 0,
                "created_at": now,
                "updated_at": now,
            })
            log.info(f"  ✓ Seeded promo: {promo['code']}")

    # Tax config singleton
    tax_doc = await db.pricing_config.find_one({"_key": "tax"})
    if not tax_doc:
        await db.pricing_config.insert_one({"_key": "tax", **TAX_CONFIG, "updated_at": now})
        log.info("  ✓ Seeded tax config")

    # Service costs (for transparency display + dynamic deduction)
    sc_doc = await db.pricing_config.find_one({"_key": "service_costs"})
    if not sc_doc:
        await db.pricing_config.insert_one({
            "_key": "service_costs",
            "items": SERVICE_COSTS,
            "updated_at": now,
        })
        log.info("  ✓ Seeded service costs")

    # Ensure indexes
    await db.pricing_plans.create_index("id", unique=True)
    await db.credit_packs.create_index("id", unique=True)
    await db.promo_codes.create_index("code", unique=True)
    await db.user_subscriptions.create_index("user_id")
    await db.credit_transactions.create_index([("user_id", 1), ("ts", -1)])
    await db.invoices.create_index([("user_id", 1), ("created_at", -1)])
    await db.invoices.create_index("invoice_number", unique=True)
    await db.paypal_orders.create_index("order_id", unique=True)
    await db.paypal_orders.create_index([("user_id", 1), ("created_at", -1)])
    log.info("✅ Pricing module ready (indexes ensured)")
