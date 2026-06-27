"""
📘 TypeScript Cortex — converts JS to TS + generates tsconfig.

Capabilities:
  - Convert vanilla JS file → TypeScript with inferred types
  - Generate sensible tsconfig.json for browser projects
  - Generate type declarations for inline objects
  - Detect and suggest interface extraction
"""
from __future__ import annotations

import json
import logging
import os
import re
import uuid
from typing import Any, Dict, Optional

logger = logging.getLogger("zenrex.typescript")


_TS_CONVERT_PROMPT = """أنت TypeScript migration expert.

حوّل هذا الـ JS لـ TypeScript:
- استنتج الـ types من السياق
- استخرج interfaces للـ objects المتكررة
- استخدم strict mode (no any إلا للضرورة)
- احتفظ بنفس logic، فقط أضف types

أرجع الـ TS فقط داخل ```ts ... ``` بدون شرح.

```js
{code}
```"""


DEFAULT_TSCONFIG = {
    "compilerOptions": {
        "target": "ES2022",
        "module": "ESNext",
        "moduleResolution": "Bundler",
        "lib": ["ES2022", "DOM", "DOM.Iterable"],
        "strict": True,
        "noImplicitAny": True,
        "strictNullChecks": True,
        "esModuleInterop": True,
        "skipLibCheck": True,
        "forceConsistentCasingInFileNames": True,
        "isolatedModules": True,
        "resolveJsonModule": True,
        "allowSyntheticDefaultImports": True,
        "jsx": "react-jsx",
        "outDir": "./dist",
        "rootDir": "./src",
        "sourceMap": True,
        "declaration": True
    },
    "include": ["src/**/*"],
    "exclude": ["node_modules", "dist", "**/*.test.ts"]
}


def get_default_tsconfig() -> Dict[str, Any]:
    return DEFAULT_TSCONFIG.copy()


def render_tsconfig_json(custom_options: Optional[Dict[str, Any]] = None) -> str:
    """Return a tsconfig.json string. Merges custom_options into compilerOptions."""
    cfg = get_default_tsconfig()
    if custom_options:
        cfg["compilerOptions"].update(custom_options)
    return json.dumps(cfg, indent=2, ensure_ascii=False)


async def convert_js_to_ts(js_code: str) -> Optional[str]:
    """Convert JS code to TypeScript via Claude. Returns TS code or None."""
    emergent_key = os.environ.get("EMERGENT_LLM_KEY", "").strip()
    if not emergent_key:
        return None
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage  # type: ignore
        chat = LlmChat(
            api_key=emergent_key,
            session_id=f"ts_convert_{uuid.uuid4().hex[:8]}",
            system_message="أنت خبير TypeScript. تحوّل JS لـ TS مع types دقيقة.",
        ).with_model("anthropic", "claude-sonnet-4-5-20250929")
        resp = await chat.send_message(UserMessage(text=_TS_CONVERT_PROMPT.format(code=js_code[:5000])))
        raw = resp if isinstance(resp, str) else str(resp)
        m = re.search(r"```(?:ts|typescript)\n?([\s\S]+?)\n?```", raw)
        if m:
            return m.group(1).strip()
        return None
    except Exception as e:
        logger.warning(f"[typescript] convert failed: {e}")
        return None


def suggest_interfaces(js_code: str) -> Dict[str, Any]:
    """Heuristic: extract object literals from JS and suggest interface names."""
    suggestions = []
    # Find `const X = { ... }` patterns
    pattern = re.compile(r"(?:const|let|var)\s+(\w+)\s*=\s*\{([^{}]*?)\}", re.DOTALL)
    for m in pattern.finditer(js_code):
        var_name = m.group(1)
        body = m.group(2)
        # Get key names
        keys = re.findall(r"(\w+)\s*:", body)
        if len(keys) >= 2:
            iface_name = var_name[0].upper() + var_name[1:]
            suggestions.append({
                "variable": var_name,
                "interface": iface_name,
                "keys": keys[:10],
            })
    return {"interfaces_suggested": suggestions, "count": len(suggestions)}
