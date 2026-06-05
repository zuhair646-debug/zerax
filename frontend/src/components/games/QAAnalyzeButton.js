import { useState } from 'react';
import { Microscope, Loader2 } from 'lucide-react';
import { toast } from 'sonner';

const API = process.env.REACT_APP_BACKEND_URL;

/**
 * 🔬 QA Analyze button — Claude reviews the live HTML and produces a report.
 * Used in the Live tab of game studios.
 */
export default function QAAnalyzeButton({ projectId, accentColor = 'amber' }) {
  const token = localStorage.getItem('token');
  const [loading, setLoading] = useState(false);
  const [report, setReport] = useState(null);
  const [open, setOpen] = useState(false);

  const accent = {
    amber: 'bg-amber-500/15 hover:bg-amber-500/25 border-amber-400/40 text-amber-200',
    blue: 'bg-blue-500/15 hover:bg-blue-500/25 border-blue-400/40 text-blue-200',
  }[accentColor] || 'bg-amber-500/15 hover:bg-amber-500/25 border-amber-400/40 text-amber-200';

  const run = async () => {
    if (!projectId) return;
    setLoading(true);
    setReport(null);
    try {
      const r = await fetch(`${API}/api/games/project/${projectId}/qa-analyze`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!r.ok) {
        const e = await r.json().catch(() => ({}));
        throw new Error(e.detail || 'qa failed');
      }
      toast.info('🔬 جاري التحليل... (60-120 ثانية)', { duration: 4000 });
      // Poll every 5s
      const poll = async () => {
        for (let i = 0; i < 36; i++) {
          await new Promise(res => setTimeout(res, 5000));
          try {
            const sr = await fetch(`${API}/api/games/project/${projectId}/qa-status`, {
              headers: { Authorization: `Bearer ${token}` },
            });
            if (sr.ok) {
              const sd = await sr.json();
              if (sd.status === 'ready') {
                setReport(sd.report);
                setOpen(true);
                toast.success('🔬 تقرير QA جاهز');
                return;
              }
              if (sd.status === 'error') {
                toast.error(`فشل التحليل: ${sd.error || 'سبب غير معروف'}`);
                return;
              }
            }
          } catch (_) { /* retry */ }
        }
        toast.error('انتهى وقت الانتظار — حاول مرة ثانية');
      };
      await poll();
    } catch (e) {
      toast.error(`فشل التحليل: ${e.message}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <button type="button" onClick={run} disabled={loading}
        data-testid="qa-analyze-btn"
        className={`px-3 py-2 rounded-lg border text-xs font-bold inline-flex items-center gap-1.5 ${accent} disabled:opacity-60`}
        title="Claude يفحص الموقع المبني ويعطيك تقرير QA كامل"
      >
        {loading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Microscope className="w-3.5 h-3.5" />}
        <span>{loading ? 'جاري التحليل...' : 'تحليل QA'}</span>
      </button>

      {open && report && (
        <div className="fixed inset-0 z-[60] bg-black/80 flex items-center justify-center p-4" onClick={() => setOpen(false)}>
          <div dir="rtl" className="bg-zinc-950 border border-white/10 rounded-2xl p-6 max-w-3xl w-full max-h-[85vh] flex flex-col" onClick={(e) => e.stopPropagation()} data-testid="qa-report-dialog">
            <div className="flex items-center justify-between mb-3">
              <h3 className="font-bold text-white flex items-center gap-2">
                <Microscope className="w-5 h-5 text-emerald-300" />
                <span>تقرير QA — تحليل Claude للموقع المبني</span>
              </h3>
              <button type="button" onClick={() => setOpen(false)} className="text-zinc-400 hover:text-white">✕</button>
            </div>
            <div className="flex-1 overflow-y-auto bg-black/40 rounded-xl border border-white/10 p-5">
              <pre className="whitespace-pre-wrap text-sm text-zinc-100 leading-relaxed font-sans">{report}</pre>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
