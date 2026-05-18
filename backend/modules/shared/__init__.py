"""
Shared Agent Core — Unified intelligence layer for every Zitex section.

Each user-facing section (Images, Videos, Websites, Apps, Games, Owner) gets
an instance of `SectionAgent` configured with:

  • `scope`            — what this agent is allowed to discuss / produce
  • `redirects`        — out-of-scope requests → suggest the right section
  • `allowed_tools`    — subset of the global tool registry
  • `system_persona`   — Arabic identity + style for this section
  • `model_pref`       — preferred LLM (auto-routes via existing model_router)

All agents transparently use:
  • Smart Model Router (auto-pick cheapest capable LLM)
  • Code-cache style semantic Q&A cache (per-section namespace)
  • Cross-session memory keyed by user_id

This file does NOT duplicate the auto-coder's heavy tool registry — that
agent stays in `modules/autocoder/`. Instead, this module provides the
generic chat loop + redirect logic + scope enforcement that the lighter
client-facing sections need.

Public API:
    SectionAgent(scope, …).chat(user_id, message, session_id) -> dict
    register_section(scope, config)
    detect_intent(text) -> str           # "image"|"video"|"website"|"app"|...

Mongo collections (created lazily):
    shared_agent_sessions   — per-session state {id, user_id, scope, turns[],
                              context, series_id?, episodes[], updated_at}
    shared_agent_qa_cache   — per-scope semantic Q&A (namespaced)
"""
from __future__ import annotations
import os
import re
import uuid
import json
import hashlib
import logging
import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Callable, Awaitable

logger = logging.getLogger(__name__)

_DB: Any = None


def bind_db(db) -> None:
    global _DB
    _DB = db


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ════════════════════════════════════════════════════════════════════════
# SECTION CONFIG — what each section knows about itself and the platform
# ════════════════════════════════════════════════════════════════════════
SECTION_CONFIG: Dict[str, Dict[str, Any]] = {
    "image": {
        "label": "قسم الصور",
        "specialty_ar": "توليد الصور الاحترافية (إعلانات، منتجات، لوقو، بوسترات…)",
        "out_of_scope_redirects": {
            "video": ("قسم الفيديو", "/chat/video"),
            "website": ("قسم بناء المواقع", "/build-from-zero"),
            "app": ("قسم تطبيقات الجوال", "/dashboard/apps"),
            "game": ("قسم الألعاب", "/games"),
        },
        "persona": (
            "أنت 'زيتاكس صور' — مصمم بصري احترافي يتكلم بالسعودي. "
            "تخصصك حصراً: توليد الصور بكل أنواعها (إعلانات، لوقو، بوستر، صور منتجات، "
            "تصاميم سوشيال). تفهم طلب العميل بعمق وتقترح نماذج بصرية متعددة قبل التوليد."
        ),
        "preferred_model": "gemini",
        "abilities": ["analyze_brief", "suggest_styles", "list_variants"],
    },
    "video": {
        "label": "قسم الفيديو",
        "specialty_ar": "إنتاج فيديوات سينمائية بمراحل (سيناريو → ستوري بورد → موافقة → إنتاج)",
        "out_of_scope_redirects": {
            "image": ("قسم الصور", "/chat/image"),
            "website": ("قسم بناء المواقع", "/build-from-zero"),
            "app": ("قسم تطبيقات الجوال", "/dashboard/apps"),
        },
        "persona": (
            "أنت 'زيتاكس فيديو' — مخرج سينمائي سعودي. تخصصك إنتاج الفيديوهات بمنهجية "
            "احترافية بمراحل: ١) كتابة السيناريو ٢) لقطات Shot list ٣) ستوري بورد (صور لكل مشهد) "
            "٤) موافقة العميل ٥) الإنتاج النهائي. "
            "تدعم سلاسل/حلقات متتالية: لو العميل يبي يكمل قصة من حلقة سابقة، "
            "ترجع لذاكرة السلسلة وتحافظ على الشخصيات والـlook & feel نفسه."
        ),
        "preferred_model": "claude",
        "abilities": [
            "write_script", "design_shots", "generate_storyboard",
            "continue_series", "estimate_cost", "approve_and_render",
        ],
    },
    "website": {
        "label": "قسم بناء المواقع من الصفر",
        "specialty_ar": "بناء مواقع تفاعلية SPA من الصفر بالشات",
        "out_of_scope_redirects": {
            "image": ("قسم الصور", "/chat/image"),
            "video": ("قسم الفيديو", "/chat/video"),
            "app": ("قسم تطبيقات الجوال", "/dashboard/apps"),
        },
        "persona": (
            "أنت 'زيتاكس مواقع' — مهندس واجهات سعودي. تبني مواقع SPA كاملة "
            "من الصفر بمحادثة حية مع معاينة لحظية. كل قسم يضاف للموقع مباشرة. "
            "لا قوالب جاهزة — كل موقع فريد."
        ),
        "preferred_model": "claude",
        "abilities": ["chat_build", "live_preview", "surgical_edits"],
    },
    "app": {
        "label": "قسم تطبيقات الجوال",
        "specialty_ar": "بناء/صيانة/تخصيص تطبيقات الجوال (3 مسارات)",
        "out_of_scope_redirects": {
            "image": ("قسم الصور", "/chat/image"),
            "video": ("قسم الفيديو", "/chat/video"),
            "website": ("قسم بناء المواقع", "/build-from-zero"),
        },
        "persona": (
            "أنت 'زيتاكس تطبيقات' — مطوّر تطبيقات سعودي. تقدم 3 مسارات: "
            "١) قوالب جاهزة قابلة للتعديل ٢) تطبيق من الصفر بالـHTML5 ٣) صيانة لتطبيق سابق. "
            "اسأل العميل عن المسار قبل ما تبدأ."
        ),
        "preferred_model": "openai",
        "abilities": ["pick_path", "template_remix", "from_scratch", "maintenance"],
    },
    "game": {
        "label": "قسم الألعاب",
        "specialty_ar": "ألعاب HTML5/Canvas بسيطة قابلة للنشر",
        "out_of_scope_redirects": {
            "video": ("قسم الفيديو", "/chat/video"),
            "app": ("قسم تطبيقات الجوال", "/dashboard/apps"),
        },
        "persona": (
            "أنت 'زيتاكس ألعاب' — مصمم ألعاب سعودي. تبني ألعاب HTML5 بسيطة "
            "تنشر مباشرة في المتصفح. تركّز على gameplay loop واضح وأشياء قابلة للّعب فوراً."
        ),
        "preferred_model": "openai",
        "abilities": ["pick_genre", "build_canvas_game"],
    },
    "owner": {
        "label": "برمجة زيتاكس",
        "specialty_ar": "صلاحيات كاملة على الكود — للمالك فقط",
        "out_of_scope_redirects": {},  # No redirects — owner can do anything
        "persona": (
            "أنت 'زيتاكس برمجة' — مهندس برمجيات senior سعودي يخدم المالك. "
            "صلاحياتك مفتوحة على الكود بالكامل."
        ),
        "preferred_model": "claude",
        "abilities": ["full_access"],
    },
}


# ════════════════════════════════════════════════════════════════════════
# INTENT DETECTION — route a request to the right section
# ════════════════════════════════════════════════════════════════════════
_INTENT_PATTERNS: List[tuple] = [
    ("video", re.compile(
        r"(فيديو|فيديوهات|مقطع|كليب|سيناريو|إخراج|مشهد|إعلان متحرك|حلقة|"
        r"video|clip|scene|episode|reel|short film)", re.IGNORECASE)),
    ("image", re.compile(
        r"(صور(?!ة\s*متحركة)|صورة(?!\s*متحركة)|تصميم|بنر|لوقو|بوستر|ثَمب نيل|"
        r"image|photo|logo|poster|banner|thumbnail)", re.IGNORECASE)),
    ("website", re.compile(
        r"(موقع|صفحة|landing|website|site|spa|web app|بناء موقع)", re.IGNORECASE)),
    ("app", re.compile(
        r"(تطبيق|جوال|أندرويد|آيفون|app|mobile|android|ios)", re.IGNORECASE)),
    ("game", re.compile(
        r"(لعبة|ألعاب|game)", re.IGNORECASE)),
]


def detect_intent(text: str) -> Optional[str]:
    if not text:
        return None
    for scope, pat in _INTENT_PATTERNS:
        if pat.search(text):
            return scope
    return None


def out_of_scope_message(current_scope: str, requested_scope: str) -> Optional[Dict[str, Any]]:
    """Return a polite redirect dict when the user asks for the wrong thing."""
    cfg = SECTION_CONFIG.get(current_scope)
    if not cfg:
        return None
    target = (cfg.get("out_of_scope_redirects") or {}).get(requested_scope)
    if not target:
        return None
    target_label, target_route = target
    return {
        "redirect": True,
        "to_scope": requested_scope,
        "to_label": target_label,
        "to_route": target_route,
        "message": (
            f"أخوي هذا القسم تخصصه {cfg['specialty_ar']}.\n"
            f"الطلب اللي تبيه يطلع من اختصاص **{target_label}**. "
            f"اضغط هنا للتحويل: {target_route}"
        ),
    }


# ════════════════════════════════════════════════════════════════════════
# SECTION-NAMESPACED Q&A CACHE (uses the same embedding helper as code_cache)
# ════════════════════════════════════════════════════════════════════════
async def _embed(text: str) -> Optional[List[float]]:
    """Reuse the code_cache embedder so we share the in-process LRU."""
    try:
        from modules.autocoder.code_cache import _embed as _emb  # type: ignore
        return await _emb(text)
    except Exception:
        return None


def _norm(q: str) -> str:
    q = (q or "").strip().lower()
    q = re.sub(r"\s+", " ", q)
    return q[:2000]


def _query_sha(scope: str, q: str) -> str:
    return hashlib.sha256(f"{scope}::{_norm(q)}".encode("utf-8")).hexdigest()


async def cache_lookup(scope: str, question: str) -> Optional[Dict[str, Any]]:
    if _DB is None or not question:
        return None
    sha = _query_sha(scope, question)
    try:
        exact = await _DB.shared_agent_qa_cache.find_one({"query_sha": sha}, {"_id": 0})
        if exact:
            return {**exact, "match_type": "exact", "similarity": 1.0}
    except Exception:
        pass
    vec = await _embed(_norm(question))
    if not vec:
        return None
    try:
        cur = _DB.shared_agent_qa_cache.find(
            {"scope": scope, "embedding": {"$exists": True}}, {"_id": 0}
        ).sort([("updated_at", -1)]).limit(80)
        cands = await cur.to_list(80)
    except Exception:
        return None
    best, bsim = None, 0.0
    for c in cands:
        cv = c.get("embedding") or []
        if len(cv) != len(vec):
            continue
        num = sum(a * b for a, b in zip(vec, cv))
        da = sum(a * a for a in vec) ** 0.5
        db = sum(b * b for b in cv) ** 0.5
        if da == 0 or db == 0:
            continue
        sim = num / (da * db)
        if sim > bsim:
            bsim, best = sim, c
    if best and bsim >= 0.92:
        return {**best, "match_type": "semantic", "similarity": bsim}
    return None


async def cache_save(scope: str, question: str, answer: str, *, meta: Optional[Dict[str, Any]] = None) -> None:
    if _DB is None or not question or not answer:
        return
    sha = _query_sha(scope, question)
    vec = await _embed(_norm(question))
    doc = {
        "query_sha": sha,
        "scope": scope,
        "question": question[:4000],
        "answer": answer[:20000],
        "meta": meta or {},
        "updated_at": _now(),
    }
    if vec:
        doc["embedding"] = vec
    try:
        await _DB.shared_agent_qa_cache.update_one(
            {"query_sha": sha},
            {"$set": doc, "$setOnInsert": {"created_at": _now(), "hit_count": 0}},
            upsert=True,
        )
    except Exception:
        pass


# ════════════════════════════════════════════════════════════════════════
# SESSION MEMORY (cross-section, persistent)
# ════════════════════════════════════════════════════════════════════════
async def session_get(session_id: str, user_id: str) -> Optional[Dict[str, Any]]:
    if _DB is None:
        return None
    return await _DB.shared_agent_sessions.find_one(
        {"id": session_id, "user_id": user_id}, {"_id": 0}
    )


async def session_create(user_id: str, scope: str, *, series_id: str = "", title: str = "") -> Dict[str, Any]:
    doc = {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "scope": scope,
        "title": title or f"جلسة {SECTION_CONFIG.get(scope, {}).get('label', scope)}",
        "series_id": series_id or "",
        "turns": [],
        "context": {},
        "created_at": _now(),
        "updated_at": _now(),
    }
    if _DB is not None:
        await _DB.shared_agent_sessions.insert_one(doc.copy())
    return doc


async def session_append_turn(session_id: str, role: str, content: str, *, meta: Optional[Dict[str, Any]] = None) -> None:
    if _DB is None:
        return
    turn = {"role": role, "content": content[:16000], "ts": _now()}
    if meta:
        turn["meta"] = meta
    await _DB.shared_agent_sessions.update_one(
        {"id": session_id},
        {"$push": {"turns": turn}, "$set": {"updated_at": _now()}},
    )


async def session_set_context(session_id: str, patch: Dict[str, Any]) -> None:
    if _DB is None or not patch:
        return
    set_doc = {f"context.{k}": v for k, v in patch.items()}
    set_doc["updated_at"] = _now()
    await _DB.shared_agent_sessions.update_one({"id": session_id}, {"$set": set_doc})


async def list_user_sessions(user_id: str, scope: str = "", limit: int = 30) -> List[Dict[str, Any]]:
    if _DB is None:
        return []
    filt: Dict[str, Any] = {"user_id": user_id}
    if scope:
        filt["scope"] = scope
    cur = _DB.shared_agent_sessions.find(filt, {"_id": 0, "turns": 0}).sort([("updated_at", -1)]).limit(limit)
    return await cur.to_list(limit)


# ════════════════════════════════════════════════════════════════════════
# LLM call — routes via Smart Model Router (existing infra)
# ════════════════════════════════════════════════════════════════════════
async def _call_llm(scope: str, messages: List[Dict[str, str]], *, max_tokens: int = 1200) -> str:
    """Call the user's preferred LLM via existing keys. Falls back gracefully."""
    cfg = SECTION_CONFIG.get(scope, {})
    pref = cfg.get("preferred_model", "claude")

    # Try OpenAI direct first when chosen / available
    oai_key = (os.environ.get("OPENAI_DIRECT_KEY") or os.environ.get("OPENAI_API_KEY") or "").strip()
    em_key = os.environ.get("EMERGENT_LLM_KEY", "").strip()

    # Path A: OpenAI direct
    if pref == "openai" and oai_key:
        try:
            import httpx
            async with httpx.AsyncClient(timeout=60.0) as client:
                r = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {oai_key}"},
                    json={"model": "gpt-4o", "messages": messages, "max_tokens": max_tokens},
                )
                if r.status_code == 200:
                    return r.json()["choices"][0]["message"]["content"]
        except Exception as e:
            logger.warning(f"openai call failed: {e}")

    # Path B: Claude via Emergent key
    if em_key:
        try:
            from emergentintegrations.llm.chat import LlmChat, UserMessage  # type: ignore
            sys_text = next((m["content"] for m in messages if m["role"] == "system"), "")
            user_msgs = [m for m in messages if m["role"] != "system"]
            chat = LlmChat(api_key=em_key, session_id=str(uuid.uuid4()), system_message=sys_text)
            chat = chat.with_model("anthropic", "claude-sonnet-4-5-20250929")
            chat = chat.with_max_tokens(max_tokens)
            # Concatenate user messages
            text_in = "\n\n".join(m["content"] for m in user_msgs)
            resp = await chat.send_message(UserMessage(text=text_in))
            return str(resp) if resp else ""
        except Exception as e:
            logger.warning(f"claude call failed: {e}")

    # Path C: OpenAI even if not preferred
    if oai_key:
        try:
            import httpx
            async with httpx.AsyncClient(timeout=60.0) as client:
                r = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {oai_key}"},
                    json={"model": "gpt-4o", "messages": messages, "max_tokens": max_tokens},
                )
                if r.status_code == 200:
                    return r.json()["choices"][0]["message"]["content"]
        except Exception as e:
            logger.warning(f"fallback openai failed: {e}")

    return "آسف، حالياً ما عندنا اتصال نشط مع موديل ذكاء. تأكد من إعداد المفاتيح."


# ════════════════════════════════════════════════════════════════════════
# SectionAgent — the public interface
# ════════════════════════════════════════════════════════════════════════
class SectionAgent:
    def __init__(self, scope: str, *, extra_persona: str = "", strict_scope: bool = True):
        if scope not in SECTION_CONFIG:
            raise ValueError(f"unknown scope: {scope}")
        self.scope = scope
        self.cfg = SECTION_CONFIG[scope]
        self.extra_persona = extra_persona
        self.strict_scope = strict_scope

    def _system_prompt(self, ctx: Optional[Dict[str, Any]] = None) -> str:
        ctx = ctx or {}
        # Build redirect map description for the AI
        redirects = self.cfg.get("out_of_scope_redirects") or {}
        redirect_lines = []
        for k, (lbl, route) in redirects.items():
            redirect_lines.append(f"  • {k} → {lbl} ({route})")
        redirect_block = "\n".join(redirect_lines) if redirect_lines else "  (لا قيود — جميع المواضيع مفتوحة)"

        ctx_block = ""
        if ctx:
            ctx_block = "\n\n📋 سياق الجلسة الحالية:\n" + json.dumps(ctx, ensure_ascii=False, indent=2)[:1500]

        scope_rule = ""
        if self.strict_scope and redirects:
            scope_rule = (
                "\n\n🚧 قاعدة النطاق:\n"
                f"تخصصك حصراً: {self.cfg['specialty_ar']}.\n"
                "لو العميل طلب شي خارج هذا التخصص، **لا تنفّذه**. وجّهه للقسم الصحيح:\n"
                f"{redirect_block}\n"
                "صياغة التحويل: 'أخوي، هذا الطلب يطلع لـ <اسم القسم>، روح هناك من <الرابط>'."
            )

        return (
            self.cfg["persona"]
            + (("\n" + self.extra_persona) if self.extra_persona else "")
            + scope_rule
            + ctx_block
            + "\n\n📝 قواعد الردّ:\n"
            "- اللغة: العربية السعودية الطبيعية.\n"
            "- ممنوع الإيموجي إلا لما يفيد فعلاً (✓ ✗ في checklists فقط).\n"
            "- ممنوع الاعتذار الفارغ ('للأسف ما أقدر…')—إذا فيه طريقة نفّذها، إذا ما فيه وضّح ليه باختصار وقدّم بديل.\n"
            "- اختصر. سؤال واحد كل دور إذا تحتاج توضيح."
        )

    async def chat(
        self,
        user_id: str,
        message: str,
        *,
        session_id: str = "",
        use_cache: bool = True,
    ) -> Dict[str, Any]:
        """Conversational entry point.
        Returns: {ok, reply, session_id, redirect?, cached?}"""
        # 1) Session resolve / create
        sess: Optional[Dict[str, Any]] = None
        if session_id:
            sess = await session_get(session_id, user_id)
        if not sess:
            sess = await session_create(user_id, self.scope)
        sid = sess["id"]

        # 2) Out-of-scope detection
        if self.strict_scope:
            intent = detect_intent(message)
            if intent and intent != self.scope:
                redirect = out_of_scope_message(self.scope, intent)
                if redirect:
                    await session_append_turn(sid, "user", message)
                    await session_append_turn(sid, "assistant", redirect["message"], meta={"redirect": redirect})
                    return {
                        "ok": True,
                        "session_id": sid,
                        "reply": redirect["message"],
                        "redirect": redirect,
                    }

        # 3) Cache lookup
        if use_cache:
            hit = await cache_lookup(self.scope, message)
            if hit:
                await session_append_turn(sid, "user", message)
                await session_append_turn(sid, "assistant", hit["answer"],
                                          meta={"cache": hit.get("match_type"), "similarity": hit.get("similarity")})
                return {
                    "ok": True, "session_id": sid, "reply": hit["answer"],
                    "cached": True, "match_type": hit.get("match_type"),
                    "similarity": round(hit.get("similarity", 0.0), 4),
                }

        # 4) Build history → call LLM
        history = sess.get("turns", [])[-12:]  # last 12 turns
        messages: List[Dict[str, str]] = [
            {"role": "system", "content": self._system_prompt(sess.get("context"))},
        ]
        for t in history:
            role = "assistant" if t.get("role") == "assistant" else "user"
            messages.append({"role": role, "content": t.get("content", "")})
        messages.append({"role": "user", "content": message})

        reply = await _call_llm(self.scope, messages)
        reply = (reply or "").strip() or "آسف، ما طلعت ردود من النموذج. حاول مرة ثانية."

        # 5) Persist + cache
        await session_append_turn(sid, "user", message)
        await session_append_turn(sid, "assistant", reply)
        if use_cache and len(reply) > 80:
            await cache_save(self.scope, message, reply)

        return {"ok": True, "session_id": sid, "reply": reply, "cached": False}
