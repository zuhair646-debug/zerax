"""
Zitex Shipping Module
─────────────────────
نظام شحن متكامل للمتاجر السعودية مع 6 شركات شحن محلية + خيارات دولية.

الفلسفة:
- توصيل داخلي (نفس المدينة): يستخدم delivery_settings الموجود (Haversine + سائقين)
- توصيل سعودي (مدن أخرى): شركات الشحن السعودية مع أسعار حسب المنطقة والوزن
- شحن دولي (خارج السعودية): Aramex/DHL مع أسعار مرجعية

Geolocation:
- المرحلة 1: قراءة IP + لغة المتصفح (في checkout)
- المرحلة 2: استخدام HTML5 Geolocation API لو وافق العميل
- لو فشل: يطلب من العميل تحديد المدينة يدوياً
"""
from typing import Dict, List, Any, Optional, Tuple

# ════════════════════════════════════════════════════════════════════════
# 6 شركات شحن سعودية رئيسية + أسعار افتراضية
# ════════════════════════════════════════════════════════════════════════
SHIPPING_PROVIDERS: List[Dict[str, Any]] = [
    {
        "id": "smsa",
        "name_ar": "سمسا إكسبرس",
        "name_en": "SMSA Express",
        "logo": "https://upload.wikimedia.org/wikipedia/en/thumb/1/1f/SMSA_Express_Logo.svg/180px-SMSA_Express_Logo.svg.png",
        "icon": "📦",
        "color": "#E30613",
        "coverage": ["SA"],  # ISO country codes covered
        "service_types": ["domestic", "express"],
        "default_rates": {
            "base_fee": 25,            # SAR — cost up to 5kg
            "extra_kg_fee": 5,          # SAR per kg above 5
            "delivery_days_min": 1,
            "delivery_days_max": 3,
        },
        "tracking_url_template": "https://www.smsaexpress.com/sa/en/trackingdetails?tracknumbers={tracking}",
        "supports_cod": True,           # cash on delivery
        "supports_returns": True,
    },
    {
        "id": "aramex",
        "name_ar": "أرامكس",
        "name_en": "Aramex",
        "logo": "https://upload.wikimedia.org/wikipedia/commons/thumb/6/6f/Aramex_logo.svg/180px-Aramex_logo.svg.png",
        "icon": "✈️",
        "color": "#E60000",
        "coverage": ["SA", "AE", "KW", "BH", "OM", "QA", "EG", "JO", "INTL"],
        "service_types": ["domestic", "international", "express"],
        "default_rates": {
            "base_fee": 30,
            "extra_kg_fee": 7,
            "delivery_days_min": 1,
            "delivery_days_max": 4,
            "international_base_fee": 90,
            "international_extra_kg_fee": 25,
            "international_delivery_days_min": 5,
            "international_delivery_days_max": 10,
        },
        "tracking_url_template": "https://www.aramex.com/track/results?ShipmentNumber={tracking}",
        "supports_cod": True,
        "supports_returns": True,
    },
    {
        "id": "saudi_post",
        "name_ar": "سُبل (البريد السعودي)",
        "name_en": "Saudi Post (SPL)",
        "logo": "https://splonline.com.sa/wp-content/uploads/2021/02/SPL-Logo.png",
        "icon": "📮",
        "color": "#005C2E",
        "coverage": ["SA"],
        "service_types": ["domestic", "economy"],
        "default_rates": {
            "base_fee": 15,             # cheapest option
            "extra_kg_fee": 3,
            "delivery_days_min": 2,
            "delivery_days_max": 5,
        },
        "tracking_url_template": "https://splonline.com.sa/en/individuals/track-and-trace/?awb={tracking}",
        "supports_cod": False,
        "supports_returns": False,
    },
    {
        "id": "naqel",
        "name_ar": "ناقل إكسبرس",
        "name_en": "Naqel Express",
        "logo": "https://www.naqelexpress.com/wp-content/uploads/2020/10/logo-1.png",
        "icon": "🚚",
        "color": "#003D7A",
        "coverage": ["SA"],
        "service_types": ["domestic", "express"],
        "default_rates": {
            "base_fee": 28,
            "extra_kg_fee": 6,
            "delivery_days_min": 1,
            "delivery_days_max": 3,
        },
        "tracking_url_template": "https://www.naqelexpress.com/track/?awb={tracking}",
        "supports_cod": True,
        "supports_returns": True,
    },
    {
        "id": "ajex",
        "name_ar": "أجكس",
        "name_en": "AJEX",
        "logo": "https://ajex.com/Style%20Library/AJEXNewBranding/images/ajex-logo.svg",
        "icon": "⚡",
        "color": "#1A2E4A",
        "coverage": ["SA", "AE", "BH", "KW", "OM", "QA", "INTL"],
        "service_types": ["domestic", "international", "express"],
        "default_rates": {
            "base_fee": 32,
            "extra_kg_fee": 8,
            "delivery_days_min": 1,
            "delivery_days_max": 2,
            "international_base_fee": 110,
            "international_extra_kg_fee": 30,
            "international_delivery_days_min": 3,
            "international_delivery_days_max": 7,
        },
        "tracking_url_template": "https://ajex.com/en/track-shipment?awb={tracking}",
        "supports_cod": True,
        "supports_returns": True,
    },
    {
        "id": "dhl",
        "name_ar": "دي إتش إل",
        "name_en": "DHL Express",
        "logo": "https://upload.wikimedia.org/wikipedia/commons/thumb/2/27/DHL_Logo.svg/200px-DHL_Logo.svg.png",
        "icon": "🌍",
        "color": "#FFCC00",
        "coverage": ["SA", "INTL"],
        "service_types": ["international", "express"],
        "default_rates": {
            "base_fee": 50,
            "extra_kg_fee": 12,
            "delivery_days_min": 1,
            "delivery_days_max": 2,
            "international_base_fee": 150,
            "international_extra_kg_fee": 40,
            "international_delivery_days_min": 2,
            "international_delivery_days_max": 5,
        },
        "tracking_url_template": "https://www.dhl.com/sa-en/home/tracking.html?tracking-id={tracking}",
        "supports_cod": False,
        "supports_returns": True,
    },
]

PROVIDER_BY_ID = {p["id"]: p for p in SHIPPING_PROVIDERS}


# ════════════════════════════════════════════════════════════════════════
# المناطق السعودية (للتسعير الذكي)
# ════════════════════════════════════════════════════════════════════════
SAUDI_REGIONS: Dict[str, Dict[str, Any]] = {
    "central":  {"name_ar": "المنطقة الوسطى", "cities": ["الرياض", "بريدة", "الخرج", "الزلفي", "حوطة سدير"], "multiplier": 1.0},
    "western":  {"name_ar": "المنطقة الغربية", "cities": ["جدة", "مكة", "المدينة", "الطائف", "ينبع", "رابغ"], "multiplier": 1.0},
    "eastern":  {"name_ar": "المنطقة الشرقية", "cities": ["الدمام", "الخبر", "الظهران", "القطيف", "الجبيل", "الأحساء"], "multiplier": 1.1},
    "southern": {"name_ar": "المنطقة الجنوبية", "cities": ["أبها", "خميس مشيط", "نجران", "جازان", "الباحة"], "multiplier": 1.25},
    "northern": {"name_ar": "المنطقة الشمالية", "cities": ["تبوك", "حائل", "عرعر", "سكاكا", "رفحاء"], "multiplier": 1.2},
}


def get_region_for_city(city: str) -> Optional[str]:
    """Identify region by city name (Arabic)."""
    if not city:
        return None
    city_norm = city.strip()
    for region_id, info in SAUDI_REGIONS.items():
        for c in info["cities"]:
            if c in city_norm or city_norm in c:
                return region_id
    return None


# ════════════════════════════════════════════════════════════════════════
# Quote Engine — يحسب خيارات الشحن المتاحة
# ════════════════════════════════════════════════════════════════════════
def calculate_shipping_quote(
    *,
    project_settings: Dict[str, Any],
    customer_country: str,
    customer_city: Optional[str] = None,
    weight_kg: float = 1.0,
    cart_subtotal: float = 0.0,
) -> List[Dict[str, Any]]:
    """
    يُرجع قائمة بكل خيارات الشحن المتاحة للعميل، مرتّبة حسب السعر.
    
    project_settings: store's shipping config (which providers enabled, custom rates)
    customer_country: ISO country code, e.g. "SA", "AE", "US"
    customer_city: e.g. "جدة" (لتحديد إذا كان داخل/خارج المدينة)
    weight_kg: total cart weight
    cart_subtotal: للـfree-shipping logic
    """
    enabled_providers = project_settings.get("enabled_providers") or [p["id"] for p in SHIPPING_PROVIDERS]
    custom_rates = project_settings.get("custom_rates") or {}
    store_city = (project_settings.get("store_city") or "").strip()
    free_shipping_above = float(project_settings.get("free_shipping_above_sar") or 0)
    local_delivery_enabled = bool(project_settings.get("local_delivery_enabled"))
    local_delivery_fee = float(project_settings.get("local_delivery_fee") or 15)
    local_delivery_eta = project_settings.get("local_delivery_eta_hours") or "2-4"
    
    options: List[Dict[str, Any]] = []
    customer_country = (customer_country or "SA").upper()
    is_sa = customer_country == "SA"
    is_same_city = is_sa and store_city and customer_city and store_city.strip() in customer_city.strip()
    
    # ──────────────────────────────────────────────────────────────────
    # 0️⃣ الاستلام من المتجر (Pickup) — مجاني، أسرع خيار
    # ──────────────────────────────────────────────────────────────────
    pickup_enabled = bool(project_settings.get("pickup_enabled"))
    if pickup_enabled:
        pickup_addr = (project_settings.get("pickup_address") or "").strip()
        pickup_hours = (project_settings.get("pickup_hours") or "").strip()
        eta_text = pickup_hours if pickup_hours else "جاهز خلال ساعة"
        options.append({
            "provider_id": "pickup",
            "provider_name": "الاستلام من المتجر",
            "icon": "🏬",
            "logo": None,
            "fee_sar": 0.0,
            "delivery_eta": eta_text,
            "delivery_days_min": 0,
            "delivery_days_max": 0,
            "service_type": "pickup",
            "supports_cod": True,
            "is_recommended": False,
            "is_free": True,
            "pickup_address": pickup_addr,
        })
    
    # ──────────────────────────────────────────────────────────────────
    # 1️⃣ توصيل داخلي (نفس المدينة) — لو مفعّل في إعدادات المتجر
    # ──────────────────────────────────────────────────────────────────
    if is_same_city and local_delivery_enabled:
        fee = 0.0 if (free_shipping_above and cart_subtotal >= free_shipping_above) else local_delivery_fee
        options.append({
            "provider_id": "local_delivery",
            "provider_name": f"توصيل {store_city} (داخلي)",
            "icon": "🛵",
            "logo": None,
            "fee_sar": round(fee, 2),
            "delivery_eta": f"{local_delivery_eta} ساعة",
            "delivery_days_min": 0,
            "delivery_days_max": 1,
            "service_type": "local",
            "supports_cod": True,
            "is_recommended": True,  # cheapest + fastest
            "is_free": fee == 0,
        })
    
    # ──────────────────────────────────────────────────────────────────
    # 2️⃣ شركات الشحن (سعودية أو دولية)
    # ──────────────────────────────────────────────────────────────────
    region_mult = 1.0
    if is_sa and customer_city:
        region = get_region_for_city(customer_city)
        if region:
            region_mult = SAUDI_REGIONS[region].get("multiplier", 1.0)
    
    for provider in SHIPPING_PROVIDERS:
        pid = provider["id"]
        if pid not in enabled_providers:
            continue
        # لو العميل سعودي والشركة ما تغطي السعودية، تخطى
        if is_sa and "SA" not in provider["coverage"]:
            continue
        # لو العميل دولي والشركة لا تدعم دولي
        if not is_sa and "INTL" not in provider["coverage"] and customer_country not in provider["coverage"]:
            continue
        # نفس المدينة — اقتراح الشحن السريع كبديل (مش الأرخص)
        if is_same_city and local_delivery_enabled:
            # نقدم خيار شحن سريع لو العميل يفضّل
            pass
        
        rates = custom_rates.get(pid) or provider["default_rates"]
        is_intl = not is_sa
        if is_intl:
            base = float(rates.get("international_base_fee") or rates.get("base_fee", 90))
            extra = float(rates.get("international_extra_kg_fee") or rates.get("extra_kg_fee", 25))
            d_min = int(rates.get("international_delivery_days_min") or rates.get("delivery_days_min", 5))
            d_max = int(rates.get("international_delivery_days_max") or rates.get("delivery_days_max", 10))
        else:
            base = float(rates.get("base_fee", provider["default_rates"]["base_fee"]))
            extra = float(rates.get("extra_kg_fee", provider["default_rates"]["extra_kg_fee"]))
            d_min = int(rates.get("delivery_days_min", provider["default_rates"]["delivery_days_min"]))
            d_max = int(rates.get("delivery_days_max", provider["default_rates"]["delivery_days_max"]))
        
        weight_overage = max(0.0, weight_kg - 5.0)
        fee = (base + (extra * weight_overage)) * region_mult
        # Free shipping override
        if free_shipping_above and cart_subtotal >= free_shipping_above and not is_intl:
            fee = 0.0
        
        options.append({
            "provider_id": pid,
            "provider_name": provider["name_ar"],
            "name_en": provider["name_en"],
            "icon": provider["icon"],
            "logo": provider.get("logo"),
            "color": provider.get("color"),
            "fee_sar": round(fee, 2),
            "delivery_eta": f"{d_min}-{d_max} أيام",
            "delivery_days_min": d_min,
            "delivery_days_max": d_max,
            "service_type": "international" if is_intl else "domestic",
            "supports_cod": provider.get("supports_cod", False),
            "is_recommended": False,
            "is_free": fee == 0,
        })
    
    # ──────────────────────────────────────────────────────────────────
    # رتّب حسب السعر (الأرخص أولاً)، الأرخص = recommended إن لم يوجد local
    # ──────────────────────────────────────────────────────────────────
    options.sort(key=lambda x: (x["fee_sar"], x["delivery_days_min"]))
    if options and not any(o.get("is_recommended") for o in options):
        options[0]["is_recommended"] = True
    
    return options


def detect_country_from_ip(ip: str) -> Tuple[str, Optional[str]]:
    """
    يكتشف دولة + مدينة العميل من IP باستخدام ipapi.co المجاني.
    Returns (country_code, city_name) — fallback إلى ("SA", None) عند الفشل.
    """
    try:
        import urllib.request
        import json as _json
        if not ip or ip.startswith(("127.", "10.", "172.16.", "192.168.")):
            return ("SA", None)  # localhost — افتراض السعودية للاختبار
        req = urllib.request.Request(
            f"https://ipapi.co/{ip}/json/",
            headers={"User-Agent": "Zitex/1.0"},
        )
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = _json.loads(resp.read())
            country = data.get("country_code", "SA")
            city = data.get("city")
            return (country, city)
    except Exception:
        return ("SA", None)


def get_provider_info(provider_id: str) -> Optional[Dict[str, Any]]:
    """Return public info for a provider (for the dashboard UI)."""
    return PROVIDER_BY_ID.get(provider_id)


def get_all_providers_summary() -> List[Dict[str, Any]]:
    """List all providers with safe fields for the dashboard."""
    out = []
    for p in SHIPPING_PROVIDERS:
        out.append({
            "id": p["id"],
            "name_ar": p["name_ar"],
            "name_en": p["name_en"],
            "icon": p["icon"],
            "color": p["color"],
            "logo": p["logo"],
            "coverage": p["coverage"],
            "service_types": p["service_types"],
            "supports_cod": p["supports_cod"],
            "supports_returns": p["supports_returns"],
            "default_rates": p["default_rates"],
            "tracking_url_template": p["tracking_url_template"],
        })
    return out
