import { useState } from 'react';
import { ImageOff } from 'lucide-react';

/**
 * 🖼️ Safe image component for game assets.
 * - Tries the primary src.
 * - On error, falls back to the CDN URL (if provided).
 * - On final failure, shows a clean "missing asset" placeholder so the user
 *   knows what happened instead of seeing a broken-image icon.
 */
export default function SafeAssetImage({ src, cdnUrl, alt, className, onClick, ...rest }) {
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
  return (
    <img
      src={finalSrc}
      alt={alt}
      onError={handleError}
      onClick={onClick}
      className={className}
      loading="lazy"
      {...rest}
    />
  );
}
