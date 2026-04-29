"""
Template Themes — UNIQUE visual identity per archetype.

Each archetype gets:
  • palette        — 4 colors (primary, secondary, accent, bg)
  • font           — Google Font (Arabic-supporting)
  • hero_pattern   — CSS background pattern/shape
  • hero_image_q   — Unsplash query keyword (varies hero photo per archetype)
  • spacing/radius — design tokens
  • custom_css     — per-archetype CSS injected to make it visually distinct

This guarantees that each of the 20 archetypes LOOKS unique — not just rearranged.
"""

# 20 unique themes — one per archetype id
ARCHETYPE_THEMES = {
    "classic_stack": {
        "name": "ذهبي كلاسيكي",
        "palette": {"primary": "#D4AF37", "secondary": "#1a1a2e", "accent": "#E8C547", "bg": "#0f0f1e", "text": "#fff"},
        "font": "Tajawal",
        "hero_image_q": "luxury+restaurant+golden",
        "hero_pattern": "linear-gradient(135deg,#1a1a2e 0%,#16213e 100%)",
        "radius": "8px",
        "shadow": "0 10px 30px rgba(212,175,55,.2)",
        "custom_css": """
.hero{background:linear-gradient(rgba(15,15,30,.85),rgba(15,15,30,.7)),url(IMG) center/cover}
.hero h1{font-weight:900;letter-spacing:1px}
.btn{border-radius:4px;letter-spacing:2px;text-transform:uppercase}
""",
    },
    "magazine": {
        "name": "مجلة كريم",
        "palette": {"primary": "#C7956D", "secondary": "#F5EBDC", "accent": "#8B5E3C", "bg": "#FAF6F0", "text": "#2C1810"},
        "font": "Reem Kufi",
        "hero_image_q": "editorial+magazine+typography",
        "hero_pattern": "linear-gradient(180deg,#FAF6F0 0%,#F5EBDC 100%)",
        "radius": "0px",
        "shadow": "0 1px 0 rgba(0,0,0,.1)",
        "custom_css": """
body{background:#FAF6F0;color:#2C1810}
.hero{background:#FAF6F0;color:#2C1810;border-bottom:8px solid #C7956D}
.hero h1{font-size:96px;line-height:.9;font-weight:900;letter-spacing:-2px}
.hero h2,h2{font-family:'Playfair Display',serif;font-style:italic;font-weight:400}
section{border-bottom:1px solid rgba(44,24,16,.1)}
.gallery img{filter:grayscale(.3) contrast(1.05)}
""",
    },
    "split_screen": {
        "name": "مقسّم تيل",
        "palette": {"primary": "#0EA5E9", "secondary": "#0F172A", "accent": "#06B6D4", "bg": "#020617", "text": "#fff"},
        "font": "Cairo",
        "hero_image_q": "modern+architecture+city+night",
        "hero_pattern": "linear-gradient(90deg,#020617 50%,#0EA5E9 50%)",
        "radius": "16px",
        "shadow": "0 25px 50px -12px rgba(14,165,233,.4)",
        "custom_css": """
body{background:#020617}
.hero{display:grid;grid-template-columns:1fr 1fr;min-height:90vh;padding:0!important}
.hero .container{padding:8% 6%;display:flex;flex-direction:column;justify-content:center}
.hero h1{font-size:64px;font-weight:900}
.hero::after{content:'';background:url(IMG) center/cover;border-right:6px solid #0EA5E9}
section:nth-child(even){background:linear-gradient(135deg,rgba(14,165,233,.05),rgba(2,6,23,.95))}
@media(max-width:768px){.hero{grid-template-columns:1fr}.hero::after{display:none}}
""",
    },
    "longform_story": {
        "name": "قصة دافئة",
        "palette": {"primary": "#92400E", "secondary": "#FEF3C7", "accent": "#D97706", "bg": "#FFFBEB", "text": "#451A03"},
        "font": "Amiri",
        "hero_image_q": "vintage+warm+sunset+story",
        "hero_pattern": "linear-gradient(180deg,#FFFBEB 0%,#FEF3C7 100%)",
        "radius": "24px",
        "shadow": "0 8px 25px rgba(146,64,14,.15)",
        "custom_css": """
body{background:#FFFBEB;color:#451A03;font-size:18px;line-height:1.9}
.hero{background:linear-gradient(rgba(255,251,235,.6),rgba(254,243,199,.8)),url(IMG) center/cover;color:#451A03}
.hero h1{font-family:'Amiri',serif;font-size:88px;font-weight:700;line-height:1.1}
.hero h2{font-style:italic;opacity:.85}
section{padding:120px 0!important}
.timeline,.story_timeline{border-right:3px dashed #D97706;padding-right:30px}
""",
    },
    "gallery_first": {
        "name": "معرض سينمائي",
        "palette": {"primary": "#EAB308", "secondary": "#0c0a09", "accent": "#FBBF24", "bg": "#000000", "text": "#fafaf9"},
        "font": "Tajawal",
        "hero_image_q": "cinematic+film+grain+portrait",
        "hero_pattern": "linear-gradient(180deg,#000 0%,#0c0a09 100%)",
        "radius": "0px",
        "shadow": "0 0 40px rgba(234,179,8,.3)",
        "custom_css": """
body{background:#000;color:#fafaf9}
.hero{background:url(IMG) center/cover;min-height:100vh;position:relative}
.hero::before{content:'';position:absolute;inset:0;background:linear-gradient(180deg,transparent 0%,rgba(0,0,0,.95) 100%)}
.hero .container{position:relative;z-index:1;display:flex;align-items:flex-end;min-height:100vh}
.hero h1{font-size:120px;font-weight:900;mix-blend-mode:difference}
.gallery{padding:0!important}
.gallery img{filter:contrast(1.15) saturate(1.1)}
section{border-top:1px solid rgba(234,179,8,.1)}
""",
    },
    "minimal_portrait": {
        "name": "بسيط صحراوي",
        "palette": {"primary": "#A8A29E", "secondary": "#FFFFFF", "accent": "#78716C", "bg": "#FAFAF9", "text": "#1c1917"},
        "font": "Almarai",
        "hero_image_q": "minimal+desert+sand+still+life",
        "hero_pattern": "linear-gradient(180deg,#FAFAF9 0%,#FFFFFF 100%)",
        "radius": "2px",
        "shadow": "none",
        "custom_css": """
body{background:#FAFAF9;color:#1c1917;font-weight:300;letter-spacing:.3px}
.hero{background:#FAFAF9;color:#1c1917;text-align:center;padding:160px 0}
.hero h1{font-size:56px;font-weight:200;letter-spacing:-1px;line-height:1.2}
.hero img{max-width:340px;border-radius:50%;margin:40px auto;display:block;filter:grayscale(.4)}
section{padding:120px 0!important;border:0}
.btn{background:transparent;border:1px solid #1c1917;color:#1c1917;border-radius:0;padding:14px 40px;letter-spacing:3px;text-transform:uppercase;font-size:11px}
""",
    },
    "bold_banner": {
        "name": "بانر أحمر ناري",
        "palette": {"primary": "#DC2626", "secondary": "#000000", "accent": "#FCD34D", "bg": "#0a0a0a", "text": "#fff"},
        "font": "Cairo",
        "hero_image_q": "bold+poster+typography+impact",
        "hero_pattern": "linear-gradient(135deg,#DC2626 0%,#000 100%)",
        "radius": "0px",
        "shadow": "8px 8px 0 #FCD34D",
        "custom_css": """
body{background:#0a0a0a;color:#fff}
.hero{background:#DC2626;color:#fff;padding:60px 0;border-bottom:12px solid #FCD34D;position:relative;overflow:hidden}
.hero::before{content:'!';position:absolute;font-size:600px;font-weight:900;right:-50px;top:-100px;color:rgba(0,0,0,.15);line-height:1}
.hero h1{font-size:120px;font-weight:900;line-height:1;text-transform:uppercase;letter-spacing:-3px}
.hero h2{font-size:24px;font-weight:700;background:#000;display:inline-block;padding:10px 20px;color:#FCD34D}
.btn,.btn-primary{background:#FCD34D!important;color:#000!important;font-weight:900;border-radius:0;padding:20px 50px;font-size:18px;text-transform:uppercase;border:4px solid #fff;box-shadow:8px 8px 0 #000}
.stats{background:#000;border-top:8px solid #DC2626;border-bottom:8px solid #DC2626}
.stats .value{color:#FCD34D;font-size:80px;font-weight:900}
""",
    },
    "card_stack": {
        "name": "بطاقات نيون",
        "palette": {"primary": "#A855F7", "secondary": "#1e1b4b", "accent": "#22D3EE", "bg": "#0F0F23", "text": "#E0E7FF"},
        "font": "Cairo",
        "hero_image_q": "neon+abstract+glass+morphism",
        "hero_pattern": "radial-gradient(circle at 20% 50%,rgba(168,85,247,.3) 0%,transparent 50%),radial-gradient(circle at 80% 80%,rgba(34,211,238,.2) 0%,transparent 50%),#0F0F23",
        "radius": "24px",
        "shadow": "0 20px 60px rgba(168,85,247,.3)",
        "custom_css": """
body{background:#0F0F23;color:#E0E7FF}
.hero{background:radial-gradient(circle at 30% 50%,rgba(168,85,247,.4) 0%,transparent 50%),radial-gradient(circle at 80% 20%,rgba(34,211,238,.3) 0%,transparent 50%),#0F0F23;backdrop-filter:blur(40px)}
section{margin:24px;border-radius:24px;background:rgba(255,255,255,.03);backdrop-filter:blur(20px);border:1px solid rgba(168,85,247,.2);padding:60px 40px!important;box-shadow:0 20px 60px rgba(168,85,247,.15)}
.btn{background:linear-gradient(135deg,#A855F7,#22D3EE);border-radius:100px;padding:14px 36px;border:0;color:#fff;font-weight:700}
.feature-card,.product-card,.testimonial,.team-card{background:rgba(255,255,255,.05);border:1px solid rgba(168,85,247,.3);border-radius:20px;backdrop-filter:blur(15px)}
""",
    },
    "asymmetric": {
        "name": "غير متماثل وحشي",
        "palette": {"primary": "#84CC16", "secondary": "#FAFAF9", "accent": "#F97316", "bg": "#FAFAF9", "text": "#0c0a09"},
        "font": "Reem Kufi",
        "hero_image_q": "abstract+brutalist+art+chaos",
        "hero_pattern": "#FAFAF9",
        "radius": "0px",
        "shadow": "12px 12px 0 #0c0a09",
        "custom_css": """
body{background:#FAFAF9;color:#0c0a09}
.hero{background:#FAFAF9;color:#0c0a09;padding:80px 0;border:6px solid #0c0a09;margin:24px;position:relative}
.hero::before{content:'';position:absolute;top:-30px;right:60px;width:120px;height:120px;background:#84CC16;border-radius:50%;z-index:0}
.hero::after{content:'';position:absolute;bottom:30px;left:80px;width:200px;height:40px;background:#F97316;transform:rotate(-3deg);z-index:0}
.hero .container{position:relative;z-index:1}
.hero h1{font-size:96px;font-weight:900;line-height:.9;transform:rotate(-1deg);text-decoration:underline #84CC16 12px}
.btn{background:#0c0a09;color:#fff;border-radius:0;border:0;padding:18px 40px;font-weight:900;text-transform:uppercase;box-shadow:8px 8px 0 #84CC16;transform:rotate(.5deg)}
section:nth-child(odd){transform:rotate(.3deg);background:#fff;margin:8px 24px;padding:80px 40px!important}
section:nth-child(even){background:#0c0a09;color:#fff;transform:rotate(-.3deg);margin:8px 24px}
""",
    },
    "services_showcase": {
        "name": "خدمات أزرق محيطي",
        "palette": {"primary": "#0891B2", "secondary": "#164E63", "accent": "#67E8F9", "bg": "#F0F9FF", "text": "#083344"},
        "font": "Cairo",
        "hero_image_q": "ocean+water+fluid+services",
        "hero_pattern": "linear-gradient(135deg,#0891B2,#164E63)",
        "radius": "20px",
        "shadow": "0 20px 40px rgba(8,145,178,.25)",
        "custom_css": """
body{background:#F0F9FF;color:#083344}
.hero{background:linear-gradient(135deg,#0891B2 0%,#164E63 100%);color:#fff;clip-path:polygon(0 0,100% 0,100% 85%,0 100%);padding:120px 0 160px;position:relative}
.hero::before{content:'';position:absolute;inset:0;background:url('{IMG_1}') center/cover;opacity:.15}
.hero .container{position:relative;z-index:1}
.hero h1{font-size:72px;font-weight:900}
section{padding:80px 0!important}
.services-grid,.product-grid{grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:24px}
.feature-card,.product-card{background:#fff;border-radius:24px;border-top:4px solid #0891B2;box-shadow:0 10px 30px rgba(8,145,178,.15)}
""",
    },
    "booking_first": {
        "name": "حجز أخضر صحي",
        "palette": {"primary": "#10B981", "secondary": "#064E3B", "accent": "#A7F3D0", "bg": "#ECFDF5", "text": "#022C22"},
        "font": "Tajawal",
        "hero_image_q": "wellness+spa+green+nature",
        "hero_pattern": "linear-gradient(135deg,#ECFDF5,#A7F3D0)",
        "radius": "16px",
        "shadow": "0 15px 40px rgba(16,185,129,.2)",
        "custom_css": """
body{background:#ECFDF5;color:#022C22}
.hero{background:linear-gradient(rgba(167,243,208,.5),rgba(236,253,245,.9)),url('{IMG_1}') center/cover;color:#022C22;padding:60px 0}
.hero h1{font-size:60px;font-weight:900;color:#064E3B}
.reservation,.reservation-form{background:#fff;border-radius:24px;padding:40px;box-shadow:0 25px 60px rgba(16,185,129,.25);max-width:520px;margin:30px auto;border:2px solid #10B981}
.reservation input,.reservation select{border:2px solid #A7F3D0;border-radius:12px;padding:14px 18px;width:100%;margin-bottom:14px;font-family:inherit}
.btn-primary{background:#10B981;color:#fff;border-radius:12px;padding:16px 32px;font-weight:900;border:0}
""",
    },
    "process_steps": {
        "name": "خطوات تقنية ساخنة",
        "palette": {"primary": "#F97316", "secondary": "#0C0A09", "accent": "#FBBF24", "bg": "#FAFAF9", "text": "#1c1917"},
        "font": "Cairo",
        "hero_image_q": "tech+process+steps+modern+orange",
        "hero_pattern": "linear-gradient(135deg,#F97316,#FBBF24)",
        "radius": "12px",
        "shadow": "0 10px 30px rgba(249,115,22,.3)",
        "custom_css": """
body{background:#FAFAF9}
.hero{background:linear-gradient(135deg,#F97316 0%,#FBBF24 100%);color:#fff;padding:100px 0;border-bottom-left-radius:60% 80px;border-bottom-right-radius:60% 80px}
.hero h1{font-size:72px;font-weight:900}
.process_steps,.steps{background:#fff}
.process_steps .step,.steps .step{position:relative;padding-right:80px;border-right:4px solid #F97316;margin-bottom:40px}
.process_steps .n,.steps .n{position:absolute;right:-30px;top:0;width:60px;height:60px;background:#F97316;border-radius:50%;color:#fff;font-size:24px;font-weight:900;display:flex;align-items:center;justify-content:center;border:6px solid #fff;box-shadow:0 8px 20px rgba(249,115,22,.4)}
""",
    },
    "team_centric": {
        "name": "فريق وردي رومانسي",
        "palette": {"primary": "#EC4899", "secondary": "#831843", "accent": "#FBCFE8", "bg": "#FDF2F8", "text": "#500724"},
        "font": "Amiri",
        "hero_image_q": "friendly+team+pink+portrait",
        "hero_pattern": "linear-gradient(135deg,#FDF2F8,#FBCFE8)",
        "radius": "32px",
        "shadow": "0 15px 40px rgba(236,72,153,.25)",
        "custom_css": """
body{background:#FDF2F8;color:#500724}
.hero{background:linear-gradient(135deg,#FDF2F8,#FBCFE8);color:#500724;padding:80px 0}
.hero h1{font-family:'Amiri',serif;font-size:80px;font-weight:700;color:#831843}
.team-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:32px;padding:0 20px}
.team-card{text-align:center;background:#fff;border-radius:32px;padding:30px;border:3px solid #FBCFE8;transition:all .3s}
.team-card:hover{transform:translateY(-8px);box-shadow:0 25px 50px rgba(236,72,153,.3);border-color:#EC4899}
.team-photo{width:160px;height:160px;border-radius:50%;margin:0 auto 20px;border:6px solid #FBCFE8;background-size:cover}
""",
    },
    "reviews_driven": {
        "name": "آراء فاخرة كحلية",
        "palette": {"primary": "#FBBF24", "secondary": "#1E1B4B", "accent": "#F59E0B", "bg": "#0F0E1F", "text": "#FEF3C7"},
        "font": "Reem Kufi",
        "hero_image_q": "luxury+stars+gold+night",
        "hero_pattern": "radial-gradient(circle at 50% 0%,#312E81 0%,#0F0E1F 100%)",
        "radius": "8px",
        "shadow": "0 10px 30px rgba(251,191,36,.2)",
        "custom_css": """
body{background:#0F0E1F;color:#FEF3C7}
.hero{background:radial-gradient(circle at 50% 0%,#312E81 0%,#0F0E1F 100%);color:#FEF3C7;text-align:center;padding:80px 0}
.hero::before{content:'★ ★ ★ ★ ★';display:block;color:#FBBF24;font-size:32px;letter-spacing:8px;margin-bottom:20px}
.hero h1{font-size:64px;font-weight:900;color:#FBBF24;font-family:'Reem Kufi',serif}
.testimonials{background:#0F0E1F;padding:80px 0!important}
.testimonial{background:rgba(251,191,36,.05);border:1px solid rgba(251,191,36,.2);border-radius:8px;padding:40px;font-size:20px;line-height:1.8;font-style:italic;border-right:6px solid #FBBF24}
.testimonial .author{color:#FBBF24;font-weight:900;margin-top:20px}
""",
    },
    "pricing_table": {
        "name": "جدول أسعار SaaS",
        "palette": {"primary": "#3B82F6", "secondary": "#1E3A8A", "accent": "#60A5FA", "bg": "#F8FAFC", "text": "#0F172A"},
        "font": "Cairo",
        "hero_image_q": "dashboard+saas+modern+blue",
        "hero_pattern": "linear-gradient(135deg,#3B82F6,#1E3A8A)",
        "radius": "12px",
        "shadow": "0 4px 6px rgba(59,130,246,.1)",
        "custom_css": """
body{background:#F8FAFC;color:#0F172A}
.hero{background:linear-gradient(135deg,#3B82F6 0%,#1E3A8A 100%);color:#fff;padding:80px 0 120px;clip-path:polygon(0 0,100% 0,100% 100%,0 90%)}
.hero h1{font-size:60px;font-weight:900}
.pricing,.pricing-table{background:#fff;padding:80px 0!important}
.pricing-card{background:#fff;border:2px solid #E2E8F0;border-radius:16px;padding:32px;transition:all .3s}
.pricing-card.featured{border-color:#3B82F6;background:linear-gradient(135deg,rgba(59,130,246,.05),rgba(255,255,255,1));transform:scale(1.05);box-shadow:0 25px 50px rgba(59,130,246,.2)}
.pricing-card .price{font-size:48px;color:#3B82F6;font-weight:900}
""",
    },
    "faq_heavy": {
        "name": "FAQ هادئ نعنعي",
        "palette": {"primary": "#14B8A6", "secondary": "#134E4A", "accent": "#5EEAD4", "bg": "#F0FDFA", "text": "#042F2E"},
        "font": "Almarai",
        "hero_image_q": "calm+question+document+teal",
        "hero_pattern": "linear-gradient(180deg,#F0FDFA,#CCFBF1)",
        "radius": "10px",
        "shadow": "0 4px 12px rgba(20,184,166,.15)",
        "custom_css": """
body{background:#F0FDFA;color:#042F2E;font-size:17px;line-height:1.8}
.hero{background:linear-gradient(180deg,#F0FDFA 0%,#CCFBF1 100%);padding:100px 0;text-align:center}
.hero h1{color:#134E4A;font-size:56px;font-weight:900}
.faq{background:#fff;padding:80px 0!important}
.faq .item{background:#F0FDFA;border-radius:10px;padding:24px 30px;margin-bottom:14px;border-right:4px solid #14B8A6;transition:all .3s}
.faq .item:hover{background:#CCFBF1;transform:translateX(-6px)}
.faq .item .q{font-weight:900;color:#134E4A;font-size:18px;margin-bottom:8px}
""",
    },
    "stats_numbers": {
        "name": "أرقام بنفسجي شركاتي",
        "palette": {"primary": "#7C3AED", "secondary": "#4C1D95", "accent": "#C4B5FD", "bg": "#FAF5FF", "text": "#2E1065"},
        "font": "Cairo",
        "hero_image_q": "corporate+building+success+purple",
        "hero_pattern": "linear-gradient(135deg,#7C3AED,#4C1D95)",
        "radius": "8px",
        "shadow": "0 20px 50px rgba(124,58,237,.3)",
        "custom_css": """
body{background:#FAF5FF;color:#2E1065}
.hero{background:linear-gradient(135deg,#7C3AED 0%,#4C1D95 100%);color:#fff;padding:120px 0;display:grid;grid-template-columns:1fr 1fr;align-items:center}
.hero::after{content:'';background:url('{IMG_2}') center/cover;opacity:.4;mix-blend-mode:overlay}
.hero h1{font-size:80px;font-weight:900;line-height:1}
.stats{background:#2E1065;color:#fff;padding:100px 0!important}
.stats .value{font-size:120px;font-weight:900;color:#C4B5FD;line-height:1;letter-spacing:-4px}
.stats .label{color:#A78BFA;font-size:14px;text-transform:uppercase;letter-spacing:3px;margin-top:10px}
""",
    },
    "location_map": {
        "name": "موقع ترابي محلي",
        "palette": {"primary": "#A16207", "secondary": "#FEF3C7", "accent": "#EAB308", "bg": "#FFFBEB", "text": "#451A03"},
        "font": "Tajawal",
        "hero_image_q": "local+shop+street+earthy+warm",
        "hero_pattern": "linear-gradient(135deg,#FFFBEB,#FEF3C7)",
        "radius": "16px",
        "shadow": "0 8px 20px rgba(161,98,7,.2)",
        "custom_css": """
body{background:#FFFBEB;color:#451A03}
.hero{background:linear-gradient(rgba(255,251,235,.7),rgba(254,243,199,.85)),url(IMG) center/cover;color:#451A03;padding:80px 0;text-align:center}
.hero h1{font-size:64px;font-weight:900;color:#451A03}
.hero h2{color:#A16207;font-size:24px}
.map_embed,.map{padding:0!important}
.map_embed iframe,.map iframe{height:500px;border:0;border-top:6px solid #A16207;border-bottom:6px solid #A16207}
.contact{background:#FEF3C7;padding:80px 0!important}
""",
    },
    "newsletter_first": {
        "name": "نشرة بريدية بنفسجية",
        "palette": {"primary": "#6366F1", "secondary": "#312E81", "accent": "#A5B4FC", "bg": "#FAFAFF", "text": "#1E1B4B"},
        "font": "Cairo",
        "hero_image_q": "newsletter+email+envelope+modern",
        "hero_pattern": "linear-gradient(135deg,#6366F1,#312E81)",
        "radius": "16px",
        "shadow": "0 15px 40px rgba(99,102,241,.25)",
        "custom_css": """
body{background:#FAFAFF;color:#1E1B4B}
.hero{background:linear-gradient(135deg,#6366F1 0%,#312E81 100%);color:#fff;padding:100px 0;text-align:center;position:relative}
.hero::before{content:'✉️';font-size:200px;position:absolute;left:5%;top:50%;transform:translateY(-50%);opacity:.1}
.hero h1{font-size:64px;font-weight:900}
.newsletter,.newsletter-card,.newsletter_section{background:linear-gradient(135deg,#6366F1,#312E81);color:#fff;padding:80px 40px!important;text-align:center;border-radius:32px;margin:40px 24px}
.newsletter input,.newsletter_section input{background:#fff;color:#1E1B4B;border-radius:100px;padding:18px 30px;width:400px;font-size:18px;border:0;max-width:80%}
""",
    },
    "product_dense": {
        "name": "منتجات Pinterest",
        "palette": {"primary": "#E11D48", "secondary": "#881337", "accent": "#FECDD3", "bg": "#FFFFFF", "text": "#0c0a09"},
        "font": "Tajawal",
        "hero_image_q": "products+grid+pinterest+colorful",
        "hero_pattern": "#FFFFFF",
        "radius": "16px",
        "shadow": "0 10px 30px rgba(225,29,72,.15)",
        "custom_css": """
body{background:#fff;color:#0c0a09}
.hero{background:url(IMG) center/cover;min-height:60vh;padding:80px 0;color:#fff;position:relative}
.hero::before{content:'';position:absolute;inset:0;background:linear-gradient(180deg,rgba(225,29,72,.7),rgba(136,19,55,.9))}
.hero .container{position:relative;z-index:1}
.hero h1{font-size:72px;font-weight:900}
.product-grid,.product_grid_filters{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:16px;padding:20px}
.product-card{background:#fff;border-radius:16px;overflow:hidden;border:0;box-shadow:0 4px 12px rgba(0,0,0,.08);transition:all .3s}
.product-card:hover{transform:translateY(-4px);box-shadow:0 25px 50px rgba(225,29,72,.2)}
.product-card img{aspect-ratio:1;object-fit:cover}
.btn-primary{background:#E11D48;color:#fff;border-radius:100px}
""",
    },
    # ════════════════════════════════════════════════════════════════════
    # 🆕 5 PREMIUM TEMPLATES — كل قالب عالم بصري مستقل بهوية فريدة
    # ════════════════════════════════════════════════════════════════════
    "beauty_megamart": {
        "name": "متجر الجمال الفاخر",
        "palette": {"primary": "#E91E63", "secondary": "#4A1D5C", "accent": "#FF8AB1", "bg": "#FFF5F8", "text": "#2D0A28"},
        "font": "Tajawal",
        "hero_image_q": "beauty+products+pink+lifestyle",
        "hero_pattern": "linear-gradient(135deg,#FFF5F8,#FFE0EC)",
        "radius": "18px",
        "shadow": "0 20px 50px rgba(233,30,99,.2)",
        "custom_css": """
body{background:#FFF5F8!important;color:#2D0A28!important;font-family:'Tajawal',sans-serif!important}
header,.site-header,nav{background:#4A1D5C!important;color:#fff!important;border-bottom:4px solid #E91E63!important}
header a,.site-header a,nav a{color:#fff!important;font-weight:700}
/* HERO with vibrant promo cards style */
.hero,section.hero{background:linear-gradient(135deg,#FFF5F8 0%,#FFE0EC 100%)!important;color:#2D0A28!important;padding:40px 20px!important;position:relative;overflow:visible}
.hero::before{content:'';position:absolute;top:30px;right:6%;width:300px;height:120px;background:linear-gradient(135deg,#E91E63,#FF8AB1);border-radius:24px;box-shadow:0 15px 40px rgba(233,30,99,.4);z-index:0;display:flex;align-items:center;justify-content:center;color:#fff;font-weight:900;font-size:22px;font-family:Tajawal}
.hero::after{content:'⏳ عروض حصرية ⏳';position:absolute;top:30px;right:6%;width:300px;height:120px;display:flex;align-items:center;justify-content:center;color:#fff;font-weight:900;font-size:22px;z-index:1;pointer-events:none;letter-spacing:1px}
.hero .container{max-width:1280px;margin:0 auto;padding:0 20px;position:relative;z-index:2;display:grid!important;grid-template-columns:1fr 1.3fr!important;gap:40px;align-items:center;min-height:480px}
.hero .hero-copy{background:linear-gradient(135deg,#4A1D5C 0%,#7A1F66 100%);padding:50px 36px;border-radius:24px;color:#fff;box-shadow:0 25px 60px rgba(74,29,92,.4)}
.hero .hero-copy h1{color:#fff!important;font-size:38px!important;font-weight:900;line-height:1.15;margin-bottom:12px}
.hero .hero-copy p{color:#FFE0EC!important;font-size:16px;line-height:1.6;margin-bottom:24px}
.hero .hero-media{border-radius:24px;overflow:hidden;box-shadow:0 30px 70px rgba(74,29,92,.3);min-height:420px;background:url('{IMG_1}') center/cover;position:relative}
.hero .hero-media img{display:none}
.hero .hero-media::before{content:'⏰ 00 : 00 : 00 : 00';position:absolute;top:24px;right:24px;background:rgba(0,0,0,.6);backdrop-filter:blur(10px);padding:10px 20px;border-radius:100px;color:#fff;font-weight:900;font-size:14px;letter-spacing:2px}
.hero .hero-media::after{content:'🛍️ تسوّق الآن';position:absolute;bottom:30px;right:30px;background:#2D0A28;color:#fff;padding:14px 28px;border-radius:100px;font-weight:900;box-shadow:0 10px 25px rgba(0,0,0,.4)}
/* Buttons everywhere */
.btn,.btn-primary,a.btn{background:#2D0A28!important;color:#fff!important;border-radius:100px!important;padding:14px 32px!important;font-weight:900!important;border:0!important;font-size:14px;letter-spacing:1px;box-shadow:0 8px 20px rgba(45,10,40,.4)!important;transition:all .3s}
.btn:hover,.btn-primary:hover{transform:translateY(-2px);background:#E91E63!important;box-shadow:0 15px 30px rgba(233,30,99,.5)!important}
/* Sections */
section{background:#FFF5F8;color:#2D0A28;padding:70px 20px!important}
section h2{color:#4A1D5C!important;font-size:36px!important;font-weight:900;text-align:center;margin-bottom:40px;position:relative}
section h2::after{content:'';display:block;width:80px;height:4px;background:linear-gradient(90deg,#E91E63,#FF8AB1);margin:16px auto 0;border-radius:100px}
/* Features = service strip dark purple */
.features{background:#4A1D5C!important;color:#fff!important;padding:50px 20px!important}
.features h2{color:#FF8AB1!important}
.features .feature-card{background:rgba(255,255,255,.06)!important;border:1px solid rgba(255,138,177,.25)!important;border-radius:16px!important;color:#fff!important}
.features .feature-card h3{color:#FF8AB1!important}
.features .feature-card p{color:#FFE0EC!important}
/* Team circles get pink borders */
.team-circles .container > div > div[style*="border-radius:50%"]{border-color:#E91E63!important;border-width:4px!important;box-shadow:0 10px 25px rgba(233,30,99,.3)!important}
.team-circles h3{color:#4A1D5C!important;font-weight:900!important}
.team-circles p{color:#7A1F66!important}
/* Products on white */
.products,.product-grid,.product_grid_filters{background:#fff!important;padding:60px 20px!important}
.product-card{background:#fff!important;border:1px solid #FFE0EC!important;border-radius:16px!important;box-shadow:0 4px 12px rgba(74,29,92,.08)!important;transition:all .3s}
.product-card:hover{border-color:#E91E63!important;transform:translateY(-4px);box-shadow:0 25px 50px rgba(233,30,99,.2)!important}
.product-card .price{color:#E91E63!important;font-weight:900!important;font-size:20px!important}
/* Testimonials */
.testimonials{background:#FFF5F8!important}
.testimonial-card,.testimonial{background:#fff!important;border:1px solid #FFE0EC!important;border-radius:20px!important;color:#2D0A28!important}
/* Footer */
footer{background:#4A1D5C!important;color:#FFE0EC!important;border-top:4px solid #E91E63!important}
@media(max-width:900px){.hero .container{grid-template-columns:1fr!important}.hero::before,.hero::after{display:none}.hero .hero-copy h1{font-size:28px!important}}
""",
    },
    "realestate_luxury_dark": {
        "name": "عقارات فاخرة كحلية",
        "palette": {"primary": "#B87333", "secondary": "#000000", "accent": "#D4A574", "bg": "#0A0A0A", "text": "#F5F0E8"},
        "font": "Reem Kufi",
        "hero_image_q": "luxury+architecture+building+night",
        "hero_pattern": "#000",
        "radius": "8px",
        "shadow": "0 25px 60px rgba(0,0,0,.6)",
        "custom_css": """
body{background:#0A0A0A!important;color:#F5F0E8!important;font-family:'Reem Kufi',serif!important}
header,.site-header,nav{background:#0A0A0A!important;border-bottom:1px solid rgba(184,115,51,.2)!important;color:#F5F0E8!important;padding:18px 0;position:relative}
header a,.site-header a,nav a{color:#F5F0E8!important;letter-spacing:1.5px;font-size:13px;text-transform:uppercase;opacity:.85}
header a:hover,.site-header a:hover{color:#D4A574!important;opacity:1}
/* HERO — leverages built-in hero-form layout, just restyle it */
.hero,.hero-form{background-image:linear-gradient(135deg,rgba(0,0,0,.85) 0%,rgba(20,15,10,.65) 100%),url('{IMG_1}')!important;background-size:cover!important;background-position:center!important;color:#F5F0E8!important;min-height:90vh;display:flex;align-items:center;position:relative;overflow:hidden;padding:60px 30px!important}
.hero::before{content:'';position:absolute;top:0;left:0;width:55%;height:100%;background:url('{IMG_2}') center/cover;opacity:.55;clip-path:polygon(20% 0,100% 0,100% 100%,0 100%);filter:contrast(1.25) brightness(.55) sepia(.2);pointer-events:none}
.hero::after{content:'🦁';position:absolute;top:24px;left:50%;transform:translateX(-50%);width:60px;height:60px;display:flex;align-items:center;justify-content:center;font-size:30px;background:radial-gradient(circle,#B87333,#7a4a1f);border:2px solid #D4A574;border-radius:50%;box-shadow:0 0 30px rgba(184,115,51,.6);z-index:10}
.hero .container{position:relative;z-index:2;max-width:1280px}
.hero-form-grid{grid-template-columns:1.2fr 1fr!important;gap:60px!important}
.hero-form-copy h1,.hero h1{font-size:54px!important;font-weight:900!important;color:#F5F0E8!important;line-height:1.05;letter-spacing:-1px;margin-bottom:14px}
.hero-form-copy p,.hero p{color:#D4A574!important;font-size:16px;line-height:1.6}
.hero-form-box{background:rgba(15,10,8,.92)!important;border:1px solid rgba(184,115,51,.4)!important;border-radius:20px!important;padding:32px!important;backdrop-filter:blur(20px);box-shadow:0 30px 80px rgba(0,0,0,.6)!important}
.hero-form-box h3{color:#D4A574!important;letter-spacing:2px;text-transform:uppercase;font-size:14px;margin-bottom:20px;border-bottom:1px solid rgba(184,115,51,.3);padding-bottom:12px}
.hero-form-box input{background:rgba(184,115,51,.08)!important;border:1px solid rgba(184,115,51,.3)!important;color:#F5F0E8!important;border-radius:8px!important;padding:14px 16px!important;width:100%!important;margin-bottom:12px;font-family:'Reem Kufi',serif}
.hero-form-box input::placeholder{color:rgba(212,165,116,.5)}
/* Buttons — copper pill */
.btn,.btn-primary,a.btn,button.btn{background:linear-gradient(135deg,#B87333,#D4A574)!important;color:#0A0A0A!important;border-radius:100px!important;padding:14px 36px!important;font-weight:900!important;border:0!important;letter-spacing:2px;text-transform:uppercase;font-size:13px;box-shadow:0 10px 30px rgba(184,115,51,.4)!important}
.btn:hover,.btn-primary:hover{transform:translateY(-3px);box-shadow:0 20px 40px rgba(212,165,116,.55)!important}
/* Sections */
section{background:#0A0A0A!important;color:#F5F0E8!important;padding:80px 30px!important;border-top:1px solid rgba(184,115,51,.1)}
section h2{color:#D4A574!important;text-align:center;letter-spacing:3px;font-weight:300;text-transform:uppercase;font-size:14px;margin-bottom:8px}
section h2::after{content:'';display:block;width:60px;height:1px;background:#B87333;margin:14px auto 28px}
/* Gallery — Lifestyle */
.gallery .gallery-grid{gap:14px}
.gallery-item,.gallery .gallery-item{border-radius:8px!important;filter:brightness(.85) contrast(1.05) sepia(.15);transition:all .4s;border:1px solid rgba(184,115,51,.2)!important;aspect-ratio:1}
.gallery-item:hover{filter:brightness(1) contrast(1.1);border-color:#B87333!important;transform:translateY(-4px)}
/* Team rows */
.team-rows .container > div > div{background:linear-gradient(180deg,rgba(184,115,51,.08),rgba(0,0,0,.5))!important;border:1px solid rgba(184,115,51,.25)!important;border-radius:8px!important}
.team-rows .container > div > div:hover{border-color:#B87333!important}
.team-rows h3{color:#D4A574!important;font-weight:700!important}
.team-rows p{color:rgba(245,240,232,.6)!important;letter-spacing:1px}
/* Features — Exclusive Projects cards */
.features .feature-grid{gap:18px}
.features .feature-card{background:linear-gradient(180deg,rgba(184,115,51,.08),rgba(0,0,0,.6))!important;border:1px solid rgba(184,115,51,.25)!important;border-radius:8px!important;padding:28px 22px!important;color:#F5F0E8!important;transition:all .3s}
.features .feature-card:hover{border-color:#B87333!important;transform:translateY(-4px);box-shadow:0 25px 60px rgba(184,115,51,.3)!important}
.features .feature-icon{font-size:48px;color:#D4A574!important;margin-bottom:12px}
.features .feature-card h3{color:#F5F0E8!important;font-size:18px}
.features .feature-card p{color:rgba(245,240,232,.55)!important;font-size:13px}
.contact{background:#0A0A0A!important}
footer{background:#000!important;border-top:1px solid rgba(184,115,51,.3)!important;color:#D4A574!important;padding:40px 30px!important}
@media(max-width:900px){.hero-form-grid{grid-template-columns:1fr!important;gap:30px!important}.hero-form-copy h1,.hero h1{font-size:38px!important}}
""",
    },
    "editorial_diagonal": {
        "name": "مجلة قطرية",
        "palette": {"primary": "#00D9FF", "secondary": "#1A1A1A", "accent": "#F5F5F0", "bg": "#0E0E0E", "text": "#F5F5F0"},
        "font": "Reem Kufi",
        "hero_image_q": "editorial+magazine+architecture+contrast",
        "hero_pattern": "#0E0E0E",
        "radius": "0px",
        "shadow": "none",
        "custom_css": """
body{background:#0E0E0E;color:#F5F5F0;font-family:'Reem Kufi',serif}
/* Hero — diagonal split image + text */
.hero{background:#0E0E0E;color:#F5F5F0;min-height:100vh;display:flex;align-items:center;position:relative;overflow:hidden;padding:0}
.hero::before{content:'';position:absolute;top:0;right:0;width:55%;height:100%;background:url('{IMG_1}') center/cover;clip-path:polygon(20% 0,100% 0,100% 100%,0 100%);filter:contrast(1.15) saturate(.85)}
.hero::after{content:'';position:absolute;top:0;right:0;width:55%;height:100%;background:linear-gradient(135deg,rgba(0,217,255,.15) 0%,transparent 50%);clip-path:polygon(20% 0,100% 0,100% 100%,0 100%)}
.hero .container{position:relative;z-index:2;max-width:1200px;padding:0 60px;width:100%}
.hero h1{font-size:104px;font-weight:900;line-height:.95;letter-spacing:-3px;font-family:'Playfair Display','Reem Kufi',serif;color:#F5F5F0;max-width:55%;text-shadow:0 0 60px rgba(0,0,0,.5)}
.hero h1::first-letter{color:#00D9FF;font-style:italic}
.hero h2{font-size:16px;letter-spacing:6px;text-transform:uppercase;color:#00D9FF;font-weight:400;margin-bottom:24px;display:inline-block;border-top:1px solid #00D9FF;border-bottom:1px solid #00D9FF;padding:8px 0}
/* Buttons — outlined sharp rectangles */
.btn,.btn-primary{background:transparent!important;color:#00D9FF!important;border:2px solid #00D9FF;border-radius:0;padding:16px 44px;font-weight:700;letter-spacing:3px;text-transform:uppercase;font-size:13px;transition:all .3s;position:relative;overflow:hidden}
.btn::before,.btn-primary::before{content:'';position:absolute;inset:0;background:#00D9FF;transform:translateX(-100%);transition:transform .3s}
.btn:hover,.btn-primary:hover{color:#0E0E0E!important}
.btn:hover::before,.btn-primary:hover::before{transform:translateX(0)}
.btn span,.btn-primary span{position:relative;z-index:1}
/* Numbered sections + diagonal cuts */
section{background:#0E0E0E;color:#F5F5F0;padding:120px 0!important;position:relative;border-top:1px solid rgba(0,217,255,.1)}
section:nth-child(even){background:#1A1A1A}
section .container{max-width:1200px;padding:0 60px;position:relative}
section h2.title,section .section-title,section h2{font-size:64px;font-weight:900;color:#F5F5F0;letter-spacing:-1.5px;font-family:'Playfair Display','Reem Kufi',serif;margin-bottom:60px;position:relative;padding-right:120px}
section h2::before,section .section-title::before{content:counter(section,decimal-leading-zero) '.';counter-increment:section;position:absolute;right:0;top:50%;transform:translateY(-50%);font-size:120px;color:transparent;-webkit-text-stroke:1px #00D9FF;font-weight:900;line-height:1;opacity:.7}
body{counter-reset:section}
/* Galleries with diagonal masks */
.gallery,.gallery-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:24px}
.gallery img,.gallery-grid img{filter:contrast(1.15) saturate(.9);clip-path:polygon(0 5%,100% 0,95% 100%,0 95%);transition:all .4s}
.gallery img:hover,.gallery-grid img:hover{clip-path:polygon(0 0,100% 0,100% 100%,0 100%);filter:contrast(1.1) saturate(1.1)}
/* Cards — sharp angled corners */
.feature-card,.product-card,.testimonial,.team-card{background:#1A1A1A;border:1px solid rgba(0,217,255,.2);border-radius:0;padding:36px;clip-path:polygon(0 0,100% 0,100% calc(100% - 20px),calc(100% - 20px) 100%,0 100%);transition:all .3s}
.feature-card:hover,.product-card:hover,.testimonial:hover{border-color:#00D9FF;background:#1F1F1F}
.feature-card h3,.product-card h3{color:#00D9FF;font-size:24px;font-weight:900;margin-bottom:12px;font-family:'Playfair Display','Reem Kufi',serif}
/* Quote — magazine pull-quote style */
.quote,.quote_big{background:#0E0E0E;color:#F5F5F0;text-align:center;padding:160px 60px!important;font-family:'Playfair Display',serif;font-style:italic;font-size:48px;line-height:1.4;letter-spacing:-1px;position:relative}
.quote::before,.quote_big::before{content:'"';font-size:240px;line-height:.5;color:#00D9FF;position:absolute;top:120px;right:50%;transform:translateX(50%)}
footer{background:#0E0E0E;border-top:1px solid #00D9FF;padding:50px 0!important;color:rgba(245,245,240,.6)}
@media(max-width:900px){.hero h1{font-size:56px;max-width:100%}.hero::before{width:100%;clip-path:none;opacity:.3}section h2{font-size:36px;padding-right:0}section h2::before{display:none}.gallery{grid-template-columns:1fr}}
""",
    },
    "organic_blobs": {
        "name": "عضوي ترابي دافئ",
        "palette": {"primary": "#C65D3E", "secondary": "#F5E6D3", "accent": "#95A572", "bg": "#FAF3E7", "text": "#3D2817"},
        "font": "Amiri",
        "hero_image_q": "organic+pottery+craft+earth+warm",
        "hero_pattern": "linear-gradient(135deg,#FAF3E7,#F5E6D3)",
        "radius": "60% 40% 30% 70% / 60% 30% 70% 40%",
        "shadow": "0 20px 50px rgba(198,93,62,.2)",
        "custom_css": """
body{background:#FAF3E7;color:#3D2817;font-family:'Amiri',serif;font-size:17px;line-height:1.7}
/* Soft watercolor background blobs */
body::before{content:'';position:fixed;top:-200px;right:-100px;width:600px;height:600px;background:radial-gradient(circle,rgba(198,93,62,.15) 0%,transparent 70%);border-radius:50%;z-index:-1;pointer-events:none}
body::after{content:'';position:fixed;bottom:-100px;left:-200px;width:500px;height:500px;background:radial-gradient(circle,rgba(149,165,114,.12) 0%,transparent 70%);border-radius:50%;z-index:-1;pointer-events:none}
header,.site-header{background:transparent;padding:30px 0}
header a,.site-header a{color:#3D2817!important;font-family:'Amiri',serif;font-weight:700;font-size:17px}
/* HERO — organic blob image */
.hero{background:linear-gradient(135deg,#FAF3E7 0%,#F5E6D3 100%);color:#3D2817;padding:60px 40px;min-height:80vh;display:flex;align-items:center;position:relative;overflow:hidden}
.hero .container{display:grid;grid-template-columns:1.1fr .9fr;gap:80px;align-items:center;max-width:1200px;margin:0 auto;width:100%}
.hero h1{font-family:'Amiri',serif;font-size:84px;font-weight:700;line-height:1.05;color:#3D2817;letter-spacing:-1px;margin-bottom:24px}
.hero h1::after{content:'';display:block;width:120px;height:4px;background:linear-gradient(90deg,#C65D3E,#95A572);margin-top:24px;border-radius:100px}
.hero h2{font-size:22px;color:#7A4226;font-style:italic;margin-bottom:30px;line-height:1.6;font-weight:400}
.hero::after{content:'';position:absolute;top:50%;left:0;transform:translateY(-50%);width:45%;height:75%;background:url('{IMG_1}') center/cover;border-radius:60% 40% 35% 65% / 55% 35% 65% 45%;box-shadow:0 30px 80px rgba(198,93,62,.35);animation:blob-shift 15s ease-in-out infinite}
@keyframes blob-shift{0%,100%{border-radius:60% 40% 35% 65% / 55% 35% 65% 45%}33%{border-radius:40% 60% 65% 35% / 35% 65% 35% 65%}66%{border-radius:50% 50% 45% 55% / 65% 50% 50% 35%}}
/* Buttons — extra rounded organic */
.btn,.btn-primary{background:#C65D3E!important;color:#FAF3E7!important;border-radius:100px;padding:18px 42px;font-weight:700;border:0;font-size:16px;font-family:'Amiri',serif;box-shadow:0 12px 30px rgba(198,93,62,.35);transition:all .3s}
.btn:hover,.btn-primary:hover{transform:translateY(-3px);background:#95A572!important;box-shadow:0 20px 40px rgba(149,165,114,.4)}
/* Sections — soft generous padding */
section{background:transparent;color:#3D2817;padding:120px 40px!important;position:relative;border:0}
section h2{font-family:'Amiri',serif;font-size:56px;font-weight:700;color:#3D2817;text-align:center;margin-bottom:60px;letter-spacing:-.5px}
section h2::after{content:'❀';display:block;font-size:32px;color:#C65D3E;margin-top:16px}
/* All images get organic blob shapes */
.gallery img,.gallery-grid img,.product-card img,.team-photo,.about img,.feature-card img{border-radius:55% 45% 50% 50% / 50% 60% 40% 50%!important;transition:border-radius .8s}
.gallery img:hover,.gallery-grid img:hover{border-radius:30% 70% 60% 40% / 40% 50% 50% 60%!important}
/* Cards — soft cream with rounded everything */
.feature-card,.product-card,.testimonial,.team-card{background:#fff;border:0;border-radius:32px;padding:36px;box-shadow:0 15px 40px rgba(198,93,62,.1);transition:all .4s}
.feature-card:hover,.product-card:hover,.testimonial:hover{transform:translateY(-8px);box-shadow:0 30px 60px rgba(198,93,62,.2)}
.feature-card h3,.product-card h3,.testimonial .author,.team-card h3{color:#C65D3E;font-family:'Amiri',serif;font-size:24px;font-weight:700}
.product-card .price{color:#95A572;font-size:24px;font-weight:700}
/* Testimonials — quote-styled */
.testimonial{font-family:'Amiri',serif;font-style:italic;font-size:18px;line-height:1.8;border-right:6px solid #95A572;background:linear-gradient(135deg,#fff,#FAF3E7)}
/* Gallery in grid with varied border-radius per image */
.gallery,.gallery-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:32px;padding:0!important}
.gallery img:nth-child(3n+1),.gallery-grid img:nth-child(3n+1){border-radius:60% 40% 30% 70% / 60% 30% 70% 40%!important}
.gallery img:nth-child(3n+2),.gallery-grid img:nth-child(3n+2){border-radius:30% 70% 70% 30% / 30% 30% 70% 70%!important}
.gallery img:nth-child(3n),.gallery-grid img:nth-child(3n){border-radius:50% 50% 30% 70% / 60% 40% 60% 40%!important}
footer{background:#3D2817;color:#F5E6D3;padding:60px 40px!important;border-radius:80px 80px 0 0;margin-top:80px;font-family:'Amiri',serif}
@media(max-width:900px){.hero .container{grid-template-columns:1fr}.hero::after{position:relative;top:0;left:0;transform:none;width:100%;height:300px;margin-bottom:30px}.hero h1{font-size:54px}}
""",
    },
    "cyber_glitch": {
        "name": "سايبر نيون مستقبلي",
        "palette": {"primary": "#00FF88", "secondary": "#000000", "accent": "#FF0099", "bg": "#000000", "text": "#00FF88"},
        "font": "Cairo",
        "hero_image_q": "cyberpunk+neon+tech+futuristic",
        "hero_pattern": "#000",
        "radius": "0px",
        "shadow": "0 0 40px rgba(0,255,136,.6)",
        "custom_css": """
body{background:#000;color:#00FF88;font-family:'Cairo',monospace;position:relative;overflow-x:hidden}
/* Scan lines overlay */
body::before{content:'';position:fixed;inset:0;background:repeating-linear-gradient(0deg,rgba(0,255,136,.03) 0,rgba(0,255,136,.03) 1px,transparent 1px,transparent 4px);pointer-events:none;z-index:1000;mix-blend-mode:screen}
/* Grid background */
body::after{content:'';position:fixed;inset:0;background-image:linear-gradient(rgba(0,255,136,.05) 1px,transparent 1px),linear-gradient(90deg,rgba(0,255,136,.05) 1px,transparent 1px);background-size:50px 50px;pointer-events:none;z-index:-1;mask-image:radial-gradient(ellipse at center,#000 30%,transparent 80%)}
header,.site-header{background:#000;border-bottom:1px solid #00FF88;padding:20px 0;font-family:'Courier New',monospace;letter-spacing:2px}
header a,.site-header a{color:#00FF88!important;text-transform:uppercase;font-size:12px;letter-spacing:3px;font-weight:700;transition:all .2s}
header a:hover,.site-header a:hover{color:#FF0099!important;text-shadow:0 0 10px #FF0099}
/* HERO — full glitch */
.hero{background:#000;color:#00FF88;min-height:100vh;display:flex;align-items:center;position:relative;overflow:hidden;padding:80px 40px}
.hero::before{content:'';position:absolute;inset:0;background:url('{IMG_1}') center/cover;opacity:.25;mix-blend-mode:lighten;filter:hue-rotate(80deg) saturate(2)}
.hero .container{position:relative;z-index:2;max-width:1100px;margin:0 auto;width:100%}
.hero h1{font-size:120px;font-weight:900;line-height:.95;color:#00FF88;text-transform:uppercase;letter-spacing:-3px;text-shadow:3px 0 0 #FF0099,-3px 0 0 #00D9FF,0 0 40px rgba(0,255,136,.6);font-family:'Cairo','Courier New',monospace;animation:glitch 4s infinite}
@keyframes glitch{0%,90%,100%{text-shadow:3px 0 0 #FF0099,-3px 0 0 #00D9FF,0 0 40px rgba(0,255,136,.6)}92%{text-shadow:-3px 0 0 #FF0099,3px 0 0 #00D9FF,0 0 40px rgba(0,255,136,.6);transform:translate(2px,0)}94%{text-shadow:5px 0 0 #FF0099,-5px 0 0 #00D9FF;transform:translate(-2px,1px)}}
.hero h2{font-family:'Courier New',monospace;color:#FF0099;font-size:14px;letter-spacing:8px;text-transform:uppercase;border:1px solid #FF0099;display:inline-block;padding:8px 20px;margin-bottom:30px;clip-path:polygon(0 0,calc(100% - 12px) 0,100% 12px,100% 100%,12px 100%,0 calc(100% - 12px))}
/* Buttons — hexagonal angular */
.btn,.btn-primary{background:transparent!important;color:#00FF88!important;border:2px solid #00FF88;border-radius:0;padding:18px 44px;font-weight:900;letter-spacing:4px;text-transform:uppercase;font-size:13px;font-family:'Courier New',monospace;clip-path:polygon(8% 0,100% 0,92% 100%,0 100%);transition:all .3s;text-shadow:0 0 10px rgba(0,255,136,.6)}
.btn:hover,.btn-primary:hover{background:#00FF88!important;color:#000!important;box-shadow:0 0 30px #00FF88,inset 0 0 20px rgba(0,0,0,.3)}
/* Sections */
section{background:#000;color:#00FF88;padding:100px 40px!important;border-top:1px solid rgba(0,255,136,.2);position:relative}
section::before{content:'';position:absolute;top:0;left:5%;width:40px;height:2px;background:#FF0099;box-shadow:0 0 10px #FF0099}
section h2{font-family:'Courier New',monospace;color:#00FF88;font-size:42px;text-transform:uppercase;letter-spacing:6px;text-align:center;margin-bottom:60px;text-shadow:0 0 20px rgba(0,255,136,.5)}
section h2::before{content:'> ';color:#FF0099}
/* Stats — ASCII-style boxes */
.stats{background:#000;padding:80px 40px!important}
.stats .container{display:grid;grid-template-columns:repeat(4,1fr);gap:24px;max-width:1200px;margin:0 auto}
.stats .item{background:rgba(0,255,136,.03);border:1px solid #00FF88;padding:40px 20px;text-align:center;clip-path:polygon(10px 0,100% 0,calc(100% - 10px) 100%,0 100%);transition:all .3s}
.stats .item:hover{background:rgba(0,255,136,.1);box-shadow:inset 0 0 30px rgba(0,255,136,.3)}
.stats .value,.stats .number{font-family:'Courier New',monospace;color:#00FF88;font-size:64px;font-weight:900;letter-spacing:-2px;text-shadow:0 0 30px rgba(0,255,136,.8);line-height:1}
.stats .label{font-family:'Courier New',monospace;color:#FF0099;font-size:11px;letter-spacing:4px;text-transform:uppercase;margin-top:12px}
/* Cards — angular hex corners */
.feature-card,.product-card,.testimonial,.team-card{background:rgba(0,255,136,.03);border:1px solid #00FF88;border-radius:0;padding:36px;clip-path:polygon(15px 0,100% 0,100% calc(100% - 15px),calc(100% - 15px) 100%,0 100%,0 15px);transition:all .3s;font-family:'Cairo',sans-serif}
.feature-card:hover,.product-card:hover{background:rgba(0,255,136,.08);box-shadow:0 0 40px rgba(0,255,136,.4),inset 0 0 20px rgba(0,255,136,.1);border-color:#FF0099}
.feature-card h3,.product-card h3{color:#FF0099;font-family:'Courier New',monospace;letter-spacing:2px;text-transform:uppercase;font-size:18px}
.feature-card p,.product-card p{color:rgba(0,255,136,.7);font-size:14px}
/* Footer */
footer{background:#000;border-top:1px solid #00FF88;padding:40px 0!important;color:#00FF88;font-family:'Courier New',monospace;font-size:13px;letter-spacing:1px}
footer::before{content:'> SYSTEM ONLINE_';display:block;text-align:center;color:#FF0099;font-size:11px;letter-spacing:4px;margin-bottom:20px;animation:blink 1s infinite}
@keyframes blink{0%,49%{opacity:1}50%,100%{opacity:.3}}
@media(max-width:900px){.hero h1{font-size:64px}.stats .container{grid-template-columns:1fr 1fr}}
""",
    },
}


# ─── Hero image library — 20 unique queries × multiple categories ────
def get_hero_image_for(category_id: str, archetype_id: str) -> str:
    """Return a unique image URL from the curated category library — different image
    for each (category, archetype) pair, deterministic so renders are stable."""
    try:
        from .category_images import pick_images_for_archetype
        imgs = pick_images_for_archetype(category_id, archetype_id, count=1)
        return imgs[0]
    except Exception:
        # Fallback to source.unsplash query
        cat_kw = {
            "restaurant": "restaurant+food", "coffee": "cafe+coffee", "store": "shop+products",
            "cosmetics": "cosmetics+makeup", "automotive": "luxury+cars", "realestate": "luxury+architecture",
        }.get(category_id, "modern")
        return f"https://source.unsplash.com/1600x900/?{cat_kw}"


def apply_archetype_theme(archetype_id: str, category_id: str, base_theme: dict) -> dict:
    """Merge per-archetype palette + font + hero image + custom CSS into the base theme.
    Also pre-fills {IMG_1}..{IMG_4} placeholders in custom_css with category-specific
    photos so each archetype within the same category shows different relevant imagery."""
    spec = ARCHETYPE_THEMES.get(archetype_id)
    if not spec:
        return base_theme
    theme = dict(base_theme)
    pal = spec.get("palette", {})
    theme.update({
        "primary": pal.get("primary", theme.get("primary")),
        "secondary": pal.get("secondary", theme.get("secondary")),
        "accent": pal.get("accent", theme.get("accent")),
        "background": pal.get("bg", theme.get("background", theme.get("bg"))),
        "bg": pal.get("bg", theme.get("bg")),
        "text": pal.get("text", theme.get("text")),
        "font": spec.get("font", theme.get("font")),
        "radius": spec.get("radius", theme.get("radius")),
    })
    hero_img = get_hero_image_for(category_id, archetype_id)
    custom = spec.get("custom_css") or ""
    # Pre-substitute {IMG_n} tokens with category-specific images (BEFORE generic IMG to avoid breaking them)
    try:
        from .category_images import pick_images_for_archetype
        imgs = pick_images_for_archetype(category_id, archetype_id, count=4)
        custom = (custom.replace("{IMG_1}", imgs[0])
                        .replace("{IMG_2}", imgs[1])
                        .replace("{IMG_3}", imgs[2])
                        .replace("{IMG_4}", imgs[3]))
    except Exception:
        pass
    # Generic IMG token (legacy) — replaced AFTER {IMG_n} so it doesn't corrupt them
    custom = custom.replace("url(IMG)", f"url({hero_img})").replace("(IMG)", f"({hero_img})")
    existing_css = theme.get("custom_css") or ""
    theme["custom_css"] = existing_css + "\n" + custom
    theme["_archetype_theme_name"] = spec.get("name", archetype_id)
    theme["_hero_image"] = hero_img
    return theme
