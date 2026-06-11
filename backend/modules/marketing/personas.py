"""5 audience personas + Saudi-tuned tone presets for content generation."""

PERSONAS = [
    {
        "id": "devs",
        "name": "المطورون",
        "emoji": "👨‍💻",
        "description": "مطورون يحبون أدوات الذكاء الاصطناعي والـ no-code وأتمتة العمل",
        "interests": ["AI tools", "React", "Python", "automation", "API integration"],
        "hashtags": ["#مطورين", "#برمجة", "#AI_arabic", "#تطوير_تطبيقات", "#nocode"],
        "tone": "تقني واضح، أمثلة كود، روابط GitHub، يحب التحدّيات",
        "hook_examples": [
            "بنيت تطبيق React في 5 دقائق بدون كتابة سطر كود — كيف؟",
            "نسيت SDK وAPI keys؟ Zenrex يربط 13 خدمة لك تلقائياً",
        ],
    },
    {
        "id": "creators",
        "name": "صنّاع المحتوى",
        "emoji": "🎬",
        "description": "يوتيوبرز ومنشئو محتوى يحتاجون صور + فيديوهات + thumbnails بسرعة",
        "interests": ["video editing", "thumbnails", "AI art", "Sora", "content creation"],
        "hashtags": ["#صناع_المحتوى", "#يوتيوب_عربي", "#محتوى_رقمي", "#AI_video"],
        "tone": "بصري، ممتع، أمثلة فيديوهات قبل/بعد، يحب السبق",
        "hook_examples": [
            "Thumbnail يجيب 10× مشاهدات — جيلتها بـ 30 ثانية",
            "Sora 2 + Flux Pro Ultra في منصة وحدة — مالك تروح برّا",
        ],
    },
    {
        "id": "marketers",
        "name": "المسوّقون",
        "emoji": "📣",
        "description": "مسوقون رقميون يحتاجون landing pages، إعلانات، حملات email",
        "interests": ["paid ads", "landing pages", "conversion", "copywriting", "analytics"],
        "hashtags": ["#تسويق_رقمي", "#حملات_إعلانية", "#زيادة_مبيعات", "#copywriting"],
        "tone": "أرقام، نسب تحويل، ROI، حالات نجاح، CTA قوي",
        "hook_examples": [
            "Landing page تحوّل 30% — Zenrex بنته في 8 دقائق",
            "نص إعلان يبيع — AI كاتبه + ينشره + يحلل نتائجه",
        ],
    },
    {
        "id": "entrepreneurs",
        "name": "رواد الأعمال",
        "emoji": "🚀",
        "description": "مؤسسو شركات ناشئة يحتاجون MVP سريع لاختبار فكرة",
        "interests": ["MVP", "startup", "validation", "fundraising", "SaaS"],
        "hashtags": ["#رواد_الأعمال", "#ستارت_اب", "#مشاريع_ناشئة", "#فكرة_مشروع"],
        "tone": "إلهامي، قصص نجاح، أرقام مستثمرين، تحفيزي",
        "hook_examples": [
            "اطلق MVP في يوم واحد — وضع للاستثمار خلال أسبوع",
            "وفّر $30K مطوّر — Zenrex يبني تطبيقك في ليلة",
        ],
    },
    {
        "id": "students",
        "name": "الطلاب والمبتدئون",
        "emoji": "🎓",
        "description": "طلاب جامعات + مبتدئون يبحثون عن أدوات سهلة لإنجاز مشاريع التخرج",
        "interests": ["projects", "thesis", "free tools", "learning", "portfolio"],
        "hashtags": ["#طلاب_السعودية", "#مشاريع_تخرج", "#تعليم", "#portfolio"],
        "tone": "بسيط، صديق، خطوة بخطوة، مجاناً، يحفّز",
        "hook_examples": [
            "مشروع تخرج جاهز في ساعتين — بدون خبرة برمجة",
            "Portfolio يخليك توظف — Zenrex بنّاه لك مجاناً",
        ],
    },
]

PERSONA_MAP = {p["id"]: p for p in PERSONAS}

# Content variation buckets — every post draws from one
CONTENT_BUCKETS = [
    {"id": "tip", "name": "نصيحة ذهبية", "weight": 25},
    {"id": "showcase", "name": "عرض ميزة", "weight": 20},
    {"id": "case_study", "name": "قصة نجاح", "weight": 15},
    {"id": "question", "name": "سؤال تفاعلي", "weight": 15},
    {"id": "comparison", "name": "مقارنة", "weight": 10},
    {"id": "behind_scenes", "name": "خلف الكواليس", "weight": 10},
    {"id": "announcement", "name": "إعلان منتج", "weight": 5},
]
