"""
🛠️ Cortex Tools — 20+ tool definitions wrapping the new 24 cortices.

These get registered in freebuild_agent's tool list so the AI can actually
CALL them. Each tool has:
  - definition: JSON schema (for Claude tool-use)
  - handler: async function that executes the cortex

The handlers are thin glue between the AI's tool_use request and the cortex's
public API. They return dicts the AI can read in next turn.
"""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("zenrex.cortex_tools")


# ──────────────────────── TOOL DEFINITIONS ────────────────────────
TOOL_DEFINITIONS: List[Dict[str, Any]] = [
    {
        "name": "inject_recipe",
        "description": "Inject a pre-made design recipe (palette + fonts + sections + libraries). Use when user's request matches one of the 30 recipes (cosmic, fintech, restaurant, gaming, etc.).",
        "input_schema": {
            "type": "object",
            "properties": {
                "recipe_id": {"type": "string", "description": "Recipe ID from creative_recipes.json (e.g. 'cosmic_immersive_landing')"},
            },
            "required": ["recipe_id"],
        },
    },
    {
        "name": "apply_shader",
        "description": "Get inject-ready code (CSS/JS/GLSL) for a visual effect. Use for neon/glitch/scanlines/nebula/matrix_rain/etc.",
        "input_schema": {
            "type": "object",
            "properties": {"shader_id": {"type": "string", "description": "Shader ID from shaders_library.json"}},
            "required": ["shader_id"],
        },
    },
    {
        "name": "inject_backend_pattern",
        "description": "Get production backend code (JWT, WebSocket, Stripe, ARQ jobs, Redis rate-limit, Twilio, Resend, etc.).",
        "input_schema": {
            "type": "object",
            "properties": {"pattern_id": {"type": "string", "description": "Pattern ID from backend_patterns.json"}},
            "required": ["pattern_id"],
        },
    },
    {
        "name": "run_architect",
        "description": "Produce architecture blueprint (Mermaid ERD + Sequence + Component + ADR + file tree) BEFORE coding. Use for complex projects.",
        "input_schema": {
            "type": "object",
            "properties": {"brief": {"type": "string", "description": "Customer's brief"}},
            "required": ["brief"],
        },
    },
    {
        "name": "run_reviewer",
        "description": "Static + LLM code review (XSS, perf, a11y, SEO, quality). Call BEFORE delivering final code.",
        "input_schema": {
            "type": "object",
            "properties": {
                "code": {"type": "string"},
                "code_type": {"type": "string", "enum": ["html", "js", "css", "mixed"], "default": "html"},
            },
            "required": ["code"],
        },
    },
    {
        "name": "extract_brand_dna",
        "description": "Extract structured brand identity (palette, tone, voice, glossary, archetypes) from a brief. Call once per new project.",
        "input_schema": {
            "type": "object",
            "properties": {"brief": {"type": "string"}},
            "required": ["brief"],
        },
    },
    {
        "name": "convert_to_typescript",
        "description": "Convert JS code to TypeScript with inferred types.",
        "input_schema": {
            "type": "object",
            "properties": {"js_code": {"type": "string"}},
            "required": ["js_code"],
        },
    },
    {
        "name": "refactor_rename",
        "description": "Rename an identifier across multiple files atomically.",
        "input_schema": {
            "type": "object",
            "properties": {
                "files": {"type": "object", "description": "Map of filename → content"},
                "old_name": {"type": "string"},
                "new_name": {"type": "string"},
            },
            "required": ["files", "old_name", "new_name"],
        },
    },
    {
        "name": "audit_a11y",
        "description": "WCAG 2.1 AA audit (alt, aria, lang, contrast, skip-link). Returns issues + auto-fix suggestions.",
        "input_schema": {
            "type": "object",
            "properties": {"html": {"type": "string"}, "auto_fix": {"type": "boolean", "default": False}},
            "required": ["html"],
        },
    },
    {
        "name": "audit_seo",
        "description": "SEO audit (meta tags, schema.org, sitemap, robots, og:image).",
        "input_schema": {
            "type": "object",
            "properties": {"html": {"type": "string"}},
            "required": ["html"],
        },
    },
    {
        "name": "optimize_performance",
        "description": "Auto-apply lazy-load + defer scripts + analyze bottlenecks.",
        "input_schema": {
            "type": "object",
            "properties": {"html": {"type": "string"}, "apply_fixes": {"type": "boolean", "default": True}},
            "required": ["html"],
        },
    },
    {
        "name": "inject_pwa",
        "description": "Generate PWA assets: manifest.json + service worker + offline.html + install prompt + push setup.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "short_name": {"type": "string"},
                "description": {"type": "string"},
                "theme_color": {"type": "string", "default": "#0a0a0a"},
                "lang": {"type": "string", "default": "ar"},
            },
            "required": ["name", "short_name", "description"],
        },
    },
    {
        "name": "setup_i18n",
        "description": "Extract translatable strings + translate to target language + RTL/LTR setup.",
        "input_schema": {
            "type": "object",
            "properties": {
                "html": {"type": "string"},
                "target_lang": {"type": "string", "enum": ["ar", "en", "fr", "es", "tr", "ur"]},
                "source_lang": {"type": "string", "default": "ar"},
            },
            "required": ["html", "target_lang"],
        },
    },
    {
        "name": "design_database",
        "description": "Design Mongo or Postgres schema from a domain brief. Returns ERD + Pydantic/SQL models.",
        "input_schema": {
            "type": "object",
            "properties": {"brief": {"type": "string"}},
            "required": ["brief"],
        },
    },
    {
        "name": "inject_liveblocks",
        "description": "Generate Liveblocks real-time files (auth endpoint + React provider + LiveCursors + LivePresence).",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "trigger_eas_build",
        "description": "Trigger Expo EAS cloud build for a mobile app. Requires EAS_ACCESS_TOKEN in vault.",
        "input_schema": {
            "type": "object",
            "properties": {
                "project_id_expo": {"type": "string", "description": "EAS project ID"},
                "platform": {"type": "string", "enum": ["android", "ios"], "default": "android"},
            },
            "required": ["project_id_expo"],
        },
    },
    {
        "name": "run_in_webcontainer",
        "description": "Execute Node.js code in customer's browser via WebContainer (WASM sandbox).",
        "input_schema": {
            "type": "object",
            "properties": {
                "code": {"type": "string"},
                "files": {"type": "object", "description": "Optional extra files {path: content}"},
            },
            "required": ["code"],
        },
    },
    {
        "name": "run_in_pyodide",
        "description": "Execute Python code in customer's browser via Pyodide (WASM).",
        "input_schema": {
            "type": "object",
            "properties": {
                "code": {"type": "string"},
                "packages": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["code"],
        },
    },
    {
        "name": "generate_tests",
        "description": "Auto-generate Pytest or Vitest tests for a code file + run them in sandbox.",
        "input_schema": {
            "type": "object",
            "properties": {
                "code": {"type": "string"},
                "language": {"type": "string", "enum": ["python", "js"], "default": "python"},
            },
            "required": ["code"],
        },
    },
    {
        "name": "generate_openapi_spec",
        "description": "Build OpenAPI 3.1 spec + Swagger UI from a list of endpoints or a DB schema.",
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "version": {"type": "string", "default": "1.0"},
                "endpoints": {"type": "array"},
                "from_schema": {"type": "object"},
            },
            "required": ["title"],
        },
    },
    {
        "name": "inject_integration",
        "description": "Inject Sentry / PostHog / GA4 / Crisp Chat / S3 / Mapbox snippet into the project.",
        "input_schema": {
            "type": "object",
            "properties": {"integration_id": {"type": "string", "enum": ["sentry", "posthog", "google_analytics", "crisp_chat", "s3_upload"]}},
            "required": ["integration_id"],
        },
    },
    {
        "name": "generate_nextjs_project",
        "description": "Generate a complete Next.js 15 (App Router) project with TypeScript + Tailwind from a brief. Use for SaaS apps, dashboards, multi-page React apps. Returns file tree {path: content}.",
        "input_schema": {
            "type": "object",
            "properties": {
                "brief": {"type": "string", "description": "Project description"},
                "brand_dna": {"type": "object", "description": "Optional brand palette/tone from extract_brand_dna"},
                "architecture": {"type": "object", "description": "Optional architecture blueprint from run_architect"},
            },
            "required": ["brief"],
        },
    },
    {
        "name": "build_capacitor_app",
        "description": "Wrap an existing web app as a native Android/iOS app via Capacitor. Returns capacitor.config.ts + package.json + Arabic build instructions for user to run locally (we cannot build .apk/.ipa server-side without Android Studio/Xcode).",
        "input_schema": {
            "type": "object",
            "properties": {
                "app_id": {"type": "string", "description": "Reverse-DNS bundle id, e.g. com.zenrex.myapp"},
                "app_name": {"type": "string"},
                "web_dir": {"type": "string", "default": "dist"},
            },
            "required": ["app_id", "app_name"],
        },
    },
    {
        "name": "recommend_state_management",
        "description": "Pick the right React state management strategy (useState / useReducer / Zustand / TanStack Query / Jotai) for a use-case. Optionally returns ready-paste Zustand store snippet.",
        "input_schema": {
            "type": "object",
            "properties": {
                "use_case": {"type": "string", "description": "Describe what state needs to be managed"},
                "store_name": {"type": "string", "description": "Optional store name to generate Zustand snippet"},
                "state_keys": {"type": "array", "items": {"type": "string"}, "description": "Optional keys for the Zustand store"},
            },
            "required": ["use_case"],
        },
    },
    {
        "name": "search_past_projects",
        "description": "Search the user's past project lessons via semantic RAG. Useful before starting a new project to reuse previous learnings (palette decisions, library choices, fixes). Returns top-K relevant lessons.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "top_k": {"type": "integer", "default": 5},
                "tags_filter": {"type": "array", "items": {"type": "string"}, "description": "Optional tag filter e.g. ['restaurant', 'arabic']"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "run_in_e2b_sandbox",
        "description": "Execute arbitrary commands in an E2B cloud sandbox (full Linux VM). Use when WebContainer/Pyodide aren't enough (needs apt-get, compiled binaries, network access). Requires E2B_API_KEY in user's vault.",
        "input_schema": {
            "type": "object",
            "properties": {
                "files": {"type": "object", "description": "Files to write {path: content}"},
                "commands": {"type": "array", "items": {"type": "string"}, "description": "Shell commands to execute sequentially"},
                "template": {"type": "string", "default": "base"},
                "timeout_min": {"type": "integer", "default": 10},
            },
            "required": ["commands"],
        },
    },
    {
        "name": "deploy_via_ssh",
        "description": "Deploy/execute commands on the user's own VPS via SSH. Requires SSH_HOST, SSH_PORT, SSH_USERNAME + (SSH_PASSWORD or SSH_PRIVATE_KEY) in vault. Use for final deploys to user's Hetzner/DigitalOcean/AWS.",
        "input_schema": {
            "type": "object",
            "properties": {
                "commands": {"type": "array", "items": {"type": "string"}, "description": "Sequential commands to run on remote"},
            },
            "required": ["commands"],
        },
    },
    {
        "name": "run_js_sandbox",
        "description": "Execute JavaScript snippet in a fast Node.js sandbox (timeout ~5s). Use for sanity-testing utility functions, regex, parsing logic before injecting into the final code. Returns {ok, stdout, stderr}.",
        "input_schema": {
            "type": "object",
            "properties": {
                "code": {"type": "string"},
                "timeout_sec": {"type": "integer", "default": 5},
            },
            "required": ["code"],
        },
    },
    {
        "name": "run_python_sandbox",
        "description": "Execute a Python snippet in an isolated subprocess (timeout ~5s). Use for quick data computations, regex tests, JSON parsing checks. Returns {ok, stdout, stderr}.",
        "input_schema": {
            "type": "object",
            "properties": {
                "code": {"type": "string"},
                "timeout_sec": {"type": "integer", "default": 5},
            },
            "required": ["code"],
        },
    },
    {
        "name": "validate_html_sandbox",
        "description": "Quick HTML validator — checks balanced tags, missing DOCTYPE/html/body. Returns {ok, issues:[]}. MUCH faster than running a full browser. Use after every HTML edit to self-verify. (ok=False if any structural issue found.)",
        "input_schema": {
            "type": "object",
            "properties": {"html": {"type": "string"}},
            "required": ["html"],
        },
    },
    {
        "name": "autofix_code_loop",
        "description": "Self-healing loop: run code → if fails, LLM-fix → rerun, up to N attempts. Use when a generated snippet has runtime errors you want the AI to fix automatically. Returns {ok, final_code, attempts:[], total_attempts}.",
        "input_schema": {
            "type": "object",
            "properties": {
                "code": {"type": "string"},
                "language": {"type": "string", "enum": ["js", "python"], "default": "js"},
                "max_attempts": {"type": "integer", "default": 3},
            },
            "required": ["code"],
        },
    },
]


# ──────────────────────── HANDLERS ────────────────────────
async def handle_inject_recipe(args: Dict[str, Any], ctx: Any = None) -> Dict[str, Any]:
    from .creative_recipes import get_recipe, recipe_to_prompt_hint
    r = get_recipe(args["recipe_id"])
    if not r:
        return {"ok": False, "error": f"recipe '{args['recipe_id']}' not found"}
    return {"ok": True, "recipe": r, "prompt_hint": recipe_to_prompt_hint(r)}


async def handle_apply_shader(args: Dict[str, Any], ctx: Any = None) -> Dict[str, Any]:
    from .shaders_library import render_shader_for_inject, get_shader
    rendered = render_shader_for_inject(args["shader_id"])
    if not rendered:
        return {"ok": False, "error": f"shader '{args['shader_id']}' not found"}
    return {"ok": True, "shader": rendered, "meta": get_shader(args["shader_id"])}


async def handle_inject_backend_pattern(args: Dict[str, Any], ctx: Any = None) -> Dict[str, Any]:
    from .backend_patterns import get_pattern
    p = get_pattern(args["pattern_id"])
    if not p:
        return {"ok": False, "error": f"pattern '{args['pattern_id']}' not found"}
    return {"ok": True, "pattern": p, "files": p.get("files", {}), "install": p.get("install", [])}


async def handle_run_architect(args: Dict[str, Any], ctx: Any = None) -> Dict[str, Any]:
    from .orchestrator.cortices.architect_cortex import design_architecture, render_architecture_summary_ar
    arch = await design_architecture(args["brief"])
    return {"ok": True, "architecture": arch, "summary_ar": render_architecture_summary_ar(arch)}


async def handle_run_reviewer(args: Dict[str, Any], ctx: Any = None) -> Dict[str, Any]:
    from .orchestrator.review_cortex import review_code, render_review_report_ar
    r = review_code(args["code"], args.get("code_type", "html"))
    return {"ok": True, "report": r, "summary_ar": render_review_report_ar(r), "passed": r.get("passed")}


async def handle_extract_brand_dna(args: Dict[str, Any], ctx: Any = None) -> Dict[str, Any]:
    from .orchestrator.brand_dna import extract_brand_dna, render_brand_dna_hint
    dna = await extract_brand_dna(args["brief"])
    # Persist into shared_memory if ctx has db/project_id
    # ⚠️ Motor Database raises NotImplementedError on bool() — use explicit None checks
    db = getattr(ctx, "db", None) if ctx else None
    pid = getattr(ctx, "project_id", None) if ctx else None
    if db is not None and pid:
        try:
            from .orchestrator.shared_memory import save_memory
            await save_memory(db, pid, {"brand_dna": dna})
        except Exception:
            pass
    return {"ok": True, "brand_dna": dna, "hint": render_brand_dna_hint(dna)}


async def handle_convert_to_typescript(args: Dict[str, Any], ctx: Any = None) -> Dict[str, Any]:
    from .orchestrator.typescript_cortex import convert_js_to_ts, render_tsconfig_json
    ts = await convert_js_to_ts(args["js_code"])
    return {"ok": ts is not None, "typescript": ts, "tsconfig": render_tsconfig_json()}


async def handle_refactor_rename(args: Dict[str, Any], ctx: Any = None) -> Dict[str, Any]:
    from .orchestrator.refactor_cortex import rename_identifier
    return {"ok": True, **rename_identifier(args["files"], args["old_name"], args["new_name"])}


async def handle_audit_a11y(args: Dict[str, Any], ctx: Any = None) -> Dict[str, Any]:
    from .orchestrator.a11y_cortex import audit, auto_fix_alt_text, auto_fix_lang_attribute, inject_skip_link
    rep = audit(args["html"])
    fixed_html = None
    if args.get("auto_fix"):
        h = args["html"]
        h = auto_fix_alt_text(h)
        h = auto_fix_lang_attribute(h)
        h = inject_skip_link(h)
        fixed_html = h
    return {"ok": True, "report": rep, "fixed_html": fixed_html}


async def handle_audit_seo(args: Dict[str, Any], ctx: Any = None) -> Dict[str, Any]:
    from .orchestrator.seo_cortex import audit_seo
    return {"ok": True, "report": audit_seo(args["html"])}


async def handle_optimize_performance(args: Dict[str, Any], ctx: Any = None) -> Dict[str, Any]:
    from .orchestrator.performance_optimizer import analyze, apply_lazy_loading, apply_defer_to_scripts
    rep = analyze(args["html"])
    fixed = None
    if args.get("apply_fixes", True):
        h = args["html"]
        h = apply_lazy_loading(h)
        h = apply_defer_to_scripts(h)
        fixed = h
    return {"ok": True, "report": rep, "optimized_html": fixed}


async def handle_inject_pwa(args: Dict[str, Any], ctx: Any = None) -> Dict[str, Any]:
    from .orchestrator.pwa_cortex import (
        build_manifest, build_service_worker, build_offline_page,
        install_prompt_snippet, push_setup_snippet,
    )
    return {
        "ok": True,
        "files": {
            "manifest.json": build_manifest(args["name"], args["short_name"], args["description"],
                                            args.get("theme_color", "#0a0a0a"),
                                            lang=args.get("lang", "ar")),
            "service-worker.js": build_service_worker("v1"),
            "offline.html": build_offline_page(args["short_name"], args.get("theme_color", "#0a0a0a")),
            "pwa-install.js": install_prompt_snippet(),
            "pwa-push.js": push_setup_snippet(),
        },
    }


async def handle_setup_i18n(args: Dict[str, Any], ctx: Any = None) -> Dict[str, Any]:
    from .orchestrator.i18n_cortex import (
        extract_translatable_strings, translate_strings, render_html_with_lang,
        language_switcher_snippet,
    )
    strs = extract_translatable_strings(args["html"])
    translated = await translate_strings(strs, args["target_lang"], args.get("source_lang", "ar"))
    return {
        "ok": True,
        "strings_extracted": len(strs),
        "translations": translated,
        "html_with_lang": render_html_with_lang(args["html"], args["target_lang"]),
        "switcher_snippet": language_switcher_snippet(args["target_lang"], ["ar", "en", "fr", "es"]),
    }


async def handle_design_database(args: Dict[str, Any], ctx: Any = None) -> Dict[str, Any]:
    from .orchestrator.db_designer import (
        design_database, render_schema_as_mongo_pydantic, render_schema_as_postgres_sql,
    )
    schema = await design_database(args["brief"])
    if not schema:
        return {"ok": False, "error": "could not design schema"}
    return {
        "ok": True,
        "schema": schema,
        "pydantic_code": render_schema_as_mongo_pydantic(schema),
        "sql_code": render_schema_as_postgres_sql(schema),
    }


async def handle_inject_liveblocks(args: Dict[str, Any], ctx: Any = None) -> Dict[str, Any]:
    from .executors.liveblocks_integrator import render_full_integration_files, package_json_deps
    return {"ok": True, "files": render_full_integration_files(), "deps": package_json_deps()}


async def handle_trigger_eas_build(args: Dict[str, Any], ctx: Any = None) -> Dict[str, Any]:
    from .executors.eas_build import trigger_build, render_user_instructions_ar
    from .concierge.credential_vault import get_credential
    db, uid, _ = _ctx_auth(ctx)
    if db is None or not uid:
        return {"ok": False, "error": "no auth context"}
    token = await get_credential(db, uid, "EAS_ACCESS_TOKEN")
    if not token:
        return {"ok": False, "error": "EAS_ACCESS_TOKEN not in vault — run Concierge setup first"}
    result = await trigger_build(token, args["project_id_expo"], args.get("platform", "android"))
    if result and result.get("build_id"):
        return {
            "ok": True, **result,
            "instructions_ar": render_user_instructions_ar(result["build_id"], result["platform"], f"https://expo.dev/builds/{result['build_id']}"),
        }
    return {"ok": False, **(result or {})}


async def handle_run_in_webcontainer(args: Dict[str, Any], ctx: Any = None) -> Dict[str, Any]:
    from .executors.webcontainer_executor import enqueue_execution
    db, uid, pid = _ctx_auth(ctx)
    if db is None:
        return {"ok": False, "error": "no db context"}
    files = args.get("files") or {"index.js": args["code"]}
    return await enqueue_execution(db, uid or "anon", pid or "default", args["code"], files)


async def handle_run_in_pyodide(args: Dict[str, Any], ctx: Any = None) -> Dict[str, Any]:
    from .executors.pyodide_executor import enqueue_python
    db, uid, pid = _ctx_auth(ctx)
    if db is None:
        return {"ok": False, "error": "no db context"}
    return await enqueue_python(db, uid or "anon", pid or "default", args["code"], args.get("packages"))


async def handle_generate_tests(args: Dict[str, Any], ctx: Any = None) -> Dict[str, Any]:
    from .orchestrator.test_generator import generate_and_run_tests
    return await generate_and_run_tests(args["code"], args.get("language", "python"))


async def handle_generate_openapi_spec(args: Dict[str, Any], ctx: Any = None) -> Dict[str, Any]:
    from .orchestrator.openapi_generator import build_openapi_spec, endpoints_from_schema, render_swagger_html
    eps = args.get("endpoints") or []
    if not eps and args.get("from_schema"):
        eps = endpoints_from_schema(args["from_schema"])
    spec = build_openapi_spec(args["title"], args.get("version", "1.0"), eps)
    return {"ok": True, "spec": spec, "swagger_html": render_swagger_html()}


async def handle_inject_integration(args: Dict[str, Any], ctx: Any = None) -> Dict[str, Any]:
    from .orchestrator.integrations_cortex import (
        sentry_setup_js, posthog_setup_js, google_analytics_setup_js,
        crisp_chat_setup_js, s3_upload_node_snippet,
    )
    routes = {
        "sentry": sentry_setup_js,
        "posthog": posthog_setup_js,
        "google_analytics": google_analytics_setup_js,
        "crisp_chat": crisp_chat_setup_js,
        "s3_upload": s3_upload_node_snippet,
    }
    fn = routes.get(args["integration_id"])
    if not fn:
        return {"ok": False, "error": "unknown integration"}
    return {"ok": True, "integration": fn()}


async def _project_brand_dna(ctx: Any) -> Dict[str, Any]:
    """Helper: load brand_dna from project doc if not explicitly passed.
    Lets tools like generate_nextjs_project / build_capacitor_app pick up the
    brand identity automatically from the auto-extracted memory."""
    if ctx is None:
        return {}
    db = getattr(ctx, "db", None)
    pid = getattr(ctx, "project_id", None)
    # IMPORTANT: Motor/PyMongo Database objects raise NotImplementedError on
    # bool(); use explicit `is None` checks instead.
    if db is None or not pid:
        return {}
    try:
        proj = await db.freebuild_projects.find_one(
            {"id": pid}, {"brand_dna": 1, "_id": 0},
        )
        return (proj or {}).get("brand_dna") or {}
    except Exception:
        return {}


def _ctx_auth(ctx: Any) -> Tuple[Any, Optional[str], Optional[str]]:
    """Helper: extract (db, user_id, project_id) from ctx safely.
    Returns (None, None, None) when ctx is missing. Use this instead of the
    `if ctx and getattr(ctx, "db", None)` truthy chain which CRASHES with
    Motor Database (raises NotImplementedError on bool())."""
    if ctx is None:
        return None, None, None
    return (
        getattr(ctx, "db", None),
        getattr(ctx, "user_id", None),
        getattr(ctx, "project_id", None),
    )


async def handle_generate_nextjs_project(args: Dict[str, Any], ctx: Any = None) -> Dict[str, Any]:
    from .orchestrator.nextjs_cortex import (
        generate_nextjs_project, default_package_json, default_tailwind_config,
    )
    # Auto-pull brand_dna from project if not explicitly provided
    brand_dna = args.get("brand_dna") or await _project_brand_dna(ctx)
    result = await generate_nextjs_project(
        args["brief"],
        brand_dna=brand_dna,
        architecture=args.get("architecture"),
    )
    if result and result.get("files"):
        return {"ok": True, "brand_dna_used": bool(brand_dna), **result}
    # LLM failed → return minimal defaults so caller can still scaffold
    return {
        "ok": False,
        "error": "LLM generation failed — falling back to defaults",
        "brand_dna_used": bool(brand_dna),
        "fallback_files": {
            "package.json": default_package_json("zenrex-app"),
            "tailwind.config.ts": default_tailwind_config(
                ((brand_dna or {}).get("palette") or None)
            ),
        },
    }


async def handle_build_capacitor_app(args: Dict[str, Any], ctx: Any = None) -> Dict[str, Any]:
    from .orchestrator.capacitor_cortex import (
        build_capacitor_config, capacitor_package_json,
        build_instructions_ar, push_native_snippet_js,
    )
    # Optionally personalize splash/theme color from brand_dna
    brand_dna = await _project_brand_dna(ctx)
    primary_color = ((brand_dna.get("palette") or {}).get("primary") if brand_dna else None) or "#0EA5E9"
    return {
        "ok": True,
        "brand_dna_used": bool(brand_dna),
        "primary_color": primary_color,
        "files": {
            "capacitor.config.ts": build_capacitor_config(
                args["app_id"], args["app_name"], args.get("web_dir", "dist"),
            ),
            "package.json": capacitor_package_json(args["app_name"]),
            "push-notifications.js": push_native_snippet_js(),
        },
        "instructions_ar": build_instructions_ar(args["app_name"]),
    }


async def handle_recommend_state_management(args: Dict[str, Any], ctx: Any = None) -> Dict[str, Any]:
    from .orchestrator.state_cortex import (
        recommend_state_strategy, zustand_store_snippet, react_query_snippet,
    )
    rec = recommend_state_strategy(args["use_case"])
    out: Dict[str, Any] = {"ok": True, "recommendation": rec}
    if args.get("store_name") and args.get("state_keys"):
        out["zustand_snippet"] = zustand_store_snippet(args["store_name"], args["state_keys"])
    if rec.get("choice") == "tanstack-query":
        out["react_query_example"] = react_query_snippet("/api/data", "data")
    return out


async def handle_search_past_projects(args: Dict[str, Any], ctx: Any = None) -> Dict[str, Any]:
    from .orchestrator.cross_project_rag import retrieve_lessons, render_lessons_hint_ar
    db, _, pid = _ctx_auth(ctx)
    if db is None:
        return {"ok": False, "error": "no db context"}
    lessons = await retrieve_lessons(
        db, args["query"],
        top_k=int(args.get("top_k", 5)),
        tags_filter=args.get("tags_filter"),
        exclude_project_id=pid,
    )
    return {"ok": True, "lessons": lessons, "hint_ar": render_lessons_hint_ar(lessons), "count": len(lessons)}


async def handle_run_in_e2b_sandbox(args: Dict[str, Any], ctx: Any = None) -> Dict[str, Any]:
    from .executors.e2b_executor import run_full_workflow
    from .concierge.credential_vault import get_credential
    db, uid, _ = _ctx_auth(ctx)
    if db is None or not uid:
        return {"ok": False, "error": "no auth context"}
    api_key = await get_credential(db, uid, "E2B_API_KEY")
    if not api_key:
        return {"ok": False, "error": "E2B_API_KEY not in vault — run Concierge setup first"}
    return await run_full_workflow(
        api_key,
        files=args.get("files") or {},
        commands=args["commands"],
        template=args.get("template", "base"),
        timeout_min=int(args.get("timeout_min", 10)),
    )


async def handle_deploy_via_ssh(args: Dict[str, Any], ctx: Any = None) -> Dict[str, Any]:
    from .executors.ssh_executor import run_workflow
    from .concierge.credential_vault import get_credential
    db, uid, _ = _ctx_auth(ctx)
    if db is None or not uid:
        return {"ok": False, "error": "no auth context"}
    host = await get_credential(db, uid, "SSH_HOST")
    if not host:
        return {"ok": False, "error": "SSH_HOST not in vault — run Concierge setup first"}
    port = await get_credential(db, uid, "SSH_PORT") or "22"
    username = await get_credential(db, uid, "SSH_USERNAME")
    if not username:
        return {"ok": False, "error": "SSH_USERNAME not in vault"}
    password = await get_credential(db, uid, "SSH_PASSWORD")
    private_key = await get_credential(db, uid, "SSH_PRIVATE_KEY")
    if not (password or private_key):
        return {"ok": False, "error": "Need SSH_PASSWORD or SSH_PRIVATE_KEY in vault"}
    return await run_workflow(
        host=host, port=int(port), username=username,
        commands=args["commands"],
        password=password, private_key=private_key,
    )


async def handle_run_js_sandbox(args: Dict[str, Any], ctx: Any = None) -> Dict[str, Any]:
    from .orchestrator.code_sandbox import run_js
    return await run_js(args["code"], timeout_sec=int(args.get("timeout_sec", 5)))


async def handle_run_python_sandbox(args: Dict[str, Any], ctx: Any = None) -> Dict[str, Any]:
    from .orchestrator.code_sandbox import run_python
    return await run_python(args["code"], timeout_sec=int(args.get("timeout_sec", 5)))


async def handle_validate_html_sandbox(args: Dict[str, Any], ctx: Any = None) -> Dict[str, Any]:
    from .orchestrator.code_sandbox import validate_html
    return validate_html(args["html"])


async def handle_autofix_code_loop(args: Dict[str, Any], ctx: Any = None) -> Dict[str, Any]:
    from .orchestrator.autofix_loop import autofix_loop
    from .orchestrator.code_sandbox import run_js, run_python
    lang = args.get("language", "js")
    runner = run_js if lang == "js" else run_python
    return await autofix_loop(
        args["code"], runner, language=lang,
        max_attempts=int(args.get("max_attempts", 3)),
    )


TOOL_HANDLERS = {
    "inject_recipe": handle_inject_recipe,
    "apply_shader": handle_apply_shader,
    "inject_backend_pattern": handle_inject_backend_pattern,
    "run_architect": handle_run_architect,
    "run_reviewer": handle_run_reviewer,
    "extract_brand_dna": handle_extract_brand_dna,
    "convert_to_typescript": handle_convert_to_typescript,
    "refactor_rename": handle_refactor_rename,
    "audit_a11y": handle_audit_a11y,
    "audit_seo": handle_audit_seo,
    "optimize_performance": handle_optimize_performance,
    "inject_pwa": handle_inject_pwa,
    "setup_i18n": handle_setup_i18n,
    "design_database": handle_design_database,
    "inject_liveblocks": handle_inject_liveblocks,
    "trigger_eas_build": handle_trigger_eas_build,
    "run_in_webcontainer": handle_run_in_webcontainer,
    "run_in_pyodide": handle_run_in_pyodide,
    "generate_tests": handle_generate_tests,
    "generate_openapi_spec": handle_generate_openapi_spec,
    "inject_integration": handle_inject_integration,
    "generate_nextjs_project": handle_generate_nextjs_project,
    "build_capacitor_app": handle_build_capacitor_app,
    "recommend_state_management": handle_recommend_state_management,
    "search_past_projects": handle_search_past_projects,
    "run_in_e2b_sandbox": handle_run_in_e2b_sandbox,
    "deploy_via_ssh": handle_deploy_via_ssh,
    "run_js_sandbox": handle_run_js_sandbox,
    "run_python_sandbox": handle_run_python_sandbox,
    "validate_html_sandbox": handle_validate_html_sandbox,
    "autofix_code_loop": handle_autofix_code_loop,
}

# ───── Continuation-mode tools (clone, ftp, snapshot, sandbox file ops) ─────
# Registered as a merge-in so the freebuild_agent picks them up via the same
# TOOL_DEFINITIONS / TOOL_HANDLERS dispatcher without needing changes there.
try:
    from .continuation_tools import (
        CONTINUATION_TOOL_DEFINITIONS,
        CONTINUATION_TOOL_HANDLERS,
    )
    TOOL_DEFINITIONS.extend(CONTINUATION_TOOL_DEFINITIONS)
    TOOL_HANDLERS.update(CONTINUATION_TOOL_HANDLERS)
    logger.info(f"[cortex_tools] +{len(CONTINUATION_TOOL_DEFINITIONS)} continuation tools registered")
except Exception as _e:
    logger.exception(f"[cortex_tools] failed to register continuation tools: {_e}")


def get_tool_names() -> List[str]:
    return [t["name"] for t in TOOL_DEFINITIONS]


async def dispatch(tool_name: str, args: Dict[str, Any], ctx: Any = None) -> Dict[str, Any]:
    """Central dispatcher used by freebuild_agent's tool-use loop."""
    fn = TOOL_HANDLERS.get(tool_name)
    if not fn:
        return {"ok": False, "error": f"unknown tool '{tool_name}'"}
    try:
        return await fn(args or {}, ctx)
    except Exception as e:
        logger.exception(f"[cortex_tools] {tool_name} failed")
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}
