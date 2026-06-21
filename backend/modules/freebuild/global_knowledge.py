"""
Zenrex AI Brain — Global Cumulative Knowledge (cross-user learning).

Every Zenrex AI agent shares ONE evolving knowledge base. When the AI solves
a tricky problem, ships a design the user explicitly approves, or discovers a
useful pattern, it can call `save_learning(...)` to persist that wisdom into
the global `ai_global_knowledge` collection. The next chat turn (for ANY user
on ANY project) automatically retrieves the top-N relevant entries and
injects them into the system prompt — so the brain truly compounds over time.

Collection schema (`ai_global_knowledge`):
    {
      id              : str  (uuid)
      category        : str  ("design" | "code" | "ux" | "pricing" | "sector" | "bug_fix" | "other")
      mode            : str  ("website" | "apps_studio" | "games_studio" | "any")
      sector          : str  ("restaurant" | "ecommerce" | "service" | "education" | "any")
      problem         : str  (≤ 280 chars — what was the challenge)
      solution        : str  (≤ 1200 chars — what worked)
      tags            : list[str]  (free-form keywords for retrieval)
      success_count   : int  (how many times this practice has been reused)
      last_used_at    : float
      created_at      : float
      created_by_user : str  (anonymized — for audit only)
    }

Public surface:
    add_best_practice(db, **kwargs)                 — persist a new entry
    load_global_knowledge_for_prompt(db, mode, sector, keywords) — RAG block
    GLOBAL_KNOWLEDGE_TOOL_SCHEMA / save_learning(ctx, args)      — agent tool
"""
from __future__ import annotations

import logging
import re
import time
import uuid
from typing import Any, Dict, List, Optional

logger = logging.getLogger("zenrex.global_knowledge")


_CATEGORIES = {"design", "code", "ux", "pricing", "sector", "bug_fix", "other"}
_MAX_INJECT = 8           # top-N practices to inject into prompt
_MAX_PROBLEM = 280
_MAX_SOLUTION = 1200


async def add_best_practice(
    db,
    *,
    category: str,
    mode: str,
    sector: str,
    problem: str,
    solution: str,
    tags: Optional[List[str]] = None,
    created_by_user: Optional[str] = None,
) -> Dict[str, Any]:
    """Persist a new global best-practice entry.

    De-dups by (category, sector, problem_normalised) — if the same lesson was
    already saved, we just bump `success_count` and `last_used_at` instead of
    inserting a duplicate.
    """
    if db is None:
        return {"ok": False, "error": "db missing"}
    cat = (category or "other").strip().lower()
    if cat not in _CATEGORIES:
        cat = "other"
    mode = (mode or "any").strip().lower() or "any"
    sector = (sector or "any").strip().lower() or "any"
    problem = (problem or "").strip()[:_MAX_PROBLEM]
    solution = (solution or "").strip()[:_MAX_SOLUTION]
    tags = [t.strip().lower() for t in (tags or []) if isinstance(t, str) and t.strip()][:12]
    if not problem or not solution:
        return {"ok": False, "error": "problem + solution are required"}
    try:
        norm = re.sub(r"\s+", " ", problem.lower()).strip()
        now = time.time()
        existing = await db.ai_global_knowledge.find_one(
            {"category": cat, "sector": sector, "_problem_norm": norm},
            {"_id": 0, "id": 1, "success_count": 1},
        )
        if existing:
            await db.ai_global_knowledge.update_one(
                {"id": existing["id"]},
                {"$inc": {"success_count": 1},
                 "$set": {"last_used_at": now,
                          "solution": solution,        # overwrite with latest wording
                          "tags": tags or None}},
            )
            return {"ok": True, "id": existing["id"], "reused": True,
                    "success_count": int(existing.get("success_count", 1)) + 1}
        new_id = uuid.uuid4().hex
        await db.ai_global_knowledge.insert_one({
            "id": new_id,
            "category": cat,
            "mode": mode,
            "sector": sector,
            "problem": problem,
            "_problem_norm": norm,
            "solution": solution,
            "tags": tags,
            "success_count": 1,
            "last_used_at": now,
            "created_at": now,
            "created_by_user": (created_by_user or "")[:64],
        })
        return {"ok": True, "id": new_id, "reused": False}
    except Exception as e:
        logger.warning(f"add_best_practice failed: {e}")
        return {"ok": False, "error": str(e)[:200]}


async def load_global_knowledge_for_prompt(
    db,
    mode: Optional[str] = None,
    sector: Optional[str] = None,
    keywords: Optional[List[str]] = None,
) -> str:
    """Return a Markdown block of the most relevant global practices.

    Retrieval is a simple but effective heuristic:
      1. Match on (mode, sector) when provided — otherwise fall back to "any".
      2. Boost entries whose tags overlap with `keywords`.
      3. Sort by success_count DESC, then last_used_at DESC.
      4. Cap to top-_MAX_INJECT.
    """
    if db is None:
        return ""
    try:
        mode = (mode or "").strip().lower() or None
        sector = (sector or "").strip().lower() or None
        keywords = [k.strip().lower() for k in (keywords or []) if isinstance(k, str) and k.strip()]
        q: Dict[str, Any] = {}
        if mode and mode != "any":
            q["mode"] = {"$in": [mode, "any"]}
        if sector and sector != "any":
            q["sector"] = {"$in": [sector, "any"]}
        cursor = db.ai_global_knowledge.find(
            q, {"_id": 0, "category": 1, "problem": 1, "solution": 1,
                "tags": 1, "success_count": 1}
        ).sort([("success_count", -1), ("last_used_at", -1)]).limit(80)
        docs = await cursor.to_list(length=80)
        if not docs:
            return ""

        # Boost by tag overlap with current keywords
        def score(d: Dict[str, Any]) -> tuple:
            tags = set(d.get("tags") or [])
            overlap = len(tags.intersection(keywords)) if keywords else 0
            return (overlap, int(d.get("success_count") or 0))
        docs.sort(key=score, reverse=True)
        docs = docs[:_MAX_INJECT]

        lines = [
            "",
            "═══════════════════════════════════════════════════════════",
            "🌍 **خبرة Zenrex التراكمية (من كل مشاريع المنصة) — استفد منها:**",
            "",
        ]
        for i, d in enumerate(docs, 1):
            cat = d.get("category", "other")
            prob = (d.get("problem") or "").strip()
            sol = (d.get("solution") or "").strip()
            used = int(d.get("success_count") or 1)
            lines.append(f"  {i}. [{cat} · مُجرَّبة {used}×] ❓ {prob}")
            lines.append(f"     ✅ {sol}")
        lines += [
            "",
            "⚠️ هذه ليست أوامر — هي **خبرات سابقة ناجحة**. وظّفها بذكاء حسب",
            "    سياق هذا المشروع، ولا تُكرّر الحلّ حرفياً إذا لم يناسب.",
            "",
        ]
        return "\n".join(lines)
    except Exception as e:
        logger.warning(f"load_global_knowledge_for_prompt failed: {e}")
        return ""


# ─── AI-callable tool ────────────────────────────────────────────────────────
GLOBAL_KNOWLEDGE_TOOL_SCHEMA: Dict[str, Any] = {
    "name": "save_learning",
    "description": (
        "🌱 احفظ درساً مكتسباً في **الذاكرة العالمية لـ Zenrex** يستفيد منه كل "
        "وكلاء المنصة لاحقاً (عبر كل المستخدمين). استخدمها فقط عند: (1) العميل "
        "صرّح بإعجابه بحل/تصميم معيّن، (2) حل مشكلة تقنية صعبة لأول مرة، "
        "(3) اكتشاف نمط ينجح بثبات في قطاع معيّن. لا تستعملها للأشياء "
        "العامة المعروفة. اكتب الـ problem والـ solution بإيجاز ودقة."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "category": {"type": "string", "enum": ["design", "code", "ux",
                                                       "pricing", "sector",
                                                       "bug_fix", "other"]},
            "sector": {"type": "string",
                        "description": "restaurant | ecommerce | service | education | health | tech | any"},
            "problem": {"type": "string", "description": "وصف موجز للموقف/التحدي (≤ 280 حرف)."},
            "solution": {"type": "string", "description": "ما الذي نجح بالضبط؟ خطوات أو نهج عمليّ (≤ 1200 حرف)."},
            "tags": {"type": "array", "items": {"type": "string"},
                       "description": "كلمات مفتاحية للاسترجاع لاحقاً (مثلاً: ['hero', 'arabic-rtl', 'glassmorphism'])."},
        },
        "required": ["category", "problem", "solution"],
    },
}


async def save_learning(ctx, args: Dict[str, Any]) -> Dict[str, Any]:
    if ctx.db is None:
        return {"ok": False, "error": "db missing"}
    project = ctx.project or {}
    mode = project.get("mode", "any")
    # Infer sector from project description / category if not passed
    sector = (args.get("sector") or "").strip().lower()
    if not sector:
        desc = (project.get("description") or "") + " " + (project.get("name") or "")
        desc_low = desc.lower()
        if any(k in desc_low for k in ("مطعم", "مقهى", "كافيه", "restaurant", "cafe")):
            sector = "restaurant"
        elif any(k in desc_low for k in ("متجر", "shop", "store", "ecommerce")):
            sector = "ecommerce"
        elif any(k in desc_low for k in ("عيادة", "صحة", "clinic", "health")):
            sector = "health"
        elif any(k in desc_low for k in ("تعليم", "دورات", "education", "course")):
            sector = "education"
        else:
            sector = "any"
    res = await add_best_practice(
        ctx.db,
        category=args.get("category", "other"),
        mode=mode,
        sector=sector,
        problem=args.get("problem", ""),
        solution=args.get("solution", ""),
        tags=args.get("tags") or [],
        created_by_user=(project.get("user_id") or project.get("merchant_id") or ""),
    )
    if res.get("ok"):
        res["message"] = ("🌱 تمت إضافة الخبرة للذاكرة العالمية — "
                          + ("(تكرار — رفعت العدّاد)" if res.get("reused") else "(جديدة)"))
    return res


# ─── Keyword extraction helper for retrieval ─────────────────────────────────
_AR_STOPWORDS = {"في", "من", "على", "إلى", "عن", "مع", "هذا", "هذه", "ذلك",
                 "أن", "إن", "أو", "و", "ال", "كذا", "بعد", "قبل", "هو", "هي"}


def extract_keywords(text: str, *, max_count: int = 8) -> List[str]:
    """Cheap keyword extraction for retrieval. Picks meaningful tokens
    (Arabic + Latin) ≥ 4 chars, drops stop-words, deduplicates."""
    if not text:
        return []
    tokens = re.findall(r"[A-Za-z\u0621-\u064A]{4,}", text)
    out: List[str] = []
    seen: set = set()
    for t in tokens:
        low = t.lower()
        if low in _AR_STOPWORDS or low in seen:
            continue
        seen.add(low)
        out.append(low)
        if len(out) >= max_count:
            break
    return out
