/**
 * 🎬 Cinema Studio
 * ─────────────────
 * Same Socratic chat experience as Web Games Studio, but for video creation:
 *   فيلم سينمائي · فيديو كليب · إعلان منتج · وثائقي · رسوم متحركة ·
 *   حلقة أكشن طويلة · محتوى تعليمي · فيديو سوشل قصير.
 *
 * Backend reuses the games engine — phases swapped to CINEMA_PHASES and the
 * system prompt morphs into a film-director persona automatically when
 * `game_type === "cinema"`.
 */
import React from 'react';
import WebGamesStudio from './WebGamesStudio';

const CINEMA_CONFIG = {
  title: '🎬 Cinema Studio',
  subtitle: 'اختر نوع الفيديو وابدأ مشروعك — نفس تجربة الألعاب لكن للسينما',
  icon: 'film',
  accentColor: 'amber',
  sectionLabel: '🎞️ اختر نوع الفيديو',
  sectionHint: 'اختر القالب اللي يناسب رؤيتك — كل قالب يضبط نمط الإخراج والإضاءة تلقائياً',
  projectLabelTitle: 'عنوان المشروع (مثال: إعلان عطر فاخر / حلقة أكشن "الصقر")',
  backRoute: '/dashboard',
  storeKey: 'cinema',
};

export default function CinemaStudio({ user }) {
  return <WebGamesStudio user={user} gameType="cinema" studioConfig={CINEMA_CONFIG} />;
}
