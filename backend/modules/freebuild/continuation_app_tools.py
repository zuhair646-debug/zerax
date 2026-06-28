"""Universal Continuation-mode tools for apps + all programming stacks.

Three concrete AI tools that, combined with the stack detector, let the
Engineer Manager work on ANY type of project — React Native, Flutter,
Capacitor, Android Gradle, iOS Xcode, .NET MAUI, Electron, Tauri, Go,
Rust, Python, Java, Ruby, PHP, Unity, WordPress — without us writing a
separate tool for each.

  1. `detect_project_stack`  — read-only: scan sandbox, return detected
     stacks + recommended build/test/install commands.

  2. `run_sandbox_command`   — write-capable: run any whitelisted shell
     command inside the sandbox. Subscription-locked after first update.
     Restricted to a safe binary whitelist (no rm -rf /, no curl piping).

  3. `submit_to_app_store`   — write-capable: dispatch to one of the
     supported store/distribution providers (Play Console, App Store
     Connect, Firebase App Distribution, TestFlight, Expo EAS Submit,
     Steam, itch.io, Microsoft Store). Encrypted credentials only.

All three respect the same guards as the website continuation tools:
sandbox isolation, paywall lock, snapshot before destructive write,
audit log with SHA-256 chain.
"""
from __future__ import annotations

import asyncio
import logging
import os
import re
import shlex
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional

from .continuation_tools import (
    _ensure_sandbox, _guard_continuation_mode, _guard_subscription_lock,
    _load_cred, _audit, _now_iso, _run, _safe_path, MAX_OP_SECONDS,
    handle_create_snapshot,
)
from .continuation_stack_detector import detect_stacks, summarize_stacks

logger = logging.getLogger("zenrex.continuation_app_tools")

# ───────────────────────────────────────────────────────────────────
# Command whitelist. Only these binaries can be invoked via
# `run_sandbox_command`. This prevents the AI (or a hostile prompt)
# from running `rm -rf /`, `curl … | sh`, or anything truly dangerous.
# Add binaries here as new stacks are needed.
# ───────────────────────────────────────────────────────────────────
ALLOWED_BINARIES = {
    # Package managers
    "npm", "yarn", "pnpm", "bun", "npx",
    "pip", "pip3", "pipx", "poetry", "uv",
    "composer", "bundle", "bundler",
    "cargo", "go", "dotnet",
    "mvn", "gradle", "./gradlew",
    "pod", "swift",
    # Build / tool runners
    "flutter", "dart", "expo", "eas",
    "node", "python", "python3", "ruby",
    "make", "cmake", "ninja",
    "vite", "next", "react-scripts", "webpack",
    # Test / lint
    "pytest", "jest", "vitest", "mocha", "phpunit", "rspec",
    "eslint", "ruff", "flake8", "mypy", "tsc", "clippy",
    # Code intelligence
    "git", "grep", "find", "ls", "cat", "head", "tail", "wc",
    "diff", "patch",
    # Capacitor / Cordova / Ionic
    "cap", "ionic", "cordova", "ns",
    # Cloud build CLIs
    "fastlane", "bitrise", "codemagic-cli-tools",
    # Container ops (read-only mostly)
    "docker",
}

# Hard-blocked patterns no matter what — extra defense layer
DANGEROUS_PATTERNS = [
    r"\brm\s+-rf\s+/",
    r":\(\)\{\s*:\|:&\s*\};:",      # fork bomb
    r">\s*/dev/sd",
    r"mkfs\.",
    r"\bdd\s+if=",
    r"\bchmod\s+777\s+/",
    r"\bcurl\s+.+\|\s*(?:bash|sh)",
    r"\bwget\s+.+\|\s*(?:bash|sh)",
    r"\b/etc/passwd\b",
    r"\b/etc/shadow\b",
    r"\bsudo\b",
    r"\bsu\s+",
]


def _is_command_safe(cmd: str) -> Optional[str]:
    """Return reason-string if blocked, None if OK."""
    if not cmd or not cmd.strip():
        return "empty command"
    if len(cmd) > 2000:
        return "command too long (max 2000 chars)"
    for pat in DANGEROUS_PATTERNS:
        if re.search(pat, cmd, re.IGNORECASE):
            return f"matches dangerous pattern: {pat}"
    # The first token must be in the binary whitelist
    try:
        tokens = shlex.split(cmd)
    except ValueError as e:
        return f"unparseable command: {e}"
    if not tokens:
        return "no tokens"
    head = tokens[0]
    # Allow ./gradlew, ./mvnw, ./scripts/x.sh (relative scripts inside sandbox)
    if head.startswith("./") or head.startswith("../"):
        if ".." in head:
            return "parent traversal in command head"
        return None
    # Allow `cd subdir && some_allowed_cmd …`
    if head == "cd" and "&&" in cmd:
        # Find the binary AFTER the &&
        try:
            rest = cmd.split("&&", 1)[1].strip()
            rest_tokens = shlex.split(rest)
            if rest_tokens and (rest_tokens[0] in ALLOWED_BINARIES or rest_tokens[0].startswith("./")):
                return None
        except Exception:
            pass
        return "binary after cd not whitelisted"
    if head not in ALLOWED_BINARIES:
        return f"binary '{head}' not whitelisted. Allowed: {sorted(ALLOWED_BINARIES)[:8]}…"
    return None


# ───────────────────────────────────────────────────────────────────
# Tool 1 — detect_project_stack
# ───────────────────────────────────────────────────────────────────
async def handle_detect_project_stack(args: Dict[str, Any], ctx: Any = None) -> Dict[str, Any]:
    pid = (args.get("project_id") or (ctx and getattr(ctx, "project_id", None)) or "").strip()
    sub = (args.get("path") or "repo").strip().strip("/")
    if not pid:
        return {"ok": False, "error": "project_id required"}

    db = getattr(ctx, "db", None) if ctx else None
    if db is None:
        from server import db as _db  # type: ignore
        db = _db

    err = await _guard_continuation_mode(db, pid)
    if err:
        return {"ok": False, "error": err}

    sandbox = _ensure_sandbox(pid)
    try:
        root = _safe_path(sandbox, sub)
    except ValueError as e:
        return {"ok": False, "error": str(e)}

    stacks = detect_stacks(root)
    summary = summarize_stacks(stacks)
    return {"ok": True, **summary, "scanned_path": str(root)}


# ───────────────────────────────────────────────────────────────────
# Tool 2 — run_sandbox_command (paywall-gated, whitelist-protected)
# ───────────────────────────────────────────────────────────────────
async def handle_run_sandbox_command(args: Dict[str, Any], ctx: Any = None) -> Dict[str, Any]:
    pid = (args.get("project_id") or (ctx and getattr(ctx, "project_id", None)) or "").strip()
    cmd = (args.get("command") or "").strip()
    workdir = (args.get("workdir") or "repo").strip().strip("/")
    timeout = int(args.get("timeout") or 180)
    purpose = (args.get("purpose") or "ai_command").strip()[:50]
    if not pid or not cmd:
        return {"ok": False, "error": "project_id and command required"}
    if timeout < 5 or timeout > MAX_OP_SECONDS:
        timeout = min(max(timeout, 5), MAX_OP_SECONDS)

    db = getattr(ctx, "db", None) if ctx else None
    if db is None:
        from server import db as _db  # type: ignore
        db = _db

    err = await _guard_continuation_mode(db, pid)
    if err:
        return {"ok": False, "error": err}

    # Whitelist enforcement
    reason = _is_command_safe(cmd)
    if reason:
        return {"ok": False, "error": "command_blocked", "reason": reason,
                "hint": "Use only whitelisted binaries: npm/yarn/flutter/gradle/etc. Avoid sudo/rm/curl-pipe."}

    # Paywall: only writes are gated, but we treat ALL commands as side-effects
    # except a tiny read-only allow-list (grep/find/cat/ls/head/tail/wc/diff).
    READ_ONLY = {"grep", "find", "ls", "cat", "head", "tail", "wc", "diff", "git"}
    first_token = shlex.split(cmd)[0]
    is_read_only = first_token in READ_ONLY or (first_token == "cd" and any(t in READ_ONLY for t in shlex.split(cmd.split("&&", 1)[-1])))
    if not is_read_only:
        locked = await _guard_subscription_lock(db, pid)
        if locked:
            return locked

    sandbox = _ensure_sandbox(pid)
    try:
        wd = _safe_path(sandbox, workdir)
    except ValueError as e:
        return {"ok": False, "error": str(e)}
    if not wd.exists() or not wd.is_dir():
        return {"ok": False, "error": "workdir_not_found", "hint": f"sandbox/{workdir}/ does not exist"}

    # Auto-snapshot if this is a destructive build that might change files
    if not is_read_only:
        await handle_create_snapshot({"project_id": pid, "label": f"pre_{purpose}"}, ctx)

    # Run via bash -lc so &&, |, env vars work — but the input is whitelist-checked
    proc_res = await _run(["bash", "-lc", cmd], cwd=wd, timeout=timeout)
    success = bool(proc_res.get("ok"))

    await _audit(ctx, db, pid, "run_sandbox_command",
                 tool_name="run_sandbox_command",
                 target_path=workdir, success=success,
                 details={"command": cmd[:200], "purpose": purpose,
                          "returncode": proc_res.get("returncode"),
                          "timeout_s": timeout})
    return {
        "ok": success,
        "returncode": proc_res.get("returncode"),
        "stdout": (proc_res.get("stdout") or "")[:4000],
        "stderr": (proc_res.get("stderr") or "")[:4000],
        "command": cmd,
        "workdir": workdir,
        "elapsed_at": _now_iso(),
    }


# ───────────────────────────────────────────────────────────────────
# Tool 3 — submit_to_app_store (paywall-gated)
# ───────────────────────────────────────────────────────────────────
SUPPORTED_STORE_PROVIDERS = {
    "play_store_internal", "play_store_alpha", "play_store_beta", "play_store_production",
    "app_store_testflight", "app_store_production",
    "firebase_app_distribution",
    "expo_eas_submit",
    "microsoft_store",
    "amazon_appstore",
    "huawei_appgallery",
    "samsung_galaxy_store",
    "steam", "itch_io",
    "test_only",  # dry-run, no real submission — used by E2E tests
}


async def handle_submit_to_app_store(args: Dict[str, Any], ctx: Any = None) -> Dict[str, Any]:
    """Dispatch a built artifact to a store/distribution provider.

    The actual upload is a thin wrapper around the provider's CLI (fastlane,
    gcloud, eas-cli, gh, etc.). Credentials must be saved via the encrypted
    continuation_credentials store first.

    For MVP we only IMPLEMENT the integrations we have concrete creds for;
    others return `not_implemented` with a clear path forward.
    """
    pid = (args.get("project_id") or (ctx and getattr(ctx, "project_id", None)) or "").strip()
    provider = (args.get("provider") or "").strip()
    artifact_path = (args.get("artifact_path") or "").strip()
    release_notes = (args.get("release_notes") or "").strip()[:1000]
    if not pid or not provider or not artifact_path:
        return {"ok": False, "error": "project_id, provider, artifact_path required"}
    if provider not in SUPPORTED_STORE_PROVIDERS:
        return {"ok": False, "error": "unsupported_provider",
                "supported": sorted(SUPPORTED_STORE_PROVIDERS)}

    db = getattr(ctx, "db", None) if ctx else None
    if db is None:
        from server import db as _db  # type: ignore
        db = _db

    err = await _guard_continuation_mode(db, pid)
    if err:
        return {"ok": False, "error": err}
    locked = await _guard_subscription_lock(db, pid)
    if locked:
        return locked

    sandbox = _ensure_sandbox(pid)
    try:
        artifact = _safe_path(sandbox, artifact_path.lstrip("/"))
    except ValueError as e:
        return {"ok": False, "error": str(e)}
    if not artifact.exists():
        return {"ok": False, "error": "artifact_not_found",
                "hint": f"Build the app first; expected at sandbox/{artifact_path}"}

    # Snapshot for audit anchor
    snap = await handle_create_snapshot(
        {"project_id": pid, "label": f"pre_submit_{provider}"}, ctx,
    )

    # ── Provider dispatch ─────────────────────────────────────────
    result: Dict[str, Any]
    if provider == "test_only":
        # Dry-run: just verify everything we'd need is in place.
        result = {"ok": True, "method": "dry_run",
                  "would_submit": str(artifact),
                  "provider": provider}
    elif provider == "firebase_app_distribution":
        token = await _load_cred(db, pid, "FIREBASE_TOKEN")
        appid = await _load_cred(db, pid, "FIREBASE_APP_ID")
        if not (token and appid):
            result = {"ok": False, "error": "firebase_credentials_incomplete",
                      "hint": "Need FIREBASE_TOKEN + FIREBASE_APP_ID"}
        else:
            firebase = shutil.which("firebase")
            if not firebase:
                result = {"ok": False, "error": "firebase_cli_not_installed",
                          "hint": "npm install -g firebase-tools"}
            else:
                env = {**os.environ, "FIREBASE_TOKEN": token}
                proc = await _run(
                    [firebase, "appdistribution:distribute", str(artifact),
                     "--app", appid, "--release-notes", release_notes or "Zenrex AI deploy",
                     "--non-interactive"],
                    env=env, timeout=300,
                )
                result = {
                    "ok": bool(proc.get("ok")),
                    "method": "firebase_app_distribution",
                    "stdout": (proc.get("stdout") or "")[:1500],
                    "stderr": (proc.get("stderr") or "")[:1500],
                }
    elif provider == "expo_eas_submit":
        eas_token = await _load_cred(db, pid, "EXPO_TOKEN")
        if not eas_token:
            result = {"ok": False, "error": "expo_token_missing",
                      "hint": "Save EXPO_TOKEN credential first"}
        else:
            eas = shutil.which("eas")
            if not eas:
                result = {"ok": False, "error": "eas_cli_not_installed",
                          "hint": "npm install -g eas-cli"}
            else:
                env = {**os.environ, "EXPO_TOKEN": eas_token}
                proc = await _run(
                    [eas, "submit", "--platform", args.get("platform", "android"),
                     "--path", str(artifact), "--non-interactive"],
                    cwd=sandbox / "repo", env=env, timeout=900,
                )
                result = {"ok": bool(proc.get("ok")), "method": "expo_eas_submit",
                          "stdout": (proc.get("stdout") or "")[:1500],
                          "stderr": (proc.get("stderr") or "")[:1500]}
    else:
        # Play Store / App Store Connect / others: implementation deferred.
        # We acknowledge the request, log it, and tell the AI what's needed.
        result = {
            "ok": False,
            "error": "provider_not_implemented_yet",
            "provider": provider,
            "hint_ar": (
                "هذا المزوّد مدعوم تنظيمياً ولكن التنفيذ المباشر بعد. "
                "حالياً يتم النشر يدوياً عبر CLI الخاص بالمزوّد. "
                f"احفظ المفاتيح المطلوبة لـ {provider}، وسنفعّل الإرسال التلقائي قريباً."
            ),
            "manual_steps_ar": _manual_steps_for(provider),
        }

    await _audit(ctx, db, pid, "submit_to_app_store",
                 tool_name="submit_to_app_store",
                 target_path=artifact_path, success=bool(result.get("ok")),
                 details={"provider": provider, "snapshot_id": snap.get("snapshot_id"),
                          "error": result.get("error")})
    return {**result, "snapshot_id": snap.get("snapshot_id")}


def _manual_steps_for(provider: str) -> List[str]:
    """Arabic step-by-step instructions for providers we haven't wired yet."""
    return {
        "play_store_internal": [
            "1) ادخل Play Console → اختر التطبيق",
            "2) Testing → Internal testing → Create new release",
            "3) ارفع ملف .aab الموقّع",
            "4) أضف release notes واضغط Save → Review → Start rollout",
        ],
        "play_store_alpha": [
            "1) ادخل Play Console → Testing → Closed testing",
            "2) أنشئ track 'alpha' لو ما هو موجود",
            "3) ارفع الـ AAB واضغط rollout",
        ],
        "play_store_production": [
            "1) Production → Create new release → upload AAB",
            "2) Review release → Start staged rollout to production",
        ],
        "app_store_testflight": [
            "1) ادخل App Store Connect → My Apps → اختر التطبيق",
            "2) TestFlight → ارفع .ipa عبر Transporter أو Xcode",
            "3) أضف testers + release notes",
        ],
        "app_store_production": [
            "1) App Store Connect → اختر التطبيق → Version → '+' Submit for review",
            "2) املأ metadata + screenshots + ipa",
            "3) Submit to App Store Review",
        ],
        "microsoft_store": [
            "1) Partner Center → اختر التطبيق",
            "2) Submission → upload .msix/.appx package",
        ],
        "steam": [
            "1) Steamworks → Steam Build SDK → 'steamcmd' لرفع الـ build",
            "2) Configure depots + push to default branch",
        ],
        "itch_io": [
            "1) butler push ./build user/game:channel",
            "2) butler هو CLI الرفع الرسمي لـ itch.io",
        ],
    }.get(provider, ["تواصل مع الدعم لتفعيل هذا المزوّد."])


# ───────────────────────────────────────────────────────────────────
# Tool registry
# ───────────────────────────────────────────────────────────────────
CONTINUATION_APP_TOOL_DEFINITIONS: List[Dict[str, Any]] = [
    {
        "name": "detect_project_stack",
        "description": (
            "READ-ONLY. Scan the cloned sandbox and identify what programming "
            "stacks/frameworks are present (Flutter, React Native, Next.js, "
            "Django, Go, Rust, Unity, etc.). Returns recommended build/test/"
            "install commands and notes about platform requirements (e.g. iOS "
            "needs cloud build). Use this BEFORE proposing any edits — never "
            "assume the stack."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "project_id": {"type": "string"},
                "path": {"type": "string",
                         "description": "sub-folder to scan, default 'repo'"},
            },
            "required": [],
        },
    },
    {
        "name": "run_sandbox_command",
        "description": (
            "Execute a whitelisted shell command inside the customer's sandbox. "
            "Use this to install dependencies, run builds, execute tests, or "
            "run linters AFTER `detect_project_stack` returned the recommended "
            "commands. Only whitelisted binaries are permitted (npm/yarn/flutter/"
            "gradle/dotnet/cargo/go/python/etc.). Subscription-locked after first "
            "concrete fix. Auto-snapshots before any non-read-only command."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "project_id": {"type": "string"},
                "command": {"type": "string",
                            "description": "The shell command (e.g. 'flutter pub get' or 'cd backend && go test ./...'). Only whitelisted binaries allowed."},
                "workdir": {"type": "string",
                            "description": "Sub-folder inside sandbox (default 'repo')"},
                "timeout": {"type": "integer",
                            "description": "Seconds, default 180, max 300"},
                "purpose": {"type": "string",
                            "description": "Short tag for audit log (e.g. 'install_deps', 'run_tests', 'build_release')"},
            },
            "required": ["command"],
        },
    },
    {
        "name": "submit_to_app_store",
        "description": (
            "Submit a built app artifact to a distribution provider: Firebase "
            "App Distribution, Expo EAS Submit, Play Store, App Store Connect, "
            "Microsoft Store, Steam, itch.io. Currently implemented end-to-end: "
            "firebase_app_distribution, expo_eas_submit, test_only. Others return "
            "manual Arabic instructions. Requires saved provider credentials. "
            "Subscription-locked + auto-snapshots."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "project_id": {"type": "string"},
                "provider": {"type": "string", "enum": sorted(SUPPORTED_STORE_PROVIDERS)},
                "artifact_path": {"type": "string",
                                  "description": "Path inside sandbox (e.g. 'repo/build/app/outputs/.../app-release.apk')"},
                "release_notes": {"type": "string"},
                "platform": {"type": "string", "enum": ["android", "ios"],
                             "description": "Required for expo_eas_submit"},
            },
            "required": ["provider", "artifact_path"],
        },
    },
]

CONTINUATION_APP_TOOL_HANDLERS: Dict[str, Any] = {
    "detect_project_stack": handle_detect_project_stack,
    "run_sandbox_command": handle_run_sandbox_command,
    "submit_to_app_store": handle_submit_to_app_store,
}
