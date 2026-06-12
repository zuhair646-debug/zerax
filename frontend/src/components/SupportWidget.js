import React, { useState, useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import { MessageCircle, X, Send, Sparkles, Loader2, ChevronLeft } from 'lucide-react';
import { toast } from 'sonner';

const API = process.env.REACT_APP_BACKEND_URL;

function api(p, opts = {}) {
  const t = localStorage.getItem('token');
  return fetch(`${API}${p}`, {
    ...opts,
    headers: { 'Content-Type': 'application/json', ...(t ? { Authorization: `Bearer ${t}` } : {}), ...(opts.headers || {}) },
  });
}

/**
 * Floating help bubble — visible on every authenticated page.
 * Lets the user:
 *  1. Ask a quick question (AI tries to answer instantly from FAQ/Claude)
 *  2. If unsatisfied, submit a full ticket (subject + body + category)
 *  3. Browse their existing tickets and reply to admin
 */
export default function SupportWidget({ user }) {
  const location = useLocation();
  const [open, setOpen] = useState(false);
  const [view, setView] = useState('ask'); // ask | ticket | list | thread
  const [question, setQuestion] = useState('');
  const [aiAnswer, setAiAnswer] = useState(null);
  const [loading, setLoading] = useState(false);
  const [subject, setSubject] = useState('');
  const [body, setBody] = useState('');
  const [category, setCategory] = useState('support');
  const [tickets, setTickets] = useState([]);
  const [active, setActive] = useState(null);
  const [replyTxt, setReplyTxt] = useState('');

  const loadTickets = async () => {
    const r = await api('/api/support/tickets/me');
    if (r.ok) setTickets((await r.json()).items || []);
  };
  useEffect(() => { if (open && view === 'list') loadTickets(); }, [open, view]);

  const askAI = async () => {
    if (!question.trim()) return;
    setLoading(true);
    try {
      const r = await api('/api/support/ai-quick-answer', {
        method: 'POST', body: JSON.stringify({ question }),
      });
      if (r.ok) setAiAnswer(await r.json());
    } finally { setLoading(false); }
  };

  const submitTicket = async () => {
    if (!subject.trim() || !body.trim()) { toast.error('أدخل الموضوع والمحتوى'); return; }
    setLoading(true);
    try {
      const r = await api('/api/support/tickets', {
        method: 'POST', body: JSON.stringify({ subject, body, category, priority: 'normal' }),
      });
      if (r.ok) {
        toast.success('تم إرسال تذكرتك');
        setSubject(''); setBody(''); setQuestion(''); setAiAnswer(null);
        setView('list');
        loadTickets();
      } else {
        const e = await r.json().catch(() => ({}));
        toast.error(e.detail || 'فشل');
      }
    } finally { setLoading(false); }
  };

  const openThread = async (tid) => {
    const r = await api(`/api/support/tickets/${tid}`);
    if (r.ok) {
      setActive(await r.json());
      setView('thread');
    }
  };

  const sendReply = async () => {
    if (!replyTxt.trim() || !active) return;
    const r = await api(`/api/support/tickets/${active.ticket.id}/messages`, {
      method: 'POST', body: JSON.stringify({ content: replyTxt }),
    });
    if (r.ok) {
      setReplyTxt('');
      openThread(active.ticket.id);
    }
  };

  if (!user) return null;
  // Hide on the FreeBuild Chat workspace (own AI workspace — no need for support widget overlay)
  if (location.pathname.startsWith('/freebuild')) return null;

  return (
    <>
      {!open && (
        <button
          onClick={() => setOpen(true)}
          data-testid="support-widget-trigger"
          data-no-translate="true"
          className="fixed bottom-4 start-4 z-[110] w-12 h-12 rounded-full bg-gradient-to-br from-purple-500 to-pink-500 shadow-2xl shadow-purple-500/30 flex items-center justify-center hover:scale-110 transition"
          aria-label="Support"
          title="مساعدة"
        >
          <MessageCircle className="w-5 h-5 text-white" />
        </button>
      )}
      {open && (
        <div
          data-testid="support-widget-panel"
          data-no-translate="true"
          dir="rtl"
          className="fixed bottom-4 start-4 z-[110] w-[360px] max-w-[92vw] max-h-[80vh] bg-zinc-950 border border-purple-400/30 rounded-2xl shadow-2xl flex flex-col"
          style={{ pointerEvents: 'auto' }}
        >
          {/* Header */}
          <div className="p-3 border-b border-zinc-800 flex items-center justify-between" data-no-translate="true">
            <div className="flex items-center gap-2">
              {view !== 'ask' && view !== 'list' && (
                <button onClick={() => setView('ask')} className="text-zinc-400 hover:text-white">
                  <ChevronLeft className="w-4 h-4" />
                </button>
              )}
              <MessageCircle className="w-4 h-4 text-purple-400" />
              <span className="font-bold text-white text-sm">مركز المساعدة</span>
            </div>
            <button onClick={() => setOpen(false)} className="text-zinc-500 hover:text-white">
              <X className="w-4 h-4" />
            </button>
          </div>

          {/* Tabs */}
          <div className="flex border-b border-zinc-800 text-xs" data-no-translate="true">
            {[
              ['ask', 'اسأل'],
              ['ticket', 'تذكرة جديدة'],
              ['list', 'تذاكري'],
            ].map(([k, l]) => (
              <button
                key={k}
                onClick={() => { setView(k); setActive(null); }}
                className={`flex-1 px-2 py-2 ${view === k ? 'text-purple-300 border-b-2 border-purple-400' : 'text-zinc-500'}`}
              >
                {l}
              </button>
            ))}
          </div>

          {/* Body */}
          <div className="flex-1 overflow-y-auto p-3 text-sm text-zinc-200">
            {view === 'ask' && (
              <div>
                <p className="text-zinc-500 text-xs mb-2">جرّب نسأل الذكاء الاصطناعي — يجاوب فوراً.</p>
                <textarea
                  value={question}
                  onChange={(e) => setQuestion(e.target.value)}
                  placeholder="اكتب سؤالك هنا..."
                  rows={3}
                  className="w-full bg-zinc-900 border border-zinc-800 rounded-lg p-2 text-sm focus:border-purple-400 outline-none"
                />
                <button
                  onClick={askAI}
                  disabled={loading || !question.trim()}
                  className="mt-2 w-full bg-purple-500/20 border border-purple-400/40 text-purple-200 rounded-lg py-2 text-sm font-bold disabled:opacity-50 flex items-center justify-center gap-1"
                >
                  {loading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Sparkles className="w-3.5 h-3.5" />}
                  اسأل
                </button>
                {aiAnswer && (
                  <div className="mt-3 bg-purple-500/10 border border-purple-400/30 rounded-lg p-3">
                    <div className="text-[10px] text-purple-300 font-bold mb-1">💡 إجابة الذكاء:</div>
                    <p className="text-zinc-200 whitespace-pre-wrap text-xs leading-relaxed">{aiAnswer.answer}</p>
                    {!aiAnswer.confident && (
                      <button
                        onClick={() => { setBody(question); setSubject(question.slice(0, 80)); setView('ticket'); }}
                        className="mt-2 text-[11px] text-amber-400 hover:underline"
                      >
                        لم تحل مشكلتي — أرسل تذكرة للفريق →
                      </button>
                    )}
                  </div>
                )}
              </div>
            )}

            {view === 'ticket' && (
              <div className="space-y-2">
                <input
                  value={subject}
                  onChange={(e) => setSubject(e.target.value)}
                  placeholder="الموضوع"
                  className="w-full bg-zinc-900 border border-zinc-800 rounded-lg p-2 text-sm"
                />
                <select
                  value={category}
                  onChange={(e) => setCategory(e.target.value)}
                  className="w-full bg-zinc-900 border border-zinc-800 rounded-lg p-2 text-sm"
                >
                  <option value="support">مشكلة / دعم</option>
                  <option value="suggestion">اقتراح</option>
                  <option value="bug">خطأ في الموقع</option>
                  <option value="feature">طلب ميزة</option>
                  <option value="payout">سحب أموال</option>
                </select>
                <textarea
                  value={body}
                  onChange={(e) => setBody(e.target.value)}
                  placeholder="اشرح مشكلتك بالتفصيل..."
                  rows={5}
                  className="w-full bg-zinc-900 border border-zinc-800 rounded-lg p-2 text-sm focus:border-purple-400 outline-none"
                />
                <button
                  onClick={submitTicket}
                  disabled={loading || !subject.trim() || !body.trim()}
                  className="w-full bg-purple-500 text-white rounded-lg py-2 text-sm font-bold disabled:opacity-50 flex items-center justify-center gap-1"
                >
                  {loading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Send className="w-3.5 h-3.5" />}
                  إرسال التذكرة
                </button>
              </div>
            )}

            {view === 'list' && !active && (
              <div>
                {tickets.length === 0 ? (
                  <div className="text-zinc-500 text-center py-8 text-xs">لا توجد تذاكر</div>
                ) : (
                  <div className="space-y-1.5">
                    {tickets.map((t) => (
                      <button
                        key={t.id}
                        onClick={() => openThread(t.id)}
                        className="w-full text-right bg-zinc-900 border border-zinc-800 rounded-lg p-2.5 hover:border-purple-400/30"
                      >
                        <div className="flex justify-between items-start mb-1">
                          <span className="text-sm font-bold truncate">{t.subject}</span>
                          <span className={`text-[9px] px-1.5 py-0.5 rounded ${
                            t.status === 'open' ? 'bg-amber-500/20 text-amber-300' :
                            t.status === 'replied' ? 'bg-emerald-500/20 text-emerald-300' :
                            'bg-zinc-700 text-zinc-400'
                          }`}>{t.status}</span>
                        </div>
                        <div className="text-[10px] text-zinc-500" data-no-translate="true">
                          {t.category} · {(t.last_message_at || '').slice(0, 16)}
                        </div>
                      </button>
                    ))}
                  </div>
                )}
              </div>
            )}

            {view === 'thread' && active && (
              <div className="flex flex-col h-full">
                <div className="font-bold text-sm mb-2">{active.ticket.subject}</div>
                <div className="flex-1 overflow-y-auto space-y-2 mb-2 max-h-60">
                  {active.messages.map((m) => (
                    <div
                      key={m.id}
                      className={`p-2 rounded-lg text-xs ${
                        m.sender_role === 'user' ? 'bg-purple-500/10 border border-purple-400/20 mr-4' :
                        m.sender_role === 'admin' ? 'bg-emerald-500/10 border border-emerald-400/20 ml-4' :
                        'bg-amber-500/10 border border-amber-400/20 ml-4'
                      }`}
                    >
                      <div className="text-[9px] text-zinc-500 mb-1" data-no-translate="true">
                        [{m.sender_role}] {(m.created_at || '').slice(0, 16)}
                      </div>
                      <div className="text-zinc-200 whitespace-pre-wrap">{m.content}</div>
                    </div>
                  ))}
                </div>
                {active.ticket.status !== 'closed' && (
                  <div className="flex gap-1">
                    <input
                      value={replyTxt}
                      onChange={(e) => setReplyTxt(e.target.value)}
                      onKeyDown={(e) => e.key === 'Enter' && sendReply()}
                      placeholder="ردك..."
                      className="flex-1 bg-zinc-900 border border-zinc-800 rounded-lg p-2 text-xs"
                    />
                    <button onClick={sendReply} className="bg-purple-500 text-white px-2 rounded-lg">
                      <Send className="w-3.5 h-3.5" />
                    </button>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}
    </>
  );
}
