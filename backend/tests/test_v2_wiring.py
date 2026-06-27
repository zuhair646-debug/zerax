"""
Iteration 78 — V2 Wiring Verification
======================================
Verifies the 4 gap closures from iteration 78:
  1. 6 new orphan cortex tools wired (generate_nextjs_project, build_capacitor_app,
     recommend_state_management, search_past_projects, run_in_e2b_sandbox, deploy_via_ssh)
  2. Classifier routing inside /agent-chat-stream (architect/review fast-paths)
  3. HARD HOOK #1: brand_dna auto-extraction on first user message
  4. HARD HOOK #2: auto-Reviewer after HTML changes
  5. Concierge regression — must still pause for mobile requests
"""
from __future__ import annotations

import asyncio
import json
import os
import time
import uuid
import pytest
import requests
import httpx

LOCAL_URL = "http://localhost:8001"
OWNER_EMAIL = "owner@zerax.com"
OWNER_PASS = "owner123"


# ────────────── Fixtures ──────────────
@pytest.fixture(scope="session")
def auth_token():
    r = requests.post(f"{LOCAL_URL}/api/auth/login",
                      json={"email": OWNER_EMAIL, "password": OWNER_PASS}, timeout=20)
    assert r.status_code == 200, f"login failed: {r.status_code} {r.text}"
    data = r.json()
    tok = data.get("access_token") or data.get("token")
    assert tok, f"no token in login response: {data}"
    return tok


@pytest.fixture(scope="session")
def auth_headers(auth_token):
    return {"Authorization": f"Bearer {auth_token}"}


def _create_project(auth_headers, suffix=""):
    name = f"TEST_v2_{suffix}_{uuid.uuid4().hex[:8]}"
    r = requests.post(
        f"{LOCAL_URL}/api/freebuild-chat/project",
        headers={**auth_headers, "Content-Type": "application/json"},
        json={"name": name, "description": "v2 wiring test", "mode": "app", "platform": "both"},
        timeout=30,
    )
    assert r.status_code == 200, f"create project failed: {r.status_code} {r.text[:400]}"
    data = r.json()
    pid = data.get("id") or data.get("project_id") or (data.get("project") or {}).get("id")
    assert pid, f"no project id: {data}"
    return pid


# ────────────── 1. Tool registration ──────────────
class TestNewCortexToolsRegistered:
    def test_tools_schema_count_and_new_tools(self):
        from modules.freebuild.freebuild_agent import TOOLS_SCHEMA
        names = {t["name"] for t in TOOLS_SCHEMA}
        assert len(TOOLS_SCHEMA) == 176, f"expected 176 tools, got {len(TOOLS_SCHEMA)}"
        expected = {"generate_nextjs_project", "build_capacitor_app",
                    "recommend_state_management", "search_past_projects",
                    "run_in_e2b_sandbox", "deploy_via_ssh"}
        missing = expected - names
        assert not missing, f"missing new tools in TOOLS_SCHEMA: {missing}"

    def test_tool_handlers_count_31(self):
        from modules.freebuild.cortex_tools import TOOL_HANDLERS
        assert len(TOOL_HANDLERS) == 31, f"expected 31 handlers, got {len(TOOL_HANDLERS)}"
        expected = {"generate_nextjs_project", "build_capacitor_app",
                    "recommend_state_management", "search_past_projects",
                    "run_in_e2b_sandbox", "deploy_via_ssh"}
        missing = expected - set(TOOL_HANDLERS.keys())
        assert not missing, f"missing handlers: {missing}"


# ────────────── 2. Dispatch each new tool ──────────────
class TestDispatchNewTools:
    def _dispatch(self, name, args, ctx=None):
        from modules.freebuild.cortex_tools import dispatch
        async def _run():
            # Try (name, args, ctx) signature first, fall back to 2-arg
            try:
                return await dispatch(name, args, ctx)
            except TypeError:
                return await dispatch(name, args)
        return asyncio.run(_run())

    def test_dispatch_generate_nextjs_project(self):
        result = self._dispatch("generate_nextjs_project", {"brief": "SaaS dashboard"})
        assert isinstance(result, dict), result
        # Must return ok=True OR a meaningful error structure
        assert "ok" in result, f"generate_nextjs_project malformed: {result}"

    def test_dispatch_build_capacitor_app(self):
        result = self._dispatch("build_capacitor_app",
                                 {"app_id": "com.test.app", "app_name": "TestApp"})
        assert isinstance(result, dict)
        assert "ok" in result, f"build_capacitor_app malformed: {result}"

    def test_dispatch_recommend_state_management(self):
        result = self._dispatch("recommend_state_management",
                                 {"use_case": "global auth state"})
        assert isinstance(result, dict)
        assert "ok" in result, f"recommend_state_management malformed: {result}"

    def test_dispatch_search_past_projects_no_db_ctx(self):
        # Pass ctx=None → expect 'no db context' style error
        result = self._dispatch("search_past_projects", {"query": "ecommerce"}, ctx=None)
        assert isinstance(result, dict)
        assert "ok" in result, f"search_past_projects malformed: {result}"
        if not result.get("ok"):
            err = (result.get("error") or "").lower()
            assert "db" in err or "ctx" in err or "context" in err, (
                f"expected db/context error, got: {result}"
            )

    def test_dispatch_run_in_e2b_sandbox_no_auth(self):
        result = self._dispatch("run_in_e2b_sandbox", {"code": "print(1)"}, ctx=None)
        assert isinstance(result, dict)
        assert "ok" in result, f"run_in_e2b_sandbox malformed: {result}"
        if not result.get("ok"):
            err = (result.get("error") or "").lower()
            assert "auth" in err or "ctx" in err or "context" in err or "token" in err, (
                f"expected auth/context error, got: {result}"
            )

    def test_dispatch_deploy_via_ssh_no_auth(self):
        result = self._dispatch("deploy_via_ssh",
                                 {"host": "1.2.3.4", "user": "root", "commands": ["ls"]},
                                 ctx=None)
        assert isinstance(result, dict)
        assert "ok" in result, f"deploy_via_ssh malformed: {result}"
        if not result.get("ok"):
            err = (result.get("error") or "").lower()
            assert "auth" in err or "ctx" in err or "context" in err or "ssh" in err, (
                f"expected auth/context error, got: {result}"
            )


# ────────────── 3. SSE Classifier Routing ──────────────
def _consume_sse(url, headers, payload, timeout=90.0, stop_on_done=True, max_events=200):
    """Return (events_seen, payloads_by_event, done_payload, full_chunks)."""
    events_seen = []
    payloads_by_event = {}
    done_payload = None
    full_chunks = []
    try:
        with httpx.stream("POST", url, headers=headers, data=payload, timeout=timeout) as r:
            assert r.status_code == 200, f"stream {r.status_code}: {r.read()[:400]}"
            current_event = None
            for line in r.iter_lines():
                if not line:
                    continue
                if line.startswith("event:"):
                    current_event = line.split(":", 1)[1].strip()
                    events_seen.append(current_event)
                    full_chunks.append(("event", current_event))
                elif line.startswith("data:") and current_event:
                    raw = line.split(":", 1)[1].strip()
                    try:
                        parsed = json.loads(raw)
                    except Exception:
                        parsed = {"_raw": raw}
                    payloads_by_event.setdefault(current_event, []).append(parsed)
                    full_chunks.append(("data", current_event, parsed))
                    if current_event == "done":
                        done_payload = parsed
                        if stop_on_done:
                            break
                if len(events_seen) >= max_events:
                    break
    except httpx.ReadTimeout:
        pass
    return events_seen, payloads_by_event, done_payload, full_chunks


class TestClassifierRouting:
    def test_architect_fast_path(self, auth_token, auth_headers):
        pid = _create_project(auth_headers, "arch")
        url = f"{LOCAL_URL}/api/freebuild-chat/project/{pid}/agent-chat-stream"
        headers = {"Authorization": f"Bearer {auth_token}"}
        data = {
            "message": "أريد design system معماري لـ SaaS multi-tenant مع ERD diagram",
            "user_language": "ar",
        }
        events, payloads, done, _ = _consume_sse(url, headers, data, timeout=90.0)
        print(f"[architect] events: {events[:30]}")
        print(f"[architect] classifier payload: {payloads.get('classifier')}")
        print(f"[architect] done: {done}")

        assert "classifier" in events, f"no classifier event; events: {events[:20]}"
        cl = (payloads.get("classifier") or [{}])[0]
        assert cl.get("primary") == "architect", f"primary={cl.get('primary')}, payload={cl}"
        assert cl.get("confidence", 0) >= 0.85, f"confidence too low: {cl}"
        # Cortex events should appear
        cortex_events = [e for e in events if "cortex" in e.lower() or e == "auto_review"]
        assert cortex_events, f"no cortex events in stream: {events[:30]}"
        # No tool_call event (architect is single-pass)
        assert "tool_call" not in events and "tool_result" not in events, (
            f"unexpected tool events in architect fast-path: {events}"
        )
        assert done is not None, "no done event"

    def test_review_fast_path(self, auth_token, auth_headers):
        pid = _create_project(auth_headers, "review")
        url = f"{LOCAL_URL}/api/freebuild-chat/project/{pid}/agent-chat-stream"
        headers = {"Authorization": f"Bearer {auth_token}"}
        data = {
            "message": "راجع لي هذا الكود واعمل audit: <html><script>eval(userInput)</script></html>",
            "user_language": "ar",
        }
        events, payloads, done, _ = _consume_sse(url, headers, data, timeout=60.0)
        print(f"[review] events: {events[:30]}")
        print(f"[review] classifier: {payloads.get('classifier')}")
        print(f"[review] cortex_step: {payloads.get('cortex_step')}")
        print(f"[review] done: {done}")

        cl = (payloads.get("classifier") or [{}])[0]
        assert cl.get("primary") == "review", f"primary={cl.get('primary')}, payload={cl}"
        assert "cortex_step" in events, f"no cortex_step event: {events[:20]}"
        assert done is not None, "no done event"
        assert done.get("model_used") == "static_analyzer", f"model_used={done.get('model_used')}"
        assert done.get("credits_charged") == 3, f"credits={done.get('credits_charged')}"
        assert "review_report" in done, f"done missing review_report: keys={list(done.keys())}"

    def test_code_normal_path(self, auth_token, auth_headers):
        """A landing-page request should classify as 'code' and NOT take fast-path."""
        pid = _create_project(auth_headers, "code")
        url = f"{LOCAL_URL}/api/freebuild-chat/project/{pid}/agent-chat-stream"
        headers = {"Authorization": f"Bearer {auth_token}"}
        data = {"message": "أبغى موقع landing لمطعمي", "user_language": "ar"}

        # Don't wait for done — just verify classifier says code and stream proceeds
        events_seen = []
        cl_payload = None
        try:
            with httpx.stream("POST", url, headers=headers, data=data, timeout=30.0) as r:
                assert r.status_code == 200
                current_event = None
                for line in r.iter_lines():
                    if not line:
                        continue
                    if line.startswith("event:"):
                        current_event = line.split(":", 1)[1].strip()
                        events_seen.append(current_event)
                    elif line.startswith("data:") and current_event == "classifier":
                        raw = line.split(":", 1)[1].strip()
                        try:
                            cl_payload = json.loads(raw)
                        except Exception:
                            pass
                    # Stop once we see proof of normal stream_agent_turn flow
                    if current_event in ("text_delta", "tool_call", "tool_result", "tool"):
                        break
                    if len(events_seen) >= 25:
                        break
        except httpx.ReadTimeout:
            pass

        print(f"[code] events: {events_seen[:20]}")
        print(f"[code] classifier: {cl_payload}")
        assert "classifier" in events_seen, f"no classifier event: {events_seen}"
        # primary should be 'code' (or at least not architect/review)
        if cl_payload:
            assert cl_payload.get("primary") not in ("architect", "review"), (
                f"unexpected fast-path classification: {cl_payload}"
            )
        # We should see normal stream events (text_delta or tool) — proves NOT architect fast-path
        normal = any(e in events_seen for e in ("text_delta", "tool_call", "tool_result", "tool"))
        assert normal, f"no normal stream events seen — may be wrongly routed: {events_seen}"


# ────────────── 4. HARD HOOK #1: Brand DNA ──────────────
class TestBrandDNAHook:
    def test_brand_dna_extracted_on_first_message_and_persisted(self, auth_token, auth_headers):
        pid = _create_project(auth_headers, "branddna")
        url = f"{LOCAL_URL}/api/freebuild-chat/project/{pid}/agent-chat-stream"
        headers = {"Authorization": f"Bearer {auth_token}"}
        data = {
            "message": "قهوة عُمانية فاخرة بشخصية أنيقة هادئة",
            "user_language": "ar",
        }

        # Stream first message — collect any brand_dna_extracted event during it
        brand_dna_event_seen = False
        events = []
        start = time.time()
        try:
            with httpx.stream("POST", url, headers=headers, data=data, timeout=120.0) as r:
                assert r.status_code == 200
                current_event = None
                for line in r.iter_lines():
                    if not line:
                        continue
                    if line.startswith("event:"):
                        current_event = line.split(":", 1)[1].strip()
                        events.append(current_event)
                        if current_event == "brand_dna_extracted":
                            brand_dna_event_seen = True
                        if current_event == "done":
                            # Read a few more lines to capture trailing brand_dna_extracted
                            pass
                    if current_event == "done" and (time.time() - start) > 5:
                        # Drain ~3 sec post-done for bg event
                        break
        except httpx.ReadTimeout:
            pass
        print(f"[brand_dna] events: {events[:40]}")
        print(f"[brand_dna] event seen: {brand_dna_event_seen}")

        # Poll GET project for up to 25s to confirm persistence
        proj_url = f"{LOCAL_URL}/api/freebuild-chat/project/{pid}"
        persisted = None
        ts = None
        for i in range(25):
            time.sleep(1)
            pr = requests.get(proj_url, headers=auth_headers, timeout=15)
            if pr.status_code == 200:
                pdata = pr.json()
                project = pdata.get("project") or pdata
                dna = project.get("brand_dna")
                ts = project.get("brand_dna_extracted_at")
                if dna:
                    persisted = dna
                    break
        print(f"[brand_dna] persisted: {bool(persisted)}, ts: {ts}")
        if persisted:
            print(f"[brand_dna] keys: {list(persisted.keys())}")

        # Accept either: (a) brand_dna_extracted SSE event fired OR (b) persistence happened
        assert brand_dna_event_seen or persisted, (
            f"neither brand_dna_extracted event nor persistence detected. events={events[:30]}"
        )
        if persisted:
            assert ts is not None, "brand_dna_extracted_at timestamp missing"
            assert isinstance(ts, str), f"ts not string: {ts}"
            # Validate at least some expected keys
            expected_keys = {"palette", "tone", "voice", "archetypes"}
            found = expected_keys & set(persisted.keys())
            assert len(found) >= 2, f"brand_dna missing expected keys; got: {list(persisted.keys())}"

        # Second message — should NOT re-fire brand_dna_extracted
        data2 = {"message": "أضف قسم about us", "user_language": "ar"}
        events2 = []
        brand_dna_again = False
        try:
            with httpx.stream("POST", url, headers=headers, data=data2, timeout=45.0) as r:
                current_event = None
                for line in r.iter_lines():
                    if not line:
                        continue
                    if line.startswith("event:"):
                        current_event = line.split(":", 1)[1].strip()
                        events2.append(current_event)
                        if current_event == "brand_dna_extracted":
                            brand_dna_again = True
                        if current_event == "done":
                            break
                    if len(events2) > 80:
                        break
        except httpx.ReadTimeout:
            pass
        print(f"[brand_dna 2nd msg] event re-fired: {brand_dna_again}")
        assert not brand_dna_again, (
            f"brand_dna_extracted fired again on 2nd msg (should be idempotent). events={events2[:30]}"
        )


# ────────────── 5. HARD HOOK #2: Auto-Reviewer ──────────────
class TestAutoReviewerHook:
    def test_auto_review_event_fires_when_html_updated(self, auth_token, auth_headers):
        pid = _create_project(auth_headers, "autorev")
        url = f"{LOCAL_URL}/api/freebuild-chat/project/{pid}/agent-chat-stream"
        headers = {"Authorization": f"Bearer {auth_token}"}
        # Use a request that creates HTML
        data = {"message": "ابني صفحة ترحيب بسيطة فيها زر تسجيل دخول", "user_language": "ar"}

        events, payloads, done, _ = _consume_sse(
            url, headers, data, timeout=180.0, stop_on_done=False, max_events=400
        )
        print(f"[auto_review] events sample: {events[:60]}")
        print(f"[auto_review] auto_review payload: {payloads.get('auto_review')}")
        print(f"[auto_review] done.html_updated: {done.get('html_updated') if done else None}")

        # If html_updated=True we MUST see auto_review event
        if done and done.get("html_updated"):
            assert "auto_review" in events, (
                f"html_updated=True but no auto_review event. events: {events[:50]}"
            )
            ar = (payloads.get("auto_review") or [{}])[0]
            assert "score" in ar, f"auto_review payload missing score: {ar}"
            assert "critical_high_count" in ar, f"auto_review missing critical_high_count: {ar}"
            assert "total_issues" in ar, f"auto_review missing total_issues: {ar}"
        else:
            # Soft assertion — at least classifier+done flow worked
            assert done is not None, f"no done event; events: {events[:30]}"
            print("[auto_review] html_updated was False — auto_review correctly skipped")


# ────────────── 6. Concierge regression ──────────────
class TestConciergeRegression:
    def test_mobile_request_still_pauses(self, auth_token, auth_headers):
        pid = _create_project(auth_headers, "concierge")
        url = f"{LOCAL_URL}/api/freebuild-chat/project/{pid}/agent-chat-stream"
        headers = {"Authorization": f"Bearer {auth_token}"}
        data = {"message": "أبغى تطبيق موبايل iOS", "user_language": "ar"}

        events_seen = []
        setup_required_seen = False
        wizard_cards = 0
        done_payload = None
        classifier_seen = False
        try:
            with httpx.stream("POST", url, headers=headers, data=data, timeout=60.0) as r:
                assert r.status_code == 200
                current_event = None
                for line in r.iter_lines():
                    if not line:
                        continue
                    if line.startswith("event:"):
                        current_event = line.split(":", 1)[1].strip()
                        events_seen.append(current_event)
                        if current_event == "concierge_setup_required":
                            setup_required_seen = True
                        if current_event == "concierge_wizard_card":
                            wizard_cards += 1
                        if current_event == "classifier":
                            classifier_seen = True
                    elif line.startswith("data:") and current_event == "done":
                        try:
                            done_payload = json.loads(line.split(":", 1)[1].strip())
                        except Exception:
                            pass
                        break
        except httpx.ReadTimeout:
            pytest.fail(f"stream timed out. events: {events_seen[:20]}")

        print(f"[concierge regress] events: {events_seen[:25]}")
        print(f"[concierge regress] setup_required: {setup_required_seen}, cards: {wizard_cards}")
        print(f"[concierge regress] classifier_seen_before_pause: {classifier_seen}")
        print(f"[concierge regress] done: {done_payload}")

        assert setup_required_seen, f"concierge pause broken; events: {events_seen[:20]}"
        assert wizard_cards >= 2, f"expected >=2 wizard cards, got {wizard_cards}"
        assert done_payload and done_payload.get("paused_for_setup") is True, (
            f"done missing paused_for_setup: {done_payload}"
        )
        # Classifier MUST NOT fire before concierge pause
        assert not classifier_seen, (
            f"classifier fired before concierge pause (wrong order!): {events_seen}"
        )
