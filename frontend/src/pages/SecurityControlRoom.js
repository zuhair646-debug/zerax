/**
 * 🛡️ SecurityControlRoom — admin dashboard for 10-layer security
 * ──────────────────────────────────────────────────────────────
 * Visible to admins at /admin/security
 * - Polls /api/admin/security/status every 30s
 * - Red/yellow/green status indicators per layer
 * - One-click scan/backup/unblock
 * - Live alert feed
 * - Audit log viewer
 */
import React, { useState, useEffect, useCallback } from 'react';
import { Shield, AlertTriangle, RefreshCw, Database, Lock, Activity, Eye, Mail } from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;

export default function SecurityControlRoom() {
  const [data, setData] = useState(null);
  const [auditRows, setAuditRows] = useState([]);
  const [loading, setLoading] = useState(false);
  const [busyAction, setBusyAction] = useState(null);
  const token = localStorage.getItem('token');

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const r = await fetch(`${API}/api/admin/security/status`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (r.ok) setData(await r.json());
    } catch {/* ignore */}
    setLoading(false);
  }, [token]);

  const loadAudit = useCallback(async () => {
    try {
      const r = await fetch(`${API}/api/admin/security/audit-log?limit=50`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (r.ok) {
        const j = await r.json();
        setAuditRows(j.log || []);
      }
    } catch {/* ignore */}
  }, [token]);

  useEffect(() => {
    load();
    loadAudit();
    const id = setInterval(load, 30000);
    return () => clearInterval(id);
  }, [load, loadAudit]);

  const action = async (path, label) => {
    setBusyAction(label);
    try {
      await fetch(`${API}/api/admin/security/${path}`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
      });
      await load();
    } catch {/* ignore */}
    setBusyAction(null);
  };

  if (!data) {
    return (
      <div className="min-h-screen bg-zinc-950 text-white p-8 flex items-center justify-center">
        <div className="text-center">
          <RefreshCw className="w-8 h-8 animate-spin mx-auto mb-4 text-amber-400" />
          <p>جاري تحميل غرفة التحكم الأمنية…</p>
        </div>
      </div>
    );
  }

  const statusColor = data.overall_status?.startsWith('🔴') ? 'border-red-500 bg-red-950/20'
                    : data.overall_status?.startsWith('🟡') ? 'border-amber-500 bg-amber-950/20'
                    : 'border-emerald-500 bg-emerald-950/20';

  return (
    <div className="min-h-screen bg-zinc-950 text-white p-6" dir="rtl">
      {/* Top status bar */}
      <div className={`rounded-2xl border-2 ${statusColor} p-6 mb-6`} data-testid="security-overall">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold flex items-center gap-3">
              <Shield className="w-8 h-8" /> غرفة التحكم الأمنية
            </h1>
            <p className="text-zinc-400 mt-1">حماية 10 طبقات · AI Auditor يفحص كل 60 دقيقة · نسخ احتياطي كل 12 ساعة</p>
          </div>
          <div className="text-center">
            <p className="text-4xl font-bold mb-1">{data.overall_status}</p>
            <p className="text-xs text-zinc-400">آخر فحص: {data.last_ai_audit?.scanned_at?.slice(11, 19) || '—'}</p>
          </div>
        </div>
      </div>

      {/* Layer status grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-6">
        {Object.entries(data.layers || {}).map(([k, v]) => {
          const dot = v?.includes('🔴') ? 'bg-red-500' : v?.includes('🟡') ? 'bg-amber-400' : 'bg-emerald-400';
          return (
            <div key={k} className="bg-zinc-900 border border-white/10 rounded-xl p-4" data-testid={`layer-${k}`}>
              <div className="flex items-center gap-2 mb-2">
                <span className={`w-2 h-2 rounded-full ${dot}`}></span>
                <span className="text-xs font-mono text-zinc-400">{k}</span>
              </div>
              <p className="text-sm font-semibold">{v?.replace(/[🟢🟡🔴]/g, '').trim()}</p>
            </div>
          );
        })}
      </div>

      {/* Counters */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mb-6">
        {[
          ['login_failures_5min', 'محاولات فاشلة (5د)', <Activity className="w-4 h-4" />],
          ['accounts_locked', 'حسابات مقفولة', <Lock className="w-4 h-4" />],
          ['ips_blocked', 'IPs محظورة', <Shield className="w-4 h-4" />],
          ['audit_events_24h', 'أحداث (24س)', <Eye className="w-4 h-4" />],
          ['alerts_recent', 'تنبيهات حديثة', <AlertTriangle className="w-4 h-4" />],
        ].map(([k, label, icon]) => (
          <div key={k} className="bg-zinc-900/70 border border-white/10 rounded-xl p-3 text-center">
            <div className="flex items-center justify-center gap-1.5 text-zinc-400 text-xs mb-1">
              {icon} {label}
            </div>
            <p className="text-2xl font-bold text-amber-200">{data.counters[k]}</p>
          </div>
        ))}
      </div>

      {/* Actions */}
      <div className="flex flex-wrap gap-3 mb-6">
        <button
          onClick={() => action('scan-now', 'scan')}
          disabled={busyAction === 'scan'}
          data-testid="scan-now-btn"
          className="px-5 py-2.5 bg-gradient-to-r from-amber-500 to-orange-500 text-zinc-900 font-bold rounded-lg hover:opacity-90 disabled:opacity-50 flex items-center gap-2"
        >
          🔬 {busyAction === 'scan' ? 'يفحص…' : 'فحص أمني فوري (AI)'}
        </button>
        <button
          onClick={() => action('backup-now', 'backup')}
          disabled={busyAction === 'backup'}
          data-testid="backup-now-btn"
          className="px-5 py-2.5 bg-emerald-600 text-white font-bold rounded-lg hover:bg-emerald-500 disabled:opacity-50 flex items-center gap-2"
        >
          <Database className="w-4 h-4" /> {busyAction === 'backup' ? 'يحفظ…' : 'نسخ احتياطي الآن'}
        </button>
        <button
          onClick={() => { load(); loadAudit(); }}
          className="px-5 py-2.5 bg-zinc-800 text-white font-semibold rounded-lg hover:bg-zinc-700 flex items-center gap-2"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} /> تحديث
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recent Alerts */}
        <div className="bg-zinc-900 border border-white/10 rounded-2xl p-5" data-testid="alerts-panel">
          <h2 className="text-lg font-bold mb-3 flex items-center gap-2">
            <AlertTriangle className="w-5 h-5 text-amber-400" /> التنبيهات الأخيرة ({data.recent_alerts?.length || 0})
          </h2>
          {data.recent_alerts?.length ? (
            <div className="space-y-2 max-h-96 overflow-y-auto">
              {data.recent_alerts.map(a => (
                <div key={a.id} className={`p-3 rounded-lg border-l-4 ${
                  a.severity === 'critical' ? 'border-red-500 bg-red-950/20'
                  : a.severity === 'high' ? 'border-orange-500 bg-orange-950/20'
                  : a.severity === 'medium' ? 'border-amber-500 bg-amber-950/20'
                  : 'border-zinc-500 bg-zinc-800/50'
                }`}>
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <p className="text-xs font-mono text-zinc-400">{a.kind} · {a.severity}</p>
                      <p className="text-sm mt-0.5">{a.message}</p>
                    </div>
                    <span className="text-[10px] text-zinc-500 whitespace-nowrap">{a.ts?.slice(11, 19)}</span>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-zinc-500 text-center py-8">لا توجد تنبيهات — كل شيء يعمل بأمان ✓</p>
          )}
        </div>

        {/* Backups */}
        <div className="bg-zinc-900 border border-white/10 rounded-2xl p-5" data-testid="backups-panel">
          <h2 className="text-lg font-bold mb-3 flex items-center gap-2">
            <Database className="w-5 h-5 text-emerald-400" /> النسخ الاحتياطية ({data.backups?.length || 0})
          </h2>
          {data.backups?.length ? (
            <div className="space-y-2">
              {data.backups.map((b, i) => (
                <div key={i} className="flex items-center justify-between p-2.5 bg-zinc-800/50 rounded-lg">
                  <span className="font-mono text-sm text-emerald-300">{b.ts}</span>
                  <span className="text-xs text-zinc-400">{(b.size_bytes / 1024).toFixed(1)} KB · {b.files} ملف</span>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-zinc-500 text-center py-8">لم تتم أي نسخة احتياطية بعد. اضغط "نسخ احتياطي الآن" لإنشاء أول snapshot.</p>
          )}
        </div>
      </div>

      {/* Last AI verdict */}
      {data.last_ai_audit?.verdict && (
        <div className="mt-6 bg-zinc-900 border border-white/10 rounded-2xl p-5" data-testid="ai-audit-panel">
          <h2 className="text-lg font-bold mb-3">🤖 آخر فحص بالذكاء الاصطناعي</h2>
          <p className="mb-2"><b>القرار:</b> <span className={
            data.last_ai_audit.verdict === 'CLEAR' ? 'text-emerald-400'
            : data.last_ai_audit.verdict === 'ELEVATED' ? 'text-amber-400'
            : 'text-red-400'
          }>{data.last_ai_audit.verdict}</span></p>
          {data.last_ai_audit.risks?.length > 0 && (
            <div className="mt-3">
              <p className="font-semibold text-amber-200">المخاطر المكتشفة:</p>
              <ul className="list-disc list-inside text-sm text-zinc-300 mt-1 space-y-1">
                {data.last_ai_audit.risks.map((r, i) => (
                  <li key={i}>[{r.severity}] {r.kind} — {r.evidence}</li>
                ))}
              </ul>
            </div>
          )}
          {data.last_ai_audit.recommendations?.length > 0 && (
            <div className="mt-3">
              <p className="font-semibold text-emerald-200">التوصيات:</p>
              <ul className="list-disc list-inside text-sm text-zinc-300 mt-1 space-y-1">
                {data.last_ai_audit.recommendations.map((r, i) => <li key={i}>{r}</li>)}
              </ul>
            </div>
          )}
        </div>
      )}

      {/* Audit log */}
      <div className="mt-6 bg-zinc-900 border border-white/10 rounded-2xl p-5" data-testid="audit-log-panel">
        <h2 className="text-lg font-bold mb-3 flex items-center gap-2">
          <Eye className="w-5 h-5" /> سجل الأحداث ({auditRows.length})
        </h2>
        <div className="max-h-96 overflow-y-auto">
          <table className="w-full text-xs">
            <thead className="text-zinc-400 sticky top-0 bg-zinc-900">
              <tr><th className="text-right p-2">الوقت</th><th className="text-right p-2">النوع</th><th className="text-right p-2">المستخدم</th><th className="text-right p-2">IP</th><th className="text-right p-2">التفاصيل</th></tr>
            </thead>
            <tbody>
              {auditRows.map((r, i) => (
                <tr key={i} className="border-t border-white/5">
                  <td className="p-2 font-mono text-zinc-500">{r.ts?.slice(11, 19)}</td>
                  <td className="p-2"><span className="px-2 py-0.5 bg-zinc-800 rounded text-amber-200">{r.kind}</span></td>
                  <td className="p-2 text-zinc-300">{r.actor?.slice(0, 16) || '—'}</td>
                  <td className="p-2 font-mono text-zinc-400">{r.ip || '—'}</td>
                  <td className="p-2 text-zinc-400 truncate max-w-md">{JSON.stringify(r.details || {})?.slice(0, 80)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
