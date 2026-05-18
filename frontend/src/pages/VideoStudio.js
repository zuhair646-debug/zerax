import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'sonner';
import {
  Film, Plus, Loader2, Check, AlertCircle, Play, ArrowLeft,
  Clapperboard, Sparkles, ImageIcon, CreditCard, RotateCcw, ChevronRight,
} from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;
const VS = `${API}/api/video-studio`;

const authHeaders = () => ({
  'Content-Type': 'application/json',
  Authorization: `Bearer ${localStorage.getItem('token') || ''}`,
});

const STAGE_LABEL = {
  script: 'سيناريو',
  storyboard: 'ستوري بورد',
  approved: 'بانتظار الإنتاج',
  rendered: 'مُنتج',
};

const STAGE_COLOR = {
  script: 'bg-sky-500/20 text-sky-200 border-sky-500/40',
  storyboard: 'bg-amber-500/20 text-amber-200 border-amber-500/40',
  approved: 'bg-violet-500/20 text-violet-200 border-violet-500/40',
  rendered: 'bg-emerald-500/20 text-emerald-200 border-emerald-500/40',
};

export default function VideoStudio() {
  const navigate = useNavigate();

  // ── State ──────────────────────────────────────────────────────────
  const [series, setSeries] = useState([]);
  const [activeSeriesId, setActiveSeriesId] = useState('');
  const [episodes, setEpisodes] = useState([]);
  const [activeEpisode, setActiveEpisode] = useState(null);

  const [chatTurns, setChatTurns] = useState([]); // {role, content}
  const [chatSessionId, setChatSessionId] = useState('');
  const [chatInput, setChatInput] = useState('');
  const [chatBusy, setChatBusy] = useState(false);

  const [briefInput, setBriefInput] = useState('');
  const [shotsRequested, setShotsRequested] = useState(4);
  const [shotDuration, setShotDuration] = useState(8);

  const [busyStage, setBusyStage] = useState('');
  const [showNewSeries, setShowNewSeries] = useState(false);
  const [newSeries, setNewSeries] = useState({ title: '', style_direction: '', main_characters: '' });

  const chatScrollRef = useRef(null);

  // ── Load series on mount ──────────────────────────────────────────
  const loadSeries = useCallback(async () => {
    try {
      const r = await fetch(`${VS}/series`, { headers: authHeaders() });
      if (!r.ok) throw new Error('failed');
      const data = await r.json();
      setSeries(data.series || []);
    } catch {
      toast.error('فشل تحميل السلاسل');
    }
  }, []);

  useEffect(() => { loadSeries(); }, [loadSeries]);

  const loadEpisodes = useCallback(async (sid) => {
    if (!sid) { setEpisodes([]); return; }
    try {
      const r = await fetch(`${VS}/series/${sid}/episodes`, { headers: authHeaders() });
      const data = await r.json();
      setEpisodes(data.episodes || []);
    } catch {
      setEpisodes([]);
    }
  }, []);

  useEffect(() => { loadEpisodes(activeSeriesId); }, [activeSeriesId, loadEpisodes]);

  useEffect(() => {
    if (chatScrollRef.current) {
      chatScrollRef.current.scrollTop = chatScrollRef.current.scrollHeight;
    }
  }, [chatTurns]);

  // ── Create series ─────────────────────────────────────────────────
  const createSeries = async () => {
    if (!newSeries.title.trim()) {
      toast.error('عنوان السلسلة مطلوب');
      return;
    }
    const characters = newSeries.main_characters
      .split('\n').filter(Boolean)
      .map((line) => {
        const [name, ...desc] = line.split(':');
        return { name: (name || '').trim(), desc: desc.join(':').trim() };
      });
    try {
      const r = await fetch(`${VS}/series/create`, {
        method: 'POST', headers: authHeaders(),
        body: JSON.stringify({
          title: newSeries.title,
          style_direction: newSeries.style_direction,
          main_characters: characters,
        }),
      });
      const data = await r.json();
      if (!r.ok) throw new Error(data?.detail || 'failed');
      toast.success('تم إنشاء السلسلة');
      setShowNewSeries(false);
      setNewSeries({ title: '', style_direction: '', main_characters: '' });
      await loadSeries();
      setActiveSeriesId(data.series.id);
    } catch (e) {
      toast.error(`فشل: ${e.message || ''}`);
    }
  };

  // ── Chat: free conversation with the AI ───────────────────────────
  const sendChat = async () => {
    const msg = chatInput.trim();
    if (!msg || chatBusy) return;
    setChatBusy(true);
    setChatInput('');
    setChatTurns((t) => [...t, { role: 'user', content: msg }]);
    try {
      const r = await fetch(`${VS}/chat`, {
        method: 'POST', headers: authHeaders(),
        body: JSON.stringify({
          session_id: chatSessionId || undefined,
          series_id: activeSeriesId || undefined,
          message: msg,
        }),
      });
      const data = await r.json();
      if (!r.ok) throw new Error(data?.detail || 'failed');
      if (data.session_id) setChatSessionId(data.session_id);
      setChatTurns((t) => [...t, {
        role: 'assistant',
        content: data.reply || '',
        redirect: data.redirect,
        cached: data.cached,
      }]);
    } catch (e) {
      toast.error(`فشل: ${e.message || ''}`);
    } finally {
      setChatBusy(false);
    }
  };

  // ── Generate script (free) ────────────────────────────────────────
  const generateScript = async () => {
    if (!briefInput.trim()) {
      toast.error('اكتب فكرة الحلقة أولاً');
      return;
    }
    setBusyStage('script');
    try {
      const r = await fetch(`${VS}/script`, {
        method: 'POST', headers: authHeaders(),
        body: JSON.stringify({
          session_id: chatSessionId || 'std',
          series_id: activeSeriesId || undefined,
          brief: briefInput,
          requested_shots: parseInt(shotsRequested, 10) || 4,
          shot_duration: parseInt(shotDuration, 10) || 8,
        }),
      });
      const data = await r.json();
      if (!r.ok) throw new Error(data?.detail || 'failed');
      setActiveEpisode(data.episode);
      toast.success(`سيناريو جاهز · تكلفة متوقعة ${data.estimated_cost_credits} نقطة (لا خصم بعد)`);
      setBriefInput('');
      loadEpisodes(activeSeriesId);
    } catch (e) {
      toast.error(`فشل: ${e.message || ''}`);
    } finally {
      setBusyStage('');
    }
  };

  // ── Generate storyboard (free) ────────────────────────────────────
  const generateStoryboard = async () => {
    if (!activeEpisode) return;
    setBusyStage('storyboard');
    try {
      const r = await fetch(`${VS}/storyboard`, {
        method: 'POST', headers: authHeaders(),
        body: JSON.stringify({ episode_id: activeEpisode.id }),
      });
      const data = await r.json();
      if (!r.ok) throw new Error(data?.detail || 'failed');
      setActiveEpisode((ep) => ({ ...ep, stage: 'storyboard', shots: data.shots }));
      toast.success(`${data.previews_generated}/${data.total_shots} لقطات معاينة جاهزة`);
    } catch (e) {
      toast.error(`فشل: ${e.message || ''}`);
    } finally {
      setBusyStage('');
    }
  };

  // ── Approve (free gate) ───────────────────────────────────────────
  const approveEpisode = async () => {
    if (!activeEpisode) return;
    if (!window.confirm(`موافق على إنتاج ${activeEpisode.shots?.length} لقطة بتكلفة ${activeEpisode.estimated_cost} نقطة؟`)) return;
    setBusyStage('approve');
    try {
      const r = await fetch(`${VS}/approve`, {
        method: 'POST', headers: authHeaders(),
        body: JSON.stringify({ episode_id: activeEpisode.id, confirmed: true }),
      });
      const data = await r.json();
      if (!r.ok) throw new Error(data?.detail || 'failed');
      setActiveEpisode((ep) => ({ ...ep, stage: 'approved' }));
      toast.success(`تمت الموافقة. اضغط 'إنتاج' لبدء الخصم.`);
    } catch (e) {
      toast.error(`فشل: ${e.message || ''}`);
    } finally {
      setBusyStage('');
    }
  };

  // ── Render (PAID) ─────────────────────────────────────────────────
  const renderEpisode = async () => {
    if (!activeEpisode) return;
    setBusyStage('render');
    toast.info('بدأ الإنتاج… قد يستغرق دقائق', { duration: 8000 });
    try {
      const r = await fetch(`${VS}/render`, {
        method: 'POST', headers: authHeaders(),
        body: JSON.stringify({ episode_id: activeEpisode.id }),
      });
      const data = await r.json();
      if (!r.ok) throw new Error(data?.detail || 'failed');
      setActiveEpisode((ep) => ({ ...ep, stage: 'rendered', final_clips: data.clips, credits_charged: data.credits_charged }));
      toast.success(`اكتمل · ${data.shots_rendered} لقطات · خُصم ${data.credits_charged} نقطة`);
      loadEpisodes(activeSeriesId);
    } catch (e) {
      toast.error(`فشل الإنتاج: ${e.message || ''}`);
    } finally {
      setBusyStage('');
    }
  };

  const openEpisode = async (epId) => {
    try {
      const r = await fetch(`${VS}/episode/${epId}`, { headers: authHeaders() });
      const data = await r.json();
      setActiveEpisode(data.episode);
    } catch {
      toast.error('فشل فتح الحلقة');
    }
  };

  const startNewEpisode = () => {
    setActiveEpisode(null);
    setBriefInput('');
  };

  // ──────────────────────────────────────────────────────────────────
  return (
    <div className="min-h-screen bg-[#0b0d12] text-zinc-100 flex" dir="rtl" data-testid="video-studio-page">
      {/* ── Sidebar — Series ─────────────────────────────────────── */}
      <aside className="w-72 border-l border-zinc-800 bg-[#0e1118] flex flex-col">
        <div className="p-4 border-b border-zinc-800 flex items-center gap-3">
          <button
            onClick={() => navigate('/dashboard')}
            className="p-2 rounded-lg hover:bg-zinc-800 transition"
            data-testid="back-btn"
          >
            <ArrowLeft className="w-4 h-4" />
          </button>
          <div className="flex items-center gap-2">
            <Clapperboard className="w-5 h-5 text-amber-400" />
            <h1 className="text-sm font-semibold tracking-tight">استوديو الفيديو</h1>
          </div>
        </div>

        <button
          onClick={() => setShowNewSeries(true)}
          className="m-3 px-3 py-2 bg-amber-500/10 hover:bg-amber-500/20 border border-amber-500/30 rounded-lg text-sm font-medium text-amber-200 flex items-center justify-center gap-2 transition"
          data-testid="new-series-btn"
        >
          <Plus className="w-4 h-4" />
          سلسلة جديدة
        </button>

        <div className="flex-1 overflow-y-auto px-3 pb-3">
          <div className="text-xs text-zinc-500 px-2 pb-2 mt-1">سلاسلك</div>
          {series.length === 0 && (
            <div className="text-xs text-zinc-600 px-2 py-6 text-center">
              ما عندك سلاسل بعد. أنشئ واحدة عشان تخزّن حلقات متتالية بنفس الستايل.
            </div>
          )}
          {series.map((s) => (
            <button
              key={s.id}
              onClick={() => { setActiveSeriesId(s.id); setActiveEpisode(null); }}
              className={`w-full text-right px-3 py-2 mb-1 rounded-lg text-sm transition ${
                activeSeriesId === s.id
                  ? 'bg-amber-500/15 text-amber-100 border border-amber-500/30'
                  : 'hover:bg-zinc-800 text-zinc-300 border border-transparent'
              }`}
              data-testid={`series-item-${s.id}`}
            >
              <div className="font-medium truncate">{s.title}</div>
              <div className="text-[10px] text-zinc-500 mt-0.5">
                {s.episode_count || 0} حلقة
              </div>
            </button>
          ))}
        </div>

        {activeSeriesId && episodes.length > 0 && (
          <div className="border-t border-zinc-800 p-3 max-h-72 overflow-y-auto">
            <div className="text-xs text-zinc-500 px-1 pb-2">حلقات السلسلة</div>
            {episodes.map((ep) => (
              <button
                key={ep.id}
                onClick={() => openEpisode(ep.id)}
                className={`w-full text-right px-2 py-1.5 mb-1 rounded text-xs flex items-center justify-between transition ${
                  activeEpisode?.id === ep.id
                    ? 'bg-zinc-700/60 text-zinc-100'
                    : 'hover:bg-zinc-800 text-zinc-400'
                }`}
                data-testid={`episode-item-${ep.id}`}
              >
                <span className="truncate">حلقة {ep.episode_number} · {ep.script?.title || 'بدون عنوان'}</span>
                <span className={`text-[9px] px-1.5 py-0.5 rounded border ${STAGE_COLOR[ep.stage] || ''}`}>
                  {STAGE_LABEL[ep.stage] || ep.stage}
                </span>
              </button>
            ))}
          </div>
        )}
      </aside>

      {/* ── Main pane ────────────────────────────────────────────── */}
      <main className="flex-1 flex flex-col min-w-0">
        {/* Header */}
        <header className="border-b border-zinc-800 px-6 py-3 flex items-center justify-between bg-[#0e1118]">
          <div className="flex items-center gap-3 min-w-0">
            {activeEpisode ? (
              <>
                <Film className="w-5 h-5 text-amber-400 shrink-0" />
                <div className="min-w-0">
                  <div className="text-sm font-medium truncate">
                    حلقة {activeEpisode.episode_number} · {activeEpisode.script?.title || 'بدون عنوان'}
                  </div>
                  <div className="text-xs text-zinc-500 truncate">
                    {activeEpisode.script?.logline || activeEpisode.brief}
                  </div>
                </div>
              </>
            ) : (
              <div className="text-sm text-zinc-400">
                {activeSeriesId
                  ? series.find((s) => s.id === activeSeriesId)?.title || 'سلسلة'
                  : 'اختر سلسلة من الجنب أو أنشئ جديدة'}
              </div>
            )}
          </div>
          <div className="flex items-center gap-2">
            {activeEpisode && (
              <span className={`text-xs px-2 py-1 rounded border ${STAGE_COLOR[activeEpisode.stage] || ''}`}>
                {STAGE_LABEL[activeEpisode.stage] || activeEpisode.stage}
              </span>
            )}
            {activeSeriesId && (
              <button
                onClick={startNewEpisode}
                className="text-xs px-3 py-1.5 rounded-lg bg-zinc-800 hover:bg-zinc-700 text-zinc-200 flex items-center gap-1.5"
                data-testid="new-episode-btn"
              >
                <Plus className="w-3 h-3" /> حلقة جديدة
              </button>
            )}
          </div>
        </header>

        {/* Content area */}
        <div className="flex-1 overflow-y-auto" ref={chatScrollRef}>
          {!activeEpisode ? (
            <EmptyEpisodePane
              activeSeriesId={activeSeriesId}
              briefInput={briefInput}
              setBriefInput={setBriefInput}
              shotsRequested={shotsRequested}
              setShotsRequested={setShotsRequested}
              shotDuration={shotDuration}
              setShotDuration={setShotDuration}
              onGenerate={generateScript}
              busy={busyStage === 'script'}
              chatTurns={chatTurns}
              chatInput={chatInput}
              setChatInput={setChatInput}
              sendChat={sendChat}
              chatBusy={chatBusy}
            />
          ) : (
            <EpisodePane
              ep={activeEpisode}
              busy={busyStage}
              onStoryboard={generateStoryboard}
              onApprove={approveEpisode}
              onRender={renderEpisode}
            />
          )}
        </div>
      </main>

      {/* ── New Series Modal ─────────────────────────────────────── */}
      {showNewSeries && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-[#12161e] border border-zinc-800 rounded-2xl p-6 w-full max-w-md" data-testid="new-series-modal">
            <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <Sparkles className="w-5 h-5 text-amber-400" /> سلسلة فيديو جديدة
            </h2>
            <div className="space-y-3">
              <div>
                <label className="text-xs text-zinc-400 block mb-1">عنوان السلسلة</label>
                <input
                  value={newSeries.title}
                  onChange={(e) => setNewSeries((s) => ({ ...s, title: e.target.value }))}
                  className="w-full bg-zinc-900 border border-zinc-700 rounded-lg px-3 py-2 text-sm"
                  placeholder="مثلاً: حكاية وادي النور"
                  data-testid="new-series-title-input"
                />
              </div>
              <div>
                <label className="text-xs text-zinc-400 block mb-1">الستايل البصري (إنجليزي مختصر)</label>
                <input
                  value={newSeries.style_direction}
                  onChange={(e) => setNewSeries((s) => ({ ...s, style_direction: e.target.value }))}
                  className="w-full bg-zinc-900 border border-zinc-700 rounded-lg px-3 py-2 text-sm font-mono"
                  placeholder="Cinematic 35mm, warm sepia, soft golden hour"
                  data-testid="new-series-style-input"
                />
              </div>
              <div>
                <label className="text-xs text-zinc-400 block mb-1">الشخصيات الرئيسية (سطر لكل واحد · الاسم: الوصف)</label>
                <textarea
                  value={newSeries.main_characters}
                  onChange={(e) => setNewSeries((s) => ({ ...s, main_characters: e.target.value }))}
                  className="w-full bg-zinc-900 border border-zinc-700 rounded-lg px-3 py-2 text-sm h-24"
                  placeholder={'سالم: شاب 25، ثوب أبيض، عيون حادة\nنورة: 22، حجاب أزرق، ابتسامة دافئة'}
                  data-testid="new-series-chars-input"
                />
              </div>
              <div className="flex gap-2 pt-2">
                <button
                  onClick={createSeries}
                  className="flex-1 bg-amber-500 hover:bg-amber-400 text-black font-medium py-2 rounded-lg text-sm"
                  data-testid="create-series-confirm-btn"
                >
                  إنشاء
                </button>
                <button
                  onClick={() => setShowNewSeries(false)}
                  className="px-4 bg-zinc-800 hover:bg-zinc-700 rounded-lg text-sm"
                  data-testid="create-series-cancel-btn"
                >
                  إلغاء
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ─── Empty Episode Pane (chat + brief input) ──────────────────────────
function EmptyEpisodePane({
  activeSeriesId, briefInput, setBriefInput,
  shotsRequested, setShotsRequested, shotDuration, setShotDuration,
  onGenerate, busy, chatTurns, chatInput, setChatInput, sendChat, chatBusy,
}) {
  return (
    <div className="max-w-3xl mx-auto p-6">
      <div className="mb-6">
        <h2 className="text-lg font-semibold mb-1 flex items-center gap-2">
          <Sparkles className="w-5 h-5 text-amber-400" /> ابدأ حلقة جديدة
        </h2>
        <p className="text-sm text-zinc-400">
          اكتب فكرة الحلقة وعدد اللقطات ومدة كل لقطة. الذكاء يطلع لك سيناريو منظّم
          {' '}<span className="text-emerald-400">(مجاناً — لا خصم نقاط)</span>.
        </p>
      </div>

      <div className="bg-[#12161e] border border-zinc-800 rounded-2xl p-5 mb-6">
        <label className="text-xs text-zinc-400 block mb-1">الفكرة / البريف</label>
        <textarea
          value={briefInput}
          onChange={(e) => setBriefInput(e.target.value)}
          className="w-full bg-zinc-900 border border-zinc-700 rounded-lg px-3 py-2 text-sm h-28 mb-3"
          placeholder="مثلاً: حلقة 1 — سالم يبدأ رحلته نحو وادي النور في فجر يوم خريفي، يلاقي مسافراً يحذّره من المدينة الفضية."
          data-testid="brief-input"
        />
        <div className="grid grid-cols-2 gap-3 mb-3">
          <div>
            <label className="text-xs text-zinc-400 block mb-1">عدد اللقطات</label>
            <input
              type="number" min="1" max="12"
              value={shotsRequested}
              onChange={(e) => setShotsRequested(e.target.value)}
              className="w-full bg-zinc-900 border border-zinc-700 rounded-lg px-3 py-2 text-sm"
              data-testid="shots-count-input"
            />
          </div>
          <div>
            <label className="text-xs text-zinc-400 block mb-1">مدة اللقطة (ثانية)</label>
            <select
              value={shotDuration}
              onChange={(e) => setShotDuration(e.target.value)}
              className="w-full bg-zinc-900 border border-zinc-700 rounded-lg px-3 py-2 text-sm"
              data-testid="shot-duration-select"
            >
              <option value="4">4 ثواني (8 نقاط/لقطة)</option>
              <option value="8">8 ثواني (14 نقطة/لقطة)</option>
              <option value="12">12 ثانية (20 نقطة/لقطة)</option>
            </select>
          </div>
        </div>
        <button
          onClick={onGenerate}
          disabled={busy || !briefInput.trim()}
          className="w-full bg-amber-500 hover:bg-amber-400 disabled:opacity-50 disabled:cursor-not-allowed text-black font-medium py-2.5 rounded-lg text-sm flex items-center justify-center gap-2"
          data-testid="generate-script-btn"
        >
          {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
          ولّد السيناريو
        </button>
      </div>

      {/* Chat panel */}
      <div className="bg-[#12161e] border border-zinc-800 rounded-2xl p-5">
        <div className="text-sm font-semibold mb-3 flex items-center gap-2">
          <ChevronRight className="w-4 h-4 text-amber-400" />
          استشر زيتاكس فيديو (مجاناً)
        </div>
        <div className="space-y-3 max-h-72 overflow-y-auto mb-3 pr-1">
          {chatTurns.length === 0 && (
            <div className="text-xs text-zinc-500 text-center py-6">
              اسأل عن أي شي يخص الفيديو — أفكار، ستايلات، طول اللقطات…
            </div>
          )}
          {chatTurns.map((t, i) => (
            <div key={i} className={`text-sm ${t.role === 'user' ? 'text-zinc-100' : 'text-zinc-300'}`}>
              <div className={`text-[10px] mb-0.5 ${t.role === 'user' ? 'text-amber-400' : 'text-emerald-400'}`}>
                {t.role === 'user' ? 'أنت' : 'زيتاكس فيديو'} {t.cached && <span className="text-zinc-500">· من الذاكرة</span>}
              </div>
              <div className="whitespace-pre-wrap leading-6">{t.content}</div>
              {t.redirect && (
                <a href={t.redirect.to_route} className="text-xs text-sky-400 underline mt-1 inline-block">
                  {t.redirect.to_label} ←
                </a>
              )}
            </div>
          ))}
        </div>
        <div className="flex gap-2">
          <input
            value={chatInput}
            onChange={(e) => setChatInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && sendChat()}
            disabled={chatBusy}
            className="flex-1 bg-zinc-900 border border-zinc-700 rounded-lg px-3 py-2 text-sm"
            placeholder="اكتب سؤالك…"
            data-testid="chat-input"
          />
          <button
            onClick={sendChat}
            disabled={chatBusy || !chatInput.trim()}
            className="px-4 bg-amber-500 hover:bg-amber-400 disabled:opacity-50 text-black font-medium rounded-lg text-sm"
            data-testid="chat-send-btn"
          >
            {chatBusy ? <Loader2 className="w-4 h-4 animate-spin" /> : 'إرسال'}
          </button>
        </div>
      </div>
    </div>
  );
}

// ─── Episode Pane (script + storyboard + actions) ─────────────────────
function EpisodePane({ ep, busy, onStoryboard, onApprove, onRender }) {
  const shots = ep.shots || [];
  const finalClips = ep.final_clips || [];
  const cost = ep.estimated_cost || 0;
  const charged = ep.credits_charged || 0;

  return (
    <div className="max-w-5xl mx-auto p-6" data-testid={`episode-${ep.id}`}>
      {/* Script header */}
      {ep.script && (
        <div className="bg-[#12161e] border border-zinc-800 rounded-2xl p-5 mb-5">
          <div className="text-xs text-zinc-500 mb-1">السيناريو</div>
          <h2 className="text-xl font-semibold mb-1">{ep.script.title}</h2>
          <p className="text-sm text-zinc-300 mb-3">{ep.script.logline}</p>
          {ep.script.characters?.length > 0 && (
            <div className="text-xs text-zinc-400">
              <span className="text-zinc-500">الشخصيات: </span>
              {ep.script.characters.map((c, i) => (
                <span key={i} className="ml-2">
                  <b className="text-zinc-200">{c.name}</b> — {c.desc}
                  {i < ep.script.characters.length - 1 ? ' · ' : ''}
                </span>
              ))}
            </div>
          )}
          <div className="text-[11px] text-zinc-500 mt-2 font-mono">{ep.script.style}</div>
        </div>
      )}

      {/* Storyboard grid */}
      {shots.length > 0 && (
        <div className="mb-5">
          <div className="text-xs text-zinc-500 mb-2 flex items-center gap-2">
            <ImageIcon className="w-3.5 h-3.5" /> اللقطات ({shots.length})
          </div>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
            {shots.map((shot, i) => {
              const clip = finalClips.find((c) => c.n === shot.n);
              const preview = shot.preview_url ? `${API}${shot.preview_url}` : null;
              return (
                <div key={i} className="bg-[#12161e] border border-zinc-800 rounded-xl overflow-hidden">
                  <div className="aspect-video bg-zinc-900 flex items-center justify-center relative">
                    {clip?.video_url ? (
                      <video src={clip.video_url} controls className="w-full h-full object-cover" data-testid={`clip-${shot.n}`} />
                    ) : preview ? (
                      <img src={preview} alt={shot.title_ar} className="w-full h-full object-cover" data-testid={`preview-${shot.n}`} />
                    ) : (
                      <div className="text-xs text-zinc-600 flex flex-col items-center gap-1">
                        <ImageIcon className="w-6 h-6" />
                        <span>لقطة {shot.n}</span>
                      </div>
                    )}
                    <div className="absolute top-1 right-1 bg-black/80 text-zinc-300 text-[10px] px-1.5 py-0.5 rounded">
                      #{shot.n} · {shot.duration || 8}s
                    </div>
                  </div>
                  <div className="p-2">
                    <div className="text-xs font-medium text-zinc-200 mb-1 truncate">{shot.title_ar}</div>
                    {shot.narration_ar && (
                      <div className="text-[10px] text-zinc-500 line-clamp-2">{shot.narration_ar}</div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Action bar */}
      <div className="bg-[#12161e] border border-zinc-800 rounded-2xl p-4 sticky bottom-4">
        {ep.stage === 'script' && (
          <div className="flex items-center justify-between gap-3">
            <div className="text-xs text-zinc-400">
              التكلفة المتوقعة عند الإنتاج: <b className="text-amber-300">{cost}</b> نقطة · لا خصم بعد
            </div>
            <button
              onClick={onStoryboard}
              disabled={busy === 'storyboard'}
              className="bg-amber-500 hover:bg-amber-400 disabled:opacity-50 text-black font-medium px-5 py-2 rounded-lg text-sm flex items-center gap-2"
              data-testid="storyboard-btn"
            >
              {busy === 'storyboard' ? <Loader2 className="w-4 h-4 animate-spin" /> : <ImageIcon className="w-4 h-4" />}
              ولّد معاينة الستوري بورد (مجاناً)
            </button>
          </div>
        )}
        {ep.stage === 'storyboard' && (
          <div className="flex items-center justify-between gap-3 flex-wrap">
            <div className="text-xs text-zinc-400">
              راجع الصور. لو عاجبتك اضغط <b className="text-emerald-300">موافق</b> — التكلفة <b className="text-amber-300">{cost}</b> نقطة.
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={onStoryboard}
                disabled={busy === 'storyboard'}
                className="bg-zinc-800 hover:bg-zinc-700 text-zinc-200 px-3 py-2 rounded-lg text-xs flex items-center gap-1.5"
                data-testid="regen-storyboard-btn"
              >
                <RotateCcw className="w-3.5 h-3.5" /> أعد التوليد
              </button>
              <button
                onClick={onApprove}
                disabled={busy === 'approve'}
                className="bg-emerald-500 hover:bg-emerald-400 disabled:opacity-50 text-black font-medium px-5 py-2 rounded-lg text-sm flex items-center gap-2"
                data-testid="approve-btn"
              >
                {busy === 'approve' ? <Loader2 className="w-4 h-4 animate-spin" /> : <Check className="w-4 h-4" />}
                موافق ابدأ الإنتاج
              </button>
            </div>
          </div>
        )}
        {ep.stage === 'approved' && (
          <div className="flex items-center justify-between gap-3">
            <div className="text-xs text-zinc-400">
              تمت الموافقة. اضغط <b className="text-emerald-300">إنتاج</b> لخصم <b className="text-amber-300">{cost}</b> نقطة وبدء الإنتاج عبر Sora 2.
            </div>
            <button
              onClick={onRender}
              disabled={busy === 'render'}
              className="bg-emerald-500 hover:bg-emerald-400 disabled:opacity-50 text-black font-medium px-5 py-2 rounded-lg text-sm flex items-center gap-2"
              data-testid="render-btn"
            >
              {busy === 'render' ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
              ابدأ الإنتاج النهائي
            </button>
          </div>
        )}
        {ep.stage === 'rendered' && (
          <div className="flex items-center gap-3 text-sm">
            <Check className="w-5 h-5 text-emerald-400" />
            <span className="text-emerald-300 font-medium">اكتمل الإنتاج</span>
            <span className="text-zinc-500">· خُصم {charged} نقطة · {finalClips.length} لقطة</span>
          </div>
        )}
        {busy === 'render' && (
          <div className="mt-3 text-xs text-amber-300 flex items-center gap-2">
            <Loader2 className="w-3.5 h-3.5 animate-spin" />
            جاري الإنتاج عبر Sora 2 — قد يستغرق دقيقتين لكل لقطة. لا تغلق الصفحة.
          </div>
        )}
        {!['script', 'storyboard', 'approved', 'rendered'].includes(ep.stage) && (
          <div className="text-xs text-zinc-500 flex items-center gap-2">
            <AlertCircle className="w-3.5 h-3.5" /> مرحلة غير معروفة: {ep.stage}
          </div>
        )}
      </div>
    </div>
  );
}
