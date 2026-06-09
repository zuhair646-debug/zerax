import React, { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Play, Image as ImageIcon, Gamepad2, Smartphone, Sparkles, ArrowLeft } from 'lucide-react';

/**
 * HeroBanner — compact rotating banner (same height as old CTA).
 * Slides rotate every 8s. Click takes user to the slide's target section.
 */
const SLIDES = [
  {
    id: 'zerax-intro',
    kind: 'brand',
    title: 'ذكاء Zerax',
    sub: 'يبني، يبحث، يولّد — في شات واحد',
    cta: 'ابدأ الآن',
    target: '/ai-agent',
    icon: Sparkles,
    accent: '#fbbf24',
    bg: 'linear-gradient(135deg,#1f1305 0%,#0a0a12 55%,#3a1f00 100%)',
    motionType: 'orbit',
  },
  {
    id: 'video',
    kind: 'media',
    title: 'فيديوهات سينمائية بـ Sora 2',
    sub: 'أنشئ إعلانك القادم في دقيقة',
    cta: 'جرّب الفيديو',
    target: '/chat/video',
    icon: Play,
    accent: '#f43f5e',
    bg: 'linear-gradient(135deg,#1a0510 0%,#0a0a12 60%,#3a0820 100%)',
    bgImage: 'https://images.unsplash.com/photo-1485846234645-a62644f84728?auto=format&fit=crop&w=1600&q=70',
    motionType: 'scanline',
  },
  {
    id: 'image',
    kind: 'media',
    title: 'صور احترافية بـ Flux Pro Ultra',
    sub: 'لوقو، منتجات، بنرات، إعلانات',
    cta: 'أنشئ صورة',
    target: '/chat/image',
    icon: ImageIcon,
    accent: '#a855f7',
    bg: 'linear-gradient(135deg,#0f0518 0%,#0a0a12 60%,#2a0a40 100%)',
    bgImage: 'https://images.unsplash.com/photo-1502691876148-a84978e59af8?auto=format&fit=crop&w=1600&q=70',
    motionType: 'pixels',
  },
  {
    id: 'game',
    kind: 'media',
    title: 'ابني لعبتك',
    sub: 'Phaser · Three.js · Unity — جاهزة للنشر',
    cta: 'افتح الألعاب',
    target: '/games/web',
    icon: Gamepad2,
    accent: '#84cc16',
    bg: 'linear-gradient(135deg,#0a1505 0%,#0a0a12 60%,#1a3000 100%)',
    bgImage: 'https://images.unsplash.com/photo-1493711662062-fa541adb3fc8?auto=format&fit=crop&w=1600&q=70',
    motionType: 'pulse',
  },
  {
    id: 'app',
    kind: 'media',
    title: 'تطبيقك من الصفر',
    sub: 'React Native · Flutter · Native · سطح المكتب',
    cta: 'ابدأ التطبيق',
    target: '/app-builder',
    icon: Smartphone,
    accent: '#06b6d4',
    bg: 'linear-gradient(135deg,#051018 0%,#0a0a12 60%,#003040 100%)',
    bgImage: 'https://images.unsplash.com/photo-1512941937669-90a1b58e7e9c?auto=format&fit=crop&w=1600&q=70',
    motionType: 'grid',
  },
];

const SLIDE_DURATION_MS = 8000;

export default function HeroBanner({ onGo }) {
  const navigate = useNavigate();
  const [idx, setIdx] = useState(0);
  const [paused, setPaused] = useState(false);
  const timerRef = useRef(null);

  useEffect(() => {
    if (paused) return;
    timerRef.current = setTimeout(() => setIdx((i) => (i + 1) % SLIDES.length), SLIDE_DURATION_MS);
    return () => clearTimeout(timerRef.current);
  }, [idx, paused]);

  const slide = SLIDES[idx];
  const Icon = slide.icon;

  const go = () => (onGo ? onGo(slide.target) : navigate(slide.target));

  return (
    <div
      className="hero-banner relative w-full rounded-2xl overflow-hidden border border-white/10 cursor-pointer group"
      style={{ height: 'clamp(118px,14vw,148px)' }}
      onClick={go}
      onMouseEnter={() => setPaused(true)}
      onMouseLeave={() => setPaused(false)}
      data-testid="hero-banner-carousel"
    >
      {/* Slides stack */}
      {SLIDES.map((s, i) => {
        const SI = s.icon;
        return (
          <div
            key={s.id}
            className={`absolute inset-0 transition-opacity duration-700 ${i === idx ? 'opacity-100 z-10' : 'opacity-0 z-0 pointer-events-none'}`}
            data-testid={`hero-slide-${s.id}`}
          >
            {/* base background */}
            <div className="absolute inset-0" style={{ background: s.bg }} />
            {/* image (if any) */}
            {s.bgImage && (
              <div
                className="absolute inset-0 bg-cover bg-center opacity-35 group-hover:opacity-50 transition-opacity duration-700"
                style={{ backgroundImage: `url('${s.bgImage}')` }}
              />
            )}
            {/* motion layer */}
            <MotionLayer type={s.motionType} accent={s.accent} />
            {/* darken right-to-left for text legibility */}
            <div className="absolute inset-0 bg-gradient-to-l from-black/85 via-black/50 to-transparent" />

            {/* content */}
            <div className="relative h-full px-4 sm:px-6 flex items-center gap-4">
              {/* icon badge */}
              <div
                className="flex-shrink-0 w-12 h-12 sm:w-14 sm:h-14 rounded-xl flex items-center justify-center"
                style={{
                  background: `linear-gradient(135deg, ${s.accent}40, ${s.accent}10)`,
                  border: `1px solid ${s.accent}50`,
                  boxShadow: `0 0 24px ${s.accent}40`,
                }}
              >
                <SI className="w-6 h-6 sm:w-7 sm:h-7" style={{ color: s.accent }} />
              </div>

              {/* text */}
              <div className="flex-1 min-w-0 text-right">
                <div
                  className="text-[10px] sm:text-[11px] font-black tracking-widest mb-0.5"
                  style={{ color: s.accent }}
                >
                  {s.kind === 'brand' ? 'منصّة Zerax' : 'استكشف القسم'}
                </div>
                <h3 className="text-base sm:text-xl font-black text-white leading-tight truncate">{s.title}</h3>
                <p className="hidden sm:block text-[11px] sm:text-xs text-white/65 mt-0.5 truncate">{s.sub}</p>
              </div>

              {/* CTA pill */}
              <div
                className="flex-shrink-0 hidden sm:flex items-center gap-1.5 px-3 sm:px-4 py-2 rounded-lg font-black text-xs whitespace-nowrap transition-transform group-hover:scale-105"
                style={{
                  background: `linear-gradient(135deg, ${s.accent}, ${s.accent}cc)`,
                  color: '#0a0a12',
                  boxShadow: `0 6px 22px -6px ${s.accent}90`,
                }}
              >
                <ArrowLeft className="w-3.5 h-3.5" />
                {s.cta}
              </div>
            </div>
          </div>
        );
      })}

      {/* dots indicator */}
      <div className="absolute bottom-1.5 left-1/2 -translate-x-1/2 z-20 flex items-center gap-1.5">
        {SLIDES.map((s, i) => (
          <button
            key={s.id}
            onClick={(e) => { e.stopPropagation(); setIdx(i); }}
            className={`transition-all rounded-full ${i === idx ? 'w-6 h-1.5' : 'w-1.5 h-1.5 hover:opacity-100'}`}
            style={{
              background: i === idx ? slide.accent : 'rgba(255,255,255,.35)',
              opacity: i === idx ? 1 : 0.6,
            }}
            aria-label={`Go to slide ${i + 1}`}
            data-testid={`hero-banner-dot-${i}`}
          />
        ))}
      </div>

      {/* progress bar */}
      <div className="absolute bottom-0 left-0 right-0 h-[2px] bg-white/5 z-20">
        <div
          key={`${slide.id}-${idx}`}
          className="h-full hero-banner-progress"
          style={{
            background: `linear-gradient(to right, ${slide.accent}, ${slide.accent}80)`,
            animationDuration: `${SLIDE_DURATION_MS}ms`,
            animationPlayState: paused ? 'paused' : 'running',
          }}
        />
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────
// MotionLayer — CSS-only motion graphics per slide (no real video required)
// ─────────────────────────────────────────────────────────
function MotionLayer({ type, accent }) {
  if (type === 'orbit') {
    // Zerax brand slide: transparent L1 logo, gentle float + glow only (no rings, no box)
    return (
      <div
        className="absolute right-4 sm:right-8 top-1/2 -translate-y-1/2 pointer-events-none flex items-center justify-center"
        style={{ width: 120, height: 120 }}
      >
        <img
          src="/zerax-logo.png"
          alt="Zerax"
          className="hb-brand-logo"
          width={112}
          height={112}
          style={{ width: 112, height: 112, objectFit: 'contain' }}
        />
      </div>
    );
  }

  if (type === 'scanline') {
    // Video slide: vertical scanlines + sweeping bar (cinematic feel)
    return (
      <>
        <div
          className="absolute inset-0 pointer-events-none opacity-25"
          style={{
            backgroundImage:
              'repeating-linear-gradient(0deg, rgba(255,255,255,0) 0px, rgba(255,255,255,0) 2px, rgba(255,255,255,.08) 2px, rgba(255,255,255,.08) 3px)',
          }}
        />
        <div
          className="absolute top-0 bottom-0 w-24 hb-scan-sweep pointer-events-none"
          style={{
            background: `linear-gradient(90deg, transparent, ${accent}40, transparent)`,
          }}
        />
      </>
    );
  }

  if (type === 'pixels') {
    // Image slide: floating colored pixels (image generation aesthetic)
    return (
      <div className="absolute inset-0 pointer-events-none overflow-hidden">
        {[...Array(12)].map((_, i) => (
          <span
            key={i}
            className="absolute rounded-sm hb-pixel-float"
            style={{
              width: 6 + (i % 3) * 3,
              height: 6 + (i % 3) * 3,
              left: `${10 + (i * 7) % 80}%`,
              top: `${15 + (i * 13) % 70}%`,
              background: accent,
              opacity: 0.55,
              animationDelay: `${i * 0.4}s`,
              animationDuration: `${4 + (i % 3)}s`,
            }}
          />
        ))}
      </div>
    );
  }

  if (type === 'pulse') {
    // Game slide: concentric rings pulsing outward (controller vibe)
    return (
      <div className="absolute right-6 top-1/2 -translate-y-1/2 pointer-events-none">
        {[0, 1, 2].map((i) => (
          <span
            key={i}
            className="absolute rounded-full hb-ring-pulse"
            style={{
              width: 80,
              height: 80,
              top: -40,
              right: -40,
              border: `1.5px solid ${accent}`,
              animationDelay: `${i * 0.9}s`,
            }}
          />
        ))}
      </div>
    );
  }

  if (type === 'grid') {
    // App slide: tech grid that breathes (mobile/desktop building blocks)
    return (
      <div
        className="absolute inset-0 pointer-events-none opacity-25 hb-grid-breathe"
        style={{
          backgroundImage: `linear-gradient(${accent}40 1px, transparent 1px), linear-gradient(90deg, ${accent}40 1px, transparent 1px)`,
          backgroundSize: '24px 24px',
        }}
      />
    );
  }

  return null;
}
