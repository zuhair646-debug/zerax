import React, { useEffect, useState, useCallback, useRef } from 'react';
import { Sparkles, Wand2, RotateCw, AlertCircle, CheckCircle2, Loader2 } from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;
const MIN_IMAGES_NEEDED = 5;

/**
 * 🎨 LoRA Style-Training Panel
 * Shows in the "Approved Assets" tab. Lets the user kick off a Flux
 * LoRA training run on the project's approved images so every future
 * generation locks into the same visual style.
 *
 * Props:
 *  - projectId : string
 *  - approvedImagesCount : number (passed from parent for instant UI)
 *  - accentColor : "amber" | "indigo" | etc.
 */
export default function StyleTrainingPanel({ projectId, approvedImagesCount = 0, accentColor = 'amber' }) {
  const token = (typeof localStorage !== 'undefined' && localStorage.getItem('token')) || '';
  const [status, setStatus] = useState({ status: 'idle' });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const pollRef = useRef(null);

  const fetchStatus = useCallback(async () => {
    if (!projectId) return;
    try {
      const r = await fetch(`${API}/api/games/project/${projectId}/train-style`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!r.ok) return;
      const d = await r.json();
      setStatus(d);
    } catch (e) { /* network blip — ignore */ }
  }, [projectId, token]);

  useEffect(() => { fetchStatus(); }, [fetchStatus]);

  // Poll every 8s while training is in flight
  useEffect(() => {
    const s = status?.status;
    if (s === 'queued' || s === 'training') {
      pollRef.current = setInterval(fetchStatus, 8000);
      return () => clearInterval(pollRef.current);
    }
    if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null; }
  }, [status?.status, fetchStatus]);

  const startTraining = async () => {
    if (busy) return;
    setError('');
    setBusy(true);
    try {
      const r = await fetch(`${API}/api/games/project/${projectId}/train-style`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
      });
      const d = await r.json().catch(() => ({}));
      if (!r.ok) throw new Error(d.detail || 'فشل بدء التدريب');
      await fetchStatus();
    } catch (e) {
      setError(e.message || 'فشل التدريب');
    } finally {
      setBusy(false);
    }
  };

  const resetLora = async () => {
    if (busy) return;
    if (typeof window !== 'undefined' && !window.confirm('متأكد تبي تحذف النموذج المدرّب؟ التوليدات الجديدة ترجع للنمط الافتراضي.')) return;
    setBusy(true);
    try {
      await fetch(`${API}/api/games/project/${projectId}/train-style`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` },
      });
      await fetchStatus();
    } finally {
      setBusy(false);
    }
  };

  const s = status?.status || 'idle';
  const colors = {
    amber:  { bg: 'from-amber-500/10 to-orange-500/10', border: 'border-amber-500/40', text: 'text-amber-300', btn: 'bg-amber-500 hover:bg-amber-400 text-black' },
    indigo: { bg: 'from-indigo-500/10 to-violet-500/10', border: 'border-indigo-500/40', text: 'text-indigo-300', btn: 'bg-indigo-500 hover:bg-indigo-400 text-black' },
  };
  const c = colors[accentColor] || colors.amber;

  const totalApproved = status?.approved_images_available ?? approvedImagesCount;
  const canTrain = totalApproved >= MIN_IMAGES_NEEDED && s !== 'queued' && s !== 'training';

  return (
    <div
      data-testid="style-training-panel"
      className={`rounded-xl border ${c.border} bg-gradient-to-br ${c.bg} p-4 backdrop-blur-sm`}
    >
      <div className="flex items-start gap-3">
        <div className={`shrink-0 w-10 h-10 rounded-lg border ${c.border} bg-black/40 flex items-center justify-center`}>
          <Sparkles className={`w-5 h-5 ${c.text}`} />
        </div>
        <div className="flex-1 min-w-0">
          <h3 className={`font-bold ${c.text} text-sm flex items-center gap-2`}>
            تدريب نمط اللعبة (Flux LoRA)
            {s === 'ready' && <span className="text-[10px] bg-emerald-500/30 text-emerald-200 px-2 py-0.5 rounded-full">جاهز ✓</span>}
          </h3>
          <p className="text-[11px] text-zinc-300 mt-1 leading-relaxed">
            درّب نموذج خاص بمشروعك على الصور المعتمدة. كل صورة جديدة بعد كذا تجي بنفس النمط البصري الدقيق — شخصيات، إضاءة، ألوان، كلها متطابقة 100%.
          </p>

          {/* status row */}
          <div className="mt-3 text-[11px] flex items-center gap-3 text-zinc-300">
            {s === 'idle' && (
              <span className="flex items-center gap-1.5"><AlertCircle className="w-3.5 h-3.5 text-zinc-400" /> ما في تدريب بعد</span>
            )}
            {s === 'queued' && (
              <span className="flex items-center gap-1.5 text-amber-300"><Loader2 className="w-3.5 h-3.5 animate-spin" /> في الطابور…</span>
            )}
            {s === 'training' && (
              <span className="flex items-center gap-1.5 text-amber-300"><Loader2 className="w-3.5 h-3.5 animate-spin" /> يدرّب الحين (5-10 دقايق)…</span>
            )}
            {s === 'ready' && (
              <span className="flex items-center gap-1.5 text-emerald-300"><CheckCircle2 className="w-3.5 h-3.5" /> جاهز — كل صورة جديدة تستخدم النمط المدرّب تلقائياً</span>
            )}
            {s === 'error' && (
              <span className="flex items-center gap-1.5 text-rose-300"><AlertCircle className="w-3.5 h-3.5" /> فشل: {status?.error || 'سبب غير معروف'}</span>
            )}
            <span className="text-zinc-500">·</span>
            <span>{totalApproved} صورة معتمدة</span>
            {status?.trigger_word && (
              <>
                <span className="text-zinc-500">·</span>
                <code className="text-[10px] bg-black/40 px-1.5 py-0.5 rounded text-amber-200">{status.trigger_word}</code>
              </>
            )}
          </div>

          {error && (
            <div className="mt-2 text-[11px] text-rose-300 bg-rose-500/10 border border-rose-500/30 rounded px-2 py-1.5">
              {error}
            </div>
          )}

          {/* actions */}
          <div className="mt-3 flex flex-wrap gap-2">
            {s !== 'ready' && (
              <button
                onClick={startTraining}
                disabled={!canTrain || busy}
                data-testid="train-style-btn"
                className={`text-xs font-bold px-3 py-1.5 rounded-md transition-colors flex items-center gap-1.5 disabled:opacity-40 disabled:cursor-not-allowed ${c.btn}`}
              >
                <Wand2 className="w-3.5 h-3.5" />
                {(s === 'queued' || s === 'training') ? 'جاري التدريب…' : 'ابدأ التدريب'}
              </button>
            )}
            {s === 'ready' && (
              <>
                <button
                  onClick={startTraining}
                  disabled={busy}
                  data-testid="retrain-style-btn"
                  className={`text-xs font-bold px-3 py-1.5 rounded-md transition-colors flex items-center gap-1.5 ${c.btn} disabled:opacity-40`}
                >
                  <RotateCw className="w-3.5 h-3.5" /> إعادة تدريب
                </button>
                <button
                  onClick={resetLora}
                  disabled={busy}
                  data-testid="reset-style-btn"
                  className="text-xs font-bold px-3 py-1.5 rounded-md border border-rose-500/40 text-rose-300 hover:bg-rose-500/20 transition-colors disabled:opacity-40"
                >
                  حذف النموذج
                </button>
              </>
            )}
            {!canTrain && s === 'idle' && totalApproved < MIN_IMAGES_NEEDED && (
              <span className="text-[11px] text-zinc-400 self-center">
                تحتاج {MIN_IMAGES_NEEDED - totalApproved} صور إضافية معتمدة عشان تقدر تدرّب.
              </span>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
