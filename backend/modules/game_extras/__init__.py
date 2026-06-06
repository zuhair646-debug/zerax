"""
🎨 Game Extras — final batch of remaining features
─────────────────────────────────────────────────
  #1  Art Direction Lock (style_dna)
  #4  Batch Approval (approve many at once)
  #5  Auto-Tagging (categorize assets via GPT-4o vision)
  #6  Preview Mode (sandbox iframe)
  #7  Prompt History/Library
  #9  Collaborative Comments
"""
from __future__ import annotations
import os, json, uuid, base64, io
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import logging
import httpx
from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import Response
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class StyleDNA(BaseModel):
    palette: List[str] = Field(default_factory=list)  # hex codes
    lighting: Optional[str] = None
    technique: Optional[str] = None  # 'watercolor' | '3d_low_poly' | 'pixel_art' ...
    perspective: Optional[str] = None  # 'isometric' | 'top_down' | 'side' ...
    notes: Optional[str] = None


class BatchApproval(BaseModel):
    asset_ids: List[str]
    approved: bool = True
    feedback: Optional[str] = None


class CommentCreate(BaseModel):
    asset_id: Optional[str] = None  # if None → project-level comment
    text: str = Field(min_length=1, max_length=2000)
    parent_id: Optional[str] = None  # threading


def create_router(db, get_current_user):
    router = APIRouter(prefix="/api/game-extras", tags=["game-extras"])

    # ────────────────────────────────────────────────────────────
    # #1 Art Direction Lock
    # ────────────────────────────────────────────────────────────
    @router.get("/{project_id}/style-dna")
    async def get_style_dna(project_id: str, user=Depends(get_current_user)):
        p = await db.game_projects.find_one(
            {"id": project_id, "user_id": user["user_id"]}, {"style_dna": 1, "_id": 0}
        )
        if not p:
            raise HTTPException(404, "project not found")
        return {"ok": True, "style_dna": p.get("style_dna") or {}}

    @router.put("/{project_id}/style-dna")
    async def set_style_dna(project_id: str, dna: StyleDNA, user=Depends(get_current_user)):
        r = await db.game_projects.update_one(
            {"id": project_id, "user_id": user["user_id"]},
            {"$set": {"style_dna": dna.model_dump(), "style_dna_updated_at": datetime.now(timezone.utc).isoformat()}},
        )
        if r.matched_count == 0:
            raise HTTPException(404, "project not found")
        return {"ok": True, "style_dna": dna.model_dump()}

    @router.post("/{project_id}/style-dna/auto-detect/{asset_id}")
    async def auto_detect_style_dna(project_id: str, asset_id: str, user=Depends(get_current_user)):
        """Use GPT-4o vision to analyze an approved image and extract its DNA."""
        src = f"/app/backend/uploads/games/{project_id}/assets/{asset_id}.png"
        if not os.path.exists(src):
            raise HTTPException(404, "asset file not found")
        oai = os.environ.get("OPENAI_DIRECT_KEY") or os.environ.get("OPENAI_API_KEY") or ""
        if not oai:
            raise HTTPException(500, "OPENAI_DIRECT_KEY missing")
        try:
            from PIL import Image
            with Image.open(src) as im:
                im = im.convert("RGB")
                if max(im.size) > 768:
                    r = 768 / max(im.size)
                    im = im.resize((int(im.size[0]*r), int(im.size[1]*r)), Image.LANCZOS)
                buf = io.BytesIO(); im.save(buf, format="JPEG", quality=80)
                b64 = base64.b64encode(buf.getvalue()).decode()
        except Exception as e:
            raise HTTPException(500, f"image preprocess: {e}")
        async with httpx.AsyncClient(timeout=60) as c:
            r = await c.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {oai}", "Content-Type": "application/json"},
                json={
                    "model": "gpt-4o-mini",
                    "max_tokens": 400,
                    "response_format": {"type": "json_object"},
                    "messages": [{"role": "user", "content": [
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
                        {"type": "text", "text": (
                            "Analyze this game art image and return ONLY a JSON object: {"
                            '"palette": [3-5 hex codes], '
                            '"lighting": "soft warm" | "harsh" | "golden hour" | ..., '
                            '"technique": "watercolor" | "3d_low_poly" | "pixel_art" | "vector_flat" | "photorealistic" | ..., '
                            '"perspective": "isometric" | "top_down" | "side" | "3/4" | "front", '
                            '"notes": "2-sentence summary of distinctive style"}'
                        )},
                    ]}],
                },
            )
            if r.status_code != 200:
                raise HTTPException(502, f"openai: {r.text[:200]}")
            data = json.loads(r.json()["choices"][0]["message"]["content"])
        await db.game_projects.update_one(
            {"id": project_id},
            {"$set": {"style_dna": data, "style_dna_updated_at": datetime.now(timezone.utc).isoformat()}},
        )
        return {"ok": True, "style_dna": data, "source_asset": asset_id}

    # ────────────────────────────────────────────────────────────
    # #4 Batch Approval
    # ────────────────────────────────────────────────────────────
    @router.post("/{project_id}/batch-approve")
    async def batch_approve(project_id: str, payload: BatchApproval, user=Depends(get_current_user)):
        proj = await db.game_projects.find_one(
            {"id": project_id, "user_id": user["user_id"]}, {"phases": 1, "assets": 1}
        )
        if not proj:
            raise HTTPException(404, "project not found")
        target_ids = set(payload.asset_ids)
        if not target_ids:
            raise HTTPException(400, "asset_ids[] required")
        updated = 0
        ts = datetime.now(timezone.utc).isoformat()
        # Mirror into BOTH storage paths
        phases = proj.get("phases") or {}
        for ph_id, ph in phases.items():
            msgs = ph.get("messages") or []
            dirty = False
            for m in msgs:
                for ga in (m.get("generated_assets") or []):
                    if ga.get("id") in target_ids:
                        ga["approved"] = bool(payload.approved)
                        ga["approval_feedback"] = payload.feedback
                        ga["approval_timestamp"] = ts
                        dirty = True
                        updated += 1
            if dirty:
                msgs.append({
                    "role": "system",
                    "content": f"{'✅ APPROVED' if payload.approved else '↻ REJECTED'} (batch): {len(target_ids)} assets",
                    "ts": ts,
                    "event_type": "batch_approval",
                    "asset_ids": list(target_ids),
                    "approved": bool(payload.approved),
                })
                await db.game_projects.update_one({"id": project_id}, {"$set": {f"phases.{ph_id}.messages": msgs}})
        # Also legacy bucket
        for atype, alist in (proj.get("assets") or {}).items():
            for a in (alist or []):
                if a.get("id") in target_ids:
                    a["approved"] = bool(payload.approved)
                    a["feedback"] = payload.feedback
            await db.game_projects.update_one({"id": project_id}, {"$set": {f"assets.{atype}": alist}})
        return {"ok": True, "updated": updated, "approved": bool(payload.approved)}

    # ────────────────────────────────────────────────────────────
    # #5 Auto-Tagging (GPT-4o categorizes the asset)
    # ────────────────────────────────────────────────────────────
    @router.post("/{project_id}/auto-tag/{asset_id}")
    async def auto_tag(project_id: str, asset_id: str, user=Depends(get_current_user)):
        src = f"/app/backend/uploads/games/{project_id}/assets/{asset_id}.png"
        if not os.path.exists(src):
            raise HTTPException(404, "asset not found")
        oai = os.environ.get("OPENAI_DIRECT_KEY") or os.environ.get("OPENAI_API_KEY") or ""
        if not oai:
            raise HTTPException(500, "OPENAI_DIRECT_KEY missing")
        try:
            from PIL import Image
            with Image.open(src) as im:
                im = im.convert("RGB")
                if max(im.size) > 512:
                    r = 512 / max(im.size); im = im.resize((int(im.size[0]*r), int(im.size[1]*r)), Image.LANCZOS)
                buf = io.BytesIO(); im.save(buf, format="JPEG", quality=78)
                b64 = base64.b64encode(buf.getvalue()).decode()
        except Exception as e:
            raise HTTPException(500, f"preprocess: {e}")
        async with httpx.AsyncClient(timeout=45) as c:
            r = await c.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {oai}", "Content-Type": "application/json"},
                json={
                    "model": "gpt-4o-mini",
                    "max_tokens": 200,
                    "response_format": {"type": "json_object"},
                    "messages": [{"role": "user", "content": [
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
                        {"type": "text", "text": (
                            'Classify this game asset image. Return ONLY JSON: {'
                            '"category": "resource"|"building"|"unit"|"decoration"|"ui"|"character"|"environment"|"item", '
                            '"subcategory": short string, '
                            '"tags": [4-8 short lowercase tags], '
                            '"primary_color_name": short string}'
                        )},
                    ]}],
                },
            )
            if r.status_code != 200:
                raise HTTPException(502, f"openai: {r.text[:200]}")
            tags = json.loads(r.json()["choices"][0]["message"]["content"])
        # Save into messages[].generated_assets
        proj = await db.game_projects.find_one({"id": project_id}, {"phases": 1})
        for ph_id, ph in (proj.get("phases") or {}).items():
            msgs = ph.get("messages") or []
            dirty = False
            for m in msgs:
                for ga in (m.get("generated_assets") or []):
                    if ga.get("id") == asset_id:
                        ga["auto_tags"] = tags
                        dirty = True
            if dirty:
                await db.game_projects.update_one({"id": project_id}, {"$set": {f"phases.{ph_id}.messages": msgs}})
                break
        return {"ok": True, "asset_id": asset_id, "tags": tags}

    @router.get("/{project_id}/assets/by-tag")
    async def list_by_tag(project_id: str, category: Optional[str] = None, tag: Optional[str] = None, user=Depends(get_current_user)):
        proj = await db.game_projects.find_one(
            {"id": project_id, "user_id": user["user_id"]}, {"phases": 1}
        )
        if not proj:
            raise HTTPException(404, "project not found")
        items = []
        for ph_id, ph in (proj.get("phases") or {}).items():
            for m in (ph.get("messages") or []):
                for a in (m.get("generated_assets") or []):
                    t = a.get("auto_tags") or {}
                    if category and t.get("category") != category:
                        continue
                    if tag and tag not in (t.get("tags") or []):
                        continue
                    items.append({
                        "id": a.get("id"), "name": a.get("name"), "image_url": a.get("image_url"),
                        "phase": ph_id, "category": t.get("category"), "subcategory": t.get("subcategory"),
                        "tags": t.get("tags", []), "approved": bool(a.get("approved")),
                    })
        return {"ok": True, "count": len(items), "assets": items}

    # ────────────────────────────────────────────────────────────
    # #6 Preview Mode (sandbox iframe for live builds)
    # ────────────────────────────────────────────────────────────
    @router.get("/{project_id}/preview-sandbox")
    async def preview_sandbox(project_id: str, build_url: str = Query(...)):
        """Returns an HTML wrapper that loads build_url in a sandboxed iframe
        with a test-controls bar so the owner can verify before publishing."""
        if not build_url.startswith("http"):
            raise HTTPException(400, "build_url must be absolute https://")
        html = f"""<!doctype html><html lang=ar dir=rtl><head><meta charset=utf-8>
<title>Preview — {project_id}</title>
<style>
*{{box-sizing:border-box}}body{{margin:0;background:#0d0e14;font-family:system-ui;color:#eee;display:flex;flex-direction:column;height:100vh}}
header{{background:#1c1f2a;padding:10px 18px;border-bottom:1px solid #333;display:flex;align-items:center;gap:14px}}
header h1{{font-size:16px;margin:0;color:#fcd34d}}
header .stat{{font-size:12px;color:#888}}
header button{{background:#fcd34d;color:#000;border:0;padding:7px 14px;border-radius:6px;cursor:pointer;font-weight:700;font-size:13px}}
header button.secondary{{background:#374151;color:#eee}}
iframe{{flex:1;border:0;width:100%;background:#fff}}
</style></head><body>
<header>
  <h1>🎬 معاينة قبل النشر</h1>
  <span class=stat>Project: <code>{project_id}</code></span>
  <span class=stat>Build: <a href="{build_url}" target=_blank style=color:#7dd3fc>{build_url}</a></span>
  <div style="margin-left:auto;display:flex;gap:8px">
    <button onclick="document.getElementById('f').src=document.getElementById('f').src">🔄 إعادة تحميل</button>
    <button class=secondary onclick="window.open('{build_url}','_blank')">🔗 افتح في نافذة جديدة</button>
    <button onclick="if(confirm('انشر هذا البناء؟')) window.parent.postMessage({{type:'publish-build', project_id:'{project_id}', url:'{build_url}'}}, '*')">🚀 انشر</button>
  </div>
</header>
<iframe id=f src="{build_url}" sandbox="allow-scripts allow-same-origin allow-forms allow-popups allow-pointer-lock allow-modals"></iframe>
</body></html>"""
        return Response(content=html, media_type="text/html; charset=utf-8")

    # ────────────────────────────────────────────────────────────
    # #7 Prompt History/Library
    # ────────────────────────────────────────────────────────────
    @router.get("/{project_id}/prompt-history")
    async def prompt_history(project_id: str, user=Depends(get_current_user)):
        proj = await db.game_projects.find_one(
            {"id": project_id, "user_id": user["user_id"]}, {"phases": 1}
        )
        if not proj:
            raise HTTPException(404, "project not found")
        prompts = []
        for ph_id, ph in (proj.get("phases") or {}).items():
            for m in (ph.get("messages") or []):
                for a in (m.get("generated_assets") or []):
                    if a.get("prompt"):
                        prompts.append({
                            "asset_id": a.get("id"),
                            "prompt": a.get("prompt"),
                            "type": a.get("type"),
                            "subtype": a.get("subtype"),
                            "phase": ph_id,
                            "approved": bool(a.get("approved")),
                            "name": a.get("name"),
                            "image_url": a.get("image_url") or a.get("audio_url") or a.get("video_url"),
                            "created_at": a.get("created_at"),
                        })
        # Newest first
        prompts.sort(key=lambda x: x.get("created_at") or "", reverse=True)
        return {"ok": True, "count": len(prompts), "prompts": prompts}

    # ────────────────────────────────────────────────────────────
    # #9 Collaborative Comments
    # ────────────────────────────────────────────────────────────
    @router.post("/{project_id}/comments")
    async def add_comment(project_id: str, payload: CommentCreate, user=Depends(get_current_user)):
        proj = await db.game_projects.find_one({"id": project_id}, {"user_id": 1})
        if not proj:
            raise HTTPException(404, "project not found")
        # Allow project owner + invited collaborators (basic: just owner for now)
        if proj["user_id"] != user["user_id"]:
            raise HTTPException(403, "not your project")
        cid = str(uuid.uuid4())
        doc = {
            "_id": cid,
            "project_id": project_id,
            "asset_id": payload.asset_id,
            "parent_id": payload.parent_id,
            "user_id": user["user_id"],
            "username": user.get("email") or user.get("username") or "user",
            "text": payload.text,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        await db.game_comments.insert_one(doc)
        doc["id"] = doc.pop("_id")
        return {"ok": True, "comment": doc}

    @router.get("/{project_id}/comments")
    async def list_comments(project_id: str, asset_id: Optional[str] = None, user=Depends(get_current_user)):
        q: Dict[str, Any] = {"project_id": project_id}
        if asset_id is not None:
            q["asset_id"] = asset_id
        rows = await db.game_comments.find(q).sort("created_at", 1).to_list(length=500)
        for r in rows:
            r["id"] = r.pop("_id")
        return {"ok": True, "count": len(rows), "comments": rows}

    @router.delete("/{project_id}/comments/{comment_id}")
    async def delete_comment(project_id: str, comment_id: str, user=Depends(get_current_user)):
        r = await db.game_comments.delete_one(
            {"_id": comment_id, "project_id": project_id, "user_id": user["user_id"]}
        )
        if r.deleted_count == 0:
            raise HTTPException(404, "comment not found or not yours")
        return {"ok": True}

    return router
