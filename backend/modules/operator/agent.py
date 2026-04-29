"""
DevOps AI Agent — ReAct-style autonomous agent per client.

Architecture:
  • System prompt describes the agent's role + available tools + client context
  • Conversation history stored in Mongo (operator_chats collection)
  • Agent responds in JSON:
      {"thought": "...", "tool": "name", "args": {...}}      — to invoke a tool
      {"thought": "...", "final": "..."}                     — to deliver final answer
  • Backend parses, executes the tool, appends the result as next turn, loops
  • Max 12 tool calls per user message to prevent runaway loops
  • Every tool invocation is logged for auditing

Available tools:
  context           → list repo files + latest deployment status + env vars
  read_file(path)   → read a file from GitHub
  write_file(path, content, message)  → commit a file to GitHub
  list_dir(path)    → list files under a dir in GitHub
  railway_status    → fetch latest Railway deployment info
  railway_redeploy  → trigger a Railway redeploy
  railway_set_env(name, value)  → upsert a Railway env variable
  vercel_redeploy   → trigger a Vercel redeploy
  done(message)     → finish the turn with a final message to the user
"""
import os
import json
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from emergentintegrations.llm.chat import LlmChat, UserMessage

from . import vault
from . import actions as ops


MAX_TOOL_STEPS = 12
MODEL_PROVIDER = "anthropic"
MODEL_NAME = "claude-sonnet-4-5-20250929"


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


SYSTEM_PROMPT = """أنت "Zitex DevOps Agent" — وكيل ذكاء اصطناعي محترف يعمل نيابةً عن مالك الوكالة لصيانة ونشر وتحديث مشاريع العملاء على GitHub + Railway + Vercel.

مبادئك:
1. تحدّث بالعربية دائماً مع المستخدم.
2. فكّر خطوة بخطوة قبل استخدام أي أداة.
3. اجمع المعلومات قبل اتخاذ إجراء مُدمّر (مثلاً: اقرأ الملف قبل الكتابة فوقه).
4. لا تنفّذ `write_file` إلا بعد توضيح التغيير للمستخدم أو حين يكون تغييراً آمناً وواضحاً.
5. عند فشل Deployment، اتبع هذه الخطة: railway_status → اقرأ الملف المسبّب للمشكلة → صحّح → write_file → railway_redeploy.
6. عندما تنتهي من مهمة المستخدم، استدعِ `done` برسالة واضحة.

تنسيق الرد (ضروري):
- إما استخدام أداة:
  ```json
  {"thought": "ما أفكر فيه", "tool": "اسم_الأداة", "args": {}}
  ```
- أو إنهاء الدور:
  ```json
  {"thought": "خلاصة", "final": "الرسالة النهائية للمستخدم"}
  ```
- لا تضف نصاً خارج بلوك JSON الواحد. بلوك واحد فقط في كل رد.

الأدوات المتاحة:
- `context` (بدون args): يعطيك ملخّصاً كاملاً عن العميل (repo, files tree, آخر deployment).
- `read_file`: args={"path": "backend/server.py"} → محتوى الملف.
- `list_dir`: args={"path": "backend/"} → قائمة الملفات والمجلدات داخل مسار.
- `write_file`: args={"path": "...", "content": "...", "message": "commit msg"} → ينشئ/يعدّل ملف.
- `railway_status` (بدون args): حالة آخر deployment على Railway.
- `railway_redeploy` (بدون args): يطلق نشر جديد على Railway.
- `railway_set_env`: args={"name": "KEY", "value": "val"} → يُحدّث متغير بيئي.
- `vercel_redeploy` (بدون args): يطلق نشر جديد على Vercel.
- `remember`: args={"fact": "..."} → يحفظ معلومة دائمة عن العميل (تُقرأ في كل جلسة لاحقة). استخدمها لتذكّر الإصلاحات الناجحة، أو تفضيلات العميل، أو معرفة هيكل مشروعه.
- `done`: args={"message": "..."} → ينهي المحادثة مع رسالة نهائية.

ابدأ دائماً بـ `context` عند أول سؤال ليتحمّل السياق. إذا فشلت أداة، لا تكرّرها أكثر من مرتين — اشرح المشكلة في `final` بدلاً من ذلك.
عند نجاح إصلاح أو تعلّم شيء جديد عن العميل، استدعِ `remember` لحفظه قبل الإنهاء."""


class AgentRunner:
    """One instance per user turn — handles tool loop + persistence."""

    def __init__(self, database, client_doc: Dict[str, Any], session_id: str, user_email: str):
        self.db = database
        self.client = client_doc
        self.session_id = session_id
        self.user_email = user_email
        self.cid = client_doc["id"]
        self.steps: List[Dict[str, Any]] = []

    # ── Tool implementations ─────────────────────────────────────────
    async def _tool_context(self) -> Dict[str, Any]:
        out: Dict[str, Any] = {"client_name": self.client.get("name")}
        gh = self.client.get("github") or {}
        rw = self.client.get("railway") or {}
        vc = self.client.get("vercel") or {}
        out["github"] = {"repo": gh.get("repo"), "branch": gh.get("branch", "main"), "configured": bool(gh.get("token_enc"))}
        out["railway"] = {"configured": bool(rw.get("token_enc")), "service_id": rw.get("service_id")}
        out["vercel"] = {"configured": bool(vc.get("token_enc")), "project_id": vc.get("project_id")}

        # Repo top-level tree
        if out["github"]["configured"] and gh.get("repo"):
            try:
                files = await ops.github_test(vault.decrypt(gh["token_enc"]), gh["repo"])
                out["github"]["info"] = files
            except Exception as e:
                out["github"]["error"] = str(e)[:200]

        # Railway latest deployment
        if out["railway"]["configured"] and rw.get("service_id") and rw.get("environment_id"):
            try:
                dep = await ops.railway_latest_deploy(
                    vault.decrypt(rw["token_enc"]), rw["service_id"], rw["environment_id"]
                )
                out["railway"]["latest"] = dep
            except Exception as e:
                out["railway"]["error"] = str(e)[:200]
        return out

    async def _tool_read_file(self, args: Dict[str, Any]) -> Dict[str, Any]:
        gh = self.client.get("github") or {}
        if not gh.get("token_enc") or not gh.get("repo"):
            return {"error": "GitHub not configured for this client"}
        path = (args or {}).get("path") or ""
        if not path:
            return {"error": "path required"}
        info = await ops.github_get_file(
            vault.decrypt(gh["token_enc"]), gh["repo"], path, gh.get("branch", "main")
        )
        if not info.get("exists"):
            return {"exists": False, "path": path}
        content = info.get("content") or ""
        # Truncate very large files
        MAX = 40000
        if len(content) > MAX:
            content = content[:MAX] + "\n\n…[محتوى مقطوع، الملف أكبر من 40KB]"
        return {"exists": True, "path": path, "sha": info["sha"], "content": content}

    async def _tool_list_dir(self, args: Dict[str, Any]) -> Dict[str, Any]:
        import httpx
        gh = self.client.get("github") or {}
        if not gh.get("token_enc") or not gh.get("repo"):
            return {"error": "GitHub not configured"}
        path = (args or {}).get("path") or ""
        async with httpx.AsyncClient(timeout=20) as c:
            r = await c.get(
                f"https://api.github.com/repos/{gh['repo']}/contents/{path}",
                params={"ref": gh.get("branch", "main")},
                headers={"Authorization": f"Bearer {vault.decrypt(gh['token_enc'])}"},
            )
            if r.status_code == 404:
                return {"entries": [], "error": "Not found"}
            r.raise_for_status()
            data = r.json()
            if isinstance(data, dict):
                return {"entries": [{"name": data.get("name"), "type": "file", "size": data.get("size")}]}
            return {
                "entries": [
                    {"name": d.get("name"), "type": d.get("type"), "size": d.get("size", 0)}
                    for d in data[:200]
                ]
            }

    async def _tool_write_file(self, args: Dict[str, Any]) -> Dict[str, Any]:
        gh = self.client.get("github") or {}
        if not gh.get("token_enc") or not gh.get("repo"):
            return {"error": "GitHub not configured"}
        path = (args or {}).get("path") or ""
        content = (args or {}).get("content")
        message = (args or {}).get("message") or f"[AI Agent] Update {path}"
        if not path or content is None:
            return {"error": "path and content are required"}
        res = await ops.github_put_file(
            vault.decrypt(gh["token_enc"]), gh["repo"], path, content, message, gh.get("branch", "main")
        )
        return {"ok": True, **res}

    async def _tool_railway_status(self) -> Dict[str, Any]:
        rw = self.client.get("railway") or {}
        if not (rw.get("token_enc") and rw.get("service_id") and rw.get("environment_id")):
            return {"error": "Railway not fully configured (need token + service_id + environment_id)"}
        return await ops.railway_latest_deploy(
            vault.decrypt(rw["token_enc"]), rw["service_id"], rw["environment_id"]
        )

    async def _tool_railway_redeploy(self) -> Dict[str, Any]:
        rw = self.client.get("railway") or {}
        if not (rw.get("token_enc") and rw.get("service_id") and rw.get("environment_id")):
            return {"error": "Railway not fully configured"}
        return await ops.railway_redeploy(
            vault.decrypt(rw["token_enc"]), rw["service_id"], rw["environment_id"]
        )

    async def _tool_railway_set_env(self, args: Dict[str, Any]) -> Dict[str, Any]:
        rw = self.client.get("railway") or {}
        if not (rw.get("token_enc") and rw.get("project_id") and rw.get("environment_id") and rw.get("service_id")):
            return {"error": "Railway missing project_id/environment_id/service_id"}
        name = (args or {}).get("name") or ""
        value = (args or {}).get("value") or ""
        if not name:
            return {"error": "name required"}
        return await ops.railway_upsert_variable(
            vault.decrypt(rw["token_enc"]),
            rw["project_id"], rw["environment_id"], rw["service_id"], name, value,
        )

    async def _tool_vercel_redeploy(self) -> Dict[str, Any]:
        vc = self.client.get("vercel") or {}
        if not vc.get("token_enc") or not vc.get("project_id"):
            return {"error": "Vercel not configured"}
        return await ops.vercel_redeploy(vault.decrypt(vc["token_enc"]), vc["project_id"])

    async def _tool_remember(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Persist a long-term memory fact about this client (re-injected into every future session)."""
        fact = ((args or {}).get("fact") or "").strip()
        if not fact:
            return {"error": "fact required"}
        await self.db.operator_clients.update_one(
            {"id": self.cid},
            {"$push": {"memory": {"$each": [{"fact": fact[:600], "at": _iso_now()}], "$slice": -40}}},
        )
        return {"ok": True, "saved": fact[:120]}

    # ── Dispatcher ──────────────────────────────────────────────────
    async def _run_tool(self, tool: str, args: Dict[str, Any]) -> Dict[str, Any]:
        try:
            if tool == "context":
                return await self._tool_context()
            if tool == "read_file":
                return await self._tool_read_file(args)
            if tool == "list_dir":
                return await self._tool_list_dir(args)
            if tool == "write_file":
                return await self._tool_write_file(args)
            if tool == "railway_status":
                return await self._tool_railway_status()
            if tool == "railway_redeploy":
                return await self._tool_railway_redeploy()
            if tool == "railway_set_env":
                return await self._tool_railway_set_env(args)
            if tool == "vercel_redeploy":
                return await self._tool_vercel_redeploy()
            if tool == "remember":
                return await self._tool_remember(args)
            return {"error": f"Unknown tool: {tool}"}
        except Exception as e:
            return {"error": str(e)[:500]}

    # ── Core loop ───────────────────────────────────────────────────
    async def run(self, user_text: str, on_step=None) -> Dict[str, Any]:
        """Run the ReAct loop for one user turn. Returns {final, steps}.

        Args:
            user_text: The new user message.
            on_step: optional async callable(event_dict) invoked after each tool step
                     and once at the end. Used for WebSocket streaming.
        """
        api_key = os.environ.get("EMERGENT_LLM_KEY", "")
        if not api_key:
            return {"final": "❌ EMERGENT_LLM_KEY غير مُعدّ في .env", "steps": []}

        # Rebuild chat from history (LlmChat manages its own memory via session_id,
        # but we still explicitly replay to guarantee determinism across restarts).
        # Build memory recap (most recent 10 facts)
        memory = (self.client.get("memory") or [])[-10:]
        memory_block = ""
        if memory:
            memory_block = "\n\n=== ذاكرة دائمة عن العميل (مما تعلّمته سابقاً) ===\n" + "\n".join(
                f"• {m.get('fact','')}" for m in memory
            )

        # Recent action log (long-term operational history)
        try:
            recent = await self.db.operator_actions.find(
                {"client_id": self.cid, "action": {"$regex": "^agent\\."}},
                {"_id": 0, "action": 1, "ok": 1, "detail": 1, "at": 1, "by": 1},
            ).sort("at", -1).limit(20).to_list(20)
        except Exception:
            recent = []
        if recent:
            lines = []
            for r in reversed(recent):
                ok = "✓" if r.get("ok") else "✗"
                tool = (r.get("action") or "").replace("agent.", "")
                detail = (r.get("detail") or "")[:120]
                at = (r.get("at") or "")[:19]
                lines.append(f"  [{at}] {ok} {tool}({detail})")
            memory_block += "\n\n=== سجل الإجراءات الأخيرة (آخر 20) ===\n" + "\n".join(lines)

        sys_prompt = SYSTEM_PROMPT + "\n\n=== بيانات العميل ===\n" + json.dumps(
            {
                "id": self.client.get("id"),
                "name": self.client.get("name"),
                "notes": (self.client.get("notes") or "")[:1000],
                "github_repo": (self.client.get("github") or {}).get("repo", ""),
                "github_branch": (self.client.get("github") or {}).get("branch", "main"),
                "railway_has_token": bool((self.client.get("railway") or {}).get("token_enc")),
                "vercel_has_token": bool((self.client.get("vercel") or {}).get("token_enc")),
            },
            ensure_ascii=False,
        ) + memory_block

        # Increment billing counter (one count per user turn)
        ym = datetime.now(timezone.utc).strftime("%Y-%m")
        await self.db.operator_clients.update_one(
            {"id": self.cid},
            {"$inc": {f"billing.{ym}.agent_calls": 1, "billing_total.agent_calls": 1},
             "$set": {"last_agent_at": _iso_now()}},
        )

        chat = LlmChat(
            api_key=api_key,
            session_id=f"operator-{self.cid}-{self.session_id}",
            system_message=sys_prompt,
        ).with_model(MODEL_PROVIDER, MODEL_NAME)

        # Replay prior conversation if any, so the model has the full thread context
        prior = await self.db.operator_chats.find(
            {"client_id": self.cid, "session_id": self.session_id},
            {"_id": 0, "role": 1, "text": 1},
        ).sort("at", 1).to_list(200)
        for msg in prior:
            # We don't replay tool calls, only user/assistant final turns to keep context lean
            if msg.get("role") == "user":
                try:
                    await chat.send_message(UserMessage(text=msg["text"]))
                except Exception:
                    pass

        # The actual new user turn
        current = user_text

        async def _emit(ev):
            if on_step:
                try:
                    await on_step(ev)
                except Exception:
                    pass

        for step_n in range(MAX_TOOL_STEPS):
            await _emit({"kind": "thinking", "step": step_n})
            try:
                raw = await chat.send_message(UserMessage(text=current))
            except Exception as e:
                final_msg = f"❌ خطأ في LLM: {e}"
                await _emit({"kind": "final", "text": final_msg})
                return {"final": final_msg, "steps": self.steps}

            parsed = self._parse(raw)
            if "final" in parsed:
                self.steps.append({"kind": "final", "thought": parsed.get("thought", ""), "text": parsed["final"]})
                await _emit({"kind": "final", "thought": parsed.get("thought", ""), "text": parsed["final"]})
                return {"final": parsed["final"], "steps": self.steps}

            tool = parsed.get("tool")
            args = parsed.get("args") or {}
            if not tool:
                # Treat plain text as final
                self.steps.append({"kind": "final", "thought": "", "text": raw})
                await _emit({"kind": "final", "text": raw})
                return {"final": raw, "steps": self.steps}

            # Notify that we're about to call a tool (for live UI updates)
            await _emit({"kind": "tool_start", "tool": tool, "args": args, "thought": parsed.get("thought", "")})

            result = await self._run_tool(tool, args)
            step_record = {
                "kind": "tool",
                "thought": parsed.get("thought", ""),
                "tool": tool,
                "args": args,
                "result": result,
            }
            self.steps.append(step_record)
            await _emit({"kind": "tool_done", **step_record})

            # Log tool usage for audit
            await self.db.operator_actions.insert_one({
                "client_id": self.cid,
                "action": f"agent.{tool}",
                "ok": "error" not in (result or {}),
                "detail": (json.dumps(args, ensure_ascii=False)[:300] if args else ""),
                "by": f"ai-agent:{self.user_email}",
                "at": _iso_now(),
            })

            # Feed tool result back as the next "user" turn (so the model keeps the loop)
            current = (
                f"نتيجة الأداة `{tool}`:\n```json\n"
                + json.dumps(result, ensure_ascii=False, default=str)[:8000]
                + "\n```\nاستكمل — استدعِ أداة أخرى أو انهِ الحوار عبر `done`."
            )

        cap_msg = "⚠️ وصلت إلى الحد الأقصى من الخطوات (12) بدون إنهاء. راجع التفاصيل."
        await _emit({"kind": "final", "text": cap_msg})
        return {"final": cap_msg, "steps": self.steps}

    def _parse(self, text: str) -> Dict[str, Any]:
        """Extract the single JSON block from model output, tolerating markdown fences."""
        if not text:
            return {}
        # Strip ```json fences
        m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        candidate = m.group(1) if m else text.strip()
        # Fallback: find first {...} that parses
        try:
            return json.loads(candidate)
        except Exception:
            # Try to locate first/last braces
            try:
                s = candidate.find("{")
                e = candidate.rfind("}")
                if s != -1 and e != -1 and e > s:
                    return json.loads(candidate[s:e + 1])
            except Exception:
                pass
        # Last resort: treat whole text as final answer
        return {"final": text}
