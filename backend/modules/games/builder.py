"""
🚀 Game / Site Builder — turns a Game-Studio project (GDD + approved assets +
reference images) into a single self-contained HTML bundle and serves it at a
public live URL the owner can share.

Pipeline:
  1. gather_build_context()  → GDD, approved assets, reference images (base64)
  2. _llm_generate_bundle()  → calls Claude Sonnet 4.5 to write index.html
  3. _persist_bundle()       → saves to disk + GridFS for permanence
  4. _update_project()       → stamps `preview_url` so the Live tab works
"""
from __future__ import annotations

import base64
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

BUILD_DIR_ROOT = "/app/backend/uploads/games"
BACKEND_PUBLIC_BASE = os.environ.get("BACKEND_PUBLIC_BASE", "")  # optional override


async def _gather_context(db, project_id: str) -> Optional[Dict[str, Any]]:
    """Collect everything the LLM needs to generate the bundle."""
    proj = await db.game_projects.find_one({"id": project_id})
    if not proj:
        return None
    assets_doc = proj.get("assets") or {}
    approved_imgs: List[Dict[str, Any]] = []
    for bucket in ("images", "models3d", "audio", "videos"):
        for a in assets_doc.get(bucket, []) or []:
            if a.get("approved") and not a.get("deleted_at"):
                approved_imgs.append({
                    "id": a.get("id"),
                    "type": a.get("type"),
                    "name": a.get("name") or (a.get("prompt") or "")[:80],
                    "image_url": a.get("image_url"),
                    "audio_url": a.get("audio_url"),
                    "video_url": a.get("video_url"),
                    "model_url": a.get("model_url"),
                    "cdn_url": a.get("cdn_url"),
                })
    # Reference images uploaded by user (from any phase attachments)
    ref_b64: List[Dict[str, str]] = []
    for ph in (proj.get("phases") or {}).values():
        for m in (ph.get("messages") or [])[-20:]:
            for att in (m.get("attachments") or []):
                fname = (att.get("filename") or "").lower()
                if fname.endswith((".png", ".jpg", ".jpeg", ".webp")) and len(ref_b64) < 4:
                    fpath = att.get("path")
                    if fpath and os.path.exists(fpath):
                        try:
                            with open(fpath, "rb") as fh:
                                data = fh.read()
                            if len(data) < 4_000_000:
                                mime = "image/jpeg" if fname.endswith((".jpg", ".jpeg")) else "image/png"
                                if fname.endswith(".webp"):
                                    mime = "image/webp"
                                ref_b64.append({"mime": mime, "data": base64.b64encode(data).decode()})
                        except Exception:
                            pass
    return {
        "title": proj.get("title") or "لعبة Zenrex",
        "description": proj.get("description") or "",
        "game_type": proj.get("game_type") or "web",
        "programming_type": proj.get("programming_type") or "",
        "ai_notes": (proj.get("ai_notes") or "")[:5000],
        "approved_assets": approved_imgs,
        "reference_images_b64": ref_b64,
    }


def _build_prompt(ctx: Dict[str, Any]) -> str:
    """Construct the master generation prompt for Claude."""
    assets_md = "\n".join([
        f"- ({a['type']}) {a['name']} → {a.get('image_url') or a.get('audio_url') or a.get('video_url') or a.get('model_url')}"
        for a in (ctx.get("approved_assets") or [])
    ]) or "(لا توجد أصول معتمدة بعد — استخدم placeholders أنيقة من نفس الـ palette)"
    return (
        "أنت معماري ويب من الطراز الأول. مهمتك توليد ملف HTML واحد متكامل "
        "(self-contained) يطبّق فكرة لعبة المالك على الـ Live Web.\n\n"
        "═══ متطلبات إلزامية ═══\n"
        "1. أخرج HTML واحد فقط (لا تكتب markdown، لا تعليقات قبل/بعد الكود).\n"
        "2. CSS و JavaScript مضمّنين داخل نفس الملف (لا ملفات منفصلة).\n"
        "3. RTL Arabic عند الحاجة. استخدم Tailwind via CDN (script tag) لسرعة التنسيق.\n"
        "4. التصميم لازم يطابق الصور المرجعية إذا موجودة (palette، style، mood) — مو generic.\n"
        "5. استخدم روابط الأصول المعتمدة (image_url) مباشرة كـ <img src=…>.\n"
        "6. اللعبة/الصفحة لازم تكون قابلة للتشغيل في المتصفح فوراً، responsive، تعمل على mobile + desktop.\n"
        "7. لو اللعبة 3D استخدم Three.js عبر CDN (esm import).\n"
        "8. أرقام البدء جميعها = 0 (لا تخترع أرقام للموارد/النقاط).\n"
        "9. أضف header بسيط فيه اسم اللعبة + شعار صغير بنفس الأسلوب البصري.\n"
        "10. الحد الأقصى ~4000 سطر. أعط الأولوية للجودة المرئية والحركة (animations) لا الكمية.\n\n"
        f"═══ معلومات المشروع ═══\n"
        f"العنوان: {ctx['title']}\n"
        f"النوع: {ctx['game_type']} | التقنية المختارة: {ctx['programming_type']}\n"
        f"الوصف: {ctx['description']}\n\n"
        f"═══ ذاكرة الـ AI / GDD ═══\n{ctx['ai_notes'] or '(لم تُلخّص بعد)'}\n\n"
        f"═══ الأصول المعتمدة ═══\n{assets_md}\n\n"
        "═══ التعليمات النهائية ═══\n"
        "ابدأ مباشرة بـ `<!DOCTYPE html>` وانتهي بـ `</html>`. لا تكتب أي شيء آخر."
    )


def _strip_code_fence(text: str) -> str:
    t = (text or "").strip()
    if t.startswith("```"):
        # remove leading ``` or ```html
        first_nl = t.find("\n")
        if first_nl > 0:
            t = t[first_nl + 1:]
    if t.endswith("```"):
        t = t[: -3]
    return t.strip()


async def _llm_generate_bundle(ctx: Dict[str, Any]) -> Optional[str]:
    """Call Claude (preferred) or Gemini (fallback) and return raw HTML."""
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY", "")
    gemini_key = os.environ.get("GEMINI_API_KEY", "")
    prompt_text = _build_prompt(ctx)

    # ── Try Claude first (best for long, structured HTML) ──────────────
    if anthropic_key:
        try:
            content_parts: List[Dict[str, Any]] = []
            for ref in (ctx.get("reference_images_b64") or [])[:4]:
                content_parts.append({
                    "type": "image",
                    "source": {"type": "base64", "media_type": ref["mime"], "data": ref["data"]},
                })
            content_parts.append({"type": "text", "text": prompt_text})
            async with httpx.AsyncClient(timeout=180.0) as cli:
                r = await cli.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={
                        "x-api-key": anthropic_key,
                        "anthropic-version": "2023-06-01",
                        "content-type": "application/json",
                    },
                    json={
                        "model": "claude-sonnet-4-5-20250929",
                        "max_tokens": 16000,
                        "messages": [{"role": "user", "content": content_parts}],
                    },
                )
                if r.status_code == 200:
                    blocks = r.json().get("content", [])
                    txt = "".join(b.get("text", "") for b in blocks if b.get("type") == "text")
                    html = _strip_code_fence(txt)
                    if "<html" in html.lower() and "</html>" in html.lower():
                        return html
                else:
                    logger.warning(f"[builder] claude http {r.status_code}: {r.text[:300]}")
        except Exception as e:
            logger.warning(f"[builder] claude call failed: {e}")

    # ── Gemini fallback ────────────────────────────────────────────────
    if gemini_key:
        try:
            parts: List[Dict[str, Any]] = []
            for ref in (ctx.get("reference_images_b64") or [])[:4]:
                parts.append({"inline_data": {"mime_type": ref["mime"], "data": ref["data"]}})
            parts.append({"text": prompt_text})
            async with httpx.AsyncClient(timeout=180.0) as cli:
                r = await cli.post(
                    f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-pro:generateContent?key={gemini_key}",
                    json={
                        "contents": [{"parts": parts}],
                        "generationConfig": {"temperature": 0.5, "maxOutputTokens": 16000},
                    },
                )
                if r.status_code == 200:
                    txt = (
                        r.json().get("candidates", [{}])[0]
                        .get("content", {}).get("parts", [{}])[0]
                        .get("text", "")
                    )
                    html = _strip_code_fence(txt)
                    if "<html" in html.lower() and "</html>" in html.lower():
                        return html
                else:
                    logger.warning(f"[builder] gemini http {r.status_code}: {r.text[:300]}")
        except Exception as e:
            logger.warning(f"[builder] gemini call failed: {e}")
    return None


async def _persist_bundle(db, project_id: str, html: str) -> str:
    """Save the bundle to disk + GridFS. Returns the local file path."""
    build_dir = f"{BUILD_DIR_ROOT}/{project_id}/build"
    os.makedirs(build_dir, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    versioned_path = f"{build_dir}/v_{timestamp}.html"
    current_path = f"{build_dir}/index.html"
    with open(versioned_path, "w", encoding="utf-8") as fh:
        fh.write(html)
    with open(current_path, "w", encoding="utf-8") as fh:
        fh.write(html)
    # Persist into GridFS so the bundle survives container redeploys
    try:
        from modules.games.persistence import persist_bytes as _persist
        await _persist(db, f"build_{project_id}_index", html.encode("utf-8"), "text/html; charset=utf-8", project_id)
    except Exception as pe:
        logger.warning(f"[builder] GridFS persist failed: {pe}")
    return current_path


async def build_and_deploy(db, project_id: str, requester_id: str) -> Dict[str, Any]:
    """Public entry point — gather, generate, persist, stamp URL."""
    ctx = await _gather_context(db, project_id)
    if not ctx:
        return {"ok": False, "error": "project not found"}
    logger.info(f"[builder] building project={project_id} | assets={len(ctx['approved_assets'])} | refs={len(ctx['reference_images_b64'])}")
    html = await _llm_generate_bundle(ctx)
    if not html:
        return {"ok": False, "error": "LLM build failed — please retry"}
    await _persist_bundle(db, project_id, html)
    # Build the public URL. /games-live/{id}/ is mounted at app level (no /api prefix)
    base = BACKEND_PUBLIC_BASE or os.environ.get("REACT_APP_BACKEND_URL", "")
    preview_url = f"/api/games/games-live/{project_id}/"  # router prefix `/api/games` + route `/games-live/{id}/`
    await db.game_projects.update_one(
        {"id": project_id},
        {"$set": {
            "preview_url": preview_url,
            "last_built_at": datetime.now(timezone.utc).isoformat(),
            "build_size_bytes": len(html.encode("utf-8")),
        }},
    )
    return {
        "ok": True,
        "preview_url": preview_url,
        "absolute_url": f"{base}{preview_url}" if base else preview_url,
        "size_bytes": len(html.encode("utf-8")),
        "built_at": datetime.now(timezone.utc).isoformat(),
    }


async def load_bundle_html(db, project_id: str) -> Optional[str]:
    """Local → GridFS lookup for the built bundle."""
    local = f"{BUILD_DIR_ROOT}/{project_id}/build/index.html"
    if os.path.exists(local):
        try:
            with open(local, "r", encoding="utf-8") as fh:
                return fh.read()
        except Exception:
            pass
    try:
        from modules.games.persistence import load_bytes as _load
        data = await _load(db, f"build_{project_id}_index")
        if data:
            # repopulate local cache
            os.makedirs(os.path.dirname(local), exist_ok=True)
            with open(local, "wb") as fh:
                fh.write(data)
            return data.decode("utf-8", errors="replace")
    except Exception as e:
        logger.warning(f"[builder] load_bundle gridfs failed: {e}")
    return None
