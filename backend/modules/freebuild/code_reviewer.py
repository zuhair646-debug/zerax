"""
Code Reviewer — الذكاء #2.3
Pre-commit code review pass for HTML mutations.

Architecture role:
    AI #3 (Builder, Claude Sonnet 4.5) produces HTML via write_full_html →
    BEFORE applying to ctx.current_html, the proposed HTML is passed through
    THIS module. The reviewer (also Claude Sonnet 4.5 but with a strict
    "senior code reviewer" persona) returns:

        {
          "verdict": "approve" | "fix" | "reject",
          "score": 0-100,
          "issues": [{"severity": "critical|high|medium|low", "msg": "..."}],
          "improved_html": "..."   # only when verdict == "fix"
        }

Verdicts:
    approve → caller applies new_html as-is.
    fix     → caller applies improved_html instead, and the AI gets a
              system note telling it what was auto-fixed.
    reject  → caller rejects the change and returns an error to the AI so
              it re-attempts (must NEVER happen >2x — escalate to human after).

Cost guardrails:
    • Skipped on trivial changes (< MIN_REVIEWABLE_CHARS diff).
    • Skipped on the first build (no prior current_html — too little context).
    • Hard time-cap of 12s; on timeout we fall back to approve (graceful).
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("zenrex.freebuild.code_reviewer")

# Cost thresholds — review is ~$0.01 per call, so skip if the change is too small.
MIN_REVIEWABLE_CHARS = 400       # If the diff is smaller than this, skip review.
MAX_HTML_FOR_REVIEW = 60_000     # Truncate huge HTML to keep cost bounded.
REVIEW_TIMEOUT_SECONDS = 25


_REVIEWER_SYSTEM_PROMPT = """أنت مهندس برمجة سيوبر-سينيور (10+ سنوات خبرة) متخصص في مراجعة HTML/CSS/JS قبل تطبيق التغييرات.

دورك: **تراجع كود اقتُرح للتطبيق** على موقع منشور لعميل حقيقي، وتحدد:
1. هل يُطبَّق كما هو (approve)؟
2. هل يحتاج إصلاحات بسيطة تقدر تسويها أنت بنفسك (fix)؟
3. هل فيه أخطاء جسيمة ترفضه وترجع للمبرمج (reject)؟

أنت لا تكتب موقع من الصفر — تراجع فقط. ركّز على:

🔴 **حرج (critical):**
- HTML/CSS/JS syntax errors تكسر الصفحة
- ثغرات XSS (innerHTML بدون escape، script tags في user content)
- صفحات بلا content أساسي (<body> فاضي أو محتوى placeholder)
- روابط لصفحات غير موجودة في المشروع (404s)
- buttons أو forms بلا handler ولا backend

🟠 **مرتفع (high):**
- accessibility (alt مفقود، aria misuse، contrast منخفض)
- design inconsistency (نُسف الـ palette الموجود، خط مختلف فجأة)
- responsive كسور (overflow-x: hidden مفقود، fixed widths)
- الصورة الواحدة استخدامها أكثر من 3 مرات (يدل على lazy generation)

🟡 **متوسط (medium):**
- semantic HTML ضعيف (div spam بدل header/nav/main/footer)
- missing meta tags (viewport, description, og:image)
- inline styles كثيرة (>20) بدل CSS classes
- text content بصيغة generic ("Lorem ipsum", "محتوى هنا")

📤 **مخرجاتك يجب أن تكون JSON صرف ومضغوط، بدون أي تعليق إضافي:**

```json
{
  "verdict": "approve|fix|reject",
  "score": 0-100,
  "issues": [
    {"severity": "critical|high|medium|low", "msg": "وصف موجز للمشكلة + رقم السطر إن أمكن"}
  ],
  "improved_html": "..."
}
```

قواعد إلزامية:
- `improved_html` يُملأ **فقط** عند verdict=="fix"، ويجب أن يكون **كامل HTML من <!DOCTYPE> إلى </html>**.
- `score` >= 70 → approve. 35-69 → fix (أصلح وارجع). < 35 → reject (نادر جداً، فقط للكود المكسور فعلاً).
- لا تكتب أي تعليق أو شرح خارج الـ JSON. لا تستخدم Markdown fences.
- إذا الكود ممتاز ومافي ملاحظات: `{"verdict":"approve","score":95,"issues":[]}`
- كن صارم لكن **منصف** — لو الكود يعمل ومافيه عيوب جسيمة، approve. الـ reject فقط للكود اللي يكسر الموقع.
"""


def _diff_size(old: str, new: str) -> int:
    """Cheap "how much changed" estimator without doing a full diff."""
    return abs(len(new) - len(old)) + min(2000, abs(len(set(new[:5000].split())) - len(set(old[:5000].split()))))


def _strip_json_fences(text: str) -> str:
    """LLMs sometimes wrap JSON in ```json ... ``` despite instructions."""
    text = text.strip()
    m = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if m:
        return m.group(1).strip()
    return text


def _safe_parse(raw: str) -> Optional[Dict[str, Any]]:
    """Try multiple parsing strategies because LLMs are not RFC-perfect."""
    cleaned = _strip_json_fences(raw)
    try:
        return json.loads(cleaned)
    except Exception:
        pass
    # Fallback: extract first {...} block
    m = re.search(r"\{[\s\S]*\}", cleaned)
    if m:
        try:
            return json.loads(m.group(0))
        except Exception:
            return None
    return None


async def review_code_change(
    action: str,
    proposed_html: str,
    current_html: str = "",
    user_request: str = "",
    project_name: str = "",
    page_filename: str = "index.html",
) -> Dict[str, Any]:
    """Returns: {verdict, score, issues, improved_html?, skipped?, error?}.

    Never raises — on failure returns {"verdict": "approve", "skipped": True, "error": "..."}.
    """
    # Cost guard 1: tiny change → skip.
    diff = _diff_size(current_html, proposed_html)
    if diff < MIN_REVIEWABLE_CHARS and current_html:
        return {"verdict": "approve", "skipped": True, "reason": f"diff_too_small ({diff})", "score": 100, "issues": []}

    # Cost guard 2: brand-new project AND tiny proposed HTML → skip (no point reviewing 50 chars).
    if not current_html and len(proposed_html) < 1500:
        return {"verdict": "approve", "skipped": True, "reason": "first_build_tiny", "score": 100, "issues": []}

    # Cost guard 3: huge HTML → truncate.
    review_target = proposed_html
    if len(review_target) > MAX_HTML_FOR_REVIEW:
        review_target = review_target[:MAX_HTML_FOR_REVIEW] + "\n<!-- ...truncated... -->\n</body></html>"

    api_key_present = bool(
        (os.environ.get("ANTHROPIC_API_KEY") or "").strip()
        or (os.environ.get("EMERGENT_LLM_KEY") or "").strip()
    )
    if not api_key_present:
        logger.warning("[code-review] no Claude key (ANTHROPIC_API_KEY or EMERGENT_LLM_KEY) — skipping review")
        return {"verdict": "approve", "skipped": True, "error": "no_api_key", "score": 100, "issues": []}

    try:
        # Lazy import — keeps the module light when reviewer is disabled.
        from modules.shared.claude_simple import ask_claude  # type: ignore
    except Exception as e:
        logger.warning(f"[code-review] claude_simple unavailable: {e}")
        return {"verdict": "approve", "skipped": True, "error": "lib_unavailable", "score": 100, "issues": []}

    session_id = f"reviewer-{project_name or 'anon'}-{action}"
    user_msg_text = (
        f"# مشروع: {project_name or '(بدون اسم)'}  •  صفحة: {page_filename}  •  أداة: {action}\n\n"
        f"## طلب العميل الأصلي:\n{user_request[:600] if user_request else '(غير محدد)'}\n\n"
        f"## الكود الحالي (قبل التعديل) — أول 2000 حرف:\n```html\n{(current_html or '')[:2000]}\n```\n\n"
        f"## الكود المقترح للتطبيق — كامل:\n```html\n{review_target}\n```\n\n"
        f"راجع الكود المقترح بصرامة وأرجع JSON النتيجة فقط."
    )

    try:
        raw_response = await asyncio.wait_for(
            ask_claude(
                system=_REVIEWER_SYSTEM_PROMPT,
                user_message=user_msg_text,
                session_id=session_id,
                max_tokens=8000,
                timeout=REVIEW_TIMEOUT_SECONDS,
            ),
            timeout=REVIEW_TIMEOUT_SECONDS + 5,
        )
    except asyncio.TimeoutError:
        logger.warning(f"[code-review] timed out after {REVIEW_TIMEOUT_SECONDS}s — defaulting to approve")
        return {"verdict": "approve", "skipped": True, "error": "timeout", "score": 100, "issues": []}
    except Exception as e:
        logger.exception(f"[code-review] LLM call failed: {e}")
        return {"verdict": "approve", "skipped": True, "error": str(e)[:200], "score": 100, "issues": []}

    if not isinstance(raw_response, str) or not raw_response.strip():
        return {"verdict": "approve", "skipped": True, "error": "empty_response", "score": 100, "issues": []}

    parsed = _safe_parse(raw_response)
    if not isinstance(parsed, dict):
        logger.warning(f"[code-review] couldn't parse JSON, raw[:200]={raw_response[:200]}")
        return {"verdict": "approve", "skipped": True, "error": "unparseable", "score": 100, "issues": []}

    verdict = (parsed.get("verdict") or "approve").lower()
    if verdict not in ("approve", "fix", "reject"):
        verdict = "approve"
    score = int(parsed.get("score") or 100)
    issues = parsed.get("issues") or []
    improved = parsed.get("improved_html")

    # Sanity check: if verdict=="fix" but improved_html is missing/invalid, downgrade to "approve" with warning.
    if verdict == "fix":
        if not isinstance(improved, str) or "<html" not in improved.lower() or "</html>" not in improved.lower():
            logger.warning("[code-review] verdict=fix but improved_html invalid → downgrading to approve")
            verdict = "approve"
            improved = None

    out = {
        "verdict": verdict,
        "score": score,
        "issues": issues if isinstance(issues, list) else [],
    }
    if verdict == "fix" and improved:
        out["improved_html"] = improved
    return out


def render_review_summary(review: Dict[str, Any]) -> str:
    """Compact human-readable summary used in chat / logs."""
    if review.get("skipped"):
        return f"⏭️ تخطّى المراجعة ({review.get('reason') or review.get('error') or 'صغير جداً'})"
    verdict = review.get("verdict", "approve")
    score = review.get("score", 100)
    issues = review.get("issues") or []
    crit = sum(1 for i in issues if (i.get("severity") or "").lower() == "critical")
    high = sum(1 for i in issues if (i.get("severity") or "").lower() == "high")
    badge = {"approve": "✅", "fix": "🛠️", "reject": "❌"}.get(verdict, "❓")
    parts = [f"{badge} المراجع: {verdict.upper()} (score: {score}/100)"]
    if crit or high:
        parts.append(f"حرج: {crit}، مرتفع: {high}")
    return " · ".join(parts)
