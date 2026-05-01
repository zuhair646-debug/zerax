import React, { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'sonner';
import { Send, Loader2, Sparkles, ArrowRight, Save, ExternalLink, Trash2, Eye, RotateCcw, Check } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';

const API = process.env.REACT_APP_BACKEND_URL;

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
        <div className="flex-shrink-0 w-8 h-8 rounded-full bg-gradient-to-br from-amber-400 to-yellow-600 flex items-center justify-center shadow-md shadow-amber-500/40">
          <Sparkles className="w-4 h-4 text-black" />
        </div>
        <div className="flex-1 max-w-[85%]">
          <div className="px-4 py-2.5 rounded-2xl rounded-tr-sm bg-white/[0.05] border border-amber-400/15 text-white leading-relaxed whitespace-pre-wrap" dir="auto">
            {content}
          </div>
          {progressNote && (
            <div className="mt-1.5 flex items-center gap-1.5 text-[11px] text-emerald-400 font-bold">
              <Check className="w-3 h-3" /> {progressNote}
            </div>
          )}
        </div>
      </div>
    );
  }
  return (
    <div className="flex gap-2 mb-4 flex-row-reverse" data-testid="chat-bubble-user">
      <div className="flex-shrink-0 w-8 h-8 rounded-full bg-white/10 flex items-center justify-center text-white/80 text-xs font-bold">أنا</div>
      <div className="max-w-[85%] px-4 py-2.5 rounded-2xl rounded-tl-sm bg-amber-500/15 border border-amber-400/30 text-amber-50 whitespace-pre-wrap" dir="auto">
        {content}
      </div>
    </div>
  );
};

const FreeBuild = () => {
  const navigate = useNavigate();
  const [sessionId, setSessionId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [questionType, setQuestionType] = useState('text'); // text | yes_no | done
  const [options, setOptions] = useState(null);
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const [loading, setLoading] = useState(false);
  const [credits, setCredits] = useState(null);
  const [turns, setTurns] = useState(0);
  const [iframeBust, setIframeBust] = useState(Date.now());
  const [htmlStarted, setHtmlStarted] = useState(false);
  const [saveOpen, setSaveOpen] = useState(false);
  const [projectName, setProjectName] = useState('');
  const [savedProjectId, setSavedProjectId] = useState(null);
  const [galleryOpen, setGalleryOpen] = useState(false);
  const [gallery, setGallery] = useState([]);
  const chatEndRef = useRef(null);

  useEffect(() => {
    if (!localStorage.getItem('token')) {
      toast.error('سجّل دخولك أولاً');
      navigate('/login');
      return;
    }
    begin();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, sending]);

  const begin = async () => {
    setLoading(true);
    try {
      const d = await fetchJson('/api/freebuild/v2/start', { method: 'POST', body: JSON.stringify({}) });
      setSessionId(d.session_id);
      setMessages([{ role: 'assistant', content: d.assistant_message, progressNote: null }]);
      setQuestionType(d.next_question_type);
      setOptions(d.options);
      setCredits(d.credits_balance);
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
    if (!sessionId) return;
    if (sending) return;

    setMessages((m) => [...m, { role: 'user', content: msg }]);
    setInput('');
    setSending(true);

    try {
      const d = await fetchJson('/api/freebuild/v2/chat', {
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
        // Bust iframe cache to reload updated preview
        setIframeBust(Date.now());
      }
      if (d.complete) {
        toast.success('الموقع جاهز! اضغط "حفظ" للحفاظ عليه.');
      }
    } catch (e) {
      toast.error(e.message);
      // Rollback optimistic user bubble
      setMessages((m) => m.slice(0, -1));
    }
    setSending(false);
  };

  const saveAsProject = async () => {
    const name = (projectName || 'موقعي').trim();
    try {
      const d = await fetchJson('/api/freebuild/v2/save-as-project', {
        method: 'POST',
        body: JSON.stringify({ session_id: sessionId, name }),
      });
      setSavedProjectId(d.project_id);
      setSaveOpen(false);
      toast.success(`تم حفظ "${name}"!`);
    } catch (e) {
      toast.error(e.message);
    }
  };

  const loadGallery = async () => {
    try {
      const d = await fetchJson('/api/freebuild/v2/projects');
      setGallery(d.projects || []);
    } catch (e) {
      toast.error('فشل تحميل: ' + e.message);
    }
  };

  useEffect(() => { if (galleryOpen) loadGallery(); }, [galleryOpen]);

  const deleteProject = async (id) => {
    if (!window.confirm('تحذف هذا المشروع؟')) return;
    try {
      await fetchJson(`/api/freebuild/v2/project/${id}`, { method: 'DELETE' });
      toast.success('تم الحذف');
      loadGallery();
    } catch (e) { toast.error(e.message); }
  };

  const newSession = async () => {
    if (htmlStarted && !savedProjectId) {
      if (!window.confirm('موقعك لم يُحفظ بعد — تأكد تبدأ جلسة جديدة؟')) return;
    }
    await begin();
  };

  const previewUrl = sessionId ? `${API}/api/freebuild/v2/preview/${sessionId}?v=${iframeBust}` : null;

  // =======================================================================
  return (
    <div dir="rtl" className="h-screen bg-[#070710] text-white flex flex-col overflow-hidden" data-testid="freebuild-v2-page">
      {/* HEADER */}
      <div className="flex-shrink-0 backdrop-blur-xl bg-black/60 border-b border-amber-400/15">
        <div className="max-w-screen-2xl mx-auto px-4 py-3 flex items-center justify-between gap-3 flex-wrap">
          <button onClick={() => navigate('/')} className="flex items-center gap-2 text-white/70 hover:text-amber-300 transition text-sm" data-testid="back-home-btn">
            <ArrowRight className="w-4 h-4" /> الرئيسية
          </button>
          <div className="flex items-center gap-2 text-amber-200/95 font-black text-sm sm:text-base">
            <Sparkles className="w-4 h-4 text-amber-400" /> المهندس الذكي — بناء مباشر
          </div>
          <div className="flex items-center gap-2 text-xs">
            <span className="px-2 py-1 rounded-md bg-amber-400/10 border border-amber-400/25 text-amber-200" data-testid="credits-pill">
              {credits !== null ? `${credits} نقطة` : '…'}
            </span>
            <button onClick={newSession} className="px-2.5 py-1 rounded-md bg-white/5 border border-white/10 text-white/70 hover:bg-white/10 flex items-center gap-1" data-testid="new-session-btn" title="بدء جلسة جديدة">
              <RotateCcw className="w-3 h-3" /> <span className="hidden sm:inline">جديد</span>
            </button>
            <button onClick={() => setGalleryOpen(true)} className="px-2.5 py-1 rounded-md bg-amber-400/10 border border-amber-400/25 text-amber-200 hover:bg-amber-400/20" data-testid="gallery-btn">
              مواقعي
            </button>
          </div>
        </div>
      </div>

      {/* SPLIT LAYOUT */}
      <div className="flex-1 flex overflow-hidden flex-col lg:flex-row">
        {/* ===== LEFT: CHAT ===== */}
        <div className="w-full lg:w-[42%] flex flex-col border-b lg:border-b-0 lg:border-l border-amber-400/10 bg-[#0a0a14] max-h-[55vh] lg:max-h-none" data-testid="chat-panel">
          <div className="flex-1 overflow-y-auto p-4 sm:p-6" data-testid="chat-messages">
            {loading && messages.length === 0 && (
              <div className="text-center text-white/50 py-10">
                <Loader2 className="w-6 h-6 animate-spin mx-auto mb-3" />
                جاري التحضير...
              </div>
            )}
            {messages.map((m, i) => (
              <Bubble key={i} role={m.role} content={m.content} progressNote={m.progressNote} />
            ))}
            {sending && (
              <div className="flex gap-2 mb-4" data-testid="chat-typing-indicator">
                <div className="flex-shrink-0 w-8 h-8 rounded-full bg-gradient-to-br from-amber-400 to-yellow-600 flex items-center justify-center">
                  <Sparkles className="w-4 h-4 text-black animate-pulse" />
                </div>
                <div className="px-4 py-3 rounded-2xl bg-white/[0.05] border border-amber-400/15">
                  <div className="flex gap-1">
                    <span className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-pulse" />
                    <span className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-pulse" style={{ animationDelay: '0.15s' }} />
                    <span className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-pulse" style={{ animationDelay: '0.3s' }} />
                  </div>
                </div>
              </div>
            )}
            <div ref={chatEndRef} />
          </div>

          {/* INPUT AREA */}
          <div className="flex-shrink-0 border-t border-amber-400/15 p-3 bg-[#0a0a14]">
            {questionType === 'done' && htmlStarted && !savedProjectId && (
              <div className="mb-2 p-3 rounded-xl bg-emerald-500/10 border border-emerald-400/30 text-center">
                <div className="text-emerald-300 font-black text-sm mb-2">✓ الموقع جاهز!</div>
                <Button onClick={() => setSaveOpen(true)} className="bg-emerald-500 hover:bg-emerald-400 text-black font-black w-full" data-testid="done-save-btn">
                  <Save className="w-4 h-4 ms-2" /> احفظ الموقع باسمه
                </Button>
              </div>
            )}
            {questionType === 'yes_no' && (
              <div className="flex gap-2 mb-2">
                <button
                  onClick={() => send(options?.[1] || 'لا')}
                  disabled={sending}
                  className="flex-1 px-4 py-3 rounded-xl bg-gradient-to-br from-rose-500/20 to-rose-700/20 border-2 border-rose-400/40 text-rose-100 font-black hover:scale-[1.02] active:scale-95 transition disabled:opacity-50"
                  data-testid="quick-no-btn"
                >{options?.[1] || 'لا'}</button>
                <button
                  onClick={() => send(options?.[0] || 'نعم')}
                  disabled={sending}
                  className="flex-1 px-4 py-3 rounded-xl bg-gradient-to-br from-emerald-500/20 to-emerald-700/20 border-2 border-emerald-400/50 text-emerald-100 font-black hover:scale-[1.02] active:scale-95 transition disabled:opacity-50"
                  data-testid="quick-yes-btn"
                >{options?.[0] || 'نعم'}</button>
              </div>
            )}
            <div className="flex items-end gap-2" data-testid="chat-input-bar">
              <textarea
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    send();
                  }
                }}
                placeholder={questionType === 'yes_no' ? 'أو اكتب إجابة مخصّصة...' : 'اكتب جوابك هنا...'}
                rows={1}
                disabled={sending || questionType === 'done'}
                className="flex-1 resize-none bg-black/50 border border-amber-400/20 rounded-xl px-3 py-2.5 text-white placeholder:text-white/35 focus:border-amber-400/60 focus:outline-none text-sm"
                data-testid="chat-input-textarea"
                style={{ minHeight: '42px', maxHeight: '120px' }}
              />
              <Button
                onClick={() => send()}
                disabled={sending || !input.trim() || questionType === 'done'}
                className="bg-gradient-to-br from-amber-500 to-yellow-500 text-black font-black h-[42px] px-4 flex-shrink-0 disabled:opacity-50"
                data-testid="chat-send-btn"
              >
                {sending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
              </Button>
            </div>
            <div className="mt-1.5 text-[10px] text-white/35 flex justify-between">
              <span>{turns} دورة · {htmlStarted ? 'يبني الآن' : 'جمع فكرة'}</span>
              <span>{htmlStarted ? '3 نقاط/تحديث' : 'الأسئلة مجانية'}</span>
            </div>
          </div>
        </div>

        {/* ===== RIGHT: LIVE PREVIEW ===== */}
        <div className="flex-1 flex flex-col bg-[#0d0d18]" data-testid="preview-panel">
          <div className="flex-shrink-0 px-4 py-2 flex items-center justify-between border-b border-amber-400/10 bg-black/40">
            <div className="flex items-center gap-2 text-xs text-white/60">
              <Eye className="w-3.5 h-3.5" />
              <span>المعاينة المباشرة</span>
              {htmlStarted && (
                <span className="px-1.5 py-0.5 rounded bg-emerald-500/15 border border-emerald-400/30 text-emerald-300 text-[10px] font-bold animate-pulse">
                  LIVE
                </span>
              )}
            </div>
            {previewUrl && htmlStarted && (
              <a
                href={previewUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="text-[11px] text-amber-300 hover:text-amber-200 flex items-center gap-1"
                data-testid="open-preview-new-tab"
              >
                <ExternalLink className="w-3 h-3" /> تبويب جديد
              </a>
            )}
          </div>
          <div className="flex-1 p-2 sm:p-3">
            {previewUrl ? (
              <iframe
                src={previewUrl}
                title="Live preview"
                className="w-full h-full rounded-xl bg-white border-0 shadow-lg shadow-black/50"
                sandbox="allow-scripts allow-same-origin"
                data-testid="preview-iframe"
              />
            ) : (
              <div className="w-full h-full rounded-xl bg-black/40 flex items-center justify-center text-white/40 text-sm">
                <Loader2 className="w-5 h-5 animate-spin" />
              </div>
            )}
          </div>
        </div>
      </div>

      {/* SAVE MODAL */}
      {saveOpen && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-md flex items-center justify-center p-4" onClick={() => setSaveOpen(false)} data-testid="save-modal">
          <div className="bg-[#0c0c18] border border-amber-400/25 rounded-2xl max-w-md w-full p-6" onClick={(e) => e.stopPropagation()}>
            <h3 className="text-lg font-black mb-4">احفظ الموقع</h3>
            <Input
              value={projectName}
              onChange={(e) => setProjectName(e.target.value)}
              placeholder="اسم الموقع (مثلاً: موقع تحفيظ القرآن)"
              className="bg-black/50 border-amber-400/20 text-white mb-4"
              data-testid="save-project-name-input"
            />
            <div className="flex gap-2">
              <Button onClick={() => setSaveOpen(false)} variant="outline" className="flex-1 border-white/20 text-white/80" data-testid="save-cancel-btn">إلغاء</Button>
              <Button onClick={saveAsProject} disabled={!projectName.trim()} className="flex-1 bg-emerald-500 hover:bg-emerald-400 text-black font-black disabled:opacity-50" data-testid="save-confirm-btn">
                <Save className="w-4 h-4 ms-2" /> احفظ
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* GALLERY MODAL */}
      {galleryOpen && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-md flex items-start justify-center p-4 overflow-auto" onClick={() => setGalleryOpen(false)} data-testid="gallery-modal">
          <div className="bg-[#0c0c18] border border-amber-400/25 rounded-2xl max-w-3xl w-full p-6 my-10" onClick={(e) => e.stopPropagation()}>
            <h3 className="text-lg font-black mb-4">مواقعي المحفوظة ({gallery.length})</h3>
            {gallery.length === 0 ? (
              <div className="text-center py-10 text-white/50">لا يوجد مواقع محفوظة بعد</div>
            ) : (
              <div className="grid gap-2">
                {gallery.map((p) => (
                  <div key={p.id} className="flex items-center gap-3 p-3 rounded-xl bg-white/[0.04] border border-white/10 hover:border-amber-400/30 transition">
                    <div className="flex-1">
                      <div className="font-bold text-sm">{p.name}</div>
                      <div className="text-[11px] text-white/40">
                        {new Date(p.created_at).toLocaleDateString('ar')} · إصدار {p.version} · {p.credits_spent} نقطة
                      </div>
                    </div>
                    <a
                      href={`${API}/api/freebuild/v2/project-preview/${p.id}`}
                      target="_blank" rel="noopener noreferrer"
                      className="text-amber-300 hover:text-amber-200 flex items-center gap-1 text-xs"
                      data-testid={`gallery-open-${p.id}`}
                    >
                      <ExternalLink className="w-3.5 h-3.5" /> فتح
                    </a>
                    <button onClick={() => deleteProject(p.id)} className="text-rose-400 hover:text-rose-300" data-testid={`gallery-delete-${p.id}`}>
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                ))}
              </div>
            )}
            <Button onClick={() => setGalleryOpen(false)} variant="outline" className="w-full mt-4 border-white/20" data-testid="gallery-close-btn">إغلاق</Button>
          </div>
        </div>
      )}
    </div>
  );
};

export default FreeBuild;
