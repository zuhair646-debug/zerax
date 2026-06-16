/**
 * AdminNotifications — silent inbox for AI integration failures.
 *
 * When the AI agent hits a broken integration (fal.ai key rejected, OpenAI
 * 429, ElevenLabs out of credit), it calls the backend `notify_owner` tool
 * which inserts a record here. This page lets the platform owner see what's
 * going wrong WITHOUT users ever seeing the technical details.
 */
import { useState, useEffect, useCallback } from 'react';
import { Bell, AlertCircle, AlertTriangle, Check, Loader2, RefreshCw } from 'lucide-react';
import { toast } from 'sonner';

const API = process.env.REACT_APP_BACKEND_URL;

const SEVERITY = {
  critical: { color: 'bg-red-500/15 border-red-500/40 text-red-200', icon: AlertCircle, label: 'حرج' },
  high:     { color: 'bg-orange-500/15 border-orange-500/40 text-orange-200', icon: AlertTriangle, label: 'عالي' },
  medium:   { color: 'bg-amber-500/15 border-amber-500/40 text-amber-200', icon: AlertTriangle, label: 'متوسط' },
  low:      { color: 'bg-zinc-500/15 border-zinc-500/40 text-zinc-300', icon: Bell, label: 'منخفض' },
};

const CATEGORY_LABEL = {
  integration_failure: 'فشل تكامل',
  quota_exceeded: 'الرصيد منتهي',
  key_invalid: 'مفتاح غير صالح',
  api_timeout: 'انتهت المهلة',
  user_complaint: 'شكوى عميل',
  other: 'متفرقات',
};

export default function AdminNotifications() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [unreadOnly, setUnreadOnly] = useState(false);
  const [unreadCount, setUnreadCount] = useState(0);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem('token');
      const url = new URL(`${API}/api/owner/notifications`);
      if (unreadOnly) url.searchParams.set('unread_only', 'true');
      const r = await fetch(url, { headers: { Authorization: `Bearer ${token}` } });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const d = await r.json();
      setItems(d.items || []);
      setUnreadCount(d.unread_count || 0);
    } catch (e) {
      toast.error(`ما قدرت أحمّل الإشعارات: ${e.message}`);
    } finally {
      setLoading(false);
    }
  }, [unreadOnly]);

  useEffect(() => { load(); }, [load]);

  // Auto-poll every 20s so new alerts appear without manual refresh.
  useEffect(() => {
    const t = setInterval(load, 20000);
    return () => clearInterval(t);
  }, [load]);

  const markRead = async (id) => {
    try {
      const token = localStorage.getItem('token');
      await fetch(`${API}/api/owner/notifications/${id}/read`, {
        method: 'POST', headers: { Authorization: `Bearer ${token}` },
      });
      setItems((prev) => prev.map((it) => it.id === id ? { ...it, read: true } : it));
      setUnreadCount((n) => Math.max(0, n - 1));
    } catch (e) {
      toast.error(e.message);
    }
  };

  const markAllRead = async () => {
    try {
      const token = localStorage.getItem('token');
      await fetch(`${API}/api/owner/notifications/mark-all-read`, {
        method: 'POST', headers: { Authorization: `Bearer ${token}` },
      });
      setItems((prev) => prev.map((it) => ({ ...it, read: true })));
      setUnreadCount(0);
      toast.success('تمّ تعليم الكل كمقروء');
    } catch (e) {
      toast.error(e.message);
    }
  };

  return (
    <div className="min-h-screen bg-black text-white p-6" dir="rtl" data-testid="admin-notifications">
      <div className="max-w-4xl mx-auto">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <Bell className="w-6 h-6 text-amber-400" />
            <h1 className="text-2xl font-black">إشعارات النظام</h1>
            {unreadCount > 0 && (
              <span className="px-2 py-0.5 rounded-full bg-red-500 text-white text-xs font-bold">
                {unreadCount} غير مقروء
              </span>
            )}
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setUnreadOnly((v) => !v)}
              data-testid="toggle-unread-filter"
              className={`px-3 py-1.5 rounded-lg text-xs font-bold border transition ${
                unreadOnly ? 'bg-amber-500/20 border-amber-500/50 text-amber-200' : 'border-white/10 hover:border-white/30'
              }`}
            >
              {unreadOnly ? 'يعرض غير المقروء فقط' : 'يعرض الكل'}
            </button>
            <button
              onClick={load}
              data-testid="refresh-notifications"
              className="p-1.5 rounded-lg border border-white/10 hover:border-white/30"
              title="تحديث"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            </button>
            {unreadCount > 0 && (
              <button
                onClick={markAllRead}
                data-testid="mark-all-read"
                className="px-3 py-1.5 rounded-lg bg-emerald-500/20 hover:bg-emerald-500/30 border border-emerald-500/40 text-emerald-200 text-xs font-bold transition"
              >
                <Check className="w-3.5 h-3.5 inline ml-1" /> تعليم الكل
              </button>
            )}
          </div>
        </div>

        {loading && items.length === 0 ? (
          <div className="flex items-center justify-center py-12 text-zinc-500">
            <Loader2 className="w-6 h-6 animate-spin" />
          </div>
        ) : items.length === 0 ? (
          <div className="text-center py-12 text-zinc-500">
            <Bell className="w-12 h-12 mx-auto mb-3 opacity-30" />
            <p className="text-sm">ما عندك أي إشعارات.</p>
            <p className="text-xs mt-1 text-zinc-600">لما تفشل أي خدمة تكامل (fal.ai، OpenAI، ...) راح يظهر هنا تلقائياً.</p>
          </div>
        ) : (
          <div className="space-y-2">
            {items.map((it) => {
              const sev = SEVERITY[it.severity] || SEVERITY.medium;
              const Icon = sev.icon;
              return (
                <div
                  key={it.id}
                  data-testid={`notif-${it.id}`}
                  className={`relative rounded-xl border p-3 ${sev.color} ${it.read ? 'opacity-60' : ''}`}
                >
                  <div className="flex items-start gap-3">
                    <Icon className="w-5 h-5 flex-shrink-0 mt-0.5" />
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="text-[10px] font-bold uppercase tracking-wide opacity-80">{sev.label}</span>
                        <span className="text-[10px] bg-black/30 px-1.5 py-0.5 rounded">
                          {CATEGORY_LABEL[it.category] || it.category}
                        </span>
                        {it.created_at && (
                          <span className="text-[10px] opacity-60">
                            {new Date(it.created_at * 1000).toLocaleString('ar-SA')}
                          </span>
                        )}
                      </div>
                      <p className="text-sm font-bold mt-1 leading-snug">{it.summary}</p>
                      {it.details && (
                        <pre className="mt-1.5 text-[11px] bg-black/30 rounded p-2 overflow-x-auto whitespace-pre-wrap leading-relaxed font-mono">
                          {it.details}
                        </pre>
                      )}
                      {it.project_id && (
                        <a
                          href={`/freebuild/chat/${it.project_id}`}
                          className="inline-block mt-1.5 text-[11px] underline hover:no-underline"
                        >افتح المشروع ←</a>
                      )}
                    </div>
                    {!it.read && (
                      <button
                        onClick={() => markRead(it.id)}
                        data-testid={`mark-read-${it.id}`}
                        className="px-2 py-1 rounded text-[10px] font-bold bg-emerald-500/20 hover:bg-emerald-500/30 border border-emerald-500/40 text-emerald-200"
                      >
                        تعليم كمقروء
                      </button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
