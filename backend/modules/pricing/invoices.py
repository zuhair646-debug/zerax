"""
Arabic PDF invoice generator + Resend email delivery.
Uses Amiri font for proper Arabic rendering with arabic-reshaper + python-bidi.
"""
import os
import logging
import base64
import io
from datetime import datetime, timezone
from typing import Dict, Any, Optional

import httpx
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

import arabic_reshaper
from bidi.algorithm import get_display

log = logging.getLogger("zerax.pricing.invoices")

# ════════════════════════════════════════════════════════════════
# Font registration (one-time)
# ════════════════════════════════════════════════════════════════
FONT_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "assets", "fonts")
FONT_DIR = os.path.abspath(FONT_DIR)
_FONTS_REGISTERED = False


def _ensure_fonts():
    global _FONTS_REGISTERED
    if _FONTS_REGISTERED:
        return
    try:
        pdfmetrics.registerFont(TTFont("Amiri", os.path.join(FONT_DIR, "Amiri-Regular.ttf")))
        pdfmetrics.registerFont(TTFont("Amiri-Bold", os.path.join(FONT_DIR, "Amiri-Bold.ttf")))
        _FONTS_REGISTERED = True
    except Exception as e:
        log.error(f"Failed to register Amiri font: {e}")


def _ar(text: str) -> str:
    """Reshape Arabic text + apply BiDi for correct rendering."""
    if not text:
        return ""
    try:
        return get_display(arabic_reshaper.reshape(str(text)))
    except Exception:
        return str(text)


# ════════════════════════════════════════════════════════════════
# Invoice number generator: ZTX-YYYYMM-NNNNN
# ════════════════════════════════════════════════════════════════
async def next_invoice_number(db) -> str:
    now = datetime.now(timezone.utc)
    prefix = f"ZTX-{now.strftime('%Y%m')}"
    # Atomic counter
    counter = await db.pricing_config.find_one_and_update(
        {"_key": f"invoice_counter:{prefix}"},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=True,
    )
    seq = (counter or {}).get("seq", 1)
    return f"{prefix}-{seq:05d}"


# ════════════════════════════════════════════════════════════════
# PDF generation
# ════════════════════════════════════════════════════════════════
def generate_invoice_pdf(invoice: Dict[str, Any]) -> bytes:
    """Renders an Arabic PDF invoice and returns the raw bytes."""
    _ensure_fonts()
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    W, H = A4

    # ── Header (brand banner) ────────────────────────────────────
    c.setFillColor(colors.HexColor("#0a0a0a"))
    c.rect(0, H - 30 * mm, W, 30 * mm, fill=1, stroke=0)
    c.setFillColor(colors.HexColor("#fbbf24"))
    c.setFont("Amiri-Bold", 28)
    c.drawString(20 * mm, H - 17 * mm, "ZERAX")
    c.setFillColor(colors.white)
    c.setFont("Amiri", 11)
    c.drawString(20 * mm, H - 24 * mm, _ar("منصة الإبداع بالذكاء الاصطناعي"))

    # Invoice label (right-aligned)
    c.setFillColor(colors.HexColor("#fbbf24"))
    c.setFont("Amiri-Bold", 22)
    c.drawRightString(W - 20 * mm, H - 17 * mm, _ar("فاتورة"))
    c.setFillColor(colors.white)
    c.setFont("Amiri", 10)
    c.drawRightString(W - 20 * mm, H - 24 * mm, f"INVOICE #{invoice['invoice_number']}")

    # ── Meta block ───────────────────────────────────────────────
    y = H - 45 * mm
    c.setFillColor(colors.HexColor("#111"))
    c.setFont("Amiri-Bold", 12)
    c.drawString(20 * mm, y, _ar("تاريخ الإصدار:"))
    c.setFont("Amiri", 11)
    c.drawString(60 * mm, y, invoice.get("issued_at_display", ""))

    c.setFont("Amiri-Bold", 12)
    c.drawString(110 * mm, y, _ar("رقم الطلب:"))
    c.setFont("Amiri", 10)
    c.drawString(140 * mm, y, invoice.get("order_id", "")[:40])

    # Customer
    y -= 8 * mm
    c.setFont("Amiri-Bold", 12)
    c.drawString(20 * mm, y, _ar("العميل:"))
    c.setFont("Amiri", 11)
    c.drawString(40 * mm, y, _ar(invoice.get("customer_name", "")))
    y -= 6 * mm
    c.setFont("Amiri", 10)
    c.setFillColor(colors.HexColor("#555"))
    c.drawString(40 * mm, y, invoice.get("customer_email", ""))

    # ── Line items table ─────────────────────────────────────────
    y -= 15 * mm
    c.setFillColor(colors.HexColor("#fbbf24"))
    c.rect(20 * mm, y, 170 * mm, 10 * mm, fill=1, stroke=0)
    c.setFillColor(colors.HexColor("#0a0a0a"))
    c.setFont("Amiri-Bold", 11)
    c.drawString(25 * mm, y + 3.5 * mm, _ar("الوصف"))
    c.drawString(120 * mm, y + 3.5 * mm, _ar("الكمية"))
    c.drawString(145 * mm, y + 3.5 * mm, _ar("السعر"))
    c.drawString(170 * mm, y + 3.5 * mm, _ar("الإجمالي"))

    y -= 10 * mm
    c.setFillColor(colors.HexColor("#111"))
    c.setFont("Amiri", 11)
    for item in invoice.get("items", []):
        c.drawString(25 * mm, y + 3 * mm, _ar(item.get("desc", ""))[:60])
        c.drawString(120 * mm, y + 3 * mm, str(item.get("qty", 1)))
        c.drawString(145 * mm, y + 3 * mm, f"${item.get('unit_price', 0):.2f}")
        c.drawString(170 * mm, y + 3 * mm, f"${item.get('total', 0):.2f}")
        y -= 8 * mm

    # ── Totals block ─────────────────────────────────────────────
    y -= 5 * mm
    c.setStrokeColor(colors.HexColor("#ddd"))
    c.line(20 * mm, y, 190 * mm, y)
    y -= 7 * mm

    def total_row(label, value, bold=False):
        nonlocal y
        c.setFont("Amiri-Bold" if bold else "Amiri", 12 if bold else 11)
        c.drawString(120 * mm, y, _ar(label))
        c.drawString(170 * mm, y, value)
        y -= 6 * mm

    total_row("المجموع الفرعي", f"${invoice.get('subtotal_usd', 0):.2f}")
    if invoice.get("discount_usd", 0) > 0:
        c.setFillColor(colors.HexColor("#22c55e"))
        total_row(f"الخصم ({invoice.get('promo_code', '')})", f"-${invoice['discount_usd']:.2f}")
        c.setFillColor(colors.HexColor("#111"))
    if invoice.get("tax_enabled"):
        total_row(
            f"{invoice.get('tax_label', 'ضريبة')} ({invoice.get('tax_rate_pct', 0)}%)",
            f"${invoice.get('tax_usd', 0):.2f}",
        )
    y -= 2 * mm
    c.setFillColor(colors.HexColor("#fbbf24"))
    c.rect(115 * mm, y - 2 * mm, 75 * mm, 9 * mm, fill=1, stroke=0)
    c.setFillColor(colors.HexColor("#0a0a0a"))
    total_row("الإجمالي المدفوع", f"${invoice.get('total_usd', 0):.2f}", bold=True)

    # Credits added
    if invoice.get("credits_added"):
        y -= 4 * mm
        c.setFillColor(colors.HexColor("#22c55e"))
        c.setFont("Amiri-Bold", 12)
        c.drawString(20 * mm, y, _ar(f"تمت إضافة {invoice['credits_added']:,} شعلة لرصيدك ✓"))

    # ── Footer ───────────────────────────────────────────────────
    c.setFillColor(colors.HexColor("#888"))
    c.setFont("Amiri", 9)
    c.drawCentredString(W / 2, 20 * mm, _ar("شكراً لاختيارك Zerax — منصة الإبداع بالذكاء الاصطناعي"))
    c.drawCentredString(W / 2, 15 * mm, "zerax.app  •  zerax.zx0@gmail.com")
    if invoice.get("tax_id"):
        c.drawCentredString(W / 2, 10 * mm, _ar(f"الرقم الضريبي: {invoice['tax_id']}"))

    c.showPage()
    c.save()
    return buf.getvalue()


# ════════════════════════════════════════════════════════════════
# Email delivery via Resend
# ════════════════════════════════════════════════════════════════
async def send_invoice_email(
    to_email: str,
    customer_name: str,
    invoice_number: str,
    pdf_bytes: bytes,
    total_usd: float,
    credits_added: int,
) -> bool:
    api_key = os.environ.get("RESEND_API_KEY")
    if not api_key:
        log.warning("RESEND_API_KEY missing — cannot send invoice email")
        return False
    from_email = os.environ.get("FROM_EMAIL", "onboarding@resend.dev")
    from_name = os.environ.get("FROM_NAME", "Zerax Billing")
    encoded_pdf = base64.b64encode(pdf_bytes).decode("ascii")
    html = (
        f"<div style='font-family:-apple-system,Segoe UI,sans-serif;max-width:600px;margin:auto;"
        f"padding:24px;background:#0a0a0a;color:#fff;border-radius:12px'>"
        f"<h1 style='color:#fbbf24;margin:0 0 8px'>شكراً لاشتراكك في Zerax! 🎉</h1>"
        f"<p style='color:#aaa'>مرحباً {customer_name}،</p>"
        f"<p>تم استلام دفعتك بنجاح. مرفق الفاتورة الرسمية بصيغة PDF.</p>"
        f"<div style='background:#1a1a1a;border-right:4px solid #fbbf24;padding:16px;margin:20px 0;border-radius:8px'>"
        f"<p><b>رقم الفاتورة:</b> {invoice_number}</p>"
        f"<p><b>المبلغ المدفوع:</b> ${total_usd:.2f} USD</p>"
        f"<p><b>الشعلات المُضافة:</b> {credits_added:,} ✨</p>"
        f"</div>"
        f"<p style='color:#888;font-size:13px'>للوصول إلى لوحة الاشتراك:<br>"
        f"<a href='https://zerax.app/billing' style='color:#fbbf24'>zerax.app/billing</a></p>"
        f"<hr style='border:0;border-top:1px solid #333;margin:20px 0'>"
        f"<p style='color:#666;font-size:11px'>Zerax — منصة الإبداع بالذكاء الاصطناعي</p>"
        f"</div>"
    )
    try:
        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.post(
                "https://api.resend.com/emails",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={
                    "from": f"{from_name} <{from_email}>",
                    "to": [to_email],
                    "subject": f"فاتورتك من Zerax — {invoice_number}",
                    "html": html,
                    "attachments": [{
                        "filename": f"{invoice_number}.pdf",
                        "content": encoded_pdf,
                    }],
                },
            )
            if r.status_code >= 400:
                log.warning(f"Resend rejected invoice email: {r.status_code} {r.text[:200]}")
                return False
            return True
    except Exception as e:
        log.error(f"send_invoice_email failed: {e}")
        return False
