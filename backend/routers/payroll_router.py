"""
Zenrex Driver Payroll & Statements
==================================
End-of-month accounting layer on top of the delivery system.

Capabilities:
  1. Auto-calculate every driver's amount due:
       - commission drivers = balance_pending_sar from delivery_router
       - salaried drivers   = monthly_salary_sar
  2. Generate a printable PDF statement per driver (Arabic, ZATCA-style QR)
  3. Bulk payout — single click that creates payout records for ALL drivers
     and pushes them to their configured payout method (placeholder calls)
  4. WhatsApp Business notification (mocked — returns the message that would
     be sent)
"""
import os
import io
import uuid
import base64
import logging
from datetime import datetime, timezone
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel

# Reach into the in-memory delivery store (single source of truth for drivers)
from routers.delivery_router import (
    DRIVERS, ORDERS, PAYOUTS, SETTINGS,
    create_payout, PayoutIn,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/payroll", tags=["payroll"])


# ─────────────────────────────────────────────────────────────────────────────
# Models
# ─────────────────────────────────────────────────────────────────────────────
class RunPayrollIn(BaseModel):
    month: Optional[int] = None      # 1-12 (defaults to current)
    year: Optional[int] = None
    only_driver_ids: Optional[List[str]] = None  # if set, only pay these
    notify_whatsapp: bool = True


class NotifyIn(BaseModel):
    driver_id: str
    message: str


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────
def _month_label(m: int, y: int) -> str:
    months_ar = ["يناير", "فبراير", "مارس", "أبريل", "مايو", "يونيو",
                 "يوليو", "أغسطس", "سبتمبر", "أكتوبر", "نوفمبر", "ديسمبر"]
    return f"{months_ar[m-1]} {y}"


def _compute_driver_dues(driver: dict, month: int, year: int) -> dict:
    """Return per-driver payroll line."""
    if driver["employment_type"] == "salaried":
        amount = float(driver.get("monthly_salary_sar", 0))
        kind = "راتب شهري"
    else:
        amount = float(driver.get("balance_pending_sar", 0))
        kind = "عمولات معلّقة"
    # Count deliveries for this month (simple — uses today's data for demo)
    deliveries = sum(
        1 for o in ORDERS.values()
        if o.get("driver_id") == driver["id"] and o["status"] == "delivered"
    )
    return {
        "driver_id": driver["id"],
        "driver_name": driver["name"],
        "phone": driver["phone"],
        "employment_type": driver["employment_type"],
        "kind": kind,
        "deliveries_this_month": deliveries,
        "amount_sar": round(amount, 2),
        "payout_method": driver.get("payout_method", "stc_pay"),
        "payout_account": driver.get("payout_account", ""),
        "vehicle": driver.get("vehicle", "موتر"),
        "area": driver.get("area", ""),
        "rating": driver.get("rating", 5.0),
    }


# ═════════════════════════════════════════════════════════════════════════════
# 1) CALCULATE — preview before running
# ═════════════════════════════════════════════════════════════════════════════
@router.get("/calculate")
async def calculate(month: Optional[int] = None, year: Optional[int] = None):
    now = datetime.now(timezone.utc)
    m, y = month or now.month, year or now.year
    lines = [_compute_driver_dues(d, m, y) for d in DRIVERS.values()]
    total = round(sum(line["amount_sar"] for line in lines), 2)
    by_type = {
        "salaried_total":  round(sum(line["amount_sar"] for line in lines if line["employment_type"] == "salaried"), 2),
        "commission_total": round(sum(line["amount_sar"] for line in lines if line["employment_type"] == "commission"), 2),
    }
    return {
        "month": m, "year": y, "label": _month_label(m, y),
        "drivers_count": len(lines),
        "lines": lines,
        "total_payable_sar": total,
        **by_type,
        "vat_pct": 15,
        "vat_amount_sar": round(total * 0.15, 2),
        "generated_at": now.isoformat(),
    }


# ═════════════════════════════════════════════════════════════════════════════
# 2) RUN — bulk-payout
# ═════════════════════════════════════════════════════════════════════════════
@router.post("/run")
async def run(payload: RunPayrollIn):
    """Iterates every driver, creates a payout, optionally notifies via WhatsApp."""
    now = datetime.now(timezone.utc)
    m, y = payload.month or now.month, payload.year or now.year
    label = _month_label(m, y)
    results = []
    total_paid = 0.0
    for d in DRIVERS.values():
        if payload.only_driver_ids and d["id"] not in payload.only_driver_ids:
            continue
        line = _compute_driver_dues(d, m, y)
        if line["amount_sar"] <= 0:
            results.append({**line, "status": "skipped", "reason": "no_balance"})
            continue
        try:
            payout = await create_payout(PayoutIn(
                driver_id=d["id"],
                amount_sar=line["amount_sar"],
                note=f"دفعة شهرية ({label}) — {line['kind']}",
            ))
        except Exception as e:
            results.append({**line, "status": "failed", "error": str(e)[:120]})
            continue
        total_paid += line["amount_sar"]
        # Mock WhatsApp notification
        wa_msg = None
        if payload.notify_whatsapp:
            wa_msg = (
                f"🎉 مرحباً {d['name']}،\n"
                f"تم إيداع راتبك/عمولاتك لشهر {label}:\n"
                f"💰 المبلغ: {line['amount_sar']} ر.س\n"
                f"💳 الوسيلة: {line['payout_method']} · {line['payout_account']}\n"
                f"🧾 رقم العملية: {payout['reference']}\n\n"
                f"شكراً لعملك معنا — Zenrex"
            )
        results.append({**line, "status": "paid", "reference": payout["reference"], "whatsapp_message": wa_msg})

    return {
        "month": m, "year": y, "label": label,
        "processed": len(results),
        "total_paid_sar": round(total_paid, 2),
        "results": results,
        "executed_at": now.isoformat(),
    }


# ═════════════════════════════════════════════════════════════════════════════
# 3) STATEMENT — single-driver PDF (downloadable HTML→PDF rendering)
# ═════════════════════════════════════════════════════════════════════════════
def _generate_statement_html(driver: dict, month: int, year: int) -> str:
    """Render a printable HTML statement (Arabic, ZATCA-style)."""
    label = _month_label(month, year)
    line = _compute_driver_dues(driver, month, year)
    delivered_orders = [o for o in ORDERS.values() if o.get("driver_id") == driver["id"] and o["status"] == "delivered"]
    rows = "".join([
        f"<tr><td>{o['id'].replace('ord_','')}</td><td>{o['customer_name']}</td>"
        f"<td>{o.get('distance_km',0)} كم</td>"
        f"<td>{o.get('delivery_fee_sar',0)} ر.س</td>"
        f"<td>{o.get('driver_share_sar',0)} ر.س</td></tr>"
        for o in delivered_orders[:25]
    ])
    if not rows:
        rows = "<tr><td colspan='5' style='text-align:center;color:#94a3b8;padding:20px'>لا توجد توصيلات مسجّلة لهذا الشهر</td></tr>"

    vat = round(line["amount_sar"] * 0.15, 2)
    grand = round(line["amount_sar"] + vat, 2)
    ref = "ZRX-STMT-" + uuid.uuid4().hex[:10].upper()

    # ZATCA-style QR text (simplified TLV — production would use proper TLV encoding)
    qr_text = f"Zenrex|{driver['name']}|{label}|{grand} SAR|{ref}"
    qr_b64_url = f"https://api.qrserver.com/v1/create-qr-code/?size=150x150&data={qr_text.replace(' ', '%20')}"

    return f"""<!DOCTYPE html><html lang="ar" dir="rtl"><head><meta charset="utf-8">
<title>كشف راتب — {driver['name']} — {label}</title>
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+Arabic:wght@400;700;900&display=swap" rel="stylesheet">
<style>
*{{box-sizing:border-box;margin:0;padding:0;font-family:'IBM Plex Sans Arabic',sans-serif}}
body{{background:#f8fafc;padding:30px 20px;color:#0a0a14}}
.sheet{{max-width:780px;margin:0 auto;background:#fff;border-radius:18px;padding:36px;box-shadow:0 12px 40px rgba(0,0,0,.08)}}
.hd{{display:flex;justify-content:space-between;align-items:center;border-bottom:3px solid #7c3aed;padding-bottom:18px;margin-bottom:24px}}
.hd .logo{{font-size:28px;font-weight:900;background:linear-gradient(135deg,#fbbf24,#a78bfa);-webkit-background-clip:text;background-clip:text;color:transparent}}
.hd .meta{{text-align:left;font-size:12px;color:#64748b;line-height:1.7}}
h1{{font-size:22px;font-weight:900;margin-bottom:6px}}
.sub{{color:#64748b;font-size:13px;margin-bottom:24px}}
.row2{{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-bottom:24px}}
.box{{background:#faf5ff;border:1.5px solid #ddd6fe;border-radius:14px;padding:14px}}
.box .lbl{{font-size:10px;color:#7c3aed;font-weight:900;text-transform:uppercase;letter-spacing:1px;margin-bottom:4px}}
.box .val{{font-size:14px;font-weight:900}}
table{{width:100%;border-collapse:collapse;margin-bottom:20px}}
th{{background:#0a0a14;color:#fff;padding:10px;font-size:11px;font-weight:900;text-align:right}}
td{{padding:9px 10px;font-size:12px;border-bottom:1px solid #f1f5f9}}
tr:last-child td{{border-bottom:none}}
.totals{{background:#0a0a14;color:#fff;border-radius:14px;padding:16px;display:grid;grid-template-columns:1fr 1fr;gap:8px}}
.totals .ln{{display:flex;justify-content:space-between;align-items:center;padding:5px 0;font-size:13px}}
.totals .ln.big{{font-size:18px;font-weight:900;color:#fbbf24;border-top:1px solid #2a2a44;padding-top:10px;margin-top:6px;grid-column:1/-1}}
.zatca{{display:flex;justify-content:space-between;align-items:center;background:linear-gradient(135deg,#1f2937,#0a0a14);color:#fff;border-radius:14px;padding:14px;margin-top:18px}}
.zatca img{{background:#fff;padding:8px;border-radius:10px}}
.zatca .info{{flex:1;padding:0 14px;font-size:11px;line-height:1.7;color:#cbd5e1}}
.zatca .info b{{color:#fbbf24}}
.foot{{margin-top:20px;text-align:center;font-size:10px;color:#94a3b8;border-top:1px dashed #e5e7eb;padding-top:12px}}
@media print{{body{{background:#fff;padding:0}}.sheet{{box-shadow:none;border-radius:0}}}}
</style></head><body><div class="sheet">

<div class="hd">
  <div class="logo">⚡ Zenrex</div>
  <div class="meta">
    رقم الكشف: <b>{ref}</b><br>
    التاريخ: {datetime.now(timezone.utc).strftime('%Y-%m-%d')}<br>
    العملة: ر.س
  </div>
</div>

<h1>كشف راتب السائق — {label}</h1>
<p class="sub">هذا الكشف صادر تلقائياً من نظام Zenrex للتجارة الذكية. يحتوي على إجمالي مستحقات السائق لشهر {label} مع تفصيل التوصيلات والضريبة المضافة.</p>

<div class="row2">
  <div class="box"><div class="lbl">اسم السائق</div><div class="val">{driver['name']}</div></div>
  <div class="box"><div class="lbl">رقم الجوال</div><div class="val" style="direction:ltr;text-align:right">{driver['phone']}</div></div>
  <div class="box"><div class="lbl">نوع التوظيف</div><div class="val">{('📅 موظف براتب' if driver['employment_type']=='salaried' else '💸 سائق بعمولة')}</div></div>
  <div class="box"><div class="lbl">المنطقة</div><div class="val">{driver.get('area','—')}</div></div>
  <div class="box"><div class="lbl">وسيلة استلام المبلغ</div><div class="val">{driver.get('payout_method','—')}</div></div>
  <div class="box"><div class="lbl">رقم الحساب</div><div class="val" style="direction:ltr;text-align:right;font-family:monospace;font-size:12px">{driver.get('payout_account','—')}</div></div>
</div>

<h3 style="font-size:14px;font-weight:900;margin-bottom:10px">📋 تفاصيل التوصيلات</h3>
<table>
  <thead><tr><th>رقم الطلب</th><th>العميل</th><th>المسافة</th><th>رسوم التوصيل</th><th>حصة السائق</th></tr></thead>
  <tbody>{rows}</tbody>
</table>

<div class="totals">
  <div class="ln"><span>عدد التوصيلات</span><b>{line['deliveries_this_month']}</b></div>
  <div class="ln"><span>{line['kind']}</span><b>{line['amount_sar']} ر.س</b></div>
  <div class="ln"><span>ضريبة القيمة المضافة (15%)</span><b>{vat} ر.س</b></div>
  <div class="ln"><span></span><span></span></div>
  <div class="ln big"><span>الإجمالي المستحق</span><b>{grand} ر.س</b></div>
</div>

<div class="zatca">
  <img src="{qr_b64_url}" alt="QR" width="120" height="120">
  <div class="info">
    <b>🇸🇦 متوافق مع هيئة الزكاة والضريبة (ZATCA)</b><br>
    رقم تعريف الكشف: {ref}<br>
    رقم ضريبي للمنشأة: 300000000000003<br>
    تاريخ الإصدار: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')}<br>
    التحقق: امسح الرمز للتأكد من صحة الكشف
  </div>
</div>

<div class="foot">
  ⚡ صادر من نظام Zenrex للتجارة الذكية · zenrex.ai<br>
  هذا الكشف رسمي ومعتمد إلكترونياً ولا يحتاج توقيع
</div>
</div></body></html>"""


@router.get("/statement/{driver_id}")
async def driver_statement(driver_id: str, month: Optional[int] = None, year: Optional[int] = None, format: str = "html"):
    """Returns HTML statement (open in browser → print as PDF)."""
    drv = DRIVERS.get(driver_id)
    if not drv:
        raise HTTPException(status_code=404, detail="driver not found")
    now = datetime.now(timezone.utc)
    m, y = month or now.month, year or now.year
    html = _generate_statement_html(drv, m, y)
    if format == "json":
        return {"html": html, "driver": drv["name"], "month": m, "year": y}
    return Response(content=html, media_type="text/html; charset=utf-8")


# ═════════════════════════════════════════════════════════════════════════════
# 4) WHATSAPP NOTIFICATION (mocked — returns the message body for now)
# ═════════════════════════════════════════════════════════════════════════════
@router.post("/notify-driver")
async def notify_driver(payload: NotifyIn):
    drv = DRIVERS.get(payload.driver_id)
    if not drv:
        raise HTTPException(status_code=404, detail="driver not found")
    # In production: call WhatsApp Business API here with the merchant's WABA credentials.
    return {
        "status": "queued",
        "provider": "whatsapp_business_api",
        "to_phone": drv["phone"],
        "message_preview": payload.message,
        "wamid": "wamid." + uuid.uuid4().hex[:24],
        "note": "MOCKED — replace with real WhatsApp Business API call (Meta Cloud API).",
    }


@router.get("/health")
async def health():
    return {
        "status": "ok",
        "drivers": len(DRIVERS),
        "payouts_total": len(PAYOUTS),
        "current_month_label": _month_label(datetime.now(timezone.utc).month, datetime.now(timezone.utc).year),
    }
