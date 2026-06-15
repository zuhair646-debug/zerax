/* eslint-disable jsx-a11y/media-has-caption */
/**
 * VideoStudioPreview
 * ──────────────────────────────────────────────────────────────────────────
 * Replaces the "Live Preview" iframe inside FreeBuildChat when the project's
 * mode is one of: video_studio | anime_studio | longform_video | image_studio.
 *
 * Why a custom preview?  In video mode the AI never produces an HTML page —
 * the deliverable is a set of assets (script + keyframes + voiceover MP3 +
 * subtitles SRT). This component synchronizes those assets into a watermarked
 * slideshow so the user can review the film before paying for real animation
 * via fal.ai. The watermark + low-res render + obvious "PREVIEW" overlay
 * protect the owner from customers screen-recording the slideshow and walking
 * away without paying for the animated render.
 *
 * Security layers:
 *   1. Big diagonal "PREVIEW · ZENREX" watermark on every keyframe (CSS)
 *   2. `pointer-events: none` on the watermark so it can't be removed by JS
 *   3. `oncontextmenu={return false}` on images to block save-as
 *   4. `user-select: none` on the whole stage
 *
 * Cost: $0 — every asset shown here is already paid for and stored on the
 * server. This component just plays them back in sync.
 */
import { useEffect, useMemo, useRef, useState } from 'react';
import { Play, Pause, Download, Lock, Sparkles } from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;

export default function VideoStudioPreview({ project }) {
  const approved = useMemo(() => project?.approved_assets || [], [project]);

  // Bucket the approved assets by kind so the slideshow can pick the right ones
  const keyframes = useMemo(() => (
    approved.filter((a) => a.image_url && !a.audio_url)
  ), [approved]);

  // Use the *latest* voiceover MP3 (the user can re-generate; the newest wins)
  const voiceover = useMemo(() => {
    const audios = approved.filter((a) => a.audio_url || (a.url && /\.(mp3|wav|m4a|ogg)/i.test(a.url || '')));
    return audios.length ? audios[audios.length - 1] : null;
  }, [approved]);

  const subtitles = useMemo(() => {
    const subs = approved.filter((a) => a.kind === 'subtitles' || (a.url && /\.srt$/i.test(a.url || '')));
    return subs.length ? subs[subs.length - 1] : null;
  }, [approved]);

  const [playing, setPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [activeFrameIdx, setActiveFrameIdx] = useState(0);
  const audioRef = useRef(null);

  const resolveSrc = (url) => (!url ? '' : (url.startsWith('http') ? url : `${API}${url}`));
  const audioSrc = voiceover ? resolveSrc(voiceover.audio_url || voiceover.url) : '';

  // Advance the active keyframe in lockstep with the audio playhead
  useEffect(() => {
    if (!duration || !keyframes.length) return;
    const perFrame = duration / keyframes.length;
    const idx = Math.min(keyframes.length - 1, Math.floor(currentTime / perFrame));
    setActiveFrameIdx(idx);
  }, [currentTime, duration, keyframes.length]);

  // Parse the SRT (if any) into [{from, to, text}] for live subtitle overlay
  const subtitleCues = useMemo(() => {
    const text = subtitles?.text || '';
    if (!text) return [];
    const cues = [];
    text.split(/\n\n+/).forEach((block) => {
      const m = block.match(/(\d{2}):(\d{2}):(\d{2})[,.](\d{3})\s*-->\s*(\d{2}):(\d{2}):(\d{2})[,.](\d{3})\s*\n([\s\S]+)/);
      if (m) {
        const from = (+m[1]) * 3600 + (+m[2]) * 60 + (+m[3]) + (+m[4]) / 1000;
        const to   = (+m[5]) * 3600 + (+m[6]) * 60 + (+m[7]) + (+m[8]) / 1000;
        cues.push({ from, to, text: m[9].trim() });
      }
    });
    // Fallback: if SRT didn't parse, evenly distribute lines from `text`
    if (!cues.length && keyframes.length) {
      const lines = text.split(/[\n.!?]+/).filter(Boolean);
      const per = (duration || 60) / Math.max(1, lines.length);
      lines.forEach((ln, i) => cues.push({ from: i * per, to: (i + 1) * per, text: ln.trim() }));
    }
    return cues;
  }, [subtitles, duration, keyframes.length]);

  const activeCue = subtitleCues.find((c) => currentTime >= c.from && currentTime <= c.to);

  const toggle = () => {
    if (!audioRef.current) return;
    if (playing) { audioRef.current.pause(); }
    else { audioRef.current.play().catch(() => {}); }
  };

  const seek = (pct) => {
    if (!audioRef.current || !duration) return;
    audioRef.current.currentTime = pct * duration;
  };

  // Empty state — nothing approved yet
  if (!keyframes.length && !voiceover) {
    return (
      <div className="flex-1 flex items-center justify-center p-8" data-testid="video-preview-empty">
        <div className="text-center max-w-md">
          <Sparkles className="w-14 h-14 mx-auto mb-4 text-violet-400/60" />
          <h3 className="text-zinc-200 text-base font-bold mb-2">المعاينة هنا</h3>
          <p className="text-zinc-500 text-xs leading-relaxed">
            بعد ما يولّد الذكاء الستوري بورد + التعليق الصوتي وتعتمد الأصول،
            راح تشاهد الفيلم هنا كعرض slideshow متزامن — قبل ما تدفع لتحويله لفيديو متحرك حقيقي.
          </p>
          <p className="text-emerald-400/70 text-[10px] mt-3">
            💰 المعاينة مجانية تماماً — كل الأصول الظاهرة هنا مدفوعة سلفاً
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col bg-black overflow-hidden" data-testid="video-studio-preview">
      {/* Header — title + protection notice */}
      <div className="px-4 py-2.5 border-b border-white/10 flex items-center justify-between gap-3 bg-zinc-950/50">
        <div className="flex items-center gap-2">
          <Sparkles className="w-4 h-4 text-violet-400" />
          <span className="text-sm font-bold text-violet-200">معاينة الفيلم (Studio)</span>
        </div>
        <div className="flex items-center gap-1.5 text-[10px] text-amber-300/80 bg-amber-500/10 border border-amber-500/30 rounded-full px-2 py-0.5">
          <Lock className="w-3 h-3" />
          <span>محمي بعلامة مائية</span>
        </div>
      </div>

      {/* Stage — keyframe with watermark + subtitle overlay */}
      <div
        className="flex-1 flex items-center justify-center bg-black relative select-none overflow-hidden"
        onContextMenu={(e) => e.preventDefault()}
        style={{ userSelect: 'none', WebkitUserSelect: 'none' }}
        data-testid="video-stage"
      >
        {keyframes.length > 0 && (
          <div className="relative w-full max-w-4xl aspect-video">
            {keyframes.map((kf, i) => (
              <img
                key={kf.id || i}
                src={resolveSrc(kf.image_url)}
                alt=""
                draggable={false}
                onContextMenu={(e) => e.preventDefault()}
                className={`absolute inset-0 w-full h-full object-cover transition-opacity duration-700 ${
                  i === activeFrameIdx ? 'opacity-100' : 'opacity-0'
                }`}
              />
            ))}

            {/* DIAGONAL WATERMARK — repeats across the whole stage */}
            <div
              className="absolute inset-0 pointer-events-none flex items-center justify-center overflow-hidden"
              aria-hidden="true"
              style={{
                background:
                  'repeating-linear-gradient(-30deg, transparent 0 110px, rgba(168,85,247,0.18) 110px 130px)',
              }}
            >
              <div className="text-white/40 font-black text-5xl tracking-widest rotate-[-30deg] whitespace-nowrap" style={{ textShadow: '0 2px 10px rgba(0,0,0,0.6)' }}>
                PREVIEW · ZENREX · PREVIEW · ZENREX
              </div>
            </div>

            {/* Subtitle overlay */}
            {activeCue && (
              <div className="absolute bottom-6 left-0 right-0 flex justify-center pointer-events-none px-4">
                <div className="bg-black/70 text-white px-3 py-1.5 rounded-md text-sm sm:text-base font-medium max-w-2xl text-center" dir="rtl" style={{ textShadow: '0 1px 2px rgba(0,0,0,0.9)' }}>
                  {activeCue.text}
                </div>
              </div>
            )}

            {/* Frame counter (bottom-right) */}
            <div className="absolute top-2 right-2 bg-black/60 text-white text-[10px] px-2 py-0.5 rounded">
              لقطة {activeFrameIdx + 1} / {keyframes.length}
            </div>
          </div>
        )}
      </div>

      {/* Controls bar */}
      <div className="px-4 py-3 border-t border-white/10 bg-zinc-950/80 flex items-center gap-3" data-testid="video-controls">
        <button
          type="button"
          onClick={toggle}
          disabled={!audioSrc}
          data-testid="video-play-btn"
          className="w-10 h-10 rounded-full bg-violet-500 hover:bg-violet-400 text-white flex items-center justify-center disabled:opacity-40 disabled:cursor-not-allowed transition"
        >
          {playing ? <Pause className="w-5 h-5" /> : <Play className="w-5 h-5 mr-[-2px]" />}
        </button>
        <div className="flex-1 flex items-center gap-2">
          <span className="text-[10px] text-zinc-400 w-10 text-center font-mono">{fmt(currentTime)}</span>
          <div
            className="flex-1 h-1.5 bg-zinc-800 rounded-full cursor-pointer relative"
            onClick={(e) => {
              const rect = e.currentTarget.getBoundingClientRect();
              seek((e.clientX - rect.left) / rect.width);
            }}
          >
            <div
              className="absolute inset-y-0 left-0 bg-violet-400 rounded-full transition-all"
              style={{ width: duration ? `${(currentTime / duration) * 100}%` : '0%' }}
            />
          </div>
          <span className="text-[10px] text-zinc-400 w-10 text-center font-mono">{fmt(duration)}</span>
        </div>
        {/* Render-to-real-video CTA: this is where the owner actually charges */}
        <button
          type="button"
          data-testid="render-real-video-btn"
          onClick={() => alert('قريباً: تصدير MP4 احترافي 1080p بدون watermark عبر fal.ai. التكلفة تظهر قبل التأكيد.')}
          className="hidden sm:flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-gradient-to-r from-emerald-500 to-teal-500 hover:from-emerald-400 hover:to-teal-400 text-black text-xs font-bold"
          title="حوّل المعاينة لفيديو متحرك حقيقي (مدفوع)"
        >
          <Download className="w-3.5 h-3.5" />
          <span>صدّر فيديو حقيقي</span>
        </button>
      </div>

      {/* Hidden audio element that drives the whole timeline */}
      {audioSrc && (
        <audio
          ref={audioRef}
          src={audioSrc}
          onLoadedMetadata={(e) => setDuration(e.target.duration || 0)}
          onTimeUpdate={(e) => setCurrentTime(e.target.currentTime || 0)}
          onPlay={() => setPlaying(true)}
          onPause={() => setPlaying(false)}
          onEnded={() => { setPlaying(false); setCurrentTime(0); setActiveFrameIdx(0); }}
          preload="metadata"
        />
      )}
    </div>
  );
}

function fmt(t) {
  if (!t || !isFinite(t)) return '0:00';
  const m = Math.floor(t / 60);
  const s = Math.floor(t % 60);
  return `${m}:${s.toString().padStart(2, '0')}`;
}
