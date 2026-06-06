import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { DollarSign, TrendingUp, Users, Tag, RotateCw } from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;

export default function PricingAdmin() {
  const [stats, setStats] = useState(null);
  const [orders, setOrders] = useState([]);
  const [promos, setPromos] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => { load(); }, []);

  const load = async () => {
    setLoading(true);
    const token = localStorage.getItem('token');
    const headers = { Authorization: `Bearer ${token}` };
    try {
      const [s, o, p] = await Promise.all([
        axios.get(`${API}/api/admin/pricing/stats`, { headers }),
        axios.get(`${API}/api/admin/pricing/orders?limit=50`, { headers }),
        axios.get(`${API}/api/admin/pricing/promos`, { headers }),
      ]);
      setStats(s.data);
      setOrders(o.data.orders);
      setPromos(p.data.promos);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div className="min-h-screen bg-zinc-950 text-white flex items-center justify-center" dir="rtl">جاري التحميل...</div>;
  }

  return (
    <div className="min-h-screen bg-zinc-950 text-white p-6" dir="rtl">
      <div className="max-w-7xl mx-auto">
        <div className="flex items-center justify-between mb-8">
          <h1 className="text-3xl font-bold flex items-center gap-3">
            <DollarSign className="w-8 h-8 text-emerald-400" /> لوحة التسعير والإيرادات
          </h1>
          <button onClick={load} data-testid="refresh-pricing-admin" className="p-2 rounded-lg bg-zinc-900 hover:bg-zinc-800">
            <RotateCw className="w-5 h-5" />
          </button>
        </div>

        {/* Stats grid */}
        <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          <StatCard label="إجمالي الإيرادات" value={`$${stats?.total_revenue_usd?.toFixed(2) || 0}`} icon={<DollarSign />} color="emerald" />
          <StatCard label="إجمالي الطلبات" value={stats?.total_orders || 0} icon={<TrendingUp />} color="amber" />
          <StatCard label="اشتراكات نشطة" value={stats?.active_subscriptions || 0} icon={<Users />} color="blue" />
          <StatCard label="آخر 30 يوم" value={`$${stats?.last_30d_revenue_usd?.toFixed(2) || 0}`} icon={<TrendingUp />} color="purple" />
        </div>

        {/* Promos */}
        <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-6 mb-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-bold flex items-center gap-2"><Tag className="w-5 h-5" /> أكواد الخصم</h2>
          </div>
          <div className="space-y-2">
            {promos.map((p) => (
              <div key={p.code} className="flex items-center justify-between p-3 bg-black/30 rounded-lg" data-testid={`promo-row-${p.code}`}>
                <div>
                  <div className="font-mono font-bold text-amber-400">{p.code}</div>
                  <div className="text-xs text-zinc-500">{p.label_ar}</div>
                </div>
                <div className="text-sm text-zinc-400">
                  {p.type === 'percent' ? `${p.value}% خصم` : `$${p.value} خصم`}
                </div>
                <div className="text-xs text-zinc-500">
                  استُخدم {p.uses_count || 0} من {p.max_uses || '∞'}
                </div>
                <div className={`text-xs px-2 py-1 rounded ${p.active ? 'bg-emerald-500/20 text-emerald-400' : 'bg-zinc-700 text-zinc-500'}`}>
                  {p.active ? 'مفعّل' : 'موقوف'}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Recent orders */}
        <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-6">
          <h2 className="text-lg font-bold mb-4">آخر الطلبات</h2>
          {orders.length === 0 ? (
            <p className="text-zinc-500 text-center py-8">لا توجد طلبات بعد — استخدم صفحة <a href="/pricing" className="text-amber-400">/pricing</a> للتجربة</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="text-zinc-500 text-xs">
                  <tr>
                    <th className="text-right p-2">PayPal Order</th>
                    <th className="text-right p-2">العميل</th>
                    <th className="text-right p-2">المنتج</th>
                    <th className="text-right p-2">المبلغ</th>
                    <th className="text-right p-2">الحالة</th>
                    <th className="text-right p-2">التاريخ</th>
                  </tr>
                </thead>
                <tbody>
                  {orders.map((o) => (
                    <tr key={o.order_id} className="border-t border-zinc-800" data-testid={`order-${o.order_id}`}>
                      <td className="p-2 font-mono text-xs">{o.order_id.slice(0, 12)}...</td>
                      <td className="p-2">{o.user_email}</td>
                      <td className="p-2">{o.item_type}: {o.item_id}</td>
                      <td className="p-2 text-amber-400 font-bold">${o.total_usd?.toFixed(2)}</td>
                      <td className="p-2">
                        <span className={`px-2 py-0.5 rounded text-xs ${
                          o.status === 'COMPLETED' ? 'bg-emerald-500/20 text-emerald-400'
                          : o.status === 'CREATED' ? 'bg-amber-500/20 text-amber-400'
                          : 'bg-rose-500/20 text-rose-400'
                        }`}>
                          {o.status}
                        </span>
                      </td>
                      <td className="p-2 text-zinc-500 text-xs">{new Date(o.created_at).toLocaleString('ar-SA')}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function StatCard({ label, value, icon, color }) {
  const colors = {
    emerald: 'from-emerald-500/20 to-emerald-500/5 border-emerald-500/30 text-emerald-400',
    amber: 'from-amber-500/20 to-amber-500/5 border-amber-500/30 text-amber-400',
    blue: 'from-blue-500/20 to-blue-500/5 border-blue-500/30 text-blue-400',
    purple: 'from-purple-500/20 to-purple-500/5 border-purple-500/30 text-purple-400',
  };
  return (
    <div className={`bg-gradient-to-br ${colors[color]} border rounded-xl p-5`}>
      <div className="flex items-center justify-between mb-2">
        <span className="text-zinc-400 text-sm">{label}</span>
        <div className="opacity-50">{icon}</div>
      </div>
      <div className="text-3xl font-bold">{value}</div>
    </div>
  );
}
