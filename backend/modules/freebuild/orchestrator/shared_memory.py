"""
🧠 Project Memory — persistent context across cortex calls.

Solves the "stateless turn" bug: each cortex now retrieves and updates
a project-scoped memory document that holds:

  - brand_dna       : palette, tone, language, voice
  - glossary        : project-specific terms the AI must use
  - past_outputs    : list of {cortex, asset_url, prompt_excerpt, ts}
  - style_seed      : reusable visual consistency seed
  - last_message    : last user message (for continuity)

This is a thin wrapper around `freebuild_project_memory` MongoDB collection.
Each cortex calls `await load_memory(db, project_id)` at the top and
`await save_memory(db, project_id, updates)` at the bottom.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


async def load_memory(db, project_id: Optional[str]) -> Dict[str, Any]:
    """Load (or initialise) the project memory document."""
    if db is None or not project_id:
        return {"brand_dna": {}, "glossary": {}, "past_outputs": [], "style_seed": None}
    doc = await db.freebuild_project_memory.find_one({"project_id": project_id}, {"_id": 0})
    if doc:
        return doc
    fresh = {
        "project_id": project_id,
        "brand_dna": {},
        "glossary": {},
        "past_outputs": [],
        "style_seed": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    try:
        await db.freebuild_project_memory.insert_one(dict(fresh))
    except Exception:
        pass
    return fresh


async def save_memory(db, project_id: Optional[str], updates: Dict[str, Any]) -> None:
    """Apply updates to project memory. Lists get appended, dicts get merged."""
    if db is None or not project_id:
        return
    set_doc: Dict[str, Any] = {"updated_at": datetime.now(timezone.utc).isoformat()}
    push_doc: Dict[str, Any] = {}
    for k, v in updates.items():
        if k == "past_outputs" and isinstance(v, list):
            push_doc.setdefault("past_outputs", {"$each": v, "$slice": -50})  # keep last 50
        elif k in ("brand_dna", "glossary") and isinstance(v, dict):
            # Merge keys
            for sub_k, sub_v in v.items():
                set_doc[f"{k}.{sub_k}"] = sub_v
        else:
            set_doc[k] = v
    update = {}
    if set_doc:
        update["$set"] = set_doc
    if push_doc:
        update["$push"] = push_doc
    try:
        await db.freebuild_project_memory.update_one(
            {"project_id": project_id}, update, upsert=True,
        )
    except Exception:
        pass


def memory_to_system_hint(mem: Dict[str, Any]) -> str:
    """Convert memory dict to a compact Arabic hint for system prompts."""
    if not mem:
        return ""
    parts: List[str] = []
    bd = mem.get("brand_dna") or {}
    if bd:
        parts.append("**هوية العميل المحفوظة (Brand DNA):**")
        for k, v in bd.items():
            parts.append(f"  • {k}: {v}")
    gl = mem.get("glossary") or {}
    if gl:
        parts.append("**مصطلحات يجب استخدامها:**")
        for k, v in list(gl.items())[:10]:
            parts.append(f"  • {k} → {v}")
    po = mem.get("past_outputs") or []
    if po:
        parts.append(f"**أعمال سابقة في هذا المشروع ({len(po)} عنصر) — الأحدث أولاً:**")
        for o in reversed(po[-5:]):
            line = f"  • [{o.get('cortex','?')}] طلب: {o.get('prompt_excerpt','')[:100]}"
            if o.get("output_excerpt"):
                line += f"\n    ← المخرجات: {(o['output_excerpt'] or '')[:200]}"
            elif o.get("asset_url") and o["asset_url"] != "inline:narrative":
                line += f"\n    ← الناتج: {o['asset_url']}"
            parts.append(line)
    if mem.get("style_seed"):
        parts.append(f"**Style Seed (للحفاظ على اتساق الصور):** {mem['style_seed']}")
    return "\n".join(parts) if parts else ""


def history_to_messages(history: List[Dict[str, Any]], max_pairs: int = 6) -> List[Dict[str, str]]:
    """Convert chat history to LlmChat-compatible role messages."""
    out: List[Dict[str, str]] = []
    items = list(history or [])[-max_pairs * 2:]
    for h in items:
        role = (h.get("role") or "").lower()
        content = h.get("content") or h.get("text") or ""
        if not content:
            continue
        if role in ("user", "human"):
            out.append({"role": "user", "content": content[:1200]})
        elif role in ("assistant", "ai", "bot"):
            out.append({"role": "assistant", "content": content[:1200]})
    return out
