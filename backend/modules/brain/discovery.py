"""Discovery Engine — generates sharp, contextual questions before any build.

Old failure mode: AI starts building immediately on vague requests, then
the user has to iterate 5+ times to get what they want (wasting credits).

New design: BEFORE the AI enters PLANNING, it must call `ask_user` 3-5
times to collect critical decisions. The questions are:

  • Project-type-aware (different for store vs portfolio vs SaaS)
  • Option-style (a/b/c/d not open-ended)
  • Specific (no "ما لونك المفضل؟" — instead "ذهبي وأخضر؟ أم أزرق غامق؟")
  • Progress-tracked in ProjectMemory

If the user types "skip" or "just build it", the brain switches to BEST_GUESS
mode but logs every assumption in memory so the user can override later.
"""
from typing import List, Dict, Any


# Pre-built question banks per project type. The brain selects the relevant
# bank during DISCOVERY based on the user's opening message.

QUESTION_BANKS: Dict[str, List[Dict[str, Any]]] = {
    "ecommerce": [
        {
            "q": "ما طبيعة المنتجات اللي تبي تبيعها؟",
            "options": ["زهور / هدايا", "ملابس / أزياء",
                         "إلكترونيات / أجهزة", "طعام / مشروبات",
                         "كتب / محتوى رقمي", "أخرى (اكتب)"],
            "key": "product_type",
        },
        {
            "q": "كم منتج تقريباً في البداية؟",
            "options": ["1-5 (متجر صغير مركّز)",
                         "6-20 (كاتالوج متوسط)",
                         "20-50 (كاتالوج كبير)",
                         "+50 (متجر ضخم)"],
            "key": "product_count",
        },
        {
            "q": "نظام الدفع المطلوب؟",
            "options": ["عرض فقط (بدون دفع فعلي الآن)",
                         "Stripe / بطاقات ائتمان",
                         "PayPal",
                         "موبايل مدى / Apple Pay (للسعودية)",
                         "Cash on Delivery"],
            "key": "payment_method",
        },
        {
            "q": "اللوحة اللونية المفضلة؟",
            "options": ["ذهبي وأخضر زيتي (فاخر)",
                         "أزرق غامق وفضي (تقني)",
                         "أبيض ووردي (نسائي)",
                         "أسود وأحمر (جريء)",
                         "بيج وبني (طبيعي)",
                         "اقترحه أنت بناء على المنتج"],
            "key": "color_palette",
        },
        {
            "q": "تركيب الموقع؟",
            "options": ["صفحة واحدة (كل شي في index)",
                         "صفحات متعددة (home, products, about, contact)",
                         "متعدد + لوحة تحكم admin",
                         "اقترح أنت الأنسب"],
            "key": "site_structure",
        },
    ],

    "portfolio": [
        {
            "q": "نوع المحفظة؟",
            "options": ["مصمم جرافيك / UI/UX",
                         "مطور / مبرمج",
                         "مصور فوتوغرافي",
                         "كاتب / مدوّن",
                         "متعدد (متنوع)"],
            "key": "portfolio_type",
        },
        {
            "q": "ما عدد المشاريع/الأعمال؟",
            "options": ["1-3 مشاريع بارزة",
                         "4-10 مشاريع",
                         "+10 مشروع (شبكة)"],
            "key": "project_count",
        },
        {
            "q": "هل تبي صفحة تواصل تستقبل رسائل فعلياً؟",
            "options": ["نعم، بنموذج + Email",
                         "نعم، WhatsApp فقط",
                         "لا، روابط سوشيال فقط"],
            "key": "contact_mode",
        },
        {
            "q": "الأسلوب البصري؟",
            "options": ["minimalist (بسيط جداً، أبيض)",
                         "dark mode فاخر",
                         "ملوّن وحيوي",
                         "كلاسيكي راقي"],
            "key": "visual_style",
        },
    ],

    "saas_landing": [
        {
            "q": "نوع المنتج؟",
            "options": ["تطبيق ويب (Web App)",
                         "تطبيق جوال (Mobile App)",
                         "API / خدمة للمطورين",
                         "أداة AI",
                         "خدمة استشارية"],
            "key": "product_type",
        },
        {
            "q": "نموذج التسعير؟",
            "options": ["مجاني فقط",
                         "Freemium (مجاني + خطط مدفوعة)",
                         "اشتراك شهري/سنوي",
                         "دفعة واحدة",
                         "بدون عرض أسعار في البداية"],
            "key": "pricing_model",
        },
        {
            "q": "Call-to-Action الأساسي؟",
            "options": ["تسجيل / Sign up",
                         "حجز Demo / Book a Call",
                         "تحميل / Download",
                         "تجربة مجانية / Free Trial"],
            "key": "primary_cta",
        },
        {
            "q": "أقسام صفحة الهبوط؟",
            "options": ["Hero + Features + Pricing + FAQ + CTA",
                         "Hero + Demo Video + Testimonials + CTA",
                         "Hero + Problem/Solution + Features + Stats + CTA",
                         "اقترح أنت الأنسب"],
            "key": "section_layout",
        },
    ],

    "generic": [
        {
            "q": "ما الهدف الأساسي من الموقع؟",
            "options": ["بيع منتجات",
                         "عرض أعمال (محفظة)",
                         "نشر محتوى (مدوّنة)",
                         "تطبيق / خدمة (SaaS)",
                         "موقع شركة تعريفي",
                         "أخرى"],
            "key": "site_purpose",
        },
        {
            "q": "الفئة المستهدفة؟",
            "options": ["أفراد / مستهلكين (B2C)",
                         "شركات / محترفين (B2B)",
                         "كلاهما"],
            "key": "audience",
        },
        {
            "q": "لغة الموقع الرئيسية؟",
            "options": ["عربية فقط",
                         "إنجليزية فقط",
                         "ثنائي (عربي + إنجليزي)"],
            "key": "language",
        },
    ],
}


def detect_project_type(user_message: str) -> str:
    """Heuristically classify the project type from the opening message."""
    msg = (user_message or "").lower()
    ecom_hints = ("متجر", "متاجر", "store", "shop", "ecommerce", "بيع", "منتج",
                   "منتجات", "سلة", "cart", "products", "زهور", "ملابس", "هدايا")
    port_hints = ("محفظ", "portfolio", "أعمالي", "اعمالي", "ساطر",
                   "مصمم", "مصور", "مطور",
                   "خبراتي")
    saas_hints = ("saas", "تطبيق", "خدمة", "اشتراك", "subscription",
                   "landing", "هبوط", "تسجيل", "demo")
    if any(h in msg for h in ecom_hints):
        return "ecommerce"
    if any(h in msg for h in port_hints):
        return "portfolio"
    if any(h in msg for h in saas_hints):
        return "saas_landing"
    return "generic"


def get_initial_questions(project_type: str, limit: int = 5) -> List[Dict[str, Any]]:
    """Return the discovery question set for the inferred project type."""
    bank = QUESTION_BANKS.get(project_type, QUESTION_BANKS["generic"])
    return bank[:limit]
