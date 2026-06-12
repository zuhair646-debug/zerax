/**
 * Studio Landing — generic entry page for Image Studio / Video Studio.
 *
 * Both studios reuse the existing FreeBuild chat workspace. This page only
 * creates a project with the correct `mode` and forwards the user.
 */
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowRight, Sparkles, Info, Loader2 } from 'lucide-react';
import { toast } from 'sonner';

const API = process.env.REACT_APP_BACKEND_URL;

const STUDIOS = {
  image_studio: {
    title: 'استوديو الصور',
    subtitle: 'ولّد بوسترات، إعلانات، Hero، أغلفة، شخصيات، صور سوشيال — كلها بـ AI',
    accent: 'from-amber-500 to-rose-500',
    icon: '🎨',
    bullets: [
      'محادثة حرّة طبيعية باللهجة اللي تحبها',
      'توليد صور بـ Gemini Nano Banana (1024×1024 افتراضياً)',
      'معرض شخصي للصور مع زر تنزيل لكل واحدة',
      'تعديل الـ prompt بالعربي → AI يترجمه لـ prompt احترافي',
      'تكامل كامل مع نظام النقاط (8 نقاط/صورة)',
    ],
    cover: 'https://images.unsplash.com/photo-1547119957-637f8679db1e?w=900&q=80&auto=format&fit=crop',
    cta: 'افتح الاستوديو',
  },
  video_studio: {
    title: 'استوديو الأفلام والفيديوهات',
    subtitle: 'منصة إنتاج سينمائية بالذكاء الاصطناعي — أفلام كاملة، إعلانات، محتوى سوشيال احترافي',
    accent: 'from-fuchsia-500 to-violet-600',
    icon: '🎬',
    bullets: [
      '🎥 إنتاج مشاهد سينمائية (Sora 2 · Veo 3 · Kling) — جودة 1080p',
      '🎞️ مونتاج تلقائي بـ AI: قصات، انتقالات، إيقاع موسيقي',
      '🗣️ تعليق صوتي بأصوات سعودية وعربية واضحة (ElevenLabs)',
      '🎵 موسيقى تصويرية ذكية تناسب المشهد',
      '📝 سب-تايتلز تلقائية بالعربي والإنجليزي (Whisper)',
      '📥 سحب مقاطع من يوتيوب/تيكتوك/إنستا للاستلهام أو إعادة المونتاج',
      '🎬 سيناريو + ستوري بورد + إنتاج كامل في chat واحد',
      '⚡ النتيجة: فيلم احترافي بدون أخطاء تقنية أو حركية',
    ],
    cover: 'https://images.unsplash.com/photo-1611162617474-5b21e879e113?w=900&q=80&auto=format&fit=crop',
    cta: 'افتح الاستوديو السينمائي',
  },
};

export default function StudioLanding({ mode, user }) {
  const navigate = useNavigate();
  const [busy, setBusy] = useState(false);
  const info = STUDIOS[mode] || STUDIOS.image_studio;

  useEffect(() => { if (typeof window !== 'undefined') window.scrollTo(0, 0); }, []);

  const handleOpen = async () => {
    if (busy) return;
    setBusy(true);
    try {
      const token = localStorage.getItem('token');
      if (!token) { navigate('/login'); return; }
      const r = await fetch(`${API}/api/freebuild-chat/project`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({
          name: `${info.icon} ${info.title}`,
          mode,  // backend reads this to switch AI system prompt
        }),
      });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const data = await r.json();
      const pid = data.id || data.project_id;
      if (!pid) throw new Error('no project id');
      toast.success(`✨ ${info.title} جاهز`);
      navigate(`/freebuild/chat/${pid}?mode=${mode}`);
    } catch (e) {
      toast.error(`فشل فتح الاستوديو: ${e.message}`);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#08070d] text-white" dir="rtl" data-testid={`studio-${mode}-page`}>
      {/* Disclaimer banner — same wording as Ready Sites for consistency */}
      <div className="bg-amber-500/10 border-b border-amber-500/30 px-4 py-3">
        <div className="max-w-5xl mx-auto flex items-start gap-3">
          <Info className="w-5 h-5 text-amber-400 flex-shrink-0 mt-0.5" />
          <div className="flex-1 text-sm text-amber-100/90 leading-relaxed">
            <b className="text-amber-300">إخلاء مسؤولية:</b> الذكاء الاصطناعي محترف، لكن النتيجة تعتمد
            على وضوح طلباتك. بعض المحتوى المُنزّل (يوتيوب/تيكتوك) قد يخضع لحقوق نشر — استخدمه بمسؤولية.
          </div>
        </div>
      </div>

      <main className="max-w-5xl mx-auto px-6 pt-12 pb-20">
        <div className="text-center mb-10">
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-white/5 border border-white/10 text-white/70 text-xs font-bold mb-4">
            <Sparkles className="w-3.5 h-3.5 text-amber-300" />
            استوديو متخصّص · نفس واجهة الشات اللي تعرفها
          </div>
          <h1 className="text-4xl sm:text-5xl lg:text-6xl font-black mb-3 bg-gradient-to-b from-white to-amber-200 bg-clip-text text-transparent leading-tight">
            {info.icon} {info.title}
          </h1>
          <p className="text-base sm:text-lg text-gray-400 max-w-2xl mx-auto leading-relaxed">
            {info.subtitle}
          </p>
        </div>

        <div className="rounded-3xl border border-white/10 bg-white/[0.02] overflow-hidden hover:border-amber-400/40 transition-all duration-300">
          {/* Cover */}
          <div className="aspect-[21/9] relative overflow-hidden">
            <img src={info.cover} alt={info.title} className="w-full h-full object-cover" />
            <div className="absolute inset-0 bg-gradient-to-t from-[#08070d] via-[#08070d]/40 to-transparent" />
            <div className={`absolute inset-0 bg-gradient-to-br ${info.accent} opacity-20 mix-blend-overlay`} />
          </div>

          {/* Body */}
          <div className="p-6 sm:p-10">
            <h3 className="text-2xl font-black mb-4 text-amber-300">المميزات</h3>
            <ul className="space-y-2.5 mb-8">
              {info.bullets.map((b, i) => (
                <li key={i} className="flex items-start gap-3 text-sm sm:text-base leading-relaxed">
                  <span className="text-amber-300 flex-shrink-0 mt-0.5">✦</span>
                  <span className="text-white/85">{b}</span>
                </li>
              ))}
            </ul>
            <button
              onClick={handleOpen}
              disabled={busy}
              className="w-full sm:w-auto py-4 px-8 rounded-xl bg-amber-400 text-black font-black text-base hover:bg-amber-300 disabled:bg-amber-400/40 disabled:cursor-wait transition-all inline-flex items-center justify-center gap-2"
              data-testid={`open-${mode}-btn`}
            >
              {busy ? (
                <><Loader2 className="w-5 h-5 animate-spin" /> جاري الفتح...</>
              ) : (
                <><Sparkles className="w-4 h-4" /> {info.cta} <ArrowRight className="w-4 h-4 rotate-180" /></>
              )}
            </button>
          </div>
        </div>
      </main>
    </div>
  );
}
