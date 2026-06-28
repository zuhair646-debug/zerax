"""Tests for lookup_domain_knowledge — verifies the AI can consult
industry-specific playbooks for any vertical (banking, e-commerce, etc.)
"""
import sys
import pytest

sys.path.insert(0, "/app")
sys.path.insert(0, "/app/backend")


@pytest.mark.asyncio
async def test_lookup_banking_returns_sama_compliance():
    from backend.modules.freebuild.continuation_app_tools import handle_lookup_domain_knowledge
    res = await handle_lookup_domain_knowledge({"domain": "banking"})
    assert res["ok"] is True
    assert res["label_ar"] == "البنوك والخدمات المصرفية"
    assert any("SAMA" in c for c in res["compliance_required"])
    assert any("Nafath" in i for i in res["common_integrations"])
    assert any("biometric" in s.lower() or "encryption" in s.lower() for s in res["security_critical"])
    assert "Native iOS (Swift)" in res["recommended_stacks"]


@pytest.mark.asyncio
async def test_lookup_auto_guess_food_delivery():
    """Auto-guess from Arabic description."""
    from backend.modules.freebuild.continuation_app_tools import handle_lookup_domain_knowledge
    res = await handle_lookup_domain_knowledge({
        "description": "تطبيق توصيل طعام من المطاعم في الرياض، فيه سائق وعميل",
    })
    assert res["ok"] is True
    assert res["domain_id"] == "food_delivery"
    assert "ETA" in str(res["typical_sections"]) or "tracking" in str(res["typical_sections"]).lower()


@pytest.mark.asyncio
async def test_lookup_auto_guess_lending():
    from backend.modules.freebuild.continuation_app_tools import handle_lookup_domain_knowledge
    res = await handle_lookup_domain_knowledge({
        "description": "تطبيق BNPL تقسيط مثل تابي مع تكامل سمة",
    })
    assert res["ok"] is True
    assert res["domain_id"] == "lending"
    assert any("SIMAH" in c or "سمة" in c for c in res["common_integrations"])


@pytest.mark.asyncio
async def test_lookup_auto_guess_ecommerce():
    from backend.modules.freebuild.continuation_app_tools import handle_lookup_domain_knowledge
    res = await handle_lookup_domain_knowledge({
        "description": "متجر إلكتروني على سلة فيه سلة و checkout ودفع",
    })
    assert res["ok"] is True
    assert res["domain_id"] == "ecommerce"
    assert any("ZATCA" in c for c in res["compliance_required"])


@pytest.mark.asyncio
async def test_lookup_lists_all_domains():
    from backend.modules.freebuild.continuation_app_tools import handle_lookup_domain_knowledge
    res = await handle_lookup_domain_knowledge({"list_domains": True})
    assert res["ok"] is True
    assert res["count"] >= 17
    ids = {d["id"] for d in res["list"]}
    # Critical Saudi domains MUST be present
    critical = {"banking", "lending", "stocks_trading", "ecommerce", "food_delivery",
                "healthcare", "education", "real_estate", "beauty_salons", "construction",
                "government_services", "logistics_shipping"}
    missing = critical - ids
    assert not missing, f"missing domains: {missing}"


@pytest.mark.asyncio
async def test_lookup_unknown_domain_returns_error_with_options():
    from backend.modules.freebuild.continuation_app_tools import handle_lookup_domain_knowledge
    res = await handle_lookup_domain_knowledge({"domain": "spaceship_repair"})
    assert res["ok"] is False
    assert res["error"] == "unknown_domain"
    assert "available" in res
    assert "banking" in res["available"]


@pytest.mark.asyncio
async def test_lookup_no_args_returns_error_with_hint():
    from backend.modules.freebuild.continuation_app_tools import handle_lookup_domain_knowledge
    res = await handle_lookup_domain_knowledge({})
    assert res["ok"] is False
    assert "available_domain_ids" in res


@pytest.mark.asyncio
async def test_lookup_returns_kpis_for_each_domain():
    """Every domain should provide concrete KPIs the AI can mention."""
    from backend.modules.freebuild.continuation_app_tools import handle_lookup_domain_knowledge, _load_domain_kb
    kb = _load_domain_kb()
    for domain_id in kb["domains"].keys():
        res = await handle_lookup_domain_knowledge({"domain": domain_id})
        assert res["ok"]
        kpis = res.get("kpis") or []
        assert len(kpis) >= 2, f"{domain_id} has too few KPIs: {kpis}"


@pytest.mark.asyncio
async def test_lookup_returns_sections_for_each_domain():
    """Every domain has typical sections so AI knows what to look for."""
    from backend.modules.freebuild.continuation_app_tools import handle_lookup_domain_knowledge, _load_domain_kb
    kb = _load_domain_kb()
    for domain_id in kb["domains"].keys():
        res = await handle_lookup_domain_knowledge({"domain": domain_id})
        sections = res.get("typical_sections") or []
        assert len(sections) >= 5, f"{domain_id} has too few sections: {sections}"


@pytest.mark.asyncio
async def test_saudi_centric_integrations():
    """Saudi-specific integrations (Nafath, SADAD, Mada, ZATCA) appear in relevant domains."""
    from backend.modules.freebuild.continuation_app_tools import handle_lookup_domain_knowledge

    # Banking must have Nafath, SADAD, Mada
    bank = await handle_lookup_domain_knowledge({"domain": "banking"})
    integrations_text = " ".join(bank["common_integrations"])
    assert "Nafath" in integrations_text
    assert "SADAD" in integrations_text
    assert "Mada" in integrations_text or "mada" in integrations_text

    # E-commerce must have ZATCA + BNPL (Tabby/Tamara)
    ecom = await handle_lookup_domain_knowledge({"domain": "ecommerce"})
    ecom_compliance = " ".join(ecom["compliance_required"])
    assert "ZATCA" in ecom_compliance
    ecom_integrations = " ".join(ecom["common_integrations"])
    assert "Tabby" in ecom_integrations or "Tamara" in ecom_integrations

    # Government services must have Nafath + Yakeen
    gov = await handle_lookup_domain_knowledge({"domain": "government_services"})
    gov_text = " ".join(gov["common_integrations"])
    assert "Nafath" in gov_text
    assert "Yakeen" in gov_text


@pytest.mark.asyncio
async def test_lookup_unicode_arabic_description_works():
    """Arabic-only descriptions auto-guess correctly."""
    from backend.modules.freebuild.continuation_app_tools import handle_lookup_domain_knowledge
    res = await handle_lookup_domain_knowledge({
        "description": "تطبيق حجز مواعيد للمشاغل النسائية والصالونات",
    })
    assert res["ok"] is True
    assert res["domain_id"] == "beauty_salons"
