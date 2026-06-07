"""FreeBuild Chat — conversational website builder with memory + asset approval flow.

Mirrors the Game Studio pattern: project → chat → tag-driven asset generation → approval.
"""
from __future__ import annotations
import os
import re
import uuid
import logging
import asyncio
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, Form
from pydantic import BaseModel

logger = logging.getLogger(__name__)

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


def _strip_tags(text: str) -> str:
    """Remove <<TAG: ...>> markers from displayed text and collapse blank lines."""
    cleaned = TAG_RE.sub("", text)
    # Collapse 3+ consecutive newlines to 2
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


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

    # ===== Chat (the core flow — like games) =====
    @router.post("/project/{pid}/chat")
    async def chat(pid: str, payload: ChatIn, user=Depends(get_current_user)):
        proj = await db.freebuild_projects.find_one(
            {"id": pid, "user_id": user["user_id"]}, {"_id": 0}
        )
        if not proj:
            raise HTTPException(404, "المشروع غير موجود")

        # Build memory: approved assets summary moved below with URLs
        # Build conversation history (last 12 turns)
        history = proj.get("messages", [])[-12:]
        msg_list = [{"role": m["role"], "content": m["content"]} for m in history]
        msg_list.append({"role": "user", "content": payload.message})

        # Context for the agent (no website type — fully open / from scratch)
        # List of approved assets with URLs so the AI can reference them
        assets_for_use = ""
        if proj.get("approved_assets"):
            assets_for_use = "\n\n🖼️ صور جاهزة معتمدة (استخدمها مباشرة بالـ URL):\n"
            for a in proj["approved_assets"][-15:]:
                if a.get("image_url"):
                    assets_for_use += f'  • {a["type"]}: "{a["prompt"][:50]}" → {a["image_url"]}\n'

        extra_ctx = (
            f"اسم المشروع: {proj['name']}\n"
            f"وصف المشروع: {proj['description'] or '(لم يحدد العميل وصفاً بعد — اسأله ودَوّن)'}\n"
            f"{assets_for_use}\n"
            "📌 بروتوكول الإنشاء من الصفر (مهم جداً):\n"
            "1. ابدأ بالاستماع — اسأل العميل عن: نشاطه/فكرته، جمهوره المستهدف، الإحساس المطلوب، أمثلة ملهمة.\n"
            "2. اقترح 2-3 اتجاهات تصميم مختلفة (ألوان/typography/تخطيط) قبل ما تنفذ شي.\n"
            "3. لما يختار اتجاه، نفّذ بإصدار صغير (Hero فقط) واستشره قبل بناء الباقي.\n"
            "4. لما تحتاج صورة، اكتبها بصيغة تاق فقط (لا تضعها داخل HTML):\n"
            "   <<HERO: english description>>  أو  <<LOGO: brand>>  أو  <<BANNER_AR: نص>>  أو  <<ICON: ...>>\n"
            "   النظام راح يولّدها تلقائياً ويعرضها للمستخدم لاعتمادها.\n"
            "5. بعد ما المستخدم يعتمد الصور (تشوفها في 'صور جاهزة معتمدة' أعلاه)، استخدم URL مباشر في الـ HTML.\n"
            "6. لما تكتب HTML للمعاينة، اكتبه داخل ```html ... ``` ويكون <!DOCTYPE html>...</html> كامل مع Tailwind CDN و RTL.\n"
            "7. عدّل تدريجياً — لا تعيد بناء كل شي من جديد كل مرة.\n"
        )

        try:
            from modules.zitex_ai import zitex_chat
            result = await zitex_chat(
                agent="freebuild",
                messages=msg_list,
                user_id=user["user_id"],
                extra_context=extra_ctx,
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

        # Detect HTML for live preview
        new_html = _extract_html(ai_text)
        clean_text = _strip_tags(ai_text)

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
                            {"role": "user", "content": payload.message, "timestamp": _now(), "pending_assets": []},
                            {"role": "assistant", "content": clean_text, "timestamp": _now(), "pending_assets": pending_assets, "had_html": bool(new_html)},
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
