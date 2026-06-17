/**
 * VideoStudioModeSelector — 4-mode entry for the Video Studio.
 *
 * Modes:
 *   1. stage_by_stage  — The original 7-phase guided flow
 *   2. open            — Freeform, AI generates without strict phases
 *   3. commercial      — Ads: AI collects logo, phone, CR number, then animates
 *   4. voice_to_video  — Upload audio narration → AI auto-builds visuals on top
 *
 * Creates a project with `mode=video_studio` + `video_submode=<chosen>`.
 */
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowRight, Sparkles, Info, Loader2, Layers, Wand2, Megaphone, Mic2, Check } from 'lucide-react';
import { toast } from 'sonner';

const API = process.env.REACT_APP_BACKEND_URL;

// ───────────────────────────────────────────────────────────────────────────
// Z + Crown SVG — the brand mark for the Video Studio header
// Red Z with a crown on top, surrounded by glowing red borders
// ───────────────────────────────────────────────────────────────────────────
const ZCrownLogo = ({ size = 180 }) => (
  <svg
    viewBox="0 0 200 220"
    width={size}
    height={size * (220 / 200)}
    xmlns="http://www.w3.org/2000/svg"
    style={{ filter: 'drop-shadow(0 0 24px rgba(220, 38, 38, 0.5))' }}
    aria-label="شعار زنركس"
  >
    <defs>
      <linearGradient id="zRed" x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%" stopColor="#fca5a5" />
        <stop offset="35%" stopColor="#ef4444" />
        <stop offset="100%" stopColor="#991b1b" />
      </linearGradient>
      <linearGradient id="crownGold" x1="0%" y1="0%" x2="0%" y2="100%">
        <stop offset="0%" stopColor="#fde68a" />
        <stop offset="55%" stopColor="#f59e0b" />
        <stop offset="100%" stopColor="#b45309" />
      </linearGradient>
    </defs>

    {/* Crown — three peaks with jewels */}
    <g transform="translate(40, 8)">
      <path
        d="M0,48 L0,16 L20,32 L40,4 L60,32 L80,16 L80,48 Z"
        fill="url(#crownGold)"
        stroke="#7c2d12"
        strokeWidth="2"
        strokeLinejoin="round"
      />
      {/* Base band */}
      <rect x="-2" y="46" width="84" height="8" rx="2" fill="#b45309" stroke="#7c2d12" strokeWidth="1.5" />
      {/* Jewels */}
      <circle cx="20" cy="34" r="3.5" fill="#dc2626" stroke="#fff" strokeWidth="0.8" />
      <circle cx="40" cy="14" r="4" fill="#dc2626" stroke="#fff" strokeWidth="0.8" />
      <circle cx="60" cy="34" r="3.5" fill="#dc2626" stroke="#fff" strokeWidth="0.8" />
    </g>

    {/* Z letter — bold geometric */}
    <g transform="translate(28, 72)">
      <path
        d="M0,0 L144,0 L144,28 L52,28 L144,108 L144,140 L0,140 L0,112 L92,112 L0,32 Z"
        fill="url(#zRed)"
        stroke="#7f1d1d"
        strokeWidth="2.5"
        strokeLinejoin="round"
      />
    </g>
  </svg>
);

// ───────────────────────────────────────────────────────────────────────────
// 4 Modes — Stylized Cinema Focus (Feb 2026)
// AI strengths: anime, stylized content, B-roll, voice storytelling.
// AI weaknesses removed: realistic Hollywood films, realistic crowds, etc.
// ───────────────────────────────────────────────────────────────────────────
const MODES = [
  {
    id: 'stage_by_stage',
    title: 'الستوديو المرحلي',
    subtitle: 'أفلام مُنَمَّطة طويلة بـ 7 مراحل',
    desc: 'الذكاء الصناعي يمشي معك خطوة بخطوة لإنتاج فيلم أنمي / كرتون / رعب مُنَمَّط / خيال علمي / فانتازيا. يقسّم القصة إلى لقطات ٥-٨ ثوانٍ ويدمجها لفيلم ٤٥ ثانية - دقيقتين بنفس الستايل.',
    icon: Layers,
    accent: 'from-emerald-400 to-teal-500',
    bullets: [
      'أنمي 2D / كرتون 3D / Cyberpunk / فانتازيا — كل المُنَمَّط',
      'Multi-Clip Stitching: فيلم طويل من ٦-١٥ لقطة بنفس الستايل',
      'تكلفة فيلم دقيقة: ~$2-$3 بدل $17',
      'Character Lock + Style Lock لحفظ الاستمرارية',
    ],
    cta: 'ابدأ مرحلي',
  },
  {
    id: 'open',
    title: 'توليد مفتوح (Open)',
    subtitle: 'لقطة وحدة بلا مراحل',
    desc: 'تكتب فكرتك مباشرة، الذكاء يولّد لقطة ٥-٨ ثوانٍ فوراً. مثالي للتجربة والأفكار السريعة. الافتراضي Hailuo Standard ($0.20 للقطة).',
    icon: Wand2,
    accent: 'from-violet-400 to-fuchsia-500',
    bullets: [
      'لا مراحل، لا قوالب — حرية كاملة',
      'افتراضي Hailuo Standard (~$0.20 للقطة)',
      'تنبيه واضح قبل أي premium tier',
    ],
    cta: 'ابدأ مفتوح',
  },
  {
    id: 'commercial',
    title: 'إعلانات تجارية Stylized',
    subtitle: 'إعلان منتجك في < $1.50',
    desc: 'الذكاء يطلب: الشعار + رقم الجوال + رقم السجل التجاري + نوع الإعلان. ينتج Logo Reveal سينمائي + لقطات Stylized للمنتج + إطار نهاية احترافي.',
    icon: Megaphone,
    accent: 'from-amber-400 to-orange-500',
    bullets: [
      'Logo Reveal Cinematic + Product Showcase Stylized',
      'بيانات التواصل (CR + جوال) overlay احترافي',
      'تكلفة إعلان ١٥ ثانية: $0.80-$1.20 (بدل $5+)',
      'مقاسات: 9:16 / 1:1 / 16:9 جاهزة',
    ],
    cta: 'ابدأ إعلان',
  },
  {
    id: 'voice_to_video',
    title: 'الراوي (Storyteller)',
    subtitle: 'الأقوى تجارياً — قصص يوتيوب',
    desc: 'مثالي لقنوات قصص الرعب، الجرائم الحقيقية، التاريخ، والأساطير. ترفع تسجيلك (أو تكتب نص ونولّد الصوت بـ ElevenLabs v3)، الذكاء يقسّم القصة لمشاهد B-roll مُنَمَّطة تطابق كل جملة.',
    icon: Mic2,
    accent: 'from-rose-400 to-red-500',
    badge: '💰 الأعلى ربحاً',
    bullets: [
      'صوت من تسجيلك أو ElevenLabs v3 (عربي/إنجليزي)',
      'لقطات B-roll مُنَمَّطة بدون وجوه (استمرارية مضمونة)',
      'تكلفة فيديو دقيقة كاملة: ~$2.50-$3',
      'مثالي لقنوات يوتيوب القصصية العربية',
    ],
    cta: 'ابدأ بالصوت',
  },
];

export default function VideoStudioModeSelector({ user }) {
  const navigate = useNavigate();
  const [busyMode, setBusyMode] = useState('');

  useEffect(() => { if (typeof window !== 'undefined') window.scrollTo(0, 0); }, []);

  const handlePick = async (mode) => {
    if (busyMode) return;
    setBusyMode(mode.id);
    try {
      const token = localStorage.getItem('token');
      if (!token) { navigate('/login'); return; }
      const r = await fetch(`${API}/api/freebuild-chat/project`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({
          name: `🎬 ${mode.title}`,
          mode: 'video_studio',
          video_submode: mode.id,
        }),
      });
      if (!r.ok) {
        const errBody = await r.text();
        throw new Error(`HTTP ${r.status} — ${errBody.slice(0, 200)}`);
      }
      const data = await r.json();
      const pid = data.id || data.project_id;
      if (!pid) throw new Error('no project id');
      toast.success(`✨ ${mode.title} جاهز`);
      navigate(`/freebuild/chat/${pid}?mode=video_studio&submode=${mode.id}`);
    } catch (e) {
      toast.error(`فشل فتح الوضع: ${e.message}`);
    } finally {
      setBusyMode('');
    }
  };

  return (
    <div className="min-h-screen bg-[#08070d] text-white" dir="rtl" data-testid="video-studio-mode-selector">
      {/* Disclaimer */}
      <div className="bg-amber-500/10 border-b border-amber-500/30 px-4 py-3">
        <div className="max-w-6xl mx-auto flex items-start gap-3">
          <Info className="w-5 h-5 text-amber-400 flex-shrink-0 mt-0.5" />
          <div className="flex-1 text-sm text-amber-100/90 leading-relaxed">
            <b className="text-amber-300">٤ أوضاع متخصّصة في المحتوى المُنَمَّط:</b> الأنمي، الكرتون، الرعب stylized، الفانتازيا، قصص اليوتيوب، الإعلانات. الافتراضي Hailuo Standard لتوفير ٩٠٪ من التكلفة.
          </div>
        </div>
      </div>

      {/* Hero with Z+Crown logo + red side borders */}
      <header className="relative max-w-6xl mx-auto px-6 pt-10 pb-6">
        {/* Left red border */}
        <div
          className="hidden sm:block absolute top-10 right-0 h-[170px] w-[6px] rounded-full"
          style={{ background: 'linear-gradient(180deg, transparent, #dc2626 30%, #dc2626 70%, transparent)', boxShadow: '0 0 24px rgba(220, 38, 38, 0.6)' }}
        />
        <div
          className="hidden sm:block absolute top-10 left-0 h-[170px] w-[6px] rounded-full"
          style={{ background: 'linear-gradient(180deg, transparent, #dc2626 30%, #dc2626 70%, transparent)', boxShadow: '0 0 24px rgba(220, 38, 38, 0.6)' }}
        />

        <div className="flex flex-col items-center text-center gap-3">
          <ZCrownLogo size={140} />
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-red-500/10 border border-red-500/30 text-red-200 text-xs font-bold">
            <Sparkles className="w-3.5 h-3.5 text-red-300" />
            استوديو الأفلام والفيديوهات
          </div>
          <h1 className="text-4xl sm:text-5xl lg:text-6xl font-black bg-gradient-to-b from-white via-red-100 to-red-400 bg-clip-text text-transparent leading-tight">
            استوديو الأفلام المُنَمَّطة
          </h1>
          <p className="text-base sm:text-lg text-gray-400 max-w-2xl mx-auto leading-relaxed">
            أنمي · كرتون · رعب stylized · فانتازيا · قصص يوتيوب · إعلانات.
            <br />
            <span className="text-amber-300/90 text-sm">⚡ بأرخص نموذج مناسب، بدون هلوسة بمستوى Hollywood.</span>
          </p>
        </div>
      </header>

      {/* 4 mode cards */}
      <main className="max-w-6xl mx-auto px-6 pb-20">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-5 mt-6">
          {MODES.map((m) => {
            const Icon = m.icon;
            const busy = busyMode === m.id;
            return (
              <button
                key={m.id}
                onClick={() => handlePick(m)}
                disabled={!!busyMode}
                data-testid={`video-mode-${m.id}`}
                className="group relative text-right rounded-3xl border border-white/10 bg-white/[0.03] p-6 hover:border-red-400/50 hover:bg-white/[0.06] transition-all duration-300 disabled:opacity-50 disabled:cursor-wait overflow-hidden"
              >
                {/* Accent glow */}
                <div className={`absolute -top-20 -left-20 w-64 h-64 rounded-full bg-gradient-to-br ${m.accent} opacity-20 blur-3xl group-hover:opacity-30 transition-opacity`} />

                <div className="relative flex items-start gap-4">
                  <div className={`p-3 rounded-2xl bg-gradient-to-br ${m.accent} flex-shrink-0`}>
                    <Icon className="w-6 h-6 text-white" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <h3 className="text-xl sm:text-2xl font-black text-white">{m.title}</h3>
                      {m.badge && (
                        <span className="px-2 py-0.5 rounded-full bg-red-500/20 border border-red-500/40 text-red-200 text-xs font-bold">
                          {m.badge}
                        </span>
                      )}
                    </div>
                    <p className="text-sm text-amber-300 font-semibold mt-0.5">{m.subtitle}</p>
                  </div>
                </div>

                <p className="relative text-sm text-white/75 leading-relaxed mt-4">{m.desc}</p>

                <ul className="relative space-y-1.5 mt-4">
                  {m.bullets.map((b, i) => (
                    <li key={i} className="flex items-start gap-2 text-xs sm:text-sm text-white/70">
                      <Check className="w-3.5 h-3.5 text-emerald-400 flex-shrink-0 mt-0.5" />
                      <span>{b}</span>
                    </li>
                  ))}
                </ul>

                <div className="relative mt-5 inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-red-500 text-white text-sm font-bold group-hover:bg-red-400 transition-colors">
                  {busy ? (
                    <><Loader2 className="w-4 h-4 animate-spin" /> جاري الفتح...</>
                  ) : (
                    <><Sparkles className="w-4 h-4" /> {m.cta} <ArrowRight className="w-4 h-4 rotate-180" /></>
                  )}
                </div>
              </button>
            );
          })}
        </div>

        {/* Capability Boundary banner */}
        <div className="mt-6 rounded-2xl border border-amber-500/20 bg-amber-500/[0.04] p-5" data-testid="capability-boundary-banner">
          <div className="text-sm text-amber-100/90 leading-relaxed">
            <b className="text-amber-300">حدود الذكاء الاصطناعي (نكون صريحين معك):</b>
            <br />
            <span className="text-emerald-300/90">✅ نطلع بامتياز:</span> أنمي 2D/3D، رعب stylized، cyberpunk، فانتازيا، لقطات طبيعة، motion graphics، متحدّث واحد + lipsync.
            <br />
            <span className="text-rose-300/90">❌ ما نوعدك بـ:</span> أفلام واقعية بمستوى Hollywood، حشود واقعية، قتال يدوي واقعي بين عدة شخصيات، نصوص عربية كبيرة داخل الفيديو. نقترح بدائل stylized تطلع أحلى وأرخص.
          </div>
        </div>

        {/* Help footer */}
        <div className="mt-4 rounded-2xl border border-white/10 bg-white/[0.02] p-5 text-sm text-white/70 leading-relaxed">
          <b className="text-amber-300">مو متأكد أي وضع تختار؟</b>
          <ul className="mt-2 space-y-1.5">
            <li>🎬 <b>«مرحلي»</b> — لو تبي فيلم أنمي/كرتون طويل (٤٥ ثانية - دقيقتين) بستايل ثابت.</li>
            <li>🎨 <b>«مفتوح»</b> — لو عندك فكرة لقطة وحدة سريعة.</li>
            <li>📢 <b>«إعلانات»</b> — لو تبي تسوّق منتج/خدمة (Logo Reveal + Product Showcase).</li>
            <li>🎙️ <b>«الراوي»</b> — لو عندك قصة (رعب، جريمة، تاريخ) تبي تحوّلها فيديو يوتيوب احترافي.</li>
          </ul>
        </div>
      </main>
    </div>
  );
}
