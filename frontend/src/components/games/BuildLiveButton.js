import { useState, useEffect, useCallback } from 'react';
import { Loader2, Rocket, ExternalLink, AlertTriangle, CheckCircle2 } from 'lucide-react';
import { toast } from 'sonner';

const API = process.env.REACT_APP_BACKEND_URL;

/**
 * 🚀 Big build & deploy button for game studios.
 * - Kicks off async build job (returns 202 immediately).
 * - Polls /build-info every 4s until status === ready or error.
 * - On success: toast + opens the Live tab in parent via onBuilt callback
 *   and offers a "Open in new tab" link.
 */
export default function BuildLiveButton({ projectId, accentColor = 'amber', onBuilt }) {
  const token = localStorage.getItem('token');
  const [status, setStatus] = useState('idle'); // idle | building | ready | error
  const [error, setError] = useState(null);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [lastBuiltAt, setLastBuiltAt] = useState(null);

  const accent = {
    amber: 'from-amber-500 to-orange-600 hover:from-amber-400 hover:to-orange-500',
    blue: 'from-blue-500 to-cyan-600 hover:from-blue-400 hover:to-cyan-500',
  }[accentColor] || 'from-amber-500 to-orange-600';

  const refreshInfo = useCallback(async () => {
    if (!projectId) return null;
    try {
      const r = await fetch(`${API}/api/games/project/${projectId}/build-info`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!r.ok) return null;
      const d = await r.json();
      setStatus(d.status || (d.preview_url ? 'ready' : 'idle'));
      setPreviewUrl(d.preview_url || null);
      setLastBuiltAt(d.last_built_at || null);
      setError(d.error || null);
      return d;
    } catch (_) {
      return null;
    }
  }, [projectId, token]);

  // Initial fetch
  useEffect(() => { refreshInfo(); }, [refreshInfo]);

  // Poll while building
  useEffect(() => {
    if (status !== 'building') return;
    const iv = setInterval(async () => {
      const info = await refreshInfo();
      if (info && info.status === 'ready') {
        toast.success('✅ الموقع جاهز ومنشور على الـ Live!', { duration: 6000 });
        onBuilt?.(info.preview_url);
        clearInterval(iv);
      } else if (info && info.status === 'error') {
        toast.error(`❌ فشل البناء: ${info.error || 'سبب غير معروف'}`, { duration: 8000 });
        clearInterval(iv);
      }
    }, 4000);
    return () => clearInterval(iv);
  }, [status, refreshInfo, onBuilt]);

  const startBuild = async () => {
    if (!projectId) return;
    try {
      setStatus('building');
      setError(null);
      const r = await fetch(`${API}/api/games/project/${projectId}/build`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!r.ok) throw new Error('failed');
      toast.info('🚀 بدأ البناء... جاري توليد الموقع — راح يجهز خلال 60-180 ثانية', { duration: 5000 });
    } catch (_) {
      setStatus('error');
      toast.error('فشل بدء البناء');
    }
  };

  const fullUrl = previewUrl && API ? `${API}${previewUrl}` : null;

  return (
    <div className="flex items-center gap-2 flex-wrap" data-testid="build-live-zone">
      <button
        type="button"
        onClick={startBuild}
        disabled={status === 'building'}
        data-testid="build-live-btn"
        className={`relative px-4 py-2 rounded-xl bg-gradient-to-l ${accent} text-white text-sm font-bold shadow-lg shadow-black/40 inline-flex items-center gap-2 disabled:opacity-70 disabled:cursor-not-allowed transition-all`}
      >
        {status === 'building' ? (
          <>
            <Loader2 className="w-4 h-4 animate-spin" />
            <span>جاري البناء والنشر...</span>
          </>
        ) : (
          <>
            <Rocket className="w-4 h-4" />
            <span>{status === 'ready' ? 'إعادة البناء والنشر' : 'ابني وانشر اللايف 🚀'}</span>
          </>
        )}
      </button>

      {status === 'ready' && fullUrl && (
        <a
          href={fullUrl}
          target="_blank"
          rel="noreferrer"
          data-testid="open-live-tab"
          className="px-3 py-2 rounded-lg bg-emerald-500/15 border border-emerald-400/30 text-emerald-200 hover:bg-emerald-500/25 text-xs font-bold inline-flex items-center gap-1.5"
          title={fullUrl}
        >
          <ExternalLink className="w-3.5 h-3.5" />
          <span>افتح الموقع</span>
        </a>
      )}

      {status === 'ready' && lastBuiltAt && (
        <span className="text-[10px] text-zinc-500 inline-flex items-center gap-1">
          <CheckCircle2 className="w-3 h-3 text-emerald-400" />
          <span>آخر نشر: {new Date(lastBuiltAt).toLocaleString('ar-SA', { hour: '2-digit', minute: '2-digit', day: '2-digit', month: '2-digit' })}</span>
        </span>
      )}

      {status === 'error' && error && (
        <span className="text-[10px] text-rose-300 inline-flex items-center gap-1">
          <AlertTriangle className="w-3 h-3" />
          <span title={error}>{error.slice(0, 60)}</span>
        </span>
      )}
    </div>
  );
}
