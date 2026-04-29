import React, { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { Sparkles, Zap, Check, ArrowLeft } from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;

// Top 5 demo categories — picked to represent the breadth of the platform
const DEMO_CATEGORIES = [
  { id: 'restaurant', name: 'مطعم', icon: '🍽️', color: '#E11D48' },
  { id: 'cosmetics',  name: 'مكياج وعطور', icon: '💄', color: '#E91E63' },
  { id: 'realestate', name: 'دلّال عقارات', icon: '🏛️', color: '#B87333' },
  { id: 'automotive', name: 'معرض سيارات', icon: '🏎️', color: '#DC2626' },
  { id: 'gym',        name: 'نادي رياضي', icon: '💪', color: '#10B981' },
];

// 6 hand-picked archetypes — variety in look/structure
const DEMO_ARCHETYPES = [
  { id: 'magazine',                 label: '📰 مجلة فاخرة',      tag: 'Editorial · Serif' },
  { id: 'beauty_megamart',          label: '🌸 ميغا‑متجر',       tag: 'كرت ترويجي + Timer' },
  { id: 'realestate_luxury_dark',   label: '🏛️ فاخر داكن',        tag: 'أسود + نحاسي' },
  { id: 'organic_blobs',            label: '🌿 عضوي ترابي',      tag: 'Blobs + Amiri' },
  { id: 'cyber_glitch',             label: '⚡ سايبر نيون',       tag: 'Neon + Glitch' },
  { id: 'editorial_diagonal',       label: '✂️ قطري مجلّاتي',     tag: 'Diagonal cuts' },
];

export default function DemoLanding() {
  const [step, setStep] = useState(1); // 1=category, 2=archetype, 3=cta
  const [category, setCategory] = useState(null);
  const [archetype, setArchetype] = useState('magazine');
  const [seconds, setSeconds] = useState(60);

  const previewUrl = useMemo(() => {
    if (!category) return '';
    return `${API}/api/websites/categories/${category.id}/layouts/${category.id}__${archetype}/preview-html-raw`;
  }, [category, archetype]);

  // Countdown — once per session, surface the registration CTA after 60s of free trial
  useEffect(() => {
    if (step !== 2) return;
    const t = setInterval(() => {
      setSeconds((s) => {
        if (s <= 1) { clearInterval(t); setStep(3); return 0; }
        return s - 1;
      });
    }, 1000);
    return () => clearInterval(t);
  }, [step]);

  return (
    <div className="min-h-screen bg-[#0a0a0a] text-white" dir="rtl" data-testid="demo-landing">
      {/* Header */}
      <header className="px-6 py-4 border-b border-white/10 flex items-center justify-between sticky top-0 bg-[#0a0a0a]/95 backdrop-blur z-30">
        <Link to="/" className="flex items-center gap-2 text-sm opacity-70 hover:opacity-100" data-testid="back-home">
          <ArrowLeft className="w-4 h-4" /> الرئيسية
        </Link>
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-yellow-400 to-orange-500 flex items-center justify-center font-black text-black">Z</div>
          <span className="font-black">Zitex</span>
        </div>
        {step !== 3 && (
          <Link to="/register" className="text-xs px-3 py-1.5 rounded-full bg-white/10 hover:bg-white/20" data-testid="header-register">
            تسجيل
          </Link>
        )}
        {step === 3 && <span className="w-20" />}
      </header>

      {/* STEP 1 — Category picker */}
      {step === 1 && (
        <div className="max-w-5xl mx-auto px-6 py-12 text-center">
          <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-yellow-500/10 border border-yellow-500/30 text-yellow-300 text-xs font-bold mb-6" data-testid="demo-badge">
            <Sparkles className="w-3.5 h-3.5" /> جرّب 60 ثانية مجاناً — بدون تسجيل
          </div>
          <h1 className="text-4xl md:text-5xl font-black mb-3 bg-gradient-to-r from-yellow-300 via-pink-400 to-cyan-400 bg-clip-text text-transparent">
            شاهد موقعك يُولد أمامك
          </h1>
          <p className="text-white/65 max-w-xl mx-auto mb-10 text-sm md:text-base">
            اختر نوع موقعك، شاهد التصميم يُبنى لحظياً، ثم احفظه عند الإعجاب. لا توجد بطاقة ائتمان مطلوبة.
          </p>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
            {DEMO_CATEGORIES.map((c) => (
              <button
                key={c.id}
                onClick={() => { setCategory(c); setStep(2); setSeconds(60); }}
                className="group relative aspect-square rounded-2xl border-2 border-white/10 hover:border-yellow-400/70 hover:-translate-y-1 transition-all duration-300 overflow-hidden"
                style={{ background: `linear-gradient(135deg, ${c.color}22, transparent)` }}
                data-testid={`demo-cat-${c.id}`}
              >
                <div className="absolute inset-0 flex flex-col items-center justify-center gap-2 p-4">
                  <div className="text-5xl group-hover:scale-110 transition-transform">{c.icon}</div>
                  <div className="font-black text-lg">{c.name}</div>
                  <div className="text-[11px] opacity-60 group-hover:opacity-90">جرّب الآن ←</div>
                </div>
              </button>
            ))}
          </div>
          <div className="mt-12 flex items-center justify-center gap-6 text-xs text-white/50">
            <span className="flex items-center gap-1"><Check className="w-3.5 h-3.5 text-emerald-400" /> 25 فئة</span>
            <span className="flex items-center gap-1"><Check className="w-3.5 h-3.5 text-emerald-400" /> 25 قالب لكل فئة</span>
            <span className="flex items-center gap-1"><Check className="w-3.5 h-3.5 text-emerald-400" /> صور احترافية لكل فئة</span>
          </div>
        </div>
      )}

      {/* STEP 2 — Live preview + archetype switch */}
      {step === 2 && category && (
        <div className="grid grid-cols-1 lg:grid-cols-[320px_1fr] min-h-[calc(100vh-65px)]">
          {/* Sidebar — archetype selector */}
          <aside className="border-l border-white/10 bg-white/[.02] p-5 overflow-y-auto" data-testid="demo-sidebar">
            <button onClick={() => setStep(1)} className="text-xs opacity-60 hover:opacity-100 mb-4 flex items-center gap-1" data-testid="demo-back">
              <ArrowLeft className="w-3 h-3" /> غيّر الفئة
            </button>
            <div className="text-[11px] uppercase tracking-widest text-yellow-400 mb-1">الفئة المختارة</div>
            <div className="font-black text-xl mb-1">{category.icon} {category.name}</div>
            <div className="h-px bg-white/10 my-4" />
            <div className="text-[11px] uppercase tracking-widest text-white/50 mb-3">جرّب أنماط مختلفة</div>
            <div className="space-y-2">
              {DEMO_ARCHETYPES.map((a) => (
                <button
                  key={a.id}
                  onClick={() => setArchetype(a.id)}
                  className={`w-full text-right p-3 rounded-xl border transition-all ${archetype === a.id
                    ? 'bg-gradient-to-l from-yellow-500/20 to-pink-500/10 border-yellow-400/60'
                    : 'bg-white/5 border-white/10 hover:border-white/30'}`}
                  data-testid={`demo-arch-${a.id}`}
                >
                  <div className="font-bold text-sm">{a.label}</div>
                  <div className="text-[11px] opacity-60 mt-0.5">{a.tag}</div>
                </button>
              ))}
            </div>
            <div className="mt-6 p-4 rounded-xl bg-gradient-to-br from-pink-500/15 to-purple-500/10 border border-pink-500/30 text-center" data-testid="demo-timer">
              <div className="text-[11px] opacity-70 mb-1">يتبقى من المعاينة المجانية</div>
              <div className="text-3xl font-black text-pink-300 tabular-nums">{seconds}s</div>
              <Link
                to="/register"
                className="mt-3 inline-block w-full py-2 rounded-full bg-gradient-to-r from-yellow-400 to-orange-500 text-black font-black text-sm hover:scale-[1.02] transition"
                data-testid="demo-cta-register-sidebar"
              >
                ⚡ احفظ موقعك — مجاني
              </Link>
            </div>
          </aside>
          {/* Live preview */}
          <main className="bg-white/[.02] p-3 lg:p-5">
            <div className="flex items-center justify-between mb-3 px-2">
              <div className="flex items-center gap-1.5">
                <span className="w-3 h-3 rounded-full bg-red-500/70" />
                <span className="w-3 h-3 rounded-full bg-yellow-500/70" />
                <span className="w-3 h-3 rounded-full bg-green-500/70" />
                <span className="text-xs text-white/50 mr-3">معاينة حية · {category.name}</span>
              </div>
              <span className="text-[11px] text-white/50">⚡ يتغيّر فوراً عند الاختيار</span>
            </div>
            <div className="rounded-2xl overflow-hidden border border-white/10 bg-white" style={{ height: 'calc(100vh - 160px)' }}>
              <iframe
                src={previewUrl}
                className="w-full h-full border-0"
                title="Live Demo Preview"
                sandbox="allow-same-origin allow-scripts"
                data-testid="demo-preview-iframe"
              />
            </div>
          </main>
        </div>
      )}

      {/* STEP 3 — CTA after timer */}
      {step === 3 && (
        <div className="max-w-2xl mx-auto px-6 py-16 text-center">
          <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-pink-500/15 border border-pink-500/30 text-pink-300 text-xs font-bold mb-6">
            <Zap className="w-3.5 h-3.5" /> انتهت الـ60 ثانية المجانية
          </div>
          <h2 className="text-4xl md:text-5xl font-black mb-4 bg-gradient-to-r from-pink-400 to-yellow-400 bg-clip-text text-transparent">
            عجبك التصميم؟
          </h2>
          <p className="text-white/65 mb-8">
            احفظ موقعك الحالي، خصّص الألوان والأقسام، وأطلقه على دومينك خلال دقائق.
          </p>
          <div className="rounded-2xl border border-white/10 bg-white/5 p-6 mb-6 text-right" data-testid="demo-checklist">
            <div className="text-[11px] uppercase tracking-widest text-yellow-400 mb-3">بعد التسجيل تحصل على:</div>
            <ul className="space-y-2 text-sm">
              {[
                'حفظ كل قوالبك الحالية + إضافة المزيد',
                'تخصيص كامل (ألوان، خطوط، أقسام، widgets)',
                'ربط دومينك الخاص',
                'لوحة تحكم تجار + سائقين + خرائط حية',
                'دفعات Stripe / Moyasar / Tabby / Tamara',
              ].map((x) => (
                <li key={x} className="flex items-start gap-2">
                  <Check className="w-4 h-4 text-emerald-400 flex-shrink-0 mt-0.5" />
                  <span>{x}</span>
                </li>
              ))}
            </ul>
          </div>
          <div className="flex flex-col sm:flex-row gap-3 justify-center">
            <Link
              to="/register"
              className="px-8 py-3 rounded-full bg-gradient-to-r from-yellow-400 to-orange-500 text-black font-black text-base hover:scale-[1.03] transition shadow-lg shadow-yellow-500/30"
              data-testid="demo-cta-register-final"
            >
              ⚡ سجّل واحفظ موقعي (مجاني)
            </Link>
            <button
              onClick={() => { setSeconds(60); setStep(2); }}
              className="px-8 py-3 rounded-full bg-white/10 hover:bg-white/20 text-sm"
              data-testid="demo-cta-retry"
            >
              ↻ تجربة قالب آخر
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
