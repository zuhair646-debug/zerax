"""
App Studio — Attachments (Multimodal Input)
Accepts user-uploaded design references (images + PDFs) so the AI Producer
can faithfully reproduce the client's mockups.

Pipeline:
  1. POST /api/app-studio/project/{pid}/upload   (multipart)
       → stores compressed image base64 or extracted PDF text in
         `app_studio_attachments` collection.
  2. Producer chat fetches the latest N attachments and includes them
     in the GPT-4o vision payload (images as image_url, PDFs as text).
  3. AI tool `analyze_uploaded_designs()` produces a structured design brief
     (palette, screen list, layout style) saved on the project. The build
     engine reads this brief and renders the PWA to match.
"""
from __future__ import annotations
import os
import io
import re
import uuid
import base64
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Caps to avoid token-blowups
MAX_IMAGE_BYTES = 4 * 1024 * 1024          # 4 MB per file
MAX_PDF_BYTES = 12 * 1024 * 1024           # 12 MB per file
MAX_IMAGE_SIDE = 1600                       # px — downsize before storage
MAX_PDF_CHARS = 30_000                      # truncation
MAX_ATTACHMENTS_PER_PROJECT = 12


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _compress_image(raw: bytes, mime: str) -> Tuple[bytes, str]:
    """Re-encode image to ≤ MAX_IMAGE_SIDE on long edge, JPEG q=82.
    Returns (bytes, mime)."""
    try:
        from PIL import Image
        img = Image.open(io.BytesIO(raw))
        if img.mode in ("RGBA", "LA", "P"):
            bg = Image.new("RGB", img.size, (255, 255, 255))
            try:
                bg.paste(img, mask=img.split()[-1])
            except Exception:
                bg.paste(img.convert("RGB"))
            img = bg
        elif img.mode != "RGB":
            img = img.convert("RGB")
        w, h = img.size
        m = max(w, h)
        if m > MAX_IMAGE_SIDE:
            scale = MAX_IMAGE_SIDE / float(m)
            img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
        out = io.BytesIO()
        img.save(out, "JPEG", quality=82, optimize=True)
        return out.getvalue(), "image/jpeg"
    except Exception as e:
        logger.warning(f"image compress failed, keeping original: {e}")
        return raw, mime or "image/png"


def _extract_pdf_text(raw: bytes) -> str:
    try:
        import pypdf
        reader = pypdf.PdfReader(io.BytesIO(raw))
        parts: List[str] = []
        for i, page in enumerate(reader.pages[:50]):  # first 50 pages
            try:
                parts.append(page.extract_text() or "")
            except Exception:
                continue
            if sum(len(p) for p in parts) > MAX_PDF_CHARS:
                break
        text = "\n\n".join(parts).strip()
        # Collapse whitespace
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r"[ \t]{2,}", " ", text)
        return text[:MAX_PDF_CHARS]
    except Exception as e:
        logger.warning(f"pdf extract failed: {e}")
        return ""


async def store_attachment(db, *, user_id: str, project_id: str,
                           filename: str, content_type: str, raw: bytes,
                           note: str = "") -> Dict[str, Any]:
    """Persist a single uploaded attachment.

    Returns the attachment doc (without `_id`).
    """
    size = len(raw)
    kind: Optional[str] = None
    payload: Dict[str, Any] = {}

    ct = (content_type or "").lower()
    if ct.startswith("image/") or filename.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
        if size > MAX_IMAGE_BYTES:
            raise ValueError(f"الصورة كبيرة جداً ({size} bytes). الحد {MAX_IMAGE_BYTES // 1024//1024}MB.")
        kind = "image"
        compressed, mime = _compress_image(raw, ct or "image/png")
        payload["b64"] = base64.b64encode(compressed).decode("ascii")
        payload["mime"] = mime
        payload["bytes_stored"] = len(compressed)
    elif ct == "application/pdf" or filename.lower().endswith(".pdf"):
        if size > MAX_PDF_BYTES:
            raise ValueError(f"ملف PDF كبير جداً ({size} bytes). الحد {MAX_PDF_BYTES // 1024//1024}MB.")
        kind = "pdf"
        text = _extract_pdf_text(raw)
        payload["text"] = text
        payload["bytes_original"] = size
    else:
        raise ValueError(f"نوع الملف غير مدعوم: {content_type}. مسموح: PNG/JPG/WEBP/PDF.")

    # Enforce per-project cap (oldest gets pruned)
    existing = await db.app_studio_attachments.count_documents({"project_id": project_id})
    if existing >= MAX_ATTACHMENTS_PER_PROJECT:
        oldest = await db.app_studio_attachments.find(
            {"project_id": project_id}, {"_id": 0, "id": 1}
        ).sort([("created_at", 1)]).limit(existing - MAX_ATTACHMENTS_PER_PROJECT + 1).to_list(50)
        if oldest:
            await db.app_studio_attachments.delete_many(
                {"id": {"$in": [o["id"] for o in oldest]}}
            )

    doc = {
        "id": uuid.uuid4().hex,
        "user_id": user_id,
        "project_id": project_id,
        "kind": kind,
        "filename": filename[:200],
        "content_type": payload.get("mime", content_type or ""),
        "note": (note or "")[:1000],
        "size": size,
        "created_at": _now(),
        **payload,
    }
    await db.app_studio_attachments.insert_one(doc.copy())
    # Strip heavy fields before returning to client
    return _safe_view(doc)


def _safe_view(doc: Dict[str, Any]) -> Dict[str, Any]:
    out = {k: v for k, v in doc.items() if k not in ("_id", "b64", "text")}
    if doc.get("kind") == "image":
        out["has_image"] = True
    if doc.get("kind") == "pdf":
        out["pdf_chars"] = len(doc.get("text") or "")
    return out


async def list_attachments(db, project_id: str, user_id: str) -> List[Dict[str, Any]]:
    cur = db.app_studio_attachments.find(
        {"project_id": project_id, "user_id": user_id}, {"_id": 0}
    ).sort([("created_at", -1)])
    items = await cur.to_list(MAX_ATTACHMENTS_PER_PROJECT * 2)
    return [_safe_view(it) for it in items]


async def delete_attachment(db, attachment_id: str, user_id: str) -> int:
    r = await db.app_studio_attachments.delete_one(
        {"id": attachment_id, "user_id": user_id}
    )
    return r.deleted_count


async def get_attachment_full(db, attachment_id: str, user_id: str) -> Optional[Dict[str, Any]]:
    return await db.app_studio_attachments.find_one(
        {"id": attachment_id, "user_id": user_id}, {"_id": 0}
    )


async def fetch_recent_for_vision(db, project_id: str, user_id: str,
                                  limit_images: int = 6,
                                  limit_pdf_chars: int = 18_000) -> Dict[str, Any]:
    """Returns ready-to-use payloads for OpenAI vision and a PDF summary
    block to inject as a system message."""
    cur = db.app_studio_attachments.find(
        {"project_id": project_id, "user_id": user_id}, {"_id": 0}
    ).sort([("created_at", -1)]).limit(20)
    docs = await cur.to_list(20)

    images: List[Dict[str, str]] = []
    pdf_chunks: List[str] = []
    for d in docs:
        if d.get("kind") == "image" and d.get("b64") and len(images) < limit_images:
            images.append({
                "mime": d.get("mime") or d.get("content_type") or "image/jpeg",
                "b64": d["b64"],
                "filename": d.get("filename"),
            })
        elif d.get("kind") == "pdf" and d.get("text"):
            note = d.get("note") or ""
            chunk = f"[ملف: {d.get('filename')}]"
            if note:
                chunk += f" (ملاحظة العميل: {note})"
            chunk += "\n" + d["text"]
            pdf_chunks.append(chunk)

    pdf_text = "\n\n---\n\n".join(pdf_chunks)[:limit_pdf_chars]
    return {
        "images": images,
        "pdf_text": pdf_text,
        "total_attachments": len(docs),
    }


def build_attachment_system_message(payload: Dict[str, Any]) -> Optional[str]:
    """Build a single system message that informs the AI of what the user
    has uploaded. The images themselves are passed via the user message
    content blocks."""
    img_count = len(payload.get("images") or [])
    pdf_text = (payload.get("pdf_text") or "").strip()
    if not img_count and not pdf_text:
        return None
    parts: List[str] = ["📎 **مرفقات العميل** — اعتبرها مصدر الحقيقة. لا تخترع شي يخالفها."]
    if img_count:
        parts.append(
            f"- {img_count} صورة/مخطط مرفوعة. شفها بنفسك من content blocks في رسالة المستخدم. "
            "لو فيها mockups للتطبيق، التزم بها حرفياً: نفس الـlayout، نفس الألوان، نفس المسميات."
        )
    if pdf_text:
        parts.append("- نص مستخرج من PDF مرفق:\n```\n" + pdf_text + "\n```")
    parts.append(
        "🎯 لما تستدعي `analyze_uploaded_designs` راح تستخرج design brief مهيكل "
        "(palette + screens + layout) ويُحفظ في المشروع، ومحرك البناء يحترمه."
    )
    return "\n".join(parts)
