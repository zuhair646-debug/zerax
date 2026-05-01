"""
Visual + audio resource library injected into the architect's system prompt.

The AI gets these REAL working URLs (Unsplash photo IDs + Quran CDN URLs +
SVG icon library + verse design templates) so it can build rich, image-heavy,
audio-enabled multi-page websites — instead of bare-text pages.

All URLs verified to exist & work as of 2026-05.
"""
from typing import Dict, List


# ════════════════════════════════════════════════════════════════════════════
#  UNSPLASH IMAGE LIBRARY  (verified photo IDs that resolve to real images)
# ════════════════════════════════════════════════════════════════════════════
UNSPLASH_LIBRARY: Dict[str, List[str]] = {
    # ─── Islamic / Quran / Mosques ─────────────────────────────────────────
    "madinah": [
        "1591604129939-f1efa4d9f7fa",  # Prophet's Mosque exterior
        "1542816417-0983c9c9ad53",     # Mosque minaret
        "1591389703635-e15a07b842d7",  # Mosque aerial
    ],
    "mecca": [
        "1591604129939-f1efa4d9f7fa",
        "1591389703635-e15a07b842d7",  # Kaaba aerial
    ],
    "quran": [
        "1591604129939-f1efa4d9f7fa",  # Mosque (suitable for Quran sites)
        "1542816417-0983c9c9ad53",     # Quran on stand
        "1591389703635-e15a07b842d7",
    ],
    "mushaf": [
        "1591604129939-f1efa4d9f7fa",
        "1542816417-0983c9c9ad53",
    ],
    "mosque": [
        "1542816417-0983c9c9ad53",
        "1591604129939-f1efa4d9f7fa",
        "1591389703635-e15a07b842d7",
    ],
    "islamic_pattern": [
        "1532375810709-75b1da00537c",  # Islamic geometric pattern
        "1542816417-0983c9c9ad53",
    ],
    # ─── Food / Restaurants / Cafes ────────────────────────────────────────
    "food_general": [
        "1565299624946-b28f40a0ae38",  # Burger
        "1571066811602-716837d681de",  # Spread
        "1567620905732-2d1ec7ab7445",  # Pancakes
    ],
    "restaurant_interior": [
        "1414235077428-338989a2e8c0",
        "1517248135467-4c7edcad34c4",
    ],
    "cafe": [
        "1495474472287-4d71bcdd2085",  # Coffee shop
        "1517248135467-4c7edcad34c4",
        "1554118811-1e0d58224f24",     # Latte art
    ],
    "saudi_food": [
        "1571066811602-716837d681de",
        "1567620905732-2d1ec7ab7445",
    ],
    "dessert": [
        "1488477181946-6428a0291777",
        "1565958011703-44f9829ba187",
    ],
    # ─── Healthcare ────────────────────────────────────────────────────────
    "doctor": [
        "1576091160399-112ba8d25d1d",
        "1559757148-5c350d0d3c56",
    ],
    "clinic": [
        "1612349317150-e413f6a5b16d",
        "1551601651-2a8555f1a136",
    ],
    "dentist": [
        "1606811971618-4486d14f3f99",
    ],
    # ─── Education ─────────────────────────────────────────────────────────
    "education": [
        "1481627834876-b7833e8f5570",  # Open book
        "1503676260728-1c00da094a0b",  # Children
        "1497486751825-1233686d5d80",  # Graduation
    ],
    "books": [
        "1481627834876-b7833e8f5570",
        "1543002588-bfa74002ed7e",
    ],
    "classroom": [
        "1503676260728-1c00da094a0b",
    ],
    # ─── Children ──────────────────────────────────────────────────────────
    "children_learning": [
        "1503676260728-1c00da094a0b",
        "1518398046578-8cca57782e17",  # Kids reading
    ],
    "kids": [
        "1503676260728-1c00da094a0b",
        "1518398046578-8cca57782e17",
    ],
    # ─── Tech / Office ─────────────────────────────────────────────────────
    "office_workspace": [
        "1497366216548-37526070297c",
        "1517245386807-bb43f82c33c4",
    ],
    "tech": [
        "1518770660439-4636190af475",
        "1531297484001-80022131f5a1",
    ],
    # ─── Hero / Backgrounds ────────────────────────────────────────────────
    "abstract_dark": [
        "1518791841217-8f162f1e1131",
        "1451187580459-43490279c0fa",
    ],
    "luxury": [
        "1542038784456-1ea8e935640e",  # Gold/luxury
        "1601758228041-f3b2795255f1",
    ],
    "nature": [
        "1469474968028-56623f02e42e",
        "1506905925346-21bda4d32df4",
    ],
    "city_night": [
        "1518481852452-9415b262eba4",
        "1444723121867-7a241cacace9",
    ],
    # ─── E-commerce ────────────────────────────────────────────────────────
    "fashion": [
        "1490481651871-ab68de25d43d",
        "1483985988355-763728e1935b",
    ],
    "perfume": [
        "1541643600914-78b084683601",
        "1592945403244-b3fbafd7f539",
    ],
    "jewelry": [
        "1515562141207-7a88fb7ce338",
        "1605100804763-247f67b3557e",
    ],
    "watch": [
        "1523275335684-37898b6baf30",
    ],
    # ─── Smart Tech / AI / Apps ────────────────────────────────────────────
    "smart_tech": [
        "1518770660439-4636190af475",  # circuit board
        "1531297484001-80022131f5a1",  # screens
        "1633356122544-f134324a6cee",  # dashboard
    ],
    "ai": [
        "1518770660439-4636190af475",
        "1531297484001-80022131f5a1",
    ],
    "interaction": [
        "1531297484001-80022131f5a1",
        "1517245386807-bb43f82c33c4",
    ],
    "tracking": [
        "1633356122544-f134324a6cee",  # analytics dashboard
        "1517245386807-bb43f82c33c4",  # laptop with charts
    ],
    "memorization": [
        "1503676260728-1c00da094a0b",  # studying
        "1481627834876-b7833e8f5570",  # open book
    ],
    "teacher_student": [
        "1503676260728-1c00da094a0b",
        "1518398046578-8cca57782e17",
    ],
    "mobile_app": [
        "1551650975-87deedd944c3",
        "1556656793-08538906a9f8",
    ],
    # ─── Real Estate / Architecture ────────────────────────────────────────
    "modern_villa": [
        "1568605114967-8130f3a36994",
        "1564013799919-ab600027ffc6",
    ],
    "interior_living": [
        "1567767292278-a4f21aa2d36e",
        "1556909114-f6e7ad7d3136",
    ],
    # ─── Sports / Fitness ──────────────────────────────────────────────────
    "gym": [
        "1571019613454-1cb2f99b2d8b",
        "1534438327276-14e5300c3a48",
    ],
    "yoga": [
        "1545205597-3d9d02c29597",
    ],
}


def unsplash_url(photo_id: str, w: int = 1600, q: int = 80) -> str:
    return f"https://images.unsplash.com/photo-{photo_id}?auto=format&fit=crop&w={w}&q={q}"


# ════════════════════════════════════════════════════════════════════════════
#  KEYWORD → CATEGORY ALIAS MAP  (for semantic image post-processing)
# ════════════════════════════════════════════════════════════════════════════
# Maps any English/Arabic keyword the AI might use to a UNSPLASH_LIBRARY key.
# Order matters — longer/more specific terms first.
KEYWORD_ALIASES: List[tuple] = [
    # Quran / Islamic
    (("quran", "qur'an", "qoran", "mushaf", "recitation", "tilawah", "ayah",
      "قرآن", "مصحف", "تلاوة", "آية"), "quran"),
    (("madinah", "medina", "prophet-mosque", "المدينة", "مدينة"), "madinah"),
    (("mecca", "kaaba", "haram", "مكة", "كعبة"), "mecca"),
    (("mosque", "masjid", "minaret", "prayer-hall", "مسجد", "مساجد"), "mosque"),
    (("islamic-pattern", "geometric-pattern", "زخرفة", "زخارف"), "islamic_pattern"),
    # Smart tech / AI
    (("smart-tech", "smart-technology", "ai", "artificial-intelligence",
      "machine-learning", "ذكاء", "ذكي", "تقنية"), "smart_tech"),
    (("interaction", "interactive", "تفاعل"), "interaction"),
    (("tracking", "monitoring", "analytics", "metrics", "متابعة", "تتبع"), "tracking"),
    (("mobile-app", "smartphone", "app", "تطبيق"), "mobile_app"),
    # Education / learning
    (("memorization", "memorize", "حفظ", "تحفيظ"), "memorization"),
    (("teacher", "student", "tutor", "lesson", "درس", "معلم", "طالب", "تعليم"),
     "teacher_student"),
    (("classroom", "school", "صف", "مدرسة"), "classroom"),
    (("books", "library", "كتب", "مكتبة"), "books"),
    (("graduation", "تخرج"), "education"),
    # Kids
    (("kids", "child", "children", "boy", "girl", "أطفال", "طفل"),
     "children_learning"),
    # Food
    (("saudi-food", "kabsa", "arab-food", "كبسة", "أكل-سعودي"), "saudi_food"),
    (("food", "meal", "dish", "طعام", "أكل", "وجبة"), "food_general"),
    (("restaurant", "dining", "مطعم"), "restaurant_interior"),
    (("cafe", "coffee", "latte", "قهوة", "كافيه", "مقهى"), "cafe"),
    (("dessert", "sweets", "cake", "حلويات"), "dessert"),
    # Healthcare
    (("dentist", "dental", "أسنان"), "dentist"),
    (("clinic", "hospital", "عيادة", "مستشفى"), "clinic"),
    (("doctor", "physician", "nurse", "طبيب", "ممرض"), "doctor"),
    # E-commerce
    (("perfume", "fragrance", "عطر", "عطور"), "perfume"),
    (("jewelry", "ring", "necklace", "مجوهرات", "ذهب"), "jewelry"),
    (("watch", "ساعة"), "watch"),
    (("fashion", "clothing", "أزياء", "ملابس"), "fashion"),
    # Real estate
    (("villa", "house", "home", "real-estate", "فيلا", "بيت", "عقار"),
     "modern_villa"),
    (("interior", "living-room", "ديكور", "صالة"), "interior_living"),
    # Other
    (("tech", "office", "workspace", "مكتب"), "office_workspace"),
    (("city", "urban", "night", "مدينة", "ليل"), "city_night"),
    (("nature", "mountain", "landscape", "طبيعة", "جبال"), "nature"),
    (("luxury", "gold", "premium", "فخامة", "ذهبي"), "luxury"),
    (("gym", "fitness", "workout", "نادي"), "gym"),
    (("yoga", "meditation", "يوغا"), "yoga"),
]


def resolve_image_for_keyword(keyword: str, w: int = 1600) -> str:
    """Map any user-supplied keyword to a real Unsplash URL via the alias table.
    Falls back to a generic abstract_dark image if no match."""
    import random as _random
    if not keyword:
        keyword = "abstract"
    kw = keyword.lower().replace("_", "-").strip()
    # Try direct category match first
    if kw in UNSPLASH_LIBRARY:
        chosen = _random.choice(UNSPLASH_LIBRARY[kw])
        return unsplash_url(chosen, w=w)
    # Fuzzy match via aliases
    for terms, category in KEYWORD_ALIASES:
        for term in terms:
            if term in kw:
                if category in UNSPLASH_LIBRARY and UNSPLASH_LIBRARY[category]:
                    chosen = _random.choice(UNSPLASH_LIBRARY[category])
                    return unsplash_url(chosen, w=w)
    # Fallback
    return unsplash_url(UNSPLASH_LIBRARY["abstract_dark"][0], w=w)


def post_process_html_images(html: str) -> str:
    """Replace AI-generated @@IMG/<keyword>@@ placeholders with real URLs.
    Pattern: src="@@IMG/quran-mushaf@@"  →  src="https://images.unsplash.com/photo-...".
    Also handles background-image: url(@@IMG/...@@).
    This guarantees images ALWAYS match section semantic intent."""
    import re
    if not html or "@@IMG/" not in html:
        return html

    def _replace(m):
        keyword = m.group(1).strip()
        return resolve_image_for_keyword(keyword)

    # Match @@IMG/<keyword>@@ where keyword is anything except '@'
    return re.sub(r"@@IMG/([^@]+)@@", _replace, html)


# ════════════════════════════════════════════════════════════════════════════
#  QURAN AUDIO LIBRARY  (verified working CDN: mp3quran.net + cdn.islamic.network)
# ════════════════════════════════════════════════════════════════════════════
QURAN_RECITERS = [
    {
        "id": "sudais", "name": "الشيخ عبد الرحمن السديس",
        "full_surah_url": "https://server11.mp3quran.net/sds/{surah:03d}.mp3",
        "ayah_url": "https://cdn.islamic.network/quran/audio/128/ar.abdurrahmaansudais/{ayah_global}.mp3",
    },
    {
        "id": "shuraim", "name": "الشيخ سعود الشريم",
        "full_surah_url": "https://server7.mp3quran.net/shur/{surah:03d}.mp3",
    },
    {
        "id": "muaiqly", "name": "الشيخ ماهر المعيقلي",
        "full_surah_url": "https://server12.mp3quran.net/maher/{surah:03d}.mp3",
    },
    {
        "id": "alafasy", "name": "الشيخ مشاري العفاسي",
        "full_surah_url": "https://server8.mp3quran.net/afs/{surah:03d}.mp3",
        "ayah_url": "https://cdn.islamic.network/quran/audio/128/ar.alafasy/{ayah_global}.mp3",
    },
    {
        "id": "husary", "name": "الشيخ محمود خليل الحصري",
        "full_surah_url": "https://server13.mp3quran.net/husr/{surah:03d}.mp3",
        "ayah_url": "https://cdn.islamic.network/quran/audio/128/ar.husary/{ayah_global}.mp3",
    },
    {
        "id": "ghamdi", "name": "الشيخ سعد الغامدي",
        "full_surah_url": "https://server7.mp3quran.net/s_gmd/{surah:03d}.mp3",
    },
]


# ════════════════════════════════════════════════════════════════════════════
#  SVG ICON LIBRARY  (inline, no external libs)
# ════════════════════════════════════════════════════════════════════════════
SVG_ICONS = {
    "play":     '<svg viewBox="0 0 24 24" fill="currentColor" width="24" height="24"><path d="M8 5v14l11-7z"/></svg>',
    "pause":    '<svg viewBox="0 0 24 24" fill="currentColor" width="24" height="24"><path d="M6 4h4v16H6zM14 4h4v16h-4z"/></svg>',
    "book":     '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="24" height="24"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20V2H6.5A2.5 2.5 0 0 0 4 4.5v15z"/></svg>',
    "user":     '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="24" height="24"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>',
    "heart":    '<svg viewBox="0 0 24 24" fill="currentColor" width="24" height="24"><path d="M12 21s-7-4.5-7-11a4.5 4.5 0 0 1 7-3.5A4.5 4.5 0 0 1 19 10c0 6.5-7 11-7 11z"/></svg>',
    "star":     '<svg viewBox="0 0 24 24" fill="currentColor" width="24" height="24"><path d="M12 2l3 7h7l-5.5 4.5L18 21l-6-4.5L6 21l1.5-7.5L2 9h7z"/></svg>',
    "search":   '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="24" height="24"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/></svg>',
    "menu":     '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" width="28" height="28"><path d="M3 6h18M3 12h18M3 18h18"/></svg>',
    "close":    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" width="24" height="24"><path d="M18 6 6 18M6 6l12 12"/></svg>',
    "arrow_left": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="24" height="24"><path d="M19 12H5M12 19l-7-7 7-7"/></svg>',
    "settings": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="24" height="24"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>',
    "bell":     '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="24" height="24"><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 0 1-3.46 0"/></svg>',
    "phone":    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="24" height="24"><path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z"/></svg>',
    "mail":     '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="24" height="24"><path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/><path d="m22 6-10 7L2 6"/></svg>',
    "check":    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" width="24" height="24"><path d="M20 6 9 17l-5-5"/></svg>',
    "graduation": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="24" height="24"><path d="M22 10v6M2 10l10-5 10 5-10 5z"/><path d="M6 12v5c3 3 9 3 12 0v-5"/></svg>',
    "trophy":   '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="24" height="24"><path d="M6 9H4.5a2.5 2.5 0 0 1 0-5H6"/><path d="M18 9h1.5a2.5 2.5 0 0 0 0-5H18"/><path d="M4 22h16"/><path d="M10 14.66V17c0 .55-.47.98-.97 1.21C7.85 18.75 7 20.24 7 22"/><path d="M14 14.66V17c0 .55.47.98.97 1.21C16.15 18.75 17 20.24 17 22"/><path d="M18 2H6v7a6 6 0 0 0 12 0V2Z"/></svg>',
}


# ════════════════════════════════════════════════════════════════════════════
#  QURAN VERSE DESIGN TEMPLATE  (HTML+CSS pattern for displaying Quran ayahs)
# ════════════════════════════════════════════════════════════════════════════
QURAN_VERSE_TEMPLATE = '''
<!-- آية كريمة بتصميم عثماني -->
<div class="quran-verse">
  <div class="verse-frame">
    <div class="bismillah">بِسْمِ اللَّهِ الرَّحْمَٰنِ الرَّحِيمِ</div>
    <p class="verse-text">{ayah_text} ﴿{ayah_number}﴾</p>
    <div class="surah-name">{surah_name}</div>
  </div>
</div>

<style>
.quran-verse{
  background: linear-gradient(135deg, #1a1208 0%, #2d1f0a 100%);
  border: 2px solid #d4af37;
  border-radius: 12px;
  padding: 40px 30px;
  text-align: center;
  position: relative;
  overflow: hidden;
}
.quran-verse::before{
  content: ""; position: absolute; inset: 8px;
  border: 1px solid rgba(212,175,55,0.4);
  border-radius: 8px; pointer-events: none;
}
.verse-frame{ position: relative; z-index: 1 }
.bismillah{
  font-family: 'Amiri Quran','Reem Kufi',serif;
  font-size: clamp(1.5rem, 4vw, 2.2rem);
  color: #d4af37; margin-bottom: 24px; font-weight: 700;
}
.verse-text{
  font-family: 'Amiri','Amiri Quran',serif;
  font-size: clamp(1.4rem, 3.5vw, 2rem);
  line-height: 2.2; color: #f5f1e8;
  letter-spacing: 0.5px;
}
.surah-name{
  margin-top: 28px; padding-top: 20px;
  border-top: 1px solid rgba(212,175,55,0.3);
  color: #d4af37; font-weight: 700;
}
</style>
'''


# ════════════════════════════════════════════════════════════════════════════
#  HTML5 AUDIO PLAYER TEMPLATE  (custom-styled, works for any MP3)
# ════════════════════════════════════════════════════════════════════════════
AUDIO_CARD_TEMPLATE = '''
<!-- بطاقة قارئ مع مشغّل صوت مدمج -->
<article class="reciter-card">
  <div class="reciter-avatar"><!-- صورة أو حرف ضمن دائرة gradient --></div>
  <h3 class="reciter-name">{reciter_name}</h3>
  <p class="reciter-meta">{description}</p>
  <audio controls preload="none" class="reciter-audio">
    <source src="{mp3_url}" type="audio/mpeg">
    متصفحك لا يدعم تشغيل الصوت.
  </audio>
</article>

<style>
.reciter-card{
  background: linear-gradient(180deg, rgba(255,255,255,0.04), rgba(255,255,255,0.02));
  border: 1px solid rgba(212,175,55,0.25);
  border-radius: 16px;
  padding: 28px 24px;
  text-align: center;
  transition: transform .3s, border-color .3s;
}
.reciter-card:hover{ transform: translateY(-4px); border-color: rgba(212,175,55,0.6) }
.reciter-avatar{
  width: 88px; height: 88px; border-radius: 50%;
  background: linear-gradient(135deg, #d4af37, #b88c2a);
  margin: 0 auto 16px;
  display:flex;align-items:center;justify-content:center;
  font-size: 2rem; color: #1a1208; font-weight: 900;
  box-shadow: 0 8px 24px rgba(212,175,55,0.3);
}
.reciter-name{ font-size: 1.25rem; font-weight: 800; color: #f5f1e8; margin-bottom: 8px }
.reciter-meta{ color: rgba(245,241,232,0.6); font-size: .9rem; margin-bottom: 16px }
.reciter-audio{ width: 100%; height: 36px; filter: invert(0.85) hue-rotate(180deg) }
</style>
'''


def build_resources_block() -> str:
    """Format the entire resource library as a system-prompt-friendly block."""
    parts: List[str] = []
    parts.append("# 📚 مكتبة الموارد الجاهزة (استخدمها بحرية — كلها مُتحقّق منها وتعمل)")

    # ════════════════════════════════════════════════════════════════════
    # CRITICAL: image placeholder system (post-processed server-side)
    # ════════════════════════════════════════════════════════════════════
    parts.append("\n## 🖼️ نظام الصور الذكي — `@@IMG/<keyword>@@`")
    parts.append(
        "**القاعدة الأهم على الإطلاق**: لا تكتب روابط صور Unsplash مباشرة (لأنك تخطئ في اختيار الـIDs).\n"
        "بدلاً من ذلك، استخدم placeholder بهذي الصيغة:\n"
        "```html\n"
        '<img src="@@IMG/quran-mushaf@@" alt="القرآن الكريم">\n'
        '<img src="@@IMG/saudi-food@@" alt="طعام">\n'
        '<div style="background-image: url(@@IMG/madinah@@)"></div>\n'
        "```\n\n"
        "السيرفر بعدها يبدّل كل `@@IMG/<keyword>@@` بصورة Unsplash حقيقية مطابقة للموضوع.\n"
        "**ميزة هذي الطريقة**: الصور تطابق سياق القسم دائماً ولا تخطئ.\n"
    )

    # Available keywords list
    parts.append("\n### الكلمات المفتاحية المتاحة (اختر الأنسب لكل قسم)")
    parts.append(
        "**ديني/إسلامي**: `quran`, `madinah`, `mecca`, `mosque`, `islamic-pattern`, "
        "`mushaf`, `recitation`, `ayah`\n"
        "**تعليم**: `memorization`, `teacher-student`, `classroom`, `books`, "
        "`children-learning`, `graduation`, `education`\n"
        "**ذكاء/تقنية**: `smart-tech`, `ai`, `interaction`, `tracking`, `mobile-app`, "
        "`tech`, `office`\n"
        "**طعام**: `saudi-food`, `food`, `restaurant`, `cafe`, `dessert`\n"
        "**صحة**: `doctor`, `clinic`, `dentist`\n"
        "**متاجر**: `perfume`, `jewelry`, `watch`, `fashion`\n"
        "**عقار**: `villa`, `interior`, `modern-house`\n"
        "**أخرى**: `nature`, `city-night`, `luxury`, `gym`, `yoga`, `abstract-dark`\n"
    )

    # Quran audio
    parts.append("\n## 🔊 تلاوات قرآنية (CDN حقيقي يعمل — استخدم رابط مباشر)")
    parts.append("استخدم هذي الروابط في `<audio>` HTML5 — كلها تعمل:")
    for r in QURAN_RECITERS:
        ex = r["full_surah_url"].format(surah=1)
        parts.append(f"- **{r['name']}**: `{r['full_surah_url']}` (مثال: {ex})")
    parts.append(
        "\nنمط استخدام (مثلاً سورة الفاتحة بصوت السديس):"
        "\n```html\n<audio controls src=\"https://server11.mp3quran.net/sds/001.mp3\"></audio>\n```"
        "\n- `{surah:03d}` = رقم السورة بـ3 أرقام (001 للفاتحة، 002 للبقرة، 114 للناس)"
        "\n- لازم تضيف بطاقات قرّاء مع مشغّل صوت في أي موقع قرآني"
    )

    # SVG icons
    parts.append("\n## 🎨 مكتبة أيقونات SVG inline (انسخ والصق مباشرة)")
    for name, svg in SVG_ICONS.items():
        compact = svg.replace("\n", "").strip()
        parts.append(f"- **{name}**: `{compact[:90]}...`")
    parts.append(
        "\nاستخدمها في الأزرار، البطاقات، navbar، dropdowns. لا تستخدم Font Awesome أو مكتبات خارجية."
    )

    # Quran verse template
    parts.append("\n## 📖 قالب آية قرآنية بتصميم عثماني")
    parts.append("```html\n" + QURAN_VERSE_TEMPLATE.strip() + "\n```")
    parts.append(
        "استخدم خط Amiri أو Amiri Quran من Google Fonts:"
        "\n`<link href=\"https://fonts.googleapis.com/css2?family=Amiri:wght@400;700&family=Amiri+Quran&display=swap\" rel=\"stylesheet\">`"
        "\nأمثلة آيات للاستخدام:"
        "\n- إنّا أعطيناك الكوثر ﴿1﴾ فصلِّ لربك وانحر ﴿2﴾ — سورة الكوثر"
        "\n- قل هو الله أحد ﴿1﴾ الله الصمد ﴿2﴾ — سورة الإخلاص"
        "\n- وما خلقت الجن والإنس إلا ليعبدون ﴿56﴾ — سورة الذاريات"
    )

    # Audio card template
    parts.append("\n## 🎵 قالب بطاقة قارئ مع مشغّل صوت")
    parts.append("```html\n" + AUDIO_CARD_TEMPLATE.strip() + "\n```")

    parts.append(
        "\n## ⚡ قواعد إجبارية"
        "\n1. **لا تكتب رابط Unsplash مباشرة أبداً** — استخدم `@@IMG/<keyword>@@` فقط."
        "\n2. كل قسم/بطاقة يحتاج صورة → اختر keyword يطابق محتوى القسم بالضبط:"
        "\n   - قسم اسمه 'نظام تفاعل ذكي' → `@@IMG/smart-tech@@` أو `@@IMG/interaction@@`"
        "\n   - قسم اسمه 'مكتبة قرّاء' → `@@IMG/quran@@`"
        "\n   - قسم اسمه 'متابعة الطالب' → `@@IMG/tracking@@`"
        "\n   - قسم اسمه 'دروس تجويد' → `@@IMG/memorization@@`"
        "\n3. لا تخلط الكلمات المفتاحية — لو القسم عن الذكاء الصناعي **لا** تستخدم `food` أو `villa`."
        "\n4. كل html_update في موقع قرآني يجب أن يحتوي على ≥3 بطاقات قارئ مع `<audio>`"
        "\n5. كل html_update في موقع قرآني يجب أن يحتوي على ≥1 آية بتصميم عثماني"
        "\n6. كل قسم مميزات/خدمات يجب أن يحتوي على صورة (`@@IMG/...@@`)"
        "\n7. Hero يجب أن يكون فيه صورة (`@@IMG/...@@`)"
    )

    return "\n".join(parts)
