"""
🛎️ Concierge Module — entry point.

Registers all sub-components: knowledge base, state machine, vault,
wizard, validators, and HTTP routes.

Usage in FastAPI app:
    from modules.freebuild.concierge import include_concierge_routes
    include_concierge_routes(app)
"""
from __future__ import annotations

from .credential_vault import (  # noqa: F401
    get_credential, has_credential, list_credentials, mask_for_display, store_credential,
)
from .knowledge import (  # noqa: F401
    detect_required_integrations, get_integration, list_integrations,
    render_setup_instructions_ar, render_setup_instructions_en,
)
from .routes import router as concierge_router
from .setup_wizard import (  # noqa: F401
    build_wizard_flow, card_checklist, card_cost_summary, card_intro,
    card_key_input, card_skip_alternative, card_success,
)
from .state_machine import (  # noqa: F401
    ConciergeState, add_required_integration, get_required_integrations,
    load_state, mark_integration_satisfied, save_state, transition,
)
from .validators import validate_by_key_name  # noqa: F401


def include_concierge_routes(app) -> None:
    """Mount /api/concierge/* on a FastAPI app."""
    app.include_router(concierge_router)
