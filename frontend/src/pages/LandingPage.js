import React from 'react';
import { Navbar, ZitexLogo } from '@/components/Navbar';
import { Button } from '@/components/ui/button';
import { useNavigate } from 'react-router-dom';
import { Sparkles } from 'lucide-react';
import SiteBannerStories from '@/components/SiteBannerStories';

const LandingPage = ({ user }) => {
  const navigate = useNavigate();
  const goOrRegister = (target) => navigate(user ? target : '/register');

  const cards = [
    {
      type: 'website-template',
      title: 'مواقع جاهزة',
      desc: '٢٥ قالب جاهز',
      gradient: 'from-emerald-500/20 to-teal-500/10',
      accent: '#10b981',
      bgImage: 'https://images.unsplash.com/photo-1467232004584-a241de8bcf5d?auto=format&fit=crop&w=800&q=70',
      action: () => goOrRegister('/websites'),
    },
    {
      type: 'mobile',
      title: 'تطبيق موبايل',
      desc: 'Flutter / Swift / Kotlin',
      gradient: 'from-pink-500/20 to-rose-500/10',
      accent: '#ec4899',
      bgImage: 'https://images.unsplash.com/photo-1512941937669-90a1b58e7e9c?auto=format&fit=crop&w=800&q=70',
      action: () => goOrRegister('/chat'),
    },
    {
      type: 'web-to-app',
      title: 'تحويل موقع لتطبيق',
      desc: 'Web → Android/iOS',
      gradient: 'from-cyan-500/20 to-sky-500/10',
      accent: '#06b6d4',
      bgImage: 'https://images.unsplash.com/photo-1607252650355-f7fd0460ccdb?auto=format&fit=crop&w=800&q=70',
      action: () => goOrRegister('/chat'),
    },
    {
      type: 'game',
      title: 'إنشاء الألعاب',
      desc: 'Phaser / Three.js',
      gradient: 'from-cyan-500/20 to-blue-500/10',
      accent: '#0ea5e9',
      bgImage: 'https://images.unsplash.com/photo-1542751371-adc38448a05e?auto=format&fit=crop&w=800&q=70',
      action: () => goOrRegister('/chat'),
    },
    {
      type: 'image',
      title: 'إنشاء الصور',
      desc: 'GPT Image 1 / Nano Banana',
      gradient: 'from-purple-500/20 to-violet-500/10',
      accent: '#a855f7',
      bgImage: 'https://images.unsplash.com/photo-1561735445-df9c3deef91d?auto=format&fit=crop&w=800&q=70',
      action: () => goOrRegister('/chat'),
    },
    {
      type: 'video',
      title: 'إنشاء الفيديوهات',
      desc: 'Sora 2',
      gradient: 'from-orange-500/20 to-red-500/10',
      accent: '#f97316',
      bgImage: 'https://images.unsplash.com/photo-1485846234645-a62644f84728?auto=format&fit=crop&w=800&q=70',
      action: () => goOrRegister('/chat'),
    },
  ];

  return (
    <div className="min-h-screen bg-[#0a0a12]" data-testid="landing-page">
      <Navbar user={user} transparent />

      {/* Rotating banner + stories at the very top */}
      <div className="pt-16">
        <SiteBannerStories placement="outside" />
      </div>

      <div className="max-w-5xl mx-auto px-4 py-8 sm:py-12">
        {/* Hero header */}
        <div className="text-center mb-8 sm:mb-10">
          <div className="flex justify-center mb-5">
            <ZitexLogo size="xl" />
          </div>
          <h1 className="text-3xl sm:text-5xl font-black text-white mb-2" data-testid="hero-title">
            مرحباً بك في <span className="text-transparent bg-clip-text bg-gradient-to-r from-amber-400 via-yellow-400 to-amber-500">Zitex</span>
          </h1>
          <p className="text-amber-200/80 text-sm sm:text-base">مساعدك الذكي لإنشاء المواقع والصور والفيديوهات والتطبيقات</p>
        </div>

        {/* STANDALONE FEATURED CTA — Build website from scratch */}
        <div
          onClick={() => goOrRegister('/websites')}
          className="relative mb-8 cursor-pointer group rounded-2xl overflow-hidden border border-amber-400/30 hover:border-amber-300/60 transition-all hover:shadow-[0_20px_60px_-12px_rgba(245,158,11,0.5)]"
          data-testid="hero-build-website-from-scratch"
        >
          <div
            className="absolute inset-0 bg-cover bg-center scale-105 group-hover:scale-110 transition-transform duration-700"
            style={{
              backgroundImage: `url('https://images.unsplash.com/photo-1551434678-e076c223a692?auto=format&fit=crop&w=1600&q=70')`,
            }}
          />
          <div className="absolute inset-0 bg-gradient-to-l from-black/95 via-black/70 to-amber-900/40" />
          <div className="relative p-5 sm:p-8 flex flex-col sm:flex-row items-start sm:items-center gap-5">
            <div className="flex-shrink-0 w-16 h-16 sm:w-20 sm:h-20 rounded-2xl bg-gradient-to-br from-amber-400 to-orange-500 flex items-center justify-center shadow-lg shadow-amber-500/40">
              <Sparkles className="w-9 h-9 sm:w-11 sm:h-11 text-black" />
            </div>
            <div className="flex-1 text-right">
              <div className="inline-block px-2 py-0.5 rounded-md bg-amber-400/20 border border-amber-300/40 text-amber-300 text-[10px] font-black tracking-wider mb-2">
                الأكثر طلباً
              </div>
              <h2 className="text-2xl sm:text-3xl font-black text-white mb-1">
                أنشئ موقعك من الصفر <span className="text-amber-300">بمحادثة ذكية</span>
              </h2>
              <p className="text-white/75 text-xs sm:text-sm leading-relaxed">
                استوديو احترافي بـ ٢٥ تخصص — تحكّم عميق بالألوان والأشكال والأزرار والـ widgets، مع تصميم مخصص بالذكاء الاصطناعي
              </p>
            </div>
            <div className="flex-shrink-0">
              <div className="px-5 py-3 rounded-xl bg-gradient-to-r from-amber-400 to-yellow-500 text-black font-black text-sm whitespace-nowrap shadow-lg group-hover:scale-105 transition-transform">
                ابدأ الآن →
              </div>
            </div>
          </div>
        </div>

        {/* 6 Creative Cards Grid */}
        <div className="text-center mb-5">
          <div className="text-xs font-bold text-amber-300/70 tracking-widest mb-1">أو اختر الإنشاء السريع</div>
          <div className="h-px w-20 mx-auto bg-gradient-to-r from-transparent via-amber-400/40 to-transparent"></div>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 sm:gap-4">
          {cards.map(({ type, title, desc, gradient, accent, bgImage, action }) => (
            <div
              key={type}
              onClick={action}
              className="relative group cursor-pointer rounded-xl overflow-hidden aspect-[4/3] sm:aspect-[5/4] border border-white/10 hover:border-white/30 transition-all hover:scale-[1.03]"
              onMouseEnter={(e) => (e.currentTarget.style.boxShadow = `0 12px 40px -8px ${accent}80`)}
              onMouseLeave={(e) => (e.currentTarget.style.boxShadow = '')}
              data-testid={`hero-card-${type}`}
            >
              {/* Background image */}
              <div
                className="absolute inset-0 bg-cover bg-center scale-110 group-hover:scale-125 transition-transform duration-700"
                style={{ backgroundImage: `url('${bgImage}')` }}
              />
              {/* Color overlay */}
              <div className={`absolute inset-0 bg-gradient-to-tr ${gradient}`} />
              <div className="absolute inset-0 bg-gradient-to-t from-black via-black/70 to-black/20" />
              {/* Content */}
              <div className="relative h-full flex flex-col justify-end p-3 sm:p-4 text-right">
                <h3 className="text-white font-black text-base sm:text-lg mb-0.5" style={{ textShadow: '0 2px 8px rgba(0,0,0,.5)' }}>
                  {title}
                </h3>
                <p className="text-[10px] sm:text-xs text-white/75 font-medium">{desc}</p>
              </div>
              {/* Top-right accent corner */}
              <div className="absolute top-2 right-2 w-2 h-2 rounded-full" style={{ background: accent, boxShadow: `0 0 8px ${accent}` }} />
            </div>
          ))}
        </div>

        {!user && (
          <div className="mt-7 flex justify-center">
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

      {/* Footer */}
      <footer className="py-8 border-t border-amber-500/10 mt-8">
        <div className="container mx-auto px-4 md:px-8 max-w-7xl">
          <div className="flex flex-col md:flex-row items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <ZitexLogo size="sm" />
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-amber-400 to-yellow-500 font-bold text-xl">Zitex</span>
            </div>
            <p className="text-sm text-gray-500">
              © 2026 Zitex. جميع الحقوق محفوظة.
            </p>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default LandingPage;
