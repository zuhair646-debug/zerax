/**
 * Image Studio — deep scenario-driven image generation.
 * Route: /studio/image
 *
 * Workflow:
 *   1. User fills the form (scenario + audience + mood + style + aspect + purpose)
 *   2. Cost preview appears (5 credits)
 *   3. Generate → image rendered in result pane
 *   4. User can either: keep & save, or click "Edit" to refine (3 credits, no regenerate)
 */
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Navbar } from '@/components/Navbar';
import { Coins, ArrowRight, Loader2, Sparkles, Pencil, Image as ImageIcon } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { toast } from 'sonner';

const API = process.env.REACT_APP_BACKEND_URL;

const ASPECTS = [
  { id: '1:1', label: 'مربع 1:1', desc: 'منشورات سوشيال' },
  { id: '9:16', label: 'عمودي 9:16', desc: 'Story / Reels' },
  { id: '16:9', label: 'أفقي 16:9', desc: 'بنر سينمائي' },
  { id: '4:5', label: 'بورتريه 4:5', desc: 'منتج / Instagram' },
];

const PURPOSES = [
  { id: 'ad',           label: '🎯 إعلان' },
  { id: 'story',        label: '📱 Story' },
  { id: 'banner',       label: '🖼️ بنر' },
  { id: 'product_shot', label: '🛍️ صورة منتج' },
  { id: 'social_post',  label: '✨ منشور سوشيال' },
];

const MOODS = [
  { id: 'dramatic',  label: 'درامي' },
  { id: 'calm',      label: 'هادئ' },
  { id: 'energetic', label: 'طاقي' },
  { id: 'luxurious', label: 'فاخر' },
  { id: 'playful',   label: 'مرح' },
  { id: 'minimal',   label: 'بسيط' },
];

const STYLES = [
  { id: 'realistic',   label: 'واقعي' },
  { id: 'cinematic',   label: 'سينمائي' },
  { id: 'cartoon',     label: 'كرتوني' },
  { id: 'minimal',     label: 'minimal' },
  { id: '3d_render',   label: '3D Render' },
  { id: 'illustration',label: 'illustration' },
];

export default function StudioImage({ user }) {
  const navigate = useNavigate();
  const [credits, setCredits] = useState(null);
  const [pricing, setPricing] = useState({ image: 5, edit: 3 });

  // Form state
  const [scenario, setScenario] = useState('');
  const [audience, setAudience] = useState('');
  const [mood, setMood] = useState('');
  const [style, setStyle] = useState('');
  const [aspectRatio, setAspectRatio] = useState('1:1');
  const [purpose, setPurpose] = useState('');
  const [extraDetails, setExtraDetails] = useState('');

  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState(null);
  const [editOpen, setEditOpen] = useState(false);
  const [editRequest, setEditRequest] = useState('');
  const [editBusy, setEditBusy] = useState(false);

  const tokenH = () => ({ Authorization: `Bearer ${localStorage.getItem('token')}` });

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
    if (scenario.trim().length < 10) {
      toast.error('السيناريو قصير جداً — اكتب وصفاً مفصّلاً (10 أحرف على الأقل)');
      return;
    }
    if (credits !== null && credits < pricing.image) {
      toast.error(`رصيد غير كافٍ (تحتاج ${pricing.image} نقاط، رصيدك ${credits})`);
      return;
    }
    setBusy(true);
    setResult(null);
    try {
      const r = await fetch(`${API}/api/studio/image/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...tokenH() },
        body: JSON.stringify({
          scenario: scenario.trim(),
          audience: audience.trim() || null,
          mood: mood || null,
          style: style || null,
          aspect_ratio: aspectRatio,
          purpose: purpose || null,
          extra_details: extraDetails.trim() || null,
        }),
      });
      const d = await r.json();
      if (!r.ok) {
        throw new Error(d.detail || 'فشل التوليد');
      }
      setResult(d.asset);
      setCredits(d.credits_remaining);
      toast.success(`✨ تم! خُصم ${d.credits_spent} نقاط`);
    } catch (e) {
      toast.error(e.message || 'فشل غير متوقع');
      refreshCredits();
    } finally {
      setBusy(false);
    }
  };

  const handleEdit = async () => {
    if (editRequest.trim().length < 5) {
      toast.error('اكتب وصفاً للتعديل المطلوب');
      return;
    }
    if (credits !== null && credits < pricing.edit) {
      toast.error(`رصيد غير كافٍ للتعديل (تحتاج ${pricing.edit} نقاط)`);
      return;
    }
    setEditBusy(true);
    try {
      const r = await fetch(`${API}/api/studio/image/edit/${result.id}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...tokenH() },
        body: JSON.stringify({ edit_request: editRequest.trim() }),
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || 'فشل التعديل');
      setResult(d.asset);
      setCredits(d.credits_remaining);
      setEditOpen(false);
      setEditRequest('');
      toast.success(`🖌️ تم التعديل! خُصم ${d.credits_spent} نقاط`);
    } catch (e) {
      toast.error(e.message || 'فشل التعديل');
      refreshCredits();
    } finally {
      setEditBusy(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#0a0a12]" data-testid="studio-image-page">
      <Navbar user={user} transparent />
      <div className="pt-20 max-w-6xl mx-auto px-4 pb-16">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <button onClick={() => navigate('/studio')} className="text-amber-300/70 hover:text-amber-300 text-sm flex items-center gap-1" data-testid="studio-image-back">
            <ArrowRight className="w-4 h-4 rotate-180" /> رجوع للاستوديو
          </button>
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-amber-500/10 border border-amber-400/30 text-amber-300 text-sm font-bold" data-testid="studio-image-credits">
            <Coins className="w-4 h-4" />
            <span>{credits ?? '...'}</span>
            <span className="text-xs text-amber-200/60">نقطة</span>
          </div>
        </div>

        <h1 className="text-3xl font-black text-white mb-1">إنشاء صورة</h1>
        <p className="text-purple-300/70 text-sm mb-8">سيناريو دقيق ← صورة احترافية بنقرة واحدة ({pricing.image} نقاط)</p>

        <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
          {/* Form */}
          <div className="lg:col-span-3 space-y-4">
            <div>
              <label className="text-sm font-bold text-amber-200 mb-2 block">📝 السيناريو الكامل *</label>
              <textarea
                value={scenario}
                onChange={(e) => setScenario(e.target.value)}
                placeholder="مثال: صورة إعلانية لمنتج عسل سدر جبلي، يظهر عند شروق الشمس فوق طاولة خشبية رستيك مع ورقات نعناع طازجة، ضوء طبيعي ذهبي، خلفية مزرعة عسل ضبابية..."
                className="w-full min-h-[140px] p-3 bg-black/40 border border-purple-500/20 focus:border-purple-400 rounded-xl text-sm text-white outline-none resize-y"
                data-testid="studio-image-scenario"
                dir="rtl"
              />
              <div className="text-[10px] text-amber-200/50 mt-1">{scenario.length} حرف · الأفضل أن تكون 50 حرف على الأقل</div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label className="text-xs font-bold text-amber-200/80 mb-1.5 block">🎯 الجمهور المستهدف</label>
                <input value={audience} onChange={(e) => setAudience(e.target.value)} placeholder="نساء 25-40، عشاق الطبخ المنزلي" className="w-full p-2.5 bg-black/40 border border-white/10 focus:border-purple-400 rounded-lg text-sm outline-none" data-testid="studio-image-audience" />
              </div>
              <div>
                <label className="text-xs font-bold text-amber-200/80 mb-1.5 block">📋 الغرض</label>
                <select value={purpose} onChange={(e) => setPurpose(e.target.value)} className="w-full p-2.5 bg-black/40 border border-white/10 focus:border-purple-400 rounded-lg text-sm outline-none" data-testid="studio-image-purpose">
                  <option value="">-- اختر --</option>
                  {PURPOSES.map(p => <option key={p.id} value={p.id}>{p.label}</option>)}
                </select>
              </div>
            </div>

            <div>
              <label className="text-xs font-bold text-amber-200/80 mb-1.5 block">🎨 المزاج</label>
              <div className="flex flex-wrap gap-2">
                {MOODS.map(m => (
                  <button key={m.id} onClick={() => setMood(mood === m.id ? '' : m.id)} className={`px-3 py-1.5 text-xs rounded-lg border transition ${mood === m.id ? 'bg-purple-500/30 border-purple-400 text-white' : 'bg-black/30 border-white/10 text-white/70 hover:border-white/30'}`} data-testid={`studio-mood-${m.id}`}>{m.label}</button>
                ))}
              </div>
            </div>

            <div>
              <label className="text-xs font-bold text-amber-200/80 mb-1.5 block">✨ الأسلوب البصري</label>
              <div className="flex flex-wrap gap-2">
                {STYLES.map(s => (
                  <button key={s.id} onClick={() => setStyle(style === s.id ? '' : s.id)} className={`px-3 py-1.5 text-xs rounded-lg border transition ${style === s.id ? 'bg-amber-500/30 border-amber-400 text-white' : 'bg-black/30 border-white/10 text-white/70 hover:border-white/30'}`} data-testid={`studio-style-${s.id}`}>{s.label}</button>
                ))}
              </div>
            </div>

            <div>
              <label className="text-xs font-bold text-amber-200/80 mb-1.5 block">📐 المقاس</label>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                {ASPECTS.map(a => (
                  <button key={a.id} onClick={() => setAspectRatio(a.id)} className={`p-2.5 text-center rounded-lg border transition ${aspectRatio === a.id ? 'bg-purple-500/20 border-purple-400' : 'bg-black/30 border-white/10 hover:border-white/30'}`} data-testid={`studio-aspect-${a.id}`}>
                    <div className="text-xs font-bold text-white">{a.label}</div>
                    <div className="text-[9px] text-white/60">{a.desc}</div>
                  </button>
                ))}
              </div>
            </div>

            <div>
              <label className="text-xs font-bold text-amber-200/80 mb-1.5 block">💡 تفاصيل إضافية (اختياري)</label>
              <textarea value={extraDetails} onChange={(e) => setExtraDetails(e.target.value)} placeholder="ألوان معينة، عناصر يجب تجنبها، إلخ..." className="w-full min-h-[60px] p-2.5 bg-black/40 border border-white/10 focus:border-purple-400 rounded-lg text-sm outline-none" data-testid="studio-image-extra" dir="rtl" />
            </div>

            <Button
              onClick={handleGenerate}
              disabled={busy || scenario.trim().length < 10}
              className="w-full h-12 bg-gradient-to-r from-purple-500 to-violet-600 hover:from-purple-600 hover:to-violet-700 text-white font-black shadow-lg shadow-purple-500/30 disabled:opacity-50"
              data-testid="studio-image-generate"
            >
              {busy ? <Loader2 className="w-5 h-5 me-2 animate-spin" /> : <Sparkles className="w-5 h-5 me-2" />}
              {busy ? 'جارٍ الإنشاء... (~30 ثانية)' : `✨ إنشاء (${pricing.image} نقاط)`}
            </Button>
          </div>

          {/* Result pane */}
          <div className="lg:col-span-2">
            <div className="rounded-2xl border border-white/10 bg-black/40 p-4 sticky top-20" data-testid="studio-image-result-pane">
              <div className="flex items-center gap-2 mb-3 text-sm font-bold text-amber-200">
                <ImageIcon className="w-4 h-4" />
                النتيجة
              </div>
              {!result && !busy && (
                <div className="aspect-square rounded-xl border-2 border-dashed border-white/10 flex flex-col items-center justify-center text-white/40 text-center p-6 text-xs">
                  املأ السيناريو ← اضغط إنشاء
                  <br/>
                  ستظهر الصورة هنا
                </div>
              )}
              {busy && (
                <div className="aspect-square rounded-xl bg-gradient-to-br from-purple-500/10 to-violet-500/5 flex flex-col items-center justify-center text-white/70 gap-3">
                  <Loader2 className="w-8 h-8 animate-spin text-purple-400" />
                  <div className="text-xs">يرسم الذكاء الاصطناعي صورتك...</div>
                </div>
              )}
              {result && (
                <div data-testid="studio-image-result">
                  <img src={result.media_url} alt="generated" className="w-full rounded-xl mb-3" />
                  <div className="flex gap-2">
                    <Button onClick={() => setEditOpen(true)} variant="outline" className="flex-1 border-amber-400/30 text-amber-300 hover:bg-amber-400/10" data-testid="studio-image-edit-btn">
                      <Pencil className="w-4 h-4 me-1.5" /> تعديل ({pricing.edit} نقاط)
                    </Button>
                    <a href={result.media_url} download={`zitex-${result.id}.png`} className="flex-1">
                      <Button variant="outline" className="w-full border-emerald-400/30 text-emerald-300 hover:bg-emerald-400/10" data-testid="studio-image-download">
                        تحميل
                      </Button>
                    </a>
                  </div>
                  {editOpen && (
                    <div className="mt-3 p-3 rounded-xl bg-amber-500/10 border border-amber-400/30 space-y-2" data-testid="studio-image-edit-panel">
                      <div className="text-xs font-bold text-amber-200">🖌️ ما الذي تريد تغييره؟</div>
                      <textarea
                        value={editRequest}
                        onChange={(e) => setEditRequest(e.target.value)}
                        placeholder="مثال: اجعل الخلفية زرقاء، احذف القلم من الجانب، أضف منتج العسل في الوسط..."
                        className="w-full min-h-[70px] p-2 bg-black/40 border border-white/10 rounded-lg text-xs outline-none"
                        data-testid="studio-image-edit-input"
                        dir="rtl"
                      />
                      <div className="flex gap-2">
                        <Button onClick={handleEdit} disabled={editBusy} className="flex-1 bg-gradient-to-r from-amber-500 to-yellow-500 text-black font-black h-9 text-xs disabled:opacity-50" data-testid="studio-image-edit-submit">
                          {editBusy ? <Loader2 className="w-3 h-3 me-1 animate-spin" /> : '✨'}
                          {editBusy ? 'جارٍ...' : 'طبّق التعديل'}
                        </Button>
                        <Button onClick={() => { setEditOpen(false); setEditRequest(''); }} variant="outline" className="h-9 text-xs">إلغاء</Button>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
