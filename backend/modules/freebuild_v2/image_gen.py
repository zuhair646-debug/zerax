"""
AI-powered image generator for FreeBuild v2.

Replaces the old Unsplash-library approach. Now every image in a generated
website is REAL AI-created via Gemini Nano Banana (gemini-3.1-flash-image-preview).

Flow:
    1. HTML post-processor extracts unique image descriptions from <img alt="..."
       and surrounding <h1/h2/h3> headings + class hints.
    2. For each unique description, calls Nano Banana in parallel.
    3. Saves PNG to /app/backend/static/fb2_images/{md5}.png
    4. Returns relative URL /api/freebuild/v2/img/{md5}.png

Cache:
    Same description → same hash → reused image (no re-generation cost).

Style brief:
    Each prompt is wrapped with a high-quality cinematic Arabic-context style
    so all images feel cohesive across the site (lighting, depth, modern look).
"""
from __future__ import annotations
import os
import re
import hashlib
import base64
import asyncio
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Where generated PNGs land (served by FastAPI endpoint /api/freebuild/v2/img/{hash})
IMAGES_DIR = Path("/app/backend/static/fb2_images")
IMAGES_DIR.mkdir(parents=True, exist_ok=True)

# Public URL prefix (must match the route registered in __init__.py)
PUBLIC_PREFIX = "/api/freebuild/v2/img"

# Style suffix appended to every prompt for cohesive look across the whole site
GLOBAL_STYLE = (
    "professional commercial photography, dramatic cinematic lighting, "
    "shallow depth of field, ultra-sharp details, modern editorial composition, "
    "rich color grading, photorealistic, 8K, magazine-quality, no text overlays, "
    "no watermarks, no logos"
)

# Concurrency cap so we don't hammer the API during a single page generation
_SEMAPHORE = asyncio.Semaphore(4)


def _hash_for(description: str, style_seed: str = "") -> str:
    norm = (description.strip().lower() + "::" + style_seed.strip().lower()).encode("utf-8")
    return hashlib.md5(norm).hexdigest()[:16]


def _file_for(h: str) -> Path:
    return IMAGES_DIR / f"{h}.png"


def _public_url(h: str) -> str:
    return f"{PUBLIC_PREFIX}/{h}.png"


# ─────────────────────────────────────────────────────────────────────────
#  Description → cinematic English prompt translator
# ─────────────────────────────────────────────────────────────────────────
# Maps common Arabic / English keywords to richer scene descriptions.
# The AI image model works best with vivid English; we still respect
# whatever raw text the architect AI passed (it gets joined in the prompt).
_PROMPT_HINTS: List[Tuple[Tuple[str, ...], str]] = [
    # ── Islamic / Quran ─────────────────────────────────────────────────
    (("quran", "qur'an", "mushaf", "tilawah", "tilawat", "ayah", "verse",
      "surah", "tajweed", "قرآن", "قران", "كريم", "مصحف", "تلاوة", "آية",
      "سورة", "تجويد", "تحفيظ", "حفظ"),
     "an open ornate Quran (Mushaf) with golden Arabic calligraphy, "
     "warm amber light beam from above, floating dust particles, "
     "deep navy background with subtle Islamic geometric pattern, "
     "spiritual reverent atmosphere"),
    (("madinah", "medina", "prophet-mosque", "المدينة", "مدينة"),
     "the Prophet's Mosque in Madinah at golden sunset, green dome glowing, "
     "minarets silhouetted against amber sky, reverent atmosphere"),
    (("mecca", "kaaba", "haram", "مكة", "كعبة"),
     "aerial view of the Kaaba in Mecca surrounded by thousands of pilgrims "
     "in white ihram, golden hour lighting, deeply spiritual"),
    (("mosque", "masjid", "minaret", "صلاة", "مسجد", "مساجد"),
     "elegant Saudi mosque interior with intricate geometric patterns, "
     "warm chandelier light, polished marble floor, calm atmosphere"),
    # ── Children / kids / rewards ───────────────────────────────────────
    (("rewards", "reward", "gift", "gifts", "prize", "prizes", "trophy",
      "achievement", "badge", "stars", "مكافآت", "مكافأة", "هدايا",
      "هدية", "جوائز", "جائزة", "نجوم", "إنجاز", "تكريم"),
     "shiny golden trophy and colorful gift boxes wrapped with ribbons, "
     "floating golden stars and confetti, soft pastel background, "
     "joyful celebratory atmosphere, family-friendly"),
    (("kids", "child", "children", "boy", "girl", "young",
      "أطفال", "طفل", "صغار"),
     "happy diverse children smiling and learning together, warm natural "
     "light through a window, colorful classroom in background, "
     "soft bokeh, candid moment"),
    # ── Education / Memorization ────────────────────────────────────────
    (("memorization", "memorize", "study", "learning"),
     "young student concentrating while reading an illuminated book, "
     "warm desk lamp light, peaceful focused atmosphere, books in background"),
    (("teacher", "tutor", "lesson", "instructor", "درس", "معلم",
      "طالب", "تعليم", "مدرس", "تعليمي"),
     "a warm Arab teacher guiding a focused student in a modern classroom, "
     "books and tablets visible, natural soft window light"),
    (("classroom", "school", "academy", "صف", "مدرسة", "أكاديمية"),
     "modern bright classroom with arabic decoration on walls, "
     "wooden desks with notebooks, sunlight streaming through tall windows"),
    (("books", "library", "reading", "كتب", "مكتبة", "قراءة"),
     "rows of antique leather-bound books in a warm wood library, "
     "amber reading lamp glow, cozy intellectual atmosphere"),
    (("graduation", "graduate", "diploma", "تخرج", "شهادة"),
     "graduation cap and diploma with golden tassels, soft confetti falling, "
     "celebratory warm lighting"),
    # ── Smart tech / AI / interaction / tracking ────────────────────────
    (("smart-tech", "smart-technology", "ai", "artificial-intelligence",
      "machine-learning", "neural", "ذكاء-اصطناعي", "ذكاء", "ذكي",
      "تقنية", "تكنولوجيا"),
     "futuristic holographic interface floating above a modern desk, "
     "blue and amber glowing data streams, sleek minimal aesthetic, dark background"),
    (("interaction", "interactive", "engagement", "تفاعل"),
     "modern hands using touchscreen tablet with glowing colorful UI, "
     "abstract data visualization floating above, dark editorial background"),
    (("tracking", "monitoring", "analytics", "metrics", "stats", "dashboard",
      "متابعة", "تتبع", "إحصاء", "تحليل", "لوحة-تحكم"),
     "elegant analytics dashboard on dark glass with neon-amber graphs and KPIs, "
     "shallow depth of field, modern cinematic look"),
    (("mobile-app", "smartphone", "app", "application", "تطبيق", "جوال"),
     "modern smartphone with vivid Arabic UI floating above a dark glass surface, "
     "soft glow around device, high-end product photography"),
    # ── Food / Restaurants ──────────────────────────────────────────────
    (("saudi-food", "kabsa", "arab-food", "kabseh", "mandi",
      "كبسة", "مندي", "أكل-سعودي", "أكل-عربي"),
     "traditional Saudi kabsa rice with lamb on copper plate, garnished "
     "with pine nuts and raisins, dramatic overhead lighting, dark wood table"),
    (("food", "meal", "dish", "cuisine", "طعام", "أكل", "وجبة", "طبق"),
     "gourmet plated dish with vibrant fresh ingredients, dramatic side lighting, "
     "rustic dark wood table, professional food photography"),
    (("restaurant", "dining", "مطعم"),
     "cozy upscale restaurant interior at dusk, warm pendant lights over "
     "set tables, blurred patrons in background, atmospheric"),
    (("cafe", "coffee", "latte", "espresso", "قهوة", "كافيه", "مقهى"),
     "artisan latte with intricate foam art on a saucer, warm wooden cafe "
     "interior bokeh in background, soft window light"),
    (("dessert", "sweets", "cake", "حلويات", "حلى"),
     "decadent layered dessert with golden honey drizzle and pistachio crumbs, "
     "macro shot, soft warm lighting"),
    # ── Healthcare ──────────────────────────────────────────────────────
    (("dentist", "dental", "أسنان"),
     "modern bright dental clinic with sleek equipment, professional and "
     "trustworthy atmosphere, soft cool lighting"),
    (("clinic", "hospital", "medical-center", "عيادة", "مستشفى", "مركز-طبي"),
     "modern Arabic medical clinic reception with soft healing colors, "
     "professional calm atmosphere, contemporary minimalist design"),
    (("doctor", "physician", "nurse", "specialist",
      "طبيب", "ممرض", "أخصائي"),
     "kind professional Arab doctor in white coat with stethoscope, "
     "warm reassuring expression, blurred bright clinic background"),
    # ── E-commerce / Retail ─────────────────────────────────────────────
    (("perfume", "fragrance", "cologne", "عطر", "عطور"),
     "elegant glass perfume bottle on glossy black surface, golden liquid, "
     "floral elements floating around, luxury product photography"),
    (("jewelry", "ring", "necklace", "diamond", "مجوهرات", "ذهب", "ألماس"),
     "glittering golden necklace and diamond ring on black velvet, "
     "dramatic spot lighting catches every facet, ultra-luxury"),
    (("watch", "ساعة", "ساعات"),
     "luxury Swiss-style watch with gold case and leather strap, "
     "macro detail shot, dramatic side lighting, blurred dark background"),
    (("fashion", "clothing", "apparel", "boutique",
      "أزياء", "ملابس", "بوتيك"),
     "elegant modest fashion editorial — flowing fabric, soft natural light, "
     "minimal upscale boutique background"),
    # ── Real Estate ─────────────────────────────────────────────────────
    (("villa", "house", "home", "real-estate", "property",
      "فيلا", "بيت", "منزل", "عقار"),
     "modern luxury villa exterior at twilight, warm interior lights glowing, "
     "infinity pool reflecting deep blue sky, palm trees"),
    (("interior", "living-room", "bedroom", "ديكور", "صالة"),
     "ultra-modern Arab living room with neutral palette, designer furniture, "
     "warm pendant lights, soft natural daylight"),
    # ── Sports / Fitness ────────────────────────────────────────────────
    (("gym", "fitness", "workout", "exercise", "نادي", "رياضة"),
     "modern dark gym with neon accent lighting, high-end equipment, "
     "athletic figure mid-action with motion blur"),
    (("yoga", "meditation", "wellness", "يوغا", "تأمل"),
     "serene yoga pose silhouetted against sunrise window, soft golden light, "
     "peaceful zen atmosphere"),
    # ── Sports / Players ─────────────────────────────────────────────────
    (("football", "soccer", "player", "stadium", "match",
      "كرة", "لاعب", "ملعب", "مباراة"),
     "dynamic football player mid-action kicking ball under stadium spotlights, "
     "motion blur, dramatic atmosphere, vibrant green pitch"),
    # ── Hero / Backgrounds ──────────────────────────────────────────────
    (("nature", "mountain", "landscape", "forest", "طبيعة", "جبال", "غابة"),
     "majestic mountain landscape at golden hour, layered peaks fading "
     "into mist, cinematic wide composition"),
    (("city-night", "urban", "skyline", "مدينة", "ليل"),
     "Riyadh skyline at night with Kingdom Tower glowing, city lights "
     "reflecting on glass, deep blue twilight"),
    (("luxury", "gold", "premium", "elegant",
      "فخامة", "ذهبي", "فاخر"),
     "luxury black-and-gold abstract composition, silk fabric flowing, "
     "premium editorial atmosphere"),
    (("office", "workspace", "desk", "مكتب"),
     "stylish modern Arabic office workspace, warm wood desk with laptop "
     "and notepad, soft window light, plants in background"),
]

# Generic fallback when nothing matches
_FALLBACK_PROMPT = (
    "abstract elegant editorial composition with warm amber light gradients, "
    "soft floating geometric shapes, modern minimalist aesthetic, "
    "premium brand visual"
)


def _build_prompt(raw_context: str) -> str:
    """Turn a free-form context string (alt + heading + classes) into a vivid
    English prompt for Nano Banana."""
    if not raw_context:
        raw_context = "abstract"
    text = raw_context.strip().lower()
    matched: List[str] = []
    for terms, scene in _PROMPT_HINTS:
        for t in terms:
            if t in text:
                matched.append(scene)
                break
        if len(matched) >= 2:  # cap
            break

    if matched:
        scene = ". ".join(matched)
    else:
        scene = _FALLBACK_PROMPT

    # Always honor the raw architect-supplied caption (often Arabic) — let
    # the model see it too so it can pick up details we didn't pre-mapped.
    return (
        f"{scene}. Original caption: {raw_context.strip()}. "
        f"{GLOBAL_STYLE}."
    )


# ─────────────────────────────────────────────────────────────────────────
#  Nano Banana call
# ─────────────────────────────────────────────────────────────────────────
async def _call_nano_banana(prompt: str) -> Optional[bytes]:
    """Generate one image. Returns PNG bytes or None on failure."""
    api_key = os.environ.get("EMERGENT_LLM_KEY")
    if not api_key:
        logger.warning("[FB2-IMG] EMERGENT_LLM_KEY missing — cannot generate")
        return None
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage
    except Exception as e:
        logger.error(f"[FB2-IMG] emergentintegrations import failed: {e}")
        return None

    try:
        chat = LlmChat(
            api_key=api_key,
            session_id=f"fb2-img-{hashlib.md5(prompt.encode()).hexdigest()[:8]}",
            system_message="You are a professional commercial photographer and visual artist."
        )
        chat.with_model("gemini", "gemini-3.1-flash-image-preview").with_params(
            modalities=["image", "text"]
        )
        msg = UserMessage(text=prompt)
        async with _SEMAPHORE:
            _txt, images = await chat.send_message_multimodal_response(msg)
        if not images:
            logger.warning(f"[FB2-IMG] Nano Banana returned no images for prompt: {prompt[:60]}")
            return None
        first = images[0]
        data = first.get("data") or ""
        if not data:
            return None
        return base64.b64decode(data)
    except Exception as e:
        logger.warning(f"[FB2-IMG] generation failed: {str(e)[:200]}")
        return None


async def generate_image(
    description: str,
    style_seed: str = "",
    force_regenerate: bool = False,
) -> Optional[str]:
    """Public entry. Returns a relative URL like /api/freebuild/v2/img/abc123.png
    or None if generation failed (caller should fall back).

    Caches by md5(description::style_seed). Same input → same file → no cost.
    """
    if not description or not description.strip():
        description = "elegant abstract composition"
    h = _hash_for(description, style_seed)
    fp = _file_for(h)
    if fp.exists() and not force_regenerate:
        return _public_url(h)

    prompt = _build_prompt(description)
    if style_seed:
        prompt = f"{prompt} Style direction: {style_seed}."
    png = await _call_nano_banana(prompt)
    if not png:
        return None
    try:
        fp.write_bytes(png)
        logger.info(f"[FB2-IMG] saved {h}.png ({len(png)} bytes) for: {description[:50]}")
        return _public_url(h)
    except Exception as e:
        logger.error(f"[FB2-IMG] failed to save {fp}: {e}")
        return None


# ─────────────────────────────────────────────────────────────────────────
#  HTML post-processor — replaces all <img> srcs with AI-generated URLs
# ─────────────────────────────────────────────────────────────────────────
async def post_process_html_with_ai_images(
    html: str,
    style_seed: str = "",
    fallback_resolver=None,
) -> str:
    """Scan the HTML, find every <img> tag and every background-image:url(),
    derive a description from alt+heading+class, generate AI images in
    parallel, and rewrite the URLs.

    `fallback_resolver(context: str) -> str` is called if AI generation
    fails for that specific image, so the page never has broken images.
    """
    if not html:
        return html

    # ── Step A: explicit @@IMG/<keyword>@@ placeholders ─────────────────
    placeholder_re = re.compile(r"@@IMG/([^@]+)@@")
    img_re = re.compile(r'<img\s+([^>]*?)\bsrc="([^"]*)"([^>]*)>', re.IGNORECASE)
    bg_re = re.compile(
        r"background-image\s*:\s*url\(\s*['\"]?([^'\")]+)['\"]?\s*\)",
        re.IGNORECASE,
    )

    # Collect all the (context, old_match_token) pairs we need to resolve.
    # We replace by RE-running the regexes after generation; since we use
    # the generated URL as a value, we don't need to track positions.

    # 1) gather contexts from explicit placeholders
    placeholder_contexts: List[str] = list({m.group(1).strip() for m in placeholder_re.finditer(html)})

    # 2) gather contexts from <img> tags (alt + nearest heading + class hint)
    def _find_nearest_heading_before(pos: int) -> str:
        before = html[max(0, pos - 1500):pos]
        m = re.findall(r"<h[1-4][^>]*>([^<]+)</h[1-4]>", before)
        return m[-1].strip() if m else ""

    def _find_class_hint_before(pos: int) -> str:
        before = html[max(0, pos - 500):pos]
        m = re.findall(r'class="([^"]+)"', before)
        return " ".join(m[-2:]) if m else ""

    img_contexts: List[str] = []
    img_jobs: List[Tuple[int, int, str]] = []  # (start, end, context)
    SKIP_IMG_CONTEXTS = ("reciter-card", "reciter-avatar", "reciter-name", "reciter-meta")
    for m in img_re.finditer(html):
        attrs_full = (m.group(1) or "") + " " + (m.group(3) or "")
        alt_m = re.search(r'\balt="([^"]*)"', attrs_full)
        alt = alt_m.group(1) if alt_m else ""
        heading = _find_nearest_heading_before(m.start())
        cls = _find_class_hint_before(m.start())
        ctx = " ".join(filter(None, [alt, heading, cls])).strip() or "abstract"
        # Skip generating heavy AI images for reciter cards (we use letter avatars)
        if any(skip in cls for skip in SKIP_IMG_CONTEXTS):
            continue
        img_jobs.append((m.start(), m.end(), ctx))
        img_contexts.append(ctx)

    bg_jobs: List[Tuple[int, int, str]] = []
    for m in bg_re.finditer(html):
        url_in = m.group(1)
        if url_in.startswith("data:") or url_in.startswith("/api/freebuild/v2/img/"):
            continue
        if "@@IMG" in url_in:
            continue
        pos = m.start()
        before = html[max(0, pos - 800):pos]
        cls = re.findall(r'class="([^"]+)"', before)
        h_m = re.findall(r"<h[1-4][^>]*>([^<]+)</h[1-4]>", before)
        ctx = " ".join(filter(None, [(cls[-1] if cls else ""), (h_m[-1] if h_m else "")])).strip() or "abstract"
        bg_jobs.append((m.start(), m.end(), ctx))

    # Unique contexts to generate
    all_contexts = list({*placeholder_contexts, *img_contexts, *(c for _, _, c in bg_jobs)})

    # Generate in parallel
    if all_contexts:
        results = await asyncio.gather(
            *[generate_image(c, style_seed) for c in all_contexts],
            return_exceptions=True
        )
        ctx_to_url: Dict[str, Optional[str]] = {}
        for ctx, res in zip(all_contexts, results):
            if isinstance(res, Exception):
                ctx_to_url[ctx] = None
            else:
                ctx_to_url[ctx] = res
    else:
        ctx_to_url = {}

    def _resolve(ctx: str) -> str:
        url = ctx_to_url.get(ctx)
        if url:
            return url
        # AI failed → fallback to old Unsplash resolver if provided
        if fallback_resolver:
            try:
                return fallback_resolver(ctx)
            except Exception:
                pass
        # last-resort: a transparent gradient SVG inline as data URI
        return (
            "data:image/svg+xml;utf8,"
            "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 16 9'>"
            "<defs><linearGradient id='g' x1='0' y1='0' x2='1' y2='1'>"
            "<stop offset='0' stop-color='%23f59e0b'/>"
            "<stop offset='1' stop-color='%231a1208'/>"
            "</linearGradient></defs>"
            "<rect width='16' height='9' fill='url(%23g)'/></svg>"
        )

    # ── Step 1 rewrite: explicit @@IMG/<kw>@@ ───────────────────────────
    def _rep_placeholder(mm: re.Match) -> str:
        return _resolve(mm.group(1).strip())
    html = placeholder_re.sub(_rep_placeholder, html)

    # ── Step 2 rewrite: <img src="..."> ─────────────────────────────────
    def _rep_img(mm: re.Match) -> str:
        before, _src, after = mm.group(1), mm.group(2), mm.group(3)
        full = (before or "") + " " + (after or "")
        alt_m = re.search(r'\balt="([^"]*)"', full)
        alt = alt_m.group(1) if alt_m else ""
        heading = _find_nearest_heading_before(mm.start())
        cls = _find_class_hint_before(mm.start())
        ctx = " ".join(filter(None, [alt, heading, cls])).strip() or "abstract"
        new_src = _resolve(ctx)
        return f'<img {(before or "").strip()} src="{new_src}" {(after or "").strip()}>'
    html = img_re.sub(_rep_img, html)

    # ── Step 3 rewrite: background-image: url(...) ──────────────────────
    def _rep_bg(mm: re.Match) -> str:
        url_in = mm.group(1)
        if url_in.startswith("data:") or url_in.startswith("/api/freebuild/v2/img/"):
            return mm.group(0)
        if "@@IMG" in url_in:
            return mm.group(0)  # already handled
        pos = mm.start()
        before = html[max(0, pos - 800):pos]
        cls = re.findall(r'class="([^"]+)"', before)
        h_m = re.findall(r"<h[1-4][^>]*>([^<]+)</h[1-4]>", before)
        ctx = " ".join(filter(None, [(cls[-1] if cls else ""), (h_m[-1] if h_m else "")])).strip() or "abstract"
        return f"background-image:url('{_resolve(ctx)}')"
    html = bg_re.sub(_rep_bg, html)

    return html
