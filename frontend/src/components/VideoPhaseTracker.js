/**
 * VideoPhaseTracker
 * ────────────────────────────────────────────────────────────────────────
 * Non-disruptive workflow tracker for video/anime/longform projects.
 *
 * Renders a thin pill bar at the top of FreeBuildChat showing 7 phases.
 * Each phase has 3 visual states:
 *   • 🟢 done    — solid green, ✓ checkmark, clickable to review assets
 *   • 🟠 current — pulsing orange glow, "in progress" label
 *   • 🔴 locked  — dim red, lock icon, click shows "finish previous phase first"
 *
 * Mobile:
 *   The pill bar stays compact (current phase only).
 *   Tap the bar → opens a bottom sheet showing all 7 phases.
 *   Tap a done/current phase → opens a slide-over inspector with its assets.
 *
 * Why a separate component?
 *   The user explicitly asked: "don't touch the chat layout or writing style."
 *   This sits ABOVE the chat as its own layer and never interferes with
 *   message rendering, streaming, or input.
 */
import { useMemo, useState } from 'react';
import { Check, Lock, Loader2, ChevronUp, X, Film, Users, FileText, Mic2, Image as ImageIcon, Eye, Sparkles } from 'lucide-react';

export const VIDEO_PHASES = [
  { id: 'film_type',     label: 'نوع الفيلم',     icon: Film,        desc: 'كرتون/أنمي/سينمائي/رعب/واقعي' },
  { id: 'characters',    label: 'الشخصيات',       icon: Users,       desc: 'تأسيس وتصميم الشخصيات' },
  { id: 'script',        label: 'السيناريو',      icon: FileText,    desc: 'كتابة الحوار والمشاهد' },
  { id: 'voice',         label: 'الصوت + الترجمة', icon: Mic2,        desc: 'اختيار الأصوات والترجمات' },
  { id: 'storyboard',    label: 'اللقطات',        icon: ImageIcon,   desc: 'توليد الصور المرجعية' },
  { id: 'preview',       label: 'المعاينة',        icon: Eye,         desc: 'مراجعة الفيلم قبل التصدير' },
  { id: 'render',        label: 'توليد HD',        icon: Sparkles,    desc: 'الفيديو النهائي المتحرك' },
];

export default function VideoPhaseTracker({ project, onOpenAssets }) {
  const [expanded, setExpanded] = useState(false);
  const [inspecting, setInspecting] = useState(null);

  const currentPhase = project?.current_phase || 'film_type';
  const phaseHistory = useMemo(() => new Set(project?.phase_history || []), [project]);

  const phases = VIDEO_PHASES.map((p) => {
    let state = 'locked';
    if (phaseHistory.has(p.id)) state = 'done';
    else if (p.id === currentPhase) state = 'current';
    else {
      // Unlock the next phase after the current one's predecessor
      const idx = VIDEO_PHASES.findIndex((x) => x.id === currentPhase);
      const myIdx = VIDEO_PHASES.findIndex((x) => x.id === p.id);
      if (myIdx < idx) state = 'done';
    }
    return { ...p, state };
  });

  const currentObj = phases.find((p) => p.id === currentPhase) || phases[0];

  const colorClass = (state) => {
    if (state === 'done')    return 'bg-emerald-500/20 border-emerald-400/50 text-emerald-300';
    if (state === 'current') return 'bg-amber-500/25 border-amber-400 text-amber-200 shadow-[0_0_20px_rgba(251,191,36,0.5)] animate-pulse';
    return 'bg-red-500/10 border-red-500/30 text-red-400/70';
  };

  const Pill = ({ p, onClick }) => {
    const Icon = p.icon;
    return (
      <button
        type="button"
        onClick={onClick}
        data-testid={`phase-pill-${p.id}`}
        className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-full border text-[10px] sm:text-xs font-bold transition-all ${colorClass(p.state)}`}
      >
        {p.state === 'done' ? <Check className="w-3 h-3" />
          : p.state === 'current' ? <Loader2 className="w-3 h-3 animate-spin" />
          : <Lock className="w-3 h-3" />}
        <Icon className="w-3 h-3" />
        <span className="whitespace-nowrap">{p.label}</span>
      </button>
    );
  };

  return (
    <>
      {/* ── Desktop: full pills bar always visible ── */}
      <div className="hidden sm:flex items-center gap-1.5 px-3 py-2 border-b border-white/5 bg-zinc-950/40 overflow-x-auto" data-testid="phase-tracker-desktop">
        {phases.map((p) => (
          <Pill
            key={p.id}
            p={p}
            onClick={() => {
              if (p.state === 'locked') return;
              setInspecting(p);
              onOpenAssets?.(p.id);
            }}
          />
        ))}
      </div>

      {/* ── Mobile: compact bar showing just the current phase + expand button ── */}
      <button
        type="button"
        onClick={() => setExpanded(true)}
        data-testid="phase-tracker-mobile-toggle"
        className="sm:hidden flex items-center justify-between gap-2 px-3 py-2 border-b border-white/5 bg-zinc-950/60 w-full"
      >
        <div className="flex items-center gap-2">
          <span className="text-[10px] text-zinc-500">المرحلة</span>
          <Pill p={currentObj} onClick={(e) => e?.stopPropagation?.()} />
        </div>
        <div className="flex items-center gap-1">
          <span className="text-[10px] text-zinc-400">{phaseHistory.size}/{VIDEO_PHASES.length}</span>
          <ChevronUp className="w-3.5 h-3.5 text-zinc-400" />
        </div>
      </button>

      {/* ── Mobile bottom sheet: all 7 phases ── */}
      {expanded && (
        <div className="sm:hidden fixed inset-0 z-50 bg-black/70 flex items-end" onClick={() => setExpanded(false)}>
          <div
            className="w-full bg-zinc-900 border-t border-white/10 rounded-t-2xl p-4 max-h-[80vh] overflow-y-auto"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-bold text-zinc-200">مراحل الإنتاج</h3>
              <button type="button" onClick={() => setExpanded(false)} className="text-zinc-400">
                <X className="w-4 h-4" />
              </button>
            </div>
            <div className="space-y-2">
              {phases.map((p) => {
                const Icon = p.icon;
                return (
                  <button
                    key={p.id}
                    type="button"
                    onClick={() => {
                      if (p.state === 'locked') return;
                      setExpanded(false);
                      setInspecting(p);
                      onOpenAssets?.(p.id);
                    }}
                    data-testid={`phase-mobile-${p.id}`}
                    className={`w-full flex items-center gap-3 p-3 rounded-xl border ${colorClass(p.state)}`}
                  >
                    <Icon className="w-5 h-5 flex-shrink-0" />
                    <div className="flex-1 text-right">
                      <div className="text-sm font-bold">{p.label}</div>
                      <div className="text-[10px] opacity-70">{p.desc}</div>
                    </div>
                    {p.state === 'done' && <Check className="w-4 h-4" />}
                    {p.state === 'current' && <Loader2 className="w-4 h-4 animate-spin" />}
                    {p.state === 'locked' && <Lock className="w-4 h-4" />}
                  </button>
                );
              })}
            </div>
            <p className="text-[10px] text-zinc-500 mt-3 text-center">
              🟠 جارية · 🟢 منتهية · 🔴 مقفلة
            </p>
          </div>
        </div>
      )}

      {/* ── Inspector slide-over (assets for a single phase) ── */}
      {inspecting && (
        <div className="fixed inset-0 z-50 bg-black/70 flex items-center justify-center p-4" onClick={() => setInspecting(null)}>
          <div className="bg-zinc-900 border border-white/10 rounded-2xl max-w-lg w-full max-h-[80vh] overflow-y-auto p-5" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-base font-bold text-zinc-100 flex items-center gap-2">
                <inspecting.icon className="w-5 h-5 text-violet-400" />
                <span>{inspecting.label}</span>
              </h3>
              <button type="button" onClick={() => setInspecting(null)} className="text-zinc-400">
                <X className="w-5 h-5" />
              </button>
            </div>
            <p className="text-xs text-zinc-400 mb-4">{inspecting.desc}</p>
            <PhaseAssetList project={project} phaseId={inspecting.id} />
          </div>
        </div>
      )}
    </>
  );
}

function PhaseAssetList({ project, phaseId }) {
  const assets = (project?.approved_assets || []).filter((a) => {
    if (phaseId === 'characters') return a.kind === 'character';
    if (phaseId === 'script')     return a.kind === 'script' || a.text;
    if (phaseId === 'voice')      return a.audio_url || a.kind === 'voiceover' || a.kind === 'subtitles';
    if (phaseId === 'storyboard') return a.image_url && a.kind !== 'character';
    if (phaseId === 'film_type')  return a.kind === 'film_type_choice';
    return false;
  });
  if (!assets.length) {
    return (
      <div className="text-center py-8 text-xs text-zinc-500">
        لا توجد أصول معتمدة بعد في هذه المرحلة
      </div>
    );
  }
  const API = process.env.REACT_APP_BACKEND_URL;
  return (
    <div className="grid grid-cols-2 gap-2">
      {assets.map((a, i) => (
        <div key={a.id || i} className="rounded-lg overflow-hidden border border-white/10 bg-black/30 p-2">
          {a.image_url && <img src={a.image_url.startsWith('http') ? a.image_url : `${API}${a.image_url}`} alt="" className="w-full aspect-square object-cover rounded" />}
          {a.audio_url && <audio controls src={a.audio_url.startsWith('http') ? a.audio_url : `${API}${a.audio_url}`} className="w-full h-7" />}
          {a.text && <div className="text-[10px] text-zinc-300 max-h-24 overflow-auto whitespace-pre-wrap" dir="rtl">{a.text.slice(0, 200)}</div>}
          <p className="text-[10px] text-zinc-500 mt-1 truncate">{a.prompt || a.kind || ''}</p>
        </div>
      ))}
    </div>
  );
}
