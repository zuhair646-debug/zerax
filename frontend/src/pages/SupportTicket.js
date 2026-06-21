/**
 * SupportTicket — Threaded conversation view (telegram-style "برقيات").
 *
 * Shows the full back-and-forth between user / AI / admin, lets the user
 * attach images/videos/PDFs (max 25MB each), and reply with text.
 */
import React, { useEffect, useState, useRef, useCallback } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { ArrowLeft, Send, Paperclip, Loader2, Bot, Shield, User as UserIcon, AlertCircle, Image as ImageIcon, FileText, Video } from 'lucide-react';
import { toast } from 'sonner';

const API = process.env.REACT_APP_BACKEND_URL;

const STATUS_LABEL = {
  open:           'مفتوحة',
  replied:        'رد فريق الدعم',
  awaiting_user:  'بانتظار ردك',
  auto_resolved:  'حلّها المساعد',
  resolved:       'تم الحل',
  closed:         'مغلقة',
};

const SENDER_META = {
  user:  { icon: UserIcon, color: 'bg-emerald-500/15 border-emerald-500/40 text-emerald-100', label: 'أنت' },
  ai:    { icon: Bot,      color: 'bg-purple-500/15 border-purple-500/40 text-purple-100',     label: 'المساعد الذكي' },
  admin: { icon: Shield,   color: 'bg-amber-500/15 border-amber-500/40 text-amber-100',         label: 'فريق الدعم' },
};

const fmtBytes = (b) => {
  if (b < 1024) return `${b} B`;
  if (b < 1024 * 1024) return `${(b / 1024).toFixed(1)} KB`;
  return `${(b / 1024 / 1024).toFixed(1)} MB`;
};

export default function SupportTicket() {
  const nav = useNavigate();
  const { id: ticketId } = useParams();
  const [loading, setLoading] = useState(true);
  const [ticket, setTicket] = useState(null);
  const [messages, setMessages] = useState([]);
  const [reply, setReply] = useState('');
  const [sending, setSending] = useState(false);
  const [uploading, setUploading] = useState(false);
  const fileRef = useRef(null);
  const bottomRef = useRef(null);

  const load = useCallback(async () => {
    setLoading(true);
    const token = localStorage.getItem('token');
    try {
      const r = await fetch(`${API}/api/support/tickets/${ticketId}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!r.ok) {
        toast.error('التذكرة غير موجودة');
        nav('/support');
        return;
      }
      const d = await r.json();
      setTicket(d.ticket);
      setMessages(d.messages || []);
    } catch (e) {
      toast.error('تعذر التحميل');
    }
    setLoading(false);
  }, [ticketId, nav]);

  useEffect(() => { load(); }, [load]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const sendReply = async (e) => {
    e?.preventDefault();
    const txt = reply.trim();
    if (!txt) return;
    if (ticket?.status === 'auto_resolved' || ticket?.status === 'closed') {
      toast.error('هذه التذكرة مغلقة — افتح تذكرة جديدة');
      return;
    }
    setSending(true);
    const token = localStorage.getItem('token');
    try {
      const r = await fetch(`${API}/api/support/tickets/${ticketId}/messages`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ content: txt }),
      });
      if (!r.ok) {
        const d = await r.json();
        throw new Error(d.detail || 'فشل');
      }
      setReply('');
      await load();
    } catch (e) {
      toast.error(e.message || 'فشل الإرسال');
    } finally {
      setSending(false);
    }
  };

  const handleUpload = async (e) => {
    const files = Array.from(e.target.files || []);
    if (!files.length) return;
    if (ticket?.status === 'auto_resolved' || ticket?.status === 'closed') {
      toast.error('التذكرة مغلقة');
      return;
    }
    setUploading(true);
    const token = localStorage.getItem('token');
    try {
      const fd = new FormData();
      files.forEach((f) => fd.append('files', f));
      const r = await fetch(`${API}/api/support/tickets/${ticketId}/upload`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
        body: fd,
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || 'فشل الرفع');
      toast.success(`تم رفع ${d.attachments?.length || 0} ملف`);
      if (fileRef.current) fileRef.current.value = '';
      await load();
    } catch (e) {
      toast.error(e.message || 'فشل الرفع');
    } finally {
      setUploading(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-zinc-950 flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-amber-400" />
      </div>
    );
  }

  if (!ticket) return null;
  const locked = ticket.status === 'auto_resolved' || ticket.status === 'closed';

  return (
    <div className="min-h-screen bg-gradient-to-b from-zinc-950 to-black text-white flex flex-col" dir="rtl">
      {/* Header */}
      <div className="sticky top-0 z-10 backdrop-blur-md bg-zinc-950/80 border-b border-zinc-800">
        <div className="max-w-3xl mx-auto px-4 py-3 flex items-center gap-3">
          <button onClick={() => nav('/support')} data-testid="ticket-back-btn" className="p-2 rounded-full bg-white/5 hover:bg-white/10">
            <ArrowLeft className="w-4 h-4" />
          </button>
          <div className="flex-1 min-w-0">
            <h1 className="font-black truncate text-sm sm:text-base">{ticket.subject}</h1>
            <p className="text-[10px] text-zinc-400">
              {STATUS_LABEL[ticket.status] || ticket.status} ·{' '}
              {new Date(ticket.created_at).toLocaleDateString('ar-SA', { dateStyle: 'medium' })}
            </p>
          </div>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto">
        <div className="max-w-3xl mx-auto px-4 py-6 space-y-4">
          {locked && (
            <div className="rounded-xl border border-purple-500/40 bg-purple-500/10 p-3 flex items-start gap-2 text-xs">
              <AlertCircle className="w-4 h-4 text-purple-300 flex-shrink-0 mt-0.5" />
              <div className="text-purple-100">
                <p className="font-bold mb-0.5">هذه التذكرة مغلقة</p>
                <p className="text-purple-100/80">إذا تحتاج مساعدة جديدة، افتح تذكرة جديدة من قائمة الدعم.</p>
              </div>
            </div>
          )}
          {messages.map((m) => {
            const meta = SENDER_META[m.sender_role] || SENDER_META.user;
            const Icon = meta.icon;
            const isOwn = m.sender_role === 'user';
            return (
              <div
                key={m.id}
                className={`flex gap-2 ${isOwn ? 'flex-row-reverse' : 'flex-row'}`}
                data-testid={`message-${m.id}`}
              >
                <div className="flex-shrink-0">
                  <div className={`w-8 h-8 rounded-full border ${meta.color} flex items-center justify-center`}>
                    <Icon className="w-4 h-4" />
                  </div>
                </div>
                <div className={`max-w-[80%] ${isOwn ? 'items-end' : 'items-start'} flex flex-col`}>
                  <div className={`text-[10px] text-zinc-400 mb-1 ${isOwn ? 'text-left' : 'text-right'}`}>
                    {meta.label} · {new Date(m.created_at).toLocaleString('ar-SA', { timeStyle: 'short', dateStyle: 'short' })}
                  </div>
                  <div className={`rounded-2xl px-3.5 py-2.5 border ${meta.color} text-sm whitespace-pre-wrap leading-relaxed`}>
                    {m.content}
                    {Array.isArray(m.attachments) && m.attachments.length > 0 && (
                      <div className="mt-2 grid grid-cols-1 sm:grid-cols-2 gap-2">
                        {m.attachments.map((a, i) => {
                          const isImg = (a.mime || '').startsWith('image/');
                          const isVid = (a.mime || '').startsWith('video/');
                          const url = `${API}${a.url}`;
                          return (
                            <a key={i} href={url} target="_blank" rel="noopener noreferrer" className="block rounded-lg overflow-hidden bg-black/30 border border-white/10">
                              {isImg ? (
                                <img src={url} alt={a.name} className="w-full max-h-48 object-cover" />
                              ) : isVid ? (
                                <video src={url} className="w-full max-h-48 object-cover" controls preload="metadata" />
                              ) : (
                                <div className="p-3 flex items-center gap-2">
                                  <FileText className="w-5 h-5 flex-shrink-0" />
                                  <div className="min-w-0 flex-1">
                                    <p className="truncate text-xs">{a.name}</p>
                                    <p className="text-[10px] opacity-60">{fmtBytes(a.size)}</p>
                                  </div>
                                </div>
                              )}
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
      </div>

      {/* Reply composer */}
      {!locked && (
        <form onSubmit={sendReply} className="border-t border-zinc-800 bg-zinc-950/95 backdrop-blur-md sticky bottom-0">
          <div className="max-w-3xl mx-auto px-4 py-3 flex items-end gap-2">
            <input
              ref={fileRef}
              type="file"
              multiple
              accept="image/*,video/*,application/pdf"
              onChange={handleUpload}
              className="hidden"
              data-testid="ticket-file-input"
            />
            <button
              type="button"
              onClick={() => fileRef.current?.click()}
              disabled={uploading}
              data-testid="ticket-attach-btn"
              title="إرفاق صور / فيديو / PDF"
              className="p-2.5 rounded-full bg-zinc-800 hover:bg-zinc-700 disabled:opacity-50"
            >
              {uploading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Paperclip className="w-4 h-4" />}
            </button>
            <textarea
              value={reply}
              onChange={(e) => setReply(e.target.value)}
              placeholder="اكتب ردك…"
              rows={1}
              className="flex-1 px-3 py-2 rounded-2xl bg-zinc-800 border border-zinc-700 focus:border-amber-500/60 outline-none text-sm resize-none max-h-32"
              data-testid="ticket-reply-input"
              maxLength={4000}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  sendReply();
                }
              }}
            />
            <button
              type="submit"
              disabled={sending || !reply.trim()}
              data-testid="ticket-send-btn"
              className="p-2.5 rounded-full bg-gradient-to-r from-amber-400 to-yellow-500 text-black hover:opacity-90 disabled:opacity-40"
            >
              {sending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
            </button>
          </div>
        </form>
      )}
    </div>
  );
}
