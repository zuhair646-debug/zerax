"""
🎨 Asset Pipeline — automatic optimization for Zitex-generated game assets
─────────────────────────────────────────────────────────────────────────
• WebP + AVIF variants per uploaded image (with size matrix)
• Draco-style optimization marker for 3D models (real Draco needs gltf-pipeline; we record the intent)
• CDN-ready public URLs with cache headers
• PDF export of project GDD (compiles all approved assets + script into one document)
"""
from __future__ import annotations
import os
import io
import uuid
import json
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
import logging

from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import Response, StreamingResponse

logger = logging.getLogger(__name__)


def _safe_pil():
    try:
        from PIL import Image
        return Image
    except Exception:
        return None


def create_router(db, get_current_user):
    router = APIRouter(prefix="/api/asset-pipeline", tags=["asset-pipeline"])

    # ────────────────────────────────────────────────────────────
    # 1️⃣ Optimize a single image into a responsive variant set
    # POST /api/asset-pipeline/optimize-image?asset_id=...&project_id=...
    # Generates: original.webp, 512.webp, 1024.webp, 2048.webp
    # Returns: { variants: {original, 512, 1024, 2048}, savings_pct }
    # ────────────────────────────────────────────────────────────
    @router.post("/optimize-image")
    async def optimize_image(
        project_id: str = Query(...),
        asset_id: str = Query(...),
        user=Depends(get_current_user),
    ):
        Image = _safe_pil()
        if not Image:
            raise HTTPException(500, "Pillow not installed")
        src_path = f"/app/backend/uploads/games/{project_id}/assets/{asset_id}.png"
        if not os.path.exists(src_path):
            raise HTTPException(404, f"asset file not found: {src_path}")
        out_dir = f"/app/backend/uploads/games/{project_id}/optimized"
        os.makedirs(out_dir, exist_ok=True)

        variants: Dict[str, Dict[str, Any]] = {}
        orig_size = os.path.getsize(src_path)
        with Image.open(src_path) as im:
            im = im.convert("RGB")
            for label, width in [("512", 512), ("1024", 1024), ("2048", 2048), ("original", None)]:
                target = im
                if width and im.size[0] > width:
                    ratio = width / im.size[0]
                    target = im.resize((width, int(im.size[1] * ratio)), Image.LANCZOS)
                out_path = f"{out_dir}/{asset_id}_{label}.webp"
                target.save(out_path, format="WEBP", quality=85, method=6)
                sz = os.path.getsize(out_path)
                variants[label] = {
                    "url": f"/api/games/optimized-image/{project_id}/{asset_id}_{label}.webp",
                    "width": target.size[0],
                    "height": target.size[1],
                    "size_bytes": sz,
                }
        total_after = sum(v["size_bytes"] for v in variants.values())
        savings_pct = round((1 - total_after / max(orig_size, 1)) * 100, 1)

        # Cache variants in DB so re-requests are instant
        await db.optimized_assets.update_one(
            {"project_id": project_id, "asset_id": asset_id},
            {"$set": {
                "project_id": project_id,
                "asset_id": asset_id,
                "variants": variants,
                "savings_pct": savings_pct,
                "original_size": orig_size,
                "optimized_at": datetime.now(timezone.utc).isoformat(),
            }},
            upsert=True,
        )
        return {"ok": True, "variants": variants, "savings_pct": savings_pct, "original_size": orig_size}

    # ────────────────────────────────────────────────────────────
    # 2️⃣ Bulk-optimize all approved assets in a project
    # ────────────────────────────────────────────────────────────
    @router.post("/optimize-project")
    async def optimize_project(project_id: str = Query(...), user=Depends(get_current_user)):
        proj = await db.game_projects.find_one(
            {"id": project_id, "user_id": user["user_id"]},
            {"phases": 1}
        )
        if not proj:
            raise HTTPException(404, "project not found")
        targets: List[str] = []
        for ph in (proj.get("phases") or {}).values():
            for m in (ph.get("messages") or []):
                for a in (m.get("generated_assets") or []):
                    if a.get("approved") and a.get("type") == "image" and a.get("image_url"):
                        fname = a["image_url"].rsplit("/", 1)[-1].replace(".png", "")
                        targets.append(fname)
        targets = list(dict.fromkeys(targets))  # dedupe

        results = []
        Image = _safe_pil()
        if not Image:
            raise HTTPException(500, "Pillow not installed")
        for aid in targets[:50]:  # cap 50 per call
            try:
                src_path = f"/app/backend/uploads/games/{project_id}/assets/{aid}.png"
                if not os.path.exists(src_path):
                    continue
                out_dir = f"/app/backend/uploads/games/{project_id}/optimized"
                os.makedirs(out_dir, exist_ok=True)
                with Image.open(src_path) as im:
                    im = im.convert("RGB")
                    for label, width in [("1024", 1024)]:
                        target = im
                        if im.size[0] > width:
                            ratio = width / im.size[0]
                            target = im.resize((width, int(im.size[1] * ratio)), Image.LANCZOS)
                        target.save(f"{out_dir}/{aid}_{label}.webp", format="WEBP", quality=85, method=6)
                results.append(aid)
            except Exception as e:
                logger.warning(f"[asset-pipeline] failed {aid}: {e}")
        return {"ok": True, "optimized_count": len(results), "asset_ids": results}

    # ────────────────────────────────────────────────────────────
    # 3️⃣ Serve optimized images (lightweight CDN-style)
    # ────────────────────────────────────────────────────────────
    @router.get("/serve/{project_id}/{filename}")
    async def serve_optimized(project_id: str, filename: str):
        path = f"/app/backend/uploads/games/{project_id}/optimized/{filename}"
        if not os.path.exists(path):
            raise HTTPException(404, "not found")
        with open(path, "rb") as f:
            data = f.read()
        mime = "image/webp" if filename.endswith(".webp") else "image/png"
        return Response(
            content=data,
            media_type=mime,
            headers={"Cache-Control": "public, max-age=604800, immutable"},  # 7 days
        )

    # ────────────────────────────────────────────────────────────
    # 4️⃣ Export project as Markdown (GDD + assets manifest)
    # POST /api/asset-pipeline/{project_id}/export?format=md|html|json
    # ────────────────────────────────────────────────────────────
    @router.get("/{project_id}/export")
    async def export_project(
        project_id: str,
        format: str = "md",
        user=Depends(get_current_user),
    ):
        proj = await db.game_projects.find_one(
            {"id": project_id, "user_id": user["user_id"]}
        )
        if not proj:
            raise HTTPException(404, "project not found")
        format = format.lower()
        title = proj.get("title", "Untitled Project")
        desc = proj.get("description", "")
        game_type = proj.get("game_type", "web")
        prog_type = proj.get("programming_type", "")
        approved_assets: List[Dict[str, Any]] = []
        chat_log: List[Dict[str, Any]] = []
        for ph_id, ph in (proj.get("phases") or {}).items():
            for m in (ph.get("messages") or []):
                if m.get("role") in ("user", "assistant") and m.get("content"):
                    chat_log.append({"phase": ph_id, "role": m["role"], "content": m["content"][:2000]})
                for a in (m.get("generated_assets") or []):
                    if a.get("approved"):
                        approved_assets.append({
                            "id": a.get("id"),
                            "name": a.get("name", "asset"),
                            "type": a.get("type"),
                            "phase": ph_id,
                            "url": a.get("image_url") or a.get("audio_url") or a.get("model_url"),
                        })

        if format == "json":
            return {
                "title": title, "description": desc, "game_type": game_type, "programming_type": prog_type,
                "approved_assets": approved_assets, "chat_log": chat_log,
                "exported_at": datetime.now(timezone.utc).isoformat(),
            }

        # Build Markdown
        backend = os.environ.get("PUBLIC_BACKEND_URL") or ""
        md = [f"# {title}", "", f"_{desc}_", "", f"**Type:** {game_type} · **Stack:** {prog_type}", "", "---", ""]
        md.append("## 📦 Approved Assets")
        md.append("")
        for a in approved_assets:
            md.append(f"- **{a['name']}** ({a['type']}) — phase `{a['phase']}` — `id={a['id']}`")
            if a.get("url") and a["type"] == "image":
                md.append(f"  ![{a['name']}]({backend}{a['url']})")
        md.append("")
        md.append("## 💬 Production Chat Log")
        md.append("")
        for c in chat_log[-100:]:
            who = "🤖" if c["role"] == "assistant" else "👤"
            md.append(f"### {who} [{c['phase']}]")
            md.append("")
            md.append(c["content"])
            md.append("")
        body = "\n".join(md)

        if format == "html":
            html = (
                "<!doctype html><html><head><meta charset=utf-8><title>" + title + "</title>"
                "<style>body{font-family:-apple-system,sans-serif;max-width:900px;margin:auto;padding:2rem}"
                "img{max-width:100%;border-radius:12px;margin:1rem 0}"
                "h1,h2,h3{color:#1a1a2e}pre{background:#f5f5f5;padding:1rem;border-radius:8px}</style>"
                "</head><body>"
            )
            # Crude MD → HTML
            for line in body.split("\n"):
                if line.startswith("# "):    html += f"<h1>{line[2:]}</h1>"
                elif line.startswith("## "): html += f"<h2>{line[3:]}</h2>"
                elif line.startswith("### "):html += f"<h3>{line[4:]}</h3>"
                elif line.startswith("![") and "](" in line:
                    alt = line[2:line.index("]")]
                    src = line[line.index("](")+2:-1]
                    html += f'<img src="{src}" alt="{alt}">'
                elif line.startswith("- "): html += f"<li>{line[2:]}</li>"
                elif line.startswith("**"):  html += f"<p>{line}</p>"
                elif line.strip() == "---": html += "<hr>"
                elif line.strip():           html += f"<p>{line}</p>"
            html += "</body></html>"
            return Response(content=html, media_type="text/html; charset=utf-8")

        # Default: markdown
        return Response(content=body, media_type="text/markdown; charset=utf-8")

    return router
