/**
 * GlobalAvatarMount — renders ZitexDuoLauncher on every page,
 * EXCEPT routes where the avatars would interfere (login/register flow,
 * VRM preview diagnostic page, public site preview).
 */
import React from 'react';
import { useLocation } from 'react-router-dom';
import ZitexDuoLauncher from './ZitexDuoLauncher';

const HIDDEN_ROUTES = [
  '/vrm-preview',
  '/auth-callback',
];

const HIDDEN_PREFIXES = [
  '/build-from-zero',  // FreeBuild has its own recorder; global voice listener interferes with it
  '/sites/',          // public site preview
  '/client/',         // client subscription site
  '/driver/',         // driver dashboard
];

export default function GlobalAvatarMount() {
  // 🛑 Temporarily hidden globally — voice agent will be re-enabled later
  // The orange floating mic was distracting users; voice input is already
  // available inside each individual chat module.
  return null;
}
