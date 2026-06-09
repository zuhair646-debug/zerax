"""
Zerax pricing catalog — single source of truth.
Stored in DB on first boot via seeds.py, can be edited from admin panel.
All prices in USD. 1 credit = $0.001.
"""
from typing import Dict, Any, List


# ════════════════════════════════════════════════════════════════
# Service costs (what we charge the user, in CREDITS)
# Internal cost shown for transparency only — used to maintain ≥50% margin
# ════════════════════════════════════════════════════════════════
SERVICE_COSTS: Dict[str, Dict[str, Any]] = {
    "text_gpt4o_1k":        {"label": "GPT-4o (1K tokens)",       "credits": 25,   "internal_cost_usd": 0.010},
    "text_claude_1k":       {"label": "Claude Sonnet (1K tokens)","credits": 30,   "internal_cost_usd": 0.015},
    "text_gemini_flash_1k": {"label": "Gemini Flash (1K tokens)", "credits": 1,    "internal_cost_usd": 0.0003},
    "image_nano_banana":    {"label": "Nano Banana image",        "credits": 80,   "internal_cost_usd": 0.04},
    "image_gpt_standard":   {"label": "GPT Image 1 (standard)",   "credits": 100,  "internal_cost_usd": 0.04},
    "image_hd":             {"label": "Image HD",                 "credits": 320,  "internal_cost_usd": 0.16},
    "video_fal_5s":         {"label": "Fal.ai video (5s)",        "credits": 250,  "internal_cost_usd": 0.10},
    "video_sora_10s":       {"label": "Sora 2 video (10s)",       "credits": 1200, "internal_cost_usd": 0.50},
    "voice_eleven_min":     {"label": "ElevenLabs voice (1min)",  "credits": 1000, "internal_cost_usd": 0.45},
    "stt_whisper_min":      {"label": "Whisper STT (1min)",       "credits": 20,   "internal_cost_usd": 0.006},
    "chat_message":         {"label": "Standard chat message",    "credits": 10,   "internal_cost_usd": 0.004},
    "game_generation":      {"label": "Full game asset pipeline", "credits": 500,  "internal_cost_usd": 0.20},
    "website_generation":   {"label": "Website builder turn",     "credits": 50,   "internal_cost_usd": 0.020},
}


# ════════════════════════════════════════════════════════════════
# Subscription plans
# ════════════════════════════════════════════════════════════════
PLANS: List[Dict[str, Any]] = [
    {
        "id": "free",
        "name": "Free",
        "name_ar": "مجاني",
        "price_monthly_usd": 0,
        "price_yearly_usd": 0,
        "credits_per_month": 100,
        "highlight": False,
        "pay_later_eligible": False,
        "order": 1,
        "features_ar": [
            "100 شعلة شهرياً",
            "علامة مائية على المخرجات",
            "حتى مشروعين فقط",
            "نماذج AI الأساسية",
        ],
    },
    {
        "id": "starter",
        "name": "Starter",
        "name_ar": "البداية",
        "price_monthly_usd": 9,
        "price_yearly_usd": 90,
        "credits_per_month": 12000,
        "highlight": False,
        "pay_later_eligible": False,
        "order": 2,
        "features_ar": [
            "12,000 شعلة شهرياً",
            "بدون علامة مائية",
            "حتى 5 مشاريع",
            "كل نماذج AI",
            "دعم بريد إلكتروني",
        ],
    },
    {
        "id": "indie",
        "name": "Indie",
        "name_ar": "المبدع المستقل",
        "price_monthly_usd": 29,
        "price_yearly_usd": 290,
        "credits_per_month": 50000,
        "highlight": True,
        "pay_later_eligible": False,  # below $30 Pay in 4 minimum
        "order": 3,
        "features_ar": [
            "50,000 شعلة شهرياً",
            "كل المزايا + أولوية في الطابور",
            "حتى 20 مشروع",
            "Cinema Studio + Game Studio",
            "تصدير عالي الجودة",
        ],
    },
    {
        "id": "studio",
        "name": "Studio",
        "name_ar": "الاستوديو",
        "price_monthly_usd": 82,        # was $79, +$3 installment buffer
        "price_yearly_usd": 820,        # was $790
        "credits_per_month": 150000,
        "highlight": False,
        "pay_later_eligible": True,
        "order": 4,
        "features_ar": [
            "150,000 شعلة شهرياً",
            "مشاريع غير محدودة",
            "Voice Agent (LiveKit)",
            "تخزين GridFS موسّع",
            "دعم أولوية",
            "✨ متاح الدفع على 4 أقساط بدون فوائد",
        ],
    },
    {
        "id": "pro_studio",
        "name": "Pro Studio",
        "name_ar": "الاستوديو الاحترافي",
        "price_monthly_usd": 209,       # was $199, +$10 installment buffer
        "price_yearly_usd": 2090,       # was $1990
        "credits_per_month": 450000,
        "highlight": False,
        "pay_later_eligible": True,
        "order": 5,
        "features_ar": [
            "450,000 شعلة شهرياً",
            "3 مقاعد فريق (Team)",
            "وصول API كامل",
            "Webhooks + Custom integrations",
            "SLA 99.9%",
            "✨ متاح الدفع على 4 أقساط + Pay Monthly",
        ],
    },
    {
        "id": "enterprise",
        "name": "Enterprise",
        "name_ar": "المؤسسة",
        "price_monthly_usd": -1,
        "price_yearly_usd": -1,
        "credits_per_month": 0,
        "highlight": False,
        "pay_later_eligible": True,
        "order": 6,
        "features_ar": [
            "حسب الطلب — تواصل مباشرة",
            "مقاعد غير محدودة",
            "خادم مخصص + SLA مخصص",
            "تدريب فريقك",
            "دعم على مدار الساعة",
        ],
    },
]


# ════════════════════════════════════════════════════════════════
# Credit packs (pay-as-you-go top-ups)
# ════════════════════════════════════════════════════════════════
CREDIT_PACKS: List[Dict[str, Any]] = [
    {"id": "pack_mini",     "name_ar": "Mini",     "price_usd": 5,    "credits": 5000,   "bonus_pct": 0,   "order": 1, "pay_later_eligible": False},
    {"id": "pack_standard", "name_ar": "Standard", "price_usd": 20,   "credits": 22000,  "bonus_pct": 10,  "order": 2, "pay_later_eligible": False},
    {"id": "pack_power",    "name_ar": "Power",    "price_usd": 52,   "credits": 60000,  "bonus_pct": 20,  "order": 3, "popular": True, "pay_later_eligible": True},   # was $50, +$2 buffer
    {"id": "pack_mega",     "name_ar": "Mega",     "price_usd": 105,  "credits": 130000, "bonus_pct": 30,  "order": 4, "pay_later_eligible": True},                    # was $100, +$5 buffer
    {"id": "pack_ultra",    "name_ar": "Ultra",    "price_usd": 259,  "credits": 350000, "bonus_pct": 40,  "order": 5, "pay_later_eligible": True},                    # was $250, +$9 buffer
]


# ════════════════════════════════════════════════════════════════
# Launch promo codes
# ════════════════════════════════════════════════════════════════
DEFAULT_PROMOS: List[Dict[str, Any]] = [
    {
        "code": "LAUNCH50",
        "type": "percent",
        "value": 50,           # 50% off
        "max_discount_usd": 100,
        "min_order_usd": 5,
        "applies_to": "all",   # "all" | "subscription" | "pack"
        "max_uses": 1000,
        "max_uses_per_user": 1,
        "active": True,
        "label_ar": "عرض الإطلاق - 50% خصم",
    },
    {
        "code": "WELCOME25",
        "type": "percent",
        "value": 25,
        "max_discount_usd": 50,
        "min_order_usd": 5,
        "applies_to": "pack",
        "max_uses": 5000,
        "max_uses_per_user": 1,
        "active": True,
        "label_ar": "ترحيب - 25% بونص",
    },
]


# ════════════════════════════════════════════════════════════════
# Tax configuration (currently 0%, ready for future)
# ════════════════════════════════════════════════════════════════
TAX_CONFIG = {
    "enabled": True,         # Show line item on invoice
    "rate_percent": 0,       # Currently 0
    "label": "ضريبة القيمة المضافة",
    "label_en": "VAT",
    "tax_id_label_ar": "الرقم الضريبي",
    "tax_id": "",            # Empty until registered
    "country": "SA",
}


# ════════════════════════════════════════════════════════════════
# First-purchase bonus (applied automatically once per user)
# ════════════════════════════════════════════════════════════════
FIRST_PURCHASE_BONUS_PCT = 25  # +25% extra credits on first ever paid purchase


def credits_per_dollar() -> int:
    """1 USD = 1000 credits (single source of truth)."""
    return 1000


def get_plan(plan_id: str) -> Dict[str, Any]:
    for p in PLANS:
        if p["id"] == plan_id:
            return p
    raise ValueError(f"Plan {plan_id} not found")


def get_pack(pack_id: str) -> Dict[str, Any]:
    for p in CREDIT_PACKS:
        if p["id"] == pack_id:
            return p
    raise ValueError(f"Pack {pack_id} not found")
