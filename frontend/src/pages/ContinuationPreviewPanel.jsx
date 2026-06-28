// ContinuationPreviewPanel.jsx — Visual "what did the AI do" panel.
// Tabs: Files browser | Snapshots (with restore) | Audit Log.
// Wired against the new /continuation/sandbox/* + /audit endpoints.

import React, { useEffect, useState, useCallback } from 'react';
import { toast } from 'sonner';
import {
  Folder, FileText, History, ShieldAlert, Loader2,
  RotateCcw, Eye, X, ChevronRight, CheckCircle2, Send,
} from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;

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

// ─── Files tab ───────────────────────────────────────────────────────
function FilesTab({ projectId }) {
  const [files, setFiles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState(null);
  const [content, setContent] = useState('');

  useEffect(() => {
    (async () => {
      setLoading(true);
      try {
        const r = await authedFetch(`${API}/api/freebuild-chat/project/${projectId}/continuation/sandbox/files`);
        const d = await r.json();
        setFiles(d.files || []);
      } catch { toast.error('فشل تحميل الملفات'); }
      finally { setLoading(false); }
    })();
  }, [projectId]);

  const openFile = async (path) => {
    setSelected(path); setContent('… جاري التحميل');
    try {
      const r = await authedFetch(`${API}/api/freebuild-chat/project/${projectId}/continuation/sandbox/file?path=${encodeURIComponent(path)}`);
      const d = await r.json();
      setContent(d.ok ? d.content : `⚠️ ${d.error}`);
    } catch { setContent('فشل القراءة'); }
  };

  if (loading) return <div className="py-10 flex justify-center"><Loader2 className="animate-spin text-fuchsia-300" /></div>;
  if (!files.length) return (
    <div data-testid="files-empty" className="py-12 text-center text-zinc-500 text-sm">
      <Folder className="w-10 h-10 mx-auto mb-2 opacity-40" />
      لا يوجد كود في الـ Sandbox بعد. اطلب من المهندس يستنسخ مستودعك أولاً.
    </div>
  );

  return (
    <div className="grid grid-cols-1 md:grid-cols-[1fr_2fr] gap-3">
      <div className="rounded-xl bg-black/30 border border-white/5 max-h-96 overflow-y-auto p-2" data-testid="files-tree">
        {files.map((f) => (
          <button
            key={f.path}
            onClick={() => f.type === 'file' && openFile(f.path)}
            data-testid={`file-row-${f.path.replace(/[^a-z0-9]/gi, '-')}`}
            className={`w-full text-right flex items-center gap-2 px-2 py-1.5 rounded text-[11px] font-mono hover:bg-white/5 ${selected === f.path ? 'bg-fuchsia-500/15 text-fuchsia-100' : 'text-zinc-300'}`}
          >
            {f.type === 'dir' ? <Folder className="w-3.5 h-3.5 text-amber-300/70 shrink-0" /> : <FileText className="w-3.5 h-3.5 text-blue-300/60 shrink-0" />}
            <span className="truncate">{f.path}</span>
            {f.size != null && <span className="text-[9px] text-zinc-500 mr-auto">{(f.size / 1024).toFixed(1)}KB</span>}
          </button>
        ))}
      </div>
      <div className="rounded-xl bg-black/50 border border-white/5 p-3 max-h-96 overflow-auto">
        {selected ? (
          <>
            <div className="flex items-center gap-2 mb-2 pb-2 border-b border-white/5">
              <Eye className="w-3.5 h-3.5 text-fuchsia-300" />
              <span className="text-[11px] font-mono text-fuchsia-200 truncate">{selected}</span>
            </div>
            <pre data-testid="file-content" className="text-[11px] text-zinc-200 font-mono whitespace-pre-wrap leading-relaxed">{content}</pre>
          </>
        ) : (
          <div className="h-full flex items-center justify-center text-zinc-500 text-sm">اختر ملفاً لمعاينته</div>
        )}
      </div>
    </div>
  );
}

// ─── Snapshots tab ────────────────────────────────────────────────────
function SnapshotsTab({ projectId, reloadSig }) {
  const [snaps, setSnaps] = useState([]);
  const [loading, setLoading] = useState(true);
  const [restoring, setRestoring] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const r = await authedFetch(`${API}/api/freebuild-chat/project/${projectId}/continuation/snapshots`);
      const d = await r.json();
      setSnaps(d.snapshots || []);
    } catch { toast.error('فشل تحميل النسخ'); }
    finally { setLoading(false); }
  }, [projectId]);

  useEffect(() => { load(); }, [load, reloadSig]);

  const restore = async (snap_id) => {
    if (!window.confirm(`استرجاع النسخة ${snap_id}؟ كل التعديلات الحالية بتنحذف من الـ Sandbox.`)) return;
    setRestoring(snap_id);
    try {
      const r = await authedFetch(`${API}/api/freebuild-chat/project/${projectId}/continuation/snapshots/restore`, {
        method: 'POST', body: JSON.stringify({ snapshot_id: snap_id }),
      });
      const d = await r.json();
      if (d.ok) { toast.success('✅ تم الاسترجاع'); load(); }
      else toast.error(d.error || 'فشل الاسترجاع');
    } finally { setRestoring(null); }
  };

  if (loading) return <div className="py-10 flex justify-center"><Loader2 className="animate-spin text-fuchsia-300" /></div>;
  if (!snaps.length) return (
    <div data-testid="snapshots-empty" className="py-12 text-center text-zinc-500 text-sm">
      <History className="w-10 h-10 mx-auto mb-2 opacity-40" />
      لا توجد نسخ احتياطية بعد. تُنشأ تلقائياً قبل أي تعديل.
    </div>
  );
  return (
    <div className="space-y-2" data-testid="snapshots-list">
      {snaps.map((s) => (
        <div key={s.snapshot_id} className="flex items-center gap-3 rounded-xl bg-black/30 border border-white/5 p-3 hover:bg-white/5">
          <div className="w-9 h-9 rounded-lg bg-amber-500/15 border border-amber-400/30 flex items-center justify-center shrink-0">
            <History className="w-4 h-4 text-amber-200" />
          </div>
          <div className="flex-1 min-w-0">
            <div className="text-[12px] font-mono text-zinc-100 truncate">{s.snapshot_id}</div>
            <div className="text-[10px] text-zinc-500">{new Date(s.created_at).toLocaleString('ar')} • {(s.size_bytes / 1024).toFixed(1)}KB</div>
          </div>
          <button
            onClick={() => restore(s.snapshot_id)}
            disabled={restoring === s.snapshot_id}
            data-testid={`restore-${s.snapshot_id}`}
            className="px-3 py-1.5 rounded-lg bg-amber-500/20 border border-amber-400/40 text-[11px] font-bold text-amber-100 hover:bg-amber-500/30 disabled:opacity-50 flex items-center gap-1"
          >
            {restoring === s.snapshot_id ? <Loader2 className="w-3 h-3 animate-spin" /> : <RotateCcw className="w-3 h-3" />}
            استرجع
          </button>
        </div>
      ))}
    </div>
  );
}

// ─── Audit tab ────────────────────────────────────────────────────────
function AuditTab({ projectId }) {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      setLoading(true);
      try {
        const r = await authedFetch(`${API}/api/freebuild-chat/project/${projectId}/continuation/audit?limit=200`);
        const d = await r.json();
        setLogs(d.logs || []);
      } catch { toast.error('فشل تحميل السجل'); }
      finally { setLoading(false); }
    })();
  }, [projectId]);

  if (loading) return <div className="py-10 flex justify-center"><Loader2 className="animate-spin text-fuchsia-300" /></div>;
  if (!logs.length) return (
    <div data-testid="audit-empty" className="py-12 text-center text-zinc-500 text-sm">
      <ShieldAlert className="w-10 h-10 mx-auto mb-2 opacity-40" />
      السجل القانوني فاضي. كل عملية AI تُسجَّل هنا تلقائياً.
    </div>
  );
  return (
    <div className="space-y-2" data-testid="audit-list">
      {logs.map((l) => (
        <div key={l.id} className="rounded-xl bg-black/30 border border-white/5 p-3 text-[11px]">
          <div className="flex items-center gap-2 mb-1">
            {l.success ? <CheckCircle2 className="w-3.5 h-3.5 text-emerald-300" /> : <X className="w-3.5 h-3.5 text-rose-300" />}
            <span className="font-bold text-zinc-100">{l.action}</span>
            {l.target_path && <span className="text-zinc-400 font-mono text-[10px] truncate">{l.target_path}</span>}
            <span className="mr-auto text-zinc-500 text-[10px]">{new Date(l.ts).toLocaleString('ar')}</span>
          </div>
          <div className="flex items-center gap-3 text-[10px] text-zinc-500">
            <span>IP: {l.ip || '—'}</span>
            <span className="font-mono">SHA: {l.signature_hash?.slice(0, 12)}…</span>
          </div>
        </div>
      ))}
    </div>
  );
}

// ─── Main panel ───────────────────────────────────────────────────────
export default function ContinuationPreviewPanel({ projectId, onClose }) {
  const [tab, setTab] = useState('files');
  const [reloadSig] = useState(0);
  const [deploying, setDeploying] = useState(false);
  const [prResult, setPrResult] = useState(null);

  const approveAndDeploy = async () => {
    const msg = window.prompt('وصف التغيير اللي تبي يكون في commit message:', 'تحديثات Zenrex AI');
    if (!msg) return;
    setDeploying(true);
    setPrResult(null);
    try {
      const r = await authedFetch(`${API}/api/freebuild-chat/project/${projectId}/continuation/sandbox/approve-and-deploy`, {
        method: 'POST',
        body: JSON.stringify({ commit_message: msg, branch_suffix: 'review' }),
      });
      const d = await r.json();
      if (!d.ok) { toast.error(d.error || 'فشل النشر'); setPrResult({ error: d.error }); return; }
      toast.success('✅ تم رفع التعديلات على فرع المراجعة');
      setPrResult(d);
    } catch (e) {
      toast.error('فشل النشر — راجع الشبكة');
    } finally { setDeploying(false); }
  };

  return (
    <div data-testid="continuation-preview-panel" dir="rtl" className="rounded-2xl border border-fuchsia-500/30 bg-gradient-to-br from-black via-fuchsia-950/30 to-black backdrop-blur p-4 sm:p-5 mb-4">
      <div className="flex items-center gap-3 mb-3 pb-3 border-b border-white/5">
        <Eye className="w-5 h-5 text-fuchsia-300" />
        <h3 className="text-sm font-black text-fuchsia-100">معاينة Sandbox + السجل</h3>
        <button
          onClick={approveAndDeploy}
          disabled={deploying}
          data-testid="approve-deploy-btn"
          className="mr-auto px-3 py-1.5 rounded-lg bg-gradient-to-r from-emerald-500 to-teal-500 hover:from-emerald-400 hover:to-teal-400 text-[11px] font-black text-white disabled:opacity-40 flex items-center gap-1.5"
          title="ارفع التعديلات على فرع مراجعة في GitHub"
        >
          {deploying ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Send className="w-3.5 h-3.5" />}
          اعتمد ونشر
        </button>
        {onClose && (
          <button onClick={onClose} data-testid="preview-close-btn" className="text-zinc-400 hover:text-fuchsia-300">
            <X className="w-4 h-4" />
          </button>
        )}
      </div>
      {/* PR result banner */}
      {prResult && prResult.ok && (
        <div data-testid="pr-result" className="mb-3 p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/30">
          <div className="flex items-start gap-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-300 shrink-0 mt-0.5" />
            <div className="flex-1 min-w-0">
              <div className="text-[11px] font-bold text-emerald-100 mb-1">تم رفع التعديلات على فرع: <code className="text-emerald-200">{prResult.branch}</code></div>
              <div className="text-[10px] text-emerald-300/80 mb-2">{prResult.instructions_ar}</div>
              {prResult.pr_url && (
                <a href={prResult.pr_url} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 text-[11px] font-bold px-3 py-1.5 rounded-lg bg-emerald-500/30 hover:bg-emerald-500/40 text-white">
                  افتح Pull Request في GitHub →
                </a>
              )}
            </div>
          </div>
        </div>
      )}
      <div className="flex gap-1 mb-3">
        {[
          { id: 'files', label: 'الكود المستنسخ', icon: Folder },
          { id: 'snapshots', label: 'النسخ الاحتياطية', icon: History },
          { id: 'audit', label: 'السجل القانوني', icon: ShieldAlert },
        ].map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            data-testid={`preview-tab-${t.id}`}
            className={`flex-1 px-3 py-2 rounded-lg text-[11px] font-bold transition flex items-center justify-center gap-1.5 ${tab === t.id ? 'bg-fuchsia-500/25 border border-fuchsia-400/50 text-fuchsia-100' : 'bg-black/30 border border-white/5 text-zinc-400 hover:bg-white/5'}`}
          >
            <t.icon className="w-3.5 h-3.5" />
            {t.label}
          </button>
        ))}
      </div>
      {tab === 'files' && <FilesTab projectId={projectId} />}
      {tab === 'snapshots' && <SnapshotsTab projectId={projectId} reloadSig={reloadSig} />}
      {tab === 'audit' && <AuditTab projectId={projectId} />}
    </div>
  );
}
