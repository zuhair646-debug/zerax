"""Widget customization system — every floating UI element can be customized:
- variant (appearance preset)
- position (anchor corner)
- offset_x / offset_y (fine nudge in px)
- hidden (toggle off entirely)

Styles are applied via a server-injected <style> block at the end of <body>
that overrides the original CSS in _floating_widgets() and related overlays.
"""
from __future__ import annotations
from typing import Any, Dict, List


# ------------------------------------------------------------------
# Widget registry — id → (target_css_id, name_ar, variants, applies_if)
# Each variant gives a CSS snippet that overrides size/background/shape.
# ------------------------------------------------------------------

# Default CSS anchors per position (right-to-left Arabic considered)
POSITIONS = {
    "top-left": "top:16px;left:16px;right:auto;bottom:auto;",
    "top-right": "top:16px;right:16px;left:auto;bottom:auto;",
    "bottom-left": "bottom:16px;left:16px;right:auto;top:auto;",
    "bottom-right": "bottom:16px;right:16px;left:auto;top:auto;",
    "middle-left": "top:50%;left:16px;right:auto;bottom:auto;transform:translateY(-50%);",
    "middle-right": "top:50%;right:16px;left:auto;bottom:auto;transform:translateY(-50%);",
}


def _base_fab(size: int, bg: str, fg: str, radius: str, border: str = "none") -> str:
    return (
        f"width:{size}px;height:{size}px;border-radius:{radius};"
        f"background:{bg};color:{fg};border:{border};"
        "display:flex;align-items:center;justify-content:center;cursor:pointer;"
        "box-shadow:0 8px 24px rgba(0,0,0,.35);font-weight:800;"
    )


# id → {selector, name, variants}
WIDGETS: Dict[str, Dict[str, Any]] = {
    "auth": {
        "selector": "#zx-auth-fab",
        "name_ar": "زر الحساب (👤)",
        "description_ar": "زر دخول/تسجيل المستخدم العائم",
        "default_pos": "top-left",
        "variants": {
            "classic": {"name_ar": "كلاسيكي (دائري)", "css": _base_fab(46, "rgba(0,0,0,.6)", "#fff", "50%", "2px solid rgba(255,255,255,.2)") + "backdrop-filter:blur(12px);font-size:20px;"},
            "pill": {"name_ar": "كبسولة", "css": "width:auto;height:42px;padding:0 18px;border-radius:24px;background:linear-gradient(135deg,#eab308,#f97316);color:#000;border:0;cursor:pointer;font-weight:900;font-size:14px;box-shadow:0 6px 18px rgba(234,179,8,.4);"},
            "square": {"name_ar": "مربع حاد", "css": _base_fab(42, "#000", "#fff", "8px", "1px solid rgba(255,255,255,.2)") + "font-size:18px;"},
            "minimal": {"name_ar": "بسيط شفاف", "css": _base_fab(36, "rgba(255,255,255,.08)", "#fff", "50%", "1px solid rgba(255,255,255,.15)") + "font-size:16px;backdrop-filter:blur(8px);"},
        },
    },
    "cart": {
        "selector": "#zx-cart-fab, .zx-cart-float",
        "name_ar": "سلة التسوق (🛒)",
        "description_ar": "زر السلة العائم مع عدد المنتجات",
        "default_pos": "bottom-right",
        "variants": {
            "classic": {"name_ar": "كلاسيكي دائري", "css": _base_fab(54, "linear-gradient(135deg,#f59e0b,#dc2626)", "#fff", "50%") + "font-size:22px;"},
            "pill": {"name_ar": "كبسولة ظاهرة", "css": "width:auto;height:48px;padding:0 22px;border-radius:28px;background:linear-gradient(90deg,#FFD700,#f97316);color:#000;border:0;cursor:pointer;font-weight:900;font-size:14px;box-shadow:0 6px 20px rgba(255,215,0,.45);display:flex;align-items:center;gap:8px;"},
            "square": {"name_ar": "مربع بسيط", "css": _base_fab(48, "#10b981", "#fff", "10px") + "font-size:20px;"},
            "minimal": {"name_ar": "شفاف", "css": _base_fab(44, "rgba(255,255,255,.08)", "#fff", "50%", "1px solid rgba(255,255,255,.15)") + "font-size:18px;backdrop-filter:blur(10px);"},
            "neon": {"name_ar": "نيون متوهّج", "css": _base_fab(52, "#000", "#00ff88", "50%", "2px solid #00ff88") + "font-size:22px;box-shadow:0 0 24px #00ff88,inset 0 0 12px rgba(0,255,136,.3);"},
        },
    },
    "portfolio": {
        "selector": "#zx-pf-fab",
        "name_ar": "المحفظة (📈)",
        "description_ar": "زر محفظة الأسهم للـstocks vertical",
        "default_pos": "top-left",
        "variants": {
            "classic": {"name_ar": "أزرق كلاسيكي", "css": _base_fab(46, "linear-gradient(135deg,#2563eb,#0891b2)", "#fff", "50%", "2px solid rgba(255,255,255,.2)") + "font-size:20px;"},
            "pill": {"name_ar": "كبسولة", "css": "width:auto;height:42px;padding:0 18px;border-radius:24px;background:linear-gradient(135deg,#2563eb,#0891b2);color:#fff;border:0;cursor:pointer;font-weight:900;font-size:14px;box-shadow:0 6px 18px rgba(37,99,235,.4);"},
            "bull": {"name_ar": "ثور (أخضر)", "css": _base_fab(48, "linear-gradient(135deg,#10b981,#065f46)", "#fff", "50%") + "font-size:22px;"},
            "minimal": {"name_ar": "مبسّط", "css": _base_fab(38, "#000", "#60a5fa", "50%", "1px solid #60a5fa") + "font-size:18px;"},
        },
    },
    "whatsapp": {
        "selector": ".zx-whatsapp",
        "name_ar": "واتساب (💬)",
        "description_ar": "زر تواصل مباشر عبر واتساب",
        "default_pos": "bottom-left",
        "variants": {
            "classic": {"name_ar": "أخضر كلاسيكي", "css": _base_fab(56, "#25D366", "#fff", "50%") + "font-size:28px;text-decoration:none;"},
            "pill": {"name_ar": "مع نص", "css": "width:auto;height:48px;padding:0 20px;border-radius:24px;background:#25D366;color:#fff;border:0;cursor:pointer;font-weight:900;font-size:14px;text-decoration:none;display:inline-flex;align-items:center;gap:8px;box-shadow:0 6px 18px rgba(37,211,102,.45);"},
            "square": {"name_ar": "مربع حاد", "css": _base_fab(48, "#25D366", "#fff", "10px") + "font-size:24px;text-decoration:none;"},
            "minimal": {"name_ar": "بسيط", "css": _base_fab(42, "rgba(37,211,102,.15)", "#25D366", "50%", "1px solid #25D366") + "font-size:20px;text-decoration:none;"},
        },
    },
    "scroll_top": {
        "selector": ".zx-scroll-top",
        "name_ar": "العودة للأعلى (⬆)",
        "description_ar": "زر الصعود السريع لأعلى الصفحة",
        "default_pos": "bottom-right",
        "variants": {
            "classic": {"name_ar": "دائري", "css": _base_fab(44, "rgba(0,0,0,.7)", "#fff", "50%", "1px solid rgba(255,255,255,.2)") + "font-size:18px;"},
            "pill": {"name_ar": "كبسولة", "css": "width:auto;height:36px;padding:0 14px;border-radius:18px;background:#000;color:#fff;border:0;cursor:pointer;font-size:13px;"},
            "minimal": {"name_ar": "بسيط", "css": _base_fab(36, "transparent", "#fff", "50%", "1px solid #fff") + "font-size:16px;"},
        },
    },
    "book_float": {
        "selector": ".zx-book-float",
        "name_ar": "زر الحجز (📅)",
        "description_ar": "زر احجز موعد سريع للصالونات والعيادات",
        "default_pos": "bottom-right",
        "variants": {
            "classic": {"name_ar": "كبسولة ذهبية", "css": "width:auto;height:48px;padding:0 22px;border-radius:28px;background:linear-gradient(90deg,#FFD700,#f97316);color:#000;border:0;cursor:pointer;font-weight:900;font-size:14px;box-shadow:0 6px 20px rgba(255,215,0,.45);"},
            "square": {"name_ar": "مربع", "css": "width:auto;height:44px;padding:0 18px;border-radius:10px;background:#7c3aed;color:#fff;border:0;font-weight:900;font-size:14px;cursor:pointer;"},
            "minimal": {"name_ar": "إطار", "css": "width:auto;height:40px;padding:0 18px;border-radius:24px;background:transparent;color:#fff;border:2px solid #fff;font-weight:900;font-size:13px;cursor:pointer;"},
        },
    },
    "announce_bar": {
        "selector": ".zx-announce",
        "name_ar": "شريط الإعلانات",
        "description_ar": "الشريط العلوي للعروض",
        "default_pos": "top",
        "supports_position": False,
        "variants": {
            "classic": {"name_ar": "متدرج ذهبي", "css": "background:linear-gradient(90deg,#FFD700,#f97316);color:#000;font-weight:900;"},
            "dark": {"name_ar": "داكن", "css": "background:#000;color:#FFD700;font-weight:800;border-bottom:1px solid rgba(255,215,0,.3);"},
            "minimal": {"name_ar": "بسيط", "css": "background:rgba(255,255,255,.05);color:#fff;border-bottom:1px solid rgba(255,255,255,.1);"},
            "festive": {"name_ar": "احتفالي", "css": "background:linear-gradient(90deg,#ef4444,#dc2626,#7c3aed);color:#fff;font-weight:900;animation:zx-gradient 8s ease infinite;background-size:200% 200%;"},
        },
    },
}


def catalog() -> List[Dict[str, Any]]:
    """Safe list for the frontend customizer UI."""
    out = []
    for wid, w in WIDGETS.items():
        out.append({
            "id": wid,
            "name_ar": w["name_ar"],
            "description_ar": w["description_ar"],
            "default_pos": w["default_pos"],
            "supports_position": w.get("supports_position", True),
            "variants": [{"id": vid, "name_ar": v["name_ar"]} for vid, v in w["variants"].items()],
        })
    return out


def get_styles_css(project: Dict[str, Any]) -> str:
    """Generate a <style> block that overrides every widget per project.widget_styles.

    Example project.widget_styles = {
        "cart": {"variant": "pill", "position": "bottom-right", "offset_x": 8, "offset_y": 0, "hidden": false},
        "auth": {"variant": "minimal", "position": "top-right"},
    }
    """
    ws = project.get("widget_styles") or {}
    if not ws:
        return ""
    out = ["<style>"]
    # Small gradient keyframes for festive variants
    out.append("@keyframes zx-gradient{0%{background-position:0% 50%}50%{background-position:100% 50%}100%{background-position:0% 50%}}")
    for wid, cfg in ws.items():
        w = WIDGETS.get(wid)
        if not w:
            continue
        sel = w["selector"]
        if cfg.get("hidden"):
            out.append(f"{sel}{{display:none !important;}}")
            continue
        variant_id = cfg.get("variant")
        v = w["variants"].get(variant_id)
        if v and v.get("css"):
            out.append(f"{sel}{{{v['css']}}}")
        if w.get("supports_position", True):
            pos = cfg.get("position") or w["default_pos"]
            pos_css = POSITIONS.get(pos)
            if pos_css:
                ox = int(cfg.get("offset_x") or 0)
                oy = int(cfg.get("offset_y") or 0)
                # nudge: we add margin on the anchor direction
                margin = f"margin:{oy}px 0 0 {ox}px;" if ox or oy else ""
                out.append(f"{sel}{{{pos_css}{margin}}}")
    out.append("</style>")
    return "".join(out)
