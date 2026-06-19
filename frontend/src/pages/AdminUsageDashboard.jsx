/**
 * AdminUsageDashboard — owner/admin view of AI consumption.
 *
 * Shows:
 *   - Today's & 30-day cost totals
 *   - Top spenders (users by tokens this month)
 *   - Top projects by cost
 *
 * Only accessible to users with role owner/super_admin/admin.
 */
import React, { useEffect, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { DollarSign, Activity, Users, FolderKanban, Loader2, ArrowLeft, RefreshCw, AlertTriangle } from 'lucide-react';
import ZenrexBrand from '../components/ZenrexBrand';

const API = process.env.REACT_APP_BACKEND_URL;

function StatCard({ label, value, accent = 'amber', sub = '' }) {
  const map = {
    amber:   'border-amber-500/30 bg-amber-500/5 text-amber-300',
    emerald: 'border-emerald-500/30 bg-emerald-500/5 text-emerald-300',
    purple:  'border-purple-500/30 bg-purple-500/5 text-purple-300',
    rose:    'border-rose-500/30 bg-rose-500/5 text-rose-300',
  };
  return (
    <div className={`rounded-xl border p-4 ${map[accent]}`}>
      <div className="text-[10px] uppercase tracking-wider font-bold opacity-70">{label}</div>
      <div className="text-2xl font-black mt-1">{value}</div>
      {sub && <div className="text-[10px] opacity-70 mt-0.5">{sub}</div>}
    </div>
  );
}

export default function AdminUsageDashboard() {
  const navigate = useNavigate();
  const [totals, setTotals] = useState(null);
  const [spenders, setSpenders] = useState([]);
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    const token = localStorage.getItem('token');
    if (!token) { navigate('/login'); return; }
    const headers = { Authorization: `Bearer ${token}` };
    try {
      const [tRes, sRes, pRes] = await Promise.all([
        fetch(`${API}/api/usage/admin/totals`, { headers }),
        fetch(`${API}/api/usage/admin/top-spenders?limit=20`, { headers }),
        fetch(`${API}/api/usage/admin/by-project?limit=20`, { headers }),
      ]);
      if (tRes.status === 403) { setError('forbidden'); return; }
      setTotals((await tRes.json()) || null);
      setSpenders((await sRes.json()).items || []);
      setProjects((await pRes.json()).items || []);
    } catch (e) {
      setError('fetch_failed');
    } finally {
      setLoading(false);
    }
  }, [navigate]);

  useEffect(() => { load(); }, [load]);

  if (error === 'forbidden') {
    return (
      <div className="min-h-screen flex items-center justify-center bg-zinc-950 text-zinc-300" dir="rtl">
        <div className="text-center">
          <AlertTriangle className="w-10 h-10 mx-auto text-amber-400 mb-3" />
          <p className="font-bold mb-2">هذي الصفحة للمشرفين فقط</p>
          <a href="/dashboard" className="text-amber-300 underline">رجوع</a>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100" dir="rtl" data-testid="admin-usage-page">
      <header className="sticky top-0 z-30 border-b border-white/10 bg-zinc-950/85 backdrop-blur">
        <div className="max-w-7xl mx-auto px-4 py-3 flex items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <a href="/" className="hover:opacity-90"><ZenrexBrand size={26} /></a>
            <span className="text-zinc-600">•</span>
            <h1 className="text-sm font-bold text-zinc-300">لوحة استهلاك الذكاء</h1>
          </div>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={load}
              data-testid="refresh-btn"
              className="p-2 rounded-lg bg-white/5 hover:bg-white/10 text-zinc-300"
              aria-label="تحديث"
            >
              <RefreshCw className="w-4 h-4" />
            </button>
            <a href="/admin/dashboard" className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg bg-white/5 hover:bg-white/10 border border-white/10 text-zinc-300 text-xs font-bold">
              <ArrowLeft className="w-4 h-4" />
              <span>لوحة الإدارة</span>
            </a>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-8">
        {loading ? (
          <div className="flex items-center justify-center py-20">
            <Loader2 className="w-6 h-6 animate-spin text-amber-400" />
          </div>
        ) : (
          <>
            {/* Totals */}
            <section className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-8" data-testid="totals-grid">
              <StatCard
                accent="amber"
                label="آخر 24 ساعة"
                value={`$${(totals?.last_24h.cost_usd ?? 0).toFixed(2)}`}
                sub={`${(totals?.last_24h.tokens ?? 0).toLocaleString()} tokens · ${totals?.last_24h.calls ?? 0} طلب`}
              />
              <StatCard
                accent="emerald"
                label="آخر 30 يوم"
                value={`$${(totals?.last_30d.cost_usd ?? 0).toFixed(2)}`}
                sub={`${(totals?.last_30d.tokens ?? 0).toLocaleString()} tokens · ${totals?.last_30d.calls ?? 0} طلب`}
              />
              <StatCard accent="purple" label="عدد المستخدمين النشطين" value={spenders.length} sub="آخر 30 يوم" />
              <StatCard accent="rose"   label="مشاريع تستهلك" value={projects.length} sub="بحاجة مراقبة" />
            </section>

            {/* Top Spenders */}
            <section className="mb-10" data-testid="top-spenders-section">
              <h2 className="text-lg font-black mb-4 flex items-center gap-2">
                <Users className="w-5 h-5 text-amber-300" />
                أعلى مستهلكين (آخر 30 يوم)
              </h2>
              {spenders.length === 0 ? (
                <p className="text-sm text-zinc-500 text-center py-8 border border-dashed border-white/10 rounded-xl">
                  ما في استهلاك بعد — لما يبدأ المستخدمين راح يبينون هنا.
                </p>
              ) : (
                <div className="rounded-xl border border-white/10 overflow-hidden">
                  <table className="w-full text-xs">
                    <thead className="bg-black/40 text-zinc-400">
                      <tr>
                        <th className="text-right px-3 py-2 font-bold">المستخدم</th>
                        <th className="text-right px-3 py-2 font-bold">الباقة</th>
                        <th className="text-right px-3 py-2 font-bold">Tokens</th>
                        <th className="text-right px-3 py-2 font-bold">الطلبات</th>
                        <th className="text-right px-3 py-2 font-bold">التكلفة</th>
                      </tr>
                    </thead>
                    <tbody>
                      {spenders.map((s) => (
                        <tr key={s.user_id} data-testid={`spender-${s.user_id}`} className="border-t border-white/5 hover:bg-white/5">
                          <td className="px-3 py-2">
                            <div className="font-bold text-zinc-200">{s.email}</div>
                            <div className="text-[10px] text-zinc-500">{s.name || s.user_id.slice(0, 8)}</div>
                          </td>
                          <td className="px-3 py-2">
                            <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
                              s.tier === 'studio' ? 'bg-amber-500/20 text-amber-300' :
                              s.tier === 'pro'    ? 'bg-emerald-500/20 text-emerald-300' :
                              'bg-zinc-700 text-zinc-400'
                            }`}>{s.tier}</span>
                          </td>
                          <td className="px-3 py-2 text-zinc-300">{s.tokens_total.toLocaleString()}</td>
                          <td className="px-3 py-2 text-zinc-300">{s.calls}</td>
                          <td className="px-3 py-2 font-bold text-emerald-300">${s.cost_usd.toFixed(4)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </section>

            {/* Top Projects */}
            <section data-testid="top-projects-section">
              <h2 className="text-lg font-black mb-4 flex items-center gap-2">
                <FolderKanban className="w-5 h-5 text-purple-300" />
                مشاريع تستهلك أكثر
              </h2>
              {projects.length === 0 ? (
                <p className="text-sm text-zinc-500 text-center py-8 border border-dashed border-white/10 rounded-xl">
                  لا توجد مشاريع بعد.
                </p>
              ) : (
                <div className="rounded-xl border border-white/10 overflow-hidden">
                  <table className="w-full text-xs">
                    <thead className="bg-black/40 text-zinc-400">
                      <tr>
                        <th className="text-right px-3 py-2 font-bold">المشروع</th>
                        <th className="text-right px-3 py-2 font-bold">القسم</th>
                        <th className="text-right px-3 py-2 font-bold">المالك</th>
                        <th className="text-right px-3 py-2 font-bold">Tokens</th>
                        <th className="text-right px-3 py-2 font-bold">التكلفة</th>
                      </tr>
                    </thead>
                    <tbody>
                      {projects.map((p) => (
                        <tr key={p.project_id} className="border-t border-white/5 hover:bg-white/5">
                          <td className="px-3 py-2 font-bold text-zinc-200">{p.project_name}</td>
                          <td className="px-3 py-2 text-zinc-400">{p.section}</td>
                          <td className="px-3 py-2 text-zinc-500">{p.user_email}</td>
                          <td className="px-3 py-2 text-zinc-300">{p.tokens_total.toLocaleString()}</td>
                          <td className="px-3 py-2 font-bold text-emerald-300">${p.cost_usd.toFixed(4)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </section>
          </>
        )}
      </main>
    </div>
  );
}
