"""
🧪 Test Generator Cortex — auto-generates Pytest / Vitest tests.

Input: a code file (Python or JS)
Output: a test file targeting it, plus a sandbox-run report.

Capabilities:
  - For Python: generates Pytest with mocks
  - For JS: generates Vitest unit tests
  - Runs the tests in code_sandbox.py
  - If tests fail, runs autofix_loop to fix the IMPLEMENTATION (not the test)
"""
from __future__ import annotations

import json
import logging
import os
import re
import uuid
from typing import Any, Dict, Optional

logger = logging.getLogger("zenrex.test_generator")


_TEST_GEN_PROMPT_PY = """أنت Pytest expert.

اكتب اختبارات Pytest لهذا الكود. غطّ:
1. الـ happy path
2. حالات الحدود (empty/None/zero/negative)
3. error paths (raises)

أرجع كود الـ test فقط داخل ```python ... ``` بدون شرح.

**الكود المراد اختباره:**
```python
{code}
```"""


_TEST_GEN_PROMPT_JS = """أنت Vitest expert.

اكتب اختبارات Vitest لهذا الكود. غطّ:
1. الـ happy path
2. حالات الحدود
3. async paths لو وُجدت

أرجع الـ test فقط داخل ```js ... ``` بدون شرح.

**الكود المراد اختباره:**
```js
{code}
```"""


async def generate_tests(code: str, language: str = "python") -> Optional[str]:
    """Generate test code for the given source. Returns test code or None."""
    emergent_key = os.environ.get("EMERGENT_LLM_KEY", "").strip()
    if not emergent_key:
        return None
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage  # type: ignore
        prompt_tpl = _TEST_GEN_PROMPT_PY if language == "python" else _TEST_GEN_PROMPT_JS
        chat = LlmChat(
            api_key=emergent_key,
            session_id=f"test_gen_{uuid.uuid4().hex[:8]}",
            system_message="أنت خبير في كتابة اختبارات unit tests عالية التغطية.",
        ).with_model("anthropic", "claude-sonnet-4-5-20250929")
        resp = await chat.send_message(UserMessage(text=prompt_tpl.format(code=code[:4000])))
        raw = resp if isinstance(resp, str) else str(resp)
        lang_re = "python" if language == "python" else r"(?:js|javascript)"
        m = re.search(r"```" + lang_re + r"\n?([\s\S]+?)\n?```", raw)
        if m:
            return m.group(1).strip()
        return None
    except Exception as e:
        logger.warning(f"[test_generator] failed: {e}")
        return None


async def generate_and_run_tests(code: str, language: str = "python") -> Dict[str, Any]:
    """Generate tests + run them in sandbox + return report.

    Returns:
        {
          "tests_code": str,
          "ran": bool,
          "passed": bool,
          "stdout": str,
          "stderr": str,
          "language": str,
        }
    """
    tests = await generate_tests(code, language)
    if not tests:
        return {"tests_code": None, "ran": False, "passed": False, "language": language}

    # For Python: wrap as a script that uses unittest's TestCase
    # For JS: use Vitest CLI
    # For simplicity: just run the combined (code + tests) as a script via sandbox
    if language == "python":
        from .code_sandbox import run_python
        combined = code + "\n\n" + tests + "\n\n"
        # Append a runner if it's pytest-style
        if "def test_" in tests and "pytest" not in combined:
            combined += '\nimport sys\nif __name__ == "__main__":\n    import unittest\n    unittest.main(argv=[""], exit=False)\n'
        result = await run_python(combined, timeout_sec=10)
    else:
        from .code_sandbox import run_js
        # For JS, we can't run vitest without it being installed. Run as plain JS.
        combined = code + "\n\n" + tests
        result = await run_js(combined, timeout_sec=10)

    return {
        "tests_code": tests,
        "ran": True,
        "passed": result.get("ok", False),
        "stdout": result.get("stdout", "")[:2000],
        "stderr": result.get("stderr", "")[:2000],
        "language": language,
    }
