import React, { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { toast } from 'sonner';
import { Loader2, CheckCircle2, XCircle, ArrowLeft, Film, AlertCircle, Sparkles } from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;
const auth = () => ({ Authorization: `Bearer ${localStorage.getItem('token') || ''}` });

export default function VideoRender() {
  const { episodeId } = useParams();
  const navigate = useNavigate();
  const [ep, setEp] = useState(null);
  const [error, setError] = useState('');
  const pollRef = useRef(null);

  useEffect(() => {
    let alive = true;
    const tick = async () => {
      try {
        const r = await fetch(`${API}/api/video-studio/render-status/${episodeId}`, { headers: auth() });
        if (!r.ok) throw new Error('فشل تحميل الحالة');
        const data = await r.json();
        if (!alive) return;
        setEp(data.episode);
        const stage = data.episode?.stage;
        if (stage === 'rendered' || stage === 'approved') {
          clearInterval(pollRef.current);
          if (stage === 'rendered') toast.success('اكتمل الإنتاج ✓');
        }
      } catch (e) {
        if (alive) setError(e.message);
      }
    };
    tick();
    pollRef.current = setInterval(tick, 3000);
    return () => { alive = false; clearInterval(pollRef.current); };
  }, [episodeId]);

  if (error) {
    return (
      <div className="min-h-screen bg-[#0b0d12] text-zinc-100 flex items-center justify-center p-6" dir="rtl">
        <div className="bg-rose-500/10 border border-rose-500/40 rounded-2xl p-6 max-w-md">
          <AlertCircle className="w-8 h-8 text-rose-400 mb-3" />
          <h2 className="text-lg font-semibold mb-2">خطأ</h2>
          <p className="text-sm text-zinc-300 leading-7">{error}</p>
          <button onClick={() => navigate('/chat/video')} className="mt-4 bg-zinc-800 hover:bg-zinc-700 px-4 py-2 rounded-lg text-sm">
            رجوع للاستوديو
          </button>
        </div>
      </div>
    );
  }

  if (!ep) {
    return (
      <div className="min-h-screen bg-[#0b0d12] text-zinc-100 flex items-center justify-center" dir="rtl">
        <Loader2 className="w-8 h-8 animate-spin text-amber-400" />
      </div>
    );
  }

  const status = ep.render_status || { running: ep.stage === 'rendering', completed: 0, total: (ep.shots || []).length };
  const total = status.total || (ep.shots || []).length || 1;
  const completed = status.completed || 0;
  const pct = Math.round((completed / total) * 100);
  const isDone = ep.stage === 'rendered';
  const isFailed = ep.stage === 'approved' && (status.phase === 'failed_refunded');
  const isRunning = ep.stage === 'rendering' || status.running;
  const errors = status.errors || [];

  return (
    <div className="min-h-screen bg-[#0b0d12] text-zinc-100 p-6" dir="rtl" data-testid="video-render-page">
      <div className="max-w-4xl mx-auto">
        <button onClick={() => navigate('/chat/video')}
          className="text-xs text-zinc-400 hover:text-zinc-200 mb-4 flex items-center gap-1.5">
          <ArrowLeft className="w-3.5 h-3.5" /> رجوع للاستوديو
        </button>

        <div className="bg-[#12161e] border border-zinc-800 rounded-2xl p-6 mb-5">
          <div className="flex items-center gap-3 mb-4">
            <Film className="w-6 h-6 text-amber-400" />
            <div>
              <h1 className="text-xl font-semibold">حلقة {ep.episode_number} · {ep.script?.title || 'بدون عنوان'}</h1>
              <p className="text-xs text-zinc-500 mt-0.5">{ep.script?.logline}</p>
            </div>
          </div>

          {/* Progress */}
          <div className="space-y-3">
            <div className="flex items-center justify-between text-sm">
              <span className="text-zinc-300">
                {isDone ? '✓ اكتمل الإنتاج' : isFailed ? '✗ فشل الإنتاج · تم استرداد النقاط' : isRunning ? `جاري الإنتاج · لقطة ${completed + 1} من ${total}` : 'جاهز'}
              </span>
              <span className="text-amber-300 font-mono">{pct}%</span>
            </div>
            <div className="h-2 bg-zinc-800 rounded-full overflow-hidden">
              <div
                className={`h-full transition-all duration-500 ${isFailed ? 'bg-rose-500' : isDone ? 'bg-emerald-500' : 'bg-gradient-to-r from-amber-500 to-orange-500'}`}
                style={{ width: `${pct}%` }}
              />
            </div>
            {isRunning && (
              <div className="text-xs text-zinc-400 flex items-center gap-2">
                <Loader2 className="w-3.5 h-3.5 animate-spin text-amber-400" />
                {status.phase ? `المرحلة: ${status.phase}` : 'بدأت العملية في الخلفية…'}
              </div>
            )}
          </div>
        </div>

        {/* Shot grid with per-shot status */}
        <div className="grid grid-cols-2 md:grid-cols-3 gap-3 mb-5">
          {(ep.shots || []).map((shot) => {
            const clipFromFinal = (ep.final_clips || []).find((c) => c.n === shot.n);
            const shotErr = errors.find((e) => e.n === shot.n);
            const done = !!clipFromFinal?.ok;
            const failed = !!shotErr || (clipFromFinal && clipFromFinal.ok === false);
            const currentlyRendering = isRunning && status.current_shot === shot.n;
            return (
              <div key={shot.n} className="bg-[#12161e] border border-zinc-800 rounded-xl overflow-hidden" data-testid={`render-shot-${shot.n}`}>
                <div className="aspect-video bg-zinc-900 flex items-center justify-center relative">
                  {clipFromFinal?.video_url ? (
                    <video src={clipFromFinal.video_url} controls className="w-full h-full object-cover" />
                  ) : currentlyRendering ? (
                    <div className="flex flex-col items-center gap-2 text-amber-300">
                      <Loader2 className="w-8 h-8 animate-spin" />
                      <span className="text-xs">يُنتَج الآن…</span>
                    </div>
                  ) : failed ? (
                    <XCircle className="w-10 h-10 text-rose-400" />
                  ) : done ? (
                    <CheckCircle2 className="w-10 h-10 text-emerald-400" />
                  ) : (
                    <Sparkles className="w-8 h-8 text-zinc-700" />
                  )}
                  <div className="absolute top-1 right-1 bg-black/80 text-zinc-300 text-[10px] px-1.5 py-0.5 rounded">
                    #{shot.n} · {shot.duration}s
                  </div>
                </div>
                <div className="p-2">
                  <div className="text-xs font-medium text-zinc-200 mb-1 truncate">{shot.title_ar}</div>
                  {failed && shotErr && (
                    <div className="text-[10px] text-rose-400 line-clamp-2" data-testid={`shot-error-${shot.n}`}>
                      ✗ {shotErr.error}
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>

        {/* Errors panel */}
        {errors.length > 0 && (
          <div className="bg-rose-500/10 border border-rose-500/30 rounded-xl p-4 mb-5" data-testid="render-errors-panel">
            <div className="text-rose-300 font-semibold text-sm mb-2 flex items-center gap-1.5">
              <AlertCircle className="w-4 h-4" /> أخطاء أثناء الإنتاج
            </div>
            <ul className="text-xs text-rose-100 space-y-1.5 leading-6">
              {errors.map((e, i) => (
                <li key={i} className="font-mono">
                  لقطة {e.n}: <span className="text-rose-200">{e.error}</span>
                </li>
              ))}
            </ul>
            <div className="text-[11px] text-rose-200/70 mt-3 leading-6 border-t border-rose-500/20 pt-2">
              💡 الأسباب الشائعة: (١) ما عندك وصول لـSora 2 — فعّله من
              <a href="https://sora.com/onboarding" target="_blank" rel="noopener noreferrer" className="underline mx-1">sora.com/onboarding</a>،
              (٢) رصيد OpenAI صفر — اشحن من
              <a href="https://platform.openai.com/account/billing/overview" target="_blank" rel="noopener noreferrer" className="underline mx-1">billing</a>،
              (٣) المنطقة الجغرافية لا تدعم Sora 2.
            </div>
          </div>
        )}

        {/* Done actions */}
        {isDone && (
          <div className="bg-emerald-500/10 border border-emerald-500/30 rounded-xl p-4 text-center">
            <CheckCircle2 className="w-10 h-10 text-emerald-400 mx-auto mb-2" />
            <h3 className="text-emerald-300 font-semibold mb-2">الإنتاج اكتمل بنجاح</h3>
            <p className="text-xs text-zinc-400 mb-3">خُصم {ep.credits_charged} نقطة · {total} لقطة جاهزة.</p>
            <button onClick={() => navigate('/chat/video')}
              className="bg-emerald-500 hover:bg-emerald-400 text-black font-medium px-5 py-2 rounded-lg text-sm">
              ارجع للاستوديو وشاهد الحلقة
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
