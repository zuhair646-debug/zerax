"""Multi-tenant payment gateways for generated e-commerce sites.

Each tenant (website_project) stores its own provider credentials encrypted at rest.
Supported providers:
- moyasar  — Saudi gateway (Mada, STC Pay, Apple Pay, credit cards)
- tabby    — BNPL (scaffolding only — stores keys, redirect to be implemented)
- tamara   — BNPL (scaffolding only)
- cod      — Cash on Delivery (no keys required)

Storage shape (inside website_projects):
    payment_gateways = {
        "moyasar": {
            "enabled": true,
            "publishable_key": "pk_test_...",  # plaintext (safe for frontend)
            "secret_key_enc": "<fernet>",       # encrypted
            "methods": ["creditcard", "mada", "applepay", "stcpay"],
            "test_mode": true,
        },
        "cod": {"enabled": true},
        ...
    }

All endpoints enforce server-side total/currency — the frontend never supplies the amount.
"""
from __future__ import annotations

import os
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import httpx
from cryptography.fernet import Fernet, InvalidToken

log = logging.getLogger(__name__)

# ------------------------------------------------------------------
# Encryption helpers
# ------------------------------------------------------------------
_FERNET: Optional[Fernet] = None


def _fernet() -> Fernet:
    global _FERNET
    if _FERNET is not None:
        return _FERNET
    key = os.environ.get("PAYMENT_KEYS_FERNET")
    if not key:
        raise RuntimeError("PAYMENT_KEYS_FERNET not configured in environment")
    _FERNET = Fernet(key.encode() if isinstance(key, str) else key)
    return _FERNET


def encrypt(value: str) -> str:
    if not value:
        return ""
    return _fernet().encrypt(value.encode()).decode()


def decrypt(value: str) -> str:
    if not value:
        return ""
    try:
        return _fernet().decrypt(value.encode()).decode()
    except InvalidToken:
        log.error("Fernet decrypt failed — key rotation issue?")
        return ""


def mask(value: str, keep: int = 4) -> str:
    """Show only last `keep` chars for safe display."""
    if not value:
        return ""
    if len(value) <= keep:
        return "•" * len(value)
    return "•" * (len(value) - keep) + value[-keep:]


# ------------------------------------------------------------------
# Catalogue (used by frontend & checkout renderer)
# ------------------------------------------------------------------
PROVIDERS = {
    "moyasar": {
        "id": "moyasar",
        "name": "Moyasar",
        "name_ar": "مُيسّر",
        "description_ar": "بوابة دفع سعودية — تدعم مدى، STC Pay، Apple Pay، وبطاقات الائتمان",
        "supports_methods": ["creditcard", "mada", "applepay", "stcpay"],
        "needs_keys": ["publishable_key", "secret_key"],
        "key_hint": "احصل عليها من لوحة تحكم Moyasar → Settings → API Keys (تبدأ بـ pk_test_ و sk_test_)",
        "signup_url": "https://dashboard.moyasar.com",
        "comparison": {
            "fees_pct": "2.5% + 1 ر.س",
            "settlement": "T+1 يوم عمل",
            "best_for": "المتاجر العامة، المطاعم، الخدمات",
            "pros": ["أقل رسوم في السعودية", "مرخّصة من ساما", "تسوية يومية", "يدعم Mada محلياً", "سهولة إعداد"],
            "cons": ["لا يدعم تقسيط BNPL", "يحتاج سجل تجاري سعودي للتفعيل"],
            "currencies": ["SAR"],
            "license": "ساما (SAMA) - رخصة مدفوعات كاملة",
            "setup_time": "5 دقائق (sandbox) / 1-3 أيام عمل للإنتاج",
        },
    },
    "tabby": {
        "id": "tabby",
        "name": "Tabby",
        "name_ar": "تابي",
        "description_ar": "الشراء الآن والدفع لاحقاً — 4 دفعات بدون فوائد",
        "supports_methods": ["tabby"],
        "needs_keys": ["public_key", "secret_key"],
        "key_hint": "احصل عليها من لوحة تحكم Tabby → Developers → API Keys",
        "signup_url": "https://tabby.ai",
        "comparison": {
            "fees_pct": "4-6% (حسب الباقة)",
            "settlement": "فوري — تابي تدفع لك كامل المبلغ مقدماً",
            "best_for": "متاجر قيمة سلة 100+ ر.س، موضة، إلكترونيات",
            "pros": ["زيادة معدل التحويل 30%+", "تابي تحمل مخاطر عدم السداد", "دفع فوري للتاجر", "تكامل سهل"],
            "cons": ["رسوم أعلى", "محدود للسعودية/الإمارات/الكويت", "قد يرفض الطلب حسب تقييم العميل"],
            "currencies": ["SAR", "AED", "KWD"],
            "license": "مرخّصة من ساما + CBUAE",
            "setup_time": "يومين (يتطلب مراجعة التاجر)",
        },
    },
    "tamara": {
        "id": "tamara",
        "name": "Tamara",
        "name_ar": "تمارا",
        "description_ar": "ادفع لاحقاً بدون رسوم — 3 دفعات شهرية",
        "supports_methods": ["tamara"],
        "needs_keys": ["api_token", "notification_token"],
        "key_hint": "احصل عليها من Tamara Merchant Portal → Developers",
        "signup_url": "https://tamara.co",
        "comparison": {
            "fees_pct": "5-7% (حسب الباقة)",
            "settlement": "فوري",
            "best_for": "متاجر المشتريات الكبيرة (1000+ ر.س)، أثاث، إلكترونيات منزلية",
            "pros": ["شريحة عملاء أكبر في السعودية", "خيار 30 يوم بدون فوائد", "دفع فوري مضمون"],
            "cons": ["رسوم أعلى من Moyasar", "حد أدنى للقيمة"],
            "currencies": ["SAR", "AED"],
            "license": "مرخّصة من ساما",
            "setup_time": "3-5 أيام عمل",
        },
    },
    "cod": {
        "id": "cod",
        "name": "Cash on Delivery",
        "name_ar": "الدفع عند الاستلام",
        "description_ar": "العميل يدفع نقداً للسائق عند تسليم الطلب",
        "supports_methods": ["cod"],
        "needs_keys": [],
        "key_hint": "",
        "signup_url": "",
        "comparison": {
            "fees_pct": "0% (لكن تحمل مخاطر رفض الاستلام)",
            "settlement": "فوري (نقداً مع السائق)",
            "best_for": "المطاعم، خدمات التوصيل المحلي، العملاء الحذرين من الدفع الإلكتروني",
            "pros": ["مجاني تماماً", "لا يحتاج حساب تجاري", "ثقة مع العملاء الجدد"],
            "cons": ["معدل رفض/إلغاء أعلى", "تحصيل الكاش يعرّض السائق للمخاطر", "صعوبة المحاسبة"],
            "currencies": ["SAR"],
            "license": "لا يتطلب",
            "setup_time": "فوري",
        },
    },
}


def catalog_public() -> List[Dict[str, Any]]:
    """Safe catalogue for frontend."""
    return [dict(p) for p in PROVIDERS.values()]


def compare_all() -> List[Dict[str, Any]]:
    """Comparison table — used by the 'Gateway Comparison' view in client dashboard."""
    rows = []
    for pid, p in PROVIDERS.items():
        c = p.get("comparison", {})
        rows.append({
            "id": pid,
            "name_ar": p["name_ar"],
            "description_ar": p["description_ar"],
            "methods": p["supports_methods"],
            "fees": c.get("fees_pct", "—"),
            "settlement": c.get("settlement", "—"),
            "best_for": c.get("best_for", "—"),
            "pros": c.get("pros", []),
            "cons": c.get("cons", []),
            "currencies": c.get("currencies", []),
            "license": c.get("license", "—"),
            "setup_time": c.get("setup_time", "—"),
            "signup_url": p.get("signup_url", ""),
        })
    return rows


# ------------------------------------------------------------------
# Safe views of stored config (for client dashboard)
# ------------------------------------------------------------------
def safe_gateway_view(provider_id: str, raw: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    raw = raw or {}
    meta = PROVIDERS.get(provider_id, {})
    out: Dict[str, Any] = {
        "id": provider_id,
        "name": meta.get("name"),
        "name_ar": meta.get("name_ar"),
        "enabled": bool(raw.get("enabled")),
        "configured": False,
        "test_mode": bool(raw.get("test_mode", True)),
        "methods": raw.get("methods") or meta.get("supports_methods", []),
        "coming_soon": meta.get("coming_soon", False),
    }
    if provider_id == "moyasar":
        pub = raw.get("publishable_key") or ""
        sec_enc = raw.get("secret_key_enc") or ""
        out["publishable_key_preview"] = mask(pub, 6) if pub else ""
        out["secret_key_preview"] = mask(decrypt(sec_enc), 4) if sec_enc else ""
        out["configured"] = bool(pub and sec_enc)
    elif provider_id == "tabby":
        pub = raw.get("public_key") or ""
        sec_enc = raw.get("secret_key_enc") or ""
        out["public_key_preview"] = mask(pub, 6) if pub else ""
        out["secret_key_preview"] = mask(decrypt(sec_enc), 4) if sec_enc else ""
        out["configured"] = bool(pub and sec_enc)
    elif provider_id == "tamara":
        tok_enc = raw.get("api_token_enc") or ""
        notif_enc = raw.get("notification_token_enc") or ""
        out["api_token_preview"] = mask(decrypt(tok_enc), 4) if tok_enc else ""
        out["notification_token_preview"] = mask(decrypt(notif_enc), 4) if notif_enc else ""
        out["configured"] = bool(tok_enc)
    elif provider_id == "cod":
        out["configured"] = True  # no keys needed
    return out


# ------------------------------------------------------------------
# Provider implementations
# ------------------------------------------------------------------
class PaymentError(Exception):
    pass


class MoyasarProvider:
    """Moyasar integration — create payments via Invoice API + verify by fetching.

    Uses HTTP Basic Auth with secret_key as username.
    Test cards:
      Mada:      5123450000000008 (any future expiry, any CVC)
      Visa:      4111111111111111
      Mastercard 5555555555554444
    """
    API_BASE = "https://api.moyasar.com/v1"

    def __init__(self, publishable_key: str, secret_key: str):
        self.publishable_key = publishable_key
        self.secret_key = secret_key

    async def test(self) -> Tuple[bool, str]:
        """Hit the Moyasar payments list endpoint (limit=1) to verify credentials."""
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                r = await client.get(
                    f"{self.API_BASE}/payments",
                    auth=(self.secret_key, ""),
                    params={"per": 1, "page": 1},
                )
            if r.status_code in (200, 201):
                return True, "تم التحقق من مفاتيح Moyasar بنجاح ✓"
            if r.status_code == 401:
                return False, "المفتاح السري غير صحيح (401)"
            return False, f"استجابة غير متوقعة: {r.status_code}"
        except Exception as e:
            return False, f"فشل الاتصال بـMoyasar: {e}"

    async def create_invoice(
        self,
        *,
        amount_sar: float,
        description: str,
        callback_url: str,
        methods: List[str],
        metadata: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Create a hosted Invoice — returns {url, invoice_id}."""
        if amount_sar <= 0:
            raise PaymentError("المبلغ يجب أن يكون أكبر من صفر")
        payload = {
            "amount": int(round(amount_sar * 100)),  # halalas
            "currency": "SAR",
            "description": description[:500],
            "callback_url": callback_url,
            "success_url": callback_url,
            "metadata": {k: str(v)[:100] for k, v in (metadata or {}).items()},
        }
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                r = await client.post(
                    f"{self.API_BASE}/invoices",
                    auth=(self.secret_key, ""),
                    json=payload,
                )
            if r.status_code not in (200, 201):
                raise PaymentError(f"Moyasar {r.status_code}: {r.text[:200]}")
            data = r.json()
            return {
                "invoice_id": data.get("id"),
                "url": data.get("url") or data.get("checkout_url"),
                "status": data.get("status"),
                "raw": data,
            }
        except httpx.HTTPError as e:
            raise PaymentError(f"شبكة Moyasar: {e}")

    async def fetch_invoice(self, invoice_id: str) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.get(
                f"{self.API_BASE}/invoices/{invoice_id}",
                auth=(self.secret_key, ""),
            )
        if r.status_code != 200:
            raise PaymentError(f"fetch_invoice {r.status_code}: {r.text[:200]}")
        return r.json()


# ------------------------------------------------------------------
# Tabby BNPL Provider
# ------------------------------------------------------------------
class TabbyProvider:
    """Tabby — 4-installment BNPL, hosted redirect flow.

    Sandbox test card: 4005550000000001 (approved) / 4005550000000011 (declined)
    Test phone:       +966501234567
    """

    API_BASE = "https://api.tabby.ai"

    def __init__(self, public_key: str, secret_key: str):
        self.public_key = public_key
        self.secret_key = secret_key

    async def test(self):
        try:
            async with httpx.AsyncClient(timeout=12) as c:
                # Hit a lightweight endpoint — Tabby has no dedicated verify;
                # use a minimal precheck call.
                r = await c.post(
                    f"{self.API_BASE}/api/v2/checkout",
                    headers={
                        "Authorization": f"Bearer {self.public_key}",
                        "Content-Type": "application/json",
                    },
                    json={"payment": {"amount": "0.00", "currency": "SAR"}},
                )
            if r.status_code in (400, 422):
                return True, "المفتاح صالح (رفض الطلب الناقص كما هو متوقع) ✓"
            if r.status_code == 401:
                return False, "المفتاح غير صحيح (401)"
            if r.status_code in (200, 201):
                return True, "تم التحقق من Tabby ✓"
            return False, f"استجابة غير متوقعة: {r.status_code}"
        except Exception as e:
            return False, f"فشل الاتصال بـTabby: {e}"

    async def create_checkout(
        self, *, amount_sar: float, order_id: str, slug: str,
        customer: dict, items: list, callback_url: str,
    ) -> dict:
        if amount_sar <= 0:
            raise PaymentError("المبلغ يجب أن يكون أكبر من صفر")
        first, _, last = (customer.get("name") or "عميل زتكس").strip().partition(" ")
        last = last or "-"
        payload = {
            "payment": {
                "amount": f"{amount_sar:.2f}",
                "currency": "SAR",
                "description": f"طلب #{order_id[:8]}",
                "buyer": {
                    "email": (customer.get("email") or "customer@example.com"),
                    "phone": (customer.get("phone") or "+966500000000"),
                    "name": customer.get("name") or "عميل",
                },
                "shipping_address": {
                    "city": (customer.get("city") or "الرياض"),
                    "address": (customer.get("address") or "—"),
                    "zip": (customer.get("zip") or "11564"),
                },
                "order": {
                    "tax_amount": "0.00",
                    "shipping_amount": "0.00",
                    "discount_amount": "0.00",
                    "reference_id": order_id,
                    "items": [
                        {"title": i.get("name") or "منتج", "quantity": int(i.get("qty", 1)),
                         "unit_price": f"{float(i.get('price', 0)):.2f}", "category": "general"}
                        for i in items
                    ],
                },
                "buyer_history": {"registered_since": datetime.utcnow().isoformat(), "loyalty_level": 0},
                "order_history": [],
                "meta": {"order_id": order_id, "slug": slug},
            },
            "lang": "ar",
            "merchant_code": "saudi_arabia",
            "merchant_urls": {
                "success": callback_url + "&status=success",
                "failure": callback_url + "&status=failure",
                "cancel": callback_url + "&status=cancel",
            },
        }
        async with httpx.AsyncClient(timeout=30) as c:
            r = await c.post(
                f"{self.API_BASE}/api/v2/checkout",
                headers={"Authorization": f"Bearer {self.public_key}",
                         "Content-Type": "application/json"},
                json=payload,
            )
        if r.status_code not in (200, 201):
            raise PaymentError(f"Tabby {r.status_code}: {r.text[:200]}")
        data = r.json()
        cfg = (data.get("configuration") or {}).get("available_products", {})
        redirect = None
        if cfg.get("installments"):
            redirect = (cfg["installments"][0] or {}).get("web_url")
        if not redirect:
            # fallback on other product types
            for k in ("pay_later", "monthly_billing"):
                if cfg.get(k):
                    redirect = (cfg[k][0] or {}).get("web_url")
                    if redirect:
                        break
        if not redirect:
            status = data.get("status", "rejected")
            raise PaymentError(f"Tabby رفض الطلب ({status})")
        return {"checkout_id": data.get("id"), "url": redirect, "status": data.get("status")}

    async def verify(self, checkout_id: str) -> dict:
        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.get(
                f"{self.API_BASE}/api/v2/checkout/{checkout_id}",
                headers={"Authorization": f"Bearer {self.secret_key}"},
            )
        if r.status_code != 200:
            raise PaymentError(f"Tabby verify {r.status_code}: {r.text[:200]}")
        return r.json()


# ------------------------------------------------------------------
# Tamara BNPL Provider
# ------------------------------------------------------------------
class TamaraProvider:
    """Tamara — 3-installment pay-later, hosted redirect."""

    SANDBOX = "https://api-sandbox.tamara.co"
    PROD = "https://api.tamara.co"

    def __init__(self, api_token: str, notification_token: str = "", sandbox: bool = True):
        self.api_token = api_token
        self.notification_token = notification_token
        self.base = self.SANDBOX if sandbox else self.PROD

    async def test(self):
        try:
            async with httpx.AsyncClient(timeout=12) as c:
                r = await c.get(
                    f"{self.base}/merchants/me",
                    headers={"Authorization": f"Bearer {self.api_token}"},
                )
            if r.status_code in (200, 201):
                return True, "تم التحقق من Tamara ✓"
            if r.status_code == 401:
                return False, "API Token غير صحيح (401)"
            return False, f"استجابة غير متوقعة: {r.status_code}"
        except Exception as e:
            return False, f"فشل الاتصال بـTamara: {e}"

    async def create_checkout(
        self, *, amount_sar: float, order_id: str, slug: str,
        customer: dict, items: list, callback_url: str,
    ) -> dict:
        if amount_sar <= 0:
            raise PaymentError("المبلغ يجب أن يكون أكبر من صفر")
        first, _, last = (customer.get("name") or "عميل زتكس").strip().partition(" ")
        last = last or "-"
        payload = {
            "order_reference_id": order_id,
            "total_amount": {"amount": f"{amount_sar:.2f}", "currency": "SAR"},
            "shipping_amount": {"amount": "0.00", "currency": "SAR"},
            "tax_amount": {"amount": "0.00", "currency": "SAR"},
            "country_code": "SA",
            "locale": "ar_SA",
            "payment_type": "PAY_BY_INSTALMENTS",
            "instalments": 3,
            "items": [
                {
                    "reference_id": str(i.get("id") or "item"),
                    "type": "Physical",
                    "name": i.get("name") or "منتج",
                    "sku": str(i.get("id") or "sku"),
                    "quantity": int(i.get("qty", 1)),
                    "unit_price": {"amount": f"{float(i.get('price', 0)):.2f}", "currency": "SAR"},
                    "total_amount": {"amount": f"{float(i.get('price', 0)) * int(i.get('qty', 1)):.2f}", "currency": "SAR"},
                } for i in items
            ],
            "consumer": {
                "first_name": first or "عميل",
                "last_name": last,
                "phone_number": (customer.get("phone") or "+966500000000"),
                "email": (customer.get("email") or "customer@example.com"),
            },
            "shipping_address": {
                "first_name": first or "عميل",
                "last_name": last,
                "line1": (customer.get("address") or "—"),
                "city": (customer.get("city") or "الرياض"),
                "country_code": "SA",
            },
            "merchant_url": {
                "success": callback_url + "&status=success",
                "failure": callback_url + "&status=failure",
                "cancel": callback_url + "&status=cancel",
                "notification": callback_url + "&status=notification",
            },
            "description": f"طلب #{order_id[:8]}",
        }
        async with httpx.AsyncClient(timeout=30) as c:
            r = await c.post(
                f"{self.base}/checkout",
                headers={"Authorization": f"Bearer {self.api_token}",
                         "Content-Type": "application/json"},
                json=payload,
            )
        if r.status_code not in (200, 201):
            raise PaymentError(f"Tamara {r.status_code}: {r.text[:200]}")
        data = r.json()
        return {
            "order_id_tamara": data.get("order_id"),
            "checkout_id": data.get("checkout_id"),
            "url": data.get("checkout_url"),
            "status": data.get("status"),
        }

    async def verify(self, tamara_order_id: str) -> dict:
        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.get(
                f"{self.base}/orders/{tamara_order_id}",
                headers={"Authorization": f"Bearer {self.api_token}"},
            )
        if r.status_code != 200:
            raise PaymentError(f"Tamara verify {r.status_code}: {r.text[:200]}")
        return r.json()


def load_tabby(gw):
    if not gw or not gw.get("enabled"):
        return None
    pub = gw.get("public_key") or ""
    sec = decrypt(gw.get("secret_key_enc") or "")
    if not (pub and sec):
        return None
    return TabbyProvider(pub, sec)


def load_tamara(gw):
    if not gw or not gw.get("enabled"):
        return None
    tok = decrypt(gw.get("api_token_enc") or "")
    notif = decrypt(gw.get("notification_token_enc") or "")
    if not tok:
        return None
    return TamaraProvider(tok, notif, sandbox=True)


# ------------------------------------------------------------------
# Convenience: load a provider ready to call
# ------------------------------------------------------------------
def load_moyasar(gw):
    if not gw or not gw.get("enabled"):
        return None
    pub = gw.get("publishable_key") or ""
    sec = decrypt(gw.get("secret_key_enc") or "")
    if not (pub and sec):
        return None
    return MoyasarProvider(pub, sec)


# ------------------------------------------------------------------
# Save helpers — build the doc patch for a given provider update
# ------------------------------------------------------------------
def build_moyasar_patch(body: Dict[str, Any]) -> Dict[str, Any]:
    patch: Dict[str, Any] = {"enabled": bool(body.get("enabled", True))}
    if "publishable_key" in body and body["publishable_key"] is not None:
        patch["publishable_key"] = body["publishable_key"].strip()
    if "secret_key" in body and body["secret_key"]:
        patch["secret_key_enc"] = encrypt(body["secret_key"].strip())
    if "methods" in body and isinstance(body["methods"], list):
        valid = {"creditcard", "mada", "applepay", "stcpay"}
        patch["methods"] = [m for m in body["methods"] if m in valid]
    patch["test_mode"] = bool(body.get("test_mode", True))
    return patch


def build_tabby_patch(body: Dict[str, Any]) -> Dict[str, Any]:
    patch: Dict[str, Any] = {"enabled": bool(body.get("enabled", False))}
    if "public_key" in body and body["public_key"] is not None:
        patch["public_key"] = body["public_key"].strip()
    if "secret_key" in body and body["secret_key"]:
        patch["secret_key_enc"] = encrypt(body["secret_key"].strip())
    return patch


def build_tamara_patch(body: Dict[str, Any]) -> Dict[str, Any]:
    patch: Dict[str, Any] = {"enabled": bool(body.get("enabled", False))}
    if "api_token" in body and body["api_token"]:
        patch["api_token_enc"] = encrypt(body["api_token"].strip())
    if "notification_token" in body and body["notification_token"]:
        patch["notification_token_enc"] = encrypt(body["notification_token"].strip())
    return patch


def build_cod_patch(body: Dict[str, Any]) -> Dict[str, Any]:
    return {"enabled": bool(body.get("enabled", False))}


PATCH_BUILDERS = {
    "moyasar": build_moyasar_patch,
    "tabby": build_tabby_patch,
    "tamara": build_tamara_patch,
    "cod": build_cod_patch,
}
