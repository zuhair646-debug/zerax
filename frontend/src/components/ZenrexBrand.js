/**
 * ZenrexBrand — official brand mark using the gold Z+crown PNG.
 * Use everywhere we want to surface the proprietary AI identity instead of
 * exposing the underlying provider (Claude/Opus/etc.).
 */
import React from 'react';

export default function ZenrexBrand({ size = 24, showLabel = true, label = 'زنركس AI', className = '' }) {
  const [imgError, setImgError] = React.useState(false);
  return (
    <span className={`inline-flex items-center gap-2 ${className}`} data-testid="zenrex-brand">
      {imgError ? (
        <span
          style={{ width: size, height: size }}
          className="inline-flex items-center justify-center rounded-md bg-gradient-to-br from-amber-400 to-yellow-600 text-black font-black"
        >
          Z
        </span>
      ) : (
        <img
          src="/zenrex-logo.png"
          alt="Zenrex"
          width={size}
          height={size}
          onError={() => setImgError(true)}
          style={{
            objectFit: 'contain',
            filter: 'drop-shadow(0 0 4px rgba(212,175,55,0.45))',
            flexShrink: 0,
          }}
        />
      )}
      {showLabel && (
        <span
          className="font-extrabold whitespace-nowrap"
          style={{
            background: 'linear-gradient(90deg, #FFD86B, #D4AF37)',
            WebkitBackgroundClip: 'text',
            backgroundClip: 'text',
            color: 'transparent',
            fontSize: `${Math.round(size * 0.55)}px`,
            letterSpacing: '0.5px',
          }}
        >
          {label}
        </span>
      )}
    </span>
  );
}
