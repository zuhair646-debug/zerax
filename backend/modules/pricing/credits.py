"""
Credit ledger — atomic balance ops + transaction log.
Used everywhere AI services charge the user.
"""
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any
import uuid

log = logging.getLogger("zenrex.pricing.credits")


async def get_balance(db, user_id: str) -> float:
    user = await db.users.find_one({"id": user_id}, {"credits": 1, "_id": 0})
    if not user:
        return 0.0
    return float(user.get("credits", 0) or 0)


async def add_credits(
    db,
    user_id: str,
    amount: float,
    reason: str,
    meta: Optional[Dict[str, Any]] = None,
) -> float:
    """Add credits to user balance, write transaction. Returns new balance."""
    if amount <= 0:
        return await get_balance(db, user_id)
    res = await db.users.find_one_and_update(
        {"id": user_id},
        {"$inc": {"credits": amount}},
        return_document=True,
        projection={"credits": 1, "_id": 0},
    )
    new_balance = float((res or {}).get("credits", 0) or 0) if res else 0
    await db.credit_transactions.insert_one({
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "type": "credit",
        "amount": float(amount),
        "balance_after": new_balance,
        "reason": reason,
        "meta": meta or {},
        "ts": datetime.now(timezone.utc).isoformat(),
    })
    return new_balance


async def deduct_credits(
    db,
    user_id: str,
    amount: float,
    reason: str,
    meta: Optional[Dict[str, Any]] = None,
) -> float:
    """Deduct credits. Raises ValueError if insufficient. Returns new balance."""
    if amount <= 0:
        return await get_balance(db, user_id)
    # Atomic conditional decrement (only if balance >= amount)
    res = await db.users.find_one_and_update(
        {"id": user_id, "credits": {"$gte": amount}},
        {"$inc": {"credits": -amount}},
        return_document=True,
        projection={"credits": 1, "_id": 0},
    )
    if not res:
        current = await get_balance(db, user_id)
        raise ValueError(
            f"رصيد الشعلات غير كافٍ. تحتاج {int(amount)} شعلة، الرصيد {int(current)}"
        )
    new_balance = float(res.get("credits", 0) or 0)
    await db.credit_transactions.insert_one({
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "type": "debit",
        "amount": float(amount),
        "balance_after": new_balance,
        "reason": reason,
        "meta": meta or {},
        "ts": datetime.now(timezone.utc).isoformat(),
    })
    return new_balance


async def has_balance(db, user_id: str, amount: float) -> bool:
    return await get_balance(db, user_id) >= amount


async def charge_user(
    db,
    user_id: str,
    service_key: str,
    multiplier: float = 1.0,
    meta: Optional[Dict[str, Any]] = None,
) -> float:
    """High-level helper: charges based on SERVICE_COSTS catalog × multiplier.

    Owner accounts (role=owner/admin) are NEVER charged.
    Raises ValueError on insufficient balance.
    """
    user = await db.users.find_one({"id": user_id}, {"role": 1, "_id": 0})
    if user and user.get("role") in ("owner", "admin"):
        return await get_balance(db, user_id)  # admins free

    from .catalog import SERVICE_COSTS
    svc = SERVICE_COSTS.get(service_key)
    if not svc:
        log.warning(f"Unknown service key: {service_key} — skipping charge")
        return await get_balance(db, user_id)

    amount = float(svc["credits"]) * float(multiplier)
    if amount <= 0:
        return await get_balance(db, user_id)
    return await deduct_credits(
        db, user_id, amount,
        reason=f"service:{service_key}",
        meta={"service": service_key, "multiplier": multiplier, **(meta or {})},
    )


async def get_user_summary(db, user_id: str) -> Dict[str, Any]:
    """Returns balance + recent transactions + active subscription."""
    bal = await get_balance(db, user_id)
    txns = await db.credit_transactions.find(
        {"user_id": user_id}, {"_id": 0}
    ).sort("ts", -1).limit(20).to_list(length=20)
    sub = await db.user_subscriptions.find_one(
        {"user_id": user_id, "active": True}, {"_id": 0}
    )
    return {
        "balance": bal,
        "balance_usd_equivalent": round(bal / 1000, 2),
        "transactions": txns,
        "subscription": sub,
    }
