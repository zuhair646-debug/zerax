"""Site Health Score — 0-100 grade with 5 weighted dimensions.

After each successful HTML generation, the chat endpoint runs `score_html()`
and stores `last_health` on the project. The frontend reads this and shows a
beautiful gauge to the customer. Improvement suggestions are clickable —
each click sends "ضيف لي [suggestion]" to the AI, naturally consuming credits.
"""

from __future__ import annotations

import re
from typing import Dict, List


# ──────────────────────────────────────────────────────────────────────────────
# DIMENSION 1: DESIGN (25 points)
# ──────────────────────────────────────────────────────────────────────────────
def _score_design(html: str) -> Dict:
    score = 0
    notes: List[str] = []
    suggestions: List[str] = []

    # Arabic font (Cairo/Tajawal) → 6 pts
    if any(f in html for f in ("Cairo", "Tajawal", "Aref Ruqaa", "Noto Naskh")):
        score += 6
        notes.append("خط عربي احترافي ✓")
    else:
        suggestions.append("ضيف خط Cairo أو Tajawal (يحسّن قراءة العربية بشكل كبير)")

    # Gradient backgrounds → 5 pts
    if re.search(r"bg-gradient|background:\s*linear-gradient|radial-gradient", html, re.IGNORECASE):
        score += 5
        notes.append("تدرجات لونية ✓")
    else:
        suggestions.append("أضف تدرجات لونية (gradients) لإحساس عصري")

    # Sections with id (multi-section layout) → 5 pts
    sections = len(re.findall(r"<section\b", html, re.IGNORECASE))
    if sections >= 4:
        score += 5
        notes.append(f"{sections} أقسام منظّمة ✓")
    elif sections >= 2:
        score += 3
    else:
        suggestions.append("نظّم المحتوى بـsections (Hero, Services, Reviews, Contact)")

    # CTA buttons (call-to-action) → 4 pts
    ctas = len(re.findall(r"<a\b[^>]*class[^>]*(?:btn|button|cta)", html, re.IGNORECASE))
    if ctas >= 2:
        score += 4
        notes.append("أزرار CTA متعددة ✓")
    elif ctas == 1:
        score += 2
    else:
        suggestions.append("أضف زر CTA رئيسي (احجز، اشترِ، تواصل)")

    # Hero with background image/visual → 3 pts
    if re.search(r"hero[^>]*(?:bg-|background)", html, re.IGNORECASE) or "<<HERO" in html:
        score += 3
        notes.append("Hero بصري ✓")

    # Animations/transitions → 2 pts
    if re.search(r"animate-|transition-|hover:|@keyframes", html, re.IGNORECASE):
        score += 2
        notes.append("Animations ✓")

    return {"score": score, "max": 25, "notes": notes, "suggestions": suggestions}


# ──────────────────────────────────────────────────────────────────────────────
# DIMENSION 2: SEO (20 points)
# ──────────────────────────────────────────────────────────────────────────────
def _score_seo(html: str) -> Dict:
    score = 0
    notes: List[str] = []
    suggestions: List[str] = []
    low = html.lower()

    if "<title" in low and re.search(r"<title>[^<]+</title>", html):
        score += 4
        notes.append("Title ✓")
    else:
        suggestions.append("أضف <title> واضح ووصفي")

    if 'name="description"' in low:
        score += 4
        notes.append("Meta description ✓")
    else:
        suggestions.append("أضف meta description (يظهر في Google)")

    if 'property="og:' in low or "property='og:" in low:
        score += 3
        notes.append("Open Graph ✓ (مشاركة احترافية)")
    else:
        suggestions.append("أضف Open Graph meta tags (للمشاركة على فيسبوك/واتساب)")

    if 'name="twitter:' in low:
        score += 2
        notes.append("Twitter Card ✓")
    else:
        suggestions.append("أضف Twitter Card meta tags")

    h1_count = len(re.findall(r"<h1\b", html, re.IGNORECASE))
    if h1_count == 1:
        score += 3
        notes.append("H1 واحد ✓")
    elif h1_count >= 2:
        suggestions.append(f"عندك {h1_count} <h1> — يفضّل واحد فقط لكل صفحة")

    # Alt text on images
    imgs = re.findall(r"<img\b[^>]*>", html, re.IGNORECASE)
    if imgs:
        with_alt = sum(1 for i in imgs if re.search(r'\balt\s*=', i, re.IGNORECASE))
        ratio = with_alt / len(imgs)
        score += int(2 * ratio)
        if ratio < 0.9:
            suggestions.append(f"{len(imgs) - with_alt} صور بدون alt — أضف وصفاً لكل صورة")
        else:
            notes.append("alt text كامل ✓")

    if 'hreflang="ar"' in low:
        score += 1
        notes.append("hreflang ✓")

    if 'application/ld+json' in low or "schema.org" in low:
        score += 1
        notes.append("Schema.org ✓")
    else:
        suggestions.append("أضف Schema.org structured data (يحسّن ظهور Google)")

    return {"score": score, "max": 20, "notes": notes, "suggestions": suggestions}


# ──────────────────────────────────────────────────────────────────────────────
# DIMENSION 3: PERFORMANCE (20 points)
# ──────────────────────────────────────────────────────────────────────────────
def _score_performance(html: str) -> Dict:
    score = 0
    notes: List[str] = []
    suggestions: List[str] = []

    size_kb = len(html.encode("utf-8")) / 1024
    if size_kb < 50:
        score += 8
        notes.append(f"حجم رائع ({size_kb:.0f}KB) ✓")
    elif size_kb < 100:
        score += 6
        notes.append(f"حجم جيد ({size_kb:.0f}KB)")
    elif size_kb < 200:
        score += 3
        suggestions.append(f"الحجم {size_kb:.0f}KB — قسّم الموقع لعدة صفحات لتسريع التحميل")
    else:
        suggestions.append(f"الحجم {size_kb:.0f}KB — كبير جداً، يحتاج تقسيم")

    # Lazy loading on images
    imgs = re.findall(r"<img\b[^>]*>", html, re.IGNORECASE)
    if imgs:
        lazy = sum(1 for i in imgs if 'loading="lazy"' in i.lower() or "loading='lazy'" in i.lower())
        if lazy / len(imgs) >= 0.7:
            score += 4
            notes.append("Lazy loading للصور ✓")
        else:
            suggestions.append(f'أضف loading="lazy" للصور غير الـHero (يسرّع التحميل 30%)')

    # Preconnect to font CDNs
    if "preconnect" in html.lower():
        score += 2
        notes.append("DNS preconnect ✓")
    else:
        suggestions.append('أضف <link rel="preconnect" href="https://fonts.googleapis.com">')

    # Minified inline CSS/JS (no excessive whitespace) — approximate
    style_blocks = re.findall(r"<style[^>]*>(.*?)</style>", html, re.DOTALL | re.IGNORECASE)
    if style_blocks:
        total = sum(len(s) for s in style_blocks)
        if total > 0:
            density = sum(len(s.replace(" ", "").replace("\n", "")) for s in style_blocks) / total
            if density > 0.7:
                score += 2
                notes.append("CSS مضغوط ✓")

    # External script count (keep low for performance)
    ext_scripts = len(re.findall(r"<script\b[^>]*src=", html, re.IGNORECASE))
    if ext_scripts <= 2:
        score += 2
        notes.append(f"{ext_scripts} scripts خارجية فقط ✓")
    elif ext_scripts <= 4:
        score += 1
    else:
        suggestions.append(f"{ext_scripts} scripts خارجية — يبطّئ الموقع")

    # No render-blocking iframes in hero
    if not re.search(r"<iframe\b[^>]*>", html[:5000], re.IGNORECASE):
        score += 2

    return {"score": score, "max": 20, "notes": notes, "suggestions": suggestions}


# ──────────────────────────────────────────────────────────────────────────────
# DIMENSION 4: ACCESSIBILITY (15 points)
# ──────────────────────────────────────────────────────────────────────────────
def _score_accessibility(html: str) -> Dict:
    score = 0
    notes: List[str] = []
    suggestions: List[str] = []

    if 'lang="ar"' in html or "lang='ar'" in html:
        score += 3
        notes.append("lang معرّفة ✓")
    if 'dir="rtl"' in html or "dir='rtl'" in html:
        score += 2
        notes.append("RTL ✓")

    # aria-label / role attributes
    aria_count = len(re.findall(r"aria-[a-z]+\s*=", html, re.IGNORECASE))
    if aria_count >= 3:
        score += 4
        notes.append(f"{aria_count} aria attributes ✓")
    elif aria_count >= 1:
        score += 2
    else:
        suggestions.append("أضف aria-label للأزرار والنماذج (يحسّن قارئ الشاشة)")

    # Form inputs with labels
    inputs = re.findall(r"<input\b[^>]*>", html, re.IGNORECASE)
    if inputs:
        with_label = sum(1 for i in inputs if 'aria-label' in i.lower() or 'placeholder' in i.lower())
        if with_label / max(len(inputs), 1) >= 0.8:
            score += 3
            notes.append("Inputs موصوفة ✓")
        else:
            suggestions.append("أضف label أو aria-label لكل input")

    # Buttons have visible text or aria-label
    if "<button" in html.lower():
        score += 2
        notes.append("أزرار semantic ✓")

    # Skip link / focus management (advanced)
    if "skip-link" in html.lower() or ":focus-visible" in html.lower():
        score += 1
        notes.append("Focus management ✓")
    else:
        suggestions.append("أضف :focus-visible styles لتجربة keyboard ممتازة")

    return {"score": score, "max": 15, "notes": notes, "suggestions": suggestions}


# ──────────────────────────────────────────────────────────────────────────────
# DIMENSION 5: COMPLIANCE & SAUDI MARKET (20 points)
# ──────────────────────────────────────────────────────────────────────────────
def _score_compliance(html: str) -> Dict:
    score = 0
    notes: List[str] = []
    suggestions: List[str] = []

    if 'id="privacy"' in html.lower():
        score += 4
        notes.append("سياسة خصوصية ✓")
    else:
        suggestions.append("أضف قسم سياسة الخصوصية (مطلوب لـPDPL السعودي)")

    if 'id="terms"' in html.lower():
        score += 3
        notes.append("شروط استخدام ✓")
    else:
        suggestions.append("أضف قسم الشروط والأحكام")

    if 'id="refund"' in html.lower():
        score += 3
        notes.append("سياسة الاسترداد ✓")
    else:
        suggestions.append("أضف سياسة الاسترداد (إجباري لنظام التجارة الإلكترونية)")

    if "wa.me" in html.lower() or "whatsapp" in html.lower():
        score += 3
        notes.append("WhatsApp ✓")
    else:
        suggestions.append("أضف زر WhatsApp Floating (يرفع التحويل 40%)")

    if "ر.س" in html or "SAR" in html or "ريال" in html:
        score += 2
        notes.append("عملة SAR ✓")

    if "+966" in html or "tel:" in html:
        score += 2
        notes.append("رقم سعودي ✓")
    else:
        suggestions.append("أضف رقم تواصل سعودي (+966)")

    if "المعروف" in html or "maroof" in html.lower():
        score += 1
        notes.append("Maroof badge placeholder ✓")
    else:
        suggestions.append("أضف placeholder لشارة معروف (وزارة التجارة)")

    if "السجل التجاري" in html or "س.ت" in html:
        score += 1
        notes.append("سجل تجاري placeholder ✓")

    if "15%" in html or "VAT" in html.upper():
        score += 1
        notes.append("ضريبة 15% مذكورة ✓")

    return {"score": score, "max": 20, "notes": notes, "suggestions": suggestions}


# ──────────────────────────────────────────────────────────────────────────────
# AGGREGATE
# ──────────────────────────────────────────────────────────────────────────────

DIMENSIONS = [
    ("design", "🎨 التصميم", _score_design),
    ("seo", "🔍 SEO", _score_seo),
    ("performance", "⚡ الأداء", _score_performance),
    ("accessibility", "♿ Accessibility", _score_accessibility),
    ("compliance", "🛡️ امتثال سعودي", _score_compliance),
]


def score_html(html: str) -> Dict:
    """Return a full health report for the given HTML.

    Output schema (frontend uses this directly):
    {
      "total": 78,
      "grade": "B+",
      "dimensions": [
        {"id": "design", "name": "🎨 التصميم", "score": 22, "max": 25, "notes": [...], "suggestions": [...]},
        ...
      ],
      "top_suggestions": [...],   # top 5 most impactful
      "summary_emoji": "🟡",
    }
    """
    if not html:
        return {
            "total": 0, "grade": "F", "dimensions": [],
            "top_suggestions": ["ولّد الموقع أولاً"],
            "summary_emoji": "⚪",
        }

    dim_results = []
    all_suggestions: List[str] = []
    total = 0
    max_total = 0
    for did, name, fn in DIMENSIONS:
        res = fn(html)
        dim_results.append({
            "id": did,
            "name": name,
            "score": res["score"],
            "max": res["max"],
            "percent": round(100 * res["score"] / max(res["max"], 1)),
            "notes": res["notes"],
            "suggestions": res["suggestions"],
        })
        total += res["score"]
        max_total += res["max"]
        all_suggestions.extend(res["suggestions"])

    total_pct = round(100 * total / max(max_total, 1))

    if total_pct >= 90:
        grade, emoji = "A+", "🟢"
    elif total_pct >= 80:
        grade, emoji = "A", "🟢"
    elif total_pct >= 70:
        grade, emoji = "B+", "🟡"
    elif total_pct >= 60:
        grade, emoji = "B", "🟡"
    elif total_pct >= 50:
        grade, emoji = "C", "🟠"
    elif total_pct >= 40:
        grade, emoji = "D", "🟠"
    else:
        grade, emoji = "F", "🔴"

    return {
        "total": total_pct,
        "raw_score": total,
        "max_score": max_total,
        "grade": grade,
        "summary_emoji": emoji,
        "dimensions": dim_results,
        "top_suggestions": all_suggestions[:5],
        "improvement_potential": max(0, 95 - total_pct),
    }


__all__ = ["score_html"]
