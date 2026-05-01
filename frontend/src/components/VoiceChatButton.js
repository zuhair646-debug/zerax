/**
 * VoiceChatButton — Simple floating voice button (ChatGPT-style).
 *
 * Replaces the 3D character peek temporarily while we work on Phase 2.
 * Click → opens VoiceStage for conversation with Zara/Layla.
 * Wake-word still works in the background.
 *
 * The 3D character system is NOT deleted — it's just hidden behind
 * `SHOW_CHARACTERS=false` in GlobalAvatarMount.
 */
import React from 'react';
import { Mic } from 'lucide-react';

export default function VoiceChatButton({ onClick }) {
  return (
    <button
      onClick={onClick}
      data-testid="voice-chat-button"
      aria-label="تكلّم مع زيتكس"
      className="fixed bottom-6 right-6 z-40 w-14 h-14 rounded-full bg-gradient-to-br from-amber-500 via-orange-500 to-pink-500 text-black shadow-[0_0_28px_rgba(245,158,11,0.55)] flex items-center justify-center hover:scale-110 active:scale-95 transition-transform group"
    >
      {/* Subtle pulse ring */}
      <span className="absolute inset-0 rounded-full bg-amber-400/25 animate-ping" aria-hidden />
      <Mic className="w-6 h-6 relative z-10" strokeWidth={2.5} />
      {/* Tooltip on hover */}
      <span className="absolute -top-10 right-0 px-3 py-1.5 rounded-xl bg-black/80 backdrop-blur-md text-white text-xs font-black whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none" dir="rtl">
        كلّم زيتكس صوتاً
      </span>
    </button>
  );
}
