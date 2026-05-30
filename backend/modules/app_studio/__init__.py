"""
App Studio — Professional mobile/web app builder with project types,
AI Producer wizard, feature marketplace, and import-existing-app flow.

Project types (be honest about what we can deliver end-to-end):
  • **pwa**      — Progressive Web App. Installable, no app stores needed.
                   We deliver full code + Vercel deploy.
  • **hybrid**   — PWA wrapped via Capacitor for App Store / Play Store.
                   We deliver code + Capacitor config; user needs Apple Dev
                   ($99/yr) or Google Play ($25 one-time) account to publish.
  • **native**   — Native Swift (iOS) / Kotlin (Android) starter code.
                   User builds & signs on their own machine via Xcode /
                   Android Studio. We do NOT compile binaries here.
  • **fullstack**— PWA + FastAPI backend + admin panel + marketing landing.
                   We deliver everything; auto-deploy to Vercel + Railway.

Each project accumulates `features` (rooms, screens, integrations). Every
feature is a paid asset that can be re-used across the project.

Collections:
  app_projects             — project doc {id, user_id, type, title, ...}
  app_project_features     — features list per project (paid)
  app_project_imports      — record of imports from FreeBuild/MobileApp
"""
from __future__ import annotations
import os
import re
import uuid
import json
import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse, JSONResponse, Response
from pydantic import BaseModel, Field

from .builder import build_project, project_build_dir, BUILD_ROOT
from .tools import (
    APP_STUDIO_TOOLS,
    ToolRuntime,
    execute_app_studio_tool,
    system_prompt as build_system_prompt,
)
from .attachments import (
    store_attachment,
    list_attachments,
    delete_attachment,
    fetch_recent_for_vision,
    build_attachment_system_message,
    MAX_ATTACHMENTS_PER_PROJECT,
)

logger = logging.getLogger(__name__)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ════════════════════════════════════════════════════════════════════════
# CATALOGUES
# ════════════════════════════════════════════════════════════════════════
PROJECT_TYPES = [
    {
        "id": "pwa",
        "label_ar": "تطبيق ويب (PWA)",
        "tagline_ar": "أسرع وأرخص — يفتح من المتصفح كأنه تطبيق",
        "pros_ar": ["نشر فوري مجاناً", "تحديث لحظي بدون موافقات", "يعمل على iOS و Android"],
        "cons_ar": ["لا يدخل App Store إلا بـHybrid"],
        "init_cost": 0,
        "build_cost": 40,
        "deployable": True,
        "deploy_provider": "vercel",
    },
    {
        "id": "hybrid",
        "label_ar": "هايبرد (Capacitor)",
        "tagline_ar": "تطبيق ويب مغلّف ليدخل App Store و Google Play",
        "pros_ar": ["وجود رسمي في المتاجر", "نفس الكود لـiOS و Android"],
        "cons_ar": ["تحتاج حساب Apple Dev ($99/سنة) أو Google Play ($25)",
                    "النشر يحتاج Xcode/Android Studio على جهازك"],
        "init_cost": 0,
        "build_cost": 80,
        "deployable": False,
        "deploy_provider": "user_local",
    },
    {
        "id": "native",
        "label_ar": "أصلي (Swift / Kotlin)",
        "tagline_ar": "كود أصلي خام — أعلى أداء وتحكّم كامل بالـAPIs الأصلية",
        "pros_ar": ["أعلى أداء", "وصول كامل لـnative APIs", "تجربة أصلية بحتة"],
        "cons_ar": ["نولّد الكود فقط — البناء يحتاج Xcode / Android Studio عندك",
                    "نشر يدوي للمتاجر"],
        "init_cost": 0,
        "build_cost": 120,
        "deployable": False,
        "deploy_provider": "user_local",
    },
    {
        "id": "fullstack",
        "label_ar": "Full-Stack أصلي",
        "tagline_ar": "PWA + FastAPI Backend + لوحة تحكم + موقع تسويقي. ينشر تلقائياً.",
        "pros_ar": ["كل شي في صفقة واحدة", "نشر تلقائي Vercel + Railway", "لوحة تحكم جاهزة"],
        "cons_ar": ["أعلى تكلفة", "أطول وقت إنتاج"],
        "init_cost": 0,
        "build_cost": 220,
        "deployable": True,
        "deploy_provider": "vercel+railway",
    },
]

FEATURE_CATALOG = [
    # Core
    {"id": "auth_basic",      "label_ar": "تسجيل دخول (بريد + كلمة سر)", "cost": 10, "category": "core"},
    {"id": "auth_social",     "label_ar": "تسجيل دخول اجتماعي (Google)", "cost": 14, "category": "core"},
    {"id": "user_profile",    "label_ar": "ملف شخصي للمستخدم",          "cost": 6,  "category": "core"},
    {"id": "push_notifications", "label_ar": "إشعارات فورية",             "cost": 12, "category": "core"},
    # Screens
    {"id": "screen_home",     "label_ar": "شاشة رئيسية مخصّصة", "cost": 5, "category": "screen"},
    {"id": "screen_list",     "label_ar": "شاشة قائمة (Feed)",   "cost": 5, "category": "screen"},
    {"id": "screen_detail",   "label_ar": "شاشة تفاصيل عنصر",     "cost": 5, "category": "screen"},
    {"id": "screen_search",   "label_ar": "بحث + فلترة",          "cost": 8, "category": "screen"},
    {"id": "screen_settings", "label_ar": "إعدادات",              "cost": 4, "category": "screen"},
    {"id": "screen_chat",     "label_ar": "شات لحظي",             "cost": 18, "category": "screen"},
    {"id": "screen_map",      "label_ar": "خريطة تفاعلية",        "cost": 12, "category": "screen"},
    # Monetization
    {"id": "subscription",    "label_ar": "اشتراكات شهرية (Stripe)", "cost": 22, "category": "money"},
    {"id": "in_app_purchase", "label_ar": "شراء داخل التطبيق",        "cost": 20, "category": "money"},
    {"id": "ads",             "label_ar": "إعلانات (AdMob/AdSense)", "cost": 8,  "category": "money"},
    # Add-ons (extra products built alongside)
    {"id": "addon_admin_panel",   "label_ar": "لوحة تحكم للمالك",       "cost": 35, "category": "addon"},
    {"id": "addon_marketing_site","label_ar": "موقع تسويقي + Landing",  "cost": 30, "category": "addon"},
    {"id": "addon_blog",          "label_ar": "مدونة / Help Center",    "cost": 18, "category": "addon"},
    # Integrations
    {"id": "integration_ai_chat", "label_ar": "ذكاء صناعي داخل التطبيق", "cost": 18, "category": "ai"},
    {"id": "integration_payment", "label_ar": "دفع إلكتروني (مدى/Visa)", "cost": 16, "category": "ai"},
    {"id": "integration_analytics","label_ar": "تحليلات (PostHog/Mixpanel)", "cost": 10, "category": "ai"},
]


# ════════════════════════════════════════════════════════════════════════
# Pydantic models
# ════════════════════════════════════════════════════════════════════════
class ProjectCreateIn(BaseModel):
    title: str = Field(..., min_length=1, max_length=160)
    type: str = Field(..., description="pwa|hybrid|native|fullstack")
    description: str = ""
    target_audience: str = ""
    primary_color: str = "#6366f1"  # default indigo
    style_direction: str = ""


class FeatureAddIn(BaseModel):
    project_id: str
    feature_id: str
    config: Dict[str, Any] = {}


class ImportExistingIn(BaseModel):
    """Import a pre-existing artifact the user already built on the platform.
    Sources we support:
      • freebuild_site:{site_id}    — generated SPA from FreeBuild v2
      • mobile_app:{mobile_id}      — generated mobile app from mobile_app_builder
    """
    project_id: str
    source: str = Field(..., description="format: freebuild_site:<id> or mobile_app:<id>")


class AppProducerChatIn(BaseModel):
    project_id: str
    step: str = Field(..., description="discover|features|addons|launch")
    message: str = ""


# ════════════════════════════════════════════════════════════════════════
# Router factory
# ════════════════════════════════════════════════════════════════════════
def create_app_studio_router(db, get_current_user) -> APIRouter:
    router = APIRouter(prefix="/api/app-studio", tags=["app-studio"])

    try:
        from modules.shared import bind_db as _shared_bind
        _shared_bind(db)
    except Exception:
        pass

    async def _get_credits(user_id: str) -> int:
        d = await db.users.find_one({"id": user_id}, {"_id": 0, "credits": 1})
        return int((d or {}).get("credits", 0))

    # ── Options / Catalogues ───────────────────────────────────────────
    @router.get("/options")
    async def options(_=Depends(get_current_user)):
        return {
            "ok": True,
            "project_types": PROJECT_TYPES,
            "features": FEATURE_CATALOG,
            "feature_categories": [
                {"id": "core",    "label": "أساسي"},
                {"id": "screen",  "label": "شاشات"},
                {"id": "money",   "label": "ربحية"},
                {"id": "addon",   "label": "إضافات"},
                {"id": "ai",      "label": "ذكاء + تكامل"},
            ],
        }

    # ── Projects CRUD ─────────────────────────────────────────────────
    @router.get("/projects")
    async def list_projects(user=Depends(get_current_user)):
        cur = db.app_projects.find({"user_id": user["user_id"]}, {"_id": 0}).sort([("updated_at", -1)]).limit(50)
        items = await cur.to_list(50)
        for p in items:
            p["features_count"] = await db.app_project_features.count_documents({"project_id": p["id"]})
        return {"ok": True, "projects": items}

    @router.post("/projects/create")
    async def create_project(payload: ProjectCreateIn, user=Depends(get_current_user)):
        ptype = next((t for t in PROJECT_TYPES if t["id"] == payload.type), None)
        if not ptype:
            raise HTTPException(400, f"نوع غير معروف: {payload.type}")
        doc = {
            "id": str(uuid.uuid4()),
            "user_id": user["user_id"],
            "type": payload.type,
            "type_label": ptype["label_ar"],
            "title": payload.title,
            "description": payload.description,
            "target_audience": payload.target_audience,
            "primary_color": payload.primary_color,
            "style_direction": payload.style_direction,
            "stage": "planning",  # planning → building → built
            "build_cost_estimate": ptype["build_cost"],
            "imports": [],
            "build_output": None,
            "created_at": _now(),
            "updated_at": _now(),
        }
        await db.app_projects.insert_one(doc.copy())
        return {"ok": True, "project": {k: v for k, v in doc.items() if k != "_id"}}

    @router.get("/projects/{project_id}")
    async def get_project(project_id: str, user=Depends(get_current_user)):
        p = await db.app_projects.find_one({"id": project_id, "user_id": user["user_id"]}, {"_id": 0})
        if not p:
            raise HTTPException(404, "project not found")
        feat_cur = db.app_project_features.find({"project_id": project_id}, {"_id": 0}).sort([("created_at", 1)])
        features = await feat_cur.to_list(200)
        # Decorate features with catalogue metadata
        cat_by_id = {f["id"]: f for f in FEATURE_CATALOG}
        for f in features:
            meta = cat_by_id.get(f.get("feature_id"), {})
            f["label_ar"] = meta.get("label_ar", f.get("feature_id"))
            f["category"] = meta.get("category", "core")
            f["cost"] = meta.get("cost", 0)
        return {"ok": True, "project": p, "features": features}

    @router.delete("/projects/{project_id}")
    async def delete_project(project_id: str, user=Depends(get_current_user)):
        r = await db.app_projects.delete_one({"id": project_id, "user_id": user["user_id"]})
        await db.app_project_features.delete_many({"project_id": project_id})
        return {"ok": True, "deleted": r.deleted_count}

    # ── Features (paid) ────────────────────────────────────────────────
    @router.post("/feature/add")
    async def add_feature(payload: FeatureAddIn, user=Depends(get_current_user)):
        proj = await db.app_projects.find_one(
            {"id": payload.project_id, "user_id": user["user_id"]}, {"_id": 0}
        )
        if not proj:
            raise HTTPException(404, "project not found")
        feat = next((f for f in FEATURE_CATALOG if f["id"] == payload.feature_id), None)
        if not feat:
            raise HTTPException(400, f"feature غير معروف: {payload.feature_id}")
        # No duplicates
        existing = await db.app_project_features.find_one(
            {"project_id": payload.project_id, "feature_id": payload.feature_id},
            {"_id": 0, "id": 1},
        )
        if existing:
            raise HTTPException(409, "هذه الميزة موجودة فعلاً في المشروع.")
        cost = feat["cost"]
        deduct = await db.users.update_one(
            {"id": user["user_id"], "credits": {"$gte": cost}},
            {"$inc": {"credits": -cost},
             "$push": {"credit_history": {
                 "amount": -cost,
                 "reason": f"app_studio_feature_{feat['id']}",
                 "timestamp": _now(),
             }}},
        )
        if deduct.modified_count == 0:
            raise HTTPException(402, f"رصيد غير كافٍ ({cost} نقطة).")
        doc = {
            "id": str(uuid.uuid4()),
            "project_id": payload.project_id,
            "user_id": user["user_id"],
            "feature_id": feat["id"],
            "config": payload.config,
            "cost_paid": cost,
            "created_at": _now(),
        }
        await db.app_project_features.insert_one(doc.copy())
        await db.app_projects.update_one({"id": payload.project_id}, {"$set": {"updated_at": _now()}})
        return {
            "ok": True,
            "feature": {k: v for k, v in doc.items() if k != "_id"},
            "credits_charged": cost,
            "credits_remaining": await _get_credits(user["user_id"]),
        }

    @router.delete("/feature/{feature_db_id}")
    async def remove_feature(feature_db_id: str, user=Depends(get_current_user)):
        # No refund — to deter spam-toggle
        r = await db.app_project_features.delete_one({"id": feature_db_id, "user_id": user["user_id"]})
        return {"ok": True, "deleted": r.deleted_count, "note": "تم الحذف، النقاط لا تُسترجع."}

    # ── Import existing artifacts (FreeBuild site / Mobile app) ────────
    @router.get("/importable")
    async def list_importable(user=Depends(get_current_user)):
        """Return a list of artefacts the user already built on this platform
        that can be imported into an app project as a starting point."""
        importable: List[Dict[str, Any]] = []
        # FreeBuild sites
        try:
            fb_cur = db.spa_websites.find(
                {"user_id": user["user_id"]}, {"_id": 0, "id": 1, "title": 1, "created_at": 1}
            ).sort([("created_at", -1)]).limit(30)
            for s in await fb_cur.to_list(30):
                importable.append({
                    "kind": "freebuild_site",
                    "id": s.get("id"),
                    "label": s.get("title") or "موقع FreeBuild",
                    "created_at": s.get("created_at"),
                    "source": f"freebuild_site:{s.get('id')}",
                })
        except Exception:
            pass
        # Mobile apps
        try:
            mb_cur = db.mobile_apps.find(
                {"user_id": user["user_id"]}, {"_id": 0, "id": 1, "title": 1, "name": 1, "created_at": 1}
            ).sort([("created_at", -1)]).limit(30)
            for m in await mb_cur.to_list(30):
                importable.append({
                    "kind": "mobile_app",
                    "id": m.get("id"),
                    "label": m.get("title") or m.get("name") or "تطبيق سابق",
                    "created_at": m.get("created_at"),
                    "source": f"mobile_app:{m.get('id')}",
                })
        except Exception:
            pass
        return {"ok": True, "items": importable, "count": len(importable)}

    @router.post("/import")
    async def import_existing(payload: ImportExistingIn, user=Depends(get_current_user)):
        proj = await db.app_projects.find_one(
            {"id": payload.project_id, "user_id": user["user_id"]}, {"_id": 0}
        )
        if not proj:
            raise HTTPException(404, "project not found")
        m = re.match(r"^(freebuild_site|mobile_app):(.+)$", payload.source)
        if not m:
            raise HTTPException(400, "source غير صالح. الصيغة: freebuild_site:<id> أو mobile_app:<id>")
        kind, src_id = m.group(1), m.group(2)

        artifact: Optional[Dict[str, Any]] = None
        if kind == "freebuild_site":
            artifact = await db.spa_websites.find_one(
                {"id": src_id, "user_id": user["user_id"]}, {"_id": 0}
            )
        elif kind == "mobile_app":
            artifact = await db.mobile_apps.find_one(
                {"id": src_id, "user_id": user["user_id"]}, {"_id": 0}
            )
        if not artifact:
            raise HTTPException(404, "المحتوى الأصلي غير موجود في حسابك.")

        import_record = {
            "id": str(uuid.uuid4()),
            "kind": kind,
            "source_id": src_id,
            "label": artifact.get("title") or artifact.get("name") or "مستورد",
            # Carry forward the most useful field for re-use
            "html_snapshot": (artifact.get("html") or artifact.get("source") or "")[:200_000],
            "spec_snapshot": artifact.get("spec") or artifact.get("structure") or {},
            "imported_at": _now(),
        }
        await db.app_projects.update_one(
            {"id": payload.project_id},
            {"$push": {"imports": import_record}, "$set": {"updated_at": _now()}},
        )
        await db.app_project_imports.insert_one({
            **import_record,
            "project_id": payload.project_id,
            "user_id": user["user_id"],
        })
        return {
            "ok": True,
            "import": import_record,
            "note": f"تم استيراد {import_record['label']} كنقطة بداية. الذكاء سيستخدم بنيته في توليد التطبيق.",
        }

    # ── AI App Producer (tool-calling, multi-iteration) ───────────────
    @router.post("/producer-chat")
    async def producer_chat(payload: AppProducerChatIn, user=Depends(get_current_user)):
        proj = await db.app_projects.find_one(
            {"id": payload.project_id, "user_id": user["user_id"]}, {"_id": 0}
        )
        if not proj:
            raise HTTPException(404, "project not found")

        # Persistent conversation per project
        conv_id = f"app_studio_{payload.project_id}"
        conv = await db.app_studio_conversations.find_one({"id": conv_id, "user_id": user["user_id"]}, {"_id": 0})
        if not conv:
            conv = {"id": conv_id, "user_id": user["user_id"], "project_id": payload.project_id,
                    "messages": [], "created_at": _now()}
            await db.app_studio_conversations.insert_one(conv.copy())

        # Append user message
        user_msg = (payload.message or "أرشدني").strip()[:4000]
        await db.app_studio_conversations.update_one(
            {"id": conv_id}, {"$push": {"messages": {"role": "user", "content": user_msg, "ts": _now()}}}
        )
        # Reload after push
        conv = await db.app_studio_conversations.find_one({"id": conv_id}, {"_id": 0})

        feats = await db.app_project_features.find(
            {"project_id": payload.project_id}, {"_id": 0}
        ).sort([("created_at", 1)]).to_list(200)

        # ── Pull attachments (images + PDFs) for vision ─────────────
        att_payload = await fetch_recent_for_vision(
            db, payload.project_id, user["user_id"]
        )
        att_system_msg = build_attachment_system_message(att_payload)

        runtime = ToolRuntime(
            db=db, user_id=user["user_id"], project_id=payload.project_id,
            feature_catalog=FEATURE_CATALOG, project_types=PROJECT_TYPES,
            build_fn=build_project,
        )

        sys_prompt = build_system_prompt(proj, feats, FEATURE_CATALOG, PROJECT_TYPES,
                                          attachments_summary=att_system_msg or "")
        history = conv.get("messages", [])[-16:]

        # Try OpenAI gpt-4o first, fallback to Claude via emergent
        direct_key = os.environ.get("OPENAI_DIRECT_KEY", "").strip() or os.environ.get("OPENAI_API_KEY", "").strip()
        emergent_key = os.environ.get("EMERGENT_LLM_KEY", "").strip()

        tool_pills: List[Dict[str, Any]] = []
        final_reply = ""

        if direct_key:
            try:
                from openai import AsyncOpenAI
                client = AsyncOpenAI(api_key=direct_key)
                messages = [{"role": "system", "content": sys_prompt}]
                for m in history:
                    if m.get("role") in ("user", "assistant"):
                        messages.append({"role": m["role"], "content": (m.get("content") or "")[:4000]})

                # Inject vision content blocks on the latest user message
                if att_payload.get("images"):
                    # Find last user message and convert to multimodal content blocks
                    for i in range(len(messages) - 1, -1, -1):
                        if messages[i].get("role") == "user":
                            base_text = messages[i]["content"] if isinstance(messages[i]["content"], str) else ""
                            blocks: List[Dict[str, Any]] = [{"type": "text", "text": base_text}]
                            for img in att_payload["images"]:
                                blocks.append({
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:{img['mime']};base64,{img['b64']}",
                                        "detail": "high",
                                    },
                                })
                            messages[i]["content"] = blocks
                            break

                for _iter in range(6):
                    resp = await client.chat.completions.create(
                        model="gpt-4o",
                        messages=messages,
                        temperature=0.5,
                        max_tokens=1500,
                        tools=APP_STUDIO_TOOLS,
                        tool_choice="auto",
                    )
                    msg = resp.choices[0].message
                    if msg.tool_calls:
                        messages.append({
                            "role": "assistant",
                            "content": msg.content or "",
                            "tool_calls": [
                                {"id": tc.id, "type": "function",
                                 "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                                for tc in msg.tool_calls
                            ],
                        })
                        async def _run(tc):
                            try:
                                args = json.loads(tc.function.arguments or "{}")
                            except Exception:
                                args = {}
                            result = await execute_app_studio_tool(runtime, tc.function.name, args)
                            tool_pills.append({
                                "name": tc.function.name, "args": args, "result": result,
                            })
                            return tc.id, json.dumps(result, ensure_ascii=False)[:8000]
                        pairs = await asyncio.gather(*[_run(tc) for tc in msg.tool_calls])
                        for tid, content in pairs:
                            messages.append({"role": "tool", "tool_call_id": tid, "content": content})
                        continue
                    final_reply = (msg.content or "").strip()
                    break
            except Exception as e:
                logger.warning(f"openai producer-chat failed: {e}")
                final_reply = ""

        # Fallback: Claude via emergent (no native tool-calling here for simplicity)
        if not final_reply and emergent_key:
            try:
                from emergentintegrations.llm.chat import LlmChat, UserMessage
                chat = LlmChat(
                    api_key=emergent_key,
                    session_id=f"app-studio-{payload.project_id[:8]}",
                    system_message=sys_prompt + "\n\nملاحظة: في هذا الوضع لا تستخدم أدوات. أعطِ نصيحة نصية مباشرة.",
                )
                chat.with_model("anthropic", "claude-sonnet-4-5")
                final_reply = await chat.send_message(UserMessage(text=user_msg))
                final_reply = (final_reply or "").strip()
            except Exception as e:
                logger.error(f"claude fallback failed: {e}")

        if not final_reply:
            final_reply = "ما قدرت أرد الحين. تأكّد من مفاتيح الذكاء في `/admin/independence` أو حاول مرة ثانية."

        await db.app_studio_conversations.update_one(
            {"id": conv_id},
            {"$push": {"messages": {
                "role": "assistant", "content": final_reply,
                "tools": tool_pills, "ts": _now(),
            }}, "$set": {"updated_at": _now()}},
        )
        return {
            "ok": True,
            "reply": final_reply,
            "tools": tool_pills,
            "step": payload.step,
            "session_id": conv_id,
        }

    # ── Conversation messages ─────────────────────────────────────────
    @router.get("/conversation/{project_id}")
    async def get_conversation(project_id: str, user=Depends(get_current_user)):
        conv_id = f"app_studio_{project_id}"
        conv = await db.app_studio_conversations.find_one(
            {"id": conv_id, "user_id": user["user_id"]}, {"_id": 0}
        )
        return {"ok": True, "messages": (conv or {}).get("messages", [])}

    @router.delete("/conversation/{project_id}")
    async def reset_conversation(project_id: str, user=Depends(get_current_user)):
        conv_id = f"app_studio_{project_id}"
        r = await db.app_studio_conversations.delete_one(
            {"id": conv_id, "user_id": user["user_id"]}
        )
        return {"ok": True, "deleted": r.deleted_count}

    # ── Build / Preview / Download ────────────────────────────────────
    @router.post("/build/{project_id}")
    async def build_now(project_id: str, user=Depends(get_current_user)):
        proj = await db.app_projects.find_one(
            {"id": project_id, "user_id": user["user_id"]}, {"_id": 0}
        )
        if not proj:
            raise HTTPException(404, "project not found")
        ptype = next((t for t in PROJECT_TYPES if t["id"] == proj.get("type")), None)
        if not ptype:
            raise HTTPException(400, "نوع غير معروف")
        cost = ptype["build_cost"]

        # Owner bypass
        u = await db.users.find_one({"id": user["user_id"]}, {"_id": 0, "credits": 1, "is_owner": 1})
        if not (u or {}).get("is_owner"):
            deduct = await db.users.update_one(
                {"id": user["user_id"], "credits": {"$gte": cost}},
                {"$inc": {"credits": -cost},
                 "$push": {"credit_history": {
                     "amount": -cost,
                     "reason": f"app_studio_build_{project_id}",
                     "timestamp": _now(),
                 }}},
            )
            if deduct.modified_count == 0:
                raise HTTPException(402, f"رصيد غير كافٍ ({cost} نقطة للبناء النهائي).")

        feats = await db.app_project_features.find(
            {"project_id": project_id}, {"_id": 0}
        ).sort([("created_at", 1)]).to_list(200)
        try:
            res = build_project(proj, feats)
        except Exception as e:
            logger.error(f"build failed: {e}", exc_info=True)
            # refund on hard failure
            if not (u or {}).get("is_owner"):
                await db.users.update_one(
                    {"id": user["user_id"]},
                    {"$inc": {"credits": cost},
                     "$push": {"credit_history": {
                         "amount": cost,
                         "reason": f"app_studio_build_refund_{project_id}",
                         "timestamp": _now(),
                     }}},
                )
            raise HTTPException(500, f"فشل البناء: {str(e)[:200]}")

        await db.app_projects.update_one(
            {"id": project_id},
            {"$set": {"stage": "built", "build_output": res, "updated_at": _now()}},
        )
        new_credits = (await db.users.find_one({"id": user["user_id"]}, {"_id": 0, "credits": 1}) or {}).get("credits", 0)
        return {"ok": True, "build": res, "credits_charged": cost, "credits_remaining": new_credits}

    @router.get("/build/{project_id}/{path:path}")
    async def serve_build_file(project_id: str, path: str):
        # Public so the iframe / share-page can fetch the artefact without auth header gymnastics
        bdir = os.path.join(BUILD_ROOT, project_id)
        # Prevent traversal
        if ".." in path or path.startswith("/"):
            raise HTTPException(400, "bad path")
        full = os.path.join(bdir, path)
        if not os.path.isfile(full):
            raise HTTPException(404, "file not found")
        # Sensible MIME guesses
        media = None
        if path.endswith(".html"): media = "text/html; charset=utf-8"
        elif path.endswith(".json"): media = "application/json; charset=utf-8"
        elif path.endswith(".js"): media = "application/javascript; charset=utf-8"
        elif path.endswith(".css"): media = "text/css; charset=utf-8"
        elif path.endswith(".png"): media = "image/png"
        elif path.endswith(".zip"): media = "application/zip"
        elif path.endswith(".md"): media = "text/markdown; charset=utf-8"
        return FileResponse(full, media_type=media)

    # ── Attachments: upload design mockups (images + PDF) ──────────────
    @router.post("/project/{project_id}/upload")
    async def upload_attachment(
        project_id: str,
        files: List[UploadFile] = File(...),
        note: str = Form(""),
        user=Depends(get_current_user),
    ):
        proj = await db.app_projects.find_one(
            {"id": project_id, "user_id": user["user_id"]}, {"_id": 0, "id": 1}
        )
        if not proj:
            raise HTTPException(404, "project not found")
        stored: List[Dict[str, Any]] = []
        errors: List[Dict[str, str]] = []
        for f in (files or [])[:MAX_ATTACHMENTS_PER_PROJECT]:
            try:
                raw = await f.read()
                if not raw:
                    continue
                doc = await store_attachment(
                    db, user_id=user["user_id"], project_id=project_id,
                    filename=f.filename or "file", content_type=f.content_type or "",
                    raw=raw, note=note,
                )
                stored.append(doc)
            except ValueError as ve:
                errors.append({"filename": f.filename or "", "error": str(ve)})
            except Exception as e:
                logger.error(f"upload failed: {e}", exc_info=True)
                errors.append({"filename": f.filename or "", "error": "تعذّر معالجة الملف."})
        return {"ok": True, "stored": stored, "errors": errors}

    @router.get("/project/{project_id}/attachments")
    async def get_attachments(project_id: str, user=Depends(get_current_user)):
        items = await list_attachments(db, project_id, user["user_id"])
        return {"ok": True, "items": items, "count": len(items),
                "max_per_project": MAX_ATTACHMENTS_PER_PROJECT}

    @router.delete("/attachment/{attachment_id}")
    async def remove_attachment(attachment_id: str, user=Depends(get_current_user)):
        deleted = await delete_attachment(db, attachment_id, user["user_id"])
        return {"ok": True, "deleted": deleted}

    @router.get("/attachment/{attachment_id}/raw")
    async def attachment_raw(attachment_id: str, user=Depends(get_current_user)):
        from .attachments import get_attachment_full
        import base64 as _b64
        doc = await get_attachment_full(db, attachment_id, user["user_id"])
        if not doc:
            raise HTTPException(404, "attachment not found")
        if doc.get("kind") == "image" and doc.get("b64"):
            raw = _b64.b64decode(doc["b64"])
            return Response(content=raw, media_type=doc.get("mime") or "image/jpeg")
        if doc.get("kind") == "pdf":
            # We don't keep the binary, only extracted text. Return text instead.
            return JSONResponse({
                "kind": "pdf",
                "filename": doc.get("filename"),
                "text": (doc.get("text") or "")[:30000],
            })
        raise HTTPException(404, "no raw payload")

    # ── AI App Producer (step-by-step wizard) ─────────────────────────
    # legacy alias kept for backward compat: just delegate to producer-chat
    @router.post("/producer-chat-legacy")
    async def producer_chat_legacy(payload: AppProducerChatIn, user=Depends(get_current_user)):
        return await producer_chat(payload, user)  # type: ignore

    return router
