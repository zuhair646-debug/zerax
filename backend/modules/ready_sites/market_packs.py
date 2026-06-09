"""Market Packs — Complete localization data for 15 markets.

Each pack contains everything a generated site needs to fully adapt:
- Language, direction, font
- Currency + symbol + format
- Payment gateways native to that market
- Local shipping carriers
- Chat apps (WhatsApp vs WeChat vs LINE vs KakaoTalk)
- Tax system
- Seasonal promotions
- Number format + calendar
"""
from __future__ import annotations
from typing import Any, Dict, List

# fmt: off
MARKET_PACKS: Dict[str, Dict[str, Any]] = {

  # ═══════════════════════════════════════ GULF / GCC ═══════════════════════════════════════
  "sa": {
    "id": "sa", "name_ar": "السعودية", "name_en": "Saudi Arabia", "flag": "🇸🇦",
    "language": "ar", "direction": "rtl", "font": "Tajawal",
    "currency": "SAR", "symbol": "ر.س", "number_format": "1,234.56",
    "calendar": ["hijri", "gregorian"], "primary_calendar": "gregorian",
    "tax": {"name_ar": "ضريبة القيمة المضافة", "name_en": "VAT", "rate": 15},
    "payment_gateways": [
      {"id": "mada", "name": "مدى", "type": "card", "fee_pct": 1.0, "logo": "mada"},
      {"id": "visa_mc", "name": "Visa / Mastercard", "type": "card", "fee_pct": 2.5},
      {"id": "tabby", "name": "Tabby", "type": "bnpl", "tagline": "اشتر الآن وادفع لاحقاً · 4 دفعات", "fee_pct": 6.0},
      {"id": "tamara", "name": "Tamara", "type": "bnpl", "tagline": "قسّم على 3 دفعات بلا فوائد", "fee_pct": 6.0},
      {"id": "stcpay", "name": "STC Pay", "type": "wallet", "fee_pct": 1.5},
      {"id": "apple_pay", "name": "Apple Pay", "type": "wallet", "fee_pct": 2.0},
      {"id": "urway", "name": "URWAY", "type": "card", "fee_pct": 2.5},
      {"id": "cod", "name": "الدفع عند الاستلام", "type": "cash"},
    ],
    "shipping_carriers": [
      {"id": "smsa", "name": "SMSA Express", "days": "1-2", "name_ar": "سمسا"},
      {"id": "aramex", "name": "Aramex", "days": "1-3", "name_ar": "أرامكس"},
      {"id": "naqel", "name": "Naqel", "days": "1-3", "name_ar": "ناقل"},
      {"id": "j_and_t", "name": "J&T Express", "days": "2-4"},
      {"id": "spl", "name": "Saudi Post (SPL)", "days": "3-5", "name_ar": "سبل"},
    ],
    "chat_apps": [
      {"id": "whatsapp", "name": "واتساب", "url_scheme": "https://wa.me/{phone}"},
      {"id": "snapchat", "name": "سناب شات", "url_scheme": "https://snapchat.com/add/{handle}"},
    ],
    "compliance": {"e_invoice": "ZATCA Fatoora (Phase 2)", "vat_required": True, "cr_required": True},
    "seasonal_promos": [
      {"id": "national_day", "name_ar": "اليوم الوطني السعودي", "month": 9, "day": 23},
      {"id": "ramadan", "name_ar": "رمضان كريم", "lunar_month": "Ramadan"},
      {"id": "white_friday", "name_ar": "الجمعة البيضاء", "month": 11},
      {"id": "riyadh_season", "name_ar": "موسم الرياض", "months": [10, 11, 12]},
    ],
  },

  "ae": {
    "id": "ae", "name_ar": "الإمارات", "name_en": "United Arab Emirates", "flag": "🇦🇪",
    "language": "ar", "direction": "rtl", "font": "Tajawal",
    "currency": "AED", "symbol": "د.إ", "number_format": "1,234.56",
    "calendar": ["hijri", "gregorian"], "primary_calendar": "gregorian",
    "tax": {"name_ar": "ضريبة القيمة المضافة", "name_en": "VAT", "rate": 5},
    "payment_gateways": [
      {"id": "tabby", "name": "Tabby", "type": "bnpl"},
      {"id": "tamara", "name": "Tamara", "type": "bnpl"},
      {"id": "telr", "name": "Telr", "type": "card"},
      {"id": "network", "name": "Network International", "type": "card"},
      {"id": "payby", "name": "PayBy", "type": "wallet"},
      {"id": "apple_pay", "name": "Apple Pay", "type": "wallet"},
      {"id": "visa_mc", "name": "Visa / Mastercard", "type": "card"},
      {"id": "cod", "name": "الدفع عند الاستلام", "type": "cash"},
    ],
    "shipping_carriers": [
      {"id": "aramex", "name": "Aramex", "days": "1-2"},
      {"id": "emirates_post", "name": "Emirates Post"},
      {"id": "fetchr", "name": "Fetchr"},
      {"id": "fedex", "name": "FedEx"},
    ],
    "chat_apps": [{"id": "whatsapp", "name": "WhatsApp"}],
    "compliance": {"e_invoice": "UAE FTA", "vat_required": True},
    "seasonal_promos": [
      {"id": "uae_national", "name_ar": "اليوم الوطني الإماراتي", "month": 12, "day": 2},
      {"id": "dubai_shopping", "name_ar": "مهرجان دبي للتسوق", "months": [12, 1]},
    ],
  },

  "kw": {
    "id": "kw", "name_ar": "الكويت", "name_en": "Kuwait", "flag": "🇰🇼",
    "language": "ar", "direction": "rtl", "font": "Tajawal",
    "currency": "KWD", "symbol": "د.ك", "number_format": "1,234.567",
    "calendar": ["hijri", "gregorian"], "primary_calendar": "gregorian",
    "tax": {"name_ar": "بدون ضريبة", "name_en": "No VAT", "rate": 0},
    "payment_gateways": [
      {"id": "knet", "name": "KNET", "type": "card", "tagline": "الدفع المحلي الكويتي"},
      {"id": "tabby", "name": "Tabby", "type": "bnpl"},
      {"id": "tamara", "name": "Tamara", "type": "bnpl"},
      {"id": "myfatoorah", "name": "MyFatoorah", "type": "card"},
      {"id": "visa_mc", "name": "Visa / Mastercard", "type": "card"},
      {"id": "apple_pay", "name": "Apple Pay", "type": "wallet"},
      {"id": "cod", "name": "الدفع عند الاستلام", "type": "cash"},
    ],
    "shipping_carriers": [
      {"id": "aramex", "name": "Aramex"},
      {"id": "kuwait_post", "name": "Kuwait Post"},
      {"id": "dhl", "name": "DHL"},
    ],
    "chat_apps": [{"id": "whatsapp", "name": "WhatsApp"}, {"id": "instagram", "name": "Instagram"}],
    "compliance": {"vat_required": False},
    "seasonal_promos": [{"id": "national_day", "name_ar": "العيد الوطني الكويتي", "month": 2, "day": 25}],
  },

  "qa": {
    "id": "qa", "name_ar": "قطر", "name_en": "Qatar", "flag": "🇶🇦",
    "language": "ar", "direction": "rtl", "font": "Tajawal",
    "currency": "QAR", "symbol": "ر.ق", "number_format": "1,234.56",
    "calendar": ["hijri", "gregorian"],
    "tax": {"name_ar": "بدون ضريبة", "rate": 0},
    "payment_gateways": [
      {"id": "qpay", "name": "QPAY", "type": "card", "tagline": "الدفع القطري المحلي"},
      {"id": "naps", "name": "NAPS", "type": "card"},
      {"id": "tabby", "name": "Tabby", "type": "bnpl"},
      {"id": "tamara", "name": "Tamara", "type": "bnpl"},
      {"id": "visa_mc", "name": "Visa / Mastercard", "type": "card"},
      {"id": "apple_pay", "name": "Apple Pay", "type": "wallet"},
      {"id": "cod", "name": "الدفع عند الاستلام", "type": "cash"},
    ],
    "shipping_carriers": [{"id": "qatar_post", "name": "Qatar Post"}, {"id": "aramex", "name": "Aramex"}],
    "chat_apps": [{"id": "whatsapp", "name": "WhatsApp"}],
    "seasonal_promos": [{"id": "qatar_national", "name_ar": "اليوم الوطني القطري", "month": 12, "day": 18}],
  },

  "bh": {
    "id": "bh", "name_ar": "البحرين", "name_en": "Bahrain", "flag": "🇧🇭",
    "language": "ar", "direction": "rtl", "font": "Tajawal",
    "currency": "BHD", "symbol": "د.ب", "number_format": "1,234.567",
    "tax": {"name_ar": "ضريبة القيمة المضافة", "rate": 10},
    "payment_gateways": [
      {"id": "benefitpay", "name": "BenefitPay", "type": "wallet", "tagline": "الدفع البحريني المحلي"},
      {"id": "tabby", "name": "Tabby", "type": "bnpl"},
      {"id": "tamara", "name": "Tamara", "type": "bnpl"},
      {"id": "visa_mc", "name": "Visa / Mastercard", "type": "card"},
      {"id": "apple_pay", "name": "Apple Pay", "type": "wallet"},
      {"id": "cod", "name": "الدفع عند الاستلام", "type": "cash"},
    ],
    "shipping_carriers": [{"id": "aramex", "name": "Aramex"}, {"id": "bahrain_post", "name": "Bahrain Post"}],
    "chat_apps": [{"id": "whatsapp", "name": "WhatsApp"}],
  },

  "om": {
    "id": "om", "name_ar": "عُمان", "name_en": "Oman", "flag": "🇴🇲",
    "language": "ar", "direction": "rtl", "font": "Tajawal",
    "currency": "OMR", "symbol": "ر.ع", "number_format": "1,234.567",
    "tax": {"name_ar": "ضريبة القيمة المضافة", "rate": 5},
    "payment_gateways": [
      {"id": "thawani", "name": "Thawani", "type": "wallet", "tagline": "الدفع العماني المحلي"},
      {"id": "omannet", "name": "OmanNet", "type": "card"},
      {"id": "tabby", "name": "Tabby", "type": "bnpl"},
      {"id": "tamara", "name": "Tamara", "type": "bnpl"},
      {"id": "visa_mc", "name": "Visa / Mastercard", "type": "card"},
      {"id": "cod", "name": "الدفع عند الاستلام", "type": "cash"},
    ],
    "shipping_carriers": [{"id": "aramex", "name": "Aramex"}, {"id": "asyad", "name": "Asyad Express"}],
    "chat_apps": [{"id": "whatsapp", "name": "WhatsApp"}],
  },

  # ═══════════════════════════════════════ LEVANT & WEST ASIA ═══════════════════════════════════════
  "iq": {
    "id": "iq", "name_ar": "العراق", "name_en": "Iraq", "flag": "🇮🇶",
    "language": "ar", "direction": "rtl", "font": "Tajawal",
    "currency": "IQD", "symbol": "د.ع", "number_format": "1,234",
    "tax": {"rate": 0},
    "payment_gateways": [
      {"id": "zaincash", "name": "ZainCash", "type": "wallet", "tagline": "محفظة زين العراق"},
      {"id": "asiahawala", "name": "Asia Hawala", "type": "wallet"},
      {"id": "fastpay", "name": "FastPay", "type": "wallet"},
      {"id": "qicard", "name": "Qi Card", "type": "card"},
      {"id": "cod", "name": "الدفع عند الاستلام", "type": "cash", "popular": True},
    ],
    "shipping_carriers": [{"id": "iraqi_post", "name": "Iraqi Post"}, {"id": "aramex", "name": "Aramex"}],
    "chat_apps": [{"id": "whatsapp", "name": "WhatsApp"}, {"id": "viber", "name": "Viber"}, {"id": "telegram", "name": "Telegram"}],
  },

  "sy": {
    "id": "sy", "name_ar": "سوريا", "name_en": "Syria", "flag": "🇸🇾",
    "language": "ar", "direction": "rtl", "font": "Tajawal",
    "currency": "SYP", "symbol": "ل.س", "number_format": "1,234",
    "tax": {"rate": 0},
    "payment_gateways": [
      {"id": "syriatel_cash", "name": "Syriatel Cash", "type": "wallet"},
      {"id": "mtn_cash", "name": "MTN Cash", "type": "wallet"},
      {"id": "alharam", "name": "Al-Haram Exchange", "type": "transfer"},
      {"id": "cod", "name": "الدفع عند الاستلام", "type": "cash", "popular": True},
    ],
    "shipping_carriers": [{"id": "syrian_post", "name": "Syrian Post"}, {"id": "private", "name": "نقل خاص"}],
    "chat_apps": [{"id": "whatsapp", "name": "WhatsApp"}, {"id": "telegram", "name": "Telegram"}],
  },

  "jo": {
    "id": "jo", "name_ar": "الأردن", "name_en": "Jordan", "flag": "🇯🇴",
    "language": "ar", "direction": "rtl", "font": "Tajawal",
    "currency": "JOD", "symbol": "د.أ", "number_format": "1,234.567",
    "tax": {"name_ar": "ضريبة المبيعات", "rate": 16},
    "payment_gateways": [
      {"id": "efawateercom", "name": "eFAWATEERcom", "type": "wallet"},
      {"id": "dinarak", "name": "Dinarak", "type": "wallet"},
      {"id": "zaincash_jo", "name": "Zain Cash", "type": "wallet"},
      {"id": "uwallet", "name": "U Wallet", "type": "wallet"},
      {"id": "tabby", "name": "Tabby", "type": "bnpl"},
      {"id": "visa_mc", "name": "Visa / Mastercard", "type": "card"},
      {"id": "cod", "name": "الدفع عند الاستلام", "type": "cash"},
    ],
    "shipping_carriers": [{"id": "aramex", "name": "Aramex"}, {"id": "jordan_post", "name": "Jordan Post"}],
    "chat_apps": [{"id": "whatsapp", "name": "WhatsApp"}],
  },

  "lb": {
    "id": "lb", "name_ar": "لبنان", "name_en": "Lebanon", "flag": "🇱🇧",
    "language": "ar", "direction": "rtl", "font": "Tajawal",
    "currency": "LBP", "symbol": "ل.ل", "number_format": "1,234",
    "tax": {"name_ar": "TVA", "rate": 11},
    "payment_gateways": [
      {"id": "whish", "name": "Whish Money", "type": "wallet"},
      {"id": "omt", "name": "OMT", "type": "transfer"},
      {"id": "areeba", "name": "Areeba", "type": "card"},
      {"id": "visa_mc", "name": "Visa / Mastercard", "type": "card"},
      {"id": "cod_usd", "name": "كاش (دولار/ليرة)", "type": "cash", "popular": True},
    ],
    "shipping_carriers": [{"id": "libanpost", "name": "LibanPost"}, {"id": "aramex", "name": "Aramex"}],
    "chat_apps": [{"id": "whatsapp", "name": "WhatsApp"}],
  },

  "eg": {
    "id": "eg", "name_ar": "مصر", "name_en": "Egypt", "flag": "🇪🇬",
    "language": "ar", "direction": "rtl", "font": "Tajawal",
    "currency": "EGP", "symbol": "ج.م", "number_format": "1,234.56",
    "tax": {"name_ar": "ضريبة القيمة المضافة", "rate": 14},
    "payment_gateways": [
      {"id": "fawry", "name": "Fawry", "type": "wallet", "tagline": "المحفظة المصرية الرائدة"},
      {"id": "paymob", "name": "Paymob", "type": "gateway"},
      {"id": "valu", "name": "valU", "type": "bnpl", "tagline": "قسّط حتى 60 شهر"},
      {"id": "instapay", "name": "InstaPay", "type": "wallet"},
      {"id": "vodafone_cash", "name": "Vodafone Cash", "type": "wallet"},
      {"id": "visa_mc", "name": "Visa / Mastercard", "type": "card"},
      {"id": "cod", "name": "الدفع عند الاستلام", "type": "cash", "popular": True},
    ],
    "shipping_carriers": [
      {"id": "aramex", "name": "Aramex"},
      {"id": "egypt_post", "name": "Egypt Post"},
      {"id": "bosta", "name": "Bosta"},
      {"id": "mylerz", "name": "Mylerz"},
    ],
    "chat_apps": [{"id": "whatsapp", "name": "WhatsApp"}],
  },

  "ir": {
    "id": "ir", "name_ar": "إيران", "name_en": "Iran", "flag": "🇮🇷",
    "language": "fa", "direction": "rtl", "font": "Vazirmatn",
    "currency": "IRR", "symbol": "﷼", "number_format": "1,234",
    "tax": {"rate": 9},
    "payment_gateways": [
      {"id": "shaparak", "name": "Shaparak", "type": "card", "tagline": "نظام الدفع الإيراني الوطني"},
      {"id": "zarinpal", "name": "ZarinPal", "type": "gateway"},
      {"id": "idpay", "name": "IDPay", "type": "gateway"},
      {"id": "ap", "name": "AP", "type": "wallet"},
      {"id": "cod", "name": "الدفع عند الاستلام", "type": "cash"},
    ],
    "shipping_carriers": [{"id": "iran_post", "name": "Iran Post"}, {"id": "tipax", "name": "TIPAX"}],
    "chat_apps": [{"id": "telegram", "name": "Telegram", "popular": True}, {"id": "whatsapp", "name": "WhatsApp"}],
  },

  # ═══════════════════════════════════════ ASIA ═══════════════════════════════════════
  "cn": {
    "id": "cn", "name_ar": "الصين", "name_en": "China", "flag": "🇨🇳",
    "language": "zh", "direction": "ltr", "font": "Noto Sans SC",
    "currency": "CNY", "symbol": "¥", "number_format": "1,234.56",
    "calendar": ["lunar", "gregorian"],
    "tax": {"name_en": "VAT (增值税)", "rate": 13},
    "payment_gateways": [
      {"id": "alipay", "name": "Alipay (支付宝)", "type": "wallet", "popular": True, "fee_pct": 1.2},
      {"id": "wechat_pay", "name": "WeChat Pay (微信支付)", "type": "wallet", "popular": True, "fee_pct": 1.2},
      {"id": "unionpay", "name": "UnionPay (银联)", "type": "card", "fee_pct": 1.0},
      {"id": "qr_code", "name": "QR Payment", "type": "qr"},
    ],
    "shipping_carriers": [
      {"id": "sf_express", "name": "SF Express (顺丰)", "days": "1-3", "popular": True},
      {"id": "zto", "name": "ZTO Express (中通)", "days": "3-7"},
      {"id": "yto", "name": "YTO Express (圆通)", "days": "3-7"},
      {"id": "sto", "name": "STO (申通)", "days": "3-7"},
      {"id": "jd_logistics", "name": "JD Logistics (京东物流)", "days": "1-3"},
    ],
    "chat_apps": [
      {"id": "wechat", "name": "WeChat (微信)", "popular": True, "url_scheme": "weixin://"},
      {"id": "weibo", "name": "Weibo (微博)"},
    ],
    "compliance": {"e_invoice": "Fapiao (发票)", "vat_required": True},
    "seasonal_promos": [
      {"id": "double_11", "name_en": "Singles Day (双十一)", "month": 11, "day": 11, "size": "HUGE"},
      {"id": "618", "name_en": "618 Festival", "month": 6, "day": 18, "size": "BIG"},
      {"id": "cny", "name_en": "Chinese New Year (春节)", "lunar": True, "size": "HUGE"},
      {"id": "double_12", "name_en": "Double 12", "month": 12, "day": 12},
    ],
  },

  "jp": {
    "id": "jp", "name_ar": "اليابان", "name_en": "Japan", "flag": "🇯🇵",
    "language": "ja", "direction": "ltr", "font": "Noto Sans JP",
    "currency": "JPY", "symbol": "¥", "number_format": "1,234",
    "tax": {"name_en": "消費税", "rate": 10},
    "payment_gateways": [
      {"id": "paypay", "name": "PayPay", "type": "wallet", "popular": True},
      {"id": "line_pay", "name": "LINE Pay", "type": "wallet"},
      {"id": "rakuten_pay", "name": "Rakuten Pay", "type": "wallet"},
      {"id": "konbini", "name": "Konbini (コンビニ払い)", "type": "cash", "tagline": "ادفع في 7-Eleven/Lawson"},
      {"id": "stripe_jp", "name": "Stripe Japan", "type": "card"},
      {"id": "amazon_pay_jp", "name": "Amazon Pay", "type": "wallet"},
    ],
    "shipping_carriers": [
      {"id": "yamato", "name": "Yamato Transport (ヤマト)", "days": "1-2", "popular": True},
      {"id": "sagawa", "name": "Sagawa Express (佐川急便)", "days": "1-2"},
      {"id": "japan_post", "name": "Japan Post (日本郵便)", "days": "2-4"},
    ],
    "chat_apps": [{"id": "line", "name": "LINE", "popular": True}, {"id": "twitter", "name": "X (Twitter)"}],
    "seasonal_promos": [{"id": "rakuten_super_sale", "name_en": "Rakuten Super Sale", "months": [3, 6, 9, 12]}],
  },

  "kr": {
    "id": "kr", "name_ar": "كوريا الجنوبية", "name_en": "South Korea", "flag": "🇰🇷",
    "language": "ko", "direction": "ltr", "font": "Noto Sans KR",
    "currency": "KRW", "symbol": "₩", "number_format": "1,234",
    "tax": {"name_en": "VAT", "rate": 10},
    "payment_gateways": [
      {"id": "kakao_pay", "name": "KakaoPay", "type": "wallet", "popular": True},
      {"id": "naver_pay", "name": "Naver Pay", "type": "wallet", "popular": True},
      {"id": "toss", "name": "Toss", "type": "wallet"},
      {"id": "samsung_pay", "name": "Samsung Pay", "type": "wallet"},
      {"id": "kg_inicis", "name": "KG Inicis", "type": "card"},
    ],
    "shipping_carriers": [
      {"id": "cj_logistics", "name": "CJ Logistics (대한통운)", "days": "1-2", "popular": True},
      {"id": "hanjin", "name": "Hanjin (한진)", "days": "1-2"},
      {"id": "korea_post", "name": "Korea Post (우체국)", "days": "1-3"},
    ],
    "chat_apps": [{"id": "kakaotalk", "name": "KakaoTalk (카카오톡)", "popular": True}],
  },

  "in": {
    "id": "in", "name_ar": "الهند", "name_en": "India", "flag": "🇮🇳",
    "language": "hi", "direction": "ltr", "font": "Noto Sans Devanagari",
    "currency": "INR", "symbol": "₹", "number_format": "1,23,456.78",
    "tax": {"name_en": "GST", "rate": 18},
    "payment_gateways": [
      {"id": "upi", "name": "UPI (PhonePe/GPay/BHIM)", "type": "wallet", "popular": True, "fee_pct": 0},
      {"id": "paytm", "name": "Paytm", "type": "wallet", "popular": True},
      {"id": "razorpay", "name": "Razorpay", "type": "gateway"},
      {"id": "phonepe", "name": "PhonePe", "type": "wallet"},
      {"id": "bharatpe", "name": "BharatPe", "type": "wallet"},
      {"id": "cod", "name": "Cash on Delivery", "type": "cash", "popular": True},
    ],
    "shipping_carriers": [
      {"id": "delhivery", "name": "Delhivery", "days": "2-5"},
      {"id": "blue_dart", "name": "Blue Dart", "days": "1-3"},
      {"id": "ekart", "name": "Ekart", "days": "2-5"},
      {"id": "india_post", "name": "India Post", "days": "3-7"},
    ],
    "chat_apps": [{"id": "whatsapp", "name": "WhatsApp", "popular": True}],
    "seasonal_promos": [
      {"id": "diwali", "name_en": "Diwali Sale", "month": 11},
      {"id": "republic_day", "name_en": "Republic Day Sale", "month": 1, "day": 26},
    ],
  },

  # ═══════════════════════════════════════ WEST ═══════════════════════════════════════
  "us": {
    "id": "us", "name_ar": "أمريكا", "name_en": "United States", "flag": "🇺🇸",
    "language": "en", "direction": "ltr", "font": "Inter",
    "currency": "USD", "symbol": "$", "number_format": "1,234.56",
    "tax": {"name_en": "Sales Tax", "rate": "varies", "note": "State-dependent (0-10%)"},
    "payment_gateways": [
      {"id": "stripe", "name": "Stripe", "type": "gateway", "popular": True},
      {"id": "paypal", "name": "PayPal", "type": "wallet", "popular": True},
      {"id": "apple_pay", "name": "Apple Pay", "type": "wallet"},
      {"id": "google_pay", "name": "Google Pay", "type": "wallet"},
      {"id": "klarna", "name": "Klarna", "type": "bnpl", "tagline": "Pay in 4"},
      {"id": "affirm", "name": "Affirm", "type": "bnpl"},
      {"id": "afterpay", "name": "Afterpay", "type": "bnpl"},
      {"id": "cash_app", "name": "Cash App", "type": "wallet"},
      {"id": "venmo", "name": "Venmo", "type": "wallet"},
    ],
    "shipping_carriers": [
      {"id": "usps", "name": "USPS", "days": "2-5"},
      {"id": "fedex", "name": "FedEx", "days": "1-3"},
      {"id": "ups", "name": "UPS", "days": "1-5"},
      {"id": "dhl_us", "name": "DHL Express", "days": "1-3"},
    ],
    "chat_apps": [
      {"id": "imessage", "name": "iMessage", "popular": True},
      {"id": "instagram_dm", "name": "Instagram DM"},
      {"id": "facebook_messenger", "name": "Facebook Messenger"},
    ],
    "seasonal_promos": [
      {"id": "black_friday", "name_en": "Black Friday", "month": 11, "size": "HUGE"},
      {"id": "cyber_monday", "name_en": "Cyber Monday", "month": 11, "size": "HUGE"},
      {"id": "prime_day", "name_en": "Amazon Prime Day", "month": 7, "size": "BIG"},
      {"id": "christmas", "name_en": "Holiday Season", "month": 12, "size": "HUGE"},
    ],
  },

  # ═══════════════════════════════════════ EUROPE ═══════════════════════════════════════
  "gb": {
    "id": "gb", "name_ar": "بريطانيا", "name_en": "United Kingdom", "flag": "🇬🇧",
    "language": "en", "direction": "ltr", "font": "Inter",
    "currency": "GBP", "symbol": "£", "number_format": "1,234.56",
    "tax": {"name_en": "VAT", "rate": 20},
    "payment_gateways": [
      {"id": "stripe_uk", "name": "Stripe", "type": "gateway", "popular": True},
      {"id": "paypal", "name": "PayPal", "type": "wallet", "popular": True},
      {"id": "apple_pay", "name": "Apple Pay", "type": "wallet"},
      {"id": "google_pay", "name": "Google Pay", "type": "wallet"},
      {"id": "klarna", "name": "Klarna", "type": "bnpl"},
      {"id": "clearpay", "name": "Clearpay", "type": "bnpl"},
      {"id": "amazon_pay", "name": "Amazon Pay", "type": "wallet"},
    ],
    "shipping_carriers": [
      {"id": "royal_mail", "name": "Royal Mail", "days": "1-3", "popular": True},
      {"id": "dpd_uk", "name": "DPD", "days": "1-2"},
      {"id": "hermes_uk", "name": "Hermes (Evri)", "days": "2-4"},
    ],
    "chat_apps": [{"id": "whatsapp", "name": "WhatsApp"}, {"id": "imessage", "name": "iMessage"}],
    "seasonal_promos": [{"id": "boxing_day", "name_en": "Boxing Day", "month": 12, "day": 26, "size": "BIG"}],
  },

  "fr": {
    "id": "fr", "name_ar": "فرنسا", "name_en": "France", "flag": "🇫🇷",
    "language": "fr", "direction": "ltr", "font": "Inter",
    "currency": "EUR", "symbol": "€", "number_format": "1 234,56",
    "tax": {"name_en": "TVA", "rate": 20},
    "payment_gateways": [
      {"id": "stripe", "name": "Stripe", "type": "gateway", "popular": True},
      {"id": "paypal", "name": "PayPal", "type": "wallet", "popular": True},
      {"id": "apple_pay", "name": "Apple Pay", "type": "wallet"},
      {"id": "klarna", "name": "Klarna", "type": "bnpl"},
      {"id": "alma", "name": "Alma", "type": "bnpl", "tagline": "Paiement en plusieurs fois"},
      {"id": "cb", "name": "Carte Bancaire", "type": "card"},
    ],
    "shipping_carriers": [
      {"id": "la_poste", "name": "La Poste", "days": "2-4", "popular": True},
      {"id": "chronopost", "name": "Chronopost", "days": "1-2"},
      {"id": "colissimo", "name": "Colissimo", "days": "2-3"},
    ],
    "chat_apps": [{"id": "whatsapp", "name": "WhatsApp"}, {"id": "instagram_dm", "name": "Instagram"}],
    "seasonal_promos": [{"id": "soldes", "name_en": "Soldes d'été/hiver", "size": "BIG"}],
  },

  "de": {
    "id": "de", "name_ar": "ألمانيا", "name_en": "Germany", "flag": "🇩🇪",
    "language": "de", "direction": "ltr", "font": "Inter",
    "currency": "EUR", "symbol": "€", "number_format": "1.234,56",
    "tax": {"name_en": "MwSt", "rate": 19},
    "payment_gateways": [
      {"id": "klarna", "name": "Klarna", "type": "bnpl", "popular": True, "tagline": "Sofortüberweisung"},
      {"id": "sepa", "name": "SEPA Lastschrift", "type": "transfer", "popular": True},
      {"id": "giropay", "name": "Giropay", "type": "transfer"},
      {"id": "paypal", "name": "PayPal", "type": "wallet"},
      {"id": "sofort", "name": "Sofort", "type": "transfer"},
      {"id": "apple_pay", "name": "Apple Pay", "type": "wallet"},
    ],
    "shipping_carriers": [
      {"id": "dhl", "name": "DHL", "days": "1-2", "popular": True},
      {"id": "hermes_de", "name": "Hermes", "days": "2-4"},
      {"id": "dpd_de", "name": "DPD", "days": "1-3"},
    ],
    "chat_apps": [{"id": "whatsapp", "name": "WhatsApp"}, {"id": "telegram", "name": "Telegram"}],
    "seasonal_promos": [{"id": "weihnachten", "name_en": "Weihnachten", "month": 12, "size": "HUGE"}],
  },

  "it": {
    "id": "it", "name_ar": "إيطاليا", "name_en": "Italy", "flag": "🇮🇹",
    "language": "it", "direction": "ltr", "font": "Inter",
    "currency": "EUR", "symbol": "€", "number_format": "1.234,56",
    "tax": {"name_en": "IVA", "rate": 22},
    "payment_gateways": [
      {"id": "stripe", "name": "Stripe", "type": "gateway"},
      {"id": "paypal", "name": "PayPal", "type": "wallet", "popular": True},
      {"id": "satispay", "name": "Satispay", "type": "wallet", "tagline": "App italiana"},
      {"id": "scalapay", "name": "Scalapay", "type": "bnpl"},
      {"id": "klarna", "name": "Klarna", "type": "bnpl"},
      {"id": "postepay", "name": "PostePay", "type": "card"},
    ],
    "shipping_carriers": [
      {"id": "poste_italiane", "name": "Poste Italiane", "days": "2-4"},
      {"id": "brt", "name": "BRT (Bartolini)", "days": "1-3"},
      {"id": "sda", "name": "SDA Express", "days": "1-3"},
    ],
    "chat_apps": [{"id": "whatsapp", "name": "WhatsApp"}],
  },

  "es": {
    "id": "es", "name_ar": "إسبانيا", "name_en": "Spain", "flag": "🇪🇸",
    "language": "es", "direction": "ltr", "font": "Inter",
    "currency": "EUR", "symbol": "€", "number_format": "1.234,56",
    "tax": {"name_en": "IVA", "rate": 21},
    "payment_gateways": [
      {"id": "stripe", "name": "Stripe", "type": "gateway"},
      {"id": "paypal", "name": "PayPal", "type": "wallet", "popular": True},
      {"id": "bizum", "name": "Bizum", "type": "wallet", "popular": True, "tagline": "Pago instantáneo"},
      {"id": "klarna", "name": "Klarna", "type": "bnpl"},
      {"id": "aplazame", "name": "Aplazame", "type": "bnpl"},
    ],
    "shipping_carriers": [
      {"id": "correos", "name": "Correos", "days": "2-4"},
      {"id": "seur", "name": "SEUR", "days": "1-2"},
      {"id": "mrw", "name": "MRW", "days": "1-2"},
    ],
    "chat_apps": [{"id": "whatsapp", "name": "WhatsApp"}],
  },

  "nl": {
    "id": "nl", "name_ar": "هولندا", "name_en": "Netherlands", "flag": "🇳🇱",
    "language": "nl", "direction": "ltr", "font": "Inter",
    "currency": "EUR", "symbol": "€", "number_format": "1.234,56",
    "tax": {"name_en": "BTW", "rate": 21},
    "payment_gateways": [
      {"id": "ideal", "name": "iDEAL", "type": "transfer", "popular": True, "tagline": "70% من المعاملات الهولندية"},
      {"id": "klarna", "name": "Klarna", "type": "bnpl"},
      {"id": "bancontact", "name": "Bancontact", "type": "card"},
      {"id": "paypal", "name": "PayPal", "type": "wallet"},
      {"id": "stripe", "name": "Stripe", "type": "gateway"},
    ],
    "shipping_carriers": [
      {"id": "postnl", "name": "PostNL", "days": "1-2", "popular": True},
      {"id": "dhl_nl", "name": "DHL Parcel", "days": "1-2"},
    ],
    "chat_apps": [{"id": "whatsapp", "name": "WhatsApp"}],
  },

  "ch": {
    "id": "ch", "name_ar": "سويسرا", "name_en": "Switzerland", "flag": "🇨🇭",
    "language": "de", "direction": "ltr", "font": "Inter",
    "currency": "CHF", "symbol": "CHF", "number_format": "1'234.56",
    "tax": {"name_en": "MWST", "rate": 7.7},
    "payment_gateways": [
      {"id": "twint", "name": "TWINT", "type": "wallet", "popular": True, "tagline": "تطبيق الدفع السويسري"},
      {"id": "postfinance", "name": "PostFinance", "type": "card"},
      {"id": "klarna", "name": "Klarna", "type": "bnpl"},
      {"id": "stripe", "name": "Stripe", "type": "gateway"},
      {"id": "paypal", "name": "PayPal", "type": "wallet"},
    ],
    "shipping_carriers": [
      {"id": "swiss_post", "name": "Swiss Post", "days": "1-2"},
      {"id": "dhl_ch", "name": "DHL Switzerland", "days": "1-3"},
    ],
    "chat_apps": [{"id": "whatsapp", "name": "WhatsApp"}],
  },

  "se": {
    "id": "se", "name_ar": "السويد", "name_en": "Sweden", "flag": "🇸🇪",
    "language": "sv", "direction": "ltr", "font": "Inter",
    "currency": "SEK", "symbol": "kr", "number_format": "1 234,56",
    "tax": {"name_en": "Moms", "rate": 25},
    "payment_gateways": [
      {"id": "swish", "name": "Swish", "type": "wallet", "popular": True, "tagline": "تطبيق الدفع السويدي"},
      {"id": "klarna", "name": "Klarna", "type": "bnpl", "popular": True, "tagline": "صناعة سويدية"},
      {"id": "bankgiro", "name": "Bankgiro", "type": "transfer"},
      {"id": "stripe", "name": "Stripe", "type": "gateway"},
    ],
    "shipping_carriers": [
      {"id": "postnord", "name": "PostNord", "days": "1-3"},
      {"id": "dhl_se", "name": "DHL Sweden", "days": "1-2"},
    ],
    "chat_apps": [{"id": "whatsapp", "name": "WhatsApp"}, {"id": "messenger", "name": "Messenger"}],
  },

  "ru": {
    "id": "ru", "name_ar": "روسيا", "name_en": "Russia", "flag": "🇷🇺",
    "language": "ru", "direction": "ltr", "font": "Inter",
    "currency": "RUB", "symbol": "₽", "number_format": "1 234,56",
    "tax": {"name_en": "НДС (VAT)", "rate": 20},
    "payment_gateways": [
      {"id": "mir", "name": "МИР (Mir)", "type": "card", "popular": True, "tagline": "نظام الدفع الروسي الوطني"},
      {"id": "yoomoney", "name": "ЮMoney (Yandex)", "type": "wallet", "popular": True},
      {"id": "sberpay", "name": "SberPay", "type": "wallet"},
      {"id": "tinkoff", "name": "Tinkoff Pay", "type": "wallet"},
      {"id": "qiwi", "name": "QIWI", "type": "wallet"},
      {"id": "cod", "name": "Наложенный платёж", "type": "cash", "popular": True},
    ],
    "shipping_carriers": [
      {"id": "russian_post", "name": "Почта России", "days": "5-14"},
      {"id": "sdek", "name": "СДЭК (CDEK)", "days": "2-5", "popular": True},
      {"id": "boxberry", "name": "Boxberry", "days": "3-7"},
    ],
    "chat_apps": [
      {"id": "telegram", "name": "Telegram", "popular": True},
      {"id": "vk", "name": "VK Messenger"},
      {"id": "whatsapp", "name": "WhatsApp"},
    ],
  },

  # ═══════════════════════════════════════ NORTH AFRICA ═══════════════════════════════════════
  "ma": {
    "id": "ma", "name_ar": "المغرب", "name_en": "Morocco", "flag": "🇲🇦",
    "language": "ar", "direction": "rtl", "font": "Tajawal",
    "currency": "MAD", "symbol": "د.م", "number_format": "1 234,56",
    "tax": {"name_ar": "ضريبة القيمة المضافة", "rate": 20},
    "payment_gateways": [
      {"id": "cmi", "name": "CMI", "type": "card", "popular": True, "tagline": "بوابة الدفع المغربية"},
      {"id": "youcanpay", "name": "YouCan Pay", "type": "gateway"},
      {"id": "payzone_ma", "name": "PayZone", "type": "gateway"},
      {"id": "cod", "name": "الدفع عند الاستلام", "type": "cash", "popular": True},
    ],
    "shipping_carriers": [
      {"id": "amana", "name": "Amana", "days": "1-3"},
      {"id": "barid_almaghrib", "name": "Barid Al-Maghrib", "days": "2-5"},
      {"id": "ctm_express", "name": "CTM Messagerie", "days": "1-3"},
    ],
    "chat_apps": [{"id": "whatsapp", "name": "WhatsApp"}, {"id": "instagram_dm", "name": "Instagram"}],
  },

  "dz": {
    "id": "dz", "name_ar": "الجزائر", "name_en": "Algeria", "flag": "🇩🇿",
    "language": "ar", "direction": "rtl", "font": "Tajawal",
    "currency": "DZD", "symbol": "د.ج", "number_format": "1 234,56",
    "tax": {"name_ar": "ضريبة القيمة المضافة", "rate": 19},
    "payment_gateways": [
      {"id": "satim", "name": "SATIM (CIB/Edahabia)", "type": "card", "popular": True},
      {"id": "baridi_mob", "name": "BaridiMob", "type": "wallet"},
      {"id": "cod", "name": "الدفع عند الاستلام", "type": "cash", "popular": True},
    ],
    "shipping_carriers": [
      {"id": "yalidine", "name": "Yalidine Express", "days": "1-3", "popular": True},
      {"id": "algerie_poste", "name": "Algérie Poste", "days": "2-5"},
      {"id": "zr_express", "name": "ZR Express", "days": "1-3"},
    ],
    "chat_apps": [{"id": "whatsapp", "name": "WhatsApp"}, {"id": "facebook_messenger", "name": "Messenger"}],
  },

  "tn": {
    "id": "tn", "name_ar": "تونس", "name_en": "Tunisia", "flag": "🇹🇳",
    "language": "ar", "direction": "rtl", "font": "Tajawal",
    "currency": "TND", "symbol": "د.ت", "number_format": "1 234,567",
    "tax": {"name_ar": "ضريبة القيمة المضافة", "rate": 19},
    "payment_gateways": [
      {"id": "click_to_pay", "name": "Click to Pay (Tunisie)", "type": "card"},
      {"id": "konnect", "name": "Konnect", "type": "gateway"},
      {"id": "edinar", "name": "e-Dinar", "type": "wallet"},
      {"id": "cod", "name": "الدفع عند الاستلام", "type": "cash", "popular": True},
    ],
    "shipping_carriers": [
      {"id": "rapid_post_tn", "name": "Rapid Poste", "days": "2-4"},
      {"id": "first_delivery", "name": "First Delivery", "days": "1-2"},
    ],
    "chat_apps": [{"id": "whatsapp", "name": "WhatsApp"}, {"id": "facebook_messenger", "name": "Messenger"}],
  },

  "ly": {
    "id": "ly", "name_ar": "ليبيا", "name_en": "Libya", "flag": "🇱🇾",
    "language": "ar", "direction": "rtl", "font": "Tajawal",
    "currency": "LYD", "symbol": "ل.د", "number_format": "1,234.567",
    "tax": {"rate": 0},
    "payment_gateways": [
      {"id": "moamalat", "name": "Moamalat", "type": "wallet"},
      {"id": "sadad_ly", "name": "Sadad Libya", "type": "transfer"},
      {"id": "cod", "name": "الدفع عند الاستلام", "type": "cash", "popular": True},
    ],
    "shipping_carriers": [
      {"id": "libyan_post", "name": "Libya Post", "days": "2-5"},
      {"id": "private_ly", "name": "نقل خاص", "days": "1-3"},
    ],
    "chat_apps": [{"id": "whatsapp", "name": "WhatsApp"}, {"id": "facebook_messenger", "name": "Messenger"}],
  },

  "sd": {
    "id": "sd", "name_ar": "السودان", "name_en": "Sudan", "flag": "🇸🇩",
    "language": "ar", "direction": "rtl", "font": "Tajawal",
    "currency": "SDG", "symbol": "ج.س", "number_format": "1,234.56",
    "tax": {"name_ar": "ضريبة القيمة المضافة", "rate": 17},
    "payment_gateways": [
      {"id": "bankak", "name": "Bankak (بنكك)", "type": "wallet", "popular": True},
      {"id": "fawry_sd", "name": "Fawry Sudan", "type": "wallet"},
      {"id": "cod", "name": "الدفع عند الاستلام", "type": "cash", "popular": True},
    ],
    "shipping_carriers": [{"id": "sudan_post", "name": "Sudan Post"}, {"id": "aramex", "name": "Aramex"}],
    "chat_apps": [{"id": "whatsapp", "name": "WhatsApp"}],
  },

  # ═══════════════════════════════════════ OTHER ARAB ═══════════════════════════════════════
  "ye": {
    "id": "ye", "name_ar": "اليمن", "name_en": "Yemen", "flag": "🇾🇪",
    "language": "ar", "direction": "rtl", "font": "Tajawal",
    "currency": "YER", "symbol": "ر.ي", "number_format": "1,234",
    "tax": {"rate": 0},
    "payment_gateways": [
      {"id": "alkuraimi", "name": "بنك الكريمي", "type": "wallet"},
      {"id": "cac_pay", "name": "CAC Pay", "type": "wallet"},
      {"id": "cod", "name": "الدفع عند الاستلام", "type": "cash", "popular": True},
    ],
    "shipping_carriers": [{"id": "yemen_post", "name": "بريد اليمن"}, {"id": "private_ye", "name": "نقل خاص"}],
    "chat_apps": [{"id": "whatsapp", "name": "WhatsApp"}, {"id": "telegram", "name": "Telegram"}],
  },

  "ps": {
    "id": "ps", "name_ar": "فلسطين", "name_en": "Palestine", "flag": "🇵🇸",
    "language": "ar", "direction": "rtl", "font": "Tajawal",
    "currency": "ILS", "symbol": "₪", "number_format": "1,234.56",
    "tax": {"name_ar": "ضريبة المبيعات", "rate": 17},
    "payment_gateways": [
      {"id": "jawwalpay", "name": "JawwalPay", "type": "wallet"},
      {"id": "paltel", "name": "PalTel Pay", "type": "wallet"},
      {"id": "cod", "name": "الدفع عند الاستلام", "type": "cash", "popular": True},
    ],
    "shipping_carriers": [{"id": "wassel", "name": "وصّل"}, {"id": "aramex", "name": "Aramex"}],
    "chat_apps": [{"id": "whatsapp", "name": "WhatsApp"}],
  },

  # ═══════════════════════════════════════ SOUTH/SOUTHEAST ASIA ═══════════════════════════════════════
  "pk": {
    "id": "pk", "name_ar": "باكستان", "name_en": "Pakistan", "flag": "🇵🇰",
    "language": "ur", "direction": "rtl", "font": "Noto Nastaliq Urdu",
    "currency": "PKR", "symbol": "₨", "number_format": "1,234.56",
    "tax": {"name_en": "GST", "rate": 17},
    "payment_gateways": [
      {"id": "easypaisa", "name": "EasyPaisa", "type": "wallet", "popular": True},
      {"id": "jazzcash", "name": "JazzCash", "type": "wallet", "popular": True},
      {"id": "sadapay", "name": "SadaPay", "type": "wallet"},
      {"id": "nayapay", "name": "NayaPay", "type": "wallet"},
      {"id": "cod", "name": "Cash on Delivery", "type": "cash", "popular": True},
    ],
    "shipping_carriers": [
      {"id": "tcs", "name": "TCS", "days": "1-3"},
      {"id": "leopards", "name": "Leopards Courier", "days": "2-4"},
      {"id": "mnp", "name": "M&P", "days": "2-4"},
    ],
    "chat_apps": [{"id": "whatsapp", "name": "WhatsApp"}],
  },

  "bd": {
    "id": "bd", "name_ar": "بنغلاديش", "name_en": "Bangladesh", "flag": "🇧🇩",
    "language": "bn", "direction": "ltr", "font": "Noto Sans Bengali",
    "currency": "BDT", "symbol": "৳", "number_format": "1,234.56",
    "tax": {"name_en": "VAT", "rate": 15},
    "payment_gateways": [
      {"id": "bkash", "name": "bKash", "type": "wallet", "popular": True},
      {"id": "nagad", "name": "Nagad", "type": "wallet", "popular": True},
      {"id": "rocket", "name": "Rocket (DBBL)", "type": "wallet"},
      {"id": "sslcommerz", "name": "SSLCommerz", "type": "gateway"},
      {"id": "cod", "name": "Cash on Delivery", "type": "cash", "popular": True},
    ],
    "shipping_carriers": [
      {"id": "pathao", "name": "Pathao Courier", "days": "1-2"},
      {"id": "redx", "name": "RedX", "days": "1-3"},
      {"id": "steadfast", "name": "Steadfast", "days": "1-2"},
    ],
    "chat_apps": [{"id": "whatsapp", "name": "WhatsApp"}, {"id": "messenger", "name": "Messenger"}],
  },

  "id": {
    "id": "id", "name_ar": "إندونيسيا", "name_en": "Indonesia", "flag": "🇮🇩",
    "language": "id", "direction": "ltr", "font": "Inter",
    "currency": "IDR", "symbol": "Rp", "number_format": "1.234,56",
    "tax": {"name_en": "PPN", "rate": 11},
    "payment_gateways": [
      {"id": "gopay", "name": "GoPay", "type": "wallet", "popular": True},
      {"id": "ovo", "name": "OVO", "type": "wallet", "popular": True},
      {"id": "dana", "name": "DANA", "type": "wallet"},
      {"id": "shopeepay", "name": "ShopeePay", "type": "wallet"},
      {"id": "linkaja", "name": "LinkAja", "type": "wallet"},
      {"id": "qris", "name": "QRIS", "type": "qr", "popular": True},
      {"id": "cod", "name": "Cash on Delivery", "type": "cash"},
    ],
    "shipping_carriers": [
      {"id": "jne", "name": "JNE", "days": "1-3", "popular": True},
      {"id": "jnt", "name": "J&T Express", "days": "1-3", "popular": True},
      {"id": "sicepat", "name": "SiCepat", "days": "1-2"},
      {"id": "gosend", "name": "GoSend", "days": "same-day"},
    ],
    "chat_apps": [{"id": "whatsapp", "name": "WhatsApp", "popular": True}, {"id": "line", "name": "LINE"}],
  },

  "my": {
    "id": "my", "name_ar": "ماليزيا", "name_en": "Malaysia", "flag": "🇲🇾",
    "language": "ms", "direction": "ltr", "font": "Inter",
    "currency": "MYR", "symbol": "RM", "number_format": "1,234.56",
    "tax": {"name_en": "SST", "rate": 8},
    "payment_gateways": [
      {"id": "grabpay", "name": "GrabPay", "type": "wallet", "popular": True},
      {"id": "touch_n_go", "name": "Touch 'n Go eWallet", "type": "wallet", "popular": True},
      {"id": "boost", "name": "Boost", "type": "wallet"},
      {"id": "shopeepay_my", "name": "ShopeePay", "type": "wallet"},
      {"id": "fpx", "name": "FPX (Online Banking)", "type": "transfer", "popular": True},
      {"id": "duitnow", "name": "DuitNow QR", "type": "qr"},
    ],
    "shipping_carriers": [
      {"id": "poslaju", "name": "Pos Laju", "days": "1-3"},
      {"id": "ninjavan", "name": "Ninja Van", "days": "1-3"},
      {"id": "jnt_my", "name": "J&T Express", "days": "1-3"},
    ],
    "chat_apps": [{"id": "whatsapp", "name": "WhatsApp", "popular": True}],
  },

  "th": {
    "id": "th", "name_ar": "تايلاند", "name_en": "Thailand", "flag": "🇹🇭",
    "language": "th", "direction": "ltr", "font": "Noto Sans Thai",
    "currency": "THB", "symbol": "฿", "number_format": "1,234.56",
    "tax": {"name_en": "VAT", "rate": 7},
    "payment_gateways": [
      {"id": "promptpay", "name": "PromptPay", "type": "qr", "popular": True, "tagline": "نظام الدفع التايلاندي الوطني"},
      {"id": "truemoney", "name": "TrueMoney Wallet", "type": "wallet"},
      {"id": "rabbit_linepay", "name": "Rabbit LINE Pay", "type": "wallet"},
      {"id": "scb_easy", "name": "SCB Easy", "type": "wallet"},
      {"id": "cod", "name": "Cash on Delivery", "type": "cash"},
    ],
    "shipping_carriers": [
      {"id": "kerry", "name": "Kerry Express", "days": "1-2", "popular": True},
      {"id": "flash_express", "name": "Flash Express", "days": "1-2"},
      {"id": "thailand_post", "name": "Thailand Post", "days": "2-4"},
    ],
    "chat_apps": [{"id": "line", "name": "LINE", "popular": True}, {"id": "whatsapp", "name": "WhatsApp"}],
  },

  "ph": {
    "id": "ph", "name_ar": "الفلبين", "name_en": "Philippines", "flag": "🇵🇭",
    "language": "fil", "direction": "ltr", "font": "Inter",
    "currency": "PHP", "symbol": "₱", "number_format": "1,234.56",
    "tax": {"name_en": "VAT", "rate": 12},
    "payment_gateways": [
      {"id": "gcash", "name": "GCash", "type": "wallet", "popular": True},
      {"id": "paymaya", "name": "Maya (PayMaya)", "type": "wallet", "popular": True},
      {"id": "grabpay_ph", "name": "GrabPay", "type": "wallet"},
      {"id": "instapay", "name": "InstaPay", "type": "transfer"},
      {"id": "cod", "name": "Cash on Delivery", "type": "cash", "popular": True},
    ],
    "shipping_carriers": [
      {"id": "lbc", "name": "LBC Express", "days": "1-3"},
      {"id": "jnt_ph", "name": "J&T Express", "days": "1-2"},
      {"id": "ninja_van_ph", "name": "Ninja Van", "days": "1-3"},
    ],
    "chat_apps": [{"id": "whatsapp", "name": "WhatsApp"}, {"id": "messenger", "name": "Messenger", "popular": True}],
  },

  "vn": {
    "id": "vn", "name_ar": "فيتنام", "name_en": "Vietnam", "flag": "🇻🇳",
    "language": "vi", "direction": "ltr", "font": "Inter",
    "currency": "VND", "symbol": "₫", "number_format": "1.234.567",
    "tax": {"name_en": "VAT", "rate": 10},
    "payment_gateways": [
      {"id": "momo", "name": "MoMo", "type": "wallet", "popular": True},
      {"id": "zalopay", "name": "ZaloPay", "type": "wallet", "popular": True},
      {"id": "vnpay", "name": "VNPAY-QR", "type": "qr"},
      {"id": "viettelpay", "name": "ViettelPay", "type": "wallet"},
      {"id": "cod", "name": "Cash on Delivery", "type": "cash", "popular": True},
    ],
    "shipping_carriers": [
      {"id": "ghn", "name": "GHN Express", "days": "1-3"},
      {"id": "ghtk", "name": "Giao Hang Tiet Kiem", "days": "2-4"},
      {"id": "vietnam_post", "name": "Vietnam Post", "days": "2-5"},
    ],
    "chat_apps": [{"id": "zalo", "name": "Zalo", "popular": True}, {"id": "messenger", "name": "Messenger"}],
  },

  # ═══════════════════════════════════════ AMERICAS ═══════════════════════════════════════
  "ca": {
    "id": "ca", "name_ar": "كندا", "name_en": "Canada", "flag": "🇨🇦",
    "language": "en", "direction": "ltr", "font": "Inter",
    "currency": "CAD", "symbol": "C$", "number_format": "1,234.56",
    "tax": {"name_en": "GST/HST/PST", "rate": "5-15", "note": "Province-dependent"},
    "payment_gateways": [
      {"id": "stripe_ca", "name": "Stripe", "type": "gateway"},
      {"id": "paypal", "name": "PayPal", "type": "wallet", "popular": True},
      {"id": "interac", "name": "Interac e-Transfer", "type": "transfer", "popular": True, "tagline": "نظام الدفع الكندي"},
      {"id": "apple_pay", "name": "Apple Pay", "type": "wallet"},
      {"id": "klarna", "name": "Klarna", "type": "bnpl"},
      {"id": "afterpay", "name": "Afterpay", "type": "bnpl"},
    ],
    "shipping_carriers": [
      {"id": "canada_post", "name": "Canada Post", "days": "2-7"},
      {"id": "purolator", "name": "Purolator", "days": "1-3"},
      {"id": "ups_ca", "name": "UPS Canada", "days": "1-3"},
    ],
    "chat_apps": [{"id": "imessage", "name": "iMessage"}, {"id": "whatsapp", "name": "WhatsApp"}],
  },

  "mx": {
    "id": "mx", "name_ar": "المكسيك", "name_en": "Mexico", "flag": "🇲🇽",
    "language": "es", "direction": "ltr", "font": "Inter",
    "currency": "MXN", "symbol": "$", "number_format": "1,234.56",
    "tax": {"name_en": "IVA", "rate": 16},
    "payment_gateways": [
      {"id": "mercado_pago", "name": "Mercado Pago", "type": "wallet", "popular": True},
      {"id": "oxxo", "name": "OXXO", "type": "cash", "popular": True, "tagline": "ادفع نقداً في 19,000+ متجر"},
      {"id": "spei", "name": "SPEI", "type": "transfer"},
      {"id": "kueski_pay", "name": "Kueski Pay", "type": "bnpl"},
      {"id": "paypal", "name": "PayPal", "type": "wallet"},
      {"id": "stripe_mx", "name": "Stripe", "type": "gateway"},
    ],
    "shipping_carriers": [
      {"id": "fedex_mx", "name": "FedEx Mexico", "days": "1-3"},
      {"id": "estafeta", "name": "Estafeta", "days": "1-3"},
      {"id": "dhl_mx", "name": "DHL Mexico", "days": "1-2"},
    ],
    "chat_apps": [{"id": "whatsapp", "name": "WhatsApp", "popular": True}, {"id": "messenger", "name": "Messenger"}],
  },

  "br": {
    "id": "br", "name_ar": "البرازيل", "name_en": "Brazil", "flag": "🇧🇷",
    "language": "pt", "direction": "ltr", "font": "Inter",
    "currency": "BRL", "symbol": "R$", "number_format": "1.234,56",
    "tax": {"name_en": "ICMS", "rate": "17-19", "note": "State-dependent"},
    "payment_gateways": [
      {"id": "pix", "name": "PIX", "type": "qr", "popular": True, "tagline": "تحويل فوري برازيلي - مجاني"},
      {"id": "boleto", "name": "Boleto Bancário", "type": "cash", "popular": True},
      {"id": "mercado_pago_br", "name": "Mercado Pago", "type": "wallet"},
      {"id": "pagseguro", "name": "PagSeguro", "type": "gateway"},
      {"id": "picpay", "name": "PicPay", "type": "wallet"},
      {"id": "stripe_br", "name": "Stripe", "type": "gateway"},
    ],
    "shipping_carriers": [
      {"id": "correios", "name": "Correios", "days": "3-10", "popular": True},
      {"id": "jadlog", "name": "Jadlog", "days": "1-3"},
      {"id": "mercado_envios", "name": "Mercado Envios", "days": "1-5"},
    ],
    "chat_apps": [{"id": "whatsapp", "name": "WhatsApp", "popular": True}, {"id": "telegram", "name": "Telegram"}],
  },

  "ar": {
    "id": "ar", "name_ar": "الأرجنتين", "name_en": "Argentina", "flag": "🇦🇷",
    "language": "es", "direction": "ltr", "font": "Inter",
    "currency": "ARS", "symbol": "$", "number_format": "1.234,56",
    "tax": {"name_en": "IVA", "rate": 21},
    "payment_gateways": [
      {"id": "mercado_pago_ar", "name": "Mercado Pago", "type": "wallet", "popular": True},
      {"id": "rapipago", "name": "Rapipago", "type": "cash"},
      {"id": "pago_facil", "name": "Pago Fácil", "type": "cash"},
      {"id": "modo", "name": "MODO", "type": "wallet"},
    ],
    "shipping_carriers": [
      {"id": "correo_argentino", "name": "Correo Argentino", "days": "3-7"},
      {"id": "andreani", "name": "Andreani", "days": "1-3"},
      {"id": "oca", "name": "OCA", "days": "1-3"},
    ],
    "chat_apps": [{"id": "whatsapp", "name": "WhatsApp", "popular": True}],
  },

  # ═══════════════════════════════════════ AFRICA ═══════════════════════════════════════
  "za": {
    "id": "za", "name_ar": "جنوب أفريقيا", "name_en": "South Africa", "flag": "🇿🇦",
    "language": "en", "direction": "ltr", "font": "Inter",
    "currency": "ZAR", "symbol": "R", "number_format": "1,234.56",
    "tax": {"name_en": "VAT", "rate": 15},
    "payment_gateways": [
      {"id": "payfast", "name": "PayFast", "type": "gateway", "popular": True},
      {"id": "yoco", "name": "Yoco", "type": "gateway"},
      {"id": "snapscan", "name": "SnapScan", "type": "qr"},
      {"id": "zapper", "name": "Zapper", "type": "qr"},
      {"id": "ozow", "name": "Ozow", "type": "transfer"},
      {"id": "paypal", "name": "PayPal", "type": "wallet"},
    ],
    "shipping_carriers": [
      {"id": "courier_guy", "name": "The Courier Guy", "days": "1-3"},
      {"id": "ram", "name": "RAM Couriers", "days": "1-2"},
      {"id": "sa_post", "name": "SA Post Office", "days": "3-7"},
    ],
    "chat_apps": [{"id": "whatsapp", "name": "WhatsApp", "popular": True}],
  },

  "ng": {
    "id": "ng", "name_ar": "نيجيريا", "name_en": "Nigeria", "flag": "🇳🇬",
    "language": "en", "direction": "ltr", "font": "Inter",
    "currency": "NGN", "symbol": "₦", "number_format": "1,234.56",
    "tax": {"name_en": "VAT", "rate": 7.5},
    "payment_gateways": [
      {"id": "paystack", "name": "Paystack", "type": "gateway", "popular": True},
      {"id": "flutterwave", "name": "Flutterwave", "type": "gateway", "popular": True},
      {"id": "opay", "name": "OPay", "type": "wallet"},
      {"id": "palmpay", "name": "PalmPay", "type": "wallet"},
      {"id": "interswitch", "name": "Interswitch", "type": "gateway"},
    ],
    "shipping_carriers": [
      {"id": "gig_logistics", "name": "GIG Logistics", "days": "1-3"},
      {"id": "nipost", "name": "NIPOST", "days": "3-7"},
      {"id": "kwik", "name": "Kwik Delivery", "days": "same-day"},
    ],
    "chat_apps": [{"id": "whatsapp", "name": "WhatsApp", "popular": True}],
  },

  "ke": {
    "id": "ke", "name_ar": "كينيا", "name_en": "Kenya", "flag": "🇰🇪",
    "language": "en", "direction": "ltr", "font": "Inter",
    "currency": "KES", "symbol": "KSh", "number_format": "1,234.56",
    "tax": {"name_en": "VAT", "rate": 16},
    "payment_gateways": [
      {"id": "mpesa", "name": "M-Pesa", "type": "wallet", "popular": True, "tagline": "الأشهر في أفريقيا"},
      {"id": "airtel_money", "name": "Airtel Money", "type": "wallet"},
      {"id": "flutterwave_ke", "name": "Flutterwave", "type": "gateway"},
      {"id": "pesapal", "name": "Pesapal", "type": "gateway"},
    ],
    "shipping_carriers": [
      {"id": "sendy", "name": "Sendy", "days": "same-day"},
      {"id": "g4s_ke", "name": "G4S Kenya", "days": "1-3"},
      {"id": "kenya_post", "name": "Posta Kenya", "days": "3-7"},
    ],
    "chat_apps": [{"id": "whatsapp", "name": "WhatsApp", "popular": True}],
  },

  # ═══════════════════════════════════════ OCEANIA ═══════════════════════════════════════
  "au": {
    "id": "au", "name_ar": "أستراليا", "name_en": "Australia", "flag": "🇦🇺",
    "language": "en", "direction": "ltr", "font": "Inter",
    "currency": "AUD", "symbol": "A$", "number_format": "1,234.56",
    "tax": {"name_en": "GST", "rate": 10},
    "payment_gateways": [
      {"id": "stripe_au", "name": "Stripe", "type": "gateway", "popular": True},
      {"id": "afterpay_au", "name": "Afterpay", "type": "bnpl", "popular": True, "tagline": "صناعة أسترالية"},
      {"id": "zip", "name": "Zip", "type": "bnpl"},
      {"id": "paypal", "name": "PayPal", "type": "wallet"},
      {"id": "apple_pay", "name": "Apple Pay", "type": "wallet"},
      {"id": "bpay", "name": "BPAY", "type": "transfer"},
      {"id": "payid", "name": "PayID", "type": "transfer"},
    ],
    "shipping_carriers": [
      {"id": "auspost", "name": "Australia Post", "days": "1-5"},
      {"id": "startrack", "name": "StarTrack", "days": "1-3"},
      {"id": "couriers_please", "name": "Couriers Please", "days": "1-3"},
    ],
    "chat_apps": [{"id": "whatsapp", "name": "WhatsApp"}, {"id": "imessage", "name": "iMessage"}],
  },

  "tr": {
    "id": "tr", "name_ar": "تركيا", "name_en": "Turkey", "flag": "🇹🇷",
    "language": "tr", "direction": "ltr", "font": "Inter",
    "currency": "TRY", "symbol": "₺", "number_format": "1.234,56",
    "tax": {"name_en": "KDV", "rate": 20},
    "payment_gateways": [
      {"id": "iyzico", "name": "iyzico", "type": "gateway", "popular": True},
      {"id": "paytr", "name": "PayTR", "type": "gateway"},
      {"id": "papara", "name": "Papara", "type": "wallet", "popular": True},
      {"id": "ininal", "name": "ininal", "type": "wallet"},
      {"id": "bkm_express", "name": "BKM Express", "type": "wallet"},
      {"id": "stripe_tr", "name": "Stripe", "type": "gateway"},
    ],
    "shipping_carriers": [
      {"id": "yurtici", "name": "Yurtiçi Kargo", "days": "1-2", "popular": True},
      {"id": "mng", "name": "MNG Kargo", "days": "1-2"},
      {"id": "ptt", "name": "PTT Kargo", "days": "2-4"},
      {"id": "aras", "name": "Aras Kargo", "days": "1-3"},
    ],
    "chat_apps": [{"id": "whatsapp", "name": "WhatsApp", "popular": True}],
  },
}
# fmt: on


def get_market(market_id: str) -> Dict[str, Any] | None:
    """Get a single market pack by ID. Always includes English as a fallback language."""
    pack = MARKET_PACKS.get(market_id.lower())
    if pack:
        # Inject "supported_languages" — local + English fallback (always available).
        local_lang = pack.get("language", "en")
        supported = [local_lang]
        if local_lang != "en":
            supported.append("en")
        # Return a copy with supported_languages added (without mutating the source)
        return {**pack, "supported_languages": supported}
    return None


def list_markets() -> List[Dict[str, Any]]:
    """Return a lightweight list of all markets (for wizard selection)."""
    return [
        {
            "id": m["id"],
            "name_ar": m["name_ar"],
            "name_en": m["name_en"],
            "flag": m["flag"],
            "currency": m["currency"],
            "language": m["language"],
            "payment_methods_count": len(m["payment_gateways"]),
            "shipping_carriers_count": len(m["shipping_carriers"]),
        }
        for m in MARKET_PACKS.values()
    ]


def detect_market_from_country_code(country_code: str) -> str:
    """Fallback to 'sa' if country not supported."""
    cc = (country_code or "").lower()
    return cc if cc in MARKET_PACKS else "sa"
