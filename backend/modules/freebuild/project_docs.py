"""Per-Project Documentation Memory.

Each FreeBuild project gets a small "engineering binder" stored in MongoDB
collection `freebuild_project_docs`:
  • prd          — Problem statement, goals, target users (stable)
  • changelog    — Append-only log of major changes/decisions
  • decisions    — Architecture decisions log (why we picked X over Y)
  • test_creds   — Test accounts / API keys created for this project

The main agent reads/writes these via two tools: `read_project_doc` and
`update_project_doc`. They persist across chat sessions so the AI can pick
up where it left off even after a long pause.

Documents are scoped strictly by `project_id` — no cross-project leakage.
"""
from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger("freebuild.project_docs")

ALLOWED_DOCS = {"prd", "changelog", "decisions", "test_creds"}
MAX_LEN = 60000  # cap per doc — keep things manageable


async def read_project_doc(db, project_id: str, doc_name: str) -> Dict[str, Any]:
    """Read one engineering doc for a project. Returns empty content if missing."""
    if not project_id or doc_name not in ALLOWED_DOCS:
        return {"ok": False, "error": f"invalid doc_name (allowed: {sorted(ALLOWED_DOCS)})"}
    try:
        doc = await db.freebuild_project_docs.find_one(
            {"project_id": project_id, "doc_name": doc_name}, {"_id": 0}
        )
        if not doc:
            return {"ok": True, "doc_name": doc_name, "content": "", "version": 0,
                     "is_empty": True}
        return {
            "ok": True,
            "doc_name": doc_name,
            "content": doc.get("content", ""),
            "version": doc.get("version", 1),
            "updated_at": doc.get("updated_at", 0),
            "is_empty": False,
        }
    except Exception as e:
        logger.exception("read_project_doc failed")
        return {"ok": False, "error": f"{type(e).__name__}: {str(e)[:160]}"}


async def update_project_doc(db, project_id: str, doc_name: str,
                                content: str, mode: str = "replace") -> Dict[str, Any]:
    """Write a project doc.

    mode='replace' → overwrite entirely (for PRD which is mostly stable)
    mode='append'  → add to the end with a timestamp (for changelog/decisions)
    """
    if not project_id or doc_name not in ALLOWED_DOCS:
        return {"ok": False, "error": f"invalid doc_name (allowed: {sorted(ALLOWED_DOCS)})"}
    if mode not in ("replace", "append"):
        return {"ok": False, "error": "mode must be 'replace' or 'append'"}
    content = (content or "").strip()
    if not content:
        return {"ok": False, "error": "content is empty"}
    if len(content) > MAX_LEN:
        return {"ok": False, "error": f"content too long ({len(content)} > {MAX_LEN})"}
    try:
        now = int(time.time())
        if mode == "append":
            existing = await db.freebuild_project_docs.find_one(
                {"project_id": project_id, "doc_name": doc_name}, {"content": 1, "version": 1}
            )
            prev = (existing or {}).get("content", "")
            new_content = (prev + ("\n\n" if prev else "") +
                           f"### {time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime(now))}\n" +
                           content)
            new_content = new_content[-MAX_LEN:]  # keep last N chars on overflow
            new_version = (existing or {}).get("version", 0) + 1
        else:
            new_content = content
            existing = await db.freebuild_project_docs.find_one(
                {"project_id": project_id, "doc_name": doc_name}, {"version": 1}
            )
            new_version = (existing or {}).get("version", 0) + 1
        await db.freebuild_project_docs.update_one(
            {"project_id": project_id, "doc_name": doc_name},
            {"$set": {
                "project_id": project_id,
                "doc_name": doc_name,
                "content": new_content,
                "version": new_version,
                "updated_at": now,
            }},
            upsert=True,
        )
        return {
            "ok": True,
            "doc_name": doc_name,
            "version": new_version,
            "length": len(new_content),
            "mode": mode,
        }
    except Exception as e:
        logger.exception("update_project_doc failed")
        return {"ok": False, "error": f"{type(e).__name__}: {str(e)[:160]}"}


# ─── Helper for the agent to dump all docs into prompt context ───────────────
async def load_all_project_docs(db, project_id: str) -> str:
    """Return a system-prompt-ready string with all 4 docs concatenated.

    Empty docs are skipped so we don't waste tokens.
    """
    if not project_id:
        return ""
    try:
        cur = db.freebuild_project_docs.find({"project_id": project_id}, {"_id": 0})
        docs = await cur.to_list(length=10)
        if not docs:
            return ""
        order = {"prd": 0, "decisions": 1, "changelog": 2, "test_creds": 3}
        docs.sort(key=lambda d: order.get(d.get("doc_name"), 99))
        parts: List[str] = [
            "", "═══════════════════════════════════════════════════════════",
            "📁 **توثيق المشروع (engineering binder) — اقرأها قبل أي عمل:**", "",
        ]
        for d in docs:
            content = (d.get("content") or "").strip()
            if not content:
                continue
            parts.append(f"### 📄 `{d['doc_name']}.md` (v{d.get('version', 1)})")
            parts.append(content[:8000])  # cap each doc to keep prompt lean
            parts.append("")
        return "\n".join(parts)
    except Exception as e:
        logger.warning(f"load_all_project_docs failed: {e}")
        return ""


# ─── Tool schemas for the agent ──────────────────────────────────────────────
PROJECT_DOC_TOOL_SCHEMAS: List[Dict[str, Any]] = [
    {
        "name": "read_project_doc",
        "description": (
            "📖 اقرأ مستند هندسي للمشروع (مخزّن دائم بين الجلسات). "
            "المستندات المتاحة: `prd` (تعريف المشروع)، `changelog` (سجل التغييرات)، "
            "`decisions` (سجل قرارات معمارية)، `test_creds` (بيانات اختبار). "
            "**اقرأ `prd` في أول كل جلسة** لتذكّر طلب العميل الأصلي."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "doc_name": {"type": "string", "enum": ["prd", "changelog", "decisions", "test_creds"]},
            },
            "required": ["doc_name"],
        },
    },
    {
        "name": "update_project_doc",
        "description": (
            "📝 حدّث مستند هندسي للمشروع. الـ `prd` يتحدّث بـ replace (التعريف يتطور). "
            "الـ `changelog` و `decisions` يستخدمون append (سجل تراكمي مع timestamps). "
            "**استخدمها لما العميل يقرر شي مهم** (تغيير tech stack, ميزة جديدة كبيرة، قرار تصميمي حاسم). "
            "هذا يخليك تذكر القرارات حتى بعد أسابيع."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "doc_name": {"type": "string", "enum": ["prd", "changelog", "decisions", "test_creds"]},
                "content": {"type": "string", "description": "نص الـ markdown الجديد (أو الإضافة لو mode=append)"},
                "mode": {"type": "string", "enum": ["replace", "append"], "default": "append"},
            },
            "required": ["doc_name", "content"],
        },
    },
]

PROJECT_DOC_TOOL_NAMES = {t["name"] for t in PROJECT_DOC_TOOL_SCHEMAS}
