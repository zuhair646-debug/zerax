"""
App Studio — AI Tools
The AI Producer can call these tools during chat to actually act on the project:
  • add_feature_to_project(feature_id)        — adds a feature (deducts credits)
  • remove_feature_from_project(feature_db_id) — removes a feature
  • list_features()                             — what's added so far
  • update_project_metadata(title?, description?, target_audience?, primary_color?)
  • build_project_now()                          — generate the actual code package
  • suggest_app_icon_prompt()                   — return a Nano Banana ready prompt
  • generate_marketing_copy(angle)              — return Arabic landing copy
The tool loop runs for up to 6 iterations per turn.
"""
from __future__ import annotations
import json
import re
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Callable, Awaitable

logger = logging.getLogger(__name__)

# Tool schemas for OpenAI function-calling format
APP_STUDIO_TOOLS: List[Dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "add_feature_to_project",
            "description": "Add a feature to the current project. The user is charged the feature cost in Zitex credits. Refuse silently if already added.",
            "parameters": {
                "type": "object",
                "properties": {
                    "feature_id": {"type": "string", "description": "ID from the feature catalogue (e.g. auth_basic, screen_chat, subscription, addon_admin_panel)"},
                },
                "required": ["feature_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "remove_feature_from_project",
            "description": "Remove a feature from the project. Credits are NOT refunded.",
            "parameters": {
                "type": "object",
                "properties": {
                    "feature_id": {"type": "string"},
                },
                "required": ["feature_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_features",
            "description": "List currently added features in the project.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_project_metadata",
            "description": "Update project title/description/target_audience/primary_color.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "description": {"type": "string"},
                    "target_audience": {"type": "string"},
                    "primary_color": {"type": "string", "description": "Hex color e.g. #6366f1"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "build_project_now",
            "description": "Trigger the build engine NOW. Generates code package (PWA/Capacitor/Native/FullStack) and returns the preview_url + zip_url. Only call when user explicitly approves or asks to build.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "suggest_app_icon_prompt",
            "description": "Return a polished cinematic English prompt for Nano Banana image generation to produce an app icon based on the project's title and concept.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "generate_marketing_copy",
            "description": "Generate Arabic marketing copy for a landing-page hero (headline, subheadline, CTA).",
            "parameters": {
                "type": "object",
                "properties": {
                    "angle": {"type": "string", "description": "marketing angle e.g. 'speed', 'savings', 'community'"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "recommend_next_steps",
            "description": "Analyze the project & added features, return a numbered list of the most impactful next steps the user should take.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "analyze_uploaded_designs",
            "description": "Inspect the design mockups (images + PDFs) the user has uploaded to the project, extract a structured design brief (palette hex colors, typography hints, list of screens detected, layout style, navigation pattern, must-keep components) and save it onto the project. The build engine reads this brief and respects it. Always call this BEFORE build_project_now whenever attachments exist.",
            "parameters": {
                "type": "object",
                "properties": {
                    "palette": {"type": "array", "items": {"type": "string"}, "description": "List of hex colors (3-6 of them) extracted from the mockups e.g. ['#0b1d3a','#f4a261']"},
                    "screens": {"type": "array", "items": {"type": "string"}, "description": "Names of screens detected e.g. ['الرئيسية','تفاصيل المنتج','السلة','الحساب']"},
                    "layout_style": {"type": "string", "description": "Short Arabic description of the visual style e.g. 'minimal + cards + bottom-nav' or 'editorial + serif typography'"},
                    "navigation": {"type": "string", "description": "navigation pattern e.g. 'bottom-tabs', 'sidebar', 'top-nav', 'drawer'"},
                    "typography": {"type": "string", "description": "Font hints e.g. 'Tajawal bold + sans body'"},
                    "primary_color": {"type": "string", "description": "Primary hex color to override the project's"},
                    "notes": {"type": "string", "description": "Any additional must-keep details from the mockups (icons, brand marks, etc.)"},
                },
                "required": ["palette", "screens", "layout_style"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "generate_store_assets",
            "description": "Generate App Store / Play Store submission package: 5 mockup screenshots (via Nano Banana), store title (30 chars max), short description (80 chars), full description (Arabic, 1500-3500 chars), 8 keywords, and a step-by-step submission guide for both stores.",
            "parameters": {
                "type": "object",
                "properties": {
                    "tone": {"type": "string", "description": "marketing tone e.g. 'professional', 'friendly', 'bold'"},
                },
            },
        },
    },
]


# ════════════════════════════════════════════════════════════════════════
# Tool runtime
# ════════════════════════════════════════════════════════════════════════
class ToolRuntime:
    """Holds dependencies the tools need to run."""

    def __init__(self, db, user_id: str, project_id: str,
                 feature_catalog: List[Dict[str, Any]],
                 project_types: List[Dict[str, Any]],
                 build_fn: Callable[[Dict[str, Any], List[Dict[str, Any]]], Dict[str, Any]]):
        self.db = db
        self.user_id = user_id
        self.project_id = project_id
        self.feature_catalog = feature_catalog
        self.project_types = project_types
        self.build_fn = build_fn

    async def _project(self) -> Optional[Dict[str, Any]]:
        return await self.db.app_projects.find_one(
            {"id": self.project_id, "user_id": self.user_id}, {"_id": 0}
        )

    async def _features(self) -> List[Dict[str, Any]]:
        cur = self.db.app_project_features.find(
            {"project_id": self.project_id}, {"_id": 0}
        ).sort([("created_at", 1)])
        return await cur.to_list(200)

    def _feat_meta(self, fid: str) -> Optional[Dict[str, Any]]:
        return next((f for f in self.feature_catalog if f["id"] == fid), None)

    async def add_feature_to_project(self, feature_id: str) -> Dict[str, Any]:
        feat = self._feat_meta(feature_id)
        if not feat:
            return {"ok": False, "error": f"feature غير معروف: {feature_id}",
                    "available_ids": [f["id"] for f in self.feature_catalog]}
        existing = await self.db.app_project_features.find_one(
            {"project_id": self.project_id, "feature_id": feature_id}, {"_id": 0, "id": 1}
        )
        if existing:
            return {"ok": False, "error": "موجود مسبقاً", "feature_id": feature_id}
        cost = feat["cost"]
        # Owner bypass
        u = await self.db.users.find_one({"id": self.user_id}, {"_id": 0, "credits": 1, "is_owner": 1})
        if not (u or {}).get("is_owner"):
            deduct = await self.db.users.update_one(
                {"id": self.user_id, "credits": {"$gte": cost}},
                {"$inc": {"credits": -cost},
                 "$push": {"credit_history": {
                     "amount": -cost,
                     "reason": f"app_studio_tool_feature_{feature_id}",
                     "timestamp": datetime.now(timezone.utc).isoformat(),
                 }}},
            )
            if deduct.modified_count == 0:
                return {"ok": False, "error": f"رصيد غير كافٍ ({cost} نقطة).", "feature_id": feature_id}
        import uuid as _u
        doc = {
            "id": _u.uuid4().hex,
            "project_id": self.project_id,
            "user_id": self.user_id,
            "feature_id": feature_id,
            "config": {},
            "cost_paid": cost,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        await self.db.app_project_features.insert_one(doc.copy())
        await self.db.app_projects.update_one(
            {"id": self.project_id},
            {"$set": {"updated_at": datetime.now(timezone.utc).isoformat()}},
        )
        return {"ok": True, "feature_id": feature_id, "label_ar": feat["label_ar"],
                "cost_paid": cost, "category": feat["category"]}

    async def remove_feature_from_project(self, feature_id: str) -> Dict[str, Any]:
        r = await self.db.app_project_features.delete_one(
            {"project_id": self.project_id, "user_id": self.user_id, "feature_id": feature_id}
        )
        return {"ok": True, "deleted": r.deleted_count, "feature_id": feature_id,
                "note": "النقاط لا تُسترجع."}

    async def list_features(self) -> Dict[str, Any]:
        feats = await self._features()
        return {
            "ok": True,
            "count": len(feats),
            "features": [
                {"feature_id": f["feature_id"],
                 "label_ar": (self._feat_meta(f["feature_id"]) or {}).get("label_ar", f["feature_id"]),
                 "cost_paid": f.get("cost_paid", 0)}
                for f in feats
            ],
        }

    async def update_project_metadata(self, title: Optional[str] = None,
                                      description: Optional[str] = None,
                                      target_audience: Optional[str] = None,
                                      primary_color: Optional[str] = None) -> Dict[str, Any]:
        upd: Dict[str, Any] = {"updated_at": datetime.now(timezone.utc).isoformat()}
        if title: upd["title"] = title[:160]
        if description: upd["description"] = description[:2000]
        if target_audience: upd["target_audience"] = target_audience[:500]
        if primary_color and primary_color.startswith("#"): upd["primary_color"] = primary_color[:7]
        if len(upd) <= 1:
            return {"ok": False, "error": "ما فيه حقول للتحديث"}
        await self.db.app_projects.update_one(
            {"id": self.project_id, "user_id": self.user_id}, {"$set": upd}
        )
        return {"ok": True, "updated": list(upd.keys())}

    async def build_project_now(self) -> Dict[str, Any]:
        proj = await self._project()
        if not proj:
            return {"ok": False, "error": "project missing"}
        feats = await self._features()
        try:
            res = self.build_fn(proj, feats)
            await self.db.app_projects.update_one(
                {"id": self.project_id},
                {"$set": {
                    "stage": "built",
                    "build_output": res,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }},
            )
            return {"ok": True, **res}
        except Exception as e:
            logger.error(f"build failed: {e}", exc_info=True)
            return {"ok": False, "error": f"build failed: {str(e)[:300]}"}

    async def suggest_app_icon_prompt(self) -> Dict[str, Any]:
        proj = await self._project()
        if not proj:
            return {"ok": False, "error": "project missing"}
        title = proj.get("title", "")
        color = proj.get("primary_color", "#6366f1")
        desc = proj.get("description", "")
        prompt = (
            f"App icon for '{title}'. Concept: {desc[:120]}. "
            f"Primary brand color: {color}. Style: modern, flat, gradient, "
            f"glyph centered, no text, iOS Apple Design Award quality, "
            f"1024x1024, transparent background, sharp edges, minimalist."
        )
        return {"ok": True, "image_prompt": prompt,
                "next_step": "استخدم استوديو الصور لتوليد الأيقونة بهذا الـprompt."}

    async def generate_marketing_copy(self, angle: str = "general") -> Dict[str, Any]:
        proj = await self._project()
        if not proj:
            return {"ok": False, "error": "project missing"}
        title = proj.get("title", "تطبيقي")
        desc = proj.get("description", "")
        templates = {
            "speed": (f"⚡ {title} — أسرع من أي وقت مضى",
                      f"{desc} بسرعة لا مثيل لها وتجربة سلسة على كل جهاز.",
                      "حمّل الآن مجاناً"),
            "savings": (f"💰 وفّر مع {title}",
                        f"{desc} وفّر وقتك وجيبك بحلّ ذكي يعمل لك بدلاً عنك.",
                        "ابدأ ادّخار اليوم"),
            "community": (f"🤝 {title} — مجتمعك الجديد",
                          f"{desc} انضم لآلاف المستخدمين الذين غيّروا روتينهم اليومي.",
                          "انضم للمجتمع"),
        }
        h, sub, cta = templates.get(angle, templates["speed"])
        return {"ok": True, "headline": h, "subheadline": sub, "cta": cta, "angle": angle}

    async def recommend_next_steps(self) -> Dict[str, Any]:
        proj = await self._project()
        feats = await self._features()
        feat_ids = {f["feature_id"] for f in feats}
        steps: List[str] = []
        if not feats:
            steps.append("ابدأ بإضافة `auth_basic` و `user_profile` كأساس لأي تطبيق.")
        if "auth_basic" in feat_ids and "user_profile" not in feat_ids:
            steps.append("أضف `user_profile` لتمكين المستخدمين من إدارة بياناتهم.")
        money = {"subscription", "in_app_purchase", "ads"} & feat_ids
        if not money and len(feats) >= 3:
            steps.append("أضف نموذج تحقيق الدخل: `subscription` أو `ads`.")
        addons = {f for f in feat_ids if f.startswith("addon_")}
        if not addons:
            steps.append("فكّر في `addon_admin_panel` لإدارة المستخدمين، أو `addon_marketing_site` لتسويق التطبيق.")
        if proj and proj.get("stage") != "built":
            steps.append("لما تكتمل الميزات، استدع `build_project_now` لتوليد الكود وتنزيل الـzip.")
        if not steps:
            steps.append("الأساس جاهز — وقت `build_project_now` ونشر التطبيق.")
        return {"ok": True, "steps": steps, "feature_count": len(feats),
                "stage": (proj or {}).get("stage")}

    async def analyze_uploaded_designs(self, palette: List[str], screens: List[str],
                                        layout_style: str, navigation: str = "bottom-tabs",
                                        typography: str = "", primary_color: str = "",
                                        notes: str = "") -> Dict[str, Any]:
        """Save the AI-extracted design brief on the project. Build engine reads it."""
        # Sanitize hex colors
        clean_palette = [c for c in (palette or []) if isinstance(c, str) and c.startswith("#") and len(c) in (4, 7)][:8]
        brief = {
            "palette": clean_palette,
            "screens": [s[:80] for s in (screens or [])][:20],
            "layout_style": (layout_style or "")[:300],
            "navigation": (navigation or "bottom-tabs")[:40],
            "typography": (typography or "")[:200],
            "primary_color": primary_color if (isinstance(primary_color, str) and primary_color.startswith("#")) else (clean_palette[0] if clean_palette else None),
            "notes": (notes or "")[:1500],
            "extracted_at": datetime.now(timezone.utc).isoformat(),
        }
        upd: Dict[str, Any] = {"design_brief": brief,
                               "updated_at": datetime.now(timezone.utc).isoformat()}
        if brief.get("primary_color"):
            upd["primary_color"] = brief["primary_color"]
        await self.db.app_projects.update_one(
            {"id": self.project_id, "user_id": self.user_id}, {"$set": upd}
        )
        return {"ok": True, "design_brief": brief,
                "note": "تم استخراج Design Brief وحفظه. محرك البناء راح يلتزم به."}

    async def generate_store_assets(self, tone: str = "professional") -> Dict[str, Any]:
        proj = await self._project()
        if not proj:
            return {"ok": False, "error": "project missing"}
        title = proj.get("title", "تطبيقي")
        desc = (proj.get("description") or "").strip()
        audience = proj.get("target_audience", "")
        color = proj.get("primary_color", "#6366f1")

        short_title = title[:30]
        subtitle = (desc[:80] or f"{title} — حلّ ذكي")[:80]
        full_desc = f"""{title}

{desc}

✨ مميزاتنا:
- تجربة استخدام سلسة وأنيقة
- متوافق مع الجوال والتابلت
- يدعم اللغة العربية والإنجليزية
- تحديثات مستمرة ودعم فني

👥 لمن هذا التطبيق:
{audience or 'لكل من يبحث عن حلّ احترافي بواجهة عربية متقنة.'}

🚀 ابدأ الآن:
نزّل التطبيق الآن وعش تجربة جديدة. نقدّر تقييمك وملاحظاتك بعد التجربة.

📧 للتواصل والدعم: راسلنا عبر صفحة الإعدادات داخل التطبيق.
""".strip()

        # Build 5 screenshot prompts for Nano Banana
        screen_prompts = [
            f"Mobile app screenshot mockup, hero/launch screen for '{title}'. Style: modern Arabic UI, RTL, "
            f"primary color {color}, clean typography, premium feel. Display app name centered. iPhone 15 frame.",
            f"Mobile app screenshot mockup, main feed screen for '{title}'. Show list of cards with Arabic placeholder text, "
            f"bottom tab bar, primary color {color}. {audience or 'general audience'}.",
            f"Mobile app screenshot mockup, detail screen for '{title}'. Header image, info card, primary CTA button with primary color {color}.",
            f"Mobile app screenshot mockup, profile/settings screen for '{title}'. Avatar circle, list rows, dark or light theme matching {color}.",
            f"Mobile app screenshot mockup, success/celebration screen for '{title}'. Confetti, big checkmark, primary color {color}, friendly tone.",
        ]

        keywords = []
        for w in re.findall(r"[\w\u0600-\u06FF]+", f"{title} {desc} {audience}"):
            if len(w) >= 3 and w not in keywords:
                keywords.append(w)
            if len(keywords) >= 8:
                break

        submission_guide = {
            "app_store_ar": (
                "## رفع على App Store (Apple)\n"
                "1. **سجّل في Apple Developer Program** ($99/سنة): https://developer.apple.com/programs/\n"
                "2. **افتح App Store Connect** → My Apps → \"+\" → New App.\n"
                "3. اختر Platform: iOS، اكتب اسم التطبيق، اختار Bundle ID.\n"
                "4. أضف الصور (5 screenshots لكل من 6.5\" و 5.5\")، أيقونة 1024×1024، وصف عربي.\n"
                "5. ارفع البناء (build) من Xcode عبر `Archive → Distribute App → App Store Connect`.\n"
                "6. اختار الفئة (Category)، عمر الجمهور (Age Rating)، أسعار التطبيق.\n"
                "7. **Submit for Review** — مراجعة آبل تأخذ 1-3 أيام.\n"
                "✅ نصيحة: ارفع كل النصوص العربية + ترجمة إنجليزية لو ممكن."
            ),
            "play_store_ar": (
                "## رفع على Google Play\n"
                "1. **سجّل في Google Play Console** ($25 مرة واحدة): https://play.google.com/console\n"
                "2. Create app → اختر اسم، لغة افتراضية (عربي)، نوع (Free/Paid).\n"
                "3. تعبئة Store Listing: العنوان، الوصف القصير (80 حرف)، الوصف الكامل، 8 screenshots، أيقونة 512×512، Feature Graphic 1024×500.\n"
                "4. App Content: تصنيف عمري، Privacy Policy URL، Data Safety.\n"
                "5. ارفع الـAAB من Android Studio: `Build → Generate Signed Bundle`.\n"
                "6. Internal/Closed/Open testing → Production rollout (يبدأ بنسبة %20).\n"
                "7. **Submit** — مراجعة جوجل عادةً 1-7 أيام."
            ),
        }

        store_assets = {
            "store_title": short_title,
            "subtitle": subtitle,
            "full_description_ar": full_desc,
            "keywords": keywords,
            "screenshot_prompts": screen_prompts,
            "submission_guide": submission_guide,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
        await self.db.app_projects.update_one(
            {"id": self.project_id, "user_id": self.user_id},
            {"$set": {"store_assets": store_assets,
                      "updated_at": datetime.now(timezone.utc).isoformat()}},
        )
        return {"ok": True, "store_assets": store_assets,
                "note": "تم تجهيز حزمة النشر. الـscreenshot prompts جاهزة لاستخدامها في استوديو الصور (Nano Banana)."}


# ════════════════════════════════════════════════════════════════════════
# Dispatcher
# ════════════════════════════════════════════════════════════════════════
async def execute_app_studio_tool(runtime: ToolRuntime, name: str, args: Dict[str, Any]) -> Dict[str, Any]:
    try:
        fn = getattr(runtime, name, None)
        if not fn or not callable(fn):
            return {"ok": False, "error": f"tool not found: {name}"}
        # Filter kwargs to only those the function accepts
        return await fn(**(args or {}))
    except TypeError as e:
        return {"ok": False, "error": f"bad args: {str(e)[:200]}"}
    except Exception as e:
        logger.error(f"tool exec failed [{name}]: {e}", exc_info=True)
        return {"ok": False, "error": f"{type(e).__name__}: {str(e)[:200]}"}


def system_prompt(project: Dict[str, Any], features: List[Dict[str, Any]],
                  catalog: List[Dict[str, Any]], project_types: List[Dict[str, Any]],
                  attachments_summary: str = "") -> str:
    feat_lines = "\n".join(f"  - `{f['id']}` ({f['category']}, {f['cost']}ن): {f['label_ar']}" for f in catalog)
    ptype_lines = "\n".join(f"  - `{t['id']}`: {t['label_ar']} ({t['build_cost']}ن للبناء)" for t in project_types)
    ptype = next((t for t in project_types if t["id"] == project.get("type")), {})
    feat_ids = [f["feature_id"] for f in features]
    design_brief = project.get("design_brief") or {}
    brief_block = ""
    if design_brief:
        brief_block = (
            "\n\n🎨 **Design Brief مستخرج سابقاً من مرفقات العميل** (ملتزم به):\n"
            f"- palette: {design_brief.get('palette')}\n"
            f"- screens: {design_brief.get('screens')}\n"
            f"- layout: {design_brief.get('layout_style')}\n"
            f"- navigation: {design_brief.get('navigation')}\n"
            f"- typography: {design_brief.get('typography')}\n"
            f"- notes: {(design_brief.get('notes') or '')[:300]}"
        )
    return f"""أنت "المنتج التنفيذي" في استوديو تطبيقات زيتاكس. تكلم سعودي طبيعي، عملي، صادق.

📱 **المشروع الحالي**:
- العنوان: {project.get('title')}
- النوع: {ptype.get('label_ar')} (`{project.get('type')}`)
- الوصف: {project.get('description') or '—'}
- الجمهور: {project.get('target_audience') or '—'}
- اللون الأساسي: {project.get('primary_color')}
- الميزات المضافة ({len(feat_ids)}): {', '.join(feat_ids) or '(لا شي)'}
- المرحلة: {project.get('stage')}{brief_block}

{attachments_summary or ''}

🛠️ **أدواتك** (استدعها بحذر، لا تتفلسف):
- `add_feature_to_project(feature_id)` — يضيف ميزة (يخصم النقاط)
- `remove_feature_from_project(feature_id)` — يحذف ميزة (لا استرجاع)
- `list_features()` — قائمة الميزات
- `update_project_metadata(...)` — تحديث العنوان/الوصف/اللون
- `analyze_uploaded_designs(palette, screens, layout_style, ...)` — **مهم**: لما العميل يرفع مخططات/تصاميم، استدع هذي قبل البناء عشان تستخرج Design Brief مهيكل.
- `build_project_now()` — يولّد الكود الفعلي (PWA/Capacitor/Native/FullStack) — يحترم design_brief لو موجود.
- `suggest_app_icon_prompt()` — prompt للأيقونة
- `generate_marketing_copy(angle)` — نص تسويقي عربي
- `generate_store_assets(tone)` — حزمة نشر للمتاجر (5 screenshots + title + description + keywords + guide)
- `recommend_next_steps()` — تلخيص الخطوات

📚 **كتالوج الميزات المتاحة**:
{feat_lines}

📚 **أنواع التطبيقات**:
{ptype_lines}

🎯 **قواعد سلوكك**:
1. اسأل العميل عن المشكلة قبل ما تكدّس ميزات.
2. **لو فيه مرفقات (صور/PDF) في رسالة المستخدم → افحصها بنفسك، استخرج الألوان/الشاشات/الـlayout، استدعِ `analyze_uploaded_designs` قبل البناء**. التزم بالتصاميم حرفياً، ممنوع تغييرها.
3. لا تضيف ميزة بدون إذن صريح. وضّح التكلفة دائماً.
4. لو طلب "أضف", "أبي", "حط" → استدعِ `add_feature_to_project` مباشرة.
5. لو طلب البناء → استدعِ `build_project_now` وأظهر له الـpreview_url والـzip_url.
6. لو طلب نشر للمتاجر → استدعِ `generate_store_assets`.
7. لا تطلق تطبيق ناقص. لو في اشتراكات بدون auth → نبّهه. لو addon_admin_panel بدون auth → نبّهه.
8. كل رد ≤ 150 كلمة. عملي، سعودي، بلا حشو.
9. عند الانتهاء من أداة، اعرض النتيجة بأسلوب طبيعي — لا تطبع JSON خام."""
