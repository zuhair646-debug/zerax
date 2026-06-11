import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Toaster, toast } from 'sonner';
import {
  ArrowLeft, Sparkles, Zap, Image as ImageIcon, Video, Edit3, Mic,
  Cpu, CheckCircle2, XCircle, Loader2, TrendingUp, Award, DollarSign,
  Lock, KeyRound, Wand2, Crown,
} from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;
const SESSION_KEY = 'zenrex_autocoder_session';

const TIER_BADGE = {
  premium: { label: 'Premium', cls: 'bg-amber-500/15 text-amber-400 border-amber-500/30', icon: Crown },
  strong:  { label: 'Strong',  cls: 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30', icon: Award },
};

const SECTION_META = {
  image: { label: 'الصور', icon: ImageIcon, color: 'text-fuchsia-400', testid: 'section-image' },
  video: { label: 'الفيديو', icon: Video, color: 'text-rose-400', testid: 'section-video' },
  image_edit: { label: 'تعديل الصور', icon: Edit3, color: 'text-emerald-400', testid: 'section-edit' },
  voice: { label: 'الصوت', icon: Mic, color: 'text-sky-400', testid: 'section-voice' },
};

const SAMPLE_PROMPTS = {
  image: [
    'شعار عطر فاخر بنص عربي ذهبي',
    'بورتري واقعي 8k لفنان عربي',
    '100 صورة منتج للمتجر الإلكتروني',
    'بوستر إعلان لتيك توك',
  ],
  video: [
    'فيديو سينمائي إعلاني لمنتج عطور فاخر',
    'فيديو سريع للسوشال ميديا تيك توك',
    'قصة سينمائية بحركة كاميرا ناعمة',
  ],
  image_edit: [
    'غيّر لون الورد إلى أحمر فقط بدون لمس الباقي',
    'احذف الشخص من الخلفية',
    'نفس الشخصية في مشهد جديد (consistent)',
  ],
  voice: [
    'اقرأ لي هذا النص باللهجة السعودية',
    'صوت طبيعي بالفصحى للقصة',
  ],
};

export default function AdminQualityRouter() {
  const nav = useNavigate();
  const [token, setToken] = useState(() => sessionStorage.getItem(SESSION_KEY) || '');
  const [pin, setPin] = useState('');
  const [unlocking, setUnlocking] = useState(false);
  const [catalog, setCatalog] = useState(null);
  const [loading, setLoading] = useState(false);
  const [activeSection, setActiveSection] = useState('image');
  const [testPrompt, setTestPrompt] = useState('');
  const [testResult, setTestResult] = useState(null);
  const [testing, setTesting] = useState(false);
  const [priority, setPriority] = useState('quality');
  const [videoDuration, setVideoDuration] = useState(8);

  useEffect(() => {
    if (token) loadCatalog();
  }, [token]); // eslint-disable-line

  const unlock = async () => {
    if (!pin.trim()) return toast.error('أدخل رمز PIN');
    setUnlocking(true);
    try {
      const res = await fetch(`${API}/api/autocoder/unlock`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ pin: pin.trim() }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data?.detail || 'فشل التحقق');
      sessionStorage.setItem(SESSION_KEY, data.token);
      setToken(data.token);
      setPin('');
      toast.success('تم فتح القسم');
    } catch (e) {
      toast.error(e.message || 'فشل');
    } finally {
      setUnlocking(false);
    }
  };

  const loadCatalog = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API}/api/autocoder/media/catalog`, {
        headers: { 'X-Autocoder-Token': token },
      });
      if (res.status === 401) {
        sessionStorage.removeItem(SESSION_KEY);
        setToken('');
        return;
      }
      const data = await res.json();
      setCatalog(data);
    } catch (e) {
      toast.error('فشل تحميل الكاتلوج');
    } finally {
      setLoading(false);
    }
  };

  const runTest = async () => {
    const prompt = testPrompt.trim();
    if (!prompt) return toast.error('اكتب وصف للاختبار');
    setTesting(true);
    setTestResult(null);
    try {
      let endpoint, body;
      if (activeSection === 'image') {
        endpoint = '/api/autocoder/media/pick/image';
        body = { prompt, priority };
      } else if (activeSection === 'video') {
        endpoint = '/api/autocoder/media/pick/video';
        body = { prompt, duration: videoDuration, priority };
      } else if (activeSection === 'image_edit') {
        endpoint = '/api/autocoder/media/pick/edit';
        body = { prompt };
      } else if (activeSection === 'voice') {
        endpoint = '/api/autocoder/media/pick/voice';
        body = { text: prompt };
      }
      const res = await fetch(`${API}${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-Autocoder-Token': token },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      setTestResult(data);
    } catch (e) {
      toast.error('فشل الاختبار');
    } finally {
      setTesting(false);
    }
  };

  // ── Lock screen ──────────────────────────────────────────────────────
  if (!token) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-zinc-950 to-black text-zinc-200 flex items-center justify-center px-4">
        <Toaster richColors position="top-center" />
        <div className="w-full max-w-md bg-zinc-900/60 border border-zinc-800 rounded-2xl p-8 backdrop-blur-xl">
          <div className="flex items-center gap-3 mb-6">
            <Lock className="w-6 h-6 text-amber-400" />
            <h1 className="text-2xl font-bold">موجّه الجودة</h1>
          </div>
          <p className="text-sm text-zinc-400 mb-6">
            مركز إدارة الموديلات الذكية في زيتاكس. أدخل رمز PIN للمالك.
          </p>
          <div className="flex gap-2">
            <input
              type="password"
              value={pin}
              onChange={(e) => setPin(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && unlock()}
              placeholder="رمز PIN"
              className="flex-1 px-4 py-3 bg-zinc-800/60 border border-zinc-700 rounded-xl outline-none focus:border-amber-500 text-base"
              data-testid="quality-router-pin-input"
            />
            <button
              onClick={unlock}
              disabled={unlocking}
              className="px-5 py-3 bg-amber-500 hover:bg-amber-400 text-black font-semibold rounded-xl disabled:opacity-50 flex items-center gap-2"
              data-testid="quality-router-unlock-btn"
            >
              {unlocking ? <Loader2 className="w-4 h-4 animate-spin" /> : <KeyRound className="w-4 h-4" />}
              فتح
            </button>
          </div>
          <button
            onClick={() => nav('/admin/autocoder')}
            className="mt-6 text-sm text-zinc-500 hover:text-zinc-300 flex items-center gap-2"
          >
            <ArrowLeft className="w-4 h-4" /> العودة لمركز التحكم
          </button>
        </div>
      </div>
    );
  }

  // ── Main dashboard ───────────────────────────────────────────────────
  const sectionData = catalog?.[activeSection] || [];
  const availableCount = sectionData.filter((m) => m.available).length;

  return (
    <div className="min-h-screen bg-gradient-to-b from-zinc-950 to-black text-zinc-100">
      <Toaster richColors position="top-center" />

      {/* Header */}
      <div className="border-b border-zinc-800/60 sticky top-0 z-30 bg-zinc-950/80 backdrop-blur-xl">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center gap-4">
          <button
            onClick={() => nav('/admin/autocoder')}
            className="p-2 hover:bg-zinc-800 rounded-lg text-zinc-400 hover:text-zinc-200"
          >
            <ArrowLeft className="w-5 h-5" />
          </button>
          <div className="flex-1">
            <div className="flex items-center gap-2">
              <Sparkles className="w-5 h-5 text-amber-400" />
              <h1 className="text-xl font-bold">موجّه الجودة</h1>
              <span className="text-xs px-2 py-0.5 bg-amber-500/10 text-amber-400 border border-amber-500/30 rounded-full">
                Quality-First v2
              </span>
            </div>
            <p className="text-xs text-zinc-500 mt-0.5">{catalog?.philosophy || ''}</p>
          </div>
          <button
            onClick={loadCatalog}
            disabled={loading}
            className="px-3 py-1.5 text-sm bg-zinc-800 hover:bg-zinc-700 rounded-lg flex items-center gap-2"
            data-testid="refresh-catalog-btn"
          >
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <TrendingUp className="w-4 h-4" />}
            تحديث
          </button>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-6 py-6">
        {/* Section tabs */}
        <div className="flex gap-2 mb-6 overflow-x-auto pb-2">
          {Object.entries(SECTION_META).map(([key, meta]) => {
            const Icon = meta.icon;
            const active = activeSection === key;
            const count = (catalog?.[key] || []).filter((m) => m.available).length;
            const total = (catalog?.[key] || []).length;
            return (
              <button
                key={key}
                onClick={() => { setActiveSection(key); setTestResult(null); setTestPrompt(''); }}
                data-testid={meta.testid}
                className={`px-4 py-2.5 rounded-xl border whitespace-nowrap flex items-center gap-2 transition ${
                  active
                    ? 'bg-zinc-100 text-zinc-900 border-zinc-100'
                    : 'bg-zinc-900/60 border-zinc-800 hover:border-zinc-700'
                }`}
              >
                <Icon className={`w-4 h-4 ${active ? '' : meta.color}`} />
                <span className="font-medium">{meta.label}</span>
                <span className={`text-xs px-1.5 rounded ${active ? 'bg-zinc-800 text-zinc-300' : 'bg-zinc-800 text-zinc-500'}`}>
                  {count}/{total}
                </span>
              </button>
            );
          })}
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* LEFT: Model list */}
          <div className="lg:col-span-2 space-y-3">
            <div className="flex items-center justify-between mb-2">
              <h2 className="text-sm font-semibold text-zinc-400 uppercase tracking-wide">
                النخبة المُعتمدة — {SECTION_META[activeSection].label}
              </h2>
              <span className="text-xs text-zinc-500">{availableCount} متاح</span>
            </div>

            {loading && !catalog ? (
              <div className="py-12 flex justify-center"><Loader2 className="w-6 h-6 animate-spin text-zinc-500" /></div>
            ) : (
              sectionData.map((m) => {
                const tierMeta = TIER_BADGE[m.tier] || TIER_BADGE.strong;
                const TierIcon = tierMeta.icon;
                return (
                  <div
                    key={m.key}
                    className={`rounded-xl border p-4 transition ${
                      m.available
                        ? 'bg-zinc-900/60 border-zinc-800 hover:border-zinc-700'
                        : 'bg-zinc-900/30 border-zinc-900 opacity-60'
                    }`}
                    data-testid={`model-card-${m.key}`}
                  >
                    <div className="flex items-start gap-3">
                      <div className={`mt-0.5 p-2 rounded-lg ${m.available ? 'bg-emerald-500/10' : 'bg-zinc-800'}`}>
                        {m.available
                          ? <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                          : <XCircle className="w-4 h-4 text-zinc-600" />
                        }
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 flex-wrap">
                          <h3 className="font-semibold">{m.label}</h3>
                          <span className={`text-[10px] px-1.5 py-0.5 rounded border flex items-center gap-1 ${tierMeta.cls}`}>
                            <TierIcon className="w-3 h-3" />
                            {tierMeta.label}
                          </span>
                          <span className="text-[10px] px-1.5 py-0.5 rounded bg-zinc-800 text-zinc-400">
                            جودة {m.quality}/10
                          </span>
                          {!m.available && (
                            <span className="text-[10px] px-1.5 py-0.5 rounded bg-rose-500/10 text-rose-400 border border-rose-500/30">
                              مفتاح ناقص
                            </span>
                          )}
                        </div>
                        <p className="text-xs text-zinc-500 mt-1">المزود: {m.provider}</p>
                        <div className="flex flex-wrap gap-1 mt-2">
                          {(m.specialties || []).slice(0, 5).map((s) => (
                            <span key={s} className="text-[10px] px-1.5 py-0.5 bg-zinc-800/80 rounded text-zinc-400">
                              {s}
                            </span>
                          ))}
                        </div>
                      </div>
                      <div className="text-right text-xs">
                        {m.price_usd !== undefined && (
                          <div className="flex items-center gap-1 text-amber-400">
                            <DollarSign className="w-3 h-3" />
                            <span>{m.price_usd}/صورة</span>
                          </div>
                        )}
                        {m.price_per_second !== undefined && (
                          <div className="flex items-center gap-1 text-rose-400">
                            <DollarSign className="w-3 h-3" />
                            <span>{m.price_per_second}/ث</span>
                          </div>
                        )}
                        {m.price_per_1k_chars !== undefined && (
                          <div className="flex items-center gap-1 text-sky-400">
                            <DollarSign className="w-3 h-3" />
                            <span>{m.price_per_1k_chars}/1k</span>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })
            )}
          </div>

          {/* RIGHT: Live test */}
          <div className="lg:col-span-1">
            <div className="sticky top-24 bg-zinc-900/60 border border-zinc-800 rounded-2xl p-5">
              <div className="flex items-center gap-2 mb-4">
                <Wand2 className="w-4 h-4 text-amber-400" />
                <h2 className="text-sm font-semibold">اختبر الموجّه الذكي</h2>
              </div>

              <p className="text-xs text-zinc-500 mb-3">
                اكتب أي طلب — الموجّه يختار لك أعلى جودة متاحة.
              </p>

              {/* Sample prompts */}
              <div className="space-y-1 mb-3">
                {(SAMPLE_PROMPTS[activeSection] || []).map((s, i) => (
                  <button
                    key={i}
                    onClick={() => setTestPrompt(s)}
                    className="w-full text-right text-xs px-3 py-2 bg-zinc-800/60 hover:bg-zinc-800 rounded-lg text-zinc-400 hover:text-zinc-200 transition"
                  >
                    {s}
                  </button>
                ))}
              </div>

              <textarea
                value={testPrompt}
                onChange={(e) => setTestPrompt(e.target.value)}
                placeholder="اكتب طلبك هنا..."
                className="w-full px-3 py-2 bg-zinc-800/60 border border-zinc-700 rounded-lg outline-none focus:border-amber-500 text-sm resize-none"
                rows={3}
                data-testid="quality-router-test-prompt"
              />

              {activeSection === 'video' && (
                <div className="mt-3">
                  <label className="text-xs text-zinc-500">المدة (ثواني)</label>
                  <input
                    type="number"
                    min={1}
                    max={20}
                    value={videoDuration}
                    onChange={(e) => setVideoDuration(parseInt(e.target.value || '8', 10))}
                    className="w-full mt-1 px-3 py-2 bg-zinc-800/60 border border-zinc-700 rounded-lg text-sm outline-none focus:border-amber-500"
                  />
                </div>
              )}

              {(activeSection === 'image' || activeSection === 'video') && (
                <div className="mt-3">
                  <label className="text-xs text-zinc-500">الأولوية</label>
                  <select
                    value={priority}
                    onChange={(e) => setPriority(e.target.value)}
                    className="w-full mt-1 px-3 py-2 bg-zinc-800/60 border border-zinc-700 rounded-lg text-sm outline-none focus:border-amber-500"
                    data-testid="quality-router-priority"
                  >
                    <option value="quality">الجودة دائماً (موصى)</option>
                    <option value="balanced">متوازن</option>
                    <option value="cost_aware">السعر أهم</option>
                  </select>
                </div>
              )}

              <button
                onClick={runTest}
                disabled={testing || !testPrompt.trim()}
                className="w-full mt-4 px-4 py-2.5 bg-amber-500 hover:bg-amber-400 text-black font-semibold rounded-lg disabled:opacity-50 flex items-center justify-center gap-2"
                data-testid="quality-router-run-test"
              >
                {testing ? <Loader2 className="w-4 h-4 animate-spin" /> : <Zap className="w-4 h-4" />}
                اختر الأفضل
              </button>

              {/* Result */}
              {testResult && (
                <div className="mt-4 p-3 bg-amber-500/5 border border-amber-500/30 rounded-lg" data-testid="quality-router-test-result">
                  {testResult.error ? (
                    <div className="text-xs text-rose-400">
                      <p className="font-semibold mb-1">⚠️ {testResult.error}</p>
                      <p>{testResult.message}</p>
                    </div>
                  ) : (
                    <>
                      <div className="flex items-center gap-2 mb-2">
                        <Crown className="w-4 h-4 text-amber-400" />
                        <span className="font-bold text-amber-300">{testResult.label}</span>
                      </div>
                      <p className="text-xs text-zinc-300 mb-2">{testResult.reason}</p>
                      <div className="flex flex-wrap gap-1 text-[10px]">
                        {testResult.tier && (
                          <span className="px-1.5 py-0.5 bg-amber-500/20 text-amber-300 rounded">
                            {testResult.tier}
                          </span>
                        )}
                        {testResult.quality && (
                          <span className="px-1.5 py-0.5 bg-zinc-800 text-zinc-400 rounded">
                            جودة {testResult.quality}/10
                          </span>
                        )}
                        {testResult.price_usd && (
                          <span className="px-1.5 py-0.5 bg-zinc-800 text-emerald-400 rounded">
                            ${testResult.price_usd}/صورة
                          </span>
                        )}
                        {testResult.cost_for_clip && (
                          <span className="px-1.5 py-0.5 bg-zinc-800 text-emerald-400 rounded">
                            ${testResult.cost_for_clip} للمقطع
                          </span>
                        )}
                      </div>
                      {(testResult.matched_specialties || []).length > 0 && (
                        <div className="mt-2 text-xs text-zinc-500">
                          <span className="text-zinc-400">طابق:</span> {testResult.matched_specialties.join(', ')}
                        </div>
                      )}
                      {(testResult.fallbacks || []).length > 0 && (
                        <div className="mt-2 text-[10px] text-zinc-500">
                          بدائل: {testResult.fallbacks.slice(0, 3).join(' • ')}
                        </div>
                      )}
                    </>
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
