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
  '/sites/',          // public site preview
  '/client/',         // client subscription site
  '/driver/',         // driver dashboard
];

export default function GlobalAvatarMount() {
  const location = useLocation();
  const path = location.pathname;
  if (HIDDEN_ROUTES.includes(path)) return null;
  if (HIDDEN_PREFIXES.some((p) => path.startsWith(p))) return null;
  return <ZitexDuoLauncher />;
}
