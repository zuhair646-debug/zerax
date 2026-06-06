import React, { useState, useEffect } from 'react';
import {
  Sparkles, X, Mic, Map, Network, Store, Package, Film,
  Download, Loader2, CheckCircle2, AlertCircle, Upload, Star
} from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;

const TABS = [
  { id: 'voice',       label: 'Voice Acting',  icon: Mic,     desc: 'تحويل حوار لصوت احترافي' },
  { id: 'level',       label: 'Level Design',  icon: Map,     desc: 'توليد خرائط مستويات' },
  { id: 'sprite',      label: 'Sprite Sheets', icon: Film,    desc: 'إطارات أنيميشن جاهزة للمحركات' },
  { id: 'multiplayer', label: 'Multiplayer',   icon: Network, desc: 'كود Multiplayer جاهز' },
  { id: 'marketplace', label: 'LoRA Market',   icon: Store,   desc: 'مكتبة أنماط مشتركة' },
  { id: 'unity',       label: 'Unity SDK',     icon: Package, desc: 'تصدير لـUnity' },
];

export default function ProStudioTools({ projectId, projectTitle = '', accentColor = 'amber' }) {
  const token = (typeof localStorage !== 'undefined' && localStorage.getItem('token')) || '';
  const [open, setOpen] = useState(false);
  const [tab, setTab] = useState('voice');
  const accent = accentColor === 'amber' ? 'amber' : 'blue';

  return (
    <>
      <button
        onClick={() => setOpen(true)}
        data-testid="pro-studio-btn"
        className={`text-xs font-bold px-3 py-1.5 rounded-lg bg-gradient-to-r from-${accent}-500 to-orange-500 hover:scale-105 text-black flex items-center gap-1.5 shadow-lg transition-transform`}
      >
        <Sparkles className="w-3.5 h-3.5" />
        Pro Studio Tools
      </button>

      {open && (
        <div className="fixed inset-0 z-50 bg-black/85 backdrop-blur-md flex items-center justify-center p-3"
             onClick={() => setOpen(false)}
             data-testid="pro-studio-modal">
          <div className={`bg-zinc-950 border-2 border-${accent}-500/40 rounded-2xl max-w-5xl w-full max-h-[92vh] overflow-hidden flex flex-col shadow-2xl`}
               onClick={(e) => e.stopPropagation()}>
            {/* Header */}
            <div className={`px-5 py-4 border-b border-${accent}-500/30 bg-gradient-to-r from-${accent}-500/15 to-orange-500/10 flex items-center justify-between`}>
              <div>
                <h2 className={`text-base font-bold text-${accent}-200 flex items-center gap-2`}>
                  <Sparkles className="w-5 h-5" /> Pro Studio Tools
                </h2>
                <p className="text-[11px] text-zinc-400">{projectTitle || 'المشروع'} · أدوات AAA لتطوير لعبة كاملة</p>
              </div>
              <button onClick={() => setOpen(false)} className="text-zinc-400 hover:text-white">
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Tabs */}
            <div className="flex border-b border-white/10 overflow-x-auto bg-black/40">
              {TABS.map(t => (
                <button
                  key={t.id}
                  onClick={() => setTab(t.id)}
                  data-testid={`pro-tab-${t.id}`}
                  className={`px-4 py-3 text-xs font-bold whitespace-nowrap flex items-center gap-1.5 border-b-2 transition-colors ${
                    tab === t.id
                      ? `border-${accent}-400 text-${accent}-200 bg-${accent}-500/10`
                      : 'border-transparent text-zinc-400 hover:text-white hover:bg-white/5'
                  }`}
                >
                  <t.icon className="w-3.5 h-3.5" />
                  {t.label}
                </button>
              ))}
            </div>

            {/* Body */}
            <div className="flex-1 overflow-y-auto p-5">
              {tab === 'voice'       && <VoicePanel       projectId={projectId} token={token} accent={accent} />}
              {tab === 'level'       && <LevelPanel       projectId={projectId} token={token} accent={accent} />}
              {tab === 'sprite'      && <SpritePanel      projectId={projectId} token={token} accent={accent} />}
              {tab === 'multiplayer' && <MultiplayerPanel projectId={projectId} token={token} accent={accent} />}
              {tab === 'marketplace' && <MarketplacePanel projectId={projectId} token={token} accent={accent} />}
              {tab === 'unity'       && <UnityPanel       projectId={projectId} token={token} accent={accent} />}
            </div>
          </div>
        </div>
      )}
    </>
  );
}

// ═════════════════════════════════════════════════════════════════════════
// VOICE PANEL
// ═════════════════════════════════════════════════════════════════════════
function VoicePanel({ projectId, token, accent }) {
  const [text, setText] = useState('');
  const [character, setCharacter] = useState('warrior');
  const [busy, setBusy] = useState(false);
  const [audio, setAudio] = useState(null);
  const [err, setErr] = useState('');

  const generate = async () => {
    setErr(''); setAudio(null); setBusy(true);
    try {
      // Send via chat with VOICE tag — auto-routed through parser
      const r = await fetch(`${API}/api/games/project/${projectId}/chat`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: `<<VOICE: ${text} | character: ${character}>>` }),
      });
      if (!r.ok) throw new Error('فشل الإرسال');
      // The chat endpoint streams; we poll the project for the new asset
      // Simpler: just inform user to check chat
      setAudio({ pending: true });
    } catch (e) {
      setErr(e.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-4 text-right">
      <div>
        <h3 className={`text-${accent}-200 font-bold mb-1`}>🎙️ Voice Acting AI</h3>
        <p className="text-xs text-zinc-400">حوّل أي حوار لصوت احترافي بصوت شخصية معينة. يستخدم ElevenLabs (لو فعّلت المفتاح) أو OpenAI TTS كـbackup.</p>
      </div>
      <div>
        <label className="text-xs text-zinc-300 block mb-1">نص الحوار</label>
        <textarea
          rows={3}
          value={text}
          onChange={e => setText(e.target.value)}
          data-testid="voice-text-input"
          className="w-full bg-black/40 border border-white/10 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-amber-400"
          placeholder="مرحباً أيها المغامر! هل أنت مستعد للقتال؟"
        />
      </div>
      <div>
        <label className="text-xs text-zinc-300 block mb-1">نوع الشخصية</label>
        <select
          value={character}
          onChange={e => setCharacter(e.target.value)}
          data-testid="voice-character-select"
          className="w-full bg-black/40 border border-white/10 rounded-lg px-3 py-2 text-sm"
        >
          <option value="warrior">محارب (Warrior)</option>
          <option value="villain">شرير (Villain)</option>
          <option value="merchant">تاجر (Merchant)</option>
          <option value="elder">حكيم (Elder)</option>
          <option value="child">طفل (Child)</option>
          <option value="narrator">راوي (Narrator)</option>
        </select>
      </div>
      {err && <div className="text-xs text-rose-300 bg-rose-500/10 p-2 rounded">{err}</div>}
      {audio?.pending && (
        <div className="text-xs text-emerald-300 bg-emerald-500/10 p-2 rounded flex items-start gap-2">
          <CheckCircle2 className="w-4 h-4 shrink-0 mt-0.5" />
          <span>تم إرسال الطلب — راح يظهر الصوت في المحادثة خلال 5-10 ثواني.</span>
        </div>
      )}
      <button
        onClick={generate}
        disabled={busy || !text.trim() || !projectId}
        data-testid="voice-generate-btn"
        className={`text-xs font-bold px-4 py-2 rounded-lg bg-${accent}-500 hover:bg-${accent}-400 text-black flex items-center gap-2 disabled:opacity-40`}
      >
        {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : <Mic className="w-4 h-4" />}
        {busy ? 'يولّد…' : 'ولّد الصوت'}
      </button>
    </div>
  );
}

// ═════════════════════════════════════════════════════════════════════════
// LEVEL DESIGN PANEL
// ═════════════════════════════════════════════════════════════════════════
function LevelPanel({ projectId, token, accent }) {
  const [desc, setDesc] = useState('');
  const [size, setSize] = useState(20);
  const [style, setStyle] = useState('top-down');
  const [busy, setBusy] = useState(false);
  const [level, setLevel] = useState(null);
  const [err, setErr] = useState('');

  const generate = async () => {
    setErr(''); setLevel(null); setBusy(true);
    try {
      const r = await fetch(`${API}/api/games/project/${projectId}/generate-level`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({ description: desc, size, style }),
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || 'فشل');
      setLevel(d.level);
    } catch (e) { setErr(e.message); }
    finally { setBusy(false); }
  };

  return (
    <div className="space-y-4 text-right">
      <div>
        <h3 className={`text-${accent}-200 font-bold mb-1`}>🗺️ Level Design Generator</h3>
        <p className="text-xs text-zinc-400">صف المستوى بالكلمات، Claude يصمم لك tilemap كامل مع spawn points و enemies و objectives — جاهز للاستيراد في Unity أو HTML5.</p>
      </div>
      <textarea
        rows={3}
        value={desc}
        onChange={e => setDesc(e.target.value)}
        data-testid="level-desc-input"
        className="w-full bg-black/40 border border-white/10 rounded-lg px-3 py-2 text-sm"
        placeholder="قرية في الصحراء، فيها 3 محلات تجارية، عدو في منتصف الخريطة، وكنز في الزاوية الشمالية الشرقية"
      />
      <div className="grid grid-cols-2 gap-2">
        <div>
          <label className="text-xs text-zinc-300 block mb-1">حجم الشبكة</label>
          <select value={size} onChange={e => setSize(Number(e.target.value))}
                  data-testid="level-size-select"
                  className="w-full bg-black/40 border border-white/10 rounded-lg px-3 py-2 text-sm">
            <option value={15}>15 x 15</option>
            <option value={20}>20 x 20</option>
            <option value={30}>30 x 30</option>
            <option value={40}>40 x 40</option>
          </select>
        </div>
        <div>
          <label className="text-xs text-zinc-300 block mb-1">المنظور</label>
          <select value={style} onChange={e => setStyle(e.target.value)}
                  data-testid="level-style-select"
                  className="w-full bg-black/40 border border-white/10 rounded-lg px-3 py-2 text-sm">
            <option value="top-down">Top-down</option>
            <option value="side-scroller">Side-scroller</option>
            <option value="isometric">Isometric</option>
          </select>
        </div>
      </div>
      {err && <div className="text-xs text-rose-300 bg-rose-500/10 p-2 rounded">{err}</div>}
      {level && (
        <div className="bg-black/40 border border-emerald-500/30 rounded-lg p-3 space-y-2">
          <div className={`text-xs text-${accent}-200 font-bold`}>✅ {level.name} · {level.size?.w}x{level.size?.h}</div>
          <pre className="text-[10px] text-emerald-200 font-mono overflow-x-auto leading-tight" dir="ltr">
            {(level.grid || []).join('\n')}
          </pre>
          <div className="text-[11px] text-zinc-300">{level.lore}</div>
          <div className="text-[10px] text-zinc-400">
            🎯 {(level.objectives || []).join(' · ')}
          </div>
        </div>
      )}
      <button onClick={generate} disabled={busy || !desc.trim() || !projectId}
              data-testid="level-generate-btn"
              className={`text-xs font-bold px-4 py-2 rounded-lg bg-${accent}-500 hover:bg-${accent}-400 text-black flex items-center gap-2 disabled:opacity-40`}>
        {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : <Map className="w-4 h-4" />}
        {busy ? 'يصمم…' : 'صمّم المستوى'}
      </button>
    </div>
  );
}

// ═════════════════════════════════════════════════════════════════════════
// SPRITE SHEET PANEL
// ═════════════════════════════════════════════════════════════════════════
function SpritePanel({ projectId, token, accent }) {
  const [character, setCharacter] = useState('');
  const [action, setAction] = useState('walk');
  const [frames, setFrames] = useState(8);
  const [busy, setBusy] = useState(false);
  const [sheet, setSheet] = useState(null);
  const [err, setErr] = useState('');

  const generate = async () => {
    setErr(''); setSheet(null); setBusy(true);
    try {
      const r = await fetch(`${API}/api/games/project/${projectId}/sprite-sheet`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({ character, action, frames }),
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || 'فشل');
      setSheet(d.sprite_sheet);
    } catch (e) { setErr(e.message); }
    finally { setBusy(false); }
  };

  return (
    <div className="space-y-4 text-right">
      <div>
        <h3 className={`text-${accent}-200 font-bold mb-1`}>🎞️ Sprite Sheet Generator</h3>
        <p className="text-xs text-zinc-400">يولّد 8 إطارات للشخصية في نفس الـpose family — جاهزة للاستخدام في Unity, Godot, Phaser. كل إطار 512x512.</p>
      </div>
      <input
        type="text"
        value={character}
        onChange={e => setCharacter(e.target.value)}
        data-testid="sprite-character-input"
        placeholder="ساحر كبير بعباءة زرقاء"
        className="w-full bg-black/40 border border-white/10 rounded-lg px-3 py-2 text-sm"
      />
      <div className="grid grid-cols-2 gap-2">
        <select value={action} onChange={e => setAction(e.target.value)}
                data-testid="sprite-action-select"
                className="bg-black/40 border border-white/10 rounded-lg px-3 py-2 text-sm">
          <option value="idle">Idle (وقوف)</option>
          <option value="walk">Walk (مشي)</option>
          <option value="attack">Attack (هجوم)</option>
          <option value="death">Death (موت)</option>
        </select>
        <select value={frames} onChange={e => setFrames(Number(e.target.value))}
                data-testid="sprite-frames-select"
                className="bg-black/40 border border-white/10 rounded-lg px-3 py-2 text-sm">
          <option value={4}>4 إطارات</option>
          <option value={8}>8 إطارات</option>
          <option value={12}>12 إطار</option>
        </select>
      </div>
      {err && <div className="text-xs text-rose-300 bg-rose-500/10 p-2 rounded">{err}</div>}
      {sheet && (
        <div className="space-y-2">
          <div className={`text-xs text-${accent}-200`}>✅ {sheet.name} · {sheet.cols}x{sheet.rows} grid</div>
          <img src={`${API}${sheet.image_url}`} alt={sheet.name}
               className="max-w-full rounded-lg border border-emerald-500/30" />
        </div>
      )}
      <button onClick={generate} disabled={busy || !character.trim() || !projectId}
              data-testid="sprite-generate-btn"
              className={`text-xs font-bold px-4 py-2 rounded-lg bg-${accent}-500 hover:bg-${accent}-400 text-black flex items-center gap-2 disabled:opacity-40`}>
        {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : <Film className="w-4 h-4" />}
        {busy ? `يولّد ${frames} إطارات…` : 'ولّد Sprite Sheet'}
      </button>
    </div>
  );
}

// ═════════════════════════════════════════════════════════════════════════
// MULTIPLAYER PANEL
// ═════════════════════════════════════════════════════════════════════════
function MultiplayerPanel({ projectId, token, accent }) {
  const [stack, setStack] = useState('colyseus');
  const [maxPlayers, setMaxPlayers] = useState(8);
  const [gameType, setGameType] = useState('co-op');
  const [scaffold, setScaffold] = useState(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState('');

  const generate = async () => {
    setErr(''); setScaffold(null); setBusy(true);
    try {
      const r = await fetch(`${API}/api/games/multiplayer-scaffold`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({ stack, max_players: maxPlayers, game_type: gameType }),
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || 'فشل');
      setScaffold(d);
    } catch (e) { setErr(e.message); }
    finally { setBusy(false); }
  };

  const download = () => {
    if (!projectId) return;
    const u = `${API}/api/games/multiplayer-scaffold/${projectId}/download?stack=${stack}&max_players=${maxPlayers}&game_type=${encodeURIComponent(gameType)}`;
    fetch(u, { headers: { Authorization: `Bearer ${token}` } })
      .then(r => r.blob())
      .then(b => {
        const url = URL.createObjectURL(b);
        const a = document.createElement('a');
        a.href = url; a.download = `zitex-${stack}.zip`; a.click();
        URL.revokeObjectURL(url);
      });
  };

  return (
    <div className="space-y-4 text-right">
      <div>
        <h3 className={`text-${accent}-200 font-bold mb-1`}>🌐 Multiplayer Scaffolds</h3>
        <p className="text-xs text-zinc-400">كود netcode احترافي جاهز للاستخدام — Colyseus (Node) أو Socket.IO أو Photon Quantum (Unity).</p>
      </div>
      <div className="grid grid-cols-3 gap-2">
        <select value={stack} onChange={e => setStack(e.target.value)}
                data-testid="mp-stack-select"
                className="bg-black/40 border border-white/10 rounded-lg px-3 py-2 text-sm">
          <option value="colyseus">Colyseus (Node)</option>
          <option value="socketio">Socket.IO</option>
          <option value="photon">Photon (Unity)</option>
        </select>
        <input type="number" min="2" max="64" value={maxPlayers}
               onChange={e => setMaxPlayers(Number(e.target.value))}
               data-testid="mp-players-input"
               className="bg-black/40 border border-white/10 rounded-lg px-3 py-2 text-sm" />
        <select value={gameType} onChange={e => setGameType(e.target.value)}
                data-testid="mp-gametype-select"
                className="bg-black/40 border border-white/10 rounded-lg px-3 py-2 text-sm">
          <option value="co-op">Co-op</option>
          <option value="battle-royale">Battle Royale</option>
          <option value="moba">MOBA</option>
          <option value="2d-platformer">2D Platformer</option>
        </select>
      </div>
      {err && <div className="text-xs text-rose-300 bg-rose-500/10 p-2 rounded">{err}</div>}
      {scaffold && (
        <div className="bg-black/40 border border-emerald-500/30 rounded-lg p-3 space-y-2 max-h-60 overflow-y-auto">
          <div className={`text-xs text-${accent}-200 font-bold`}>✅ {scaffold.stack} · {Object.keys(scaffold.files).length} files</div>
          {Object.entries(scaffold.files).map(([fname, content]) => (
            <details key={fname} className="text-[11px]">
              <summary className="cursor-pointer text-emerald-300 font-bold">{fname}</summary>
              <pre className="mt-1 p-2 bg-black/60 rounded text-[10px] text-zinc-200 overflow-x-auto" dir="ltr">{content.slice(0, 1500)}{content.length > 1500 ? '\n...' : ''}</pre>
            </details>
          ))}
        </div>
      )}
      <div className="flex gap-2">
        <button onClick={generate} disabled={busy}
                data-testid="mp-generate-btn"
                className={`text-xs font-bold px-4 py-2 rounded-lg bg-${accent}-500 hover:bg-${accent}-400 text-black flex items-center gap-2 disabled:opacity-40`}>
          {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : <Network className="w-4 h-4" />}
          عاينه
        </button>
        <button onClick={download} disabled={!projectId}
                data-testid="mp-download-btn"
                className="text-xs font-bold px-4 py-2 rounded-lg border-2 border-emerald-500/40 text-emerald-200 hover:bg-emerald-500/10 flex items-center gap-2 disabled:opacity-40">
          <Download className="w-4 h-4" /> تنزيل .zip
        </button>
      </div>
    </div>
  );
}

// ═════════════════════════════════════════════════════════════════════════
// MARKETPLACE PANEL
// ═════════════════════════════════════════════════════════════════════════
function MarketplacePanel({ projectId, token, accent }) {
  const [items, setItems] = useState([]);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState('');
  const [tab, setTab] = useState('browse');
  const [title, setTitle] = useState('');
  const [desc, setDesc] = useState('');
  const [tags, setTags] = useState('');

  const load = async () => {
    setBusy(true);
    try {
      const r = await fetch(`${API}/api/games/marketplace?page_size=20&sort=popular`);
      const d = await r.json();
      setItems(d.items || []);
    } catch (e) { setErr(e.message); }
    finally { setBusy(false); }
  };

  useEffect(() => { if (tab === 'browse') load(); }, [tab]);

  const publish = async () => {
    setErr(''); setBusy(true);
    try {
      const r = await fetch(`${API}/api/games/marketplace/publish`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({
          project_id: projectId, title, description: desc,
          tags: tags.split(',').map(t => t.trim()).filter(Boolean),
        }),
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || 'فشل');
      alert('✅ تم نشر النموذج للماركتبليس');
      setTab('browse');
    } catch (e) { setErr(e.message); }
    finally { setBusy(false); }
  };

  const install = async (mid) => {
    if (!projectId) return alert('افتح مشروع أولاً');
    setBusy(true);
    try {
      const r = await fetch(`${API}/api/games/marketplace/${mid}/install`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({ target_project_id: projectId }),
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || 'فشل');
      alert('✅ تم تثبيت النمط على مشروعك');
    } catch (e) { alert('❌ ' + e.message); }
    finally { setBusy(false); }
  };

  return (
    <div className="space-y-4 text-right">
      <div>
        <h3 className={`text-${accent}-200 font-bold mb-1`}>🛒 LoRA Marketplace</h3>
        <p className="text-xs text-zinc-400">شارك نمط مشروعك مع الآخرين أو ثبّت نمط جاهز من المجتمع.</p>
      </div>
      <div className="flex gap-2">
        <button onClick={() => setTab('browse')}
                data-testid="market-browse-tab"
                className={`text-xs font-bold px-3 py-1.5 rounded-lg ${tab === 'browse' ? `bg-${accent}-500 text-black` : 'bg-black/40 text-zinc-300'}`}>
          تصفح
        </button>
        <button onClick={() => setTab('publish')}
                data-testid="market-publish-tab"
                className={`text-xs font-bold px-3 py-1.5 rounded-lg ${tab === 'publish' ? `bg-${accent}-500 text-black` : 'bg-black/40 text-zinc-300'}`}>
          نشر نمط
        </button>
      </div>

      {err && <div className="text-xs text-rose-300 bg-rose-500/10 p-2 rounded">{err}</div>}

      {tab === 'browse' && (
        <div>
          {busy && <Loader2 className="w-5 h-5 animate-spin text-amber-400" />}
          {!busy && items.length === 0 && (
            <div className="text-xs text-zinc-400 text-center py-8">لا يوجد نماذج منشورة بعد — كن أول من ينشر!</div>
          )}
          <div className="grid grid-cols-2 gap-3">
            {items.map(it => (
              <div key={it.id} className="bg-black/40 border border-white/10 rounded-lg p-3 hover:border-amber-500/40 transition-colors">
                <div className="flex gap-1.5 mb-2 h-20 overflow-hidden rounded">
                  {(it.preview_images || []).slice(0, 3).map((p, i) => (
                    <img key={i} src={p} alt="" className="flex-1 object-cover rounded" />
                  ))}
                </div>
                <div className={`text-xs font-bold text-${accent}-200 truncate`}>{it.title}</div>
                <div className="text-[10px] text-zinc-400 truncate">{it.description}</div>
                <div className="flex items-center justify-between mt-2">
                  <span className="text-[10px] text-zinc-500 flex items-center gap-1">
                    <Star className="w-3 h-3" /> {it.rating_avg?.toFixed(1) || '–'} · {it.installs} تثبيت
                  </span>
                  <button onClick={() => install(it.id)} disabled={busy}
                          data-testid={`market-install-${it.id}`}
                          className="text-[10px] font-bold px-2 py-1 bg-emerald-500/20 border border-emerald-400/40 text-emerald-200 rounded hover:bg-emerald-500/30">
                    ثبّت
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {tab === 'publish' && (
        <div className="space-y-3">
          <input type="text" value={title} onChange={e => setTitle(e.target.value)}
                 data-testid="market-title-input"
                 placeholder="اسم النمط (مثل: Anime Cyberpunk)" className="w-full bg-black/40 border border-white/10 rounded-lg px-3 py-2 text-sm" />
          <textarea rows={3} value={desc} onChange={e => setDesc(e.target.value)}
                    data-testid="market-desc-input"
                    placeholder="وصف قصير — أين يصلح هذا النمط؟" className="w-full bg-black/40 border border-white/10 rounded-lg px-3 py-2 text-sm" />
          <input type="text" value={tags} onChange={e => setTags(e.target.value)}
                 data-testid="market-tags-input"
                 placeholder="tags بفواصل (anime, cyberpunk, dark)" className="w-full bg-black/40 border border-white/10 rounded-lg px-3 py-2 text-sm" />
          <button onClick={publish} disabled={busy || !title.trim() || !projectId}
                  data-testid="market-publish-btn"
                  className={`text-xs font-bold px-4 py-2 rounded-lg bg-${accent}-500 hover:bg-${accent}-400 text-black flex items-center gap-2 disabled:opacity-40`}>
            {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : <Upload className="w-4 h-4" />}
            انشر للماركتبليس
          </button>
          <p className="text-[10px] text-zinc-500">يتطلب نموذج LoRA مُدرَّب على هذا المشروع (تبويب الأصول المعتمدة → ابدأ التدريب).</p>
        </div>
      )}
    </div>
  );
}

// ═════════════════════════════════════════════════════════════════════════
// UNITY SDK PANEL
// ═════════════════════════════════════════════════════════════════════════
function UnityPanel({ projectId, token, accent }) {
  const [isPublic, setIsPublic] = useState(false);
  const [busy, setBusy] = useState(false);
  const manifestUrl = projectId ? `${API}/api/games/project/${projectId}/unity-manifest` : '';

  const togglePublic = async () => {
    setBusy(true);
    try {
      const r = await fetch(`${API}/api/games/project/${projectId}/unity-public`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({ is_public: !isPublic }),
      });
      const d = await r.json();
      if (r.ok) setIsPublic(d.is_public_unity);
    } finally { setBusy(false); }
  };

  const download = async () => {
    if (!projectId) return;
    setBusy(true);
    try {
      const r = await fetch(`${API}/api/games/project/${projectId}/unity-sdk.zip`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      const b = await r.blob();
      const url = URL.createObjectURL(b);
      const a = document.createElement('a');
      a.href = url; a.download = `zitex-unity-${projectId.slice(0, 8)}.zip`; a.click();
      URL.revokeObjectURL(url);
    } finally { setBusy(false); }
  };

  return (
    <div className="space-y-4 text-right">
      <div>
        <h3 className={`text-${accent}-200 font-bold mb-1`}>🎮 Unity SDK Export</h3>
        <p className="text-xs text-zinc-400">حمّل حزمة C# تستورد كل أصولك تلقائياً في Unity scene عند التشغيل.</p>
      </div>
      <div className="bg-black/40 border border-white/10 rounded-lg p-3 space-y-2">
        <div className="text-xs text-zinc-300 font-bold">Manifest URL</div>
        <code className="block text-[10px] text-amber-200 break-all" dir="ltr">{manifestUrl || 'افتح مشروع أولاً'}</code>
        <label className="flex items-center gap-2 text-xs text-zinc-300 cursor-pointer">
          <input type="checkbox" checked={isPublic} onChange={togglePublic} disabled={busy}
                 data-testid="unity-public-toggle" />
          <span>اجعل الـmanifest عام (للوصول بدون مصادقة من Unity)</span>
        </label>
      </div>
      <button onClick={download} disabled={busy || !projectId}
              data-testid="unity-download-btn"
              className={`text-xs font-bold px-4 py-2 rounded-lg bg-${accent}-500 hover:bg-${accent}-400 text-black flex items-center gap-2 disabled:opacity-40`}>
        {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : <Download className="w-4 h-4" />}
        تنزيل Unity SDK .zip
      </button>
      <p className="text-[11px] text-zinc-500 leading-relaxed">
        داخل الـZIP: <code>Zitex/ZitexClient.cs</code>, <code>Zitex/ZitexImporter.cs</code>, <code>manifest.json</code>, <code>README.md</code>.
        ضع المجلد في <code>Assets/</code>، ثبّت GLTFast، أضف <code>ZitexImporter</code> لـGameObject في المشهد، اضغط Play.
      </p>
    </div>
  );
}
