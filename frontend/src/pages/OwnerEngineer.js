/**
 * OwnerEngineer — مهندس المالك الشخصي (Owner Engineer Portal)
 *
 * Cross-platform oversight dashboard for the platform owner:
 *   • Browse EVERY project on the server (any user)
 *   • Open a project → live iframe preview + AI chat scoped to it
 *   • Ask the AI (Claude Sonnet 4.5) for analysis, code reads, search
 *   • Persistent chat sessions in `owner_chat_sessions`
 *
 * Visually inherits FreeBuildChat's dark + amber/emerald palette but is a
 * dedicated single-purpose console — no design tweaks to existing apps.
 */
import React, { useEffect, useMemo, useRef, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Send, ArrowRight, Sparkles, Wrench, FolderOpen, BarChart3, Search,
  RefreshCw, ExternalLink, Layers, User as UserIcon, Eye,
  Activity, AlertTriangle, Power, ShieldCheck, X, Check, ListChecks,
  Image as ImageIcon, Film, Gamepad2, Globe, Paperclip, Mic, Square,
  MessageCircle, Tv2, ChevronDown, Plus,
} from 'lucide-react';
import { toast } from 'sonner';

const API = process.env.REACT_APP_BACKEND_URL;
const BASE = `${API}/api/freebuild-chat/owner/engineer`;

const fmt = (s) => (s ? String(s).slice(0, 16).replace('T', ' ') : '—');

export default function OwnerEngineer({ user }) {
  const nav = useNavigate();

  // Auth gate.
  useEffect(() => {
    const role = (user?.role || '').toLowerCase();
    if (!['owner', 'admin', 'superuser', 'super_admin'].includes(role) && !user?.is_owner) {
      toast.error('هذا القسم خاص بالمالك');
      nav('/');
    }
  }, [user, nav]);

  // ── Projects sidebar state ─────────────────────────────────────────
  const [projects, setProjects] = useState([]);
  const [projLoading, setProjLoading] = useState(false);
  const [query, setQuery] = useState('');
  const [activeProject, setActiveProject] = useState(null); // {id,name,owner_email,published_slug,...}
  const [projectDetail, setProjectDetail] = useState(null);
  const [stats, setStats] = useState(null);
  const [independence, setIndependence] = useState(null);

  // ── Chat state ─────────────────────────────────────────────────────
  const [sessions, setSessions] = useState([]);
  const [activeSession, setActiveSession] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [busy, setBusy] = useState(false);
  const scrollerRef = useRef(null);

  // ── Owner-Engineer dashboard state ─────────────────────────────────
  const [dailyReport, setDailyReport] = useState(null);
  const [errorAnalysis, setErrorAnalysis] = useState(null);
  const [maintenance, setMaintenance] = useState([]); // [{section, active, ...}]
  const [patches, setPatches] = useState([]);
  const [dashLoading, setDashLoading] = useState(false);

  // ── New layout state (2026-06 redesign) ────────────────────────────
  const [activeView, setActiveView] = useState('chat'); // 'chat' | 'reports' | 'live'
  const [showSessionsMenu, setShowSessionsMenu] = useState(false);
  const [showProjectsMenu, setShowProjectsMenu] = useState(false);
  const [attachedFile, setAttachedFile] = useState(null); // {name, size, dataUrl?}
  const [recording, setRecording] = useState(false);
  const [recElapsed, setRecElapsed] = useState(0); // seconds
  const mediaRecorderRef = useRef(null);
  const recChunksRef = useRef([]);
  const recTimerRef = useRef(null);
  const fileInputRef = useRef(null);

  const authHeaders = useMemo(() => {
    const token = localStorage.getItem('token');
    return { Authorization: `Bearer ${token}` };
  }, []);

  // ── Loaders ────────────────────────────────────────────────────────
  const loadProjects = async (q = '') => {
    setProjLoading(true);
    try {
      const url = q
        ? `${BASE}/projects?q=${encodeURIComponent(q)}&limit=50`
        : `${BASE}/projects?limit=50`;
      const r = await fetch(url, { headers: authHeaders });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const d = await r.json();
      setProjects(d.projects || d.matches || []);
    } catch (e) {
      toast.error('فشل تحميل المشاريع');
    } finally {
      setProjLoading(false);
    }
  };

  const loadStats = async () => {
    try {
      const r = await fetch(`${BASE}/stats`, { headers: authHeaders });
      if (r.ok) setStats(await r.json());
    } catch { /* non-critical */ }
    try {
      const r2 = await fetch(`${BASE}/independence`, { headers: authHeaders });
      if (r2.ok) setIndependence(await r2.json());
    } catch { /* non-critical */ }
  };

  const loadSessions = async () => {
    try {
      const r = await fetch(`${BASE}/sessions`, { headers: authHeaders });
      if (r.ok) {
        const d = await r.json();
        setSessions(d.sessions || []);
      }
    } catch { /* non-critical */ }
  };

  // ── Owner-Engineer dashboard loaders ───────────────────────────────
  const loadDashboard = useCallback(async () => {
    setDashLoading(true);
    try {
      const [r1, r2, r3, r4] = await Promise.all([
        fetch(`${BASE}/daily-report?hours=24`, { headers: authHeaders }),
        fetch(`${BASE}/error-analysis?period_hours=24&min_repeats=2`, { headers: authHeaders }),
        fetch(`${BASE}/maintenance`, { headers: authHeaders }),
        fetch(`${BASE}/patches`, { headers: authHeaders }),
      ]);
      if (r1.ok) setDailyReport(await r1.json());
      if (r2.ok) setErrorAnalysis(await r2.json());
      if (r3.ok) {
        const d = await r3.json();
        setMaintenance(d.modes || []);
      }
      if (r4.ok) {
        const d = await r4.json();
        setPatches(d.patches || []);
      }
    } catch (e) {
      // non-critical
    } finally {
      setDashLoading(false);
    }
  }, [authHeaders]);

  const toggleMaintenance = async (section, currentlyActive) => {
    try {
      const url = currentlyActive
        ? `${BASE}/maintenance/exit`
        : `${BASE}/maintenance/enter`;
      const fd = new FormData();
      fd.append('section', section);
      if (!currentlyActive) {
        fd.append('duration_minutes', '30');
        fd.append('banner_ar', `⚙️ قسم «${section}» في تحديث جزئي — راح يرجع خلال 30 دقيقة.`);
      }
      const r = await fetch(url, { method: 'POST', headers: authHeaders, body: fd });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      toast.success(currentlyActive ? `✅ تم تشغيل قسم ${section}` : `🔧 قسم ${section} في وضع الصيانة`);
      await loadDashboard();
    } catch (e) {
      toast.error('فشل تغيير حالة الصيانة');
    }
  };

  const reviewPatch = async (patchId, action /* 'approve'|'reject' */) => {
    try {
      const r = await fetch(`${BASE}/patches/${patchId}/${action}`, {
        method: 'POST', headers: authHeaders,
      });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      toast.success(action === 'approve' ? '✅ تم اعتماد الاقتراح' : '❌ تم رفض الاقتراح');
      await loadDashboard();
    } catch (e) {
      toast.error('فشل تحديث الاقتراح');
    }
  };

  // ── File upload ────────────────────────────────────────────────────
  const handleFileSelect = (e) => {
    const f = e.target.files?.[0];
    if (!f) return;
    if (f.size > 10 * 1024 * 1024) {
      toast.error('الحد الأقصى 10MB');
      return;
    }
    const reader = new FileReader();
    reader.onload = (ev) => {
      setAttachedFile({
        name: f.name, size: f.size, type: f.type, dataUrl: ev.target.result,
      });
      toast.success(`📎 تم إرفاق: ${f.name}`);
    };
    reader.readAsDataURL(f);
    e.target.value = ''; // reset
  };

  // ── Voice recording (MediaRecorder → Whisper) ──────────────────────
  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mr = new MediaRecorder(stream, { mimeType: 'audio/webm' });
      recChunksRef.current = [];
      mr.ondataavailable = (e) => { if (e.data.size > 0) recChunksRef.current.push(e.data); };
      mr.onstop = async () => {
        try {
          const blob = new Blob(recChunksRef.current, { type: 'audio/webm' });
          stream.getTracks().forEach((t) => t.stop());
          if (blob.size < 200) {
            toast.error('التسجيل قصير جداً');
            return;
          }
          toast.info('⏳ يحوّل الصوت لنص...');
          const fd = new FormData();
          fd.append('audio', blob, 'voice.webm');
          fd.append('language', 'ar');
          const r = await fetch(`${API}/api/stt/transcribe`, {
            method: 'POST', headers: authHeaders, body: fd,
          });
          if (!r.ok) throw new Error('STT failed');
          const d = await r.json();
          if (d.text) {
            setInput((prev) => (prev ? `${prev} ${d.text}` : d.text));
            toast.success('✅ تم النسخ');
          }
        } catch (err) {
          toast.error('فشل تحويل الصوت');
        }
      };
      mr.start();
      mediaRecorderRef.current = mr;
      setRecording(true);
      setRecElapsed(0);
      recTimerRef.current = setInterval(() => setRecElapsed((s) => s + 1), 1000);
    } catch (e) {
      toast.error('ما قدرنا نوصل للمايكروفون');
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && recording) {
      mediaRecorderRef.current.stop();
      mediaRecorderRef.current = null;
      setRecording(false);
      if (recTimerRef.current) {
        clearInterval(recTimerRef.current);
        recTimerRef.current = null;
      }
    }
  };

  // Cleanup on unmount.
  useEffect(() => {
    return () => {
      if (recTimerRef.current) clearInterval(recTimerRef.current);
      if (mediaRecorderRef.current) {
        try { mediaRecorderRef.current.stop(); } catch { /* ignored */ }
      }
    };
  }, []);

  useEffect(() => {
    loadProjects();
    loadStats();
    loadSessions();
  }, []);

  // Debounced search.
  useEffect(() => {
    const t = setTimeout(() => loadProjects(query.trim()), 350);
    return () => clearTimeout(t);
  }, [query]);

  // Auto-scroll chat.
  useEffect(() => {
    if (scrollerRef.current) scrollerRef.current.scrollTop = scrollerRef.current.scrollHeight;
  }, [messages]);

  // Select a project → fetch its detail.
  const selectProject = async (p) => {
    setActiveProject(p);
    setProjectDetail(null);
    try {
      const r = await fetch(`${BASE}/projects/${p.id}`, { headers: authHeaders });
      if (r.ok) setProjectDetail(await r.json());
    } catch { /* non-critical */ }
  };

  const openSession = async (sid) => {
    try {
      const r = await fetch(`${BASE}/sessions/${sid}`, { headers: authHeaders });
      if (r.ok) {
        const d = await r.json();
        setActiveSession(sid);
        setMessages(d.messages || []);
      }
    } catch {
      toast.error('فشل تحميل المحادثة');
    }
  };

  const newChat = () => {
    setActiveSession(null);
    setMessages([]);
  };

  // ── Send a chat message (SSE stream) ───────────────────────────────
  const send = async () => {
    const text = input.trim();
    if ((!text && !attachedFile) || busy) return;
    setBusy(true);
    setInput('');
    const fileLabel = attachedFile ? `📎 ${attachedFile.name}` : '';
    const composed = [text, fileLabel].filter(Boolean).join('\n');
    setMessages((m) => [...m, { role: 'user', content: composed }]);
    const fileSnapshot = attachedFile;
    setAttachedFile(null);

    try {
      const form = new FormData();
      // If a file was attached, prepend a marker so the AI knows.
      const fullMessage = fileSnapshot
        ? `${text}\n\n[ملف مُرفق: ${fileSnapshot.name} (${(fileSnapshot.size / 1024).toFixed(1)} KB، نوع: ${fileSnapshot.type})]`
        : text;
      form.append('message', fullMessage || '(ملف فقط)');
      if (activeSession) form.append('session_id', activeSession);
      if (activeProject?.id) form.append('project_id', activeProject.id);
      const r = await fetch(`${BASE}/chat`, {
        method: 'POST', headers: authHeaders, body: form,
      });
      if (!r.ok || !r.body) {
        toast.error('فشل الاتصال بالمهندس');
        setBusy(false);
        return;
      }
      const reader = r.body.getReader();
      const decoder = new TextDecoder();
      let buf = '';
      let toolEvents = [];
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buf += decoder.decode(value, { stream: true });
        const lines = buf.split('\n');
        buf = lines.pop();
        let currentEv = null;
        for (const line of lines) {
          if (line.startsWith('event: ')) currentEv = line.slice(7).trim();
          else if (line.startsWith('data: ')) {
            try {
              const d = JSON.parse(line.slice(6));
              if (currentEv === 'start' && d.session_id) setActiveSession(d.session_id);
              else if (currentEv === 'tool') toolEvents.push({ kind: 'tool', name: d.name, args: d.args });
              else if (currentEv === 'tool_result') {
                toolEvents.push({
                  kind: 'result', name: d.name, ok: d.result?.ok,
                  summary: JSON.stringify(d.result).slice(0, 240),
                });
              } else if (currentEv === 'text') {
                setMessages((m) => [...m, { role: 'assistant', content: d.content, tool_events: toolEvents }]);
                toolEvents = [];
                loadSessions();
              } else if (currentEv === 'error') {
                toast.error(d.message || 'حدث خطأ');
              }
            } catch { /* ignore parse error */ }
          }
        }
      }
    } catch (e) {
      toast.error(String(e?.message || e));
    } finally {
      setBusy(false);
    }
  };

  const liveUrl = projectDetail?.live_url || (activeProject?.published_slug ? `https://zenrex.ai/s/${activeProject.published_slug}` : null);

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100" dir="rtl" data-testid="owner-engineer-page">
      {/* Topbar */}
      <header className="border-b border-zinc-800 px-4 py-3 flex items-center justify-between bg-zinc-950/90 backdrop-blur sticky top-0 z-20">
        <button type="button" onClick={() => nav('/admin')} className="flex items-center gap-2 text-zinc-400 hover:text-white text-sm" data-testid="back-btn">
          <ArrowRight className="w-4 h-4" />
          <span>لوحة الإدارة</span>
        </button>
        <div className="flex items-center gap-2 text-amber-300 font-bold">
          <Wrench className="w-5 h-5" />
          <span>مهندس Zenrex — بوابة المالك</span>
          <Sparkles className="w-4 h-4 text-amber-400 animate-pulse" />
        </div>
        <div className="flex items-center gap-2">
          {independence && (
            <span
              data-testid="independence-badge"
              title={independence.message}
              className={`text-[10px] font-bold px-2 py-1 rounded-full border ${
                independence.independent
                  ? 'bg-emerald-500/15 text-emerald-200 border-emerald-400/40'
                  : 'bg-amber-500/15 text-amber-200 border-amber-400/40'
              }`}
            >
              {independence.independent ? '🟢 مستقل 100%' : '🟡 Emergent'}
            </span>
          )}
          {stats && (
            <span className="text-[10px] text-zinc-500 hidden sm:inline">
              {stats.total_projects} مشروع · {stats.published_projects} منشور · {stats.total_users} مستخدم
            </span>
          )}

          {/* 📁 Projects dropdown (compact) */}
          <div className="relative">
            <button
              type="button"
              onClick={() => { setShowProjectsMenu((v) => !v); setShowSessionsMenu(false); }}
              data-testid="projects-dropdown-toggle"
              className="text-xs bg-zinc-900 border border-zinc-700 hover:border-amber-400/40 text-zinc-300 hover:text-amber-200 px-3 py-1.5 rounded-lg flex items-center gap-1.5"
            >
              <FolderOpen className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">المشاريع</span>
              <span className="text-[10px] text-zinc-500">({projects.length})</span>
              <ChevronDown className="w-3 h-3" />
            </button>
            {showProjectsMenu && (
              <div className="absolute top-full mt-1 left-0 w-80 max-h-[420px] bg-zinc-950 border border-zinc-700 rounded-xl shadow-2xl z-30 overflow-hidden" data-testid="projects-menu">
                <div className="p-2 border-b border-zinc-800">
                  <div className="relative">
                    <Search className="absolute right-2 top-2 w-3.5 h-3.5 text-zinc-500" />
                    <input
                      value={query}
                      onChange={(e) => setQuery(e.target.value)}
                      placeholder="ابحث..."
                      data-testid="project-search"
                      className="w-full bg-zinc-900 border border-zinc-800 rounded-lg pr-7 pl-2 py-1 text-xs text-zinc-100 placeholder-zinc-600 focus:outline-none focus:border-amber-400/50"
                    />
                  </div>
                </div>
                <div className="max-h-[340px] overflow-y-auto p-1">
                  {projects.length === 0 ? (
                    <p className="text-[11px] text-zinc-600 px-2 py-6 text-center">لا توجد مشاريع.</p>
                  ) : (
                    projects.map((p) => (
                      <button
                        key={p.id}
                        type="button"
                        onClick={() => { selectProject(p); setShowProjectsMenu(false); }}
                        data-testid={`project-${p.id}`}
                        className={`w-full text-right text-[11px] px-2 py-1.5 rounded-md transition-all flex items-center gap-1.5 ${
                          activeProject?.id === p.id
                            ? 'bg-amber-500/15 text-amber-100'
                            : 'hover:bg-zinc-900 text-zinc-300'
                        }`}
                      >
                        {p.published_slug && <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 shrink-0" />}
                        <span className="truncate flex-1">{p.name || '(بدون اسم)'}</span>
                        <span className="text-[9px] text-zinc-500 shrink-0">{p.mode || '—'}</span>
                      </button>
                    ))
                  )}
                </div>
              </div>
            )}
          </div>

          {/* 📜 Sessions dropdown */}
          <div className="relative">
            <button
              type="button"
              onClick={() => { setShowSessionsMenu((v) => !v); setShowProjectsMenu(false); }}
              data-testid="sessions-dropdown-toggle"
              className="text-xs bg-zinc-900 border border-zinc-700 hover:border-violet-400/40 text-zinc-300 hover:text-violet-200 px-3 py-1.5 rounded-lg flex items-center gap-1.5"
            >
              <MessageCircle className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">السابقات</span>
              <span className="text-[10px] text-zinc-500">({sessions.length})</span>
              <ChevronDown className="w-3 h-3" />
            </button>
            {showSessionsMenu && (
              <div className="absolute top-full mt-1 left-0 w-80 max-h-[420px] bg-zinc-950 border border-zinc-700 rounded-xl shadow-2xl z-30 overflow-hidden" data-testid="sessions-menu">
                <div className="px-3 py-2 border-b border-zinc-800 flex items-center justify-between">
                  <span className="text-[11px] text-zinc-500 font-bold">المحادثات السابقة</span>
                  <button
                    type="button"
                    onClick={() => { newChat(); setShowSessionsMenu(false); }}
                    data-testid="new-chat-from-menu"
                    className="text-[10px] text-emerald-300 hover:text-emerald-200 flex items-center gap-1"
                  >
                    <Plus className="w-3 h-3" /> جديدة
                  </button>
                </div>
                <div className="max-h-[360px] overflow-y-auto p-1">
                  {sessions.length === 0 ? (
                    <p className="text-[11px] text-zinc-600 px-2 py-6 text-center">لا توجد محادثات سابقة بعد.</p>
                  ) : (
                    sessions.map((s) => (
                      <button
                        key={s.id}
                        type="button"
                        onClick={() => { openSession(s.id); setShowSessionsMenu(false); setActiveView('chat'); }}
                        data-testid={`session-${s.id}`}
                        className={`w-full text-right text-[11px] px-2 py-1.5 rounded-md ${
                          activeSession === s.id
                            ? 'bg-violet-500/15 text-violet-100'
                            : 'hover:bg-zinc-900 text-zinc-300'
                        }`}
                      >
                        <div className="truncate font-bold">{s.messages?.[0]?.content?.slice(0, 50) || 'محادثة'}</div>
                        <div className="text-[9px] text-zinc-500 mt-0.5">{fmt(s.updated_at)}</div>
                      </button>
                    ))
                  )}
                </div>
              </div>
            )}
          </div>

          <button
            type="button"
            onClick={newChat}
            data-testid="new-chat-btn"
            className="text-xs bg-emerald-500/20 border border-emerald-400/40 text-emerald-200 px-3 py-1.5 rounded-lg hover:bg-emerald-500/30"
          >
            + جديدة
          </button>
        </div>
      </header>

      {/* ─── Tab bar (chat / reports / live) ───────────────────────── */}
      <nav className="border-b border-zinc-800 bg-zinc-950/60 backdrop-blur sticky top-[58px] z-10 px-4 flex items-center gap-1" data-testid="owner-view-tabs">
        <ViewTab id="chat" current={activeView} setCurrent={setActiveView}
          icon={MessageCircle} label="محادثة"
          tone="amber" />
        <ViewTab id="reports" current={activeView} setCurrent={setActiveView}
          icon={BarChart3} label="تقارير فعلية"
          tone="emerald" />
        <ViewTab id="live" current={activeView} setCurrent={setActiveView}
          icon={Tv2} label="لايف 📺"
          tone="rose"
          badge={activeProject?.published_slug ? null : '⚠️'} />
        {activeProject && (
          <div className="mr-auto flex items-center gap-2 text-xs">
            <span className="text-amber-200 font-bold flex items-center gap-1">
              <FolderOpen className="w-3 h-3" /> {activeProject.name}
            </span>
            <button
              type="button"
              onClick={() => { setActiveProject(null); setProjectDetail(null); }}
              className="text-zinc-500 hover:text-rose-300 text-[10px]"
            >
              ✕ إلغاء
            </button>
          </div>
        )}
      </nav>

      {/* ─── Main area: chat | reports | live ──────────────────────── */}
      <main className="flex flex-col min-h-[calc(100vh-118px)]" data-testid={`view-${activeView}`}>
        {activeView === 'chat' && (
          <ChatView
            messages={messages}
            busy={busy}
            input={input}
            setInput={setInput}
            send={send}
            scrollerRef={scrollerRef}
            activeProject={activeProject}
            attachedFile={attachedFile}
            setAttachedFile={setAttachedFile}
            fileInputRef={fileInputRef}
            onFileSelect={handleFileSelect}
            recording={recording}
            recElapsed={recElapsed}
            startRecording={startRecording}
            stopRecording={stopRecording}
          />
        )}

        {activeView === 'reports' && (
          <ReportsView
            report={dailyReport}
            errors={errorAnalysis}
            maintenance={maintenance}
            patches={patches}
            loading={dashLoading}
            onRefresh={loadDashboard}
            onToggleMaintenance={toggleMaintenance}
            onReviewPatch={reviewPatch}
            onAskAI={(prompt) => { setInput(prompt); setActiveView('chat'); }}
          />
        )}

        {activeView === 'live' && (
          <LiveView
            project={activeProject}
            projectDetail={projectDetail}
            messages={messages}
            busy={busy}
            input={input}
            setInput={setInput}
            send={send}
            attachedFile={attachedFile}
            setAttachedFile={setAttachedFile}
            fileInputRef={fileInputRef}
            onFileSelect={handleFileSelect}
            recording={recording}
            recElapsed={recElapsed}
            startRecording={startRecording}
            stopRecording={stopRecording}
          />
        )}
      </main>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────
// ViewTab — single tab pill in the view-tab bar.
// ─────────────────────────────────────────────────────────────────
function ViewTab({ id, current, setCurrent, icon: Icon, label, tone, badge }) {
  const active = current === id;
  const tones = {
    amber: active ? 'text-amber-300 border-amber-400' : 'text-zinc-500 border-transparent hover:text-amber-200',
    emerald: active ? 'text-emerald-300 border-emerald-400' : 'text-zinc-500 border-transparent hover:text-emerald-200',
    rose: active ? 'text-rose-300 border-rose-400' : 'text-zinc-500 border-transparent hover:text-rose-200',
  };
  return (
    <button
      type="button"
      onClick={() => setCurrent(id)}
      data-testid={`tab-${id}`}
      className={`px-4 py-3 text-sm font-bold border-b-2 flex items-center gap-2 transition-all ${tones[tone]}`}
    >
      <Icon className="w-4 h-4" />
      <span>{label}</span>
      {badge && <span className="text-[10px]">{badge}</span>}
    </button>
  );
}


// ═════════════════════════════════════════════════════════════════
// ChatView — wide, centered chat with file/voice/send composer.
// ═════════════════════════════════════════════════════════════════
function ChatView({
  messages, busy, input, setInput, send,
  scrollerRef, activeProject,
  attachedFile, setAttachedFile,
  fileInputRef, onFileSelect,
  recording, recElapsed, startRecording, stopRecording,
}) {
  const suggestions = activeProject
    ? [
        'اعطني ملخص هذا المشروع',
        'اقرأ index.html واخبرني وش فيه',
        'هل هذا المشروع منشور؟',
        'مين صاحبه؟',
      ]
    : [
        '🩺 أعطني تقرير اليوم الكامل',
        '🐛 ليش الذكاء الصناعي يكرر نفس الخطأ؟ حلل آخر 24 ساعة',
        '⚙️ شغّل وضع الصيانة على قسم الفيديوهات نص ساعة',
        '📋 شو الاقتراحات المعلقة لإصلاح الـ AI؟',
      ];

  return (
    <div className="flex flex-col flex-1 bg-zinc-950" data-testid="chat-view">
      <div ref={scrollerRef} className="flex-1 overflow-y-auto p-4 sm:p-8 space-y-4">
        <div className="max-w-4xl mx-auto w-full space-y-4">
          {messages.length === 0 ? (
            <div className="text-center py-16">
              <Wrench className="w-16 h-16 mx-auto mb-4 text-amber-400/30" />
              <p className="text-zinc-200 font-bold text-lg mb-2">المهندس بانتظار أوامرك</p>
              <p className="text-xs text-zinc-500 mb-8">
                {activeProject
                  ? `سؤالك مرتبط حالياً بمشروع: ${activeProject.name}`
                  : 'اختر مشروعاً من قائمة المشاريع، أو اسأل سؤالاً عاماً.'}
              </p>
              <div className="flex flex-wrap gap-2 justify-center max-w-2xl mx-auto">
                {suggestions.map((q, i) => (
                  <button
                    key={i}
                    type="button"
                    onClick={() => setInput(q)}
                    data-testid={`suggest-${i}`}
                    className="text-xs bg-zinc-900 border border-zinc-700 text-zinc-300 px-3 py-2 rounded-lg hover:border-amber-400/40 hover:text-amber-200"
                  >
                    {q}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            messages.map((m, i) => (
              <div key={i} className={m.role === 'user' ? 'flex justify-start' : 'flex justify-end'} data-testid={`msg-${i}`}>
                <div
                  className={`max-w-[85%] rounded-2xl px-5 py-4 text-sm whitespace-pre-wrap leading-7 ${
                    m.role === 'user'
                      ? 'bg-emerald-500/15 text-emerald-100 border border-emerald-400/30'
                      : 'bg-zinc-900 text-zinc-200 border border-zinc-800'
                  }`}
                >
                  {(m.tool_events || []).length > 0 && (
                    <div className="mb-2 space-y-1">
                      {m.tool_events.map((te, j) => (
                        <div
                          key={j}
                          className="text-[10px] bg-amber-500/10 border border-amber-500/30 rounded px-2 py-1 text-amber-200 font-mono"
                        >
                          {te.kind === 'tool'
                            ? `⚙️ ${te.name}(${JSON.stringify(te.args).slice(0, 90)})`
                            : `${te.ok ? '✓' : '✗'} ${te.name}: ${te.summary}`}
                        </div>
                      ))}
                    </div>
                  )}
                  {m.content}
                </div>
              </div>
            ))
          )}

          {busy && (
            <div className="flex justify-end">
              <div className="bg-zinc-900 border border-zinc-800 rounded-2xl px-5 py-4 text-sm text-zinc-500">
                <span className="animate-pulse">المهندس يفكّر...</span>
              </div>
            </div>
          )}
        </div>
      </div>

      <Composer
        input={input} setInput={setInput} send={send} busy={busy}
        attachedFile={attachedFile} setAttachedFile={setAttachedFile}
        fileInputRef={fileInputRef} onFileSelect={onFileSelect}
        recording={recording} recElapsed={recElapsed}
        startRecording={startRecording} stopRecording={stopRecording}
        activeProject={activeProject}
      />
    </div>
  );
}


// ═════════════════════════════════════════════════════════════════
// Composer — text + 📎 file + 🎙️ voice + ▶ send.
// ═════════════════════════════════════════════════════════════════
function Composer({
  input, setInput, send, busy,
  attachedFile, setAttachedFile,
  fileInputRef, onFileSelect,
  recording, recElapsed, startRecording, stopRecording,
  activeProject,
}) {
  return (
    <div className="border-t border-zinc-800 p-3 sm:p-4 bg-zinc-950/90 backdrop-blur" data-testid="composer">
      <div className="max-w-4xl mx-auto">
        {/* Attached file preview */}
        {attachedFile && (
          <div className="mb-2 flex items-center gap-2 bg-amber-500/10 border border-amber-400/30 rounded-lg px-3 py-2 text-xs" data-testid="attached-file">
            <Paperclip className="w-3.5 h-3.5 text-amber-300" />
            <span className="text-amber-100 truncate flex-1">{attachedFile.name}</span>
            <span className="text-zinc-500 text-[10px]">{(attachedFile.size / 1024).toFixed(1)} KB</span>
            <button
              type="button"
              onClick={() => setAttachedFile(null)}
              data-testid="remove-attached-file"
              className="text-zinc-500 hover:text-rose-300 p-0.5"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
        )}

        {/* Recording indicator */}
        {recording && (
          <div className="mb-2 flex items-center gap-2 bg-rose-500/10 border border-rose-400/30 rounded-lg px-3 py-2 text-xs" data-testid="recording-indicator">
            <span className="w-2 h-2 rounded-full bg-rose-400 animate-pulse" />
            <span className="text-rose-200 font-bold">يسجّل... {Math.floor(recElapsed / 60)}:{String(recElapsed % 60).padStart(2, '0')}</span>
            <button
              type="button"
              onClick={stopRecording}
              data-testid="stop-recording"
              className="mr-auto text-[11px] bg-rose-500/30 hover:bg-rose-500/50 border border-rose-400/40 text-rose-100 px-2 py-0.5 rounded font-bold flex items-center gap-1"
            >
              <Square className="w-3 h-3" /> إيقاف
            </button>
          </div>
        )}

        <div className="flex items-end gap-2">
          <input
            type="file"
            ref={fileInputRef}
            onChange={onFileSelect}
            className="hidden"
            data-testid="file-input"
            accept="image/*,.pdf,.txt,.md,.json,.csv,.html,.js,.py,.zip"
          />
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            data-testid="attach-file-btn"
            disabled={busy || recording}
            className="p-3 rounded-xl bg-zinc-900 border border-zinc-700 text-zinc-400 hover:text-amber-200 hover:border-amber-400/40 disabled:opacity-40"
            title="إرفاق ملف"
          >
            <Paperclip className="w-4 h-4" />
          </button>
          <button
            type="button"
            onClick={recording ? stopRecording : startRecording}
            data-testid={recording ? 'stop-voice-btn' : 'start-voice-btn'}
            disabled={busy}
            className={`p-3 rounded-xl border disabled:opacity-40 ${
              recording
                ? 'bg-rose-500/30 border-rose-400/50 text-rose-100 animate-pulse'
                : 'bg-zinc-900 border-zinc-700 text-zinc-400 hover:text-rose-300 hover:border-rose-400/40'
            }`}
            title={recording ? 'إيقاف التسجيل' : 'تسجيل صوتي'}
          >
            {recording ? <Square className="w-4 h-4" /> : <Mic className="w-4 h-4" />}
          </button>
          <textarea
            data-testid="owner-chat-input"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                send();
              }
            }}
            placeholder={activeProject ? `اسأل عن "${activeProject.name}"...` : 'اكتب أمرك للمهندس...'}
            rows={2}
            className="flex-1 bg-zinc-900 border border-zinc-700 focus:border-amber-400/50 rounded-xl px-4 py-3 text-sm text-zinc-100 placeholder-zinc-600 resize-none focus:outline-none"
          />
          <button
            type="button"
            onClick={send}
            disabled={busy || (!input.trim() && !attachedFile)}
            data-testid="owner-chat-send"
            className="px-4 py-3 rounded-xl bg-gradient-to-r from-amber-500 to-orange-500 hover:from-amber-400 hover:to-orange-400 text-zinc-950 font-bold disabled:opacity-40 disabled:cursor-not-allowed flex items-center gap-2"
          >
            <Send className="w-4 h-4" />
            <span className="hidden sm:inline">إرسال</span>
          </button>
        </div>
      </div>
    </div>
  );
}


// ═════════════════════════════════════════════════════════════════
// ReportsView — daily-report widgets + maintenance + patches inbox.
// ═════════════════════════════════════════════════════════════════
function ReportsView({ report, errors, maintenance, patches, loading, onRefresh, onToggleMaintenance, onReviewPatch, onAskAI }) {
  return (
    <div className="flex-1 overflow-y-auto p-4 sm:p-6" data-testid="reports-view">
      <DashboardStrip
        report={report} errors={errors} maintenance={maintenance} patches={patches}
        loading={loading} onRefresh={onRefresh}
        onToggleMaintenance={onToggleMaintenance}
        onReviewPatch={onReviewPatch}
        onAskAI={onAskAI}
      />

      <div className="max-w-5xl mx-auto mt-6 grid md:grid-cols-2 gap-4">
        {/* Recent published projects */}
        <div className="bg-zinc-900/50 border border-zinc-800 rounded-xl p-4">
          <h3 className="text-sm font-bold text-cyan-300 mb-3 flex items-center gap-2">
            <Sparkles className="w-4 h-4" /> آخر المشاريع المنشورة (24 ساعة)
          </h3>
          {!report?.recent_published?.length ? (
            <p className="text-xs text-zinc-500 text-center py-6">لا يوجد منشور خلال 24 ساعة الماضية.</p>
          ) : (
            <ul className="space-y-1.5">
              {report.recent_published.map((p) => (
                <li key={p.id} data-testid={`recent-pub-${p.id}`} className="flex items-center gap-2 text-xs">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 shrink-0" />
                  <span className="text-zinc-200 truncate flex-1">{p.name || p.id}</span>
                  <span className="text-zinc-500 text-[10px]">v{p.published_version}</span>
                  <span className="text-zinc-500 text-[10px]">{p.owner_email?.slice(0, 20) || '—'}</span>
                </li>
              ))}
            </ul>
          )}
        </div>

        {/* Error patterns analysis */}
        <div className="bg-zinc-900/50 border border-zinc-800 rounded-xl p-4">
          <h3 className="text-sm font-bold text-amber-300 mb-3 flex items-center gap-2">
            <AlertTriangle className="w-4 h-4" /> أنماط أخطاء الذكاء الصناعي (24 ساعة)
          </h3>
          {!errors?.patterns_with_repeats?.length ? (
            <p className="text-xs text-emerald-400 text-center py-6">✅ ما فيه أنماط خطأ متكررة. الذكاء الصناعي يشتغل تمام.</p>
          ) : (
            <ul className="space-y-2">
              {errors.patterns_with_repeats.map((p, i) => (
                <li key={i} data-testid={`error-pattern-${i}`} className="bg-amber-500/5 border border-amber-400/30 rounded-lg p-2 text-xs">
                  <div className="font-bold text-amber-200 flex items-center justify-between">
                    <span>{p.pattern}</span>
                    <span className="text-[10px] bg-amber-500/20 px-1.5 py-0.5 rounded">{p.occurrences}×</span>
                  </div>
                  <p className="text-[10px] text-zinc-500 mt-1">أول ظهور: {p.first_seen_project?.slice(0, 12) || '—'}</p>
                </li>
              ))}
            </ul>
          )}
          {!!errors?.recommendations?.length && (
            <div className="mt-3 pt-3 border-t border-zinc-800">
              <p className="text-[10px] font-bold text-emerald-300 mb-1">💡 توصيات:</p>
              <ul className="text-[11px] text-zinc-400 space-y-0.5">
                {errors.recommendations.map((r, i) => (
                  <li key={i}>· {r}</li>
                ))}
              </ul>
            </div>
          )}
        </div>

        {/* Tool failure samples */}
        {!!report?.tool_failure_samples?.length && (
          <div className="bg-zinc-900/50 border border-rose-400/20 rounded-xl p-4 md:col-span-2">
            <h3 className="text-sm font-bold text-rose-300 mb-3 flex items-center gap-2">
              <AlertTriangle className="w-4 h-4" /> عينات من فشل الأدوات (آخر 24 ساعة)
            </h3>
            <ul className="space-y-1.5">
              {report.tool_failure_samples.map((s, i) => (
                <li key={i} className="text-[11px] bg-rose-500/5 border border-rose-400/20 rounded p-2">
                  <code className="text-rose-200">{s.project_id?.slice(0, 12) || '—'}</code>
                  <span className="text-zinc-500 mx-2">·</span>
                  <span className="text-zinc-400">{s.snippet?.slice(0, 200)}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}


// ═════════════════════════════════════════════════════════════════
// LiveView — iframe preview of a project + chat side-by-side for
// real-time troubleshooting with the owner.
// ═════════════════════════════════════════════════════════════════
function LiveView({
  project, projectDetail, messages, busy, input, setInput, send,
  attachedFile, setAttachedFile, fileInputRef, onFileSelect,
  recording, recElapsed, startRecording, stopRecording,
}) {
  if (!project) {
    return (
      <div className="flex-1 flex items-center justify-center bg-zinc-950 p-6" data-testid="live-empty">
        <div className="text-center max-w-md">
          <Tv2 className="w-16 h-16 mx-auto mb-4 text-rose-400/30" />
          <p className="text-zinc-200 font-bold text-lg mb-2">اختر مشروعاً أولاً</p>
          <p className="text-xs text-zinc-500">
            افتح قائمة «المشاريع» من الأعلى واختر مشروعاً عشان نشوفه لايف ونعالج أي مشكلة معاً.
          </p>
        </div>
      </div>
    );
  }

  const liveUrl = projectDetail?.live_url || (project?.published_slug ? `https://zenrex.ai/s/${project.published_slug}` : null);

  return (
    <div className="flex-1 grid lg:grid-cols-[1fr,460px] grid-cols-1 bg-zinc-950" data-testid="live-view">
      {/* Live iframe */}
      <div className="flex flex-col border-l border-zinc-800">
        <div className="px-3 py-2 border-b border-zinc-800 bg-zinc-900/60 flex items-center justify-between text-xs">
          <div className="flex items-center gap-2 text-rose-200">
            <Tv2 className="w-3.5 h-3.5" />
            <span className="font-bold">{project.name}</span>
            {projectDetail && (
              <span className="text-zinc-500">· v{projectDetail.published_version || '—'} · {projectDetail.page_count || 0} صفحة</span>
            )}
          </div>
          {liveUrl && (
            <a href={liveUrl} target="_blank" rel="noreferrer" className="text-emerald-300 hover:text-emerald-200 flex items-center gap-1 text-[11px]" data-testid="live-open-tab">
              <ExternalLink className="w-3 h-3" /> فتح في تبويب جديد
            </a>
          )}
        </div>
        {liveUrl ? (
          <iframe
            src={liveUrl}
            title="live-preview"
            className="flex-1 w-full bg-white"
            data-testid="live-iframe"
          />
        ) : (
          <div className="flex-1 flex items-center justify-center text-zinc-500 text-sm p-6 text-center">
            هذا المشروع لم يُنشر بعد — لا توجد معاينة لايف. اطلب من المهندس فحصه عبر الشات.
          </div>
        )}
      </div>

      {/* Side chat (compact) */}
      <div className="flex flex-col border-r border-zinc-800 bg-zinc-950/80">
        <div className="px-3 py-2 border-b border-zinc-800 text-xs font-bold text-amber-300 flex items-center gap-2">
          <Wrench className="w-3.5 h-3.5" /> شات معالجة مباشر
        </div>
        <div className="flex-1 overflow-y-auto p-3 space-y-2">
          {messages.length === 0 ? (
            <p className="text-xs text-zinc-600 text-center py-8">
              اكتب وش المشكلة وأنا أحلّلها وأقترح حل (أو أنفّذ مباشرة لو أمرتني).
            </p>
          ) : (
            messages.slice(-15).map((m, i) => (
              <div key={i} className={m.role === 'user' ? 'flex justify-start' : 'flex justify-end'}>
                <div className={`max-w-[90%] rounded-lg px-3 py-2 text-[11px] leading-6 whitespace-pre-wrap ${
                  m.role === 'user' ? 'bg-emerald-500/15 text-emerald-100' : 'bg-zinc-900 text-zinc-200'
                }`}>
                  {m.content?.slice(0, 800)}
                </div>
              </div>
            ))
          )}
          {busy && <p className="text-xs text-zinc-500 animate-pulse text-left">المهندس يحلّل...</p>}
        </div>
        <Composer
          input={input} setInput={setInput} send={send} busy={busy}
          attachedFile={attachedFile} setAttachedFile={setAttachedFile}
          fileInputRef={fileInputRef} onFileSelect={onFileSelect}
          recording={recording} recElapsed={recElapsed}
          startRecording={startRecording} stopRecording={stopRecording}
          activeProject={project}
        />
      </div>
    </div>
  );
}


// ═════════════════════════════════════════════════════════════════
// DashboardStrip — Top band with 4 status cards + maintenance
// toggles + pending patches inbox. Refreshes every 30s automatically.
// ═════════════════════════════════════════════════════════════════
function DashboardStrip({
  report, errors, maintenance, patches, loading,
  onRefresh, onToggleMaintenance, onReviewPatch, onAskAI,
}) {
  const newCount = report?.projects_created_in_window ?? 0;
  const pubCount = report?.projects_published_in_window ?? 0;
  const summonsCount = report?.engineer_summons_in_window ?? 0;
  const errorPatternsCount = errors?.patterns_with_repeats?.length ?? 0;
  const pendingPatches = report?.pending_system_prompt_patches ?? 0;

  const activeMaintCount = (maintenance || []).filter((m) => m.active).length;

  const sections = [
    { key: 'images', label: 'الصور', icon: ImageIcon, color: 'from-fuchsia-500 to-pink-500' },
    { key: 'videos', label: 'الفيديوهات', icon: Film, color: 'from-rose-500 to-red-500' },
    { key: 'games', label: 'الألعاب', icon: Gamepad2, color: 'from-violet-500 to-indigo-500' },
    { key: 'global', label: 'كل الموقع', icon: Globe, color: 'from-amber-500 to-orange-500' },
  ];

  const findMaint = (key) => (maintenance || []).find((m) => m.section === key && m.active);

  return (
    <div className="border-b border-zinc-800 bg-gradient-to-l from-zinc-950 via-zinc-900/30 to-zinc-950" data-testid="owner-dashboard-strip">
      <div className="px-4 py-3 grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-2">
        {/* Today's report cards */}
        <StatCard
          icon={Activity}
          label="مشاريع جديدة اليوم"
          value={newCount}
          tone="emerald"
          testId="stat-new-projects"
          onClick={() => onAskAI('اعطني تفاصيل المشاريع اللي اتفتحت اليوم')}
        />
        <StatCard
          icon={Sparkles}
          label="نُشِرَت اليوم"
          value={pubCount}
          tone="cyan"
          testId="stat-published-today"
          onClick={() => onAskAI('قائمة المشاريع اللي نُشرت اليوم')}
        />
        <StatCard
          icon={AlertTriangle}
          label={summonsCount > 0 ? "🚨 استدعاءات للمهندس" : "استدعاءات للمهندس"}
          value={summonsCount}
          tone={summonsCount > 0 ? "rose" : "zinc"}
          testId="stat-engineer-summons"
          onClick={() => onAskAI(`الـ AI استدعى المهندس ${summonsCount} مرة اليوم — حلل السبب`)}
        />
        <StatCard
          icon={AlertTriangle}
          label={errorPatternsCount > 0 ? "⚠️ أخطاء متكررة" : "أنماط أخطاء"}
          value={errorPatternsCount}
          tone={errorPatternsCount > 0 ? "amber" : "zinc"}
          testId="stat-error-patterns"
          onClick={() => onAskAI('حلل آخر الأخطاء المتكررة في الذكاء الصناعي وقدم لي اقتراحات إصلاح')}
        />
        <StatCard
          icon={ListChecks}
          label="اقتراحات إصلاح معلقة"
          value={pendingPatches}
          tone={pendingPatches > 0 ? "violet" : "zinc"}
          testId="stat-pending-patches"
          onClick={() => onAskAI('اعرض لي الاقتراحات المعلقة لإصلاح الذكاء الصناعي')}
        />
      </div>

      {/* Maintenance toolbar */}
      <div className="px-4 pb-3 flex items-center gap-2 flex-wrap" data-testid="maintenance-toolbar">
        <span className="text-[11px] text-zinc-500 font-bold flex items-center gap-1">
          <Power className="w-3 h-3" /> عزل أقسام:
        </span>
        {sections.map(({ key, label, icon: Icon, color }) => {
          const active = !!findMaint(key);
          return (
            <button
              key={key}
              type="button"
              onClick={() => onToggleMaintenance(key, active)}
              data-testid={`maint-toggle-${key}`}
              className={`text-[11px] px-3 py-1.5 rounded-full border font-bold flex items-center gap-1.5 transition-all ${
                active
                  ? `bg-gradient-to-r ${color} text-white border-transparent shadow-md scale-105`
                  : 'bg-zinc-900/60 text-zinc-400 border-zinc-700 hover:border-amber-400/40 hover:text-amber-200'
              }`}
              title={active ? `قسم ${label} في وضع الصيانة الآن — اضغط للتفعيل` : `اضغط لإيقاف قسم ${label} مؤقتاً`}
            >
              <Icon className="w-3 h-3" />
              <span>{label}</span>
              {active && <span className="text-[9px] bg-white/20 px-1 rounded">معطّل</span>}
            </button>
          );
        })}
        {activeMaintCount > 0 && (
          <span className="text-[10px] text-amber-200 bg-amber-500/10 border border-amber-400/30 px-2 py-0.5 rounded-md font-bold ml-auto">
            🔧 {activeMaintCount} قسم في الصيانة
          </span>
        )}
        <button
          type="button"
          onClick={onRefresh}
          data-testid="dashboard-refresh"
          className="text-[11px] text-zinc-500 hover:text-amber-300 mr-auto flex items-center gap-1"
          title="تحديث التقرير"
        >
          <RefreshCw className={`w-3 h-3 ${loading ? 'animate-spin' : ''}`} /> تحديث
        </button>
      </div>

      {/* Pending patches inbox */}
      {(patches || []).length > 0 && (
        <div className="border-t border-zinc-800 bg-violet-500/5 px-4 py-2" data-testid="patches-inbox">
          <div className="flex items-center gap-2 mb-1.5">
            <ShieldCheck className="w-3.5 h-3.5 text-violet-300" />
            <span className="text-[11px] text-violet-200 font-bold">
              📋 اقتراحات إصلاح للذكاء الصناعي ({patches.length})
            </span>
          </div>
          <div className="flex gap-2 overflow-x-auto pb-1">
            {patches.slice(0, 8).map((p) => (
              <div
                key={p.id}
                data-testid={`patch-${p.id}`}
                className="min-w-[280px] max-w-[320px] bg-zinc-900/80 border border-violet-400/30 rounded-lg p-2.5 text-[11px]"
              >
                <div className="flex items-center justify-between mb-1">
                  <span className="text-violet-200 font-bold">🎯 {p.target}</span>
                  <span className="text-[9px] text-zinc-500">{fmt(p.created_at)}</span>
                </div>
                <p className="text-zinc-300 text-[11px] leading-5 line-clamp-2" dir="rtl">{p.observation}</p>
                <div className="flex gap-1 mt-2">
                  <button
                    type="button"
                    onClick={() => onReviewPatch(p.id, 'approve')}
                    data-testid={`patch-approve-${p.id}`}
                    className="flex-1 px-2 py-1 rounded bg-emerald-500/20 hover:bg-emerald-500/30 border border-emerald-400/40 text-emerald-200 font-bold flex items-center justify-center gap-1"
                  >
                    <Check className="w-3 h-3" /> اعتماد
                  </button>
                  <button
                    type="button"
                    onClick={() => onReviewPatch(p.id, 'reject')}
                    data-testid={`patch-reject-${p.id}`}
                    className="flex-1 px-2 py-1 rounded bg-zinc-800 hover:bg-rose-500/20 border border-zinc-700 hover:border-rose-400/40 text-zinc-400 hover:text-rose-200 flex items-center justify-center gap-1"
                  >
                    <X className="w-3 h-3" /> رفض
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function StatCard({ icon: Icon, label, value, tone, testId, onClick }) {
  const tones = {
    emerald: 'border-emerald-400/30 bg-emerald-500/5 text-emerald-200 hover:bg-emerald-500/10',
    cyan: 'border-cyan-400/30 bg-cyan-500/5 text-cyan-200 hover:bg-cyan-500/10',
    rose: 'border-rose-400/40 bg-rose-500/10 text-rose-200 hover:bg-rose-500/15',
    amber: 'border-amber-400/40 bg-amber-500/10 text-amber-200 hover:bg-amber-500/15',
    violet: 'border-violet-400/40 bg-violet-500/10 text-violet-200 hover:bg-violet-500/15',
    zinc: 'border-zinc-700 bg-zinc-900/50 text-zinc-400 hover:bg-zinc-800/60',
  };
  return (
    <button
      type="button"
      onClick={onClick}
      data-testid={testId}
      className={`text-right p-3 rounded-xl border transition-all flex items-center justify-between gap-2 ${tones[tone]}`}
      title="اضغط لتسأل المهندس عن هذا الرقم"
    >
      <div>
        <div className="text-[10px] uppercase tracking-wider opacity-70 font-bold">{label}</div>
        <div className="text-2xl font-black mt-0.5 leading-none" data-testid={`${testId}-value`}>
          {value ?? '—'}
        </div>
      </div>
      <Icon className="w-7 h-7 opacity-30" />
    </button>
  );
}
