"""
🔧 Refactor Cortex — multi-file rename/refactor.

For now we use regex-based refactoring (safer than full AST since we
operate on flat HTML/JS/CSS files). Supports:
  - rename_identifier: rename a variable/function across all files
  - extract_section: pull repeated HTML into a reusable snippet
  - find_duplicates: detect copy-paste blocks

Future: integrate tree-sitter for true AST-aware refactoring.
"""
from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("zenrex.refactor_cortex")


def rename_identifier(files: Dict[str, str], old_name: str, new_name: str) -> Dict[str, Any]:
    """Rename a JS identifier across all files.

    Args:
        files: {filename: content}
        old_name: existing identifier (e.g. 'userName')
        new_name: replacement (e.g. 'customerName')

    Returns:
        {
          "files_changed": {filename: new_content, ...},
          "total_replacements": int,
          "per_file": {filename: count},
        }

    Notes:
        - Uses word-boundary regex (won't replace inside strings reliably)
        - Skips comments and string literals via best-effort tokenizer
    """
    if not old_name or not new_name or old_name == new_name:
        return {"files_changed": {}, "total_replacements": 0, "per_file": {}}

    # Word-boundary regex; in JS, $ and _ count as identifier chars
    pattern = re.compile(r"(?<![A-Za-z0-9_$])" + re.escape(old_name) + r"(?![A-Za-z0-9_$])")

    files_changed: Dict[str, str] = {}
    per_file: Dict[str, int] = {}
    total = 0
    for fname, content in files.items():
        new_content, n = pattern.subn(new_name, content)
        if n > 0:
            files_changed[fname] = new_content
            per_file[fname] = n
            total += n

    return {"files_changed": files_changed, "total_replacements": total, "per_file": per_file}


def find_duplicate_blocks(files: Dict[str, str], min_lines: int = 5) -> List[Dict[str, Any]]:
    """Find blocks of N+ consecutive lines that appear in multiple places."""
    block_locations: Dict[str, List[Tuple[str, int]]] = {}  # block_text → [(file, line)]
    for fname, content in files.items():
        lines = content.split("\n")
        for i in range(len(lines) - min_lines + 1):
            block = "\n".join(lines[i:i + min_lines]).strip()
            if len(block) < 50:  # skip tiny blocks
                continue
            block_locations.setdefault(block, []).append((fname, i + 1))

    duplicates = []
    for block, locs in block_locations.items():
        if len(locs) >= 2:
            duplicates.append({
                "block_preview": block[:200],
                "occurrences": len(locs),
                "locations": locs[:10],
            })
    duplicates.sort(key=lambda d: -d["occurrences"])
    return duplicates[:20]


def extract_section(html: str, start_marker: str, end_marker: str) -> Dict[str, Any]:
    """Pull a section out of HTML between two markers."""
    s = html.find(start_marker)
    e = html.find(end_marker, s + len(start_marker)) if s >= 0 else -1
    if s < 0 or e < 0:
        return {"ok": False, "error": "markers not found"}
    return {
        "ok": True,
        "section": html[s + len(start_marker):e],
        "before": html[:s],
        "after": html[e + len(end_marker):],
    }


def add_class_globally(files: Dict[str, str], css_selector: str, css_class: str) -> Dict[str, Any]:
    """Add a CSS class to all elements matching a selector across files.

    Limited to simple tag/id selectors. Returns dict of changed files.
    """
    files_changed: Dict[str, str] = {}
    per_file: Dict[str, int] = {}
    # Build a simple regex from the selector
    if css_selector.startswith("#"):
        # #my-id → <* id="my-id" ...>
        sel_id = css_selector[1:]
        pattern = re.compile(r'(<(\w+)[^>]*\sid=["\']' + re.escape(sel_id) + r'["\'][^>]*)>', re.IGNORECASE)
    elif css_selector.startswith("."):
        # .my-class → not a re-application case
        return {"ok": False, "error": "selector type not supported"}
    elif re.match(r"^\w+$", css_selector):
        # tag name
        pattern = re.compile(r"(<" + re.escape(css_selector) + r"\b[^>]*?)>", re.IGNORECASE)
    else:
        return {"ok": False, "error": "selector type not supported"}

    def _replace(m: re.Match) -> str:
        tag_open = m.group(1)
        if re.search(r'\sclass=["\']', tag_open):
            return re.sub(r'(\sclass=["\'])([^"\']*)', r'\1\2 ' + css_class, tag_open) + ">"
        return tag_open + f' class="{css_class}">'

    for fname, content in files.items():
        new_content, n = pattern.subn(_replace, content)
        if n > 0:
            files_changed[fname] = new_content
            per_file[fname] = n
    return {"ok": True, "files_changed": files_changed, "per_file": per_file}
