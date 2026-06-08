"""Ready Sites — Python Data Factory.

Generates ALL the seed data (categories, products, orders, customers, drivers,
analytics, reviews) deterministically in Python, then injects it into the AI brief.

This frees the AI from having to produce ~40KB of JSON inside its 16K-token output
budget, so it can focus entirely on the UI shell. Result: every generated site
ALWAYS has 60+ products, 30 orders, 20 customers, 5 drivers — guaranteed.

The same factory pattern will be reused for car-dealerships, clinics, real-estate.
"""
from __future__ import annotations
import random
import json
from typing import Any, Dict, List

# ──────────────── Saudi cultural data ────────────────

SAUDI_FIRST_NAMES = [
    "محمد", "أحمد", "عبدالله", "فيصل", "سلطان", "خالد", "سعد", "ناصر", "بدر",
    "تركي", "ماجد", "نواف", "وليد", "زياد", "عمر", "ياسر", "هشام", "إبراهيم",
    "سارة", "نورة", "ريم", "هند", "لمى", "غادة", "أمل", "ليان", "رنا", "دانة"
]
SAUDI_FAMILIES = [
    "العتيبي", "السبيعي", "القحطاني", "الشمري", "الدوسري", "العنزي", "الزهراني",
    "المالكي", "الغامدي", "العمري", "الحربي", "الرشيدي", "البلوي", "العميري",
    "السهلي", "الصاعدي", "الفهد", "العسيري", "النفيعي", "اليامي"
]
SAUDI_CITIES = [
    {"city": "الرياض", "districts": ["حي العليا", "حي النخيل", "حي الملقا", "حي الغدير", "حي الياسمين", "حي الورود"]},
    {"city": "جدة", "districts": ["حي الزهراء", "حي الشاطئ", "حي الروضة", "حي السلامة", "حي الفيصلية"]},
    {"city": "الدمام", "districts": ["حي الفيصلية", "حي النور", "حي الجلوية", "حي الشاطئ"]},
    {"city": "مكة", "districts": ["حي العزيزية", "حي العوالي", "حي الششة"]},
    {"city": "المدينة", "districts": ["حي قباء", "حي العوالي", "حي الجامعة"]},
]

# ──────────────── Restaurant data ────────────────

RESTAURANT_CATEGORIES = [
    {"id": "pizza", "name": "البيتزا", "desc": "أفضل أنواع البيتزا الإيطالية الأصيلة",
     "img": "photo-1565299624946-b28f40a0ae38"},
    {"id": "burger", "name": "البرجر", "desc": "برجر طازج بأشهى الأنواع",
     "img": "photo-1551782450-a2132b4ba21d"},
    {"id": "broast", "name": "بروست", "desc": "بروست مقرمش بطعم لا يقاوم",
     "img": "photo-1567620905732-2d1ec7ab7445"},
    {"id": "shawarma", "name": "شاورما", "desc": "شاورما لحم ودجاج على الفحم",
     "img": "photo-1601050690597-df0568f70950"},
    {"id": "salads", "name": "السلطات", "desc": "سلطات طازجة ومنعشة",
     "img": "photo-1546833999-b9f581a1996d"},
    {"id": "desserts", "name": "الحلويات", "desc": "حلويات تنهي وجبتك بإتقان",
     "img": "photo-1572441713132-c542fc4fe282"},
]

# Real Unsplash food photo IDs categorized
PRODUCT_PHOTOS = {
    "pizza": ["photo-1565299624946-b28f40a0ae38", "photo-1574071318508-1cdbab80d002",
              "photo-1513104890138-7c749659a591", "photo-1571066811602-716837d681de",
              "photo-1604068549290-dea0e4a305ca", "photo-1593504049359-74330189a345",
              "photo-1542587227-cf86b8edec57", "photo-1555072956-7758afb20e8f",
              "photo-1628840042765-356cda07504e", "photo-1620374643123-6e0d3e3e7e21"],
    "burger": ["photo-1551782450-a2132b4ba21d", "photo-1568901346375-23c9450c58cd",
               "photo-1572802419224-296b0aeee0d9", "photo-1586190848861-99aa4a171e90",
               "photo-1550547660-d9450f859349", "photo-1561758033-d89a9ad46330",
               "photo-1525164286253-04ae5f0b5e26", "photo-1606131731446-5568d87113aa",
               "photo-1597314867637-d10b9cd5a4f8", "photo-1607013251379-e6eecfffe234"],
    "broast": ["photo-1567620905732-2d1ec7ab7445", "photo-1626082929543-5bab709cb6e8",
               "photo-1610057099443-fde8c4d50f91", "photo-1562967914-608f82629710",
               "photo-1565299507177-b0ac66763828", "photo-1626645738196-c2a7c87a8f58",
               "photo-1639024471283-03518883512d", "photo-1606755962773-d324e0a13086",
               "photo-1604908554007-29229c12389b", "photo-1606824093866-77555fbeb4f3"],
    "shawarma": ["photo-1601050690597-df0568f70950", "photo-1633936827229-a8f1eb1d2db8",
                 "photo-1599487488170-d11ec9c172f0", "photo-1559847844-5315695dadae",
                 "photo-1602253057119-44d745d9b860", "photo-1633505650443-9b59b95e7d3a",
                 "photo-1561651823-34feb02250e4", "photo-1644852471055-7b1bb6c1ed42",
                 "photo-1593504049359-74330189a345", "photo-1574484284002-952d92456975"],
    "salads": ["photo-1546833999-b9f581a1996d", "photo-1540420773420-3366772f4999",
               "photo-1502741338009-cac2772e18bc", "photo-1604908554049-3ac3a26fcadb",
               "photo-1505253716362-afaea1d3d1af", "photo-1623428187969-5da2dcea5ebf",
               "photo-1551248429-40975aa4de74", "photo-1571197119282-7c4e2c2fc6dc",
               "photo-1517248135467-4c7edcad34c4", "photo-1556909114-f6e7ad7d3136"],
    "desserts": ["photo-1572441713132-c542fc4fe282", "photo-1488477181946-6428a0291777",
                 "photo-1565958011703-44f9829ba187", "photo-1563729784474-d77dbb933a9e",
                 "photo-1551024506-0bccd828d307", "photo-1505976670281-65cce8d75ade",
                 "photo-1576107324820-3a3ed1c63fb5", "photo-1606313564200-e75d5e30476c",
                 "photo-1606755456206-b25206cde27e", "photo-1551024601-bec78aea704b"],
}

# 10 product templates per category (60 total)
PRODUCT_TEMPLATES = {
    "pizza": [
        ("بيتزا مارجريتا", 35, 850, "طماطم سان مارزانو، موزاريلا الجاموس الطازج، أوراق ريحان، زيت زيتون بكر",
         ["دقيق إيطالي 00", "صلصة طماطم", "موزاريلا", "ريحان", "زيت زيتون"], ["نباتي"]),
        ("بيتزا بيبروني", 42, 980, "بيبروني حار، موزاريلا مدخنة، صلصة طماطم بالأعشاب",
         ["بيبروني", "موزاريلا", "صلصة طماطم", "أوريغانو"], ["حار"]),
        ("بيتزا الفطر والترفل", 58, 920, "فطر بورتوبيلو مشوي مع زيت الترفل البيضاء",
         ["فطر", "ترفل", "موزاريلا", "بقدونس"], ["نباتي"]),
        ("بيتزا الدجاج بالباربكيو", 45, 1050, "دجاج مشوي مع صلصة باربكيو وبصل أحمر",
         ["دجاج", "بصل أحمر", "باربكيو", "موزاريلا"], []),
        ("بيتزا البحرية", 55, 890, "ميكس البحر: روبيان، كاليماري، بلح البحر",
         ["روبيان", "كاليماري", "بلح البحر", "ثوم"], []),
        ("بيتزا الخضار", 38, 720, "فلفل ملون، فطر، زيتون، طماطم، بصل",
         ["فلفل", "فطر", "زيتون", "طماطم"], ["نباتي"]),
        ("بيتزا اللحم المفروم", 47, 1100, "لحم بقري مفروم مع صلصة الطماطم والفلفل الأخضر",
         ["لحم بقري", "فلفل أخضر", "بصل", "صلصة طماطم"], []),
        ("بيتزا الجبنة الرباعية", 49, 1180, "موزاريلا + شيدر + بارميزان + ريكوتا",
         ["موزاريلا", "شيدر", "بارميزان", "ريكوتا"], ["نباتي"]),
        ("بيتزا المشكلة", 52, 960, "نصف بيبروني ونصف خضار للذواقة",
         ["بيبروني", "خضار مشكل", "موزاريلا"], []),
        ("بيتزا الذرة والدجاج", 40, 870, "دجاج متبّل مع ذرة حلوة وزيتون أسود",
         ["دجاج", "ذرة", "زيتون أسود", "موزاريلا"], []),
    ],
    "burger": [
        ("برجر كلاسيك", 32, 750, "لحم بقري طازج مع جبنة شيدر وخس وطماطم",
         ["لحم بقري", "شيدر", "خس", "طماطم", "خبز محمص"], []),
        ("برجر اللحم المضاعف", 45, 1100, "قطعتين لحم بقري مع جبنة مذابة وبصل مكرمل",
         ["لحم بقري ×2", "شيدر", "بصل مكرمل"], []),
        ("برجر الدجاج المقرمش", 28, 680, "صدور دجاج مقرمشة مع صلصة سرية وخس",
         ["دجاج", "كورن فليكس", "خس", "صلصة"], []),
        ("برجر الفلافل", 25, 590, "فلافل منزلي مع طحينة وسلطة خضار",
         ["فلافل", "طحينة", "خضار"], ["نباتي", "حلال"]),
        ("برجر الجبن الأزرق", 38, 920, "لحم بقري مع جبنة روكفور وعسل أسود",
         ["لحم", "جبنة روكفور", "عسل أسود"], []),
        ("برجر البيكون", 42, 1050, "لحم بقري مع بيكون لحم (حلال) وجبنة سويسرية",
         ["لحم", "بيكون لحم حلال", "سويسري"], ["حلال"]),
        ("برجر السمك", 36, 720, "فيليه سمك مقرمش مع صلصة التارتار",
         ["سمك", "تارتار", "خس"], []),
        ("برجر الفطر والجبنة", 34, 780, "لحم بقري مع فطر مشوي وجبنة موزاريلا",
         ["لحم", "فطر", "موزاريلا"], []),
        ("برجر BBQ", 36, 950, "لحم بقري مع صلصة باربكيو وبصل محمر",
         ["لحم", "BBQ", "بصل محمر"], []),
        ("برجر الجمبري", 48, 690, "جمبري مقلي مع صلصة الكوكتيل",
         ["جمبري", "كوكتيل", "خس"], []),
    ],
    "broast": [
        ("بروست ربع دجاج", 22, 620, "ربع دجاجة بروست مقرمش مع البطاطس",
         ["دجاج", "بهارات سرية", "بطاطس"], []),
        ("بروست نصف دجاج", 38, 1180, "نصف دجاجة بروست + سلطة + خبز",
         ["دجاج", "بهارات", "خبز"], []),
        ("بروست دجاجة كاملة", 65, 2300, "دجاجة كاملة + 4 خبز + 2 سلطة + بطاطس",
         ["دجاج", "بطاطس", "سلطة", "خبز"], []),
        ("ستربس دجاج", 28, 680, "شرائح دجاج مقرمشة مع 3 صلصات",
         ["دجاج", "صلصات"], []),
        ("بروست تشكن بوبس", 24, 540, "قطع دجاج صغيرة مقرمشة جداً",
         ["دجاج", "بهارات"], []),
        ("ساندويش بروست", 18, 480, "ساندويش بروست مع خس وطماطم وصلصة",
         ["دجاج", "خبز", "خضار"], []),
        ("بروست حار", 26, 660, "بروست بنكهة الفلفل الحار",
         ["دجاج", "فلفل حار"], ["حار"]),
        ("بروست العسل والخردل", 27, 720, "بروست مع صلصة العسل والخردل",
         ["دجاج", "عسل", "خردل"], []),
        ("بروست بالثوم", 25, 690, "بروست بنكهة الثوم الأبيض",
         ["دجاج", "ثوم"], []),
        ("وجبة عائلية بروست", 95, 3800, "دجاجتين + 6 خبز + 4 سلطة + 2 بطاطس",
         ["دجاج ×2", "خبز", "سلطة", "بطاطس"], []),
    ],
    "shawarma": [
        ("شاورما لحم", 18, 480, "لحم غنم متبّل مع طحينة وخضار",
         ["لحم غنم", "طحينة", "خضار", "خبز صاج"], []),
        ("شاورما دجاج", 15, 420, "دجاج متبّل مع توم وخس وبطاطس",
         ["دجاج", "توم", "خس", "بطاطس"], []),
        ("شاورما مكس", 20, 510, "لحم ودجاج معاً مع جميع الإضافات",
         ["لحم", "دجاج", "خضار"], []),
        ("صحن شاورما لحم", 38, 880, "صحن لحم شاورما مع رز وخضار",
         ["لحم", "رز", "خضار"], []),
        ("صحن شاورما دجاج", 32, 760, "صحن دجاج شاورما مع رز وخضار",
         ["دجاج", "رز", "خضار"], []),
        ("شاورما عربي", 16, 450, "شاورما عربي بالخبز المقشط",
         ["لحم", "خبز عربي"], []),
        ("سلطة شاورما", 22, 380, "سلطة بقطع شاورما مشوية",
         ["شاورما", "خس", "طماطم"], []),
        ("بوكس شاورما", 28, 720, "علبة شاورما لحم + بطاطس + مشروب",
         ["شاورما", "بطاطس", "مشروب"], []),
        ("شاورما حار", 17, 470, "شاورما بنكهة الفلفل الحار",
         ["شاورما", "فلفل حار"], ["حار"]),
        ("شاورما اللحم بالخبز الفينو", 22, 590, "شاورما لحم مع خبز فينو طازج",
         ["لحم", "خبز فينو"], []),
    ],
    "salads": [
        ("سلطة سيزر", 28, 380, "خس روماني، دجاج مشوي، بارميزان، كروتون",
         ["خس روماني", "دجاج", "بارميزان", "كروتون"], []),
        ("سلطة فتوش", 18, 240, "خضار طازجة مع خبز محمص ودبس الرمان",
         ["خس", "خيار", "طماطم", "خبز محمص", "دبس رمان"], ["نباتي"]),
        ("سلطة تبولة", 16, 180, "بقدونس مفروم مع برغل وطماطم وليمون",
         ["بقدونس", "برغل", "طماطم", "ليمون"], ["نباتي"]),
        ("سلطة يونانية", 25, 320, "طماطم، خيار، فلفل، جبنة فيتا، زيتون كالاماتا",
         ["طماطم", "فيتا", "زيتون"], ["نباتي"]),
        ("سلطة كينوا", 32, 350, "كينوا مع خضار مشوية وأفوكادو",
         ["كينوا", "أفوكادو", "خضار مشوية"], ["نباتي"]),
        ("سلطة الدجاج بالأفوكادو", 30, 420, "دجاج مشوي مع أفوكادو وذرة",
         ["دجاج", "أفوكادو", "ذرة"], []),
        ("سلطة التونة", 26, 360, "تونة مع خس وذرة وطماطم وبصل",
         ["تونة", "خس", "ذرة"], []),
        ("سلطة المانجو والروبيان", 38, 410, "روبيان مشوي مع مانجو طازجة",
         ["روبيان", "مانجو"], []),
        ("سلطة الباذنجان المشوي", 22, 290, "باذنجان مشوي مع طماطم وثوم",
         ["باذنجان", "طماطم", "ثوم"], ["نباتي"]),
        ("سلطة كولسلو", 14, 220, "ملفوف وجزر مبشور مع المايونيز",
         ["ملفوف", "جزر", "مايونيز"], ["نباتي"]),
    ],
    "desserts": [
        ("تشيز كيك التوت", 22, 380, "تشيز كيك كريمي مع توت أحمر طازج",
         ["جبنة كريمية", "بسكويت", "توت"], []),
        ("كنافة بالقشطة", 18, 420, "كنافة ناعمة بالقشطة الطازجة والقطر",
         ["كنافة", "قشطة", "قطر"], []),
        ("بقلاوة", 12, 280, "بقلاوة بالفستق الحلبي والعسل",
         ["فيلو", "فستق", "عسل"], []),
        ("ام علي", 16, 360, "أم علي ساخنة بالحليب والمكسرات",
         ["كرواسون", "حليب", "مكسرات"], []),
        ("لافا كيك", 24, 480, "كيك شوكولاتة سائل ساخن مع ايسكريم",
         ["شوكولاتة", "ايسكريم"], []),
        ("تيراميسو", 28, 420, "تيراميسو إيطالي بالقهوة والماسكاربوني",
         ["ماسكاربوني", "قهوة", "كاكاو"], []),
        ("ايس كريم 3 كرات", 18, 320, "اختر 3 نكهات من 8",
         ["حليب", "سكر", "نكهات"], []),
        ("بانكيك بالعسل", 22, 480, "بانكيك ساخن مع عسل وزبدة وفواكه",
         ["دقيق", "عسل", "زبدة"], []),
        ("وافل بلجيكي", 24, 510, "وافل مع نوتيلا وموز وفراولة",
         ["وافل", "نوتيلا", "موز"], []),
        ("بسبوسة بالقشطة", 14, 340, "بسبوسة بالقشطة والقطر",
         ["سميد", "قشطة", "قطر"], []),
    ],
}


def _saudi_name() -> str:
    return f"{random.choice(SAUDI_FIRST_NAMES)} {random.choice(SAUDI_FAMILIES)}"


def _saudi_phone() -> str:
    return f"+9665{random.randint(0, 9)}{''.join(str(random.randint(0, 9)) for _ in range(7))}"


def _saudi_address() -> str:
    c = random.choice(SAUDI_CITIES)
    return f"{c['city']} - {random.choice(c['districts'])} - شارع {random.choice(['الأمير سلطان', 'الملك فهد', 'العروبة', 'التحلية', 'العليا'])}"


def _unsplash(pid: str, w: int = 800) -> str:
    return f"https://images.unsplash.com/{pid}?auto=format&fit=crop&w={w}&q=80"


def seed_restaurant(business_name: str, tagline: str = "", phone: str = "", email: str = "") -> Dict[str, Any]:
    """Generate a complete restaurant seed data dict."""
    random.seed(business_name)  # deterministic per business

    phone = phone or "+966512345678"
    email = email or f"info@{(business_name or 'brand').replace(' ', '').lower()[:20]}.sa"

    # Categories
    categories = [
        {**c, "img": _unsplash(c["img"], 800)}
        for c in RESTAURANT_CATEGORIES
    ]

    # Products (60 = 10 per category)
    products: List[Dict[str, Any]] = []
    pid = 1
    for cat in categories:
        templates = PRODUCT_TEMPLATES[cat["id"]]
        photos = PRODUCT_PHOTOS[cat["id"]]
        for i, (name, price, calories, desc, ingredients, tags) in enumerate(templates):
            products.append({
                "id": f"p{pid}",
                "category": cat["id"],
                "name": name,
                "price": price,
                "calories": calories,
                "desc": desc,
                "ingredients": ingredients,
                "tags": tags + (["حلال"] if "حلال" not in tags else []),
                "img": _unsplash(photos[i % len(photos)], 1000),
                "prep_time": f"{10 + i * 2}-{15 + i * 2} دقيقة",
                "rating": round(4.2 + random.random() * 0.7, 1),
                "reviews_count": random.randint(20, 380),
                "is_new": i < 2,
                "is_popular": i in (2, 5, 8),
            })
            pid += 1

    # Orders (30 sample)
    statuses = ["تم الاستلام", "قيد التحضير", "في الطريق", "تم التسليم"]
    payments = ["مدى", "Visa", "STC Pay", "Apple Pay", "كاش عند الاستلام"]
    orders = []
    for i in range(30):
        n_items = random.randint(1, 4)
        items = random.sample(products, n_items)
        order_items = [{"name": p["name"], "qty": random.randint(1, 3), "price": p["price"]} for p in items]
        total = sum(it["qty"] * it["price"] for it in order_items)
        orders.append({
            "id": f"ORD-{1000 + i}",
            "customer": _saudi_name(),
            "phone": _saudi_phone(),
            "items": order_items,
            "total": total,
            "status": random.choice(statuses),
            "time": random.choice(["قبل 5 دقائق", "قبل 12 دقيقة", "قبل ساعة", "قبل 3 ساعات", "اليوم 14:30", "اليوم 12:10"]),
            "payment": random.choice(payments),
            "address": _saudi_address(),
            "driver": random.choice(["أحمد السبيعي", "خالد العتيبي", "سلطان القحطاني", "فيصل الشمري", "بدر الدوسري"]),
        })

    # Customers (20)
    customers = []
    for i in range(20):
        n_orders = random.randint(1, 35)
        avg = random.randint(45, 180)
        customers.append({
            "name": _saudi_name(),
            "phone": _saudi_phone(),
            "total_orders": n_orders,
            "total_spent": n_orders * avg,
            "last_order": random.choice(["اليوم", "أمس", "قبل 3 أيام", "قبل أسبوع", "قبل أسبوعين"]),
            "loyalty_points": n_orders * 25,
            "status": "VIP" if n_orders > 20 else ("منتظم" if n_orders > 5 else "جديد"),
            "wallet": round(random.random() * 80, 2),
        })

    # Drivers (5)
    drivers = [
        {"name": "أحمد السبيعي", "phone": "+966551111111", "status": "متاح", "deliveries_today": 6, "rating": 4.8, "area": "شمال الرياض"},
        {"name": "خالد العتيبي", "phone": "+966552222222", "status": "في توصيل", "deliveries_today": 8, "rating": 4.9, "area": "شرق الرياض"},
        {"name": "سلطان القحطاني", "phone": "+966553333333", "status": "متاح", "deliveries_today": 4, "rating": 4.7, "area": "غرب الرياض"},
        {"name": "فيصل الشمري", "phone": "+966554444444", "status": "استراحة", "deliveries_today": 5, "rating": 4.6, "area": "جنوب الرياض"},
        {"name": "بدر الدوسري", "phone": "+966555555555", "status": "في توصيل", "deliveries_today": 7, "rating": 4.9, "area": "وسط الرياض"},
    ]

    # Analytics
    today_orders = [o for o in orders[:18]]
    today_revenue = sum(o["total"] for o in today_orders)
    # Top dishes by appearance in orders
    from collections import Counter
    dish_count: Counter = Counter()
    for o in orders:
        for it in o["items"]:
            dish_count[it["name"]] += it["qty"]
    top = dish_count.most_common(6)
    analytics = {
        "today": {
            "orders": len(today_orders),
            "revenue": today_revenue,
            "avg_order": round(today_revenue / max(len(today_orders), 1), 2),
            "top_dish": top[0][0] if top else "بيتزا مارجريتا",
        },
        "week": {
            "orders": 142,
            "revenue": 11280,
            "growth_pct": 12.4,
        },
        "top_dishes": [
            {"name": name, "sold": count, "revenue": count * next((p["price"] for p in products if p["name"] == name), 30)}
            for name, count in top
        ],
    }

    # Reviews (5 sample)
    review_texts = [
        "والله مذاق فوق الخيال، أنصح بكل أصناف القائمة! خدمة ممتازة وتوصيل سريع.",
        "أحسن مطعم في الرياض، عائلة كاملة طلبنا وكل واحد عاجبه طلبه. تقييم 10/10.",
        "البيتزا تجنن، خاصة المارجريتا. هتطلب منهم بشكل دائم.",
        "الأسعار معقولة جداً مقارنة بالجودة. تجربة ممتازة.",
        "الموقع منظم والتطبيق سهل، طلبنا وصل خلال 25 دقيقة فقط.",
    ]
    reviews = []
    for i, text in enumerate(review_texts):
        reviews.append({
            "name": _saudi_name(),
            "stars": random.choice([4, 5, 5, 5]),
            "date": random.choice(["قبل يومين", "الأسبوع الماضي", "قبل أسبوعين", "الشهر الماضي"]),
            "text": text,
        })

    # Hours
    hours = {
        "saturday": {"open": "12:00", "close": "00:00"},
        "sunday":   {"open": "12:00", "close": "00:00"},
        "monday":   {"open": "12:00", "close": "00:00"},
        "tuesday":  {"open": "12:00", "close": "00:00"},
        "wednesday":{"open": "12:00", "close": "00:00"},
        "thursday": {"open": "12:00", "close": "01:00"},
        "friday":   {"open": "14:00", "close": "01:00"},
    }

    return {
        "branding": {
            "name": business_name,
            "tagline": tagline or "أصالة الذوق في كل لقمة",
            "phone": phone,
            "whatsapp": phone.replace("+", ""),
            "email": email,
            "address": _saudi_address(),
            "city": "الرياض",
            "instagram": f"@{(business_name or 'brand').replace(' ', '_').lower()[:25]}",
        },
        "hours": hours,
        "categories": categories,
        "products": products,
        "orders": orders,
        "customers": customers,
        "drivers": drivers,
        "analytics": analytics,
        "reviews": reviews,
    }


def seed_to_js(seed: Dict[str, Any]) -> str:
    """Return JS code that defines window.SITE and window.ADMIN_DATA from the seed.

    This goes INTO the brief so the AI knows the exact data shape to consume,
    but the AI does NOT regenerate it — the platform injects the final JS.
    """
    site = {
        "branding": seed["branding"],
        "hours": seed["hours"],
        "categories": seed["categories"],
        "products": seed["products"],
        "reviews": seed["reviews"],
    }
    admin = {
        "orders": seed["orders"],
        "customers": seed["customers"],
        "drivers": seed["drivers"],
        "analytics": seed["analytics"],
    }
    return (
        "window.SITE = " + json.dumps(site, ensure_ascii=False) + ";\n"
        "window.ADMIN_DATA = " + json.dumps(admin, ensure_ascii=False) + ";\n"
    )
