/**
 * AdminSupport — Inbox for the support team.
 *
 * Two-pane layout: ticket list (filtered by status) on the right,
 * full conversation + reply composer + AUDIT SNAPSHOT on the left.
 * The audit snapshot gives admins instant context: credits, recent
 * payments, recent usage, project count, storage subscription.
 */
import React, { useEffect, useState, useCallback, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, Loader2, RefreshCw, Bot, Shield, User as UserIcon, Send, Inbox, Clock, CheckCircle2, Archive } from 'lucide-react';
import { toast } from 'sonner';

const API = process.env.REACT_APP_BACKEND_URL;

const STATUS_TABS = [
  { id: 'awaiting_admin', label: 'بانتظار الرد', icon: Clock },
  { id: 'open',           label: 'مفتوحة',       icon: Inbox },
  { id: 'replied',        label: 'تم الرد',      icon: CheckCircle2 },
  { id: 'auto_resolved',  label: 'حلّها المساعد', icon: Bot },
  { id: 'resolved',       label: 'محلولة',       icon: CheckCircle2 },
  { id: 'closed',         label: 'مغلقة',        icon: Archive },
];

const CATEGORY_LABEL = {
  support: 'استفسار', bug: 'مشكلة تقنية', billing: 'فواتير',
  feature: 'طلب ميزة', suggestion: 'اقتراح', refund: 'استرداد', payout: 'سحب أرباح',
};

const fmtUSD = (n) => `$${(Number(n || 0)).toFixed(2)}`;

export default function AdminSupport() {
  const nav = useNavigate();
  const [tab, setTab] = useState('awaiting_admin');
  const [loading, setLoading] = useState(true);
  const [tickets, setTickets] = useState([]);
  const [counts, setCounts] = useState({});
  const [selectedId, setSelectedId] = useState(null);
  const [thread, setThread] = useState(null);
  const [reply, setReply] = useState('');
  const [sending, setSending] = useState(false);
  const bottomRef = useRef(null);

  const loadList = useCallback(async () => {
    setLoading(true);
    const token = localStorage.getItem('token');
    try {
      const r = await fetch(`${API}/api/admin/support/tickets?status=${tab}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || 'فشل');
      setTickets(d.items || []);
      // Re-fetch counts separately (without status filter)
      const r2 = await fetch(`${API}/api/admin/support/tickets`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (r2.ok) {
        const all = await r2.json();
        const c = {};
        STATUS_TABS.forEach((s) => {
          c[s.id] = (all.items || []).filter((t) => t.status === s.id).length;
        });
        setCounts(c);
      }
    } catch (e) {
      toast.error(e.message || 'فشل التحميل');
    } finally {
      setLoading(false);
    }
  }, [tab]);

  const loadThread = useCallback(async (id) => {
    const token = localStorage.getItem('token');
    try {
      const r = await fetch(`${API}/api/admin/support/tickets/${id}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!r.ok) throw new Error('غير موجود');
      setThread(await r.json());
    } catch (e) {
      toast.error(e.message);
    }
  }, []);

  useEffect(() => { loadList(); }, [loadList]);
  useEffect(() => { if (selectedId) loadThread(selectedId); }, [selectedId, loadThread]);
  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [thread]);

  const sendReply = async (e) => {
    e?.preventDefault();
    const txt = reply.trim();
    if (!txt || !selectedId) return;
    setSending(true);
    const token = localStorage.getItem('token');
    try {
      const r = await fetch(`${API}/api/admin/support/tickets/${selectedId}/reply`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ content: txt }),
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || 'فشل');
      setReply('');
      await loadThread(selectedId);
      await loadList();
      toast.success('تم إرسال الرد');
    } catch (e) {
      toast.error(e.message || 'فشل');
    } finally {
      setSending(false);
    }
  };

  const closeTicket = async (status) => {
    if (!selectedId) return;
    const token = localStorage.getItem('token');
    try {
      const r = await fetch(`${API}/api/admin/support/tickets/${selectedId}/reply`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({
          content: status === 'resolved' ? '✅ تم حل المشكلة. شكراً لتواصلك معنا.' : '🗄️ تم إغلاق التذكرة.',
          new_status: status,
        }),
      });
      if (!r.ok) throw new Error('فشل');
      await loadThread(selectedId);
      await loadList();
      toast.success(status === 'resolved' ? 'تم وضعها كمحلولة' : 'تم الإغلاق');
    } catch (e) {
      toast.error(e.message);
    }
  };

  const t = thread?.ticket;
  const messages = thread?.messages || [];
  const audit = t?.audit_snapshot || {};

  return (
    <div className="min-h-screen bg-zinc-950 text-white" dir="rtl">
      {/* Top bar */}
      <div className="sticky top-0 z-10 backdrop-blur-md bg-zinc-950/90 border-b border-zinc-800">
        <div className="max-w-7xl mx-auto px-4 py-3 flex items-center gap-3">
          <button onClick={() => nav('/admin')} data-testid="admin-back-btn" className="p-2 rounded-full bg-white/5 hover:bg-white/10">
            <ArrowLeft className="w-4 h-4" />
          </button>
          <h1 className="text-lg font-black flex-1">صندوق الدعم — Admin</h1>
          <button onClick={loadList} className="p-2 rounded-full bg-white/5 hover:bg-white/10" title="تحديث">
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
        {/* Status tabs */}
        <div className="max-w-7xl mx-auto px-4 pb-2 flex gap-1.5 overflow-x-auto">
          {STATUS_TABS.map((s) => {
            const Icon = s.icon;
            const active = tab === s.id;
            const count = counts[s.id] || 0;
            return (
              <button
                key={s.id}
                onClick={() => { setTab(s.id); setSelectedId(null); setThread(null); }}
                data-testid={`admin-tab-${s.id}`}
                className={`px-3 py-1.5 rounded-lg text-xs font-bold flex items-center gap-1.5 whitespace-nowrap transition ${
                  active ? 'bg-amber-400 text-black' : 'bg-zinc-800 hover:bg-zinc-700 text-zinc-300'
                }`}
              >
                <Icon className="w-3 h-3" /> {s.label}
                {count > 0 && <span className={`px-1.5 rounded-full text-[10px] font-black ${active ? 'bg-black/20' : 'bg-amber-500/20 text-amber-300'}`}>{count}</span>}
              </button>
            );
          })}
        </div>
      </div>

      <div className="max-w-7xl mx-auto grid grid-cols-1 lg:grid-cols-12 gap-4 p-4">
        {/* List */}
        <div className="lg:col-span-4 rounded-xl border border-zinc-800 bg-zinc-900/50 overflow-hidden max-h-[80vh] flex flex-col">
          {loading ? (
            <div className="flex-1 flex items-center justify-center"><Loader2 className="w-6 h-6 animate-spin text-amber-400" /></div>
          ) : tickets.length === 0 ? (
            <div className="flex-1 flex flex-col items-center justify-center p-8 text-center">
              <Inbox className="w-10 h-10 text-zinc-700 mb-2" />
              <p className="text-zinc-500 text-sm">لا توجد تذاكر في هذا التصنيف</p>
            </div>
          ) : (
            <div className="flex-1 overflow-y-auto divide-y divide-zinc-800">
              {tickets.map((tk) => (
                <button
                  key={tk.id}
                  onClick={() => setSelectedId(tk.id)}
                  data-testid={`admin-ticket-${tk.id}`}
                  className={`w-full text-right p-3 hover:bg-zinc-800/50 transition ${selectedId === tk.id ? 'bg-zinc-800' : ''}`}
                >
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-[10px] px-1.5 py-0.5 rounded bg-amber-500/15 text-amber-300 border border-amber-500/30 font-bold">
                      {CATEGORY_LABEL[tk.category] || tk.category}
                    </span>
                    {tk.unread_for_admin && <span className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-pulse" />}
                  </div>
                  <h3 className="text-sm font-bold truncate">{tk.subject}</h3>
                  <p className="text-[10px] text-zinc-400 truncate">{tk.user_email}</p>
                  <p className="text-[10px] text-zinc-500 mt-0.5">
                    {tk.last_message_at && new Date(tk.last_message_at).toLocaleString('ar-SA', { dateStyle: 'short', timeStyle: 'short' })}
                  </p>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Thread + Audit */}
        <div className="lg:col-span-8 flex flex-col gap-4">
          {!thread ? (
            <div className="rounded-xl border border-zinc-800 bg-zinc-900/40 p-12 text-center text-zinc-500">
              اختر تذكرة لعرضها
            </div>
          ) : (
            <>
              {/* Audit panel */}
              <div className="rounded-xl border border-amber-500/30 bg-amber-500/5 p-4 grid grid-cols-2 md:grid-cols-4 gap-3 text-xs">
                <div>
                  <p className="text-[10px] text-zinc-400 mb-0.5">العميل</p>
                  <p className="font-bold text-white truncate">{audit?.user?.name || audit?.user?.email}</p>
                  <p className="text-[10px] text-zinc-500 truncate">{audit?.user?.email}</p>
                </div>
                <div>
                  <p className="text-[10px] text-zinc-400 mb-0.5">رصيد النقاط</p>
                  <p className="font-black text-emerald-300">{Math.round(Number(audit?.user?.credits || 0)).toLocaleString('en-US')}</p>
                  <p className="text-[10px] text-zinc-500">الدور: {audit?.user?.role || 'user'}</p>
                </div>
                <div>
                  <p className="text-[10px] text-zinc-400 mb-0.5">المشاريع</p>
                  <p className="font-black text-amber-300">{audit?.project_count || 0}</p>
                  <p className="text-[10px] text-zinc-500">باقة: {audit?.user?.storage_tier || 'free'}</p>
                </div>
                <div>
                  <p className="text-[10px] text-zinc-400 mb-0.5">آخر شحن</p>
                  {audit?.recent_transactions?.[0] ? (
                    <>
                      <p className="font-black text-blue-300">{fmtUSD(audit.recent_transactions[0].amount_usd)}</p>
                      <p className="text-[10px] text-zinc-500">
                        {audit.recent_transactions[0].status} · {new Date(audit.recent_transactions[0].created_at).toLocaleDateString('ar-SA')}
                      </p>
                    </>
                  ) : (
                    <p className="text-zinc-600">— لا يوجد —</p>
                  )}
                </div>
              </div>

              {/* AI summary */}
              {t.ai_summary && (
                <div className="rounded-xl border border-purple-500/30 bg-purple-500/5 p-3 text-xs">
                  <p className="text-[10px] text-purple-300 font-bold mb-1 flex items-center gap-1"><Bot className="w-3 h-3" /> ملخص المساعد الذكي</p>
                  <p className="text-purple-100">{t.ai_summary}</p>
                </div>
              )}

              {/* Messages */}
              <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-4 max-h-[55vh] overflow-y-auto space-y-3">
                {messages.map((m) => {
                  const role = m.sender_role;
                  const meta = role === 'admin'
                    ? { icon: Shield, bg: 'bg-amber-500/15 border-amber-500/40 text-amber-100', label: 'فريق الدعم' }
                    : role === 'ai'
                      ? { icon: Bot, bg: 'bg-purple-500/15 border-purple-500/40 text-purple-100', label: 'المساعد الذكي' }
                      : { icon: UserIcon, bg: 'bg-emerald-500/15 border-emerald-500/40 text-emerald-100', label: t?.user_name || 'العميل' };
                  const Icon = meta.icon;
                  const isAdmin = role === 'admin';
                  return (
                    <div key={m.id} className={`flex gap-2 ${isAdmin ? 'flex-row-reverse' : 'flex-row'}`}>
                      <div className={`w-7 h-7 flex-shrink-0 rounded-full border ${meta.bg} flex items-center justify-center`}>
                        <Icon className="w-3.5 h-3.5" />
                      </div>
                      <div className={`max-w-[75%] ${isAdmin ? 'items-end' : 'items-start'} flex flex-col`}>
                        <p className="text-[10px] text-zinc-400 mb-1">
                          {meta.label} · {new Date(m.created_at).toLocaleString('ar-SA', { timeStyle: 'short', dateStyle: 'short' })}
                          {m.is_internal && <span className="ml-1 text-amber-400">(داخلية)</span>}
                        </p>
                        <div className={`rounded-2xl px-3 py-2 border text-xs whitespace-pre-wrap leading-relaxed ${meta.bg}`}>
                          {m.content}
                          {Array.isArray(m.attachments) && m.attachments.length > 0 && (
                            <div className="mt-2 grid grid-cols-1 sm:grid-cols-2 gap-2">
                              {m.attachments.map((a, i) => {
                                const url = `${API}${a.url}`;
                                const isImg = (a.mime || '').startsWith('image/');
                                const isVid = (a.mime || '').startsWith('video/');
                                return (
                                  <a key={i} href={url} target="_blank" rel="noopener noreferrer" className="block rounded-lg overflow-hidden bg-black/30 border border-white/10">
                                    {isImg ? <img src={url} alt={a.name} className="w-full max-h-40 object-cover" />
                                     : isVid ? <video src={url} className="w-full max-h-40 object-cover" controls preload="metadata" />
                                     : <p className="p-2 text-[10px] truncate">{a.name}</p>}
                                  </a>
                                );
                              })}
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  );
                })}
                <div ref={bottomRef} />
              </div>

              {/* Reply composer */}
              {t.status !== 'closed' && t.status !== 'resolved' && (
                <form onSubmit={sendReply} className="flex items-end gap-2">
                  <textarea
                    value={reply}
                    onChange={(e) => setReply(e.target.value)}
                    placeholder="اكتب ردك للعميل…"
                    rows={2}
                    data-testid="admin-reply-input"
                    className="flex-1 px-3 py-2 rounded-lg bg-zinc-800 border border-zinc-700 focus:border-amber-500/60 outline-none text-sm resize-none"
                    maxLength={4000}
                  />
                  <div className="flex flex-col gap-1.5">
                    <button
                      type="submit"
                      disabled={sending || !reply.trim()}
                      data-testid="admin-send-reply-btn"
                      className="px-3 py-2 rounded-lg bg-gradient-to-r from-amber-400 to-yellow-500 text-black text-xs font-black hover:opacity-90 disabled:opacity-40 flex items-center gap-1"
                    >
                      {sending ? <Loader2 className="w-3 h-3 animate-spin" /> : <Send className="w-3 h-3" />} رد
                    </button>
                    <button type="button" onClick={() => closeTicket('resolved')} className="px-3 py-1 rounded-lg bg-emerald-600/40 hover:bg-emerald-600/60 text-[10px] font-bold">
                      حلّ
                    </button>
                    <button type="button" onClick={() => closeTicket('closed')} className="px-3 py-1 rounded-lg bg-zinc-700 hover:bg-zinc-600 text-[10px] font-bold">
                      إغلاق
                    </button>
                  </div>
                </form>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
