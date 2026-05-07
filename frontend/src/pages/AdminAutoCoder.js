import React, { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Toaster, toast } from 'sonner';
import {
  Lock, Unlock, KeyRound, Send, Loader2, Plus, Trash2,
  ArrowLeft, Terminal, FileCode, FolderTree, GitBranch,
  Search, FileEdit, FilePlus, FileX, RotateCw, ShieldCheck,
  AlertTriangle, Copy, ScrollText, MessageSquare,
} from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;
const SESSION_KEY = 'zitex_autocoder_session';

const TOOL_ICON = {
  list_dir: FolderTree,
  read_file: FileCode,
  write_file: FilePlus,
  edit_file: FileEdit,
  delete_file: FileX,
  search_code: Search,
  run_command: Terminal,
  restart_service: RotateCw,
  git_status: GitBranch,
  git_diff: GitBranch,
  git_commit_push: GitBranch,
};

const TOOL_LABEL = {
  list_dir: 'قائمة مجلد',
  read_file: 'قراءة ملف',
  write_file: 'كتابة ملف',
  edit_file: 'تعديل ملف',
  delete_file: 'حذف ملف',
  search_code: 'بحث في الكود',
  run_command: 'تنفيذ أمر',
  restart_service: 'إعادة تشغيل خدمة',
  git_status: 'git status',
  git_diff: 'git diff',
  git_commit_push: 'commit + push',
};

export default function AdminAutoCoder() {
  const nav = useNavigate();
  const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null;
  const [phase, setPhase] = useState('loading'); // loading | setup | locked | unlocked
  const [acToken, setAcToken] = useState(null);
  const [acExpiresAt, setAcExpiresAt] = useState(null);

  // setup state
  const [setupPasscode, setSetupPasscode] = useState('');
  const [setupConfirm, setSetupConfirm] = useState('');
  const [setupBusy, setSetupBusy] = useState(false);
  const [generatedRecovery, setGeneratedRecovery] = useState(null);

  // unlock state
  const [unlockPasscode, setUnlockPasscode] = useState('');
  const [unlockBusy, setUnlockBusy] = useState(false);
  const [showRecover, setShowRecover] = useState(false);
  const [recoveryCode, setRecoveryCode] = useState('');
  const [recoveryNewPass, setRecoveryNewPass] = useState('');
  const [recoveryBusy, setRecoveryBusy] = useState(false);

  // chat state
  const [conversations, setConversations] = useState([]);
  const [conversationId, setConversationId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const [currentStream, setCurrentStream] = useState('');
  const [currentTools, setCurrentTools] = useState([]);
  const [showSidebar, setShowSidebar] = useState(false);
  const scrollRef = useRef(null);

  // ---- bootstrap ----
  useEffect(() => {
    if (!token) { nav('/login'); return; }
    bootstrap();
    // eslint-disable-next-line
  }, []);

  const bootstrap = async () => {
    try {
      const r = await fetch(`${API}/api/autocoder/status`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (r.status === 403) {
        toast.error('هذا القسم للمالك فقط');
        nav('/dashboard'); return;
      }
      if (!r.ok) throw new Error('status failed');
      const d = await r.json();
      if (!d.is_setup) { setPhase('setup'); return; }
      // try restore session
      try {
        const stored = JSON.parse(localStorage.getItem(SESSION_KEY) || 'null');
        if (stored && stored.token && stored.expires_at) {
          if (new Date(stored.expires_at) > new Date()) {
            setAcToken(stored.token);
            setAcExpiresAt(stored.expires_at);
            setPhase('unlocked');
            loadConversations(stored.token);
            return;
          }
          localStorage.removeItem(SESSION_KEY);
        }
      } catch (_) {}
      setPhase('locked');
    } catch (e) {
      toast.error('فشل تحميل الحالة');
      setPhase('locked');
    }
  };

  // ---- setup ----
  const doSetup = async () => {
    if (setupPasscode.length < 6) { toast.error('كلمة السر 6 أحرف على الأقل'); return; }
    if (setupPasscode !== setupConfirm) { toast.error('كلمتا السر غير متطابقتين'); return; }
    setSetupBusy(true);
    try {
      const r = await fetch(`${API}/api/autocoder/setup`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ passcode: setupPasscode }),
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || 'setup failed');
      setGeneratedRecovery(d.recovery_codes);
      toast.success('تم الإعداد. احفظ رموز الاسترجاع!');
    } catch (e) {
      toast.error(e.message);
    } finally { setSetupBusy(false); }
  };

  const finishSetupAfterRecovery = () => {
    setGeneratedRecovery(null);
    setSetupPasscode('');
    setSetupConfirm('');
    setPhase('locked');
  };

  // ---- unlock ----
  const doUnlock = async () => {
    if (!unlockPasscode) return;
    setUnlockBusy(true);
    try {
      const r = await fetch(`${API}/api/autocoder/unlock`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ passcode: unlockPasscode }),
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || 'unlock failed');
      setAcToken(d.session_token);
      setAcExpiresAt(d.expires_at);
      localStorage.setItem(SESSION_KEY, JSON.stringify({
        token: d.session_token, expires_at: d.expires_at,
      }));
      setUnlockPasscode('');
      setPhase('unlocked');
      toast.success('تم فتح القفل');
      loadConversations(d.session_token);
    } catch (e) {
      toast.error('كلمة السر خاطئة');
    } finally { setUnlockBusy(false); }
  };

  const doRecover = async () => {
    if (!recoveryCode || recoveryNewPass.length < 6) { toast.error('املأ الحقول'); return; }
    setRecoveryBusy(true);
    try {
      const r = await fetch(`${API}/api/autocoder/recover`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ recovery_code: recoveryCode, new_passcode: recoveryNewPass }),
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || 'recover failed');
      toast.success('تم استرجاع الوصول. سجّل دخول بكلمة السر الجديدة');
      if (d.new_recovery_codes && d.new_recovery_codes.length) {
        setGeneratedRecovery(d.new_recovery_codes);
      }
      setShowRecover(false);
      setRecoveryCode('');
      setRecoveryNewPass('');
    } catch (e) {
      toast.error('رمز استرجاع غير صالح');
    } finally { setRecoveryBusy(false); }
  };

  const doLock = async () => {
    try {
      await fetch(`${API}/api/autocoder/lock`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          'X-AutoCoder-Token': acToken || '',
        },
      });
    } catch (_) {}
    localStorage.removeItem(SESSION_KEY);
    setAcToken(null);
    setMessages([]);
    setConversationId(null);
    setPhase('locked');
    toast.success('تم القفل');
  };

  // ---- chat ----
  const loadConversations = async (tk) => {
    try {
      const r = await fetch(`${API}/api/autocoder/conversations`, {
        headers: { Authorization: `Bearer ${token}`, 'X-AutoCoder-Token': tk || acToken || '' },
      });
      const d = await r.json();
      setConversations(d.conversations || []);
    } catch (_) {}
  };

  const loadConversation = async (cid) => {
    try {
      const r = await fetch(`${API}/api/autocoder/conversation/${cid}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      const d = await r.json();
      setMessages(d.messages || []);
      setConversationId(cid);
      setShowSidebar(false);
    } catch (e) { toast.error('فشل التحميل'); }
  };

  const newChat = () => {
    setMessages([]);
    setConversationId(null);
    setCurrentStream('');
    setCurrentTools([]);
    setShowSidebar(false);
  };

  const deleteConversation = async (cid) => {
    if (!window.confirm('احذف هذه المحادثة؟')) return;
    try {
      await fetch(`${API}/api/autocoder/conversation/${cid}`, {
        method: 'DELETE', headers: { Authorization: `Bearer ${token}` },
      });
      if (cid === conversationId) newChat();
      loadConversations();
    } catch (_) {}
  };

  const send = async () => {
    const msg = input.trim();
    if (!msg || sending) return;
    setInput('');
    setSending(true);
    setMessages((prev) => [...prev, { role: 'user', content: msg }]);
    setCurrentStream('');
    setCurrentTools([]);

    try {
      const r = await fetch(`${API}/api/autocoder/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
          'X-AutoCoder-Token': acToken,
        },
        body: JSON.stringify({ conversation_id: conversationId, message: msg }),
      });
      if (r.status === 401) {
        toast.error('انتهت الجلسة. ادخل كلمة السر مرة ثانية');
        localStorage.removeItem(SESSION_KEY);
        setPhase('locked');
        return;
      }
      if (!r.body) throw new Error('no stream');
      const reader = r.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      let assistantText = '';
      let toolEvents = [];

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const parts = buffer.split('\n\n');
        buffer = parts.pop() || '';
        for (const part of parts) {
          if (!part.startsWith('data: ')) continue;
          try {
            const evt = JSON.parse(part.slice(6));
            if (evt.type === 'text') {
              assistantText += evt.content;
              setCurrentStream(assistantText);
            } else if (evt.type === 'tool') {
              toolEvents.push(evt);
              setCurrentTools([...toolEvents]);
            } else if (evt.type === 'saved') {
              setConversationId(evt.conversation_id);
              loadConversations();
            } else if (evt.type === 'error') {
              toast.error(evt.message);
            }
          } catch (_) {}
        }
      }

      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: assistantText, tool_events: toolEvents },
      ]);
      setCurrentStream('');
      setCurrentTools([]);
    } catch (e) {
      toast.error('خطأ في الشبكة: ' + e.message);
    } finally { setSending(false); }
  };

  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  }, [messages, currentStream, currentTools]);

  // ════════════════════════════════════════════════════════════════════
  // Render gates
  // ════════════════════════════════════════════════════════════════════
  if (phase === 'loading') {
    return (
      <div className="min-h-screen bg-[#050505] text-white flex items-center justify-center">
        <Loader2 className="w-6 h-6 animate-spin text-amber-400" />
      </div>
    );
  }

  if (generatedRecovery) {
    return (
      <RecoveryDisplay
        codes={generatedRecovery}
        onDone={phase === 'setup' ? finishSetupAfterRecovery : () => setGeneratedRecovery(null)}
      />
    );
  }

  if (phase === 'setup') {
    return (
      <LockShell title="إعداد قسم برمجة زيتاكس">
        <div className="text-amber-300/80 text-xs mb-4 leading-relaxed">
          هذا أول دخول لك. ضع كلمة سر قوية. سنولّد لك 6 رموز استرجاع لاستخدامها لو نسيت كلمة السر.
        </div>
        <input
          type="password"
          value={setupPasscode}
          onChange={(e) => setSetupPasscode(e.target.value)}
          placeholder="كلمة السر (6 أحرف على الأقل)"
          data-testid="setup-passcode"
          className="w-full bg-black/40 border border-white/15 rounded-lg px-4 py-3 mb-3 text-sm focus:border-amber-400 outline-none"
        />
        <input
          type="password"
          value={setupConfirm}
          onChange={(e) => setSetupConfirm(e.target.value)}
          placeholder="تأكيد كلمة السر"
          data-testid="setup-confirm"
          className="w-full bg-black/40 border border-white/15 rounded-lg px-4 py-3 mb-4 text-sm focus:border-amber-400 outline-none"
        />
        <button
          onClick={doSetup}
          disabled={setupBusy}
          data-testid="setup-submit"
          className="w-full py-3 rounded-lg bg-amber-500 hover:bg-amber-400 text-black font-bold text-sm flex items-center justify-center gap-2 disabled:opacity-50"
        >
          {setupBusy ? <Loader2 className="w-4 h-4 animate-spin" /> : <ShieldCheck className="w-4 h-4" />}
          إنشاء الحماية
        </button>
      </LockShell>
    );
  }

  if (phase === 'locked') {
    return (
      <LockShell title="برمجة زيتاكس">
        {!showRecover ? (
          <>
            <div className="text-amber-300/70 text-xs mb-4 leading-relaxed">
              قسم خاص بك بس. أدخل كلمة السر للدخول.
            </div>
            <input
              type="password"
              value={unlockPasscode}
              onChange={(e) => setUnlockPasscode(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && doUnlock()}
              placeholder="كلمة السر"
              data-testid="unlock-passcode"
              autoFocus
              className="w-full bg-black/40 border border-white/15 rounded-lg px-4 py-3 mb-3 text-sm focus:border-amber-400 outline-none"
            />
            <button
              onClick={doUnlock}
              disabled={unlockBusy}
              data-testid="unlock-submit"
              className="w-full py-3 rounded-lg bg-amber-500 hover:bg-amber-400 text-black font-bold text-sm flex items-center justify-center gap-2 disabled:opacity-50"
            >
              {unlockBusy ? <Loader2 className="w-4 h-4 animate-spin" /> : <Unlock className="w-4 h-4" />}
              دخول
            </button>
            <button
              onClick={() => setShowRecover(true)}
              data-testid="recover-link"
              className="w-full mt-3 text-amber-300/70 hover:text-amber-300 text-xs"
            >
              نسيت كلمة السر؟ استخدم رمز استرجاع
            </button>
          </>
        ) : (
          <>
            <div className="text-amber-300/70 text-xs mb-4 leading-relaxed">
              ادخل أحد رموز الاسترجاع الـ6 (يستخدم مرة واحدة) + كلمة سر جديدة.
            </div>
            <input
              type="text"
              value={recoveryCode}
              onChange={(e) => setRecoveryCode(e.target.value.toUpperCase())}
              placeholder="رمز الاسترجاع (مثال: ABCD-1234-EF56-7890)"
              data-testid="recovery-code"
              className="w-full bg-black/40 border border-white/15 rounded-lg px-4 py-3 mb-3 text-sm font-mono focus:border-amber-400 outline-none"
            />
            <input
              type="password"
              value={recoveryNewPass}
              onChange={(e) => setRecoveryNewPass(e.target.value)}
              placeholder="كلمة السر الجديدة"
              data-testid="recovery-new-passcode"
              className="w-full bg-black/40 border border-white/15 rounded-lg px-4 py-3 mb-4 text-sm focus:border-amber-400 outline-none"
            />
            <button
              onClick={doRecover}
              disabled={recoveryBusy}
              data-testid="recover-submit"
              className="w-full py-3 rounded-lg bg-amber-500 hover:bg-amber-400 text-black font-bold text-sm flex items-center justify-center gap-2 disabled:opacity-50"
            >
              {recoveryBusy ? <Loader2 className="w-4 h-4 animate-spin" /> : <KeyRound className="w-4 h-4" />}
              استرجاع
            </button>
            <button
              onClick={() => setShowRecover(false)}
              className="w-full mt-3 text-white/50 hover:text-white text-xs"
            >
              رجوع
            </button>
          </>
        )}
      </LockShell>
    );
  }

  // ════════════════════════════════════════════════════════════════════
  // Unlocked: full chat shell
  // ════════════════════════════════════════════════════════════════════
  return (
    <div dir="rtl" className="h-screen bg-[#050505] text-white flex flex-col overflow-hidden">
      <Toaster richColors position="top-center" />

      <header className="h-14 px-3 md:px-4 border-b border-amber-500/20 flex items-center justify-between bg-black/60 backdrop-blur z-20 flex-shrink-0">
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowSidebar((s) => !s)}
            data-testid="ac-toggle-sidebar"
            className="md:hidden p-2 hover:bg-white/5 rounded"
          >
            <MessageSquare className="w-4 h-4" />
          </button>
          <button onClick={() => nav('/admin')} className="p-1.5 hover:bg-white/5 rounded">
            <ArrowLeft className="w-4 h-4" />
          </button>
          <h1 className="font-black text-sm flex items-center gap-1.5">
            <ShieldCheck className="w-4 h-4 text-amber-400" /> برمجة زيتاكس
            <span className="text-[10px] text-amber-300/60 font-normal me-1">(Owner Only)</span>
          </h1>
        </div>
        <div className="flex items-center gap-2">
          <SessionTimer expiresAt={acExpiresAt} />
          <button
            onClick={newChat}
            data-testid="ac-new-chat"
            className="px-3 py-1.5 rounded-md bg-amber-500 text-black text-xs font-bold flex items-center gap-1 hover:bg-amber-400"
          >
            <Plus className="w-3.5 h-3.5" /> جديدة
          </button>
          <button
            onClick={doLock}
            data-testid="ac-lock"
            title="قفل القسم"
            className="px-2 py-1.5 rounded-md bg-rose-500/20 text-rose-300 text-xs hover:bg-rose-500/30 flex items-center gap-1"
          >
            <Lock className="w-3.5 h-3.5" /> قفل
          </button>
        </div>
      </header>

      <div className="flex-1 flex overflow-hidden">
        <aside
          className={`${showSidebar ? 'flex' : 'hidden md:flex'} flex-col w-64 border-e border-white/10 bg-black/30 flex-shrink-0`}
        >
          <div className="p-2 border-b border-white/10 text-[10px] uppercase tracking-widest text-white/40">
            المحادثات
          </div>
          <div className="flex-1 overflow-y-auto px-2 py-2 space-y-1">
            {conversations.length === 0 ? (
              <div className="text-center text-white/40 text-xs p-4">لا توجد بعد</div>
            ) : conversations.map((c) => (
              <div
                key={c.id}
                data-testid={`ac-conv-${c.id}`}
                onClick={() => loadConversation(c.id)}
                className={`group p-2 rounded-lg cursor-pointer flex items-start gap-2 text-xs transition ${conversationId === c.id ? 'bg-amber-500/15 border border-amber-400/30' : 'hover:bg-white/5'}`}
              >
                <MessageSquare className="w-3.5 h-3.5 mt-0.5 flex-shrink-0 opacity-60" />
                <span className="flex-1 line-clamp-2 leading-snug">{c.preview || 'محادثة'}</span>
                <button
                  onClick={(e) => { e.stopPropagation(); deleteConversation(c.id); }}
                  className="opacity-0 group-hover:opacity-100 text-rose-400 hover:text-rose-300"
                >
                  <Trash2 className="w-3 h-3" />
                </button>
              </div>
            ))}
          </div>
        </aside>

        <main className="flex-1 flex flex-col min-w-0">
          <div ref={scrollRef} className="flex-1 overflow-y-auto p-4 md:p-6 space-y-4">
            {messages.length === 0 && !currentStream && (
              <div className="max-w-2xl mx-auto text-center py-12">
                <ShieldCheck className="w-12 h-12 text-amber-400 mx-auto mb-4" />
                <h3 className="text-2xl font-black mb-2">شنو نبرمج اليوم؟</h3>
                <p className="text-white/60 text-sm mb-6 leading-relaxed">
                  هذا ذكاء برمجة متخصص. عنده وصول كامل لقاعدة الكود حقّك.<br/>
                  يقرا، يكتب، ينفّذ أوامر، ويعمل commit + push للـGitHub.
                </p>
                <div className="grid md:grid-cols-2 gap-3 text-start">
                  {[
                    'أضف صفحة جديدة /admin/logs تعرض آخر 100 سجل من autocoder_audit',
                    'اعرض شجرة /app/backend/modules وقل لي وش وظيفة كل module',
                    'اقرا /app/backend/server.py واشرح لي كيف الـauth يشتغل',
                    'سوّي fix لأي bug تشوفه بعد ما تشغّل pytest على /app/backend/tests',
                  ].map((ex) => (
                    <button
                      key={ex}
                      onClick={() => setInput(ex)}
                      data-testid="ac-example-chip"
                      className="p-3 rounded-xl border border-white/10 bg-white/[0.03] hover:border-amber-400/30 hover:bg-amber-500/5 text-sm transition leading-snug"
                    >
                      {ex}
                    </button>
                  ))}
                </div>
                <div className="mt-8 inline-flex items-start gap-2 text-[11px] text-amber-300/60 bg-amber-500/5 border border-amber-500/15 rounded-lg p-3 max-w-md mx-auto">
                  <AlertTriangle className="w-3.5 h-3.5 mt-0.5 flex-shrink-0" />
                  <div className="text-start leading-relaxed">
                    صلاحيات مفتوحة بالكامل (read/write/exec/git push). راجع كل عملية قبل ما توافق.
                  </div>
                </div>
              </div>
            )}

            {messages.map((m, i) => <MessageBubble key={i} m={m} />)}

            {(currentStream || currentTools.length > 0) && (
              <div className="bg-white/[0.04] border border-white/10 rounded-2xl p-4 max-w-3xl">
                <div className="text-[10px] uppercase tracking-widest text-amber-400/80 mb-2">برمجة زيتاكس</div>
                {currentTools.map((t, i) => <ToolPill key={i} t={t} />)}
                {currentStream && <div className="text-sm leading-relaxed whitespace-pre-wrap mt-2">{currentStream}</div>}
              </div>
            )}
          </div>

          <div className="border-t border-white/10 p-3 md:p-4 bg-black/40">
            <div className="max-w-3xl mx-auto flex items-end gap-2">
              <textarea
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); }
                }}
                rows={2}
                placeholder="اكتب أمرك للذكاء... مثال: اقرا server.py واشرح كيف الـauth يشتغل"
                data-testid="ac-input"
                className="flex-1 bg-black/40 border border-white/15 rounded-xl px-4 py-3 text-sm resize-none focus:border-amber-400 outline-none"
              />
              <button
                onClick={send}
                disabled={sending || !input.trim()}
                data-testid="ac-send"
                className="h-12 w-12 rounded-xl bg-amber-500 hover:bg-amber-400 text-black flex items-center justify-center disabled:opacity-50"
              >
                {sending ? <Loader2 className="w-5 h-5 animate-spin" /> : <Send className="w-5 h-5" />}
              </button>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}

// ════════════════════════════════════════════════════════════════════════
// Sub-components
// ════════════════════════════════════════════════════════════════════════
function LockShell({ title, children }) {
  return (
    <div dir="rtl" className="min-h-screen bg-[#050505] text-white flex items-center justify-center p-6">
      <Toaster richColors position="top-center" />
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <div className="inline-flex w-16 h-16 rounded-2xl bg-amber-500/15 border border-amber-400/30 items-center justify-center mb-4">
            <Lock className="w-7 h-7 text-amber-400" />
          </div>
          <h1 className="text-2xl font-black mb-1" data-testid="ac-lock-title">{title}</h1>
          <p className="text-white/50 text-xs">قسم خاص بمالك المنصة فقط</p>
        </div>
        <div className="bg-white/[0.03] border border-white/10 rounded-2xl p-6 backdrop-blur">
          {children}
        </div>
      </div>
    </div>
  );
}

function RecoveryDisplay({ codes, onDone }) {
  const copyAll = () => {
    navigator.clipboard.writeText(codes.join('\n'));
    toast.success('تم النسخ');
  };
  return (
    <div dir="rtl" className="min-h-screen bg-[#050505] text-white flex items-center justify-center p-6">
      <Toaster richColors position="top-center" />
      <div className="w-full max-w-lg">
        <div className="text-center mb-6">
          <div className="inline-flex w-16 h-16 rounded-2xl bg-emerald-500/15 border border-emerald-400/30 items-center justify-center mb-4">
            <KeyRound className="w-7 h-7 text-emerald-400" />
          </div>
          <h1 className="text-2xl font-black mb-1">رموز الاسترجاع</h1>
          <p className="text-amber-300/80 text-xs leading-relaxed">
            احفظ هذه الرموز في مكان آمن جداً (Password Manager / Notes مشفّرة).<br/>
            كل رمز يعمل مرة واحدة فقط لاسترجاع الوصول لو نسيت كلمة السر.
          </p>
        </div>
        <div className="bg-black/60 border border-amber-500/20 rounded-2xl p-5 mb-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 font-mono text-sm" data-testid="recovery-codes-list">
            {codes.map((c, i) => (
              <div key={i} className="bg-amber-500/5 border border-amber-500/15 rounded-lg px-3 py-2 text-amber-200 text-center select-all">
                {c}
              </div>
            ))}
          </div>
        </div>
        <div className="flex gap-2">
          <button
            onClick={copyAll}
            data-testid="copy-recovery-codes"
            className="flex-1 py-3 rounded-lg bg-white/10 hover:bg-white/15 text-sm font-bold flex items-center justify-center gap-2"
          >
            <Copy className="w-4 h-4" /> نسخ الكل
          </button>
          <button
            onClick={onDone}
            data-testid="recovery-codes-done"
            className="flex-1 py-3 rounded-lg bg-amber-500 hover:bg-amber-400 text-black text-sm font-bold"
          >
            حفظت الرموز، تابع
          </button>
        </div>
      </div>
    </div>
  );
}

function SessionTimer({ expiresAt }) {
  const [remaining, setRemaining] = useState('');
  useEffect(() => {
    if (!expiresAt) return;
    const tick = () => {
      const ms = new Date(expiresAt) - new Date();
      if (ms <= 0) { setRemaining('انتهت'); return; }
      const h = Math.floor(ms / 3600000);
      const m = Math.floor((ms % 3600000) / 60000);
      setRemaining(h > 0 ? `${h}س ${m}د` : `${m}د`);
    };
    tick();
    const id = setInterval(tick, 30000);
    return () => clearInterval(id);
  }, [expiresAt]);
  if (!remaining) return null;
  return (
    <span
      data-testid="ac-session-timer"
      className="hidden md:inline-flex text-[10px] px-2 py-1 rounded-full bg-emerald-500/10 border border-emerald-400/20 text-emerald-300 items-center gap-1"
    >
      <ScrollText className="w-3 h-3" /> {remaining}
    </span>
  );
}

function MessageBubble({ m }) {
  if (m.role === 'user') {
    return (
      <div className="flex justify-end">
        <div className="bg-amber-500/15 border border-amber-400/25 rounded-2xl rounded-br-sm px-4 py-3 max-w-2xl text-sm leading-relaxed whitespace-pre-wrap">
          {m.content}
        </div>
      </div>
    );
  }
  return (
    <div className="bg-white/[0.04] border border-white/10 rounded-2xl p-4 max-w-3xl">
      <div className="text-[10px] uppercase tracking-widest text-amber-400/80 mb-2">برمجة زيتاكس</div>
      {(m.tool_events || []).map((t, i) => <ToolPill key={i} t={t} />)}
      {m.content && <div className="text-sm leading-relaxed whitespace-pre-wrap mt-2">{m.content}</div>}
    </div>
  );
}

function ToolPill({ t }) {
  const [open, setOpen] = useState(false);
  const Icon = TOOL_ICON[t.name] || Terminal;
  const isCalling = t.status === 'calling';
  const isOk = t.ok !== false;
  return (
    <div className="my-1.5 rounded-lg border border-white/10 bg-black/30 overflow-hidden text-xs">
      <button
        onClick={() => setOpen((o) => !o)}
        className="w-full flex items-center gap-2 px-3 py-2 hover:bg-white/5 text-start"
      >
        <Icon className={`w-3.5 h-3.5 ${isCalling ? 'text-amber-300 animate-pulse' : isOk ? 'text-emerald-300' : 'text-rose-300'}`} />
        <span className="font-bold">{TOOL_LABEL[t.name] || t.name}</span>
        <span className="text-white/40 truncate flex-1">{t.summary || (isCalling ? 'يشتغل...' : '')}</span>
        {!isCalling && (
          <span className={`text-[10px] px-1.5 py-0.5 rounded ${isOk ? 'bg-emerald-500/15 text-emerald-300' : 'bg-rose-500/15 text-rose-300'}`}>
            {isOk ? 'تم' : 'فشل'}
          </span>
        )}
      </button>
      {open && (
        <div className="border-t border-white/10 bg-black/40 p-3 space-y-2">
          {t.args && Object.keys(t.args).length > 0 && (
            <div>
              <div className="text-[10px] uppercase text-white/40 mb-1">المدخلات</div>
              <pre className="text-[11px] text-white/70 whitespace-pre-wrap break-all bg-black/40 rounded p-2 max-h-40 overflow-y-auto">{JSON.stringify(t.args, null, 2)}</pre>
            </div>
          )}
          {t.preview && (
            <div>
              <div className="text-[10px] uppercase text-white/40 mb-1">النتيجة</div>
              <pre className="text-[11px] text-white/70 whitespace-pre-wrap break-all bg-black/40 rounded p-2 max-h-60 overflow-y-auto">{t.preview}</pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
