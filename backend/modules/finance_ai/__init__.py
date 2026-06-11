"""AI-assisted finance intelligence for Zenrex owner dashboard.

Read-only by default: summarizes payments, credit liability, revenue quality,
risk signals, and owner recommendations without mutating users/payments.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple

from fastapi import APIRouter, Depends


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_dt(value: Any) -> Optional[datetime]:
    if not value:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, str):
        try:
            v = value.replace("Z", "+00:00")
            dt = datetime.fromisoformat(v)
            return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        except Exception:
            return None
    return None


def _num(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except Exception:
        return default


def _safe_round(value: float, digits: int = 2) -> float:
    try:
        return round(float(value), digits)
    except Exception:
        return 0.0


def _currency(payment: Dict[str, Any]) -> str:
    return str(payment.get("currency") or payment.get("currency_code") or "SAR").upper()


def _status(payment: Dict[str, Any]) -> str:
    return str(payment.get("status") or "pending").lower()


def _amount(payment: Dict[str, Any]) -> float:
    return _num(payment.get("amount") or payment.get("total") or payment.get("price"))


def _user_id(doc: Dict[str, Any]) -> str:
    return str(doc.get("user_id") or doc.get("id") or "unknown")


def _days_since(dt: Optional[datetime]) -> Optional[float]:
    if not dt:
        return None
    return (_now() - dt).total_seconds() / 86400


def _trend_for_payments(payments: List[Dict[str, Any]], status_filter: Tuple[str, ...] = ("approved", "paid", "completed")) -> Dict[str, Any]:
    today = _now().date()
    buckets: Dict[str, Dict[str, float]] = {}
    for i in range(13, -1, -1):
        day = today - timedelta(days=i)
        buckets[day.isoformat()] = {"SAR": 0.0, "USD": 0.0, "count": 0.0}

    for p in payments:
        if _status(p) not in status_filter:
            continue
        dt = _parse_dt(p.get("created_at") or p.get("paid_at") or p.get("updated_at"))
        if not dt:
            continue
        key = dt.date().isoformat()
        if key not in buckets:
            continue
        cur = _currency(p)
        if cur not in buckets[key]:
            buckets[key][cur] = 0.0
        buckets[key][cur] += _amount(p)
        buckets[key]["count"] += 1

    series = [{"date": k, **{c: _safe_round(v) for c, v in val.items()}} for k, val in buckets.items()]
    last7 = series[-7:]
    prev7 = series[:7]
    last7_sar = sum(x.get("SAR", 0) for x in last7)
    prev7_sar = sum(x.get("SAR", 0) for x in prev7)
    change = None if prev7_sar == 0 else _safe_round(((last7_sar - prev7_sar) / prev7_sar) * 100, 1)
    return {"series": series, "last7_sar": _safe_round(last7_sar), "prev7_sar": _safe_round(prev7_sar), "change_pct": change}


def _make_risk(level: str, title: str, detail: str, action: str, score: int) -> Dict[str, Any]:
    return {"level": level, "title": title, "detail": detail, "action": action, "score": score}


def _recommendation(priority: str, title: str, why: str, next_step: str, impact: str) -> Dict[str, Any]:
    return {"priority": priority, "title": title, "why": why, "next_step": next_step, "expected_impact": impact}


async def _collect_finance_data(db) -> Dict[str, Any]:
    since_90 = (_now() - timedelta(days=90)).isoformat()
    payments = await db.payments.find({}, {"_id": 0}).sort("created_at", -1).to_list(2000)
    payment_orders = await db.payment_orders.find(
        {"created_at": {"$gte": since_90}}, {"_id": 0}
    ).sort("created_at", -1).to_list(1000)
    users = await db.users.find(
        {}, {"_id": 0, "password": 0, "password_hash": 0}
    ).sort("created_at", -1).to_list(2000)
    offers = await db.offers.find({}, {"_id": 0}).to_list(200)
    pricing = await db.service_pricing.find_one({"type": "default"}, {"_id": 0})
    activities = await db.activity_logs.find(
        {"created_at": {"$gte": since_90}}, {"_id": 0}
    ).sort("created_at", -1).to_list(1500)
    stripe_transactions = await db.payment_transactions.find(
        {"created_at": {"$gte": since_90}}, {"_id": 0}
    ).sort("created_at", -1).to_list(1000)
    return {
        "payments": payments,
        "payment_orders": payment_orders,
        "users": users,
        "offers": offers,
        "pricing": pricing or {},
        "activities": activities,
        "stripe_transactions": stripe_transactions,
    }


def _analyze(data: Dict[str, Any]) -> Dict[str, Any]:
    payments: List[Dict[str, Any]] = data["payments"]
    orders: List[Dict[str, Any]] = data["payment_orders"]
    users: List[Dict[str, Any]] = data["users"]
    offers: List[Dict[str, Any]] = data["offers"]
    activities: List[Dict[str, Any]] = data["activities"]
    stripe_transactions: List[Dict[str, Any]] = data["stripe_transactions"]

    status_counts = Counter(_status(p) for p in payments)
    revenue_by_status_currency: Dict[str, Dict[str, float]] = defaultdict(lambda: defaultdict(float))
    revenue_confirmed: Dict[str, float] = defaultdict(float)
    pending_by_currency: Dict[str, float] = defaultdict(float)
    rejected_by_currency: Dict[str, float] = defaultdict(float)
    customer_spend: Dict[str, Dict[str, Any]] = {}

    confirmed_statuses = {"approved", "paid", "completed", "success"}
    pending_statuses = {"pending", "created", "requires_action"}
    rejected_statuses = {"rejected", "failed", "cancelled", "canceled"}

    for p in payments:
        st = _status(p)
        cur = _currency(p)
        amt = _amount(p)
        revenue_by_status_currency[st][cur] += amt
        if st in confirmed_statuses:
            revenue_confirmed[cur] += amt
            uid = _user_id(p)
            if uid not in customer_spend:
                customer_spend[uid] = {
                    "user_id": uid,
                    "name": p.get("user_name") or "غير معروف",
                    "email": p.get("user_email") or "",
                    "SAR": 0.0,
                    "USD": 0.0,
                    "count": 0,
                }
            customer_spend[uid][cur] = customer_spend[uid].get(cur, 0.0) + amt
            customer_spend[uid]["count"] += 1
        elif st in pending_statuses:
            pending_by_currency[cur] += amt
        elif st in rejected_statuses:
            rejected_by_currency[cur] += amt

    # Include Stripe checkout transactions/orders as extra signal if legacy payments is empty/partial.
    stripe_confirmed = [t for t in stripe_transactions if str(t.get("payment_status") or t.get("status") or "").lower() in confirmed_statuses]
    orders_completed = [o for o in orders if str(o.get("status") or "").lower() in confirmed_statuses]

    total_credits = sum(_num(u.get("credits")) for u in users)
    negative_credit_users = [u for u in users if _num(u.get("credits")) < 0]
    high_credit_users = sorted(
        [u for u in users if _num(u.get("credits")) >= 500],
        key=lambda u: _num(u.get("credits")),
        reverse=True,
    )[:10]

    active_offers = [o for o in offers if o.get("is_active", True)]
    offer_price_per_credit = []
    for o in active_offers:
        credits = _num(o.get("credits"))
        price = _num(o.get("price") or o.get("price_sar"))
        if credits > 0 and price > 0:
            offer_price_per_credit.append({
                "id": o.get("id"),
                "name": o.get("name"),
                "credits": credits,
                "price": price,
                "price_per_credit": _safe_round(price / credits, 4),
                "discount": _num(o.get("discount")),
            })

    now = _now()
    stale_pending = []
    duplicate_keys = defaultdict(list)
    for p in payments:
        created = _parse_dt(p.get("created_at"))
        st = _status(p)
        key = (p.get("user_id"), _amount(p), _currency(p), p.get("proof_image_url"))
        if key[0] and key[1] and key[3]:
            duplicate_keys[key].append(p)
        age_days = _days_since(created)
        if st in pending_statuses and age_days is not None and age_days >= 2:
            stale_pending.append({
                "id": p.get("id"),
                "user_name": p.get("user_name"),
                "amount": _amount(p),
                "currency": _currency(p),
                "age_days": _safe_round(age_days, 1),
            })

    duplicate_payments = []
    for key, docs in duplicate_keys.items():
        if len(docs) > 1:
            duplicate_payments.append({
                "user_id": key[0],
                "amount": key[1],
                "currency": key[2],
                "count": len(docs),
                "payment_ids": [d.get("id") for d in docs[:5]],
            })

    rejected_count = sum(status_counts[s] for s in rejected_statuses)
    pending_count = sum(status_counts[s] for s in pending_statuses)
    confirmed_count = sum(status_counts[s] for s in confirmed_statuses)
    total_payment_count = max(len(payments), 1)
    rejection_rate = rejected_count / total_payment_count
    pending_rate = pending_count / total_payment_count

    trend = _trend_for_payments(payments)
    avg_daily_sar = trend["last7_sar"] / 7 if trend["last7_sar"] else 0
    forecast_30_sar = _safe_round(avg_daily_sar * 30)

    risks: List[Dict[str, Any]] = []
    if stale_pending:
        risks.append(_make_risk(
            "high" if len(stale_pending) >= 5 else "medium",
            "مدفوعات معلقة قديمة",
            f"يوجد {len(stale_pending)} دفعة معلقة لأكثر من 48 ساعة؛ هذا يبطئ التحصيل ويزيد استفسارات العملاء.",
            "راجع أقدم المدفوعات أولاً، وفعّل تنبيه تلقائي بعد 24 ساعة.",
            min(95, 45 + len(stale_pending) * 7),
        ))
    if duplicate_payments:
        risks.append(_make_risk(
            "high",
            "اشتباه تكرار إثبات دفع",
            f"تم رصد {len(duplicate_payments)} حالة تشابه في المستخدم/المبلغ/الإثبات.",
            "لا تعتمد أي دفعة مكررة قبل مقارنة صورة الإثبات ورقم التحويل.",
            88,
        ))
    if negative_credit_users:
        risks.append(_make_risk(
            "high",
            "أرصدة سالبة",
            f"يوجد {len(negative_credit_users)} مستخدمين برصيد نقاط سالب.",
            "صحح الرصيد أو راجع عمليات الخصم الأخيرة لمنع خسارة خدمة غير مدفوعة.",
            82,
        ))
    if rejection_rate >= 0.25 and len(payments) >= 8:
        risks.append(_make_risk(
            "medium",
            "نسبة رفض مرتفعة",
            f"نسبة الرفض الحالية {round(rejection_rate * 100, 1)}% من إجمالي المدفوعات.",
            "وضّح تعليمات الدفع في صفحة الدفع وأضف تحقق من المبلغ قبل رفع الإثبات.",
            70,
        ))
    if pending_rate >= 0.35 and len(payments) >= 8:
        risks.append(_make_risk(
            "medium",
            "تراكم في مراجعة المدفوعات",
            f"نسبة المعلق {round(pending_rate * 100, 1)}%؛ قد تحتاج SLA أو فرز تلقائي.",
            "رتب القائمة حسب العمر والمبلغ وابدأ بالأكبر قيمة.",
            66,
        ))
    if total_credits > 10000:
        risks.append(_make_risk(
            "medium",
            "التزام نقاط كبير",
            f"إجمالي النقاط غير المستخدمة تقريباً {int(total_credits):,} نقطة.",
            "راقب تكلفة توليد الصور/الفيديو مقابل النقاط المباعة وعدّل pricing عند الحاجة.",
            58,
        ))

    recommendations: List[Dict[str, Any]] = []
    recommendations.append(_recommendation(
        "high",
        "حوّل مراجعة الدفع إلى طابور ذكي",
        "أعلى خسارة تشغيلية عادةً تأتي من تأخر اعتماد الدفع أو اعتماد مكرر.",
        "اعرض المدفوعات حسب risk_score ثم age_days، مع زر نسخ رسالة واتساب للعميل.",
        "تسريع التحصيل وتقليل الأخطاء اليدوية.",
    ))
    if not active_offers:
        recommendations.append(_recommendation(
            "high",
            "أنشئ عروض نقاط فعّالة",
            "لا توجد عروض نشطة، وهذا يقلل التحويل من الزوار إلى مشترين.",
            "فعّل 3 عروض: بداية، محترف، أعمال مع خصم واضح للباقات الأكبر.",
            "رفع معدل الشراء الأول.",
        ))
    if offer_price_per_credit:
        cheapest = min(offer_price_per_credit, key=lambda x: x["price_per_credit"])
        recommendations.append(_recommendation(
            "medium",
            "راجع ربحية أرخص عرض",
            f"أرخص عرض هو {cheapest.get('name')} بسعر {cheapest['price_per_credit']} لكل نقطة.",
            "قارن تكلفة استخدام النقطة في الصور والفيديو قبل أي خصم كبير.",
            "حماية هامش الربح.",
        ))
    if forecast_30_sar == 0:
        recommendations.append(_recommendation(
            "medium",
            "ابدأ تتبع إيراد مؤكد موحد",
            "لا توجد إيرادات SAR مؤكدة في آخر 7 أيام أو البيانات موزعة بين collections.",
            "وحّد Stripe/PayPal/التحويل البنكي في finance ledger واحد لاحقاً.",
            "تقارير مالية أدق وأسرع.",
        ))
    else:
        recommendations.append(_recommendation(
            "medium",
            "استغل توقع الإيراد القادم",
            f"بناءً على آخر 7 أيام، توقع 30 يوم تقريباً {forecast_30_sar:,.0f} SAR.",
            "اختبر عرض ترقية للباقات الأعلى للعملاء الأعلى إنفاقاً.",
            "زيادة متوسط قيمة الطلب.",
        ))

    if not risks:
        risks.append(_make_risk(
            "low",
            "لا توجد مخاطر مالية حرجة حالياً",
            "لم تظهر مدفوعات معلقة قديمة أو تكرارات واضحة أو أرصدة سالبة ضمن آخر فحص.",
            "استمر بالمراجعة اليومية وفعّل مراقبة آلية عند نمو الحجم.",
            18,
        ))

    top_customers = sorted(
        customer_spend.values(),
        key=lambda c: (c.get("SAR", 0) * 1 + c.get("USD", 0) * 3.75),
        reverse=True,
    )[:10]

    intelligence_score = 100
    intelligence_score -= min(25, len(stale_pending) * 3)
    intelligence_score -= 18 if duplicate_payments else 0
    intelligence_score -= min(15, int(rejection_rate * 40))
    intelligence_score -= 15 if negative_credit_users else 0
    intelligence_score = max(35, intelligence_score)

    return {
        "generated_at": now.isoformat(),
        "health_score": intelligence_score,
        "summary": {
            "payments_total": len(payments),
            "payments_confirmed": confirmed_count,
            "payments_pending": pending_count,
            "payments_rejected": rejected_count,
            "users_total": len(users),
            "active_offers": len(active_offers),
            "credits_liability": _safe_round(total_credits, 0),
            "confirmed_revenue": {k: _safe_round(v) for k, v in revenue_confirmed.items()},
            "pending_revenue": {k: _safe_round(v) for k, v in pending_by_currency.items()},
            "rejected_revenue": {k: _safe_round(v) for k, v in rejected_by_currency.items()},
            "stripe_transactions_90d": len(stripe_transactions),
            "stripe_confirmed_90d": len(stripe_confirmed),
            "payment_orders_90d": len(orders),
            "payment_orders_completed_90d": len(orders_completed),
        },
        "status_breakdown": {k: v for k, v in status_counts.items()},
        "revenue_by_status_currency": {
            st: {cur: _safe_round(val) for cur, val in cur_map.items()}
            for st, cur_map in revenue_by_status_currency.items()
        },
        "trend": trend,
        "forecast": {
            "next_30_days_sar": forecast_30_sar,
            "confidence": "medium" if confirmed_count >= 5 else "low",
            "basis": "آخر 7 أيام من المدفوعات المؤكدة في collection payments",
        },
        "risks": sorted(risks, key=lambda r: r["score"], reverse=True),
        "recommendations": recommendations,
        "watchlist": {
            "stale_pending_payments": stale_pending[:20],
            "duplicate_payment_signals": duplicate_payments[:20],
            "negative_credit_users": [
                {"id": u.get("id"), "name": u.get("name"), "email": u.get("email"), "credits": _num(u.get("credits"))}
                for u in negative_credit_users[:20]
            ],
            "high_credit_users": [
                {"id": u.get("id"), "name": u.get("name"), "email": u.get("email"), "credits": _num(u.get("credits"))}
                for u in high_credit_users
            ],
        },
        "top_customers": [
            {**c, "SAR": _safe_round(c.get("SAR", 0)), "USD": _safe_round(c.get("USD", 0))}
            for c in top_customers
        ],
        "offer_unit_economics": offer_price_per_credit,
        "activity_signal": {
            "events_90d": len(activities),
            "payment_events_90d": sum(1 for a in activities if "payment" in str(a.get("action", "")).lower()),
        },
        "ai_notes": [
            "التحليل لا يعدّل أي رصيد أو دفعة؛ قراءة فقط.",
            "الأولوية: منع الاعتماد المكرر، تقليل المعلق، مراقبة تكلفة النقاط.",
            "كل الأرقام تعتمد على البيانات الحالية في MongoDB وقد تختلف إذا توجد مدفوعات خارج النظام.",
        ],
    }


def create_finance_ai_router(db, get_current_user, require_owner):
    router = APIRouter(prefix="/api/admin/finance-ai", tags=["finance-ai"])

    @router.get("/overview")
    async def finance_overview(owner: dict = Depends(require_owner)):
        data = await _collect_finance_data(db)
        return _analyze(data)

    @router.get("/risks")
    async def finance_risks(owner: dict = Depends(require_owner)):
        data = await _collect_finance_data(db)
        analysis = _analyze(data)
        return {
            "generated_at": analysis["generated_at"],
            "health_score": analysis["health_score"],
            "risks": analysis["risks"],
            "watchlist": analysis["watchlist"],
        }

    @router.post("/snapshot")
    async def save_finance_snapshot(owner: dict = Depends(require_owner)):
        data = await _collect_finance_data(db)
        analysis = _analyze(data)
        snapshot = {
            "id": f"finance-ai-{int(_now().timestamp())}",
            "owner_id": owner.get("id") or owner.get("user_id"),
            "created_at": _now().isoformat(),
            "health_score": analysis["health_score"],
            "summary": analysis["summary"],
            "risk_count": len(analysis["risks"]),
            "top_risk": analysis["risks"][0] if analysis["risks"] else None,
            "recommendations": analysis["recommendations"][:5],
        }
        await db.finance_ai_snapshots.insert_one(snapshot)
        snapshot.pop("_id", None)
        return {"ok": True, "snapshot": snapshot}

    @router.get("/snapshots")
    async def list_finance_snapshots(limit: int = 20, owner: dict = Depends(require_owner)):
        limit = max(1, min(int(limit or 20), 50))
        snapshots = await db.finance_ai_snapshots.find(
            {}, {"_id": 0}
        ).sort("created_at", -1).to_list(limit)
        return {"snapshots": snapshots}

    return router
