"""
Gateway enrichment — adds real-world merchant URLs, credentials specs,
fee breakdowns and AI-helper hints to every gateway in the catalog.

This is loaded by gateways_router.py and merged on top of the base catalog
at response time, so the source catalog stays clean and this stays separately
maintainable as providers change their portals.
"""

# Universal gateways that should appear in EVERY country alongside local ones
UNIVERSAL_IDS = {"stripe_card", "paypal", "apple_pay", "google_pay", "cod", "bank_transfer", "crypto_usdc"}


# Per-gateway enrichment: real URLs, real fees, required credentials
ENRICHMENT = {
    "tabby": {
        "merchant_signup_url":  "https://merchants.tabby.ai/signup",
        "merchant_dashboard_url":"https://merchants.tabby.ai",
        "developer_docs_url":   "https://docs.tabby.ai",
        "real_fees": {"customer": "0% (interest-free)", "merchant": "5-7% + 1 SAR per transaction", "settlement_days": 1},
        "required_credentials": [
            {"name": "public_key",  "label_ar": "المفتاح العام (Public Key)",   "type": "text",     "where_ar": "لوحة Tabby → Settings → API → Public Key (pk_test_... / pk_live_...)"},
            {"name": "secret_key",  "label_ar": "المفتاح السري (Secret Key)",   "type": "password", "where_ar": "لوحة Tabby → Settings → API → Secret Key (sk_test_... / sk_live_...)"},
            {"name": "merchant_code","label_ar": "كود المتجر (Merchant Code)",   "type": "text",     "where_ar": "ستجده في صفحة Settings → Stores"},
        ],
        "ai_helper_ar": "تابي يحتاج موافقة تجارية أولاً (3-5 أيام). سجّل بسجلك التجاري، ضع رابط متجرك، واستخرج المفاتيح من لوحة التحكم بعد الموافقة. للمتاجر الجديدة جرّب الـ Sandbox أولاً.",
    },
    "tamara": {
        "merchant_signup_url":  "https://partners.tamara.co/en/signup",
        "merchant_dashboard_url":"https://partners.tamara.co",
        "developer_docs_url":   "https://docs.tamara.co",
        "real_fees": {"customer": "0% (Pay in 3) or fees on longer plans", "merchant": "3.5-7% + flat fee", "settlement_days": 1},
        "required_credentials": [
            {"name": "merchant_id", "label_ar": "Merchant ID",        "type": "text",     "where_ar": "Tamara Partner Portal → Integration → Merchant ID"},
            {"name": "public_key",  "label_ar": "Merchant Public Key","type": "text",     "where_ar": "Partner Portal → Integration → Public Key"},
            {"name": "api_token",   "label_ar": "API Token",          "type": "password", "where_ar": "Partner Portal → Integration → Generate API Token"},
            {"name": "notification_token","label_ar":"Notification Token","type":"password","where_ar":"Partner Portal → Webhooks"},
        ],
        "ai_helper_ar": "تمارا مرخّصة من ساما. تحتاج سجل تجاري + موقع نشط + ضريبي. بعد الموافقة، فعّل OTP في بوابة الشركاء وحط رابط الـ webhook.",
    },
    "mada": {
        "merchant_signup_url":  "https://www.mada.com.sa/businesses",
        "merchant_dashboard_url":"—",
        "developer_docs_url":   "https://www.mada.com.sa/developers",
        "real_fees": {"customer": "free", "merchant": "~1% per transaction (varies by PSP)", "settlement_days": 1},
        "required_credentials": [
            {"name": "psp_provider", "label_ar": "اختر PSP", "type": "select", "options": ["HyperPay","PayTabs","Checkout.com","Moyasar","Geidea"], "where_ar": "تحتاج PSP وسيط (مثل Moyasar أو PayTabs) لقبول مدى"},
            {"name": "psp_merchant_id","label_ar":"Merchant ID من الـ PSP","type":"text","where_ar":"حسب الـ PSP المختار"},
            {"name": "psp_api_key",    "label_ar":"API Key من الـ PSP",    "type":"password","where_ar":"حسب الـ PSP المختار"},
        ],
        "ai_helper_ar": "مدى ما تتكامل مباشرة — لازم تمر عبر PSP مرخّص. Moyasar و PayTabs الأسرع. التسوية في 24 ساعة.",
    },
    "stc_pay_checkout": {
        "merchant_signup_url":  "https://stcpay.com.sa/business",
        "merchant_dashboard_url":"https://merchant.stcpay.com.sa",
        "developer_docs_url":   "https://developers.stcpay.com.sa",
        "real_fees": {"customer": "free", "merchant": "1.5% (varies)", "settlement_days": 1},
        "required_credentials": [
            {"name": "merchant_number","label_ar":"رقم التاجر STC Pay","type":"text","where_ar":"بوابة التاجر STC Pay → Settings"},
            {"name": "api_key",        "label_ar":"API Key",             "type":"password","where_ar":"بوابة التاجر → Developers → API Keys"},
        ],
        "ai_helper_ar": "STC Pay يحتاج هوية تجارية + حساب بنك سعودي. التكامل عبر API مباشر، التسوية يومية.",
    },
    "urpay": {
        "merchant_signup_url": "https://urpay.com.sa/business",
        "merchant_dashboard_url":"https://merchant.urpay.com.sa",
        "developer_docs_url": "https://urpay.com.sa/developers",
        "real_fees": {"customer":"free","merchant":"~1.5%","settlement_days":1},
        "required_credentials":[
            {"name":"api_key","label_ar":"API Key","type":"password","where_ar":"بوابة urpay التاجر"},
            {"name":"merchant_id","label_ar":"Merchant ID","type":"text","where_ar":"الصفحة الرئيسية للوحة urpay"}
        ],
        "ai_helper_ar":"urpay من البنك الأهلي السعودي. مناسب للمتاجر داخل السعودية فقط.",
    },
    "spotii": {
        "merchant_signup_url":"https://www.spotii.com/merchants",
        "merchant_dashboard_url":"https://portal.spotii.com",
        "developer_docs_url":"https://developer.spotii.com",
        "real_fees":{"customer":"0%","merchant":"4-6%","settlement_days":2},
        "required_credentials":[
            {"name":"merchant_id","label_ar":"Merchant ID","type":"text","where_ar":"Spotii Portal → Integration"},
            {"name":"secret_key","label_ar":"Secret Key","type":"password","where_ar":"Spotii Portal → Integration → Keys"}
        ],
        "ai_helper_ar":"Spotii صارت تابعة لـ Zip Co الأسترالية. يدعمون السعودية والإمارات بـ 4 دفعات.",
    },
    "fawry": {
        "merchant_signup_url":"https://www.fawrybusiness.com/signup",
        "merchant_dashboard_url":"https://atfawry.com/atfawry",
        "developer_docs_url":"https://developer.fawrystaging.com",
        "real_fees":{"customer":"~2-5 EGP","merchant":"2-3% + 1 EGP","settlement_days":2},
        "required_credentials":[
            {"name":"merchant_code","label_ar":"Merchant Code","type":"text","where_ar":"Fawry Business Portal"},
            {"name":"secure_key","label_ar":"Secure Key","type":"password","where_ar":"Fawry Business → Integration"}
        ],
        "ai_helper_ar":"فوري الأشهر في مصر — يقبل دفع نقدي عبر منافذ + إلكتروني. مهم للوصول لشريحة بدون بطاقات.",
    },
    "instapay_eg": {
        "merchant_signup_url":"https://instapay.eg",
        "merchant_dashboard_url":"https://instapay.eg",
        "developer_docs_url":"https://instapay.eg/developers",
        "real_fees":{"customer":"free <70k EGP","merchant":"free for receiving","settlement_days":0},
        "required_credentials":[
            {"name":"ipa","label_ar":"IPA (Instant Payment Address)","type":"text","where_ar":"تطبيق InstaPay → Profile"}
        ],
        "ai_helper_ar":"InstaPay مجاني للأفراد. ربطه بسيط جداً — فقط IPA. مدعوم من البنك المركزي المصري.",
    },
    "valu": {
        "merchant_signup_url":"https://valu.com.eg/merchants",
        "merchant_dashboard_url":"https://merchants.valu.com.eg",
        "developer_docs_url":"https://developer.valu.com.eg",
        "real_fees":{"customer":"0-25% (حسب فترة التقسيط)","merchant":"variable, often subsidized","settlement_days":3},
        "required_credentials":[
            {"name":"merchant_id","label_ar":"Merchant ID","type":"text","where_ar":"valU Portal"},
            {"name":"api_key","label_ar":"API Key","type":"password","where_ar":"valU Portal → Integration"}
        ],
        "ai_helper_ar":"valU من EFG Hermes — أقساط تصل 60 شهر. يحتاج KYC كامل للعميل.",
    },
    "klarna": {
        "merchant_signup_url":"https://www.klarna.com/business/sign-up",
        "merchant_dashboard_url":"https://merchants.klarna.com",
        "developer_docs_url":"https://docs.klarna.com",
        "real_fees":{"customer":"0% (Pay in 4)","merchant":"~3.29-5.99% + $0.30 per transaction","settlement_days":1},
        "required_credentials":[
            {"name":"username","label_ar":"Klarna Username","type":"text","where_ar":"Klarna Merchant Portal → Settings → API Credentials"},
            {"name":"password","label_ar":"Klarna Password","type":"password","where_ar":"Klarna Merchant Portal → Settings → API Credentials"}
        ],
        "ai_helper_ar":"Klarna الأقوى في أوروبا وأمريكا. لازم Stripe Connect عند ربطه على متاجر صغيرة. يدعم 4 دفعات + شهر + تمويل طويل.",
    },
    "afterpay": {
        "merchant_signup_url":"https://www.afterpay.com/en-US/business/signup",
        "merchant_dashboard_url":"https://merchant.afterpay.com",
        "developer_docs_url":"https://developers.afterpay.com",
        "real_fees":{"customer":"0%","merchant":"4-6% + $0.30","settlement_days":1},
        "required_credentials":[
            {"name":"merchant_id","label_ar":"Merchant ID","type":"text","where_ar":"Afterpay Merchant Portal"},
            {"name":"secret_key","label_ar":"Secret Key","type":"password","where_ar":"Afterpay Merchant Portal → API"}
        ],
        "ai_helper_ar":"Afterpay (= Clearpay في بريطانيا) من Block (Square). الأكثر شيوعاً عند جيل Z في US/AU.",
    },
    "affirm": {
        "merchant_signup_url":"https://www.affirm.com/business",
        "merchant_dashboard_url":"https://merchants.affirm.com",
        "developer_docs_url":"https://docs.affirm.com",
        "real_fees":{"customer":"0-36% APR (حسب الخطة)","merchant":"5.99% APR borne by customer + fees","settlement_days":2},
        "required_credentials":[
            {"name":"public_api_key","label_ar":"Public API Key","type":"text","where_ar":"Affirm Merchant Portal → Settings"},
            {"name":"private_api_key","label_ar":"Private API Key","type":"password","where_ar":"Affirm Merchant Portal → Settings"}
        ],
        "ai_helper_ar":"Affirm مناسب للسلع الغالية (تمويل طويل). يحتاج soft credit check للعميل + APR disclosure مرئي.",
    },
    "paypal": {
        "merchant_signup_url":"https://www.paypal.com/us/business/open-business-account",
        "merchant_dashboard_url":"https://www.paypal.com/businessprofile",
        "developer_docs_url":"https://developer.paypal.com",
        "real_fees":{"customer":"free","merchant":"3.49% + $0.49 per transaction (US)","settlement_days":1},
        "required_credentials":[
            {"name":"client_id","label_ar":"Client ID","type":"text","where_ar":"PayPal Developer → My Apps & Credentials → Live"},
            {"name":"client_secret","label_ar":"Client Secret","type":"password","where_ar":"PayPal Developer → My Apps & Credentials → Live"}
        ],
        "ai_helper_ar":"PayPal الأكثر انتشاراً عالمياً. سهل في التكامل، رسوم أعلى من Stripe. مهم لو تبيع لأمريكا/أوروبا.",
    },
    "stripe_card": {
        "merchant_signup_url":"https://dashboard.stripe.com/register",
        "merchant_dashboard_url":"https://dashboard.stripe.com",
        "developer_docs_url":"https://stripe.com/docs",
        "real_fees":{"customer":"free","merchant":"2.9% + $0.30 (US), 1.4% + £0.20 (EU)","settlement_days":2},
        "required_credentials":[
            {"name":"publishable_key","label_ar":"Publishable Key","type":"text","where_ar":"Stripe Dashboard → Developers → API keys (pk_live_...)"},
            {"name":"secret_key","label_ar":"Secret Key","type":"password","where_ar":"Stripe Dashboard → Developers → API keys (sk_live_...)"},
            {"name":"webhook_secret","label_ar":"Webhook Signing Secret","type":"password","where_ar":"Stripe Dashboard → Webhooks → Your endpoint → Signing secret"}
        ],
        "ai_helper_ar":"Stripe الأقوى عالمياً. تكامل ممتاز، يدعم Klarna/Afterpay/Affirm كـ payment methods داخله. مطلوب للأسواق الغربية.",
    },
    "apple_pay": {
        "merchant_signup_url":"https://developer.apple.com/apple-pay/get-started/",
        "merchant_dashboard_url":"https://developer.apple.com/account",
        "developer_docs_url":"https://developer.apple.com/documentation/apple_pay_on_the_web",
        "real_fees":{"customer":"free","merchant":"PSP fee only (Stripe/Adyen)","settlement_days":2},
        "required_credentials":[
            {"name":"merchant_identifier","label_ar":"Apple Merchant ID","type":"text","where_ar":"Apple Developer Account → Certificates → Merchant IDs"},
            {"name":"domain_verification","label_ar":"Domain Verification File","type":"file","where_ar":"Apple يعطيك ملف ترفعه على /.well-known/ لتأكيد ملكية الدومين"}
        ],
        "ai_helper_ar":"Apple Pay يحتاج حساب Apple Developer ($99/سنة) + شهادة + توثيق دومين. التكامل الفعلي عبر Stripe أو PSP آخر.",
    },
    "google_pay": {
        "merchant_signup_url":"https://pay.google.com/business",
        "merchant_dashboard_url":"https://pay.google.com/business",
        "developer_docs_url":"https://developers.google.com/pay/api/web",
        "real_fees":{"customer":"free","merchant":"PSP fee only","settlement_days":2},
        "required_credentials":[
            {"name":"merchant_id","label_ar":"Google Pay Merchant ID","type":"text","where_ar":"Google Pay & Wallet Console"},
            {"name":"gateway","label_ar":"Underlying gateway","type":"select","options":["stripe","adyen","braintree","checkout.com"],"where_ar":"اختر الـ PSP اللي يعالج الدفع فعلياً"}
        ],
        "ai_helper_ar":"Google Pay مجاني للتكامل، لكن يحتاج PSP خلفه (مثل Stripe). يظهر تلقائياً لأجهزة Android.",
    },
    "alipay": {
        "merchant_signup_url":"https://global.alipay.com/platform/site/ihome",
        "merchant_dashboard_url":"https://b.alipay.com",
        "developer_docs_url":"https://global.alipay.com/docs",
        "real_fees":{"customer":"free","merchant":"1.2-1.4% cross-border","settlement_days":2},
        "required_credentials":[
            {"name":"partner_id","label_ar":"Partner ID (PID)","type":"text","where_ar":"Alipay Global Merchant Portal"},
            {"name":"private_key","label_ar":"Private Key (RSA)","type":"password","where_ar":"تولّده محلياً وتسجّل العام في Alipay Portal"},
            {"name":"alipay_public_key","label_ar":"Alipay Public Key","type":"text","where_ar":"Alipay Global Portal بعد رفع مفتاحك العام"}
        ],
        "ai_helper_ar":"Alipay للسوق الصيني — لازم PSP cross-border مرخّص (مثل Adyen/Stripe China/Silkpay). يستخدم QR scan.",
    },
    "wechat_pay": {
        "merchant_signup_url":"https://pay.weixin.qq.com",
        "merchant_dashboard_url":"https://pay.weixin.qq.com",
        "developer_docs_url":"https://pay.weixin.qq.com/docs/global",
        "real_fees":{"customer":"free","merchant":"1.2% cross-border","settlement_days":2},
        "required_credentials":[
            {"name":"mch_id","label_ar":"Merchant ID (mch_id)","type":"text","where_ar":"WeChat Pay Merchant Platform"},
            {"name":"api_key","label_ar":"API V3 Key","type":"password","where_ar":"WeChat Pay Merchant Platform → Account Center → API Security"},
            {"name":"cert_file","label_ar":"Merchant Certificate","type":"file","where_ar":"تنزل من Merchant Platform"}
        ],
        "ai_helper_ar":"WeChat Pay الأكثر استخداماً في الصين. cross-border يحتاج PSP. التكامل عبر QR أو In-App.",
    },
    "unionpay": {
        "merchant_signup_url":"https://www.unionpayintl.com/en/merchant/",
        "merchant_dashboard_url":"https://merchant.unionpayintl.com",
        "developer_docs_url":"https://developer.unionpayintl.com",
        "real_fees":{"customer":"free","merchant":"~1.4-2%","settlement_days":2},
        "required_credentials":[
            {"name":"merchant_id","label_ar":"UnionPay Merchant ID","type":"text","where_ar":"UnionPay International Merchant Portal"},
            {"name":"terminal_id","label_ar":"Terminal ID","type":"text","where_ar":"UnionPay Merchant Portal"},
            {"name":"signing_cert","label_ar":"Signing Certificate","type":"file","where_ar":"UnionPay Portal → Security → Certs"}
        ],
        "ai_helper_ar":"UnionPay = بطاقات الصين. للقبول cross-border لازم PSP محلي صيني أو Stripe Asia.",
    },
    "clearpay": {
        "merchant_signup_url":"https://www.clearpay.co.uk/en-GB/business/sign-up",
        "merchant_dashboard_url":"https://portal.clearpay.co.uk",
        "developer_docs_url":"https://developers.clearpay.co.uk",
        "real_fees":{"customer":"0% if on-time","merchant":"~4-6%","settlement_days":1},
        "required_credentials":[
            {"name":"merchant_id","label_ar":"Merchant ID","type":"text","where_ar":"Clearpay Merchant Portal"},
            {"name":"secret_key","label_ar":"Secret Key","type":"password","where_ar":"Clearpay Merchant Portal → API"}
        ],
        "ai_helper_ar":"Clearpay هو نفس Afterpay لكن للسوق البريطاني/الأوروبي. نفس الـ API تقريباً.",
    },
    "sepa": {
        "merchant_signup_url":"https://stripe.com/docs/payments/sepa-debit",
        "merchant_dashboard_url":"—",
        "developer_docs_url":"https://stripe.com/docs/payments/sepa-debit",
        "real_fees":{"customer":"free","merchant":"0.8% (capped at €5)","settlement_days":5},
        "required_credentials":[
            {"name":"stripe_account","label_ar":"Stripe Account (للتفعيل)","type":"text","where_ar":"تحتاج حساب Stripe أوروبي + IBAN"}
        ],
        "ai_helper_ar":"SEPA Direct Debit عبر Stripe — مناسب لأوروبا. التسوية أبطأ (5 أيام) لكن الرسوم منخفضة.",
    },
    "sofort": {
        "merchant_signup_url":"https://www.klarna.com/sofort/",
        "merchant_dashboard_url":"https://merchants.klarna.com",
        "developer_docs_url":"https://docs.klarna.com/sofort/",
        "real_fees":{"customer":"free","merchant":"0.9% + €0.29","settlement_days":2},
        "required_credentials":[{"name":"klarna_account","label_ar":"Klarna Merchant Account","type":"text","where_ar":"يندمج تلقائياً مع حساب Klarna"}],
        "ai_helper_ar":"Sofort تابعة لـ Klarna الآن. شائعة في ألمانيا/النمسا. تحويل بنكي فوري.",
    },
    "ideal": {
        "merchant_signup_url":"https://www.ideal.nl/en/businesses/",
        "merchant_dashboard_url":"—",
        "developer_docs_url":"https://stripe.com/docs/payments/ideal",
        "real_fees":{"customer":"free","merchant":"€0.29 per tx","settlement_days":2},
        "required_credentials":[{"name":"stripe_account","label_ar":"Stripe Account","type":"text","where_ar":"يفعّل تلقائياً من حساب Stripe الهولندي"}],
        "ai_helper_ar":"iDEAL = هولندا فقط. 70% من المدفوعات الأونلاين الهولندية تمر منه. لازم تفعّله للسوق الهولندي.",
    },
    "upi": {
        "merchant_signup_url":"https://www.npci.org.in/what-we-do/upi/onboarding",
        "merchant_dashboard_url":"—",
        "developer_docs_url":"https://www.npci.org.in/what-we-do/upi/product-overview",
        "real_fees":{"customer":"free","merchant":"free <₹2000 / 0.3-1% above","settlement_days":1},
        "required_credentials":[
            {"name":"upi_id","label_ar":"UPI Virtual ID (VPA)","type":"text","where_ar":"من بنكك الهندي أو PSP (Razorpay/Cashfree)"},
            {"name":"psp_key","label_ar":"PSP API Key","type":"password","where_ar":"حسب الـ PSP المختار"}
        ],
        "ai_helper_ar":"UPI الأسرع في الهند (مجاني للأفراد). يحتاج PSP مرخّص مثل Razorpay أو Cashfree للتجار.",
    },
    "grabpay": {
        "merchant_signup_url":"https://www.grab.com/sg/merchant/",
        "merchant_dashboard_url":"https://merchant.grab.com",
        "developer_docs_url":"https://developer.grab.com/online/grabpay",
        "real_fees":{"customer":"free","merchant":"~1.5%","settlement_days":2},
        "required_credentials":[
            {"name":"partner_id","label_ar":"Partner ID","type":"text","where_ar":"GrabPay Merchant Portal"},
            {"name":"partner_secret","label_ar":"Partner Secret","type":"password","where_ar":"GrabPay Merchant Portal → API"}
        ],
        "ai_helper_ar":"GrabPay يدعم 6 دول بجنوب شرق آسيا. الأكثر شيوعاً في سنغافورة وماليزيا.",
    },
    "cod": {
        "merchant_signup_url":"#enable-cod",
        "merchant_dashboard_url":"#enable-cod",
        "developer_docs_url":"#",
        "real_fees":{"customer":"free","merchant":"0% (لكن مخاطر رفض الاستلام ~10-15%)","settlement_days":0},
        "required_credentials":[],
        "ai_helper_ar":"الدفع عند الاستلام ضروري في المنطقة العربية (يمثل 40-60% من الطلبات). فعّله مع حد أعلى.",
    },
    "bank_transfer": {
        "merchant_signup_url":"#manual",
        "merchant_dashboard_url":"#manual",
        "developer_docs_url":"#",
        "real_fees":{"customer":"حسب البنك","merchant":"0%","settlement_days":3},
        "required_credentials":[
            {"name":"iban","label_ar":"IBAN رقم الحساب","type":"text","where_ar":"من حسابك البنكي"},
            {"name":"bank_name","label_ar":"اسم البنك","type":"text","where_ar":"—"},
            {"name":"account_holder","label_ar":"اسم صاحب الحساب","type":"text","where_ar":"—"}
        ],
        "ai_helper_ar":"تحويل بنكي يدوي للقيم الكبيرة. تأكيد يدوي مطلوب من التاجر. مناسب B2B.",
    },
    "crypto_usdc": {
        "merchant_signup_url":"https://commerce.coinbase.com/signup",
        "merchant_dashboard_url":"https://commerce.coinbase.com",
        "developer_docs_url":"https://docs.cloud.coinbase.com/commerce/docs",
        "real_fees":{"customer":"network gas fee","merchant":"1% (Coinbase Commerce)","settlement_days":0},
        "required_credentials":[
            {"name":"api_key","label_ar":"Coinbase Commerce API Key","type":"password","where_ar":"Coinbase Commerce → Settings → API Keys"},
            {"name":"webhook_secret","label_ar":"Webhook Shared Secret","type":"password","where_ar":"Coinbase Commerce → Settings → Webhooks"}
        ],
        "ai_helper_ar":"USDC stablecoin مربوط بالدولار. تسوية فورية بدون بنوك. مناسب للعملاء الدوليين.",
    },
}


def enrich(gateway: dict) -> dict:
    """Merge enrichment data into a gateway dict (non-destructive)."""
    extra = ENRICHMENT.get(gateway["id"], {})
    out = {**gateway, **extra, "is_universal": gateway["id"] in UNIVERSAL_IDS}
    # Always provide a help link
    out.setdefault("ai_helper_ar", f"بوابة {gateway['name_ar']} — راجع الموقع الرسمي للمتطلبات الكاملة.")
    out.setdefault("required_credentials", [])
    out.setdefault("real_fees", {"customer":"—","merchant":gateway.get("fees_hint","—"),"settlement_days":1})
    return out
