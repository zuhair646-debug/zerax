/**
 * ConnectionHelpModal — hand-holds non-technical users through the process of
 * obtaining a credential/token from a third-party service.
 *
 * Each "guide" is a structured walkthrough with:
 *  - friendly intro
 *  - direct link to the official page
 *  - numbered steps with optional inline screenshots
 *  - common pitfalls
 *
 * Used by ConnectionsPanel and any other place that asks the user for an
 * API key, token, or external account credential.
 */
import React from 'react';
import { X, ExternalLink, CheckCircle2, AlertTriangle, Sparkles } from 'lucide-react';
import ZenrexBrand from './ZenrexBrand';

export const CONNECTION_GUIDES = {
  github: {
    title: 'GitHub Personal Access Token',
    icon: '🐙',
    intro:
      'لازم تعطي زنركس صلاحية يدفع كودك إلى مستودع باسمك. هذا التوكن يخلي كل عمليات Push آلية وما تحتاج تكتب كلمة سر كل مرة.',
    officialUrl: 'https://github.com/settings/personal-access-tokens/new',
    officialLabel: 'افتح صفحة إنشاء التوكن مباشرة',
    screenshot: 'https://docs.github.com/assets/cb-43094/mw-1440/images/help/personal_token/personal-access-tokens-page-with-new-fine-grained-token-button.webp',
    steps: [
      'افتح الرابط فوق — يطلب منك تسجيل دخول GitHub.',
      'اكتب اسم وصفي مثل: "Zenrex Deploy".',
      'في "Repository access" اختر: All repositories (أو حدد المستودعات اللي تبيها).',
      'في "Permissions" → Repository permissions، فعّل: Contents = Read & Write، Workflows = Read & Write، Metadata = Read.',
      'اضغط Generate token — يطلع لك توكن يبدأ بـ ghp_ أو github_pat_.',
      '⚠️ انسخه فوراً — لما تقفل الصفحة ما راح يبان مرة ثانية.',
      'ارجع لزنركس والصقه في الخانة وضغط احفظ.',
    ],
    pitfalls: [
      'لو نسيت تختار Workflows permission، النشر بـ GitHub Actions ما راح يشتغل.',
      'لو اخترت Fine-grained لكن المدة قصيرة (7 يوم)، التوكن يصير عديم النفع بعدها — اختر 90 يوم على الأقل.',
    ],
  },
  vercel: {
    title: 'Vercel API Token',
    icon: '▲',
    intro:
      'Vercel يستضيف موقعك بسرعة عالمية مجاناً. التوكن يخلي زنركس ينشر المشروع بدون ما تفتح Vercel يدوياً.',
    officialUrl: 'https://vercel.com/account/tokens',
    officialLabel: 'افتح صفحة Tokens في Vercel',
    screenshot: 'https://images.opengraph.tech/vercel/account-tokens-create.png',
    steps: [
      'سجّل دخول على Vercel (أنشئ حساب لو ما عندك — مجاني).',
      'افتح الرابط فوق → اضغط "Create Token".',
      'اكتب اسم: Zenrex Deploy. اختر Scope: Full Account.',
      'اختر Expiration: No expiration (أو سنة على الأقل).',
      'اضغط Create — يطلع التوكن مرة واحدة فقط.',
      'انسخه والصقه هنا.',
    ],
    pitfalls: [
      'لو حسابك تابع لـ Team، تأكد إنك تختار الـ Team الصحيح في Scope.',
      'التوكن يبدأ عادة بحروف عشوائية بدون prefix واضح — لا تخلط بينه وبين توكنات أخرى.',
    ],
  },
  cloudflare: {
    title: 'Cloudflare API Token',
    icon: '☁️',
    intro:
      'Cloudflare يدير الـDomain والـDNS والـCDN. التوكن يسمح لزنركس بضبط DNS records لربط دومينك بالموقع.',
    officialUrl: 'https://dash.cloudflare.com/profile/api-tokens',
    officialLabel: 'افتح صفحة API Tokens في Cloudflare',
    screenshot: 'https://developers.cloudflare.com/_astro/get-started.D0AhJg-9_Z1QzqLT.webp',
    steps: [
      'سجّل دخول Cloudflare (الحساب اللي عليه دومينك).',
      'افتح الرابط فوق → اضغط "Create Token".',
      'اختر القالب "Edit zone DNS" (أو Custom token بصلاحيات Zone:DNS:Edit).',
      'في Zone Resources، اختر دومينك المعين أو All zones.',
      'اضغط Continue ثم Create Token — انسخ التوكن مباشرة.',
      'الصق التوكن في زنركس.',
    ],
    pitfalls: [
      'تأكد إن الدومين فعلاً مضاف لحساب Cloudflare قبل ما تجرّب الربط.',
      'لو اخترت "Edit zone DNS" لكن الدومين على حساب آخر، الربط راح يرفض.',
    ],
  },
  domain: {
    title: 'دومين مخصص',
    icon: '🌐',
    intro:
      'الدومين هو اسم موقعك (مثل: myshop.com). لازم يكون مسجّل عندك من قبل في Namecheap أو GoDaddy أو Cloudflare Registrar.',
    officialUrl: 'https://www.namecheap.com/domains/',
    officialLabel: 'إذا ما عندك دومين، اشتر من Namecheap (الأرخص)',
    screenshot: null,
    steps: [
      'تأكد إن عندك دومين فعلي مسجّل باسمك.',
      'اكتبه هنا بدون https:// مثل: myshop.com (بدون www أيضاً).',
      'بعد الحفظ، زنركس راح يرشدك لإعداد DNS records في Cloudflare.',
    ],
    pitfalls: [
      'لا تكتب http:// أو https:// في الخانة.',
      'لا تكتب path مثل /home — الدومين فقط.',
    ],
  },
  stripe: {
    title: 'Stripe API Key',
    icon: '💳',
    intro:
      'Stripe يستقبل المدفوعات من بطاقات Visa/Mastercard. لازم يكون عندك حساب Stripe مفعّل (يحتاج سجل تجاري في السعودية).',
    officialUrl: 'https://dashboard.stripe.com/apikeys',
    officialLabel: 'افتح Dashboard → API Keys',
    screenshot: 'https://b.stripecdn.com/docs-statics-srv/assets/api-keys-developer-tab.7b9d5fcc8d5f2.png',
    steps: [
      'سجّل دخول على Dashboard Stripe.',
      'افتح الرابط فوق → ستجد قسم Standard Keys.',
      'انسخ Secret Key (يبدأ بـ sk_live_ في الإنتاج أو sk_test_ في الاختبار).',
      'الصقه في زنركس — لا تشاركه مع أحد آخر أبداً.',
    ],
    pitfalls: [
      'لا تستخدم Test Keys للإنتاج — العملاء الفعليين ما راح يقدرون يدفعون.',
      'فعّل حسابك Stripe بالكامل (هوية + بنك) قبل ما تربطه، وإلا المدفوعات ما تنزل لحسابك.',
    ],
  },
  brand_logo: {
    title: 'رفع شعار العلامة التجارية',
    icon: '🎨',
    intro:
      'الشعار هو هوية تطبيقك. يطلع في الـHeader، أيقونة الجوال (PWA)، والـfavicon. يفضل PNG شفافة بدقة 512×512.',
    officialUrl: 'https://www.canva.com/create/logos/',
    officialLabel: 'ما عندك شعار؟ صمّمه مجاناً في Canva',
    screenshot: null,
    steps: [
      'احضر صورة شعارك بصيغة PNG (أفضل) أو SVG أو JPG.',
      'الدقة الموصى بها: 512×512 بكسل بخلفية شفافة.',
      'الحد الأقصى للحجم: 5MB.',
      'اضغط زر الرفع تحت واختر الملف.',
    ],
    pitfalls: [
      'ملفات أكبر من 5MB راح ترفض — صغّر الحجم في موقع مثل tinypng.com.',
      'لو الشعار مربع غير متناسق، ممكن يتقصّ من الأيقونة المربعة.',
    ],
  },
};

export default function ConnectionHelpModal({ open, providerId, onClose }) {
  if (!open || !providerId) return null;
  const guide = CONNECTION_GUIDES[providerId];
  if (!guide) return null;

  return (
    <div
      className="fixed inset-0 z-[70] bg-black/85 backdrop-blur-md flex items-start sm:items-center justify-center p-3 sm:p-4 overflow-y-auto"
      onClick={onClose}
      data-testid={`help-modal-${providerId}`}
    >
      <div
        className="bg-zinc-900 border border-amber-500/40 rounded-2xl max-w-2xl w-full my-4 sm:my-8 shadow-2xl shadow-amber-500/10 max-h-[calc(100vh-2rem)] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="p-5 border-b border-white/10 flex items-start justify-between gap-3">
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-1">
              <ZenrexBrand size={18} />
              <span className="text-[10px] text-zinc-500">دليل تفصيلي</span>
            </div>
            <h3 className="text-xl font-black flex items-center gap-2 text-amber-200">
              <span className="text-2xl">{guide.icon}</span>
              <span>{guide.title}</span>
            </h3>
            <p className="text-xs text-zinc-400 mt-2 leading-relaxed">{guide.intro}</p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="text-zinc-400 hover:text-white p-2 rounded-lg hover:bg-white/5"
            data-testid="help-modal-close"
            aria-label="إغلاق"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="p-5 space-y-5">
          {/* Quick action button */}
          <a
            href={guide.officialUrl}
            target="_blank"
            rel="noreferrer"
            data-testid="help-official-link"
            className="block w-full text-center px-4 py-3 rounded-xl bg-gradient-to-r from-amber-500 to-yellow-500 hover:from-amber-400 hover:to-yellow-400 text-black font-black text-sm shadow-lg shadow-amber-500/20 transition"
          >
            <ExternalLink className="w-4 h-4 inline ml-1.5" />
            {guide.officialLabel}
          </a>

          {/* Screenshot */}
          {guide.screenshot && (
            <div className="rounded-xl overflow-hidden border border-white/10 bg-black/30">
              <img
                src={guide.screenshot}
                alt={`${guide.title} — لقطة من الموقع الرسمي`}
                className="w-full max-h-64 object-contain"
                loading="lazy"
                onError={(e) => { e.target.style.display = 'none'; }}
              />
              <p className="text-[10px] text-zinc-500 px-3 py-2 border-t border-white/5">
                ↑ شكل الصفحة على الموقع الرسمي (قد يتغيّر التصميم مع الوقت).
              </p>
            </div>
          )}

          {/* Numbered steps */}
          <div>
            <h4 className="text-sm font-bold text-emerald-300 mb-3 flex items-center gap-1.5">
              <Sparkles className="w-4 h-4" />
              <span>الخطوات بالتفصيل</span>
            </h4>
            <ol className="space-y-2.5">
              {guide.steps.map((s, i) => (
                <li
                  key={i}
                  className="flex gap-3 text-sm text-zinc-200 leading-relaxed"
                  data-testid={`help-step-${i + 1}`}
                >
                  <span className="flex-shrink-0 w-6 h-6 rounded-full bg-emerald-500/20 border border-emerald-400/40 text-emerald-300 text-xs font-black flex items-center justify-center">
                    {i + 1}
                  </span>
                  <span>{s}</span>
                </li>
              ))}
            </ol>
          </div>

          {/* Pitfalls */}
          {guide.pitfalls && guide.pitfalls.length > 0 && (
            <div className="rounded-xl border border-amber-500/30 bg-amber-500/5 p-4">
              <h4 className="text-sm font-bold text-amber-300 mb-2 flex items-center gap-1.5">
                <AlertTriangle className="w-4 h-4" />
                <span>انتبه — أخطاء شائعة</span>
              </h4>
              <ul className="space-y-1.5">
                {guide.pitfalls.map((p, i) => (
                  <li key={i} className="text-xs text-amber-100/85 leading-relaxed flex gap-2">
                    <span className="text-amber-400">•</span>
                    <span>{p}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Reassurance */}
          <div className="rounded-xl border border-emerald-500/20 bg-emerald-500/5 p-3 flex items-start gap-2.5">
            <CheckCircle2 className="w-4 h-4 text-emerald-400 mt-0.5 flex-shrink-0" />
            <p className="text-xs text-emerald-100/85 leading-relaxed">
              <strong>أمان كامل:</strong> كل التوكنات تتشفّر قبل الحفظ في قاعدة بياناتنا.
              مَن يدخل قاعدة البيانات ما يقدر يقرأها بدون مفتاح التشفير. وتقدر تلغي الربط
              في أي وقت من زر السلة بجنب الحالة.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
