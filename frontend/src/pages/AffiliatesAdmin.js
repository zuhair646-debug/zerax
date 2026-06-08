import React, { useState, useEffect } from 'react';
import { Navbar } from '@/components/Navbar';
import { toast } from 'sonner';
import { useNavigate } from 'react-router-dom';
import {
  TrendingUp, Users, DollarSign, Activity, Award, AlertTriangle,
  Loader2, Search, ChevronLeft, Eye, MousePointer, ShieldCheck,
} from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;

function api(p) {
  const t = localStorage.getItem('token');
  return fetch(`${API}${p}`, { headers: t ? { Authorization: `Bearer ${t}` } : {} });
}

const VERDICT_COLOR = {
  too_new: 'zinc',
  low: 'red',
  fair: 'yellow',
  good: 'emerald',
  excellent: 'amber',
};

export default function AffiliatesAdmin({ user }) {
  const [list, setList] = useState([]);
  const [loading, setLoading] = useState(true);
  const [q, setQ] = useState('');
  const [sortBy, setSortBy] = useState('lifetime_earnings');
  const [selected, setSelected] = useState(null);
  const [impact, setImpact] = useState(null);
  const [impactLoading, setImpactLoading] = useState(false);
  const navigate = useNavigate();

  const isAdmin = user?.role === 'admin' || user?.role === 'super_admin' || user?.role === 'owner' || user?.is_owner;

  const load = async () => {
    setLoading(true);
    try {
      const r = await api(`/api/admin/affiliates/list?q=${encodeURIComponent(q)}&sort_by=${sortBy}&limit=200`);
      if (r.ok) {
        const d = await r.json();
        setList(d.items || []);
      } else if (r.status === 403) {
        toast.error('للأدمن فقط');
      }
    } finally { setLoading(false); }
  };
  useEffect(() => { if (isAdmin) load(); /* eslint-disable-next-line */ }, [sortBy]);

  const loadImpact = async (uid) => {
    setImpactLoading(true);
    setImpact(null);
    setSelected(uid);
    try {
      const r = await api(`/api/admin/affiliates/${uid}/impact`);
      if (r.ok) setImpact(await r.json());
    } finally { setImpactLoading(false); }
  };

  if (!isAdmin) {
    return (
      <div className="min-h-screen bg-zinc-950 text-white flex items-center justify-center">
        <div className="text-center">
          <ShieldCheck className="w-12 h-12 text-red-400 mx-auto mb-3" />
          <div className="text-lg font-bold">هذه الصفحة للأدمن فقط</div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-zinc-950 text-white">
      <Navbar user={user} />
      <div className="pt-24 pb-12 px-4 max-w-[1500px] mx-auto">
        <div className="mb-5 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-pink-500 to-purple-600 flex items-center justify-center">
              <TrendingUp className="w-5 h-5" />
            </div>
            <div>
              <h1 className="text-2xl font-black">مركز المسوّقين</h1>
              <p className="text-zinc-500 text-sm">تتبع كل مسوّق، نقراته، مصادره، ومدى تأثيره الحقيقي</p>
            </div>
          </div>
          <button onClick={() => navigate('/admin')} className="text-zinc-500 hover:text-white text-sm">← لوحة الأدمن</button>
        </div>

        {!selected ? (
          <>
            <div className="flex flex-wrap gap-2 mb-4">
              <div className="relative flex-1 min-w-[240px]">
                <Search className="w-4 h-4 absolute top-2.5 right-3 text-zinc-500" />
                <input
                  value={q}
                  onChange={(e) => setQ(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && load()}
                  placeholder="ابحث بالاسم أو البريد..."
                  className="w-full bg-zinc-900 border border-zinc-800 rounded-lg pe-9 ps-3 py-2 text-sm"
                  data-testid="aff-search"
                />
              </div>
              {[
                ['lifetime_earnings', 'الأعلى عمولات'],
                ['clicks_30d', 'الأكثر نقرات'],
                ['signups_30d', 'الأكثر تسجيلات'],
                ['joined_at', 'الأحدث'],
              ].map(([k, l]) => (
                <button
                  key={k}
                  onClick={() => setSortBy(k)}
                  className={`px-3 py-2 rounded-lg text-xs ${sortBy === k ? 'bg-amber-500/20 border border-amber-400/40 text-amber-200' : 'border border-zinc-800 text-zinc-400'}`}
                >
                  {l}
                </button>
              ))}
            </div>

            {loading ? (
              <div className="text-center py-12"><Loader2 className="w-6 h-6 animate-spin mx-auto" /></div>
            ) : list.length === 0 ? (
              <div className="text-center py-16 text-zinc-500">لا يوجد مسوّقون بعد</div>
            ) : (
              <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-3" data-testid="aff-grid">
                {list.map((a, i) => (
                  <button
                    key={a.user_id}
                    onClick={() => loadImpact(a.user_id)}
                    data-testid={`aff-card-${a.code}`}
                    className="text-right bg-zinc-900/60 border border-zinc-800 hover:border-amber-400/40 rounded-xl p-4 transition-all"
                  >
                    <div className="flex items-start justify-between mb-2">
                      <div>
                        <div className="font-bold flex items-center gap-2">
                          {i < 3 && <Award className="w-4 h-4 text-amber-400" />}
                          {a.name}
                        </div>
                        <div className="text-[10px] text-zinc-500" data-no-translate="true">{a.email}</div>
                      </div>
                      <span className="text-[10px] px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-300 font-mono" data-no-translate="true">{a.code}</span>
                    </div>
                    <div className="grid grid-cols-3 gap-2 text-xs">
                      <div>
                        <div className="text-zinc-500 text-[9px]">نقرات</div>
                        <div className="font-bold text-blue-300" data-no-translate="true">{a.clicks_30d}</div>
                      </div>
                      <div>
                        <div className="text-zinc-500 text-[9px]">تسجيلات</div>
                        <div className="font-bold text-emerald-300" data-no-translate="true">{a.signups_30d}</div>
                      </div>
                      <div>
                        <div className="text-zinc-500 text-[9px]">عمولات</div>
                        <div className="font-bold text-amber-300" data-no-translate="true">${a.lifetime_earnings.toFixed(0)}</div>
                      </div>
                    </div>
                    <div className="text-[10px] text-zinc-500 mt-2 flex gap-2">
                      <span><span data-no-translate="true">{a.posts_count}</span> منشور</span>
                      <span>·</span>
                      <span data-no-translate="true">{a.commission_pct}%</span>
                      <span>عمولة</span>
                    </div>
                  </button>
                ))}
              </div>
            )}
          </>
        ) : (
          <div>
            <button onClick={() => { setSelected(null); setImpact(null); }} className="mb-4 text-amber-400 hover:text-amber-300 flex items-center gap-1 text-sm">
              <ChevronLeft className="w-4 h-4" /> رجوع للقائمة
            </button>
            {impactLoading || !impact ? (
              <div className="text-center py-12"><Loader2 className="w-6 h-6 animate-spin mx-auto" /></div>
            ) : (
              <div className="space-y-5">
                {/* Verdict */}
                <div className={`bg-${VERDICT_COLOR[impact.verdict.key] || 'zinc'}-500/10 border border-${VERDICT_COLOR[impact.verdict.key] || 'zinc'}-400/40 rounded-2xl p-5`}>
                  <div className="text-xs font-bold text-zinc-400 mb-1">حُكم النظام على هذا المسوّق:</div>
                  <div className={`text-xl font-black text-${VERDICT_COLOR[impact.verdict.key] || 'zinc'}-300`}>
                    {impact.verdict.label}
                  </div>
                </div>

                {/* Funnel */}
                <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
                  {[
                    ['نقرات إجمالي', impact.funnel.clicks_total, MousePointer, 'blue'],
                    ['نقرات 30 يوم', impact.funnel.clicks_30d, Activity, 'cyan'],
                    ['تسجيلات', impact.funnel.signups, Users, 'emerald'],
                    ['عملاء دافعون', impact.funnel.paid_customers, DollarSign, 'amber'],
                    ['إيراد ولّده', '$' + impact.funnel.total_revenue_generated_usd.toFixed(0), DollarSign, 'pink'],
                  ].map(([l, v, I, c]) => (
                    <div key={l} className={`bg-zinc-900/60 border border-zinc-800 rounded-xl p-4`}>
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-zinc-500 text-[10px] font-bold">{l}</span>
                        <I className={`w-4 h-4 text-${c}-400`} />
                      </div>
                      <div className="text-2xl font-black" data-no-translate="true">{v}</div>
                    </div>
                  ))}
                </div>

                <div className="bg-zinc-900/60 border border-zinc-800 rounded-xl p-5">
                  <div className="text-zinc-400 text-xs font-bold mb-2">معدل تحويل النقرة → تسجيل</div>
                  <div className="flex items-end gap-2">
                    <span className="text-4xl font-black text-amber-300" data-no-translate="true">{impact.funnel.signup_cr_pct}%</span>
                    <span className="text-zinc-500 mb-1 text-sm">
                      ({impact.funnel.signups}/{impact.funnel.clicks_total})
                    </span>
                  </div>
                </div>

                {/* Platforms */}
                <div className="bg-zinc-900/40 border border-zinc-800 rounded-2xl p-5">
                  <h3 className="font-bold mb-3">المنصات المصدّرة (30 يوم)</h3>
                  {impact.platforms.length > 0 ? (
                    <div className="space-y-2">
                      {impact.platforms.map((p) => (
                        <div key={p.platform} className="flex items-center justify-between p-2 bg-black/30 rounded">
                          <span data-no-translate="true">{p.platform}</span>
                          <div className="flex gap-3 text-xs">
                            <span className="text-blue-300"><span data-no-translate="true">{p.clicks}</span> نقرة</span>
                            <span className="text-emerald-300"><span data-no-translate="true">{p.signups}</span> تسجيل</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : <div className="text-zinc-500 text-sm">لا توجد بيانات</div>}
                </div>

                {/* Top posts */}
                {impact.top_posts.length > 0 && (
                  <div className="bg-zinc-900/40 border border-zinc-800 rounded-2xl p-5">
                    <h3 className="font-bold mb-3">أفضل منشوراته</h3>
                    <div className="space-y-2">
                      {impact.top_posts.map((p, i) => (
                        <div key={i} className="bg-black/30 rounded p-3 flex flex-wrap gap-3">
                          <a href={p.post_url} target="_blank" rel="noreferrer" className="flex-1 min-w-[200px] text-xs text-amber-300 hover:underline truncate" data-no-translate="true">
                            {p.post_url}
                          </a>
                          <div className="text-xs flex gap-3">
                            <span className="text-blue-300"><span data-no-translate="true">{p.clicks}</span> نقرة</span>
                            <span className="text-emerald-300"><span data-no-translate="true">{p.signups}</span> تسجيل</span>
                            <span className="text-purple-300" data-no-translate="true">{p.conversion_pct}%</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Recent click events */}
                {impact.recent_clicks.length > 0 && (
                  <div className="bg-zinc-900/40 border border-zinc-800 rounded-2xl p-5">
                    <h3 className="font-bold mb-3">آخر النقرات (forensics)</h3>
                    <div className="overflow-x-auto">
                      <table className="w-full text-xs">
                        <thead>
                          <tr className="text-zinc-500 text-[10px] uppercase">
                            <th className="text-right p-2">الوقت</th>
                            <th className="text-right p-2">المنصة</th>
                            <th className="text-right p-2">الجهاز</th>
                            <th className="text-right p-2">المتصفح</th>
                            <th className="text-right p-2">IP</th>
                            <th className="text-right p-2">حالة</th>
                          </tr>
                        </thead>
                        <tbody>
                          {impact.recent_clicks.slice(0, 30).map((c, i) => (
                            <tr key={i} className="border-t border-zinc-800/50">
                              <td className="p-2 text-zinc-400" data-no-translate="true">{(c.at || '').replace('T', ' ').slice(0, 19)}</td>
                              <td className="p-2" data-no-translate="true">{c.platform}</td>
                              <td className="p-2" data-no-translate="true">{c.device}</td>
                              <td className="p-2" data-no-translate="true">{c.browser}</td>
                              <td className="p-2 text-zinc-500" data-no-translate="true">{c.ip}</td>
                              <td className="p-2">
                                {c.paid ? <span className="text-amber-400">💰 دفع</span> :
                                 c.converted ? <span className="text-emerald-400">✓ سجّل</span> :
                                 <span className="text-zinc-500">ضغط</span>}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
