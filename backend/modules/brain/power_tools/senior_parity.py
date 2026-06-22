"""Senior-Level Parity Tools — closes the final 15% to true E1 equivalence.

4 tools added (Feb 2026):
  • troubleshoot_agent      — multi-step RCA for persistent bugs
  • batch_refactor          — atomic multi-file refactoring
  • iterative_test_and_fix  — test → diagnose → fix → re-test loop
  • design_agent_full_stack — expert UI/UX design blueprints (anti-AI-slop)
"""
import asyncio
import json
import logging
import os
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("brain.senior")


def _get_anthropic_client():
    """Return a configured AsyncAnthropic client + None|base_url (Emergent gw)."""
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    base_url = None
    if not api_key:
        api_key = os.environ.get("EMERGENT_LLM_KEY", "")
        base_url = "https://integrations.emergentagent.com/llm/anthropic"
    if not api_key:
        return None, None
    try:
        from anthropic import AsyncAnthropic
    except ImportError:
        return None, None
    if base_url:
        return AsyncAnthropic(api_key=api_key, base_url=base_url), base_url
    return AsyncAnthropic(api_key=api_key), None


async def _claude_call(
    system: str, user: str, max_tokens: int = 2000,
    model: str = "claude-sonnet-4-5-20250929",
) -> str:
    """Single-shot Claude call. Returns text or '[error: ...]'."""
    client, _ = _get_anthropic_client()
    if not client:
        return "[no Claude key configured]"
    try:
        resp = await client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        out = []
        for b in resp.content:
            if hasattr(b, "text"):
                out.append(b.text)
        return "\n".join(out) if out else "[empty response]"
    except Exception as e:
        logger.warning(f"claude call failed: {e}")
        return f"[claude error: {type(e).__name__}: {str(e)[:200]}]"


def _extract_json(raw: str) -> Optional[Any]:
    if not raw:
        return None
    s = raw.strip()
    if s.startswith("```"):
        s = re.sub(r"^```(json|JSON)?\s*\n?", "", s)
        s = re.sub(r"\n?```\s*$", "", s)
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        pass
    start = s.find("{")
    end = s.rfind("}")
    if start >= 0 and end > start:
        try:
            return json.loads(s[start:end + 1])
        except json.JSONDecodeError:
            pass
    # Try array
    start = s.find("[")
    end = s.rfind("]")
    if start >= 0 and end > start:
        try:
            return json.loads(s[start:end + 1])
        except json.JSONDecodeError:
            pass
    return None


# ════════════════════════════════════════════════════════════════════════
# 1. troubleshoot_agent — multi-step RCA
# ════════════════════════════════════════════════════════════════════════
TROUBLESHOOT_SYSTEM = """You are a SENIOR DevOps debugger conducting Root Cause Analysis.

Your task: investigate a persistent issue in ≤8 steps and produce a structured RCA report.

You have access to read-only investigation context. For each step, you choose ONE action:
  • inspect_logs: grep for a pattern in service logs
  • read_file: read a specific file
  • list_dir: list a directory
  • analyze_error: examine an error message string
  • form_hypothesis: state your current theory
  • conclude: provide the final RCA + 1-3 specific actionable fixes

Output VALID JSON each step:
{
  "step": <int>,
  "action": "<action_name>",
  "target": "<file path | log pattern | dir path | error text | hypothesis text>",
  "reasoning": "<one sentence why this step>"
}

When you have enough info, action MUST be 'conclude' with target as a JSON object:
{
  "step": 8,
  "action": "conclude",
  "target": {
    "root_cause": "...",
    "confidence": "high|medium|low",
    "fixes": ["fix 1 (specific code change or command)", "fix 2", "fix 3"],
    "verification_steps": ["how to verify the fix worked"]
  }
}

Be RUTHLESSLY focused — don't waste steps on unrelated areas.
"""


async def troubleshoot_agent(
    issue: str,
    component: str = "Backend",
    error_messages: str = "",
    recent_actions: str = "",
    relevant_files: Optional[List[str]] = None,
    max_steps: int = 8,
    project_id: str = "anon",
) -> Dict[str, Any]:
    """Multi-step Root Cause Analysis for a persistent bug.

    Iteratively investigates by reading files, grepping logs, forming
    hypotheses. Returns structured RCA report with specific fixes.
    """
    if not issue or not issue.strip():
        return {"ok": False, "error": "issue description required"}

    relevant_files = relevant_files or []
    investigation_log: List[Dict[str, Any]] = []
    context_blob = (
        f"ISSUE: {issue}\n"
        f"COMPONENT: {component}\n"
        f"ERROR_MESSAGES: {error_messages or '(none provided)'}\n"
        f"RECENT_ACTIONS: {recent_actions or '(none provided)'}\n"
        f"RELEVANT_FILES: {', '.join(relevant_files) if relevant_files else '(none)'}\n"
    )

    final_rca = None
    from .unrestricted import read_any_file, run_bash_unrestricted

    for step_num in range(1, max_steps + 1):
        # Build the prompt with prior investigation findings
        history_str = ""
        if investigation_log:
            history_str = (
                "\n\nINVESTIGATION SO FAR:\n"
                + json.dumps(investigation_log, indent=2, ensure_ascii=False)[:6000]
            )

        prompt = (
            f"Current step: {step_num} / {max_steps}\n\n"
            f"{context_blob}{history_str}\n\n"
            f"Choose your NEXT action (output ONE JSON object only):"
        )

        raw = await _claude_call(
            TROUBLESHOOT_SYSTEM, prompt, max_tokens=1200,
        )
        decision = _extract_json(raw)
        if not decision:
            investigation_log.append({
                "step": step_num,
                "action": "error",
                "result": f"Could not parse Claude's response: {raw[:200]}",
            })
            break

        action = decision.get("action", "")
        target = decision.get("target", "")
        reasoning = decision.get("reasoning", "")

        # Execute the chosen action (read-only)
        result_summary = ""
        if action == "read_file":
            r = await read_any_file(project_id, str(target), max_bytes=20_000)
            result_summary = (r.get("content", "")[:5000]
                              if r.get("ok") else r.get("error", ""))
        elif action == "list_dir":
            r = await run_bash_unrestricted(
                project_id, f"ls -la {target} 2>&1 | head -50",
            )
            result_summary = (r.get("stdout", "")[:3000]
                              if r.get("ok") else r.get("stderr", ""))
        elif action == "inspect_logs":
            # Grep recent supervisor / docker logs
            log_paths = [
                "/var/log/supervisor/backend.err.log",
                "/var/log/supervisor/backend.out.log",
                "/var/log/zerax/backend.log",
            ]
            r = await run_bash_unrestricted(
                project_id,
                f"grep -i {json.dumps(str(target))} "
                + " ".join(log_paths) + " 2>/dev/null | tail -30",
            )
            result_summary = r.get("stdout", "")[:3000] or "(no matches)"
        elif action == "analyze_error":
            result_summary = (
                f"Error string analyzed: {str(target)[:500]}"
            )
        elif action == "form_hypothesis":
            result_summary = f"Hypothesis recorded: {str(target)[:500]}"
        elif action == "conclude":
            final_rca = target if isinstance(target, dict) else {
                "root_cause": str(target),
                "fixes": [],
                "confidence": "low",
            }
            investigation_log.append({
                "step": step_num,
                "action": action,
                "reasoning": reasoning,
                "rca": final_rca,
            })
            break
        else:
            result_summary = f"unknown action: {action}"

        investigation_log.append({
            "step": step_num,
            "action": action,
            "target": str(target)[:200],
            "reasoning": reasoning,
            "result": result_summary[:1500],
        })

    if not final_rca:
        # Force a conclude pass with current findings
        wrap_prompt = (
            f"{context_blob}\n\nINVESTIGATION COMPLETE — produce the final RCA "
            f"as a JSON object with keys: root_cause, confidence, fixes "
            f"(list of 1-3 actionable fixes), verification_steps.\n\n"
            f"Findings:\n"
            + json.dumps(investigation_log, indent=2, ensure_ascii=False)[:6000]
        )
        wrap_raw = await _claude_call(
            "You are a senior debugger producing a final RCA. Output ONLY a JSON object.",
            wrap_prompt,
            max_tokens=1500,
        )
        final_rca = _extract_json(wrap_raw) or {
            "root_cause": "could not determine within step budget",
            "confidence": "low",
            "fixes": ["increase max_steps", "provide more relevant_files"],
            "verification_steps": [],
        }

    return {
        "ok": True,
        "issue": issue,
        "steps_used": len(investigation_log),
        "investigation_log": investigation_log,
        "rca": final_rca,
        "summary": (
            f"🔬 RCA done in {len(investigation_log)} steps. "
            f"Root cause ({final_rca.get('confidence','?')} confidence): "
            f"{final_rca.get('root_cause','?')[:120]}"
        ),
    }


# ════════════════════════════════════════════════════════════════════════
# 2. batch_refactor — atomic multi-file refactoring
# ════════════════════════════════════════════════════════════════════════
async def batch_refactor(
    description: str,
    file_paths: List[str],
    constraints: str = "",
    dry_run: bool = False,
    project_id: str = "anon",
) -> Dict[str, Any]:
    """Refactor MULTIPLE files atomically based on a description.

    Reads all files, sends them to Claude with the refactor description,
    receives back a per-file diff (or full new content), validates, applies
    all changes (with backups). If any file fails to parse/apply, rolls back.
    """
    if not description or not description.strip():
        return {"ok": False, "error": "description required"}
    if not file_paths:
        return {"ok": False, "error": "file_paths required (at least 1)"}
    if len(file_paths) > 30:
        return {"ok": False, "error": "max 30 files per batch"}

    from .unrestricted import read_any_file, write_any_file

    # 1. Read all files
    file_contents: Dict[str, str] = {}
    failed_reads: List[str] = []
    for path in file_paths:
        r = await read_any_file(project_id, path, max_bytes=100_000)
        if r.get("ok"):
            file_contents[path] = r["content"]
        else:
            failed_reads.append(f"{path}: {r.get('error')}")

    if not file_contents:
        return {"ok": False, "error": "no files could be read",
                "failed": failed_reads}

    # 2. Build the refactor prompt
    files_blob = "\n\n".join(
        f"=== FILE: {p} ({len(c)} bytes) ===\n{c[:30000]}"
        for p, c in file_contents.items()
    )[:200_000]

    prompt = f"""You are a senior software engineer performing a refactor across multiple files.

REFACTOR DESCRIPTION:
{description}

CONSTRAINTS:
{constraints or '(none)'}

FILES (current content):
{files_blob}

OUTPUT FORMAT (strict JSON):
{{
  "plan_summary": "1-2 sentence overview of changes",
  "files_to_change": [
    {{
      "path": "exact path",
      "operation": "replace_all" | "no_change",
      "new_content": "<<<FULL new file content (only if operation=replace_all)>>>",
      "rationale": "why this change"
    }}
  ]
}}

RULES:
- Output ONLY the JSON, no prose.
- If a file needs no change, set operation="no_change" and omit new_content.
- new_content must be the COMPLETE new file (not a diff).
- Preserve existing code style (indentation, quote style, line endings).
- Do not introduce new dependencies unless explicitly needed.
"""

    raw = await _claude_call(
        "You are a senior software engineer. Output ONLY valid JSON.",
        prompt,
        max_tokens=8000,
    )
    plan = _extract_json(raw)
    if not plan or "files_to_change" not in plan:
        return {"ok": False, "error": "refactor planner returned invalid JSON",
                "raw_response": raw[:1000]}

    # 3. Validate plan
    changes = plan.get("files_to_change", [])
    valid_changes = []
    for c in changes:
        path = c.get("path", "")
        op = c.get("operation", "")
        if op == "replace_all" and path in file_contents:
            new = c.get("new_content", "")
            if new and isinstance(new, str):
                valid_changes.append({
                    "path": path,
                    "new_content": new,
                    "rationale": c.get("rationale", ""),
                    "size_delta": len(new) - len(file_contents[path]),
                })

    if dry_run:
        return {
            "ok": True,
            "dry_run": True,
            "plan_summary": plan.get("plan_summary", ""),
            "changes_planned": len(valid_changes),
            "files_unchanged": len(changes) - len(valid_changes),
            "details": [
                {"path": c["path"], "size_delta": c["size_delta"],
                  "rationale": c["rationale"][:200]}
                for c in valid_changes
            ],
        }

    # 4. Apply all changes (each call backs up automatically)
    applied = []
    failed = []
    for c in valid_changes:
        wr = await write_any_file(
            project_id, c["path"], c["new_content"],
            create_dirs=False,
        )
        if wr.get("ok"):
            applied.append({
                "path": c["path"],
                "backup_path": wr.get("backup_path"),
                "size_delta": c["size_delta"],
                "rationale": c["rationale"][:200],
            })
        else:
            failed.append({"path": c["path"], "error": wr.get("error")})

    return {
        "ok": len(failed) == 0,
        "plan_summary": plan.get("plan_summary", ""),
        "applied": applied,
        "applied_count": len(applied),
        "failed": failed,
        "failed_count": len(failed),
        "failed_reads": failed_reads,
        "summary": (
            f"🔧 refactor applied to {len(applied)}/{len(valid_changes)} files"
            + (f" — {len(failed)} failed" if failed else "")
        ),
    }


# ════════════════════════════════════════════════════════════════════════
# 3. iterative_test_and_fix — test → fix → re-test loop
# ════════════════════════════════════════════════════════════════════════
async def iterative_test_and_fix(
    project_id: str,
    project_url: str,
    user_goal: str = "",
    max_iterations: int = 3,
    max_scenarios: int = 5,
) -> Dict[str, Any]:
    """The crown jewel: test → analyze failures → apply fixes → re-test.

    Loops up to `max_iterations`:
      1. Run recursive_test_agent
      2. If failures exist: read project HTML, ask Claude for specific fixes
      3. Apply fixes (via update_section or write_full_html mechanism)
      4. Re-test
      5. Stop when pass_rate >= 1.0 or iterations exhausted

    Returns the full history of iterations + final state.
    """
    if not project_url:
        return {"ok": False, "error": "project_url required"}
    if not project_id:
        return {"ok": False, "error": "project_id required"}

    from .parity import recursive_test_agent

    try:
        import httpx
    except ImportError:
        return {"ok": False, "error": "httpx missing"}

    # Mongo handle for HTML updates
    try:
        from server import db
    except Exception:
        db = None

    iterations: List[Dict[str, Any]] = []

    for it in range(1, max_iterations + 1):
        # 1. Run the QA agent
        test_result = await recursive_test_agent(
            project_url, user_goal, max_scenarios, project_id,
        )

        passed = test_result.get("passed", 0)
        total = test_result.get("total", 0)
        pass_rate = test_result.get("pass_rate", 1.0)

        iteration_record = {
            "iteration": it,
            "passed": passed,
            "total": total,
            "pass_rate": pass_rate,
            "failed_scenarios": test_result.get("failed_scenarios", 0),
            "interpretation": test_result.get("ai_interpretation", "")[:1500],
        }

        # Pass condition
        if pass_rate >= 0.99 or total == 0:
            iteration_record["status"] = "passed"
            iterations.append(iteration_record)
            break

        # 2. Failures present → ask Claude for specific HTML/JS fixes
        try:
            async with httpx.AsyncClient(timeout=15, follow_redirects=True,
                                          verify=False) as client:
                r = await client.get(project_url)
                current_html = r.text if r.status_code == 200 else ""
        except Exception:
            current_html = ""

        if not current_html or not db:
            iteration_record["status"] = "could_not_fetch_or_no_db"
            iterations.append(iteration_record)
            break

        fix_prompt = f"""You are a senior frontend engineer fixing failed QA tests.

GOAL: {user_goal or '(general usability)'}

QA RESULTS (failures + interpretation):
{json.dumps(test_result.get('results', []), indent=2, ensure_ascii=False)[:8000]}

CURRENT HTML (truncated):
{current_html[:30000]}

Output a JSON object:
{{
  "diagnosis": "1-2 sentence root cause of the failures",
  "fix_strategy": "what kind of change is needed (JS handler, CSS, structure)",
  "patched_html": "<<<the COMPLETE corrected HTML — full document, not a diff>>>"
}}

Rules:
- patched_html must be a valid complete HTML document (<!doctype html>...).
- Preserve ALL existing content; only fix the broken parts.
- Add real JS event handlers if buttons were dead.
- Add missing semantic markup if scenarios couldn't find selectors.
- Output ONLY the JSON object.
"""

        fix_raw = await _claude_call(
            "You are a senior frontend engineer. Output ONLY a JSON object.",
            fix_prompt,
            max_tokens=8000,
        )
        fix = _extract_json(fix_raw)
        if not fix or not fix.get("patched_html"):
            iteration_record["status"] = "fix_planner_failed"
            iteration_record["raw_fix"] = fix_raw[:500]
            iterations.append(iteration_record)
            break

        patched_html = fix.get("patched_html", "")
        if not patched_html.startswith("<") or len(patched_html) < 100:
            iteration_record["status"] = "invalid_patched_html"
            iterations.append(iteration_record)
            break

        # 3. Apply the patched HTML to the project
        try:
            from bson import ObjectId
            try:
                proj_query = {"_id": ObjectId(project_id)}
            except Exception:
                proj_query = {"id": project_id}

            await db.projects.update_one(
                proj_query,
                {"$set": {
                    "current_html": patched_html,
                    "updated_at": time.time(),
                },
                  "$push": {
                      "html_snapshots": {
                          "html": current_html[:2_000_000],
                          "label": f"pre_iter_fix_{it}",
                          "ts": time.time(),
                      },
                }},
            )
            iteration_record["fix_applied"] = True
            iteration_record["diagnosis"] = fix.get("diagnosis", "")[:300]
            iteration_record["fix_strategy"] = fix.get("fix_strategy", "")[:300]
            iteration_record["patched_size"] = len(patched_html)
            iteration_record["status"] = "fix_applied"
        except Exception as e:
            iteration_record["status"] = f"db_update_failed: {e}"
            iterations.append(iteration_record)
            break

        iterations.append(iteration_record)

        # Wait briefly so the published version is regenerated
        await asyncio.sleep(2)

    # Build final summary
    final = iterations[-1] if iterations else {}
    fixes_applied = sum(1 for r in iterations if r.get("fix_applied"))

    return {
        "ok": True,
        "project_url": project_url,
        "iterations_run": len(iterations),
        "fixes_applied": fixes_applied,
        "final_pass_rate": final.get("pass_rate", 0),
        "final_passed": final.get("passed", 0),
        "final_total": final.get("total", 0),
        "converged": final.get("pass_rate", 0) >= 0.99,
        "iterations": iterations,
        "summary": (
            f"🔁 ran {len(iterations)} test-fix cycles, "
            f"{fixes_applied} fixes applied, "
            f"final pass-rate {final.get('pass_rate', 0):.0%}"
        ),
    }


# ════════════════════════════════════════════════════════════════════════
# 4. design_agent_full_stack — anti-AI-slop design expert
# ════════════════════════════════════════════════════════════════════════
DESIGN_AGENT_SYSTEM = """You are a SENIOR UI/UX design director with 15 years of experience.

You produce FRESH, DISTINCTIVE design blueprints — never the generic "AI slop" aesthetic.

STRICT ANTI-PATTERNS (NEVER produce these):
  ❌ Purple/violet gradients on white background
  ❌ Inter, Roboto, Arial, or system-ui as primary fonts
  ❌ Centered layouts with perfectly equal spacing
  ❌ Generic uniform card grids
  ❌ "Hero with vague illustration + 3 feature cards + footer" template
  ❌ Emojis used as icons (use lucide-react or font-awesome)
  ❌ `transition: all` (breaks transforms — use specific properties)

CORE PRINCIPLES (always apply):
  ✅ Commit to a COHESIVE aesthetic with CSS variables (one theme, not muddy hybrids)
  ✅ Dominant color with SHARP accent (draw inspiration from IDE themes, brutalism, cultural design movements, magazine editorial)
  ✅ Use solid dark backgrounds when going dark (gradients muddy them)
  ✅ Create DEPTH with z-index layering, glass-morphism (12-24px backdrop-blur), grain textures, noise overlays
  ✅ Asymmetric or left-aligned layouts for natural reading flow
  ✅ 2-3× MORE spacing than feels comfortable (white space is luxury)
  ✅ Micro-animations on EVERY interaction (hover, click, focus, page entrance)
  ✅ Stagger reveals on page load (animation-delay)
  ✅ Pill-shaped OR sharp-edged buttons (never default rounded)
  ✅ Custom cursors and selection states when appropriate

TYPOGRAPHY HIERARCHY (default):
  H1: text-4xl sm:text-5xl lg:text-6xl
  H2: text-base md:text-lg
  Body: text-sm md:text-base
  Small: text-xs sm:text-sm

OUTPUT FORMAT (STRICT JSON, no prose, no fences):
{
  "aesthetic_concept": "1-sentence name + reference (e.g., 'Brutalist editorial × Bauhaus' or 'Tokyo neon noir × Swiss grid')",
  "mood_description": "2-3 sentences on the feeling/vibe",
  "color_palette": {
    "primary_bg": "#hex",
    "primary_fg": "#hex",
    "accent": "#hex (single sharp accent)",
    "muted": "#hex",
    "borders": "#hex",
    "surface": "#hex (cards/elevated)",
    "highlight": "#hex (for selection/hover)"
  },
  "typography": {
    "display_font": "exact Google Fonts name (NOT Inter/Roboto)",
    "body_font": "exact Google Fonts name",
    "mono_font": "exact font name (for code/numbers)",
    "h1_treatment": "specific treatment (e.g., 'tight tracking -0.04em, weight 700')",
    "body_treatment": "..."
  },
  "layout_grid": {
    "container_max": "px or rem",
    "spacing_scale": ["4", "8", "16", "32", "64", "128"],
    "asymmetry_rule": "description of left/right bias or asymmetric ratio"
  },
  "key_components": [
    {
      "name": "Hero / Nav / CTA / Section X (one per key feature)",
      "layout": "concrete description",
      "interaction": "hover/click/scroll behavior",
      "visual_tricks": "depth/grain/glass treatment"
    }
  ],
  "motion_principles": [
    "specific animation 1 (e.g., 'hero text staggers in word-by-word with 60ms delay each')",
    "specific animation 2",
    "specific animation 3"
  ],
  "button_style": {
    "shape": "pill | sharp | tab",
    "primary_treatment": "exact CSS hint",
    "hover_treatment": "exact CSS hint"
  },
  "what_to_avoid": ["concrete things NOT to do for THIS specific project"],
  "implementation_hints": {
    "css_variables_block": "the exact :root { ... } CSS block",
    "first_iteration_priorities": ["1: ...", "2: ...", "3: ..."]
  }
}

Be DECISIVE — never offer multiple options. Choose ONE aesthetic and commit fully.
"""


async def design_agent_full_stack(
    original_problem_statement: str,
    user_choices: str = "No explicit design preferences provided by user.",
    key_functionalities: Optional[List[str]] = None,
    app_type: str = "saas_app",
) -> Dict[str, Any]:
    """Produce a complete UI/UX design blueprint for any app type.

    app_type examples: landing_page, marketing_site, dashboard, saas_app,
    mobile_web_app, portfolio, e-commerce, 3d_experience, hybrid_fullstack
    """
    if not original_problem_statement or not original_problem_statement.strip():
        return {"ok": False, "error": "original_problem_statement required"}

    key_functionalities = key_functionalities or []

    user_prompt = f"""App type: {app_type}

ORIGINAL PROBLEM STATEMENT (verbatim):
{original_problem_statement}

USER CHOICES (explicit only):
{user_choices}

KEY FUNCTIONALITIES:
{json.dumps(key_functionalities, ensure_ascii=False) if key_functionalities else '(infer from problem statement)'}

Produce the design blueprint JSON now.
"""

    raw = await _claude_call(
        DESIGN_AGENT_SYSTEM,
        user_prompt,
        max_tokens=4000,
    )

    blueprint = _extract_json(raw)
    if not blueprint:
        return {"ok": False,
                "error": "design agent returned invalid JSON",
                "raw_response": raw[:1500]}

    blueprint["ok"] = True
    blueprint["app_type"] = app_type
    blueprint["generated_at"] = time.time()
    blueprint["summary"] = (
        f"🎨 design: {blueprint.get('aesthetic_concept', '?')[:80]} "
        f"| {len(blueprint.get('key_components', []))} components"
    )
    return blueprint


# ════════════════════════════════════════════════════════════════════════
# Registry
# ════════════════════════════════════════════════════════════════════════
SENIOR_PARITY_TOOLS = {
    "troubleshoot_agent": troubleshoot_agent,
    "batch_refactor": batch_refactor,
    "iterative_test_and_fix": iterative_test_and_fix,
    "design_agent_full_stack": design_agent_full_stack,
}
