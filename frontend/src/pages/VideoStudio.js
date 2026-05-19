import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'sonner';
import {
  Film, Plus, Loader2, Check, AlertCircle, Play, ArrowLeft,
  Clapperboard, Sparkles, ImageIcon, RotateCcw, Settings, MessageSquare,
  FileText, Languages, Share2, Copy, Download, Key, Upload, Users, Heart, Eye,
} from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;
const VS = `${API}/api/video-studio`;

const authHeaders = () => ({
  'Content-Type': 'application/json',
  Authorization: `Bearer ${localStorage.getItem('token') || ''}`,
});

const STAGE_LABEL = { script: 'سيناريو', storyboard: 'ستوري بورد', approved: 'بانتظار الإنتاج', rendered: 'مُنتج' };
const STAGE_COLOR = {
  script: 'bg-sky-500/20 text-sky-200 border-sky-500/40',
  storyboard: 'bg-amber-500/20 text-amber-200 border-amber-500/40',
  approved: 'bg-violet-500/20 text-violet-200 border-violet-500/40',
  rendered: 'bg-emerald-500/20 text-emerald-200 border-emerald-500/40',
};

const SOCIAL_PLATFORMS = [
  { id: 'tiktok',   label: 'TikTok',    url: 'https://www.tiktok.com/upload',           color: 'bg-pink-500/20 border-pink-500/40 text-pink-200' },
  { id: 'instagram', label: 'Instagram', url: 'https://www.instagram.com/',              color: 'bg-fuchsia-500/20 border-fuchsia-500/40 text-fuchsia-200' },
  { id: 'youtube',  label: 'YouTube',   url: 'https://studio.youtube.com/channel/UC/videos/short', color: 'bg-red-500/20 border-red-500/40 text-red-200' },
  { id: 'twitter',  label: 'X/Twitter', url: 'https://twitter.com/compose/tweet',       color: 'bg-sky-500/20 border-sky-500/40 text-sky-200' },
  { id: 'snapchat', label: 'Snapchat',  url: 'https://web.snapchat.com/',                color: 'bg-yellow-500/20 border-yellow-500/40 text-yellow-200' },
];

export default function VideoStudio() {
  const navigate = useNavigate();

  // Catalogues from backend
  const [opts, setOpts] = useState({ languages: [], art_styles: [], genres: [], aspect_ratios: [], voice_genders: [], owner_key_configured: false });

  // Series + episodes
  const [series, setSeries] = useState([]);
  const [activeSeriesId, setActiveSeriesId] = useState('');
  const [episodes, setEpisodes] = useState([]);
  const [activeEpisode, setActiveEpisode] = useState(null);

  // Chat
  const [chatTurns, setChatTurns] = useState([]);
  const [chatSessionId, setChatSessionId] = useState('');
  const [chatInput, setChatInput] = useState('');
  const [chatBusy, setChatBusy] = useState(false);

  // Brief + settings
  const [briefInput, setBriefInput] = useState('');
  const [settings, setSettings] = useState({
    shots: 4,
    shot_duration: 8,
    language: 'ar-saudi',
    dialect_notes: '',
    subtitle_language: '',
    art_style: 'cinematic',
    genre: 'drama',
    aspect_ratio: '16x9',
    voice_gender: 'male',
    extra_directives: '',
  });

  // Tabs in the episode pane
  const [tab, setTab] = useState('chat'); // chat | story | dialogue | storyboard
  const [busyStage, setBusyStage] = useState('');

  // New series modal
  const [showNewSeries, setShowNewSeries] = useState(false);
  const [newSeries, setNewSeries] = useState({ title: '', style_direction: '', main_characters: '' });

  // Share state
  const [shareData, setShareData] = useState(null); // { slug, public_url, captions }

  // Narration upload
  const [narrationFile, setNarrationFile] = useState(null);
  const narrationInputRef = useRef(null);

  // Community / Discover
  const [discoverFeed, setDiscoverFeed] = useState([]);
  const [discoverLoaded, setDiscoverLoaded] = useState(false);

  const chatScrollRef = useRef(null);

  // ── Load catalogues + series on mount ─────────────────────────────
  useEffect(() => {
    (async () => {
      try {
        const r = await fetch(`${VS}/options`, { headers: authHeaders() });
        if (r.ok) setOpts(await r.json());
      } catch { /* ignore */ }
    })();
  }, []);

  const loadSeries = useCallback(async () => {
    try {
      const r = await fetch(`${VS}/series`, { headers: authHeaders() });
      const d = await r.json();
      setSeries(d.series || []);
    } catch { toast.error('فشل تحميل السلاسل'); }
  }, []);
  useEffect(() => { loadSeries(); }, [loadSeries]);

  const loadEpisodes = useCallback(async (sid) => {
    if (!sid) { setEpisodes([]); return; }
    try {
      const r = await fetch(`${VS}/series/${sid}/episodes`, { headers: authHeaders() });
      setEpisodes((await r.json()).episodes || []);
    } catch { setEpisodes([]); }
  }, []);
  useEffect(() => { loadEpisodes(activeSeriesId); }, [activeSeriesId, loadEpisodes]);

  useEffect(() => {
    if (chatScrollRef.current) chatScrollRef.current.scrollTop = chatScrollRef.current.scrollHeight;
  }, [chatTurns]);

  // ── Actions ───────────────────────────────────────────────────────
  const createSeries = async () => {
    if (!newSeries.title.trim()) return toast.error('عنوان السلسلة مطلوب');
    const characters = newSeries.main_characters.split('\n').filter(Boolean)
      .map((line) => { const [n, ...d] = line.split(':'); return { name: (n || '').trim(), desc: d.join(':').trim() }; });
    try {
      const r = await fetch(`${VS}/series/create`, {
        method: 'POST', headers: authHeaders(),
        body: JSON.stringify({ title: newSeries.title, style_direction: newSeries.style_direction, main_characters: characters }),
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d?.detail || 'failed');
      toast.success('تم إنشاء السلسلة');
      setShowNewSeries(false);
      setNewSeries({ title: '', style_direction: '', main_characters: '' });
      await loadSeries();
      setActiveSeriesId(d.series.id);
    } catch (e) { toast.error(`فشل: ${e.message || ''}`); }
  };

  const sendChat = async () => {
    const msg = chatInput.trim();
    if (!msg || chatBusy) return;
    setChatBusy(true);
    setChatInput('');
    setChatTurns((t) => [...t, { role: 'user', content: msg }]);
    try {
      const r = await fetch(`${VS}/chat`, {
        method: 'POST', headers: authHeaders(),
        body: JSON.stringify({ session_id: chatSessionId || undefined, series_id: activeSeriesId || undefined, message: msg }),
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d?.detail || 'failed');
      if (d.session_id) setChatSessionId(d.session_id);
      setChatTurns((t) => [...t, { role: 'assistant', content: d.reply || '', redirect: d.redirect, cached: d.cached }]);
    } catch (e) { toast.error(`فشل: ${e.message || ''}`); }
    finally { setChatBusy(false); }
  };

  const generateScript = async () => {
    if (!briefInput.trim()) return toast.error('اكتب فكرة الحلقة أولاً');
    if (!opts.owner_key_configured) {
      return toast.error('أضف مفتاح OpenAI الخاص بك من /admin/independence أولاً');
    }
    setBusyStage('script');
    try {
      const r = await fetch(`${VS}/script`, {
        method: 'POST', headers: authHeaders(),
        body: JSON.stringify({
          session_id: chatSessionId || 'std',
          series_id: activeSeriesId || undefined,
          brief: briefInput,
          requested_shots: parseInt(settings.shots, 10) || 4,
          shot_duration: parseInt(settings.shot_duration, 10) || 8,
          language: settings.language,
          dialect_notes: settings.dialect_notes,
          subtitle_language: settings.subtitle_language,
          art_style: settings.art_style,
          genre: settings.genre,
          aspect_ratio: settings.aspect_ratio,
          voice_gender: settings.voice_gender,
          extra_directives: settings.extra_directives,
        }),
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d?.detail || 'failed');
      setActiveEpisode(d.episode);
      setShareData(null);
      toast.success(`سيناريو جاهز · تكلفة ${d.estimated_cost_credits} نقطة (لا خصم بعد)`);
      setBriefInput('');
      setTab('story');
      loadEpisodes(activeSeriesId);
    } catch (e) { toast.error(`فشل: ${e.message || ''}`); }
    finally { setBusyStage(''); }
  };

  const generateStoryboard = async () => {
    if (!activeEpisode) return;
    setBusyStage('storyboard');
    try {
      const r = await fetch(`${VS}/storyboard`, {
        method: 'POST', headers: authHeaders(),
        body: JSON.stringify({ episode_id: activeEpisode.id }),
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d?.detail || 'failed');
      setActiveEpisode((ep) => ({ ...ep, stage: 'storyboard', shots: d.shots }));
      toast.success(`${d.previews_generated}/${d.total_shots} لقطات معاينة جاهزة`);
      setTab('storyboard');
    } catch (e) { toast.error(`فشل: ${e.message || ''}`); }
    finally { setBusyStage(''); }
  };

  const approveEpisode = async () => {
    if (!activeEpisode) return;
    if (!window.confirm(`موافق على إنتاج ${activeEpisode.shots?.length} لقطة بتكلفة ${activeEpisode.estimated_cost} نقطة؟`)) return;
    setBusyStage('approve');
    try {
      const r = await fetch(`${VS}/approve`, {
        method: 'POST', headers: authHeaders(),
        body: JSON.stringify({ episode_id: activeEpisode.id, confirmed: true }),
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d?.detail || 'failed');
      setActiveEpisode((ep) => ({ ...ep, stage: 'approved' }));
      toast.success('تمت الموافقة. اضغط الإنتاج لبدء الخصم.');
    } catch (e) { toast.error(`فشل: ${e.message || ''}`); }
    finally { setBusyStage(''); }
  };

  const uploadNarration = async () => {
    if (!narrationFile) return toast.error('اختر ملف صوت أولاً');
    if (!opts.owner_key_configured) return toast.error('أضف مفتاح OpenAI من /admin/independence');
    setBusyStage('narration');
    try {
      const fd = new FormData();
      fd.append('audio', narrationFile);
      fd.append('series_id', activeSeriesId || '');
      fd.append('language', settings.language);
      fd.append('art_style', settings.art_style);
      fd.append('aspect_ratio', settings.aspect_ratio);
      fd.append('max_shots', String(settings.shots || 8));
      const r = await fetch(`${VS}/narration-to-script`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${localStorage.getItem('token') || ''}` },
        body: fd,
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d?.detail || 'failed');
      setActiveEpisode(d.episode);
      setShareData(null);
      toast.success(`السيناريو جاهز · ${d.shots_count} لقطات · ${d.transcribed_chars} حرف من صوتك`);
      setNarrationFile(null);
      if (narrationInputRef.current) narrationInputRef.current.value = '';
      setTab('story');
      loadEpisodes(activeSeriesId);
    } catch (e) {
      toast.error(`فشل: ${e.message || ''}`);
    } finally {
      setBusyStage('');
    }
  };

  const loadDiscover = async () => {
    try {
      const r = await fetch(`${VS}/discover?limit=30`, { headers: authHeaders() });
      const d = await r.json();
      setDiscoverFeed(d.feed || []);
      setDiscoverLoaded(true);
    } catch { toast.error('فشل تحميل المجتمع'); }
  };

  const likeEpisode = async (epId) => {
    try {
      await fetch(`${VS}/discover/${epId}/like`, { method: 'POST', headers: authHeaders() });
      setDiscoverFeed((f) => f.map((x) => x.id === epId ? { ...x, likes: (x.likes || 0) + 1 } : x));
    } catch { /* silent */ }
  };

  const renderEpisode = async () => {
    if (!activeEpisode) return;
    setBusyStage('render');
    toast.info('بدأ الإنتاج… قد يستغرق دقائق', { duration: 8000 });
    try {
      const r = await fetch(`${VS}/render`, {
        method: 'POST', headers: authHeaders(),
        body: JSON.stringify({ episode_id: activeEpisode.id }),
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d?.detail || 'failed');
      setActiveEpisode((ep) => ({ ...ep, stage: 'rendered', final_clips: d.clips, credits_charged: d.credits_charged }));
      toast.success(`اكتمل · ${d.shots_rendered} لقطات · خُصم ${d.credits_charged} نقطة`);
      loadEpisodes(activeSeriesId);
    } catch (e) { toast.error(`فشل الإنتاج: ${e.message || ''}`); }
    finally { setBusyStage(''); }
  };

  const shareEpisode = async () => {
    if (!activeEpisode) return;
    setBusyStage('share');
    try {
      const r = await fetch(`${VS}/share`, {
        method: 'POST', headers: authHeaders(),
        body: JSON.stringify({ episode_id: activeEpisode.id }),
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d?.detail || 'failed');
      setShareData({ ...d, full_url: `${API}${d.public_url}` });
      toast.success('رابط المشاركة جاهز');
    } catch (e) { toast.error(`فشل: ${e.message || ''}`); }
    finally { setBusyStage(''); }
  };

  const downloadAllClips = () => {
    if (!activeEpisode?.final_clips) return;
    activeEpisode.final_clips.forEach((c, i) => {
      if (!c.video_url) return;
      const a = document.createElement('a');
      a.href = c.video_url;
      a.download = `shot_${c.n || i + 1}.mp4`;
      a.click();
    });
  };

  const openEpisode = async (epId) => {
    try {
      const r = await fetch(`${VS}/episode/${epId}`, { headers: authHeaders() });
      const d = await r.json();
      setActiveEpisode(d.episode);
      setShareData(null);
      setTab(d.episode?.stage === 'rendered' ? 'storyboard' : 'story');
    } catch { toast.error('فشل فتح الحلقة'); }
  };

  const startNewEpisode = () => {
    setActiveEpisode(null);
    setBriefInput('');
    setShareData(null);
    setTab('chat');
  };

  // ──────────────────────────────────────────────────────────────────
  return (
    <div className="min-h-screen bg-[#0b0d12] text-zinc-100 flex" dir="rtl" data-testid="video-studio-page">
      {/* ── LEFT — Series sidebar ─────────────────────────────────── */}
      <aside className="w-64 border-l border-zinc-800 bg-[#0e1118] flex flex-col shrink-0">
        <div className="p-4 border-b border-zinc-800 flex items-center gap-3">
          <button onClick={() => navigate('/dashboard')} className="p-2 rounded-lg hover:bg-zinc-800" data-testid="back-btn">
            <ArrowLeft className="w-4 h-4" />
          </button>
          <div className="flex items-center gap-2">
            <Clapperboard className="w-5 h-5 text-amber-400" />
            <h1 className="text-sm font-semibold">استوديو الفيديو</h1>
          </div>
        </div>

        {!opts.owner_key_configured && (
          <div className="mx-3 mt-3 bg-rose-500/10 border border-rose-500/40 rounded-lg p-3 text-[11px] text-rose-200" data-testid="missing-key-warning">
            <div className="flex items-center gap-1.5 mb-1 font-semibold">
              <Key className="w-3.5 h-3.5" /> مفتاحك مفقود
            </div>
            <div className="leading-5">أضف OPENAI_DIRECT_KEY في صفحة <a href="/admin/independence" className="underline text-rose-100">/admin/independence</a> عشان ما يُخصم من حساب المنصة.</div>
          </div>
        )}

        <button onClick={() => setShowNewSeries(true)}
          className="m-3 px-3 py-2 bg-amber-500/10 hover:bg-amber-500/20 border border-amber-500/30 rounded-lg text-sm font-medium text-amber-200 flex items-center justify-center gap-2"
          data-testid="new-series-btn">
          <Plus className="w-4 h-4" /> سلسلة جديدة
        </button>

        <div className="flex-1 overflow-y-auto px-3 pb-3">
          <div className="text-xs text-zinc-500 px-2 pb-2 mt-1">سلاسلك</div>
          {series.length === 0 && (
            <div className="text-xs text-zinc-600 px-2 py-6 text-center">ما عندك سلاسل بعد.</div>
          )}
          {series.map((s) => (
            <button key={s.id} onClick={() => { setActiveSeriesId(s.id); setActiveEpisode(null); }}
              className={`w-full text-right px-3 py-2 mb-1 rounded-lg text-sm transition ${
                activeSeriesId === s.id ? 'bg-amber-500/15 text-amber-100 border border-amber-500/30'
                                        : 'hover:bg-zinc-800 text-zinc-300 border border-transparent'
              }`} data-testid={`series-item-${s.id}`}>
              <div className="font-medium truncate">{s.title}</div>
              <div className="text-[10px] text-zinc-500 mt-0.5">{s.episode_count || 0} حلقة</div>
            </button>
          ))}
        </div>

        {activeSeriesId && episodes.length > 0 && (
          <div className="border-t border-zinc-800 p-3 max-h-72 overflow-y-auto">
            <div className="text-xs text-zinc-500 px-1 pb-2">حلقات السلسلة</div>
            {episodes.map((ep) => (
              <button key={ep.id} onClick={() => openEpisode(ep.id)}
                className={`w-full text-right px-2 py-1.5 mb-1 rounded text-xs flex items-center justify-between ${
                  activeEpisode?.id === ep.id ? 'bg-zinc-700/60 text-zinc-100' : 'hover:bg-zinc-800 text-zinc-400'
                }`} data-testid={`episode-item-${ep.id}`}>
                <span className="truncate">حلقة {ep.episode_number} · {ep.script?.title || '—'}</span>
                <span className={`text-[9px] px-1.5 py-0.5 rounded border ${STAGE_COLOR[ep.stage] || ''}`}>{STAGE_LABEL[ep.stage] || ep.stage}</span>
              </button>
            ))}
          </div>
        )}
      </aside>

      {/* ── CENTER — Episode pane with tabs ─────────────────────── */}
      <main className="flex-1 flex flex-col min-w-0">
        <header className="border-b border-zinc-800 px-6 py-3 flex items-center justify-between bg-[#0e1118]">
          <div className="flex items-center gap-3 min-w-0">
            {activeEpisode ? (
              <>
                <Film className="w-5 h-5 text-amber-400 shrink-0" />
                <div className="min-w-0">
                  <div className="text-sm font-medium truncate">حلقة {activeEpisode.episode_number} · {activeEpisode.script?.title || 'بدون عنوان'}</div>
                  <div className="text-xs text-zinc-500 truncate">{activeEpisode.script?.logline || activeEpisode.brief}</div>
                </div>
              </>
            ) : (
              <div className="text-sm text-zinc-400">
                {activeSeriesId ? series.find((s) => s.id === activeSeriesId)?.title : 'اختر سلسلة من الجنب أو ابدأ شات جديد'}
              </div>
            )}
          </div>
          <div className="flex items-center gap-2">
            {activeEpisode && (
              <span className={`text-xs px-2 py-1 rounded border ${STAGE_COLOR[activeEpisode.stage] || ''}`}>{STAGE_LABEL[activeEpisode.stage]}</span>
            )}
            <button onClick={startNewEpisode}
              className="text-xs px-3 py-1.5 rounded-lg bg-zinc-800 hover:bg-zinc-700 flex items-center gap-1.5" data-testid="new-episode-btn">
              <Plus className="w-3 h-3" /> حلقة جديدة
            </button>
          </div>
        </header>

        {/* Tabs */}
        <div className="border-b border-zinc-800 px-4 flex items-center gap-1 bg-[#0e1118]/60">
          {[
            { id: 'chat',       label: 'محادثة',         icon: <MessageSquare className="w-3.5 h-3.5" /> },
            { id: 'story',      label: 'سيناريو القصة',  icon: <FileText className="w-3.5 h-3.5" /> },
            { id: 'dialogue',   label: 'سيناريو الحوار', icon: <Languages className="w-3.5 h-3.5" /> },
            { id: 'storyboard', label: 'ستوري بورد',    icon: <ImageIcon className="w-3.5 h-3.5" /> },
            { id: 'community',  label: 'المجتمع',        icon: <Users className="w-3.5 h-3.5" /> },
          ].map((t) => (
            <button key={t.id} onClick={() => { setTab(t.id); if (t.id === 'community' && !discoverLoaded) loadDiscover(); }}
              className={`px-3 py-2 text-xs flex items-center gap-1.5 border-b-2 transition ${
                tab === t.id ? 'border-amber-400 text-amber-200' : 'border-transparent text-zinc-400 hover:text-zinc-200'
              }`} data-testid={`tab-${t.id}`}>
              {t.icon} {t.label}
            </button>
          ))}
        </div>

        {/* Tab content */}
        <div className="flex-1 overflow-y-auto" ref={chatScrollRef}>
          {tab === 'chat' && (
            <ChatTab
              activeEpisode={activeEpisode}
              briefInput={briefInput} setBriefInput={setBriefInput}
              busy={busyStage === 'script'} onGenerate={generateScript}
              chatTurns={chatTurns} chatInput={chatInput} setChatInput={setChatInput}
              sendChat={sendChat} chatBusy={chatBusy}
              ownerKeyConfigured={opts.owner_key_configured}
              narrationFile={narrationFile} setNarrationFile={setNarrationFile}
              narrationInputRef={narrationInputRef} uploadNarration={uploadNarration}
              narrationBusy={busyStage === 'narration'}
            />
          )}
          {tab === 'story' && (
            <StoryTab ep={activeEpisode} />
          )}
          {tab === 'dialogue' && (
            <DialogueTab ep={activeEpisode} opts={opts} />
          )}
          {tab === 'storyboard' && (
            <StoryboardTab ep={activeEpisode} api={API} />
          )}
          {tab === 'community' && (
            <CommunityTab feed={discoverFeed} loaded={discoverLoaded} onLike={likeEpisode} onRefresh={loadDiscover} />
          )}

          {/* Sticky action bar (always visible when episode exists) */}
          {activeEpisode && (
            <ActionBar
              ep={activeEpisode} busy={busyStage}
              onStoryboard={generateStoryboard} onApprove={approveEpisode}
              onRender={renderEpisode} onShare={shareEpisode}
              shareData={shareData} downloadAll={downloadAllClips}
            />
          )}
        </div>
      </main>

      {/* ── RIGHT — Settings panel ──────────────────────────────── */}
      <aside className="w-72 border-r border-zinc-800 bg-[#0e1118] p-4 overflow-y-auto shrink-0" data-testid="settings-panel">
        <h3 className="text-sm font-semibold mb-3 flex items-center gap-2"><Settings className="w-4 h-4 text-amber-400" /> الإعدادات</h3>
        <SettingsForm opts={opts} settings={settings} setSettings={setSettings} />
      </aside>

      {/* ── New Series Modal ───────────────────────────────────── */}
      {showNewSeries && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-[#12161e] border border-zinc-800 rounded-2xl p-6 w-full max-w-md" data-testid="new-series-modal">
            <h2 className="text-lg font-semibold mb-4 flex items-center gap-2"><Sparkles className="w-5 h-5 text-amber-400" /> سلسلة فيديو جديدة</h2>
            <div className="space-y-3">
              <div>
                <label className="text-xs text-zinc-400 block mb-1">عنوان السلسلة</label>
                <input value={newSeries.title} onChange={(e) => setNewSeries((s) => ({ ...s, title: e.target.value }))}
                  className="w-full bg-zinc-900 border border-zinc-700 rounded-lg px-3 py-2 text-sm" placeholder="مثلاً: حكاية وادي النور"
                  data-testid="new-series-title-input" />
              </div>
              <div>
                <label className="text-xs text-zinc-400 block mb-1">الستايل البصري (إنجليزي)</label>
                <input value={newSeries.style_direction} onChange={(e) => setNewSeries((s) => ({ ...s, style_direction: e.target.value }))}
                  className="w-full bg-zinc-900 border border-zinc-700 rounded-lg px-3 py-2 text-sm font-mono"
                  placeholder="Cinematic 35mm, warm sepia, soft golden hour" data-testid="new-series-style-input" />
              </div>
              <div>
                <label className="text-xs text-zinc-400 block mb-1">الشخصيات (سطر لكل واحد · الاسم: الوصف)</label>
                <textarea value={newSeries.main_characters} onChange={(e) => setNewSeries((s) => ({ ...s, main_characters: e.target.value }))}
                  className="w-full bg-zinc-900 border border-zinc-700 rounded-lg px-3 py-2 text-sm h-24"
                  placeholder={'سالم: شاب 25، ثوب أبيض\nنورة: 22، حجاب أزرق'} data-testid="new-series-chars-input" />
              </div>
              <div className="flex gap-2 pt-2">
                <button onClick={createSeries} className="flex-1 bg-amber-500 hover:bg-amber-400 text-black font-medium py-2 rounded-lg text-sm" data-testid="create-series-confirm-btn">إنشاء</button>
                <button onClick={() => setShowNewSeries(false)} className="px-4 bg-zinc-800 hover:bg-zinc-700 rounded-lg text-sm" data-testid="create-series-cancel-btn">إلغاء</button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────
// Settings form (right panel)
// ─────────────────────────────────────────────────────────────────────
function SettingsForm({ opts, settings, setSettings }) {
  const update = (k, v) => setSettings((s) => ({ ...s, [k]: v }));
  return (
    <div className="space-y-3 text-xs">
      <Field label="اللغة الأساسية للحوار">
        <select value={settings.language} onChange={(e) => update('language', e.target.value)}
          className="w-full bg-zinc-900 border border-zinc-700 rounded-lg px-2 py-1.5" data-testid="settings-language">
          {(opts.languages || []).map((l) => <option key={l.id} value={l.id}>{l.label}</option>)}
        </select>
      </Field>
      <Field label="ملاحظات على اللهجة (اختياري)">
        <input value={settings.dialect_notes} onChange={(e) => update('dialect_notes', e.target.value)}
          placeholder="مثلاً: لهجة نجدية كلاسيكية" className="w-full bg-zinc-900 border border-zinc-700 rounded-lg px-2 py-1.5"
          data-testid="settings-dialect" />
      </Field>
      <Field label="ترجمة مكتوبة (اختياري)">
        <select value={settings.subtitle_language} onChange={(e) => update('subtitle_language', e.target.value)}
          className="w-full bg-zinc-900 border border-zinc-700 rounded-lg px-2 py-1.5" data-testid="settings-subtitle">
          <option value="">بدون ترجمة</option>
          {(opts.languages || []).map((l) => <option key={l.id} value={l.id}>{l.label}</option>)}
        </select>
      </Field>
      <Field label="نوع الرسم / الستايل">
        <select value={settings.art_style} onChange={(e) => update('art_style', e.target.value)}
          className="w-full bg-zinc-900 border border-zinc-700 rounded-lg px-2 py-1.5" data-testid="settings-style">
          {(opts.art_styles || []).map((s) => <option key={s.id} value={s.id}>{s.label}</option>)}
        </select>
      </Field>
      <Field label="نوع الفيديو">
        <select value={settings.genre} onChange={(e) => update('genre', e.target.value)}
          className="w-full bg-zinc-900 border border-zinc-700 rounded-lg px-2 py-1.5" data-testid="settings-genre">
          {(opts.genres || []).map((g) => <option key={g.id} value={g.id}>{g.label}</option>)}
        </select>
      </Field>
      <Field label="نسبة العرض (Aspect)">
        <select value={settings.aspect_ratio} onChange={(e) => update('aspect_ratio', e.target.value)}
          className="w-full bg-zinc-900 border border-zinc-700 rounded-lg px-2 py-1.5" data-testid="settings-aspect">
          {(opts.aspect_ratios || []).map((a) => <option key={a.id} value={a.id}>{a.label}</option>)}
        </select>
      </Field>
      <Field label="جنس الصوت الرئيسي">
        <select value={settings.voice_gender} onChange={(e) => update('voice_gender', e.target.value)}
          className="w-full bg-zinc-900 border border-zinc-700 rounded-lg px-2 py-1.5" data-testid="settings-voice">
          {(opts.voice_genders || []).map((v) => <option key={v.id} value={v.id}>{v.label}</option>)}
        </select>
      </Field>
      <div className="grid grid-cols-2 gap-2">
        <Field label="عدد اللقطات">
          <input type="number" min="1" max="12" value={settings.shots} onChange={(e) => update('shots', e.target.value)}
            className="w-full bg-zinc-900 border border-zinc-700 rounded-lg px-2 py-1.5" data-testid="settings-shots" />
        </Field>
        <Field label="مدة كل لقطة (ث)">
          <select value={settings.shot_duration} onChange={(e) => update('shot_duration', e.target.value)}
            className="w-full bg-zinc-900 border border-zinc-700 rounded-lg px-2 py-1.5" data-testid="settings-shot-duration">
            <option value="4">4ث · 8 نقاط</option>
            <option value="8">8ث · 14 نقطة</option>
            <option value="12">12ث · 20 نقطة</option>
          </select>
        </Field>
      </div>
      <Field label="توجيهات إضافية للذكاء (اختياري)">
        <textarea value={settings.extra_directives} onChange={(e) => update('extra_directives', e.target.value)}
          className="w-full bg-zinc-900 border border-zinc-700 rounded-lg px-2 py-1.5 h-16"
          placeholder="مثلاً: ركّز على لقطات قريبة، أو تجنّب الأماكن المغلقة..." data-testid="settings-directives" />
      </Field>
      <div className="text-[10px] text-zinc-500 pt-2 border-t border-zinc-800">
        💡 الذكاء يستخدم مفتاحك الخاص في OpenAI، لا يخصم من المنصة.
      </div>
    </div>
  );
}

function Field({ label, children }) {
  return (
    <div>
      <label className="text-[10px] text-zinc-400 block mb-1">{label}</label>
      {children}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────
// Tab: Chat (free conversation + brief input)
// ─────────────────────────────────────────────────────────────────────
function ChatTab({ activeEpisode, briefInput, setBriefInput, busy, onGenerate,
                  chatTurns, chatInput, setChatInput, sendChat, chatBusy, ownerKeyConfigured,
                  narrationFile, setNarrationFile, narrationInputRef, uploadNarration, narrationBusy }) {
  return (
    <div className="max-w-3xl mx-auto p-6 space-y-5">
      {!activeEpisode && (
        <>
        <div className="bg-[#12161e] border border-zinc-800 rounded-2xl p-5">
          <h2 className="text-base font-semibold mb-1 flex items-center gap-2"><Sparkles className="w-4 h-4 text-amber-400" /> ابدأ حلقة جديدة</h2>
          <p className="text-xs text-zinc-400 mb-3">اكتب الفكرة، اضبط الإعدادات من الجنب الأيمن، اضغط ولّد السيناريو.
            <span className="text-emerald-400"> (مجاناً، لا خصم)</span></p>
          <textarea value={briefInput} onChange={(e) => setBriefInput(e.target.value)}
            className="w-full bg-zinc-900 border border-zinc-700 rounded-lg px-3 py-2 text-sm h-32 mb-3"
            placeholder="حلقة 1 — سالم يبدأ رحلته نحو وادي النور..." data-testid="brief-input" />
          <button onClick={onGenerate} disabled={busy || !briefInput.trim() || !ownerKeyConfigured}
            className="w-full bg-amber-500 hover:bg-amber-400 disabled:opacity-50 text-black font-medium py-2.5 rounded-lg text-sm flex items-center justify-center gap-2"
            data-testid="generate-script-btn">
            {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
            {ownerKeyConfigured ? 'ولّد السيناريو' : 'أضف مفتاحك أولاً'}
          </button>
        </div>

        <div className="bg-gradient-to-br from-indigo-500/10 to-violet-500/10 border border-indigo-500/30 rounded-2xl p-5" data-testid="narration-upload-card">
          <h2 className="text-base font-semibold mb-1 flex items-center gap-2">
            <Upload className="w-4 h-4 text-indigo-300" /> رفع تسجيل صوتك (للقصص الواقعية)
          </h2>
          <p className="text-xs text-zinc-300 mb-3 leading-6">
            لو عندك راوي بصوتك أو قصة مسجّلة، ارفعها هنا. الذكاء يفرّغ الصوت (Whisper)
            ثم يقسّم النص للقطات فيلمية واقعية ١٠٠٪ تتطابق مع كلامك. الستايل الافتراضي
            <b className="text-amber-300"> "واقعي تماماً"</b> — ولا فرق عن لقطات فيلم حقيقي.
          </p>
          <input ref={narrationInputRef} type="file" accept="audio/*,video/*"
            onChange={(e) => setNarrationFile(e.target.files?.[0] || null)}
            className="block w-full text-xs text-zinc-300 file:bg-indigo-500 file:text-white file:px-3 file:py-1.5 file:rounded-md file:border-0 file:mr-3 mb-3"
            data-testid="narration-file-input" />
          {narrationFile && (
            <div className="text-[11px] text-zinc-400 mb-2 flex items-center gap-2">
              <span className="bg-zinc-800 px-2 py-1 rounded font-mono">{narrationFile.name}</span>
              <span>{(narrationFile.size / 1024 / 1024).toFixed(2)} MB</span>
            </div>
          )}
          <button onClick={uploadNarration} disabled={narrationBusy || !narrationFile || !ownerKeyConfigured}
            className="w-full bg-indigo-500 hover:bg-indigo-400 disabled:opacity-50 text-white font-medium py-2.5 rounded-lg text-sm flex items-center justify-center gap-2"
            data-testid="upload-narration-btn">
            {narrationBusy ? <Loader2 className="w-4 h-4 animate-spin" /> : <Upload className="w-4 h-4" />}
            رفع وتحويل لفيلم واقعي
          </button>
          <div className="text-[10px] text-zinc-500 mt-2 leading-5">
            صيغ مدعومة: mp3, m4a, wav, mp4 · حد أقصى 25MB · Whisper يستخدم مفتاحك الخاص.
          </div>
        </div>
        </>
      )}

      <div className="bg-[#12161e] border border-zinc-800 rounded-2xl p-5">
        <div className="text-sm font-semibold mb-3 flex items-center gap-2"><MessageSquare className="w-4 h-4 text-amber-400" /> محادثة استشارية</div>
        <div className="space-y-3 max-h-80 overflow-y-auto mb-3 pr-1">
          {chatTurns.length === 0 && (
            <div className="text-xs text-zinc-500 text-center py-6">اسأل عن أفكار، ستايلات، طول لقطات…</div>
          )}
          {chatTurns.map((t, i) => (
            <div key={i} className="text-sm">
              <div className={`text-[10px] mb-0.5 ${t.role === 'user' ? 'text-amber-400' : 'text-emerald-400'}`}>
                {t.role === 'user' ? 'أنت' : 'زيتاكس فيديو'} {t.cached && <span className="text-zinc-500">· من الذاكرة</span>}
              </div>
              <div className="whitespace-pre-wrap leading-6 text-zinc-200">{t.content}</div>
              {t.redirect && (
                <a href={t.redirect.to_route} className="text-xs text-sky-400 underline mt-1 inline-block">{t.redirect.to_label} ←</a>
              )}
            </div>
          ))}
        </div>
        <div className="flex gap-2">
          <input value={chatInput} onChange={(e) => setChatInput(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && sendChat()}
            disabled={chatBusy} className="flex-1 bg-zinc-900 border border-zinc-700 rounded-lg px-3 py-2 text-sm"
            placeholder="اكتب سؤالك…" data-testid="chat-input" />
          <button onClick={sendChat} disabled={chatBusy || !chatInput.trim()}
            className="px-4 bg-amber-500 hover:bg-amber-400 disabled:opacity-50 text-black font-medium rounded-lg text-sm" data-testid="chat-send-btn">
            {chatBusy ? <Loader2 className="w-4 h-4 animate-spin" /> : 'إرسال'}
          </button>
        </div>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────
// Tab: Story Scenario — high-level beat sheet
// ─────────────────────────────────────────────────────────────────────
function StoryTab({ ep }) {
  if (!ep || !ep.script) {
    return <div className="p-8 text-center text-sm text-zinc-500">ولّد السيناريو أولاً من تبويب المحادثة.</div>;
  }
  const s = ep.script;
  return (
    <div className="max-w-3xl mx-auto p-6" data-testid="story-tab">
      <div className="bg-[#12161e] border border-zinc-800 rounded-2xl p-5 mb-4">
        <div className="text-xs text-zinc-500 mb-1">العنوان</div>
        <h2 className="text-2xl font-semibold mb-2">{s.title}</h2>
        <div className="text-sm text-zinc-300 leading-7">{s.logline}</div>
      </div>
      {(s.characters || []).length > 0 && (
        <div className="bg-[#12161e] border border-zinc-800 rounded-2xl p-5 mb-4">
          <div className="text-xs text-zinc-500 mb-2">الشخصيات</div>
          <div className="space-y-2">
            {s.characters.map((c, i) => (
              <div key={i} className="text-sm">
                <span className="font-semibold text-amber-200">{c.name}</span>
                <span className="text-zinc-400"> — {c.desc}</span>
              </div>
            ))}
          </div>
        </div>
      )}
      <div className="bg-[#12161e] border border-zinc-800 rounded-2xl p-5 mb-4">
        <div className="text-xs text-zinc-500 mb-2">الستايل البصري</div>
        <div className="text-xs font-mono text-zinc-300 leading-6">{s.style}</div>
      </div>
      <div className="bg-[#12161e] border border-zinc-800 rounded-2xl p-5">
        <div className="text-xs text-zinc-500 mb-2">المشاهد (سيناريو القصة)</div>
        <ol className="space-y-3">
          {(ep.shots || []).map((sh, i) => (
            <li key={i} className="border-b border-zinc-800 pb-3 last:border-0">
              <div className="text-sm font-medium text-zinc-100">لقطة {sh.n} · {sh.title_ar}</div>
              <div className="text-xs text-zinc-400 leading-6 mt-1">{sh.scenario_ar || sh.narration_ar}</div>
            </li>
          ))}
        </ol>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────
// Tab: Dialogue — line-by-line with subtitle column
// ─────────────────────────────────────────────────────────────────────
function DialogueTab({ ep, opts }) {
  if (!ep) return <div className="p-8 text-center text-sm text-zinc-500">لا توجد حلقة فعّالة.</div>;
  const lang = (opts.languages || []).find((l) => l.id === ep.language) || { label: ep.language || '' };
  const sub = (opts.languages || []).find((l) => l.id === ep.subtitle_language);
  return (
    <div className="max-w-4xl mx-auto p-6" data-testid="dialogue-tab">
      <div className="bg-[#12161e] border border-zinc-800 rounded-2xl p-5">
        <div className="text-xs text-zinc-500 mb-3 flex items-center gap-2">
          <Languages className="w-3.5 h-3.5" /> سيناريو الحوار · لغة: <b className="text-zinc-200">{lang.label}</b>
          {sub && <span>· ترجمة: <b className="text-zinc-200">{sub.label}</b></span>}
        </div>
        <table className="w-full text-sm">
          <thead className="text-xs text-zinc-500 border-b border-zinc-800">
            <tr>
              <th className="text-right py-2 px-2 w-10">#</th>
              <th className="text-right py-2 px-2 w-32">المتحدث</th>
              <th className="text-right py-2 px-2">الحوار ({lang.label})</th>
              {sub && <th className="text-right py-2 px-2">الترجمة ({sub.label})</th>}
            </tr>
          </thead>
          <tbody>
            {(ep.shots || []).map((sh, i) => (
              <tr key={i} className="border-b border-zinc-800 last:border-0 align-top">
                <td className="py-3 px-2 text-zinc-500">{sh.n}</td>
                <td className="py-3 px-2 text-amber-200 text-xs">{sh.dialogue_speaker || 'راوي'}</td>
                <td className="py-3 px-2 text-zinc-100 leading-7">{sh.dialogue || '—'}</td>
                {sub && <td className="py-3 px-2 text-zinc-400 leading-7">{sh.subtitle_translation || '—'}</td>}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────
// Tab: Storyboard grid
// ─────────────────────────────────────────────────────────────────────
function StoryboardTab({ ep, api }) {
  if (!ep) return <div className="p-8 text-center text-sm text-zinc-500">—</div>;
  const shots = ep.shots || [];
  const final = ep.final_clips || [];
  return (
    <div className="max-w-5xl mx-auto p-6" data-testid="storyboard-tab">
      <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
        {shots.map((shot, i) => {
          const clip = final.find((c) => c.n === shot.n);
          const preview = shot.preview_url ? `${api}${shot.preview_url}` : null;
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
                <div className="absolute top-1 right-1 bg-black/80 text-zinc-300 text-[10px] px-1.5 py-0.5 rounded">#{shot.n} · {shot.duration || 8}s</div>
              </div>
              <div className="p-2">
                <div className="text-xs font-medium text-zinc-200 mb-1 truncate">{shot.title_ar}</div>
                {shot.dialogue && (<div className="text-[10px] text-zinc-400 line-clamp-2">{shot.dialogue}</div>)}
              </div>
            </div>
          );
        })}
      </div>
      {shots.length === 0 && (<div className="text-sm text-zinc-500 text-center py-12">ولّد ستوري بورد من الأسفل لمعاينة كل لقطة.</div>)}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────
// Action bar (sticky bottom)
// ─────────────────────────────────────────────────────────────────────
function ActionBar({ ep, busy, onStoryboard, onApprove, onRender, onShare, shareData, downloadAll }) {
  return (
    <div className="sticky bottom-0 bg-[#0e1118]/95 backdrop-blur border-t border-zinc-800 px-6 py-3" data-testid="action-bar">
      {ep.stage === 'script' && (
        <div className="flex items-center justify-between gap-3">
          <div className="text-xs text-zinc-400">تكلفة متوقعة: <b className="text-amber-300">{ep.estimated_cost}</b> نقطة · لا خصم</div>
          <button onClick={onStoryboard} disabled={busy === 'storyboard'}
            className="bg-amber-500 hover:bg-amber-400 disabled:opacity-50 text-black font-medium px-5 py-2 rounded-lg text-sm flex items-center gap-2" data-testid="storyboard-btn">
            {busy === 'storyboard' ? <Loader2 className="w-4 h-4 animate-spin" /> : <ImageIcon className="w-4 h-4" />}
            ولّد معاينة الستوري بورد (مجاناً)
          </button>
        </div>
      )}
      {ep.stage === 'storyboard' && (
        <div className="flex items-center justify-between gap-3 flex-wrap">
          <div className="text-xs text-zinc-400">راجع الصور. <b className="text-amber-300">{ep.estimated_cost}</b> نقطة لو وافقت.</div>
          <div className="flex items-center gap-2">
            <button onClick={onStoryboard} disabled={busy === 'storyboard'}
              className="bg-zinc-800 hover:bg-zinc-700 text-zinc-200 px-3 py-2 rounded-lg text-xs flex items-center gap-1.5" data-testid="regen-storyboard-btn">
              <RotateCcw className="w-3.5 h-3.5" /> أعد التوليد
            </button>
            <button onClick={onApprove} disabled={busy === 'approve'}
              className="bg-emerald-500 hover:bg-emerald-400 disabled:opacity-50 text-black font-medium px-5 py-2 rounded-lg text-sm flex items-center gap-2" data-testid="approve-btn">
              {busy === 'approve' ? <Loader2 className="w-4 h-4 animate-spin" /> : <Check className="w-4 h-4" />} موافق ابدأ الإنتاج
            </button>
          </div>
        </div>
      )}
      {ep.stage === 'approved' && (
        <div className="flex items-center justify-between gap-3">
          <div className="text-xs text-zinc-400">جاهز. اضغط الإنتاج لخصم <b className="text-amber-300">{ep.estimated_cost}</b> نقطة.</div>
          <button onClick={onRender} disabled={busy === 'render'}
            className="bg-emerald-500 hover:bg-emerald-400 disabled:opacity-50 text-black font-medium px-5 py-2 rounded-lg text-sm flex items-center gap-2" data-testid="render-btn">
            {busy === 'render' ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />} ابدأ الإنتاج النهائي
          </button>
        </div>
      )}
      {ep.stage === 'rendered' && (
        <SharePanel ep={ep} shareData={shareData} onShare={onShare} busy={busy} downloadAll={downloadAll} />
      )}
      {busy === 'render' && (
        <div className="mt-3 text-xs text-amber-300 flex items-center gap-2">
          <Loader2 className="w-3.5 h-3.5 animate-spin" />
          جاري الإنتاج عبر Sora 2 — دقيقتين/لقطة. لا تغلق الصفحة.
        </div>
      )}
      {!['script', 'storyboard', 'approved', 'rendered'].includes(ep.stage) && (
        <div className="text-xs text-zinc-500 flex items-center gap-2"><AlertCircle className="w-3.5 h-3.5" /> مرحلة غير معروفة: {ep.stage}</div>
      )}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────
// Tab: Community / Discover (feed of public episodes)
// ─────────────────────────────────────────────────────────────────────
function CommunityTab({ feed, loaded, onLike, onRefresh }) {
  return (
    <div className="max-w-5xl mx-auto p-6" data-testid="community-tab">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h2 className="text-lg font-semibold flex items-center gap-2">
            <Users className="w-5 h-5 text-amber-400" /> إبداعات المجتمع
          </h2>
          <p className="text-xs text-zinc-500 mt-1">كل اللي ينشره المستخدمون من حلقات على منصة زيتاكس فقط — لا محتوى خارجي.</p>
        </div>
        <button onClick={onRefresh} className="bg-zinc-800 hover:bg-zinc-700 text-xs px-3 py-1.5 rounded-lg flex items-center gap-1.5" data-testid="refresh-community-btn">
          <RotateCcw className="w-3.5 h-3.5" /> تحديث
        </button>
      </div>

      {!loaded && (<div className="text-center text-sm text-zinc-500 py-12">جاري التحميل…</div>)}
      {loaded && feed.length === 0 && (
        <div className="text-center text-sm text-zinc-500 py-12 bg-[#12161e] border border-zinc-800 rounded-2xl">
          ما فيه حلقات منشورة بعد. كن أول واحد يشارك إبداعه.
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {feed.map((ep) => (
          <div key={ep.id} className="bg-[#12161e] border border-zinc-800 rounded-2xl overflow-hidden hover:border-amber-500/40 transition" data-testid={`community-card-${ep.id}`}>
            <div className={`bg-zinc-900 ${ep.aspect_ratio === '9x16' ? 'aspect-[9/16]' : ep.aspect_ratio === '1x1' ? 'aspect-square' : 'aspect-video'}`}>
              {ep.first_clip_url ? (
                <video src={ep.first_clip_url} controls className="w-full h-full object-cover" />
              ) : (
                <div className="w-full h-full flex items-center justify-center text-zinc-600">
                  <Film className="w-12 h-12" />
                </div>
              )}
            </div>
            <div className="p-3 space-y-2">
              <div className="text-sm font-medium truncate">{ep.title}</div>
              <div className="text-[11px] text-zinc-400 line-clamp-2 leading-5">{ep.logline}</div>
              <div className="flex items-center justify-between text-[10px] text-zinc-500 pt-2 border-t border-zinc-800">
                <span>بواسطة <b className="text-zinc-300">{ep.author}</b></span>
                <div className="flex items-center gap-2">
                  <span className="flex items-center gap-1"><Eye className="w-3 h-3" /> {ep.views || 0}</span>
                  <button onClick={() => onLike(ep.id)} className="flex items-center gap-1 hover:text-rose-400 transition" data-testid={`like-${ep.id}`}>
                    <Heart className="w-3 h-3" /> {ep.likes || 0}
                  </button>
                </div>
              </div>
              <a href={ep.public_url} target="_blank" rel="noopener noreferrer"
                className="block text-center text-[11px] bg-zinc-800 hover:bg-zinc-700 py-1.5 rounded text-zinc-200">
                شاهد كامل ←
              </a>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function SharePanel({ ep, shareData, onShare, busy, downloadAll }) {
  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text).then(() => toast.success('تم النسخ'));
  };
  return (
    <div className="space-y-3" data-testid="share-panel">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div className="flex items-center gap-2 text-sm">
          <Check className="w-4 h-4 text-emerald-400" />
          <span className="text-emerald-300 font-medium">اكتمل الإنتاج</span>
          <span className="text-zinc-500">· {ep.credits_charged} نقطة · {(ep.final_clips || []).length} لقطة</span>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={downloadAll}
            className="bg-zinc-800 hover:bg-zinc-700 text-zinc-200 px-3 py-1.5 rounded-lg text-xs flex items-center gap-1.5"
            data-testid="download-all-btn">
            <Download className="w-3.5 h-3.5" /> تنزيل الكل
          </button>
          {!shareData && (
            <button onClick={onShare} disabled={busy === 'share'}
              className="bg-sky-500 hover:bg-sky-400 disabled:opacity-50 text-white font-medium px-4 py-1.5 rounded-lg text-xs flex items-center gap-1.5"
              data-testid="share-btn">
              {busy === 'share' ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Share2 className="w-3.5 h-3.5" />}
              أنشئ رابط مشاركة
            </button>
          )}
        </div>
      </div>

      {shareData && (
        <div className="bg-[#12161e] border border-zinc-800 rounded-xl p-3 space-y-3">
          <div className="flex items-center gap-2">
            <input readOnly value={shareData.full_url} className="flex-1 bg-zinc-900 border border-zinc-700 rounded px-2 py-1 text-xs font-mono" data-testid="share-url-input" />
            <button onClick={() => copyToClipboard(shareData.full_url)} className="bg-zinc-800 hover:bg-zinc-700 p-1.5 rounded" data-testid="copy-share-url"><Copy className="w-3.5 h-3.5" /></button>
          </div>
          <div>
            <div className="text-[10px] text-zinc-500 mb-1.5">انشر على:</div>
            <div className="flex flex-wrap gap-1.5">
              {SOCIAL_PLATFORMS.map((p) => (
                <div key={p.id} className={`border rounded-lg p-2 text-xs flex flex-col gap-1.5 min-w-[140px] ${p.color}`}>
                  <div className="flex items-center justify-between">
                    <b>{p.label}</b>
                    <a href={p.url} target="_blank" rel="noopener noreferrer" className="underline text-[10px]" data-testid={`open-${p.id}`}>افتح →</a>
                  </div>
                  <button onClick={() => copyToClipboard(shareData.captions[p.id] || '')}
                    className="bg-black/30 hover:bg-black/50 text-zinc-200 px-2 py-1 rounded text-[10px] flex items-center justify-center gap-1"
                    data-testid={`copy-caption-${p.id}`}>
                    <Copy className="w-3 h-3" /> انسخ النص + الهاشتاقات
                  </button>
                </div>
              ))}
            </div>
            <div className="text-[10px] text-zinc-500 mt-2 leading-5">
              💡 نزّل المقطع من <b>تنزيل الكل</b>، افتح المنصة، الصق الكابشن. التحميل التلقائي مباشرة عبر API بيوصل قريباً.
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
