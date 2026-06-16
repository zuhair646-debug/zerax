/**
 * ZCrownSpinner — Animated brand logo shown while the AI agent is actively
 * working (streaming, fetching tools, generating media).
 *
 * - Uses the same red Z + golden crown SVG from the Video Studio header.
 * - Rotates continuously, pulses softly, glows with red shadow.
 * - Self-contained: no external props except `size`.
 *
 * Usage:
 *   {message.agent_streaming && <ZCrownSpinner size={32} />}
 */
import React from 'react';

export default function ZCrownSpinner({ size = 36, label = 'يعمل الآن…' }) {
  return (
    <div
      className="inline-flex items-center gap-2.5 rounded-full bg-red-500/10 border border-red-500/30 px-3 py-1.5 text-xs font-bold text-red-200"
      data-testid="z-crown-spinner"
      role="status"
      aria-live="polite"
    >
      <svg
        viewBox="0 0 200 220"
        width={size}
        height={size * (220 / 200)}
        xmlns="http://www.w3.org/2000/svg"
        style={{
          filter: 'drop-shadow(0 0 8px rgba(220, 38, 38, 0.75))',
          animation: 'zcrown-spin 2.2s linear infinite, zcrown-pulse 1.4s ease-in-out infinite',
        }}
        aria-hidden="true"
      >
        <defs>
          <linearGradient id="zSpinRed" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#fca5a5" />
            <stop offset="35%" stopColor="#ef4444" />
            <stop offset="100%" stopColor="#991b1b" />
          </linearGradient>
          <linearGradient id="zSpinGold" x1="0%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stopColor="#fde68a" />
            <stop offset="55%" stopColor="#f59e0b" />
            <stop offset="100%" stopColor="#b45309" />
          </linearGradient>
        </defs>
        {/* Crown */}
        <g transform="translate(40, 8)">
          <path
            d="M0,48 L0,16 L20,32 L40,4 L60,32 L80,16 L80,48 Z"
            fill="url(#zSpinGold)"
            stroke="#7c2d12"
            strokeWidth="2"
            strokeLinejoin="round"
          />
          <rect x="-2" y="46" width="84" height="8" rx="2" fill="#b45309" stroke="#7c2d12" strokeWidth="1.5" />
          <circle cx="20" cy="34" r="3.5" fill="#dc2626" stroke="#fff" strokeWidth="0.8" />
          <circle cx="40" cy="14" r="4" fill="#dc2626" stroke="#fff" strokeWidth="0.8" />
          <circle cx="60" cy="34" r="3.5" fill="#dc2626" stroke="#fff" strokeWidth="0.8" />
        </g>
        {/* Z */}
        <g transform="translate(28, 72)">
          <path
            d="M0,0 L144,0 L144,28 L52,28 L144,108 L144,140 L0,140 L0,112 L92,112 L0,32 Z"
            fill="url(#zSpinRed)"
            stroke="#7f1d1d"
            strokeWidth="2.5"
            strokeLinejoin="round"
          />
        </g>
      </svg>
      <span className="whitespace-nowrap">{label}</span>
      <style>{`
        @keyframes zcrown-spin {
          0%   { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }
        @keyframes zcrown-pulse {
          0%, 100% { filter: drop-shadow(0 0 6px rgba(220, 38, 38, 0.5)); }
          50%      { filter: drop-shadow(0 0 14px rgba(220, 38, 38, 0.95)); }
        }
      `}</style>
    </div>
  );
}
