"""Gap audit — what would a real engineer manager need that we DON'T have?

This pretends to be Claude during a typical "fix this Flutter app" job and
asks: "for each common engineering action, do we have a tool?"
"""
import sys
sys.path.insert(0, '/app')
sys.path.insert(0, '/app/backend')

from backend.modules.freebuild.cortex_tools import TOOL_DEFINITIONS

tool_names = {t['name'] for t in TOOL_DEFINITIONS}

# What a senior engineer typically does on a project
NEEDS = [
    ("git_clone", "Clone repo", {"clone_remote_repo"}),
    ("git_pull", "Pull latest changes from remote (after initial clone)", {"clone_remote_repo"}),  # accepted: re-clone
    ("stack_detect", "Identify framework", {"detect_project_stack"}),
    ("list_files", "Browse files", {"list_sandbox_files"}),
    ("read_file", "Read a specific file", {"read_sandbox_file"}),
    ("grep_search", "Search across codebase", {"run_sandbox_command"}),  # grep -r is whitelisted
    ("write_file", "Modify a file", {"propose_sandbox_change"}),
    ("delete_file", "Remove a file", {"delete_sandbox_file"}),
    ("create_file", "Create a NEW file", {"propose_sandbox_change"}),
    ("rename_move_file", "Rename or move a file", {"move_sandbox_file"}),
    ("apply_patch", "Apply a unified diff/patch", {"apply_patch"}),
    ("install_deps", "Install dependencies (npm/pip/cargo)", {"run_sandbox_command"}),
    ("build", "Build project (release artifact)", {"run_sandbox_command"}),
    ("run_tests", "Run test suite", {"run_sandbox_command"}),
    ("run_lint", "Run linter", {"run_sandbox_command"}),
    ("snapshot", "Save state for rollback", {"create_snapshot"}),
    ("restore_snapshot", "Rollback", {"restore_snapshot"}),
    ("list_snapshots", "Show available rollback points", {"list_snapshots"}),
    ("create_pr", "Open Pull Request", {"push_to_review_branch"}),
    ("deploy_live_ssh", "Push to live SSH server", {"deploy_to_live_vps"}),
    ("deploy_live_ftp", "Push to live FTP host", {"deploy_to_live_ftp"}),
    ("submit_store", "Submit to app store", {"submit_to_app_store"}),
    ("mark_first_update", "Trigger paywall after first ship", {"mark_first_update"}),
    ("read_audit", "Show audit log (for AI itself)", {"read_continuation_audit"}),
    ("get_project_status", "Check first_update_delivered / unlocked", {"get_continuation_status"}),
    ("read_logs", "Read backend/app logs (Firebase Crashlytics etc)", {"run_sandbox_command"}),  # via firebase CLI through run_sandbox_command
    ("inspect_secrets", "Verify which credentials are saved (NOT read values)", {"inspect_saved_credentials"}),
    ("validate_env", "Check env vars present in sandbox", {"run_sandbox_command"}),  # via env / printenv inside whitelist
]

print("\n=== Engineer Manager Gap Analysis ===\n")
has_count = 0
missing = []
for need_id, desc, required in NEEDS:
    covered = required & tool_names
    if covered:
        has_count += 1
        print(f"  ✓ {need_id:25s}  via: {', '.join(covered)}")
    else:
        missing.append((need_id, desc))
        print(f"  ✗ {need_id:25s}  MISSING — needs one of {required} but only have {required & tool_names}")

print(f"\nCoverage: {has_count}/{len(NEEDS)} = {has_count*100//len(NEEDS)}%")
print(f"Gaps to fill: {len(missing)}")
for need_id, desc in missing:
    print(f"  • {need_id}: {desc}")
