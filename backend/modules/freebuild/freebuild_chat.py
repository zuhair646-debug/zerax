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


def _extract_html(text: str) -> Optional[str]:
    m = HTML_BLOCK_RE.search(text)
    if m:
        return m.group(1).strip()
    m = HTML_FALLBACK_RE.search(text)
    if m:
        return m.group(1).strip()
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


def _strip_code_from_chat(text: str) -> str:
    """Remove fenced code blocks from displayed chat text and replace with a friendly notice.
    Code is kept in current_html for Live Preview only."""
    has_code = bool(_CODE_BLOCK_RE.search(text))
    cleaned = _CODE_BLOCK_RE.sub("\n*✨ تم تحديث المعاينة الحية — افتح تبويب المعاينة للمشاهدة*\n", text)
    if has_code:
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
        await db.freebuild_projects.insert_one({
            "id": pid,
            "user_id": user["user_id"],
            "website_type": "custom",  # legacy field, kept for compatibility
            "name": payload.name.strip()[:120],
            "description": payload.description.strip()[:1500],
            "status": "active",
            "current_phase": "discovery",
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

        extra_ctx = (
            f"اسم المشروع: {proj['name']}\n"
            f"وصف المشروع: {proj['description'] or '(لم يحدد العميل وصفاً بعد — اسأله ودَوّن)'}\n"
            f"{assets_for_use}"
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
            "🎨 تصاميم متعددة (Design Variants) — اللب الذكي:\n"
            "عند تقديم خيارات تصميم للعميل، اكتب 2-3 صفحات HTML كاملة في رسالة واحدة — كل واحدة في ```html ...``` block منفصل.\n"
            "النظام راح يعرضها للعميل كـ live mini-previews يضغط عليها ويختار وحدة → اللي يختاره يصير current_html مباشرة بدون تغيير.\n"
            "كل variant يجب أن يكون كامل ومستقل (<!DOCTYPE html>...</html>) مع Tailwind CDN ومحتوى وهمي (Lorem) لكنه مرتب.\n"
            "أمثلة على متى تستخدم variants: 'وش الأنسب: تصميم 1 (داكن فاخر) ولا 2 (فاتح ناعم) ولا 3 (مينيمال)؟'\n"
            "بعد ما العميل يختار، عدّل عليه تدريجياً — لا تعيد تصميم من الصفر.\n"
            "\n"
            "✅ التحقق الذاتي (لا تكذب على العميل):\n"
            "بعد ما تنشئ أي قسم جديد في الـHTML، اختتم رسالتك بـ checklist واضح:\n"
            "  ✓ Hero: موجود ويحتوي زر CTA يشير إلى #contact\n"
            "  ✓ المنتجات: 3 cards مع صور placeholder\n"
            "  ⚠️ نموذج التواصل: لم أضفه بعد — سأضيفه في الجولة القادمة\n"
            "إذا قلت 'أضفت X' بدون فعلاً تضيفه في الكود → هذي خيانة لثقة العميل. الصدق أولاً.\n"
            "إذا في عنصر معطوب أو رابط فارغ، اذكر ذلك بصراحة كـ ⚠️ بدل ما تخفيها.\n"
            "7. عدّل تدريجياً — لا تعيد بناء كل شي من جديد كل مرة. حافظ على الـDesign اللي اختاره العميل.\n"
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

        try:
            from modules.zitex_ai import zitex_chat
            result = await zitex_chat(
                agent="freebuild",
                messages=msg_list,
                user_id=user["user_id"],
                extra_context=extra_ctx,
                requires_vision=bool(vision_images),
            )
            if not result.get("ok"):
                raise HTTPException(502, "خطأ في الذكاء الاصطناعي")
            ai_text = result["content"]
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
        all_variants = _extract_all_html_variants(ai_text)
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

        # Strip code blocks from chat display — code is private/paid feature.
        # If we have design variants, replace all blocks with a single one-line notice;
        # otherwise replace each block with the "updated live preview" notice.
        if design_variants:
            chat_text = _CODE_BLOCK_RE.sub("", ai_text).strip()
            chat_text = re.sub(r"\n{3,}", "\n\n", chat_text)
            chat_text = (chat_text + "\n\n*🎨 شوف التصاميم تحت — اختر اللي يعجبك*").strip()
        else:
            chat_text = _strip_code_from_chat(ai_text)
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
        if new_html:
            update_set["current_html"] = new_html
        await db.freebuild_projects.update_one(
            {"id": pid},
            {
                "$push": {
                    "messages": {
                        "$each": [
                            {"role": "user", "content": message, "timestamp": _now(), "pending_assets": [], "attachments": attachment_meta, "reference": reference_meta, "answer_meta": parsed_answer_meta},
                            {"role": "assistant", "content": clean_text, "timestamp": _now(), "pending_assets": pending_assets, "had_html": bool(new_html), "options": options, "design_variants": design_variants},
                        ]
                    }
                },
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
        await db.freebuild_projects.update_one(
            {"id": pid},
            {"$set": {
                "current_html": variant_html,
                "approved_design_id": variant_id,
                "updated_at": _now(),
            }},
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
