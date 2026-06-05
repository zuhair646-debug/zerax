import { useState } from 'react';
import { ImageOff, Eye } from 'lucide-react';

/**
 * 🖼️ Safe image component for game assets with auto-vision verification badge.
 * - Tries the primary src, then cdnUrl, then placeholder.
 * - Shows a small verification overlay (verdict + match %) if the asset has been
 *   auto-analyzed by Claude vision (set by _auto_vision_verify on backend).
 */
export default function SafeAssetImage({ src, cdnUrl, alt, className, onClick, verification, ...rest }) {
  const [stage, setStage] = useState(0); // 0=primary, 1=cdn, 2=missing
  const handleError = () => {
    if (stage === 0 && cdnUrl) setStage(1);
    else setStage(2);
  };
  if (stage === 2) {
    return (
      <div
        className={`${className || ''} flex flex-col items-center justify-center bg-zinc-800/60 border border-dashed border-zinc-600 text-zinc-400 p-3 text-center`}
        title={alt}
        onClick={onClick}
      >
        <ImageOff className="w-6 h-6 mb-1 opacity-50" />
        <span className="text-[10px] leading-tight">الصورة غير متاحة</span>
        <span className="text-[9px] opacity-60 mt-1 line-clamp-2">{(alt || '').slice(0, 50)}</span>
      </div>
    );
  }
  const finalSrc = stage === 1 && cdnUrl ? cdnUrl : src;
  const matchPct = verification?.match;
  let badgeColor = 'bg-emerald-500/80 text-white';
  if (matchPct != null) {
    if (matchPct < 60) badgeColor = 'bg-rose-500/80 text-white';
    else if (matchPct < 80) badgeColor = 'bg-amber-500/80 text-white';
  }
  const title = verification
    ? `${verification.verdict || ''}${verification.issues?.length ? ' • ' + verification.issues.join(' / ') : ''}`
    : '';
  return (
    <div className={`relative ${className || ''}`}>
      <img
        src={finalSrc}
        alt={alt}
        onError={handleError}
        onClick={onClick}
        className="w-full h-full object-cover"
        loading="lazy"
        {...rest}
      />
      {verification && matchPct != null && (
        <div
          className={`absolute bottom-1.5 right-1.5 px-1.5 py-0.5 rounded-md ${badgeColor} text-[9px] font-bold inline-flex items-center gap-1 backdrop-blur-sm shadow-md`}
          title={title}
          data-testid="vision-verify-badge"
        >
          <Eye className="w-3 h-3" />
          <span>{matchPct}%</span>
        </div>
      )}
    </div>
  );
}
