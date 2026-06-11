"""
Zenrex Global Payment Gateways Catalog
======================================
Single source of truth for every payment gateway Zenrex supports (or plans to
support). Designed so the actual API integration can be plugged in later
without touching the frontend: each gateway is fully described — branding,
constraints, supported countries/currencies, BNPL split rules, badge design
hints — so the UI can render correct checkout buttons + installment widgets
even before the real credentials are wired.

Categories:
  - card       : credit/debit cards (Visa, Mastercard, Mada, …)
  - wallet     : digital wallets (Apple Pay, Google Pay, STC Pay, …)
  - bnpl       : Buy-Now-Pay-Later (Tabby, Tamara, Klarna, Afterpay, Affirm)
  - bank       : direct bank transfer (IBAN, SEPA, Sofort, …)
  - cod        : Cash on delivery
  - crypto     : Crypto (USDC, USDT) — flagged off by default
  - qr         : QR-based (Alipay, WeChat Pay, Mada Pay QR)

Each gateway dict keys:
  id, name_ar, name_en, provider, type, countries, currencies,
  min_amount, max_amount, fees_hint, installments (for bnpl),
  badge {bg, fg, logo_url_placeholder, slogan_ar, slogan_en},
  checkout {redirect|inline|popup, otp_required, kyc_required},
  api_docs_url, integration_status
"""

from typing import Dict, List, Any

# ─────────────────────────────────────────────────────────────────────────────
GATEWAYS: List[Dict[str, Any]] = [

    # ═════════════════════════════════════════════════════════════════════════
    # MIDDLE EAST / GULF
    # ═════════════════════════════════════════════════════════════════════════
    {
        "id": "tabby", "name_ar": "تابي", "name_en": "Tabby",
        "provider": "Tabby", "type": "bnpl",
        "countries": ["SA", "AE", "KW", "QA", "BH"],
        "currencies": ["SAR", "AED", "KWD", "QAR", "BHD"],
        "min_amount": 100, "max_amount": 25000, "fees_hint": "merchant pays ~3-6%",
        "installments": {"plans": [{"count": 4, "interval_days": 30, "interest": 0}], "default": 4},
        "badge": {"bg": "#3BFFC1", "fg": "#0A0A14", "logo": "tabby", "slogan_ar": "قسّمها على 4 دفعات بدون فوائد", "slogan_en": "Split in 4 — interest-free"},
        "checkout": {"flow": "redirect", "otp_required": True, "kyc_required": False, "mobile_first": True},
        "api_docs_url": "https://docs.tabby.ai",
        "design_notes": "Mint green CTA pill, white logo, must show '4 دفعات' chip on PDP",
        "integration_status": "scaffold",  # scaffold | sandbox | live
    },
    {
        "id": "tamara", "name_ar": "تمارا", "name_en": "Tamara",
        "provider": "Tamara", "type": "bnpl",
        "countries": ["SA", "AE", "KW"],
        "currencies": ["SAR", "AED", "KWD"],
        "min_amount": 50, "max_amount": 30000, "fees_hint": "merchant pays ~3-6%",
        "installments": {"plans": [
            {"count": 3, "interval_days": 30, "interest": 0},
            {"count": 4, "interval_days": 30, "interest": 0},
            {"count": 6, "interval_days": 30, "interest": 0},
        ], "default": 3},
        "badge": {"bg": "#FFD7DE", "fg": "#FF3366", "logo": "tamara", "slogan_ar": "ادفع لاحقاً أو قسّط على 3", "slogan_en": "Pay later or split in 3"},
        "checkout": {"flow": "redirect", "otp_required": True, "kyc_required": False, "mobile_first": True},
        "api_docs_url": "https://docs.tamara.co",
        "design_notes": "Pink/coral CTA, requires OTP via SAMA license. Show installment count selector on PDP.",
        "integration_status": "scaffold",
    },
    {
        "id": "mada", "name_ar": "مدى", "name_en": "Mada",
        "provider": "SAMA/Mada", "type": "card",
        "countries": ["SA"], "currencies": ["SAR"],
        "min_amount": 1, "max_amount": 500000, "fees_hint": "~1% per transaction",
        "badge": {"bg": "#84BD00", "fg": "#FFFFFF", "logo": "mada", "slogan_ar": "ادفع ببطاقة مدى", "slogan_en": "Pay with Mada"},
        "checkout": {"flow": "inline", "otp_required": True, "kyc_required": False, "mobile_first": True},
        "api_docs_url": "https://www.mada.com.sa",
        "design_notes": "Green/black Mada badge. Mandatory in Saudi e-commerce.",
        "integration_status": "scaffold",
    },
    {
        "id": "stc_pay_checkout", "name_ar": "STC Pay", "name_en": "STC Pay",
        "provider": "STC Pay", "type": "wallet",
        "countries": ["SA", "BH"], "currencies": ["SAR", "BHD"],
        "min_amount": 1, "max_amount": 20000, "fees_hint": "~1.5%",
        "badge": {"bg": "#4F008C", "fg": "#FFFFFF", "logo": "stc_pay", "slogan_ar": "ادفع بـ STC Pay", "slogan_en": "Pay with STC Pay"},
        "checkout": {"flow": "redirect", "otp_required": True, "kyc_required": False, "mobile_first": True},
        "integration_status": "scaffold",
    },
    {
        "id": "apple_pay", "name_ar": "Apple Pay", "name_en": "Apple Pay",
        "provider": "Apple", "type": "wallet",
        "countries": ["*"], "currencies": ["*"],
        "min_amount": 1, "max_amount": 1000000, "fees_hint": "PSP fee only",
        "badge": {"bg": "#000000", "fg": "#FFFFFF", "logo": "apple_pay", "slogan_ar": "ادفع بـ Apple Pay", "slogan_en": "Pay with Apple Pay"},
        "checkout": {"flow": "inline", "otp_required": False, "kyc_required": False, "mobile_first": True},
        "integration_status": "scaffold",
    },
    {
        "id": "google_pay", "name_ar": "Google Pay", "name_en": "Google Pay",
        "provider": "Google", "type": "wallet",
        "countries": ["*"], "currencies": ["*"],
        "min_amount": 1, "max_amount": 1000000, "fees_hint": "PSP fee only",
        "badge": {"bg": "#FFFFFF", "fg": "#202124", "logo": "google_pay", "slogan_ar": "Google Pay", "slogan_en": "G Pay"},
        "checkout": {"flow": "inline", "otp_required": False, "kyc_required": False, "mobile_first": True},
        "integration_status": "scaffold",
    },
    {
        "id": "urpay", "name_ar": "urpay", "name_en": "urpay",
        "provider": "urpay", "type": "wallet",
        "countries": ["SA"], "currencies": ["SAR"],
        "min_amount": 1, "max_amount": 50000, "fees_hint": "~1.5%",
        "badge": {"bg": "#FF6B00", "fg": "#FFFFFF", "logo": "urpay", "slogan_ar": "ادفع بـ urpay", "slogan_en": "Pay with urpay"},
        "checkout": {"flow": "redirect", "otp_required": True, "kyc_required": False, "mobile_first": True},
        "integration_status": "scaffold",
    },
    {
        "id": "spotii", "name_ar": "سبوتي", "name_en": "Spotii",
        "provider": "Spotii (Zip)", "type": "bnpl",
        "countries": ["SA", "AE"], "currencies": ["SAR", "AED"],
        "min_amount": 50, "max_amount": 10000, "fees_hint": "~4%",
        "installments": {"plans": [{"count": 4, "interval_days": 14, "interest": 0}], "default": 4},
        "badge": {"bg": "#000000", "fg": "#FFC700", "logo": "spotii", "slogan_ar": "4 دفعات كل أسبوعين", "slogan_en": "4 payments biweekly"},
        "checkout": {"flow": "redirect", "otp_required": True, "kyc_required": False, "mobile_first": True},
        "integration_status": "scaffold",
    },

    # ═════════════════════════════════════════════════════════════════════════
    # EGYPT
    # ═════════════════════════════════════════════════════════════════════════
    {
        "id": "fawry", "name_ar": "فوري", "name_en": "Fawry",
        "provider": "Fawry", "type": "wallet",
        "countries": ["EG"], "currencies": ["EGP"],
        "min_amount": 10, "max_amount": 100000, "fees_hint": "~2%",
        "badge": {"bg": "#FFC107", "fg": "#000000", "logo": "fawry", "slogan_ar": "ادفع بـ فوري", "slogan_en": "Pay with Fawry"},
        "checkout": {"flow": "redirect", "otp_required": True, "kyc_required": False, "mobile_first": True},
        "integration_status": "scaffold",
    },
    {
        "id": "instapay_eg", "name_ar": "InstaPay مصر", "name_en": "InstaPay Egypt",
        "provider": "Central Bank of Egypt", "type": "bank",
        "countries": ["EG"], "currencies": ["EGP"],
        "min_amount": 1, "max_amount": 70000, "fees_hint": "free for individuals",
        "badge": {"bg": "#0066CC", "fg": "#FFFFFF", "logo": "instapay", "slogan_ar": "تحويل فوري مجاني", "slogan_en": "Instant free transfer"},
        "checkout": {"flow": "redirect", "otp_required": True, "kyc_required": False, "mobile_first": True},
        "integration_status": "scaffold",
    },
    {
        "id": "valu", "name_ar": "valU", "name_en": "valU",
        "provider": "EFG Hermes", "type": "bnpl",
        "countries": ["EG"], "currencies": ["EGP"],
        "min_amount": 500, "max_amount": 500000, "fees_hint": "merchant subsidized",
        "installments": {"plans": [{"count": n, "interval_days": 30, "interest": 0} for n in [6, 12, 18, 24, 36, 60]], "default": 12},
        "badge": {"bg": "#FF3D00", "fg": "#FFFFFF", "logo": "valu", "slogan_ar": "قسّط على 60 شهر", "slogan_en": "Up to 60 months"},
        "checkout": {"flow": "redirect", "otp_required": True, "kyc_required": True, "mobile_first": True},
        "integration_status": "scaffold",
    },

    # ═════════════════════════════════════════════════════════════════════════
    # USA / CANADA
    # ═════════════════════════════════════════════════════════════════════════
    {
        "id": "klarna", "name_ar": "كلارنا", "name_en": "Klarna",
        "provider": "Klarna", "type": "bnpl",
        "countries": ["US", "CA", "GB", "DE", "FR", "ES", "IT", "NL", "SE", "AU"],
        "currencies": ["USD", "CAD", "GBP", "EUR", "SEK", "AUD"],
        "min_amount": 35, "max_amount": 10000, "fees_hint": "merchant pays 3-6% + $0.30",
        "installments": {"plans": [
            {"count": 4, "interval_days": 14, "interest": 0, "label": "Pay in 4"},
            {"count": 1, "interval_days": 30, "interest": 0, "label": "Pay in 30 days"},
            {"count": 6, "interval_days": 30, "interest": 0, "label": "6-month financing"},
            {"count": 12, "interval_days": 30, "interest": 9.99, "label": "12-month financing"},
        ], "default": 4},
        "badge": {"bg": "#FFA8CD", "fg": "#0E0E0E", "logo": "klarna", "slogan_ar": "ادفع لاحقاً بـ Klarna", "slogan_en": "Pay in 4 with Klarna"},
        "checkout": {"flow": "redirect", "otp_required": False, "kyc_required": False, "mobile_first": True},
        "design_notes": "Pink badge with K. Mandatory on-site messaging widget on PDP for amounts ≥$35.",
        "integration_status": "scaffold",
    },
    {
        "id": "afterpay", "name_ar": "أفتربي", "name_en": "Afterpay",
        "provider": "Block (Square)", "type": "bnpl",
        "countries": ["US", "CA", "GB", "AU", "NZ"],
        "currencies": ["USD", "CAD", "GBP", "AUD", "NZD"],
        "min_amount": 35, "max_amount": 2000, "fees_hint": "merchant 4-6%",
        "installments": {"plans": [{"count": 4, "interval_days": 14, "interest": 0}], "default": 4},
        "badge": {"bg": "#B2FCE4", "fg": "#000000", "logo": "afterpay", "slogan_ar": "4 دفعات بدون فوائد", "slogan_en": "4 interest-free payments"},
        "checkout": {"flow": "redirect", "otp_required": False, "kyc_required": False, "mobile_first": True},
        "design_notes": "Mint green pill with curved A. UK brand is Clearpay (same provider).",
        "integration_status": "scaffold",
    },
    {
        "id": "affirm", "name_ar": "أفيرم", "name_en": "Affirm",
        "provider": "Affirm", "type": "bnpl",
        "countries": ["US", "CA"], "currencies": ["USD", "CAD"],
        "min_amount": 50, "max_amount": 17500, "fees_hint": "merchant 5.99% APR borne by customer for long terms",
        "installments": {"plans": [
            {"count": 4, "interval_days": 14, "interest": 0, "label": "Pay in 4"},
            {"count": 3, "interval_days": 30, "interest": 0, "label": "3 months"},
            {"count": 6, "interval_days": 30, "interest": 10, "label": "6 months"},
            {"count": 12, "interval_days": 30, "interest": 15, "label": "12 months"},
        ], "default": 4},
        "badge": {"bg": "#0FA0EA", "fg": "#FFFFFF", "logo": "affirm", "slogan_ar": "أقساط شهرية مع Affirm", "slogan_en": "Monthly payments with Affirm"},
        "checkout": {"flow": "redirect", "otp_required": True, "kyc_required": True, "mobile_first": True},
        "design_notes": "Cyan blue badge. Soft credit check; APR disclosure required.",
        "integration_status": "scaffold",
    },
    {
        "id": "paypal", "name_ar": "PayPal", "name_en": "PayPal",
        "provider": "PayPal", "type": "wallet",
        "countries": ["US", "CA", "GB", "DE", "FR", "ES", "IT", "AU", "JP"],
        "currencies": ["USD", "EUR", "GBP", "CAD", "AUD", "JPY"],
        "min_amount": 1, "max_amount": 60000, "fees_hint": "3.49% + $0.49",
        "badge": {"bg": "#FFC439", "fg": "#003087", "logo": "paypal", "slogan_ar": "ادفع بـ PayPal", "slogan_en": "Pay with PayPal"},
        "checkout": {"flow": "popup", "otp_required": False, "kyc_required": False, "mobile_first": True},
        "integration_status": "scaffold",
    },
    {
        "id": "stripe_card", "name_ar": "بطاقة (Stripe)", "name_en": "Card via Stripe",
        "provider": "Stripe", "type": "card",
        "countries": ["*"], "currencies": ["*"],
        "min_amount": 1, "max_amount": 1000000, "fees_hint": "2.9% + $0.30",
        "badge": {"bg": "#635BFF", "fg": "#FFFFFF", "logo": "stripe", "slogan_ar": "ادفع ببطاقتك", "slogan_en": "Pay by card"},
        "checkout": {"flow": "inline", "otp_required": True, "kyc_required": False, "mobile_first": True},
        "integration_status": "scaffold",
    },

    # ═════════════════════════════════════════════════════════════════════════
    # CHINA
    # ═════════════════════════════════════════════════════════════════════════
    {
        "id": "alipay", "name_ar": "Alipay", "name_en": "Alipay",
        "provider": "Ant Group", "type": "qr",
        "countries": ["CN", "*"], "currencies": ["CNY", "USD", "HKD"],
        "min_amount": 1, "max_amount": 1000000, "fees_hint": "1.2% cross-border",
        "badge": {"bg": "#1677FF", "fg": "#FFFFFF", "logo": "alipay", "slogan_ar": "ادفع بـ Alipay", "slogan_en": "Pay with Alipay"},
        "checkout": {"flow": "qr", "otp_required": False, "kyc_required": False, "mobile_first": True},
        "design_notes": "Cross-border requires licensed PSP. QR code scan flow.",
        "integration_status": "scaffold",
    },
    {
        "id": "wechat_pay", "name_ar": "WeChat Pay", "name_en": "WeChat Pay",
        "provider": "Tencent", "type": "qr",
        "countries": ["CN", "*"], "currencies": ["CNY", "USD", "HKD"],
        "min_amount": 1, "max_amount": 500000, "fees_hint": "1.2% cross-border",
        "badge": {"bg": "#07C160", "fg": "#FFFFFF", "logo": "wechat_pay", "slogan_ar": "WeChat Pay", "slogan_en": "WeChat Pay"},
        "checkout": {"flow": "qr", "otp_required": False, "kyc_required": False, "mobile_first": True},
        "integration_status": "scaffold",
    },
    {
        "id": "unionpay", "name_ar": "UnionPay", "name_en": "UnionPay",
        "provider": "China UnionPay", "type": "card",
        "countries": ["CN", "*"], "currencies": ["CNY", "USD"],
        "min_amount": 1, "max_amount": 1000000, "fees_hint": "~1.4%",
        "badge": {"bg": "#E21A23", "fg": "#FFFFFF", "logo": "unionpay", "slogan_ar": "UnionPay", "slogan_en": "UnionPay"},
        "checkout": {"flow": "inline", "otp_required": True, "kyc_required": False, "mobile_first": True},
        "integration_status": "scaffold",
    },

    # ═════════════════════════════════════════════════════════════════════════
    # EUROPE / UK
    # ═════════════════════════════════════════════════════════════════════════
    {
        "id": "clearpay", "name_ar": "Clearpay", "name_en": "Clearpay",
        "provider": "Block", "type": "bnpl",
        "countries": ["GB", "FR", "ES", "IT"],
        "currencies": ["GBP", "EUR"],
        "min_amount": 50, "max_amount": 1500, "fees_hint": "merchant 4-6%",
        "installments": {"plans": [{"count": 4, "interval_days": 14, "interest": 0}], "default": 4},
        "badge": {"bg": "#B2FCE4", "fg": "#000000", "logo": "clearpay", "slogan_ar": "4 دفعات", "slogan_en": "4 payments"},
        "checkout": {"flow": "redirect", "otp_required": False, "kyc_required": False, "mobile_first": True},
        "integration_status": "scaffold",
    },
    {
        "id": "sepa", "name_ar": "SEPA", "name_en": "SEPA Direct Debit",
        "provider": "EU", "type": "bank",
        "countries": ["DE", "FR", "ES", "IT", "NL", "BE", "AT"],
        "currencies": ["EUR"],
        "min_amount": 1, "max_amount": 1000000, "fees_hint": "0.25-1%",
        "badge": {"bg": "#003399", "fg": "#FFCC00", "logo": "sepa", "slogan_ar": "تحويل بنكي SEPA", "slogan_en": "SEPA Direct Debit"},
        "checkout": {"flow": "inline", "otp_required": True, "kyc_required": True, "mobile_first": False},
        "integration_status": "scaffold",
    },
    {
        "id": "sofort", "name_ar": "Sofort", "name_en": "Sofort",
        "provider": "Klarna", "type": "bank",
        "countries": ["DE", "AT", "CH", "BE", "NL"],
        "currencies": ["EUR", "CHF"],
        "min_amount": 1, "max_amount": 100000, "fees_hint": "0.9-2%",
        "badge": {"bg": "#F18FBA", "fg": "#FFFFFF", "logo": "sofort", "slogan_ar": "تحويل بنكي فوري", "slogan_en": "Instant bank transfer"},
        "checkout": {"flow": "redirect", "otp_required": True, "kyc_required": False, "mobile_first": True},
        "integration_status": "scaffold",
    },
    {
        "id": "ideal", "name_ar": "iDEAL", "name_en": "iDEAL",
        "provider": "Dutch Banks", "type": "bank",
        "countries": ["NL"], "currencies": ["EUR"],
        "min_amount": 1, "max_amount": 50000, "fees_hint": "~€0.29 per tx",
        "badge": {"bg": "#CC0066", "fg": "#FFFFFF", "logo": "ideal", "slogan_ar": "iDEAL", "slogan_en": "iDEAL"},
        "checkout": {"flow": "redirect", "otp_required": True, "kyc_required": False, "mobile_first": True},
        "integration_status": "scaffold",
    },

    # ═════════════════════════════════════════════════════════════════════════
    # SOUTHEAST ASIA / INDIA
    # ═════════════════════════════════════════════════════════════════════════
    {
        "id": "upi", "name_ar": "UPI", "name_en": "UPI (India)",
        "provider": "NPCI", "type": "qr",
        "countries": ["IN"], "currencies": ["INR"],
        "min_amount": 1, "max_amount": 100000, "fees_hint": "free under ₹2000",
        "badge": {"bg": "#072654", "fg": "#FFFFFF", "logo": "upi", "slogan_ar": "UPI", "slogan_en": "UPI"},
        "checkout": {"flow": "qr", "otp_required": True, "kyc_required": False, "mobile_first": True},
        "integration_status": "scaffold",
    },
    {
        "id": "grabpay", "name_ar": "GrabPay", "name_en": "GrabPay",
        "provider": "Grab", "type": "wallet",
        "countries": ["SG", "MY", "TH", "PH", "VN", "ID"],
        "currencies": ["SGD", "MYR", "THB", "PHP", "VND", "IDR"],
        "min_amount": 1, "max_amount": 10000, "fees_hint": "~1.5%",
        "badge": {"bg": "#00B14F", "fg": "#FFFFFF", "logo": "grabpay", "slogan_ar": "GrabPay", "slogan_en": "GrabPay"},
        "checkout": {"flow": "redirect", "otp_required": True, "kyc_required": False, "mobile_first": True},
        "integration_status": "scaffold",
    },

    # ═════════════════════════════════════════════════════════════════════════
    # UNIVERSAL FALLBACKS
    # ═════════════════════════════════════════════════════════════════════════
    {
        "id": "cod", "name_ar": "الدفع عند الاستلام", "name_en": "Cash on Delivery",
        "provider": "—", "type": "cod",
        "countries": ["*"], "currencies": ["*"],
        "min_amount": 1, "max_amount": 5000, "fees_hint": "no fees",
        "badge": {"bg": "#10B981", "fg": "#FFFFFF", "logo": "cod", "slogan_ar": "ادفع كاش عند الاستلام", "slogan_en": "Pay cash on delivery"},
        "checkout": {"flow": "inline", "otp_required": False, "kyc_required": False, "mobile_first": True},
        "integration_status": "live",  # always available
    },
    {
        "id": "bank_transfer", "name_ar": "تحويل بنكي", "name_en": "Bank Transfer",
        "provider": "—", "type": "bank",
        "countries": ["*"], "currencies": ["*"],
        "min_amount": 1, "max_amount": 10000000, "fees_hint": "varies",
        "badge": {"bg": "#0F172A", "fg": "#FFFFFF", "logo": "bank", "slogan_ar": "تحويل بنكي مباشر", "slogan_en": "Direct bank transfer"},
        "checkout": {"flow": "manual", "otp_required": False, "kyc_required": False, "mobile_first": False},
        "integration_status": "live",
    },
    {
        "id": "crypto_usdc", "name_ar": "USDC", "name_en": "USDC (Crypto)",
        "provider": "Coinbase Commerce", "type": "crypto",
        "countries": ["*"], "currencies": ["USDC", "USD"],
        "min_amount": 1, "max_amount": 1000000, "fees_hint": "~1% network fee",
        "badge": {"bg": "#2775CA", "fg": "#FFFFFF", "logo": "usdc", "slogan_ar": "ادفع بـ USDC", "slogan_en": "Pay with USDC"},
        "checkout": {"flow": "qr", "otp_required": False, "kyc_required": False, "mobile_first": True},
        "integration_status": "scaffold",
    },
]


# ─────────────────────────────────────────────────────────────────────────────
# Country → recommended default gateway set
# ─────────────────────────────────────────────────────────────────────────────
COUNTRY_PROFILES: Dict[str, Dict[str, Any]] = {
    "SA": {
        "name_ar": "السعودية", "currency": "SAR", "vat_pct": 15,
        "invoice_standard": "ZATCA Phase 2 (XML + PDF/A-3 + QR)",
        "shipping_partners": ["SMSA", "أرامكس", "DHL", "Naqel", "AJEX"],
        "recommended_gateways": ["mada", "tabby", "tamara", "stc_pay_checkout", "apple_pay", "urpay", "cod", "bank_transfer"],
        "regulator": "SAMA (البنك المركزي السعودي)",
    },
    "AE": {
        "name_ar": "الإمارات", "currency": "AED", "vat_pct": 5,
        "invoice_standard": "FTA e-invoicing",
        "shipping_partners": ["Aramex", "Emirates Post", "DHL", "Fetchr"],
        "recommended_gateways": ["tabby", "tamara", "spotii", "apple_pay", "google_pay", "stripe_card", "cod"],
        "regulator": "CBUAE",
    },
    "EG": {
        "name_ar": "مصر", "currency": "EGP", "vat_pct": 14,
        "invoice_standard": "ETA e-Invoice (مصلحة الضرائب)",
        "shipping_partners": ["Aramex", "Bosta", "R2S", "Fawry Logistics"],
        "recommended_gateways": ["fawry", "instapay_eg", "valu", "stripe_card", "cod", "bank_transfer"],
        "regulator": "CBE",
    },
    "KW": {"name_ar": "الكويت", "currency": "KWD", "vat_pct": 0, "invoice_standard": "Standard tax invoice",
           "shipping_partners": ["Aramex", "Q'go", "DHL"], "recommended_gateways": ["tabby", "tamara", "stripe_card", "cod"], "regulator": "CBK"},
    "BH": {"name_ar": "البحرين", "currency": "BHD", "vat_pct": 10, "invoice_standard": "NBR e-invoice",
           "shipping_partners": ["Aramex", "DHL"], "recommended_gateways": ["tabby", "stc_pay_checkout", "stripe_card", "cod"], "regulator": "CBB"},
    "QA": {"name_ar": "قطر", "currency": "QAR", "vat_pct": 0, "invoice_standard": "Tax invoice",
           "shipping_partners": ["Qatar Post", "Aramex", "DHL"], "recommended_gateways": ["tabby", "stripe_card", "cod"], "regulator": "QCB"},
    "US": {
        "name_ar": "الولايات المتحدة", "currency": "USD", "vat_pct": 0, "invoice_standard": "State sales tax invoice",
        "shipping_partners": ["UPS", "FedEx", "USPS", "DHL"],
        "recommended_gateways": ["stripe_card", "klarna", "afterpay", "affirm", "paypal", "apple_pay", "google_pay"],
        "regulator": "FTC + State regulators",
    },
    "GB": {
        "name_ar": "بريطانيا", "currency": "GBP", "vat_pct": 20, "invoice_standard": "HMRC VAT invoice",
        "shipping_partners": ["Royal Mail", "DPD", "Hermes", "DHL"],
        "recommended_gateways": ["stripe_card", "klarna", "clearpay", "paypal", "apple_pay", "google_pay"],
        "regulator": "FCA",
    },
    "DE": {"name_ar": "ألمانيا", "currency": "EUR", "vat_pct": 19, "invoice_standard": "ZUGFeRD/XRechnung",
           "shipping_partners": ["DHL", "Hermes", "DPD"], "recommended_gateways": ["stripe_card", "klarna", "sepa", "sofort", "paypal"], "regulator": "BaFin"},
    "FR": {"name_ar": "فرنسا", "currency": "EUR", "vat_pct": 20, "invoice_standard": "Factur-X",
           "shipping_partners": ["La Poste", "Chronopost", "DHL"], "recommended_gateways": ["stripe_card", "klarna", "sepa", "paypal"], "regulator": "ACPR"},
    "NL": {"name_ar": "هولندا", "currency": "EUR", "vat_pct": 21, "invoice_standard": "EU e-invoice",
           "shipping_partners": ["PostNL", "DHL"], "recommended_gateways": ["ideal", "stripe_card", "klarna", "paypal", "sepa"], "regulator": "DNB"},
    "CN": {
        "name_ar": "الصين", "currency": "CNY", "vat_pct": 13, "invoice_standard": "Fapiao (发票)",
        "shipping_partners": ["SF Express", "China Post", "JD Logistics", "Cainiao"],
        "recommended_gateways": ["alipay", "wechat_pay", "unionpay"],
        "regulator": "PBOC + SAFE",
    },
    "IN": {"name_ar": "الهند", "currency": "INR", "vat_pct": 18, "invoice_standard": "GST e-invoice (IRN+QR)",
           "shipping_partners": ["Delhivery", "Blue Dart", "DTDC", "India Post"],
           "recommended_gateways": ["upi", "stripe_card", "paypal", "cod"], "regulator": "RBI"},
    "SG": {"name_ar": "سنغافورة", "currency": "SGD", "vat_pct": 9, "invoice_standard": "InvoiceNow (Peppol)",
           "shipping_partners": ["SingPost", "Ninja Van", "DHL"], "recommended_gateways": ["grabpay", "stripe_card", "paypal", "apple_pay"], "regulator": "MAS"},
}


def gateways_for_country(country_code: str) -> List[Dict[str, Any]]:
    """Return all gateways available in a country (matching `*` wildcard too)."""
    cc = country_code.upper()
    return [g for g in GATEWAYS if cc in g["countries"] or "*" in g["countries"]]


def gateway_by_id(gid: str) -> Dict[str, Any]:
    return next((g for g in GATEWAYS if g["id"] == gid), None)


def country_profile(country_code: str) -> Dict[str, Any]:
    return COUNTRY_PROFILES.get(country_code.upper())
