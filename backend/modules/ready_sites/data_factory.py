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
    """Return JS code that defines window.SITE and window.ADMIN_DATA from the seed."""
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


def render_categories_html(seed: Dict[str, Any]) -> str:
    """Build the 6-category grid HTML directly in Python (guarantees visibility)."""
    cards = []
    for c in seed["categories"]:
        cards.append(f'''
<a href="#/category/{c["id"]}" class="cat-card" data-cat="{c["id"]}">
  <div class="cat-img" style="background-image:url('{c["img"]}')"></div>
  <div class="cat-body">
    <h3 class="cat-name">{c["name"]}</h3>
    <p class="cat-desc">{c["desc"]}</p>
    <span class="cat-cta">تصفّح ←</span>
  </div>
</a>''')
    return "\n".join(cards)


def render_products_html(seed: Dict[str, Any]) -> str:
    """Build all 60 product cards HTML directly in Python — grouped by category."""
    cards = []
    for p in seed["products"]:
        tags_html = "".join(f'<span class="ptag">{t}</span>' for t in p.get("tags", [])[:3])
        cards.append(f'''
<article class="product-card" data-category="{p["category"]}" data-name="{p["name"]}" data-tags="{','.join(p.get('tags',[]))}">
  <div class="prod-img" style="background-image:url('{p["img"]}')">
    <span class="prod-cal">{p["calories"]} سعرة</span>
    {'<span class="prod-new">جديد</span>' if p.get("is_new") else ''}
    {'<span class="prod-pop">⭐ مميز</span>' if p.get("is_popular") else ''}
  </div>
  <div class="prod-body">
    <div class="prod-tags">{tags_html}</div>
    <h4 class="prod-name">{p["name"]}</h4>
    <p class="prod-desc">{p["desc"]}</p>
    <div class="prod-foot">
      <span class="prod-price">{p["price"]} ر.س</span>
      <button class="prod-add" onclick="window.addToCart && window.addToCart('{p["id"]}')" data-pid="{p["id"]}">أضف للسلة</button>
    </div>
  </div>
</article>''')
    return "\n".join(cards)


def render_admin_orders_html(seed: Dict[str, Any]) -> str:
    """Pre-built admin orders table HTML."""
    rows = []
    status_colors = {"تم الاستلام": "#3b82f6", "قيد التحضير": "#f59e0b", "في الطريق": "#a855f7", "تم التسليم": "#22c55e"}
    for o in seed["orders"][:15]:
        items_count = sum(it.get("qty", 1) for it in o.get("items", []))
        color = status_colors.get(o["status"], "#888")
        rows.append(f'''
<tr>
  <td><strong>{o["id"]}</strong></td>
  <td>{o["customer"]}</td>
  <td dir="ltr">{o["phone"]}</td>
  <td>{items_count} صنف</td>
  <td><strong>{o["total"]} ر.س</strong></td>
  <td><span class="status-badge" style="background:{color}20;color:{color};border:1px solid {color}40">{o["status"]}</span></td>
  <td>{o["time"]}</td>
  <td><button class="btn-sm">عرض</button></td>
</tr>''')
    return "\n".join(rows)


def render_admin_customers_html(seed: Dict[str, Any]) -> str:
    rows = []
    for c in seed["customers"][:12]:
        badge_color = "#a855f7" if c["status"] == "VIP" else ("#22c55e" if c["status"] == "منتظم" else "#3b82f6")
        rows.append(f'''
<tr>
  <td><strong>{c["name"]}</strong></td>
  <td dir="ltr">{c["phone"]}</td>
  <td>{c["total_orders"]}</td>
  <td>{c["total_spent"]} ر.س</td>
  <td>{c["loyalty_points"]} نقطة</td>
  <td>{c["wallet"]} ر.س</td>
  <td><span class="status-badge" style="background:{badge_color}20;color:{badge_color}">{c["status"]}</span></td>
  <td><a href="https://wa.me/{c['phone'].replace('+','')}" target="_blank" class="btn-sm" style="background:#22c55e;color:#fff">واتساب</a></td>
</tr>''')
    return "\n".join(rows)


def render_cart_module(seed: Dict[str, Any]) -> str:
    """Pre-built cart drawer + working addToCart + checkout flow. Overrides any AI-defined cart."""
    brand_phone = seed["branding"]["whatsapp"]
    return f"""
<!-- ═══ Zitex Cart Module ═══ -->
<style>
#zx-cart-btn{{position:fixed;bottom:24px;left:24px;width:62px;height:62px;border-radius:50%;background:#a52a2a;color:#fff;border:none;cursor:pointer;box-shadow:0 10px 30px rgba(165,42,42,.4);z-index:9000;font-size:24px;transition:transform .2s}}
#zx-cart-btn:hover{{transform:scale(1.08)}}
#zx-cart-badge{{position:absolute;top:-6px;right:-6px;background:#fbbf24;color:#000;width:24px;height:24px;border-radius:50%;font-size:12px;font-weight:900;display:flex;align-items:center;justify-content:center}}
#zx-cart-drawer{{position:fixed;top:0;right:-420px;width:400px;height:100vh;background:#fff;box-shadow:-10px 0 40px rgba(0,0,0,.2);z-index:9100;transition:right .3s ease;display:flex;flex-direction:column;direction:rtl;font-family:'Tajawal',sans-serif}}
#zx-cart-drawer.open{{right:0}}
.zx-cart-head{{background:#0f172a;color:#fff;padding:20px;display:flex;justify-content:space-between;align-items:center}}
.zx-cart-head h3{{font-size:18px;font-weight:900;color:#fff}}
.zx-cart-close{{background:none;border:none;color:#fff;font-size:22px;cursor:pointer}}
.zx-cart-items{{flex:1;overflow-y:auto;padding:14px}}
.zx-cart-item{{display:flex;gap:10px;padding:12px;border-bottom:1px solid #f3f4f6;align-items:center}}
.zx-cart-item img{{width:60px;height:60px;border-radius:8px;object-fit:cover}}
.zx-cart-item .info{{flex:1;min-width:0}}
.zx-cart-item .name{{font-weight:700;color:#0a0a0a;font-size:13px}}
.zx-cart-item .price{{color:#a52a2a;font-weight:900;font-size:13px}}
.zx-qty{{display:flex;align-items:center;gap:6px;background:#f9fafb;border-radius:99px;padding:3px}}
.zx-qty button{{width:24px;height:24px;border-radius:50%;border:none;background:#fff;cursor:pointer;font-weight:900;color:#a52a2a}}
.zx-cart-foot{{padding:16px;background:#f9fafb;border-top:1px solid #e5e7eb}}
.zx-total{{display:flex;justify-content:space-between;margin-bottom:12px;font-size:17px;font-weight:900;color:#0a0a0a}}
.zx-checkout-btn{{width:100%;padding:13px;background:#a52a2a;color:#fff;border:none;border-radius:10px;font-weight:900;cursor:pointer;font-size:14px}}
.zx-empty{{text-align:center;padding:40px;color:#888;font-size:13px}}
#zx-toast{{position:fixed;bottom:100px;left:24px;background:#22c55e;color:#fff;padding:12px 20px;border-radius:99px;font-weight:700;font-size:13px;z-index:9500;opacity:0;transition:opacity .3s;direction:rtl}}
#zx-toast.show{{opacity:1}}
#zx-checkout-modal{{position:fixed;inset:0;background:rgba(0,0,0,.7);z-index:9200;display:none;align-items:center;justify-content:center;direction:rtl}}
#zx-checkout-modal.open{{display:flex}}
.zx-checkout-card{{background:#fff;border-radius:18px;width:480px;max-width:92vw;max-height:90vh;overflow-y:auto;padding:24px}}
.zx-checkout-card h3{{font-size:20px;font-weight:900;margin-bottom:14px;color:#0a0a0a}}
.zx-checkout-card input,.zx-checkout-card select,.zx-checkout-card textarea{{width:100%;padding:11px 14px;border:1px solid #e5e7eb;border-radius:10px;margin-bottom:10px;font-family:inherit;font-size:13px}}
.zx-pay-grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-bottom:14px}}
.zx-pay-opt{{padding:10px;border:1px solid #e5e7eb;border-radius:8px;text-align:center;cursor:pointer;font-size:11px;font-weight:700}}
.zx-pay-opt.sel{{border-color:#a52a2a;background:#fef2f2;color:#a52a2a}}
.zx-conf{{text-align:center;padding:20px}}
.zx-conf h2{{color:#22c55e;font-size:24px;margin-bottom:8px}}
.zx-conf .oid{{font-family:monospace;background:#f3f4f6;padding:8px 18px;border-radius:99px;display:inline-block;margin:10px 0;font-weight:900}}
</style>

<button id="zx-cart-btn" onclick="zxCartToggle()">🛒<span id="zx-cart-badge" style="display:none">0</span></button>
<div id="zx-cart-drawer">
  <div class="zx-cart-head"><h3>🛒 سلتك</h3><button class="zx-cart-close" onclick="zxCartToggle()">✕</button></div>
  <div class="zx-cart-items" id="zx-cart-items"><div class="zx-empty">السلة فارغة</div></div>
  <div class="zx-cart-foot"><div class="zx-total"><span>الإجمالي:</span><span><span id="zx-cart-total">0</span> ر.س</span></div><button class="zx-checkout-btn" onclick="zxOpenCheckout()">إتمام الطلب →</button></div>
</div>
<div id="zx-toast">تمت الإضافة</div>

<div id="zx-checkout-modal">
  <div class="zx-checkout-card" id="zx-checkout-content"></div>
</div>

<script>
(function(){{
  const CART_KEY = 'zx_restaurant_cart';
  function getCart(){{ try{{return JSON.parse(localStorage.getItem(CART_KEY)||'[]')}} catch(e){{return []}} }}
  function setCart(c){{ localStorage.setItem(CART_KEY, JSON.stringify(c)); zxRenderCart(); }}
  window.addToCart = function(pid){{
    const prod = (window.SITE?.products || []).find(p => p.id === pid);
    if(!prod) return console.warn('Product not found:', pid);
    const cart = getCart();
    const ex = cart.find(i => i.id === pid);
    if(ex) ex.qty = (ex.qty||1) + 1;
    else cart.push({{id: prod.id, name: prod.name, price: prod.price, img: prod.img, qty: 1}});
    setCart(cart);
    const t = document.getElementById('zx-toast');
    t.textContent = '✓ تمت إضافة ' + prod.name;
    t.classList.add('show');
    setTimeout(() => t.classList.remove('show'), 1800);
  }};
  window.openCart = window.addToCart; // alias
  window.zxCartToggle = function(){{ document.getElementById('zx-cart-drawer').classList.toggle('open'); }};
  window.zxRenderCart = function(){{
    const cart = getCart();
    const ctr = document.getElementById('zx-cart-items');
    const badge = document.getElementById('zx-cart-badge');
    const total = cart.reduce((s,i) => s + (i.price * (i.qty||1)), 0);
    document.getElementById('zx-cart-total').textContent = total.toFixed(2);
    const totalQty = cart.reduce((s,i) => s + (i.qty||1), 0);
    badge.style.display = totalQty > 0 ? 'flex' : 'none';
    badge.textContent = totalQty;
    if(!cart.length){{ ctr.innerHTML = '<div class="zx-empty">السلة فارغة</div>'; return; }}
    ctr.innerHTML = cart.map(i => `
      <div class="zx-cart-item">
        <img src="${{i.img}}" alt="">
        <div class="info"><div class="name">${{i.name}}</div><div class="price">${{(i.price * (i.qty||1)).toFixed(2)}} ر.س</div></div>
        <div class="zx-qty">
          <button onclick="zxCartQty('${{i.id}}',-1)">−</button>
          <span style="min-width:18px;text-align:center;font-weight:700">${{i.qty||1}}</span>
          <button onclick="zxCartQty('${{i.id}}',1)">+</button>
        </div>
      </div>`).join('');
  }};
  window.zxCartQty = function(pid, delta){{
    const cart = getCart();
    const it = cart.find(i => i.id === pid);
    if(!it) return;
    it.qty = (it.qty||1) + delta;
    setCart(it.qty <= 0 ? cart.filter(i => i.id !== pid) : cart);
  }};
  // Checkout flow
  let checkoutStep = 1;
  let checkoutData = {{type:'delivery', payment:'Mada'}};
  window.zxOpenCheckout = function(){{
    const cart = getCart();
    if(!cart.length){{ alert('السلة فارغة'); return; }}
    checkoutStep = 1;
    document.getElementById('zx-checkout-modal').classList.add('open');
    zxRenderCheckout();
  }};
  window.zxCloseCheckout = function(){{ document.getElementById('zx-checkout-modal').classList.remove('open'); }};
  function zxRenderCheckout(){{
    const c = document.getElementById('zx-checkout-content');
    const cart = getCart();
    const total = cart.reduce((s,i) => s + (i.price * (i.qty||1)), 0);
    if(checkoutStep === 1){{
      c.innerHTML = `<h3>1️⃣ نوع الطلب والعنوان</h3>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:14px">
          <button class="zx-pay-opt ${{checkoutData.type==='delivery'?'sel':''}}" onclick="checkoutData.type='delivery';zxRenderCheckout()">🛵 توصيل</button>
          <button class="zx-pay-opt ${{checkoutData.type==='pickup'?'sel':''}}" onclick="checkoutData.type='pickup';zxRenderCheckout()">🏪 استلام</button>
        </div>
        ${{checkoutData.type==='delivery' ? `
          <input placeholder="المدينة" id="zx-city" />
          <input placeholder="الحي" id="zx-dist" />
          <input placeholder="الشارع" id="zx-street" />
          <input placeholder="رقم المبنى / الشقة" id="zx-bld" />` : '<p style="color:#666;font-size:13px;margin-bottom:14px">جاهز خلال 20 دقيقة من تأكيد الطلب</p>'}}
        <input placeholder="اسمك" id="zx-name" />
        <input placeholder="رقم الهاتف +966..." id="zx-phone" />
        <div style="display:flex;gap:8px;margin-top:14px">
          <button class="zx-checkout-btn" onclick="zxCheckoutNext()">التالي ←</button>
          <button class="zx-checkout-btn" style="background:#e5e7eb;color:#0a0a0a" onclick="zxCloseCheckout()">إلغاء</button>
        </div>`;
    }} else if (checkoutStep === 2){{
      const opts = ['Mada','Visa','Apple Pay','STC Pay','Tap','كاش'];
      c.innerHTML = `<h3>2️⃣ طريقة الدفع</h3>
        <div class="zx-pay-grid">${{opts.map(o => `<div class="zx-pay-opt ${{checkoutData.payment===o?'sel':''}}" onclick="checkoutData.payment='${{o}}';zxRenderCheckout()">${{o}}</div>`).join('')}}</div>
        <div style="background:#f9fafb;padding:14px;border-radius:10px;margin-bottom:14px">
          <div style="font-size:13px;color:#666;margin-bottom:6px">ملخص الطلب:</div>
          ${{cart.map(i => `<div style="display:flex;justify-content:space-between;font-size:12px;margin:4px 0"><span>${{i.name}} × ${{i.qty||1}}</span><span>${{(i.price*(i.qty||1)).toFixed(2)}} ر.س</span></div>`).join('')}}
          <div style="border-top:1px solid #e5e7eb;margin-top:8px;padding-top:8px;display:flex;justify-content:space-between;font-weight:900"><span>الإجمالي:</span><span>${{total.toFixed(2)}} ر.س</span></div>
        </div>
        <div style="display:flex;gap:8px"><button class="zx-checkout-btn" onclick="zxCheckoutNext()">تأكيد الدفع</button><button class="zx-checkout-btn" style="background:#e5e7eb;color:#0a0a0a" onclick="checkoutStep=1;zxRenderCheckout()">رجوع</button></div>`;
    }} else {{
      const oid = 'ORD-' + Math.floor(Math.random()*9000 + 1000);
      c.innerHTML = `<div class="zx-conf"><h2>✓ تم الطلب بنجاح</h2><p style="color:#666;font-size:13px">سنبدأ في تجهيز طلبك فوراً</p><div class="oid">${{oid}}</div>
        <div style="display:flex;justify-content:space-around;margin:20px 0;font-size:11px">
          <div>✓ تم الاستلام</div><div style="opacity:.4">→ تحضير</div><div style="opacity:.4">→ في الطريق</div><div style="opacity:.4">→ توصيل</div>
        </div>
        <a href="https://wa.me/{brand_phone}?text=استفسار%20عن%20الطلب%20${{oid}}" target="_blank" style="display:inline-block;padding:10px 24px;background:#22c55e;color:#fff;border-radius:99px;text-decoration:none;font-weight:900;margin-top:8px">📱 تواصل واتساب</a>
        <button class="zx-checkout-btn" style="margin-top:14px" onclick="localStorage.removeItem('zx_restaurant_cart');zxRenderCart();zxCloseCheckout()">إنهاء</button></div>`;
    }}
  }}
  window.zxCheckoutNext = function(){{
    if(checkoutStep === 1){{
      const name = document.getElementById('zx-name')?.value?.trim();
      const phone = document.getElementById('zx-phone')?.value?.trim();
      if(!name || !phone){{ alert('املأ الاسم والهاتف'); return; }}
      checkoutData.name = name; checkoutData.phone = phone;
    }}
    checkoutStep++;
    zxRenderCheckout();
  }};
  document.addEventListener('DOMContentLoaded', zxRenderCart);
  zxRenderCart();
}})();
</script>
"""


def render_zitex_enhancements(seed: Dict[str, Any], project_id: str = "") -> str:
    """Unified enhancements: global add-to-cart delegation, category filter, reservation modal,
    contact smooth-scroll, reviews slider, and clean Zitex footer with tracking link.

    This is injected near </body> AFTER the AI's HTML, so it overrides AI behaviour.
    """
    reviews = seed.get("reviews", [])
    branding = seed.get("branding", {})
    cats = seed.get("categories", [])
    # Build reviews slide HTML
    review_slides = ""
    for i, r in enumerate(reviews):
        stars = "★" * int(r.get("stars", 5)) + "☆" * (5 - int(r.get("stars", 5)))
        review_slides += f'''
<div class="zx-rev-slide" data-idx="{i}">
  <div class="zx-rev-stars">{stars}</div>
  <p class="zx-rev-text">"{r["text"]}"</p>
  <div class="zx-rev-meta"><strong>{r["name"]}</strong> · <span>{r["date"]}</span></div>
</div>'''

    # Build hours rows for contact
    hours_rows = ""
    day_ar = {"saturday":"السبت","sunday":"الأحد","monday":"الإثنين","tuesday":"الثلاثاء",
              "wednesday":"الأربعاء","thursday":"الخميس","friday":"الجمعة"}
    for k, v in seed.get("hours", {}).items():
        hours_rows += f'<div class="zx-hour-row"><span>{day_ar.get(k,k)}</span><span dir="ltr">{v["open"]} - {v["close"]}</span></div>'

    # Build category filter pills
    cat_pills = '<button class="zx-cat-pill active" data-cat="all">الكل</button>'
    for c in cats:
        cat_pills += f'<button class="zx-cat-pill" data-cat="{c["id"]}">{c["name"]}</button>'

    track_url = f"https://zitex.com/?ref={project_id}" if project_id else "https://zitex.com"
    map_q = (branding.get("address") or branding.get("city") or "Riyadh").replace(" ", "+")

    return f"""
<!-- ═══ Zitex Enhancements Module ═══ -->
<style>
/* Reservation modal */
#zx-resv-modal,#zx-contact-modal{{position:fixed;inset:0;background:rgba(0,0,0,.7);z-index:9300;display:none;align-items:center;justify-content:center;direction:rtl;font-family:'Tajawal',sans-serif}}
#zx-resv-modal.open,#zx-contact-modal.open{{display:flex}}
.zx-resv-card{{background:#fff;border-radius:18px;width:480px;max-width:92vw;padding:28px;position:relative;max-height:90vh;overflow-y:auto}}
.zx-resv-card h3{{font-size:22px;font-weight:900;margin-bottom:6px;color:#0a0a0a;text-align:center}}
.zx-resv-card .zx-sub{{font-size:13px;color:#666;text-align:center;margin-bottom:20px}}
.zx-resv-card input,.zx-resv-card select{{width:100%;padding:13px 14px;border:1px solid #e5e7eb;border-radius:10px;margin-bottom:11px;font-family:inherit;font-size:14px;background:#fafafa}}
.zx-resv-card input:focus,.zx-resv-card select:focus{{border-color:#a52a2a;outline:none;background:#fff}}
.zx-resv-btn{{width:100%;padding:13px;background:linear-gradient(135deg,#a52a2a,#7a1f1f);color:#fff;border:none;border-radius:10px;font-weight:900;cursor:pointer;font-size:15px;letter-spacing:.5px;margin-top:6px}}
.zx-modal-x{{position:absolute;top:14px;left:14px;background:#f3f4f6;border:none;width:36px;height:36px;border-radius:50%;font-size:18px;cursor:pointer;color:#666}}
.zx-resv-ok{{display:none;text-align:center;padding:20px}}
.zx-resv-ok.show{{display:block}}
.zx-resv-ok .ico{{font-size:54px;color:#22c55e;margin-bottom:10px}}
.zx-resv-ok h4{{font-size:20px;font-weight:900;margin-bottom:8px}}
.zx-resv-ok p{{color:#666;font-size:13px}}

/* Category filter pills (sticky, shown on menu) */
#zx-cat-bar{{position:sticky;top:60px;background:rgba(255,255,255,.96);backdrop-filter:blur(12px);z-index:50;padding:14px;display:none;border-bottom:1px solid #e5e7eb;direction:rtl}}
#zx-cat-bar.show{{display:block}}
#zx-cat-bar-inner{{max-width:1200px;margin:0 auto;display:flex;gap:8px;overflow-x:auto;flex-wrap:nowrap;padding:0 14px;scrollbar-width:none}}
#zx-cat-bar-inner::-webkit-scrollbar{{display:none}}
.zx-cat-pill{{padding:8px 18px;border-radius:99px;border:1px solid #e5e7eb;background:#fff;color:#0a0a0a;font-weight:700;font-size:13px;cursor:pointer;white-space:nowrap;flex-shrink:0;font-family:inherit;transition:all .2s}}
.zx-cat-pill:hover{{border-color:#a52a2a;color:#a52a2a}}
.zx-cat-pill.active{{background:#a52a2a;color:#fff;border-color:#a52a2a;box-shadow:0 4px 14px rgba(165,42,42,.3)}}

/* Reviews slider */
#zx-rev-slider{{max-width:900px;margin:60px auto;padding:0 20px;text-align:center;direction:rtl}}
#zx-rev-slider h2{{font-size:30px;font-weight:900;margin-bottom:8px;color:#0a0a0a}}
#zx-rev-slider .zx-rev-sub{{color:#666;margin-bottom:32px;font-size:14px}}
.zx-rev-stage{{position:relative;min-height:200px;background:linear-gradient(135deg,#fef7ed,#fff);border-radius:24px;padding:36px 28px;box-shadow:0 12px 40px rgba(0,0,0,.08);overflow:hidden}}
.zx-rev-slide{{position:absolute;inset:36px 28px;opacity:0;transform:translateX(40px);transition:opacity .55s,transform .55s;text-align:center}}
.zx-rev-slide.active{{opacity:1;transform:translateX(0);position:relative;inset:auto}}
.zx-rev-stars{{color:#fbbf24;font-size:22px;letter-spacing:3px;margin-bottom:12px}}
.zx-rev-text{{font-size:18px;line-height:1.8;color:#0a0a0a;margin-bottom:14px;font-style:italic;font-weight:500}}
.zx-rev-meta{{color:#666;font-size:13px}}
.zx-rev-dots{{display:flex;justify-content:center;gap:8px;margin-top:18px}}
.zx-rev-dot{{width:10px;height:10px;border-radius:50%;background:#d1d5db;border:none;cursor:pointer;transition:all .2s;padding:0}}
.zx-rev-dot.active{{width:30px;border-radius:99px;background:#a52a2a}}

/* Unified Zitex footer */
#zx-footer{{background:#0a0a0b;color:#cbd5e1;padding:50px 24px 0;direction:rtl;font-family:'Tajawal',sans-serif}}
#zx-footer-inner{{max-width:1200px;margin:0 auto}}
.zx-foot-grid{{display:grid;grid-template-columns:1.4fr 1fr 1fr 1.2fr;gap:36px;padding-bottom:36px}}
@media(max-width:900px){{.zx-foot-grid{{grid-template-columns:1fr 1fr;gap:30px}}}}
@media(max-width:560px){{.zx-foot-grid{{grid-template-columns:1fr}}}}
.zx-foot-col h4{{color:#fbbf24;font-size:14px;font-weight:900;margin-bottom:14px;letter-spacing:.5px}}
.zx-foot-col p,.zx-foot-col a{{color:#94a3b8;font-size:13px;line-height:2;text-decoration:none;display:block}}
.zx-foot-col a:hover{{color:#fff}}
.zx-foot-brand{{font-size:24px;font-weight:900;color:#fff;margin-bottom:8px}}
.zx-foot-tagline{{color:#94a3b8;font-size:13px;line-height:1.8;margin-bottom:16px}}
.zx-social{{display:flex;gap:10px;margin-top:14px}}
.zx-social a{{width:38px;height:38px;border-radius:50%;background:#1e293b;display:flex;align-items:center;justify-content:center;font-size:16px;transition:all .2s}}
.zx-social a:hover{{background:#a52a2a;transform:translateY(-3px)}}
.zx-hour-row{{display:flex;justify-content:space-between;padding:4px 0;font-size:12px;color:#94a3b8;border-bottom:1px dashed #1e293b}}
.zx-hour-row:last-child{{border:none}}
#zx-contact-section{{scroll-margin-top:80px}}
.zx-contact-list{{display:grid;gap:8px}}
.zx-contact-list a{{display:flex;align-items:center;gap:10px;padding:9px 12px;background:#1e293b;border-radius:10px;color:#cbd5e1;font-size:13px;transition:all .2s}}
.zx-contact-list a:hover{{background:#a52a2a;color:#fff;transform:translateX(-3px)}}
.zx-contact-list .zx-ico{{font-size:16px}}
.zx-map-mini{{margin-top:10px;width:100%;height:140px;border:none;border-radius:10px;background:#1e293b}}

/* Zitex tracker bar */
.zx-zitex-bar{{border-top:1px solid #1e293b;padding:18px 0;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:14px}}
.zx-zitex-copy{{color:#64748b;font-size:12px}}
.zx-zitex-brand{{display:flex;align-items:center;gap:10px;text-decoration:none;padding:8px 14px;border-radius:99px;background:linear-gradient(135deg,rgba(251,191,36,.1),rgba(165,42,42,.1));border:1px solid rgba(251,191,36,.2);transition:all .25s}}
.zx-zitex-brand:hover{{background:linear-gradient(135deg,rgba(251,191,36,.2),rgba(165,42,42,.2));border-color:#fbbf24;transform:translateY(-2px)}}
.zx-zitex-logo{{width:28px;height:28px;border-radius:50%;background:linear-gradient(135deg,#fbbf24,#a52a2a);display:flex;align-items:center;justify-content:center;color:#fff;font-weight:900;font-size:13px}}
.zx-zitex-text{{display:flex;flex-direction:column;line-height:1.2}}
.zx-zitex-text small{{color:#64748b;font-size:10px}}
.zx-zitex-text strong{{color:#fbbf24;font-size:13px;font-weight:900}}
.zx-pay-icons{{display:flex;gap:8px;align-items:center}}
.zx-pay-icons span{{padding:5px 10px;background:#1e293b;border-radius:6px;font-size:10px;color:#94a3b8;font-weight:700}}

/* Hide AI-generated reservation/contact links in nav */
.zx-nav-hidden{{display:none !important}}
</style>

<!-- Reservation Modal -->
<div id="zx-resv-modal">
  <div class="zx-resv-card">
    <button class="zx-modal-x" onclick="zxResvClose()">✕</button>
    <div id="zx-resv-form-wrap">
      <h3>🍽️ احجز طاولتك</h3>
      <p class="zx-sub">احجز مكانك مسبقاً وضمن لك أجواء مميزة</p>
      <input type="text" id="zx-resv-name" placeholder="الاسم الكامل" />
      <input type="tel" id="zx-resv-phone" placeholder="رقم الجوال +966..." />
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px">
        <input type="date" id="zx-resv-date" />
        <input type="time" id="zx-resv-time" />
      </div>
      <select id="zx-resv-party">
        <option value="2">2 أشخاص</option>
        <option value="4" selected>4 أشخاص</option>
        <option value="6">6 أشخاص</option>
        <option value="8">8 أشخاص</option>
        <option value="10">10+ أشخاص</option>
      </select>
      <input type="text" id="zx-resv-notes" placeholder="ملاحظات (اختياري) — مناسبة، حساسية..." />
      <button class="zx-resv-btn" onclick="zxResvSubmit()">تأكيد الحجز</button>
    </div>
    <div class="zx-resv-ok" id="zx-resv-ok">
      <div class="ico">✓</div>
      <h4>تم استلام طلب الحجز</h4>
      <p>سنتواصل معك خلال دقائق لتأكيد الموعد. شكراً لاختيارك لنا 🌹</p>
      <button class="zx-resv-btn" style="margin-top:18px" onclick="zxResvClose()">رجوع</button>
    </div>
  </div>
</div>

<!-- Sticky Category Filter Bar -->
<div id="zx-cat-bar"><div id="zx-cat-bar-inner">{cat_pills}</div></div>

<!-- Reviews Auto-Slider -->
<section id="zx-rev-slider">
  <h2>آراء عملائنا</h2>
  <p class="zx-rev-sub">قالوا عنا ما لم نقله عن أنفسنا</p>
  <div class="zx-rev-stage" id="zx-rev-stage">{review_slides}</div>
  <div class="zx-rev-dots" id="zx-rev-dots"></div>
</section>

<!-- ═══ Unified Zitex Footer ═══ -->
<footer id="zx-footer">
  <div id="zx-footer-inner">
    <div class="zx-foot-grid">
      <div class="zx-foot-col">
        <div class="zx-foot-brand">{branding.get('name','مطعمي')}</div>
        <p class="zx-foot-tagline">{branding.get('tagline','نقدّم لك تجربة طعام لا تُنسى — مذاق أصيل وأجواء مميزة في كل زيارة.')}</p>
        <div class="zx-social">
          <a href="https://instagram.com/{(branding.get('instagram') or '').replace('@','')}" target="_blank" rel="noopener" aria-label="Instagram">📷</a>
          <a href="https://wa.me/{branding.get('whatsapp','966512345678')}" target="_blank" rel="noopener" aria-label="WhatsApp">💬</a>
          <a href="https://twitter.com/{(branding.get('instagram') or '').replace('@','')}" target="_blank" rel="noopener" aria-label="Twitter">🐦</a>
          <a href="https://tiktok.com/@{(branding.get('instagram') or '').replace('@','')}" target="_blank" rel="noopener" aria-label="TikTok">🎵</a>
        </div>
      </div>

      <div class="zx-foot-col">
        <h4>ساعات العمل</h4>
        {hours_rows}
      </div>

      <div class="zx-foot-col">
        <h4>روابط سريعة</h4>
        <a href="#/">الرئيسية</a>
        <a href="#/menu">القائمة</a>
        <a href="javascript:zxResvOpen()">احجز طاولة</a>
        <a href="#zx-contact-section" onclick="zxScrollContact(event)">تواصل معنا</a>
        <a href="?admin=1" target="_blank">لوحة الإدارة</a>
      </div>

      <div class="zx-foot-col" id="zx-contact-section">
        <h4>تواصل معنا</h4>
        <div class="zx-contact-list">
          <a href="tel:{branding.get('phone','+966512345678')}"><span class="zx-ico">📞</span><span dir="ltr">{branding.get('phone','+966512345678')}</span></a>
          <a href="https://wa.me/{branding.get('whatsapp','966512345678')}" target="_blank"><span class="zx-ico">💬</span>واتساب</a>
          <a href="mailto:{branding.get('email','info@brand.sa')}"><span class="zx-ico">✉️</span><span style="word-break:break-all">{branding.get('email','info@brand.sa')}</span></a>
          <a href="https://maps.google.com/?q={map_q}" target="_blank"><span class="zx-ico">📍</span>{branding.get('address','الرياض')}</a>
        </div>
        <iframe class="zx-map-mini" loading="lazy" src="https://maps.google.com/maps?q={map_q}&output=embed" referrerpolicy="no-referrer-when-downgrade"></iframe>
      </div>
    </div>

    <div class="zx-zitex-bar">
      <div class="zx-zitex-copy">© {branding.get('name','مطعمي')} {seed.get('year', 2026)} — جميع الحقوق محفوظة</div>
      <div class="zx-pay-icons">
        <span>Mada</span><span>Visa</span><span>Apple Pay</span><span>STC Pay</span>
      </div>
      <a class="zx-zitex-brand" href="{track_url}" target="_blank" rel="noopener" data-zx-tracker="{project_id}">
        <div class="zx-zitex-logo">Z</div>
        <div class="zx-zitex-text">
          <small>صُنع بواسطة</small>
          <strong>Zitex</strong>
        </div>
      </a>
    </div>
  </div>
</footer>

<script>
(function(){{
  /* ═══ 1. Global Add-to-Cart click delegation ═══ */
  document.addEventListener('click', function(e){{
    const btn = e.target.closest('.prod-add,[data-pid],.add-to-cart,[data-add-cart]');
    if(!btn) return;
    const pid = btn.getAttribute('data-pid') || btn.getAttribute('data-product-id') || btn.dataset.pid;
    if(!pid) return;
    e.preventDefault();
    if(typeof window.addToCart === 'function') window.addToCart(pid);
  }}, true);

  /* ═══ 2. Category filter pill delegation ═══ */
  let curCat = 'all';
  function applyCatFilter(cat){{
    curCat = cat;
    document.querySelectorAll('.zx-cat-pill').forEach(p => p.classList.toggle('active', p.dataset.cat === cat));
    document.querySelectorAll('[data-category]').forEach(card => {{
      const c = card.getAttribute('data-category');
      card.style.display = (cat === 'all' || c === cat) ? '' : 'none';
    }});
  }}
  document.addEventListener('click', function(e){{
    const pill = e.target.closest('.zx-cat-pill');
    if(pill){{ e.preventDefault(); applyCatFilter(pill.dataset.cat); return; }}
    /* AI-generated category cards */
    const card = e.target.closest('.cat-card,[data-cat],[data-category-link]');
    if(card && (card.dataset.cat || card.getAttribute('data-cat'))){{
      const cat = card.dataset.cat || card.getAttribute('data-cat');
      if(cat){{
        applyCatFilter(cat);
        document.getElementById('zx-cat-bar')?.classList.add('show');
        const prodSec = document.querySelector('[data-category]')?.parentElement;
        if(prodSec) setTimeout(() => prodSec.scrollIntoView({{behavior:'smooth',block:'start'}}), 50);
      }}
    }}
  }}, false);

  /* show cat-bar when user scrolls past the categories grid */
  const catBar = document.getElementById('zx-cat-bar');
  if(catBar){{
    const obs = new IntersectionObserver((entries) => {{
      entries.forEach(en => {{
        if(en.target.matches('[data-category]')) catBar.classList.toggle('show', en.isIntersecting);
      }});
    }}, {{threshold: 0.05}});
    setTimeout(() => {{
      document.querySelectorAll('[data-category]').forEach(p => obs.observe(p));
    }}, 600);
  }}

  /* ═══ 3. Reservation modal ═══ */
  window.zxResvOpen = function(){{
    document.getElementById('zx-resv-modal').classList.add('open');
    document.getElementById('zx-resv-ok').classList.remove('show');
    document.getElementById('zx-resv-form-wrap').style.display = 'block';
  }};
  window.zxResvClose = function(){{ document.getElementById('zx-resv-modal').classList.remove('open'); }};
  window.zxResvSubmit = function(){{
    const name = document.getElementById('zx-resv-name').value.trim();
    const phone = document.getElementById('zx-resv-phone').value.trim();
    const date = document.getElementById('zx-resv-date').value;
    const time = document.getElementById('zx-resv-time').value;
    if(!name || !phone || !date || !time){{ alert('املأ كل الحقول المطلوبة'); return; }}
    /* persist to localStorage so admin can see */
    const resvs = JSON.parse(localStorage.getItem('zx_reservations')||'[]');
    resvs.push({{name, phone, date, time, party: document.getElementById('zx-resv-party').value,
      notes: document.getElementById('zx-resv-notes').value, ts: Date.now()}});
    localStorage.setItem('zx_reservations', JSON.stringify(resvs));
    document.getElementById('zx-resv-form-wrap').style.display = 'none';
    document.getElementById('zx-resv-ok').classList.add('show');
  }};

  /* ═══ 4. Smooth scroll for contact ═══ */
  window.zxScrollContact = function(e){{
    if(e) e.preventDefault();
    const el = document.getElementById('zx-contact-section');
    if(el) el.scrollIntoView({{behavior:'smooth', block:'start'}});
    if(history.replaceState) history.replaceState(null,'','#zx-contact');
  }};

  /* ═══ 5. Intercept legacy nav links ═══ */
  document.addEventListener('click', function(e){{
    const a = e.target.closest('a');
    if(!a) return;
    const txt = (a.textContent || '').trim();
    const href = (a.getAttribute('href') || '').toLowerCase();
    /* احجز طاولة → open modal */
    if(/احجز\\s*طاول|reserve|reservation|book\\s*table/i.test(txt) || href.includes('reservation') || href === '#reserve' || href === '#reservation') {{
      e.preventDefault(); zxResvOpen(); return;
    }}
    /* تواصل / contact → smooth scroll to footer contact */
    if(/تواصل|اتصل|contact/i.test(txt) && !/whatsapp|wa\\.me|tel:|mailto:/i.test(href)) {{
      const isPlainLink = href === '#' || href === '' || href.startsWith('#contact') || href.endsWith('contact') || href.endsWith('contact-us');
      if(isPlainLink){{ e.preventDefault(); zxScrollContact(); return; }}
    }}
  }}, true);

  /* ═══ 6. Reviews auto-slider ═══ */
  const stage = document.getElementById('zx-rev-stage');
  const dots = document.getElementById('zx-rev-dots');
  if(stage && dots){{
    const slides = stage.querySelectorAll('.zx-rev-slide');
    if(slides.length){{
      slides.forEach((s,i) => {{
        const d = document.createElement('button');
        d.className = 'zx-rev-dot' + (i===0?' active':'');
        d.setAttribute('aria-label','مراجعة ' + (i+1));
        d.onclick = () => zxRev(i);
        dots.appendChild(d);
      }});
      slides[0].classList.add('active');
      let cur = 0;
      window.zxRev = function(idx){{
        slides[cur].classList.remove('active');
        document.querySelectorAll('.zx-rev-dot')[cur].classList.remove('active');
        cur = idx % slides.length;
        slides[cur].classList.add('active');
        document.querySelectorAll('.zx-rev-dot')[cur].classList.add('active');
      }};
      setInterval(() => zxRev(cur + 1), 5000);
    }}
  }}

  /* ═══ 7. Zitex tracker ping ═══ */
  const trkLink = document.querySelector('[data-zx-tracker]');
  if(trkLink){{
    const pid = trkLink.getAttribute('data-zx-tracker');
    if(pid){{
      /* fire-and-forget visit ping (non-blocking) */
      try{{
        const img = new Image();
        img.src = 'https://zitex.com/api/ready-sites/track-visit/' + pid + '?t=' + Date.now();
      }}catch(_){{}}
    }}
  }}
}})();
</script>
"""


def render_admin_full_app(seed: Dict[str, Any], admin_email: str, admin_password: str) -> str:
    """Complete pre-built Admin login + 7-tab dashboard (HTML + CSS + JS). Drop-in module."""
    orders_rows = render_admin_orders_html(seed)
    customers_rows = render_admin_customers_html(seed)

    # Drivers cards
    drivers_html = ""
    for d in seed["drivers"]:
        status_color = "#22c55e" if d["status"] == "متاح" else ("#f59e0b" if d["status"] == "في توصيل" else "#888")
        drivers_html += f'''
<div class="zx-driver-card">
  <div class="zx-driver-head"><strong>{d["name"]}</strong><span class="status-badge" style="background:{status_color}20;color:{status_color}">{d["status"]}</span></div>
  <div class="zx-driver-info">
    <div>📞 <span dir="ltr">{d["phone"]}</span></div>
    <div>🛵 {d["deliveries_today"]} توصيلة اليوم</div>
    <div>⭐ {d["rating"]} تقييم</div>
    <div>📍 {d["area"]}</div>
  </div>
  <div class="zx-driver-actions"><a href="https://wa.me/{d["phone"].replace("+","")}" target="_blank">واتساب</a><button>تعليق</button></div>
</div>'''

    # Top dishes bar chart
    top_dishes_html = ""
    max_sold = max((td["sold"] for td in seed["analytics"]["top_dishes"]), default=1)
    for td in seed["analytics"]["top_dishes"]:
        width_pct = round(td["sold"] / max_sold * 100)
        top_dishes_html += f'''
<div class="zx-bar-row"><span class="zx-bar-label">{td["name"]}</span>
  <div class="zx-bar-track"><div class="zx-bar-fill" style="width:{width_pct}%"></div></div>
  <span class="zx-bar-val">{td["sold"]} × {td["revenue"]} ر.س</span></div>'''

    analytics = seed["analytics"]["today"]

    return f"""
<!-- ═══ Zitex Admin Module ═══ -->
<style>
#zx-admin-root,#zx-driver-root{{display:none;font-family:'Tajawal',sans-serif;direction:rtl}}
#zx-admin-root.active,#zx-driver-root.active{{display:block;position:fixed;inset:0;background:#f3f4f6;z-index:9999;overflow-y:auto}}
.zx-login{{min-height:100vh;display:flex;align-items:center;justify-content:center;background:linear-gradient(135deg,#1a1a1a,#374151)}}
.zx-login-card{{background:#fff;padding:40px;border-radius:18px;width:380px;box-shadow:0 30px 80px rgba(0,0,0,.3)}}
.zx-login-card h2{{font-size:22px;font-weight:900;margin-bottom:6px;text-align:center;color:#0a0a0a}}
.zx-login-card p{{font-size:12px;color:#666;text-align:center;margin-bottom:24px}}
.zx-login-card input{{width:100%;padding:13px 14px;border:1px solid #e5e7eb;border-radius:10px;margin-bottom:12px;font-family:inherit;font-size:14px}}
.zx-login-card button{{width:100%;padding:13px;background:#a52a2a;color:#fff;border:none;border-radius:10px;font-weight:900;cursor:pointer;font-size:14px}}
.zx-login-err{{color:#dc2626;font-size:12px;margin-top:8px;text-align:center;display:none}}
.zx-admin-shell{{display:grid;grid-template-columns:240px 1fr;min-height:100vh}}
.zx-side{{background:#0f172a;color:#fff;padding:20px 14px}}
.zx-side .brand{{font-size:18px;font-weight:900;color:#fbbf24;margin-bottom:24px;text-align:center}}
.zx-side a{{display:block;padding:11px 14px;color:#cbd5e1;text-decoration:none;border-radius:8px;margin-bottom:4px;font-size:13px;cursor:pointer}}
.zx-side a:hover,.zx-side a.active{{background:#1e293b;color:#fbbf24}}
.zx-side .logout{{margin-top:30px;color:#ef4444}}
.zx-main{{padding:24px;overflow-y:auto}}
.zx-topbar{{display:flex;justify-content:space-between;align-items:center;margin-bottom:24px}}
.zx-topbar h1{{font-size:22px;font-weight:900;color:#0a0a0a}}
.zx-metrics{{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin-bottom:24px}}
.zx-metric{{background:#fff;padding:18px;border-radius:14px;box-shadow:0 2px 8px rgba(0,0,0,.05)}}
.zx-metric .lbl{{font-size:11px;color:#888;margin-bottom:6px;letter-spacing:1px}}
.zx-metric .val{{font-size:24px;font-weight:900;color:#0a0a0a}}
.zx-metric .delta{{font-size:11px;color:#22c55e;margin-top:4px}}
.zx-card{{background:#fff;border-radius:14px;padding:20px;box-shadow:0 2px 8px rgba(0,0,0,.05);margin-bottom:18px}}
.zx-card h3{{font-size:16px;font-weight:900;margin-bottom:14px;color:#0a0a0a}}
.zx-table{{width:100%;border-collapse:collapse;font-size:12px}}
.zx-table th{{text-align:right;padding:10px 8px;font-weight:700;color:#888;border-bottom:1px solid #e5e7eb;font-size:11px;letter-spacing:1px}}
.zx-table td{{padding:11px 8px;border-bottom:1px solid #f3f4f6;color:#0a0a0a}}
.status-badge{{padding:4px 10px;border-radius:99px;font-size:11px;font-weight:700;display:inline-block}}
.btn-sm{{padding:5px 12px;border-radius:6px;border:1px solid #e5e7eb;background:#f9fafb;color:#0a0a0a;font-size:11px;cursor:pointer;text-decoration:none;display:inline-block}}
.zx-bar-row{{display:grid;grid-template-columns:140px 1fr 140px;gap:12px;align-items:center;margin-bottom:10px;font-size:12px}}
.zx-bar-track{{background:#f3f4f6;height:8px;border-radius:99px;overflow:hidden}}
.zx-bar-fill{{height:100%;background:linear-gradient(90deg,#a52a2a,#fbbf24);border-radius:99px}}
.zx-driver-card{{background:#fff;border-radius:14px;padding:18px;margin-bottom:12px;box-shadow:0 2px 8px rgba(0,0,0,.05)}}
.zx-driver-head{{display:flex;justify-content:space-between;margin-bottom:10px;font-size:14px}}
.zx-driver-info{{display:grid;grid-template-columns:repeat(2,1fr);gap:6px;font-size:12px;color:#666;margin-bottom:10px}}
.zx-driver-actions a,.zx-driver-actions button{{padding:6px 14px;border-radius:6px;border:none;font-size:11px;font-weight:700;cursor:pointer;text-decoration:none;margin-left:6px}}
.zx-driver-actions a{{background:#22c55e;color:#fff}}
.zx-driver-actions button{{background:#f3f4f6;color:#0a0a0a}}
.zx-section{{display:none}}
.zx-section.active{{display:block}}
.zx-tutorial{{position:fixed;inset:0;background:rgba(0,0,0,.7);display:flex;align-items:center;justify-content:center;z-index:10000}}
.zx-tutorial-card{{background:#fff;padding:30px;border-radius:18px;max-width:480px;text-align:center}}
.zx-tutorial-card h3{{font-size:20px;font-weight:900;margin-bottom:10px}}
.zx-tutorial-card p{{color:#666;font-size:14px;margin-bottom:20px}}
.zx-tutorial-card button{{padding:11px 28px;background:#a52a2a;color:#fff;border:none;border-radius:99px;font-weight:900;cursor:pointer}}
/* Driver app */
#zx-driver-root.active{{background:#0f172a;color:#fff}}
.zx-driver-shell{{max-width:480px;margin:0 auto;padding:20px}}
.zx-driver-top{{background:#1e293b;padding:18px;border-radius:14px;margin-bottom:14px;text-align:center}}
.zx-delivery{{background:#1e293b;border-radius:12px;padding:14px;margin-bottom:10px}}
.zx-delivery h4{{font-size:14px;margin-bottom:6px}}
.zx-delivery .addr{{font-size:11px;color:#94a3b8;margin-bottom:10px}}
.zx-delivery-actions{{display:flex;gap:6px;flex-wrap:wrap}}
.zx-delivery-actions a,.zx-delivery-actions button{{flex:1;padding:8px;border-radius:6px;border:none;font-size:10px;font-weight:700;cursor:pointer;text-align:center;text-decoration:none}}
.zx-delivery-actions .wa{{background:#22c55e;color:#fff}}
.zx-delivery-actions .map{{background:#3b82f6;color:#fff}}
.zx-delivery-actions .status{{background:#fbbf24;color:#000}}
</style>

<div id="zx-admin-root">
  <!-- Login -->
  <div class="zx-login" id="zx-admin-login-screen">
    <div class="zx-login-card">
      <h2>🔐 لوحة تحكم المطعم</h2>
      <p>أدخل بيانات الدخول للوصول</p>
      <input type="email" id="zx-admin-email" placeholder="البريد الإلكتروني" />
      <input type="password" id="zx-admin-pass" placeholder="كلمة المرور" />
      <button onclick="zxAdminLogin()">دخول</button>
      <div class="zx-login-err" id="zx-admin-err">بيانات الدخول غير صحيحة</div>
    </div>
  </div>
  <!-- Dashboard -->
  <div class="zx-admin-shell" id="zx-admin-shell" style="display:none">
    <aside class="zx-side">
      <div class="brand">🍽️ لوحة الإدارة</div>
      <a class="active" onclick="zxShow('overview',this)">📊 نظرة عامة</a>
      <a onclick="zxShow('orders',this)">📦 الطلبات</a>
      <a onclick="zxShow('menu',this)">🍕 القائمة</a>
      <a onclick="zxShow('customers',this)">👥 العملاء</a>
      <a onclick="zxShow('drivers',this)">🛵 السائقين</a>
      <a onclick="zxShow('reports',this)">📈 التقارير</a>
      <a onclick="zxShow('settings',this)">⚙️ الإعدادات</a>
      <a class="logout" onclick="zxAdminLogout()">🚪 تسجيل خروج</a>
    </aside>
    <main class="zx-main">
      <div class="zx-topbar"><h1 id="zx-page-title">نظرة عامة</h1><span style="color:#888;font-size:12px">مرحباً بك في لوحة التحكم</span></div>

      <div class="zx-section active" id="zx-overview">
        <div class="zx-metrics">
          <div class="zx-metric"><div class="lbl">طلبات اليوم</div><div class="val">{analytics["orders"]}</div><div class="delta">+12% عن أمس</div></div>
          <div class="zx-metric"><div class="lbl">إيرادات اليوم</div><div class="val">{analytics["revenue"]} ر.س</div><div class="delta">+8% عن أمس</div></div>
          <div class="zx-metric"><div class="lbl">متوسط الطلب</div><div class="val">{analytics["avg_order"]} ر.س</div><div class="delta">+3% عن أمس</div></div>
          <div class="zx-metric"><div class="lbl">الطبق الأكثر مبيعاً</div><div class="val" style="font-size:14px">{analytics["top_dish"]}</div><div class="delta">⭐ مميز</div></div>
        </div>
        <div class="zx-card"><h3>📦 أحدث الطلبات</h3><table class="zx-table"><thead><tr><th>رقم الطلب</th><th>العميل</th><th>الهاتف</th><th>الأصناف</th><th>المبلغ</th><th>الحالة</th><th>الوقت</th><th></th></tr></thead><tbody id="admin-orders-tbody">{orders_rows}</tbody></table></div>
        <div class="zx-card"><h3>📊 أكثر الأطباق مبيعاً (هذا الأسبوع)</h3>{top_dishes_html}</div>
      </div>

      <div class="zx-section" id="zx-orders">
        <div class="zx-card"><h3>📦 جميع الطلبات</h3><table class="zx-table"><thead><tr><th>رقم</th><th>العميل</th><th>الهاتف</th><th>الأصناف</th><th>المبلغ</th><th>الحالة</th><th>الوقت</th><th></th></tr></thead><tbody>{orders_rows}</tbody></table></div>
      </div>

      <div class="zx-section" id="zx-menu">
        <div class="zx-card"><h3>🍕 إدارة القائمة</h3><p style="color:#666;font-size:13px;margin-bottom:14px">إجمالي المنتجات: {len(seed["products"])}</p>
        <button class="btn-sm" style="background:#22c55e;color:#fff;border-color:#22c55e;padding:8px 16px">+ إضافة طبق جديد</button>
        <table class="zx-table" style="margin-top:14px"><thead><tr><th>المنتج</th><th>الفئة</th><th>السعر</th><th>السعرات</th><th>التقييم</th><th>الإجراءات</th></tr></thead><tbody>
        {"".join(f'<tr><td><strong>{p["name"]}</strong></td><td>{p["category"]}</td><td>{p["price"]} ر.س</td><td>{p["calories"]} kcal</td><td>⭐ {p["rating"]}</td><td><button class="btn-sm">تعديل</button> <button class="btn-sm" style="color:#dc2626">حذف</button></td></tr>' for p in seed["products"][:20])}
        </tbody></table></div>
      </div>

      <div class="zx-section" id="zx-customers">
        <div class="zx-card"><h3>👥 العملاء (CRM)</h3><table class="zx-table"><thead><tr><th>الاسم</th><th>الهاتف</th><th>الطلبات</th><th>الإنفاق</th><th>النقاط</th><th>المحفظة</th><th>الحالة</th><th>تواصل</th></tr></thead><tbody id="admin-customers-tbody">{customers_rows}</tbody></table></div>
      </div>

      <div class="zx-section" id="zx-drivers">
        <div class="zx-card"><h3>🛵 السائقين</h3>{drivers_html}</div>
      </div>

      <div class="zx-section" id="zx-reports">
        <div class="zx-card"><h3>📈 تقرير الأسبوع</h3>
        <div class="zx-metrics"><div class="zx-metric"><div class="lbl">طلبات الأسبوع</div><div class="val">{seed["analytics"]["week"]["orders"]}</div></div><div class="zx-metric"><div class="lbl">إيرادات الأسبوع</div><div class="val">{seed["analytics"]["week"]["revenue"]} ر.س</div></div><div class="zx-metric"><div class="lbl">نمو</div><div class="val">+{seed["analytics"]["week"]["growth_pct"]}%</div></div></div>
        {top_dishes_html}</div>
      </div>

      <div class="zx-section" id="zx-settings">
        <div class="zx-card"><h3>⚙️ إعدادات المطعم</h3>
        <label style="font-size:12px;font-weight:700">اسم المطعم</label>
        <input type="text" value="{seed["branding"]["name"]}" style="width:100%;padding:10px;border:1px solid #e5e7eb;border-radius:8px;margin:6px 0 14px"/>
        <label style="font-size:12px;font-weight:700">الهاتف</label>
        <input type="text" value="{seed["branding"]["phone"]}" style="width:100%;padding:10px;border:1px solid #e5e7eb;border-radius:8px;margin:6px 0 14px"/>
        <label style="font-size:12px;font-weight:700">الإيميل</label>
        <input type="email" value="{seed["branding"]["email"]}" style="width:100%;padding:10px;border:1px solid #e5e7eb;border-radius:8px;margin:6px 0 14px"/>
        <label style="font-size:12px;font-weight:700">العنوان</label>
        <input type="text" value="{seed["branding"]["address"]}" style="width:100%;padding:10px;border:1px solid #e5e7eb;border-radius:8px;margin:6px 0 14px"/>
        <button style="background:#22c55e;color:#fff;padding:10px 24px;border:none;border-radius:8px;font-weight:900;cursor:pointer">حفظ التغييرات</button>
        </div>
      </div>
    </main>
  </div>
</div>

<script>
const ZX_ADMIN_EMAIL = "{admin_email}";
const ZX_ADMIN_PASS = "{admin_password}";
function zxAdminLogin(){{
  const e = document.getElementById('zx-admin-email').value.trim();
  const p = document.getElementById('zx-admin-pass').value.trim();
  if(e === ZX_ADMIN_EMAIL && p === ZX_ADMIN_PASS){{
    localStorage.setItem('zx_admin_session','ok');
    document.getElementById('zx-admin-login-screen').style.display='none';
    document.getElementById('zx-admin-shell').style.display='grid';
    if(!localStorage.getItem('zx_tutorial_done')) zxShowTutorial();
  }} else {{ document.getElementById('zx-admin-err').style.display='block'; }}
}}
function zxAdminLogout(){{ localStorage.removeItem('zx_admin_session'); location.reload(); }}
function zxShow(name, link){{
  document.querySelectorAll('#zx-admin-root .zx-section').forEach(s=>s.classList.remove('active'));
  document.getElementById('zx-'+name)?.classList.add('active');
  document.querySelectorAll('#zx-admin-root .zx-side a').forEach(a=>a.classList.remove('active'));
  if(link) link.classList.add('active');
  document.getElementById('zx-page-title').textContent = link ? link.textContent.replace(/^[^أ-ي]+/,'').trim() : 'نظرة عامة';
}}
function zxShowTutorial(){{
  const overlay = document.createElement('div'); overlay.className='zx-tutorial';
  overlay.innerHTML = '<div class="zx-tutorial-card"><h3>🎉 أهلاً بك في لوحة التحكم</h3><p>كل اللي تحتاجه لإدارة مطعمك في مكان واحد: الطلبات، القائمة، العملاء، السائقين، التقارير. جرّب التنقل من القائمة الجانبية.</p><button onclick="this.closest(\\'.zx-tutorial\\').remove();localStorage.setItem(\\'zx_tutorial_done\\',\\'1\\');">ابدأ الإدارة</button></div>';
  document.body.appendChild(overlay);
}}
// Auto-open on ?admin=1
if (location.search.includes('admin=1')) {{
  document.getElementById('zx-admin-root').classList.add('active');
  if(localStorage.getItem('zx_admin_session')==='ok'){{
    document.getElementById('zx-admin-login-screen').style.display='none';
    document.getElementById('zx-admin-shell').style.display='grid';
  }}
}}
</script>

<!-- ═══ Driver Module ═══ -->
<div id="zx-driver-root">
  <div class="zx-login" id="zx-driver-login-screen">
    <div class="zx-login-card">
      <h2>🛵 تطبيق السائق</h2>
      <p>أدخل رقمك والـ PIN للدخول</p>
      <input type="text" id="zx-driver-phone" placeholder="رقم الهاتف" />
      <input type="password" id="zx-driver-pin" placeholder="PIN (1234)" />
      <button onclick="zxDriverLogin()">دخول</button>
      <div class="zx-login-err" id="zx-driver-err">رقم أو PIN غير صحيح</div>
    </div>
  </div>
  <div class="zx-driver-shell" id="zx-driver-shell" style="display:none">
    <div class="zx-driver-top"><h3 style="font-size:18px;margin-bottom:6px" id="zx-driver-name">السائق</h3><span style="font-size:12px;color:#94a3b8">توصيلات اليوم: <strong id="zx-driver-count">0</strong></span></div>
    <div id="zx-driver-deliveries"></div>
    <button onclick="zxDriverLogout()" style="margin-top:14px;width:100%;padding:12px;background:#ef4444;color:#fff;border:none;border-radius:8px;font-weight:900">تسجيل خروج</button>
  </div>
</div>
<script>
const ZX_DRIVERS = window.ADMIN_DATA?.drivers || [];
const ZX_DRIVER_ORDERS = (window.ADMIN_DATA?.orders || []).filter(o => o.status !== 'تم التسليم');
function zxDriverLogin(){{
  const p = document.getElementById('zx-driver-phone').value.trim();
  const pin = document.getElementById('zx-driver-pin').value.trim();
  const driver = ZX_DRIVERS.find(d => d.phone.replace(/[^0-9]/g,'').endsWith(p.replace(/[^0-9]/g,'').slice(-7)));
  if(driver && pin === '1234'){{
    localStorage.setItem('zx_driver_session', driver.name);
    document.getElementById('zx-driver-login-screen').style.display='none';
    document.getElementById('zx-driver-shell').style.display='block';
    zxRenderDeliveries(driver.name);
  }} else {{ document.getElementById('zx-driver-err').style.display='block'; }}
}}
function zxDriverLogout(){{ localStorage.removeItem('zx_driver_session'); location.reload(); }}
function zxRenderDeliveries(name){{
  document.getElementById('zx-driver-name').textContent = 'مرحباً '+name;
  const my = ZX_DRIVER_ORDERS.filter(o => o.driver === name);
  document.getElementById('zx-driver-count').textContent = my.length;
  const ctr = document.getElementById('zx-driver-deliveries');
  ctr.innerHTML = my.length === 0 ? '<div style="text-align:center;padding:40px;color:#94a3b8">لا توجد توصيلات حالياً</div>' : my.map(o => `
    <div class="zx-delivery">
      <h4>${{o.id}} · ${{o.customer}}</h4>
      <div class="addr">📍 ${{o.address}}</div>
      <div style="font-size:11px;color:#94a3b8;margin-bottom:10px">${{o.items.length}} صنف · ${{o.total}} ر.س · ${{o.payment}}</div>
      <div class="zx-delivery-actions">
        <a class="wa" href="https://wa.me/${{o.phone.replace('+','')}}" target="_blank">واتساب</a>
        <a class="map" href="https://maps.google.com/?q=${{encodeURIComponent(o.address)}}" target="_blank">خريطة</a>
        <button class="status" onclick="this.textContent='تم التسليم ✓';this.style.background='#22c55e';this.style.color='#fff'">${{o.status}}</button>
      </div>
    </div>
  `).join('');
}}
if (location.search.includes('driver=1')) {{
  document.getElementById('zx-driver-root').classList.add('active');
  const sess = localStorage.getItem('zx_driver_session');
  if(sess){{
    document.getElementById('zx-driver-login-screen').style.display='none';
    document.getElementById('zx-driver-shell').style.display='block';
    zxRenderDeliveries(sess);
  }}
}}
</script>
"""


