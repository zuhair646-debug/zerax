/* eslint-disable */
import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import { isRTL } from './languages';

// Core UI strings — Arabic & English are fully hand-translated.
// All other languages fall back to English; future translations can
// be added incrementally OR generated on-demand via the backend
// translate-on-demand endpoint (calls Claude for high-quality results).
const resources = {
  ar: { translation: {
    'nav.home': 'الرئيسية',
    'nav.builder': 'الأستوديو',
    'nav.games': 'الألعاب',
    'nav.marketing': 'التسويق',
    'nav.apps': 'تطبيقاتي',
    'nav.deploy': 'النشر',
    'nav.pricing': 'الأسعار',
    'nav.login': 'تسجيل الدخول',
    'nav.signup': 'إنشاء حساب',
    'nav.dashboard': 'لوحة التحكم',
    'nav.logout': 'تسجيل الخروج',
    'common.send': 'إرسال',
    'common.cancel': 'إلغاء',
    'common.save': 'حفظ',
    'common.delete': 'حذف',
    'common.edit': 'تعديل',
    'common.loading': 'جاري التحميل...',
    'common.error': 'حدث خطأ',
    'common.success': 'تم بنجاح',
    'common.next': 'التالي',
    'common.previous': 'السابق',
    'common.close': 'إغلاق',
    'common.confirm': 'تأكيد',
    'common.search': 'بحث',
    'common.language': 'اللغة',
    'common.welcome': 'مرحباً',
    'freebuild.title': 'ابنِ موقعك من الصفر',
    'freebuild.placeholder': 'اكتب أو سجل صوت أو ارفع صورة...',
    'freebuild.thinking': 'رُوح تحلل وتكتب...',
    'freebuild.send': 'إرسال',
    'freebuild.preview': 'المعاينة الحية',
    'freebuild.deploy': 'انشر على GitHub',
    'freebuild.locked': 'افتح GitHub Push (مدفوع)',
    'lang.picker.title': 'اختر لغتك',
    'lang.picker.search': 'ابحث عن لغة...',
    'lang.picker.empty': 'لا توجد لغات مطابقة',
  }},
  en: { translation: {
    'nav.home': 'Home',
    'nav.builder': 'Studio',
    'nav.games': 'Games',
    'nav.marketing': 'Marketing',
    'nav.apps': 'My Apps',
    'nav.deploy': 'Deploy',
    'nav.pricing': 'Pricing',
    'nav.login': 'Sign in',
    'nav.signup': 'Sign up',
    'nav.dashboard': 'Dashboard',
    'nav.logout': 'Logout',
    'common.send': 'Send',
    'common.cancel': 'Cancel',
    'common.save': 'Save',
    'common.delete': 'Delete',
    'common.edit': 'Edit',
    'common.loading': 'Loading...',
    'common.error': 'Something went wrong',
    'common.success': 'Done',
    'common.next': 'Next',
    'common.previous': 'Previous',
    'common.close': 'Close',
    'common.confirm': 'Confirm',
    'common.search': 'Search',
    'common.language': 'Language',
    'common.welcome': 'Welcome',
    'freebuild.title': 'Build your site from scratch',
    'freebuild.placeholder': 'Type, record voice, or upload image...',
    'freebuild.thinking': 'Roh is analyzing and writing...',
    'freebuild.send': 'Send',
    'freebuild.preview': 'Live Preview',
    'freebuild.deploy': 'Deploy to GitHub',
    'freebuild.locked': 'Unlock GitHub Push (premium)',
    'lang.picker.title': 'Choose your language',
    'lang.picker.search': 'Search a language...',
    'lang.picker.empty': 'No matching languages',
  }},
};

i18n.use(initReactI18next).init({
  resources,
  lng: localStorage.getItem('zitex_lang') || 'ar',
  fallbackLng: 'en',
  interpolation: { escapeValue: false },
  returnEmptyString: false,
});

// Apply <html dir="rtl|ltr"> & lang attribute on every change
function applyLangSideEffects(code) {
  try {
    document.documentElement.lang = code;
    document.documentElement.dir = isRTL(code) ? 'rtl' : 'ltr';
    localStorage.setItem('zitex_lang', code);
  } catch (_) { /* SSR-safe */ }
}
applyLangSideEffects(i18n.language);
i18n.on('languageChanged', applyLangSideEffects);

// On-demand machine translation — when a string isn't in our hand-curated
// resources, the UI can call this to translate via Claude and cache it
// in localStorage so it's instant next time. Caller passes the source text
// (Arabic or English) and gets back the target-language string.
export async function translateOnDemand(text, targetCode) {
  if (!text || !targetCode || targetCode === 'ar') return text;
  const cacheKey = `zitex_t_${targetCode}_${btoa(unescape(encodeURIComponent(text))).slice(0, 60)}`;
  const cached = localStorage.getItem(cacheKey);
  if (cached) return cached;
  try {
    const r = await fetch(`${process.env.REACT_APP_BACKEND_URL}/api/i18n/translate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text, target: targetCode }),
    });
    if (!r.ok) return text;
    const d = await r.json();
    if (d.translated) {
      localStorage.setItem(cacheKey, d.translated);
      return d.translated;
    }
  } catch (_) { /* keep source */ }
  return text;
}

export default i18n;
