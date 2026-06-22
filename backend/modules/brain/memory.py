"""Project Memory — persistent context the brain never forgets.

Every project gets a structured memory file stored alongside the project
in MongoDB (`freebuild_projects.brain_memory` field). The memory tracks:

  • preferences      — colors, fonts, style choices the user approved
  • decisions        — every YES/NO the user made (with timestamps)
  • do_not           — explicit "don't do this" rules from the user
  • design_anchor    — original design checkpoint to compare against
  • completed_tasks  — what's been done (so brain doesn't re-do it)
  • pending_questions — discovery questions still unanswered
  • trust_score      — running quality score (0-100, decreases on lies)

At the start of every turn, a compact summary is injected into the system
prompt so the brain literally cannot "forget" what the user told it.
"""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class ProjectMemory:
    """Append-only memory for a single project."""

    def __init__(self, raw: Optional[Dict[str, Any]] = None):
        raw = raw or {}
        self.preferences: Dict[str, Any] = raw.get("preferences", {})
        self.decisions: List[Dict[str, Any]] = raw.get("decisions", [])
        self.do_not: List[str] = raw.get("do_not", [])
        self.design_anchor: Optional[Dict[str, Any]] = raw.get("design_anchor")
        self.completed_tasks: List[Dict[str, Any]] = raw.get("completed_tasks", [])
        self.pending_questions: List[Dict[str, Any]] = raw.get("pending_questions", [])
        self.trust_score: int = raw.get("trust_score", 100)
        self.lies_detected: int = raw.get("lies_detected", 0)
        self.last_updated: str = raw.get("last_updated", _now_iso())

    # ─── Mutators ──────────────────────────────────────────────────────
    def set_preference(self, key: str, value: Any) -> None:
        self.preferences[key] = value
        self.last_updated = _now_iso()

    def record_decision(self, question: str, answer: str) -> None:
        self.decisions.append({
            "question": question,
            "answer": answer,
            "at": _now_iso(),
        })
        self.last_updated = _now_iso()

    def forbid(self, rule: str) -> None:
        if rule and rule not in self.do_not:
            self.do_not.append(rule)
            self.last_updated = _now_iso()

    def set_design_anchor(self, html_size: int, structure_hash: str) -> None:
        self.design_anchor = {
            "html_size": html_size,
            "structure_hash": structure_hash,
            "set_at": _now_iso(),
        }
        self.last_updated = _now_iso()

    def mark_completed(self, task: str, evidence: Dict[str, Any]) -> None:
        self.completed_tasks.append({
            "task": task,
            "evidence": evidence,
            "at": _now_iso(),
        })
        self.last_updated = _now_iso()

    def add_pending_question(self, question: str, options: List[str],
                              key: Optional[str] = None) -> None:
        self.pending_questions.append({
            "question": question,
            "options": options,
            "key": key,
            "asked_at": _now_iso(),
        })
        self.last_updated = _now_iso()

    def resolve_pending_question(self, question: str, answer: str) -> None:
        self.pending_questions = [
            q for q in self.pending_questions if q.get("question") != question
        ]
        self.record_decision(question, answer)

    def record_lie(self, claim: str) -> None:
        self.lies_detected += 1
        self.trust_score = max(0, self.trust_score - 8)
        self.last_updated = _now_iso()

    def record_truth(self) -> None:
        self.trust_score = min(100, self.trust_score + 1)

    # ─── Serialization ─────────────────────────────────────────────────
    def to_dict(self) -> Dict[str, Any]:
        return {
            "preferences": self.preferences,
            "decisions": self.decisions[-40:],   # cap to last 40
            "do_not": self.do_not,
            "design_anchor": self.design_anchor,
            "completed_tasks": self.completed_tasks[-30:],
            "pending_questions": self.pending_questions,
            "trust_score": self.trust_score,
            "lies_detected": self.lies_detected,
            "last_updated": self.last_updated,
        }

    # ─── System Prompt Injection ──────────────────────────────────────
    def to_prompt_block(self) -> str:
        """Compact summary injected into every system prompt so the brain
        cannot forget."""
        lines = ["═══ ذاكرة المشروع (لا تنسى أبداً) ═══"]
        if self.preferences:
            lines.append("📌 التفضيلات المعتمدة:")
            for k, v in list(self.preferences.items())[:10]:
                lines.append(f"  • {k}: {v}")
        if self.do_not:
            lines.append("🚫 ممنوع تفعله (قرارات صريحة من العميل):")
            for r in self.do_not[:10]:
                lines.append(f"  ❌ {r}")
        if self.design_anchor:
            lines.append(f"🎨 مرساة التصميم: {self.design_anchor['html_size']} حرف "
                          f"(snapshot: {self.design_anchor['structure_hash'][:8]})")
        if self.completed_tasks:
            lines.append("✅ مهام مكتملة (لا تعيد بناءها):")
            for t in self.completed_tasks[-5:]:
                lines.append(f"  ✓ {t['task']}")
        if self.pending_questions:
            lines.append("❓ أسئلة بانتظار إجابة:")
            for q in self.pending_questions[:5]:
                lines.append(f"  • {q['question']}")
        lines.append(f"📊 درجة الثقة: {self.trust_score}/100  |  أكاذيب: {self.lies_detected}")
        return "\n".join(lines)
