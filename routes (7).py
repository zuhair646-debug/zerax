"""Base CSS generator — large string template with theme placeholders."""
from typing import Dict, Any


def _base_css(theme: Dict[str, Any]) -> str:
    p = theme.get("primary", "#FFD700")
    s = theme.get("secondary", "#1a1f3a")
    a = theme.get("accent", "#FF6B35")
    bg = theme.get("background", "#0b0f1f")
    tx = theme.get("text", "#ffffff")
    font = theme.get("font", "Tajawal")
    radius_map = {"none": "0", "small": "6px", "medium": "12px", "large": "20px", "full": "999px"}
    r = radius_map.get(theme.get("radius", "medium"), "12px")
    return f"""
*{{margin:0;padding:0;box-sizing:border-box;font-family:{font},-apple-system,BlinkMacSystemFont,sans-serif}}
html{{scroll-behavior:smooth}}
body{{background:{bg};color:{tx};line-height:1.6;overflow-x:hidden}}
.container{{max-width:1200px;margin:0 auto;padding:0 24px}}
section{{padding:72px 0}}
h1{{font-size:clamp(32px,5vw,56px);font-weight:900;line-height:1.15;margin-bottom:18px}}
h2{{font-size:clamp(26px,3.5vw,40px);font-weight:800;margin-bottom:36px;text-align:center}}
h3{{font-size:22px;font-weight:700;margin-bottom:10px}}
p{{opacity:.88}}
img{{max-width:100%;display:block;border-radius:{r}}}
.btn{{display:inline-block;padding:12px 28px;border:0;border-radius:{r};font-weight:700;cursor:pointer;transition:all .25s;font-size:15px;font-family:inherit;text-decoration:none}}
.btn-primary{{background:{p};color:{s}}}
.btn-primary:hover{{transform:translateY(-2px);box-shadow:0 10px 30px {p}66}}
.btn-lg{{padding:16px 36px;font-size:17px}}
.btn-sm{{padding:8px 16px;font-size:13px}}

/* HERO */
.hero-split .container{{display:grid;grid-template-columns:1.1fr 1fr;gap:48px;align-items:center}}
.hero-split .hero-media img{{border-radius:{r};box-shadow:0 30px 80px rgba(0,0,0,.5)}}
.hero-full,.hero-portrait{{padding:120px 0;background-size:cover;background-position:center}}
.hero-full h1,.hero-portrait h1{{text-align:center}}

/* NEW HERO VARIANTS */
.hero-centered{{text-align:center;padding:80px 0}}
.hero-centered-inner{{max-width:800px;margin:0 auto}}
.hero-centered-media{{width:100%;height:320px;background-size:cover;background-position:center;border-radius:{r};margin-top:40px;box-shadow:0 40px 80px rgba(0,0,0,.4)}}
.hero-magazine{{padding:60px 0;background:linear-gradient(135deg,rgba(255,255,255,.02),rgba(255,255,255,.05))}}
.mag-grid{{display:grid;grid-template-columns:1fr 1fr;gap:60px;align-items:center}}
.mag-eyebrow{{font-size:12px;letter-spacing:4px;color:{p};margin-bottom:16px;text-transform:uppercase}}
.mag-divider{{width:60px;height:3px;background:{p};margin:20px 0}}
.mag-frame{{position:relative}}
.mag-frame img{{width:100%;border-radius:{r};filter:grayscale(.2)}}
.mag-tag{{position:absolute;top:-12px;right:-12px;background:{p};color:{s};padding:8px 14px;font-size:11px;letter-spacing:2px;font-weight:900;border-radius:4px}}
.hero-boxed{{min-height:90vh;display:flex;align-items:center;justify-content:center;background-size:cover;background-position:center}}
.hero-boxed-card{{background:rgba(255,255,255,.05);backdrop-filter:blur(20px);border:1px solid rgba(255,255,255,.15);padding:60px 50px;border-radius:{r};max-width:560px;text-align:center;box-shadow:0 40px 100px rgba(0,0,0,.6)}}
.hero-story{{padding:120px 0 80px;text-align:center}}
.story-lead{{max-width:720px;margin:0 auto}}
.story-tag{{display:inline-block;background:rgba(255,255,255,.08);padding:6px 20px;border-radius:99px;font-size:12px;letter-spacing:3px;margin-bottom:18px;color:{p}}}
.story-arrow{{margin-top:60px;font-size:32px;animation:bounce 2s infinite;color:{p}}}
@keyframes bounce{{0%,100%{{transform:translateY(0)}}50%{{transform:translateY(10px)}}}}
.hero-form{{padding:80px 0;background-size:cover;background-position:center;min-height:80vh;display:flex;align-items:center}}
.hero-form-grid{{display:grid;grid-template-columns:1.2fr 1fr;gap:48px;align-items:center}}
.hero-form-box{{background:rgba(0,0,0,.6);backdrop-filter:blur(16px);padding:32px;border-radius:{r};border:1px solid rgba(255,255,255,.1)}}
.hero-form-box h3{{margin-bottom:18px;color:{p}}}
.hero-form-box input{{width:100%;padding:12px 14px;background:rgba(255,255,255,.08);border:1px solid rgba(255,255,255,.1);border-radius:8px;color:#fff;margin-bottom:12px;font-family:inherit;box-sizing:border-box}}
.hero-form-box .btn-primary{{width:100%}}

/* Alt features */
.features-alt{{padding:80px 0}}
.feat-alt-row{{display:grid;grid-template-columns:1fr 1fr;gap:48px;align-items:center;margin-bottom:80px}}
.feat-alt-row.feat-alt-right{{direction:ltr}}
.feat-alt-media{{background:linear-gradient(135deg,{p}33,{a}33);border-radius:{r};padding:60px;text-align:center;aspect-ratio:4/3;display:flex;align-items:center;justify-content:center}}
.feat-alt-ico{{font-size:96px}}
.feat-alt-num{{font-size:14px;letter-spacing:4px;color:{p};font-weight:900;margin-bottom:14px}}
.feat-alt-body h3{{font-size:32px;margin-bottom:14px}}

/* Horizontal features */
.feat-h-list{{display:flex;flex-direction:column;gap:14px;max-width:820px;margin:0 auto}}
.feat-h{{display:grid;grid-template-columns:auto 1fr;gap:18px;background:rgba(255,255,255,.03);padding:20px;border-radius:{r};border:1px solid rgba(255,255,255,.06);transition:.2s}}
.feat-h:hover{{border-color:{p};transform:translateX(4px)}}
.feat-h-ico{{font-size:40px;width:60px;height:60px;display:flex;align-items:center;justify-content:center;background:{p}22;border-radius:{r}}}

/* Story Timeline */
.story-tl{{padding:80px 0;background:linear-gradient(135deg,rgba(255,255,255,.02),rgba(255,255,255,.05))}}
.tl-line{{position:relative;padding:40px 0}}
.tl-line::before{{content:'';position:absolute;right:120px;top:0;bottom:0;width:2px;background:linear-gradient(180deg,{p},{a});opacity:.3}}
.tl-node{{display:grid;grid-template-columns:100px 40px 1fr;gap:20px;margin-bottom:32px;align-items:start}}
.tl-year{{color:{p};font-size:28px;font-weight:900;text-align:left;padding-top:4px}}
.tl-dot{{width:16px;height:16px;border-radius:50%;background:{p};margin-top:10px;margin-right:auto;box-shadow:0 0 0 4px {p}33}}
.tl-body{{background:rgba(255,255,255,.03);padding:18px 20px;border-radius:{r};border-right:3px solid {p}}}
.tl-body h4{{margin:0 0 6px;font-size:17px}}
.tl-body p{{margin:0;font-size:14px;opacity:.8}}

/* Process Steps */
.process{{padding:80px 0}}
.ps-list{{display:flex;align-items:stretch;flex-wrap:wrap;gap:12px;justify-content:center}}
.ps-step{{background:rgba(255,255,255,.04);padding:24px;border-radius:{r};border:1px solid rgba(255,255,255,.08);min-width:200px;max-width:260px;flex:1;text-align:center}}
.ps-num{{width:48px;height:48px;border-radius:50%;background:linear-gradient(135deg,{p},{a});color:{s};display:flex;align-items:center;justify-content:center;font-weight:900;font-size:20px;margin:0 auto 14px}}
.ps-arrow{{display:flex;align-items:center;color:{p};font-size:28px;font-weight:900}}

/* Reservation */
.reservation{{padding:80px 0;background:linear-gradient(135deg,{p}11,{a}11)}}
.reservation-grid{{display:grid;grid-template-columns:1fr 1fr;gap:48px;align-items:center}}
.res-form{{background:rgba(255,255,255,.03);padding:28px;border-radius:{r};border:1px solid rgba(255,255,255,.1);display:flex;flex-direction:column;gap:14px}}
.res-row, .res-row-2{{display:flex;flex-direction:column;gap:6px}}
.res-row-2{{display:grid;grid-template-columns:1fr 1fr;gap:12px}}
.res-form label{{font-size:12px;opacity:.7}}
.res-form input, .res-form select{{background:rgba(0,0,0,.3);border:1px solid rgba(255,255,255,.1);color:#fff;padding:10px 12px;border-radius:8px;font-family:inherit}}
.res-form .btn-primary{{margin-top:10px}}

/* Quote block */
.quote-block{{padding:100px 0;text-align:center;background:linear-gradient(135deg,{p}22,{a}22)}}
.quote-ico{{font-size:80px;color:{p};line-height:.5;margin-bottom:-20px;opacity:.5}}
.quote-block blockquote{{font-size:28px;font-weight:300;font-style:italic;max-width:760px;margin:20px auto;line-height:1.6}}
.quote-author{{color:{p};font-weight:700;margin-top:20px}}
.quote-author span{{opacity:.7;font-weight:400}}

/* Highlight Pulse (for wizard scroll-to) */
[data-hl]{{transition:.3s}}
.zx-pulse{{animation:zxPulse 1.5s ease-out}}
@keyframes zxPulse{{
  0%{{box-shadow:0 0 0 0 {p}99, 0 0 0 0 {p}66}}
  50%{{box-shadow:0 0 0 14px {p}22, 0 0 40px 10px {p}44}}
  100%{{box-shadow:0 0 0 0 transparent}}
}}

@media (max-width:768px){{
  .mag-grid,.feat-alt-row,.reservation-grid,.hero-form-grid{{grid-template-columns:1fr}}
  .ps-list{{flex-direction:column}}
  .ps-arrow{{transform:rotate(-90deg)}}
  .tl-line::before{{right:30px}}
  .tl-node{{grid-template-columns:60px 30px 1fr}}
}}

/* VIDEO / NEWSLETTER / STATS_BAND */
.video-sec{{padding:60px 0;text-align:center}}
.video-frame{{max-width:880px;margin:20px auto;aspect-ratio:16/9;border-radius:{r};overflow:hidden;box-shadow:0 40px 80px rgba(0,0,0,.4);border:1px solid rgba(255,255,255,.08)}}
.video-frame iframe{{width:100%;height:100%;border:0}}
.newsletter-sec{{padding:60px 0;background:linear-gradient(135deg,{p}22,{a}22)}}
.nl-inner{{display:grid;grid-template-columns:1fr 1fr;gap:32px;align-items:center}}
.nl-form{{display:flex;gap:8px}}
.nl-form input{{flex:1;padding:14px 18px;background:rgba(255,255,255,.1);border:1px solid rgba(255,255,255,.15);border-radius:{r};color:inherit;font-family:inherit;font-size:14px}}
.stats-band{{padding:70px 0;background:linear-gradient(135deg,{p}22,{a}11);text-align:center}}
.sb-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:20px;margin-top:24px}}
.sb-item{{padding:20px;background:rgba(255,255,255,.04);border-radius:{r};border:1px solid rgba(255,255,255,.08)}}
.sb-val{{font-size:36px;font-weight:900;color:{p}}}
.sb-lbl{{font-size:13px;opacity:.75;margin-top:4px}}

/* 🆕 STORIES (WhatsApp/Snapchat-style) */
.zx-stories{{padding:36px 0 24px;background:linear-gradient(180deg,rgba(255,255,255,.02),transparent)}}
.zx-st-head{{margin-bottom:16px}}
.zx-st-head h2{{font-size:22px;margin:0}}
.zx-st-head p{{font-size:12px;opacity:.65;margin:4px 0 0}}
.zx-st-row{{display:flex;gap:14px;overflow-x:auto;padding:8px 2px 16px;scroll-snap-type:x mandatory}}
.zx-st-row::-webkit-scrollbar{{height:4px}}
.zx-st-row::-webkit-scrollbar-thumb{{background:{p}66;border-radius:99px}}
.zx-st-item{{flex:0 0 auto;text-align:center;scroll-snap-align:start;cursor:pointer;transition:.2s}}
.zx-st-item:hover{{transform:translateY(-3px)}}
.zx-st-ring{{width:74px;height:74px;border-radius:50%;padding:3px;background:conic-gradient(from 180deg,{p},{a},{p});box-shadow:0 6px 16px rgba(0,0,0,.3)}}
.zx-st-thumb{{width:100%;height:100%;border-radius:50%;background-size:cover;background-position:center;border:2.5px solid {bg};display:flex;align-items:center;justify-content:center;font-size:26px;position:relative}}
.zx-st-ico{{filter:drop-shadow(0 1px 2px rgba(0,0,0,.5))}}
.zx-st-play{{position:absolute;bottom:2px;right:2px;width:22px;height:22px;border-radius:50%;background:{p};color:{s};display:flex;align-items:center;justify-content:center;font-size:10px;font-weight:900;border:2px solid {bg}}}
.zx-st-lbl{{margin-top:6px;font-size:11px;font-weight:700;max-width:80px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}}

/* 🆕 BANNER */
.zx-banner{{padding:54px 0;margin:0;background-color:{p}22;position:relative;overflow:hidden}}
.zx-bn-inner{{display:flex;align-items:center;justify-content:space-between;gap:24px;flex-wrap:wrap}}
.zx-bn-copy h2{{font-size:28px;margin:0 0 6px;color:#fff;text-shadow:0 2px 8px rgba(0,0,0,.4)}}
.zx-bn-copy p{{margin:0;opacity:.92;color:#fff;max-width:620px}}
.zx-bn-cta{{white-space:nowrap;box-shadow:0 10px 24px rgba(0,0,0,.35)}}
.zx-announce-sec{{position:relative;display:block;text-align:center;padding:12px 16px;background:linear-gradient(90deg,{p},{a});color:{s};font-weight:700;font-size:14px}}
.zx-announce-sec a{{color:inherit;text-decoration:underline;margin-right:8px;font-weight:900}}

/* 🆕 CUSTOM (generic fallback — guarantees visibility) */
.zx-custom{{padding:64px 0}}
.zx-cc-head{{text-align:center;margin-bottom:28px}}
.zx-cc-head h2{{font-size:30px;margin:0 0 6px;background:linear-gradient(90deg,{p},{a});-webkit-background-clip:text;background-clip:text;color:transparent}}
.zx-cc-head p{{opacity:.72;margin:0;font-size:14px}}
.zx-cc-grid.zx-cc-grid,.zx-cc-grid{{display:grid;gap:18px}}
.zx-cc-grid.zx-cc-grid{{grid-template-columns:repeat(auto-fit,minmax(240px,1fr))}}
.zx-cc-grid.zx-cc-list{{grid-template-columns:1fr;max-width:760px;margin:0 auto}}
.zx-cc-grid.zx-cc-row{{display:flex;overflow-x:auto;gap:14px;padding-bottom:10px}}
.zx-cc-grid.zx-cc-row .zx-cc-card{{flex:0 0 260px}}
.zx-cc-card{{background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.08);border-radius:{r};overflow:hidden;transition:.25s;padding:0}}
.zx-cc-card:hover{{transform:translateY(-4px);border-color:{p}66;box-shadow:0 18px 40px rgba(0,0,0,.35)}}
.zx-cc-img{{aspect-ratio:16/10;background-size:cover;background-position:center;background-color:{p}22}}
.zx-cc-ico{{font-size:32px;padding:18px 18px 0}}
.zx-cc-body{{padding:16px 18px 18px}}
.zx-cc-body h3{{margin:0 0 6px;font-size:17px;color:{p}}}
.zx-cc-body p{{margin:0 0 10px;font-size:13.5px;opacity:.82;line-height:1.7}}
.zx-cc-cta{{display:inline-block;font-size:12.5px;font-weight:900;color:{p};text-decoration:none;margin-top:4px}}
.zx-custom-raw{{display:block}}

/* FLOATING WIDGETS */
.zx-announce{{position:sticky;top:0;left:0;right:0;background:linear-gradient(90deg,{p},{a});color:{s};padding:10px 16px;text-align:center;font-size:13px;font-weight:700;z-index:100}}
.zx-sticky-phone{{position:fixed;bottom:20px;left:20px;background:{p};color:{s};padding:12px 20px;border-radius:99px;font-weight:900;box-shadow:0 10px 30px rgba(0,0,0,.4);text-decoration:none;z-index:90;font-size:14px;animation:zxPop .4s}}
.zx-whatsapp{{position:fixed;bottom:20px;right:20px;width:56px;height:56px;border-radius:50%;background:#25D366;color:#fff;display:flex;align-items:center;justify-content:center;font-size:28px;text-decoration:none;box-shadow:0 10px 30px rgba(0,0,0,.4);z-index:90;animation:zxPop .4s}}
.zx-scroll-top{{position:fixed;bottom:90px;right:20px;width:42px;height:42px;border-radius:50%;background:rgba(255,255,255,.15);border:1px solid rgba(255,255,255,.2);color:#fff;cursor:pointer;font-size:18px;z-index:90}}
.zx-countdown{{position:fixed;top:20px;left:50%;transform:translateX(-50%);background:rgba(0,0,0,.85);color:{p};padding:10px 22px;border-radius:99px;font-weight:700;font-size:13px;z-index:95;border:1px solid {p}44}}
.zx-cd-val{{color:{p};font-family:monospace;margin-right:6px}}
.zx-rating{{position:fixed;top:80px;right:20px;background:rgba(255,255,255,.08);backdrop-filter:blur(10px);padding:10px 14px;border-radius:{r};border:1px solid rgba(255,255,255,.1);z-index:85;text-align:center}}
.zx-stars{{color:#fbbf24;font-size:16px}}
.zx-rtx{{font-size:11px;opacity:.75;margin-top:2px}}
.zx-social{{position:fixed;right:10px;top:50%;transform:translateY(-50%);display:flex;flex-direction:column;gap:8px;z-index:85}}
.zx-social a{{width:38px;height:38px;background:rgba(255,255,255,.1);border-radius:50%;display:flex;align-items:center;justify-content:center;text-decoration:none;font-size:18px;transition:.2s}}
.zx-social a:hover{{background:{p};transform:scale(1.1)}}
.zx-trust{{display:flex;gap:12px;justify-content:center;flex-wrap:wrap;padding:14px;background:rgba(255,255,255,.03);border-top:1px solid rgba(255,255,255,.06);border-bottom:1px solid rgba(255,255,255,.06)}}
.zx-trust span{{font-size:12px;padding:6px 12px;background:rgba(255,255,255,.06);border-radius:99px;font-weight:700}}
.zx-chat{{position:fixed;bottom:20px;right:20px;width:280px;background:rgba(14,20,40,.95);backdrop-filter:blur(16px);border:1px solid rgba(255,255,255,.15);border-radius:{r};z-index:95;overflow:hidden;animation:zxPop .4s}}
.zx-chat-head{{background:{p};color:{s};padding:10px 14px;font-weight:900;font-size:13px}}
.zx-chat-body{{padding:14px;font-size:13px}}

/* 🆕 MAP / DELIVERY / CART FLOAT / BOOK FLOAT */
.zx-map{{padding:60px 0}}
.zx-map-head{{text-align:center;margin-bottom:18px}}
.zx-map-head h2{{margin:0 0 4px;font-size:26px}}
.zx-map-head p{{margin:0;opacity:.7;font-size:13px}}
.zx-map-frame{{max-width:1040px;margin:0 auto;aspect-ratio:16/9;border-radius:{r};overflow:hidden;box-shadow:0 30px 70px rgba(0,0,0,.35);border:1px solid rgba(255,255,255,.08)}}
.zx-map-frame iframe{{width:100%;height:100%;filter:contrast(.95) brightness(.9)}}
.zx-delivery{{padding:28px 0;background:linear-gradient(90deg,{p}22,{a}22);border-top:1px solid rgba(255,255,255,.05);border-bottom:1px solid rgba(255,255,255,.05)}}
.zx-dl-inner{{display:flex;align-items:center;gap:16px;flex-wrap:wrap;justify-content:center}}
.zx-dl-ico{{font-size:46px;line-height:1}}
.zx-dl-copy{{flex:1;min-width:220px}}
.zx-dl-copy h3{{margin:0 0 2px;font-size:20px;color:{p}}}
.zx-dl-copy p{{margin:0;opacity:.85;font-size:13.5px}}
.zx-dl-cta{{white-space:nowrap}}
.zx-cart-float{{position:fixed;bottom:20px;left:86px;width:54px;height:54px;border-radius:50%;background:{p};color:{s};border:none;cursor:pointer;font-size:22px;box-shadow:0 10px 28px rgba(0,0,0,.4);z-index:90;animation:zxPop .4s;display:flex;align-items:center;justify-content:center}}
.zx-cart-count{{position:absolute;top:-4px;right:-4px;background:#EF4444;color:#fff;font-size:11px;width:20px;height:20px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-weight:900;border:2px solid {bg}}}
.zx-book-float{{position:fixed;top:80px;left:20px;background:{p};color:{s};padding:10px 18px;border-radius:99px;font-weight:900;font-size:13px;cursor:pointer;border:none;box-shadow:0 10px 28px rgba(0,0,0,.35);z-index:85;animation:zxPop .4s}}
@keyframes zxPop{{from{{opacity:0;transform:scale(.8)}}to{{opacity:1;transform:scale(1)}}}}
@media (max-width:768px){{
  .nl-inner{{grid-template-columns:1fr}}
  .zx-rating,.zx-social{{display:none}}
}}
.hero p{{font-size:18px;opacity:.85;margin-bottom:24px;max-width:560px}}

/* FEATURES */
.feature-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:24px}}
.feature-card{{background:rgba(255,255,255,.04);padding:28px;border-radius:{r};border:1px solid rgba(255,255,255,.06);transition:all .3s}}
.feature-card:hover{{transform:translateY(-4px);border-color:{p}}}
.feature-icon{{font-size:36px;margin-bottom:14px}}

/* ABOUT */
.about-layout{{display:grid;grid-template-columns:1.2fr 1fr;gap:48px;align-items:center}}
.stats-row{{display:flex;gap:32px;margin-top:28px;flex-wrap:wrap}}
.stat-value{{font-size:36px;font-weight:900;color:{p}}}
.stat-label{{opacity:.7;font-size:14px}}

/* PRODUCTS */
.product-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:22px}}
.product-card{{background:rgba(255,255,255,.04);border-radius:{r};overflow:hidden;transition:transform .3s;border:1px solid rgba(255,255,255,.06)}}
.product-card:hover{{transform:translateY(-6px)}}
.product-image{{aspect-ratio:1;background-size:cover;background-position:center;position:relative}}
.badge{{position:absolute;top:12px;right:12px;background:{a};color:white;padding:4px 10px;border-radius:20px;font-size:12px;font-weight:700}}
.product-body{{padding:16px}}
.price-row{{display:flex;align-items:center;gap:10px;margin:8px 0 14px}}
.price{{font-size:20px;font-weight:900;color:{p}}}
.old-price{{text-decoration:line-through;opacity:.5;font-size:14px}}

/* MENU */
.menu-cat{{margin-bottom:40px}}
.menu-cat h3{{color:{p};font-size:24px;margin-bottom:20px;border-bottom:2px solid {p}44;padding-bottom:8px}}
.menu-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:22px}}
.menu-item{{display:flex;gap:14px;background:rgba(255,255,255,.04);padding:14px;border-radius:{r}}}
.menu-item img{{width:96px;height:96px;object-fit:cover;flex:0 0 96px}}
.menu-row{{display:flex;justify-content:space-between;align-items:baseline;gap:8px}}
.menu-price{{color:{p};font-weight:900;font-size:18px}}

/* GALLERY */
.gallery-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:14px}}
.gallery-item{{aspect-ratio:1;background-size:cover;background-position:center;border-radius:{r};transition:transform .3s;cursor:pointer}}
.gallery-item:hover{{transform:scale(1.04)}}

/* TESTIMONIALS */
.testimonials-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:22px}}
.testimonial-card{{background:rgba(255,255,255,.04);padding:26px;border-radius:{r};border:1px solid rgba(255,255,255,.06)}}
.stars{{color:{p};font-size:18px;margin-bottom:10px}}
.author{{opacity:.7;margin-top:14px;font-weight:700}}

/* TEAM */
.team-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:22px}}
.team-card{{text-align:center}}
.team-photo{{aspect-ratio:1;background-size:cover;background-position:center;border-radius:50%;margin-bottom:12px;border:3px solid {p}}}

/* PRICING */
.pricing-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:22px}}
.pricing-card{{background:rgba(255,255,255,.04);padding:32px 24px;border-radius:{r};text-align:center;border:1px solid rgba(255,255,255,.08);transition:all .3s}}
.pricing-card.featured{{border-color:{p};box-shadow:0 20px 60px {p}22;transform:scale(1.04)}}
.pricing-card .price{{font-size:48px;font-weight:900;color:{p};margin:16px 0}}
.pricing-card .currency{{font-size:20px;opacity:.7}}
.pricing-card .period{{font-size:14px;opacity:.6}}
.pricing-card ul{{list-style:none;margin:20px 0;text-align:right}}
.pricing-card li{{padding:8px 0;border-bottom:1px solid rgba(255,255,255,.06)}}
.pricing-card li::before{{content:'✓ ';color:{p};font-weight:900}}

/* FAQ */
.faq-item{{background:rgba(255,255,255,.04);padding:18px 22px;border-radius:{r};margin-bottom:12px;cursor:pointer}}
.faq-item summary{{font-weight:700;font-size:16px;list-style:none}}
.faq-item summary::after{{content:'+';float:left;font-size:22px;color:{p}}}
.faq-item[open] summary::after{{content:'−'}}
.faq-item p{{margin-top:10px;opacity:.85}}

/* CONTACT */
.contact-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:16px}}
.contact-card{{background:rgba(255,255,255,.04);padding:22px;border-radius:{r};display:flex;gap:12px;align-items:center}}
.contact-card .icon{{font-size:26px;color:{p}}}

/* CTA band */
.cta-band{{background:linear-gradient(135deg,{p},{a});color:{s};text-align:center;padding:72px 0}}
.cta-band h2{{color:{s}}}
.cta-band p{{font-size:18px;margin-bottom:24px}}
.cta-band .btn-primary{{background:{s};color:{p}}}

/* FOOTER */
.site-footer{{background:rgba(0,0,0,.4);padding:32px 0;border-top:1px solid rgba(255,255,255,.08)}}
.site-footer .container{{display:flex;justify-content:space-between;flex-wrap:wrap;gap:16px}}
.footer-brand{{font-weight:900;color:{p}}}
.footer-meta{{display:flex;gap:20px;opacity:.6;font-size:13px}}
.footer-pay{{margin:14px 0 10px;padding:12px 0;border-top:1px solid rgba(255,255,255,.06);border-bottom:1px solid rgba(255,255,255,.06);display:flex;align-items:center;gap:12px;flex-wrap:wrap}}
.pay-label{{font-size:12px;opacity:.7;font-weight:700}}
.pay-chips{{display:flex;gap:6px;flex-wrap:wrap}}
.pay-chip{{font-size:12px;padding:5px 11px;background:rgba(255,255,255,.06);border:1px solid rgba(255,255,255,.1);border-radius:99px;font-weight:700}}

/* DASHBOARD */
.brand-logo{{max-width:140px;max-height:90px;margin-bottom:18px;display:block;object-fit:contain}}
.footer-logo{{max-width:120px;max-height:60px;object-fit:contain}}

/* Dashboard Pro Mode */
.dp-mode{{min-height:100vh;background:#0a0e1c;color:#fff;padding:0;border:none}}
.dp-topbar{{display:flex;justify-content:space-between;align-items:center;padding:14px 24px;background:linear-gradient(90deg,{p}22,{a}11);border-bottom:1px solid rgba(255,255,255,.1)}}
.dp-topbar-brand{{font-weight:900;font-size:18px;color:{p}}}
.dp-topbar-user{{background:rgba(255,255,255,.08);padding:6px 14px;border-radius:{r};font-size:13px}}
.dp-layout{{display:grid;grid-template-columns:240px 1fr;min-height:calc(100vh - 60px)}}
.dp-side{{background:#0e1428;padding:16px 12px;border-left:1px solid rgba(255,255,255,.06)}}
.dp-side-title{{font-size:11px;opacity:.5;margin-bottom:10px;padding:0 10px;text-transform:uppercase;letter-spacing:1px}}
.dp-nav-item{{display:flex;align-items:center;gap:12px;padding:10px 12px;border-radius:8px;cursor:pointer;margin-bottom:3px;transition:.2s;color:#fff;text-decoration:none}}
.dp-nav-item:hover{{background:{p}22;color:{p}}}
.dp-nav-ico{{font-size:18px;width:22px;display:inline-block;text-align:center}}
.dp-main{{padding:24px;overflow-y:auto}}
.dp-cards-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(520px,1fr));gap:18px;padding:24px}}
.dp-tabsbar{{display:flex;gap:4px;padding:8px 24px 0;overflow-x:auto;border-bottom:1px solid rgba(255,255,255,.08);background:#0e1428}}
.dp-tab{{padding:12px 18px;cursor:pointer;font-weight:700;white-space:nowrap;border-bottom:3px solid transparent;color:#fff;text-decoration:none;transition:.2s}}
.dp-tab:hover{{color:{p}}}
.dp-tab-on{{color:{p};border-bottom-color:{p};background:rgba(255,255,255,.03)}}
.dp-hint{{padding:60px 20px;text-align:center;font-size:15px;opacity:.6;background:repeating-linear-gradient(45deg,rgba(255,255,255,.02),rgba(255,255,255,.02) 10px,transparent 10px,transparent 20px);border-radius:{r};margin:24px}}
.dp-empty{{opacity:.5;text-align:center;padding:30px}}

/* Panels */
.dp-panel{{background:#11182c;border:1px solid rgba(255,255,255,.08);border-radius:14px;padding:20px;margin-bottom:18px;animation:dpFadeIn .35s ease-out}}
@keyframes dpFadeIn{{from{{opacity:0;transform:translateY(8px)}}to{{opacity:1;transform:translateY(0)}}}}
.dp-head{{display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;gap:12px;flex-wrap:wrap}}
.dp-head h3{{margin:0;font-size:17px;color:{p}}}
.dp-btn{{background:rgba(255,255,255,.08);border:1px solid rgba(255,255,255,.12);color:#fff;padding:8px 14px;border-radius:8px;cursor:pointer;font-size:13px;font-weight:700}}
.dp-btn:hover{{background:{p}33;border-color:{p}}}
.dp-btn-primary{{background:{p};color:{s};padding:10px 18px;border-radius:8px;border:none;font-weight:900;cursor:pointer;font-size:14px;margin-top:10px}}
.dp-btn-primary:hover{{opacity:.9}}

/* Forms */
.dp-form{{display:flex;flex-direction:column;gap:12px}}
.dp-row{{display:flex;flex-direction:column;gap:5px}}
.dp-row-2{{display:grid;grid-template-columns:1fr 1fr;gap:12px}}
.dp-row label, .dp-row-2 label{{font-size:12px;opacity:.7;font-weight:700}}
.dp-row input, .dp-row select, .dp-row-2 input, .dp-row-2 select, .dp-reply-box input, .dp-search input{{background:rgba(0,0,0,.3);border:1px solid rgba(255,255,255,.1);color:#fff;padding:10px 12px;border-radius:8px;font-family:inherit;font-size:14px;width:100%;box-sizing:border-box}}
.dp-row input:focus, .dp-row select:focus{{outline:none;border-color:{p}}}
.dp-upload{{border:2px dashed rgba(255,255,255,.15);padding:24px;text-align:center;border-radius:8px;cursor:pointer;font-size:13px;opacity:.7}}
.dp-upload:hover{{border-color:{p};opacity:1}}

/* Tables */
.dp-table{{width:100%;border-collapse:collapse;margin-top:14px;font-size:13px}}
.dp-table th{{text-align:right;padding:10px 8px;font-size:11px;text-transform:uppercase;opacity:.6;border-bottom:1px solid rgba(255,255,255,.1);font-weight:700}}
.dp-table td{{padding:12px 8px;border-bottom:1px solid rgba(255,255,255,.05)}}
.dp-table tr:hover td{{background:rgba(255,255,255,.02)}}

/* Badges */
.dp-badge-ok{{background:#10b98122;color:#10b981;padding:3px 10px;border-radius:99px;font-size:11px;font-weight:700}}
.dp-badge-warn{{background:#f59e0b22;color:#f59e0b;padding:3px 10px;border-radius:99px;font-size:11px;font-weight:700}}
.dp-badge-err{{background:#ef444422;color:#ef4444;padding:3px 10px;border-radius:99px;font-size:11px;font-weight:700}}
.dp-badge-info{{background:{p}22;color:{p};padding:3px 10px;border-radius:99px;font-size:11px;font-weight:700}}

/* Stats */
.dp-stats-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:12px;margin-bottom:16px}}
.dp-stat{{background:rgba(255,255,255,.03);padding:16px;border-radius:10px;border:1px solid rgba(255,255,255,.06);position:relative}}
.dp-stat-ico{{font-size:24px}}
.dp-stat-val{{font-size:22px;font-weight:900;color:{p};margin-top:6px}}
.dp-stat-lbl{{font-size:11px;opacity:.7;margin-top:2px}}
.dp-stat-trend{{position:absolute;top:12px;left:12px;font-size:11px;font-weight:700;opacity:.7}}
.dp-stat-trend.up{{color:#10b981;opacity:1}}
.dp-stats-inline{{display:flex;gap:10px;flex-wrap:wrap}}
.dp-mini{{background:rgba(255,255,255,.04);padding:8px 14px;border-radius:8px;text-align:center;min-width:80px}}
.dp-mini-val{{font-size:17px;font-weight:900;color:{p}}}
.dp-mini-lbl{{font-size:10px;opacity:.65}}

/* Chart */
.dp-chart{{margin-top:16px;background:rgba(255,255,255,.03);padding:16px;border-radius:10px}}
.dp-chart-title{{font-size:13px;opacity:.8;margin-bottom:12px;font-weight:700}}
.dp-bars{{display:flex;align-items:flex-end;justify-content:space-between;height:100px;gap:6px}}
.dp-bar{{flex:1;background:linear-gradient(180deg,{p},{a});border-radius:4px 4px 0 0;min-height:10px;transition:.3s}}
.dp-bar:hover{{filter:brightness(1.2)}}
.dp-bars-lbl{{display:flex;justify-content:space-between;margin-top:6px;font-size:11px;opacity:.6}}

/* Reviews & Messages & Calendar & Notifications */
.dp-review-list, .dp-msg-list, .dp-cal, .dp-notif-list{{display:flex;flex-direction:column;gap:10px}}
.dp-review, .dp-msg{{background:rgba(255,255,255,.03);padding:12px 14px;border-radius:10px;border-right:3px solid {p}}}
.dp-msg-new{{background:{p}11;border-right-color:{p}}}
.dp-rev-head, .dp-msg-head{{display:flex;justify-content:space-between;margin-bottom:6px;font-size:13px}}
.dp-rev-head span{{color:#f59e0b}}
.dp-rev-actions{{display:flex;gap:6px;margin-top:8px}}
.dp-review p, .dp-msg p{{margin:4px 0;font-size:13px;opacity:.9}}
.dp-reply-box{{display:flex;gap:8px;margin-top:12px;align-items:center}}
.dp-reply-box input{{flex:1}}
.dp-cal-row{{display:grid;grid-template-columns:160px 1fr auto;gap:10px;align-items:center;padding:10px 12px;background:rgba(255,255,255,.03);border-radius:8px;font-size:13px}}
.dp-cal-date{{font-weight:700;color:{p};font-size:12px}}
.dp-notif{{padding:12px 14px;background:rgba(255,255,255,.03);border-radius:8px;font-size:13px;border-right:3px solid {p}}}

/* Filters / Chips */
.dp-filters{{display:flex;gap:6px;flex-wrap:wrap}}
.dp-chip{{background:rgba(255,255,255,.06);border:1px solid rgba(255,255,255,.08);color:#fff;padding:5px 11px;border-radius:99px;font-size:11px;cursor:pointer;font-weight:700}}
.dp-chip:hover{{background:{p}22}}
.dp-chip-on{{background:{p};color:{s};border-color:{p}}}
.dp-search{{flex:1;max-width:280px}}
.dp-select{{background:rgba(0,0,0,.3);border:1px solid rgba(255,255,255,.1);color:#fff;padding:8px 12px;border-radius:8px;font-size:13px}}

@media (max-width:768px){{
  .dp-layout{{grid-template-columns:1fr}}
  .dp-side{{border-left:none;border-bottom:1px solid rgba(255,255,255,.06)}}
  .dp-cards-grid{{grid-template-columns:1fr;padding:12px}}
}}

@media (max-width:768px){{
  .hero-split .container,.about-layout{{grid-template-columns:1fr}}
  section{{padding:48px 0}}
}}
"""


