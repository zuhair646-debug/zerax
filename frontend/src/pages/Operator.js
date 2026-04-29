import React, { useEffect, useMemo, useState, useRef } from 'react';
import { toast } from 'sonner';
import { DashboardView, MemoryTab, AlertsBell, SettingsPanel, ModernChatTab } from './OperatorParts';

const API = process.env.REACT_APP_BACKEND_URL;

/**
 * Operator (Agency Mode) — owner/developer-only multi-client management.
 * Route: /operator
 */
export default function Operator({ user }) {
  const [access, setAccess] = useState(null);
  const [clients, setClients] = useState([]);
  const [selected, setSelected] = useState(null);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [view, setView] = useState('dashboard'); // 'dashboard' | 'client'
  const [settingsOpen, setSettingsOpen] = useState(false);
  const token = useMemo(() => localStorage.getItem('token') || '', []);
  const H = useMemo(() => ({ Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' }), [token]);

  useEffect(() => {
    (async () => {
      try {
        const a = await fetch(`${API}/api/operator/access`, { headers: H }).then(r => r.json());
        setAccess(a);
        if (a.has_access) {
          const d = await fetch(`${API}/api/operator/clients`, { headers: H }).then(r => r.json());
          setClients(d.clients || []);
        }
      } catch (e) { /* ignore */ }
      setLoading(false);
    })();
  }, [H]);

  const reload = async () => {
    const d = await fetch(`${API}/api/operator/clients`, { headers: H }).then(r => r.json());
    setClients(d.clients || []);
    if (selected) {
      const fresh = (d.clients || []).find(c => c.id === selected.id);
      if (fresh) setSelected(fresh);
    }
  };

  const createClient = async (name) => {
    setCreating(true);
    try {
      const r = await fetch(`${API}/api/operator/clients`, { method: 'POST', headers: H, body: JSON.stringify({ name }) });
      const c = await r.json();
      if (!r.ok) throw new Error(c.detail || 'Failed');
      toast.success('✅ تم إنشاء العميل');
      await reload();
      setSelected(c);
    } catch (e) { toast.error(e.message); }
    setCreating(false);
  };

  if (loading) return <div className="min-h-screen bg-[#0a0b14] text-white flex items-center justify-center">⏳ تحميل...</div>;

  if (!access?.has_access) {
    return (
      <div className="min-h-screen bg-[#0a0b14] text-white flex items-center justify-center p-8">
        <div className="bg-red-500/10 border border-red-400/30 rounded-2xl p-8 text-center max-w-md">
          <div className="text-4xl mb-3">🔒</div>
          <div className="font-black text-lg mb-2">الوصول مقيّد</div>
          <div className="text-sm text-white/70">هذا القسم متاح لمالك المنصّة والمطوّرين المرخّصين فقط.</div>
          <a href="/" className="inline-block mt-4 px-5 py-2 bg-yellow-500 text-black rounded-lg font-black">العودة</a>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#0a0b14] text-white flex" dir="rtl" data-testid="operator-page">
      {/* Sidebar */}
      <aside className="w-80 border-l border-white/10 flex flex-col">
        <div className="p-4 border-b border-white/10">
          <div className="text-[10px] uppercase text-white/40 tracking-widest">Agency Mode</div>
          <h2 className="font-black text-lg mb-3">🧑‍💼 الوكالة</h2>
          <button
            onClick={() => { setView('dashboard'); setSelected(null); }}
            className={`w-full px-3 py-2 rounded-lg text-xs font-black mb-2 transition-colors ${view === 'dashboard' ? 'bg-emerald-500 text-black' : 'bg-white/10 hover:bg-white/20 text-white'}`}
            data-testid="dashboard-btn"
          >📊 لوحة التحكم</button>
          <button
            onClick={() => {
              const name = prompt('اسم العميل الجديد:');
              if (name && name.trim()) createClient(name.trim());
            }}
            disabled={creating}
            className="w-full px-3 py-2 bg-yellow-500 text-black rounded-lg font-black text-xs disabled:opacity-50"
            data-testid="new-client-btn"
          >+ عميل جديد</button>
        </div>
        <div className="px-4 pt-3 pb-1 text-[10px] uppercase text-white/40 tracking-widest">العملاء</div>
        <div className="flex-1 overflow-y-auto">
          {clients.length === 0 && <div className="p-6 text-xs text-white/50 text-center">لا عملاء بعد</div>}
          {clients.map((c) => (
            <button
              key={c.id}
              onClick={() => { setSelected(c); setView('client'); }}
              className={`w-full text-right p-4 border-b border-white/5 hover:bg-white/5 transition-colors ${view === 'client' && selected?.id === c.id ? 'bg-yellow-500/10 border-r-2 border-r-yellow-400' : ''}`}
              data-testid={`client-${c.id}`}
            >
              <div className="font-bold truncate">{c.name}</div>
              <div className="text-[10px] text-white/50 truncate">{c.client_email || '—'}</div>
              <div className="flex gap-1 mt-1.5">
                {c.github?.has_token && <span className="text-[9px] bg-white/10 px-1.5 py-0.5 rounded">GH</span>}
                {c.railway?.has_token && <span className="text-[9px] bg-purple-500/20 px-1.5 py-0.5 rounded">RW</span>}
                {c.vercel?.has_token && <span className="text-[9px] bg-black/50 border border-white/20 px-1.5 py-0.5 rounded">VC</span>}
                {c.mongo?.has_url && <span className="text-[9px] bg-emerald-500/20 px-1.5 py-0.5 rounded">DB</span>}
              </div>
            </button>
          ))}
        </div>
        <div className="p-3 border-t border-white/10 space-y-1">
          <AlertsBell H={H} />
          {user?.role === 'owner' && (
            <button onClick={() => setSettingsOpen(true)} className="w-full text-xs text-white/60 hover:text-white py-1 text-right px-2" data-testid="open-settings">
              ⚙️ الإعدادات
            </button>
          )}
          {user?.role === 'owner' && <DevelopersManager H={H} />}
          <a href="/" className="block text-center text-[11px] text-white/50 hover:text-white py-1">← الرئيسية</a>
        </div>
      </aside>

      {/* Main panel */}
      <main className="flex-1 overflow-y-auto">
        {view === 'dashboard' ? (
          <DashboardView H={H} onPick={(cid) => {
            const c = clients.find(x => x.id === cid);
            if (c) { setSelected(c); setView('client'); }
          }} />
        ) : selected ? (
          <ClientDetail client={selected} H={H} onChange={reload} onDelete={() => { setSelected(null); setView('dashboard'); reload(); }} />
        ) : (
          <div className="flex items-center justify-center h-full text-white/40 text-sm">اختر عميلاً من القائمة</div>
        )}
      </main>

      {settingsOpen && <SettingsPanel H={H} onClose={() => setSettingsOpen(false)} />}
    </div>
  );
}

// ─────────────────────────────────────────────────────
function DevelopersManager({ H }) {
  const [open, setOpen] = useState(false);
  const [list, setList] = useState([]);
  const [email, setEmail] = useState('');

  const load = async () => {
    const d = await fetch(`${API}/api/operator/developers`, { headers: H }).then(r => r.json());
    setList(d.developers || []);
  };
  useEffect(() => { if (open) load(); /* eslint-disable-next-line */ }, [open]);

  const add = async () => {
    if (!email.trim()) return;
    const r = await fetch(`${API}/api/operator/developers`, { method: 'POST', headers: H, body: JSON.stringify({ email: email.trim() }) });
    if (r.ok) { setEmail(''); load(); toast.success('تم الإضافة'); } else toast.error('فشل');
  };
  const remove = async (em) => {
    const r = await fetch(`${API}/api/operator/developers/${encodeURIComponent(em)}`, { method: 'DELETE', headers: H });
    if (r.ok) load();
  };

  return (
    <>
      <button onClick={() => setOpen(!open)} className="w-full text-xs text-white/60 hover:text-white py-1 text-right px-2" data-testid="toggle-devs">
        👥 المطوّرون ({list.length})
      </button>
      {open && (
        <div className="bg-white/5 rounded-lg p-3 space-y-2" data-testid="devs-panel">
          <div className="flex gap-1">
            <input value={email} onChange={e => setEmail(e.target.value)} placeholder="email" className="flex-1 text-xs px-2 py-1 bg-black/30 border border-white/10 rounded" />
            <button onClick={add} className="text-xs px-2 py-1 bg-yellow-500 text-black rounded font-bold">+</button>
          </div>
          {list.map((e) => (
            <div key={e} className="flex items-center justify-between text-xs text-white/80">
              <span className="truncate">{e}</span>
              <button onClick={() => remove(e)} className="text-red-400 hover:text-red-300 text-[10px]">حذف</button>
            </div>
          ))}
        </div>
      )}
    </>
  );
}

// ─────────────────────────────────────────────────────
function ClientDetail({ client, H, onChange, onDelete }) {
  const [tab, setTab] = useState('creds');
  const [saving, setSaving] = useState(false);
  const [logs, setLogs] = useState([]);

  const save = async (patch) => {
    setSaving(true);
    try {
      const r = await fetch(`${API}/api/operator/clients/${client.id}`, { method: 'PATCH', headers: H, body: JSON.stringify(patch) });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || 'Failed');
      toast.success('✅ تم الحفظ');
      onChange();
    } catch (e) { toast.error(e.message); }
    setSaving(false);
  };

  const act = async (url, body = null) => {
    const t = toast.loading('⏳ جاري التنفيذ...');
    try {
      const r = await fetch(`${API}/api/operator/clients/${client.id}${url}`, {
        method: 'POST', headers: H, body: body ? JSON.stringify(body) : undefined,
      });
      const d = await r.json();
      toast.dismiss(t);
      if (!r.ok) throw new Error(d.detail || 'Failed');
      toast.success('✅ نجحت العملية');
      return d;
    } catch (e) { toast.dismiss(t); toast.error(e.message); return null; }
  };

  const loadLogs = async () => {
    const d = await fetch(`${API}/api/operator/clients/${client.id}/actions/log`, { headers: H }).then(r => r.json());
    setLogs(d.entries || []);
  };
  useEffect(() => { if (tab === 'log') loadLogs(); /* eslint-disable-next-line */ }, [tab, client.id]);

  const del = async () => {
    if (!window.confirm(`حذف العميل "${client.name}" نهائياً؟`)) return;
    await fetch(`${API}/api/operator/clients/${client.id}`, { method: 'DELETE', headers: H });
    toast.success('تم الحذف');
    onDelete();
  };

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <div className="flex items-start justify-between mb-6">
        <div>
          <h1 className="text-2xl font-black">{client.name}</h1>
          <div className="text-xs text-white/50">{client.client_email || '—'} · أُنشئ {new Date(client.created_at).toLocaleDateString('ar-SA')}</div>
        </div>
        <button onClick={del} className="text-xs px-3 py-1.5 bg-red-500/20 hover:bg-red-500/40 text-red-300 rounded-lg" data-testid="delete-client">🗑️ حذف</button>
      </div>

      <div className="flex gap-1 mb-5 border-b border-white/10">
        {[
          { id: 'chat', label: '🤖 وكيل الـ AI' },
          { id: 'memory', label: '🧠 الذاكرة' },
          { id: 'creds', label: '🔐 الاعتمادات' },
          { id: 'actions', label: '⚡ الإجراءات' },
          { id: 'log', label: '📝 السجل' },
          { id: 'info', label: 'ℹ️ معلومات' },
        ].map(t => (
          <button key={t.id} onClick={() => setTab(t.id)}
            className={`px-4 py-2 text-sm font-bold transition-colors ${tab === t.id ? 'border-b-2 border-yellow-400 text-yellow-300' : 'text-white/60 hover:text-white'}`}
            data-testid={`tab-${t.id}`}>
            {t.label}
          </button>
        ))}
      </div>

      {tab === 'chat' && (
        <ModernChatTab client={client} H={H} />
      )}

      {tab === 'memory' && (
        <MemoryTab client={client} H={H} />
      )}

      {tab === 'info' && (
        <InfoTab client={client} save={save} saving={saving} />
      )}

      {tab === 'creds' && (
        <CredsTab client={client} save={save} saving={saving} />
      )}

      {tab === 'actions' && (
        <ActionsTab client={client} act={act} />
      )}

      {tab === 'log' && (
        <div className="space-y-2">
          {logs.length === 0 && <div className="text-white/40 text-sm text-center py-8">لا سجلات</div>}
          {logs.map((e, i) => (
            <div key={i} className={`flex items-center gap-3 p-3 rounded-lg text-sm ${e.ok ? 'bg-emerald-500/5 border border-emerald-500/20' : 'bg-red-500/5 border border-red-500/20'}`}>
              <span>{e.ok ? '✅' : '❌'}</span>
              <code className="font-mono text-xs">{e.action}</code>
              <span className="flex-1 text-xs text-white/60 truncate">{e.detail}</span>
              <span className="text-[10px] text-white/40">{new Date(e.at).toLocaleString('ar-SA')}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ─────────────────────────────────────────────────────
function InfoTab({ client, save, saving }) {
  const [name, setName] = useState(client.name);
  const [email, setEmail] = useState(client.client_email || '');
  const [notes, setNotes] = useState(client.notes || '');
  const [autoFix, setAutoFix] = useState(!!client.auto_fix_enabled);
  return (
    <div className="space-y-4 max-w-xl">
      <Field label="اسم العميل"><input value={name} onChange={e => setName(e.target.value)} className="inp" data-testid="info-name" /></Field>
      <Field label="بريد العميل"><input value={email} onChange={e => setEmail(e.target.value)} className="inp" data-testid="info-email" /></Field>
      <Field label="ملاحظات"><textarea rows={4} value={notes} onChange={e => setNotes(e.target.value)} className="inp" data-testid="info-notes" /></Field>

      {/* 🆕 Auto-fix mode */}
      <div className="bg-gradient-to-br from-violet-500/10 to-fuchsia-500/10 border border-violet-400/30 rounded-xl p-4">
        <div className="flex items-start justify-between gap-3">
          <div className="flex-1">
            <div className="font-black text-base flex items-center gap-2"><span>🤖</span> الإصلاح التلقائي (Auto-Fix)</div>
            <p className="text-xs text-white/65 mt-1 leading-relaxed">
              عند تفعيل هذه الميزة، سيقوم الوكيل تلقائياً بـ:
              <br />• اكتشاف فشل الـ deployment على Railway (كل 6 ساعات)
              <br />• قراءة السجلّات والملفات ذات الصلة
              <br />• تطبيق الإصلاح ودفعه إلى GitHub
              <br />• إعادة النشر والتأكّد من النجاح
              <br />• إرسال إشعار واتساب بالنتيجة
            </p>
          </div>
          <label className="cursor-pointer flex-shrink-0">
            <input type="checkbox" checked={autoFix} onChange={e => setAutoFix(e.target.checked)} className="sr-only" data-testid="autofix-toggle" />
            <div className={`w-12 h-6 rounded-full p-0.5 transition-colors ${autoFix ? 'bg-violet-500' : 'bg-white/15'}`}>
              <div className={`w-5 h-5 rounded-full bg-white transition-transform ${autoFix ? 'translate-x-6' : ''}`} />
            </div>
          </label>
        </div>
      </div>

      <button disabled={saving} onClick={() => save({ name, client_email: email, notes, auto_fix_enabled: autoFix })} className="btn-primary" data-testid="save-info">💾 حفظ</button>
    </div>
  );
}

// ─────────────────────────────────────────────────────
function CredsTab({ client, save, saving }) {
  return (
    <div className="space-y-5">
      <div className="bg-blue-500/5 border border-blue-500/20 rounded-xl p-3 text-xs text-white/70">
        🛡️ كل الرموز تُحفظ <b>مشفّرة (AES-128 + HMAC)</b>. لن نعرضها مرة أخرى بعد الحفظ — فقط آخر 4 أحرف للتأكيد.
      </div>
      <CredCard title="🐙 GitHub" accent="from-gray-600 to-gray-800">
        <GithubForm client={client} save={save} saving={saving} />
      </CredCard>
      <CredCard title="🚂 Railway" accent="from-purple-600 to-pink-600">
        <RailwayForm client={client} save={save} saving={saving} />
      </CredCard>
      <CredCard title="▲ Vercel" accent="from-neutral-700 to-black">
        <VercelForm client={client} save={save} saving={saving} />
      </CredCard>
      <CredCard title="🗄️ MongoDB" accent="from-emerald-600 to-teal-600">
        <MongoForm client={client} save={save} saving={saving} />
      </CredCard>
    </div>
  );
}

function CredCard({ title, accent, children }) {
  return (
    <div className={`bg-gradient-to-br ${accent} bg-opacity-10 rounded-xl p-5 border border-white/10`}>
      <h3 className="font-black mb-3 text-base">{title}</h3>
      {children}
    </div>
  );
}

function GithubForm({ client, save, saving }) {
  const g = client.github || {};
  const [repo, setRepo] = useState(g.repo || '');
  const [branch, setBranch] = useState(g.branch || 'main');
  const [token, setToken] = useState('');
  return (
    <div className="space-y-2">
      <Field label="Repo (user/repo)"><input value={repo} onChange={e => setRepo(e.target.value)} placeholder="zuhair646-debug/zitex" className="inp" data-testid="gh-repo" /></Field>
      <Field label="Branch"><input value={branch} onChange={e => setBranch(e.target.value)} className="inp" data-testid="gh-branch" /></Field>
      <Field label={`Token ${g.has_token ? `(محفوظ: ${g.token_mask})` : ''}`}>
        <input type="password" value={token} onChange={e => setToken(e.target.value)} placeholder={g.has_token ? 'اترك فارغاً للإبقاء' : 'ghp_...'} className="inp" data-testid="gh-token" />
      </Field>
      <div className="flex gap-2">
        <button disabled={saving} onClick={() => save({ github: { repo, branch, token: token || undefined } })} className="btn-primary" data-testid="save-gh">💾 حفظ</button>
        {g.has_token && <button disabled={saving} onClick={() => save({ github: { clear_token: true } })} className="btn-danger">مسح التوكن</button>}
      </div>
      <a href="https://github.com/settings/tokens?type=beta" target="_blank" rel="noopener" className="text-[11px] text-blue-300 hover:underline">إنشاء Fine-grained Token ↗</a>
    </div>
  );
}

function RailwayForm({ client, save, saving }) {
  const rw = client.railway || {};
  const [pid, setPid] = useState(rw.project_id || '');
  const [eid, setEid] = useState(rw.environment_id || '');
  const [sid, setSid] = useState(rw.service_id || '');
  const [token, setToken] = useState('');
  return (
    <div className="space-y-2">
      <div className="grid grid-cols-3 gap-2">
        <Field label="Project ID"><input value={pid} onChange={e => setPid(e.target.value)} className="inp" data-testid="rw-pid" /></Field>
        <Field label="Environment ID"><input value={eid} onChange={e => setEid(e.target.value)} className="inp" data-testid="rw-eid" /></Field>
        <Field label="Service ID"><input value={sid} onChange={e => setSid(e.target.value)} className="inp" data-testid="rw-sid" /></Field>
      </div>
      <Field label={`Token ${rw.has_token ? `(محفوظ: ${rw.token_mask})` : ''}`}>
        <input type="password" value={token} onChange={e => setToken(e.target.value)} placeholder={rw.has_token ? 'اترك فارغاً للإبقاء' : 'xxx-xxx-xxx'} className="inp" data-testid="rw-token" />
      </Field>
      <div className="flex gap-2">
        <button disabled={saving} onClick={() => save({ railway: { project_id: pid, environment_id: eid, service_id: sid, token: token || undefined } })} className="btn-primary" data-testid="save-rw">💾 حفظ</button>
        {rw.has_token && <button disabled={saving} onClick={() => save({ railway: { clear_token: true } })} className="btn-danger">مسح التوكن</button>}
      </div>
      <a href="https://railway.app/account/tokens" target="_blank" rel="noopener" className="text-[11px] text-pink-300 hover:underline">إنشاء Railway Token ↗</a>
    </div>
  );
}

function VercelForm({ client, save, saving }) {
  const v = client.vercel || {};
  const [pid, setPid] = useState(v.project_id || '');
  const [token, setToken] = useState('');
  return (
    <div className="space-y-2">
      <Field label="Project ID"><input value={pid} onChange={e => setPid(e.target.value)} className="inp" data-testid="vc-pid" /></Field>
      <Field label={`Token ${v.has_token ? `(محفوظ: ${v.token_mask})` : ''}`}>
        <input type="password" value={token} onChange={e => setToken(e.target.value)} placeholder={v.has_token ? 'اترك فارغاً للإبقاء' : 'vercel_...'} className="inp" data-testid="vc-token" />
      </Field>
      <div className="flex gap-2">
        <button disabled={saving} onClick={() => save({ vercel: { project_id: pid, token: token || undefined } })} className="btn-primary" data-testid="save-vc">💾 حفظ</button>
        {v.has_token && <button disabled={saving} onClick={() => save({ vercel: { clear_token: true } })} className="btn-danger">مسح التوكن</button>}
      </div>
      <a href="https://vercel.com/account/tokens" target="_blank" rel="noopener" className="text-[11px] text-white/60 hover:underline">إنشاء Vercel Token ↗</a>
    </div>
  );
}

function MongoForm({ client, save, saving }) {
  const m = client.mongo || {};
  const [db, setDb] = useState(m.db_name || '');
  const [url, setUrl] = useState('');
  return (
    <div className="space-y-2">
      <Field label="Database name"><input value={db} onChange={e => setDb(e.target.value)} className="inp" data-testid="mg-db" /></Field>
      <Field label={`Connection URL ${m.has_url ? `(محفوظ: ${m.url_mask})` : ''}`}>
        <input type="password" value={url} onChange={e => setUrl(e.target.value)} placeholder={m.has_url ? 'اترك فارغاً للإبقاء' : 'mongodb+srv://...'} className="inp" data-testid="mg-url" />
      </Field>
      <div className="flex gap-2">
        <button disabled={saving} onClick={() => save({ mongo: { db_name: db, url: url || undefined } })} className="btn-primary" data-testid="save-mg">💾 حفظ</button>
        {m.has_url && <button disabled={saving} onClick={() => save({ mongo: { clear_url: true } })} className="btn-danger">مسح</button>}
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────
function ActionsTab({ client, act }) {
  const [result, setResult] = useState(null);
  const run = async (fn) => { setResult(null); const r = await fn(); if (r) setResult(r); };

  return (
    <div className="space-y-4">
      <Section title="🐙 GitHub" available={client.github?.has_token}>
        <Btn onClick={() => run(() => act('/actions/github/test'))} data-testid="gh-test">اختبار الاتصال</Btn>
        <GithubPutForm act={act} />
      </Section>

      <Section title="🚂 Railway" available={client.railway?.has_token}>
        <Btn onClick={() => run(() => act('/actions/railway/test'))} data-testid="rw-test">اختبار Token</Btn>
        <Btn onClick={() => run(() => act('/actions/railway/latest'))} data-testid="rw-latest">آخر Deployment</Btn>
        <Btn variant="primary" onClick={() => run(() => act('/actions/railway/redeploy'))} data-testid="rw-redeploy">🚀 إعادة النشر</Btn>
        <RailwaySetEnv act={act} />
      </Section>

      <Section title="▲ Vercel" available={client.vercel?.has_token}>
        <Btn onClick={() => run(() => act('/actions/vercel/test'))} data-testid="vc-test">اختبار Token</Btn>
        <Btn variant="primary" onClick={() => run(() => act('/actions/vercel/redeploy'))} data-testid="vc-redeploy">🚀 إعادة النشر</Btn>
      </Section>

      {result && (
        <div className="mt-4 bg-black/60 border border-white/10 rounded-xl p-4">
          <div className="text-xs text-white/50 mb-2">النتيجة:</div>
          <pre className="text-[11px] text-emerald-300 font-mono overflow-auto max-h-80" data-testid="action-result">{JSON.stringify(result, null, 2)}</pre>
        </div>
      )}
    </div>
  );
}

function Section({ title, available, children }) {
  return (
    <div className="bg-white/[.03] border border-white/10 rounded-xl p-4">
      <div className="flex items-center justify-between mb-3">
        <h3 className="font-black">{title}</h3>
        {!available && <span className="text-[10px] bg-red-500/15 border border-red-500/30 px-2 py-0.5 rounded">لا Token</span>}
      </div>
      <div className={`flex gap-2 flex-wrap ${available ? '' : 'opacity-40 pointer-events-none'}`}>{children}</div>
    </div>
  );
}

function Btn({ onClick, children, variant = 'default', ...rest }) {
  const cls = variant === 'primary'
    ? 'px-4 py-2 bg-yellow-500 hover:bg-yellow-600 text-black font-black text-sm rounded-lg'
    : 'px-4 py-2 bg-white/10 hover:bg-white/20 font-bold text-sm rounded-lg';
  return <button onClick={onClick} className={cls} {...rest}>{children}</button>;
}

function GithubPutForm({ act }) {
  const [path, setPath] = useState('');
  const [content, setContent] = useState('');
  const [message, setMessage] = useState('');
  const submit = async () => {
    if (!path || !content) return toast.error('املأ المسار والمحتوى');
    await act('/actions/github/put-file', { path, content, message });
  };
  return (
    <details className="w-full mt-2">
      <summary className="cursor-pointer text-xs text-white/70 select-none">✏️ إنشاء/تعديل ملف في Repo</summary>
      <div className="space-y-2 mt-2">
        <input value={path} onChange={e => setPath(e.target.value)} placeholder="مسار الملف: backend/railway.toml" className="inp" data-testid="gh-put-path" />
        <textarea rows={5} value={content} onChange={e => setContent(e.target.value)} placeholder="محتوى الملف" className="inp font-mono text-xs" data-testid="gh-put-content" />
        <input value={message} onChange={e => setMessage(e.target.value)} placeholder="Commit message (اختياري)" className="inp" data-testid="gh-put-msg" />
        <Btn onClick={submit} variant="primary" data-testid="gh-put-submit">📤 ادفع الملف</Btn>
      </div>
    </details>
  );
}

function RailwaySetEnv({ act }) {
  const [name, setName] = useState('');
  const [value, setValue] = useState('');
  const submit = async () => {
    if (!name) return toast.error('اسم المتغير مطلوب');
    await act('/actions/railway/set-env', { name, value });
  };
  return (
    <details className="w-full mt-2">
      <summary className="cursor-pointer text-xs text-white/70 select-none">⚙️ إضافة/تحديث متغير بيئي</summary>
      <div className="flex gap-2 mt-2">
        <input value={name} onChange={e => setName(e.target.value)} placeholder="NAME" className="inp" data-testid="rw-env-name" />
        <input value={value} onChange={e => setValue(e.target.value)} placeholder="value" className="inp" data-testid="rw-env-value" />
        <Btn onClick={submit} data-testid="rw-env-submit">حفظ</Btn>
      </div>
    </details>
  );
}

function Field({ label, children }) {
  return (
    <label className="block">
      <div className="text-[11px] text-white/55 mb-1">{label}</div>
      {children}
    </label>
  );
}

// ─────────────────────────────────────────────────────────
// AI Agent Chat Tab
// ─────────────────────────────────────────────────────────
function ChatTab({ client, H }) {
  const [sessionId, setSessionId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const [sessions, setSessions] = useState([]);
  const listRef = useRef(null);

  const loadSessions = async () => {
    const d = await fetch(`${API}/api/operator/clients/${client.id}/chat/sessions`, { headers: H }).then(r => r.json());
    setSessions(d.sessions || []);
  };

  const loadSession = async (sid) => {
    setSessionId(sid);
    if (!sid) { setMessages([]); return; }
    const d = await fetch(`${API}/api/operator/clients/${client.id}/chat/${sid}`, { headers: H }).then(r => r.json());
    setMessages(d.messages || []);
  };

  useEffect(() => { loadSessions(); setSessionId(null); setMessages([]); /* eslint-disable-next-line */ }, [client.id]);
  useEffect(() => { if (listRef.current) listRef.current.scrollTop = listRef.current.scrollHeight; }, [messages, sending]);

  const send = async () => {
    const t = input.trim(); if (!t || sending) return;
    setInput('');
    setMessages(m => [...m, { role: 'user', text: t, at: new Date().toISOString() }]);
    setSending(true);
    try {
      const r = await fetch(`${API}/api/operator/clients/${client.id}/chat`, {
        method: 'POST', headers: H,
        body: JSON.stringify({ text: t, session_id: sessionId || undefined }),
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || 'Failed');
      if (!sessionId) { setSessionId(d.session_id); loadSessions(); }
      setMessages(m => [...m, { role: 'assistant', text: d.final, steps: d.steps, at: new Date().toISOString() }]);
    } catch (e) { toast.error(e.message); }
    setSending(false);
  };

  const delSession = async (sid) => {
    if (!window.confirm('حذف هذه الجلسة؟')) return;
    await fetch(`${API}/api/operator/clients/${client.id}/chat/${sid}`, { method: 'DELETE', headers: H });
    if (sid === sessionId) { setSessionId(null); setMessages([]); }
    loadSessions();
  };

  const suggestions = [
    '🔍 افحص حالة المشروع الحالية (context)',
    '🚨 افحص آخر deployment على Railway وقل لي إذا فشل',
    '📄 اقرأ ملف backend/railway.toml وأخبرني ماذا يحتوي',
    '🛠️ أصلح مشكلة PORT في railway.toml وأعد النشر',
    '🌐 أعد نشر Vercel للـ frontend',
  ];

  return (
    <div className="flex gap-4 h-[calc(100vh-220px)]">
      {/* Sessions sidebar */}
      <div className="w-56 flex-shrink-0 bg-white/[.02] border border-white/10 rounded-xl p-3 overflow-y-auto">
        <button
          onClick={() => { setSessionId(null); setMessages([]); }}
          className="w-full px-3 py-2 bg-emerald-500 text-black rounded-lg text-xs font-black mb-2"
          data-testid="new-chat"
        >+ محادثة جديدة</button>
        {sessions.length === 0 && <div className="text-[11px] text-white/40 text-center py-4">لا محادثات</div>}
        {sessions.map((s) => (
          <div key={s.session_id} className={`group flex items-center gap-1 mb-1 rounded-lg ${s.session_id === sessionId ? 'bg-emerald-500/15 border border-emerald-500/30' : 'hover:bg-white/5'}`}>
            <button onClick={() => loadSession(s.session_id)} className="flex-1 text-right p-2 text-xs truncate">
              <div className="truncate font-medium">{s.title || '(بدون عنوان)'}</div>
              <div className="text-[9px] text-white/40">{new Date(s.last_at).toLocaleString('ar-SA')} · {s.messages} رسالة</div>
            </button>
            <button onClick={() => delSession(s.session_id)} className="opacity-0 group-hover:opacity-100 text-red-400 text-xs px-1 transition-opacity">✕</button>
          </div>
        ))}
      </div>

      {/* Main chat */}
      <div className="flex-1 flex flex-col bg-white/[.02] border border-white/10 rounded-xl overflow-hidden">
        <div ref={listRef} className="flex-1 overflow-y-auto p-4 space-y-3" data-testid="chat-log">
          {messages.length === 0 && !sending && (
            <div className="py-6">
              <div className="text-center text-white/60 mb-5">
                <div className="text-4xl mb-2">🤖</div>
                <div className="font-black text-lg">Zitex DevOps Agent</div>
                <div className="text-xs mt-2">وكيل ذكي يصلح، ينشر، ويدير مشاريع العملاء تلقائياً</div>
              </div>
              <div className="max-w-md mx-auto space-y-2">
                <div className="text-[11px] text-white/50 text-center mb-2">جرّب:</div>
                {suggestions.map((s, i) => (
                  <button
                    key={i}
                    onClick={() => setInput(s)}
                    className="w-full text-right p-3 bg-white/5 hover:bg-white/10 border border-white/10 rounded-lg text-xs transition-colors"
                    data-testid={`suggest-${i}`}
                  >{s}</button>
                ))}
              </div>
            </div>
          )}
          {messages.map((m, i) => <MessageRow key={i} msg={m} />)}
          {sending && (
            <div className="flex items-center gap-2 text-xs text-white/60 p-3">
              <div className="animate-pulse">🤖</div>
              <span>الوكيل يفكّر ويستدعي الأدوات...</span>
            </div>
          )}
        </div>
        <div className="border-t border-white/10 p-3 flex gap-2">
          <textarea
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); }
            }}
            placeholder="اكتب ما تريد أن يفعله الوكيل... (Enter للإرسال، Shift+Enter لسطر جديد)"
            rows={2}
            className="flex-1 px-3 py-2 bg-black/40 border border-white/10 rounded-lg text-sm resize-none focus:border-emerald-400 outline-none"
            data-testid="chat-input"
          />
          <button
            onClick={send}
            disabled={sending || !input.trim()}
            className="px-5 py-2 bg-emerald-500 hover:bg-emerald-600 text-black font-black rounded-lg disabled:opacity-40"
            data-testid="chat-send"
          >{sending ? '⏳' : '📤 إرسال'}</button>
        </div>
      </div>
    </div>
  );
}

function MessageRow({ msg }) {
  if (msg.role === 'user') {
    return (
      <div className="flex justify-start">
        <div className="bg-yellow-500/15 border border-yellow-500/30 rounded-2xl rounded-tr-sm px-4 py-2.5 max-w-[80%] text-sm whitespace-pre-wrap" data-testid="msg-user">
          {msg.text}
        </div>
      </div>
    );
  }
  return (
    <div className="flex justify-end">
      <div className="flex-1 max-w-[90%]">
        {(msg.steps || []).filter(s => s.kind === 'tool').length > 0 && (
          <details className="mb-2">
            <summary className="cursor-pointer text-[10px] text-emerald-400 select-none hover:text-emerald-300">
              🔧 {msg.steps.filter(s => s.kind === 'tool').length} استدعاء أدوات — انقر للتفاصيل
            </summary>
            <div className="mt-2 space-y-1.5">
              {msg.steps.filter(s => s.kind === 'tool').map((s, i) => (
                <div key={i} className="bg-black/50 border border-white/10 rounded-lg p-2.5 text-[11px]">
                  {s.thought && <div className="text-white/60 italic mb-1">💭 {s.thought}</div>}
                  <div className="flex items-center gap-2 mb-1.5">
                    <code className={`font-mono font-bold ${s.result?.error ? 'text-red-300' : 'text-emerald-300'}`}>{s.tool}</code>
                    {s.args && Object.keys(s.args).length > 0 && (
                      <span className="text-white/40">({Object.keys(s.args).join(', ')})</span>
                    )}
                    {s.result?.error ? <span className="text-red-400">❌</span> : <span className="text-emerald-400">✅</span>}
                  </div>
                  <pre className="text-white/50 text-[10px] overflow-auto max-h-24 font-mono">{JSON.stringify(s.result, null, 2).slice(0, 500)}</pre>
                </div>
              ))}
            </div>
          </details>
        )}
        <div className="bg-emerald-500/10 border border-emerald-500/25 rounded-2xl rounded-tl-sm px-4 py-2.5 text-sm whitespace-pre-wrap" data-testid="msg-assistant">
          {msg.text}
        </div>
      </div>
    </div>
  );
}

// Global CSS classes (declared inline so file is self-contained)
const style = document.createElement('style');
style.textContent = `
  .inp { width: 100%; padding: 8px 12px; background: rgba(0,0,0,.3); border: 1px solid rgba(255,255,255,.1); border-radius: 8px; color: white; font-size: 13px; font-family: inherit; }
  .inp:focus { outline: none; border-color: rgba(234,179,8,.5); }
  .btn-primary { padding: 8px 16px; background: rgb(234,179,8); color: black; font-weight: 900; border-radius: 8px; font-size: 13px; transition: all .2s; }
  .btn-primary:hover:not(:disabled) { background: rgb(202,138,4); }
  .btn-primary:disabled { opacity: .5; cursor: not-allowed; }
  .btn-danger { padding: 8px 16px; background: rgba(239,68,68,.15); border: 1px solid rgba(239,68,68,.3); color: rgb(252,165,165); font-weight: 700; border-radius: 8px; font-size: 12px; }
  .btn-danger:hover:not(:disabled) { background: rgba(239,68,68,.25); }
`;
if (typeof document !== 'undefined' && !document.getElementById('operator-styles')) {
  style.id = 'operator-styles';
  document.head.appendChild(style);
}
