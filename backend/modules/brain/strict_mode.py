"""Strict Tool Mode — eliminate "تم بنجاح" lies forever.

Pre-Brain-v2, the AI would emit text like "تم بنجاح! أنشأت about.html" without
calling any tool. The Lie Detector caught some of these but only post-hoc.

In Brain v2, the AI is *physically incapable* of claiming completion via text:

  • The model is forced to call `complete_task(evidence=[...])` to finish.
  • `complete_task` validates the evidence against ctx.changes_made and the
    actual HTML state. If evidence is fabricated, the tool returns an error
    AND the brain transitions back to EXECUTING.
  • The final user-facing summary is constructed by Brain v2 itself based on
    the *validated evidence*, not the model's text.

This shifts the source-of-truth from "what the AI says" to "what actually
happened in the project state."
"""
from typing import Any, Dict, List, Set


def validate_completion_evidence(
    evidence: List[Dict[str, Any]],
    actual_changes_made: int,
    actual_pages: Dict[str, str],
    actual_html_size: int,
) -> Dict[str, Any]:
    """Verify the evidence the AI provided is consistent with the real state.

    Evidence is a list of facts the AI claims to have accomplished. Each
    fact has a `type` and `details`. We verify each:

      • { type: "page_created", filename: "about.html" } — verify pages dict
      • { type: "section_added", section_id: "cart" }   — verify in HTML
      • { type: "section_removed", section_id: "cart" } — verify NOT in HTML
      • { type: "section_moved", from_page, to_page, section_id } — verify both
      • { type: "html_modified", bytes_changed: 5234 }  — verify >= 100 bytes
      • { type: "page_deleted", filename }              — verify not in pages

    Returns:
      {
        "valid": bool,
        "verified_facts": [...],
        "rejected_facts": [{"fact": ..., "reason": "..."}],
        "summary": "..."
      }
    """
    import re

    if not isinstance(evidence, list):
        return {"valid": False, "verified_facts": [], "rejected_facts": [],
                "summary": "evidence must be a list"}
    if len(evidence) == 0 and actual_changes_made > 0:
        return {"valid": False, "verified_facts": [], "rejected_facts": [],
                "summary": "changes were made but no evidence provided"}
    if len(evidence) == 0 and actual_changes_made == 0:
        return {"valid": False, "verified_facts": [], "rejected_facts": [],
                "summary": "no work done — cannot claim completion"}

    verified, rejected = [], []
    full_html = "\n".join(actual_pages.values())

    for fact in evidence:
        if not isinstance(fact, dict) or "type" not in fact:
            rejected.append({"fact": fact, "reason": "missing 'type'"})
            continue
        t = fact.get("type")

        if t == "page_created":
            fn = (fact.get("filename") or "").strip().lower()
            if not fn:
                rejected.append({"fact": fact, "reason": "filename required"})
            elif fn not in actual_pages:
                rejected.append({"fact": fact,
                                  "reason": f"page '{fn}' not in actual pages — LIE"})
            else:
                verified.append(fact)

        elif t == "section_added":
            sid = (fact.get("section_id") or "").lstrip("#")
            if not sid:
                rejected.append({"fact": fact, "reason": "section_id required"})
            elif not re.search(
                rf'<section\b[^>]*\bid\s*=\s*["\']({re.escape(sid)})["\']',
                full_html, re.I,
            ):
                rejected.append({"fact": fact,
                                  "reason": f"section #{sid} not found in any page — LIE"})
            else:
                verified.append(fact)

        elif t == "section_removed":
            sid = (fact.get("section_id") or "").lstrip("#")
            page = (fact.get("page") or "").strip().lower()
            if page and page in actual_pages:
                hay = actual_pages[page]
            else:
                hay = full_html
            if re.search(rf'<section\b[^>]*\bid\s*=\s*["\']({re.escape(sid)})["\']',
                          hay, re.I):
                rejected.append({"fact": fact,
                                  "reason": f"section #{sid} STILL present — removal was a LIE"})
            else:
                verified.append(fact)

        elif t == "section_moved":
            sid = (fact.get("section_id") or "").lstrip("#")
            src = (fact.get("from_page") or "").strip().lower()
            tgt = (fact.get("to_page") or "").strip().lower()
            src_html = actual_pages.get(src, "")
            tgt_html = actual_pages.get(tgt, "")
            sec_pat = rf'<section\b[^>]*\bid\s*=\s*["\']({re.escape(sid)})["\']'
            still_in_src = bool(re.search(sec_pat, src_html, re.I))
            now_in_tgt = bool(re.search(sec_pat, tgt_html, re.I))
            if still_in_src and not now_in_tgt:
                rejected.append({"fact": fact,
                                  "reason": "section still in source, not in target — move is a LIE"})
            elif not now_in_tgt:
                rejected.append({"fact": fact,
                                  "reason": f"section #{sid} not in target page '{tgt}' — LIE"})
            else:
                verified.append(fact)

        elif t == "html_modified":
            bc = int(fact.get("bytes_changed") or 0)
            if bc < 100:
                rejected.append({"fact": fact, "reason": "claimed <100 bytes change — too small to count"})
            else:
                verified.append(fact)

        elif t == "page_deleted":
            fn = (fact.get("filename") or "").strip().lower()
            if fn in actual_pages:
                rejected.append({"fact": fact,
                                  "reason": f"page '{fn}' still present — deletion is a LIE"})
            else:
                verified.append(fact)

        elif t == "preference_recorded" or t == "question_asked" or t == "plan_presented":
            # Non-HTML facts — accept as-is (orchestrator records them)
            verified.append(fact)

        else:
            rejected.append({"fact": fact, "reason": f"unknown evidence type '{t}'"})

    valid = len(rejected) == 0 and len(verified) > 0
    summary = (f"✅ تحقق من {len(verified)} حقيقة"
                if valid
                else f"❌ {len(rejected)} حقيقة مرفوضة / {len(verified)} مقبولة")
    return {
        "valid": valid,
        "verified_facts": verified,
        "rejected_facts": rejected,
        "summary": summary,
    }
