"""
Sanity tests for the Hetzner provisioning module.

We exercise the deterministic parts (token validation error messages
and cloud-init template formatting). Live Hetzner API calls are NOT
made — that requires a real customer token at runtime.
"""
from __future__ import annotations

import os
import sys

import pytest

# Make the backend modules importable when pytest is invoked from /app
_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if os.path.join(_ROOT, "backend") not in sys.path:
    sys.path.insert(0, os.path.join(_ROOT, "backend"))


def test_cloud_init_template_includes_required_fields():
    from modules.freebuild.hetzner_provision import _CLOUD_INIT_TEMPLATE

    rendered = _CLOUD_INIT_TEMPLATE.format(
        hostname="my-site",
        project_id="abc-123",
        domain="example.com",
        kit_url="https://zenrex.ai/api/freebuild-chat/project/abc-123/kit-download/TOKEN",
    )
    # cloud-config header
    assert rendered.startswith("#cloud-config")
    # Docker install
    assert "get.docker.com" in rendered
    # Deploys with domain
    assert "example.com" in rendered
    # Has the kit URL
    assert "kit-download" in rendered
    # Hostname stamped
    assert "my-site" in rendered
    # Final status marker
    assert ".zenrex_status" in rendered


def test_validate_token_rejects_blank():
    from modules.freebuild.hetzner_provision import validate_token

    with pytest.raises(ValueError):
        validate_token("")  # empty token must fail loudly


def test_validate_token_friendly_arabic_error():
    """Bad/short tokens should produce an Arabic-friendly message."""
    from modules.freebuild.hetzner_provision import validate_token

    with pytest.raises(ValueError) as exc:
        validate_token("not-a-real-token-just-fake-string-1234567890")
    # Should be in Arabic or contain "Hetzner" string
    msg = str(exc.value)
    assert ("Hetzner" in msg) or ("التوكن" in msg) or ("غير صالح" in msg)
