// Frontend pieces extending /pages/Operator.js — Dashboard, Memory, Alerts, Settings, modern Chat UX.
// This file is imported by Operator.js to keep it modular.
import React, { useEffect, useMemo, useRef, useState } from 'react';
import { toast } from 'sonner';

const API = process.env.REACT_APP_BACKEND_URL;

// ─────────────────────────────────────────────────────────
// Multi-client Dashboard
// ─────────────────────────────────────────────────────────
export function DashboardView({ H, onPick }) {
  const [data, setData] = useState(null);
  const [running, setRunning] = useState(false);

  const load = async () => {
    const d = await fetch(`${API}/api/operator/dashboard`, { headers: H }).then(r => r.json());
    setData(d);
  };
  useEffect(() => { load(); /* eslint-disable-next-line */ }, []);

  const runChecks = async () => {
    setRunning(true);
    try {
      await fetch(`${API}/api/operator/health-check/run`, { method: 'POST', headers: H });
      toast.success('✅ تم فحص كل العملاء');
      load();
    } catch (_) { toast.error('فشل'); }
    setRunning(false);
  };

  if (!data) return <div className="p-8 text-white/40 text-sm">⏳ جاري التحميل...</div>;
  const s = data.summary || {};

  return (
    <div className="p-6 max-w-6xl mx-auto" data-testid="dashboard-view">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-2xl font-black">📊 لوحة التحكم</h2>
          <div className="text-xs text-white/50">إجمالي {s.total} عميل · يعمل {s.healthy} · فاشل {s.failing} · غير مهيّأ {s.unconfigured}</div>
        </div>
        <button onClick={runChecks} disabled={running}
          className="px-4 py-2 bg-emerald-500 hover:bg-emerald-600 text-black font-black rounded-lg text-sm disabled:opacity-50"
          data-testid="run-checks-btn">
          {running ? '⏳ جاري الفحص...' : '🔄 فحص كل العملاء الآن'}
        </button>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
        <Stat label="✅ يعمل" value={s.healthy || 0} color="emerald" />
        <Stat label="❌ فاشل" value={s.failing || 0} color="red" />
        <Stat label="⏳ معلّق" value={s.pending || 0} color="amber" />
        <Stat label="⚪ غير مهيّأ" value={s.unconfigured || 0} color="gray" />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {(data.clients || []).map(c => <ClientCard key={c.id} c={c} onPick={onPick} />)}
      </div>
    </div>
  );
}

function Stat({ label, value, color }) {
  const colors = {
    emerald: 'from-emerald-500/15 to-emerald-500/5 border-emerald-500/30',
    red: 'from-red-500/15 to-red-500/5 border-red-500/30',
    amber: 'from-amber-500/15 to-amber-500/5 border-amber-500/30',
    gray: 'from-white/10 to-white/5 border-white/20',
  };
  return (
    <div className={`bg-gradient-to-br ${colors[color]} border rounded-xl p-4`}>
      <div className="text-3xl font-black">{value}</div>
      <div className="text-xs text-white/70 mt-1">{label}</div>
    </div>
  );
}

function ClientCard({ c, onPick }) {
  const stateColors = {
    healthy: 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30',
    failing: 'bg-red-500/15 text-red-300 border-red-500/30',
    pending: 'bg-amber-500/15 text-amber-300 border-amber-500/30',
    unknown: 'bg-white/10 text-white/60 border-white/20',
    error: 'bg-red-500/15 text-red-300 border-red-500/30',
    'n/a': 'bg-white/5 text-white/40 border-white/10',
  };
  return (
    <button onClick={() => onPick(c.id)} className="text-right p-4 bg-white/[.03] hover:bg-white/[.06] border border-white/10 rounded-xl transition-colors" data-testid={`dash-client-${c.id}`}>
      <div className="flex items-start justify-between mb-2">
        <div className="flex-1 min-w-0">
          <div className="font-black truncate">{c.name}</div>
          <div className="text-[10px] text-white/50 truncate">{c.client_email || '—'}</div>
        </div>
        <span className={`text-[10px] px-2 py-0.5 rounded-full border ${stateColors[c.railway_state] || stateColors['n/a']}`}>
          {c.railway_state === 'healthy' && '✅'}
          {c.railway_state === 'failing' && '❌'}
          {c.railway_state === 'pending' && '⏳'}
          {(c.railway_state === 'unknown' || c.railway_state === 'n/a') && '⚪'}
          {' '}{c.railway_status || c.railway_state}
        </span>
      </div>
      <div className="flex items-center gap-2 mt-3">
        {c.has_github && <span className="text-[9px] bg-white/10 px-1.5 py-0.5 rounded">GH</span>}
        {c.has_railway && <span className="text-[9px] bg-purple-500/20 px-1.5 py-0.5 rounded">RW</span>}
        {c.has_vercel && <span className="text-[9px] bg-black/50 border border-white/20 px-1.5 py-0.5 rounded">VC</span>}
        <span className="flex-1" />
        <span className="text-[10px] text-white/50">🤖 {c.agent_calls_month}/شهر</span>
        {c.memory_count > 0 && <span className="text-[10px] text-emerald-300">🧠 {c.memory_count}</span>}
      </div>
    </button>
  );
}

// ─────────────────────────────────────────────────────────
// Memory Tab
// ─────────────────────────────────────────────────────────
export function MemoryTab({ client, H }) {
  const [items, setItems] = useState([]);
  const [text, setText] = useState('');

  const load = async () => {
    const d = await fetch(`${API}/api/operator/clients/${client.id}/memory`, { headers: H }).then(r => r.json());
    setItems(d.memory || []);
  };
  useEffect(() => { load(); /* eslint-disable-next-line */ }, [client.id]);

  const add = async () => {
    if (!text.trim()) return;
    await fetch(`${API}/api/operator/clients/${client.id}/memory`, {
      method: 'POST', headers: H, body: JSON.stringify({ fact: text.trim() }),
    });
    setText(''); load(); toast.success('تم الحفظ');
  };
  const clearAll = async () => {
    if (!window.confirm('مسح كل الذاكرة؟')) return;
    await fetch(`${API}/api/operator/clients/${client.id}/memory`, { method: 'DELETE', headers: H });
    load();
  };

  return (
    <div className="space-y-3" data-testid="memory-tab">
      <div className="bg-blue-500/5 border border-blue-500/20 rounded-xl p-3 text-xs text-white/70">
        🧠 الذاكرة الدائمة تُحقن في system prompt في كل جلسة لاحقة. الوكيل يضيف لها تلقائياً عبر أداة `remember`، ويمكنك تعديلها يدوياً هنا.
      </div>
      <div className="flex gap-2">
        <textarea rows={2} value={text} onChange={e => setText(e.target.value)}
          placeholder="مثلاً: العميل يفضّل اسم branch 'production' بدلاً من 'main'..."
          className="flex-1 px-3 py-2 bg-black/30 border border-white/10 rounded-lg text-sm resize-none" data-testid="mem-input" />
        <button onClick={add} className="px-4 py-2 bg-yellow-500 text-black rounded-lg font-black text-sm" data-testid="mem-add">+ حفظ</button>
      </div>
      {items.length === 0 ? (
        <div className="text-center py-10 text-white/40 text-sm">لا توجد ذاكرة بعد. ستُملأ تلقائياً عند تفاعل الوكيل مع العميل.</div>
      ) : (
        <>
          <div className="flex justify-end">
            <button onClick={clearAll} className="text-[11px] text-red-400 hover:text-red-300">🗑️ مسح كل الذاكرة</button>
          </div>
          <div className="space-y-2">
            {items.map((m, i) => (
              <div key={i} className="bg-white/[.03] border border-white/10 rounded-lg p-3 text-sm flex gap-3">
                <span className="text-emerald-300">🧠</span>
                <div className="flex-1">
                  <div>{m.fact}</div>
                  <div className="text-[10px] text-white/40 mt-1">{new Date(m.at).toLocaleString('ar-SA')}</div>
                </div>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}

// ─────────────────────────────────────────────────────────
// Alerts inbox
// ─────────────────────────────────────────────────────────
export function AlertsBell({ H }) {
  const [count, setCount] = useState(0);
  const [open, setOpen] = useState(false);
  const [alerts, setAlerts] = useState([]);

  const load = async () => {
    const d = await fetch(`${API}/api/operator/alerts?unseen=true`, { headers: H }).then(r => r.json());
    setCount(d.count || 0);
  };
  const loadAll = async () => {
    const d = await fetch(`${API}/api/operator/alerts`, { headers: H }).then(r => r.json());
    setAlerts(d.alerts || []);
  };

  useEffect(() => {
    load();
    const t = setInterval(load, 60000);
    return () => clearInterval(t);
    // eslint-disable-next-line
  }, []);

  const openPanel = async () => {
    setOpen(true); await loadAll();
    await fetch(`${API}/api/operator/alerts/mark-seen`, { method: 'POST', headers: H });
    setCount(0);
  };

  return (
    <>
      <button onClick={openPanel} className="relative w-full text-xs text-white/60 hover:text-white py-1 text-right px-2" data-testid="alerts-bell">
        🔔 التنبيهات {count > 0 && <span className="absolute top-0 left-1 bg-red-500 text-white text-[9px] font-black px-1.5 py-0.5 rounded-full">{count}</span>}
      </button>
      {open && (
        <div className="fixed inset-0 bg-black/70 z-50 flex items-center justify-center p-4" onClick={() => setOpen(false)}>
          <div onClick={e => e.stopPropagation()} className="bg-[#0a0b14] border border-white/10 rounded-2xl max-w-2xl w-full max-h-[80vh] overflow-hidden flex flex-col">
            <div className="p-4 border-b border-white/10 flex items-center justify-between">
              <h3 className="font-black text-lg">🔔 التنبيهات</h3>
              <button onClick={() => setOpen(false)} className="text-white/60 hover:text-white">✕</button>
            </div>
            <div className="overflow-y-auto p-4 space-y-2">
              {alerts.length === 0 && <div className="text-center text-white/40 py-8 text-sm">لا تنبيهات</div>}
              {alerts.map((a, i) => (
                <div key={i} className="bg-red-500/5 border border-red-500/20 rounded-lg p-3 flex items-center gap-3">
                  <span className="text-2xl">⚠️</span>
                  <div className="flex-1">
                    <div className="font-bold text-sm">{a.title}</div>
                    <div className="text-[10px] text-white/40">{new Date(a.at).toLocaleString('ar-SA')}</div>
                  </div>
                  {a.whatsapp_link && (
                    <a href={a.whatsapp_link} target="_blank" rel="noopener" className="text-xs px-3 py-1.5 bg-emerald-500 text-black rounded-lg font-bold">📱 واتساب</a>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </>
  );
}

// ─────────────────────────────────────────────────────────
// Settings panel (alert phone)
// ─────────────────────────────────────────────────────────
export function SettingsPanel({ H, onClose }) {
  const [s, setS] = useState({ alert_phone: '', alert_email: '' });
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    fetch(`${API}/api/operator/settings`, { headers: H }).then(r => r.json()).then(d => {
      setS({ alert_phone: d.alert_phone || '', alert_email: d.alert_email || '' });
      setLoaded(true);
    });
    // eslint-disable-next-line
  }, []);

  const save = async () => {
    await fetch(`${API}/api/operator/settings`, { method: 'PUT', headers: H, body: JSON.stringify(s) });
    toast.success('✅ تم الحفظ');
    onClose && onClose();
  };

  if (!loaded) return null;

  return (
    <div className="fixed inset-0 bg-black/70 z-50 flex items-center justify-center p-4" onClick={onClose}>
      <div onClick={e => e.stopPropagation()} className="bg-[#0a0b14] border border-white/10 rounded-2xl max-w-lg w-full p-6">
        <h3 className="font-black text-lg mb-4">⚙️ إعدادات الوكالة</h3>
        <label className="block mb-3">
          <div className="text-xs text-white/60 mb-1">📱 رقم واتساب للتنبيهات (مع رمز الدولة، بدون +)</div>
          <input value={s.alert_phone} onChange={e => setS({ ...s, alert_phone: e.target.value })} placeholder="966500000000"
            className="w-full px-3 py-2 bg-black/30 border border-white/10 rounded-lg text-sm" data-testid="alert-phone" />
        </label>
        <label className="block mb-4">
          <div className="text-xs text-white/60 mb-1">📧 إيميل التنبيهات (اختياري)</div>
          <input value={s.alert_email} onChange={e => setS({ ...s, alert_email: e.target.value })} placeholder="ops@example.com"
            className="w-full px-3 py-2 bg-black/30 border border-white/10 rounded-lg text-sm" data-testid="alert-email" />
        </label>
        <div className="flex gap-2 justify-end">
          <button onClick={onClose} className="px-4 py-2 bg-white/10 hover:bg-white/20 rounded-lg text-sm">إلغاء</button>
          <button onClick={save} className="px-4 py-2 bg-yellow-500 text-black rounded-lg font-black text-sm" data-testid="save-settings">💾 حفظ</button>
        </div>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────
// Modern Chat UX (auto-scroll, collapsible old replies, live WebSocket streaming)
// ─────────────────────────────────────────────────────────
export function ModernChatTab({ client, H }) {
  const [sessionId, setSessionId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const [sessions, setSessions] = useState([]);
  const [liveSteps, setLiveSteps] = useState([]);  // in-progress tool steps for current turn
  const [liveStatus, setLiveStatus] = useState(''); // e.g. "🔧 calling read_file..."
  const bottomRef = useRef(null);
  const wsRef = useRef(null);
  const pendingResolveRef = useRef(null);

  const loadSessions = async () => {
    const d = await fetch(`${API}/api/operator/clients/${client.id}/chat/sessions`, { headers: H }).then(r => r.json());
    setSessions(d.sessions || []);
  };
  const loadSession = async (sid) => {
    setSessionId(sid);
    if (!sid) { setMessages([]); return; }
    const d = await fetch(`${API}/api/operator/clients/${client.id}/chat/${sid}`, { headers: H }).then(r => r.json());
    const msgs = (d.messages || []).map((m, i, arr) => ({
      ...m,
      _collapsed: m.role === 'assistant' && i < arr.length - 1,
    }));
    setMessages(msgs);
  };
  useEffect(() => {
    loadSessions(); setSessionId(null); setMessages([]);
    // close WS on client switch
    if (wsRef.current) { try { wsRef.current.close(); } catch (_) {} wsRef.current = null; }
    // eslint-disable-next-line
  }, [client.id]);

  useEffect(() => {
    if (bottomRef.current) bottomRef.current.scrollIntoView({ behavior: 'smooth', block: 'end' });
  }, [messages, sending, liveSteps]);

  // Cleanup on unmount
  useEffect(() => () => { if (wsRef.current) { try { wsRef.current.close(); } catch (_) {} } }, []);

  const ensureSocket = () => new Promise((resolve, reject) => {
    if (wsRef.current && wsRef.current.readyState === 1) { resolve(wsRef.current); return; }
    const tok = localStorage.getItem('token') || '';
    const wsUrl = (API.replace(/^http/, 'ws')) + `/api/operator/ws/agent/${client.id}?token=${encodeURIComponent(tok)}`;
    const ws = new WebSocket(wsUrl);
    let opened = false;
    ws.onopen = () => { opened = true; wsRef.current = ws; };
    ws.onmessage = (ev) => {
      let m; try { m = JSON.parse(ev.data); } catch (_) { return; }
      if (m.kind === 'ready') { resolve(ws); return; }
      if (m.kind === 'tool_start') {
        setLiveStatus(`🔧 ${m.tool}(${Object.keys(m.args || {}).join(', ')})...`);
      } else if (m.kind === 'tool_done') {
        setLiveSteps(prev => [...prev, m]);
        setLiveStatus(m.result?.error ? `❌ ${m.tool}` : `✅ ${m.tool}`);
      } else if (m.kind === 'thinking') {
        setLiveStatus('💭 يفكّر...');
      } else if (m.kind === 'final') {
        setLiveStatus('');
      } else if (m.kind === 'complete') {
        if (pendingResolveRef.current) {
          pendingResolveRef.current({ final: m.final, session_id: m.session_id });
          pendingResolveRef.current = null;
        }
      } else if (m.kind === 'error') {
        if (pendingResolveRef.current) {
          pendingResolveRef.current({ error: m.error });
          pendingResolveRef.current = null;
        }
      }
    };
    ws.onerror = () => { if (!opened) reject(new Error('WebSocket failed')); };
    ws.onclose = () => { wsRef.current = null; };
    setTimeout(() => { if (!opened) reject(new Error('WS timeout')); }, 10000);
  });

  const send = async () => {
    const t = input.trim(); if (!t || sending) return;
    setInput('');
    setMessages(prev => [
      ...prev.map(m => m.role === 'assistant' ? { ...m, _collapsed: true } : m),
      { role: 'user', text: t, at: new Date().toISOString() },
    ]);
    setSending(true);
    setLiveSteps([]); setLiveStatus('🚀 متصل...');

    // Try WebSocket streaming; fallback to HTTP if WS fails
    let usedWS = false;
    try {
      const ws = await ensureSocket();
      usedWS = true;
      const result = await new Promise((resolve) => {
        pendingResolveRef.current = resolve;
        ws.send(JSON.stringify({ text: t, session_id: sessionId || undefined }));
      });
      if (result.error) throw new Error(result.error);
      if (!sessionId && result.session_id) { setSessionId(result.session_id); loadSessions(); }
      // Capture the steps we collected via stream; merge into final message
      setMessages(prev => {
        const stepsCopy = liveSteps.slice();
        return [...prev, { role: 'assistant', text: result.final, steps: stepsCopy, at: new Date().toISOString(), _collapsed: false }];
      });
    } catch (e) {
      if (!usedWS) {
        // HTTP fallback
        try {
          const r = await fetch(`${API}/api/operator/clients/${client.id}/chat`, {
            method: 'POST', headers: H,
            body: JSON.stringify({ text: t, session_id: sessionId || undefined }),
          });
          const d = await r.json();
          if (!r.ok) throw new Error(d.detail || 'Failed');
          if (!sessionId) { setSessionId(d.session_id); loadSessions(); }
          setMessages(prev => [...prev, { role: 'assistant', text: d.final, steps: d.steps, at: new Date().toISOString(), _collapsed: false }]);
        } catch (e2) { toast.error(e2.message); }
      } else {
        toast.error(e.message);
      }
    }
    setSending(false); setLiveStatus(''); setLiveSteps([]);
  };

  const toggleCollapse = (idx) => {
    setMessages(prev => prev.map((m, i) => i === idx ? { ...m, _collapsed: !m._collapsed } : m));
  };

  const delSession = async (sid) => {
    if (!window.confirm('حذف هذه الجلسة؟')) return;
    await fetch(`${API}/api/operator/clients/${client.id}/chat/${sid}`, { method: 'DELETE', headers: H });
    if (sid === sessionId) { setSessionId(null); setMessages([]); }
    loadSessions();
  };

  const suggestions = [
    '🔍 افحص حالة المشروع الحالية (context)',
    '🚨 افحص آخر deployment على Railway وقل لي إذا فشل',
    '📄 اقرأ ملف backend/railway.toml وأخبرني ماذا يحتوي',
    '🛠️ أصلح مشكلة PORT في railway.toml وأعد النشر',
    '🌐 أعد نشر Vercel للـ frontend',
    '🧠 ما الذي تتذكّره عن هذا العميل؟',
  ];

  return (
    <div className="flex gap-4 h-[calc(100vh-220px)]" data-testid="modern-chat-tab">
      <div className="w-56 flex-shrink-0 bg-white/[.02] border border-white/10 rounded-xl p-3 overflow-y-auto">
        <button onClick={() => { setSessionId(null); setMessages([]); }}
          className="w-full px-3 py-2 bg-emerald-500 text-black rounded-lg text-xs font-black mb-2" data-testid="new-chat">
          + محادثة جديدة
        </button>
        {sessions.length === 0 && <div className="text-[11px] text-white/40 text-center py-4">لا محادثات</div>}
        {sessions.map((s) => (
          <div key={s.session_id} className={`group flex items-center gap-1 mb-1 rounded-lg ${s.session_id === sessionId ? 'bg-emerald-500/15 border border-emerald-500/30' : 'hover:bg-white/5'}`}>
            <button onClick={() => loadSession(s.session_id)} className="flex-1 text-right p-2 text-xs truncate">
              <div className="truncate font-medium">{s.title || '(بدون عنوان)'}</div>
              <div className="text-[9px] text-white/40">{new Date(s.last_at).toLocaleString('ar-SA')} · {s.messages}</div>
            </button>
            <button onClick={() => delSession(s.session_id)} className="opacity-0 group-hover:opacity-100 text-red-400 text-xs px-1">✕</button>
          </div>
        ))}
      </div>

      <div className="flex-1 flex flex-col bg-white/[.02] border border-white/10 rounded-xl overflow-hidden">
        <div className="flex-1 overflow-y-auto p-4 space-y-3" data-testid="chat-log">
          {messages.length === 0 && !sending && (
            <div className="py-6">
              <div className="text-center text-white/60 mb-5">
                <div className="text-4xl mb-2">🤖</div>
                <div className="font-black text-lg">Zitex DevOps Agent</div>
                <div className="text-xs mt-2">وكيل ذكي يصلح، ينشر، ويدير مشاريع العملاء تلقائياً</div>
              </div>
              <div className="max-w-md mx-auto space-y-2">
                <div className="text-[11px] text-white/50 text-center mb-2">جرّب:</div>
                {suggestions.map((s, i) => (
                  <button key={i} onClick={() => setInput(s)}
                    className="w-full text-right p-3 bg-white/5 hover:bg-white/10 border border-white/10 rounded-lg text-xs transition-colors"
                    data-testid={`suggest-${i}`}>{s}</button>
                ))}
              </div>
            </div>
          )}
          {messages.map((m, i) => (
            <ModernMessageRow key={i} msg={m} idx={i} onToggle={() => toggleCollapse(i)} />
          ))}
          {sending && (
            <div className="flex flex-col gap-2" data-testid="thinking">
              {liveSteps.length > 0 && (
                <div className="bg-emerald-500/5 border border-emerald-500/20 rounded-lg p-2 space-y-1.5">
                  {liveSteps.map((s, i) => (
                    <div key={i} className="flex items-start gap-2 text-[11px]">
                      <span>{s.result?.error ? '❌' : '✅'}</span>
                      <code className={`font-mono font-bold ${s.result?.error ? 'text-red-300' : 'text-emerald-300'}`}>{s.tool}</code>
                      <span className="text-white/50 truncate flex-1">({Object.keys(s.args || {}).join(', ')})</span>
                    </div>
                  ))}
                </div>
              )}
              <div className="flex items-center gap-2 text-xs text-white/70 p-3 bg-white/[.03] border border-white/5 rounded-lg" data-testid="live-status">
                <div className="animate-bounce">🤖</div>
                <span className="animate-pulse">{liveStatus || 'الوكيل يفكّر ويستدعي الأدوات...'}</span>
              </div>
            </div>
          )}
          <div ref={bottomRef} />
        </div>
        <div className="border-t border-white/10 p-3 flex gap-2">
          <textarea value={input} onChange={e => setInput(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); } }}
            placeholder="اكتب ما تريد أن يفعله الوكيل... (Enter للإرسال، Shift+Enter لسطر جديد)"
            rows={2}
            className="flex-1 px-3 py-2 bg-black/40 border border-white/10 rounded-lg text-sm resize-none focus:border-emerald-400 outline-none"
            data-testid="chat-input" />
          <button onClick={send} disabled={sending || !input.trim()}
            className="px-5 py-2 bg-emerald-500 hover:bg-emerald-600 text-black font-black rounded-lg disabled:opacity-40"
            data-testid="chat-send">{sending ? '⏳' : '📤 إرسال'}</button>
        </div>
      </div>
    </div>
  );
}

function ModernMessageRow({ msg, idx, onToggle }) {
  if (msg.role === 'user') {
    return (
      <div className="flex justify-start" data-testid={`msg-user-${idx}`}>
        <div className="bg-yellow-500/15 border border-yellow-500/30 rounded-2xl rounded-tr-sm px-4 py-2.5 max-w-[80%] text-sm whitespace-pre-wrap">
          {msg.text}
        </div>
      </div>
    );
  }
  // Collapsed assistant message
  if (msg._collapsed) {
    const preview = ((msg.text || '').split('\n').slice(0, 2).join('\n')).slice(0, 140);
    const toolCount = (msg.steps || []).filter(s => s.kind === 'tool').length;
    return (
      <div className="flex justify-end" data-testid={`msg-collapsed-${idx}`}>
        <button onClick={onToggle} className="bg-emerald-500/8 hover:bg-emerald-500/15 border border-emerald-500/20 rounded-2xl rounded-tl-sm px-4 py-2 max-w-[90%] text-sm text-right transition-colors w-full">
          <div className="flex items-center gap-2 text-[10px] text-emerald-400 mb-1">
            <span>🤖</span>
            {toolCount > 0 && <span>{toolCount} أدوات</span>}
            <span className="flex-1" />
            <span className="text-white/40">انقر للتوسيع ⇡</span>
          </div>
          <div className="text-white/70 line-clamp-2 truncate">{preview}…</div>
        </button>
      </div>
    );
  }
  // Full assistant message
  return (
    <div className="flex justify-end" data-testid={`msg-assistant-${idx}`}>
      <div className="flex-1 max-w-[90%]">
        {(msg.steps || []).filter(s => s.kind === 'tool').length > 0 && (
          <details className="mb-2" open>
            <summary className="cursor-pointer text-[10px] text-emerald-400 select-none hover:text-emerald-300">
              🔧 {msg.steps.filter(s => s.kind === 'tool').length} استدعاء أدوات
            </summary>
            <div className="mt-2 space-y-1.5">
              {msg.steps.filter(s => s.kind === 'tool').map((s, i) => (
                <div key={i} className="bg-black/50 border border-white/10 rounded-lg p-2.5 text-[11px]">
                  {s.thought && <div className="text-white/60 italic mb-1">💭 {s.thought}</div>}
                  <div className="flex items-center gap-2 mb-1.5">
                    <code className={`font-mono font-bold ${s.result?.error ? 'text-red-300' : 'text-emerald-300'}`}>{s.tool}</code>
                    {s.args && Object.keys(s.args).length > 0 && (
                      <span className="text-white/40">({Object.keys(s.args).join(', ')})</span>
                    )}
                    {s.result?.error ? <span className="text-red-400">❌</span> : <span className="text-emerald-400">✅</span>}
                  </div>
                  <pre className="text-white/50 text-[10px] overflow-auto max-h-24 font-mono">
                    {JSON.stringify(s.result, null, 2).slice(0, 500)}
                  </pre>
                </div>
              ))}
            </div>
          </details>
        )}
        <div className="bg-emerald-500/10 border border-emerald-500/25 rounded-2xl rounded-tl-sm px-4 py-2.5 text-sm whitespace-pre-wrap relative group">
          {msg.text}
          <button onClick={onToggle} className="absolute top-1 left-1 opacity-0 group-hover:opacity-100 text-[9px] text-white/40 hover:text-white/80 transition-opacity">طي ⇣</button>
        </div>
      </div>
    </div>
  );
}
