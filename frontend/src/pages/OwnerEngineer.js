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
  Image as ImageIcon, Film, Gamepad2, Globe,
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
    if (!text || busy) return;
    setBusy(true);
    setInput('');
    setMessages((m) => [...m, { role: 'user', content: text }]);

    try {
      const form = new FormData();
      form.append('message', text);
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
          <button
            type="button"
            onClick={newChat}
            data-testid="new-chat-btn"
            className="text-xs bg-emerald-500/20 border border-emerald-400/40 text-emerald-200 px-3 py-1.5 rounded-lg hover:bg-emerald-500/30"
          >
            + محادثة جديدة
          </button>
        </div>
      </header>

      {/* ─── Owner-Engineer Dashboard Strip ─────────────────────────── */}
      <DashboardStrip
        report={dailyReport}
        errors={errorAnalysis}
        maintenance={maintenance}
        patches={patches}
        loading={dashLoading}
        onRefresh={loadDashboard}
        onToggleMaintenance={toggleMaintenance}
        onReviewPatch={reviewPatch}
        onAskAI={(prompt) => { setInput(prompt); }}
      />

      <div className="grid lg:grid-cols-[300px,1fr,420px] md:grid-cols-[260px,1fr] gap-0 min-h-[calc(100vh-58px)]">
        {/* Projects sidebar */}
        <aside className="border-l border-zinc-800 bg-zinc-900/50 overflow-y-auto" data-testid="projects-sidebar">
          <div className="p-3 sticky top-0 bg-zinc-900/95 backdrop-blur border-b border-zinc-800">
            <h3 className="text-[11px] font-bold text-zinc-500 uppercase tracking-wider mb-2 flex items-center gap-1.5">
              <Layers className="w-3 h-3" /> كل المشاريع
            </h3>
            <div className="relative">
              <Search className="absolute right-2 top-2.5 w-3.5 h-3.5 text-zinc-500" />
              <input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="ابحث باسم المشروع..."
                data-testid="project-search"
                className="w-full bg-zinc-950 border border-zinc-800 focus:border-amber-400/50 rounded-lg pr-7 pl-2 py-1.5 text-xs text-zinc-100 placeholder-zinc-600 focus:outline-none"
              />
            </div>
            <button
              type="button"
              onClick={() => { loadProjects(query); loadStats(); }}
              className="mt-2 w-full text-[11px] text-zinc-400 hover:text-amber-300 flex items-center justify-center gap-1 py-1"
              data-testid="refresh-projects"
            >
              <RefreshCw className={`w-3 h-3 ${projLoading ? 'animate-spin' : ''}`} /> تحديث
            </button>
          </div>

          <div className="p-2">
            {projects.length === 0 && !projLoading && (
              <p className="text-xs text-zinc-600 px-2 py-6 text-center">لا توجد مشاريع.</p>
            )}
            <ul className="space-y-1">
              {projects.map((p) => (
                <li key={p.id}>
                  <button
                    type="button"
                    onClick={() => selectProject(p)}
                    data-testid={`project-${p.id}`}
                    className={`w-full text-right text-xs px-3 py-2 rounded-lg transition-all ${
                      activeProject?.id === p.id
                        ? 'bg-amber-500/15 text-amber-100 border border-amber-400/40'
                        : 'hover:bg-zinc-800/60 text-zinc-300 border border-transparent'
                    }`}
                  >
                    <div className="font-bold truncate flex items-center gap-1.5">
                      {p.published_slug && <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 shrink-0" />}
                      {p.name || '(بدون اسم)'}
                    </div>
                    <div className="text-[10px] text-zinc-500 mt-0.5 flex items-center gap-1.5">
                      <UserIcon className="w-2.5 h-2.5" />
                      <span className="truncate">{p.owner_email || p.user_id?.slice(0, 8) || '—'}</span>
                      <span className="text-zinc-600">·</span>
                      <span>{p.mode || '—'}</span>
                    </div>
                    <div className="text-[10px] text-zinc-600 mt-0.5">{fmt(p.updated_at)}</div>
                  </button>
                </li>
              ))}
            </ul>
          </div>
        </aside>

        {/* Center: Chat */}
        <main className="flex flex-col border-l border-zinc-800">
          {/* Active project bar */}
          {activeProject && (
            <div className="bg-amber-500/5 border-b border-amber-500/20 px-4 py-2 flex items-center justify-between text-xs" data-testid="active-project-bar">
              <div className="flex items-center gap-2">
                <FolderOpen className="w-3.5 h-3.5 text-amber-400" />
                <span className="text-amber-200 font-bold">{activeProject.name}</span>
                <span className="text-zinc-500">·</span>
                <span className="text-zinc-400">{activeProject.owner_email || '—'}</span>
              </div>
              <div className="flex items-center gap-2">
                {liveUrl && (
                  <a href={liveUrl} target="_blank" rel="noreferrer" className="text-emerald-300 hover:text-emerald-200 flex items-center gap-1" data-testid="open-live">
                    <ExternalLink className="w-3 h-3" /> فتح الموقع
                  </a>
                )}
                <button type="button" onClick={() => { setActiveProject(null); setProjectDetail(null); }} className="text-zinc-500 hover:text-zinc-300">إلغاء التركيز</button>
              </div>
            </div>
          )}

          <div ref={scrollerRef} className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-4">
            {messages.length === 0 && (
              <div className="text-center py-10">
                <Wrench className="w-14 h-14 mx-auto mb-3 text-amber-400/40" />
                <p className="text-zinc-300 font-bold mb-1">المهندس بانتظار أوامرك</p>
                <p className="text-xs text-zinc-500 mb-6">
                  {activeProject
                    ? `سؤالك مرتبط حالياً بمشروع: ${activeProject.name}`
                    : 'اختر مشروعاً من الجانب، أو اسأل سؤالاً عاماً عن المنصة.'}
                </p>
                <div className="flex flex-wrap gap-2 justify-center max-w-xl mx-auto">
                  {(activeProject
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
                        'اعطني آخر 10 مشاريع منشورة',
                        'كم مستخدم على المنصة؟',
                      ]
                  ).map((q, i) => (
                    <button
                      key={i}
                      type="button"
                      onClick={() => setInput(q)}
                      data-testid={`suggest-${i}`}
                      className="text-xs bg-zinc-900 border border-zinc-700 text-zinc-300 px-3 py-1.5 rounded-lg hover:border-amber-400/40 hover:text-amber-200"
                    >
                      {q}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {messages.map((m, i) => (
              <div key={i} className={m.role === 'user' ? 'flex justify-start' : 'flex justify-end'} data-testid={`msg-${i}`}>
                <div
                  className={`max-w-[80%] rounded-xl px-4 py-3 text-sm whitespace-pre-wrap leading-7 ${
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
            ))}

            {busy && (
              <div className="flex justify-end">
                <div className="bg-zinc-900 border border-zinc-800 rounded-xl px-4 py-3 text-sm text-zinc-500">
                  <span className="animate-pulse">المهندس يفكّر...</span>
                </div>
              </div>
            )}
          </div>

          {/* Input */}
          <div className="border-t border-zinc-800 p-3 sm:p-4 bg-zinc-950/80 backdrop-blur">
            <div className="flex items-end gap-2 max-w-4xl mx-auto">
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
                disabled={busy || !input.trim()}
                data-testid="owner-chat-send"
                className="px-4 py-3 rounded-xl bg-gradient-to-r from-amber-500 to-orange-500 hover:from-amber-400 hover:to-orange-400 text-zinc-950 font-bold disabled:opacity-40 disabled:cursor-not-allowed flex items-center gap-2"
              >
                <Send className="w-4 h-4" />
                <span>إرسال</span>
              </button>
            </div>
          </div>
        </main>

        {/* Right: Preview + sessions */}
        <aside className="hidden lg:flex flex-col border-r border-zinc-800 bg-zinc-900/30 overflow-hidden" data-testid="preview-pane">
          {activeProject ? (
            <>
              <div className="px-3 py-2 border-b border-zinc-800 flex items-center justify-between">
                <div className="flex items-center gap-1.5 text-xs text-zinc-400">
                  <Eye className="w-3 h-3" /> معاينة حية
                </div>
                {projectDetail && (
                  <span className="text-[10px] text-zinc-500">
                    v{projectDetail.published_version || '—'} · {projectDetail.page_count || 0} صفحة
                  </span>
                )}
              </div>
              {liveUrl ? (
                <iframe
                  src={liveUrl}
                  title="project-preview"
                  className="flex-1 w-full bg-white"
                  data-testid="project-preview-iframe"
                />
              ) : (
                <div className="flex-1 flex items-center justify-center text-zinc-600 text-xs p-6 text-center">
                  لم يُنشر هذا المشروع بعد — لا توجد معاينة حية.
                </div>
              )}
              {projectDetail && (
                <div className="border-t border-zinc-800 p-3 text-[11px] space-y-1 text-zinc-400 bg-zinc-950/60">
                  <div><span className="text-zinc-600">ID:</span> <code className="text-zinc-300">{activeProject.id?.slice(0, 12)}</code></div>
                  <div><span className="text-zinc-600">المالك:</span> {projectDetail.owner_email || '—'}</div>
                  <div><span className="text-zinc-600">حجم HTML:</span> {projectDetail.html_size?.toLocaleString() || 0} حرف</div>
                  <div><span className="text-zinc-600">آخر تحديث:</span> {fmt(projectDetail.updated_at)}</div>
                </div>
              )}
            </>
          ) : (
            <>
              <div className="px-3 py-2 border-b border-zinc-800 text-xs text-zinc-400 flex items-center gap-1.5">
                <FolderOpen className="w-3 h-3" /> محادثاتي السابقة
              </div>
              <div className="flex-1 overflow-y-auto p-2">
                {sessions.length === 0 ? (
                  <p className="text-xs text-zinc-600 px-2 py-6 text-center">لا توجد محادثات بعد.</p>
                ) : (
                  <ul className="space-y-1">
                    {sessions.map((s) => (
                      <li key={s.id}>
                        <button
                          type="button"
                          onClick={() => openSession(s.id)}
                          data-testid={`session-${s.id}`}
                          className={`w-full text-right text-xs px-3 py-2 rounded-lg transition-all ${
                            activeSession === s.id
                              ? 'bg-emerald-500/15 text-emerald-200 border border-emerald-400/30'
                              : 'hover:bg-zinc-800/60 text-zinc-400 border border-transparent'
                          }`}
                        >
                          <div className="font-bold truncate">{s.messages?.[0]?.content?.slice(0, 40) || 'محادثة'}</div>
                          <div className="text-[10px] text-zinc-600 mt-0.5">{fmt(s.updated_at)}</div>
                        </button>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
              <div className="border-t border-zinc-800 p-3 bg-zinc-950/60">
                <h4 className="text-[10px] font-bold text-zinc-500 uppercase tracking-wider mb-1.5 flex items-center gap-1">
                  <BarChart3 className="w-3 h-3" /> الأدوات (16)
                </h4>
                <ul className="text-[10px] text-zinc-500 space-y-0.5">
                  <li className="text-zinc-400 font-bold mt-1">قراءة:</li>
                  <li>· list_all_projects · search_projects</li>
                  <li>· get_project_summary · read_project_page</li>
                  <li>· read_full_html · get_project_owner</li>
                  <li>· get_platform_stats · read_server_logs</li>
                  <li className="text-amber-400 font-bold mt-1">🆕 تحليل ميداني:</li>
                  <li>· get_daily_report · analyze_ai_errors</li>
                  <li>· list_pending_patches · list_maintenance_modes</li>
                  <li className="text-emerald-400 font-bold mt-1">🆕 تحكم:</li>
                  <li>· propose_system_prompt_patch</li>
                  <li>· enter/exit_maintenance_mode</li>
                  <li>· apply_fix_to_project · republish_project</li>
                  <li>· resume_project_ai · run_browser_audit</li>
                </ul>
              </div>
            </>
          )}
        </aside>
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
