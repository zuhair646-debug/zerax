"""Power Tools — exported helpers."""
from .runtime import (
    validate_js_handlers,
    check_navigation_graph,
    fetch_unsplash_image,
    verify_my_work,
    auto_generate_scenarios,
    quick_browser_check,
)
from .advanced import (
    capture_visual_snapshot,
    compare_visuals,
    run_js_in_sandbox,
    run_safe_bash,
)
from .unrestricted import (
    run_bash_unrestricted,
    run_python_in_sandbox,
    read_any_file,
    write_any_file,
    edit_file,
    web_search,
    get_integration_playbook,
    deploy_to_production,
    call_self_test_agent,
    UNRESTRICTED_TOOLS,
)
from .parity import (
    analyze_uploaded_file,
    integration_playbook_live,
    recursive_test_agent,
    crawl_url_deep,
    remember,
    recall,
    PARITY_TOOLS,
)
from .senior_parity import (
    troubleshoot_agent,
    batch_refactor,
    iterative_test_and_fix,
    design_agent_full_stack,
    SENIOR_PARITY_TOOLS,
)

__all__ = [
    # runtime
    "validate_js_handlers", "check_navigation_graph",
    "fetch_unsplash_image", "verify_my_work",
    "auto_generate_scenarios", "quick_browser_check",
    # advanced
    "capture_visual_snapshot", "compare_visuals",
    "run_js_in_sandbox", "run_safe_bash",
    # unrestricted (full agent parity)
    "run_bash_unrestricted", "run_python_in_sandbox",
    "read_any_file", "write_any_file", "edit_file",
    "web_search", "get_integration_playbook",
    "deploy_to_production", "call_self_test_agent",
    "UNRESTRICTED_TOOLS",
    # parity (final 5% closing the gap to 100%)
    "analyze_uploaded_file", "integration_playbook_live",
    "recursive_test_agent", "crawl_url_deep",
    "remember", "recall", "PARITY_TOOLS",
    # senior_parity (the last 15% — sub-agent equivalents)
    "troubleshoot_agent", "batch_refactor",
    "iterative_test_and_fix", "design_agent_full_stack",
    "SENIOR_PARITY_TOOLS",
]
