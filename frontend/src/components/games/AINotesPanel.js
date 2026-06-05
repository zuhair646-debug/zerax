import { useEffect, useState, useCallback } from 'react';
import { Brain, Loader2, RefreshCw, FileText } from 'lucide-react';
import { toast } from 'sonner';
import StyleProfileSelector from './StyleProfileSelector';

const API = process.env.REACT_APP_BACKEND_URL;

/**
 * 🧠 AI Memory / GDD panel — shows the AI's living summary of the project so the
 * user can see at any time exactly what the AI remembers, and refresh it on demand.
 * Used as the 4th tab in WebGamesStudio / AppGamesStudio.
 */
export default function AINotesPanel({ projectId, accentColor = 'amber', refreshSignal = 0, styleProfile = 'stylized' }) {
  const token = localStorage.getItem('token');
  const [notes, setNotes] = useState('');
  const [updatedAt, setUpdatedAt] = useState(null);
  const [loading, setLoading] = useState(false);
  const [refreshing, setRefreshing] = useState(false);

  const colorClass = {
    amber: { accent: 'text-amber-300', bg: 'bg-amber-500/10', border: 'border-amber-500/30', btn: 'bg-amber-500/20 hover:bg-amber-500/30 border-amber-400/40 text-amber-100' },
    blue: { accent: 'text-blue-300', bg: 'bg-blue-500/10', border: 'border-blue-500/30', btn: 'bg-blue-500/20 hover:bg-blue-500/30 border-blue-400/40 text-blue-100' },
  }[accentColor] || { accent: 'text-violet-300', bg: 'bg-violet-500/10', border: 'border-violet-500/30', btn: 'bg-violet-500/20 hover:bg-violet-500/30 border-violet-400/40 text-violet-100' };

  const fetchNotes = useCallback(async () => {
    if (!projectId) return;
    setLoading(true);
    try {
      const r = await fetch(`${API}/api/games/project/${projectId}/notes`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (r.ok) {
        const d = await r.json();
        setNotes(d.notes || '');
        setUpdatedAt(d.updated_at || null);
      }
    } finally {
      setLoading(false);
    }
  }, [projectId, token]);

  const refreshNotes = useCallback(async () => {
    if (!projectId) return;
    setRefreshing(true);
    try {
      const r = await fetch(`${API}/api/games/project/${projectId}/notes/refresh`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!r.ok) throw new Error('failed');
      const d = await r.json();
      if (d.notes) {
        setNotes(d.notes);
        setUpdatedAt(new Date().toISOString());
        toast.success('🧠 تم تحديث ذاكرة AI');
      } else {
        toast.info('لا توجد محادثات كافية لتلخيصها بعد');
      }
    } catch (e) {
      toast.error('فشل تحديث الذاكرة — حاول مرة ثانية');
    } finally {
      setRefreshing(false);
    }
  }, [projectId, token]);

  // Initial load + when parent signals a refresh
  useEffect(() => {
    fetchNotes();
  }, [fetchNotes, refreshSignal]);

  const updatedLabel = updatedAt ? new Date(updatedAt).toLocaleString('ar-SA') : '—';

  return (
    <div className="flex-1 overflow-y-auto p-6 bg-black/40" data-testid="tab-content-notes">
      <div className="max-w-3xl mx-auto space-y-4">
        {/* Header */}
        <div className="flex items-center justify-between gap-3 flex-wrap">
          <div>
            <h2 className={`text-lg font-bold flex items-center gap-2 ${colorClass.accent}`}>
              <Brain className="w-5 h-5" />
              <span>ذاكرة AI · ملخص المشروع المستديم</span>
            </h2>
            <p className="text-xs text-zinc-400 mt-1">
              هذا اللي يتذكره الذكاء عن مشروعك. يتحدث تلقائياً كل عدة رسائل، ويقدر يستفيد منه في كل محادثة.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-[10px] text-zinc-500">آخر تحديث: {updatedLabel}</span>
            <button
              type="button"
              onClick={refreshNotes}
              disabled={refreshing}
              data-testid="refresh-ai-notes-btn"
              className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border text-xs font-bold transition-all ${colorClass.btn} disabled:opacity-50`}
            >
              {refreshing ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <RefreshCw className="w-3.5 h-3.5" />}
              <span>تحديث الآن</span>
            </button>
          </div>
        </div>

        {/* Content */}
        {loading ? (
          <div className="flex items-center justify-center py-16 text-zinc-400">
            <Loader2 className="w-6 h-6 animate-spin me-2" />
            <span>جاري تحميل الذاكرة...</span>
          </div>
        ) : notes ? (
          <div className={`rounded-xl border ${colorClass.border} ${colorClass.bg} p-5`} data-testid="ai-notes-content">
            <div className="prose prose-invert prose-sm max-w-none whitespace-pre-wrap leading-relaxed text-zinc-100">
              {notes}
            </div>
          </div>
        ) : (
          <div className="rounded-xl border border-white/10 bg-black/40 p-8 text-center">
            <FileText className="w-12 h-12 mx-auto mb-3 text-zinc-600" />
            <p className="text-zinc-300 font-bold mb-2">لا توجد ذاكرة محفوظة بعد</p>
            <p className="text-xs text-zinc-500 mb-4">
              ابدأ محادثة مع AI عن مشروعك، وبعد عدة رسائل راح يلخص لك كل ما تم الاتفاق عليه هنا تلقائياً.
            </p>
            <button
              type="button"
              onClick={refreshNotes}
              disabled={refreshing}
              className={`inline-flex items-center gap-2 px-4 py-2 rounded-lg border text-sm font-bold ${colorClass.btn}`}
            >
              {refreshing ? <Loader2 className="w-4 h-4 animate-spin" /> : <RefreshCw className="w-4 h-4" />}
              <span>توليد الذاكرة الآن</span>
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
