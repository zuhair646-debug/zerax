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


def _find_bottom_nav(soup) -> Optional[Any]:
    """Heuristics to identify the 'bottom navigation' element.

    Order of preference:
      1. <nav> with class containing fixed+bottom (Tailwind)
      2. Element with class hint: bottom-nav, tab-bar, fab-menu, bottom-bar
      3. <nav> with inline `position:fixed;bottom:`
      4. The LAST <nav> in <body> (heuristic for mobile-style apps)
    """
    if not soup:
        return None
    body = soup.body or soup

    # Class-hint patterns
    class_hint = re.compile(
        r"(?:^|\s)(bottom[-_]?nav|tab[-_]?bar|fab[-_]?menu|bottom[-_]?bar|"
        r"mobile[-_]?nav|nav[-_]?bottom|footer[-_]?nav)(?:$|\s)",
        re.I,
    )
    for el in body.find_all(["nav", "div", "footer", "aside"]):
        classes = " ".join(el.get("class") or [])
        if class_hint.search(classes):
            return el
        # Tailwind fixed+bottom
        if "fixed" in classes and re.search(r"\bbottom-0?\b", classes):
            return el
        # Inline style fixed+bottom
        style = (el.get("style") or "").lower()
        if "position" in style and "fixed" in style and "bottom" in style:
            return el

    # Fallback: last <nav> in body
    navs = body.find_all("nav")
    if len(navs) >= 2:
        return navs[-1]
    return None


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
        "summary": (
            f"🎨 unified layout from '{src}' → "
            f"{len(updated)} pages patched, "
            f"{len(targets) - len(updated) - len(failed)} already in sync"
            + (f", {len(failed)} failed" if failed else "")
        ),
    }
