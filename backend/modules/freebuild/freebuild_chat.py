"""FreeBuild Chat — conversational website builder with memory + asset approval flow.

Mirrors the Game Studio pattern: project → chat → tag-driven asset generation → approval.
"""
from __future__ import annotations
import os
import re
import uuid
import logging
import asyncio
import hashlib
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, Form, UploadFile, File
from pydantic import BaseModel
import base64
from cryptography.fernet import Fernet, InvalidToken

logger = logging.getLogger(__name__)


def _get_fernet() -> Fernet:
    """Derive a deterministic Fernet from JWT_SECRET (already a strong secret).
    Tokens stored encrypted at rest in MongoDB."""
    seed = os.environ.get("JWT_SECRET", "fallback-dev-secret-do-not-use")
    key = base64.urlsafe_b64encode(hashlib.sha256(seed.encode()).digest())
    return Fernet(key)


def _enc(plain: str) -> str:
    return _get_fernet().encrypt(plain.encode()).decode()


def _dec(cipher: str) -> Optional[str]:
    try:
        return _get_fernet().decrypt(cipher.encode()).decode()
    except (InvalidToken, ValueError):
        return None


def _mask(token: str) -> str:
    if not token:
        return ""
    if len(token) <= 8:
        return "•••"
    return f"{token[:4]}••••••{token[-4:]}"

# ─── Website types (like game types) ───
WEBSITE_TYPES = [
    {"id": "ecommerce", "title": "🏪 متجر إلكتروني", "desc": "متجر كامل مع كتالوج، سلة، دفع", "credits": 500},
    {"id": "landing", "title": "🚀 صفحة هبوط", "desc": "صفحة وحيدة لمنتج أو خدمة", "credits": 200},
    {"id": "corporate", "title": "💼 موقع شركة", "desc": "موقع رسمي للشركات", "credits": 400},
    {"id": "restaurant", "title": "🍔 مطعم / كافيه", "desc": "قائمة طعام + حجوزات + توصيل", "credits": 450},
    {"id": "clinic", "title": "🩺 عيادة / خدمي", "desc": "حجوزات + ملفات + نظام مواعيد", "credits": 380},
    {"id": "portfolio", "title": "🎨 بورتفوليو شخصي", "desc": "أعمالي + سيرة + تواصل", "credits": 250},
    {"id": "blog", "title": "📰 مدونة / مجلة", "desc": "مقالات + تصنيفات + كتّاب", "credits": 350},
    {"id": "saas", "title": "⚡ تطبيق SaaS", "desc": "تطبيق ويب كامل مع dashboard", "credits": 600},
]

# Tag regex for asset generation in AI responses
TAG_RE = re.compile(r"<<\s*(HERO|SECTION_BG|LOGO|PRODUCT|ICON|BANNER_AR|GALLERY)\s*[:：]\s*([^>]+?)\s*>>", re.IGNORECASE)

# Clickable choices the AI offers to the user
OPT_RE = re.compile(r"<<\s*OPT\s*[:：]\s*([^>]+?)\s*>>", re.IGNORECASE)

# HTML code-block extractor (```html ... ``` or ```<html> ... ```)
HTML_BLOCK_RE = re.compile(r"```(?:html|HTML)?\s*(<!DOCTYPE[\s\S]+?</html>|<html[\s\S]+?</html>)\s*```", re.IGNORECASE)
# Fallback: any code block containing full HTML
HTML_FALLBACK_RE = re.compile(r"(<!DOCTYPE[\s\S]+?</html>|<html[\s\S]+?</html>)", re.IGNORECASE)

# ─── SECTION BUILDER (incremental HTML construction) ─────────────────────
# The AI can write a single section instead of the whole page. The backend
# splices it into the existing current_html. This lets the AI build large
# sites (Quran, e-commerce, ...) one section per turn without hitting the
# response-size limit. Examples:
#   <<APPEND_SECTION id="contact">...</APPEND_SECTION>>   — adds before </body>
#   <<REPLACE_SECTION id="hero">...</REPLACE_SECTION>>    — overwrites a section
#   <<UPDATE_NAV>>home,الرئيسية|quran,القرآن|contact,تواصل<</UPDATE_NAV>>
APPEND_SECTION_RE = re.compile(
    r"<<\s*APPEND_SECTION\s+id\s*=\s*[\"']([a-zA-Z0-9_\-]+)[\"']\s*>>([\s\S]*?)<<\s*/\s*APPEND_SECTION\s*>>",
    re.IGNORECASE,
)
REPLACE_SECTION_RE = re.compile(
    r"<<\s*REPLACE_SECTION\s+id\s*=\s*[\"']([a-zA-Z0-9_\-]+)[\"']\s*>>([\s\S]*?)<<\s*/\s*REPLACE_SECTION\s*>>",
    re.IGNORECASE,
)
UPDATE_NAV_RE = re.compile(
    r"<<\s*UPDATE_NAV\s*>>([\s\S]*?)<<\s*/\s*UPDATE_NAV\s*>>",
    re.IGNORECASE,
)


def _merge_sections(current_html: str, append_sections: List[tuple], replace_sections: List[tuple], nav_items: Optional[List[tuple]] = None) -> Optional[str]:
    """
    Splice new/updated sections into the existing HTML.
    - append_sections: [(id, html_fragment), ...] inserted before </body>
    - replace_sections: [(id, html_fragment), ...] overwrites <section id="X">...</section>
    - nav_items: [(id, label), ...] rewrites the nav <a href="#id"> list (best-effort)
    Returns merged HTML or None on failure.
    """
    if not current_html:
        return None
    html = current_html
    # 1. REPLACE: find existing <section id="X"> ... </section> and swap
    for sec_id, frag in replace_sections:
        frag = frag.strip()
        # Ensure fragment is wrapped in a section tag if not already
        if not re.match(r"\s*<(section|div|main|article)\b", frag, re.IGNORECASE):
            frag = f'<section id="{sec_id}">{frag}</section>'
        pattern = re.compile(
            r"<section\b[^>]*\bid\s*=\s*[\"']" + re.escape(sec_id) + r"[\"'][^>]*>[\s\S]*?</section>",
            re.IGNORECASE,
        )
        if pattern.search(html):
            html = pattern.sub(lambda m: frag, html, count=1)
        else:
            # If section with that id doesn't exist yet, append it
            html = _splice_before_body_close(html, frag)
    # 2. APPEND: insert each new section just before </body>
    for sec_id, frag in append_sections:
        frag = frag.strip()
        if not re.match(r"\s*<(section|div|main|article)\b", frag, re.IGNORECASE):
            frag = f'<section id="{sec_id}">{frag}</section>'
        # Avoid duplicates: if a section with this id already exists, REPLACE instead
        dup_pattern = re.compile(
            r"<section\b[^>]*\bid\s*=\s*[\"']" + re.escape(sec_id) + r"[\"'][^>]*>[\s\S]*?</section>",
            re.IGNORECASE,
        )
        if dup_pattern.search(html):
            html = dup_pattern.sub(lambda m: frag, html, count=1)
        else:
            html = _splice_before_body_close(html, frag)
    # 3. UPDATE_NAV: replace anchors inside first <nav>...</nav>
    if nav_items:
        nav_html = "\n".join(
            f'        <a href="#{nid}" class="px-3 py-2 hover:text-emerald-400 transition">{label}</a>'
            for nid, label in nav_items
        )
        nav_pattern = re.compile(r"(<nav\b[^>]*>)([\s\S]*?)(</nav>)", re.IGNORECASE)
        if nav_pattern.search(html):
            html = nav_pattern.sub(lambda m: m.group(1) + "\n" + nav_html + "\n      " + m.group(3), html, count=1)
    return html


def _splice_before_body_close(html: str, fragment: str) -> str:
    """Insert fragment immediately before </body>, or append if no </body>."""
    if "</body>" in html.lower():
        return re.sub(r"</body>", fragment + "\n</body>", html, count=1, flags=re.IGNORECASE)
    if "</html>" in html.lower():
        return re.sub(r"</html>", fragment + "\n</html>", html, count=1, flags=re.IGNORECASE)
    return html + "\n" + fragment


def _extract_section_directives(text: str) -> Dict[str, Any]:
    """Pull APPEND/REPLACE/UPDATE_NAV directives out of the AI response."""
    appends = [(m.group(1), m.group(2)) for m in APPEND_SECTION_RE.finditer(text)]
    replaces = [(m.group(1), m.group(2)) for m in REPLACE_SECTION_RE.finditer(text)]
    nav_items: List[tuple] = []
    nav_m = UPDATE_NAV_RE.search(text)
    if nav_m:
        for pair in nav_m.group(1).split("|"):
            parts = [p.strip() for p in pair.split(",", 1)]
            if len(parts) == 2 and parts[0] and parts[1]:
                nav_items.append((parts[0], parts[1]))
    return {"appends": appends, "replaces": replaces, "nav_items": nav_items}


def _strip_section_directives(text: str) -> str:
    """Remove section directive tags from displayed chat text (they're internal)."""
    text = APPEND_SECTION_RE.sub("", text)
    text = REPLACE_SECTION_RE.sub("", text)
    text = UPDATE_NAV_RE.sub("", text)
    return text


def _verify_anchor_links(html: str) -> List[str]:
    """Return list of broken anchor links (nav href="#X" with no <section id="X">)."""
    if not html:
        return []
    anchors = re.findall(r'href\s*=\s*["\']#([a-zA-Z0-9_\-]+)["\']', html, re.IGNORECASE)
    section_ids = set(re.findall(r'<(?:section|div|main|article)\b[^>]*\bid\s*=\s*["\']([a-zA-Z0-9_\-]+)["\']', html, re.IGNORECASE))
    broken = []
    for a in anchors:
        if a not in ("", "top", "#") and a not in section_ids:
            broken.append(a)
    return broken


def _summarize_html(html: str) -> str:
    """Short description of an HTML snapshot for the version-history UI."""
    if not html:
        return "(فارغ)"
    title_m = re.search(r"<title[^>]*>([^<]+)</title>", html, re.IGNORECASE)
    title = title_m.group(1).strip()[:40] if title_m else ""
    section_ids = re.findall(r'<section\b[^>]*\bid\s*=\s*["\']([a-zA-Z0-9_\-]+)["\']', html, re.IGNORECASE)
    sec_count = len(section_ids)
    length_kb = len(html) // 1024
    parts = []
    if title:
        parts.append(f'"{title}"')
    if sec_count:
        parts.append(f"{sec_count} قسم")
        if section_ids[:3]:
            parts.append(f"({', '.join('#'+s for s in section_ids[:3])}{'...' if sec_count > 3 else ''})")
    parts.append(f"~{length_kb}KB" if length_kb else f"{len(html)}B")
    return " · ".join(parts)


def _extract_html(text: str) -> Optional[str]:
    m = HTML_BLOCK_RE.search(text)
    if m:
        return m.group(1).strip()
    m = HTML_FALLBACK_RE.search(text)
    if m:
        return m.group(1).strip()
    # Salvage truncated stream: ```html <!DOCTYPE...  with no closing ``` or </html>
    open_fence = re.search(r"```(?:html|HTML)?\s*(<!DOCTYPE[\s\S]+|<html[\s\S]+)$", text, re.IGNORECASE)
    if open_fence:
        partial = open_fence.group(1).strip()
        # Try to auto-close common tags
        if "</html>" not in partial.lower():
            partial += "\n</body></html>"
        return partial
    return None


def _extract_all_html_variants(text: str) -> List[str]:
    """Return ALL HTML blocks in the message (used for design variants)."""
    items: List[str] = []
    for m in HTML_BLOCK_RE.finditer(text):
        items.append(m.group(1).strip())
    if not items:
        # fallback for ungated <html>...</html>
        for m in HTML_FALLBACK_RE.finditer(text):
            items.append(m.group(1).strip())
    return items


# ─── TRUTHFULNESS VALIDATION ──────────────────────────────────────────────
# Phrases the AI uses to claim it produced output
_CLAIM_VARIANTS_RE = re.compile(
    r"(تصاميم\s+(?:متعددة|مختلفة|جاهزة|مقترحة)|إليك\s+(?:\d+|عدة|تصاميم)|"
    r"اخترت\s+لك\s+تصاميم|نزّلت\s+تصاميم|قدّمت\s+لك|تجد\s+\d+\s+تصاميم|"
    r"3\s+(?:خيارات|تصاميم|variants)|three\s+(?:designs|options))",
    re.IGNORECASE,
)
_CLAIM_UPDATE_RE = re.compile(
    r"(حدّثت\s+المعاينة|تم\s+التحديث|أضفت\s+(?:قسم|زر|الخاصية)|نشرت|"
    r"updated\s+the\s+preview|added\s+the\s+section|"
    r"تم\s+(?:بنجاح|إضافة|التعديل)\s|"
    r"خلصت\s+التحديث)",
    re.IGNORECASE,
)


def _validate_truthfulness(ai_text: str) -> Optional[str]:
    """Return error message if AI lied about producing content; None if OK."""
    html_count = len(_extract_all_html_variants(ai_text))
    has_opts = bool(OPT_RE.search(ai_text))
    has_assets = bool(TAG_RE.search(ai_text))
    has_section_dirs = bool(APPEND_SECTION_RE.search(ai_text) or REPLACE_SECTION_RE.search(ai_text))
    claim_variants = bool(_CLAIM_VARIANTS_RE.search(ai_text))
    claim_update = bool(_CLAIM_UPDATE_RE.search(ai_text))

    # Rule 1: claimed multiple designs/variants but produced <2 HTML blocks
    if claim_variants and html_count < 2:
        return (
            "ادّعيت إنك قدّمت تصاميم متعددة، لكن لم تُصدر بلوكات HTML فعلية. "
            "أعد الرد: أرسل 3 صفحات <!DOCTYPE html>...</html> كاملة، كل واحدة في ```html ...``` block منفصل، "
            "أو اعترف بصراحة إنك تحتاج معلومات أكثر قبل التصميم."
        )
    # Rule 2: claimed an update was made but produced no HTML/section/asset/option tags
    if claim_update and html_count == 0 and not has_section_dirs and not has_assets and not has_opts:
        return (
            "ادّعيت إنك حدّثت المعاينة أو أضفت قسماً، لكن لم تُصدر أي HTML أو APPEND_SECTION/REPLACE_SECTION. "
            "أعد الرد: إما أصدر بلوك ```html ...``` كامل، أو استخدم <<APPEND_SECTION id=\"...\">>...<</APPEND_SECTION>> لإضافة قسم، "
            "أو اعترف بصراحة إنك لم تطبّق التغيير."
        )
    # Rule 3: count mismatch — "5 تصاميم" but actually produced 3
    count_match = re.search(
        r"(?:قدّمت|أنشأت|صممت|نزّلت|أرسلت|إليك|اخترت\s+لك|تجد)\s+(\d+|ثلاث|أربع|خمس|ست|سبع|ثمان|تسع|عشر)\s+(?:تصاميم|تصميم|variants?|designs?|options?)",
        ai_text,
        re.IGNORECASE,
    )
    if count_match:
        word = count_match.group(1)
        word_map = {"ثلاث": 3, "أربع": 4, "خمس": 5, "ست": 6, "سبع": 7, "ثمان": 8, "تسع": 9, "عشر": 10}
        try:
            claimed = int(word) if word.isdigit() else word_map.get(word, 0)
        except (ValueError, KeyError):
            claimed = 0
        if claimed >= 2 and html_count != claimed:
            return (
                f"ادّعيت إنك قدّمت {claimed} تصاميم لكن أنتجت {html_count} فقط. "
                f"عدّ الـ```html``` blocks في ردك قبل إرساله. "
                f"إما أنتج {claimed} بلوكات فعلاً، أو عدّل الرقم في النص ليطابق العدد الفعلي."
            )
    # Rule 4: design variants that use EXTERNAL image URLs (we forbid this for variants)
    if html_count >= 2:
        all_v = _extract_all_html_variants(ai_text)
        external_urls = 0
        for v in all_v:
            if re.search(r'<img[^>]+src=["\']https?://(?!fonts\.googleapis\.com|cdn\.tailwindcss\.com)', v):
                external_urls += 1
        if external_urls > 0:
            return (
                f"{external_urls} من تصاميمك تحتوي على صور خارجية (URLs). "
                "التصاميم يجب تكون مستقلة 100% — استخدم gradient backgrounds، SVG inline، أو emoji كـplaceholders. "
                "أعد التصاميم بدون أي img src='http...' خارجي."
            )
    return None


# ─── DESIGN-DRIFT DETECTION ───────────────────────────────────────────────
def _design_signature(html: str) -> Dict[str, Any]:
    """Cheap structural fingerprint: counts of major sections + length bucket."""
    if not html:
        return {"length": 0, "sections": 0, "header": False, "footer": False, "navs": 0}
    h = html.lower()
    return {
        "length": len(html),
        "sections": h.count("<section"),
        "divs": h.count("<div"),
        "header": "<header" in h,
        "footer": "<footer" in h,
        "navs": h.count("<nav"),
        "h1s": h.count("<h1"),
    }


def _structural_drift_ratio(prev_sig: Dict[str, Any], new_sig: Dict[str, Any]) -> float:
    """0.0 = identical structure, 1.0 = completely different."""
    if not prev_sig.get("length"):
        return 0.0
    keys = ["sections", "divs", "navs", "h1s"]
    total = 0.0
    for k in keys:
        a, b = prev_sig.get(k, 0), new_sig.get(k, 0)
        m = max(a, b, 1)
        total += abs(a - b) / m
    total /= len(keys)
    # Length drift: only flag if NEW is drastically SHORTER (destructive)
    # or absurdly longer (likely garbage). Additive growth is normal.
    len_ratio = new_sig.get("length", 0) / max(prev_sig.get("length", 1), 1)
    if len_ratio < 0.5 or len_ratio > 3.5:
        total += 0.3
    return min(1.0, total)


def _is_additive_change(prev_sig: Dict[str, Any], new_sig: Dict[str, Any]) -> bool:
    """
    True if the new HTML kept all major old structural elements AND added more.
    Adding sections/divs while keeping header/footer/nav is a legitimate edit.
    """
    if not prev_sig.get("length"):
        return True
    # All major elements preserved or grown
    preserved = (
        new_sig.get("sections", 0) >= prev_sig.get("sections", 0)
        and new_sig.get("divs", 0) >= int(prev_sig.get("divs", 0) * 0.85)
        and new_sig.get("navs", 0) >= prev_sig.get("navs", 0)
        and (not prev_sig.get("header") or new_sig.get("header"))
        and (not prev_sig.get("footer") or new_sig.get("footer"))
    )
    # And new HTML is at least the same size (not destructive shrink)
    grew = new_sig.get("length", 0) >= int(prev_sig.get("length", 1) * 0.9)
    return preserved and grew


# Intent detection on user's latest message — distinguishes additive edits
# from "wipe everything and redo" requests so the drift gate doesn't punish
# legitimate growth.
_INTENT_ADDITIVE_RE = re.compile(
    r"(ضي?ف|أضف|اضف|زو?د|حط|أبي\s+قسم|أبي\s+ميزة|ابي\s+قسم|"
    r"أضف\s+قسم|اضف\s+قسم|أحتاج\s+قسم|أحتاج\s+صفحة|"
    r"\badd\b|\bappend\b|\binsert\b|\bmore\s+section|new\s+section|"
    r"also|كمان|بعد|زيادة|توسيع|expand)",
    re.IGNORECASE,
)
_INTENT_REDESIGN_RE = re.compile(
    r"(غيّ?ر\s+كل|صمم\s+من\s+جديد|تصميم\s+جديد\s+كلي|من\s+الصفر|أبدأ\s+من\s+جديد|"
    r"ابدأ\s+من\s+الصفر|اعد\s+التصميم|أعد\s+التصميم|تصميم\s+آخر|تصميم\s+مختلف\s+كلي|"
    r"\bredesign\b|\brebuild\b|from\s+scratch|start\s+over|completely\s+new)",
    re.IGNORECASE,
)
# Conversational / non-executive messages (questions about capability, self-talk,
# meta questions). These should NEVER trigger drift gate even if AI responds
# with sample HTML.
_INTENT_CONVERSATIONAL_RE = re.compile(
    r"(تكلم|كلّم|اشرح|وضّح|من\s+أنت|مين\s+أنت|كيف\s+تشتغل|"
    r"وش\s+تقدر|ايش\s+تقدر|قدراتك|مميزاتك|إمكانياتك|قدر?اتك|"
    r"فحص|تحدّث|قول\s+لي|اخبرني|اعرض\s+علي|"
    r"\bwhat\s+can\s+you|how\s+do\s+you|tell\s+me\s+about|"
    r"who\s+are\s+you|explain|describe|capabilities|"
    r"اسأل|سؤال|متى|لماذا|ليش|ليه)",
    re.IGNORECASE,
)


def _detect_user_intent(user_msg: str) -> str:
    """Returns 'conversational' | 'additive' | 'redesign' | 'modify'."""
    if not user_msg:
        return "modify"
    msg = user_msg.strip()
    # Conversational takes precedence (no code change implied)
    if _INTENT_CONVERSATIONAL_RE.search(msg) and not (
        _INTENT_ADDITIVE_RE.search(msg) or _INTENT_REDESIGN_RE.search(msg)
    ):
        return "conversational"
    if _INTENT_REDESIGN_RE.search(msg):
        return "redesign"
    if _INTENT_ADDITIVE_RE.search(msg):
        return "additive"
    return "modify"


# ─── ADAPTIVE TASK ROUTING — pick the right LLM specialty per turn ─────
# The Smart Orchestrator already maps task_type → priority list of models.
# Here we pick the best task_type based on what THIS turn actually needs:
#   • "design"        → Claude Opus 4.5 (best visual taste, variant generation)
#   • "website_build" → Kimi K2.6 / Claude Sonnet (clean HTML/JS generation)
#   • "reasoning_hard"→ GPT-5/Opus (debugging broken code, fixing logic)
#   • "long_context"  → Kimi K2.6 (256K context for huge multi-section sites)

def _classify_freebuild_task(
    user_msg: str,
    has_current_html: bool,
    current_html_len: int,
    is_retry_for_fix: bool = False,
) -> tuple[str, str]:
    """
    Returns (task_type, reason_label) — task_type for the orchestrator,
    and a human-readable label like "🎨 توليد تصاميم (Claude Opus)" surfaced
    to the user as live progress.
    """
    if is_retry_for_fix:
        return ("reasoning_hard", "🛠️ يصلّح أخطاء برمجية (GPT-5 / Opus)")

    msg = (user_msg or "").lower()

    # Conversational / meta question — quick chat response, no code work needed
    if _INTENT_CONVERSATIONAL_RE.search(user_msg or "") and not (
        _INTENT_ADDITIVE_RE.search(user_msg or "") or _INTENT_REDESIGN_RE.search(user_msg or "")
    ):
        return ("arabic", "💬 يحاور (Claude Opus — أفضل عربي)")

    # Big existing project → need long context (Kimi 256K)
    if has_current_html and current_html_len > 30_000:
        return ("long_context", "📚 يحلّل موقع كبير (Kimi 256K)")

    # Variant / multi-design request → design specialty
    variant_re = re.compile(
        r"(تصاميم|variants?|خيارات\s+تصميم|اقترح|نمط|أنماط|"
        r"design\s+options?|show\s+me\s+(?:designs?|options))",
        re.IGNORECASE,
    )
    # First time (no current_html) OR explicit visual exploration → design
    if not has_current_html or variant_re.search(msg):
        return ("design", "🎨 يصمم (Claude Opus 4.5)")

    # Debug/fix request → reasoning
    fix_re = re.compile(
        r"(أصلح|اصلح|fix|debug|مكسور|ما\s+يشتغل|مو\s+شغّال|"
        r"خطأ|error|broken|doesn'?t\s+work|not\s+working|"
        r"الزر\s+ما|الرابط\s+ما)",
        re.IGNORECASE,
    )
    if fix_re.search(msg):
        return ("reasoning_hard", "🧠 يحلّل ويصحّح (GPT-5 / Opus)")

    # Complex code request (multiple sections, advanced features) → coding_strong
    complex_re = re.compile(
        r"(مشغل|player|navigation|router|تفاعلي|interactive|"
        r"شريط\s+تحكم|controls|api\s+call|fetch|قاعدة\s+بيانات|"
        r"database|backend|auth|تسجيل\s+دخول|state\s+management)",
        re.IGNORECASE,
    )
    if complex_re.search(msg):
        return ("coding_strong", "⚡ كود متقدم (Kimi K2.6 + Opus)")

    # Code add/modify → website_build (Kimi K2.6 leads)
    return ("website_build", "💻 يكتب الكود (Kimi K2.6)")


def _strip_tags(text: str) -> str:
    """Remove <<TAG: ...>> markers from displayed text and collapse blank lines."""
    cleaned = TAG_RE.sub("", text)
    cleaned = OPT_RE.sub("", cleaned)
    # Collapse 3+ consecutive newlines to 2
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


# Strip code blocks from chat display (code lives ONLY in Live Preview).
# We hide HTML/CSS/JS code by default — user can pay to receive the code.
_CODE_BLOCK_RE = re.compile(r"```[a-zA-Z]*\n?[\s\S]*?```", re.MULTILINE)
# Unclosed/truncated fenced code: ```html ... <end-of-stream>
_UNCLOSED_FENCE_RE = re.compile(r"```[a-zA-Z]*\n?[\s\S]*$", re.MULTILINE)
# Raw HTML without fences (full <!DOCTYPE ... </html>)
_RAW_HTML_DOC_RE = re.compile(r"(<!DOCTYPE\s+html[\s\S]+?</html>)", re.IGNORECASE)
# Raw HTML fragment leak: large <body|<div|<section ... potentially unclosed
_RAW_HTML_FRAGMENT_RE = re.compile(
    r"(<(?:html|head|body|section|div|main|header|footer|nav)\b[\s\S]{50,})$",
    re.IGNORECASE,
)
# Inline CSS/JS that may leak
_RAW_CSS_LEAK_RE = re.compile(r"<style[\s\S]*?</style>", re.IGNORECASE)
_RAW_JS_LEAK_RE = re.compile(r"<script[\s\S]*?</script>", re.IGNORECASE)


def _strip_code_from_chat(text: str) -> str:
    """Remove fenced + raw code from displayed chat text. Code is kept in current_html.
    Aggressive multi-pass strip to handle truncated/partial AI output."""
    original_had_code = bool(
        _CODE_BLOCK_RE.search(text) or _RAW_HTML_DOC_RE.search(text) or _RAW_HTML_FRAGMENT_RE.search(text)
    )
    cleaned = _CODE_BLOCK_RE.sub("", text)
    # Truncated fence (AI got cut off mid-stream)
    cleaned = _UNCLOSED_FENCE_RE.sub("", cleaned)
    # Standalone raw HTML doc (no fence)
    cleaned = _RAW_HTML_DOC_RE.sub("", cleaned)
    cleaned = _RAW_CSS_LEAK_RE.sub("", cleaned)
    cleaned = _RAW_JS_LEAK_RE.sub("", cleaned)
    # Raw HTML fragment trailing leak
    cleaned = _RAW_HTML_FRAGMENT_RE.sub("", cleaned)
    if original_had_code:
        cleaned = cleaned.strip()
        if cleaned:
            cleaned = cleaned + "\n\n*✨ تم تحديث المعاينة الحية — افتح تبويب المعاينة للمشاهدة*"
        else:
            cleaned = "✨ تم تحديث المعاينة الحية — افتح تبويب المعاينة للمشاهدة"
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def _extract_options(text: str) -> List[str]:
    """Pull clickable choices out of AI response: <<OPT: ...>>."""
    opts = [m.group(1).strip() for m in OPT_RE.finditer(text)]
    if opts:
        return opts
    items, _ = _extract_options_fallback(text)
    return items


# Fallback patterns when AI forgets <<OPT>> but still writes a list under a question.
_LIST_LINE_RE = re.compile(r"^\s*(?:(?:[-•*]|\d+[\.\)]|[\u0660-\u0669]+[\.\)])\s+)(.+?)\s*$")


def _extract_options_fallback(text: str):
    """If the message contains a question followed by a numbered/bulleted list,
    treat the list items as clickable options. Returns (items, lines_to_strip_set)."""
    stripped = _strip_tags(text)
    if "؟" not in stripped and "?" not in stripped:
        return [], set()
    # Strip code blocks — never pull options from inside ```html ... ```
    cleaned = re.sub(r"```[\s\S]+?```", "", stripped)
    lines = cleaned.split("\n")
    items: List[str] = []
    consumed_lines: List[str] = []
    found_question = False
    current_block_items: List[str] = []
    current_block_lines: List[str] = []
    for line in lines:
        m = _LIST_LINE_RE.match(line)
        if m:
            current_block_items.append(m.group(1).strip())
            current_block_lines.append(line)
        else:
            if current_block_items and len(current_block_items) >= 2:
                items = current_block_items[:]
                consumed_lines = current_block_lines[:]
            current_block_items = []
            current_block_lines = []
            if "؟" in line or "?" in line:
                found_question = True
                items = []
                consumed_lines = []
    if current_block_items and len(current_block_items) >= 2:
        items = current_block_items
        consumed_lines = current_block_lines
    if not found_question and not items:
        return [], set()
    cleaned_items = []
    for it in items[:8]:
        x = re.sub(r"\*\*(.+?)\*\*", r"\1", it)
        x = re.sub(r"\*(.+?)\*", r"\1", x)
        x = x.rstrip(":：،,. ")
        if 1 <= len(x) <= 80:
            cleaned_items.append(x)
    if len(cleaned_items) < 2:
        return [], set()
    return cleaned_items, set(consumed_lines)


def _now():
    return datetime.now(timezone.utc).isoformat()


# Pydantic models — MUST be at module level (FastAPI resolves via globals)
class ProjectIn(BaseModel):
    name: str
    description: str = ""
    category_id: Optional[str] = None  # if set → template-based mode (websites)


class ChatIn(BaseModel):
    message: str


def make_freebuild_chat_router(db, get_current_user):
    router = APIRouter(prefix="/freebuild-chat", tags=["freebuild-chat"])

    # ===== Catalog =====
    @router.get("/types")
    async def list_types():
        return {"types": WEBSITE_TYPES}

    # ===== Create project =====
    @router.post("/project")
    async def create_project(payload: ProjectIn, user=Depends(get_current_user)):
        pid = str(uuid.uuid4())
        category_meta = None
        if payload.category_id:
            try:
                from modules.websites.catalog import CATEGORIES
                category_meta = next((c for c in CATEGORIES if c["id"] == payload.category_id), None)
            except Exception:
                category_meta = None
        await db.freebuild_projects.insert_one({
            "id": pid,
            "user_id": user["user_id"],
            "website_type": "template" if payload.category_id else "custom",
            "category_id": payload.category_id,
            "category_name": (category_meta or {}).get("name"),
            "category_icon": (category_meta or {}).get("icon"),
            "name": payload.name.strip()[:120],
            "description": payload.description.strip()[:1500],
            "status": "active",
            "current_phase": "design" if payload.category_id else "discovery",
            "messages": [],
            "approved_assets": [],
            "current_html": None,
            "preview_url": None,
            "created_at": _now(),
            "updated_at": _now(),
        })
        return {"id": pid, "name": payload.name}

    # ===== List projects =====
    @router.get("/projects")
    async def list_projects(user=Depends(get_current_user)):
        cur = db.freebuild_projects.find(
            {"user_id": user["user_id"], "status": {"$ne": "deleted"}}, {"_id": 0}
        ).sort("updated_at", -1).limit(50)
        items = await cur.to_list(length=50)
        return {"projects": items}

    # ===== Get single project =====
    @router.get("/project/{pid}")
    async def get_project(pid: str, user=Depends(get_current_user)):
        proj = await db.freebuild_projects.find_one(
            {"id": pid, "user_id": user["user_id"]}, {"_id": 0}
        )
        if not proj:
            raise HTTPException(404, "المشروع غير موجود")
        return proj

    # ===== Chat (the core flow — multipart: text + optional image attachments) =====
    @router.post("/project/{pid}/chat")
    async def chat(
        pid: str,
        message: str = Form(...),
        files: List[UploadFile] = File(default=[]),
        reference_asset_id: str = Form(default=""),
        answer_meta: str = Form(default=""),
        user=Depends(get_current_user),
    ):
        proj = await db.freebuild_projects.find_one(
            {"id": pid, "user_id": user["user_id"]}, {"_id": 0}
        )
        if not proj:
            raise HTTPException(404, "المشروع غير موجود")

        # Parse answer_meta JSON (sent when user clicks AI's offered options)
        parsed_answer_meta: Optional[Dict[str, Any]] = None
        if answer_meta:
            try:
                import json as _json
                am = _json.loads(answer_meta)
                if isinstance(am, dict):
                    parsed_answer_meta = {
                        "picks": list(am.get("picks", []))[:10],
                        "comment": str(am.get("comment", ""))[:500],
                    }
            except Exception:
                pass

        # Read uploaded image files → base64 (for vision context)
        vision_images: List[Dict[str, Any]] = []
        attachment_meta: List[Dict[str, str]] = []
        for f in files[:4]:  # max 4 images per turn
            try:
                data = await f.read()
                if len(data) > 6 * 1024 * 1024:  # 6 MB
                    continue
                ctype = (f.content_type or "image/png").lower()
                if not ctype.startswith("image/"):
                    continue
                b64 = base64.b64encode(data).decode()
                vision_images.append({
                    "type": "image",
                    "source": {"type": "base64", "media_type": ctype, "data": b64},
                })
                attachment_meta.append({"name": f.filename or "image", "type": ctype, "size": len(data)})
            except Exception as _e:
                logger.warning(f"freebuild attachment read failed: {_e}")

        # If user is replying to a specific in-chat asset, pull it from DB and add to vision
        reference_meta: Optional[Dict[str, Any]] = None
        if reference_asset_id:
            ref_asset = None
            for m in proj.get("messages", []):
                for a in (m.get("pending_assets") or []):
                    if a.get("id") == reference_asset_id:
                        ref_asset = a
                        break
                if ref_asset:
                    break
            if not ref_asset:
                for a in proj.get("approved_assets", []):
                    if a.get("id") == reference_asset_id:
                        ref_asset = a
                        break
            if ref_asset and ref_asset.get("image_url"):
                try:
                    import httpx
                    img_url = ref_asset["image_url"]
                    # HTTP fetch (works for both internal-routed and external URLs)
                    abs_url = img_url
                    if abs_url.startswith("/"):
                        backend_internal = os.environ.get("BACKEND_INTERNAL_URL", "http://localhost:8001")
                        abs_url = f"{backend_internal.rstrip('/')}{abs_url}"
                    async with httpx.AsyncClient(timeout=15) as cli:
                        rr = await cli.get(abs_url)
                        if rr.status_code == 200 and rr.content:
                            ctype = rr.headers.get("content-type", "image/png").split(";")[0]
                            b64 = base64.b64encode(rr.content).decode()
                            vision_images.append({
                                "type": "image",
                                "source": {"type": "base64", "media_type": ctype, "data": b64},
                            })
                            reference_meta = {
                                "asset_id": reference_asset_id,
                                "type": ref_asset.get("type", "asset"),
                                "image_url": ref_asset.get("image_url"),
                                "prompt": ref_asset.get("prompt", ""),
                            }
                except Exception as e:
                    logger.warning(f"freebuild reference fetch failed: {e}")

        # Build conversation history (last 12 turns)
        history = proj.get("messages", [])[-12:]
        msg_list = [{"role": m["role"], "content": m["content"]} for m in history]

        # Current user turn: text + (optional) images
        prefix_text = message
        if reference_meta:
            prefix_text = (
                f"[ردّ المستخدم على الصورة المرفقة "
                f"(النوع: {reference_meta['type']}، البرومبت الأصلي: {reference_meta['prompt'][:80]})]\n\n"
                f"{message}"
            )
        if vision_images:
            user_content: Any = [{"type": "text", "text": prefix_text}] + vision_images
        else:
            user_content = prefix_text
        msg_list.append({"role": "user", "content": user_content})

        # Context for the agent (no website type — fully open / from scratch)
        # List of approved assets with URLs so the AI can reference them
        assets_for_use = ""
        if proj.get("approved_assets"):
            assets_for_use = "\n\n🖼️ صور جاهزة معتمدة (استخدمها مباشرة بالـ URL):\n"
            for a in proj["approved_assets"][-15:]:
                if a.get("image_url"):
                    assets_for_use += f'  • {a["type"]}: "{a["prompt"][:50]}" → {a["image_url"]}\n'

        # Connection / deployment context (only in guided independence mode)
        guided_ctx = ""
        if proj.get("code_unlocked") and proj.get("tier") == "guided":
            conns = await db.freebuild_connections.find(
                {"project_id": pid, "user_id": user["user_id"]},
                {"_id": 0, "provider": 1, "mask": 1, "extra": 1},
            ).to_list(length=10)
            conn_map = {c["provider"]: c for c in conns}
            guided_ctx = (
                "\n\n🚀 وضع الاستقلالية المُرشَدة (Premium Guided $99):\n"
                "العميل اشترى باقة الإرشاد الكامل. وظيفتك الآن مرشد نشر فعلي خطوة بخطوة.\n"
                "📋 حالة الاتصالات الحالية:\n"
                f"  • GitHub: {'✅ مربوط (' + conn_map['github']['mask'] + ')' if 'github' in conn_map else '❌ غير مربوط — اطلب من العميل ربطه من زر الاتصالات'}\n"
                f"  • Vercel: {'✅ مربوط (' + conn_map['vercel']['mask'] + ')' if 'vercel' in conn_map else '❌ غير مربوط'}\n"
                f"  • Cloudflare: {'✅ مربوط (' + conn_map['cloudflare']['mask'] + ')' if 'cloudflare' in conn_map else '❌ غير مربوط'}\n"
                f"  • Domain: {'✅ ' + conn_map['domain'].get('extra', '') if 'domain' in conn_map else '❌ غير محدد'}\n"
                "\n"
                "🎯 خطوات الإرشاد التدريجية (بطيء ومنظم، لا تستعجل):\n"
                "1. تأكد من ربط GitHub أولاً — اشرح للعميل كيف يولّد PAT (Personal Access Token):\n"
                "   - يدخل: https://github.com/settings/tokens?type=beta → Generate new token\n"
                "   - الصلاحيات المطلوبة: Contents (Read/Write) + Workflows (Read/Write)\n"
                "   - يلصق التوكن في 'إعدادات الاتصالات' (سيظهر زر أعلى الشات)\n"
                "2. بعد ربط GitHub، اقترح اسم للمستودع واطلب الموافقة، ثم سأل العميل يضغط زر 'ادفع لـ GitHub' في تبويب المعاينة الحية.\n"
                "3. بعد رفع الكود، أرشده لتفعيل GitHub Pages أو ربط Vercel.\n"
                "4. لما يطلب دومين مخصص، اطلب منه ربط Cloudflare token وأرشده لإعداد DNS records.\n"
                "5. اعطه فيديو-مرجعي أو screenshot وصفية لكل خطوة (وصف بالكلمات).\n"
                "✋ تذكير: لا تستعجل! اشرح كل خطوة بهدوء وتأكد من فهم العميل قبل الانتقال.\n"
                "إذا العميل بدا متعجلاً، ذكّره بفائدة كل خطوة.\n"
            )
        elif proj.get("code_unlocked"):
            guided_ctx = (
                "\n\n💻 وضع استلام الكود ($49):\n"
                "العميل اشترى الكود فقط — هو مبرمج محترف لا يحتاج إرشاد طويل. كن مختصراً وموجزاً.\n"
                "يقدر يستعمل أزرار 'نسخ الكود' و 'تحميل HTML' و 'دفع لـ GitHub' (إذا ربط token).\n"
                "ركّز على إجابات تقنية مختصرة فقط لما يسأل.\n"
            )

        # Template-based project (Websites Studio mode)
        template_ctx = ""
        if proj.get("category_id"):
            cat_name = proj.get("category_name", "")
            cat_id = proj.get("category_id", "")
            template_ctx = (
                f"\n\n🏷️ مشروع قائم على قالب جاهز (Template Mode):\n"
                f"الفئة: {cat_name} ({cat_id})\n"
                "📌 سلوك خاص بالقوالب:\n"
                "- العميل اختار قالباً من فئة محددة. لا تسأل أسئلة استكشاف طويلة.\n"
                "- في رسالتك الأولى، اطرح 3 تصاميم variants لنفس الفئة بأنماط مختلفة:\n"
                "  • Variant 1: أناقة كلاسيكية\n"
                "  • Variant 2: حداثة معاصرة (glassmorphism)\n"
                "  • Variant 3: مينيمال نظيف\n"
                "  كل واحد <!DOCTYPE html>...</html> كامل (≤300 سطر) مع Tailwind CDN ومحتوى مناسب للفئة.\n"
                "- بعد ما يختار، خذ معلوماته (اسم النشاط، رقم تواصل، عنوان) عبر <<OPT>> قدر الإمكان.\n"
                "- لا تعيد تصميم القالب — فقط استبدل النصوص والصور والألوان الثانوية.\n"
            )


        extra_ctx = (
            f"اسم المشروع: {proj['name']}\n"
            f"وصف المشروع: {proj['description'] or '(لم يحدد العميل وصفاً بعد — اسأله ودَوّن)'}\n"
            f"{assets_for_use}"
            f"{template_ctx}"
            f"{guided_ctx}\n"
            "📌 بروتوكول الإنشاء من الصفر (مهم جداً):\n"
            "1. ابدأ بالاستماع — اسأل العميل عن: نشاطه/فكرته، جمهوره المستهدف، الإحساس المطلوب، أمثلة ملهمة.\n"
            "2. اقترح 2-3 اتجاهات تصميم مختلفة (ألوان/typography/تخطيط) قبل ما تنفذ شي.\n"
            "3. لما يختار اتجاه، نفّذ بإصدار صغير (Hero فقط) واستشره قبل بناء الباقي.\n"
            "4. لما تحتاج صورة، اكتبها بصيغة تاق فقط (لا تضعها داخل HTML):\n"
            "   <<HERO: english description>>  أو  <<LOGO: brand>>  أو  <<BANNER_AR: نص>>  أو  <<ICON: ...>>\n"
            "   النظام راح يولّدها تلقائياً ويعرضها للمستخدم لاعتمادها.\n"
            "5. بعد ما المستخدم يعتمد الصور (تشوفها في 'صور جاهزة معتمدة' أعلاه)، استخدم URL مباشر في الـ HTML.\n"
            "6. لما تكتب HTML للمعاينة، اكتبه داخل ```html ... ``` ويكون <!DOCTYPE html>...</html> كامل مع Tailwind CDN و RTL.\n"
            "   ⚠️ المستخدم لن يرى الكود داخل الشات — الكود يُعرض فقط في 'المعاينة الحية'. لا تشرح الكود ولا تذكر تفاصيل تقنية في رسائلك.\n"
            "   اكتب فقط مقدمة قصيرة مثل: 'جاهز! حدّثت المعاينة الحية — شوفها في تبويب المعاينة 👀' ثم الكود.\n"
            "   لا تكتب: 'إليك ما عملته في الكود: لقد استخدمت emerald-500...' — هذي تفاصيل ما تهم المستخدم العادي.\n"
            "\n"
            "🚫 قاعدة الحظر الكامل لتسريب الكود:\n"
            "• ❌ لا تكتب أي كود HTML/CSS/JS خارج بلوك ```html ... ``` مغلق.\n"
            "• ❌ لا تكتب أمثلة كود قصيرة كمثل `<button class=\"...\">` في النص العادي.\n"
            "• ❌ لا تذكر أسماء classes/Tailwind أو خصائص CSS في الرسائل النصية.\n"
            "• ❌ لا تطرح كود ناقص أبداً — إما كامل من <!DOCTYPE> إلى </html> أو لا تطرح أصلاً.\n"
            "• إذا الموقع طويل جداً (>700 سطر)، قسّمه على مراحل: في كل رسالة اكتب نسخة كاملة لكن مختصرة، ثم اسأل: 'هل تبي أزود قسم X؟' وانتظر الرد.\n"
            "\n"
            "🛑 قاعدة عدم التوقف وسط الكود (مهمة جداً):\n"
            "• إذا حسيت إن المساحة المتاحة لا تكفي لكتابة الـHTML كامل، **لا تبدأ كتابة الكود أصلاً**.\n"
            "• بدل ذلك، اسأل سؤالاً ذكياً يقلّص النطاق: 'في الجولة الأولى، أركّز على Hero + قسم المنتجات فقط، أم تبي footer أيضاً؟'\n"
            "• استخدم خيارات قابلة للضغط <<OPT: ...>> لتسهيل الرد.\n"
            "• الهدف: كل رسالة تحتوي إما (شرح وأسئلة) أو (كود HTML كامل ومغلق). لا تخلط بينهما إذا الكود ما راح يكتمل.\n"
            "\n"
            "🏗️ **اللب الذكي: استراتيجية البناء التدريجي (Section Builder) — مهمة جداً للمواقع الكبيرة:**\n"
            "❌ خطأ شائع: محاولة كتابة موقع 7 أقسام (قرآن + تحفيظ + تفسير + صوتيات + إعدادات + ...) في رسالة واحدة → يتقطّع في المنتصف ويصير كذبة.\n"
            "✅ الحل: **اكتب الـshell أولاً، ثم املأ قسم بقسم في رسائل لاحقة**.\n"
            "\n"
            "📋 **خطة موقع كبير على 3-7 جولات**:\n"
            "  • **الجولة 1 (Shell)**: ```html بـ200-400 سطر فقط: <!DOCTYPE> + Tailwind CDN + RTL + header + nav (روابط لكل الأقسام بـ#anchors) + 7 أقسام **فاضية** فيها فقط placeholder بسيط: `<section id=\"quran\" class=\"min-h-screen py-20\"><h2>قسم القرآن (قيد البناء)</h2></section>` + footer.``` ← هذا الكامل في رسالة وحدة.\n"
            "  • **الجولة 2**: استخدم `<<REPLACE_SECTION id=\"quran\">>` لملء قسم القرآن كامل بالميزات الحقيقية (audio player + قائمة سور + قارئ). ما تكتب باقي الـHTML — فقط محتوى القسم الجديد. الحجم: ~150-300 سطر.\n"
            "  • **الجولة 3**: `<<REPLACE_SECTION id=\"audio\">>` لقسم الصوتيات.\n"
            "  • وهكذا لكل قسم.\n"
            "\n"
            "🔧 **صيغة الـsection directives** (الـbackend يدمجها تلقائياً في current_html — أنت ما تحتاج تعيد كتابة الموقع):\n"
            "```\n"
            "<<APPEND_SECTION id=\"contact\">>\n"
            "<section id=\"contact\" class=\"py-20 bg-zinc-900\">\n"
            "  <div class=\"container mx-auto px-6\">\n"
            "    <h2 class=\"text-4xl font-bold mb-8\">تواصل معنا</h2>\n"
            "    <form>...</form>\n"
            "  </div>\n"
            "</section>\n"
            "<</APPEND_SECTION>>\n"
            "```\n"
            "  • `APPEND_SECTION`: لإضافة قسم **جديد** (يُدرج قبل `</body>`).\n"
            "  • `REPLACE_SECTION`: لاستبدال قسم موجود بنفس الـid.\n"
            "  • `UPDATE_NAV`: لتحديث الـnav links — مثال: `<<UPDATE_NAV>>home,الرئيسية|quran,القرآن|contact,تواصل<</UPDATE_NAV>>`.\n"
            "\n"
            "⚠️ **متى تستخدم Section Builder vs HTML كامل**:\n"
            "  • موقع بقسم أو اثنين فقط (~500 سطر إجمالي) → اكتب ```html``` كامل في رسالة واحدة.\n"
            "  • موقع بـ3+ أقسام كبيرة (قرآن، متجر، تعليم) → **ابدأ بـshell، ثم section-by-section**.\n"
            "  • تعديل قسم واحد فقط في موقع موجود → `REPLACE_SECTION` (لا تعيد كامل الـHTML).\n"
            "  • إضافة قسم جديد لموقع موجود → `APPEND_SECTION`.\n"
            "\n"
            "🔗 **قاعدة الروابط الفعلية (تجنّب الأزرار المعطوبة)**:\n"
            "  • كل زر/رابط في الـnav أو الـCTA يجب يشير لـanchor فعلي موجود: `<a href=\"#quran\">القرآن</a>` فقط لو فيه `<section id=\"quran\">` فعلاً في الـHTML.\n"
            "  • النظام يفحص تلقائياً ويسجّل تحذير لو نَفّى الذكاء على روابط معطوبة.\n"
            "  • للـscroll smooth، أضف `<style>html { scroll-behavior: smooth; }</style>` في الـhead.\n"
            "\n"
            "🎨 تصاميم متعددة (Design Variants) — اللب الذكي:\n"
            "عند تقديم خيارات تصميم للعميل، اكتب 2-3 صفحات HTML كاملة في رسالة واحدة — كل واحدة في ```html ...``` block منفصل.\n"
            "النظام راح يعرضها للعميل كـ live mini-previews يضغط عليها ويختار وحدة → اللي يختاره يصير current_html مباشرة بدون تغيير.\n"
            "كل variant يجب أن يكون كامل ومستقل (<!DOCTYPE html>...</html>) مع Tailwind CDN ومحتوى وهمي (Lorem) لكنه مرتب.\n"
            "اجعل كل variant مختصر (200-300 سطر max) عشان كلهم يكتملوا في رسالة وحدة.\n"
            "أمثلة على متى تستخدم variants: 'وش الأنسب: تصميم 1 (داكن فاخر) ولا 2 (فاتح ناعم) ولا 3 (مينيمال)؟'\n"
            "بعد ما العميل يختار، عدّل عليه تدريجياً — لا تعيد تصميم من الصفر.\n"
            "\n"
            "🚫 قاعدة الـ Variants النظيفة (مهمة جداً):\n"
            "• ❌ ممنوع تماماً استخدام صور خارجية في الـvariants — لا <img src='https://...'> ولا <img src='/api/...'>.\n"
            "• ❌ ممنوع <<HERO:>>, <<LOGO:>>, <<BANNER_AR:>>, <<ICON:>> في رسالة الـvariants. الـvariants يجب تكون مستقلة وفورية.\n"
            "• ✅ استخدم بدائل CSS/SVG/Emoji كـ placeholders:\n"
            "   - خلفيات: linear-gradient, radial-gradient, conic-gradient, mesh-gradient\n"
            "   - أشكال: SVG inline (<svg viewBox=...>...</svg>)، CSS shapes، Tailwind shapes\n"
            "   - رموز: 🍽️🌹💎🚗🏠⚡ كـicons كبيرة بـ text-6xl\n"
            "   - placeholder للصور: <div class='aspect-video bg-gradient-to-br from-rose-500 to-amber-500'></div>\n"
            "• السبب: الـvariant اللي يشوفه العميل = الكود اللي ينتقل للايف **بدون تغيير**. لا انتظار لـFal.ai.\n"
            "\n"
            "🔢 قاعدة العدّ الذاتي (الذكاء يفحص نفسه قبل الإرسال):\n"
            "قبل ما تكتب جملة فيها رقم تصاميم، **عُدّ بالفعل** كم ```html``` block أنت كاتبها.\n"
            "إذا قلت 'إليك 5 تصاميم' يجب فعلاً يكون عندك 5 بلوكات HTML كاملة (وليس 3 أو 4).\n"
            "إذا قلت 'إليك 3 تصاميم' وأنتجت 2 → النظام يرفض رسالتك ويعيدها لك.\n"
            "الأسلم: قُل 'إليك تصاميم' (بدون رقم) ثم أنتج اللي تقدر عليه فعلاً.\n"
            "أو: لو تبي تذكر رقم، اكتب التصاميم أولاً، ثم عُدّها، ثم اكتب الجملة برقم صحيح.\n"
            "\n"
            "✅ التحقق الذاتي (لا تكذب على العميل):\n"
            "بعد ما تنشئ أي قسم جديد في الـHTML، اختتم رسالتك بـ checklist واضح:\n"
            "  ✓ Hero: موجود ويحتوي زر CTA يشير إلى #contact\n"
            "  ✓ المنتجات: 3 cards مع صور placeholder\n"
            "  ⚠️ نموذج التواصل: لم أضفه بعد — سأضيفه في الجولة القادمة\n"
            "إذا قلت 'أضفت X' بدون فعلاً تضيفه في الكود → هذي خيانة لثقة العميل. الصدق أولاً.\n"
            "إذا في عنصر معطوب أو رابط فارغ، اذكر ذلك بصراحة كـ ⚠️ بدل ما تخفيها.\n"
            "\n"
            "\n"
            "📐 خطة عمل + Shell معاً (للمواقع متعددة الأقسام — قرآن، تعليم، تجارة، إلخ):\n"
            "إذا الموقع له **أقسام منفصلة**، اكتب في **نفس رسالتك الأولى**:\n"
            "  1️⃣ خطة سريعة (5-6 سطور):\n"
            "    ### 📋 خطة الموقع\n"
            "    • #home: الصفحة الرئيسية\n"
            "    • #quran: قائمة السور + قارئ تفاعلي\n"
            "    • #audio: صوتيات MP3 مع controls\n"
            "    • #settings: تخصيص\n"
            "  2️⃣ ```html``` يحتوي **shell كامل** (200-400 سطر): header + nav (بـanchors لكل الأقسام) + كل الـsections placeholder + footer.\n"
            "  3️⃣ سؤال واحد: 'الـshell جاهز — أبدأ بقسم #quran الكامل ولا تبي ترتيب آخر؟ <<OPT: ابدأ بـquran>> <<OPT: ابدأ بـaudio>>'\n"
            "**لا تنتظر موافقة على الخطة قبل كتابة الـshell**. اكتبهم معاً في نفس الرسالة. الخطة شرح، الـshell تنفيذ.\n"
            "بعدها استخدم Section Builder (`REPLACE_SECTION`) لملء كل قسم في رسائل لاحقة.\n"
            "\n"
            "🔗 لما تبني موقع متعدد الأقسام:\n"
            "• استخدم anchors `<section id='quran'>` مع navigation `<a href='#quran'>`\n"
            "• ✋ ممنوع: زر 'القرآن' يـscroll في الـHero — يجب يوديك لـ#quran فعلياً\n"
            "• استخدم مصادر صحيحة (CDN قرآن من api.alquran.cloud) عوضاً عن placeholder\n"
            "• كل قسم له audio/video/text controls شغّالة فعلياً، مش مجرد icons\n"
            "\n"

            "🚀 **قاعدة التنفيذ الفوري (READ FIRST — هذي تعلو على كل القواعد التالية)**:\n"
            "═══════════════════════════════════════════════════════════════\n"
            "أنت **مطوّر مُنفّذ** مو مستشار. الافتراضي = **اكتب الكود الآن**.\n"
            "\n"
            "💬 **لكن: ميّز بين 3 أنواع رسائل**:\n"
            "  🟦 **سؤال محادثة (Conversational)** — مثل: 'كلّم عن نفسك'، 'وش قدراتك'، 'كيف تشتغل'، 'اشرح لي'، 'فحص ذاتي':\n"
            "     → جاوب نص فقط بدون HTML. لا تكتب ```html``` ولا تاقات. حوار طبيعي مهذّب.\n"
            "  🟢 **طلب تنفيذي** — مثل: 'ابني، اعمل، نفّذ، صمم، اكتب، ضيف، عدّل، غيّر':\n"
            "     → اكتب الكود فوراً بدون أي سؤال موافقة. هذا الافتراضي.\n"
            "  🟡 **طلب توضيح/تخطيط** — مثل: 'قبل ما تبني، شرح الخطة':\n"
            "     → اكتب الخطة + الـshell معاً في نفس الرسالة. لا تنتظر موافقة على الخطة.\n"
            "\n"
            "🟢 **متى تكتب HTML فوراً بدون أي سؤال موافقة**:\n"
            "  • أول مرة في المشروع (current_html فاضي) → اكتب الـshell كاملاً فوراً.\n"
            "  • العميل قال 'ابني، اعمل، نفّذ، صمم لي، اكتب' → اكتب الكود فوراً.\n"
            "  • طلب إضافة قسم جديد → استخدم `APPEND_SECTION` فوراً.\n"
            "  • طلب تعديل قسم موجود → استخدم `REPLACE_SECTION` فوراً.\n"
            "  • طلب تغيير ألوان/نصوص/صور → نفّذ فوراً.\n"
            "  • أي طلب صريح يتضمن فعل تنفيذي → نفّذ فوراً.\n"
            "\n"
            "🟡 **متى تسأل سؤال واحد فقط قبل التنفيذ**:\n"
            "  • فقط حالة واحدة: current_html موجود + العميل قال صراحة 'صمم لي من جديد كلياً' أو 'غيّر التصميم كاملاً' أو 'ابدأ من الصفر'.\n"
            "  • في هذي الحالة فقط: 'هل تأكد؟ التصميم الحالي محفوظ تلقائياً.' وانتظر.\n"
            "  • **في كل الحالات الثانية، اكتب الكود فوراً**.\n"
            "\n"
            "🔴 **ممنوع منعاً باتاً**:\n"
            "  • الكذب بقولك 'تم' بدون كتابة كود فعلي.\n"
            "  • تأخير الكود بحجة 'انتظر موافقة' في الحالات اللي ما تحتاج موافقة.\n"
            "  • قول 'نظامي يمنعني' أو 'في قيد على' — **ما في قيد يمنعك**. اكتب وامضِ.\n"
            "  • كتابة HTML عرضي في رسالة محادثة (سؤال meta) — جاوب نص فقط.\n"
            "  • قول 'أحتاج مبرمج backend' أو 'الـbackend خارج قدرتي' — **أنت تبني الـbackend بـFirebase/Supabase/localStorage بدون أي backend منفصل**. أي تطبيق ويب يمكن بناؤه client-side في 2026.\n"
            "═══════════════════════════════════════════════════════════════\n"
            "\n"
            "🚨 قواعد ثقة (فحص ذاتي قبل الإرسال — مو عقوبات، بس صدق مع العميل):\n"
            "1. لو قلت 'إليك 3 تصاميم' أو 'نزّلت تصاميم' → عُدّ الـ```html``` blocks قبل الإرسال. إذا قلت 3 وكتبت 2 → عدّل الجملة لـ'إليك تصميمين'.\n"
            "2. لو قلت 'حدّثت' أو 'أضفت قسم X' → يجب يكون عندك:\n"
            "   • بلوك ```html``` كامل، **أو**\n"
            "   • `<<APPEND_SECTION id=\"X\">>...<</APPEND_SECTION>>`، **أو**\n"
            "   • `<<REPLACE_SECTION id=\"X\">>...<</REPLACE_SECTION>>`.\n"
            "   أي واحد من هذي الثلاثة كافي. النظام يكتشف ويدمج تلقائياً.\n"
            "3. **حرية كاملة في الإضافة والتعديل** (هذي مو قيود — هذي قدرات):\n"
            "   ✅ أضف أي قسم جديد بدون إذن خاص — استخدم `APPEND_SECTION`\n"
            "   ✅ عدّل أي قسم موجود — استخدم `REPLACE_SECTION`\n"
            "   ✅ غيّر الـnav links — استخدم `UPDATE_NAV`\n"
            "   ✅ بدّل النصوص/الصور/الألوان — استخدم HTML كامل\n"
            "   النظام يحميك فقط من خطأ واحد: حذف header أو footer بالخطأ. أي إضافة أو تعديل → يمر بدون مشكلة.\n"
            "4. قبل ما تقول 'تم'، **افحص بنفسك**: هل الكود فعلاً يحتوي التغيير؟ إذا لا، صحّحه قبل الإرسال.\n"
            "\n"
            "🛡️ **حماية إعادة التصميم الكلي** (يطبّق في حالة واحدة فقط):\n"
            "هذا البروتوكول **مو** عن كتابة HTML أول مرة، ولا عن إضافة أقسام، ولا عن تعديل لون. هذا فقط لما:\n"
            "  ✦ current_html موجود فعلاً (موقع شغّال) + \n"
            "  ✦ العميل قال بوضوح: 'غيّر التصميم كله' / 'صمم من جديد كلياً' / 'تصميم مختلف تماماً'.\n"
            "\n"
            "في هذي الحالة فقط، اتبع 3 خطوات:\n"
            "  1. سؤال واحد للتأكيد + انتظر.\n"
            "  2. اقترح التصميم الجديد كـPreview كامل + سؤال اعتماد.\n"
            "  3. عند الاعتماد: احتفظ بالـ`<script>` و `<section id>` ومحتواها الوظيفي — غيّر **الشكل فقط**.\n"
            "\n"
            "💾 شبكة الأمان: النظام يحفظ snapshots تلقائياً (آخر 20 نسخة) — العميل يقدر يسترجع أي وقت من زر 'السجل'.\n"
            "\n"
            "🎯 خيارات قابلة للضغط (مهم جداً لتسهيل التجربة):\n"
            "⚠️ قاعدة ذهبية: **اطرح سؤال واحد فقط في كل رسالة** ومعه خياراته. لا تطرح 5 أسئلة دفعة وحدة!\n"
            "لكل سؤال له إجابات محتملة، اكتب الخيارات بصيغة تاقات منفصلة:\n"
            "   <<OPT: نص الخيار الأول>>\n"
            "   <<OPT: نص الخيار الثاني>>\n"
            "   <<OPT: نص الخيار الثالث>>\n"
            "هذي راح تظهر للمستخدم كأزرار خضراء يضغط عليها بدل ما يكتب.\n"
            "أمثلة (سؤال واحد فقط لكل رسالة!):\n"
            "  • 'وش نوع الجمهور المستهدف؟ <<OPT: شباب>> <<OPT: عائلات>> <<OPT: محترفون>> <<OPT: غير ذلك (سيكتب)>>'\n"
            "  • 'إيش الإحساس اللي تبيه؟ <<OPT: فاخر وراقي>> <<OPT: عصري وحديث>> <<OPT: دافئ ومريح>> <<OPT: جريء ومثير>>'\n"
            "اكتب 3-5 خيارات لكل سؤال. اجعل آخر خيار غالباً 'غير ذلك' أو 'أبي أوضح بنفسي' عشان يقدر يكتب حر.\n"
            "بعد إجابة المستخدم، اشكره مختصراً ثم اطرح السؤال التالي. التدفق التدريجي يخلي التجربة سلسة.\n"
            "استخدم العربية في الخيارات.\n"
            "\n"
            "🎨 تنسيق النص (markdown):\n"
            "- استخدم **bold** للنقاط المهمة\n"
            "- استخدم ### للعناوين الفرعية فقط (لا تستخدم # كبير)\n"
            "- استخدم قوائم - أو 1. للنقاط\n"
            "- إيموجي بسيط ✨ 🎨 ✅ باعتدال\n"
            "- اجعل الرسائل قصيرة (3-6 أسطر) وحوارية\n"
        )

        # ── Adaptive task routing — pick the right model for this turn
        task_type, task_label = _classify_freebuild_task(
            user_msg=message or "",
            has_current_html=bool(proj.get("current_html")),
            current_html_len=len(proj.get("current_html") or ""),
        )
        logger.info(f"freebuild route: task={task_type} label={task_label}")

        try:
            from modules.zitex_ai import zitex_chat
            result = await zitex_chat(
                agent="freebuild",
                messages=msg_list,
                user_id=user["user_id"],
                extra_context=extra_ctx,
                requires_vision=bool(vision_images),
                task_type_override=task_type,
            )
            if not result.get("ok"):
                raise HTTPException(502, "خطأ في الذكاء الاصطناعي")
            ai_text = result["content"]
            model_used = result.get("model_used", "unknown")

            # Truthfulness gate — if AI lied about producing variants/updates, retry once
            error_msg = _validate_truthfulness(ai_text)
            if error_msg:
                logger.warning(f"freebuild AI lied: {error_msg[:80]}")
                retry_msgs = msg_list + [
                    {"role": "assistant", "content": ai_text},
                    {"role": "user", "content": f"⚠️ تنبيه نظام داخلي (لا تظهره للمستخدم): {error_msg}"},
                ]
                retry_result = await zitex_chat(
                    agent="freebuild",
                    messages=retry_msgs,
                    user_id=user["user_id"],
                    extra_context=extra_ctx,
                    requires_vision=bool(vision_images),
                    task_type_override=task_type,
                )
                if retry_result.get("ok"):
                    ai_text = retry_result["content"]
                    model_used = retry_result.get("model_used", model_used)

            # ── Self-correction loop — if generated HTML has broken anchors,
            # ask a stronger reasoning model to fix them. One pass only.
            quick_html = _extract_html(ai_text)
            if quick_html:
                broken = _verify_anchor_links(quick_html)
                if broken and len(broken) >= 2:
                    logger.warning(f"freebuild auto-fix: {len(broken)} broken anchors")
                    fix_msgs = msg_list + [
                        {"role": "assistant", "content": ai_text},
                        {"role": "user", "content": (
                            "⚠️ تنبيه نظام داخلي (لا تظهره للمستخدم): "
                            f"الكود فيه روابط معطوبة لأقسام غير موجودة: {', '.join('#'+a for a in broken[:5])}. "
                            "أعد إصدار نفس الكود مع إصلاح: إما أنشئ الـsections المفقودة، أو احذف الروابط الميتة من الـnav."
                        )},
                    ]
                    fix_result = await zitex_chat(
                        agent="freebuild",
                        messages=fix_msgs,
                        user_id=user["user_id"],
                        extra_context=extra_ctx,
                        requires_vision=False,
                        task_type_override="reasoning_hard",
                    )
                    if fix_result.get("ok") and _extract_html(fix_result["content"]):
                        ai_text = fix_result["content"]
                        model_used = f"{model_used} + {fix_result.get('model_used', 'fix')}"

            # Design-drift gate — smart guard that distinguishes:
            #   • Conversational (user asked "what can you do?")     → SKIP entirely
            #   • Additive edits (user asked to ADD a section)       → ALLOW
            #   • Explicit redesign (user said "غيّر كل شي")          → ALLOW
            #   • Destructive shrink (AI deleted header/footer)      → BLOCK
            #   • Catastrophic drift > 0.85                          → BLOCK
            if proj.get("current_html"):
                new_full = _extract_html(ai_text)
                user_intent = _detect_user_intent(message or "")
                # For conversational/meta turns, never overwrite the saved site
                # — even if the AI accidentally pasted demo HTML.
                if user_intent == "conversational":
                    logger.info("freebuild conversational turn: skipping HTML save")
                    # Force-strip the demo HTML so it doesn't enter current_html
                    new_full = None
                if new_full:
                    prev_sig = _design_signature(proj["current_html"])
                    new_sig = _design_signature(new_full)
                    drift = _structural_drift_ratio(prev_sig, new_sig)
                    is_additive = _is_additive_change(prev_sig, new_sig)
                    # AI is destructive if it shrank a major element it had before
                    is_destructive = (
                        (prev_sig.get("header") and not new_sig.get("header"))
                        or (prev_sig.get("footer") and not new_sig.get("footer"))
                        or (new_sig.get("sections", 0) < int(prev_sig.get("sections", 0) * 0.6))
                        or (new_sig.get("length", 0) < int(prev_sig.get("length", 1) * 0.55))
                    )
                    should_block = False
                    if user_intent == "redesign":
                        should_block = False  # user asked for redesign
                    elif user_intent == "additive" and is_additive:
                        should_block = False  # legit growth
                    elif is_destructive and user_intent != "redesign":
                        should_block = True   # AI silently deleted parts
                    elif drift > 0.85 and user_intent != "redesign":
                        should_block = True   # catastrophic non-additive change
                    if should_block:
                        logger.warning(
                            f"freebuild design drift blocked: drift={drift:.2f} "
                            f"intent={user_intent} additive={is_additive} destructive={is_destructive}"
                        )
                        ai_text = (
                            "⚠️ لاحظت إن التعديل سيغيّر تصميمك المعتمد بشكل كبير وقد يحذف أقسام مهمة.\n\n"
                            "لحماية شغلك، حفظت **التصميم الأصلي كما هو** ولم أطبّق التغيير.\n\n"
                            "هل تأكد إنك تبي تغيير جذري؟ اختر:\n"
                            "<<OPT: نعم — أبي تصميم جديد كلياً (ابدأ من الصفر)>>\n"
                            "<<OPT: لا — اكتفِ بتعديلات صغيرة على التصميم الحالي>>\n"
                            "<<OPT: أرني الفرق قبل التطبيق>>"
                        )
                    else:
                        logger.info(
                            f"freebuild drift OK: drift={drift:.2f} intent={user_intent} "
                            f"additive={is_additive}"
                        )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"freebuild_chat ai error: {e}")
            raise HTTPException(502, "خطأ في الذكاء")

        # Detect tags and queue asset generation (async)
        tags = TAG_RE.findall(ai_text)
        pending_assets = []
        for tag_type, tag_body in tags[:3]:  # max 3 per turn
            asset_id = str(uuid.uuid4())
            pending_assets.append({
                "id": asset_id,
                "type": tag_type.upper(),
                "prompt": tag_body.strip(),
                "status": "generating",
                "image_url": None,
                "approved": False,
                "created_at": _now(),
            })

        # Detect HTML for live preview (extracted BEFORE stripping)
        # Skip entirely on conversational turns (user asked a meta question).
        is_conversational = (
            proj.get("current_html")
            and _detect_user_intent(message or "") == "conversational"
        )
        all_variants = [] if is_conversational else _extract_all_html_variants(ai_text)
        # If AI produced 2+ HTML blocks → design variants (user picks one);
        # otherwise the single block becomes current_html immediately.
        new_html = None
        design_variants: List[Dict[str, str]] = []
        if len(all_variants) >= 2:
            for idx, html in enumerate(all_variants[:4]):  # cap at 4
                design_variants.append({
                    "id": str(uuid.uuid4()),
                    "label": f"تصميم #{idx + 1}",
                    "html": html,
                })
        elif len(all_variants) == 1:
            new_html = all_variants[0]

        # ── SECTION BUILDER: if AI used <<APPEND_SECTION>> / <<REPLACE_SECTION>>
        # directives instead of a full HTML block, splice them into existing
        # current_html. This is how the AI builds large multi-section sites
        # incrementally (one section per turn) without busting the response cap.
        section_dirs = _extract_section_directives(ai_text)
        sections_applied = 0
        if (section_dirs["appends"] or section_dirs["replaces"] or section_dirs["nav_items"]):
            base_html = new_html or proj.get("current_html")
            if base_html:
                merged = _merge_sections(
                    base_html,
                    section_dirs["appends"],
                    section_dirs["replaces"],
                    section_dirs["nav_items"],
                )
                if merged:
                    new_html = merged
                    sections_applied = (
                        len(section_dirs["appends"])
                        + len(section_dirs["replaces"])
                        + (1 if section_dirs["nav_items"] else 0)
                    )
                    logger.info(
                        f"freebuild sections merged: append={len(section_dirs['appends'])} "
                        f"replace={len(section_dirs['replaces'])} nav={bool(section_dirs['nav_items'])}"
                    )

        # ── Anchor sanity check: if nav has #X but no <section id="X">, log warning
        if new_html:
            broken = _verify_anchor_links(new_html)
            if broken:
                logger.warning(f"freebuild broken anchors: {broken[:5]}")

        # Strip code blocks from chat display — code is private/paid feature.
        # If we have design variants, replace all blocks with a single one-line notice;
        # otherwise replace each block with the "updated live preview" notice.
        if design_variants:
            chat_text = _CODE_BLOCK_RE.sub("", ai_text).strip()
            chat_text = re.sub(r"\n{3,}", "\n\n", chat_text)
            chat_text = (chat_text + "\n\n*🎨 شوف التصاميم تحت — اختر اللي يعجبك*").strip()
        else:
            chat_text = _strip_code_from_chat(ai_text)
        # Strip section directives from chat (internal-only)
        chat_text = _strip_section_directives(chat_text)
        if sections_applied > 0:
            chat_text = (chat_text + f"\n\n*✨ تم تحديث المعاينة الحية — {sections_applied} قسم/أقسام جديدة*").strip()
        clean_text = _strip_tags(chat_text)
        # First try OPT tags; if none, fall back to numbered/bulleted lists after a question.
        opt_tag_items = [m.group(1).strip() for m in OPT_RE.finditer(ai_text)]
        if opt_tag_items:
            options = opt_tag_items
        else:
            fb_items, fb_lines = _extract_options_fallback(ai_text)
            options = fb_items
            # Strip the consumed list lines from displayed text so we don't show twice.
            if fb_lines:
                kept = [ln for ln in clean_text.split("\n") if ln not in fb_lines]
                clean_text = re.sub(r"\n{3,}", "\n\n", "\n".join(kept)).strip()

        # Save chat message + pending assets
        update_set = {"updated_at": _now()}
        push_ops: Dict[str, Any] = {
            "messages": {
                "$each": [
                    {"role": "user", "content": message, "timestamp": _now(), "pending_assets": [], "attachments": attachment_meta, "reference": reference_meta, "answer_meta": parsed_answer_meta},
                    {"role": "assistant", "content": clean_text, "timestamp": _now(), "pending_assets": pending_assets, "had_html": bool(new_html), "options": options, "design_variants": design_variants},
                ]
            }
        }
        if new_html:
            # ── AUTO-SNAPSHOT — before overwriting current_html, archive the
            # previous version so the user can restore if AI makes a mistake.
            # Keep last 20 snapshots only.
            old_html = proj.get("current_html")
            if old_html and old_html != new_html:
                snapshot = {
                    "id": str(uuid.uuid4()),
                    "html": old_html,
                    "created_at": _now(),
                    "user_msg": (message or "")[:200],
                    "summary": _summarize_html(old_html),
                }
                push_ops["html_snapshots"] = {
                    "$each": [snapshot],
                    "$slice": -20,  # keep last 20
                }
            update_set["current_html"] = new_html
        await db.freebuild_projects.update_one(
            {"id": pid},
            {
                "$push": push_ops,
                "$set": update_set,
            },
        )

        # Kick off background asset generation (don't block chat response)
        if pending_assets:
            asyncio.create_task(_generate_assets_bg(db, pid, pending_assets))

        return {
            "response": clean_text,
            "pending_assets": pending_assets,
            "html_updated": bool(new_html),
            "task_label": task_label,
            "model_used": model_used,
        }

    # ===== Approve a design variant (when AI offered 2-3 designs) =====
    @router.post("/project/{pid}/approve-design")
    async def approve_design(
        pid: str,
        variant_id: str = Form(...),
        user=Depends(get_current_user),
    ):
        proj = await db.freebuild_projects.find_one(
            {"id": pid, "user_id": user["user_id"]}, {"_id": 0}
        )
        if not proj:
            raise HTTPException(404)
        variant_html: Optional[str] = None
        for m in proj.get("messages", []):
            for v in (m.get("design_variants") or []):
                if v.get("id") == variant_id:
                    variant_html = v.get("html")
                    break
            if variant_html:
                break
        if not variant_html:
            raise HTTPException(404, "التصميم غير موجود")
        # Snapshot the previous design before swapping (safety net)
        update_doc: Dict[str, Any] = {"$set": {
            "current_html": variant_html,
            "approved_design_id": variant_id,
            "approved_design_sig": _design_signature(variant_html),
            "updated_at": _now(),
        }}
        old_html = proj.get("current_html")
        if old_html and old_html != variant_html:
            update_doc["$push"] = {"html_snapshots": {
                "$each": [{
                    "id": str(uuid.uuid4()),
                    "html": old_html,
                    "created_at": _now(),
                    "user_msg": "[تصميم سابق قبل اعتماد variant جديد]",
                    "summary": _summarize_html(old_html),
                }],
                "$slice": -20,
            }}
        await db.freebuild_projects.update_one(
            {"id": pid},
            update_doc,
        )
        return {"ok": True, "html_length": len(variant_html)}

    # ===== Approve asset =====
    @router.post("/project/{pid}/asset/{aid}/approve")
    async def approve_asset(pid: str, aid: str, user=Depends(get_current_user)):
        proj = await db.freebuild_projects.find_one({"id": pid, "user_id": user["user_id"]})
        if not proj:
            raise HTTPException(404)
        # Find pending asset in messages
        target = None
        for m in proj.get("messages", []):
            for a in (m.get("pending_assets") or []):
                if a["id"] == aid:
                    target = a
                    break
            if target:
                break
        if not target:
            raise HTTPException(404, "الأصل غير موجود")
        target["approved"] = True
        await db.freebuild_projects.update_one(
            {"id": pid},
            {"$push": {"approved_assets": target}, "$set": {"updated_at": _now()}},
        )
        return {"ok": True}

    # ===== Compile final HTML with approved asset URLs =====
    @router.post("/project/{pid}/compile")
    async def compile_html(pid: str, user=Depends(get_current_user)):
        proj = await db.freebuild_projects.find_one({"id": pid, "user_id": user["user_id"]}, {"_id": 0})
        if not proj:
            raise HTTPException(404)
        html = proj.get("current_html") or ""
        if not html:
            raise HTTPException(400, "لا يوجد HTML للتجميع. اطلب من الذكاء توليد الصفحة أولاً.")
        # Inject approved asset URLs by type — replace placeholder src markers
        for a in proj.get("approved_assets", []):
            url = a.get("image_url")
            if not url:
                continue
            atype = a.get("type", "").upper()
            # replace any data-tag="HERO" src or placeholder
            html = html.replace(f"{{{{ASSET:{atype}}}}}", url)
            html = html.replace(f"PLACEHOLDER_{atype}", url)
        await db.freebuild_projects.update_one(
            {"id": pid},
            {"$set": {"compiled_html": html, "updated_at": _now()}},
        )
        return {"ok": True, "html_length": len(html)}

    # ===== Delete project =====
    @router.delete("/project/{pid}")
    async def delete_project(pid: str, user=Depends(get_current_user)):
        r = await db.freebuild_projects.update_one(
            {"id": pid, "user_id": user["user_id"]},
            {"$set": {"status": "deleted", "updated_at": _now()}},
        )
        if r.matched_count == 0:
            raise HTTPException(404)
        return {"ok": True}

    # ===== Finalization options (when user wants to publish/take ownership) =====
    @router.get("/project/{pid}/finalize-options")
    async def finalize_options(pid: str, user=Depends(get_current_user)):
        proj = await db.freebuild_projects.find_one(
            {"id": pid, "user_id": user["user_id"]}, {"_id": 0, "id": 1, "name": 1, "current_html": 1}
        )
        if not proj:
            raise HTTPException(404)
        if not proj.get("current_html"):
            raise HTTPException(400, "أكمل الموقع أولاً — لا يوجد محتوى نهائي بعد")
        return {
            "ready": True,
            "paths": [
                {
                    "id": "host_with_us",
                    "title": "🏠 استضف معنا على Zitex",
                    "price_usd": 0,
                    "subtitle": "مجاني تماماً — موقعك على دومين Zitex، نتولى الاستضافة والصيانة",
                    "features": [
                        "نشر فوري على نطاق zitex.com",
                        "SSL مجاني وأداء عالي",
                        "تعديل لاحق عبر نفس الشات",
                        "لا تحتاج خبرة تقنية",
                    ],
                    "cta": "انشر موقعي الآن",
                },
                {
                    "id": "take_code_self",
                    "title": "💻 استلم الكود (مبرمج)",
                    "price_usd": 49,
                    "subtitle": "بتنشره بنفسك على GitHub/Vercel/Cloudflare — أنت محترف وعندك خبرة",
                    "features": [
                        "كل ملفات HTML/CSS/JS",
                        "صور بحجم Production",
                        "ملف README فيه طريقة النشر",
                        "بدون أي إرشاد إضافي",
                    ],
                    "cta": "اشترِ الكود بـ $49",
                },
                {
                    "id": "take_code_guided",
                    "title": "🎓 الكود + إرشاد كامل",
                    "price_usd": 99,
                    "subtitle": "الذكاء يمشي معك خطوة بخطوة — يربط GitHub repo، يدفع لـVercel، يضبط الدومين",
                    "features": [
                        "كل اللي في الباقة السابقة",
                        "الذكاء يتصل بمستودعاتك",
                        "يضبط CI/CD ودومين مخصص",
                        "دعم 30 يوم على المشاكل التقنية",
                    ],
                    "cta": "اشترِ الإرشاد الكامل بـ $99",
                },
            ],
        }

    # ===== Convert this website project to an App project (placeholder for apps module) =====
    @router.post("/project/{pid}/convert-to-app")
    async def convert_to_app(pid: str, user=Depends(get_current_user)):
        proj = await db.freebuild_projects.find_one(
            {"id": pid, "user_id": user["user_id"]}, {"_id": 0}
        )
        if not proj:
            raise HTTPException(404)
        if not proj.get("current_html"):
            raise HTTPException(400, "أكمل الموقع قبل التحويل لتطبيق")
        app_id = str(uuid.uuid4())
        await db.app_conversion_projects.insert_one({
            "id": app_id,
            "source_kind": "freebuild",
            "source_id": pid,
            "user_id": user["user_id"],
            "name": f"{proj['name']} (تطبيق)",
            "description": proj.get("description", ""),
            "current_html": proj.get("current_html"),
            "approved_assets": proj.get("approved_assets", []),
            "messages": [],
            "status": "discovery",
            "created_at": _now(),
            "updated_at": _now(),
        })
        await db.freebuild_projects.update_one(
            {"id": pid},
            {"$set": {"converted_to_app_id": app_id, "updated_at": _now()}},
        )
        return {"ok": True, "app_id": app_id}

    # ===== INDEPENDENCE TOOLKIT =====
    # Unlock the code/independence tier (mocked payment — wire Lemon Squeezy later)
    @router.post("/project/{pid}/unlock")
    async def unlock_independence(
        pid: str,
        tier: str = Form(...),  # "code_only" ($49) | "guided" ($99)
        user=Depends(get_current_user),
    ):
        if tier not in ("code_only", "guided"):
            raise HTTPException(400, "tier غير صالح")
        r = await db.freebuild_projects.update_one(
            {"id": pid, "user_id": user["user_id"]},
            {"$set": {
                "code_unlocked": True,
                "tier": tier,
                "unlocked_at": _now(),
                "updated_at": _now(),
            }},
        )
        if r.matched_count == 0:
            raise HTTPException(404)
        return {"ok": True, "tier": tier}

    # Save a deployment provider token (encrypted at rest)
    @router.post("/project/{pid}/connections/{provider}")
    async def save_connection(
        pid: str,
        provider: str,
        token: str = Form(...),
        extra: str = Form(default=""),
        user=Depends(get_current_user),
    ):
        if provider not in ("github", "vercel", "cloudflare", "domain"):
            raise HTTPException(400, "provider غير مدعوم")
        proj = await db.freebuild_projects.find_one({"id": pid, "user_id": user["user_id"]}, {"_id": 0, "id": 1})
        if not proj:
            raise HTTPException(404)
        await db.freebuild_connections.update_one(
            {"project_id": pid, "user_id": user["user_id"], "provider": provider},
            {"$set": {
                "project_id": pid,
                "user_id": user["user_id"],
                "provider": provider,
                "token_enc": _enc(token.strip()),
                "extra": extra,
                "mask": _mask(token.strip()),
                "updated_at": _now(),
            }, "$setOnInsert": {"created_at": _now()}},
            upsert=True,
        )
        return {"ok": True, "mask": _mask(token.strip())}

    @router.get("/project/{pid}/connections")
    async def list_connections(pid: str, user=Depends(get_current_user)):
        cursor = db.freebuild_connections.find(
            {"project_id": pid, "user_id": user["user_id"]},
            {"_id": 0, "provider": 1, "mask": 1, "extra": 1, "created_at": 1, "updated_at": 1},
        )
        items = await cursor.to_list(length=20)
        return {"connections": items}

    @router.delete("/project/{pid}/connections/{provider}")
    async def delete_connection(pid: str, provider: str, user=Depends(get_current_user)):
        await db.freebuild_connections.delete_one(
            {"project_id": pid, "user_id": user["user_id"], "provider": provider},
        )
        return {"ok": True}

    # Push current HTML to a GitHub repo (creates if not exists, pushes index.html)
    @router.post("/project/{pid}/push-to-github")
    async def push_to_github(
        pid: str,
        repo_name: str = Form(...),
        private: bool = Form(default=False),
        user=Depends(get_current_user),
    ):
        proj = await db.freebuild_projects.find_one(
            {"id": pid, "user_id": user["user_id"]}, {"_id": 0}
        )
        if not proj:
            raise HTTPException(404)
        if not proj.get("current_html"):
            raise HTTPException(400, "لا يوجد HTML للنشر")
        conn = await db.freebuild_connections.find_one(
            {"project_id": pid, "user_id": user["user_id"], "provider": "github"},
            {"_id": 0, "token_enc": 1},
        )
        if not conn:
            raise HTTPException(400, "ربط GitHub أولاً من إعدادات الاتصالات")
        token = _dec(conn["token_enc"]) if conn.get("token_enc") else None
        if not token:
            raise HTTPException(400, "GitHub token غير صالح — أعد ربطه")

        import httpx
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        async with httpx.AsyncClient(timeout=30) as cli:
            # 1) Get authenticated user
            u_r = await cli.get("https://api.github.com/user", headers=headers)
            if u_r.status_code != 200:
                raise HTTPException(400, f"فشل التحقق من GitHub: {u_r.status_code}")
            owner = u_r.json().get("login")
            # 2) Create repo (or ignore if exists)
            cr_r = await cli.post(
                "https://api.github.com/user/repos",
                headers=headers,
                json={"name": repo_name, "private": private, "auto_init": True, "description": f"Built with Zitex — {proj.get('name','')}"},
            )
            if cr_r.status_code not in (201, 422):  # 422 = already exists
                raise HTTPException(400, f"فشل إنشاء المستودع: {cr_r.status_code} — {cr_r.text[:120]}")
            # 3) Get current SHA of index.html (if exists)
            sha = None
            get_f = await cli.get(
                f"https://api.github.com/repos/{owner}/{repo_name}/contents/index.html",
                headers=headers,
            )
            if get_f.status_code == 200:
                sha = get_f.json().get("sha")
            # 4) PUT index.html
            content_b64 = base64.b64encode(proj["current_html"].encode()).decode()
            payload = {
                "message": f"Update from Zitex — {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')}",
                "content": content_b64,
            }
            if sha:
                payload["sha"] = sha
            put_r = await cli.put(
                f"https://api.github.com/repos/{owner}/{repo_name}/contents/index.html",
                headers=headers,
                json=payload,
            )
            if put_r.status_code not in (200, 201):
                raise HTTPException(400, f"فشل رفع الملف: {put_r.status_code} — {put_r.text[:120]}")

        repo_url = f"https://github.com/{owner}/{repo_name}"
        pages_url = f"https://{owner}.github.io/{repo_name}/"
        await db.freebuild_projects.update_one(
            {"id": pid},
            {"$set": {"github_repo_url": repo_url, "updated_at": _now()}},
        )
        return {"ok": True, "repo_url": repo_url, "pages_url_hint": pages_url}

    # ═══════════════════════════════════════════════════════════════
    # APP CONVERSION ENDPOINTS — convert a finished FreeBuild website
    # into a downloadable PWA / Capacitor (Android+iOS) / Expo bundle.
    # ═══════════════════════════════════════════════════════════════
    @router.get("/app-conversion/{aid}")
    async def get_app_conversion(aid: str, user=Depends(get_current_user)):
        doc = await db.app_conversion_projects.find_one(
            {"id": aid, "user_id": user["user_id"]}, {"_id": 0}
        )
        if not doc:
            raise HTTPException(404, "تحويل غير موجود")
        return doc

    @router.patch("/app-conversion/{aid}")
    async def update_app_conversion(
        aid: str,
        name: Optional[str] = Form(None),
        package_id: Optional[str] = Form(None),
        primary_color: Optional[str] = Form(None),
        app_type: Optional[str] = Form(None),  # pwa | hybrid
        user=Depends(get_current_user),
    ):
        update: Dict[str, Any] = {"updated_at": _now()}
        if name is not None:
            update["name"] = name.strip()[:80]
        if package_id is not None:
            # normalize: only lowercase + dots + dashes
            pkg = re.sub(r"[^a-z0-9.\-]", "", package_id.lower()) or "com.zitex.app"
            update["package_id"] = pkg[:80]
        if primary_color is not None and primary_color.startswith("#"):
            update["primary_color"] = primary_color[:7]
        if app_type in ("pwa", "hybrid"):
            update["app_type"] = app_type
        r = await db.app_conversion_projects.update_one(
            {"id": aid, "user_id": user["user_id"]},
            {"$set": update},
        )
        if r.matched_count == 0:
            raise HTTPException(404)
        return {"ok": True, **{k: v for k, v in update.items() if k != "updated_at"}}

    @router.post("/app-conversion/{aid}/build")
    async def build_app_conversion(aid: str, user=Depends(get_current_user)):
        doc = await db.app_conversion_projects.find_one(
            {"id": aid, "user_id": user["user_id"]}, {"_id": 0}
        )
        if not doc:
            raise HTTPException(404)
        if not doc.get("current_html"):
            raise HTTPException(400, "لا يوجد HTML للتحويل — أكمل الموقع أولاً")

        # adapt to the app_studio.builder.build_project signature
        try:
            from modules.app_studio.builder import build_project
        except Exception:
            logger.exception("app_studio.builder import failed")
            raise HTTPException(500, "محرّك البناء غير متاح")

        app_type = doc.get("app_type") or "pwa"
        if app_type not in ("pwa", "hybrid"):
            app_type = "pwa"

        pseudo_project = {
            "id": aid,
            "type": app_type,
            "title": doc.get("name", "تطبيق Zitex"),
            "description": doc.get("description", ""),
            "primary_color": doc.get("primary_color", "#10b981"),
            "package_id": doc.get("package_id", "com.zitex.app"),
            "imports": [{"kind": "freebuild_site", "html_snapshot": doc["current_html"]}],
        }
        try:
            result = build_project(pseudo_project, features=[])
        except Exception as e:
            logger.exception("build_project failed")
            raise HTTPException(500, f"فشل البناء: {str(e)[:120]}")

        await db.app_conversion_projects.update_one(
            {"id": aid},
            {"$set": {
                "status": "built",
                "last_build": result,
                "updated_at": _now(),
            }},
        )
        return result

    # ═══════════════════════════════════════════════════════════════
    # HTML SNAPSHOTS — every overwrite of current_html auto-archives the
    # previous version. User can list, preview, and restore.
    # ═══════════════════════════════════════════════════════════════
    @router.get("/project/{pid}/snapshots")
    async def list_snapshots(pid: str, user=Depends(get_current_user)):
        proj = await db.freebuild_projects.find_one(
            {"id": pid, "user_id": user["user_id"]},
            {"_id": 0, "html_snapshots": 1, "current_html": 1},
        )
        if not proj:
            raise HTTPException(404)
        snaps = proj.get("html_snapshots") or []
        # newest first, strip the full html from listing (only summaries)
        items = []
        for s in reversed(snaps):
            items.append({
                "id": s.get("id"),
                "created_at": s.get("created_at"),
                "user_msg": s.get("user_msg", "")[:200],
                "summary": s.get("summary") or _summarize_html(s.get("html", "")),
                "size": len(s.get("html") or ""),
            })
        current_summary = _summarize_html(proj.get("current_html") or "")
        return {
            "ok": True,
            "snapshots": items,
            "current_summary": current_summary,
            "count": len(items),
        }

    @router.get("/project/{pid}/snapshots/{sid}/preview")
    async def preview_snapshot(pid: str, sid: str, user=Depends(get_current_user)):
        proj = await db.freebuild_projects.find_one(
            {"id": pid, "user_id": user["user_id"]},
            {"_id": 0, "html_snapshots": 1},
        )
        if not proj:
            raise HTTPException(404)
        for s in (proj.get("html_snapshots") or []):
            if s.get("id") == sid:
                return {"ok": True, "html": s.get("html", ""), "created_at": s.get("created_at")}
        raise HTTPException(404, "نسخة غير موجودة")

    @router.post("/project/{pid}/snapshots/{sid}/restore")
    async def restore_snapshot(pid: str, sid: str, user=Depends(get_current_user)):
        proj = await db.freebuild_projects.find_one(
            {"id": pid, "user_id": user["user_id"]}, {"_id": 0}
        )
        if not proj:
            raise HTTPException(404)
        target = None
        for s in (proj.get("html_snapshots") or []):
            if s.get("id") == sid:
                target = s
                break
        if not target:
            raise HTTPException(404, "نسخة غير موجودة")
        # Push current_html as a NEW snapshot (so restore is reversible)
        push_doc: Dict[str, Any] = {}
        if proj.get("current_html"):
            push_doc["html_snapshots"] = {
                "$each": [{
                    "id": str(uuid.uuid4()),
                    "html": proj["current_html"],
                    "created_at": _now(),
                    "user_msg": f"[نسخة محفوظة تلقائياً قبل استرجاع {sid[:8]}]",
                    "summary": _summarize_html(proj["current_html"]),
                }],
                "$slice": -20,
            }
        update_doc: Dict[str, Any] = {
            "$set": {"current_html": target["html"], "updated_at": _now()},
        }
        if push_doc:
            update_doc["$push"] = push_doc
        await db.freebuild_projects.update_one({"id": pid}, update_doc)
        return {
            "ok": True,
            "restored_summary": target.get("summary") or _summarize_html(target.get("html", "")),
            "html_length": len(target.get("html", "")),
        }

    return router


async def _generate_assets_bg(db, pid: str, assets: List[Dict[str, Any]]):
    """Generate images for tagged assets via Fal.ai in background."""
    try:
        from modules.games.fal_tools import generate_flux_pro
    except Exception:
        logger.warning("fal_tools not available")
        return
    for a in assets:
        try:
            ar = "16:9" if a["type"] in ("HERO", "SECTION_BG", "GALLERY") else "1:1"
            r = await generate_flux_pro(prompt=a["prompt"], project_id=pid, aspect_ratio=ar, style_profile="cinematic")
            url = r.get("image_url") or r.get("url")
            await db.freebuild_projects.update_one(
                {"id": pid},
                {"$set": {
                    "messages.$[msg].pending_assets.$[asset].image_url": url,
                    "messages.$[msg].pending_assets.$[asset].status": "ready",
                }},
                array_filters=[
                    {"msg.pending_assets.id": a["id"]},
                    {"asset.id": a["id"]},
                ],
            )
        except Exception as e:
            logger.warning(f"asset gen failed for {a['id']}: {e}")
            await db.freebuild_projects.update_one(
                {"id": pid},
                {"$set": {"messages.$[msg].pending_assets.$[asset].status": "failed"}},
                array_filters=[
                    {"msg.pending_assets.id": a["id"]},
                    {"asset.id": a["id"]},
                ],
            )
