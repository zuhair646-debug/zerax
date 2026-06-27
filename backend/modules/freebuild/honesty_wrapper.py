"""
🛡️ Honesty Wrapper — prevents the AI from claiming "done / working / published"
without actually verifying its work via the verification tools available to it.

Owner directive (Arabic, Saudi): the AI MUST not lie. If it says
"خلّصت / جاهز / يشتغل / نشرت", it must have actually run a verification tool
(test_page, verify_my_work, validate_html, audit_html, or check_navigation_graph)
during the SAME turn. Otherwise the wrapper:

  1. Logs the violation.
  2. Returns an Arabic system-style nudge that gets injected on the next turn
     forcing the AI to actually verify before re-asserting.

The wrapper is invoked from the chat loop right after assembling the final
text (before the `done` SSE event is emitted). It is read-only: it never
mutates the AI's text — it only emits a `honesty_check` SSE event and adds
an injection to be picked up next turn if violated.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

# Claim phrases the AI uses to declare completion.
_CLAIM_PHRASES_AR = (
    "خلصت", "خلّصت", "أنجزت", "أكملت", "جاهز", "تم بنجاح", "نشرت", "نشرته",
    "شغّال", "يشتغل", "اختبرت", "تم الاختبار", "تم النشر",
    "الموقع جاهز", "التطبيق جاهز", "كل شي تمام", "كل شيء تمام",
    "all done", "it works", "deployed successfully", "verified",
)

# Tools that count as "real verification" — actually exercising the work.
_VERIFICATION_TOOLS = {
    "test_page",                   # Playwright sanity test
    "verify_my_work",              # AI's self-grading
    "validate_html",               # structural validation
    "audit_html",                  # deeper audit
    "check_navigation_graph",      # links/nav check
    "call_self_test_agent",        # generated browser scenarios
    "recursive_test_agent",        # full QA pass
    "iterative_test_and_fix",      # test→fix→retest loop
    "compare_visuals",             # visual regression
    "capture_visual_snapshot",     # visual evidence
    "validate_js_handlers",        # JS handlers check
}

# Tools where the result itself is verification (e.g. deploy that returned
# `ok:true` from a real API call — that's evidence).
_DEPLOY_TOOLS = {
    "publish_site",
    "deploy_to_vercel",
    "deploy_to_cloudflare_pages",
    "deploy_to_github_pages",
    "deploy_to_production",
}


def claims_completion(text: str) -> bool:
    """True if the AI's text contains a completion claim."""
    if not text:
        return False
    txt = (text or "").lower()
    for phrase in _CLAIM_PHRASES_AR:
        if phrase.lower() in txt:
            return True
    return False


def verification_evidence(tool_log: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Return a structured proof-of-verification report from the turn's tool log.

    The chat loop appends every tool call to `ctx.tool_log` as
    `{"name": ..., "args": ..., "result": {...}}`. We scan it for verification
    or successful deploy tool calls.
    """
    if not tool_log:
        return {"verified": False, "verification_tools_used": [], "deploys_succeeded": []}
    verif_used: List[str] = []
    deploys_ok: List[Dict[str, Any]] = []
    for entry in tool_log:
        name = (entry or {}).get("name")
        result = (entry or {}).get("result") or {}
        if name in _VERIFICATION_TOOLS:
            verif_used.append(name)
        elif name in _DEPLOY_TOOLS and result.get("ok") is True:
            deploys_ok.append({
                "tool": name,
                "url": result.get("url"),
                "provider": result.get("provider", name),
            })
    return {
        "verified": bool(verif_used) or bool(deploys_ok),
        "verification_tools_used": verif_used,
        "deploys_succeeded": deploys_ok,
    }


def build_honesty_violation_nudge(claim_excerpt: str, evidence: Dict[str, Any]) -> str:
    """Compose the corrective Arabic message that will be injected next turn."""
    excerpt = (claim_excerpt or "").strip()[:120]
    return (
        "🛡️ **فحص الصدق (Honesty Check)** — قلتَ شيئاً يدل على إكمال العمل "
        f"(«{excerpt}»…) لكنك لم تستدعِ **أي أداة تحقق فعلية في هذا الدور**.\n\n"
        "هذا غير مقبول. القاعدة الذهبية:\n"
        "**ممنوع تقول «خلّصت / جاهز / يشتغل / نشرت» قبل ما تستدعي واحدة من:**\n"
        "  • `test_page` — يفتح الصفحة في Playwright ويقطع لقطة فعلية\n"
        "  • `verify_my_work` — يجمع كل المؤشرات (روابط، JS، صور)\n"
        "  • `validate_html` أو `audit_html` — للفحص البنيوي\n"
        "  • أو نشر فعلي عبر `publish_site`/`deploy_to_*` وترجع `ok:true` بـ URL\n\n"
        "🧠 **القاعدة التي يجب أن تتعلمها:** في كل دور تقول فيه «جاهز»، لازم "
        "تستدعي على الأقل أداة تحقق واحدة قبلها. وإلا أنت تكذب على العميل."
    )
