import { useEffect } from 'react';
import { X, Download, ExternalLink } from 'lucide-react';

/**
 * Full-screen image lightbox.
 * Click outside or press Esc to close.
 * Props:
 *   src — full image URL
 *   alt — accessibility label
 *   downloadName — filename suggestion for download
 *   onClose — callback
 */
export default function ImageLightbox({ src, alt, downloadName, onClose }) {
  useEffect(() => {
    const handler = (e) => { if (e.key === 'Escape') onClose?.(); };
    window.addEventListener('keydown', handler);
    document.body.style.overflow = 'hidden';
    return () => {
      window.removeEventListener('keydown', handler);
      document.body.style.overflow = '';
    };
  }, [onClose]);

  if (!src) return null;

  return (
    <div
      className="fixed inset-0 z-[300] flex items-center justify-center bg-black/90 backdrop-blur-md p-4 sm:p-8"
      onClick={onClose}
      data-testid="image-lightbox"
    >
      {/* Action buttons (top-right) */}
      <div className="absolute top-4 right-4 flex gap-2 z-10" onClick={(e) => e.stopPropagation()}>
        <a
          href={src}
          download={downloadName || 'asset.png'}
          className="px-3 py-2 bg-white/10 hover:bg-white/20 backdrop-blur border border-white/20 rounded-lg text-white text-sm font-bold flex items-center gap-2 transition-all"
          data-testid="lightbox-download"
          title="تنزيل"
        >
          <Download className="w-4 h-4" />
          <span className="hidden sm:inline">تنزيل</span>
        </a>
        <a
          href={src}
          target="_blank"
          rel="noopener noreferrer"
          className="px-3 py-2 bg-white/10 hover:bg-white/20 backdrop-blur border border-white/20 rounded-lg text-white text-sm font-bold flex items-center gap-2 transition-all"
          data-testid="lightbox-open-new-tab"
          title="فتح في نافذة جديدة"
        >
          <ExternalLink className="w-4 h-4" />
        </a>
        <button
          type="button"
          onClick={onClose}
          className="px-3 py-2 bg-red-500/20 hover:bg-red-500/30 backdrop-blur border border-red-400/40 rounded-lg text-white text-sm font-bold flex items-center gap-2 transition-all"
          data-testid="lightbox-close"
          title="إغلاق (Esc)"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Image */}
      <img
        src={src}
        alt={alt || ''}
        className="max-w-full max-h-full object-contain rounded-lg shadow-2xl select-none"
        onClick={(e) => e.stopPropagation()}
        data-testid="lightbox-image"
      />

      {/* Caption (bottom) */}
      {alt && (
        <div className="absolute bottom-4 left-4 right-4 text-center pointer-events-none">
          <div className="inline-block px-4 py-2 bg-black/60 backdrop-blur border border-white/10 rounded-lg text-sm text-white/90 max-w-2xl truncate">
            {alt}
          </div>
        </div>
      )}
    </div>
  );
}
