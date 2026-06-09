"""Data factories for Store / Clinic / Realestate site types.

Each factory returns the SAME shape as restaurant's `seed_restaurant`:
  branding, hours, categories, products, orders, customers, drivers,
  analytics, reviews

This shape is consumed by the SAME admin/cart/footer modules, so we get
6 patterns × 4 types = 24 production-ready sites with one rendering pipeline.

Vocabulary tweaks per type (handled in seed metadata):
  - store:       categories→categories, products→products, orders→orders, drivers→drivers
  - clinic:      categories→specialties, products→services, orders→appointments,
                 customers→patients, drivers→doctors
  - realestate:  categories→property_types, products→listings, orders→inquiries,
                 customers→clients, drivers→agents
"""
from __future__ import annotations
import random
import json
from typing import Any, Dict, List
from collections import Counter

# Import common helpers
from .data_factory import (
    SAUDI_FIRST_NAMES, SAUDI_FAMILIES, SAUDI_CITIES,
    _saudi_name, _saudi_phone, _saudi_address, _unsplash,
)


# ═══════════════════════════════════════════════════════════════════
# STORE (E-commerce)
# ═══════════════════════════════════════════════════════════════════
STORE_CATEGORIES = [
    {"id": "electronics", "name": "إلكترونيات", "desc": "أحدث الأجهزة والإكسسوارات", "img": "photo-1498049794561-7780e7231661"},
    {"id": "fashion",     "name": "أزياء",      "desc": "ملابس وإكسسوارات عصرية",     "img": "photo-1483985988355-763728e1935b"},
    {"id": "beauty",      "name": "تجميل",      "desc": "منتجات العناية والجمال",     "img": "photo-1596462502278-27bfdc403348"},
    {"id": "home",        "name": "منزل",       "desc": "ديكور وأدوات منزلية",        "img": "photo-1556228453-efd6c1ff04f6"},
    {"id": "sports",      "name": "رياضة",      "desc": "معدات رياضية وملابس",         "img": "photo-1571019613454-1cb2f99b2d8b"},
    {"id": "kids",        "name": "أطفال",      "desc": "ألعاب وملابس أطفال",         "img": "photo-1607734834519-d8576ae60ea7"},
]
STORE_PHOTOS = {
    "electronics": ["photo-1505740420928-5e560c06d30e", "photo-1572569511254-d8f925fe2cbb", "photo-1546054454-aa26e2b734c7",
                    "photo-1523275335684-37898b6baf30", "photo-1593642632559-0c6d3fc62b89", "photo-1542751371-adc38448a05e",
                    "photo-1583394838336-acd977736f90", "photo-1517336714731-489689fd1ca8", "photo-1593359677879-a4bb92f829d1",
                    "photo-1572569511254-d8f925fe2cbb"],
    "fashion":     ["photo-1483985988355-763728e1935b", "photo-1542295669297-4d352b042bca", "photo-1485518882345-15568b007407",
                    "photo-1490481651871-ab68de25d43d", "photo-1539109136881-3be0616acf4b", "photo-1576566588028-4147f3842f27",
                    "photo-1503341504253-dff4815485f1", "photo-1591047139829-d91aecb6caea", "photo-1551488831-00ddcb6c6bd3",
                    "photo-1612722432474-b971cdcea546"],
    "beauty":      ["photo-1596462502278-27bfdc403348", "photo-1571781926291-c477ebfd024b", "photo-1522335789203-aaa5224fdb70",
                    "photo-1556228720-195a672e8a03", "photo-1487412947147-5cebf100ffc2", "photo-1599733589046-9b89c87b8c14",
                    "photo-1517637382994-f02da38c6728", "photo-1620916566398-39f1143ab7be", "photo-1631730486572-226d1f595b68",
                    "photo-1571781926291-c477ebfd024b"],
    "home":        ["photo-1556228453-efd6c1ff04f6", "photo-1493663284031-b7e3aefcae8e", "photo-1567538096630-e0c55bd6374c",
                    "photo-1513506003901-1e6a229e2d15", "photo-1583847268964-b28dc8f51f92", "photo-1565793298595-6a879b1d9492",
                    "photo-1556909114-f6e7ad7d3136", "photo-1586023492125-27b2c045efd7", "photo-1567538096630-e0c55bd6374c",
                    "photo-1513519245088-0e12902e5a38"],
    "sports":      ["photo-1571019613454-1cb2f99b2d8b", "photo-1517836357463-d25dfeac3438", "photo-1538805060514-97d9cc17730c",
                    "photo-1517649763962-0c623066013b", "photo-1530549387789-4c1017266635", "photo-1593013820156-3eed3f04e8ce",
                    "photo-1606107557195-0e29a4b5b4aa", "photo-1556909114-f6e7ad7d3136", "photo-1532187863486-abf9dbad1b69",
                    "photo-1571902943202-507ec2618e8f"],
    "kids":        ["photo-1607734834519-d8576ae60ea7", "photo-1566312922674-1e35a59ace00", "photo-1596461404969-9ae70f2830c1",
                    "photo-1471286174890-9c112ffca5b4", "photo-1564429097439-e29ec9d8b1f3", "photo-1503944583220-79d8926ad5e2",
                    "photo-1515488042361-ee00e0ddd4e4", "photo-1559827260-dc66d52bef19", "photo-1545558014-8692077e9b5c",
                    "photo-1596461404969-9ae70f2830c1"],
}
STORE_PRODUCTS = {
    "electronics": [
        ("سماعات AirPods Pro 2", 999, "سماعات لاسلكية بإلغاء الضوضاء النشط، صوت مكاني، مقاومة للماء", ["ANC", "Spatial Audio", "حلال"]),
        ("ساعة Apple Watch S9", 1450, "تتبع لياقة، ECG، مكالمات، GPS، شاشة 49mm", ["GPS", "ECG"]),
        ("لابتوب MacBook Air M3", 5499, "13.6 إنش، 16GB RAM، 512GB SSD، Retina display", ["M3", "16GB"]),
        ("ايفون 15 Pro Max", 6299, "256GB، تيتانيوم، كاميرا 48MP، A17 Pro", ["5G", "48MP"]),
        ("ايباد Air M2 11 إنش", 2799, "256GB، شاشة Liquid Retina، Apple Pencil compatible", ["M2"]),
        ("Samsung Galaxy S24 Ultra", 5899, "256GB، كاميرا 200MP، S Pen، AI features", ["AI", "200MP"]),
        ("PlayStation 5 Slim", 2199, "1TB SSD، Disc edition، 4K gaming", ["4K"]),
        ("سماعات Sony WH-1000XM5", 1499, "أفضل إلغاء ضوضاء، 30 ساعة بطارية", ["ANC", "Hi-Res"]),
        ("شاشة LG OLED C3 55 إنش", 4499, "4K OLED، 120Hz، HDR، Dolby Vision", ["4K", "OLED"]),
        ("كاميرا Canon EOS R6 Mark II", 9899, "Mirrorless فل فريم، 24MP، 4K 60fps", ["4K", "Full Frame"]),
    ],
    "fashion": [
        ("ثوب رجالي صيفي", 285, "قطن مصري 100%، صنع سعودي، أبيض كلاسيكي", ["قطن", "صيفي"]),
        ("غترة شماغ بلون أبيض", 145, "قماش فاخر، تطريز يدوي، مقاس قياسي", ["مصنوع سعودي"]),
        ("عقال أسود مذهب", 89, "حرير وذهب، حافة منقوشة", ["فاخر"]),
        ("نظارة Ray-Ban Aviator", 750, "ذهبية، عدسات بنية متدرجة، أصلي 100%", ["UV400"]),
        ("ساعة Casio G-Shock", 690, "مقاومة الصدمات والماء، رقمية وعقارب", ["مقاوم ماء"]),
        ("حذاء Nike Air Max 2024", 599, "ركض وكاجوال، Air technology، تصميم 2024", ["خفيف"]),
        ("حقيبة كروس Coach", 1290, "جلد طبيعي، تصميم عصري، 3 جيوب", ["جلد"]),
        ("تيشيرت Polo Ralph Lauren", 320, "قطن 100%، خياطة فاخرة، 6 ألوان", ["قطن"]),
        ("بنطلون جينز Levi's 501", 380, "كلاسيكي مستقيم، قطن صلب، مقاس مرن", ["جينز"]),
        ("حذاء رسمي إيطالي", 850, "جلد إيطالي أصلي، خياطة يدوية، أسود", ["جلد", "إيطالي"]),
    ],
    "beauty": [
        ("سيروم فيتامين C", 245, "20% فيتامين C، حمض الهيالورونيك، 30ml", ["VitC", "30ml"]),
        ("كريم مرطّب لاروش بوزيه", 189, "للبشرة الحساسة، 50ml، خالٍ من العطر", ["حساسة"]),
        ("ماسكارا ميبيلين Lash Sensational", 75, "حجم وكثافة، مقاوم للماء، أسود", ["مقاوم ماء"]),
        ("أحمر شفاه ماك Ruby Woo", 195, "مات، أحمر كلاسيكي، يدوم 8 ساعات", ["مات"]),
        ("عطر شانيل No.5 EDP 100ml", 1450, "العطر الكلاسيكي الفاخر، نسائي", ["EDP", "كلاسيكي"]),
        ("عطر Tom Ford Tobacco Vanille", 1890, "شرقي دافئ، 100ml، رجالي ونسائي", ["شرقي"]),
        ("مجفف شعر Dyson Supersonic", 1899, "تقنية متطورة، حماية للشعر، 3 مستويات", ["Dyson"]),
        ("بالم شفاه فازلين", 22, "ترطيب 48 ساعة، 4 ألوان طبيعية", ["مرطّب"]),
        ("كحل غمزة Kohl أصلي", 35, "كحل عربي تقليدي، أسود غامق، عبوة فضية", ["تقليدي"]),
        ("ماسك طين أخضر", 89, "تنظيف عميق، يزيل الزيوت، 150ml", ["طين"]),
    ],
    "home": [
        ("مكنسة Dyson V15", 3290, "لاسلكية، كشف ليزر، 60 دقيقة، فلتر HEPA", ["لاسلكية"]),
        ("روبوت تنظيف iRobot Roomba j7+", 2899, "ذكاء اصطناعي، خرائط، تفريغ ذاتي", ["AI"]),
        ("مكنسة Roborock S8 Pro", 2499, "مسح ومسح بالماء، تنقيب 6000Pa", ["مسح ماء"]),
        ("فرن Smeg Retro 60cm", 4599, "تصميم ريترو إيطالي، 80L، 11 وظيفة", ["إيطالي"]),
        ("ميكروويف LG NeoChef 42L", 949, "مع شواية، Smart Inverter، 1100W", ["شواية"]),
        ("Air Fryer Philips XXL", 729, "5.6L، بدون زيت، 13 برنامج تلقائي", ["صحي"]),
        ("غسالة LG 12kg مع مجفف", 4799, "ذكية، WiFi، AI Direct Drive، بخار", ["WiFi"]),
        ("ثلاجة Samsung Side-by-Side", 8499, "600L، ماء بارد وثلج، شاشة لمس", ["Smart"]),
        ("مكواة Tefal Express Steam", 569, "بخار 6 بار، خزان 1.5L، تنقية تلقائية", ["6 bar"]),
        ("سيت أواني WMF Function 4 12 قطعة", 2890, "ستانلس ستيل، ألماني، 4 وظائف", ["ألماني"]),
    ],
    "sports": [
        ("جهاز جري NordicTrack X22i", 11500, "شاشة 22 إنش HD، iFit، انحدار 40%", ["HD"]),
        ("دراجة Peloton Bike+", 8990, "بث مباشر، شاشة دوارة، 100+ مدرّب", ["Peloton"]),
        ("أوزان دامبل قابلة للتعديل 2-24 كجم", 890, "بنوب التحويل، توفر مساحة، زوج", ["قابل للتعديل"]),
        ("حصيرة يوغا Lululemon 5mm", 295, "مقاومة للانزلاق، طبيعية، 5mm سُمك", ["يوغا"]),
        ("كرة سلة Spalding Official NBA", 240, "حجم 7 رسمي، جلد مركب، داخل وخارج", ["NBA"]),
        ("سكوتر كهربائي Xiaomi Pro 4", 1990, "45km مدى، 25km/سرعة، مقاوم ماء", ["كهربائي"]),
        ("ساعة Garmin Forerunner 965", 2450, "GPS متعدد الترددات، AMOLED، 31 رياضة", ["GPS"]),
        ("حذاء Adidas Ultraboost 24", 749, "ركض طويل، رغوة Boost، تصميم 2024", ["Boost"]),
        ("حقيبة جيم Under Armour", 245, "60L، مقاومة ماء، 5 جيوب", ["60L"]),
        ("شاكر ذكي PROMiXX", 195, "بطارية، خلط تلقائي، 600ml", ["ذكي"]),
    ],
    "kids": [
        ("LEGO Star Wars Millennium Falcon", 1299, "+7300 قطعة، تشكيل تفصيلي، 16+ سنة", ["LEGO"]),
        ("ألعاب بليستيشن للأطفال (4 ألعاب)", 590, "حزمة عائلية، PEGI 3+، متعة لكل الأعمار", ["PS5"]),
        ("دراجة BMX 16 إنش", 450, "للأطفال 5-9 سنوات، عجلات تدريب", ["دراجة"]),
        ("روبوت تعليمي Anki Vector", 1290, "ذكاء اصطناعي، يتعرّف على الأشخاص، يتعلّم", ["AI"]),
        ("كرسي سيارة Maxi-Cosi", 1290, "ISOFIX، من الولادة حتى 4 سنوات، 5 مستويات أمان", ["ISOFIX"]),
        ("عربة أطفال Babyzen YOYO 2", 2899, "قابلة للطي، خفيفة 6kg، تناسب الطيران", ["خفيف"]),
        ("تيشيرت Disney Frozen للبنات", 89, "قطن 100%، مقاس 4-10، ألوان متعددة", ["Disney"]),
        ("حذاء Skechers Lights للأولاد", 245, "أضواء LED، تصميم رياضي، 6 ألوان", ["LED"]),
        ("لعبة ميجا بلوكس 80 قطعة", 145, "قطع كبيرة آمنة، +1 سنة، تخزين بالحقيبة", ["1+"]),
        ("سيارة كهربائية للأطفال 12V", 1290, "تشغيل بمفتاح، ريموت للأهل، صوت ومحرّك", ["12V"]),
    ],
}


# ═══════════════════════════════════════════════════════════════════
# CLINIC (Medical)
# ═══════════════════════════════════════════════════════════════════
CLINIC_CATEGORIES = [  # specialties
    {"id": "cardiology",  "name": "أمراض القلب",   "desc": "تشخيص وعلاج أمراض القلب",         "img": "photo-1559757148-5c350d0d3c56"},
    {"id": "dental",      "name": "طب الأسنان",    "desc": "تنظيف، تقويم، زراعة، تجميل",       "img": "photo-1606811971618-4486d14f3f99"},
    {"id": "pediatric",   "name": "طب الأطفال",    "desc": "رعاية شاملة للأطفال من الولادة",   "img": "photo-1576091160550-2173dba999ef"},
    {"id": "dermatology", "name": "الجلدية",       "desc": "بشرة وشعر وأمراض الجلد",           "img": "photo-1612349317150-e413f6a5b16d"},
    {"id": "internal",    "name": "الباطنة",        "desc": "السكر، الضغط، الأمراض المزمنة",   "img": "photo-1581595220892-b0739db3ba8c"},
    {"id": "ophthalmology","name": "العيون",       "desc": "فحص، نظارات، جراحة الليزر",        "img": "photo-1577401239170-897942555fb3"},
]
CLINIC_SERVICES = {
    "cardiology": [
        ("استشارة طبيب قلب", 350, "كشف وفحص ECG"), ("تخطيط القلب ECG", 180, "تخطيط شامل"),
        ("إيكو القلب", 480, "صورة بالموجات فوق الصوتية"), ("اختبار الجهد", 590, "تحت إشراف الطبيب"),
        ("هولتر 24 ساعة", 690, "تسجيل نبضات 24h"), ("استشارة متابعة", 200, "للحالات المعروفة"),
        ("فحص شامل للقلب", 1290, "ECG + إيكو + اختبار جهد"), ("ضبط الأدوية", 200, "متابعة الأدوية"),
        ("استشارة عن بُعد", 250, "زووم 30 دقيقة"), ("تقرير طبي رسمي", 150, "ختم وتوقيع"),
    ],
    "dental": [
        ("تنظيف أسنان", 250, "تنظيف وتلميع"), ("حشوة كومبوزيت", 200, "بلون السن"),
        ("سحب عصب", 850, "علاج جذور كامل"), ("تقويم شفاف Invisalign", 12500, "خطة كاملة 18 شهر"),
        ("تبييض أسنان", 850, "زووم بليتش جلسة"), ("زراعة سن (Implant)", 4500, "تيتانيوم سويسري"),
        ("ابتسامة هوليوود (فينير)", 1290, "السن الواحد"), ("استشارة أولى", 100, "كشف وأشعة"),
        ("علاج اللثة", 590, "قشط الجذور"), ("خلع ضرس العقل", 690, "تخدير موضعي"),
    ],
    "pediatric": [
        ("كشف طبيب أطفال", 250, "فحص شامل"), ("تطعيم (Vaccine)", 180, "حسب جدول الوزارة"),
        ("استشارة تغذية الرضع", 200, "خطة غذائية مخصصة"), ("علاج البرد والحرارة", 200, "كشف ووصفة"),
        ("استشارة عن بُعد", 150, "زووم 30 دقيقة"), ("متابعة نمو وتطور", 220, "للأطفال 0-3 سنوات"),
        ("علاج التهابات الأذن", 250, "كشف ووصفة"), ("شهادة طبية مدرسية", 100, "للمدارس"),
        ("استشارة مغص الرضع", 200, "حلول وعلاج"), ("تطعيمات السفر", 280, "حسب الوجهة"),
    ],
    "dermatology": [
        ("استشارة جلدية", 300, "كشف وتشخيص"), ("علاج حب الشباب", 450, "جلسة + علاج موضعي"),
        ("ليزر إزالة الشعر (وجه)", 350, "جلسة"), ("ليزر إزالة الشعر (الجسم كامل)", 1290, "جلسة"),
        ("بوتوكس", 1290, "20 وحدة"), ("فيلر شفايف", 1490, "1ml"),
        ("هايفو لشد الوجه", 2900, "جلسة كاملة"), ("علاج تساقط الشعر PRP", 890, "جلسة"),
        ("ميزو ثيرابي للبشرة", 690, "جلسة"), ("علاج التصبّغات", 590, "جلسة"),
    ],
    "internal": [
        ("كشف باطنية", 280, "فحص شامل"), ("تحاليل دم شاملة", 450, "30 تحليل"),
        ("متابعة سكري", 220, "كل 3 أشهر"), ("متابعة ضغط دم", 200, "كل شهر"),
        ("استشارة بدانة", 350, "خطة غذائية ودوائية"), ("علاج القولون العصبي", 290, "كشف ووصفة"),
        ("تقرير طبي شامل", 250, "للسفر/التأمين"), ("استشارة عن بُعد", 200, "زووم 30 دقيقة"),
        ("متابعة كولسترول", 220, "تحليل ومتابعة"), ("علاج أنيميا", 290, "تشخيص وعلاج"),
    ],
    "ophthalmology": [
        ("فحص نظر شامل", 200, "قياس وإعطاء نظارة"), ("جراحة الليزك", 4900, "العينين، تقنية Z-LASIK"),
        ("استشارة جلوكوما", 350, "قياس ضغط العين"), ("علاج جفاف العين", 290, "كشف وعلاج"),
        ("فحص قاع العين", 250, "للسكريين"), ("علاج التهاب العين", 200, "كشف ووصفة"),
        ("عدسات لاصقة سنوية", 990, "زوج لمدة سنة"), ("نظارة شمسية طبية", 1290, "Ray-Ban أصلي"),
        ("استشارة الأطفال", 280, "فحص وعلاج"), ("تقرير طبي للقيادة", 150, "للحصول على رخصة"),
    ],
}


# ═══════════════════════════════════════════════════════════════════
# REALESTATE
# ═══════════════════════════════════════════════════════════════════
REALESTATE_CATEGORIES = [  # property types
    {"id": "villa",      "name": "فلل",      "desc": "فلل سكنية فاخرة",        "img": "photo-1564013799919-ab600027ffc6"},
    {"id": "apartment",  "name": "شقق",      "desc": "شقق سكنية حديثة",        "img": "photo-1522708323590-d24dbb6b0267"},
    {"id": "land",       "name": "أراضٍ",    "desc": "أراضي سكنية وتجارية",    "img": "photo-1500382017468-9049fed747ef"},
    {"id": "commercial", "name": "تجاري",    "desc": "مكاتب ومحلات تجارية",     "img": "photo-1486406146926-c627a92ad1ab"},
    {"id": "rent",       "name": "للإيجار",  "desc": "وحدات للإيجار الشهري",    "img": "photo-1502672260266-1c1ef2d93688"},
    {"id": "luxury",     "name": "فاخر",     "desc": "قصور وفلل مميزة",         "img": "photo-1613490493576-7fde63acd811"},
]
REALESTATE_PROPERTIES = {
    "villa": [
        ("فيلا 5 غرف - حي الياسمين", 2900000, "فيلا حديثة بمسبح وحديقة، 480 م²، 6 حمامات، 3 صالات",
         {"bedrooms": 5, "bathrooms": 6, "area_sqm": 480, "city": "الرياض"}),
        ("فيلا 4 غرف - حي النخيل", 2450000, "تشطيب فاخر، حديقة 100م، مدخلين منفصلين، 380م²",
         {"bedrooms": 4, "bathrooms": 5, "area_sqm": 380, "city": "الرياض"}),
        ("فيلا 6 غرف - حي الملقا", 3490000, "أرضي + علوي + ملحق + مسبح، 560 م²",
         {"bedrooms": 6, "bathrooms": 7, "area_sqm": 560, "city": "الرياض"}),
        ("فيلا 4 غرف - جدة الشاطئ", 3200000, "إطلالة بحرية مباشرة، تشطيب أوروبي، 420م²",
         {"bedrooms": 4, "bathrooms": 5, "area_sqm": 420, "city": "جدة"}),
        ("فيلا 5 غرف - الخبر", 2150000, "هادئة وعائلية، حدائق، مواقف، 400 م²",
         {"bedrooms": 5, "bathrooms": 5, "area_sqm": 400, "city": "الخبر"}),
        ("فيلا 7 غرف - شمال الرياض", 4990000, "قصر صغير، مسبح خارجي + داخلي، 720 م²",
         {"bedrooms": 7, "bathrooms": 8, "area_sqm": 720, "city": "الرياض"}),
        ("فيلا 3 غرف - حي الورود", 1450000, "اقتصادية للعائلة الصغيرة، 280 م²",
         {"bedrooms": 3, "bathrooms": 4, "area_sqm": 280, "city": "الرياض"}),
        ("فيلا 5 غرف - النموذجية", 1890000, "تصميم نموذجي، تشطيب لوكس، 360م²",
         {"bedrooms": 5, "bathrooms": 5, "area_sqm": 360, "city": "الدمام"}),
        ("فيلا دوبلكس 4 غرف", 1980000, "دوبلكس مودرن، حديقة خلفية، 340م²",
         {"bedrooms": 4, "bathrooms": 4, "area_sqm": 340, "city": "الرياض"}),
        ("فيلا 6 غرف - حي العقيق", 3290000, "بمسبح + 4 مواقف، تشطيب راقي، 520 م²",
         {"bedrooms": 6, "bathrooms": 6, "area_sqm": 520, "city": "الرياض"}),
    ],
    "apartment": [
        ("شقة 3 غرف - حي العليا", 850000, "120 م²، إطلالة شارع، مصعد، حارس", {"bedrooms": 3, "bathrooms": 2, "area_sqm": 120, "city": "الرياض"}),
        ("شقة 4 غرف - حي الملقا", 1250000, "160 م²، مودرن، تشطيب أوروبي", {"bedrooms": 4, "bathrooms": 3, "area_sqm": 160, "city": "الرياض"}),
        ("شقة 2 غرفة - الأمير سلطان", 580000, "85 م²، مفروشة، جاهزة للسكن", {"bedrooms": 2, "bathrooms": 2, "area_sqm": 85, "city": "الرياض"}),
        ("شقة 3 غرف - جدة - الشاطئ", 1190000, "إطلالة بحرية، 140م²، طابق علوي", {"bedrooms": 3, "bathrooms": 3, "area_sqm": 140, "city": "جدة"}),
        ("شقة 4 غرف - الخبر", 920000, "حي راقي، 175 م²، 4 حمامات", {"bedrooms": 4, "bathrooms": 4, "area_sqm": 175, "city": "الخبر"}),
        ("بنتهاوس 4 غرف", 2890000, "240م²، شرفة 100م، إطلالة بانورامية", {"bedrooms": 4, "bathrooms": 4, "area_sqm": 240, "city": "الرياض"}),
        ("شقة 3 غرف - حي النرجس", 690000, "115 م²، تشطيب حديث، قريبة من الخدمات", {"bedrooms": 3, "bathrooms": 2, "area_sqm": 115, "city": "الرياض"}),
        ("شقة 1 غرفة - استوديو", 320000, "60 م²، استوديو فاخر، للعزاب", {"bedrooms": 1, "bathrooms": 1, "area_sqm": 60, "city": "الرياض"}),
        ("شقة 5 غرف - دوبلكس", 1690000, "200م²، 5 غرف، 2 صالة، شرفتين", {"bedrooms": 5, "bathrooms": 4, "area_sqm": 200, "city": "جدة"}),
        ("شقة 3 غرف - مدينة الملك عبدالله", 990000, "145م²، تشطيب فاخر، مجمّع سكني", {"bedrooms": 3, "bathrooms": 3, "area_sqm": 145, "city": "جدة"}),
    ],
    "land": [
        ("أرض سكنية 600م - الياسمين", 1800000, "زاوية، شارعين، فلل من حولها", {"area_sqm": 600, "city": "الرياض"}),
        ("أرض سكنية 1000م - الملقا", 3500000, "شارع 30، بمخطط راقي", {"area_sqm": 1000, "city": "الرياض"}),
        ("أرض تجارية 500م - طريق الملك فهد", 4500000, "تجاري راقي، مرور كثيف", {"area_sqm": 500, "city": "الرياض"}),
        ("أرض زراعية 5000م - الخرج", 950000, "زراعة محاصيل، بئر ماء، كهرباء", {"area_sqm": 5000, "city": "الخرج"}),
        ("أرض سكنية 750م - جدة", 2100000, "حي الشاطئ، قريب من الكورنيش", {"area_sqm": 750, "city": "جدة"}),
        ("أرض 1500م - الدمام", 2890000, "مخطط سكني جديد، خدمات كاملة", {"area_sqm": 1500, "city": "الدمام"}),
        ("أرض زاوية 800م - الرياض", 2890000, "زاوية رئيسية، 3 واجهات", {"area_sqm": 800, "city": "الرياض"}),
        ("أرض استثمارية 2000م", 5900000, "خام، قابلة للتقسيم، عائد ممتاز", {"area_sqm": 2000, "city": "الرياض"}),
        ("أرض صغيرة 400م - النخيل", 980000, "للبناء عائلي، شارع 20", {"area_sqm": 400, "city": "الرياض"}),
        ("أرض 1200م - حي العقيق", 3490000, "شمال الرياض، تطوير عمراني سريع", {"area_sqm": 1200, "city": "الرياض"}),
    ],
    "commercial": [
        ("محل تجاري 80م - شارع التحلية", 1990000, "موقع مميز، تشطيب لوكس", {"area_sqm": 80, "city": "الرياض"}),
        ("مكتب 200م - برج المملكة", 3500000, "إطلالة على الرياض، خدمات 24h", {"area_sqm": 200, "city": "الرياض"}),
        ("مستودع 1000م - منطقة صناعية", 2900000, "ارتفاع 8م، رصيف تحميل، مكاتب", {"area_sqm": 1000, "city": "الرياض"}),
        ("معرض سيارات 500م", 4500000, "واجهة 50م، طريق الملك فهد", {"area_sqm": 500, "city": "الرياض"}),
        ("مكتب 150م - حي العليا", 1890000, "جاهز للاستخدام، أثاث كامل", {"area_sqm": 150, "city": "الرياض"}),
        ("محل 60م - الورود", 890000, "مناسب للعيادات والمكاتب", {"area_sqm": 60, "city": "الرياض"}),
        ("مكتب طبي 100م", 1690000, "مجهّز للعيادة، قسم استقبال", {"area_sqm": 100, "city": "جدة"}),
        ("معرض كبير 800م - الدمام", 3590000, "شامل ساحة عرض ومكاتب", {"area_sqm": 800, "city": "الدمام"}),
        ("محل سوبر ماركت 250م", 1490000, "موقع سكني نشط، عائد 8%", {"area_sqm": 250, "city": "الرياض"}),
        ("بناء تجاري كامل 1500م", 12900000, "5 طوابق + بدروم + موقف", {"area_sqm": 1500, "city": "الرياض"}),
    ],
    "rent": [
        ("شقة 3 غرف للإيجار - العليا", 45000, "سنوي، مفروشة، 130م²", {"bedrooms": 3, "bathrooms": 2, "area_sqm": 130, "city": "الرياض", "rent_period": "سنوي"}),
        ("فيلا 5 غرف للإيجار - الياسمين", 120000, "سنوي، مع مسبح، 450م²", {"bedrooms": 5, "bathrooms": 6, "area_sqm": 450, "city": "الرياض", "rent_period": "سنوي"}),
        ("شقة 2 غرفة - الورود", 28000, "سنوي، 75م²، تشطيب جيد", {"bedrooms": 2, "bathrooms": 1, "area_sqm": 75, "city": "الرياض", "rent_period": "سنوي"}),
        ("شقة استوديو - النموذجية", 1800, "شهري، مفروش، 50م²", {"bedrooms": 1, "bathrooms": 1, "area_sqm": 50, "city": "الرياض", "rent_period": "شهري"}),
        ("فيلا 4 غرف - جدة الشاطئ", 95000, "سنوي، إطلالة بحرية", {"bedrooms": 4, "bathrooms": 4, "area_sqm": 360, "city": "جدة", "rent_period": "سنوي"}),
        ("شقة 3 غرف للإيجار - الخبر", 38000, "سنوي، 120م²، تشطيب حديث", {"bedrooms": 3, "bathrooms": 2, "area_sqm": 120, "city": "الخبر", "rent_period": "سنوي"}),
        ("مكتب 80م - حي العليا", 38000, "سنوي، جاهز، مع موقف", {"area_sqm": 80, "city": "الرياض", "rent_period": "سنوي"}),
        ("محل تجاري 50م - التحلية", 89000, "سنوي، موقع نشط", {"area_sqm": 50, "city": "الرياض", "rent_period": "سنوي"}),
        ("غرفة في فيلا مشتركة", 2200, "شهري، مع خدمات", {"bedrooms": 1, "bathrooms": 1, "area_sqm": 25, "city": "الرياض", "rent_period": "شهري"}),
        ("شاليه ساحلي - جدة", 1500, "يومي، 3 غرف، حمام سباحة", {"bedrooms": 3, "bathrooms": 2, "area_sqm": 200, "city": "جدة", "rent_period": "يومي"}),
    ],
    "luxury": [
        ("قصر 12 غرفة - شمال الرياض", 25000000, "1200م²، مسبح أولمبي، 3 مجالس", {"bedrooms": 12, "bathrooms": 14, "area_sqm": 1200, "city": "الرياض"}),
        ("فيلا فاخرة 8 غرف - حي الياسمين", 8900000, "800م²، تصميم إيطالي، مصعد", {"bedrooms": 8, "bathrooms": 9, "area_sqm": 800, "city": "الرياض"}),
        ("بنتهاوس فاخر - جدة", 6500000, "350م²، إطلالة بانورامية، حوض سباحة خاص", {"bedrooms": 4, "bathrooms": 5, "area_sqm": 350, "city": "جدة"}),
        ("قصر تاريخي مرمّم", 12900000, "1500م²، حديقة 800م، أثاث أنتيك", {"bedrooms": 10, "bathrooms": 12, "area_sqm": 1500, "city": "الرياض"}),
        ("فيلا حصرية - مدينة الملك عبدالله", 5990000, "تصميم معماري حصري، 650م²", {"bedrooms": 6, "bathrooms": 7, "area_sqm": 650, "city": "جدة"}),
        ("قصر ساحلي - جدة الشمال", 18900000, "إطلالة بحرية مباشرة، مرسى خاص", {"bedrooms": 10, "bathrooms": 12, "area_sqm": 1800, "city": "جدة"}),
        ("فيلا ذكية بالكامل (Smart)", 7290000, "كل الإضاءة والتكييف بالتطبيق، 580م²", {"bedrooms": 6, "bathrooms": 7, "area_sqm": 580, "city": "الرياض"}),
        ("بنتهاوس برج المملكة", 9890000, "إطلالة 360°، 280م²، خدمات الفندق", {"bedrooms": 3, "bathrooms": 4, "area_sqm": 280, "city": "الرياض"}),
        ("قصر تراثي - الدرعية", 16900000, "تراث نجدي مرمم، حدائق ومسجد خاص", {"bedrooms": 9, "bathrooms": 10, "area_sqm": 1400, "city": "الرياض"}),
        ("فيلا حديثة بحمام سباحة داخلي", 10500000, "750م²، تكييف مركزي ذكي", {"bedrooms": 7, "bathrooms": 8, "area_sqm": 750, "city": "الرياض"}),
    ],
}
REALESTATE_PHOTOS = {
    "villa":      ["photo-1564013799919-ab600027ffc6", "photo-1613490493576-7fde63acd811", "photo-1583608205776-bfd35f0d9f83",
                   "photo-1600596542815-ffad4c1539a9", "photo-1605276374104-dee2a0ed3cd6", "photo-1571055107559-3e67626fa8be",
                   "photo-1582268611958-ebfd161ef9cf", "photo-1568605114967-8130f3a36994", "photo-1600585154340-be6161a56a0c",
                   "photo-1600596542815-ffad4c1539a9"],
    "apartment":  ["photo-1522708323590-d24dbb6b0267", "photo-1502672260266-1c1ef2d93688", "photo-1493809842364-78817add7ffb",
                   "photo-1560448204-e02f11c3d0e2", "photo-1502672023488-70e25813eb80", "photo-1554995207-c18c203602cb",
                   "photo-1560185007-cde436f6a4d0", "photo-1567496898669-ee935f5f647a", "photo-1493809842364-78817add7ffb",
                   "photo-1502672260266-1c1ef2d93688"],
    "land":       ["photo-1500382017468-9049fed747ef", "photo-1501785888041-af3ef285b470", "photo-1518495973542-4542c06a5843",
                   "photo-1500382017468-9049fed747ef", "photo-1465146344425-f00d5f5c8f07", "photo-1542273917363-3b1817f69a2d",
                   "photo-1518495973542-4542c06a5843", "photo-1574263867128-a3d5c1b1deae", "photo-1518495973542-4542c06a5843",
                   "photo-1542273917363-3b1817f69a2d"],
    "commercial": ["photo-1486406146926-c627a92ad1ab", "photo-1497366754035-f200968a6e72", "photo-1497366216548-37526070297c",
                   "photo-1564540583246-934409427776", "photo-1497366811353-6870744d04b2", "photo-1556761175-5973dc0f32e7",
                   "photo-1497366216548-37526070297c", "photo-1486406146926-c627a92ad1ab", "photo-1497366754035-f200968a6e72",
                   "photo-1604328698692-f76ea9498e76"],
    "rent":       ["photo-1502672260266-1c1ef2d93688", "photo-1522708323590-d24dbb6b0267", "photo-1493809842364-78817add7ffb",
                   "photo-1560448204-e02f11c3d0e2", "photo-1502672023488-70e25813eb80", "photo-1554995207-c18c203602cb",
                   "photo-1560185007-cde436f6a4d0", "photo-1567496898669-ee935f5f647a", "photo-1564013799919-ab600027ffc6",
                   "photo-1583608205776-bfd35f0d9f83"],
    "luxury":     ["photo-1613490493576-7fde63acd811", "photo-1582268611958-ebfd161ef9cf", "photo-1600596542815-ffad4c1539a9",
                   "photo-1564013799919-ab600027ffc6", "photo-1571055107559-3e67626fa8be", "photo-1605276374104-dee2a0ed3cd6",
                   "photo-1600585154340-be6161a56a0c", "photo-1568605114967-8130f3a36994", "photo-1583608205776-bfd35f0d9f83",
                   "photo-1613490493576-7fde63acd811"],
}


# ═══════════════════════════════════════════════════════════════════
# Common utilities
# ═══════════════════════════════════════════════════════════════════
def _build_products_store(seed_name: str) -> tuple[List[Dict], List[Dict]]:
    """Returns (categories, products) for a store seed."""
    random.seed(seed_name)
    categories = [{**c, "img": _unsplash(c["img"], 800)} for c in STORE_CATEGORIES]
    products = []
    pid = 1
    for cat in categories:
        photos = STORE_PHOTOS[cat["id"]]
        templates = STORE_PRODUCTS[cat["id"]]
        for i, (name, price, desc, tags) in enumerate(templates):
            products.append({
                "id": f"p{pid}", "category": cat["id"], "name": name, "price": price,
                "calories": 0,  # n/a for store but kept for shape compat
                "desc": desc, "ingredients": [],
                "tags": tags + (["جديد"] if i < 2 else []),
                "img": _unsplash(photos[i % len(photos)], 1000),
                "prep_time": "توصيل خلال 1-3 أيام",
                "rating": round(4.2 + random.random() * 0.7, 1),
                "reviews_count": random.randint(15, 280),
                "is_new": i < 2, "is_popular": i in (2, 5, 8),
                "stock": random.randint(5, 200),
            })
            pid += 1
    return categories, products


def _build_products_clinic(seed_name: str) -> tuple[List[Dict], List[Dict]]:
    random.seed(seed_name)
    categories = [{**c, "img": _unsplash(c["img"], 800)} for c in CLINIC_CATEGORIES]
    products = []
    pid = 1
    photo_for = {"cardiology":"photo-1559757148-5c350d0d3c56","dental":"photo-1606811971618-4486d14f3f99",
                 "pediatric":"photo-1576091160550-2173dba999ef","dermatology":"photo-1612349317150-e413f6a5b16d",
                 "internal":"photo-1581595220892-b0739db3ba8c","ophthalmology":"photo-1577401239170-897942555fb3"}
    for cat in categories:
        templates = CLINIC_SERVICES[cat["id"]]
        for i, (name, price, desc) in enumerate(templates):
            products.append({
                "id": f"p{pid}", "category": cat["id"], "name": name, "price": price,
                "calories": 0, "desc": desc, "ingredients": [],
                "tags": [cat["name"], "موعد سريع"],
                "img": _unsplash(photo_for[cat["id"]], 800),
                "prep_time": f"المدة: {30 + i * 5} دقيقة",
                "rating": round(4.3 + random.random() * 0.6, 1),
                "reviews_count": random.randint(20, 280),
                "is_new": i < 2, "is_popular": i in (2, 5),
            })
            pid += 1
    return categories, products


def _build_products_realestate(seed_name: str) -> tuple[List[Dict], List[Dict]]:
    random.seed(seed_name)
    categories = [{**c, "img": _unsplash(c["img"], 800)} for c in REALESTATE_CATEGORIES]
    products = []
    pid = 1
    for cat in categories:
        photos = REALESTATE_PHOTOS[cat["id"]]
        templates = REALESTATE_PROPERTIES[cat["id"]]
        for i, (name, price, desc, meta) in enumerate(templates):
            tags = []
            if "bedrooms" in meta:
                tags.append(f"{meta['bedrooms']} غرف")
            if "bathrooms" in meta:
                tags.append(f"{meta['bathrooms']} حمام")
            if "area_sqm" in meta:
                tags.append(f"{meta['area_sqm']} م²")
            if meta.get("rent_period"):
                tags.append(f"إيجار {meta['rent_period']}")
            products.append({
                "id": f"p{pid}", "category": cat["id"], "name": name, "price": price,
                "calories": 0, "desc": desc, "ingredients": [],
                "tags": tags + (["مميز"] if i in (0, 2, 5) else []),
                "img": _unsplash(photos[i % len(photos)], 1200),
                "prep_time": f"متاح فوراً · {meta.get('city','الرياض')}",
                "rating": round(4.4 + random.random() * 0.5, 1),
                "reviews_count": random.randint(5, 80),
                "is_new": i < 2, "is_popular": i in (2, 5, 8),
                "meta": meta,
            })
            pid += 1
    return categories, products


def _build_orders(products: List[Dict], type_id: str, n: int = 30) -> List[Dict]:
    """Orders/appointments/inquiries."""
    if type_id == "clinic":
        statuses = ["مؤكد", "بانتظار التأكيد", "قيد المعالجة", "مكتمل"]
        payments = ["مدى", "Visa", "تأمين بوبا", "تأمين الراجحي", "كاش"]
    elif type_id == "realestate":
        statuses = ["استفسار جديد", "تواصل", "جولة مجدولة", "مغلق - متابعة"]
        payments = ["استفسار", "زيارة", "مفاوضة", "عرض رسمي"]
    else:  # store/restaurant
        statuses = ["تم الاستلام", "قيد التحضير", "في الطريق", "تم التسليم"]
        payments = ["مدى", "Visa", "STC Pay", "Apple Pay", "كاش عند الاستلام"]
    drivers_pool = ["أحمد السبيعي", "خالد العتيبي", "سلطان القحطاني", "فيصل الشمري", "بدر الدوسري"]
    orders = []
    for i in range(n):
        items = random.sample(products, random.randint(1, 3))
        order_items = [{"name": p["name"], "qty": random.randint(1, 2), "price": p["price"]} for p in items]
        total = sum(it["qty"] * it["price"] for it in order_items)
        orders.append({
            "id": f"ORD-{1000 + i}",
            "customer": _saudi_name(),
            "phone": _saudi_phone(),
            "items": order_items,
            "total": total,
            "status": random.choice(statuses),
            "time": random.choice(["قبل 5 دقائق", "قبل 12 دقيقة", "قبل ساعة", "قبل 3 ساعات", "اليوم", "أمس"]),
            "payment": random.choice(payments),
            "address": _saudi_address(),
            "driver": random.choice(drivers_pool),
        })
    return orders


def _build_customers(n: int = 20) -> List[Dict]:
    customers = []
    for i in range(n):
        n_orders = random.randint(1, 35)
        avg = random.randint(45, 280)
        customers.append({
            "name": _saudi_name(),
            "phone": _saudi_phone(),
            "total_orders": n_orders,
            "total_spent": n_orders * avg,
            "last_order": random.choice(["اليوم", "أمس", "قبل 3 أيام", "قبل أسبوع"]),
            "loyalty_points": n_orders * 25,
            "status": "VIP" if n_orders > 20 else ("منتظم" if n_orders > 5 else "جديد"),
            "wallet": round(random.random() * 120, 2),
        })
    return customers


def _build_drivers(type_id: str) -> List[Dict]:
    if type_id == "clinic":
        return [
            {"name": "د. محمد العتيبي", "phone": "+966551111111", "status": "متاح", "deliveries_today": 8, "rating": 4.9, "area": "أمراض القلب"},
            {"name": "د. سارة القحطاني", "phone": "+966552222222", "status": "في كشف", "deliveries_today": 12, "rating": 4.8, "area": "طب الأطفال"},
            {"name": "د. خالد الدوسري", "phone": "+966553333333", "status": "متاح", "deliveries_today": 6, "rating": 4.7, "area": "طب الأسنان"},
            {"name": "د. نورة الشمري", "phone": "+966554444444", "status": "إجازة", "deliveries_today": 0, "rating": 4.9, "area": "الجلدية"},
            {"name": "د. فيصل المالكي", "phone": "+966555555555", "status": "متاح", "deliveries_today": 10, "rating": 4.8, "area": "العيون"},
        ]
    if type_id == "realestate":
        return [
            {"name": "أحمد السبيعي", "phone": "+966551111111", "status": "متاح", "deliveries_today": 4, "rating": 4.8, "area": "شمال الرياض"},
            {"name": "خالد العتيبي", "phone": "+966552222222", "status": "في جولة", "deliveries_today": 5, "rating": 4.9, "area": "شرق الرياض"},
            {"name": "سلطان القحطاني", "phone": "+966553333333", "status": "متاح", "deliveries_today": 3, "rating": 4.7, "area": "جدة"},
            {"name": "نورة الفهد", "phone": "+966554444444", "status": "في مكتب", "deliveries_today": 6, "rating": 4.6, "area": "الخبر"},
            {"name": "بدر الدوسري", "phone": "+966555555555", "status": "متاح", "deliveries_today": 4, "rating": 4.9, "area": "الرياض"},
        ]
    return [  # store/restaurant: delivery drivers
        {"name": "أحمد السبيعي", "phone": "+966551111111", "status": "متاح", "deliveries_today": 6, "rating": 4.8, "area": "شمال الرياض"},
        {"name": "خالد العتيبي", "phone": "+966552222222", "status": "في توصيل", "deliveries_today": 8, "rating": 4.9, "area": "شرق الرياض"},
        {"name": "سلطان القحطاني", "phone": "+966553333333", "status": "متاح", "deliveries_today": 4, "rating": 4.7, "area": "غرب الرياض"},
        {"name": "فيصل الشمري", "phone": "+966554444444", "status": "استراحة", "deliveries_today": 5, "rating": 4.6, "area": "جنوب الرياض"},
        {"name": "بدر الدوسري", "phone": "+966555555555", "status": "في توصيل", "deliveries_today": 7, "rating": 4.9, "area": "وسط الرياض"},
    ]


def _build_reviews(type_id: str) -> List[Dict]:
    txts = {
        "store": [
            "خدمة ممتازة وتوصيل سريع، المنتج جودته فوق التوقعات!",
            "أحسن متجر إلكتروني تعاملت معه، أنصح فيه الكل.",
            "الأسعار منافسة جداً والمنتجات أصلية 100%.",
            "تجربتي رائعة، الموقع سهل وخدمة العملاء ممتازة.",
            "وصل الطلب أسرع من المتوقع، التغليف فاخر.",
        ],
        "clinic": [
            "أطباء محترفين وخدمة راقية، الكشف كان دقيق ومريح.",
            "العيادة نظيفة جداً، المواعيد دقيقة وفريق العمل ودود.",
            "علاجي تحسّن كثير بفضل الدكتور، أنصح بزيارة العيادة.",
            "أسعار معقولة والتأمين قُبل بدون مشاكل.",
            "تجربتي ممتازة، شكراً لكل الطاقم الطبي.",
        ],
        "realestate": [
            "خدمة احترافية، ساعدني الوسيط في إيجاد منزلي المثالي.",
            "الشفافية والمصداقية أهم ما يميّز هذا المكتب.",
            "تجربتي راقية، تابعوا معي حتى إتمام البيع.",
            "أنصح بهم، سرعة في الرد ومعرفة عميقة بالسوق.",
            "وفّروا لي وقت كبير وجولات منظّمة جداً.",
        ],
    }.get(type_id, [])
    revs = []
    for i, t in enumerate(txts):
        revs.append({"name": _saudi_name(), "stars": random.choice([4, 5, 5, 5]),
                     "date": random.choice(["قبل يومين", "الأسبوع الماضي", "قبل أسبوعين"]),
                     "text": t})
    return revs


def seed_generic(type_id: str, business_name: str, tagline: str = "",
                 phone: str = "", email: str = "") -> Dict[str, Any]:
    """Build a complete seed dict for a non-restaurant business type."""
    random.seed(business_name + type_id)
    phone = phone or "+966512345678"
    email = email or f"info@{(business_name or 'brand').replace(' ', '').lower()[:20]}.sa"

    if type_id == "store":
        categories, products = _build_products_store(business_name)
    elif type_id == "clinic":
        categories, products = _build_products_clinic(business_name)
    elif type_id == "realestate":
        categories, products = _build_products_realestate(business_name)
    else:
        raise ValueError(f"Unsupported type_id: {type_id}")

    orders = _build_orders(products, type_id, n=30)
    customers = _build_customers(20)
    drivers = _build_drivers(type_id)

    # Analytics
    today_orders = orders[:18]
    today_revenue = sum(o["total"] for o in today_orders)
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
            "top_dish": top[0][0] if top else (products[0]["name"] if products else "—"),
        },
        "week": {"orders": 142, "revenue": today_revenue * 6, "growth_pct": 12.4},
        "top_dishes": [
            {"name": name, "sold": count,
             "revenue": count * next((p["price"] for p in products if p["name"] == name), 100)}
            for name, count in top
        ],
    }
    reviews = _build_reviews(type_id)

    # Hours
    hours = {
        "saturday":  {"open": "09:00", "close": "22:00"},
        "sunday":    {"open": "09:00", "close": "22:00"},
        "monday":    {"open": "09:00", "close": "22:00"},
        "tuesday":   {"open": "09:00", "close": "22:00"},
        "wednesday": {"open": "09:00", "close": "22:00"},
        "thursday":  {"open": "09:00", "close": "23:00"},
        "friday":    {"open": "14:00", "close": "23:00"},
    }
    if type_id == "realestate":
        # offices have shorter hours
        for k in hours:
            hours[k] = {"open": "09:00", "close": "18:00"}
        hours["friday"] = {"open": "16:00", "close": "20:00"}

    default_tagline = {
        "store": "تسوّق بثقة · جودة عالمية · توصيل سريع",
        "clinic": "صحتك أولويتنا · أطباء متميزون · رعاية شاملة",
        "realestate": "نبني الأحلام · شريكك العقاري الموثوق",
    }.get(type_id, "")

    return {
        "branding": {
            "name": business_name,
            "tagline": tagline or default_tagline,
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
        "type_id": type_id,
    }
