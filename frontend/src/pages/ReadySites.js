/**
 * Ready Sites — Step 1: Category Picker
 *
 * Modern category selector. User picks an industry → moves to purchase step.
 * Designed in the dark/gold Zenrex aesthetic used across the dashboard.
 */
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowRight, Sparkles, Info } from 'lucide-react';

const CATEGORIES = [
  {
    id: 'restaurants',
    title: 'مطاعم وكافيهات',
    subtitle: 'مطاعم، كافيهات، حلويات، عصائر',
    img: 'https://images.unsplash.com/photo-1517248135467-4c7edcad34c4?w=900&q=80&auto=format&fit=crop',
    accent: 'from-orange-500 to-rose-600',
  },
  {
    id: 'electronics',
    title: 'إلكترونيات وتقنية',
    subtitle: 'جوالات، لابتوبات، إكسسوارات',
    img: 'https://images.unsplash.com/photo-1518770660439-4636190af475?w=900&q=80&auto=format&fit=crop',
    accent: 'from-cyan-500 to-blue-600',
  },
  {
    id: 'stationery',
    title: 'قرطاسيات ومكتبات',
    subtitle: 'كتب، أدوات مدرسية، هدايا',
    img: 'https://images.unsplash.com/photo-1568097114537-9af5dd1cfb73?w=900&q=80&auto=format&fit=crop',
    accent: 'from-amber-500 to-orange-600',
  },
  {
    id: 'grocery',
    title: 'بقالات وسوبرماركت',
    subtitle: 'مواد غذائية، خضار، فواكه',
    img: 'https://images.unsplash.com/photo-1542838132-92c53300491e?w=900&q=80&auto=format&fit=crop',
    accent: 'from-green-500 to-emerald-600',
  },
  {
    id: 'pharmacy',
    title: 'صيدليات',
    subtitle: 'أدوية، عناية شخصية، فيتامينات',
    img: 'https://images.unsplash.com/photo-1576091160399-112ba8d25d1d?w=900&q=80&auto=format&fit=crop',
    accent: 'from-teal-500 to-cyan-600',
  },
  {
    id: 'fashion',
    title: 'أزياء وموضة',
    subtitle: 'ملابس رجالية، نسائية، أطفال',
    img: 'https://images.unsplash.com/photo-1490481651871-ab68de25d43d?w=900&q=80&auto=format&fit=crop',
    accent: 'from-pink-500 to-fuchsia-600',
  },
  {
    id: 'beauty',
    title: 'تجميل وعطور',
    subtitle: 'مكياج، عطور، عناية بالبشرة',
    img: 'https://images.unsplash.com/photo-1522335789203-aaa566306b3a?w=900&q=80&auto=format&fit=crop',
    accent: 'from-rose-500 to-pink-600',
  },
  {
    id: 'flowers',
    title: 'زهور وهدايا',
    subtitle: 'باقات، هدايا، مناسبات',
    img: 'https://images.unsplash.com/photo-1487530811176-3780de880c2d?w=900&q=80&auto=format&fit=crop',
    accent: 'from-violet-500 to-purple-600',
  },
];

export default function ReadySites({ user }) {
  const navigate = useNavigate();
  const [hovered, setHovered] = useState(null);
  const [disclaimerSeen, setDisclaimerSeen] = useState(
    typeof window !== 'undefined' && localStorage.getItem('zx_ready_sites_disclaimer') === '1'
  );

  useEffect(() => {
    if (typeof window !== 'undefined') {
      window.scrollTo(0, 0);
    }
  }, []);

  const handleSelect = (cat) => {
    sessionStorage.setItem('zx_ready_sites_category', JSON.stringify(cat));
    navigate(`/ready-sites/purchase?category=${cat.id}`);
  };

  const dismissDisclaimer = () => {
    localStorage.setItem('zx_ready_sites_disclaimer', '1');
    setDisclaimerSeen(true);
  };

  return (
    <div className="min-h-screen bg-[#08070d] text-white" dir="rtl" data-testid="ready-sites-page">
      {/* Disclaimer banner (shown once, dismissible) */}
      {!disclaimerSeen && (
        <div className="bg-amber-500/10 border-b border-amber-500/30 px-4 py-3" data-testid="rs-disclaimer">
          <div className="max-w-7xl mx-auto flex items-start gap-3">
            <Info className="w-5 h-5 text-amber-400 flex-shrink-0 mt-0.5" />
            <div className="flex-1 text-sm text-amber-100/90 leading-relaxed">
              <b className="text-amber-300">إخلاء مسؤولية:</b> الذكاء الاصطناعي في Zenrex محترف ومدرّب،
              لكن النتيجة تعتمد على وضوح طلبات العميل. بعض الطلبات غير الواضحة قد تؤدي إلى نتائج غير
              متوقعة. <b>Zenrex لا تتحمل أي خلل يحصل بسبب عدم وضوح فكرة العميل للذكاء الاصطناعي.</b>
            </div>
            <button
              onClick={dismissDisclaimer}
              className="text-amber-300 hover:text-amber-100 text-sm font-bold px-3 py-1 rounded-lg hover:bg-amber-500/20 transition"
              data-testid="dismiss-disclaimer-btn"
            >
              فهمت ✓
            </button>
          </div>
        </div>
      )}

      {/* Header */}
      <header className="max-w-7xl mx-auto px-6 pt-12 pb-8 text-center">
        <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-amber-500/10 border border-amber-500/30 text-amber-300 text-xs font-bold mb-6">
          <Sparkles className="w-3.5 h-3.5" />
          المواقع الجاهزة · جاهزة للإطلاق خلال دقائق
        </div>
        <h1 className="text-4xl sm:text-5xl lg:text-6xl font-black mb-4 bg-gradient-to-b from-white via-white to-amber-200 bg-clip-text text-transparent leading-tight">
          اختر تخصص مشروعك
        </h1>
        <p className="text-base sm:text-lg text-gray-400 max-w-2xl mx-auto leading-relaxed">
          نوفّر لك قوالب احترافية جاهزة لـ <b className="text-amber-300">8 تخصصات</b> مختلفة. اختر تخصصك،
          وراح يبني لك Zenrex AI موقعاً كاملاً باسمك وشعارك في خطوات بسيطة.
        </p>
      </header>

      {/* Category Grid */}
      <main className="max-w-7xl mx-auto px-6 pb-20">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5" data-testid="categories-grid">
          {CATEGORIES.map((cat) => (
            <button
              key={cat.id}
              onClick={() => handleSelect(cat)}
              onMouseEnter={() => setHovered(cat.id)}
              onMouseLeave={() => setHovered(null)}
              className="group relative aspect-[4/5] rounded-2xl overflow-hidden border border-white/10 bg-white/[0.02] hover:border-amber-400/50 transition-all duration-300 hover:-translate-y-1 hover:shadow-2xl hover:shadow-amber-500/10 text-right"
              data-testid={`category-card-${cat.id}`}
            >
              {/* Background image */}
              <div className="absolute inset-0">
                <img
                  src={cat.img}
                  alt={cat.title}
                  loading="lazy"
                  className="w-full h-full object-cover transition-transform duration-700 group-hover:scale-110"
                  onError={(e) => {
                    e.target.style.background = '#1a1625';
                  }}
                />
                {/* Dark gradient overlay */}
                <div className="absolute inset-0 bg-gradient-to-t from-black via-black/70 to-black/20" />
                {/* Accent gradient (subtle on hover) */}
                <div
                  className={`absolute inset-0 bg-gradient-to-br ${cat.accent} opacity-0 group-hover:opacity-20 transition-opacity duration-500 mix-blend-overlay`}
                />
              </div>

              {/* Content */}
              <div className="relative h-full flex flex-col justify-end p-5">
                <h3 className="text-xl font-black text-white mb-1 leading-tight">{cat.title}</h3>
                <p className="text-xs text-white/70 mb-4 leading-relaxed">{cat.subtitle}</p>
                <div className="flex items-center justify-between">
                  <span className="text-[11px] font-bold text-amber-300 uppercase tracking-wider">
                    اختر هذا
                  </span>
                  <div
                    className={`w-9 h-9 rounded-full bg-amber-400/20 border border-amber-400/40 flex items-center justify-center transition-all duration-300 ${
                      hovered === cat.id ? 'bg-amber-400 border-amber-400 scale-110' : ''
                    }`}
                  >
                    <ArrowRight
                      className={`w-4 h-4 rotate-180 transition-colors ${
                        hovered === cat.id ? 'text-black' : 'text-amber-300'
                      }`}
                    />
                  </div>
                </div>
              </div>

              {/* Top-left badge */}
              <div className="absolute top-3 left-3 px-2.5 py-1 rounded-full bg-black/60 backdrop-blur-md border border-white/10 text-[10px] font-bold text-white/90">
                قالب جاهز
              </div>
            </button>
          ))}
        </div>

        {/* Footer info */}
        <div className="mt-12 text-center">
          <p className="text-sm text-gray-500">
            ما تلقى تخصصك؟{' '}
            <button
              onClick={() => navigate('/freebuild/chat')}
              className="text-amber-300 hover:text-amber-200 underline-offset-4 hover:underline font-bold"
              data-testid="custom-build-link"
            >
              ابني موقعك من الصفر مع Zenrex AI
            </button>
          </p>
        </div>
      </main>
    </div>
  );
}
