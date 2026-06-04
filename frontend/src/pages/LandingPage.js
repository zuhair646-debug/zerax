import React from 'react';
import { Navbar, ZitexLogo } from '@/components/Navbar';
import { Button } from '@/components/ui/button';
import { useNavigate } from 'react-router-dom';
import { Sparkles } from 'lucide-react';
import { toast } from 'sonner';
import SiteBannerStories from '@/components/SiteBannerStories';

const LandingPage = ({ user }) => {
  const navigate = useNavigate();
  const goOrRegister = (target) => navigate(user ? target : '/register');
  const showSoon = () => toast.info('🛠️ هذا القسم قيد التحضير — قريباً!', { duration: 2200 });

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
          desc: 'FreeBuild — تصميم حصري',
          gradient: 'from-emerald-500/20 to-teal-500/10',
          accent: '#10b981',
          bgImage: 'https://images.unsplash.com/photo-1467232004584-a241de8bcf5d?auto=format&fit=crop&w=800&q=70',
          action: () => goOrRegister('/ai-agent'),
        },
        {
          type: 'website-template',
          title: 'مواقع جاهزة',
          desc: '٢٥ قالب احترافي',
          gradient: 'from-teal-500/20 to-emerald-500/10',
          accent: '#14b8a6',
          bgImage: 'https://images.unsplash.com/photo-1559028012-481c04fa702d?auto=format&fit=crop&w=800&q=70',
          action: () => goOrRegister('/websites'),
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
          badge: 'قريباً',
          action: () => goOrRegister('/games/web'),
        },
        {
          type: 'game-mobile',
          title: 'تطبيقات ألعاب',
          desc: 'Unity / Godot + 3D Tools',
          gradient: 'from-green-500/20 to-emerald-500/10',
          accent: '#22c55e',
          bgImage: 'https://images.unsplash.com/photo-1542751371-adc38448a05e?auto=format&fit=crop&w=800&q=70',
          badge: 'قريباً',
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

  // Coming-soon sections (bottom)
  const soonCards = [
    {
      type: 'web-to-app',
      title: 'تحويل موقع لتطبيق',
      desc: 'Web → Android/iOS APK',
      gradient: 'from-cyan-500/20 to-sky-500/10',
      accent: '#06b6d4',
      bgImage: 'https://images.unsplash.com/photo-1607252650355-f7fd0460ccdb?auto=format&fit=crop&w=800&q=70',
      action: showSoon,
    },
    {
      type: 'desktop-app',
      title: 'تطبيقات سطح المكتب',
      desc: 'Electron / Tauri',
      gradient: 'from-violet-500/20 to-purple-500/10',
      accent: '#8b5cf6',
      bgImage: 'https://images.unsplash.com/photo-1593642632559-0c6d3fc62b89?auto=format&fit=crop&w=800&q=70',
      action: showSoon,
    },
  ];

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
      <div className="relative h-full flex flex-col justify-end p-3 sm:p-4 text-right">
        <h3 className="text-white font-black text-base sm:text-lg mb-0.5" style={{ textShadow: '0 2px 8px rgba(0,0,0,.5)' }}>
          {title}
        </h3>
        <p className="text-[10px] sm:text-xs text-white/75 font-medium">{desc}</p>
      </div>
      {!soon && (
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

      <div className="max-w-5xl mx-auto px-4 py-8 sm:py-12">
        {/* Hero header — minimal */}
        <div className="text-center mb-8">
          <div className="flex justify-center mb-4">
            <ZitexLogo size="xl" />
          </div>
          <h1 className="text-3xl sm:text-5xl font-black text-white" data-testid="hero-title">
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-amber-400 via-yellow-400 to-amber-500">Zitex</span>
          </h1>
        </div>

        {/* STANDALONE FEATURED CTA */}
        <div
          onClick={() => goOrRegister('/ai-agent')}
          className="relative mb-8 cursor-pointer group rounded-2xl overflow-hidden border border-amber-400/30 hover:border-amber-300/60 transition-all hover:shadow-[0_20px_60px_-12px_rgba(245,158,11,0.5)]"
          data-testid="hero-ai-agent"
        >
          <div
            className="absolute inset-0 bg-cover bg-center scale-105 group-hover:scale-110 transition-transform duration-700"
            style={{ backgroundImage: `url('https://images.unsplash.com/photo-1551434678-e076c223a692?auto=format&fit=crop&w=1600&q=70')` }}
          />
          <div className="absolute inset-0 bg-gradient-to-l from-black/95 via-black/70 to-amber-900/40" />
          <div className="relative p-5 sm:p-8 flex flex-col sm:flex-row items-start sm:items-center gap-5">
            <div className="flex-shrink-0 w-16 h-16 sm:w-20 sm:h-20 rounded-2xl bg-gradient-to-br from-amber-400 to-orange-500 flex items-center justify-center shadow-lg shadow-amber-500/40">
              <Sparkles className="w-9 h-9 sm:w-11 sm:h-11 text-black" />
            </div>
            <div className="flex-1 text-right">
              <div className="inline-block px-2 py-0.5 rounded-md bg-amber-400/20 border border-amber-300/40 text-amber-300 text-[10px] font-black tracking-wider mb-2">
                ذكاء واحد · 10 أدوات · معاينة مباشرة
              </div>
              <h2 className="text-2xl sm:text-3xl font-black text-white mb-1">
                ذكاء Zitex <span className="text-amber-300">يبني، يبحث، يولّد</span>
              </h2>
              <p className="text-white/75 text-xs sm:text-sm leading-relaxed">
                اكتب أي طلب — الذكاء يفكّر، يستدعي أدوات حقيقية (بحث، صور AI، صوت، قرآن، رياضة، مصادر سعودية)، ويبني موقعك live جنب الشات.
              </p>
            </div>
            <div className="flex-shrink-0">
              <div className="px-5 py-3 rounded-xl bg-gradient-to-r from-amber-400 to-yellow-500 text-black font-black text-sm whitespace-nowrap shadow-lg group-hover:scale-105 transition-transform">
                ابدأ الآن →
              </div>
            </div>
          </div>
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

        {/* COMING SOON SECTIONS */}
        <div className="text-center mb-4 mt-10">
          <div className="text-xs font-bold text-white/40 tracking-widest mb-1">قريباً — قيد التطوير</div>
          <div className="h-px w-20 mx-auto bg-gradient-to-r from-transparent via-white/15 to-transparent"></div>
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 sm:gap-4">
          {soonCards.map((c) => <Card key={c.type} {...c} soon />)}
        </div>

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
              <ZitexLogo size="sm" />
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-amber-400 to-yellow-500 font-bold text-xl">Zitex</span>
            </div>
            <p className="text-sm text-gray-500">© 2026 Zitex. جميع الحقوق محفوظة.</p>
          </div>
        </div>
      </footer>

      {/* Dual AI characters now mounted globally via GlobalAvatarMount */}
    </div>
  );
};

export default LandingPage;
