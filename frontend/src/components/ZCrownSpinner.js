/**
 * Working indicator — neutral animated dots while the AI agent is busy.
 * (Previously a red Z + crown brand logo; replaced per UX requirement
 * to keep Zenrex AI feeling proprietary and not flag any model name.)
 */
import React from 'react';

export default function ZCrownSpinner({ size = 28, label = 'يحلل ويكتب...' }) {
  const dot = Math.max(4, Math.round(size / 7));
  return (
    <div
      className="inline-flex items-center gap-2 rounded-full bg-emerald-500/10 border border-emerald-400/30 px-3 py-1.5 text-[12px] font-semibold"
      data-testid="z-crown-spinner"
      role="status"
      aria-live="polite"
    >
      <span className="flex items-center gap-1">
        <span
          className="rounded-full bg-cyan-300 animate-pulse"
          style={{ width: dot, height: dot, animationDelay: '0ms' }}
        />
        <span
          className="rounded-full bg-emerald-300 animate-pulse"
          style={{ width: dot, height: dot, animationDelay: '180ms' }}
        />
        <span
          className="rounded-full bg-cyan-300 animate-pulse"
          style={{ width: dot, height: dot, animationDelay: '360ms' }}
        />
      </span>
      <span className="bg-gradient-to-r from-cyan-300 via-emerald-300 to-cyan-300 bg-clip-text text-transparent whitespace-nowrap">
        {label}
      </span>
    </div>
  );
}
