"""Tests for Brain v2 — state machine, memory, strict-mode, discovery, planner.

Run: pytest /app/backend/tests/test_brain_v2.py -v
"""
import pytest
from modules.brain import BrainOrchestrator, BrainConfig, BrainState, ProjectMemory
from modules.brain.states import can_transition, tools_for_state
from modules.brain.discovery import (
    detect_project_type, get_initial_questions, QUESTION_BANKS,
)
from modules.brain.planner import build_plan, estimate_plan_cost
from modules.brain.strict_mode import validate_completion_evidence


# ─── State Machine ───────────────────────────────────────────────────────

class TestStateMachine:
    def test_legal_transitions(self):
        assert can_transition(BrainState.IDLE, BrainState.DISCOVERY)
        assert can_transition(BrainState.DISCOVERY, BrainState.PLANNING)
        assert can_transition(BrainState.PLANNING, BrainState.AWAITING_APPROVAL)
        assert can_transition(BrainState.AWAITING_APPROVAL, BrainState.EXECUTING)
        assert can_transition(BrainState.EXECUTING, BrainState.VERIFYING)
        assert can_transition(BrainState.VERIFYING, BrainState.IDLE)

    def test_illegal_transitions(self):
        # cannot jump from IDLE straight to VERIFYING
        assert not can_transition(BrainState.IDLE, BrainState.VERIFYING)
        # cannot jump from DISCOVERY straight to EXECUTING
        assert not can_transition(BrainState.DISCOVERY, BrainState.EXECUTING)
        # cannot go from AWAITING_APPROVAL straight to VERIFYING
        assert not can_transition(BrainState.AWAITING_APPROVAL, BrainState.VERIFYING)

    def test_tools_per_state(self):
        assert "ask_user" in tools_for_state(BrainState.DISCOVERY)
        assert "ask_user" not in tools_for_state(BrainState.EXECUTING)
        assert "write_full_html" in tools_for_state(BrainState.EXECUTING)
        assert "write_full_html" not in tools_for_state(BrainState.DISCOVERY)
        assert "complete_task" in tools_for_state(BrainState.VERIFYING)
        assert "complete_task" not in tools_for_state(BrainState.PLANNING)


# ─── Project Memory ──────────────────────────────────────────────────────

class TestProjectMemory:
    def test_record_decisions(self):
        m = ProjectMemory()
        m.record_decision("اللون؟", "ذهبي")
        m.record_decision("الصفحات؟", "3")
        assert len(m.decisions) == 2
        assert m.decisions[0]["answer"] == "ذهبي"

    def test_forbid_list(self):
        m = ProjectMemory()
        m.forbid("لا أنميشن زائد")
        m.forbid("لا تستخدم أرجواني")
        m.forbid("لا أنميشن زائد")  # duplicate
        assert len(m.do_not) == 2

    def test_trust_score_drops_on_lies(self):
        m = ProjectMemory()
        assert m.trust_score == 100
        m.record_lie("claimed to create page but did nothing")
        assert m.trust_score == 92
        assert m.lies_detected == 1

    def test_prompt_block_contains_preferences(self):
        m = ProjectMemory()
        m.set_preference("اللون", "ذهبي وأخضر")
        m.forbid("لا تستخدم أرجواني")
        block = m.to_prompt_block()
        assert "ذهبي وأخضر" in block
        assert "أرجواني" in block
        assert "ذاكرة المشروع" in block

    def test_serialization_roundtrip(self):
        m1 = ProjectMemory()
        m1.set_preference("color", "gold")
        m1.record_decision("Q?", "A")
        d = m1.to_dict()
        m2 = ProjectMemory(d)
        assert m2.preferences == {"color": "gold"}
        assert len(m2.decisions) == 1


# ─── Discovery Engine ────────────────────────────────────────────────────

class TestDiscovery:
    @pytest.mark.parametrize("msg,expected", [
        ("ابني لي متجر زهور", "ecommerce"),
        ("أبي محفظة مصمم جرافيك", "portfolio"),
        ("ابني صفحة هبوط لتطبيق", "saas_landing"),
        ("ابني موقع شركة", "generic"),
    ])
    def test_project_type_detection(self, msg, expected):
        assert detect_project_type(msg) == expected

    def test_question_banks_have_options(self):
        for ptype, bank in QUESTION_BANKS.items():
            assert len(bank) >= 3, f"{ptype} has too few questions"
            for q in bank:
                assert q.get("q"), f"missing question text in {ptype}"
                assert isinstance(q.get("options"), list)
                assert len(q["options"]) >= 2

    def test_initial_questions_limit(self):
        qs = get_initial_questions("ecommerce", limit=3)
        assert len(qs) == 3


# ─── Planner ─────────────────────────────────────────────────────────────

class TestPlanner:
    def test_build_plan_ecommerce(self):
        plan = build_plan(
            user_goal="متجر زهور",
            project_type="ecommerce",
            answers={"site_structure": "صفحات متعددة"},
            current_pages=["index.html"],
        )
        assert plan["approval_required"]
        assert len(plan["steps"]) > 5
        # Should include products/about/contact pages
        steps_str = str(plan["steps"])
        assert "products.html" in steps_str
        assert "about.html" in steps_str

    def test_plan_cost_estimate(self):
        plan = build_plan("test", "ecommerce", {}, [])
        cost = plan["cost_estimate"]
        assert cost["min"] < cost["expected"] < cost["max"]
        assert cost["expected"] > 30


# ─── Strict Mode (Completion Evidence Validation) ────────────────────────

class TestStrictMode:
    def test_no_evidence_rejected(self):
        r = validate_completion_evidence([], 0, {"index.html": "x"}, 100)
        assert not r["valid"]

    def test_page_created_lie(self):
        # AI claims it created about.html but pages dict has only index.html
        r = validate_completion_evidence(
            [{"type": "page_created", "filename": "about.html"}],
            actual_changes_made=1,
            actual_pages={"index.html": "x"},
            actual_html_size=100,
        )
        assert not r["valid"]
        assert len(r["rejected_facts"]) == 1
        assert "LIE" in r["rejected_facts"][0]["reason"]

    def test_page_created_truth(self):
        r = validate_completion_evidence(
            [{"type": "page_created", "filename": "about.html"}],
            actual_changes_made=1,
            actual_pages={"index.html": "x", "about.html": "y"},
            actual_html_size=200,
        )
        assert r["valid"]

    def test_section_removed_lie(self):
        # AI claims it removed #cart but the section is still in HTML
        r = validate_completion_evidence(
            [{"type": "section_removed", "section_id": "cart"}],
            actual_changes_made=1,
            actual_pages={"index.html": '<section id="cart">x</section>'},
            actual_html_size=100,
        )
        assert not r["valid"]
        assert "STILL present" in r["rejected_facts"][0]["reason"]

    def test_section_moved_validation(self):
        # Moved #cart from index to cart.html — both halves verified
        r = validate_completion_evidence(
            [{"type": "section_moved", "section_id": "cart",
              "from_page": "index.html", "to_page": "cart.html"}],
            actual_changes_made=1,
            actual_pages={
                "index.html": "<body>no cart here</body>",
                "cart.html": '<body><section id="cart">moved</section></body>',
            },
            actual_html_size=200,
        )
        assert r["valid"]


# ─── Brain Orchestrator integration ──────────────────────────────────────

class TestBrainOrchestrator:
    def test_initial_state_decision_empty_project(self):
        cfg = BrainConfig(enable_discovery=True)
        brain = BrainOrchestrator(cfg)
        brain.load_memory({"id": "p1"})
        state = brain.decide_initial_state(
            {"id": "p1", "current_html": "", "pages": {}},
            "ابني لي متجر زهور",
        )
        assert state == BrainState.DISCOVERY

    def test_initial_state_skip_phrase(self):
        cfg = BrainConfig(enable_discovery=True)
        brain = BrainOrchestrator(cfg)
        brain.load_memory({"id": "p1"})
        state = brain.decide_initial_state(
            {"id": "p1", "current_html": "", "pages": {}},
            "ابدأ فوراً بدون أسئلة، متجر زهور",
        )
        assert state == BrainState.EXECUTING

    def test_initial_state_existing_project(self):
        cfg = BrainConfig()
        brain = BrainOrchestrator(cfg)
        brain.load_memory({"id": "p1"})
        state = brain.decide_initial_state(
            {"id": "p1", "current_html": "x" * 1000},
            "غيّر اللون لذهبي",
        )
        assert state == BrainState.EXECUTING

    def test_initial_state_approval_resumes_execution(self):
        cfg = BrainConfig()
        brain = BrainOrchestrator(cfg)
        brain.load_memory({"id": "p1"})
        state = brain.decide_initial_state(
            {"id": "p1", "brain_last_state": "awaiting_approval"},
            "موافق",
        )
        assert state == BrainState.EXECUTING

    def test_illegal_transition_rejected(self):
        brain = BrainOrchestrator(BrainConfig())
        brain.current_state = BrainState.IDLE
        # IDLE → VERIFYING is illegal
        assert not brain.transition_to(BrainState.VERIFYING, "test")
        assert brain.current_state == BrainState.IDLE
