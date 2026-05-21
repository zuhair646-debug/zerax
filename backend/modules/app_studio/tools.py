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
                  catalog: List[Dict[str, Any]], project_types: List[Dict[str, Any]]) -> str:
    feat_lines = "\n".join(f"  - `{f['id']}` ({f['category']}, {f['cost']}ن): {f['label_ar']}" for f in catalog)
    ptype_lines = "\n".join(f"  - `{t['id']}`: {t['label_ar']} ({t['build_cost']}ن للبناء)" for t in project_types)
    ptype = next((t for t in project_types if t["id"] == project.get("type")), {})
    feat_ids = [f["feature_id"] for f in features]
    return f"""أنت "المنتج التنفيذي" في استوديو تطبيقات زيتاكس. تكلم سعودي طبيعي، عملي، صادق.

📱 **المشروع الحالي**:
- العنوان: {project.get('title')}
- النوع: {ptype.get('label_ar')} (`{project.get('type')}`)
- الوصف: {project.get('description') or '—'}
- الجمهور: {project.get('target_audience') or '—'}
- اللون الأساسي: {project.get('primary_color')}
- الميزات المضافة ({len(feat_ids)}): {', '.join(feat_ids) or '(لا شي)'}
- المرحلة: {project.get('stage')}

🛠️ **أدواتك** (استدعها بحذر، لا تتفلسف):
- `add_feature_to_project(feature_id)` — يضيف ميزة (يخصم النقاط)
- `remove_feature_from_project(feature_id)` — يحذف ميزة (لا استرجاع)
- `list_features()` — قائمة الميزات
- `update_project_metadata(...)` — تحديث العنوان/الوصف/اللون
- `build_project_now()` — يولّد الكود الفعلي للتطبيق (PWA + manifest + SW أو Capacitor أو Native)
- `suggest_app_icon_prompt()` — يعطيك prompt لتوليد أيقونة
- `generate_marketing_copy(angle)` — نص تسويقي عربي
- `recommend_next_steps()` — يلخّص خطوات التحسين

📚 **كتالوج الميزات المتاحة**:
{feat_lines}

📚 **أنواع التطبيقات**:
{ptype_lines}

🎯 **قواعد سلوكك**:
1. اسأل العميل عن المشكلة قبل ما تكدّس ميزات. الإجابة على "وش مشكلة جمهورك" أهم من قائمة ميزات.
2. لا تضيف ميزة بدون إذن صريح. وضّح التكلفة دائماً.
3. لو العميل قال "أضف", "أبي", "حط" أو ما يشابه → استدع `add_feature_to_project` مباشرة.
4. لو طلب البناء النهائي → استدع `build_project_now` وأظهر له الـpreview_url والـzip_url.
5. لا تطلق تطبيق ناقص. لو في اشتراكات بدون auth → نبّهه. لو في addon_admin_panel بدون auth → نبّهه.
6. كل رد ≤ 150 كلمة. عملي، سعودي، بلا حشو.
7. عند الانتهاء من أداة، اعرض النتيجة بأسلوب طبيعي للعميل — لا تطبع JSON خام."""
