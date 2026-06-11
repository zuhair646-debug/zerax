import React from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, Check } from 'lucide-react';

// ─── Variant 1: Minimal Pure Z (no orbits, just shimmer + glow) ───
const LogoMinimal = ({ size = 96 }) => {
  const uid = React.useId();
  return (
    <span className="zlp-wrap" style={{ width: size, height: size, display: 'inline-block' }}>
      <svg viewBox="0 0 100 100" width={size} height={size} fill="none" style={{ overflow: 'visible' }}>
        <defs>
          <linearGradient id={`a-${uid}`} x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stopColor="#fef3c7" />
            <stop offset="50%" stopColor="#f59e0b" />
            <stop offset="100%" stopColor="#92400e" />
          </linearGradient>
          <linearGradient id={`s-${uid}`} x1="0" y1="0" x2="1" y2="0">
            <stop offset="0%" stopColor="#fde68a" stopOpacity="0" />
            <stop offset="50%" stopColor="#fff7ed" stopOpacity=".9" />
            <stop offset="100%" stopColor="#fde68a" stopOpacity="0" />
          </linearGradient>
        </defs>
        <g className="zlp-minimal-pulse">
          <path d="M 24 24 L 76 24 L 76 32 L 38 68 L 76 68 L 76 76 L 24 76 L 24 68 L 62 32 L 24 32 Z" fill={`url(#a-${uid})`} stroke="#fcd34d" strokeWidth=".6" />
          <path d="M 24 24 L 76 24 L 76 32 L 38 68 L 76 68 L 76 76 L 24 76 L 24 68 L 62 32 L 24 32 Z" fill={`url(#s-${uid})`} className="zlp-minimal-shine" />
        </g>
      </svg>
    </span>
  );
};

// ─── Variant 2: Constellation Z (Z + stars that twinkle around it) ───
const LogoConstellation = ({ size = 96 }) => {
  const uid = React.useId();
  const stars = [
    { x: 10, y: 18, d: 0 }, { x: 90, y: 22, d: .3 }, { x: 8, y: 78, d: .6 },
    { x: 92, y: 82, d: .9 }, { x: 50, y: 6, d: 1.2 }, { x: 50, y: 92, d: 1.5 },
    { x: 15, y: 50, d: 1.8 }, { x: 85, y: 50, d: 2.1 },
  ];
  return (
    <span className="zlp-wrap" style={{ width: size, height: size, display: 'inline-block' }}>
      <svg viewBox="0 0 100 100" width={size} height={size} fill="none" style={{ overflow: 'visible' }}>
        <defs>
          <linearGradient id={`b-${uid}`} x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stopColor="#fde68a" />
            <stop offset="50%" stopColor="#f59e0b" />
            <stop offset="100%" stopColor="#b45309" />
          </linearGradient>
        </defs>
        <path d="M 26 26 L 74 26 L 74 34 L 40 66 L 74 66 L 74 74 L 26 74 L 26 66 L 60 34 L 26 34 Z" fill={`url(#b-${uid})`} stroke="#fbbf24" strokeWidth=".5" />
        {stars.map((s, i) => (
          <g key={i}>
            <circle cx={s.x} cy={s.y} r="1.2" fill="#fef3c7" className="zlp-star-twinkle" style={{ animationDelay: `${s.d}s` }} />
            <line x1={s.x - 3} y1={s.y} x2={s.x + 3} y2={s.y} stroke="#fde68a" strokeWidth=".3" opacity=".5" className="zlp-star-twinkle" style={{ animationDelay: `${s.d}s` }} />
            <line x1={s.x} y1={s.y - 3} x2={s.x} y2={s.y + 3} stroke="#fde68a" strokeWidth=".3" opacity=".5" className="zlp-star-twinkle" style={{ animationDelay: `${s.d}s` }} />
          </g>
        ))}
      </svg>
    </span>
  );
};

// ─── Variant 3: Neon Outline Z (just outline, neon glow, breathing) ───
const LogoNeon = ({ size = 96 }) => {
  const uid = React.useId();
  return (
    <span className="zlp-wrap" style={{ width: size, height: size, display: 'inline-block' }}>
      <svg viewBox="0 0 100 100" width={size} height={size} fill="none" style={{ overflow: 'visible' }}>
        <defs>
          <filter id={`ng-${uid}`} x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur stdDeviation="2.4" result="b" />
            <feMerge><feMergeNode in="b" /><feMergeNode in="SourceGraphic" /></feMerge>
          </filter>
        </defs>
        <g filter={`url(#ng-${uid})`} className="zlp-neon-breathe">
          <path d="M 22 24 L 78 24 L 78 33 L 38 67 L 78 67 L 78 76 L 22 76 L 22 67 L 62 33 L 22 33 Z" fill="none" stroke="#fbbf24" strokeWidth="2.2" strokeLinejoin="round" />
          <path d="M 22 24 L 78 24 L 78 33 L 38 67 L 78 67 L 78 76 L 22 76 L 22 67 L 62 33 L 22 33 Z" fill="none" stroke="#fef3c7" strokeWidth=".6" strokeLinejoin="round" opacity=".8" />
        </g>
      </svg>
    </span>
  );
};

// ─── Variant 4: 3D Stacked Z (depth with offset layers) ───
const LogoStacked = ({ size = 96 }) => {
  const uid = React.useId();
  return (
    <span className="zlp-wrap" style={{ width: size, height: size, display: 'inline-block' }}>
      <svg viewBox="0 0 100 100" width={size} height={size} fill="none" style={{ overflow: 'visible' }}>
        <defs>
          <linearGradient id={`d-${uid}`} x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stopColor="#fbbf24" />
            <stop offset="100%" stopColor="#92400e" />
          </linearGradient>
        </defs>
        <g className="zlp-stacked-tilt">
          {/* Back shadow layers */}
          <path d="M 30 30 L 80 30 L 80 38 L 44 70 L 80 70 L 80 78 L 30 78 L 30 70 L 66 38 L 30 38 Z" fill="#92400e" opacity=".25" />
          <path d="M 27 27 L 77 27 L 77 35 L 41 67 L 77 67 L 77 75 L 27 75 L 27 67 L 63 35 L 27 35 Z" fill="#b45309" opacity=".5" />
          {/* Front main layer */}
          <path d="M 24 24 L 74 24 L 74 32 L 38 64 L 74 64 L 74 72 L 24 72 L 24 64 L 60 32 L 24 32 Z" fill={`url(#d-${uid})`} stroke="#fef3c7" strokeWidth=".5" />
        </g>
      </svg>
    </span>
  );
};

// ─── Variant 5: Liquid Z (filling animation from bottom up) ───
const LogoLiquid = ({ size = 96 }) => {
  const uid = React.useId();
  return (
    <span className="zlp-wrap" style={{ width: size, height: size, display: 'inline-block' }}>
      <svg viewBox="0 0 100 100" width={size} height={size} fill="none" style={{ overflow: 'visible' }}>
        <defs>
          <linearGradient id={`l-${uid}`} x1="0" y1="1" x2="0" y2="0">
            <stop offset="0%" stopColor="#92400e" />
            <stop offset="50%" stopColor="#f59e0b" />
            <stop offset="100%" stopColor="#fef3c7" />
          </linearGradient>
          <clipPath id={`cz-${uid}`}>
            <path d="M 24 24 L 76 24 L 76 32 L 38 68 L 76 68 L 76 76 L 24 76 L 24 68 L 62 32 L 24 32 Z" />
          </clipPath>
        </defs>
        {/* Outline */}
        <path d="M 24 24 L 76 24 L 76 32 L 38 68 L 76 68 L 76 76 L 24 76 L 24 68 L 62 32 L 24 32 Z" fill="none" stroke="#fbbf24" strokeWidth="1.4" opacity=".55" />
        {/* Liquid fill */}
        <g clipPath={`url(#cz-${uid})`}>
          <rect x="0" y="0" width="100" height="100" fill={`url(#l-${uid})`} />
          {/* wave on top */}
          <path className="zlp-liquid-wave" d="M -10 50 Q 25 42 60 50 T 130 50 V 100 H -10 Z" fill="#0a0a12" opacity=".95" />
        </g>
      </svg>
    </span>
  );
};

const VARIANTS = [
  { id: 'v1', name: 'الخيار 1 — حرف نظيف', desc: 'حرف Z واضح بدون أي عناصر إضافية، فيه فقط لمعان ذهبي يمرّ عليه + توهج خفيف', Comp: LogoMinimal },
  { id: 'v2', name: 'الخيار 2 — نجوم حوله', desc: 'حرف Z ثابت ومحاط بنجوم ذهبية صغيرة تومض بترتيب لطيف', Comp: LogoConstellation },
  { id: 'v3', name: 'الخيار 3 — نيون مفرّغ', desc: 'حدود الحرف فقط (بدون تعبئة)، توهج نيون متنفّس يكبر ويصغر', Comp: LogoNeon },
  { id: 'v4', name: 'الخيار 4 — مجسّم 3D', desc: 'حرف Z بثلاث طبقات متراكبة تعطي عمق ثلاثي الأبعاد، يميل برفق', Comp: LogoStacked },
  { id: 'v5', name: 'الخيار 5 — تعبئة سائلة', desc: 'حرف Z يمتلئ بسائل ذهبي من تحت لفوق بحركة موجة هادئة', Comp: LogoLiquid },
];

export default function LogoPicker() {
  const nav = useNavigate();
  const [chosen, setChosen] = React.useState(null);

  return (
    <div className="min-h-screen bg-[#0a0a12] text-white" dir="rtl">
      <header className="sticky top-0 z-10 bg-[#0a0a12]/95 backdrop-blur border-b border-amber-500/15">
        <div className="max-w-5xl mx-auto px-5 py-4 flex items-center gap-3">
          <button onClick={() => nav('/')} className="p-2 rounded-lg hover:bg-amber-500/10 text-amber-400" data-testid="logo-picker-back">
            <ArrowLeft className="w-5 h-5" />
          </button>
          <div className="flex-1">
            <h1 className="text-xl font-black text-amber-300">اختر شعار Zenrex</h1>
            <p className="text-xs text-white/55">5 خيارات بنفس اللون الذهبي — كل واحد بحركة مختلفة. اضغط على اللي يعجبك.</p>
          </div>
        </div>
      </header>

      <div className="max-w-5xl mx-auto px-5 py-8">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
          {VARIANTS.map((v) => {
            const Comp = v.Comp;
            const active = chosen === v.id;
            return (
              <div
                key={v.id}
                onClick={() => setChosen(v.id)}
                className={`relative rounded-2xl border-2 p-6 cursor-pointer transition-all ${
                  active
                    ? 'border-amber-400 bg-amber-500/10 shadow-[0_10px_40px_-10px_rgba(251,191,36,0.5)]'
                    : 'border-white/10 bg-zinc-950/60 hover:border-amber-400/40'
                }`}
                data-testid={`logo-variant-${v.id}`}
              >
                {active && (
                  <div className="absolute top-3 left-3 w-7 h-7 rounded-full bg-amber-400 text-black flex items-center justify-center">
                    <Check className="w-4 h-4" strokeWidth={3} />
                  </div>
                )}
                <div className="flex justify-center mb-4 h-28 items-center">
                  <Comp size={108} />
                </div>
                <div className="text-center">
                  <h3 className="text-base font-black text-amber-200 mb-1">{v.name}</h3>
                  <p className="text-xs text-white/55 leading-relaxed">{v.desc}</p>
                </div>
              </div>
            );
          })}
        </div>

        {chosen && (
          <div className="mt-8 p-5 rounded-xl border border-amber-400/30 bg-amber-500/5">
            <div className="flex items-center gap-4 flex-wrap">
              <div className="text-sm text-amber-200">
                اخترت: <span className="font-black">{VARIANTS.find((v) => v.id === chosen).name}</span>
              </div>
              <div className="text-xs text-white/55">
                — رجع للشات قول لي: <code className="text-amber-300 bg-black/40 px-2 py-0.5 rounded">طبّق {chosen}</code> — وأطبّقه فوراً على كامل الموقع.
              </div>
            </div>
          </div>
        )}

        <div className="mt-10 p-4 rounded-xl border border-white/10 bg-zinc-950/60">
          <h4 className="text-sm font-bold text-amber-300 mb-2">ملاحظات:</h4>
          <ul className="text-xs text-white/60 space-y-1 list-disc list-inside">
            <li>كل الخيارات تستخدم نفس درجات الذهبي الحالية — ما يتغيّر اللون.</li>
            <li>الحركات هادئة وغير مزعجة — الأطول 8 ثواني والأقصر ~3 ثواني.</li>
            <li>الحجم يتكيّف تلقائياً (Navbar صغير، Hero كبير).</li>
            <li>تقدر تخلّيه ثابت بإطفاء الحركة من خاصية <code className="text-amber-300">animated</code>.</li>
          </ul>
        </div>
      </div>
    </div>
  );
}
