import React, { useEffect, useRef, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'sonner';
import { Send, Loader2, Sparkles, Save, ExternalLink, Smartphone, Gamepad2, AppWindow, Wrench, Baby, RotateCcw, Plus, ChevronRight, X, Eye, Download } from 'lucide-react';
import { Button } from '@/components/ui/button';
import ChatShellLayout from '@/components/ChatShellLayout';

const API = process.env.REACT_APP_BACKEND_URL;

const CATEGORY_ICONS = {
  game: Gamepad2,
  app: AppWindow,
  tool: Wrench,
  kids: Baby,
};

const fetchJson = async (url, options = {}) => {
  const token = localStorage.getItem('token');
  const headers = { 'Content-Type': 'application/json', ...(options.headers || {}) };
  if (token) headers.Authorization = `Bearer ${token}`;
  const res = await fetch(`${API}${url}`, { ...options, headers });
  const text = await res.text();
  let data;
  try { data = text ? JSON.parse(text) : {}; } catch { data = { detail: text }; }
  if (!res.ok) throw new Error(data?.detail || `HTTP ${res.status}`);
  return data;
};

const Bubble = ({ role, content, progressNote }) => {
  if (role === 'assistant') {
    return (
      <div className="flex gap-2 mb-4" data-testid="chat-bubble-ai">
        <div className="flex-shrink-0 w-8 h-8 rounded-full bg-gradient-to-br from-cyan-400 to-blue-600 flex items-center justify-center shadow-md shadow-cyan-500/40">
          <Sparkles className="w-4 h-4 text-black" />
        </div>
        <div className="flex-1 max-w-[85%]">
          <div className="px-4 py-2.5 rounded-2xl rounded-tr-sm bg-white/[0.05] border border-cyan-400/15 text-white leading-relaxed whitespace-pre-wrap" dir="auto">
            {content}
          </div>
          {progressNote && (
            <div className="mt-1.5 flex items-center gap-1.5 text-[11px] text-emerald-400 font-bold">
              <ChevronRight className="w-3 h-3" /> {progressNote}
            </div>
          )}
        </div>
      </div>
    );
  }
  return (
    <div className="flex justify-end mb-4" data-testid="chat-bubble-user">
      <div className="max-w-[85%] px-4 py-2.5 rounded-2xl rounded-tl-sm bg-cyan-500/20 border border-cyan-400/30 text-white whitespace-pre-wrap" dir="auto">
        {content}
      </div>
    </div>
  );
};

export default function MobileAppBuilder() {
  const navigate = useNavigate();
  const [sessionId, setSessionId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const [loading, setLoading] = useState(false);
  const [questionType, setQuestionType] = useState('text');
  const [options, setOptions] = useState(null);
  const [credits, setCredits] = useState(0);
  const [turns, setTurns] = useState(0);
  const [htmlStarted, setHtmlStarted] = useState(false);
  const [iframeBust, setIframeBust] = useState(Date.now());
  const [categories, setCategories] = useState([]);
  const [savedProjectId, setSavedProjectId] = useState(null);
  const [saveOpen, setSaveOpen] = useState(false);
  const [saveName, setSaveName] = useState('');
  const [saveCategory, setSaveCategory] = useState('app');
  const [galleryOpen, setGalleryOpen] = useState(false);
  const [projects, setProjects] = useState([]);
  const [sessions, setSessions] = useState([]);

  const scrollRef = useRef(null);

  // ── Sessions list for the shell sidebar ──────────────────────────
  const loadSessions = useCallback(async () => {
    try {
      const d = await fetchJson('/api/mobile-app/sessions');
      setSessions(d.items || []);
    } catch (_) { /* silent */ }
  }, []);

  useEffect(() => {
    const token = localStorage.getItem('token');
    if (!token) navigate('/login');
    else { begin(); loadSessions(); }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // refresh sessions list every time the current session id changes
  useEffect(() => { if (sessionId) loadSessions(); }, [sessionId, loadSessions]);

  // Switch to an existing session
  const switchToSession = async (sid) => {
    if (sid === sessionId) return;
    try {
      setLoading(true);
      const s = await fetchJson(`/api/mobile-app/session/${sid}`);
      const cats = await fetchJson('/api/mobile-app/categories');
      setSessionId(sid);
      setMessages((s.messages || []).map((m) => ({
        role: m.role, content: m.content, progressNote: m.progress_note,
      })));
      setQuestionType('text');
      setOptions(null);
      setCategories(cats.categories || []);
      setHtmlStarted(!!s.html);
      setIframeBust(Date.now());
      setTurns(s.turns || 0);
    } catch (e) {
      toast.error(`فشل التحميل: ${e.message}`);
    } finally { setLoading(false); }
  };

  const removeSession = async (sid) => {
    if (!window.confirm('احذف هذه الجلسة؟')) return;
    try {
      await fetchJson(`/api/mobile-app/session/${sid}`, { method: 'DELETE' });
      setSessions((prev) => prev.filter((s) => s.id !== sid));
      if (sid === sessionId) {
        setSessionId(null);
        setMessages([]);
        begin();
      }
      toast.success('تم الحذف');
    } catch (e) { toast.error(`فشل: ${e.message}`); }
  };

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' });
  }, [messages]);

  const begin = async () => {
    setLoading(true);
    try {
      // If user came from Marketplace via remix → resume that session
      const remixSid = localStorage.getItem('zitex_mobile_remix_session');
      if (remixSid) {
        localStorage.removeItem('zitex_mobile_remix_session');
        try {
          const s = await fetchJson(`/api/mobile-app/session/${remixSid}`);
          const cats = await fetchJson('/api/mobile-app/categories');
          setSessionId(remixSid);
          setMessages((s.messages || []).map((m) => ({
            role: m.role, content: m.content, progressNote: m.progress_note,
          })));
          setQuestionType('text');
          setOptions(null);
          setCategories(cats.categories || []);
          setHtmlStarted(!!s.html);
          setIframeBust(Date.now());
          setTurns(s.turns || 0);
          // fetch credits separately
          try {
            const bal = await fetchJson('/api/user/balance');
            setCredits(bal.credits || 0);
          } catch {}
          setLoading(false);
          return;
        } catch {
          // fall through to fresh session
        }
      }
      const d = await fetchJson('/api/mobile-app/start', { method: 'POST', body: JSON.stringify({}) });
      setSessionId(d.session_id);
      setMessages([{ role: 'assistant', content: d.assistant_message, progressNote: null }]);
      setQuestionType(d.next_question_type);
      setOptions(d.options);
      setCredits(d.credits_balance);
      setCategories(d.categories || []);
      setTurns(0);
      setHtmlStarted(false);
      setSavedProjectId(null);
    } catch (e) {
      toast.error('فشل بدء المحادثة: ' + e.message);
    }
    setLoading(false);
  };

  const send = async (text) => {
    const msg = (text || input).trim();
    if (!msg) { toast.error('اكتب جوابك'); return; }
    if (!sessionId || sending) return;
    setMessages((m) => [...m, { role: 'user', content: msg }]);
    setInput('');
    setSending(true);
    try {
      const d = await fetchJson('/api/mobile-app/chat', {
        method: 'POST',
        body: JSON.stringify({ session_id: sessionId, message: msg }),
      });
      setMessages((m) => [...m, {
        role: 'assistant',
        content: d.assistant_message,
        progressNote: d.progress_note,
      }]);
      setQuestionType(d.next_question_type);
      setOptions(d.options);
      setCredits(d.credits_balance);
      setTurns(d.turns);
      if (d.html_updated) {
        setHtmlStarted(true);
        setIframeBust(Date.now());
      }
      if (d.complete) toast.success('التطبيق جاهز! اضغط "حفظ" للاحتفاظ به.');
    } catch (e) {
      toast.error(e.message);
      setMessages((m) => m.slice(0, -1));
    }
    setSending(false);
  };

  const pickCategory = (cat) => {
    send(`أبي ${cat.label} — اقترح علي مثال جذاب.`);
  };

  const saveProject = async () => {
    if (!saveName.trim()) { toast.error('اكتب اسم التطبيق'); return; }
    try {
      const d = await fetchJson('/api/mobile-app/save', {
        method: 'POST',
        body: JSON.stringify({
          session_id: sessionId,
          name: saveName.trim(),
          category: saveCategory,
          icon_emoji: '📱',
        }),
      });
      setSavedProjectId(d.project_id);
      setSaveOpen(false);
      setSaveName('');
      toast.success('تم حفظ التطبيق!');
    } catch (e) {
      toast.error(e.message);
    }
  };

  const publishProject = async () => {
    if (!savedProjectId) return;
    try {
      await fetchJson(`/api/mobile-app/publish/${savedProjectId}`, { method: 'POST' });
      toast.success('تم النشر في السوق! غيرك يقدر يعمل Remix لتطبيقك');
    } catch (e) { toast.error(e.message); }
  };

  const exportRN = async () => {
    if (!savedProjectId) return;
    try {
      const d = await fetchJson(`/api/mobile-app/export-rn/${savedProjectId}`);
      // Build a zip in-browser using simple text concatenation (one .txt download)
      // To keep it simple, dump each file as a separate download
      Object.entries(d.files).forEach(([name, content]) => {
        const blob = new Blob([content], { type: 'text/plain;charset=utf-8' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = name;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
      });
      toast.success('تم تنزيل ملفات React Native — افتح Terminal واتبع التعليمات في README.md');
    } catch (e) { toast.error(e.message); }
  };

  const openGallery = async () => {
    try {
      const d = await fetchJson('/api/mobile-app/projects');
      setProjects(d.projects || []);
      setGalleryOpen(true);
    } catch (e) {
      toast.error(e.message);
    }
  };

  const deleteProject = async (id) => {
    try {
      await fetchJson(`/api/mobile-app/project/${id}`, { method: 'DELETE' });
      setProjects((p) => p.filter((x) => x.id !== id));
      toast.success('تم الحذف');
    } catch (e) { toast.error(e.message); }
  };

  return (
    <ChatShellLayout
      title="إنشاء التطبيقات من الصفر"
      sessions={sessions}
      activeId={sessionId}
      onSelect={switchToSession}
      onNewChat={begin}
      onDelete={removeSession}
      credits={credits}
      emptyHint="ابدأ تطبيقك الأول"
      rightExtras={(
        <>
          <button onClick={() => navigate('/dashboard/apps-market')} className="text-[11px] px-2.5 py-1 rounded-full bg-amber-500/10 border border-amber-400/30 text-amber-200 hover:bg-amber-500/20 font-bold flex items-center gap-1" data-testid="market-btn">
            🔥 السوق
          </button>
          <button onClick={openGallery} className="text-[11px] px-2.5 py-1 rounded-full bg-white/5 border border-white/10 hover:bg-white/10 font-bold flex items-center gap-1" data-testid="gallery-btn">
            معرض
          </button>
        </>
      )}>
      <div className="h-full flex flex-col" dir="rtl" data-testid="mobile-app-builder">
        {/* MAIN GRID: chat (left) + iPhone preview (right) */}
        <div className="flex-1 min-h-0 max-w-7xl mx-auto w-full grid grid-cols-1 lg:grid-cols-[1fr_400px] gap-4 p-4 overflow-hidden">
          {/* CHAT PANEL */}
          <div className="flex flex-col bg-[#0a0a14]/60 border border-cyan-400/15 rounded-2xl overflow-hidden min-h-[60vh] lg:min-h-0">
            {/* Messages */}
            <div ref={scrollRef} className="flex-1 overflow-y-auto p-4 min-h-0">
              {messages.map((m, i) => (
              <Bubble key={i} role={m.role} content={m.content} progressNote={m.progressNote} />
            ))}
            {sending && (
              <div className="flex gap-2 mb-4">
                <div className="w-8 h-8 rounded-full bg-gradient-to-br from-cyan-400 to-blue-600 flex items-center justify-center">
                  <Loader2 className="w-4 h-4 text-black animate-spin" />
                </div>
                <div className="px-4 py-2.5 rounded-2xl bg-white/[0.05] border border-cyan-400/15 text-white/60 text-sm">يفكّر…</div>
              </div>
            )}
          </div>

          {/* QUICK CATEGORY CHIPS (only when very fresh) */}
          {messages.length <= 1 && categories.length > 0 && (
            <div className="px-4 pb-2">
              <div className="text-[10px] text-white/40 mb-1.5">قوالب سريعة:</div>
              <div className="flex flex-wrap gap-1.5">
                {categories.map((c) => {
                  const Icon = CATEGORY_ICONS[c.id] || AppWindow;
                  return (
                    <button
                      key={c.id}
                      onClick={() => pickCategory(c)}
                      disabled={sending}
                      className="px-2.5 py-1.5 rounded-lg bg-white/5 hover:bg-cyan-500/15 border border-white/10 hover:border-cyan-400/40 text-[11px] text-white/80 font-bold flex items-center gap-1.5 transition disabled:opacity-50"
                      data-testid={`category-${c.id}`}
                    >
                      <Icon className="w-3 h-3" />
                      {c.label}
                    </button>
                  );
                })}
              </div>
            </div>
          )}

          {/* COMPOSER */}
          <div className="flex-shrink-0 border-t border-cyan-400/15 p-3 bg-[#0a0a14]">
            {htmlStarted && !savedProjectId && (
              <div className="mb-2">
                <Button onClick={() => setSaveOpen(true)} className="w-full bg-emerald-500/20 hover:bg-emerald-500/30 text-emerald-200 border border-emerald-400/40 font-bold text-xs h-9" data-testid="save-app-btn">
                  <Save className="w-3.5 h-3.5 ms-1.5" /> احفظ التطبيق
                </Button>
              </div>
            )}
            {questionType === 'yes_no' && (
              <div className="flex gap-2 mb-2">
                <button
                  onClick={() => send(options?.[1] || 'لا')}
                  disabled={sending}
                  className="flex-1 px-4 py-3 rounded-xl bg-rose-500/15 border-2 border-rose-400/40 text-rose-100 font-black hover:scale-[1.02] active:scale-95 transition disabled:opacity-50"
                  data-testid="quick-no-btn"
                >{options?.[1] || 'لا'}</button>
                <button
                  onClick={() => send(options?.[0] || 'نعم')}
                  disabled={sending}
                  className="flex-1 px-4 py-3 rounded-xl bg-emerald-500/15 border-2 border-emerald-400/50 text-emerald-100 font-black hover:scale-[1.02] active:scale-95 transition disabled:opacity-50"
                  data-testid="quick-yes-btn"
                >{options?.[0] || 'نعم'}</button>
              </div>
            )}
            <div className="flex items-end gap-2">
              <textarea
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); }
                }}
                placeholder={questionType === 'done' ? 'تم! احفظ التطبيق أو ابدأ جلسة جديدة' : 'اكتب جوابك أو اطلب تعديل…'}
                rows={1}
                disabled={sending || loading || questionType === 'done'}
                className="flex-1 bg-white/5 border border-white/10 focus:border-cyan-400/40 rounded-xl px-3 py-2.5 text-white placeholder-white/30 outline-none resize-none disabled:opacity-50 text-sm"
                data-testid="chat-input"
              />
              <button
                onClick={() => send()}
                disabled={sending || loading || !input.trim() || questionType === 'done'}
                className="h-[42px] px-4 rounded-xl bg-gradient-to-br from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-white font-bold disabled:opacity-40 disabled:cursor-not-allowed flex items-center gap-1.5"
                data-testid="send-btn"
              >
                {sending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
              </button>
            </div>
            <div className="mt-1.5 flex items-center justify-between text-[10px] text-white/40">
              <span>{turns}/50 جولة · 3 نقاط/تحديث</span>
              {savedProjectId && (
                <div className="flex items-center gap-1.5">
                  <button onClick={publishProject} className="px-2 py-1 rounded-full bg-amber-500/15 hover:bg-amber-500/25 text-amber-200 border border-amber-400/30 text-[10px] font-bold flex items-center gap-1" data-testid="publish-btn">
                    🔥 انشر للسوق
                  </button>
                  <button onClick={exportRN} className="px-2 py-1 rounded-full bg-fuchsia-500/15 hover:bg-fuchsia-500/25 text-fuchsia-200 border border-fuchsia-400/30 text-[10px] font-bold flex items-center gap-1" data-testid="export-rn-btn">
                    <Download className="w-3 h-3" /> React Native
                  </button>
                  <a href={`${API}/api/mobile-app/public/${savedProjectId}`} target="_blank" rel="noreferrer" className="text-emerald-300 hover:underline flex items-center gap-1" data-testid="public-link">
                    <ExternalLink className="w-3 h-3" /> رابط
                  </a>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* iPHONE PREVIEW */}
        <div className="hidden lg:flex flex-col items-center justify-center bg-[#0a0a14]/60 border border-cyan-400/15 rounded-2xl p-4">
          <div className="relative w-[300px] h-[600px] bg-black rounded-[44px] border-[6px] border-zinc-800 shadow-2xl shadow-cyan-500/10 overflow-hidden" data-testid="iphone-frame">
            {/* Notch */}
            <div className="absolute top-0 left-1/2 -translate-x-1/2 w-32 h-6 bg-black rounded-b-2xl z-10"></div>
            {htmlStarted && sessionId ? (
              <iframe
                src={`${API}/api/mobile-app/preview/${sessionId}?t=${iframeBust}`}
                className="w-full h-full"
                title="Mobile App Preview"
                data-testid="preview-iframe"
              />
            ) : (
              <div className="w-full h-full flex flex-col items-center justify-center text-white/50 text-center px-6">
                <Smartphone className="w-12 h-12 mb-3 text-cyan-400/40" />
                <div className="text-sm">المعاينة المباشرة</div>
                <div className="text-[11px] mt-1 text-white/30">ابدأ المحادثة وشاهد تطبيقك يتكوّن</div>
              </div>
            )}
          </div>
          <div className="mt-3 text-[10px] text-white/40">معاينة بمقاس iPhone 13 mini · 375×812</div>
        </div>
      </div>

      {/* SAVE MODAL */}
      {saveOpen && (
        <div className="fixed inset-0 bg-black/70 z-50 flex items-center justify-center p-4" onClick={() => setSaveOpen(false)}>
          <div className="bg-[#0d0d18] border border-cyan-400/30 rounded-2xl p-6 max-w-md w-full" onClick={(e) => e.stopPropagation()} data-testid="save-modal">
            <h3 className="text-lg font-black mb-4 flex items-center gap-2">
              <Save className="w-5 h-5 text-cyan-400" /> احفظ التطبيق
            </h3>
            <label className="block text-xs text-white/60 mb-1">اسم التطبيق</label>
            <input
              value={saveName}
              onChange={(e) => setSaveName(e.target.value)}
              placeholder="مثلاً: لعبة الذاكرة"
              className="w-full bg-white/5 border border-white/10 focus:border-cyan-400/50 rounded-xl px-3 py-2 text-white outline-none text-sm mb-3"
              data-testid="save-name-input"
            />
            <label className="block text-xs text-white/60 mb-1">الفئة</label>
            <select
              value={saveCategory}
              onChange={(e) => setSaveCategory(e.target.value)}
              className="w-full bg-white/5 border border-white/10 rounded-xl px-3 py-2 text-white text-sm mb-4"
              data-testid="save-category-select"
            >
              {categories.map((c) => (
                <option key={c.id} value={c.id} className="bg-[#0d0d18]">{c.label}</option>
              ))}
            </select>
            <div className="flex gap-2">
              <Button onClick={() => setSaveOpen(false)} variant="outline" className="flex-1 border-white/20 text-white/70 hover:bg-white/5 text-xs h-9">إلغاء</Button>
              <Button onClick={saveProject} className="flex-1 bg-gradient-to-br from-cyan-500 to-blue-600 hover:from-cyan-400 text-white font-bold text-xs h-9" data-testid="confirm-save-btn">حفظ</Button>
            </div>
          </div>
        </div>
      )}

      {/* GALLERY MODAL */}
      {galleryOpen && (
        <div className="fixed inset-0 bg-black/70 z-50 flex items-center justify-center p-4" onClick={() => setGalleryOpen(false)}>
          <div className="bg-[#0d0d18] border border-cyan-400/30 rounded-2xl p-6 max-w-2xl w-full max-h-[80vh] overflow-y-auto" onClick={(e) => e.stopPropagation()} data-testid="gallery-modal">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-black flex items-center gap-2">
                <AppWindow className="w-5 h-5 text-cyan-400" /> تطبيقاتي المحفوظة ({projects.length})
              </h3>
              <button onClick={() => setGalleryOpen(false)} className="p-1 hover:bg-white/5 rounded-lg" data-testid="close-gallery-btn">
                <X className="w-5 h-5" />
              </button>
            </div>
            {projects.length === 0 ? (
              <div className="text-center py-12 text-white/40">
                <Smartphone className="w-12 h-12 mx-auto mb-3 opacity-40" />
                لا توجد تطبيقات محفوظة بعد. ابدأ محادثة واحفظ تطبيقك الأول.
              </div>
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {projects.map((p) => {
                  const Icon = CATEGORY_ICONS[p.category] || AppWindow;
                  return (
                    <div key={p.id} className="bg-white/[0.03] border border-white/10 rounded-xl p-3 flex items-center gap-3" data-testid={`project-${p.id}`}>
                      <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-cyan-500/20 to-blue-600/20 border border-cyan-400/30 flex items-center justify-center flex-shrink-0">
                        <Icon className="w-6 h-6 text-cyan-300" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="font-bold text-sm truncate">{p.name}</div>
                        <div className="text-[10px] text-white/40">{new Date(p.created_at).toLocaleDateString('ar-SA')}</div>
                      </div>
                      <a href={`${API}/api/mobile-app/public/${p.id}`} target="_blank" rel="noreferrer" className="p-2 rounded-lg bg-cyan-500/10 hover:bg-cyan-500/20 text-cyan-300" title="معاينة">
                        <Eye className="w-4 h-4" />
                      </a>
                      <button onClick={() => deleteProject(p.id)} className="p-2 rounded-lg bg-rose-500/10 hover:bg-rose-500/20 text-rose-300" title="حذف">
                        <X className="w-4 h-4" />
                      </button>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  </ChatShellLayout>
  );
}
