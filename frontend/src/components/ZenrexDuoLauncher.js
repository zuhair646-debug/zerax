/**
 * ZenrexDuoLauncher v8 — AMBIENT VOICE ONLY (no chat panel, no 3D).
 *
 * Just mounts AmbientVoiceAgent on every eligible page.
 * User either:
 *   - Says "زيتكس" to wake the AI, or
 *   - Clicks the mic button to start talking immediately
 * AI replies are played as audio + shown as toast (no modal).
 */
import React from 'react';
import AmbientVoiceAgent from './AmbientVoiceAgent';

export default function ZenrexDuoLauncher() {
  return <AmbientVoiceAgent />;
}
