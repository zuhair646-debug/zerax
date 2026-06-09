import React from 'react';
import { Navbar, ZeraxLogo } from '@/components/Navbar';
import { Button } from '@/components/ui/button';
import { useNavigate } from 'react-router-dom';
import { Sparkles, HelpCircle, X, Check, AlertTriangle, Target } from 'lucide-react';
import SiteBannerStories from '@/components/SiteBannerStories';
import HeroBanner from '@/components/HeroBanner';

// ─── Detailed info for every card (opens in modal when user clicks the (?) icon) ───
const cardInfo = {
  'website-freebuild': {
    title: 'إنشاء موقع من الصفر — FreeBuild',
    description: 'محرّك ذكي يبني لك موقعاً كاملاً من فكرة واحدة — تكلّم مع الذكاء الاصطناعي بلغتك، ويولّد لك تصميم حصري ١٠٠٪ (مش قالب جاهز).',
    features: [
      'تصميم فريد لكل موقع (مافي تكرار)',
      'محادثة طبيعية — قل وصفك بكلام عادي',
      'يعدّل لك بشكل مباشر — "كبّر الزر"، "غيّر اللون"',
      'يدعم تجارة إلكترونية + مدفوعات Stripe',
      'استضافة وSSL مجاناً'
    ],
    drawbacks: [
      'يحتاج وضوح في الفكرة (وصف جيّد = نتيجة أفضل)',
      'أبطأ من القوالب الجاهزة (٥-١٠ دقائق للموقع الأول)'
    ],
    bestFor: 'لمن يبي موقعاً حصرياً يميّزه عن المنافسين، أو فكرة جديدة مالها قالب جاهز.',
  },
  'website-template': {
    title: 'مواقع جاهزة — ٢٥ قالب',
    description: '٢٥ قالب احترافي مصمّم مسبقاً لقطاعات مختلفة (مطاعم، عيادات، عقارات، تجارة، خدمات...). اختر قالباً، خصّص الألوان والمحتوى، وانشره في دقائق.',
    features: [
      'انشر موقعك في ٥ دقائق',
      'قوالب جاهزة لكل قطاع',
      'تحرير سهل بدون خبرة',
      'متجاوب مع الجوّال تلقائياً',
      'مدفوعات + حجوزات مدمجة'
    ],
    drawbacks: [
      'أقل حصرية من FreeBuild (الناس راح يشوفون قوالب مشابهة)',
      'مرونة محدودة في التصميم'
    ],
    bestFor: 'لمن يبي موقعاً سريعاً ومحترفاً بدون تخصيص عميق — مثالي لأصحاب الأعمال الصغيرة.',
  },
  'app-builder': {
    title: 'إنشاء تطبيق من الصفر',
    description: 'بناء تطبيقات جوّال احترافية بـReact Native / Flutter / Native — من فكرة إلى APK جاهز للنشر على Google Play وApp Store.',
    features: [
      'يدعم Android + iOS من نفس الكود',
      'واجهات حديثة (Material 3 / iOS Native)',
      'تكامل مع APIs خارجية تلقائياً',
      'تصدير APK/IPA جاهز للنشر',
      'يدعم الإشعارات + الخرائط + المدفوعات'
    ],
    drawbacks: [
      'نشر التطبيق على Google Play / App Store يحتاج حسابات مدفوعة (Google $25 مرة واحدة، Apple $99/سنة)',
      'بعض الميزات المتقدمة تحتاج تخصيص يدوي'
    ],
    bestFor: 'الشركات والأفراد اللي يبون يطلقون تطبيقاً جديداً بدون توظيف فريق برمجة كامل.',
  },
  'app-continue': {
    title: 'تطبيق قابل للإكمال',
    description: 'لو عندك مشروع تطبيق نصف منجَز (Flutter / React Native / Native) — ارفع الكود وخلّي الذكاء يكمل لك المزايا الناقصة أو يصلّح bugs.',
    features: [
      'يفهم كودك الموجود ويبني عليه',
      'يضيف ميزات جديدة بدون كسر الموجود',
      'يصلّح bugs ويحسّن الأداء',
      'يدعم تحويل التطبيق لـtech stack مختلف'
    ],
    drawbacks: [
      'يحتاج كود نظيف نسبياً (مش معقّد جداً)',
      'حجم الرفع محدود (max 100MB)'
    ],
    bestFor: 'المطوّرين اللي تعطّلوا في مشروع، أو الشركات اللي ورثت كود قديم تبي تطوّره.',
  },
  'web-to-app': {
    title: 'تحويل موقع لتطبيق',
    description: 'حوّل موقعك (أي موقع) إلى تطبيق جوّال أصلي بدون كتابة سطر كود. يبني لك APK لـAndroid وIPA لـiOS مع تجربة استخدام أصلية (مش WebView بسيط).',
    features: [
      'تحويل سريع — ١٠ دقائق فقط',
      'يدعم PWA features (إشعارات، عمل بدون نت)',
      'أيقونة وSplash screen مخصّصة',
      'تكامل مع الإشعارات الفورية',
      'متجر تطبيقات جاهز'
    ],
    drawbacks: [
      'الأداء أقل من تطبيق Native كامل',
      'بعض ميزات الجوّال (Bluetooth، NFC) محدودة'
    ],
    bestFor: 'أصحاب المتاجر الإلكترونية والمواقع اللي يبون حضور قوي على متجر التطبيقات بدون إعادة بناء.',
  },
  'desktop-app': {
    title: 'تطبيقات سطح المكتب',
    description: 'بناء تطبيقات لـWindows وMac وLinux باستخدام Electron أو Tauri — تطبيقات احترافية تشتغل بدون متصفح.',
    features: [
      'يشتغل على Windows + Mac + Linux',
      'وصول كامل لملفات النظام',
      'بدون متصفح — تجربة Native',
      'يدعم الأوفلاين الكامل',
      'حجم خفيف مع Tauri (~5MB)'
    ],
    drawbacks: [
      'حجم التطبيق أكبر مع Electron (~80MB)',
      'يحتاج توقيع رقمي للنشر على Mac (Apple Developer)'
    ],
    bestFor: 'الأدوات الإنتاجية، تطبيقات الشركات الداخلية، البرامج اللي تحتاج وصول للنظام.',
  },
  'mobile-market': {
    title: 'سوق التطبيقات — Remix',
    description: 'مكتبة تطبيقات بناها مجتمع Zerax — استلهم منها، أو "Remix" تطبيق موجود وعدّله لاحتياجك.',
    features: [
      'تطبيقات جاهزة لكل قطاع',
      'Remix تطبيق بضغطة زر',
      'تعديل سهل بالـAI',
      'مشاركة تطبيقك مع المجتمع',
      'كسب نقاط من كل Remix على تطبيقك'
    ],
    drawbacks: [
      'بعض التطبيقات قد تحتاج تخصيص قبل الاستخدام التجاري',
      'يحتاج فهم أساسي لطريقة Remix'
    ],
    bestFor: 'المبتدئين اللي يبون يفهمون كيف تتبنى التطبيقات، أو من يبي بداية سريعة.',
  },
  'game-web': {
    title: 'مواقع ألعاب — HTML5 / Phaser / Three.js',
    description: 'بناء ألعاب تشتغل في المتصفح مباشرة بدون تنزيل. تختار بين HTML5 Canvas أو Phaser.js (٢D احترافي) أو Three.js (٣D).',
    features: [
      'يشتغل في أي متصفح — بدون تنزيل',
      'دعم 2D و 3D كامل',
      'ألعاب متعدّدة اللاعبين (WebSockets)',
      'مشاركة سهلة عبر رابط',
      'متوافق مع الجوّال + الكمبيوتر'
    ],
    drawbacks: [
      'الأداء أقل من ألعاب Native',
      'الألعاب الكبيرة (3D معقّدة) قد تثقل المتصفح'
    ],
    bestFor: 'الألعاب التسويقية، الألعاب التعليمية، البزل، الألعاب المتعدّدة اللاعبين البسيطة.',
  },
  'game-mobile': {
    title: 'تطبيقات ألعاب — Unity / Godot + 3D Tools',
    description: 'ألعاب أصلية للجوّال بمحرّكات احترافية (Unity / Godot) — تشمل 3D modeling، فيزياء، أصوات، وأنظمة كاملة.',
    features: [
      'محرّكات احترافية (Unity Pro / Godot 4)',
      'دعم 3D كامل + Asset Store',
      'ألعاب AAA-quality ممكنة',
      'تصدير لـAndroid + iOS + PC',
      'فيزياء + AI + Multiplayer'
    ],
    drawbacks: [
      'منحنى تعلّم أعلى من ألعاب الويب',
      'حجم التطبيق أكبر (50MB+)',
      'يحتاج وقت أطول للنشر'
    ],
    bestFor: 'الألعاب الجدية، استوديوهات الألعاب الناشئة، الألعاب اللي تبي تجاري الكبار.',
  },
  'image': {
    title: 'إنشاء الصور — Flux Pro Ultra · Nano Banana',
    description: 'توليد صور احترافية بأفضل موديلات الذكاء الاصطناعي العالمية: Flux Pro Ultra (واقعية فوتوغرافية)، Nano Banana (سريع ومبدع)، GPT Image 1 (دقّة عالية).',
    features: [
      'جودة استوديو احترافية (8K ready)',
      '٣ موديلات حسب احتياجك',
      'يفهم العربية والإنجليزية',
      'تعديل صور موجودة',
      'إزالة الخلفية + تكبير ذكي'
    ],
    drawbacks: [
      'الموديلات الفاخرة (Flux Ultra) أبطأ (20-40 ثانية)',
      'كل صورة تستهلك نقاط من رصيدك'
    ],
    bestFor: 'المصمّمين، صنّاع المحتوى، الإعلانات، التسويق، أي شخص يبي صور احترافية بدون فوتوشوب.',
  },
  'video': {
    title: 'إنشاء الفيديوهات — Veo 3 · Kling · Sora 2',
    description: 'توليد فيديوهات سينمائية بأقوى موديلات الفيديو في 2026: Sora 2 من OpenAI، Veo 3 من Google، Kling من Kuaishou.',
    features: [
      'فيديو 1080p بجودة سينمائية',
      'حتى ٦٠ ثانية لكل فيديو',
      'موسيقى + مؤثرات صوتية',
      'تحريك الصور الثابتة',
      'تحويل نص → فيديو مباشرة'
    ],
    drawbacks: [
      'وقت التوليد أطول (٢-٥ دقائق للفيديو الواحد)',
      'استهلاك نقاط أعلى من الصور',
      'بعض الموديلات تحدّد طول الفيديو'
    ],
    bestFor: 'صنّاع المحتوى، الإعلانات، YouTube/TikTok، عروض المنتجات، المحتوى التعليمي.',
  },
  'voice': {
    title: 'الأصوات واللهجات — ElevenLabs · سعودي طبيعي',
    description: 'توليد أصوات طبيعية بالعربية والإنجليزية بأكثر من ٥٠ لهجة — سعودي، خليجي، مصري، شامي، مغربي. يستخدم ElevenLabs Pro.',
    features: [
      'صوت طبيعي ١٠٠٪ — مش روبوتي',
      '٥٠+ لهجة عربية وإنجليزية',
      'يدعم المشاعر (فرح، حزن، حماس)',
      'نسخ صوتك (Voice Cloning)',
      'صوت احترافي للدوبلاج والإعلانات'
    ],
    drawbacks: [
      'Voice Cloning يحتاج ١-٢ دقيقة من صوتك',
      'بعض اللهجات النادرة قد تحتاج تدريب إضافي'
    ],
    bestFor: 'مذيعو YouTube، صنّاع البودكاست، الدوبلاج، دروس تعليمية، رسائل تسويقية.',
  },
};

const LandingPage = ({ user }) => {
  const navigate = useNavigate();
  const goOrRegister = (target) => navigate(user ? target : '/register');
  const [infoCard, setInfoCard] = React.useState(null); // selected card type for info modal

  // Organized sections by category
  const categories = [
    {
      id: 'websites',
      label: 'المواقع',
      accent: '#10b981',
      cards: [
        {
          type: 'website-freebuild',
          title: 'إنشاء موقع من الصفر',
          desc: 'شات ذكي · توليد أصول · معاينة حية',
          gradient: 'from-emerald-500/20 to-teal-500/10',
          accent: '#10b981',
          bgImage: 'https://images.unsplash.com/photo-1467232004584-a241de8bcf5d?auto=format&fit=crop&w=800&q=70',
          badge: 'جديد',
          action: () => goOrRegister('/freebuild/chat'),
        },
        {
          type: 'website-template',
          title: 'مواقع جاهزة',
          desc: 'معالج ٦ خطوات · ٦ أنماط حصرية · ٢٤ ميزة',
          gradient: 'from-teal-500/20 to-emerald-500/10',
          accent: '#14b8a6',
          bgImage: 'https://images.unsplash.com/photo-1559028012-481c04fa702d?auto=format&fit=crop&w=800&q=70',
          badge: 'جديد',
          action: () => goOrRegister('/ready-sites'),
        },
      ],
    },
    {
      id: 'apps',
      label: 'التطبيقات',
      accent: '#06b6d4',
      cards: [
        {
          type: 'app-builder',
          title: 'إنشاء تطبيق من الصفر',
          desc: 'React Native + Flutter + Native',
          gradient: 'from-cyan-500/20 to-blue-500/10',
          accent: '#06b6d4',
          bgImage: 'https://images.unsplash.com/photo-1512941937669-90a1b58e7e9c?auto=format&fit=crop&w=800&q=70',
          badge: 'مطوّر',
          action: () => goOrRegister('/app-builder'),
        },
        {
          type: 'app-continue',
          title: 'تطبيق قابل للإكمال',
          desc: 'ارفع كودك ونكمل معك',
          gradient: 'from-blue-500/20 to-indigo-500/10',
          accent: '#3b82f6',
          bgImage: 'https://images.unsplash.com/photo-1555066931-4365d14bab8c?auto=format&fit=crop&w=800&q=70',
          badge: 'جديد',
          action: () => goOrRegister('/app-builder?mode=continue'),
        },
        {
          type: 'web-to-app',
          title: 'تحويل موقع لتطبيق',
          desc: 'Web → Android / iOS APK',
          gradient: 'from-sky-500/20 to-cyan-500/10',
          accent: '#0ea5e9',
          bgImage: 'https://images.unsplash.com/photo-1607252650355-f7fd0460ccdb?auto=format&fit=crop&w=800&q=70',
          badge: 'محوّل',
          action: () => goOrRegister('/app-builder?mode=web-to-app'),
        },
        {
          type: 'desktop-app',
          title: 'تطبيقات سطح المكتب',
          desc: 'Electron / Tauri · Windows/Mac/Linux',
          gradient: 'from-violet-500/20 to-purple-500/10',
          accent: '#8b5cf6',
          bgImage: 'https://images.unsplash.com/photo-1593642632559-0c6d3fc62b89?auto=format&fit=crop&w=800&q=70',
          badge: 'سطح المكتب',
          action: () => goOrRegister('/app-builder?mode=desktop'),
        },
        {
          type: 'mobile-market',
          title: 'سوق التطبيقات',
          desc: 'Remix تطبيقات المجتمع',
          gradient: 'from-amber-500/20 to-orange-500/10',
          accent: '#f59e0b',
          bgImage: 'https://images.unsplash.com/photo-1551434678-e076c223a692?auto=format&fit=crop&w=800&q=70',
          action: () => navigate('/dashboard/apps-market'),
        },
      ],
    },
    {
      id: 'games',
      label: 'الألعاب',
      accent: '#84cc16',
      cards: [
        {
          type: 'game-web',
          title: 'مواقع ألعاب',
          desc: 'HTML5 / Phaser / Three.js',
          gradient: 'from-lime-500/20 to-green-500/10',
          accent: '#84cc16',
          bgImage: 'https://images.unsplash.com/photo-1493711662062-fa541adb3fc8?auto=format&fit=crop&w=800&q=70',
          badge: 'جديد',
          action: () => goOrRegister('/games/web'),
        },
        {
          type: 'game-mobile',
          title: 'تطبيقات ألعاب',
          desc: 'Unity / Godot + 3D Tools',
          gradient: 'from-green-500/20 to-emerald-500/10',
          accent: '#22c55e',
          bgImage: 'https://images.unsplash.com/photo-1542751371-adc38448a05e?auto=format&fit=crop&w=800&q=70',
          badge: 'جديد',
          action: () => goOrRegister('/games/mobile'),
        },
      ],
    },
    {
      id: 'media',
      label: 'الصور والفيديوهات',
      accent: '#a855f7',
      cards: [
        {
          type: 'image',
          title: 'إنشاء الصور',
          desc: 'Flux Pro Ultra · Nano Banana',
          gradient: 'from-purple-500/20 to-violet-500/10',
          accent: '#a855f7',
          bgImage: 'https://images.unsplash.com/photo-1502691876148-a84978e59af8?auto=format&fit=crop&w=800&q=70',
          action: () => goOrRegister('/chat/image'),
        },
        {
          type: 'video',
          title: 'إنشاء الفيديوهات',
          desc: 'Veo 3 · Kling · Sora 2',
          gradient: 'from-rose-500/20 to-pink-500/10',
          accent: '#f43f5e',
          bgImage: 'https://images.unsplash.com/photo-1485846234645-a62644f84728?auto=format&fit=crop&w=800&q=70',
          action: () => goOrRegister('/chat/video'),
        },
        {
          type: 'voice',
          title: 'الأصوات واللهجات',
          desc: 'ElevenLabs · سعودي طبيعي',
          gradient: 'from-sky-500/20 to-cyan-500/10',
          accent: '#0ea5e9',
          bgImage: 'https://images.unsplash.com/photo-1478737270239-2f02b77fc618?auto=format&fit=crop&w=800&q=70',
          badge: 'جديد',
          action: () => goOrRegister('/chat/voice'),
        },
      ],
    },
  ];

  // No more "coming soon" — everything is in the proper category now

  const Card = ({ type, title, desc, gradient, accent, bgImage, action, badge, soon = false }) => (
    <div
      onClick={action}
      className={`relative group rounded-xl overflow-hidden aspect-[4/3] sm:aspect-[5/4] border transition-all ${
        soon
          ? 'border-white/10 cursor-not-allowed opacity-70 hover:opacity-90'
          : 'border-white/10 hover:border-white/30 cursor-pointer hover:scale-[1.03]'
      }`}
      onMouseEnter={(e) => {
        if (!soon) e.currentTarget.style.boxShadow = `0 12px 40px -8px ${accent}80`;
      }}
      onMouseLeave={(e) => (e.currentTarget.style.boxShadow = '')}
      data-testid={`hero-card-${type}`}
    >
      <div
        className={`absolute inset-0 bg-cover bg-center scale-110 transition-transform duration-700 ${
          soon ? 'grayscale' : 'group-hover:scale-125'
        }`}
        style={{ backgroundImage: `url('${bgImage}')` }}
      />
      <div className={`absolute inset-0 bg-gradient-to-tr ${gradient}`} />
      <div className="absolute inset-0 bg-gradient-to-t from-black via-black/70 to-black/20" />
      {soon && (
        <div className="absolute top-2 left-2 z-10 px-2 py-0.5 rounded-md bg-amber-400/90 text-black text-[10px] font-black tracking-wider">
          🔒 قريباً
        </div>
      )}
      {!soon && badge && (
        <div className="absolute top-2 left-2 z-10 px-2 py-0.5 rounded-md bg-gradient-to-r from-emerald-400 to-cyan-400 text-black text-[10px] font-black tracking-wider animate-pulse">
          ✨ {badge}
        </div>
      )}
      {/* Info button (?) — opens detailed description in modal */}
      {cardInfo[type] && (
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation();
            setInfoCard(type);
          }}
          className="absolute top-2 right-2 z-20 w-7 h-7 rounded-full bg-black/60 backdrop-blur-sm border border-white/20 hover:border-white/50 hover:bg-black/80 flex items-center justify-center transition-all hover:scale-110"
          style={{ boxShadow: `0 0 12px ${accent}40` }}
          data-testid={`card-info-btn-${type}`}
          aria-label={`معلومات عن ${title}`}
          title="ما هذا؟ اضغط لمعرفة المزيد"
        >
          <HelpCircle className="w-3.5 h-3.5 text-white/90" />
        </button>
      )}
      <div className="relative h-full flex flex-col justify-end p-3 sm:p-4 text-right">
        <h3 className="text-white font-black text-base sm:text-lg mb-0.5" style={{ textShadow: '0 2px 8px rgba(0,0,0,.5)' }}>
          {title}
        </h3>
        <p className="text-[10px] sm:text-xs text-white/75 font-medium">{desc}</p>
      </div>
      {!soon && !cardInfo[type] && (
        <div className="absolute top-2 right-2 w-2 h-2 rounded-full" style={{ background: accent, boxShadow: `0 0 8px ${accent}` }} />
      )}
    </div>
  );

  return (
    <div className="min-h-screen bg-[#0a0a12]" data-testid="landing-page">
      <Navbar user={user} transparent />

      {/* Rotating banner + stories */}
      <div className="pt-16">
        <SiteBannerStories placement="outside" />
      </div>

      <div className="max-w-5xl mx-auto px-4 py-6 sm:py-10">
        {/* Hero header — clean, animated logo only */}
        <div className="text-center mb-6">
          <div className="flex justify-center mb-3">
            <ZeraxLogo size="xl" />
          </div>
          <p className="text-sm sm:text-base text-amber-200/60 font-medium tracking-wide" data-testid="hero-tagline">
            منصّة <span className="text-amber-300 font-bold">Zerax</span> — أنشئ مواقع، تطبيقات، صور وفيديوهات بالذكاء الاصطناعي
          </p>
        </div>

        {/* Rotating hero banner — 5 slides (Zerax/Video/Image/Game/App), 8s each */}
        <div className="mb-10">
          <HeroBanner onGo={goOrRegister} />
        </div>

        {/* WORKING SECTIONS — GROUPED BY CATEGORY */}
        <div className="text-center mb-6">
          <div className="text-xs font-bold text-amber-300/70 tracking-widest mb-1">الأقسام المتاحة</div>
          <div className="h-px w-20 mx-auto bg-gradient-to-r from-transparent via-amber-400/40 to-transparent"></div>
        </div>

        {categories.map((cat) => (
          <section key={cat.id} className="mb-9" data-testid={`category-${cat.id}`}>
            <div className="flex items-center gap-3 mb-3">
              <div
                className="h-px flex-1"
                style={{ background: `linear-gradient(to left, transparent, ${cat.accent}40, transparent)` }}
              />
              <div
                className="px-3 py-1 rounded-full border text-[11px] font-bold tracking-wider"
                style={{ borderColor: `${cat.accent}40`, color: cat.accent, background: `${cat.accent}10` }}
              >
                {cat.label}
              </div>
              <div
                className="h-px flex-1"
                style={{ background: `linear-gradient(to right, transparent, ${cat.accent}40, transparent)` }}
              />
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 sm:gap-4">
              {cat.cards.map((c) => <Card key={c.type} {...c} />)}
            </div>
          </section>
        ))}

        {/* No more "coming soon" — features moved into proper categories */}

        {!user && (
          <div className="mt-10 flex justify-center">
            <Button
              size="lg"
              onClick={() => navigate('/register')}
              className="bg-gradient-to-r from-amber-500 to-yellow-500 hover:from-amber-600 hover:to-yellow-600 text-black font-black shadow-lg shadow-amber-500/25"
              data-testid="landing-register-btn"
            >
              <Sparkles className="w-4 h-4 me-2" /> أنشئ حساباً مجانياً
            </Button>
          </div>
        )}
      </div>

      <footer className="py-8 border-t border-amber-500/10 mt-8">
        <div className="container mx-auto px-4 md:px-8 max-w-7xl">
          <div className="flex flex-col md:flex-row items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <ZeraxLogo size="sm" />
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-amber-400 to-yellow-500 font-bold text-xl">Zerax</span>
            </div>
            <p className="text-sm text-gray-500">© 2026 Zerax. جميع الحقوق محفوظة.</p>
          </div>
        </div>
      </footer>

      {/* Info Modal — opens when (?) clicked on any card */}
      {infoCard && cardInfo[infoCard] && (
        <div
          className="fixed inset-0 z-[200] flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-in fade-in duration-200"
          onClick={() => setInfoCard(null)}
          data-testid="card-info-modal"
        >
          <div
            className="relative w-full max-w-lg max-h-[88vh] overflow-y-auto rounded-2xl border border-amber-500/20 bg-gradient-to-br from-[#13131c] to-[#0a0a12] shadow-2xl shadow-amber-500/10 p-6 sm:p-7"
            onClick={(e) => e.stopPropagation()}
            dir="rtl"
          >
            {/* Close button */}
            <button
              type="button"
              onClick={() => setInfoCard(null)}
              className="absolute top-3 left-3 w-8 h-8 rounded-full bg-white/5 hover:bg-white/10 border border-white/10 flex items-center justify-center transition-all hover:scale-110"
              data-testid="card-info-close-btn"
              aria-label="إغلاق"
            >
              <X className="w-4 h-4 text-white/80" />
            </button>

            {/* Title */}
            <div className="mb-5 pl-10">
              <div className="text-[10px] font-bold tracking-widest text-amber-300/70 mb-1">📘 تعرّف على هذه الميزة</div>
              <h3 className="text-xl sm:text-2xl font-black text-white leading-tight" data-testid="card-info-title">
                {cardInfo[infoCard].title}
              </h3>
            </div>

            {/* Description */}
            <div className="mb-5 p-4 rounded-xl bg-white/[0.03] border border-white/10">
              <p className="text-sm sm:text-base text-white/85 leading-relaxed">
                {cardInfo[infoCard].description}
              </p>
            </div>

            {/* Features */}
            <div className="mb-4">
              <div className="flex items-center gap-2 mb-2.5">
                <div className="w-6 h-6 rounded-full bg-emerald-500/20 border border-emerald-400/40 flex items-center justify-center">
                  <Check className="w-3.5 h-3.5 text-emerald-300" />
                </div>
                <h4 className="text-sm font-black text-emerald-300">المميزات</h4>
              </div>
              <ul className="space-y-1.5 pr-2">
                {cardInfo[infoCard].features.map((f, i) => (
                  <li key={i} className="text-xs sm:text-sm text-white/80 flex items-start gap-2">
                    <span className="text-emerald-400 mt-1">•</span>
                    <span>{f}</span>
                  </li>
                ))}
              </ul>
            </div>

            {/* Drawbacks */}
            <div className="mb-4">
              <div className="flex items-center gap-2 mb-2.5">
                <div className="w-6 h-6 rounded-full bg-amber-500/20 border border-amber-400/40 flex items-center justify-center">
                  <AlertTriangle className="w-3.5 h-3.5 text-amber-300" />
                </div>
                <h4 className="text-sm font-black text-amber-300">السلبيات / القيود</h4>
              </div>
              <ul className="space-y-1.5 pr-2">
                {cardInfo[infoCard].drawbacks.map((d, i) => (
                  <li key={i} className="text-xs sm:text-sm text-white/80 flex items-start gap-2">
                    <span className="text-amber-400 mt-1">•</span>
                    <span>{d}</span>
                  </li>
                ))}
              </ul>
            </div>

            {/* Best For */}
            <div className="mb-5 p-4 rounded-xl bg-gradient-to-br from-cyan-500/10 to-blue-500/10 border border-cyan-400/20">
              <div className="flex items-center gap-2 mb-2">
                <Target className="w-4 h-4 text-cyan-300" />
                <h4 className="text-sm font-black text-cyan-300">الأفضل لمن؟</h4>
              </div>
              <p className="text-xs sm:text-sm text-white/85 leading-relaxed">
                {cardInfo[infoCard].bestFor}
              </p>
            </div>

            {/* CTA */}
            <Button
              onClick={() => {
                const cardType = infoCard;
                setInfoCard(null);
                // Find the card and trigger its action
                for (const cat of categories) {
                  const c = cat.cards.find((x) => x.type === cardType);
                  if (c) {
                    c.action();
                    return;
                  }
                }
              }}
              className="w-full bg-gradient-to-r from-amber-500 to-yellow-500 hover:from-amber-600 hover:to-yellow-600 text-black font-black shadow-lg shadow-amber-500/20"
              data-testid="card-info-cta"
            >
              <Sparkles className="w-4 h-4 ms-2" />
              ابدأ الآن
            </Button>
          </div>
        </div>
      )}

      {/* Dual AI characters now mounted globally via GlobalAvatarMount */}
    </div>
  );
};

export default LandingPage;
