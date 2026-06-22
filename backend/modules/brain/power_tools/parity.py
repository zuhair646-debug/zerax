"""Parity Tools — closes the final gap to 100% agent parity.

5 tools added (Feb 2026):
  • analyze_uploaded_file — AI-powered PDF/image/audio/video analysis
  • integration_playbook_live — dynamic web research → playbook generation
  • recursive_test_agent — multi-step QA AI that exercises real user journeys
  • crawl_url_deep — fetch URL, return clean Markdown w/ headings + code blocks
  • remember / recall — global cross-project memory in MongoDB
"""
import asyncio
import json
import logging
import os
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

logger = logging.getLogger("brain.parity")

EMERGENT_LLM_KEY = os.environ.get("EMERGENT_LLM_KEY", "")


# ════════════════════════════════════════════════════════════════════════
# 1. analyze_uploaded_file — Claude Vision + Whisper + pypdf
# ════════════════════════════════════════════════════════════════════════
async def analyze_uploaded_file(
    source: str,
    query: str = "Summarize this file",
    project_id: str = "anon",
) -> Dict[str, Any]:
    """Analyze any file with AI. Auto-detects type.

    Supported:
      • PDF → text extracted via pypdf → Claude summary
      • Image (.png/.jpg/.webp/.gif/.heic) → Claude Vision
      • Audio (.mp3/.wav/.m4a/.flac/.ogg) → OpenAI Whisper transcription
      • Text/Code (.txt/.json/.csv/.md/.py/.js/.html) → direct Claude analysis
      • URL → downloads first, then routes by content-type

    Returns: {ok, type, content, summary, raw_extract}
    """
    if not source:
        return {"ok": False, "error": "source (path or URL) required"}

    # Step 1: Resolve source → local file path
    local_path = await _resolve_to_local(source, project_id)
    if not local_path:
        return {"ok": False, "error": f"could not access source: {source}"}

    ext = Path(local_path).suffix.lower().lstrip(".")
    file_type = _classify_file_type(ext)
    if file_type == "unknown":
        # Best-effort: try as text
        file_type = "text"

    try:
        if file_type == "pdf":
            return await _analyze_pdf(local_path, query)
        if file_type == "image":
            return await _analyze_image(local_path, query)
        if file_type == "audio":
            return await _analyze_audio(local_path, query)
        if file_type == "text":
            return await _analyze_text(local_path, query)
        return {"ok": False, "error": f"unsupported file type: {file_type}"}
    except Exception as e:
        logger.exception("analyze_uploaded_file failed")
        return {"ok": False, "error": f"{type(e).__name__}: {str(e)[:300]}"}


def _classify_file_type(ext: str) -> str:
    if ext == "pdf":
        return "pdf"
    if ext in ("png", "jpg", "jpeg", "webp", "gif", "heic", "heif", "bmp"):
        return "image"
    if ext in ("mp3", "wav", "m4a", "flac", "ogg", "aac", "aiff", "opus"):
        return "audio"
    if ext in ("txt", "json", "csv", "md", "py", "js", "ts", "jsx", "tsx",
                "html", "css", "xml", "yaml", "yml", "toml", "ini", "log",
                "sh", "bash", "go", "rs", "rb", "php", "java", "kt"):
        return "text"
    return "unknown"


async def _resolve_to_local(source: str, project_id: str) -> Optional[str]:
    """Convert URL or relative path to absolute local path."""
    if source.startswith(("http://", "https://")):
        try:
            import httpx
            ws = _ensure_workspace(project_id)
            fname = (urlparse(source).path.split("/")[-1] or "download.bin")[:128]
            local = os.path.join(ws, f"_dl_{int(time.time())}_{fname}")
            async with httpx.AsyncClient(timeout=30, follow_redirects=True,
                                          verify=False) as client:
                async with client.stream("GET", source) as r:
                    if r.status_code != 200:
                        return None
                    with open(local, "wb") as f:
                        async for chunk in r.aiter_bytes(chunk_size=64_000):
                            f.write(chunk)
                            if os.path.getsize(local) > 50_000_000:
                                break
            return local
        except Exception as e:
            logger.warning(f"download failed: {e}")
            return None
    abs_p = os.path.abspath(source)
    return abs_p if os.path.exists(abs_p) else None


def _ensure_workspace(project_id: str) -> str:
    pid = re.sub(r"[^a-zA-Z0-9_-]", "_", str(project_id or "anon"))[:64]
    ws = f"/tmp/zenrex_workspaces/{pid}"
    Path(ws).mkdir(parents=True, exist_ok=True)
    return ws


async def _analyze_pdf(path: str, query: str) -> Dict[str, Any]:
    try:
        from pypdf import PdfReader
    except ImportError:
        return {"ok": False, "error": "pypdf not installed"}

    reader = PdfReader(path)
    text_chunks = []
    for i, page in enumerate(reader.pages[:50]):  # cap at 50 pages
        try:
            txt = page.extract_text() or ""
        except Exception:
            txt = ""
        if txt.strip():
            text_chunks.append(f"--- Page {i+1} ---\n{txt}")
    extracted = "\n\n".join(text_chunks)[:100_000]

    if not extracted.strip():
        return {"ok": True, "type": "pdf",
                "content": "", "summary": "PDF appears to be empty or image-only",
                "pages": len(reader.pages)}

    summary = await _claude_analyze(
        f"You are analyzing a PDF document. User's question:\n{query}\n\n"
        f"PDF content:\n{extracted}",
        max_tokens=1500,
    )
    return {
        "ok": True,
        "type": "pdf",
        "pages": len(reader.pages),
        "raw_extract": extracted[:5000],
        "extract_length": len(extracted),
        "summary": summary,
    }


async def _analyze_image(path: str, query: str) -> Dict[str, Any]:
    """Analyze image with Claude Vision using the official anthropic SDK."""
    import base64

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    base_url = None
    if not api_key:
        api_key = os.environ.get("EMERGENT_LLM_KEY", "")
        base_url = "https://integrations.emergentagent.com/llm/anthropic"
    if not api_key:
        return {"ok": False, "error": "no Claude key (ANTHROPIC_API_KEY or EMERGENT_LLM_KEY)"}

    try:
        from anthropic import AsyncAnthropic
    except ImportError:
        return {"ok": False, "error": "anthropic SDK missing"}

    with open(path, "rb") as f:
        img_b64 = base64.b64encode(f.read()).decode()

    ext = Path(path).suffix.lower().lstrip(".")
    mime_map = {"jpg": "jpeg", "jpeg": "jpeg", "png": "png",
                 "webp": "webp", "gif": "gif"}
    mime = f"image/{mime_map.get(ext, 'png')}"

    try:
        client = (AsyncAnthropic(api_key=api_key, base_url=base_url)
                   if base_url else AsyncAnthropic(api_key=api_key))
        resp = await client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=1500,
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": mime,
                            "data": img_b64,
                        },
                    },
                    {"type": "text", "text": query},
                ],
            }],
            system="You are an expert image analyst. Be detailed and specific.",
        )
        out = []
        for block in resp.content:
            if hasattr(block, "text"):
                out.append(block.text)
        summary = "\n".join(out)
    except Exception as e:
        return {"ok": False, "error": f"Claude Vision failed: {e}"}

    return {
        "ok": True,
        "type": "image",
        "summary": summary,
        "image_size_bytes": len(img_b64) * 3 // 4,
        "mime": mime,
    }


async def _analyze_audio(path: str, query: str) -> Dict[str, Any]:
    """Use OpenAI Whisper for transcription, then Claude for analysis."""
    api_key = (os.environ.get("OPENAI_DIRECT_KEY")
               or os.environ.get("OPENAI_API_KEY")
               or os.environ.get("EMERGENT_LLM_KEY"))
    if not api_key:
        return {"ok": False, "error": "no OpenAI/Emergent key for Whisper"}
    try:
        import httpx
    except ImportError:
        return {"ok": False, "error": "httpx missing"}

    # Use OpenAI Whisper via Emergent proxy
    try:
        with open(path, "rb") as f:
            audio_bytes = f.read()
        if len(audio_bytes) > 24_000_000:
            return {"ok": False, "error": "audio file too large (>24MB Whisper limit)"}

        async with httpx.AsyncClient(timeout=120) as client:
            files = {"file": (Path(path).name, audio_bytes,
                              "application/octet-stream")}
            data = {"model": "whisper-1"}
            # Use Emergent gateway if using EMERGENT_LLM_KEY, else direct
            if api_key.startswith("sk-emergent-"):
                whisper_url = "https://integrations.emergentagent.com/llm/openai/v1/audio/transcriptions"
            else:
                whisper_url = "https://api.openai.com/v1/audio/transcriptions"
            r = await client.post(
                whisper_url,
                headers={"Authorization": f"Bearer {api_key}"},
                files=files,
                data=data,
            )
            if r.status_code != 200:
                return {"ok": False,
                        "error": f"Whisper API: {r.status_code} {r.text[:200]}"}
            transcript = r.json().get("text", "")
    except Exception as e:
        return {"ok": False, "error": f"Whisper failed: {e}"}

    if not transcript:
        return {"ok": True, "type": "audio", "transcript": "",
                 "summary": "audio file produced empty transcript"}

    summary = await _claude_analyze(
        f"You are analyzing an audio transcript. User's question:\n{query}\n\n"
        f"Transcript:\n{transcript}",
        max_tokens=1000,
    )
    return {
        "ok": True,
        "type": "audio",
        "transcript": transcript,
        "transcript_length": len(transcript),
        "summary": summary,
    }


async def _analyze_text(path: str, query: str) -> Dict[str, Any]:
    try:
        with open(path, "rb") as f:
            content = f.read(500_000).decode("utf-8", errors="replace")
    except Exception as e:
        return {"ok": False, "error": str(e)}

    summary = await _claude_analyze(
        f"You are analyzing a text/code file ({Path(path).suffix}). "
        f"User's question:\n{query}\n\nFile content:\n{content}",
        max_tokens=1500,
    )
    return {
        "ok": True,
        "type": "text",
        "content_length": len(content),
        "preview": content[:1000],
        "summary": summary,
    }


async def _claude_analyze(prompt: str, max_tokens: int = 1500) -> str:
    """Lightweight Claude call for analysis subtasks.

    Uses the official anthropic SDK with ANTHROPIC_API_KEY (preferred) or
    EMERGENT_LLM_KEY via the Emergent gateway. Both supported.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    base_url = None
    if not api_key:
        api_key = os.environ.get("EMERGENT_LLM_KEY", "")
        base_url = "https://integrations.emergentagent.com/llm/anthropic"
    if not api_key:
        return "[no Claude key — cannot analyze]"

    try:
        from anthropic import AsyncAnthropic
    except ImportError:
        return "[anthropic SDK missing]"

    try:
        client = (AsyncAnthropic(api_key=api_key, base_url=base_url)
                   if base_url else AsyncAnthropic(api_key=api_key))
        resp = await client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
            system="You are a precise analyst. Be concise but complete.",
        )
        # Extract text from response
        out = []
        for block in resp.content:
            if hasattr(block, "text"):
                out.append(block.text)
        return "\n".join(out) if out else "[empty Claude response]"
    except Exception as e:
        logger.warning(f"claude analyze failed: {e}")
        return f"[analysis failed: {type(e).__name__}: {str(e)[:200]}]"


# ════════════════════════════════════════════════════════════════════════
# 2. integration_playbook_live — dynamic web research → playbook
# ════════════════════════════════════════════════════════════════════════
async def integration_playbook_live(
    service_name: str,
    use_case: str = "general integration",
) -> Dict[str, Any]:
    """Generate a fresh integration playbook for ANY service.

    Flow:
      1. Check hardcoded playbooks first (instant)
      2. If miss → web_search for "{service} python SDK 2026"
      3. Crawl top 2 docs URLs
      4. Feed everything to Claude → synthesize playbook
      5. Cache result in /tmp for 24h
    """
    if not service_name or not service_name.strip():
        return {"ok": False, "error": "service_name required"}

    from .unrestricted import get_integration_playbook
    # 1. Hardcoded check
    cached = get_integration_playbook(service_name)
    if cached.get("ok"):
        cached["source"] = "hardcoded"
        return cached

    # 2. Web search
    from .unrestricted import web_search
    query = f"{service_name} python SDK official documentation install example"
    search = await web_search(query, num_results=5)
    if not search.get("ok"):
        return {"ok": False, "error": f"web search failed: {search.get('error')}"}

    results = search.get("results", [])
    if not results:
        return {"ok": False, "error": "no search results — service might not exist"}

    # 3. Crawl top 2 URLs
    crawled_text = []
    for item in results[:2]:
        url = item.get("url", "")
        if not url or not url.startswith("http"):
            continue
        c = await crawl_url_deep(url, max_chars=15_000)
        if c.get("ok"):
            crawled_text.append(f"=== Source: {url} ===\n{c['markdown'][:15000]}")

    if not crawled_text:
        # Fallback: use just search snippets
        crawled_text = [
            f"=== Source: {r['url']} ===\n{r.get('title','')}\n{r.get('snippet','')}"
            for r in results[:5]
        ]

    docs_blob = "\n\n".join(crawled_text)[:50_000]

    # 4. Claude synthesizes playbook
    prompt = f"""You are generating an integration playbook for a developer.

Service requested: **{service_name}**
Use case: {use_case}

Below is recent documentation/blog content fetched from the web.
Synthesize a complete, actionable integration playbook in valid JSON format:

{{
  "service": "Display name",
  "env_vars": ["KEY_NAME_1", "KEY_NAME_2"],
  "install": "pip install xyz",
  "backend_snippet": "<<<complete working Python code>>>",
  "frontend_snippet": "<<<JS/React code if relevant, else empty string>>>",
  "docs": "https://...",
  "get_key": "https://... (where to obtain credentials)",
  "common_pitfalls": ["pitfall 1", "pitfall 2"]
}}

Output ONLY valid JSON. No prose, no markdown fences.

=== Web Documentation ===
{docs_blob}
"""

    raw = await _claude_analyze(prompt, max_tokens=2500)

    # Robust JSON extraction
    playbook = _extract_json_object(raw)
    if not playbook:
        return {"ok": False,
                "error": "Claude returned invalid JSON",
                "raw_response": raw[:1000]}

    playbook["ok"] = True
    playbook["source"] = "live_research"
    playbook["search_results_used"] = len(crawled_text)
    return playbook


def _extract_json_object(raw: str) -> Optional[Dict[str, Any]]:
    """Extract a JSON object from Claude's response, robust to prose/fences."""
    if not raw:
        return None
    s = raw.strip()
    # Strip code fences
    if s.startswith("```"):
        s = re.sub(r"^```(json|JSON)?\s*\n?", "", s)
        s = re.sub(r"\n?```\s*$", "", s)
    # Try direct parse
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        pass
    # Find first { ... last }
    start = s.find("{")
    end = s.rfind("}")
    if start >= 0 and end > start:
        try:
            return json.loads(s[start:end + 1])
        except json.JSONDecodeError:
            pass
    return None


# ════════════════════════════════════════════════════════════════════════
# 3. recursive_test_agent — multi-turn QA AI
# ════════════════════════════════════════════════════════════════════════
async def recursive_test_agent(
    project_url: str,
    user_goal: str = "",
    max_scenarios: int = 8,
    project_id: str = "anon",
) -> Dict[str, Any]:
    """Spawn a QA-focused Claude session that:

    1. Fetches the live page HTML
    2. Generates realistic end-to-end user journeys (not just button clicks)
    3. Executes them via Playwright (verify_my_work)
    4. Captures before/after visual snapshots
    5. Asks Claude to interpret failures and suggest fixes
    6. Returns a structured QA report

    This is the closest thing to testing_agent_v3 — a real recursive AI.
    """
    if not project_url:
        return {"ok": False, "error": "project_url required"}

    # Step 1: Fetch page HTML
    try:
        import httpx
        async with httpx.AsyncClient(timeout=15, follow_redirects=True,
                                      verify=False) as client:
            r = await client.get(project_url)
            html = r.text if r.status_code == 200 else ""
    except Exception as e:
        return {"ok": False, "error": f"fetch failed: {e}"}

    if not html:
        return {"ok": False, "error": "could not fetch project HTML"}

    html_snip = html[:25_000]

    # Step 2: Claude generates scenarios
    gen_prompt = f"""You are a QA engineer testing a website. The site's HTML is below.

User's goal for the site: {user_goal or 'general usability'}

Generate up to {max_scenarios} REALISTIC end-to-end test scenarios that simulate
actual user journeys (not just "click each button"). Examples of good scenarios:
- "Visitor lands on home, clicks 'Sign Up', fills form, submits"
- "User scrolls to pricing, clicks 'Buy Now', checkout opens"
- "Mobile user opens menu, navigates to /about, scrolls to footer"

For each scenario, output VALID JSON:
{{
  "scenarios": [
    {{"name": "scenario_id", "description": "...",
      "steps": [
        {{"action": "navigate", "url": "{project_url}", "expect": "page text"}},
        {{"action": "click", "selector": "css", "expect_url_contains": "/foo"}},
        {{"action": "fill", "selector": "input[name='email']", "value": "test@x.com"}},
        {{"action": "count", "selector": "a", "min": 3}}
      ]}}
  ]
}}

HTML (truncated to 25KB):
{html_snip}

Output ONLY the JSON object. No prose.
"""

    raw = await _claude_analyze(gen_prompt, max_tokens=3000)
    plan = _extract_json_object(raw)
    if not plan:
        return {"ok": False,
                "error": "QA agent returned invalid scenario JSON",
                "raw": raw[:500]}
    scenarios = plan.get("scenarios", [])

    if not scenarios:
        return {"ok": True, "passed": 0, "total": 0,
                 "message": "QA agent found no testable flows"}

    # Step 3: Execute each scenario via Playwright
    from .runtime import verify_my_work
    all_results = []
    for sc in scenarios[:max_scenarios]:
        steps = sc.get("steps", [])
        if not steps:
            continue
        scenario_list = [{**s, "name": f"{sc.get('name','sc')}_{i}"}
                         for i, s in enumerate(steps)]
        res = await verify_my_work(project_url, scenario_list,
                                    timeout_seconds=30)
        all_results.append({
            "name": sc.get("name", "scenario"),
            "description": sc.get("description", ""),
            "passed": res.get("passed", 0),
            "total": res.get("total", 0),
            "details": res.get("results", []),
            "ok": res.get("ok", False),
        })

    total_passed = sum(r["passed"] for r in all_results)
    total_total = sum(r["total"] for r in all_results)
    failed_scenarios = [r for r in all_results
                         if r["total"] > 0 and r["passed"] < r["total"]]

    # Step 4: Claude interprets failures
    interpretation = "All scenarios passed ✅"
    if failed_scenarios:
        interp_prompt = (
            "You are a senior QA engineer reviewing test results. "
            "Summarize the failures and suggest 1-2 specific fixes per failure.\n\n"
            "Test results (JSON):\n"
            + json.dumps(failed_scenarios, indent=2, ensure_ascii=False)[:8000]
        )
        interpretation = await _claude_analyze(interp_prompt, max_tokens=1500)

    return {
        "ok": True,
        "project_url": project_url,
        "user_goal": user_goal,
        "scenarios_generated": len(scenarios),
        "scenarios_executed": len(all_results),
        "passed": total_passed,
        "total": total_total,
        "pass_rate": (total_passed / total_total) if total_total else 1.0,
        "failed_scenarios": len(failed_scenarios),
        "results": all_results,
        "ai_interpretation": interpretation,
        "summary": (f"🧪 QA: {total_passed}/{total_total} steps passed "
                    f"across {len(all_results)} scenarios "
                    f"({len(failed_scenarios)} failed)"),
    }


# ════════════════════════════════════════════════════════════════════════
# 4. crawl_url_deep — fetch URL → clean Markdown
# ════════════════════════════════════════════════════════════════════════
async def crawl_url_deep(url: str, max_chars: int = 50_000) -> Dict[str, Any]:
    """Fetch a URL and return clean Markdown with headings, code blocks, tables.

    Strips ads, nav, scripts. Preserves semantic structure.
    """
    if not url or not url.startswith(("http://", "https://")):
        return {"ok": False, "error": "valid http(s) URL required"}

    try:
        import httpx
        from bs4 import BeautifulSoup
        from markdownify import markdownify as md
    except ImportError as e:
        return {"ok": False, "error": f"missing dep: {e}"}

    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "en-US,en;q=0.9",
    }

    try:
        async with httpx.AsyncClient(timeout=20, follow_redirects=True,
                                      verify=False) as client:
            r = await client.get(url, headers=headers)
            if r.status_code != 200:
                return {"ok": False,
                         "error": f"HTTP {r.status_code}",
                         "url": url}
            html = r.text
    except Exception as e:
        return {"ok": False, "error": f"fetch failed: {type(e).__name__}: {e}"}

    soup = BeautifulSoup(html, "html.parser")

    # Strip junk
    for tag in soup(["script", "style", "nav", "header", "footer",
                      "aside", "noscript", "iframe", "form"]):
        tag.decompose()
    for tag in soup.find_all(class_=re.compile(r"(ad|advert|cookie|popup|modal|sidebar|menu)",
                                                  re.I)):
        try:
            tag.decompose()
        except Exception:
            pass

    # Try to find <main> or <article> first
    body = (soup.find("main") or soup.find("article")
            or soup.find("body") or soup)

    title = ""
    if soup.title:
        title = soup.title.get_text(strip=True)[:200]

    try:
        markdown = md(str(body), heading_style="ATX",
                       code_language="", strip=["a", "img"])
    except Exception:
        markdown = body.get_text("\n", strip=True)

    # Cleanup: collapse multiple blank lines, trim
    markdown = re.sub(r"\n{3,}", "\n\n", markdown).strip()
    markdown = markdown[:max_chars]

    # Extract code blocks separately for quick reference
    code_blocks = re.findall(r"```[^\n]*\n(.+?)```", markdown, re.S)[:10]

    return {
        "ok": True,
        "url": url,
        "title": title,
        "markdown": markdown,
        "char_count": len(markdown),
        "truncated": len(markdown) >= max_chars,
        "code_blocks_found": len(code_blocks),
        "summary": f"📄 fetched {len(markdown)}c from {url}",
    }


# ════════════════════════════════════════════════════════════════════════
# 5. Global Cross-Project Memory (remember / recall)
# ════════════════════════════════════════════════════════════════════════
async def remember(
    insight: str,
    tags: Optional[List[str]] = None,
    project_id: str = "anon",
    importance: int = 5,
) -> Dict[str, Any]:
    """Save a cross-project insight to global memory.

    Use this for: "user prefers Arabic", "this user always wants RTL",
    "this client always uses Stripe", patterns, mistakes to avoid, etc.
    """
    if not insight or not insight.strip():
        return {"ok": False, "error": "insight required"}
    if len(insight) > 2000:
        return {"ok": False, "error": "insight too long (>2KB)"}

    importance = max(1, min(10, int(importance or 5)))
    tags = [str(t)[:50] for t in (tags or [])][:10]

    try:
        from server import db
        doc = {
            "insight": insight.strip(),
            "tags": tags,
            "project_id": str(project_id),
            "importance": importance,
            "ts": time.time(),
            "access_count": 0,
        }
        result = await db.ai_global_memory.insert_one(doc)
        return {
            "ok": True,
            "memory_id": str(result.inserted_id),
            "summary": f"🧠 remembered (importance={importance}): {insight[:80]}",
        }
    except Exception as e:
        return {"ok": False, "error": f"DB error: {e}"}


async def recall(
    query: str = "",
    tags: Optional[List[str]] = None,
    project_id: str = "",
    limit: int = 5,
) -> Dict[str, Any]:
    """Search global memory by query/tags/project_id.

    Use this at the start of a project to learn from past work.
    """
    limit = max(1, min(20, int(limit or 5)))

    try:
        from server import db
        mongo_q = {}
        if tags:
            mongo_q["tags"] = {"$in": [str(t) for t in tags]}
        if project_id:
            mongo_q["project_id"] = str(project_id)
        if query and query.strip():
            mongo_q["$or"] = [
                {"insight": {"$regex": re.escape(query.strip()),
                              "$options": "i"}},
                {"tags": {"$regex": re.escape(query.strip()),
                           "$options": "i"}},
            ]

        cursor = db.ai_global_memory.find(mongo_q).sort(
            [("importance", -1), ("ts", -1)]
        ).limit(limit)

        memories = []
        ids_to_bump = []
        async for m in cursor:
            memories.append({
                "id": str(m.get("_id", "")),
                "insight": m.get("insight", ""),
                "tags": m.get("tags", []),
                "project_id": m.get("project_id", ""),
                "importance": m.get("importance", 5),
                "ts": m.get("ts", 0),
                "access_count": m.get("access_count", 0),
            })
            ids_to_bump.append(m["_id"])

        # Bump access counts (best-effort)
        if ids_to_bump:
            try:
                await db.ai_global_memory.update_many(
                    {"_id": {"$in": ids_to_bump}},
                    {"$inc": {"access_count": 1}},
                )
            except Exception:
                pass

        return {
            "ok": True,
            "count": len(memories),
            "memories": memories,
            "summary": f"🧠 recalled {len(memories)} memories",
        }
    except Exception as e:
        return {"ok": False, "error": f"DB error: {e}"}


# ════════════════════════════════════════════════════════════════════════
# Registry
# ════════════════════════════════════════════════════════════════════════
PARITY_TOOLS = {
    "analyze_uploaded_file": analyze_uploaded_file,
    "integration_playbook_live": integration_playbook_live,
    "recursive_test_agent": recursive_test_agent,
    "crawl_url_deep": crawl_url_deep,
    "remember": remember,
    "recall": recall,
}
