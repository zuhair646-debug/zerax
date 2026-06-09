import React, { useEffect, useState } from 'react';
import { Smartphone, Download, CheckCircle2, Apple } from 'lucide-react';

/**
 * Zerax PWA Install Card
 * A reusable installable-app card for any control panel (Customer / Merchant / Admin).
 * Handles:
 *  - Android/Chrome: triggers `beforeinstallprompt` deferred event
 *  - iOS Safari: opens the visual 3-step guide (defined in /public/index.html)
 *  - Desktop Chrome/Edge: triggers prompt if available
 *  - Already-installed detection: shows confirmation badge instead
 */

const detectInitialState = () => {
  if (typeof window === 'undefined') return 'idle';
  const isStandalone =
    window.matchMedia('(display-mode: standalone)').matches ||
    window.navigator.standalone === true;
  if (isStandalone) return 'installed';
  const isIOS = /iPad|iPhone|iPod/.test(navigator.userAgent) && !window.MSStream;
  if (window.__zxDeferredPrompt) return 'installable';
  if (isIOS) return 'ios';
  return 'unsupported';
};

const safeSet = (k, v) => { try { localStorage.setItem(k, v); } catch { /* ignore */ } };
const safeRm = (k) => { try { localStorage.removeItem(k); } catch { /* ignore */ } };

const PWAInstallCard = () => {
  const [state, setState] = useState(detectInitialState);
  const [deferredPrompt, setDeferredPrompt] = useState(() =>
    typeof window !== 'undefined' ? window.__zxDeferredPrompt || null : null
  );

  useEffect(() => {
    const onPrompt = (e) => {
      e.preventDefault();
      setDeferredPrompt(e);
      window.__zxDeferredPrompt = e;
      setState('installable');
    };
    const onInstalled = () => {
      setState('installed');
      safeSet('zx_pwa_installed', '1');
    };
    window.addEventListener('beforeinstallprompt', onPrompt);
    window.addEventListener('appinstalled', onInstalled);
    return () => {
      window.removeEventListener('beforeinstallprompt', onPrompt);
      window.removeEventListener('appinstalled', onInstalled);
    };
  }, []);

  const handleInstall = async () => {
    const isIOS = /iPad|iPhone|iPod/.test(navigator.userAgent) && !window.MSStream;
    if (isIOS && typeof window.showIOSInstallGuide === 'function') {
      window.showIOSInstallGuide();
      return;
    }
    if (deferredPrompt) {
      deferredPrompt.prompt();
      const choice = await deferredPrompt.userChoice;
      if (choice && choice.outcome === 'accepted') {
        safeSet('zx_pwa_installed', '1');
        setState('installed');
      }
      setDeferredPrompt(null);
      window.__zxDeferredPrompt = null;
    } else {
      safeRm('zx_pwa_installed');
      alert(
        'لتثبيت التطبيق:\n\n' +
        '• على Chrome (Android/Desktop): افتح القائمة (⋮) → "تثبيت Zerax".\n' +
        '• على Safari (iPhone/iPad): زر المشاركة ⬆ → "إضافة إلى الشاشة الرئيسية".\n\n' +
        'إذا قمت بحذف التطبيق سابقاً، أعد فتح الموقع وانتظر بضع ثوانٍ ليظهر زر التثبيت تلقائياً.'
      );
    }
  };

  // Already installed → show confirmation card (non-clickable)
  if (state === 'installed') {
    return (
      <div
        className="rounded-2xl bg-gradient-to-br from-emerald-500/10 to-emerald-700/5 border border-emerald-500/25 p-5"
        data-testid="pwa-install-card-installed"
      >
        <h3 className="text-white font-black text-sm mb-3 flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 text-emerald-400" /> تطبيق Zerax
        </h3>
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-emerald-500/15 flex items-center justify-center">
            <CheckCircle2 className="w-6 h-6 text-emerald-400" />
          </div>
          <div className="flex-1">
            <p className="text-white text-sm font-bold">التطبيق مثبت على هذا الجهاز</p>
            <p className="text-gray-400 text-xs">افتحه من شاشتك الرئيسية في أي وقت</p>
          </div>
        </div>
      </div>
    );
  }

  // iOS Safari → show install button (opens visual guide)
  if (state === 'ios') {
    return (
      <div
        className="rounded-2xl bg-gradient-to-br from-purple-500/10 to-pink-700/5 border border-purple-500/25 p-5"
        data-testid="pwa-install-card-ios"
      >
        <h3 className="text-white font-black text-sm mb-3 flex items-center gap-2">
          <Apple className="w-4 h-4 text-purple-300" /> ثبّت تطبيق Zerax على آيفونك
        </h3>
        <p className="text-purple-200/70 text-xs mb-4 leading-relaxed">
          استخدم Safari واضغط الزر أدناه — ستظهر لك ٣ خطوات مصورة لإضافة التطبيق إلى شاشتك الرئيسية.
        </p>
        <button
          type="button"
          onClick={handleInstall}
          data-testid="pwa-install-ios-btn"
          className="w-full px-4 py-3 rounded-lg bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-500 hover:to-pink-500 text-white text-sm font-black flex items-center justify-center gap-2 transition-all"
        >
          <Download className="w-4 h-4" /> عرض دليل التثبيت
        </button>
      </div>
    );
  }

  // Android/Chrome with installable prompt → primary CTA
  if (state === 'installable') {
    return (
      <div
        className="rounded-2xl bg-gradient-to-br from-amber-500/10 to-yellow-700/5 border border-amber-500/25 p-5"
        data-testid="pwa-install-card-installable"
      >
        <h3 className="text-white font-black text-sm mb-3 flex items-center gap-2">
          <Smartphone className="w-4 h-4 text-amber-400" /> ثبّت تطبيق Zerax
        </h3>
        <p className="text-amber-200/70 text-xs mb-4 leading-relaxed">
          احصل على Zerax كتطبيق على جهازك — تشغيل أسرع، شاشة كاملة، بدون شريط المتصفح.
        </p>
        <button
          type="button"
          onClick={handleInstall}
          data-testid="pwa-install-btn"
          className="w-full px-4 py-3 rounded-lg bg-gradient-to-r from-amber-500 to-yellow-500 hover:from-amber-400 hover:to-yellow-400 text-black text-sm font-black flex items-center justify-center gap-2 transition-all"
        >
          <Download className="w-4 h-4" /> تثبيت الآن
        </button>
      </div>
    );
  }

  // Unsupported / unknown — still show a manual install instructions button
  return (
    <div
      className="rounded-2xl bg-slate-800/40 border border-slate-700 p-5"
      data-testid="pwa-install-card-manual"
    >
      <h3 className="text-white font-black text-sm mb-3 flex items-center gap-2">
        <Smartphone className="w-4 h-4 text-amber-400" /> تطبيق Zerax
      </h3>
      <p className="text-gray-400 text-xs mb-4 leading-relaxed">
        لم نتمكن من اكتشاف خيار التثبيت التلقائي على هذا المتصفح. اضغط الزر لرؤية تعليمات التثبيت اليدوية.
      </p>
      <button
        type="button"
        onClick={handleInstall}
        data-testid="pwa-install-manual-btn"
        className="w-full px-4 py-3 rounded-lg border border-slate-700 bg-slate-900/40 hover:bg-slate-900/60 text-gray-200 text-sm font-bold flex items-center justify-center gap-2 transition-all"
      >
        <Download className="w-4 h-4" /> طريقة التثبيت
      </button>
    </div>
  );
};

export default PWAInstallCard;
