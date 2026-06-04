import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Toaster, toast } from 'sonner';
import {
  ArrowLeft, Lock, KeyRound, Loader2, Globe, AppWindow, Image as ImageIcon,
  Video, Mic, Smartphone, Cpu, Gamepad2, MessageSquare, Sparkles,
  Crown, Shield, Shuffle, ChevronRight, CheckCircle2, AlertTriangle,
  Wand2,
} from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;
const SESSION_KEY = 'zitex_autocoder_session';

const ICON_MAP = {
  Globe, AppWindow, Image: ImageIcon, Video, Mic, Smartphone, Cpu,
  Gamepad2, MessageSquare,
};

const COLOR_MAP = {
  fuchsia:  { ring: 'ring-fuchsia-500/30', bg: 'bg-fuchsia-500/10', text: 'text-fuchsia-400', dot: 'bg-fuchsia-400' },
  indigo:   { ring: 'ring-indigo-500/30',  bg: 'bg-indigo-500/10',  text: 'text-indigo-400',  dot: 'bg-indigo-400' },
  amber:    { ring: 'ring-amber-500/30',   bg: 'bg-amber-500/10',   text: 'text-amber-400',   dot: 'bg-amber-400' },
  rose:     { ring: 'ring-rose-500/30',    bg: 'bg-rose-500/10',    text: 'text-rose-400',    dot: 'bg-rose-400' },
  sky:      { ring: 'ring-sky-500/30',     bg: 'bg-sky-500/10',     text: 'text-sky-400',     dot: 'bg-sky-400' },
  violet:   { ring: 'ring-violet-500/30',  bg: 'bg-violet-500/10',  text: 'text-violet-400',  dot: 'bg-violet-400' },
  emerald:  { ring: 'ring-emerald-500/30', bg: 'bg-emerald-500/10', text: 'text-emerald-400', dot: 'bg-emerald-400' },
  lime:     { ring: 'ring-lime-500/30',    bg: 'bg-lime-500/10',    text: 'text-lime-400',    dot: 'bg-lime-400' },
  zinc:     { ring: 'ring-zinc-500/30',    bg: 'bg-zinc-500/10',    text: 'text-zinc-400',    dot: 'bg-zinc-400' },
};

export default function AdminSections() {
  const nav = useNavigate();
  const [token, setToken] = useState(() => sessionStorage.getItem(SESSION_KEY) || '');
  const [pin, setPin] = useState('');
  const [unlocking, setUnlocking] = useState(false);
  const [sections, setSections] = useState([]);
  const [loading, setLoading] = useState(false);
  const [selected, setSelected] = useState(null);
  const [detail, setDetail] = useState(null);
  const [picking, setPicking] = useState(false);
  const [pickResult, setPickResult] = useState(null);

  useEffect(() => { if (token) loadSections(); }, [token]); // eslint-disable-line

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
      if (!res.ok) throw new Error(data?.detail || 'فشل');
      sessionStorage.setItem(SESSION_KEY, data.token);
      setToken(data.token);
      setPin('');
      toast.success('تم فتح القسم');
    } catch (e) { toast.error(e.message || 'فشل'); } finally { setUnlocking(false); }
  };

  const loadSections = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API}/api/autocoder/sections`, {
        headers: { 'X-Autocoder-Token': token },
      });
      if (res.status === 401) { sessionStorage.removeItem(SESSION_KEY); setToken(''); return; }
      const data = await res.json();
      setSections(data.sections || []);
    } catch (e) { toast.error('فشل التحميل'); } finally { setLoading(false); }
  };

  const openSection = async (s) => {
    setSelected(s);
    setPickResult(null);
    setDetail(null);
    try {
      const res = await fetch(`${API}/api/autocoder/sections/${s.id}`, {
        headers: { 'X-Autocoder-Token': token },
      });
      const data = await res.json();
      setDetail(data);
    } catch {}
  };

  const tryPick = async () => {
    if (!selected) return;
    setPicking(true);
    setPickResult(null);
    try {
      const res = await fetch(`${API}/api/autocoder/sections/${selected.id}/pick`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-Autocoder-Token': token },
        body: JSON.stringify({}),
      });
      const data = await res.json();
      setPickResult(data);
    } catch {} finally { setPicking(false); }
  };

  // Lock screen
  if (!token) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-zinc-950 to-black text-zinc-200 flex items-center justify-center px-4">
        <Toaster richColors position="top-center" />
        <div className="w-full max-w-md bg-zinc-900/60 border border-zinc-800 rounded-2xl p-8 backdrop-blur-xl">
          <div className="flex items-center gap-3 mb-6">
            <Lock className="w-6 h-6 text-amber-400" />
            <h1 className="text-2xl font-bold">مركز الأقسام</h1>
          </div>
          <p className="text-sm text-zinc-400 mb-6">
            كل قسم في زيتاكس له خبير AI خاص. أدخل رمز PIN.
          </p>
          <div className="flex gap-2">
            <input
              type="password"
              value={pin}
              onChange={(e) => setPin(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && unlock()}
              placeholder="رمز PIN"
              className="flex-1 px-4 py-3 bg-zinc-800/60 border border-zinc-700 rounded-xl outline-none focus:border-amber-500 text-base"
              data-testid="sections-pin-input"
            />
            <button onClick={unlock} disabled={unlocking}
              className="px-5 py-3 bg-amber-500 hover:bg-amber-400 text-black font-semibold rounded-xl disabled:opacity-50 flex items-center gap-2"
              data-testid="sections-unlock-btn">
              {unlocking ? <Loader2 className="w-4 h-4 animate-spin" /> : <KeyRound className="w-4 h-4" />}
              فتح
            </button>
          </div>
          <button onClick={() => nav('/admin/autocoder')}
            className="mt-6 text-sm text-zinc-500 hover:text-zinc-300 flex items-center gap-2">
            <ArrowLeft className="w-4 h-4" /> العودة لمركز التحكم
          </button>
        </div>
      </div>
    );
  }

  const availableCount = sections.filter((s) => s.available).length;
  const totalCount = sections.length;

  return (
    <div className="min-h-screen bg-gradient-to-b from-zinc-950 to-black text-zinc-100">
      <Toaster richColors position="top-center" />

      <div className="border-b border-zinc-800/60 sticky top-0 z-30 bg-zinc-950/80 backdrop-blur-xl">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center gap-4">
          <button onClick={() => nav('/admin/autocoder')}
            className="p-2 hover:bg-zinc-800 rounded-lg text-zinc-400 hover:text-zinc-200">
            <ArrowLeft className="w-5 h-5" />
          </button>
          <div className="flex-1">
            <div className="flex items-center gap-2">
              <Sparkles className="w-5 h-5 text-amber-400" />
              <h1 className="text-xl font-bold">مركز الأقسام الذكية</h1>
              <span className="text-xs px-2 py-0.5 bg-amber-500/10 text-amber-400 border border-amber-500/30 rounded-full">
                {availableCount}/{totalCount} جاهز
              </span>
            </div>
            <p className="text-xs text-zinc-500 mt-0.5">
              كل قسم له خبير AI مخصص — محدود في مجاله، مفتوح على أفضل الموديلات بشكل متنوع.
            </p>
          </div>
          <button onClick={loadSections} disabled={loading}
            className="px-3 py-1.5 text-sm bg-zinc-800 hover:bg-zinc-700 rounded-lg">
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : 'تحديث'}
          </button>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-6 py-6">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

          {/* LEFT: Sections grid */}
          <div className="lg:col-span-2 space-y-3">
            {sections.map((s) => {
              const Icon = ICON_MAP[s.icon] || Sparkles;
              const palette = COLOR_MAP[s.color] || COLOR_MAP.zinc;
              const active = selected?.id === s.id;
              return (
                <button key={s.id} onClick={() => openSection(s)}
                  data-testid={`section-${s.id}`}
                  className={`w-full text-right rounded-xl border p-4 transition group ${
                    active ? `${palette.ring} ring-2 bg-zinc-900 border-zinc-700`
                           : 'bg-zinc-900/60 border-zinc-800 hover:border-zinc-700'
                  } ${s.coming_soon ? 'opacity-70' : ''}`}>
                  <div className="flex items-start gap-3">
                    <div className={`p-2.5 rounded-lg ${palette.bg}`}>
                      <Icon className={`w-5 h-5 ${palette.text}`} />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <h3 className="font-semibold">{s.label}</h3>
                        {s.owner_only && (
                          <span className="text-[10px] px-1.5 py-0.5 bg-amber-500/10 text-amber-400 border border-amber-500/30 rounded flex items-center gap-1">
                            <Shield className="w-3 h-3" /> للمالك
                          </span>
                        )}
                        {s.coming_soon && (
                          <span className="text-[10px] px-1.5 py-0.5 bg-zinc-700 text-zinc-300 rounded">
                            قريباً
                          </span>
                        )}
                        {s.available ? (
                          <span className={`text-[10px] px-1.5 py-0.5 rounded flex items-center gap-1 ${palette.bg} ${palette.text}`}>
                            <CheckCircle2 className="w-3 h-3" />
                            {s.current_model} (Q{s.current_quality})
                          </span>
                        ) : (
                          <span className="text-[10px] px-1.5 py-0.5 bg-rose-500/10 text-rose-400 border border-rose-500/30 rounded flex items-center gap-1">
                            <AlertTriangle className="w-3 h-3" /> مفتاح ناقص
                          </span>
                        )}
                      </div>
                      <p className="text-xs text-zinc-500 mt-1">{s.description}</p>
                      <div className="flex items-center gap-3 mt-2 text-[10px] text-zinc-500">
                        <span className="flex items-center gap-1">
                          <Crown className="w-3 h-3" /> {s.models_count} موديل
                        </span>
                        {s.personas_count > 0 && (
                          <span className="flex items-center gap-1">
                            <Shuffle className="w-3 h-3" /> {s.personas_count} هوية تصميم
                          </span>
                        )}
                        <span className="flex items-center gap-1">
                          <Shield className="w-3 h-3" /> {s.constraints.length} قيد
                        </span>
                      </div>
                    </div>
                    <ChevronRight className={`w-4 h-4 transition ${active ? palette.text : 'text-zinc-600 group-hover:text-zinc-400'}`} />
                  </div>
                </button>
              );
            })}
          </div>

          {/* RIGHT: Detail panel */}
          <div className="lg:col-span-1">
            <div className="sticky top-24 bg-zinc-900/60 border border-zinc-800 rounded-2xl p-5">
              {!selected ? (
                <div className="text-center py-12 text-zinc-500 text-sm">
                  <Sparkles className="w-8 h-8 mx-auto mb-2 opacity-40" />
                  اختر قسماً لتشاهد تفاصيله
                </div>
              ) : !detail ? (
                <div className="flex justify-center py-8">
                  <Loader2 className="w-6 h-6 animate-spin text-zinc-500" />
                </div>
              ) : (
                <div>
                  <div className="flex items-center gap-2 mb-3">
                    {(() => {
                      const Icon = ICON_MAP[detail.icon] || Sparkles;
                      const palette = COLOR_MAP[detail.color] || COLOR_MAP.zinc;
                      return (
                        <div className={`p-2 rounded-lg ${palette.bg}`}>
                          <Icon className={`w-4 h-4 ${palette.text}`} />
                        </div>
                      );
                    })()}
                    <h3 className="font-bold">{detail.label}</h3>
                  </div>

                  <p className="text-xs text-zinc-400 mb-4">{detail.description}</p>

                  {/* Constraints */}
                  <div className="mb-4">
                    <p className="text-[10px] font-bold text-zinc-500 uppercase mb-2 flex items-center gap-1">
                      <Shield className="w-3 h-3" /> القيود / Scope
                    </p>
                    <div className="space-y-1">
                      {(detail.constraints || []).map((c, i) => (
                        <div key={i} className="text-[11px] text-zinc-400 bg-zinc-800/40 px-2 py-1 rounded">
                          • {c}
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Models */}
                  {(detail.resolved_models || []).length > 0 && (
                    <div className="mb-4">
                      <p className="text-[10px] font-bold text-zinc-500 uppercase mb-2 flex items-center gap-1">
                        <Crown className="w-3 h-3" /> النخبة المُعتمدة
                      </p>
                      <div className="space-y-1">
                        {detail.resolved_models.map((m, i) => (
                          <div key={i} className={`flex items-center justify-between text-[11px] px-2 py-1.5 rounded ${
                            m.available ? 'bg-zinc-800/60' : 'bg-zinc-900/30 opacity-50'
                          }`}>
                            <span className="flex items-center gap-1.5">
                              {m.available ? <CheckCircle2 className="w-3 h-3 text-emerald-400" /> : <AlertTriangle className="w-3 h-3 text-rose-400" />}
                              <span>{m.provider}</span>
                              <span className="text-zinc-600">·</span>
                              <span className="text-zinc-500">{m.tier}</span>
                            </span>
                            <span className="text-amber-400">Q{m.quality}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Media models */}
                  {(detail.image_models || []).length > 0 && (
                    <div className="mb-4">
                      <p className="text-[10px] font-bold text-zinc-500 uppercase mb-2">موديلات الصور</p>
                      <div className="space-y-1">
                        {detail.image_models.map((m, i) => (
                          <div key={i} className="text-[11px] bg-zinc-800/40 px-2 py-1 rounded">
                            {m[0]} • Q{m[2]}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                  {(detail.video_models || []).length > 0 && (
                    <div className="mb-4">
                      <p className="text-[10px] font-bold text-zinc-500 uppercase mb-2">موديلات الفيديو</p>
                      <div className="space-y-1">
                        {detail.video_models.map((m, i) => (
                          <div key={i} className="text-[11px] bg-zinc-800/40 px-2 py-1 rounded">
                            {m[0]} • Q{m[2]} • {'$' + m[4]}/ث
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Personas */}
                  {(detail.design_personas || []).length > 0 && (
                    <div className="mb-4">
                      <p className="text-[10px] font-bold text-zinc-500 uppercase mb-2 flex items-center gap-1">
                        <Shuffle className="w-3 h-3" /> {detail.design_personas.length} هوية تصميم متنوعة
                      </p>
                      <div className="flex flex-wrap gap-1">
                        {detail.design_personas.slice(0, 12).map((p, i) => (
                          <span key={i} className="text-[10px] px-1.5 py-0.5 bg-zinc-800 text-zinc-400 rounded">
                            {p}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  <button onClick={tryPick} disabled={picking || detail.coming_soon}
                    className="w-full mt-2 px-4 py-2.5 bg-amber-500 hover:bg-amber-400 text-black font-semibold rounded-lg disabled:opacity-50 flex items-center justify-center gap-2"
                    data-testid="section-try-pick-btn">
                    {picking ? <Loader2 className="w-4 h-4 animate-spin" /> : <Wand2 className="w-4 h-4" />}
                    جرّب الموجّه الآن
                  </button>

                  {pickResult && (
                    <div className="mt-3 p-3 bg-amber-500/5 border border-amber-500/30 rounded-lg" data-testid="section-pick-result">
                      <div className="flex items-center gap-2 mb-1">
                        <Crown className="w-3.5 h-3.5 text-amber-400" />
                        <span className="font-bold text-amber-300 text-sm">{pickResult.model || '?'}</span>
                        <span className="text-[10px] text-zinc-500">Q{pickResult.model_quality}</span>
                      </div>
                      {pickResult.persona && (
                        <p className="text-[11px] text-zinc-300">
                          <span className="text-zinc-500">هوية:</span> {pickResult.persona}
                        </p>
                      )}
                      <p className="text-[11px] text-zinc-400 mt-1">{pickResult.reason}</p>
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
