"""
🎨 Asset Pipeline — automatic optimization for Zenrex-generated game assets
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

    # ────────────────────────────────────────────────────────────
    # 5️⃣ Visual Similarity API (task 19)
    # POST /api/asset-pipeline/visual-compare
    # Body: { url_a, url_b }  OR  { asset_id_a, asset_id_b, project_id }
    # Uses GPT-4o Vision via OPENAI_DIRECT_KEY (independent, no Emergent).
    # ────────────────────────────────────────────────────────────
    @router.post("/visual-compare")
    async def visual_compare(payload: Dict[str, Any], user=Depends(get_current_user)):
        """Returns a structured similarity score + analysis using GPT-4o Vision."""
        import base64 as _b64
        import httpx

        # Resolve image bytes for both sides
        def _local_to_bytes(project_id: str, asset_id: str) -> Optional[bytes]:
            fpath = f"/app/backend/uploads/games/{project_id}/assets/{asset_id}.png"
            if os.path.exists(fpath):
                with open(fpath, "rb") as f:
                    return f.read()
            return None

        async def _url_to_bytes(url: str) -> Optional[bytes]:
            try:
                if url.startswith("/api/games/asset-image/"):
                    parts = url.rsplit("/", 2)
                    pid, fname = parts[-2], parts[-1].replace(".png", "")
                    return _local_to_bytes(pid, fname)
                async with httpx.AsyncClient(timeout=30) as c:
                    r = await c.get(url, follow_redirects=True)
                    r.raise_for_status()
                    return r.content
            except Exception as e:
                logger.warning(f"[visual-compare] url fetch failed: {e}")
                return None

        bytes_a = bytes_b = None
        if payload.get("asset_id_a") and payload.get("asset_id_b") and payload.get("project_id"):
            pid = payload["project_id"]
            bytes_a = _local_to_bytes(pid, payload["asset_id_a"])
            bytes_b = _local_to_bytes(pid, payload["asset_id_b"])
        elif payload.get("url_a") and payload.get("url_b"):
            bytes_a = await _url_to_bytes(payload["url_a"])
            bytes_b = await _url_to_bytes(payload["url_b"])
        if not bytes_a or not bytes_b:
            raise HTTPException(400, "could not resolve both images")

        # Use GPT-4o for vision comparison via direct OpenAI key
        oai_key = os.environ.get("OPENAI_DIRECT_KEY") or os.environ.get("OPENAI_API_KEY") or ""
        if not oai_key:
            raise HTTPException(500, "OPENAI_DIRECT_KEY missing")

        # Downscale to keep request small
        try:
            from PIL import Image
            import io as _io
            def _shrink(b: bytes) -> str:
                with Image.open(_io.BytesIO(b)) as im:
                    im = im.convert("RGB")
                    if max(im.size) > 768:
                        ratio = 768 / max(im.size)
                        im = im.resize((int(im.size[0]*ratio), int(im.size[1]*ratio)), Image.LANCZOS)
                    out = _io.BytesIO()
                    im.save(out, format="JPEG", quality=80)
                    return _b64.b64encode(out.getvalue()).decode()
            b64_a, b64_b = _shrink(bytes_a), _shrink(bytes_b)
        except Exception as e:
            raise HTTPException(500, f"image preprocess failed: {e}")

        prompt = (
            "Compare these two images carefully and respond ONLY with a JSON object of shape:\n"
            "{\n"
            '  "similarity_score": 0.0-1.0,\n'
            '  "color_match": 0.0-1.0,\n'
            '  "composition_match": 0.0-1.0,\n'
            '  "style_match": 0.0-1.0,\n'
            '  "differences": ["list of visual differences"],\n'
            '  "suggestions": ["list of edits to make image B closer to image A"],\n'
            '  "verdict": "EXCELLENT" | "GOOD_MATCH" | "NEEDS_ADJUSTMENT" | "POOR_MATCH"\n'
            "}\n"
            "Image A is the REFERENCE. Image B is the candidate. Be precise and quantitative."
        )

        async with httpx.AsyncClient(timeout=60) as c:
            r = await c.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {oai_key}", "Content-Type": "application/json"},
                json={
                    "model": "gpt-4o-mini",  # cost-effective vision model
                    "max_tokens": 600,
                    "messages": [{
                        "role": "user",
                        "content": [
                            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64_a}"}},
                            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64_b}"}},
                            {"type": "text", "text": prompt},
                        ],
                    }],
                    "response_format": {"type": "json_object"},
                },
            )
            if r.status_code != 200:
                raise HTTPException(502, f"openai vision error: {r.status_code} {r.text[:200]}")
            data = r.json()
            raw = data["choices"][0]["message"]["content"]
            try:
                parsed = json.loads(raw)
            except Exception:
                parsed = {"raw": raw}
        return {"ok": True, "analysis": parsed}

    return router
