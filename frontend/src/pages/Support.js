/**
 * Support — User-facing ticket list + new ticket form.
 *
 * Lists my tickets, shows unread badge, and lets me open a new ticket
 * (which the backend auto-triages via Claude before reaching admin).
 */
import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, Plus, Inbox, MessageSquare, Loader2, CheckCircle2, Clock, Archive } from 'lucide-react';
import { toast } from 'sonner';

const API = process.env.REACT_APP_BACKEND_URL;

const STATUS_META = {
  open:          { label: 'مفتوحة',          icon: Clock,         color: 'text-amber-300 bg-amber-500/10 border-amber-500/30' },
  replied:       { label: 'رد فريق الدعم',    icon: MessageSquare, color: 'text-emerald-300 bg-emerald-500/10 border-emerald-500/30' },
  awaiting_user: { label: 'بانتظار ردك',      icon: MessageSquare, color: 'text-blue-300 bg-blue-500/10 border-blue-500/30' },
  auto_resolved: { label: 'حلّها المساعد',    icon: CheckCircle2,  color: 'text-purple-300 bg-purple-500/10 border-purple-500/30' },
  resolved:      { label: 'تم الحل',          icon: CheckCircle2,  color: 'text-emerald-300 bg-emerald-500/10 border-emerald-500/30' },
  closed:        { label: 'مغلقة',            icon: Archive,       color: 'text-zinc-400 bg-zinc-700/40 border-zinc-700' },
};

const CATEGORY_LABEL = {
  support: 'استفسار',
  bug: 'مشكلة تقنية',
  billing: 'فواتير',
  feature: 'طلب ميزة',
  suggestion: 'اقتراح',
  refund: 'استرداد',
  payout: 'سحب أرباح',
};

export default function Support() {
  const nav = useNavigate();
  const [loading, setLoading] = useState(true);
  const [tickets, setTickets] = useState([]);
  const [showForm, setShowForm] = useState(false);
  const [subject, setSubject] = useState('');
  const [body, setBody] = useState('');
  const [category, setCategory] = useState('support');
  const [busy, setBusy] = useState(false);

  const load = async () => {
    setLoading(true);
    const token = localStorage.getItem('token');
    try {
      const r = await fetch(`${API}/api/support/tickets/me`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (r.ok) {
        const d = await r.json();
        setTickets(d.items || []);
      }
    } catch (_) { /* silent */ }
    setLoading(false);
  };

  useEffect(() => { load(); }, []);

  const submit = async (e) => {
    e.preventDefault();
    if (subject.trim().length < 2 || body.trim().length < 5) {
      toast.error('اكتب موضوع ووصف مناسب');
      return;
    }
    setBusy(true);
    const token = localStorage.getItem('token');
    try {
      const r = await fetch(`${API}/api/support/tickets`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ subject: subject.trim(), body: body.trim(), category, priority: 'normal' }),
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || 'فشل');
      toast.success('تم إنشاء التذكرة');
      setShowForm(false);
      setSubject(''); setBody(''); setCategory('support');
      // Jump straight to the new ticket so user sees the AI reply
      nav(`/support/tickets/${d.id}`);
    } catch (e) {
      toast.error(e.message || 'فشل إنشاء التذكرة');
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-zinc-950 to-black text-white" dir="rtl">
      <div className="max-w-4xl mx-auto px-4 sm:px-6 py-8">
        <div className="flex items-center gap-3 mb-6">
          <button
            onClick={() => nav('/dashboard')}
            data-testid="support-back-btn"
            className="p-2 rounded-full bg-white/5 hover:bg-white/10 transition"
            aria-label="رجوع"
          >
            <ArrowLeft className="w-5 h-5" />
          </button>
          <div className="flex-1">
            <h1 className="text-2xl sm:text-3xl font-black bg-gradient-to-r from-amber-200 to-yellow-400 bg-clip-text text-transparent">
              مركز الدعم
            </h1>
            <p className="text-zinc-400 text-sm mt-0.5">
              المساعد الذكي يرد فوراً، وإذا احتاج الأمر إدارة بشرية يحوّل تذكرتك لفريقنا.
            </p>
          </div>
          <button
            onClick={() => setShowForm(true)}
            data-testid="support-new-ticket-btn"
            className="px-4 py-2 rounded-lg bg-gradient-to-r from-amber-400 to-yellow-500 text-black text-sm font-black hover:opacity-90 flex items-center gap-1.5"
          >
            <Plus className="w-4 h-4" /> تذكرة جديدة
          </button>
        </div>

        {showForm && (
          <form
            onSubmit={submit}
            className="rounded-2xl border border-amber-500/30 bg-zinc-900/70 p-5 mb-6 space-y-3"
            data-testid="support-ticket-form"
          >
            <div>
              <label className="text-xs text-zinc-400 block mb-1.5">الموضوع</label>
              <input
                type="text"
                value={subject}
                onChange={(e) => setSubject(e.target.value)}
                placeholder="مثال: شحنت 10$ ولم تصل النقاط"
                className="w-full px-3 py-2 rounded-lg bg-zinc-800 border border-zinc-700 focus:border-amber-500/60 outline-none text-sm"
                data-testid="support-subject-input"
                maxLength={200}
                required
              />
            </div>
            <div>
              <label className="text-xs text-zinc-400 block mb-1.5">نوع الطلب</label>
              <select
                value={category}
                onChange={(e) => setCategory(e.target.value)}
                className="w-full px-3 py-2 rounded-lg bg-zinc-800 border border-zinc-700 focus:border-amber-500/60 outline-none text-sm"
                data-testid="support-category-select"
              >
                <option value="support">استفسار عام</option>
                <option value="bug">مشكلة تقنية / خطأ</option>
                <option value="billing">شحن / دفع</option>
                <option value="feature">طلب ميزة جديدة</option>
                <option value="suggestion">اقتراح</option>
              </select>
            </div>
            <div>
              <label className="text-xs text-zinc-400 block mb-1.5">الوصف التفصيلي</label>
              <textarea
                value={body}
                onChange={(e) => setBody(e.target.value)}
                placeholder="اشرح المشكلة بالتفصيل. تستطيع رفع صور وفيديو بعد إنشاء التذكرة."
                className="w-full px-3 py-2 rounded-lg bg-zinc-800 border border-zinc-700 focus:border-amber-500/60 outline-none text-sm min-h-[140px] resize-y"
                data-testid="support-body-textarea"
                maxLength={4000}
                required
              />
              <p className="text-[10px] text-zinc-500 mt-1">{body.length}/4000 حرف</p>
            </div>
            <div className="flex gap-2 justify-end">
              <button
                type="button"
                onClick={() => setShowForm(false)}
                className="px-4 py-2 rounded-lg bg-zinc-800 hover:bg-zinc-700 text-xs font-bold"
              >
                إلغاء
              </button>
              <button
                type="submit"
                disabled={busy}
                data-testid="support-submit-btn"
                className="px-4 py-2 rounded-lg bg-gradient-to-r from-amber-400 to-yellow-500 text-black text-xs font-black hover:opacity-90 disabled:opacity-50 flex items-center gap-1.5"
              >
                {busy && <Loader2 className="w-3.5 h-3.5 animate-spin" />} إرسال التذكرة
              </button>
            </div>
          </form>
        )}

        {loading ? (
          <div className="flex items-center justify-center py-20">
            <Loader2 className="w-8 h-8 animate-spin text-amber-400" />
          </div>
        ) : tickets.length === 0 ? (
          <div className="rounded-2xl border border-zinc-800 bg-zinc-900/40 p-10 text-center">
            <Inbox className="w-12 h-12 text-zinc-600 mx-auto mb-3" />
            <h2 className="text-lg font-black mb-1">لا توجد تذاكر</h2>
            <p className="text-zinc-400 text-sm mb-4">ابدأ بإنشاء تذكرة جديدة لطرح أي مشكلة أو اقتراح.</p>
            <button
              onClick={() => setShowForm(true)}
              className="px-4 py-2 rounded-lg bg-gradient-to-r from-amber-400 to-yellow-500 text-black text-xs font-black hover:opacity-90"
            >
              إنشاء أول تذكرة
            </button>
          </div>
        ) : (
          <div className="space-y-2">
            {tickets.map((t) => {
              const meta = STATUS_META[t.status] || STATUS_META.open;
              const Icon = meta.icon;
              return (
                <button
                  key={t.id}
                  onClick={() => nav(`/support/tickets/${t.id}`)}
                  data-testid={`support-ticket-${t.id}`}
                  className="w-full text-right rounded-xl border border-zinc-800 bg-zinc-900/60 hover:bg-zinc-900 hover:border-zinc-700 transition p-4 flex items-start gap-3"
                >
                  <span className={`mt-0.5 px-2 py-1 rounded-md text-[10px] font-black border ${meta.color} flex items-center gap-1`}>
                    <Icon className="w-3 h-3" /> {meta.label}
                  </span>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-0.5">
                      <h3 className="font-black text-sm truncate">{t.subject}</h3>
                      {t.unread_for_user && (
                        <span className="w-2 h-2 rounded-full bg-amber-400 animate-pulse flex-shrink-0" title="رد جديد" />
                      )}
                    </div>
                    <p className="text-[11px] text-zinc-400">
                      {CATEGORY_LABEL[t.category] || t.category} ·{' '}
                      {t.last_message_at && new Date(t.last_message_at).toLocaleString('ar-SA', { dateStyle: 'short', timeStyle: 'short' })}
                    </p>
                  </div>
                </button>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
