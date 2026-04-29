"""Content section renderers — hero, about, gallery, testimonials, etc.
Generic content — not tied to any specific vertical."""
from typing import Dict, Any
from .renderer_helpers import _esc


def _section_hero(d: Dict[str, Any], theme: Dict[str, Any]) -> str:
    img = _esc(d.get("image", ""))
    layout = d.get("layout", "split")
    title = _esc(d.get("title", ""))
    sub = _esc(d.get("subtitle", ""))
    cta = _esc(d.get("cta_text", ""))
    link = _esc(d.get("cta_link", "#"))
    logo = theme.get("logo_url") or ""
    logo_html = f'<img src="{_esc(logo)}" class="brand-logo" alt="logo"/>' if logo else ""
    btn = f'<a href="{link}" class="btn btn-primary" data-hl="btn">{cta}</a>' if cta else ''
    if layout == "split":
        return f"""<section class="hero hero-split" id="hero" data-hl="hero"><div class="container"><div class="hero-copy">{logo_html}<h1 data-hl="h1">{title}</h1><p>{sub}</p>{btn}</div><div class="hero-media"><img src="{img}" alt=""/></div></div></section>"""
    if layout == "portrait":
        return f"""<section class="hero hero-portrait" id="hero" data-hl="hero" style="background-image:linear-gradient(180deg,rgba(0,0,0,.4),rgba(0,0,0,.8)),url('{img}')"><div class="container" style="text-align:center">{logo_html}<h1 data-hl="h1">{title}</h1><p>{sub}</p>{btn}</div></section>"""
    if layout == "centered":
        return f"""<section class="hero hero-centered" id="hero" data-hl="hero"><div class="container hero-centered-inner">{logo_html}<h1 data-hl="h1">{title}</h1><p>{sub}</p>{btn}<div class="hero-centered-media" style="background-image:url('{img}')"></div></div></section>"""
    if layout == "magazine":
        return f"""<section class="hero hero-magazine" id="hero" data-hl="hero"><div class="container mag-grid"><div class="mag-copy"><div class="mag-eyebrow">✦ مرحباً بكم</div>{logo_html}<h1 data-hl="h1">{title}</h1><div class="mag-divider"></div><p>{sub}</p>{btn}</div><div class="mag-frame"><img src="{img}" alt=""/><div class="mag-tag">EDITORIAL</div></div></div></section>"""
    if layout == "boxed":
        return f"""<section class="hero hero-boxed" id="hero" data-hl="hero" style="background-image:linear-gradient(rgba(0,0,0,.65),rgba(0,0,0,.9)),url('{img}')"><div class="hero-boxed-card">{logo_html}<h1 data-hl="h1">{title}</h1><p>{sub}</p>{btn}</div></section>"""
    if layout == "story":
        return f"""<section class="hero hero-story" id="hero" data-hl="hero"><div class="container"><div class="story-lead">{logo_html}<div class="story-tag">منذ 2010</div><h1 data-hl="h1">{title}</h1><p>{sub}</p>{btn}</div><div class="story-arrow">↓</div></div></section>"""
    if layout == "form":
        return f"""<section class="hero hero-form" id="hero" data-hl="hero" style="background-image:linear-gradient(rgba(0,0,0,.55),rgba(0,0,0,.85)),url('{img}')"><div class="container hero-form-grid"><div class="hero-form-copy">{logo_html}<h1 data-hl="h1">{title}</h1><p>{sub}</p></div><div class="hero-form-box"><h3>احجز الآن</h3><input placeholder="الاسم"/><input placeholder="رقم الجوال"/><input placeholder="التاريخ" type="date"/><button class="btn btn-primary" data-hl="btn">{cta or 'تأكيد'}</button></div></div></section>"""
    return f"""<section class="hero hero-full" id="hero" data-hl="hero" style="background-image:linear-gradient(rgba(0,0,0,.35),rgba(0,0,0,.7)),url('{img}')"><div class="container">{logo_html}<h1 data-hl="h1">{title}</h1><p>{sub}</p>{btn}</div></section>"""


def _section_features(d: Dict[str, Any], theme) -> str:
    items = d.get("items", [])
    layout = d.get("layout", "grid")
    if layout == "alt":
        rows = ""
        for idx, it in enumerate(items):
            side = "feat-alt-right" if idx % 2 else "feat-alt-left"
            rows += f"""<div class="feat-alt-row {side}"><div class="feat-alt-media"><div class="feat-alt-ico">{_esc(it.get('icon','✨'))}</div></div><div class="feat-alt-body"><div class="feat-alt-num">{idx+1:02d}</div><h3>{_esc(it.get('title',''))}</h3><p>{_esc(it.get('text',''))}</p></div></div>"""
        return f"""<section class="features features-alt" id="features" data-hl="features"><div class="container"><h2>{_esc(d.get('title',''))}</h2>{rows}</div></section>"""
    if layout == "horizontal":
        cards = "".join(f'<div class="feat-h"><div class="feat-h-ico">{_esc(i.get("icon","✨"))}</div><div><h3>{_esc(i.get("title",""))}</h3><p>{_esc(i.get("text",""))}</p></div></div>' for i in items)
        return f"""<section class="features features-h" id="features" data-hl="features"><div class="container"><h2>{_esc(d.get('title',''))}</h2><div class="feat-h-list">{cards}</div></div></section>"""
    cards = "".join(f"""<div class="feature-card"><div class="feature-icon">{_esc(i.get('icon',''))}</div><h3>{_esc(i.get('title',''))}</h3><p>{_esc(i.get('text',''))}</p></div>""" for i in items)
    return f"""<section class="features" id="features" data-hl="features"><div class="container"><h2>{_esc(d.get('title',''))}</h2><div class="feature-grid">{cards}</div></div></section>"""


def _section_story_timeline(d, theme) -> str:
    items = d.get("items", [])
    nodes = "".join(
        f'<div class="tl-node"><div class="tl-year">{_esc(i.get("year",""))}</div><div class="tl-dot"></div><div class="tl-body"><h4>{_esc(i.get("title",""))}</h4><p>{_esc(i.get("text",""))}</p></div></div>'
        for i in items
    ) or '<div class="tl-empty">اكتب قصتك هنا</div>'
    return f"""<section class="story-tl" id="story" data-hl="story"><div class="container"><h2>{_esc(d.get('title','قصتنا'))}</h2><div class="tl-line">{nodes}</div></div></section>"""


def _section_process_steps(d, theme) -> str:
    items = d.get("items", [])
    steps = "".join(
        f'<div class="ps-step"><div class="ps-num">{idx+1}</div><div class="ps-body"><h4>{_esc(i.get("title",""))}</h4><p>{_esc(i.get("text",""))}</p></div></div>{("<div class=ps-arrow>←</div>" if idx < len(items)-1 else "")}'
        for idx, i in enumerate(items)
    ) or '<div class="ps-empty">أضف خطوات</div>'
    return f"""<section class="process" id="process" data-hl="process"><div class="container"><h2>{_esc(d.get('title','كيف تطلب؟'))}</h2><div class="ps-list">{steps}</div></div></section>"""



def _section_quote(d, theme) -> str:
    return f"""<section class="quote-block" id="quote" data-hl="quote"><div class="container"><div class="quote-ico">"</div><blockquote>{_esc(d.get('text',''))}</blockquote><div class="quote-author">— {_esc(d.get('author',''))}{f", <span>{_esc(d.get('role',''))}</span>" if d.get('role') else ''}</div></div></section>"""


def _section_about(d, theme) -> str:
    stats_html = ""
    if d.get("stats"):
        stats_html = '<div class="stats-row">' + "".join(f'<div class="stat-item"><div class="stat-value">{_esc(s.get("value"))}</div><div class="stat-label">{_esc(s.get("label"))}</div></div>' for s in d["stats"]) + '</div>'
    img_html = f'<div class="about-media"><img src="{_esc(d.get("image"))}" alt=""/></div>' if d.get("image") else ''
    return f"""<section class="about" id="about" data-hl="about"><div class="container about-layout"><div class="about-copy"><h2>{_esc(d.get('title',''))}</h2><p>{_esc(d.get('text',''))}</p>{stats_html}</div>{img_html}</div></section>"""



def _section_gallery(d, theme) -> str:
    style = d.get("style") or "grid"
    imgs = d.get("images", [])
    if style == "masonry":
        # Pinterest-style masonry via CSS columns
        cards = "".join(f"""<img src="{_esc(u)}" alt="" style="width:100%;display:block;border-radius:10px;margin-bottom:10px;break-inside:avoid"/>""" for u in imgs)
        return f"""<section class="gallery gallery-masonry" id="gallery" data-hl="gallery"><div class="container"><h2>{_esc(d.get('title',''))}</h2><div style="columns:3 300px;column-gap:12px">{cards}</div></div></section>"""
    if style == "strip":
        # Horizontal scroll strip
        cards = "".join(f"""<div style="flex:0 0 240px;aspect-ratio:3/4;background:#000 url('{_esc(u)}') center/cover;border-radius:14px;scroll-snap-align:start"></div>""" for u in imgs)
        return f"""<section class="gallery gallery-strip" id="gallery" data-hl="gallery"><div class="container"><h2>{_esc(d.get('title',''))}</h2><div style="display:flex;gap:14px;overflow-x:auto;padding:8px 4px;scroll-snap-type:x mandatory">{cards}</div></div></section>"""
    # default: grid (classic)
    cards = "".join(f"""<div class="gallery-item" style="background-image:url('{_esc(u)}')"></div>""" for u in imgs)
    return f"""<section class="gallery" id="gallery" data-hl="gallery"><div class="container"><h2>{_esc(d.get('title',''))}</h2><div class="gallery-grid">{cards}</div></div></section>"""


def _section_testimonials(d, theme) -> str:
    style = d.get("style") or "grid"
    items = d.get("items", [])
    if style == "carousel":
        cards = "".join(f"""<div class="testimonial-car-card"><div class="stars">{'★' * int(i.get('rating', 5))}</div><p>"{_esc(i.get('text',''))}"</p><div class="author">— {_esc(i.get('name',''))}</div></div>""" for i in items)
        return f"""<section class="testimonials testi-carousel" id="testimonials" data-hl="testimonials"><div class="container"><h2>{_esc(d.get('title',''))}</h2><div class="testi-strip">{cards}</div></div><style>.testi-strip{{display:flex;gap:20px;overflow-x:auto;padding:12px 4px;scroll-snap-type:x mandatory}}.testimonial-car-card{{flex:0 0 320px;background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.1);border-radius:14px;padding:20px;scroll-snap-align:start}}.testimonial-car-card .stars{{color:#FFD700;margin-bottom:10px}}.testimonial-car-card p{{line-height:1.7}}.testimonial-car-card .author{{opacity:.7;margin-top:10px;font-size:13px}}</style></section>"""
    if style == "quote-big":
        cards = "".join(f"""<blockquote style="background:rgba(255,255,255,.03);border-right:4px solid #FFD700;padding:24px;margin:12px 0;border-radius:12px;font-size:18px;line-height:1.8"><div style="color:#FFD700;font-size:32px;line-height:1">"</div>{_esc(i.get('text',''))}<div style="opacity:.7;margin-top:12px;font-size:14px">— {_esc(i.get('name',''))}</div></blockquote>""" for i in items)
        return f"""<section class="testimonials testi-quote" id="testimonials" data-hl="testimonials"><div class="container"><h2>{_esc(d.get('title',''))}</h2><div>{cards}</div></div></section>"""
    # default: grid (cards)
    cards = "".join(f"""<div class="testimonial-card"><div class="stars">{'★' * int(i.get('rating', 5))}</div><p>{_esc(i.get('text',''))}</p><div class="author">— {_esc(i.get('name',''))}</div></div>""" for i in items)
    return f"""<section class="testimonials" id="testimonials" data-hl="testimonials"><div class="container"><h2>{_esc(d.get('title',''))}</h2><div class="testimonials-grid">{cards}</div></div></section>"""


def _section_team(d, theme) -> str:
    style = d.get("style") or "grid"
    items = d.get("members", [])
    if style == "circles":
        cards = "".join(f"""<div style="text-align:center"><div style="width:140px;height:140px;border-radius:50%;background:#000 url('{_esc(i.get("image",""))}') center/cover;margin:0 auto 12px;border:3px solid rgba(255,255,255,.15)"></div><h3 style="margin:0;font-size:16px">{_esc(i.get('name',''))}</h3><p style="opacity:.7;font-size:13px;margin:4px 0 0">{_esc(i.get('role',''))}</p></div>""" for i in items)
        return f"""<section class="team team-circles" id="team" data-hl="team"><div class="container"><h2>{_esc(d.get('title',''))}</h2><div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:28px;padding:12px 0">{cards}</div></div></section>"""
    if style == "rows":
        cards = "".join(f"""<div style="display:flex;gap:16px;align-items:center;background:rgba(255,255,255,.03);border:1px solid rgba(255,255,255,.1);border-radius:14px;padding:14px;margin-bottom:12px"><div style="width:70px;height:70px;border-radius:50%;background:#000 url('{_esc(i.get("image",""))}') center/cover;flex-shrink:0"></div><div><h3 style="margin:0;font-size:17px">{_esc(i.get('name',''))}</h3><p style="opacity:.7;font-size:13px;margin:4px 0 0">{_esc(i.get('role',''))}</p></div></div>""" for i in items)
        return f"""<section class="team team-rows" id="team" data-hl="team"><div class="container"><h2>{_esc(d.get('title',''))}</h2><div>{cards}</div></div></section>"""
    # default: grid
    cards = "".join(f"""<div class="team-card"><div class="team-photo" style="background-image:url('{_esc(i.get("image",""))}')"></div><h3>{_esc(i.get('name',''))}</h3><p>{_esc(i.get('role',''))}</p></div>""" for i in items)
    return f"""<section class="team" id="team" data-hl="team"><div class="container"><h2>{_esc(d.get('title',''))}</h2><div class="team-grid">{cards}</div></div></section>"""



def _section_pricing(d, theme) -> str:
    style = d.get("style") or "cards"
    items = d.get("plans", [])
    if style == "table":
        # Comparison table — plans as columns, features as rows
        all_features = []
        for p in items:
            for f in (p.get("features") or []):
                if f not in all_features:
                    all_features.append(f)
        head = "<tr><th></th>" + "".join(f"""<th style="padding:14px;text-align:center;background:{'rgba(255,215,0,.1)' if p.get('featured') else 'rgba(255,255,255,.03)'}">{_esc(p.get('name',''))}<div style="font-size:26px;font-weight:900;color:#FFD700;margin-top:6px">{_esc(p.get('price',''))}<span style="font-size:12px;opacity:.6">ر.س</span></div></th>""" for p in items) + "</tr>"
        rows = ""
        for f in all_features:
            cells = "".join(f"""<td style="text-align:center;padding:10px">{'✓' if f in (p.get('features') or []) else '—'}</td>""" for p in items)
            rows += f"""<tr><td style="padding:10px 14px;opacity:.85;font-size:14px">{_esc(f)}</td>{cells}</tr>"""
        ctas = "<tr><td></td>" + "".join(f"""<td style="padding:14px;text-align:center"><button class="btn btn-primary" style="width:100%">{_esc(p.get('cta','اشترك'))}</button></td>""" for p in items) + "</tr>"
        return f"""<section class="pricing pricing-table" id="pricing" data-hl="pricing"><div class="container"><h2>{_esc(d.get('title',''))}</h2><div style="overflow-x:auto"><table style="width:100%;border-collapse:collapse;background:rgba(255,255,255,.02);border-radius:16px;overflow:hidden"><thead>{head}</thead><tbody>{rows}</tbody><tfoot>{ctas}</tfoot></table></div></div></section>"""
    if style == "minimal":
        cards = "".join(f"""<div style="padding:24px;border-bottom:1px solid rgba(255,255,255,.08);display:flex;justify-content:space-between;align-items:center;gap:16px"><div><h3 style="margin:0;font-size:18px">{_esc(p.get('name',''))}</h3><div style="opacity:.7;font-size:13px;margin-top:4px">{_esc((p.get('features') or [''])[0] if p.get('features') else '')}</div></div><div style="text-align:left"><div style="font-size:24px;font-weight:900;color:#FFD700">{_esc(p.get('price',''))} ر.س</div><button class="btn btn-primary" style="margin-top:6px;padding:6px 14px;font-size:12px">{_esc(p.get('cta','اشترك'))}</button></div></div>""" for p in items)
        return f"""<section class="pricing pricing-minimal" id="pricing" data-hl="pricing"><div class="container"><h2>{_esc(d.get('title',''))}</h2><div style="background:rgba(255,255,255,.02);border-radius:16px;overflow:hidden">{cards}</div></div></section>"""
    # default: cards
    cards = "".join(
        f"""<div class="pricing-card {'featured' if p.get('featured') else ''}">
          <h3>{_esc(p.get('name',''))}</h3>
          <div class="price"><span class="currency">ر.س</span> <span class="amount">{_esc(p.get('price',''))}</span> <span class="period">/ {_esc(p.get('period',''))}</span></div>
          <ul>{"".join(f'<li>{_esc(x)}</li>' for x in p.get('features',[]))}</ul>
          <button class="btn btn-primary">{_esc(p.get('cta','اشترك'))}</button>
        </div>"""
        for p in items
    )
    return f"""<section class="pricing" id="pricing" data-hl="pricing"><div class="container"><h2>{_esc(d.get('title',''))}</h2><div class="pricing-grid">{cards}</div></div></section>"""


def _section_faq(d, theme) -> str:
    items = d.get("items", [])
    cards = "".join(f"""<details class="faq-item"><summary>{_esc(i.get('q',''))}</summary><p>{_esc(i.get('a',''))}</p></details>""" for i in items)
    return f"""<section class="faq"><div class="container"><h2>{_esc(d.get('title',''))}</h2>{cards}</div></section>"""


def _section_contact(d, theme) -> str:
    return f"""<section class="contact" id="contact" data-hl="contact"><div class="container"><h2>{_esc(d.get('title','تواصل معنا'))}</h2><div class="contact-grid">
      <div class="contact-card"><div class="icon">📧</div><div>{_esc(d.get('email',''))}</div></div>
      <div class="contact-card"><div class="icon">📞</div><div>{_esc(d.get('phone',''))}</div></div>
      <div class="contact-card"><div class="icon">📍</div><div>{_esc(d.get('address',''))}</div></div>
      <div class="contact-card"><div class="icon">🕒</div><div>{_esc(d.get('hours',''))}</div></div>
    </div></div></section>"""


def _section_cta(d, theme) -> str:
    return f"""<section class="cta-band" id="cta" data-hl="cta"><div class="container"><h2>{_esc(d.get('title',''))}</h2><p>{_esc(d.get('subtitle',''))}</p><button class="btn btn-primary btn-lg" data-hl="btn">{_esc(d.get('cta_text','ابدأ'))}</button></div></section>"""


def _section_footer(d, theme) -> str:
    logo = theme.get("logo_url") or ""
    brand_html = f'<img src="{_esc(logo)}" class="footer-logo" alt="logo"/>' if logo else f'<div class="footer-brand">{_esc(d.get("brand",""))}</div>'
    # Payment methods strip (if configured in theme)
    pay_map = {"stripe":"💳 فيزا/ماستر","mada":"🏦 مدى","applepay":"📱 Apple Pay","stcpay":"💰 STC Pay","paypal":"🅿️ PayPal","cod":"💵 كاش","bank":"🏛️ تحويل"}
    methods = theme.get("payment_methods") or []
    pay_html = ""
    if methods:
        chips = "".join(f'<span class="pay-chip">{_esc(pay_map.get(m, m))}</span>' for m in methods if m != "none")
        if chips:
            pay_html = f'<div class="footer-pay" data-hl="payment"><div class="pay-label">وسائل الدفع المقبولة:</div><div class="pay-chips">{chips}</div></div>'
    return f"""<footer class="site-footer" data-hl="footer"><div class="container">{brand_html}{pay_html}<div class="footer-meta"><span>© 2026 — جميع الحقوق محفوظة</span><span>مدعوم من Zitex</span></div></div></footer>"""



def _section_video(d, theme) -> str:
    url = _esc(d.get("url", "https://www.youtube.com/embed/dQw4w9WgXcQ"))
    return f"""<section class="video-sec" id="video" data-hl="video"><div class="container"><h2>{_esc(d.get('title','شاهد قصتنا'))}</h2><div class="video-frame"><iframe src="{url}" frameborder="0" allow="autoplay; encrypted-media" allowfullscreen></iframe></div></div></section>"""


def _section_newsletter(d, theme) -> str:
    return f"""<section class="newsletter-sec" id="newsletter" data-hl="newsletter"><div class="container nl-inner"><div><h2>{_esc(d.get('title','اشترك في نشرتنا'))}</h2><p>{_esc(d.get('subtitle','خصومات حصرية وعروض أولاً'))}</p></div><form class="nl-form"><input type="email" placeholder="بريدك الإلكتروني"/><button class="btn btn-primary">اشترك</button></form></div></section>"""


def _section_stats_band(d, theme) -> str:
    items = d.get("items", [])
    cards = "".join(f'<div class="sb-item"><div class="sb-val">{_esc(i.get("value",""))}</div><div class="sb-lbl">{_esc(i.get("label",""))}</div></div>' for i in items)
    return f"""<section class="stats-band" id="stats_band" data-hl="stats_band"><div class="container"><h2>{_esc(d.get('title',''))}</h2><div class="sb-grid">{cards}</div></div></section>"""


def _section_stories(d, theme) -> str:
    """Stories row like WhatsApp/Snapchat — circular clickable rings with optional video/image."""
    p = theme.get("primary", "#FFD700")
    a = theme.get("accent", "#FF6B35")
    items = d.get("items") or []
    if not items:
        # Smart defaults so empty "stories" still looks alive
        items = [
            {"title": "جديدنا", "image": "https://images.unsplash.com/photo-1556742049-0cfed4f6a45d?w=300"},
            {"title": "عروض", "image": "https://images.unsplash.com/photo-1556740738-b6a63e27c4df?w=300"},
            {"title": "خلف الكواليس", "image": "https://images.unsplash.com/photo-1542282088-72c9c27ed0cd?w=300"},
            {"title": "قصص العملاء", "image": "https://images.unsplash.com/photo-1511367461989-f85a21fda167?w=300"},
            {"title": "فعاليات", "image": "https://images.unsplash.com/photo-1492684223066-81342ee5ff30?w=300"},
            {"title": "وصفات", "image": "https://images.unsplash.com/photo-1504674900247-0877df9cc836?w=300"},
        ]
    chips = []
    for it in items:
        img = _esc(it.get("image") or it.get("thumbnail") or it.get("cover") or "")
        vid = _esc(it.get("video") or it.get("url") or "")
        title = _esc(it.get("title") or "حالة")
        icon = _esc(it.get("icon") or "")
        style_bg = f"background-image:url('{img}')" if img else f"background:linear-gradient(135deg,{p},{a})"
        play_dot = '<span class="zx-st-play">▶</span>' if vid else ''
        ico_html = f'<span class="zx-st-ico">{icon}</span>' if (icon and not img) else ''
        chips.append(f'<div class="zx-st-item" data-video="{vid}"><div class="zx-st-ring"><div class="zx-st-thumb" style="{style_bg}">{ico_html}{play_dot}</div></div><div class="zx-st-lbl">{title}</div></div>')
    title_h = _esc(d.get("title") or "حالاتنا")
    subtitle = _esc(d.get("subtitle") or "اضغط على أي حالة لمشاهدتها")
    return f"""<section class="zx-stories" id="stories" data-hl="stories"><div class="container"><div class="zx-st-head"><h2>{title_h}</h2><p>{subtitle}</p></div><div class="zx-st-row">{''.join(chips)}</div></div></section>"""


def _section_banner(d, theme) -> str:
    """Full-width promo banner with CTA."""
    p = theme.get("primary", "#FFD700")
    a = theme.get("accent", "#FF6B35")
    title = _esc(d.get("title") or "عرض خاص — لا تفوّته")
    subtitle = _esc(d.get("subtitle") or d.get("text") or "استفد من العرض قبل انتهائه")
    cta = _esc(d.get("cta_text") or d.get("cta") or "اعرف المزيد")
    image = _esc(d.get("image") or "")
    bg_style = f"background-image:linear-gradient(90deg,rgba(0,0,0,.55),rgba(0,0,0,.25)),url('{image}');background-size:cover;background-position:center" if image else f"background:linear-gradient(135deg,{p},{a})"
    return f"""<section class="zx-banner" id="banner" data-hl="banner" style="{bg_style}"><div class="container zx-bn-inner"><div class="zx-bn-copy"><h2>{title}</h2><p>{subtitle}</p></div><a href="#" class="btn btn-primary zx-bn-cta">{cta}</a></div></section>"""


def _section_announce_bar(d, theme) -> str:
    """A dedicated announce bar as a section (sticky to top)."""
    txt = _esc(d.get("text") or d.get("title") or "🎉 عرض محدود — خصم حصري الآن")
    cta = _esc(d.get("cta_text") or "")
    cta_html = f' · <a href="#">{cta} ↗</a>' if cta else ""
    return f'<section class="zx-announce zx-announce-sec" id="announce_bar" data-hl="announce_bar">{txt}{cta_html}</section>'


def _section_map_embed(d, theme) -> str:
    """Interactive map embed using OpenStreetMap (no API key needed)."""
    title = _esc(d.get("title") or "موقعنا")
    address = _esc(d.get("address") or "")
    lat = float(d.get("lat") or 24.7136)
    lng = float(d.get("lng") or 46.6753)
    # OSM embed with marker
    bbox = f"{lng-0.01}%2C{lat-0.01}%2C{lng+0.01}%2C{lat+0.01}"
    osm_url = f"https://www.openstreetmap.org/export/embed.html?bbox={bbox}&layer=mapnik&marker={lat}%2C{lng}"
    return f"""<section class="zx-map" id="map_embed" data-hl="map"><div class="container"><div class="zx-map-head"><h2>{title}</h2>{("<p>"+address+"</p>") if address else ""}</div><div class="zx-map-frame"><iframe src="{osm_url}" loading="lazy" style="border:0" title="map"></iframe></div></div></section>"""


def _section_delivery_banner(d, theme) -> str:
    """Delivery-focused banner — shows the delivery promise prominently."""
    title = _esc(d.get("title") or "🛵 توصيل سريع")
    subtitle = _esc(d.get("subtitle") or "توصيل مجاني للطلبات فوق 100 ريال")
    cta = _esc(d.get("cta_text") or "اطلب الآن")
    return f"""<section class="zx-delivery" id="delivery_banner" data-hl="delivery"><div class="container zx-dl-inner"><div class="zx-dl-ico">🛵</div><div class="zx-dl-copy"><h3>{title}</h3><p>{subtitle}</p></div><a href="#" class="btn btn-primary zx-dl-cta">{cta}</a></div></section>"""



def _section_custom(d, theme) -> str:
    """🌐 Generic visible fallback for ANY AI-invented section type.
    Accepts flexible shape: {title, subtitle, layout (grid|list|row|card), items: [{icon, title, text, image, cta}], html}
    Guarantees the user SEES what was added, even if type is unknown.
    """
    # Raw HTML passthrough (trusted from AI directive — AI is the creator here)
    raw = d.get("html")
    if isinstance(raw, str) and raw.strip().startswith("<"):
        return f'<section class="zx-custom-raw" data-hl="custom">{raw}</section>'
    title = _esc(d.get("title") or d.get("name") or "قسم مخصّص")
    subtitle = _esc(d.get("subtitle") or d.get("description") or "")
    layout = str(d.get("layout") or "grid")
    items = d.get("items") or d.get("cards") or []
    if not items:
        # Show a visible placeholder so user knows section landed
        items = [{"icon": "✨", "title": title, "text": subtitle or "تمت إضافة هذا القسم — عدّل محتواه من لوحة التحكم."}]
    cards_html = []
    for it in items:
        if isinstance(it, str):
            it = {"title": it}
        icon = _esc(it.get("icon") or "")
        t = _esc(it.get("title") or "")
        txt = _esc(it.get("text") or it.get("description") or "")
        img = _esc(it.get("image") or "")
        cta = _esc(it.get("cta") or it.get("cta_text") or "")
        img_html = f'<div class="zx-cc-img" style="background-image:url(\'{img}\')"></div>' if img else ''
        ico_html = f'<div class="zx-cc-ico">{icon}</div>' if icon and not img else ''
        cta_html = f'<a class="zx-cc-cta" href="#">{cta} →</a>' if cta else ''
        cards_html.append(f'<div class="zx-cc-card">{img_html}{ico_html}<div class="zx-cc-body"><h3>{t}</h3><p>{txt}</p>{cta_html}</div></div>')
    return f'<section class="zx-custom zx-custom-{layout}" id="custom-{_esc(d.get("id","sec"))}" data-hl="custom"><div class="container"><div class="zx-cc-head"><h2>{title}</h2>{("<p>"+subtitle+"</p>") if subtitle else ""}</div><div class="zx-cc-grid zx-cc-{layout}">{"".join(cards_html)}</div></div></section>'


