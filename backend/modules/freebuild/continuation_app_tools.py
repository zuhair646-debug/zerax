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
    "diff", "patch", "env", "printenv", "echo",
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


# Tools that need a verified toolchain present BEFORE we even try the command.
# Maps command-head → list of binaries that must exist + install hint.
TOOLCHAIN_REQUIREMENTS = {
    "flutter": [("flutter", "Install Flutter SDK: https://docs.flutter.dev/get-started/install/linux")],
    "dart":    [("dart",    "Install Dart SDK or use the bundled flutter dart")],
    "expo":    [("npx",     "Install Node.js + run: npm install -g expo-cli")],
    "eas":     [("eas",     "Install: npm install -g eas-cli")],
    "cap":     [("npx",     "Install: npm install -g @ionic/cli + @capacitor/cli")],
    "ionic":   [("ionic",   "Install: npm install -g @ionic/cli")],
    "cordova": [("cordova", "Install: npm install -g cordova")],
    "ns":      [("ns",      "Install: npm install -g @nativescript/cli")],
    "dotnet":  [("dotnet",  "Install .NET SDK: https://dotnet.microsoft.com/download")],
    "cargo":   [("cargo",   "Install Rust: https://rustup.rs")],
    "go":      [("go",      "Install Go: https://go.dev/dl")],
    "mvn":     [("mvn",     "Install Maven: apt install maven")],
    "gradle":  [("gradle",  "Install Gradle: apt install gradle")],
    "./gradlew": [],  # bundled in project — assume OK
    "composer": [("composer", "Install Composer: https://getcomposer.org")],
    "bundle":  [("bundle",  "Install Bundler: gem install bundler")],
    "ruby":    [("ruby",    "Install Ruby: apt install ruby")],
    "pod":     [("pod",     "iOS only — needs macOS + Cocoapods")],
    "swift":   [("swift",   "iOS/macOS only")],
    "fastlane":[("fastlane","Install: gem install fastlane")],
    "firebase":[("firebase","Install: npm install -g firebase-tools")],
}


def _preflight_toolchain(cmd: str) -> Optional[Dict[str, Any]]:
    """Return a structured error if the required toolchain isn't installed.
    Returns None if OK to proceed. This prevents the AI from running a
    command, waiting 3 min, and getting 'command not found' — which would
    make us look broken to the customer."""
    try:
        tokens = shlex.split(cmd)
    except Exception:
        return None
    if not tokens:
        return None
    head = tokens[0]
    if head == "cd" and "&&" in cmd:
        try:
            rest = cmd.split("&&", 1)[1].strip()
            head = shlex.split(rest)[0]
        except Exception:
            return None
    req = TOOLCHAIN_REQUIREMENTS.get(head)
    if not req:
        return None  # nothing to check
    missing = []
    for bin_name, hint in req:
        if not shutil.which(bin_name):
            missing.append({"binary": bin_name, "install_hint": hint})
    if missing:
        return {
            "ok": False,
            "error": "toolchain_missing",
            "missing": missing,
            "command_attempted": cmd,
            "message_ar": (
                f"⚠️ السيرفر ما عنده {missing[0]['binary']} مثبّت. "
                f"إما (أ) تثبيت محلي على السيرفر، أو (ب) استخدم خدمة بناء سحابية: "
                f"`submit_to_app_store(provider='expo_eas_submit')` أو Codemagic. "
                f"للتثبيت اليدوي: {missing[0]['install_hint']}"
            ),
            "hint_for_ai": (
                "Tell the customer this binary is not installed on the Zenrex build "
                "server and offer them: 1) ask the platform team to add it, OR 2) use "
                "a cloud build service (EAS / Codemagic) which already has it."
            ),
        }
    return None


# ───────────────────────────────────────────────────────────────────
# Tool 1 — detect_project_stack
# ───────────────────────────────────────────────────────────────────

# ── Project ID resolver ──────────────────────────────────────────────────
# The Anthropic AI sometimes passes literal placeholders like "current",
# "$project_id", "{{project_id}}", or just the empty string when it cannot
# distinguish runtime context from arguments. Treat any of these as "use
# the project bound to the current request context" so tools never fail
# with "project not found" just because the AI guessed at the field.
_PID_SENTINELS = {"", "current", "this", "self", "null", "none",
                  "$project_id", "{{project_id}}", "<project_id>"}

def _resolve_pid(args, ctx):
    raw = (args.get("project_id") or "").strip()
    if raw.lower() in _PID_SENTINELS:
        raw = ""
    return raw or (ctx and getattr(ctx, "project_id", None) or "")


async def handle_detect_project_stack(args: Dict[str, Any], ctx: Any = None) -> Dict[str, Any]:
    pid = _resolve_pid(args, ctx)
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
    pid = _resolve_pid(args, ctx)
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
    READ_ONLY = {"grep", "find", "ls", "cat", "head", "tail", "wc", "diff", "git", "env", "printenv", "echo"}
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

    # ─── Toolchain preflight: refuse to run if binary isn't installed.
    # Better to fail fast with a clear message than waste 3 minutes and
    # return "command not found".
    pre = _preflight_toolchain(cmd)
    if pre:
        await _audit(ctx, db, pid, "run_sandbox_command",
                     tool_name="run_sandbox_command",
                     target_path=workdir, success=False,
                     details={"command": cmd[:200], "reason": "toolchain_missing",
                              "missing": pre["missing"]})
        return pre

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
    pid = _resolve_pid(args, ctx)
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
    elif provider == "play_store_internal" or provider == "play_store_alpha" or provider == "play_store_beta" or provider == "play_store_production":
        # Map provider → fastlane track
        track_map = {
            "play_store_internal": "internal",
            "play_store_alpha": "alpha",
            "play_store_beta": "beta",
            "play_store_production": "production",
        }
        track = track_map[provider]
        service_json = await _load_cred(db, pid, "GOOGLE_SERVICE_ACCOUNT_JSON")
        package = await _load_cred(db, pid, "GOOGLE_PLAY_PACKAGE_NAME")
        if not (service_json and package):
            result = {"ok": False, "error": "play_store_credentials_incomplete",
                      "hint": "Need GOOGLE_SERVICE_ACCOUNT_JSON + GOOGLE_PLAY_PACKAGE_NAME"}
        else:
            fastlane = shutil.which("fastlane")
            if not fastlane:
                result = {"ok": False, "error": "fastlane_not_installed",
                          "hint": "Install: gem install fastlane"}
            else:
                # Write the service account JSON to a temp file
                import tempfile as _tmp
                key_file = _tmp.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
                try:
                    key_file.write(service_json)
                    key_file.flush()
                    key_file.close()
                    os.chmod(key_file.name, 0o600)
                    # Run fastlane supply
                    is_aab = str(artifact).endswith(".aab")
                    flag = "--aab" if is_aab else "--apk"
                    cmd = [
                        fastlane, "supply",
                        "--package_name", package,
                        "--track", track,
                        "--json_key", key_file.name,
                        flag, str(artifact),
                        "--skip_upload_metadata", "true",
                        "--skip_upload_changelogs", "true",
                        "--skip_upload_images", "true",
                        "--skip_upload_screenshots", "true",
                    ]
                    if release_notes:
                        # Write release notes file for fastlane
                        notes_dir = sandbox / ".fastlane_metadata" / "android" / "en-US" / "changelogs"
                        notes_dir.mkdir(parents=True, exist_ok=True)
                        # Need versionCode of the APK — fastlane figures this out
                        cmd.extend(["--metadata_path", str(sandbox / ".fastlane_metadata" / "android")])
                    proc = await _run(cmd, cwd=sandbox / "repo", timeout=900)
                    result = {
                        "ok": bool(proc.get("ok")),
                        "method": "fastlane_supply",
                        "track": track, "package": package,
                        "stdout": (proc.get("stdout") or "")[:1500],
                        "stderr": (proc.get("stderr") or "")[:1500],
                    }
                finally:
                    try:
                        os.unlink(key_file.name)
                    except Exception:
                        pass
    elif provider == "app_store_testflight" or provider == "app_store_production":
        api_key = await _load_cred(db, pid, "APP_STORE_CONNECT_API_KEY")
        key_id = await _load_cred(db, pid, "APP_STORE_CONNECT_KEY_ID")
        issuer = await _load_cred(db, pid, "APP_STORE_CONNECT_ISSUER_ID")
        if not (api_key and key_id and issuer):
            result = {"ok": False, "error": "app_store_credentials_incomplete",
                      "hint": "Need APP_STORE_CONNECT_API_KEY + KEY_ID + ISSUER_ID"}
        else:
            fastlane = shutil.which("fastlane")
            if not fastlane:
                result = {"ok": False, "error": "fastlane_not_installed",
                          "hint_ar": "App Store يحتاج macOS — استخدم Codemagic/EAS بدلاً"}
            else:
                import tempfile as _tmp
                key_file = _tmp.NamedTemporaryFile(mode="w", suffix=".p8", delete=False)
                try:
                    key_file.write(api_key)
                    key_file.flush()
                    key_file.close()
                    os.chmod(key_file.name, 0o600)
                    lane = "pilot" if provider == "app_store_testflight" else "deliver"
                    cmd = [
                        fastlane, lane, "upload",
                        "--ipa", str(artifact),
                        "--api_key_path", key_file.name,
                        "--key_id", key_id,
                        "--issuer_id", issuer,
                        "--skip_waiting_for_build_processing", "true",
                    ]
                    if release_notes and provider == "app_store_testflight":
                        cmd.extend(["--changelog", release_notes])
                    proc = await _run(cmd, cwd=sandbox / "repo", timeout=1800)
                    result = {
                        "ok": bool(proc.get("ok")),
                        "method": f"fastlane_{lane}",
                        "stdout": (proc.get("stdout") or "")[:1500],
                        "stderr": (proc.get("stderr") or "")[:1500],
                    }
                finally:
                    try:
                        os.unlink(key_file.name)
                    except Exception:
                        pass
    else:
        # Microsoft Store / Steam / itch.io / Huawei / Amazon — return manual steps
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
# Gap-closing tools — file ops, project status, secret inspection
# ───────────────────────────────────────────────────────────────────
async def handle_delete_sandbox_file(args: Dict[str, Any], ctx: Any = None) -> Dict[str, Any]:
    """Delete a file in the sandbox. Snapshots before; paywall-gated."""
    pid = _resolve_pid(args, ctx)
    rel = (args.get("path") or "").strip()
    if not pid or not rel:
        return {"ok": False, "error": "project_id and path required"}
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
        p = _safe_path(sandbox, rel)
    except ValueError as e:
        return {"ok": False, "error": str(e)}
    if not p.exists():
        return {"ok": False, "error": "file_not_found"}
    await handle_create_snapshot({"project_id": pid, "label": "pre_delete"}, ctx)
    was_dir = p.is_dir()
    if was_dir:
        shutil.rmtree(p)
    else:
        p.unlink()
    await _audit(ctx, db, pid, "delete_sandbox_file",
                 tool_name="delete_sandbox_file", target_path=rel,
                 success=True, details={"was_dir": was_dir})
    return {"ok": True, "deleted": rel, "was_dir": was_dir, "at": _now_iso()}


async def handle_move_sandbox_file(args: Dict[str, Any], ctx: Any = None) -> Dict[str, Any]:
    """Rename or move a file/folder inside the sandbox. Snapshots first."""
    pid = _resolve_pid(args, ctx)
    src = (args.get("source") or "").strip()
    dst = (args.get("destination") or "").strip()
    if not pid or not src or not dst:
        return {"ok": False, "error": "project_id, source, destination required"}
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
        sp = _safe_path(sandbox, src)
        dp = _safe_path(sandbox, dst)
    except ValueError as e:
        return {"ok": False, "error": str(e)}
    if not sp.exists():
        return {"ok": False, "error": "source_not_found"}
    if dp.exists():
        return {"ok": False, "error": "destination_exists"}
    await handle_create_snapshot({"project_id": pid, "label": "pre_move"}, ctx)
    dp.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(sp), str(dp))
    await _audit(ctx, db, pid, "move_sandbox_file",
                 tool_name="move_sandbox_file", target_path=f"{src} → {dst}",
                 success=True, details={"source": src, "destination": dst})
    return {"ok": True, "moved": f"{src} → {dst}", "at": _now_iso()}


async def handle_apply_patch(args: Dict[str, Any], ctx: Any = None) -> Dict[str, Any]:
    """Apply a unified diff to a file in the sandbox. Lighter than full-file rewrite.
    The patch must be in the standard `--- a/path\\n+++ b/path\\n@@…` format."""
    import tempfile as _tmp
    pid = _resolve_pid(args, ctx)
    rel = (args.get("path") or "").strip()
    patch_text = args.get("patch_text") or ""
    if not pid or not rel or not patch_text:
        return {"ok": False, "error": "project_id, path, patch_text required"}
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
        p = _safe_path(sandbox, rel)
    except ValueError as e:
        return {"ok": False, "error": str(e)}
    if not p.exists() or not p.is_file():
        return {"ok": False, "error": "target_file_not_found"}
    await handle_create_snapshot({"project_id": pid, "label": "pre_patch"}, ctx)
    # Write patch to temp file then `patch -p0 < tmp` from sandbox root
    with _tmp.NamedTemporaryFile("w", suffix=".patch", delete=False) as tf:
        tf.write(patch_text)
        tf.flush()
        tmp_name = tf.name
    try:
        res = await _run(["bash", "-lc", f"patch -p1 < {shlex.quote(tmp_name)}"],
                         cwd=sandbox, timeout=30)
    finally:
        try:
            os.unlink(tmp_name)
        except Exception:
            pass
    success = bool(res.get("ok"))
    await _audit(ctx, db, pid, "apply_patch",
                 tool_name="apply_patch", target_path=rel,
                 success=success,
                 details={"patch_bytes": len(patch_text), "stderr": (res.get("stderr") or "")[:200]})
    return {"ok": success, "stdout": (res.get("stdout") or "")[:500],
            "stderr": (res.get("stderr") or "")[:500], "at": _now_iso()}


async def handle_get_continuation_status(args: Dict[str, Any], ctx: Any = None) -> Dict[str, Any]:
    """Read project's paywall + setup state. AI calls this BEFORE attempting
    writes to know whether it's pre-mark, locked, or unlocked."""
    pid = _resolve_pid(args, ctx)
    if not pid:
        return {"ok": False, "error": "project_id required"}
    db = getattr(ctx, "db", None) if ctx else None
    if db is None:
        from server import db as _db  # type: ignore
        db = _db
    proj = await db.freebuild_projects.find_one(
        {"id": pid},
        {"_id": 0, "mode": 1, "project_kind": 1, "app_kind": 1,
         "first_update_delivered": 1, "continuation_unlocked": 1,
         "continuation_sandbox": 1, "continuation_credentials": 1,
         "continuation_deploy_target": 1, "continuation_subscription_monthly_usd": 1},
    )
    if not proj:
        return {"ok": False, "error": "project_not_found"}
    if proj.get("mode") != "continuation":
        return {"ok": False, "error": "not_continuation_mode"}
    saved_creds = list((proj.get("continuation_credentials") or {}).keys())
    return {
        "ok": True,
        "project_kind": proj.get("project_kind") or "site",
        "app_kind": proj.get("app_kind"),
        "first_update_delivered": bool(proj.get("first_update_delivered")),
        "continuation_unlocked": bool(proj.get("continuation_unlocked")),
        "paywall_active": bool(proj.get("first_update_delivered")) and not bool(proj.get("continuation_unlocked")),
        "sandbox_ready": bool(proj.get("continuation_sandbox")),
        "sandbox_meta": proj.get("continuation_sandbox") or None,
        "saved_credential_keys": saved_creds,
        "deploy_target_configured": bool(proj.get("continuation_deploy_target")),
        "monthly_price_usd": float(proj.get("continuation_subscription_monthly_usd") or 150.0),
    }


async def handle_inspect_saved_credentials(args: Dict[str, Any], ctx: Any = None) -> Dict[str, Any]:
    """Return ONLY THE NAMES of saved credentials — never the values. So
    the AI can decide what to ask the customer for without leaking secrets."""
    pid = _resolve_pid(args, ctx)
    if not pid:
        return {"ok": False, "error": "project_id required"}
    db = getattr(ctx, "db", None) if ctx else None
    if db is None:
        from server import db as _db  # type: ignore
        db = _db
    err = await _guard_continuation_mode(db, pid)
    if err:
        return {"ok": False, "error": err}
    proj = await db.freebuild_projects.find_one(
        {"id": pid}, {"_id": 0, "continuation_credentials": 1},
    )
    creds = (proj or {}).get("continuation_credentials") or {}
    keys = sorted(creds.keys())
    return {
        "ok": True,
        "saved_keys": keys,
        "count": len(keys),
        "has_git": any(k.endswith("_TOKEN") and "GIT" in k or k == "GITHUB_TOKEN" for k in keys),
        "has_ssh": all(k in keys for k in ("SSH_HOST", "SSH_USERNAME", "SSH_PRIVATE_KEY")),
        "has_ftp": all(k in keys for k in ("FTP_HOST", "FTP_USERNAME", "FTP_PASSWORD")),
        "has_firebase": "FIREBASE_TOKEN" in keys and "FIREBASE_APP_ID" in keys,
        "has_eas": "EXPO_TOKEN" in keys,
        "has_play_store": "GOOGLE_SERVICE_ACCOUNT_JSON" in keys,
        "has_app_store": "APP_STORE_CONNECT_API_KEY" in keys,
        "has_android_signing": "ANDROID_KEYSTORE_BASE64" in keys,
        "has_ios_signing": "IOS_CERTIFICATE_P12_BASE64" in keys,
    }


async def handle_read_continuation_audit(args: Dict[str, Any], ctx: Any = None) -> Dict[str, Any]:
    """Let the AI read its own audit history so it doesn't repeat
    destructive actions or contradict prior commitments."""
    pid = _resolve_pid(args, ctx)
    limit = int(args.get("limit") or 30)
    if not pid:
        return {"ok": False, "error": "project_id required"}
    db = getattr(ctx, "db", None) if ctx else None
    if db is None:
        from server import db as _db  # type: ignore
        db = _db
    err = await _guard_continuation_mode(db, pid)
    if err:
        return {"ok": False, "error": err}
    try:
        from .continuation_audit import fetch_audit
        logs = await fetch_audit(db, pid, limit=min(max(limit, 1), 100))
    except Exception:
        logs = []
    # Strip signatures for brevity, keep the action timeline
    trimmed = [
        {"ts": entry.get("ts"), "action": entry.get("action"),
         "target_path": entry.get("target_path"), "success": entry.get("success"),
         "summary": (entry.get("details") or {}).get("summary") or (entry.get("details") or {}).get("command", "")[:80]}
        for entry in logs
    ]
    return {"ok": True, "count": len(trimmed), "logs": trimmed}


# ───────────────────────────────────────────────────────────────────
# Domain knowledge — lets the AI consult industry-specific playbooks
# (banking, lending, e-commerce, healthcare, education, real estate,
# salons, construction, government, stocks, food delivery, etc.)
# ───────────────────────────────────────────────────────────────────
_DOMAIN_KB_CACHE: Optional[Dict[str, Any]] = None


def _load_domain_kb() -> Dict[str, Any]:
    global _DOMAIN_KB_CACHE
    if _DOMAIN_KB_CACHE is not None:
        return _DOMAIN_KB_CACHE
    from pathlib import Path as _P
    import json as _json
    kb_path = _P(__file__).parent.parent.parent / "data" / "continuation_domain_knowledge.json"
    try:
        _DOMAIN_KB_CACHE = _json.loads(kb_path.read_text("utf-8"))
    except Exception as e:
        logger.exception(f"[continuation] failed to load domain KB: {e}")
        _DOMAIN_KB_CACHE = {"domains": {}}
    return _DOMAIN_KB_CACHE


def _guess_domain(text: str) -> List[str]:
    """Cheap keyword-based domain guess. Returns up to 3 candidate domain ids
    ordered by match strength. Used when the customer didn't tell us
    explicitly what their app is about."""
    if not text:
        return []
    t = text.lower()
    keywords = {
        "banking": ["بنك", "حساب", "كشف", "حوالة", "بطاقة", "ساما", "sama", "iban", "bank"],
        "lending": ["تمويل", "قرض", "قسط", "تقسيط", "bnpl", "تابي", "تمارا", "simah", "سمة", "مرابحة"],
        "stocks_trading": ["تداول", "أسهم", "محفظة", "اكتتاب", "بورصة", "tadawul", "stock", "trade"],
        "ecommerce": ["متجر", "تسوق", "سلة", "checkout", "shop", "salla", "zid", "نون", "أمازون"],
        "food_delivery": ["توصيل طعام", "مطعم", "هنقر", "جاهز", "delivery", "restaurant", "كشتات"],
        "healthcare": ["طبيب", "موعد", "وصفة", "صحة", "telemedicine", "صيدلية", "تأمين طبي", "ehr"],
        "education": ["دورة", "تعليم", "تدريب", "course", "lms", "اختبار", "شهادة"],
        "real_estate": ["عقار", "بيت", "شقة", "إيجار", "ejar", "real estate", "property"],
        "beauty_salons": ["مشغل", "صالون", "تجميل", "salon", "beauty", "spa"],
        "construction": ["بناء", "مقاولة", "موقع إنشائي", "construction", "bim", "مشروع إنشائي"],
        "government_services": ["نفاذ", "أبشر", "حكومي", "nafath", "absher", "yakeen", "وزارة"],
        "logistics_shipping": ["شحن", "توصيل طرد", "smsa", "aramex", "naqel", "logistics"],
        "automotive": ["سيارة", "صيانة سيارات", "قطع غيار", "automotive", "vehicle"],
        "social_networking": ["تواصل اجتماعي", "feed", "stories", "social", "chat"],
        "fitness_wellness": ["لياقة", "تمارين", "fitness", "workout", "تغذية"],
        "media_entertainment": ["بث", "مسلسل", "أفلام", "streaming", "vod", "music"],
        "travel_tourism": ["سفر", "حجز فندق", "طيران", "travel", "hotel", "flight"],
    }
    scores = {}
    for domain, kws in keywords.items():
        score = sum(1 for kw in kws if kw in t)
        if score:
            scores[domain] = score
    return [d for d, _ in sorted(scores.items(), key=lambda kv: -kv[1])[:3]]


async def handle_lookup_domain_knowledge(args: Dict[str, Any], ctx: Any = None) -> Dict[str, Any]:
    """READ-ONLY. Look up the domain-specific playbook the AI needs to handle
    a given industry vertical. The AI calls this RIGHT AFTER `detect_project_stack`
    so it knows what sections the app should have, what compliance applies,
    what integrations are standard, and what pitfalls to avoid.

    Usage modes:
      • Explicit:   lookup_domain_knowledge(domain="banking")
      • Auto-guess: lookup_domain_knowledge(description="تطبيق توصيل طعام في الرياض")
      • List all:   lookup_domain_knowledge(list_domains=True)
    """
    kb = _load_domain_kb()
    domains = kb.get("domains", {})

    if args.get("list_domains"):
        return {
            "ok": True,
            "list": [{"id": k, "ar": v.get("label_ar"), "en": v.get("label_en"),
                       "examples": v.get("examples_ar", [])[:3]}
                     for k, v in domains.items()],
            "count": len(domains),
        }

    domain_id = (args.get("domain") or "").strip().lower()
    if not domain_id:
        # Try auto-guess from description
        guesses = _guess_domain(args.get("description") or "")
        if not guesses:
            return {
                "ok": False,
                "error": "domain_required",
                "hint": "Pass 'domain' or 'description' to auto-guess. Or list_domains=True to see options.",
                "available_domain_ids": sorted(domains.keys()),
            }
        domain_id = guesses[0]
        suggested = guesses
    else:
        suggested = [domain_id]

    info = domains.get(domain_id)
    if not info:
        return {
            "ok": False,
            "error": "unknown_domain",
            "available": sorted(domains.keys()),
            "hint": "Use list_domains=True to see all 17 domains.",
        }

    return {
        "ok": True,
        "domain_id": domain_id,
        "label_ar": info.get("label_ar"),
        "label_en": info.get("label_en"),
        "examples_ar": info.get("examples_ar", []),
        "typical_sections": info.get("typical_sections", []),
        "compliance_required": info.get("compliance_required", []),
        "common_integrations": info.get("common_integrations", []),
        "security_critical": info.get("security_critical", []),
        "common_pitfalls": info.get("common_pitfalls", []),
        "kpis": info.get("kpis", []),
        "recommended_stacks": info.get("recommended_stacks", []),
        "anti_patterns": info.get("anti_patterns", []),
        "auto_guess_candidates": suggested if len(suggested) > 1 else None,
        "usage_hint_ar": (
            f"استخدم هذه القائمة كـ checklist عند تحليل التطبيق. "
            f"للسوق السعودي تأكّد من تطبيق: {', '.join((info.get('compliance_required') or [])[:2]) or 'لا متطلبات خاصة'}"
        ),
    }


# ───────────────────────────────────────────────────────────────────
# Integration playbook tool — gives the AI the EXACT code, setup steps,
# security gotchas, and common bugs for each critical Saudi integration:
# Nafath, Mada, Tabby, SIMAH, ZATCA, STC Pay, WhatsApp Business.
# ───────────────────────────────────────────────────────────────────
_INTEGRATION_KB_CACHE: Optional[Dict[str, Any]] = None


def _load_integration_kb() -> Dict[str, Any]:
    global _INTEGRATION_KB_CACHE
    if _INTEGRATION_KB_CACHE is not None:
        return _INTEGRATION_KB_CACHE
    from pathlib import Path as _P
    import json as _json
    kb_path = _P(__file__).parent.parent.parent / "data" / "continuation_integration_playbooks.json"
    try:
        _INTEGRATION_KB_CACHE = _json.loads(kb_path.read_text("utf-8"))
    except Exception as e:
        logger.exception(f"[continuation] failed to load integration KB: {e}")
        _INTEGRATION_KB_CACHE = {"playbooks": {}}
    return _INTEGRATION_KB_CACHE


async def handle_get_integration_playbook(args: Dict[str, Any], ctx: Any = None) -> Dict[str, Any]:
    """READ-ONLY. Retrieve a complete integration playbook for a Saudi-market
    integration. Returns: where to get credentials, setup steps in Arabic,
    code templates for Flutter/RN/Python, security gotchas, common bugs.

    Use this AFTER `lookup_domain_knowledge` told you a domain needs (e.g.)
    SIMAH integration but BEFORE you write any code. The playbook prevents
    bugs that would cost the customer their license or regulatory standing.

    Usage:
      • Single:  get_integration_playbook(integration='nafath')
      • Multi:   get_integration_playbook(domain='banking') → returns all 4-5 integrations the AI will likely need
      • List:    get_integration_playbook(list_all=True)
    """
    kb = _load_integration_kb()
    playbooks = kb.get("playbooks", {})

    if args.get("list_all"):
        return {
            "ok": True,
            "list": [
                {"id": k, "name_ar": v.get("name_ar"), "name_en": v.get("name_en"),
                 "category": v.get("category"), "used_in": v.get("domains_using", [])}
                for k, v in playbooks.items()
            ],
            "count": len(playbooks),
        }

    # Multi-mode: return all playbooks relevant to a domain
    domain = (args.get("domain") or "").strip().lower()
    if domain:
        relevant = {k: v for k, v in playbooks.items()
                    if domain in v.get("domains_using", [])}
        if not relevant:
            return {"ok": True, "domain": domain, "playbooks": [], "count": 0,
                    "hint": f"No Saudi integration playbooks tagged for domain '{domain}' yet."}
        return {
            "ok": True,
            "domain": domain,
            "playbooks": [{"id": k, **v} for k, v in relevant.items()],
            "count": len(relevant),
        }

    integration_id = (args.get("integration") or "").strip().lower()
    if not integration_id:
        return {
            "ok": False,
            "error": "integration_required",
            "hint": "Pass integration='nafath'/'mada_payment'/etc, OR domain='banking', OR list_all=True",
            "available": sorted(playbooks.keys()),
        }
    pb = playbooks.get(integration_id)
    if not pb:
        return {"ok": False, "error": "unknown_integration",
                "available": sorted(playbooks.keys())}
    return {"ok": True, "integration_id": integration_id, **pb}


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
    {
        "name": "delete_sandbox_file",
        "description": (
            "Delete a file or folder in the sandbox. Auto-snapshots before "
            "deleting so it's recoverable. Subscription-locked. Use carefully — "
            "for refactors that need to remove files (e.g. removing deprecated components)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "project_id": {"type": "string"},
                "path": {"type": "string", "description": "relative path inside sandbox"},
            },
            "required": ["path"],
        },
    },
    {
        "name": "move_sandbox_file",
        "description": (
            "Rename or move a file/folder inside the sandbox. Auto-snapshots first. "
            "Subscription-locked. Use for refactors (e.g. moving files into a "
            "feature folder, renaming components)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "project_id": {"type": "string"},
                "source": {"type": "string"},
                "destination": {"type": "string"},
            },
            "required": ["source", "destination"],
        },
    },
    {
        "name": "apply_patch",
        "description": (
            "Apply a unified diff (`patch -p1` style) to a file in the sandbox. "
            "Lighter than full-file rewrite via propose_sandbox_change — use this "
            "when changes are small and you want to preserve unchanged context "
            "without sending the whole file. Auto-snapshots first. Subscription-locked."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "project_id": {"type": "string"},
                "path": {"type": "string"},
                "patch_text": {"type": "string",
                               "description": "Standard unified diff with --- a/path / +++ b/path / @@ hunks"},
            },
            "required": ["path", "patch_text"],
        },
    },
    {
        "name": "get_continuation_status",
        "description": (
            "READ-ONLY. Return the project's paywall + setup state: whether "
            "first_update_delivered, whether continuation_unlocked, whether "
            "sandbox is ready, which credentials are saved, monthly price, "
            "project_kind (site/app). Call this BEFORE attempting any write "
            "to avoid PAYWALL_LOCKED surprises."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"project_id": {"type": "string"}},
            "required": [],
        },
    },
    {
        "name": "inspect_saved_credentials",
        "description": (
            "READ-ONLY (names-only — never returns secret values). Returns the "
            "list of credential keys the customer has already provided + helpful "
            "boolean flags (has_ssh, has_ftp, has_firebase, has_eas, "
            "has_play_store, has_app_store, has_android_signing, has_ios_signing). "
            "Use this to decide what to ASK the customer for before trying "
            "deployment/store-submit tools."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"project_id": {"type": "string"}},
            "required": [],
        },
    },
    {
        "name": "read_continuation_audit",
        "description": (
            "READ-ONLY. Return the project's tamper-evident audit log entries "
            "(action, target_path, success, timestamp). Use this to recall what "
            "you've done in previous turns so you don't repeat destructive "
            "actions or contradict prior commitments to the customer."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "project_id": {"type": "string"},
                "limit": {"type": "integer", "description": "default 30, max 100"},
            },
            "required": [],
        },
    },
    {
        "name": "lookup_domain_knowledge",
        "description": (
            "READ-ONLY. Retrieve the domain-specific playbook for an industry "
            "vertical (banking, lending, e-commerce, healthcare, education, "
            "real_estate, beauty_salons, construction, government_services, "
            "logistics_shipping, automotive, social_networking, fitness_wellness, "
            "media_entertainment, travel_tourism, food_delivery, stocks_trading). "
            "Returns: typical sections, Saudi/GCC compliance requirements, common "
            "integrations (Nafath, SADAD, Mada, Tabby, etc.), security critical "
            "items, common pitfalls, KPIs, recommended tech stacks, anti-patterns. "
            "Call this RIGHT AFTER detect_project_stack so you analyze the app "
            "with the right domain-expert lens. Pass `domain` explicitly OR "
            "`description` for auto-guess. Pass `list_domains=True` to see all 17."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "domain": {"type": "string", "description": "Domain id, e.g. 'banking', 'food_delivery'"},
                "description": {"type": "string", "description": "App description; will auto-guess domain"},
                "list_domains": {"type": "boolean", "description": "Return list of all available domains"},
            },
            "required": [],
        },
    },
    {
        "name": "get_saudi_integration_playbook",
        "description": (
            "READ-ONLY. Retrieve a complete integration playbook for a Saudi/GCC "
            "market integration: Nafath (national SSO), Mada payment, Tabby BNPL, "
            "SIMAH credit bureau, ZATCA e-invoicing Phase 2, STC Pay, WhatsApp "
            "Business Cloud API. Each playbook includes: where to get credentials, "
            "Arabic setup steps, ready-to-paste code templates (Flutter/RN/Python), "
            "security gotchas, common bugs to avoid. Call this BEFORE writing any "
            "integration code — copying from the playbook prevents regulatory bugs "
            "(SAMA/CMA/ZATCA penalties) and lost customer trust. Usage: "
            "integration='nafath' for one, domain='banking' for all relevant, "
            "list_all=True to see catalog."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "integration": {"type": "string",
                                "description": "Integration id (e.g. 'nafath', 'mada_payment', 'zatca_einvoice')"},
                "domain": {"type": "string",
                           "description": "Get all playbooks relevant to a domain (e.g. 'banking')"},
                "list_all": {"type": "boolean"},
            },
            "required": [],
        },
    },
]

CONTINUATION_APP_TOOL_HANDLERS: Dict[str, Any] = {
    "detect_project_stack": handle_detect_project_stack,
    "run_sandbox_command": handle_run_sandbox_command,
    "submit_to_app_store": handle_submit_to_app_store,
    "delete_sandbox_file": handle_delete_sandbox_file,
    "move_sandbox_file": handle_move_sandbox_file,
    "apply_patch": handle_apply_patch,
    "get_continuation_status": handle_get_continuation_status,
    "inspect_saved_credentials": handle_inspect_saved_credentials,
    "read_continuation_audit": handle_read_continuation_audit,
    "lookup_domain_knowledge": handle_lookup_domain_knowledge,
    "get_saudi_integration_playbook": handle_get_integration_playbook,
}
