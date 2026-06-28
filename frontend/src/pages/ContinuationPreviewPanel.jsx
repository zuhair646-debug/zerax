// ContinuationPreviewPanel.jsx — Visual "what did the AI do" panel.
// Tabs: Files browser | Snapshots (with restore) | Audit Log.
// Wired against the new /continuation/sandbox/* + /audit endpoints.

import React, { useEffect, useState, useCallback } from 'react';
import { toast } from 'sonner';
import {
  Folder, FileText, History, ShieldAlert, Loader2,
  RotateCcw, Eye, X, ChevronRight, CheckCircle2, Send, Rocket, AlertTriangle,
  Smartphone, Apple, QrCode, Hammer,
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

// ─── Phone Preview tab (apps only) ────────────────────────────────────
function PhonePreviewTab({ projectId }) {
  const [frame, setFrame] = useState('ios'); // 'ios' | 'android'
  const [buildInfo, setBuildInfo] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      try {
        const r = await authedFetch(`${API}/api/freebuild-chat/project/${projectId}`);
        const d = await r.json();
        if (cancelled) return;
        setBuildInfo({
          last_build: d.continuation_last_build || null,
          preview_url: d.preview_url || null,
          expo_url: d.continuation_expo_url || null,
          artifact_url: d.continuation_artifact_url || null,
          app_kind: d.app_kind,
        });
      } catch { /* ignore */ }
      finally { if (!cancelled) setLoading(false); }
    };
    load();
    // Poll every 8s so live build progress shows up without manual refresh.
    const id = setInterval(load, 8000);
    return () => { cancelled = true; clearInterval(id); };
  }, [projectId]);

  if (loading) {
    return <div className="py-10 flex justify-center"><Loader2 className="animate-spin text-cyan-300" /></div>;
  }

  const hasPreview = buildInfo?.preview_url || buildInfo?.expo_url;
  const qrTarget = buildInfo?.expo_url || buildInfo?.artifact_url || buildInfo?.preview_url;
  const qrSrc = qrTarget
    ? `https://api.qrserver.com/v1/create-qr-code/?size=220x220&margin=10&data=${encodeURIComponent(qrTarget)}`
    : null;

  return (
    <div data-testid="phone-preview-tab" className="space-y-4">
      {/* Frame toggle */}
      <div className="flex items-center justify-center gap-2">
        <button
          onClick={() => setFrame('ios')}
          data-testid="frame-ios-btn"
          className={`px-3 py-1.5 rounded-lg text-[11px] font-bold border flex items-center gap-1.5 transition ${frame === 'ios' ? 'bg-zinc-500/30 border-zinc-300 text-white' : 'bg-black/30 border-white/10 text-zinc-400 hover:bg-white/5'}`}
        >
          <Apple className="w-3.5 h-3.5" /> iOS
        </button>
        <button
          onClick={() => setFrame('android')}
          data-testid="frame-android-btn"
          className={`px-3 py-1.5 rounded-lg text-[11px] font-bold border flex items-center gap-1.5 transition ${frame === 'android' ? 'bg-emerald-500/30 border-emerald-400 text-white' : 'bg-black/30 border-white/10 text-zinc-400 hover:bg-white/5'}`}
        >
          <Smartphone className="w-3.5 h-3.5" /> Android
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-[1fr_280px] gap-4">
        {/* Phone frame */}
        <div className="flex justify-center">
          <div
            data-testid="phone-frame"
            className={`relative ${frame === 'ios' ? 'rounded-[2.5rem]' : 'rounded-[1.5rem]'} bg-zinc-950 border-4 ${frame === 'ios' ? 'border-zinc-800' : 'border-zinc-700'} shadow-2xl shadow-cyan-500/10 overflow-hidden`}
            style={{ width: 280, height: 580 }}
          >
            {/* Notch / Status bar */}
            {frame === 'ios' && (
              <div className="absolute top-2 left-1/2 -translate-x-1/2 w-32 h-6 rounded-full bg-zinc-900 z-10" />
            )}
            {frame === 'android' && (
              <div className="absolute top-0 left-0 right-0 h-5 bg-zinc-900 z-10 flex items-center justify-end px-3">
                <span className="text-[8px] text-zinc-500 font-mono">100%</span>
              </div>
            )}
            {/* Screen */}
            <div className="absolute inset-0 mt-7 mb-2 mx-1 rounded-lg overflow-hidden bg-zinc-950">
              {hasPreview ? (
                <iframe
                  src={buildInfo.preview_url || buildInfo.expo_url}
                  title="App Preview"
                  data-testid="phone-preview-iframe"
                  className="w-full h-full border-0"
                  sandbox="allow-scripts allow-same-origin allow-popups"
                />
              ) : (
                <div className="w-full h-full flex flex-col items-center justify-center text-center px-4 text-zinc-500">
                  <Smartphone className="w-12 h-12 mb-3 opacity-40" />
                  <div className="text-[11px] font-bold text-zinc-400 mb-2">لا توجد نسخة بناء بعد</div>
                  <div className="text-[10px] text-zinc-600 leading-relaxed">
                    اطلب من المهندس في الشات:<br/>
                    <code className="text-cyan-400 font-mono">&quot;ابني التطبيق وارفعه على Expo Go&quot;</code>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* QR + Build Status */}
        <div className="space-y-3">
          <div data-testid="qr-card" className="rounded-xl bg-black/40 border border-cyan-500/20 p-4 flex flex-col items-center">
            <div className="text-[10px] font-black text-cyan-300 mb-2 flex items-center gap-1.5">
              <QrCode className="w-3.5 h-3.5" /> امسح للاختبار على جوالك
            </div>
            {qrSrc ? (
              <>
                <img src={qrSrc} alt="QR" data-testid="qr-image" className="w-44 h-44 rounded-lg bg-white p-2" />
                <div className="text-[10px] text-cyan-200 mt-2 font-mono truncate w-full text-center">{qrTarget}</div>
              </>
            ) : (
              <div className="w-44 h-44 rounded-lg bg-zinc-900 border border-dashed border-white/10 flex items-center justify-center text-[10px] text-zinc-500 text-center p-4">
                ينتظر أول بناء ناجح
              </div>
            )}
          </div>

          <div data-testid="build-status-card" className="rounded-xl bg-black/40 border border-fuchsia-500/20 p-4">
            <div className="text-[10px] font-black text-fuchsia-300 mb-2 flex items-center gap-1.5">
              <Hammer className="w-3.5 h-3.5" /> آخر بناء
            </div>
            {buildInfo?.last_build ? (
              <div className="space-y-2 text-[11px]">
                <div className="flex justify-between">
                  <span className="text-zinc-500">الحالة:</span>
                  <span className={`font-bold ${
                    buildInfo.last_build.status === 'success' ? 'text-emerald-300'
                    : buildInfo.last_build.status === 'failed' ? 'text-rose-300'
                    : 'text-amber-300'
                  }`}>
                    {buildInfo.last_build.status || 'pending'}
                  </span>
                </div>
                {buildInfo.last_build.platform && (
                  <div className="flex justify-between">
                    <span className="text-zinc-500">المنصة:</span>
                    <span className="text-zinc-200">{buildInfo.last_build.platform}</span>
                  </div>
                )}
                {buildInfo.last_build.started_at && (
                  <div className="flex justify-between">
                    <span className="text-zinc-500">بدأ:</span>
                    <span className="text-zinc-400 text-[10px]">{new Date(buildInfo.last_build.started_at).toLocaleString('ar-SA')}</span>
                  </div>
                )}
                {buildInfo.last_build.logs_tail && (
                  <details className="mt-2">
                    <summary className="text-[10px] text-zinc-400 cursor-pointer hover:text-fuchsia-300">سجل البناء</summary>
                    <pre data-testid="build-logs" className="mt-2 text-[9px] text-zinc-300 bg-black/60 rounded p-2 max-h-32 overflow-auto whitespace-pre-wrap font-mono">
                      {buildInfo.last_build.logs_tail}
                    </pre>
                  </details>
                )}
              </div>
            ) : (
              <div className="text-[10px] text-zinc-500 leading-relaxed">
                ما في بناء حتى الآن. أطلب من المهندس في الشات يستخدم أداة <code className="text-fuchsia-300 font-mono">build_app</code>.
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

// ─── Main panel ───────────────────────────────────────────────────────
export default function ContinuationPreviewPanel({ projectId, onClose, projectKind }) {
  const [tab, setTab] = useState(projectKind === 'app' ? 'phone' : 'files');
  const [reloadSig] = useState(0);
  const [deploying, setDeploying] = useState(false);
  const [prResult, setPrResult] = useState(null);

  // ─── Direct Deploy state ────────────────────────────────────────────
  const [showDirect, setShowDirect] = useState(false);
  const [directLoading, setDirectLoading] = useState(false);
  const [directResult, setDirectResult] = useState(null);
  const [deployTarget, setDeployTarget] = useState({
    target_dir: '', source_subdir: 'repo', post_deploy_command: '',
  });
  const [transport, setTransport] = useState('ssh'); // 'ssh' | 'ftp'
  const [hasSsh, setHasSsh] = useState(false);
  const [hasFtp, setHasFtp] = useState(false);
  const [confirmText, setConfirmText] = useState('');

  // Pre-fill the modal with any previously saved config
  useEffect(() => {
    if (!showDirect) return;
    (async () => {
      try {
        const r = await authedFetch(`${API}/api/freebuild-chat/project/${projectId}/continuation/deploy-target`);
        const d = await r.json();
        if (d.ok) {
          if (d.deploy_target) setDeployTarget({
            target_dir: d.deploy_target.target_dir || '',
            source_subdir: d.deploy_target.source_subdir || 'repo',
            post_deploy_command: d.deploy_target.post_deploy_command || '',
          });
          setHasSsh(!!d.has_ssh);
          setHasFtp(!!d.has_ftp);
          setTransport(d.has_ssh ? 'ssh' : (d.has_ftp ? 'ftp' : 'ssh'));
        }
      } catch (_) { /* ignore */ }
    })();
  }, [showDirect, projectId]);

  const approveAndDeploy = async () => {
    const msg = window.prompt('وصف التغيير اللي تبي يكون في commit message:', 'تحديثات Zenrex AI');
    if (!msg) return;
    setDeploying(true);
    setPrResult(null);
    try {
      const r = await authedFetch(`${API}/api/freebuild-chat/project/${projectId}/continuation/sandbox/approve-and-deploy`, {
        method: 'POST',
        body: JSON.stringify({ mode: 'github_pr', commit_message: msg, branch_suffix: 'review' }),
      });
      const d = await r.json();
      if (!d.ok) { toast.error(d.error || 'فشل النشر'); setPrResult({ error: d.error }); return; }
      toast.success('✅ تم رفع التعديلات على فرع المراجعة');
      setPrResult(d);
    } catch (e) {
      toast.error('فشل النشر — راجع الشبكة');
    } finally { setDeploying(false); }
  };

  const runDirectDeploy = async () => {
    if (confirmText.trim() !== 'نشر مباشر') {
      toast.error('اكتب "نشر مباشر" بالضبط للتأكيد');
      return;
    }
    if (!deployTarget.target_dir.trim().startsWith('/')) {
      toast.error('مسار النشر لازم يبدأ بـ /');
      return;
    }
    setDirectLoading(true);
    setDirectResult(null);
    try {
      // 1) Save / update deploy target config
      const save = await authedFetch(`${API}/api/freebuild-chat/project/${projectId}/continuation/deploy-target`, {
        method: 'POST',
        body: JSON.stringify(deployTarget),
      });
      const saveD = await save.json();
      if (!saveD.ok) { toast.error(saveD.detail || 'فشل حفظ إعدادات النشر'); return; }

      // 2) Trigger direct deploy
      const r = await authedFetch(`${API}/api/freebuild-chat/project/${projectId}/continuation/sandbox/approve-and-deploy`, {
        method: 'POST',
        body: JSON.stringify({ mode: 'direct_live', transport }),
      });
      const d = await r.json();
      setDirectResult(d);
      if (!d.ok) {
        toast.error(d.error || 'فشل النشر المباشر');
      } else {
        toast.success('🚀 نُشر مباشرة على السيرفر الحي');
        setConfirmText('');
      }
    } catch (e) {
      toast.error('فشل النشر — راجع الشبكة');
    } finally { setDirectLoading(false); }
  };

  return (
    <div data-testid="continuation-preview-panel" dir="rtl" className="rounded-2xl border border-fuchsia-500/30 bg-gradient-to-br from-black via-fuchsia-950/30 to-black backdrop-blur p-4 sm:p-5 mb-4">
      <div className="flex items-center gap-3 mb-3 pb-3 border-b border-white/5">
        <Eye className="w-5 h-5 text-fuchsia-300" />
        <h3 className="text-sm font-black text-fuchsia-100">معاينة Sandbox + السجل</h3>
        <button
          onClick={() => { setShowDirect(true); setDirectResult(null); }}
          disabled={deploying || directLoading}
          data-testid="direct-deploy-btn"
          className="mr-auto px-3 py-1.5 rounded-lg bg-gradient-to-r from-rose-600 to-orange-500 hover:from-rose-500 hover:to-orange-400 text-[11px] font-black text-white disabled:opacity-40 flex items-center gap-1.5"
          title="ارفع التعديلات مباشرة على السيرفر الحي بدون GitHub"
        >
          <Rocket className="w-3.5 h-3.5" />
          نشر مباشر للسيرفر
        </button>
        <button
          onClick={approveAndDeploy}
          disabled={deploying || directLoading}
          data-testid="approve-deploy-btn"
          className="px-3 py-1.5 rounded-lg bg-gradient-to-r from-emerald-500 to-teal-500 hover:from-emerald-400 hover:to-teal-400 text-[11px] font-black text-white disabled:opacity-40 flex items-center gap-1.5"
          title="ارفع التعديلات على فرع مراجعة في GitHub"
        >
          {deploying ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Send className="w-3.5 h-3.5" />}
          فرع مراجعة (PR)
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

      {/* Direct Deploy result banner */}
      {directResult && (
        <div data-testid="direct-deploy-result" className={`mb-3 p-3 rounded-xl border ${directResult.ok ? 'bg-orange-500/10 border-orange-500/30' : 'bg-rose-500/10 border-rose-500/40'}`}>
          <div className="flex items-start gap-2">
            {directResult.ok
              ? <Rocket className="w-4 h-4 text-orange-300 shrink-0 mt-0.5" />
              : <AlertTriangle className="w-4 h-4 text-rose-300 shrink-0 mt-0.5" />}
            <div className="flex-1 min-w-0">
              <div className={`text-[11px] font-bold mb-1 ${directResult.ok ? 'text-orange-100' : 'text-rose-100'}`}>
                {directResult.ok ? 'نُشر مباشر على السيرفر الحي' : `فشل النشر: ${directResult.error || 'غير معروف'}`}
              </div>
              {directResult.deployed_to && (
                <div className="text-[10px] text-zinc-300 mb-1 font-mono break-all">{directResult.deployed_to}</div>
              )}
              {directResult.instructions_ar && (
                <div className="text-[10px] text-zinc-300/80 mb-2">{directResult.instructions_ar}</div>
              )}
              {directResult.snapshot_id && (
                <div className="text-[10px] text-zinc-400">سناب شوت احتياطي قبل النشر: <code className="text-zinc-200">{directResult.snapshot_id}</code></div>
              )}
              {(directResult.post_stderr || directResult.stderr) && (
                <pre className="mt-2 max-h-32 overflow-auto text-[10px] bg-black/40 p-2 rounded text-rose-200 font-mono whitespace-pre-wrap">{directResult.post_stderr || directResult.stderr}</pre>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Direct Deploy confirmation modal */}
      {showDirect && (
        <div data-testid="direct-deploy-modal" className="fixed inset-0 z-[200] flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm" onClick={() => !directLoading && setShowDirect(false)}>
          <div dir="rtl" className="w-full max-w-lg rounded-2xl border border-rose-500/40 bg-gradient-to-br from-zinc-950 via-rose-950/30 to-zinc-950 p-5 shadow-2xl" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center gap-2 mb-3">
              <Rocket className="w-5 h-5 text-rose-300" />
              <h4 className="text-base font-black text-rose-100">نشر مباشر للسيرفر الحي</h4>
              <button onClick={() => setShowDirect(false)} disabled={directLoading} className="mr-auto text-zinc-400 hover:text-rose-300"><X className="w-4 h-4" /></button>
            </div>
            <div className="mb-3 p-3 rounded-xl bg-rose-500/10 border border-rose-500/30 text-[11px] text-rose-100 leading-relaxed">
              <div className="flex items-center gap-1.5 font-bold mb-1"><AlertTriangle className="w-4 h-4" /> تحذير</div>
              هذا الإجراء يكتب فوق ملفات سيرفرك الحي مباشرة. سيتم أخذ نسخة احتياطية تلقائية قبل النشر، لكن المسؤولية الكاملة عليك. للنشر الأكثر أماناً استخدم زر «فرع مراجعة (PR)».
            </div>

            {/* Transport selector */}
            <div className="mb-3">
              <label className="text-[11px] font-bold text-zinc-300 mb-1.5 block">قناة النقل:</label>
              <div className="flex gap-2">
                <button
                  type="button"
                  data-testid="transport-ssh"
                  onClick={() => setTransport('ssh')}
                  disabled={!hasSsh}
                  className={`flex-1 px-3 py-2 rounded-lg text-[11px] font-bold border transition ${transport === 'ssh' ? 'bg-rose-500/30 border-rose-400 text-white' : 'bg-black/30 border-white/10 text-zinc-400 hover:bg-white/5'} ${!hasSsh ? 'opacity-40 cursor-not-allowed' : ''}`}
                >
                  SSH + rsync {hasSsh ? '✓' : '(لا توجد مفاتيح)'}
                </button>
                <button
                  type="button"
                  data-testid="transport-ftp"
                  onClick={() => setTransport('ftp')}
                  disabled={!hasFtp}
                  className={`flex-1 px-3 py-2 rounded-lg text-[11px] font-bold border transition ${transport === 'ftp' ? 'bg-rose-500/30 border-rose-400 text-white' : 'bg-black/30 border-white/10 text-zinc-400 hover:bg-white/5'} ${!hasFtp ? 'opacity-40 cursor-not-allowed' : ''}`}
                >
                  FTP / SFTP {hasFtp ? '✓' : '(لا توجد بيانات)'}
                </button>
              </div>
            </div>

            {/* Deploy target fields */}
            <div className="space-y-2 mb-3">
              <label className="text-[11px] font-bold text-zinc-300 block">
                مسار النشر على السيرفر الحي (target_dir):
                <input
                  data-testid="deploy-target-dir"
                  value={deployTarget.target_dir}
                  onChange={(e) => setDeployTarget({ ...deployTarget, target_dir: e.target.value })}
                  placeholder="/var/www/html/  أو  /opt/myapp/frontend/build/"
                  className="mt-1 w-full px-3 py-2 rounded-lg bg-black/40 border border-white/10 text-[12px] text-white font-mono placeholder:text-zinc-600 focus:border-rose-400 outline-none"
                />
              </label>
              <label className="text-[11px] font-bold text-zinc-300 block">
                المجلد المصدر داخل Sandbox (source_subdir):
                <input
                  data-testid="deploy-source-subdir"
                  value={deployTarget.source_subdir}
                  onChange={(e) => setDeployTarget({ ...deployTarget, source_subdir: e.target.value })}
                  placeholder="repo"
                  className="mt-1 w-full px-3 py-2 rounded-lg bg-black/40 border border-white/10 text-[12px] text-white font-mono placeholder:text-zinc-600 focus:border-rose-400 outline-none"
                />
              </label>
              {transport === 'ssh' && (
                <label className="text-[11px] font-bold text-zinc-300 block">
                  أمر بعد النشر (اختياري — بناء/إعادة تشغيل):
                  <textarea
                    data-testid="deploy-post-cmd"
                    value={deployTarget.post_deploy_command}
                    onChange={(e) => setDeployTarget({ ...deployTarget, post_deploy_command: e.target.value })}
                    placeholder="cd /opt/myapp && yarn build && systemctl reload nginx"
                    rows={2}
                    className="mt-1 w-full px-3 py-2 rounded-lg bg-black/40 border border-white/10 text-[11px] text-white font-mono placeholder:text-zinc-600 focus:border-rose-400 outline-none"
                  />
                </label>
              )}
            </div>

            <div className="mb-4">
              <label className="text-[11px] font-bold text-rose-200 block mb-1.5">
                للتأكيد — اكتب <code className="bg-black/40 px-1.5 py-0.5 rounded text-white">نشر مباشر</code>:
              </label>
              <input
                data-testid="deploy-confirm-text"
                value={confirmText}
                onChange={(e) => setConfirmText(e.target.value)}
                placeholder="نشر مباشر"
                className="w-full px-3 py-2 rounded-lg bg-black/40 border border-rose-500/40 text-[12px] text-white font-bold focus:border-rose-400 outline-none"
              />
            </div>

            <div className="flex gap-2">
              <button
                data-testid="deploy-cancel-btn"
                onClick={() => setShowDirect(false)}
                disabled={directLoading}
                className="flex-1 px-3 py-2 rounded-lg bg-zinc-800 hover:bg-zinc-700 text-[12px] font-bold text-zinc-200 disabled:opacity-40"
              >
                إلغاء
              </button>
              <button
                data-testid="deploy-confirm-btn"
                onClick={runDirectDeploy}
                disabled={directLoading || (!hasSsh && !hasFtp)}
                className="flex-1 px-3 py-2 rounded-lg bg-gradient-to-r from-rose-600 to-orange-500 hover:from-rose-500 hover:to-orange-400 text-[12px] font-black text-white disabled:opacity-40 flex items-center justify-center gap-1.5"
              >
                {directLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Rocket className="w-4 h-4" />}
                نفّذ النشر المباشر
              </button>
            </div>
          </div>
        </div>
      )}
      <div className="flex gap-1 mb-3">
        {[
          ...(projectKind === 'app' ? [{ id: 'phone', label: 'معاينة الجوال', icon: Smartphone }] : []),
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
      {tab === 'phone' && projectKind === 'app' && <PhonePreviewTab projectId={projectId} />}
      {tab === 'files' && <FilesTab projectId={projectId} />}
      {tab === 'snapshots' && <SnapshotsTab projectId={projectId} reloadSig={reloadSig} />}
      {tab === 'audit' && <AuditTab projectId={projectId} />}
    </div>
  );
}
