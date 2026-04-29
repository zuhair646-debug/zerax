/**
 * Video Studio — deep video generation with separate scenario + voiceover.
 * Route: /studio/video
 *
 * Two key fields side-by-side:
 *   - السيناريو البصري (what happens visually, scene by scene)
 *   - النص الصوتي (voiceover script — what is being said)
 *
 * Cost calculator updates LIVE as user changes duration.
 * Sora 2 supports 4/8/12 second durations — UI snaps to nearest valid value.
 */
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Navbar } from '@/components/Navbar';
import { Coins, ArrowRight, Loader2, Video as VideoIcon, Clapperboard, Mic } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { toast } from 'sonner';

const API = process.env.REACT_APP_BACKEND_URL;

const DURATIONS = [
  { sec: 4,  label: '4 ثواني',  desc: 'قصير سريع' },
  { sec: 8,  label: '8 ثواني',  desc: 'إعلان قصير' },
  { sec: 12, label: '12 ثانية', desc: 'إعلان مكتمل' },
];

const ASPECTS = [
  { id: '16:9', label: 'أفقي 16:9', desc: 'YouTube / TV' },
  { id: '9:16', label: 'عمودي 9:16', desc: 'Reels / Story' },
  { id: '1:1',  label: 'مربع 1:1',  desc: 'Instagram' },
];

const STYLES = [
  { id: 'cinematic',   label: 'سينمائي' },
  { id: 'documentary', label: 'وثائقي' },
  { id: 'social',      label: 'سوشيال' },
  { id: 'commercial',  label: 'تجاري' },
  { id: 'animated',    label: 'animated' },
];

const MUSIC = [
  { id: 'epic',     label: 'epic' },
  { id: 'calm',     label: 'هادئ' },
  { id: 'upbeat',   label: 'مرح' },
  { id: 'corporate',label: 'corporate' },
  { id: 'none',     label: 'بدون موسيقى' },
];

export default function StudioVideo({ user }) {
  const navigate = useNavigate();
  const [credits, setCredits] = useState(null);
  const [pricing, setPricing] = useState({ video_per_second: 4 });

  const [title, setTitle] = useState('');
  const [scenario, setScenario] = useState('');
  const [voiceoverScript, setVoiceoverScript] = useState('');
  const [duration, setDuration] = useState(8);
  const [aspectRatio, setAspectRatio] = useState('16:9');
  const [style, setStyle] = useState('');
  const [musicMood, setMusicMood] = useState('');

  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState(null);

  const tokenH = () => ({ Authorization: `Bearer ${localStorage.getItem('token')}` });
  const cost = duration * pricing.video_per_second;
  const canAfford = credits !== null && credits >= cost;

  useEffect(() => {
    if (!localStorage.getItem('token')) { navigate('/login'); return; }
    refreshCredits();
  }, [navigate]);

  const refreshCredits = () => {
    fetch(`${API}/api/studio/credits`, { headers: tokenH() })
      .then(r => r.ok ? r.json() : null)
      .then(d => { if (d) { setCredits(d.credits); setPricing(d.pricing); } });
  };

  const handleGenerate = async () => {
    if (!title.trim()) { toast.error('عنوان الفيديو مطلوب'); return; }
    if (scenario.trim().length < 10) { toast.error('السيناريو قصير جداً (10 أحرف على الأقل)'); return; }
    if (!canAfford) { toast.error(`رصيد غير كافٍ (تحتاج ${cost} نقاط، رصيدك ${credits})`); return; }

    setBusy(true);
    setResult(null);
    try {
      const r = await fetch(`${API}/api/studio/video/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...tokenH() },
        body: JSON.stringify({
          title: title.trim(),
          scenario: scenario.trim(),
          voiceover_script: voiceoverScript.trim() || null,
          duration_seconds: duration,
          aspect_ratio: aspectRatio,
          style: style || null,
          music_mood: musicMood || null,
        }),
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || 'فشل التوليد');
      setResult(d.asset);
      setCredits(d.credits_remaining);
      toast.success(`🎬 تم! خُصم ${d.credits_spent} نقاط`);
    } catch (e) {
      toast.error(e.message || 'فشل غير متوقع');
      refreshCredits();
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#0a0a12]" data-testid="studio-video-page">
      <Navbar user={user} transparent />
      <div className="pt-20 max-w-6xl mx-auto px-4 pb-16">
        <div className="flex items-center justify-between mb-6">
          <button onClick={() => navigate('/studio')} className="text-amber-300/70 hover:text-amber-300 text-sm flex items-center gap-1" data-testid="studio-video-back">
            <ArrowRight className="w-4 h-4 rotate-180" /> رجوع للاستوديو
          </button>
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-amber-500/10 border border-amber-400/30 text-amber-300 text-sm font-bold" data-testid="studio-video-credits">
            <Coins className="w-4 h-4" />
            <span>{credits ?? '...'}</span>
            <span className="text-xs text-amber-200/60">نقطة</span>
          </div>
        </div>

        <h1 className="text-3xl font-black text-white mb-1">إنشاء فيديو</h1>
        <p className="text-orange-300/70 text-sm mb-6">سيناريو منفصل عن النص الصوتي — تكلفة محسوبة بدقة قبل الإنشاء</p>

        {/* Live cost banner */}
        <div className="mb-6 p-4 rounded-2xl bg-gradient-to-r from-orange-500/15 to-red-500/10 border border-orange-400/30 flex items-center justify-between" data-testid="studio-video-cost-banner">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-orange-400 to-red-500 flex items-center justify-center">
              <Clapperboard className="w-6 h-6 text-white" />
            </div>
            <div>
              <div className="text-xs text-amber-200/60">التكلفة لـ {duration} ثواني</div>
              <div className="text-2xl font-black text-amber-300">{cost} نقطة</div>
            </div>
          </div>
          <div className={`px-3 py-1.5 rounded-lg text-xs font-bold ${canAfford ? 'bg-emerald-500/20 text-emerald-300' : 'bg-red-500/20 text-red-300'}`}>
            {canAfford ? '✓ رصيدك كافٍ' : `يلزم ${cost - (credits || 0)} نقاط إضافية`}
          </div>
        </div>

        <div className="space-y-4">
          <div>
            <label className="text-xs font-bold text-amber-200/80 mb-1.5 block">🎬 عنوان الفيديو *</label>
            <input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="إعلان عسل سدر — رمضان 2026" className="w-full p-2.5 bg-black/40 border border-white/10 focus:border-orange-400 rounded-lg text-sm outline-none" data-testid="studio-video-title" />
          </div>

          {/* Two columns: scenario + voiceover */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
            <div>
              <label className="text-sm font-bold text-amber-200 mb-2 flex items-center gap-2">
                <Clapperboard className="w-4 h-4" />
                السيناريو البصري *
              </label>
              <textarea
                value={scenario}
                onChange={(e) => setScenario(e.target.value)}
                placeholder="ما يحدث في الفيديو بصرياً، خطوة بخطوة:&#10;&#10;1. مشهد افتتاحي: شروق شمس فوق جبل&#10;2. زوم على نحلة تطير&#10;3. كلوز أب على عسل ينسكب من ملعقة..."
                className="w-full min-h-[180px] p-3 bg-black/40 border border-orange-500/20 focus:border-orange-400 rounded-xl text-sm text-white outline-none resize-y"
                data-testid="studio-video-scenario"
                dir="rtl"
              />
              <div className="text-[10px] text-amber-200/50 mt-1">{scenario.length} حرف · يصف ما يُرى في الفيديو</div>
            </div>

            <div>
              <label className="text-sm font-bold text-amber-200 mb-2 flex items-center gap-2">
                <Mic className="w-4 h-4" />
                النص الصوتي (اختياري)
              </label>
              <textarea
                value={voiceoverScript}
                onChange={(e) => setVoiceoverScript(e.target.value)}
                placeholder="ما يُقال بصوت عالٍ في الفيديو:&#10;&#10;'عسل السدر الجبلي — صفاء يعود بك للأصل... قطرة تكفي.'&#10;&#10;اتركه فارغاً إذا لا تريد تعليقاً صوتياً."
                className="w-full min-h-[180px] p-3 bg-black/40 border border-orange-500/20 focus:border-orange-400 rounded-xl text-sm text-white outline-none resize-y"
                data-testid="studio-video-voiceover"
                dir="rtl"
              />
              <div className="text-[10px] text-amber-200/50 mt-1">{voiceoverScript.length} حرف · ما يُسمع في الفيديو</div>
            </div>
          </div>

          {/* Duration */}
          <div>
            <label className="text-xs font-bold text-amber-200/80 mb-1.5 block">⏱️ المدة (Sora 2: 4 / 8 / 12 ثانية فقط)</label>
            <div className="grid grid-cols-3 gap-2">
              {DURATIONS.map(d => (
                <button key={d.sec} onClick={() => setDuration(d.sec)} className={`p-3 text-center rounded-lg border transition ${duration === d.sec ? 'bg-orange-500/20 border-orange-400' : 'bg-black/30 border-white/10 hover:border-white/30'}`} data-testid={`studio-duration-${d.sec}`}>
                  <div className="text-sm font-bold text-white">{d.label}</div>
                  <div className="text-[10px] text-white/60">{d.desc}</div>
                  <div className="text-[10px] text-amber-300 font-bold mt-1">{d.sec * pricing.video_per_second} نقطة</div>
                </button>
              ))}
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div>
              <label className="text-xs font-bold text-amber-200/80 mb-1.5 block">📐 المقاس</label>
              <select value={aspectRatio} onChange={(e) => setAspectRatio(e.target.value)} className="w-full p-2.5 bg-black/40 border border-white/10 rounded-lg text-sm outline-none" data-testid="studio-video-aspect">
                {ASPECTS.map(a => <option key={a.id} value={a.id}>{a.label} — {a.desc}</option>)}
              </select>
            </div>
            <div>
              <label className="text-xs font-bold text-amber-200/80 mb-1.5 block">🎨 الأسلوب</label>
              <select value={style} onChange={(e) => setStyle(e.target.value)} className="w-full p-2.5 bg-black/40 border border-white/10 rounded-lg text-sm outline-none" data-testid="studio-video-style">
                <option value="">-- اختر --</option>
                {STYLES.map(s => <option key={s.id} value={s.id}>{s.label}</option>)}
              </select>
            </div>
            <div>
              <label className="text-xs font-bold text-amber-200/80 mb-1.5 block">🎵 الموسيقى</label>
              <select value={musicMood} onChange={(e) => setMusicMood(e.target.value)} className="w-full p-2.5 bg-black/40 border border-white/10 rounded-lg text-sm outline-none" data-testid="studio-video-music">
                <option value="">-- اختر --</option>
                {MUSIC.map(m => <option key={m.id} value={m.id}>{m.label}</option>)}
              </select>
            </div>
          </div>

          <Button
            onClick={handleGenerate}
            disabled={busy || !canAfford || scenario.trim().length < 10 || !title.trim()}
            className="w-full h-12 bg-gradient-to-r from-orange-500 to-red-600 hover:from-orange-600 hover:to-red-700 text-white font-black shadow-lg shadow-orange-500/30 disabled:opacity-50"
            data-testid="studio-video-generate"
          >
            {busy ? <Loader2 className="w-5 h-5 me-2 animate-spin" /> : <VideoIcon className="w-5 h-5 me-2" />}
            {busy ? 'جارٍ الإنشاء... (~3-5 دقائق)' : `🎬 إنشاء الفيديو (${cost} نقاط)`}
          </Button>

          {result && (
            <div className="mt-4 p-4 rounded-2xl border border-emerald-400/30 bg-emerald-500/5" data-testid="studio-video-result">
              <div className="text-sm font-bold text-emerald-300 mb-2">✓ {result.title}</div>
              <video src={result.media_url} controls className="w-full rounded-xl mb-3" />
              <div className="flex gap-2">
                <a href={result.media_url} download={`zitex-${result.id}.mp4`} className="flex-1">
                  <Button variant="outline" className="w-full border-emerald-400/30 text-emerald-300" data-testid="studio-video-download">
                    تحميل
                  </Button>
                </a>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
