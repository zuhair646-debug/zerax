"""
🏛️ Architect Cortex — produces architecture diagrams + ADR BEFORE code.

Output for any non-trivial request:
  1. Mermaid Component Diagram
  2. Mermaid Sequence Diagram (for flows)
  3. Mermaid ERD (for data models)
  4. ADR (Architecture Decision Record) — one paragraph
  5. File/folder tree the AI will create

The Architect runs BEFORE the CodeCortex when intent is detected as
"complex app" (multiple pages, backend logic, integrations). For simple
landing pages it's skipped.

The diagrams are emitted as a `cortex_step` event so the UI can render them.
"""
from __future__ import annotations

import json
import logging
import os
import re
import uuid
from typing import Any, AsyncGenerator, Dict, List, Optional

logger = logging.getLogger("zenrex.architect_cortex")


def _sse(event: str, data: Dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


_ARCHITECT_PROMPT = """أنت **Architect Cortex** — مهندس برمجيات أعلى مستوى.

مهمتك: قبل أي كود، صمّم البنية المعمارية. أرجع JSON صرف:

{
  "complexity_score": 1-10,
  "stack": {
    "frontend": "HTML/JS | React | Next.js | Vue",
    "backend": "FastAPI | Express | none",
    "database": "MongoDB | Postgres | none",
    "key_libs": ["chart.js", "three.js", ...]
  },
  "component_diagram_mermaid": "graph TD\\n  ...",
  "sequence_diagram_mermaid": "sequenceDiagram\\n  ...",
  "erd_mermaid": "erDiagram\\n  ...",
  "file_tree": [
    "index.html",
    "css/main.css",
    "js/app.js",
    ...
  ],
  "adr": "قرار معماري في فقرة واحدة بالعربي (لماذا اخترت هذا الـ stack، ما البدائل، ما المقايضات)",
  "estimated_files": <count>,
  "estimated_credits": <50-500>,
  "phases": [
    {"name": "Phase 1: Skeleton", "deliverable": "..."},
    {"name": "Phase 2: ...", "deliverable": "..."}
  ]
}

**القواعد:**
- اختر أبسط stack يحقق المطلوب (KISS).
- إذا المشروع صفحة واحدة → frontend فقط، estimated_files <= 3.
- إذا فيه backend → اشرح الـ endpoints الرئيسية في sequence_diagram.
- إذا فيه DB → ERD واضح بـ relations.
- ADR: لماذا هذا الـ stack وليس بديل آخر؟
- لا تشرح، JSON صرف.
"""


def should_run_architect(user_message: str) -> bool:
    """Heuristic: only run Architect for complex requests."""
    msg = (user_message or "").lower()
    complex_signals = [
        "تطبيق", "نظام", "platform", "app", "saas", "dashboard",
        "auth", "login", "تسجيل دخول", "اشتراك", "subscription",
        "database", "قاعدة بيانات", "api", "backend",
        "multi-page", "صفحات متعددة", "متعدد المستخدمين", "multi-user",
        "realtime", "websocket", "live", "بث مباشر",
        "checkout", "payment", "دفع", "ecommerce", "متجر",
    ]
    score = sum(1 for s in complex_signals if s in msg)
    return score >= 1


async def design_architecture(user_message: str, brand_dna: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Call Claude to produce the architecture blueprint."""
    emergent_key = os.environ.get("EMERGENT_LLM_KEY", "").strip()
    if not emergent_key:
        return _fallback_architecture(user_message)

    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage  # type: ignore
        ctx = ""
        if brand_dna:
            ctx = f"\n\nBrand DNA (التزم به):\n{json.dumps(brand_dna, ensure_ascii=False)[:600]}\n"
        chat = LlmChat(
            api_key=emergent_key,
            session_id=f"architect_{uuid.uuid4().hex[:8]}",
            system_message=_ARCHITECT_PROMPT,
        ).with_model("anthropic", "claude-sonnet-4-5-20250929")
        resp = await chat.send_message(UserMessage(text=f"Brief:\n{user_message}{ctx}"))
        raw = resp if isinstance(resp, str) else str(resp)
        m = re.search(r"\{[\s\S]*\}", raw)
        if m:
            try:
                data = json.loads(m.group(0))
                return _normalize(data)
            except Exception as e:
                logger.warning(f"[architect] JSON parse failed: {e}")
    except Exception as e:
        logger.warning(f"[architect] LLM call failed: {e}")
    return _fallback_architecture(user_message)


def _normalize(data: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "complexity_score": max(1, min(10, int(data.get("complexity_score") or 3))),
        "stack": data.get("stack") or {"frontend": "HTML/JS"},
        "component_diagram_mermaid": data.get("component_diagram_mermaid") or "",
        "sequence_diagram_mermaid": data.get("sequence_diagram_mermaid") or "",
        "erd_mermaid": data.get("erd_mermaid") or "",
        "file_tree": data.get("file_tree") or [],
        "adr": data.get("adr") or "قرار معماري لم يُسجل.",
        "estimated_files": int(data.get("estimated_files") or len(data.get("file_tree") or []) or 3),
        "estimated_credits": max(50, min(500, int(data.get("estimated_credits") or 100))),
        "phases": data.get("phases") or [],
    }


def _fallback_architecture(user_message: str) -> Dict[str, Any]:
    return {
        "complexity_score": 3,
        "stack": {"frontend": "HTML/JS", "backend": "none", "database": "none", "key_libs": []},
        "component_diagram_mermaid": "graph TD\n  User-->Browser\n  Browser-->StaticHTML",
        "sequence_diagram_mermaid": "",
        "erd_mermaid": "",
        "file_tree": ["index.html", "css/main.css", "js/app.js"],
        "adr": "Stack بسيط (HTML/CSS/JS) — لا حاجة لـ backend أو DB لمشروع الصفحة الواحدة.",
        "estimated_files": 3,
        "estimated_credits": 60,
        "phases": [],
        "fallback": True,
    }


def render_architecture_summary_ar(arch: Dict[str, Any]) -> str:
    """Format the architecture as a markdown summary."""
    if not arch:
        return ""
    stack = arch.get("stack") or {}
    lines = [
        f"🏛️ **التخطيط المعماري (Complexity: {arch.get('complexity_score', 3)}/10)**",
        f"**Stack:** {stack.get('frontend', '?')} | {stack.get('backend', 'no-backend')} | {stack.get('database', 'no-db')}",
        f"**ملفات متوقعة:** {arch.get('estimated_files', '?')} ملف",
        f"**تكلفة متوقعة:** ~{arch.get('estimated_credits', '?')} credits",
        "",
        f"**ADR:** {arch.get('adr', '-')}",
    ]
    if arch.get("component_diagram_mermaid"):
        lines.append("\n**Component Diagram:**\n```mermaid\n" + arch["component_diagram_mermaid"] + "\n```")
    if arch.get("sequence_diagram_mermaid"):
        lines.append("\n**Sequence Diagram:**\n```mermaid\n" + arch["sequence_diagram_mermaid"] + "\n```")
    if arch.get("erd_mermaid"):
        lines.append("\n**ERD:**\n```mermaid\n" + arch["erd_mermaid"] + "\n```")
    if arch.get("file_tree"):
        tree = "\n".join(f"  - {f}" for f in arch["file_tree"][:20])
        lines.append(f"\n**File Tree:**\n{tree}")
    if arch.get("phases"):
        phases = "\n".join(f"  {i+1}. {p.get('name', '?')} — {p.get('deliverable', '?')}" for i, p in enumerate(arch["phases"]))
        lines.append(f"\n**Phases:**\n{phases}")
    return "\n".join(lines)


async def stream_architect_cortex(
    user_message: str,
    project: Optional[Dict[str, Any]] = None,
    brand_dna: Optional[Dict[str, Any]] = None,
) -> AsyncGenerator[str, None]:
    """SSE wrapper for the orchestrator."""
    yield _sse("cortex_started", {"cortex": "architect"})
    yield _sse("cortex_step", {"cortex": "architect", "step": "designing",
                                "ar": "🏛️ أصمم البنية المعمارية..."})
    arch = await design_architecture(user_message, brand_dna)
    yield _sse("cortex_step", {"cortex": "architect", "step": "blueprint_ready",
                                "complexity": arch.get("complexity_score"),
                                "estimated_files": arch.get("estimated_files"),
                                "estimated_credits": arch.get("estimated_credits")})
    yield _sse("architecture_blueprint", arch)
    yield _sse("done", {
        "summary": render_architecture_summary_ar(arch),
        "credits_charged": 8,
        "auto_refunded": False,
        "model_used": "architect_cortex/claude-sonnet-4-5",
        "iterations": 1,
        "options": [],
        "inline_images": [],
        "architecture": arch,
    })
