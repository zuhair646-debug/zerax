"""
Quality gate and deterministic fallback builder for FreeBuild v2.

The LLM can be creative, but weak/half-built HTML should not reach customers.
This module validates every generated site and can produce a complete
publish-ready fallback SPA when the model output is incomplete.
"""
from __future__ import annotations

import html as html_lib
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

REQUIRED_ROUTES = ["home", "login", "register", "dashboard"]
DOMAIN_ROUTE_HINTS: Dict[str, List[str]] = {
    "quran_memorization": ["readers", "memorize", "lessons", "rewards", "contact"],
    "restaurant": ["menu", "booking", "branches", "offers", "contact"],
    "ecommerce_store": ["products", "cart", "checkout", "orders", "contact"],
    "sports_club": ["players", "matches", "tickets", "store", "contact"],
    "clinic": ["book", "doctors", "services", "insurance", "contact"],
    "academy_education": ["courses", "teachers", "schedule", "enroll", "contact"],
    "realestate": ["properties", "agents", "mortgage", "book", "contact"],
    "salon_beauty": ["services", "booking", "specialists", "packages", "contact"],
}
DOMAIN_LABELS: Dict[str, str] = {
    "quran_memorization": "منصة تحفيظ القرآن",
    "restaurant": "مطعم ومقهى",
    "ecommerce_store": "متجر إلكتروني",
    "sports_club": "نادي رياضي",
    "clinic": "عيادة طبية",
    "academy_education": "أكاديمية تعليمية",
    "realestate": "منصة عقارية",
    "salon_beauty": "صالون تجميل",
}
ROUTE_LABELS: Dict[str, str] = {
    "home": "الرئيسية", "login": "دخول", "register": "حساب جديد", "dashboard": "لوحة التحكم",
    "readers": "القرّاء", "memorize": "التحفيظ", "lessons": "الدروس", "rewards": "المكافآت",
    "menu": "المنيو", "booking": "الحجز", "branches": "الفروع", "offers": "العروض",
    "products": "المنتجات", "cart": "السلة", "checkout": "الدفع", "orders": "طلباتي",
    "players": "اللاعبون", "matches": "المباريات", "tickets": "التذاكر", "store": "المتجر",
    "book": "حجز موعد", "doctors": "الأطباء", "services": "الخدمات", "insurance": "التأمين",
    "courses": "الدورات", "teachers": "المدربون", "schedule": "الجدول", "enroll": "التسجيل",
    "properties": "العقارات", "agents": "المستشارون", "mortgage": "التمويل",
    "specialists": "الأخصائيون", "packages": "الباقات", "contact": "تواصل",
}


def _strip_tags(s: str) -> str:
    return re.sub(r"<[^>]+>", " ", s or "")


def _extract_routes(html: str) -> List[str]:
    routes = set(re.findall(r'id=["\']page-([a-zA-Z0-9_-]+)["\']', html or ""))
    routes.update(re.findall(r'data-page=["\']([a-zA-Z0-9_-]+)["\']', html or ""))
    return sorted(routes)


def _nav_links(html: str) -> List[str]:
    return sorted(set(re.findall(r'href=["\']#/([a-zA-Z0-9_-]+)["\']', html or "")))


def analyze_html_quality(html: str, domain_key: Optional[str] = None) -> Dict[str, Any]:
    html = html or ""
    low = html.lower()
    text = _strip_tags(html)
    routes = _extract_routes(html)
    navs = _nav_links(html)
    route_set = set(routes)
    issues: List[Dict[str, str]] = []
    strengths: List[str] = []

    def issue(severity: str, code: str, message: str) -> None:
        issues.append({"severity": severity, "code": code, "message": message})

    if "<html" not in low:
        issue("critical", "missing_html", "الناتج لا يحتوي على وسم HTML كامل.")
    if len(html) < 12000:
        issue("high", "too_short", "حجم الموقع أقل من المطلوب لموقع متكامل.")
    elif len(html) >= 18000:
        strengths.append("حجم الموقع غني ومناسب لتطبيق متعدد الصفحات")

    missing_core = [r for r in REQUIRED_ROUTES if r not in route_set]
    if missing_core:
        issue("critical", "missing_core_pages", "صفحات أساسية ناقصة: " + ", ".join(missing_core))
    else:
        strengths.append("يحتوي على الرئيسية والدخول والتسجيل ولوحة التحكم")

    domain_routes = DOMAIN_ROUTE_HINTS.get(domain_key or "", [])
    domain_hits = [r for r in domain_routes if r in route_set]
    if domain_routes and len(domain_hits) < 2:
        issue("high", "weak_domain_pages", "الصفحات المتخصصة للمجال قليلة أو ناقصة.")
    elif domain_hits:
        strengths.append("يحتوي على صفحات متخصصة للمجال: " + ", ".join(domain_hits[:4]))

    if len(routes) < 5:
        issue("critical", "not_enough_pages", "الموقع أقل من 5 صفحات داخلية.")
    elif len(routes) >= 7:
        strengths.append(f"عدد الصفحات جيد ({len(routes)} صفحات)")

    broken_nav = sorted([n for n in navs if n not in route_set])
    if broken_nav:
        issue("high", "broken_navigation", "روابط تنقل بلا صفحات: " + ", ".join(broken_nav[:8]))

    if "hashchange" not in low or "window.location.hash" not in low:
        issue("critical", "missing_router", "لا يوجد hash router واضح للتنقل بين الصفحات.")
    else:
        strengths.append("يدعم تنقل SPA عبر hash routing")

    if not re.search(r"<form\b", low):
        issue("high", "missing_forms", "لا توجد نماذج تفاعل/تسجيل/حجز.")
    else:
        strengths.append("يحتوي على نماذج تفاعلية")

    if "@media" not in low and "max-width" not in low:
        issue("medium", "weak_responsive", "لا تظهر قواعد responsive كافية للجوال.")
    else:
        strengths.append("يحتوي على قواعد تجاوب للجوال")

    if "lorem ipsum" in low or "لوريم" in low:
        issue("critical", "placeholder_text", "يوجد نص تجريبي Lorem/Lorem ipsum.")
    if "@@img/" in low:
        issue("medium", "image_placeholders", "بعض placeholders الصور لم تُستبدل.")
    if re.search(r'<img[^>]+src=["\']\s*["\']', html):
        issue("medium", "empty_images", "توجد صور بدون src.")

    cta_count = len(re.findall(r"(احجز|سجل|ابدأ|اطلب|تواصل|اشترك|جرّب|جرب|شراء|أضف للسلة)", text))
    if cta_count < 3:
        issue("medium", "weak_cta", "نداءات الإجراء قليلة؛ الموقع يحتاج أزرار تحويل أكثر.")
    else:
        strengths.append("نداءات الإجراء واضحة")

    section_count = len(re.findall(r"<section\b", low))
    if section_count < 8:
        issue("medium", "few_sections", "عدد الأقسام قليل لموقع متكامل.")

    penalty = 0
    for it in issues:
        penalty += {"critical": 24, "high": 14, "medium": 7, "low": 3}.get(it["severity"], 5)
    score = max(0, min(100, 100 - penalty))
    blocking = any(i["severity"] == "critical" for i in issues) or score < 72
    return {
        "ok": not blocking,
        "score": score,
        "grade": "A" if score >= 90 else ("B" if score >= 80 else ("C" if score >= 70 else "D")),
        "blocking": blocking,
        "routes": routes,
        "nav_links": navs,
        "issues": issues,
        "strengths": strengths[:8],
        "summary": f"جاهزية الموقع {score}/100 — {'جاهز للنشر' if not blocking else 'يحتاج إصلاح قبل التسليم'}",
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }


def build_quality_report(html: str, domain_key: Optional[str] = None) -> Dict[str, Any]:
    q = analyze_html_quality(html, domain_key)
    recommendations = []
    for issue in q["issues"][:8]:
        code = issue["code"]
        if code == "too_short":
            recommendations.append("زِد المحتوى العملي: خدمات، خطوات، شهادات، FAQ، وصفحات داخلية.")
        elif code == "missing_core_pages":
            recommendations.append("أضف صفحات home/login/register/dashboard بنفس نظام الـSPA.")
        elif code == "weak_domain_pages":
            recommendations.append("أضف صفحات متخصصة حسب المجال مثل الحجز/المنتجات/الدورات/الأطباء.")
        elif code == "missing_router":
            recommendations.append("أضف hash router يبدّل بين section.page حسب الرابط.")
        elif code == "weak_responsive":
            recommendations.append("أضف @media للجوال والتابلت وتأكد من القائمة المتحركة.")
        elif code == "weak_cta":
            recommendations.append("أضف أزرار واضحة للتحويل: احجز، سجل، تواصل، اطلب الآن.")
    if not recommendations:
        recommendations.append("الموقع جاهز. الخطوة التالية: توليد صور AI مخصصة ثم نشر الرابط للعميل.")
    q["recommendations"] = recommendations
    return q


def _detect_domain(text: str) -> Optional[str]:
    try:
        from .blueprints import detect_domain
        return detect_domain(text or "")
    except Exception:
        return None


def _domain_routes(domain_key: Optional[str]) -> List[str]:
    extra = DOMAIN_ROUTE_HINTS.get(domain_key or "", ["services", "booking", "contact"])
    return list(dict.fromkeys(REQUIRED_ROUTES + extra))


def _label(route: str) -> str:
    return ROUTE_LABELS.get(route, route.replace("-", " ").title())


def _feature_cards(domain_key: Optional[str]) -> List[Tuple[str, str]]:
    if domain_key == "clinic":
        return [("حجز فوري", "اختيار الطبيب والموعد خلال أقل من دقيقة"), ("ملف مريض", "متابعة المواعيد والوصفات والتنبيهات"), ("أطباء موثوقون", "عرض التخصصات والخبرات والتقييمات")]
    if domain_key == "ecommerce_store":
        return [("كتالوج ذكي", "تصنيف وبحث وفلاتر للمنتجات"), ("سلة ودفع", "تجربة شراء مختصرة وواضحة"), ("لوحة طلبات", "متابعة الطلبات والشحن والإرجاع")]
    if domain_key == "quran_memorization":
        return [("خطة حفظ", "مسارات يومية مع متابعة التقدم"), ("مكتبة قرّاء", "مشغلات صوت وروابط تلاوة موثوقة"), ("مكافآت", "تحفيز الطلاب بالنقاط والإنجازات")]
    if domain_key == "restaurant":
        return [("منيو تفاعلي", "أقسام وأسعار وعروض يومية"), ("حجز طاولة", "اختيار الفرع والوقت وعدد الأشخاص"), ("طلبات سريعة", "CTA واضح للطلب والتواصل")]
    if domain_key == "academy_education":
        return [("دورات منظمة", "مسارات تعليمية ومواعيد واضحة"), ("مدربون", "ملفات خبراء وتقييمات"), ("تسجيل سريع", "نموذج تسجيل ولوحة طالب")]
    return [("تجربة احترافية", "تصميم متكامل ومتجاوب"), ("إدارة كاملة", "لوحة تحكم ونماذج تشغيل"), ("جاهز للنشر", "رابط عام وتحسينات SEO")]


def _styles() -> str:
    return """
:root{--bg:#08080a;--card:#111218;--muted:#a1a1aa;--text:#fff;--amber:#f59e0b;--amber2:#fbbf24;--line:rgba(255,255,255,.12);--green:#22c55e}
*{box-sizing:border-box} body{margin:0;background:radial-gradient(circle at top right,#3b2504 0,#09090b 38%,#050506 100%);color:var(--text);font-family:Tajawal,Arial,sans-serif;line-height:1.8} a{color:inherit;text-decoration:none} img{max-width:100%;display:block}
.navbar{position:sticky;top:0;z-index:20;display:flex;align-items:center;justify-content:space-between;gap:1rem;padding:1rem 5vw;background:rgba(8,8,10,.74);backdrop-filter:blur(18px);border-bottom:1px solid var(--line)}
.brand{display:flex;align-items:center;gap:.75rem;font-weight:900;font-size:1.15rem}.logo{width:42px;height:42px;border-radius:16px;background:linear-gradient(135deg,var(--amber),#fff3c4);color:#111;display:grid;place-items:center;font-weight:900}
.nav{display:flex;align-items:center;gap:.4rem;flex-wrap:wrap}.nav-link{padding:.65rem .9rem;border-radius:999px;color:#e4e4e7}.nav-link:hover,.nav-link.active{background:rgba(245,158,11,.18);color:#fde68a}
.actions{display:flex;gap:.6rem}.btn,button{border:0;border-radius:14px;padding:.85rem 1.1rem;font-weight:800;cursor:pointer;background:var(--amber);color:#111;box-shadow:0 12px 30px rgba(245,158,11,.18)}.btn.secondary{background:rgba(255,255,255,.08);color:#fff;border:1px solid var(--line);box-shadow:none}
.page{display:none;min-height:calc(100vh - 80px);padding:4rem 5vw}.page.active{display:block}.hero{display:grid;grid-template-columns:1.1fr .9fr;gap:2rem;align-items:center;min-height:72vh}.eyebrow{color:#fde68a;background:rgba(245,158,11,.12);display:inline-flex;border:1px solid rgba(245,158,11,.25);padding:.4rem .8rem;border-radius:999px}
h1{font-size:clamp(2.3rem,6vw,5.2rem);line-height:1.08;margin:.9rem 0} h2{font-size:clamp(1.8rem,4vw,3rem);margin:0 0 1rem} h3{margin:.4rem 0;color:#fff} p{color:#d4d4d8;margin:.35rem 0 1rem}.lead{font-size:1.25rem;max-width:720px;color:#e4e4e7}
.hero-card{position:relative;min-height:480px;border:1px solid var(--line);border-radius:34px;background:linear-gradient(145deg,rgba(255,255,255,.08),rgba(255,255,255,.02));overflow:hidden;padding:1.2rem;box-shadow:0 30px 80px rgba(0,0,0,.35)}.hero-card img{height:260px;width:100%;object-fit:cover;border-radius:24px}.floating{position:absolute;bottom:1.2rem;left:1.2rem;right:1.2rem;background:rgba(0,0,0,.58);backdrop-filter:blur(12px);border:1px solid var(--line);border-radius:22px;padding:1rem}
.cards,.grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:1rem}.card,.mini,.panel{background:rgba(17,18,24,.76);border:1px solid var(--line);border-radius:26px;padding:1.4rem;box-shadow:0 24px 70px rgba(0,0,0,.24)}.card .icon{width:44px;height:44px;border-radius:14px;background:rgba(245,158,11,.16);display:grid;place-items:center;color:#fbbf24;font-weight:900}
.mini img{height:170px;width:100%;object-fit:cover;border-radius:18px;margin-bottom:.8rem}.person .avatar,.avatar{width:70px;height:70px;border-radius:24px;background:linear-gradient(135deg,var(--amber),#fff);color:#111;display:grid;place-items:center;font-size:1.4rem;font-weight:900;margin-bottom:.8rem}
.split{display:grid;grid-template-columns:1fr 1fr;gap:1.2rem;align-items:start}.form{display:grid;gap:.8rem} input,textarea,select{width:100%;background:rgba(0,0,0,.35);border:1px solid var(--line);border-radius:14px;padding:1rem;color:#fff;outline:none}textarea{min-height:120px} input:focus,textarea:focus{border-color:var(--amber)}
.dash{display:grid;grid-template-columns:280px 1fr;gap:1.2rem}.sidebar{background:rgba(255,255,255,.05);border:1px solid var(--line);border-radius:28px;padding:1rem;height:max-content}.side-link{display:block;padding:.85rem 1rem;border-radius:14px;color:#e4e4e7}.side-link:hover{background:rgba(245,158,11,.14)}.stats{display:grid;grid-template-columns:repeat(4,1fr);gap:1rem;margin:1rem 0}.stat{background:linear-gradient(145deg,rgba(245,158,11,.16),rgba(255,255,255,.04));border:1px solid var(--line);border-radius:22px;padding:1rem}.stat b{font-size:2rem;color:#fde68a;display:block}
.timeline{display:grid;grid-template-columns:repeat(4,1fr);gap:1rem;margin-top:1rem}.timeline div{padding:1.2rem;border-radius:20px;border:1px solid var(--line);background:rgba(255,255,255,.05);text-align:center;font-weight:800}.ticks{color:#e4e4e7}.ticks li{margin:.4rem 0}footer{border-top:1px solid var(--line);padding:2rem 5vw;color:#a1a1aa;text-align:center}
.auth-wrap{max-width:520px;margin:0 auto}.auth-card{background:rgba(17,18,24,.9);border:1px solid var(--line);border-radius:30px;padding:2rem;box-shadow:0 30px 80px rgba(0,0,0,.35)}.notice{padding:1rem;border-radius:18px;background:rgba(34,197,94,.12);border:1px solid rgba(34,197,94,.25);color:#bbf7d0;margin:1rem 0}
@media(max-width:980px){.hero,.split,.dash{grid-template-columns:1fr}.cards,.grid,.stats,.timeline{grid-template-columns:1fr 1fr}.nav{display:none}}
@media(max-width:640px){.page{padding:2rem 1rem}.cards,.grid,.stats,.timeline{grid-template-columns:1fr}.navbar{padding:1rem}.actions{display:none}h1{font-size:2.4rem}}
"""


def build_publish_ready_fallback_html(brief: str = "", domain_key: Optional[str] = None) -> str:
    domain_key = domain_key or _detect_domain(brief) or "generic"
    title = DOMAIN_LABELS.get(domain_key, "موقع احترافي")
    safe_title = html_lib.escape(title)
    safe_brief = html_lib.escape((brief or title).strip()[:220])
    routes = _domain_routes(domain_key)
    nav_routes = [r for r in routes if r not in ("login", "register")][:7]
    nav_html = "".join(f'<a class="nav-link" href="#/{r}">{_label(r)}</a>' for r in nav_routes)
    cards = _feature_cards(domain_key)
    feature_html = "".join(
        f'<article class="card"><span class="icon">{i}</span><h3>{html_lib.escape(t)}</h3><p>{html_lib.escape(d)}</p><a href="#/dashboard">جرّب الآن</a></article>'
        for i, (t, d) in enumerate(cards, 1)
    )
    domain_sections: List[str] = []
    for r in routes:
        if r in ("home", "login", "register", "dashboard"):
            continue
        label = _label(r)
        if r in ("book", "booking", "enroll", "contact", "checkout"):
            content = f'''
<div class="split"><div><h2>{label}</h2><p>نموذج عملي جاهز للتواصل والتحويل مع حقول واضحة وتجربة سهلة.</p><ul class="ticks"><li>تأكيد فوري داخل الصفحة</li><li>تصميم متجاوب للجوال</li><li>إمكانية ربطه لاحقاً بـAPI حقيقي</li></ul></div>
<form class="panel form" onsubmit="event.preventDefault(); toast('تم استلام طلبك بنجاح');"><input placeholder="الاسم الكامل"><input placeholder="رقم الجوال"><input placeholder="البريد الإلكتروني"><textarea placeholder="تفاصيل الطلب"></textarea><button>إرسال الطلب</button></form></div>'''
        elif r in ("products", "menu", "courses", "services", "properties", "packages"):
            items = "".join(f'<article class="mini"><img src="@@IMG/auto@@" alt="{label} احترافي بتصوير تجاري حديث"><h3>{label} {n}</h3><p>وصف واضح، سعر/مدة، ومميزات تساعد العميل يقرر بسرعة.</p><button>اختيار</button></article>' for n in range(1, 7))
            content = f"<h2>{label}</h2><p>قسم غني يعرض الخيارات بطريقة منظمة.</p><div class=\"grid\">{items}</div>"
        elif r in ("doctors", "teachers", "players", "agents", "specialists", "readers"):
            target_route = "booking" if "booking" in routes else ("book" if "book" in routes else "contact")
            people = "".join(f'<article class="mini person"><div class="avatar">{n}</div><h3>{label} {n}</h3><p>نبذة مختصرة وخبرة وتقييم وزر تواصل.</p><a href="#/{target_route}">احجز/تواصل</a></article>' for n in range(1, 7))
            content = f"<h2>{label}</h2><p>بطاقات أشخاص/خبراء مع معلومات عملية.</p><div class=\"grid\">{people}</div>"
        else:
            content = f"<h2>{label}</h2><p>صفحة متخصصة ضمن {safe_title} مبنية لتخدم رحلة العميل من التعرف إلى القرار.</p><div class=\"timeline\"><div>استكشاف</div><div>اختيار</div><div>تأكيد</div><div>متابعة</div></div>"
        domain_sections.append(f'<section class="page inner" id="page-{r}">{content}</section>')
    side_links = "".join(f'<a class="side-link" href="#/{r}">{_label(r)}</a>' for r in nav_routes)
    first_domain = nav_routes[1] if len(nav_routes) > 1 else "dashboard"
    return f'''<!doctype html>
<html lang="ar" dir="rtl">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>{safe_title} — موقع جاهز للنشر</title><meta name="description" content="{safe_brief}"><style>{_styles()}</style></head>
<body>
<header class="navbar"><a class="brand" href="#/home"><span class="logo">Z</span><span>{safe_title}</span></a><nav class="nav">{nav_html}</nav><div class="actions"><a class="btn secondary" href="#/login">دخول</a><a class="btn" href="#/register">ابدأ الآن</a></div></header>
<section class="page" id="page-home"><div class="hero"><div><span class="eyebrow">نسخة أولى جاهزة للنشر والتحسين</span><h1>{safe_title} يخدم عميلك من أول زيارة إلى القرار</h1><p class="lead">{safe_brief or 'موقع متكامل متعدد الصفحات، سريع، متجاوب، وفيه رحلة عميل واضحة ونماذج تفاعل ولوحة تحكم.'}</p><div class="actions"><a class="btn" href="#/{first_domain}">استكشف الخدمة</a><a class="btn secondary" href="#/contact">تواصل معنا</a></div></div><div class="hero-card"><img src="@@IMG/auto@@" alt="واجهة موقع احترافي عربي حديث بإضاءة ذهبية وتجربة رقمية فاخرة"><div class="floating"><b>جاهزية تشغيل عالية</b><p>تصميم، صفحات، نماذج، لوحة، وتجربة جوال في ملف واحد.</p></div></div></div><div class="cards">{feature_html}</div></section>
<section class="page" id="page-login"><div class="auth-wrap"><form class="auth-card" onsubmit="event.preventDefault(); toast('تم تسجيل الدخول تجريبياً'); location.hash='#/dashboard';"><h2>تسجيل الدخول</h2><p>ادخل لحسابك لمتابعة الخدمات والطلبات.</p><input type="email" placeholder="البريد الإلكتروني"><input type="password" placeholder="كلمة المرور"><button>دخول</button><p>ما عندك حساب؟ <a href="#/register">أنشئ حساب</a></p></form></div></section>
<section class="page" id="page-register"><div class="auth-wrap"><form class="auth-card" onsubmit="event.preventDefault(); toast('تم إنشاء الحساب تجريبياً'); location.hash='#/dashboard';"><h2>إنشاء حساب</h2><p>ابدأ تجربة كاملة خلال ثواني.</p><input placeholder="الاسم"><input type="email" placeholder="البريد الإلكتروني"><input type="password" placeholder="كلمة المرور"><input type="password" placeholder="تأكيد كلمة المرور"><button>إنشاء حساب</button></form></div></section>
<section class="page" id="page-dashboard"><div class="dash"><aside class="sidebar"><h3>لوحة التحكم</h3>{side_links}</aside><main><h2>أهلاً بك في لوحة الإدارة</h2><p>نظرة تنفيذية على أداء الموقع وتفاعل العملاء.</p><div class="stats"><div class="stat"><b>128</b><span>عميل مهتم</span></div><div class="stat"><b>34</b><span>طلب جديد</span></div><div class="stat"><b>92%</b><span>رضا العملاء</span></div><div class="stat"><b>24/7</b><span>جاهزية</span></div></div><div class="panel"><h3>آخر النشاط</h3><p>طلب جديد، رسالة تواصل، وزيادة زيارات من الجوال. هذه اللوحة جاهزة للربط ببيانات حقيقية لاحقاً.</p></div></main></div></section>
{''.join(domain_sections)}
<footer>© {datetime.now().year} {safe_title} — موقع تم بناؤه عبر Zerax FreeBuild v2</footer>
<script>
function navigate(){{var hash=(window.location.hash||'#/home').slice(2)||'home';document.querySelectorAll('.page').forEach(function(p){{p.classList.remove('active');p.style.display='none';}});var target=document.getElementById('page-'+hash)||document.getElementById('page-home');target.classList.add('active');target.style.display='block';document.querySelectorAll('.nav-link').forEach(function(l){{l.classList.toggle('active',l.getAttribute('href')==='#/'+hash);}});window.scrollTo(0,0);}}
function toast(msg){{var n=document.createElement('div');n.className='notice';n.style.position='fixed';n.style.left='1rem';n.style.bottom='1rem';n.style.zIndex='99';n.textContent=msg;document.body.appendChild(n);setTimeout(function(){{n.remove();}},2500);}}
window.addEventListener('hashchange',navigate);window.addEventListener('DOMContentLoaded',navigate);
</script>
</body></html>'''


def ensure_quality_or_fallback(html: str, brief: str = "", previous_html: str = "", domain_key: Optional[str] = None) -> Tuple[str, Dict[str, Any], bool]:
    domain_key = domain_key or _detect_domain(brief)
    report = build_quality_report(html, domain_key)
    if report["ok"]:
        return html, report, False
    if previous_html:
        prev_report = build_quality_report(previous_html, domain_key)
        if prev_report["ok"] and prev_report["score"] >= report["score"]:
            prev_report["preserved_previous"] = True
            prev_report["rejected_score"] = report["score"]
            prev_report["rejected_issues"] = report["issues"]
            return previous_html, prev_report, True
    fallback = build_publish_ready_fallback_html(brief=brief, domain_key=domain_key)
    try:
        from .resources import post_process_html_images
        fallback = post_process_html_images(fallback)
    except Exception:
        pass
    fallback_report = build_quality_report(fallback, domain_key)
    fallback_report["used_fallback"] = True
    fallback_report["rejected_score"] = report["score"]
    fallback_report["rejected_issues"] = report["issues"]
    return fallback, fallback_report, True
