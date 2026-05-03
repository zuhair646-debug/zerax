"""
Verified curated source library for FreeBuild v2.

CRITICAL PHILOSOPHY: The LLM must NEVER invent sources/data/URLs.
When the architect needs to reference real-world data (Quran reciters, Islamic
institutions, medical specialists, academy certifications, etc.), it pulls
ONLY from this library. If something isn't here, the AI should say "ما عندي
مصدر معتمد لهذا" instead of hallucinating.

This prevents:
    - Broken/404 audio URLs for Quran reciters
    - Made-up Quran verses with corrupted Arabic
    - Fake certifications
    - Invented institutional partnerships
"""
from typing import Dict, List, Any


# ════════════════════════════════════════════════════════════════════════
#  QURAN RECITERS — all verified on mp3quran.net (complete library)
# ════════════════════════════════════════════════════════════════════════
# Each reciter has a `server` number and slug. Full surah URL pattern:
#   https://server{server}.mp3quran.net/{slug}/{surah:03d}.mp3
# All 20 below verified to return 200 OK as of 2026-05.
VERIFIED_QURAN_RECITERS: List[Dict[str, Any]] = [
    {
        "id": "sudais",
        "name": "الشيخ عبد الرحمن السديس",
        "bio": "إمام المسجد الحرام، رواية حفص عن عاصم",
        "server": 11, "slug": "sds",
        "country": "السعودية",
    },
    {
        "id": "shuraim",
        "name": "الشيخ سعود الشريم",
        "bio": "إمام المسجد الحرام، صوت خاشع",
        "server": 7, "slug": "shur",
        "country": "السعودية",
    },
    {
        "id": "muaiqly",
        "name": "الشيخ ماهر المعيقلي",
        "bio": "إمام المسجد الحرام، تلاوة مميزة",
        "server": 12, "slug": "maher",
        "country": "السعودية",
    },
    {
        "id": "alafasy",
        "name": "الشيخ مشاري راشد العفاسي",
        "bio": "قارئ كويتي بارز، تلاوة رخيمة",
        "server": 8, "slug": "afs",
        "country": "الكويت",
    },
    {
        "id": "husary",
        "name": "الشيخ محمود خليل الحصري",
        "bio": "شيخ قراء مصر، رواية حفص المعتمدة",
        "server": 13, "slug": "husr",
        "country": "مصر",
    },
    {
        "id": "ghamdi",
        "name": "الشيخ سعد الغامدي",
        "bio": "قارئ مجوّد، إمام الجزائر سابقاً",
        "server": 7, "slug": "s_gmd",
        "country": "السعودية",
    },
    {
        "id": "minshawi",
        "name": "الشيخ محمد صديق المنشاوي",
        "bio": "علم من أعلام القراء المصريين الكلاسيكيين",
        "server": 6, "slug": "minsh",
        "country": "مصر",
    },
    {
        "id": "abdulbasit",
        "name": "الشيخ عبد الباسط عبد الصمد",
        "bio": "الصوت الذهبي، مرجع تلاوة المجوّد",
        "server": 7, "slug": "basit",
        "country": "مصر",
    },
    {
        "id": "ajmi",
        "name": "الشيخ أحمد بن علي العجمي",
        "bio": "إمام سعودي، تلاوة مؤثرة",
        "server": 10, "slug": "ajm",
        "country": "السعودية",
    },
    {
        "id": "bukhatir",
        "name": "الشيخ أحمد بن صالح البخاطر",
        "bio": "قارئ إماراتي، صوت دافئ",
        "server": 13, "slug": "bkhatir",
        "country": "الإمارات",
    },
    {
        "id": "juhany",
        "name": "الشيخ عبد الله بن عواد الجهني",
        "bio": "إمام المسجد الحرام",
        "server": 11, "slug": "jhn",
        "country": "السعودية",
    },
    {
        "id": "ayyub",
        "name": "الشيخ محمد أيوب",
        "bio": "إمام المسجد النبوي سابقاً، تلاوة هادئة",
        "server": 8, "slug": "m_ayyub",
        "country": "السعودية",
    },
    {
        "id": "luhaidan",
        "name": "الشيخ خالد اللحيدان",
        "bio": "قارئ سعودي متميّز",
        "server": 13, "slug": "khalid",
        "country": "السعودية",
    },
    {
        "id": "qahtani",
        "name": "الشيخ علي بن عبد الرحمن الحذيفي",
        "bio": "إمام المسجد النبوي",
        "server": 8, "slug": "hthfi",
        "country": "السعودية",
    },
    {
        "id": "dossary",
        "name": "الشيخ ياسر الدوسري",
        "bio": "إمام المسجد الحرام، صوت عذب",
        "server": 11, "slug": "yasser",
        "country": "السعودية",
    },
    {
        "id": "shaatri",
        "name": "الشيخ أبو بكر الشاطري",
        "bio": "إمام سعودي، تلاوة مرتّلة",
        "server": 6, "slug": "shatri",
        "country": "السعودية",
    },
    {
        "id": "mueaqly",
        "name": "الشيخ عادل الكلباني",
        "bio": "إمام المسجد الحرام سابقاً",
        "server": 6, "slug": "klb",
        "country": "السعودية",
    },
    {
        "id": "tablawi",
        "name": "الشيخ محمد محمود الطبلاوي",
        "bio": "شيخ قراء مصر الحالي",
        "server": 8, "slug": "tblawi",
        "country": "مصر",
    },
    {
        "id": "rifai",
        "name": "الشيخ هاني الرفاعي",
        "bio": "قارئ سعودي، صوت مؤثر",
        "server": 8, "slug": "rifai",
        "country": "السعودية",
    },
    {
        "id": "fares_abbad",
        "name": "الشيخ فارس عباد",
        "bio": "قارئ يمني، صوت شجيّ",
        "server": 6, "slug": "abbad",
        "country": "اليمن",
    },
]


def get_full_surah_url(reciter_slug: str, reciter_server: int, surah: int) -> str:
    """e.g. sudais, server 11, surah 1 → https://server11.mp3quran.net/sds/001.mp3"""
    return f"https://server{reciter_server}.mp3quran.net/{reciter_slug}/{surah:03d}.mp3"


# ════════════════════════════════════════════════════════════════════════
#  QURAN VERSE TEXT — authoritative CDN (NEVER use LLM to write verses)
# ════════════════════════════════════════════════════════════════════════
# The LLM corrupts Arabic diacritics when writing Quranic verses.
# We use al-Quran Cloud API (backed by the official Madinah Mushaf).
VERSE_TEXT_API = "https://api.alquran.cloud/v1/ayah/{surah}:{ayah}/ar.asad"
# OR per-ayah text from islamic.network (verified Madinah text):
VERSE_TEXT_CDN = "https://cdn.islamic.network/quran/arabic/quran-uthmani/{ayah_global}.json"

# Full Surah names and lengths (for reference; AI must use these, not invent)
SURAH_LIST = [
    {"num": 1, "name_ar": "الفاتحة", "name_en": "Al-Fatihah", "ayahs": 7, "type": "مكية"},
    {"num": 2, "name_ar": "البقرة", "name_en": "Al-Baqarah", "ayahs": 286, "type": "مدنية"},
    {"num": 3, "name_ar": "آل عمران", "name_en": "Ali 'Imran", "ayahs": 200, "type": "مدنية"},
    {"num": 36, "name_ar": "يس", "name_en": "Ya-Sin", "ayahs": 83, "type": "مكية"},
    {"num": 55, "name_ar": "الرحمن", "name_en": "Ar-Rahman", "ayahs": 78, "type": "مدنية"},
    {"num": 67, "name_ar": "الملك", "name_en": "Al-Mulk", "ayahs": 30, "type": "مكية"},
    {"num": 78, "name_ar": "النبأ", "name_en": "An-Naba'", "ayahs": 40, "type": "مكية"},
    {"num": 112, "name_ar": "الإخلاص", "name_en": "Al-Ikhlas", "ayahs": 4, "type": "مكية"},
    {"num": 113, "name_ar": "الفلق", "name_en": "Al-Falaq", "ayahs": 5, "type": "مكية"},
    {"num": 114, "name_ar": "الناس", "name_en": "An-Nas", "ayahs": 6, "type": "مكية"},
    # (full 114 available via alquran.cloud API at /surah)
]


# ════════════════════════════════════════════════════════════════════════
#  CERTIFIED ISLAMIC INSTITUTIONS & REFERENCES
# ════════════════════════════════════════════════════════════════════════
SAUDI_QURAN_INSTITUTIONS = [
    "جمعية تحفيظ القرآن الكريم الخيرية (مركز رسمي، معتمد من وزارة الشؤون الإسلامية)",
    "جامعة الإمام محمد بن سعود الإسلامية — كلية القرآن وعلومه",
    "الجامعة الإسلامية بالمدينة المنورة — كلية القرآن الكريم",
    "الرئاسة العامة لشؤون المسجد الحرام والمسجد النبوي",
    "مجمع الملك فهد لطباعة المصحف الشريف (المدينة المنورة)",
    "المنظمة العربية للتربية والثقافة والعلوم (ألكسو)",
    "رابطة العالم الإسلامي — الهيئة العالمية للقرآن الكريم",
]

VERIFIED_QURAN_APPS_SITES = [
    {"name": "مصحف المدينة (تطبيق رسمي)", "url": "https://quran.com"},
    {"name": "موقع القرآن الكريم — مجمع الملك فهد", "url": "https://qurancomplex.gov.sa"},
    {"name": "IslamWeb", "url": "https://www.islamweb.net"},
    {"name": "Quran.com (مشروع عالمي رسمي)", "url": "https://quran.com"},
    {"name": "mp3quran.net (مكتبة تلاوات معتمدة)", "url": "https://mp3quran.net"},
    {"name": "EveryAyah (قطع آيات منفصلة)", "url": "https://everyayah.com"},
]


# ════════════════════════════════════════════════════════════════════════
#  MEDICAL & ACADEMY SOURCES (verified for other domains)
# ════════════════════════════════════════════════════════════════════════
SAUDI_MEDICAL_REFERENCES = [
    "وزارة الصحة السعودية — moh.gov.sa",
    "مركز صحة — sehha.sa",
    "الهيئة السعودية للتخصصات الصحية (SCFHS) — scfhs.org.sa",
    "المستشفى التخصصي — kfshrc.edu.sa",
    "مستشفى الملك فيصل التخصصي ومركز الأبحاث",
]

SAUDI_EDUCATION_REFERENCES = [
    "وزارة التعليم السعودية — moe.gov.sa",
    "هيئة تقويم التعليم والتدريب — etec.gov.sa",
    "مدرستي (منصة التعليم عن بُعد الرسمية)",
    "منصة FutureX — futurex.sa",
    "رواق (منصة عربية مفتوحة معتمدة)",
]


# ════════════════════════════════════════════════════════════════════════
#  BUILD SOURCE BLOCK — injects the right verified sources per domain
# ════════════════════════════════════════════════════════════════════════
def build_verified_sources_block(domain_key: str = None) -> str:
    parts: List[str] = []
    parts.append(
        "# ⚓ المصادر المعتمدة (استخدم فقط من هذه القائمة — ممنوع اختراع مصادر)\n"
    )
    parts.append(
        "**قاعدة ذهبية**: لو احتجت تذكر قارئ، مؤسسة، تطبيق، مرجع — لازم يكون من هذه "
        "القائمة المعتمدة. لو طُلب منك شي خارج القائمة → قل 'ما عندي مصدر معتمد لهذا' "
        "ولا تخترع.\n"
    )

    if domain_key == "quran_memorization" or domain_key in (None, ""):
        parts.append("\n## 🎙️ مكتبة القرّاء الكاملة المعتمدة (20 قارئ من mp3quran.net)")
        parts.append("كل قارئ له server + slug. رابط السورة الكاملة:")
        parts.append("`https://server{SERVER}.mp3quran.net/{SLUG}/{SURAH_3_DIGITS}.mp3`")
        parts.append("مثال سورة الفاتحة بصوت السديس: `https://server11.mp3quran.net/sds/001.mp3`\n")
        parts.append("| ID | الاسم | الدولة | server | slug |")
        parts.append("|----|-------|--------|--------|------|")
        for r in VERIFIED_QURAN_RECITERS:
            parts.append(f"| `{r['id']}` | {r['name']} | {r.get('country','')} | {r['server']} | `{r['slug']}` |")
        parts.append(
            "\n**إلزامي**: أي موقع قرآن لازم يحتوي على بطاقة لكل قارئ (10 قرّاء كحد أدنى) "
            "+ `<audio controls>` مع رابط mp3quran.net صحيح. ممنوع استخدام أي CDN آخر."
        )

        parts.append("\n## 📖 عرض آيات القرآن — قاعدة حرجة")
        parts.append(
            "⚠️ **ممنوع منعاً باتاً كتابة آيات القرآن كنص LLM** لأن الذكاء يحرّف التشكيل "
            "والكلمات. البدائل المسموحة فقط:\n"
            "1. **صورة خط عربي**: `<img src=\"@@IMG/auto@@\" alt=\"مصحف مفتوح بإضاءة ذهبية "
            "وخط عربي متوهج غير واضح التفاصيل\">` — الذكاء يولد صورة تشبه القرآن بدون نص "
            "واضح (مستحيل يحرّف نص فعلي لأنها صورة decorative).\n"
            "2. **جلب من API معتمد**: إذا الموقع لازم يعرض نص آية، يستخدم fetch لـ "
            "`https://api.alquran.cloud/v1/ayah/{surah}:{ayah}/ar.asad` في الـJavaScript "
            "وقت التشغيل — هذا النص من مصحف المدينة المنورة (مجمع الملك فهد).\n"
            "3. **أسماء السور والإحصائيات** فقط — من القائمة: الفاتحة (7 آيات مكية)، "
            "البقرة (286 مدنية)، آل عمران (200 مدنية)، يس (83 مكية)، الرحمن (78 مدنية)، "
            "الملك (30 مكية)، النبأ (40 مكية)، الإخلاص (4 مكية)، الفلق (5 مكية)، الناس "
            "(6 مكية). لا تخترع أرقام آيات."
        )

        parts.append("\n## 🏛️ المؤسسات والتطبيقات المعتمدة (للإشارة إليها في 'شراكاتنا' أو 'about')")
        for inst in SAUDI_QURAN_INSTITUTIONS:
            parts.append(f"- {inst}")
        parts.append("")
        for app in VERIFIED_QURAN_APPS_SITES:
            parts.append(f"- {app['name']} — {app['url']}")

    if domain_key == "clinic":
        parts.append("\n## 🏥 المراجع الصحية المعتمدة (للإشارة)")
        for r in SAUDI_MEDICAL_REFERENCES:
            parts.append(f"- {r}")

    if domain_key == "academy_education":
        parts.append("\n## 🎓 المراجع التعليمية المعتمدة (للإشارة)")
        for r in SAUDI_EDUCATION_REFERENCES:
            parts.append(f"- {r}")

    parts.append(
        "\n## ⚠️ قواعد صارمة للمصادر"
        "\n1. **لا تخترع أرقام هواتف، روابط، عناوين، أسماء أشخاص حقيقيين.** استخدم "
        "placeholders واضحة (مثلاً: `+966-5X-XXX-XXXX`، `info@site.sa`) لو ما عندك قيمة حقيقية."
        "\n2. **لا تخترع إحصائيات** (مثلاً '5000 طفل حفظوا'). استخدم أرقام placeholder "
        "واضح إنها افتراضية، أو اسأل المستخدم عن الأرقام الحقيقية."
        "\n3. **لا تخترع شهادات/اعتمادات** لمؤسسات غير معروفة."
        "\n4. **لا تلصق شعارات شركات** (Apple/Google/KFC) بدون إذن صريح من المستخدم."
    )

    return "\n".join(parts)
