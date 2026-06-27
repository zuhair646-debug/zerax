"""
🔁 Stack-Trace Auto-Fix Loop.

When code execution fails:
  1. Parse the stack trace (file, line, error_type, message).
  2. Call Claude with the failing code + parsed error → request a fix.
  3. Re-run the code in the sandbox.
  4. If still failing, repeat (max 3 attempts).
  5. If all attempts fail, return original error + final attempt.

Used by:
  - Test Generator Cortex (when generated tests fail)
  - CodeCortex (when validation step finds runtime errors)
"""
from __future__ import annotations

import json
import logging
import os
import re
import uuid
from typing import Any, Awaitable, Callable, Dict, List, Optional

from .code_sandbox import parse_stack_trace

logger = logging.getLogger("zenrex.autofix")


_FIX_PROMPT = """أنت Senior JS/Python debugger.

الكود التالي رمى Error. أصلحه وأرجع الكود الكامل بعد الإصلاح **بدون أي شرح**.

**الخطأ:**
{error_type}: {error_message}
{file}:{line}

**الـ stderr الكامل:**
```
{stderr}
```

**الكود الحالي:**
```{language}
{code}
```

أرجع الكود الكامل بعد الإصلاح فقط، داخل ```{language} ... ```. **لا تشرح**."""


async def autofix_loop(
    code: str,
    runner: Callable[[str], Awaitable[Dict[str, Any]]],
    language: str = "js",
    max_attempts: int = 3,
) -> Dict[str, Any]:
    """Execute → if fails, fix via LLM → re-execute. Max 3 cycles.

    Args:
        code: initial code string
        runner: async function that takes code → returns {ok, stdout, stderr}
        language: 'js' or 'python'
        max_attempts: how many fix tries before giving up

    Returns:
        {
          "final_code": str,
          "ok": bool,
          "attempts": [{code, result, fix_explanation}, ...],
          "total_attempts": int,
        }
    """
    attempts: List[Dict[str, Any]] = []
    current = code

    for i in range(max_attempts):
        result = await runner(current)
        attempts.append({"attempt": i + 1, "code_preview": current[:200], "ok": result.get("ok", False),
                          "stderr_preview": result.get("stderr", "")[:200]})

        if result.get("ok"):
            return {
                "final_code": current,
                "ok": True,
                "attempts": attempts,
                "total_attempts": i + 1,
            }

        # Parse stack trace
        parsed = parse_stack_trace(result.get("stderr", ""))
        if i + 1 >= max_attempts:
            break  # don't fix on the last attempt

        # Request fix from LLM
        fixed = await _request_fix(
            code=current,
            error_type=parsed.get("error_type") or "Error",
            error_message=parsed.get("error_message") or "Unknown error",
            file=parsed.get("file") or "code",
            line=parsed.get("line") or 0,
            stderr=result.get("stderr", ""),
            language=language,
        )
        if not fixed or fixed == current:
            break  # LLM couldn't fix → bail
        current = fixed

    return {
        "final_code": current,
        "ok": False,
        "attempts": attempts,
        "total_attempts": len(attempts),
        "final_stderr": attempts[-1].get("stderr_preview", "") if attempts else "",
    }


async def _request_fix(
    code: str, error_type: str, error_message: str,
    file: str, line: int, stderr: str, language: str = "js",
) -> Optional[str]:
    """Ask Claude to fix the code. Returns the new code or None."""
    emergent_key = os.environ.get("EMERGENT_LLM_KEY", "").strip()
    if not emergent_key:
        return None

    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage  # type: ignore
        chat = LlmChat(
            api_key=emergent_key,
            session_id=f"autofix_{uuid.uuid4().hex[:8]}",
            system_message="أنت debugger خبير. أصلح الأخطاء بأقل تغيير ممكن.",
        ).with_model("anthropic", "claude-sonnet-4-5-20250929")
        prompt = _FIX_PROMPT.format(
            error_type=error_type,
            error_message=error_message,
            file=file,
            line=line,
            stderr=(stderr or "")[:1500],
            language=language,
            code=code[:4000],
        )
        resp = await chat.send_message(UserMessage(text=prompt))
        raw = resp if isinstance(resp, str) else str(resp)
        # Extract code block
        m = re.search(r"```(?:" + language + r")?\n?([\s\S]+?)\n?```", raw)
        if m:
            return m.group(1).strip()
        # Fallback: raw response if no fence
        return raw.strip() if raw.strip() else None
    except Exception as e:
        logger.warning(f"[autofix] LLM fix failed: {e}")
        return None
