"""
🔬 PHASES 1-4 — Comprehensive Verification Suite

Tests all 24 new components built in this session.
Categorized by phase, with functional checks (not just import).
"""
import asyncio
import os
import sys

sys.path.insert(0, "/app/backend")

P = 0  # pass
F = 0  # fail
FAILS = []


def ok(name, msg=""):
    global P
    P += 1
    print(f"  ✅ {name}" + (f" — {msg}" if msg else ""))


def fail(name, msg):
    global F
    F += 1
    FAILS.append(f"{name}: {msg}")
    print(f"  ❌ {name} — {msg}")


def section(t):
    print(f"\n=== {t} ===")


# ──────────────────────────── PHASE 1 ────────────────────────────
def test_phase_1():
    section("PHASE 1 — Creative Layer")

    # 1.1 Recipes
    from modules.freebuild.creative_recipes import (
        list_recipes, get_recipe, find_recipe_for_intent, render_recipes_atlas,
    )
    recipes = list_recipes()
    if len(recipes) >= 30: ok("recipes-count", f"{len(recipes)} وصفة")
    else: fail("recipes-count", f"only {len(recipes)} (need ≥30)")

    cosmic = get_recipe("cosmic_immersive_landing")
    if cosmic and cosmic.get("shaders"): ok("recipes-get", f"cosmic has {len(cosmic['shaders'])} shaders")
    else: fail("recipes-get", "couldn't fetch cosmic recipe")

    found = find_recipe_for_intent("اعمل لي موقع كوني فضائي")
    if found and found.get("id") == "cosmic_immersive_landing":
        ok("recipes-intent-cosmic")
    else: fail("recipes-intent-cosmic", f"got {found.get('id') if found else None}")

    found = find_recipe_for_intent("متجر عطور فاخر")
    if found and "perfume" in found.get("id", ""):
        ok("recipes-intent-perfume")
    else: fail("recipes-intent-perfume", f"got {found.get('id') if found else None}")

    atlas = render_recipes_atlas()
    if "cosmic" in atlas and len(atlas) > 500:
        ok("recipes-atlas-render", f"len={len(atlas)}")
    else: fail("recipes-atlas-render", f"len={len(atlas)}")

    # 1.2 Shaders
    from modules.freebuild.shaders_library import (
        list_shaders, get_shader, find_shaders_for_intent, render_shader_catalog,
        render_shader_for_inject,
    )
    shaders = list_shaders()
    if len(shaders) >= 28: ok("shaders-count", f"{len(shaders)} shader")
    else: fail("shaders-count", f"only {len(shaders)}")

    nebula = get_shader("nebula")
    if nebula and nebula.get("fragment_shader"):
        ok("shaders-get-nebula", "has GLSL fragment_shader")
    else: fail("shaders-get-nebula", "no nebula or no GLSL")

    found_s = find_shaders_for_intent("خلفية فضاء كون نيون")
    if "nebula" in found_s or "starfield" in found_s:
        ok("shaders-intent", f"matched {found_s[:3]}")
    else: fail("shaders-intent", f"got {found_s}")

    inject = render_shader_for_inject("glitch")
    if inject and inject.get("kind") == "css" and "@keyframes" in inject.get("head_inject", ""):
        ok("shaders-inject-glitch")
    else: fail("shaders-inject-glitch", str(inject)[:200])

    # 1.4 Reviewer
    from modules.freebuild.orchestrator.review_cortex import review_code, render_review_report_ar
    code_with_issues = """<!DOCTYPE html><html><head><title>x</title></head><body>
    <img src=a.jpg>
    <script>eval(userInput); console.log('test'); document.write('hi')</script>
    </body></html>"""
    report = review_code(code_with_issues, code_type="html")
    if report["summary"].get("critical", 0) >= 1 and not report["passed"]:
        ok("reviewer-detects-critical", f"score={report['score']}")
    else: fail("reviewer-detects-critical", f"{report['summary']}")
    txt = render_review_report_ar(report)
    if "تقرير المراجعة" in txt:
        ok("reviewer-report-render")
    else: fail("reviewer-report-render", txt[:200])


async def test_phase_1_async():
    section("PHASE 1 — Async")
    # 1.5 Brand DNA (LLM)
    from modules.freebuild.orchestrator.brand_dna import extract_brand_dna, render_brand_dna_hint
    dna = await extract_brand_dna("متجر قهوة عُماني فاخر بنبرة هادئة أنيقة")
    if dna and dna.get("palette") and len(dna["palette"]) >= 3:
        ok("brand-dna-extract", f"palette={dna['palette'][:3]}")
    else: fail("brand-dna-extract", str(dna)[:200])
    hint = render_brand_dna_hint(dna)
    if "Brand DNA" in hint:
        ok("brand-dna-render")
    else: fail("brand-dna-render", hint[:200])

    # 1.3 Asset Pipeline (no real assets — test the orchestration path)
    from modules.freebuild.orchestrator.asset_pipeline import generate_recipe_assets
    fake_recipe = {"assets": [{"type": "AUDIO", "kind": "ambient", "prompt": "calm"}]}
    result = await generate_recipe_assets(fake_recipe, {"id": "test"}, db=None, budget_credits=100)
    if "assets" in result and isinstance(result.get("credits_spent"), int):
        ok("asset-pipeline-shape", f"spent={result['credits_spent']}, failures={len(result['failures'])}")
    else: fail("asset-pipeline-shape", str(result)[:200])


# ──────────────────────────── PHASE 2 ────────────────────────────
def test_phase_2():
    section("PHASE 2 — Architectural Brain")

    # 2.1 Architect heuristic + fallback
    from modules.freebuild.orchestrator.cortices.architect_cortex import (
        should_run_architect, _fallback_architecture, render_architecture_summary_ar,
    )
    if should_run_architect("اعمل لي SaaS مع auth + dashboard + database"):
        ok("architect-detects-complex")
    else: fail("architect-detects-complex", "complex SaaS not detected")
    if not should_run_architect("اعمل لي صفحة هبوط بسيطة"):
        ok("architect-skips-simple")
    else: fail("architect-skips-simple", "simple landing wrongly tagged complex")
    arch = _fallback_architecture("simple page")
    if arch and arch.get("file_tree"):
        ok("architect-fallback")
    else: fail("architect-fallback", str(arch)[:200])
    txt = render_architecture_summary_ar(arch)
    if "التخطيط المعماري" in txt:
        ok("architect-render")
    else: fail("architect-render", txt[:200])

    # 2.2 Code Sandbox (sync parts)
    from modules.freebuild.orchestrator.code_sandbox import validate_html, parse_stack_trace
    res = validate_html("<!DOCTYPE html><html><body><div>x</body></html>")
    if not res["ok"] and len(res["issues"]) >= 1:
        ok("sandbox-validate-html-detects-mismatch", f"detected {len(res['issues'])} issue(s)")
    else: fail("sandbox-validate-html-detects-mismatch", str(res))
    parsed = parse_stack_trace("ReferenceError: foo is not defined\n    at Object.<anonymous> (/tmp/x.js:5:1)")
    if parsed["error_type"] == "ReferenceError" and parsed["line"] == 5:
        ok("sandbox-parse-trace")
    else: fail("sandbox-parse-trace", str(parsed))

    # 2.5 TypeScript helpers
    from modules.freebuild.orchestrator.typescript_cortex import (
        get_default_tsconfig, render_tsconfig_json, suggest_interfaces,
    )
    cfg = get_default_tsconfig()
    if cfg["compilerOptions"]["strict"] and cfg["compilerOptions"]["target"] == "ES2022":
        ok("ts-tsconfig-default")
    else: fail("ts-tsconfig-default", str(cfg)[:200])
    out = render_tsconfig_json({"jsx": "preserve"})
    if '"jsx": "preserve"' in out:
        ok("ts-tsconfig-merge")
    else: fail("ts-tsconfig-merge")
    sug = suggest_interfaces("const userProfile = { name: 'a', age: 20, email: 'b@c.com' };")
    if sug["count"] >= 1 and sug["interfaces_suggested"][0]["interface"] == "UserProfile":
        ok("ts-suggest-interfaces")
    else: fail("ts-suggest-interfaces", str(sug))

    # 2.6 Refactor
    from modules.freebuild.orchestrator.refactor_cortex import (
        rename_identifier, find_duplicate_blocks, add_class_globally,
    )
    files = {"a.js": "const userName = 'foo'; console.log(userName);", "b.js": "let userName = 1;"}
    r = rename_identifier(files, "userName", "customerName")
    if r["total_replacements"] == 3 and len(r["files_changed"]) == 2:
        ok("refactor-rename")
    else: fail("refactor-rename", str(r))

    files2 = {
        "a.html": "<header>X</header>\n<nav>Y</nav>\n<main>A</main>\n<footer>F</footer>\n<aside>S</aside>",
        "b.html": "<header>X</header>\n<nav>Y</nav>\n<main>A</main>\n<footer>F</footer>\n<aside>S</aside>",
    }
    dups = find_duplicate_blocks(files2, min_lines=3)
    if len(dups) >= 1 and dups[0]["occurrences"] >= 2:
        ok("refactor-find-duplicates", f"{len(dups)} dup blocks")
    else: fail("refactor-find-duplicates", str(dups)[:200])

    add = add_class_globally({"x.html": '<button id="cta">go</button>'}, "#cta", "primary")
    if add.get("ok") and "primary" in add["files_changed"]["x.html"]:
        ok("refactor-add-class")
    else: fail("refactor-add-class", str(add))


async def test_phase_2_async():
    section("PHASE 2 — Async")
    from modules.freebuild.orchestrator.code_sandbox import run_python, lint_python

    res = await run_python("print(2+2)")
    if res["ok"] and "4" in res["stdout"]:
        ok("sandbox-run-python")
    else: fail("sandbox-run-python", str(res)[:200])

    res = await run_python("print(undefined_var)")
    if not res["ok"] and "NameError" in res["stderr"]:
        ok("sandbox-run-python-error")
    else: fail("sandbox-run-python-error", str(res)[:200])

    res = await lint_python("def f(:\n  pass")
    if not res["ok"]:
        ok("sandbox-lint-python-syntax-error")
    else: fail("sandbox-lint-python-syntax-error", "should have failed")


# ──────────────────────────── PHASE 3 ────────────────────────────
def test_phase_3():
    section("PHASE 3 — SaaS Capability")

    # 3.1 Next.js helpers
    from modules.freebuild.orchestrator.nextjs_cortex import (
        default_package_json, default_tailwind_config,
    )
    pkg = default_package_json("my-app")
    if '"next": "^15' in pkg and '"react": "^18' in pkg:
        ok("nextjs-package-json")
    else: fail("nextjs-package-json", pkg[:200])
    cfg = default_tailwind_config(["#ff0000", "#00ff00"])
    if 'brand-1' in cfg and 'tailwindcss' in cfg:
        ok("nextjs-tailwind-config")
    else: fail("nextjs-tailwind-config", cfg[:200])

    # 3.2 Backend patterns
    from modules.freebuild.backend_patterns import (
        list_patterns, get_pattern, find_patterns_for_intent, render_patterns_catalog,
    )
    p = list_patterns()
    if len(p) >= 15:
        ok("backend-patterns-count", f"{len(p)} patterns")
    else: fail("backend-patterns-count", f"only {len(p)}")
    jwt_p = get_pattern("jwt_auth_fastapi")
    if jwt_p and "files" in jwt_p and "auth/jwt_handler.py" in jwt_p["files"]:
        ok("backend-pattern-jwt-loaded")
    else: fail("backend-pattern-jwt-loaded", str(jwt_p)[:200])
    found = find_patterns_for_intent("احتاج WebSocket realtime chat")
    if "websocket_fastapi" in found:
        ok("backend-pattern-intent-websocket")
    else: fail("backend-pattern-intent-websocket", str(found))
    catalog = render_patterns_catalog()
    if "Backend Patterns" in catalog and len(catalog) > 200:
        ok("backend-patterns-catalog")
    else: fail("backend-patterns-catalog", catalog[:200])

    # 3.3 DB Designer renderers
    from modules.freebuild.orchestrator.db_designer import (
        render_schema_as_mongo_pydantic, render_schema_as_postgres_sql,
    )
    schema_mongo = {
        "database_type": "mongodb",
        "collections_or_tables": [{
            "name": "users",
            "fields": [
                {"name": "id", "type": "uuid", "required": True, "primary": True},
                {"name": "email", "type": "string", "required": True, "unique": True},
                {"name": "created_at", "type": "datetime", "required": True, "default": "now()"},
            ],
        }]
    }
    py = render_schema_as_mongo_pydantic(schema_mongo)
    if "class User(BaseModel)" in py and "email: str" in py:
        ok("db-designer-mongo-pydantic")
    else: fail("db-designer-mongo-pydantic", py[:200])

    schema_pg = {
        "database_type": "postgres",
        "collections_or_tables": [{
            "name": "products",
            "fields": [
                {"name": "id", "type": "uuid", "primary": True, "required": True},
                {"name": "price", "type": "float", "required": True},
            ],
            "indexes": [{"name": "price_idx", "fields": ["price"], "unique": False}]
        }]
    }
    sql = render_schema_as_postgres_sql(schema_pg)
    if "CREATE TABLE products" in sql and "PRIMARY KEY" in sql and "CREATE INDEX price_idx" in sql:
        ok("db-designer-postgres-sql")
    else: fail("db-designer-postgres-sql", sql[:200])

    # 3.4 OpenAPI generator
    from modules.freebuild.orchestrator.openapi_generator import (
        build_openapi_spec, endpoints_from_schema, render_swagger_html,
    )
    eps = endpoints_from_schema(schema_pg)
    if len(eps) == 5:
        ok("openapi-endpoints-from-schema", f"{len(eps)} REST endpoints")
    else: fail("openapi-endpoints-from-schema", f"got {len(eps)} expected 5")
    spec = build_openapi_spec("Test API", "1.0", eps)
    if spec.get("openapi") == "3.1.0" and "/api/products" in spec.get("paths", {}):
        ok("openapi-spec-built")
    else: fail("openapi-spec-built", str(list(spec.get("paths", {}).keys()))[:200])
    swagger = render_swagger_html()
    if "swagger-ui" in swagger:
        ok("openapi-swagger-html")
    else: fail("openapi-swagger-html")

    # 3.5 State management
    from modules.freebuild.orchestrator.state_cortex import (
        recommend_state_strategy, zustand_store_snippet, react_query_snippet,
    )
    rec = recommend_state_strategy("global auth state shared between routes")
    if rec["choice"] == "zustand":
        ok("state-recommend-zustand")
    else: fail("state-recommend-zustand", str(rec))
    rec = recommend_state_strategy("fetch api data with cache")
    if rec["choice"] == "tanstack-query":
        ok("state-recommend-rq")
    else: fail("state-recommend-rq", str(rec))
    z = zustand_store_snippet("Auth", ["user", "token"])
    if "useAuth" in z and "create<AuthState>" in z:
        ok("state-zustand-snippet")
    else: fail("state-zustand-snippet", z[:200])
    rq = react_query_snippet("/api/users", "users")
    if "useUsers" in rq and "useMutation" in rq:
        ok("state-rq-snippet")
    else: fail("state-rq-snippet", rq[:200])


# ──────────────────────────── PHASE 4 ────────────────────────────
def test_phase_4():
    section("PHASE 4 — Production Polish")

    # 4.1 Performance
    from modules.freebuild.orchestrator.performance_optimizer import (
        analyze, apply_lazy_loading, apply_defer_to_scripts,
    )
    html = "<html><head></head><body><img src='a.jpg'><img src='b.jpg'><img src='c.jpg'><img src='d.jpg'><script src='x.js'></script></body></html>"
    rep = analyze(html)
    if rep["score"] >= 0 and len(rep["suggestions"]) >= 1:
        ok("perf-analyze")
    else: fail("perf-analyze", str(rep))
    lazy = apply_lazy_loading("<img src='a.jpg'><img src='b.jpg' alt='x'>")
    if lazy.count("loading=\"lazy\"") == 2:
        ok("perf-lazy-loading")
    else: fail("perf-lazy-loading", lazy)
    defer = apply_defer_to_scripts("<script src='a.js'></script>")
    if "defer" in defer:
        ok("perf-defer-scripts")
    else: fail("perf-defer-scripts", defer)

    # 4.2 SEO
    from modules.freebuild.orchestrator.seo_cortex import (
        build_jsonld, build_meta_tags, build_sitemap_xml, build_robots_txt, audit_seo,
    )
    ld = build_jsonld("Organization", {"name": "Zenrex", "url": "https://zenrex.ai"})
    if 'application/ld+json' in ld and '"Organization"' in ld:
        ok("seo-jsonld")
    else: fail("seo-jsonld", ld[:200])
    meta = build_meta_tags("Title", "Desc", canonical_url="https://x.com", og_image="https://x.com/og.png")
    if '<title>Title</title>' in meta and 'og:image' in meta:
        ok("seo-meta-tags")
    else: fail("seo-meta-tags", meta[:200])
    sm = build_sitemap_xml([{"loc": "/"}, {"loc": "/about"}])
    if "<urlset" in sm and "/about" in sm:
        ok("seo-sitemap")
    else: fail("seo-sitemap", sm[:200])
    rb = build_robots_txt(disallow=["/admin"])
    if "Disallow: /admin" in rb and "Sitemap:" in rb:
        ok("seo-robots-txt")
    else: fail("seo-robots-txt", rb)
    audit = audit_seo("<html><head></head><body></body></html>")
    if len(audit["issues"]) >= 2 and audit["score"] < 80:
        ok("seo-audit-detects-issues")
    else: fail("seo-audit-detects-issues", str(audit))

    # 4.3 A11y
    from modules.freebuild.orchestrator.a11y_cortex import (
        audit as a11y_audit, auto_fix_alt_text, auto_fix_lang_attribute, inject_skip_link,
    )
    r = a11y_audit("<html><body><img src='a.jpg'><button><i class='fa fa-x'></i></button></body></html>")
    if r["issues"]:
        ok("a11y-audit-detects")
    else: fail("a11y-audit-detects", str(r))
    fixed = auto_fix_alt_text("<img src='a.jpg'>")
    if 'alt=""' in fixed:
        ok("a11y-auto-fix-alt")
    else: fail("a11y-auto-fix-alt", fixed)
    fixed = auto_fix_lang_attribute("<html><body></body></html>")
    if 'lang="ar"' in fixed and 'dir="rtl"' in fixed:
        ok("a11y-auto-fix-lang")
    else: fail("a11y-auto-fix-lang", fixed)
    fixed = inject_skip_link("<body><div>x</div></body>")
    if 'skip-link' in fixed:
        ok("a11y-skip-link")
    else: fail("a11y-skip-link", fixed)

    # 4.4 i18n
    from modules.freebuild.orchestrator.i18n_cortex import (
        SUPPORTED_LANGS, extract_translatable_strings, render_html_with_lang,
        language_switcher_snippet,
    )
    if "ar" in SUPPORTED_LANGS and SUPPORTED_LANGS["ar"]["dir"] == "rtl":
        ok("i18n-supported-langs")
    else: fail("i18n-supported-langs")
    strs = extract_translatable_strings("<h1>مرحباً</h1><p>السطر الثاني</p>")
    if len(strs) >= 2:
        ok("i18n-extract", f"{len(strs)} strings")
    else: fail("i18n-extract", str(strs))
    h = render_html_with_lang("<html><body></body></html>", lang="ar")
    if 'lang="ar"' in h and 'dir="rtl"' in h:
        ok("i18n-render-lang")
    else: fail("i18n-render-lang", h[:200])
    sw = language_switcher_snippet("ar", ["ar", "en", "fr"])
    if "العربية" in sw and "English" in sw:
        ok("i18n-switcher")
    else: fail("i18n-switcher", sw[:200])

    # 4.5 PWA
    from modules.freebuild.orchestrator.pwa_cortex import (
        build_manifest, build_service_worker, build_offline_page,
        install_prompt_snippet, push_setup_snippet,
    )
    m = build_manifest("App", "App", "desc")
    if '"start_url": "/"' in m and '"icons"' in m:
        ok("pwa-manifest")
    else: fail("pwa-manifest", m[:200])
    sw = build_service_worker("v3")
    if "CACHE_VERSION = 'v3'" in sw and "addEventListener('push'" in sw:
        ok("pwa-service-worker")
    else: fail("pwa-service-worker", sw[:200])
    off = build_offline_page()
    if "غير متصل" in off:
        ok("pwa-offline-page")
    else: fail("pwa-offline-page")
    sn = install_prompt_snippet()
    if "beforeinstallprompt" in sn and "serviceWorker.register" in sn:
        ok("pwa-install-snippet")
    else: fail("pwa-install-snippet")
    p = push_setup_snippet()
    if "applicationServerKey" in p and "urlBase64ToUint8Array" in p:
        ok("pwa-push-snippet")
    else: fail("pwa-push-snippet")

    # 4.6 Capacitor
    from modules.freebuild.orchestrator.capacitor_cortex import (
        build_capacitor_config, capacitor_package_json, build_instructions_ar,
        push_native_snippet_js,
    )
    c = build_capacitor_config("com.zenrex.app", "Zenrex")
    if "com.zenrex.app" in c and "CapacitorConfig" in c:
        ok("capacitor-config")
    else: fail("capacitor-config", c[:200])
    pkg = capacitor_package_json()
    if "@capacitor/core" in pkg and "@capacitor/android" in pkg:
        ok("capacitor-package-json")
    else: fail("capacitor-package-json", pkg[:200])
    ins = build_instructions_ar()
    if "Android Studio" in ins and "Xcode" in ins:
        ok("capacitor-instructions")
    else: fail("capacitor-instructions")
    sn = push_native_snippet_js()
    if "PushNotifications" in sn and "addListener" in sn:
        ok("capacitor-push")
    else: fail("capacitor-push")

    # 4.8 Integrations
    from modules.freebuild.orchestrator.integrations_cortex import (
        sentry_setup_js, posthog_setup_js, google_analytics_setup_js, list_all,
    )
    s = sentry_setup_js()
    if "Sentry" in s["init_snippet"]:
        ok("integrations-sentry")
    else: fail("integrations-sentry")
    g = google_analytics_setup_js("G-1234")
    if "G-1234" in g["head_inject"]:
        ok("integrations-ga4")
    else: fail("integrations-ga4")
    if len(list_all()) >= 4:
        ok("integrations-list-all")
    else: fail("integrations-list-all")


async def test_phase_4_async():
    section("PHASE 4 — RAG (Async)")
    # 4.7 Cross-Project RAG (no real Mongo write — just verify shape)
    from modules.freebuild.orchestrator.cross_project_rag import (
        render_lessons_hint_ar,
    )
    fake_lessons = [
        {"problem": "CORS issue", "solution": "add CORSMiddleware", "tags": ["cors"], "similarity": 0.85},
        {"problem": "JWT expired", "solution": "refresh token logic", "tags": ["jwt"], "similarity": 0.71},
    ]
    h = render_lessons_hint_ar(fake_lessons)
    if "دروس متعلّمة" in h and "CORS" in h:
        ok("rag-render-lessons-hint")
    else: fail("rag-render-lessons-hint", h[:200])


# ──────────────────────────── MAIN ────────────────────────────
async def main():
    print("\n" + "█" * 60)
    print("█  PHASES 1-4 VERIFICATION — 24 components")
    print("█" * 60)

    test_phase_1()
    await test_phase_1_async()
    test_phase_2()
    await test_phase_2_async()
    test_phase_3()
    test_phase_4()
    await test_phase_4_async()

    print("\n" + "█" * 60)
    print(f"█  RESULT: ✅ {P} pass · ❌ {F} fail")
    print("█" * 60)
    if F:
        print("\nFailures:")
        for f in FAILS:
            print(f"  - {f}")
        sys.exit(1)
    print("🎉 ALL 24 NEW COMPONENTS GREEN.\n")


if __name__ == "__main__":
    asyncio.run(main())
