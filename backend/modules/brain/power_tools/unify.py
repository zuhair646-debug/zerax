"""Layout Unifier — forces visual consistency across multi-page projects.

Solves the recurring complaint: "AI creates separate pages with different
nav/footer/bottom-bar styles". This tool extracts the canonical layout shell
(head styles, top nav, bottom nav, footer) from one source page and forcibly
applies it to every other page.

Public API:
  • unify_pages_layout(pages_dict, source_page='index.html', sections=...)
      → {ok, updated, source, report}

  • extract_layout_shell(html) → {head_styles, top_nav, bottom_nav, footer, theme_classes}

  • inject_layout_shell(target_html, shell) → patched_html
"""
import re
from typing import Any, Dict, List, Optional


DEFAULT_SECTIONS = ("head_styles", "top_nav", "bottom_nav", "footer", "body_classes")


def _safe_bs4(html: str):
    """Lazy import + parse with BeautifulSoup. Returns soup or None."""
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        return None
    try:
        return BeautifulSoup(html, "html.parser")
    except Exception:
        return None


def _find_all_bottom_navs(soup) -> List[Any]:
    """Find ALL elements that look like bottom navigation. Used for dedup."""
    if not soup:
        return []
    body = soup.body or soup
    found: List[Any] = []
    class_hint = re.compile(
        r"(?:^|\s)(bottom[-_]?nav|tab[-_]?bar|fab[-_]?menu|bottom[-_]?bar|"
        r"mobile[-_]?nav|nav[-_]?bottom|footer[-_]?nav)(?:$|\s)",
        re.I,
    )
    for el in body.find_all(["nav", "div", "footer", "aside"]):
        # Skip if nested inside an already-found one
        if any(el in f.descendants for f in found):
            continue
        classes = " ".join(el.get("class") or [])
        if class_hint.search(classes):
            found.append(el)
            continue
        if "fixed" in classes and re.search(r"\bbottom-0?\b", classes):
            found.append(el)
            continue
        style = (el.get("style") or "").lower()
        if "position" in style and "fixed" in style and "bottom" in style:
            found.append(el)
    return found


def _pick_canonical_bottom_nav(candidates: List[Any]) -> Optional[Any]:
    """Pick the BEST bottom-nav from multiple candidates.

    Scoring (highest wins):
      • +10 if has anchors with href to .html files (functional nav)
      • +1 per anchor link
      • +5 if uses 'fixed bottom-0' Tailwind (the modern pattern)
      • +3 if longer (more complete)
    """
    if not candidates:
        return None
    if len(candidates) == 1:
        return candidates[0]

    def score(el):
        s = 0
        anchors = el.find_all("a", href=True)
        html_links = [a for a in anchors if ".html" in a.get("href", "")]
        if html_links:
            s += 10
        s += len(anchors)
        classes = " ".join(el.get("class") or [])
        if "fixed" in classes and "bottom-0" in classes:
            s += 5
        s += min(len(str(el)) // 200, 5)
        return s

    return max(candidates, key=score)


def _find_bottom_nav(soup) -> Optional[Any]:
    """Heuristics to identify the 'bottom navigation' element.

    Now uses scoring across all candidates rather than first-match, so when
    a page has BOTH `<div fixed bottom-0>` AND a `<nav class="bottom-nav">`,
    we pick the most functional one (most nav links, most modern).
    """
    candidates = _find_all_bottom_navs(soup)
    if not candidates:
        # Fallback: last <nav> in body of multi-nav pages
        if soup and (soup.body or soup):
            navs = (soup.body or soup).find_all("nav")
            if len(navs) >= 2:
                return navs[-1]
        return None
    return _pick_canonical_bottom_nav(candidates)


def _dedupe_bottom_navs_in_place(soup) -> int:
    """Remove duplicate bottom-nav elements. Keeps the canonical one.

    Returns the number of duplicates removed.
    """
    candidates = _find_all_bottom_navs(soup)
    if len(candidates) < 2:
        return 0
    canonical = _pick_canonical_bottom_nav(candidates)
    removed = 0
    for el in candidates:
        if el is not canonical:
            try:
                el.decompose()
                removed += 1
            except Exception:
                pass
    return removed



def _rewrite_anchor_links_to_pages(soup, available_pages: List[str]) -> int:
    """Convert `#anchor` hrefs to `anchor.html` when that page exists.

    Solves the bug: bottom-nav uses #delivery #contests #cart anchors from
    the original single-page version, but the project is now multi-page —
    so those anchors don't navigate anywhere on sub-pages.

    Returns count of rewritten links.
    """
    if not soup or not available_pages:
        return 0
    # Build map: 'delivery' → 'delivery.html' for fast lookup
    stem_to_file = {}
    for fn in available_pages:
        if fn.endswith(".html"):
            stem = fn[:-5].lower()
            stem_to_file[stem] = fn
            stem_to_file[stem + "-section"] = fn
            stem_to_file["section-" + stem] = fn
    rewrites = 0
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if not href.startswith("#"):
            continue
        target_stem = href[1:].lower()
        target_file = stem_to_file.get(target_stem)
        if target_file:
            a["href"] = target_file
            rewrites += 1
    return rewrites



def _find_top_nav(soup) -> Optional[Any]:
    """Identify the top-of-page navigation.

    Order:
      1. <header> element (most semantic)
      2. First <nav> that's NOT the bottom nav
      3. Element with class .top-nav / .main-nav / .site-header
    """
    if not soup:
        return None
    body = soup.body or soup

    header = body.find("header")
    if header:
        return header

    bottom = _find_bottom_nav(soup)
    for nav in body.find_all("nav"):
        if nav is not bottom:
            return nav

    class_hint = re.compile(
        r"(?:^|\s)(top[-_]?nav|main[-_]?nav|site[-_]?header|navbar)(?:$|\s)",
        re.I,
    )
    for el in body.find_all(["div", "section"]):
        classes = " ".join(el.get("class") or [])
        if class_hint.search(classes):
            return el
    return None


def _find_footer(soup, bottom_nav) -> Optional[Any]:
    """Find the page footer. Skip if it IS the bottom_nav."""
    if not soup:
        return None
    body = soup.body or soup
    for el in body.find_all("footer"):
        if el is not bottom_nav:
            return el
    return None


def extract_layout_shell(html: str) -> Dict[str, Any]:
    """Pull the canonical layout pieces out of an HTML document.

    Returns:
      {
        ok: bool,
        head_styles: "<style>...</style><link rel=stylesheet...>" (all style/font/cdn refs)
        head_scripts_cdn: "<script src='cdn...'>...</script>" (Tailwind, Font Awesome, etc.)
        body_classes: list[str] (the <body class="..."> classes)
        body_attrs: dict (dir, lang, data-theme)
        top_nav_html: str | None
        bottom_nav_html: str | None
        footer_html: str | None
        theme_lang: str (rtl/ltr)
        theme_dir: str
      }
    """
    soup = _safe_bs4(html)
    if not soup:
        return {"ok": False, "error": "BeautifulSoup parse failed"}

    head = soup.head
    body = soup.body

    # ── HEAD: collect all <style>, <link rel="stylesheet">, <script src=cdn>
    head_style_html = ""
    head_cdn_html = ""
    if head:
        styles = []
        cdns = []
        for tag in head.find_all(["style", "link", "script"]):
            outer = str(tag)
            if tag.name == "style":
                styles.append(outer)
            elif tag.name == "link" and (tag.get("rel") or []) and \
                    any(r in ("stylesheet", "preconnect", "preload", "icon", "shortcut icon")
                        for r in (tag.get("rel") or [])):
                styles.append(outer)
            elif tag.name == "script" and tag.get("src"):
                src = tag.get("src", "").lower()
                if any(h in src for h in ("cdn.", "cloudflare", "googleapis",
                                              "jsdelivr", "unpkg", "fontawesome")):
                    cdns.append(outer)
        head_style_html = "\n".join(styles)
        head_cdn_html = "\n".join(cdns)

    # ── BODY attributes
    body_classes = []
    body_attrs = {}
    if body:
        body_classes = list(body.get("class") or [])
        for k in ("dir", "lang", "data-theme", "data-mode"):
            v = body.get(k)
            if v:
                body_attrs[k] = v

    html_root = soup.find("html")
    theme_dir = ""
    theme_lang = ""
    if html_root:
        theme_dir = html_root.get("dir", "") or ""
        theme_lang = html_root.get("lang", "") or ""

    # ── Nav / Footer extraction
    bottom_nav = _find_bottom_nav(soup)
    top_nav = _find_top_nav(soup)
    footer = _find_footer(soup, bottom_nav)

    return {
        "ok": True,
        "head_styles": head_style_html,
        "head_cdn": head_cdn_html,
        "body_classes": body_classes,
        "body_attrs": body_attrs,
        "theme_dir": theme_dir,
        "theme_lang": theme_lang,
        "top_nav_html": str(top_nav) if top_nav else None,
        "bottom_nav_html": str(bottom_nav) if bottom_nav else None,
        "footer_html": str(footer) if footer else None,
        "has_top_nav": bool(top_nav),
        "has_bottom_nav": bool(bottom_nav),
        "has_footer": bool(footer),
    }


def inject_layout_shell(
    target_html: str,
    shell: Dict[str, Any],
    sections: tuple = DEFAULT_SECTIONS,
    preserve_title: bool = True,
) -> Dict[str, Any]:
    """Apply a layout shell to a target HTML doc.

    Replaces head styles + cdn, body classes, top nav, bottom nav, footer.
    Preserves the target page's <title> and main content.

    Returns: {ok, html, changes: [...], skipped: [...]}
    """
    soup = _safe_bs4(target_html)
    if not soup:
        return {"ok": False, "error": "target HTML parse failed"}

    changes: List[str] = []
    skipped: List[str] = []

    # ── HTML root: dir/lang sync
    html_root = soup.find("html")
    if html_root and "body_classes" in sections or "head_styles" in sections:
        if shell.get("theme_dir"):
            if html_root.get("dir") != shell["theme_dir"]:
                html_root["dir"] = shell["theme_dir"]
                changes.append("html[dir]")
        if shell.get("theme_lang"):
            if html_root.get("lang") != shell["theme_lang"]:
                html_root["lang"] = shell["theme_lang"]
                changes.append("html[lang]")

    # ── HEAD: replace styles + cdn (preserve title)
    if "head_styles" in sections:
        head = soup.head
        if head is None:
            head = soup.new_tag("head")
            if html_root:
                html_root.insert(0, head)

        target_title = None
        if preserve_title:
            t = head.find("title")
            if t:
                target_title = t.get_text(strip=True)

        # Remove old style/link/cdn-script tags
        for tag in list(head.find_all(["style", "link"])):
            tag.decompose()
        for s in list(head.find_all("script")):
            if s.get("src", "").lower().startswith(("http", "//")):
                src = s.get("src", "").lower()
                if any(h in src for h in ("cdn.", "cloudflare", "googleapis",
                                              "jsdelivr", "unpkg", "fontawesome")):
                    s.decompose()

        # Inject new styles + cdn from shell
        injected_html = (shell.get("head_cdn") or "") + "\n" + (shell.get("head_styles") or "")
        if injected_html.strip():
            from bs4 import BeautifulSoup
            new_frag = BeautifulSoup(injected_html, "html.parser")
            for el in list(new_frag.contents):
                if getattr(el, "name", None) is not None:
                    head.append(el)

        # Re-ensure <title> (preserve target's original)
        if preserve_title and target_title and not head.find("title"):
            t = soup.new_tag("title")
            t.string = target_title
            head.insert(0, t)

        changes.append("head_styles+cdn")

    # ── BODY classes + attrs
    body = soup.body
    if body and "body_classes" in sections:
        if shell.get("body_classes"):
            body["class"] = list(shell["body_classes"])
            changes.append("body[class]")
        for k, v in (shell.get("body_attrs") or {}).items():
            if body.get(k) != v:
                body[k] = v
                changes.append(f"body[{k}]")

    # ── TOP NAV
    if "top_nav" in sections and shell.get("top_nav_html"):
        from bs4 import BeautifulSoup
        new_nav = BeautifulSoup(shell["top_nav_html"], "html.parser")
        new_nav_el = new_nav.find(["header", "nav", "div"])
        if new_nav_el:
            existing = _find_top_nav(soup)
            if existing:
                existing.replace_with(new_nav_el)
                changes.append("top_nav (replaced)")
            elif body:
                body.insert(0, new_nav_el)
                changes.append("top_nav (inserted)")

    # ── BOTTOM NAV
    if "bottom_nav" in sections and shell.get("bottom_nav_html"):
        from bs4 import BeautifulSoup
        new_bn = BeautifulSoup(shell["bottom_nav_html"], "html.parser")
        new_bn_el = new_bn.find(["nav", "div", "footer", "aside"])
        if new_bn_el:
            existing = _find_bottom_nav(soup)
            if existing:
                existing.replace_with(new_bn_el)
                changes.append("bottom_nav (replaced)")
            elif body:
                body.append(new_bn_el)
                changes.append("bottom_nav (inserted)")

    # ── FOOTER
    if "footer" in sections and shell.get("footer_html"):
        from bs4 import BeautifulSoup
        new_ft = BeautifulSoup(shell["footer_html"], "html.parser")
        new_ft_el = new_ft.find("footer")
        if new_ft_el:
            bn = _find_bottom_nav(soup)
            existing = _find_footer(soup, bn)
            if existing:
                existing.replace_with(new_ft_el)
                changes.append("footer (replaced)")
            elif body:
                # Insert before bottom_nav if present, else append
                if bn:
                    bn.insert_before(new_ft_el)
                else:
                    body.append(new_ft_el)
                changes.append("footer (inserted)")

    return {
        "ok": True,
        "html": str(soup),
        "changes": changes,
        "skipped": skipped,
        "byte_size": len(str(soup)),
    }


def unify_pages_layout(
    pages_dict: Dict[str, str],
    source_page: str = "index.html",
    sections: Optional[List[str]] = None,
    target_pages: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Force layout consistency across multi-page projects.

    Args:
      pages_dict: {"index.html": "<html>...", "delivery.html": "...", ...}
      source_page: which page's layout is the "canonical" one
      sections: which layout pieces to sync (default: all)
      target_pages: which pages to update (default: all except source)

    Returns:
      {ok, source, updated, report}
      updated: {filename: patched_html}
      report: [{filename, changes, byte_delta}]
    """
    if not pages_dict:
        return {"ok": False, "error": "no pages provided"}

    src = (source_page or "index.html").strip().lower()
    if src not in pages_dict:
        return {"ok": False,
                 "error": f"source page '{src}' not in project",
                 "available": list(pages_dict.keys())}

    sections_t = tuple(sections) if sections else DEFAULT_SECTIONS

    source_html = pages_dict[src]

    # 🆕 STEP 0: Rewrite anchor links (#delivery) → file links (delivery.html)
    # in BOTH source and all target pages. This solves the recurring bug
    # where bottom-nav uses #anchor from the single-page era but the
    # project is now multi-page.
    available = list(pages_dict.keys())
    total_anchor_rewrites = 0
    pages_with_anchor_rewrites: List[str] = []
    for fn in list(pages_dict.keys()):
        s = _safe_bs4(pages_dict[fn])
        if s:
            n = _rewrite_anchor_links_to_pages(s, available)
            if n > 0:
                pages_dict[fn] = str(s)
                total_anchor_rewrites += n
                pages_with_anchor_rewrites.append(fn)
    source_html = pages_dict[src]

    # 🆕 STEP 1: Dedupe ALL bottom-nav duplicates in the SOURCE first.
    # If index.html has BOTH `<nav class="bottom-nav">` AND `<div fixed
    # bottom-0>`, pick the canonical one and remove duplicates. This is
    # the #1 reason the homepage "looks different from sub-pages".
    src_soup = _safe_bs4(source_html)
    source_dedupes = 0
    if src_soup:
        source_dedupes = _dedupe_bottom_navs_in_place(src_soup)
        if source_dedupes > 0:
            source_html = str(src_soup)
            pages_dict[src] = source_html  # mutate in-place for downstream use

    shell = extract_layout_shell(source_html)
    if not shell.get("ok"):
        return {"ok": False, "error": "could not extract source layout",
                "detail": shell.get("error")}

    if not (shell.get("has_top_nav") or shell.get("has_bottom_nav")
            or shell.get("has_footer")):
        return {"ok": False,
                "error": ("source page has no extractable layout shell "
                          "(no <header>, <nav>, or <footer>). add layout to source first.")}

    targets = (target_pages or
               [p for p in pages_dict.keys()
                if p != src and p.endswith(".html")])
    targets = [t for t in targets if t in pages_dict]

    updated: Dict[str, str] = {}
    report: List[Dict[str, Any]] = []
    failed: List[Dict[str, Any]] = []

    # 🆕 If we deduped the source OR rewrote anchors in it, mark it as updated
    if source_dedupes > 0 or src in pages_with_anchor_rewrites:
        updated[src] = source_html
        changes_list = []
        if source_dedupes > 0:
            changes_list.append(f"removed_{source_dedupes}_duplicate_bottom_navs")
        if src in pages_with_anchor_rewrites:
            changes_list.append("rewrote_anchor_links")
        report.append({
            "filename": src,
            "changes": changes_list,
            "byte_delta": 0,  # we don't track delta from pre-rewrite size
            "new_byte_size": len(source_html),
        })

    for fn in targets:
        original = pages_dict[fn]
        original_size = len(original)
        result = inject_layout_shell(original, shell, sections=sections_t)
        if result.get("ok"):
            patched = result["html"]
            if patched != original:
                updated[fn] = patched
                report.append({
                    "filename": fn,
                    "changes": result.get("changes", []),
                    "byte_delta": len(patched) - original_size,
                    "new_byte_size": len(patched),
                })
            else:
                report.append({
                    "filename": fn,
                    "changes": [],
                    "byte_delta": 0,
                    "note": "already in sync",
                })
        else:
            failed.append({
                "filename": fn,
                "error": result.get("error"),
            })

    return {
        "ok": True,
        "source": src,
        "sections_synced": list(sections_t),
        "shell_summary": {
            "has_top_nav": shell["has_top_nav"],
            "has_bottom_nav": shell["has_bottom_nav"],
            "has_footer": shell["has_footer"],
            "theme_dir": shell["theme_dir"],
            "body_classes_count": len(shell["body_classes"]),
        },
        "updated": updated,
        "updated_count": len(updated),
        "unchanged_count": len(targets) - len(updated) - len(failed),
        "failed": failed,
        "report": report,
        "anchor_rewrites": total_anchor_rewrites,
        "source_dedupes": source_dedupes,
        "summary": (
            f"🎨 unified layout from '{src}' → "
            f"{len(updated)} pages patched, "
            f"{len(targets) - len(updated) - len(failed)} already in sync"
            + (f", {total_anchor_rewrites} anchor links fixed" if total_anchor_rewrites else "")
            + (f", {source_dedupes} source duplicates removed" if source_dedupes else "")
            + (f", {len(failed)} failed" if failed else "")
        ),
    }
