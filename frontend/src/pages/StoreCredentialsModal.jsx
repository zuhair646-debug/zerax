// StoreCredentialsModal.jsx — opens from inside the chat (after the
// onboarding wizard is done) so the customer can paste store/signing keys
// for actual publication: Google Play, App Store Connect, Firebase, TestFlight,
// Steam, itch.io, Amazon, Huawei, Microsoft + Android Keystore / iOS
// Provisioning Profile.
//
// AES-128 encrypted server-side via /credentials/save-extra. Revocable
// individually via DELETE /credentials/{key_name}. The AI uses these keys
// only when the user explicitly approves a store submission in the chat.

import React, { useEffect, useState } from 'react';
import { toast } from 'sonner';
import {
  X, Loader2, ShieldCheck, KeyRound, CheckCircle2, Trash2, Eye, EyeOff,
  Lock, Upload, AlertTriangle, Store, FileSignature,
} from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;
const cls = (...x) => x.filter(Boolean).join(' ');

async function authedFetch(url, opts = {}) {
  const token = localStorage.getItem('token');
  return fetch(url, {
    ...opts,
    headers: {
      'Content-Type': 'application/json',
      ...(opts.headers || {}),
      Authorization: `Bearer ${token}`,
    },
  });
}

// Determine the appropriate input type for each credential key.
function detectFieldType(keyName) {
  const k = keyName.toUpperCase();
  if (k.endsWith('_JSON') || k.includes('SERVICE_ACCOUNT')) return 'file_json';
  if (k.endsWith('_BASE64') || k.includes('KEYSTORE') || k.includes('PROVISIONING_PROFILE')) return 'file_binary';
  if (k.includes('PACKAGE_NAME') || k.includes('APP_ID') || k.includes('KEY_ID') ||
      k.includes('ISSUER_ID') || k.includes('USERNAME') || k.includes('ALIAS') ||
      k.includes('TENANT_ID') || k.includes('CLIENT_ID')) return 'text';
  return 'password';
}

// One credential row (shows mask if saved, input + save/revoke buttons).
function CredentialRow({ projectId, keyName, meta, category, onChanged }) {
  const [val, setVal] = useState('');
  const [show, setShow] = useState(false);
  const [busy, setBusy] = useState(false);
  const fieldType = detectFieldType(keyName);

  const handleFile = async (e) => {
    const f = e.target.files?.[0];
    if (!f) return;
    if (f.size > 5 * 1024 * 1024) { toast.error('الملف أكبر من 5MB'); return; }
    if (fieldType === 'file_json') {
      const txt = await f.text();
      try {
        JSON.parse(txt); // validate
        setVal(txt);
        toast.success(`✓ ${f.name} (${(f.size / 1024).toFixed(1)} KB) جاهز للحفظ`);
      } catch {
        toast.error('الملف ليس JSON صالح');
      }
    } else {
      // file_binary → base64
      const buf = await f.arrayBuffer();
      const bytes = new Uint8Array(buf);
      let bin = '';
      for (let i = 0; i < bytes.length; i++) bin += String.fromCharCode(bytes[i]);
      const b64 = btoa(bin);
      setVal(b64);
      toast.success(`✓ ${f.name} → base64 (${(b64.length / 1024).toFixed(1)} KB)`);
    }
  };

  const save = async () => {
    if (val.trim().length < 4) { toast.error('قيمة قصيرة جداً'); return; }
    setBusy(true);
    try {
      const r = await authedFetch(`${API}/api/freebuild-chat/project/${projectId}/continuation/credentials/save-extra`, {
        method: 'POST',
        body: JSON.stringify({ key_name: keyName, value: val.trim(), validity_months: 12, category }),
      });
      const d = await r.json();
      if (!d.ok) throw new Error(d.detail || 'save failed');
      toast.success('🔐 محفوظ بتشفير AES-128');
      setVal('');
      onChanged && onChanged();
    } catch (e) {
      toast.error('فشل الحفظ: ' + (e.message || ''));
    } finally {
      setBusy(false);
    }
  };

  const revoke = async () => {
    if (!window.confirm(`حذف ${keyName} نهائياً؟ هذا الإجراء غير قابل للتراجع.`)) return;
    setBusy(true);
    try {
      const r = await authedFetch(`${API}/api/freebuild-chat/project/${projectId}/continuation/credentials/${encodeURIComponent(keyName)}`, {
        method: 'DELETE',
      });
      const d = await r.json();
      if (!d.ok) throw new Error();
      toast.success('🗑️ حُذف');
      onChanged && onChanged();
    } catch {
      toast.error('فشل الحذف');
    } finally {
      setBusy(false);
    }
  };

  const isSaved = !!meta;

  return (
    <div data-testid={`cred-row-${keyName}`} className="rounded-lg bg-black/30 border border-white/10 p-3">
      <div className="flex items-center justify-between mb-2 gap-2">
        <div className="flex items-center gap-2 min-w-0">
          <KeyRound className={cls('w-3.5 h-3.5 flex-shrink-0', isSaved ? 'text-emerald-300' : 'text-zinc-500')} />
          <code className="text-[11px] font-mono font-bold text-zinc-200 truncate">{keyName}</code>
        </div>
        {isSaved && (
          <button
            onClick={revoke}
            disabled={busy}
            data-testid={`cred-revoke-${keyName}`}
            className="text-[10px] px-2 py-0.5 rounded text-rose-300 hover:bg-rose-500/10 border border-rose-500/30 flex items-center gap-1"
          >
            <Trash2 className="w-3 h-3" /> حذف
          </button>
        )}
      </div>

      {isSaved ? (
        <div className="flex items-center gap-2 text-[10px] text-emerald-200">
          <CheckCircle2 className="w-3.5 h-3.5" />
          <span className="font-mono">{meta.mask}</span>
          <span className="text-zinc-500 ml-auto">صالح حتى: {new Date(meta.expires_at).toLocaleDateString('ar-SA')}</span>
        </div>
      ) : (
        <div className="space-y-2">
          {fieldType === 'file_json' || fieldType === 'file_binary' ? (
            <label className="flex items-center gap-2 px-3 py-2 rounded-lg bg-amber-500/5 border border-dashed border-amber-500/30 cursor-pointer hover:bg-amber-500/10 text-[11px] text-amber-100">
              <Upload className="w-3.5 h-3.5" />
              <span>{val ? `جاهز (${(val.length / 1024).toFixed(1)} KB)` : 'اختر ملف...'}</span>
              <input
                type="file"
                accept={fieldType === 'file_json' ? '.json' : undefined}
                onChange={handleFile}
                data-testid={`cred-file-${keyName}`}
                className="hidden"
              />
            </label>
          ) : (
            <div className="relative">
              <input
                type={fieldType === 'password' && !show ? 'password' : 'text'}
                value={val}
                onChange={(e) => setVal(e.target.value)}
                placeholder={`الصق ${keyName}`}
                data-testid={`cred-input-${keyName}`}
                className="w-full px-3 py-2 pl-9 rounded-lg bg-black/50 border border-white/10 text-xs font-mono focus:border-cyan-400/50 focus:outline-none"
              />
              {fieldType === 'password' && (
                <button
                  type="button"
                  onClick={() => setShow((s) => !s)}
                  className="absolute left-2 top-1/2 -translate-y-1/2 text-zinc-500 hover:text-zinc-300"
                >
                  {show ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
                </button>
              )}
            </div>
          )}
          <button
            onClick={save}
            disabled={busy || val.trim().length < 4}
            data-testid={`cred-save-${keyName}`}
            className="w-full py-1.5 rounded-lg bg-cyan-500/20 hover:bg-cyan-500/30 border border-cyan-400/30 text-[11px] font-bold text-cyan-100 disabled:opacity-40 flex items-center justify-center gap-1.5"
          >
            {busy ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Lock className="w-3.5 h-3.5" />}
            احفظ مشفّر
          </button>
        </div>
      )}
    </div>
  );
}

// Single provider section: header + list of credential rows.
function ProviderSection({ projectId, provider, category, savedMeta, onChanged }) {
  const keys = provider.credential_keys || [];
  const savedCount = keys.filter((k) => savedMeta[k]).length;

  return (
    <div data-testid={`store-section-${provider.id}`} className="rounded-xl bg-zinc-950/40 border border-white/10 p-4">
      <div className="flex items-center gap-3 mb-3">
        <div className="text-2xl">{provider.logo_emoji}</div>
        <div className="flex-1">
          <h4 className="text-sm font-black text-zinc-100">{provider.label_ar}</h4>
          {provider.label_en && <p className="text-[10px] text-zinc-500">{provider.label_en}</p>}
        </div>
        {savedCount > 0 && (
          <span className="text-[10px] px-2 py-0.5 rounded-full bg-emerald-500/15 border border-emerald-500/30 text-emerald-200 font-bold">
            {savedCount}/{keys.length} ✓
          </span>
        )}
      </div>
      {provider.instructions_ar && (
        <details className="mb-3">
          <summary className="text-[10px] text-cyan-300 cursor-pointer hover:text-cyan-100">📖 كيف أحصل على المفاتيح؟</summary>
          <pre className="mt-2 p-2 rounded bg-black/40 text-[10px] text-zinc-300 leading-relaxed whitespace-pre-wrap font-sans">
            {provider.instructions_ar}
          </pre>
          {provider.where_to_get_url && (
            <a href={provider.where_to_get_url} target="_blank" rel="noopener noreferrer" className="mt-1 inline-block text-[10px] text-cyan-300 hover:text-cyan-100 underline">
              افتح صفحة الإنشاء ↗
            </a>
          )}
        </details>
      )}
      <div className="space-y-2">
        {keys.map((k) => (
          <CredentialRow
            key={k}
            projectId={projectId}
            keyName={k}
            meta={savedMeta[k]}
            category={category}
            onChanged={onChanged}
          />
        ))}
      </div>
    </div>
  );
}

// ─── Modal ─────────────────────────────────────────────────────────────
export default function StoreCredentialsModal({ projectId, onClose, appKind }) {
  const [tab, setTab] = useState('stores'); // 'stores' | 'signing'
  const [catalog, setCatalog] = useState(null);
  const [savedMeta, setSavedMeta] = useState({});
  const [loading, setLoading] = useState(true);
  const [reloadKey, setReloadKey] = useState(0);

  const reload = async () => {
    try {
      const [cat, meta] = await Promise.all([
        fetch(`${API}/api/freebuild-chat/continuation/store-providers-catalog`).then((r) => r.json()),
        authedFetch(`${API}/api/freebuild-chat/project/${projectId}/continuation/credentials/meta`).then((r) => r.json()),
      ]);
      setCatalog(cat);
      setSavedMeta(meta.credentials_meta || {});
    } catch {
      toast.error('فشل تحميل البيانات');
    } finally {
      setLoading(false);
    }
  };

  // intentionally only re-fetch on project change; reload is stable
  useEffect(() => { reload(); }, [projectId, reloadKey]);

  // Smart filter: recommend platforms relevant to the app kind.
  const filterByAppKind = (providers) => {
    if (!appKind) return providers;
    const k = String(appKind).toLowerCase();
    if (k.includes('ios') || k === 'swift') {
      return providers.filter((p) => ['app_store_connect', 'testflight', 'firebase_distribution'].includes(p.id));
    }
    if (k.includes('android') || k === 'kotlin') {
      return providers.filter((p) => ['google_play', 'firebase_distribution', 'amazon_appstore', 'huawei_appgallery'].includes(p.id));
    }
    if (k.includes('unity') || k.includes('game')) {
      return providers.filter((p) => ['steam', 'itch_io', 'google_play', 'app_store_connect'].includes(p.id));
    }
    if (k.includes('electron') || k.includes('tauri')) {
      return providers.filter((p) => ['microsoft_store', 'steam', 'itch_io'].includes(p.id));
    }
    return providers;
  };

  return (
    <div
      data-testid="store-credentials-modal"
      className="fixed inset-0 z-50 bg-black/85 backdrop-blur-sm flex items-center justify-center p-3 sm:p-6"
      onClick={onClose}
    >
      <div
        dir="rtl"
        onClick={(e) => e.stopPropagation()}
        className="w-full max-w-4xl max-h-[92vh] overflow-y-auto rounded-2xl bg-gradient-to-br from-zinc-950 via-fuchsia-950/30 to-black border border-cyan-500/30 shadow-2xl"
      >
        {/* Header */}
        <div className="sticky top-0 z-10 bg-zinc-950/95 backdrop-blur border-b border-white/10 px-5 py-4 flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-cyan-500/20 border border-cyan-400/40 flex items-center justify-center flex-shrink-0">
            <Store className="w-5 h-5 text-cyan-200" />
          </div>
          <div className="flex-1 min-w-0">
            <h2 className="text-base sm:text-lg font-black text-cyan-100">إعدادات النشر للمتاجر</h2>
            <p className="text-[11px] text-zinc-400 mt-0.5">
              مفاتيح Google Play / App Store / Firebase / Signing — يستخدمها المهندس فقط لما توافق على النشر.
            </p>
          </div>
          <button
            onClick={onClose}
            data-testid="store-modal-close"
            className="p-2 rounded-lg hover:bg-white/5 text-zinc-400 hover:text-zinc-100"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Security banner */}
        <div className="mx-5 mt-4 rounded-xl bg-amber-500/10 border border-amber-500/30 p-3 flex items-start gap-2.5">
          <ShieldCheck className="w-4 h-4 text-amber-300 flex-shrink-0 mt-0.5" />
          <div className="text-[11px] text-amber-100 leading-relaxed">
            🔒 كل قيمة تحفظها هنا تُشفّر بـ AES-128 على سيرفرنا ولا تُكشف لأي إنسان. الذكاء يستخدمها <strong>مرة واحدة فقط</strong> لما توافق صراحة على نشر بإصدار جديد، وأي إصدار يبدأ على <code className="font-mono bg-black/40 px-1 rounded">Track Internal / TestFlight</code> أولاً.
          </div>
        </div>

        {/* Tabs */}
        <div className="px-5 mt-4 flex gap-2 border-b border-white/10">
          <button
            onClick={() => setTab('stores')}
            data-testid="store-tab-stores"
            className={cls(
              'px-4 py-2 text-[12px] font-bold border-b-2 -mb-px transition flex items-center gap-1.5',
              tab === 'stores' ? 'border-cyan-400 text-cyan-100' : 'border-transparent text-zinc-400 hover:text-zinc-200',
            )}
          >
            <Store className="w-3.5 h-3.5" /> منصات النشر
          </button>
          <button
            onClick={() => setTab('signing')}
            data-testid="store-tab-signing"
            className={cls(
              'px-4 py-2 text-[12px] font-bold border-b-2 -mb-px transition flex items-center gap-1.5',
              tab === 'signing' ? 'border-fuchsia-400 text-fuchsia-100' : 'border-transparent text-zinc-400 hover:text-zinc-200',
            )}
          >
            <FileSignature className="w-3.5 h-3.5" /> مفاتيح التوقيع
          </button>
        </div>

        {/* Body */}
        <div className="p-5 space-y-3">
          {loading ? (
            <div className="py-12 flex justify-center">
              <Loader2 className="w-6 h-6 animate-spin text-cyan-300" />
            </div>
          ) : tab === 'stores' ? (
            <>
              {appKind && (
                <p className="text-[10px] text-cyan-300/80 mb-2 flex items-center gap-1.5">
                  <AlertTriangle className="w-3 h-3" />
                  عرضنا المتاجر المناسبة لتطبيق <strong>{appKind}</strong>. لو تبي تشوف الكل، الذكاء يقدر يضيفها من الشات.
                </p>
              )}
              {filterByAppKind(catalog?.store_providers || []).map((p) => (
                <ProviderSection
                  key={p.id}
                  projectId={projectId}
                  provider={p}
                  category="store"
                  savedMeta={savedMeta}
                  onChanged={() => setReloadKey((k) => k + 1)}
                />
              ))}
            </>
          ) : (
            (catalog?.signing_providers || []).map((p) => (
              <ProviderSection
                key={p.id}
                projectId={projectId}
                provider={p}
                category="signing"
                savedMeta={savedMeta}
                onChanged={() => setReloadKey((k) => k + 1)}
              />
            ))
          )}
        </div>
      </div>
    </div>
  );
}
