"""
⚛️ Next.js Cortex — generates a complete Next.js 15 (App Router) project.

Outputs a file tree:
  - app/layout.tsx
  - app/page.tsx
  - app/[route]/page.tsx
  - components/<Name>.tsx
  - lib/utils.ts
  - tailwind.config.ts
  - package.json
  - next.config.mjs

Uses Tailwind CSS + shadcn/ui patterns by default.
LLM-driven: takes a brief + brand_dna + architecture blueprint → produces files.
"""
from __future__ import annotations

import json
import logging
import os
import re
import uuid
from typing import Any, Dict, List, Optional

logger = logging.getLogger("zenrex.nextjs_cortex")


_NEXTJS_PROMPT = """أنت Next.js 15 (App Router) expert.

اعطني المشروع كاملاً (كل الملفات) كـ JSON بهذا الشكل:

{
  "files": {
    "app/layout.tsx": "...",
    "app/page.tsx": "...",
    "components/Hero.tsx": "...",
    "lib/utils.ts": "...",
    "package.json": "...",
    "tailwind.config.ts": "...",
    "next.config.mjs": "..."
  },
  "install_commands": ["npm install"],
  "dev_command": "npm run dev",
  "notes": "ملاحظات للمستخدم"
}

**القواعد:**
- TypeScript strict
- Tailwind CSS فقط للستايل
- Server Components افتراضي، 'use client' فقط لـ interactivity
- استخدم Lucide icons
- File names بصيغة kebab-case أو PascalCase حسب الـ convention
- لا تستخدم external libs كثيرة (limit to 3-5 deps)

ارجع JSON فقط بدون شرح."""


async def generate_nextjs_project(
    brief: str,
    brand_dna: Optional[Dict[str, Any]] = None,
    architecture: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    """Generate a complete Next.js project from a brief."""
    emergent_key = os.environ.get("EMERGENT_LLM_KEY", "").strip()
    if not emergent_key:
        return None

    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage  # type: ignore

        ctx_parts = [f"Brief: {brief[:1000]}"]
        if brand_dna:
            ctx_parts.append(f"Brand DNA: {json.dumps(brand_dna, ensure_ascii=False)[:500]}")
        if architecture:
            ctx_parts.append(f"Architecture: {json.dumps(architecture, ensure_ascii=False)[:600]}")
        ctx = "\n\n".join(ctx_parts)

        chat = LlmChat(
            api_key=emergent_key,
            session_id=f"nextjs_{uuid.uuid4().hex[:8]}",
            system_message=_NEXTJS_PROMPT,
        ).with_model("anthropic", "claude-sonnet-4-5-20250929")
        resp = await chat.send_message(UserMessage(text=ctx))
        raw = resp if isinstance(resp, str) else str(resp)
        m = re.search(r"\{[\s\S]*\}", raw)
        if m:
            try:
                data = json.loads(m.group(0))
                if "files" in data:
                    return data
            except Exception as e:
                logger.warning(f"[nextjs_cortex] JSON parse failed: {e}")
    except Exception as e:
        logger.warning(f"[nextjs_cortex] LLM call failed: {e}")
    return None


def default_package_json(project_name: str = "zenrex-app") -> str:
    return json.dumps({
        "name": project_name,
        "version": "0.1.0",
        "private": True,
        "scripts": {
            "dev": "next dev",
            "build": "next build",
            "start": "next start",
            "lint": "next lint"
        },
        "dependencies": {
            "react": "^18.3.1",
            "react-dom": "^18.3.1",
            "next": "^15.0.0",
            "lucide-react": "^0.460.0",
            "clsx": "^2.1.1",
            "tailwind-merge": "^2.5.4"
        },
        "devDependencies": {
            "typescript": "^5.6.0",
            "@types/node": "^22.0.0",
            "@types/react": "^18.3.0",
            "@types/react-dom": "^18.3.0",
            "tailwindcss": "^3.4.14",
            "postcss": "^8.4.47",
            "autoprefixer": "^10.4.20"
        }
    }, indent=2)


def default_tailwind_config(palette: Any = None) -> str:
    """Accept palette as either a list of hex strings (legacy) OR a dict like
    {primary, secondary, accent, background, text} (canonical brand_dna shape).
    Auto-normalizes to a list before generating Tailwind config.
    """
    colors = {}
    if palette:
        if isinstance(palette, dict):
            # Canonical brand_dna palette shape — extract hex string values
            palette_list = [v for v in palette.values() if isinstance(v, str) and v.startswith("#")]
            # Preserve semantic names if present (primary/secondary/accent)
            for name, val in palette.items():
                if isinstance(val, str) and val.startswith("#") and name in ("primary", "secondary", "accent", "background", "text"):
                    colors[name] = val
            # Fallback to brand-N for any remaining hex values
            for i, c in enumerate(palette_list[:5]):
                colors.setdefault(f"brand-{i+1}", c)
        elif isinstance(palette, (list, tuple)):
            for i, c in enumerate(palette[:5]):
                if isinstance(c, str):
                    colors[f"brand-{i+1}"] = c
    cfg = (
        "import type { Config } from 'tailwindcss';\n\n"
        "const config: Config = {\n"
        "  content: ['./app/**/*.{ts,tsx}', './components/**/*.{ts,tsx}'],\n"
        "  theme: {\n"
        "    extend: {\n"
        f"      colors: {json.dumps(colors, indent=8) if colors else '{}'},\n"
        "      fontFamily: { sans: ['Inter', 'sans-serif'], display: ['Cairo', 'sans-serif'] }\n"
        "    }\n"
        "  },\n"
        "  plugins: []\n"
        "};\n\n"
        "export default config;\n"
    )
    return cfg
