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
}
# fmt: on


def get_market(market_id: str) -> Dict[str, Any] | None:
    """Get a single market pack by ID."""
    return MARKET_PACKS.get(market_id.lower())


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
