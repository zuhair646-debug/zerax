/**
 * 🧪 Freebuild Lab — A bare-bones chat that exercises the SAME backend AI
 * (Claude / GPT / GLM) with the SAME tool set, but BYPASSES all workflow
 * stages, the brain orchestrator, mockup phases, and discovery flows.
 *
 * Built for the user to A/B test where the failure mode lives: in the
 * orchestration/workflow layer OR in the underlying AI itself.
 *
 * Mounted at /lab/:id (project ID required). The user picks one of their
 * existing projects, opens the lab, and chats directly with the AI.
 */
import React, { useEffect, useRef, useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import axios from 'axios';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const EVENT_DELIMITER = /\n\n/;

function parseSSE(buffer) {
  const events = [];
  let rest = buffer;
  let idx = rest.search(EVENT_DELIMITER);
  while (idx !== -1) {
    const block = rest.slice(0, idx);
    rest = rest.slice(idx + 2);
    let event = 'message';
    const dataLines = [];
    for (const ln of block.split('\n')) {
      if (ln.startsWith('event:')) event = ln.slice(6).trim();
      else if (ln.startsWith('data:')) dataLines.push(ln.slice(5).trimStart());
    }
    if (dataLines.length) {
      try { events.push({ event, data: JSON.parse(dataLines.join('\n')) }); }
      catch { events.push({ event, raw: dataLines.join('\n') }); }
    }
    idx = rest.search(EVENT_DELIMITER);
  }
  return { events, rest };
}

export default function FreebuildLab() {
  const { id: pid } = useParams();
  const navigate = useNavigate();
  const [project, setProject] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [busy, setBusy] = useState(false);
  const [toolLog, setToolLog] = useState([]);
  const scrollRef = useRef(null);

  useEffect(() => {
    if (!pid) return;
    const token = localStorage.getItem('token');
    axios.get(`${API}/freebuild-chat/project/${pid}`, {
      headers: { Authorization: `Bearer ${token}` },
    }).then(r => {
      setProject(r.data);
      setMessages(r.data?.messages || []);
    }).catch(() => {});
  }, [pid]);

  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  }, [messages, toolLog, busy]);

  const send = async () => {
    if (!input.trim() || busy) return;
    const msg = input.trim();
    setInput('');
    setMessages(m => [...m, { role: 'user', content: msg }]);
    setToolLog([]);
    setBusy(true);
    try {
      const token = localStorage.getItem('token');
      const fd = new FormData();
      fd.append('message', msg);
      fd.append('user_language', 'ar');
      fd.append('mode', 'lab');
      const resp = await fetch(
        `${API}/freebuild-chat/project/${pid}/agent-chat-stream`,
        { method: 'POST', body: fd, headers: { Authorization: `Bearer ${token}` } },
      );
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const reader = resp.body.getReader();
      const decoder = new TextDecoder('utf-8');
      let buffer = '';
      let summary = '', images = [];
      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const { events, rest } = parseSSE(buffer);
        buffer = rest;
        for (const ev of events) {
          if (ev.event === 'tool') {
            setToolLog(l => [...l, { name: ev.data?.name, phase: ev.data?.phase, label: ev.data?.label, step: ev.data?.step }]);
          } else if (ev.event === 'thinking') {
            setToolLog(l => [...l, { name: '🧠', phase: 'thinking', label: ev.data?.text }]);
          } else if (ev.event === 'done') {
            summary = ev.data?.summary || '';
            images = ev.data?.inline_images || [];
          }
        }
      }
      setMessages(m => [...m, { role: 'assistant', content: summary, inline_images: images }]);
    } catch (e) {
      setMessages(m => [...m, { role: 'system', content: `❌ خطأ: ${e.message}` }]);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div data-testid="freebuild-lab-page" className="min-h-screen bg-gradient-to-b from-slate-950 to-slate-900 text-white">
      <div className="max-w-4xl mx-auto p-4">
        <div className="flex items-center justify-between mb-4 border-b border-amber-500/20 pb-4">
          <div>
            <h1 data-testid="lab-title" className="text-2xl font-bold flex items-center gap-2">
              🧪 المختبر <span className="text-xs px-2 py-1 rounded-full bg-amber-500/20 text-amber-300">LAB MODE</span>
            </h1>
            <p className="text-sm opacity-70 mt-1">
              نفس الـAI ونفس الأدوات — بدون مراحل ولا workflow. شات مباشر مع الذكاء الصناعي للاختبار.
            </p>
            {project && (
              <p className="text-xs opacity-60 mt-1">
                مشروع: <code data-testid="lab-project-name">{project.name}</code> · {Object.keys(project.pages || {}).length} صفحة
              </p>
            )}
          </div>
          <div className="flex gap-2">
            <Link data-testid="lab-back-to-chat" to={`/freebuild/chat/${pid}`} className="px-3 py-1.5 text-sm rounded-lg bg-white/10 hover:bg-white/20">
              ← الشات العادي
            </Link>
            <button data-testid="lab-back-projects" onClick={() => navigate('/freebuild/projects')} className="px-3 py-1.5 text-sm rounded-lg bg-white/10 hover:bg-white/20">
              المشاريع
            </button>
          </div>
        </div>

        <div ref={scrollRef} data-testid="lab-messages" className="h-[60vh] overflow-y-auto space-y-3 p-3 rounded-lg bg-slate-900/60 border border-white/5">
          {messages.length === 0 && (
            <div className="text-center opacity-50 py-12">
              <p className="text-lg">المختبر فاضي — ابدأ بإرسال رسالة.</p>
              <p className="text-xs mt-2">مثلاً: <code>ابني لي صفحة about.html فيها عن الموقع + nav يربط بالرئيسية</code></p>
            </div>
          )}
          {messages.map((m, i) => (
            <div key={i} data-testid={`lab-msg-${i}`} className={`p-3 rounded-lg ${
              m.role === 'user' ? 'bg-amber-500/10 border border-amber-500/20' :
              m.role === 'assistant' ? 'bg-slate-800/80 border border-white/5' :
              'bg-red-500/10 border border-red-500/20'
            }`}>
              <div className="text-xs opacity-60 mb-1">
                {m.role === 'user' ? '👤 أنت' : m.role === 'assistant' ? '🤖 AI' : '⚠️ نظام'}
              </div>
              <div className="whitespace-pre-wrap text-sm">{m.content}</div>
              {(m.inline_images || []).length > 0 && (
                <div className="mt-2 grid grid-cols-2 gap-2">
                  {m.inline_images.map((img, j) => (
                    <a key={j} href={img.url} target="_blank" rel="noreferrer">
                      <img src={img.url} alt={img.caption || ''} className="rounded-lg w-full" />
                      {img.caption && <p className="text-xs opacity-60 mt-1">{img.caption}</p>}
                    </a>
                  ))}
                </div>
              )}
            </div>
          ))}
          {busy && (
            <div className="p-3 rounded-lg bg-slate-800/40 border border-white/5">
              <div className="text-xs opacity-60 mb-1">🤖 AI</div>
              <div className="text-sm opacity-70">⏳ يعمل... ({toolLog.length} خطوة حتى الآن)</div>
              <div className="mt-2 space-y-1 max-h-40 overflow-y-auto">
                {toolLog.slice(-10).map((t, k) => (
                  <div key={k} data-testid={`lab-tool-${k}`} className="text-xs px-2 py-1 bg-slate-900/60 rounded font-mono">
                    {t.label || `${t.name} · ${t.phase}`}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        <div className="mt-4 flex gap-2">
          <input
            data-testid="lab-input"
            type="text"
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && !e.shiftKey && send()}
            disabled={busy}
            placeholder="اكتب رسالتك للـAI..."
            className="flex-1 px-4 py-3 rounded-lg bg-slate-900/60 border border-white/10 focus:border-amber-500/50 outline-none"
          />
          <button
            data-testid="lab-send-btn"
            onClick={send}
            disabled={busy || !input.trim()}
            className="px-6 py-3 rounded-lg bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold disabled:opacity-40"
          >
            {busy ? '...' : 'إرسال'}
          </button>
        </div>

        <div className="mt-3 text-xs opacity-50 text-center">
          <p>المختبر يتجاوز: Brain orchestrator · Workflow stages · Discovery · Mockup phases · Post-write audits</p>
          <p>يبقى فقط: نفس الـ3 موديل (Claude / GPT / GLM) + كل الأدوات + Smart-Merge</p>
        </div>
      </div>
    </div>
  );
}
