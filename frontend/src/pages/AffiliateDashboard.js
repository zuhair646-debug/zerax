import React, { useState, useEffect } from 'react';
import { Navbar } from '@/components/Navbar';
import { toast } from 'sonner';
import {
  Link2, Copy, TrendingUp, Users, MousePointer, DollarSign,
  Share2, Plus, Trash2, ExternalLink, Sparkles, BarChart3,
  Twitter, Instagram, Facebook, Youtube, Music, MessageCircle,
  Globe, Activity, Eye, Smartphone, Monitor, Tablet, Loader2,
  Wallet, CheckCircle2, XCircle, Mail,
} from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;

function api(path, opts = {}) {
  const token = localStorage.getItem('token');
  return fetch(`${API}${path}`, {
    ...opts,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(opts.headers || {}),
    },
  });
}

const PLATFORM_ICON = {
  twitter: Twitter, instagram: Instagram, facebook: Facebook,
  youtube: Youtube, tiktok: Music, whatsapp: MessageCircle,
  telegram: MessageCircle, linkedin: Globe, direct: Globe,
};

const PlatformIcon = ({ name }) => {
  const I = PLATFORM_ICON[name] || Globe;
  return <I className="w-4 h-4" />;
};

const StatCard = ({ label, value, sub, icon: Icon, accent = 'amber' }) => (
  <div className="bg-zinc-900/60 border border-zinc-800 rounded-xl p-4">
    <div className="flex items-center justify-between mb-2">
      <span className="text-zinc-500 text-xs font-bold">{label}</span>
      <Icon className={`w-4 h-4 text-${accent}-400`} />
    </div>
    <div className="text-2xl font-black text-white" data-no-translate="true">{value}</div>
    {sub && <div className="text-[11px] text-zinc-500 mt-1">{sub}</div>}
  </div>
);

export default function AffiliateDashboard({ user }) {
  const [data, setData] = useState(null);
  const [posts, setPosts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [newPost, setNewPost] = useState({ post_url: '', platform: 'twitter', note: '' });
  const [adding, setAdding] = useState(false);
  const [linkBuilder, setLinkBuilder] = useState(null);
  const [lbPlatform, setLbPlatform] = useState('twitter');
  const [lbCampaign, setLbCampaign] = useState('default');
  const [payoutInfo, setPayoutInfo] = useState(null);
  const [payoutAmount, setPayoutAmount] = useState('');
  const [paypalEmail, setPaypalEmail] = useState('');
  const [paypalSaving, setPaypalSaving] = useState(false);
  const [requestingPayout, setRequestingPayout] = useState(false);
  const [payoutHistory, setPayoutHistory] = useState([]);

  const load = async () => {
    setLoading(true);
    try {
      const r1 = await api('/api/affiliate/me/dashboard');
      if (r1.ok) setData(await r1.json());
      const r2 = await api('/api/affiliate/me/posts');
      if (r2.ok) setPosts((await r2.json()).items || []);
      const r3 = await api('/api/affiliate/me/payout-info');
      if (r3.ok) {
        const d = await r3.json();
        setPayoutInfo(d);
        setPaypalEmail(d.paypal_email || '');
      }
      const r4 = await api('/api/affiliate/me/payouts');
      if (r4.ok) setPayoutHistory((await r4.json()).items || []);
    } finally { setLoading(false); }
  };

  const buildLink = async () => {
    const r = await api(`/api/affiliate/me/link-builder?platform=${lbPlatform}&campaign=${lbCampaign}`);
    if (r.ok) setLinkBuilder(await r.json());
  };

  useEffect(() => { load(); }, []);
  useEffect(() => { buildLink(); }, [lbPlatform, lbCampaign]);

  const savePaypal = async () => {
    if (!paypalEmail.match(/^[^\s@]+@[^\s@]+\.[^\s@]+$/)) { toast.error('بريد PayPal غير صحيح'); return; }
    setPaypalSaving(true);
    try {
      const r = await api('/api/affiliate/me/paypal-email', {
        method: 'POST', body: JSON.stringify({ paypal_email: paypalEmail }),
      });
      if (r.ok) { toast.success('تم حفظ بريد PayPal'); load(); }
      else { const e = await r.json().catch(() => ({})); toast.error(e.detail || 'فشل'); }
    } finally { setPaypalSaving(false); }
  };

  const requestPayout = async () => {
    const amt = parseFloat(payoutAmount);
    if (!amt || amt < (payoutInfo?.min_payout_usd || 25)) {
      toast.error(`الحد الأدنى $${payoutInfo?.min_payout_usd || 25}`); return;
    }
    if (!payoutInfo?.paypal_email) { toast.error('أضف بريد PayPal أولاً'); return; }
    setRequestingPayout(true);
    try {
      const r = await api('/api/affiliate/me/payout/request', {
        method: 'POST', body: JSON.stringify({ amount_usd: amt }),
      });
      if (r.ok) {
        const d = await r.json();
        toast.success(`تم إرسال طلب سحب $${d.amount_requested} (تستلم $${d.amount_net})`);
        setPayoutAmount('');
        load();
      } else {
        const e = await r.json().catch(() => ({}));
        toast.error(e.detail || 'فشل');
      }
    } finally { setRequestingPayout(false); }
  };

  const copy = (txt) => {
    navigator.clipboard?.writeText(txt);
    toast.success('تم النسخ');
  };

  const addPost = async () => {
    if (!newPost.post_url.trim()) { toast.error('أدخل رابط المنشور'); return; }
    setAdding(true);
    try {
      const r = await api('/api/affiliate/me/posts', { method: 'POST', body: JSON.stringify(newPost) });
      if (r.ok) {
        toast.success('تمت إضافة المنشور');
        setNewPost({ post_url: '', platform: 'twitter', note: '' });
        load();
      } else {
        const err = await r.json().catch(() => ({}));
        toast.error(err.detail || 'فشل');
      }
    } finally { setAdding(false); }
  };

  const delPost = async (id) => {
    if (!confirm('حذف هذا المنشور من السجل؟')) return;
    const r = await api(`/api/affiliate/me/posts/${id}`, { method: 'DELETE' });
    if (r.ok) {
      toast.success('تم الحذف');
      load();
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-zinc-950 text-white">
        <Navbar user={user} />
        <div className="pt-24 flex justify-center"><Loader2 className="w-6 h-6 animate-spin" /></div>
      </div>
    );
  }

  if (data && !data.is_affiliate) {
    return (
      <div className="min-h-screen bg-zinc-950 text-white">
        <Navbar user={user} />
        <div className="pt-24 px-4 max-w-2xl mx-auto text-center">
          <Sparkles className="w-16 h-16 text-amber-400 mx-auto mb-4" />
          <h1 className="text-3xl font-black mb-3">انضم لبرنامج المسوّقين</h1>
          <p className="text-zinc-400 mb-6">احصل على عمولة 20% على كل عميل تجلبه. ادعم منصة Zenrex وكسب المال.</p>
          <button
            className="px-6 py-3 bg-gradient-to-r from-amber-500 to-orange-500 text-zinc-950 rounded-lg font-black"
            onClick={async () => {
              const r = await api('/api/affiliate/apply', { method: 'POST' });
              if (r.ok) { toast.success('تم التقديم — بانتظار الموافقة'); load(); }
            }}
          >
            قدّم الآن
          </button>
        </div>
      </div>
    );
  }

  const s = data?.stats || {};
  const e = data?.earnings || {};

  return (
    <div className="min-h-screen bg-zinc-950 text-white">
      <Navbar user={user} />
      <div className="pt-24 pb-12 px-4 max-w-7xl mx-auto">
        <div className="flex items-center justify-between mb-6 flex-wrap gap-3">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-amber-500 to-orange-500 flex items-center justify-center">
              <TrendingUp className="w-6 h-6 text-zinc-950" />
            </div>
            <div>
              <h1 className="text-2xl font-black">لوحة المسوّق</h1>
              <p className="text-zinc-500 text-sm">كودك: <span className="font-mono text-amber-400" data-no-translate="true">{data.code}</span> · عمولة <span data-no-translate="true">{data.commission_pct}%</span></p>
            </div>
          </div>
          <div className="text-end">
            <div className="text-3xl font-black text-emerald-400" data-no-translate="true">${e.pending_balance?.toFixed(2)}</div>
            <div className="text-[11px] text-zinc-500">الرصيد المعلّق</div>
          </div>
        </div>

        {/* Hero stats */}
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3 mb-6">
          <StatCard label="نقرات 30 يوم" value={s.clicks_30d} sub={`${s.clicks_7d} في آخر 7 أيام`} icon={MousePointer} accent="blue" />
          <StatCard label="نقرات إجمالي" value={s.clicks_total} icon={Eye} accent="cyan" />
          <StatCard label="زوار فريدون" value={s.unique_visitors_30d} icon={Users} accent="purple" />
          <StatCard label="تسجيلات" value={s.signups_total} sub={`${s.signups_30d} هذا الشهر`} icon={Sparkles} accent="amber" />
          <StatCard label="عملاء دافعين" value={s.paid_referrals_total} icon={DollarSign} accent="emerald" />
          <StatCard label="معدل التحويل" value={`${s.signup_conversion_pct}%`} sub="نقرة → تسجيل" icon={Activity} accent="pink" />
        </div>

        {/* Impact + Earnings */}
        <div className="grid md:grid-cols-3 gap-4 mb-6">
          <div className="bg-gradient-to-br from-amber-500/10 to-orange-500/5 border border-amber-400/30 rounded-xl p-5">
            <div className="text-amber-300 text-xs font-bold mb-2">درجة تأثيرك</div>
            <div className="flex items-end gap-2">
              <span className="text-5xl font-black text-amber-300" data-no-translate="true">{s.impact_score}</span>
              <span className="text-zinc-500 mb-2 text-sm" data-no-translate="true">/100</span>
            </div>
            <div className="w-full h-2 bg-zinc-800 rounded-full mt-2 overflow-hidden">
              <div className="h-full bg-gradient-to-r from-amber-500 to-orange-500" style={{ width: `${s.impact_score}%` }} />
            </div>
          </div>
          <div className="bg-zinc-900/60 border border-zinc-800 rounded-xl p-5">
            <div className="text-zinc-500 text-xs font-bold mb-2">إجمالي العمولات</div>
            <div className="text-3xl font-black text-white" data-no-translate="true">${e.lifetime_earnings?.toFixed(2)}</div>
            <div className="text-[11px] text-zinc-500 mt-1">دُفع: <span data-no-translate="true">${e.paid_total?.toFixed(2)}</span></div>
          </div>
          <div className="bg-zinc-900/60 border border-zinc-800 rounded-xl p-5">
            <div className="text-zinc-500 text-xs font-bold mb-2">معدل تحويل التسجيل → دفع</div>
            <div className="text-3xl font-black text-white" data-no-translate="true">{s.paid_conversion_pct}%</div>
            <div className="text-[11px] text-zinc-500 mt-1">جودة عملاءك</div>
          </div>
        </div>

        {/* Payout panel */}
        <div className="bg-gradient-to-br from-emerald-500/10 to-amber-500/5 border border-emerald-400/30 rounded-2xl p-5 mb-6">
          <div className="flex items-center gap-2 mb-3">
            <Wallet className="w-5 h-5 text-emerald-400" />
            <h3 className="font-bold">سحب الأرباح عبر PayPal</h3>
          </div>
          <div className="grid md:grid-cols-2 gap-4">
            {/* Left: PayPal email */}
            <div>
              <label className="text-xs text-zinc-400 mb-1 block flex items-center gap-1">
                <Mail className="w-3 h-3" /> بريد PayPal (مطلوب)
              </label>
              <div className="flex gap-2">
                <input
                  type="email"
                  value={paypalEmail}
                  onChange={(e) => setPaypalEmail(e.target.value)}
                  placeholder="your@paypal.com"
                  className="flex-1 bg-zinc-900 border border-zinc-800 rounded-lg px-3 py-2 text-sm"
                  data-testid="paypal-email-input"
                />
                <button
                  onClick={savePaypal}
                  disabled={paypalSaving}
                  data-testid="save-paypal-btn"
                  className="bg-emerald-500/20 border border-emerald-400/40 text-emerald-300 rounded-lg px-3 py-2 text-xs font-bold"
                >
                  {paypalSaving ? <Loader2 className="w-4 h-4 animate-spin" /> : 'حفظ'}
                </button>
              </div>
              {payoutInfo?.paypal_email && (
                <div className="text-[10px] text-emerald-400 mt-1 flex items-center gap-1">
                  <CheckCircle2 className="w-3 h-3" /> مُفعّل: <span data-no-translate="true">{payoutInfo.paypal_email}</span>
                </div>
              )}
              <p className="text-[10px] text-zinc-500 mt-2">
                ⚠️ ضروري يكون عندك حساب PayPal — هذي الطريقة الوحيدة لتحويل أموالك.
              </p>
            </div>

            {/* Right: Request payout */}
            <div>
              <label className="text-xs text-zinc-400 mb-1 block">المبلغ المراد سحبه (USD)</label>
              <input
                type="number"
                min={payoutInfo?.min_payout_usd || 25}
                step="0.01"
                value={payoutAmount}
                onChange={(e) => setPayoutAmount(e.target.value)}
                placeholder={`الحد الأدنى $${payoutInfo?.min_payout_usd || 25}`}
                className="w-full bg-zinc-900 border border-zinc-800 rounded-lg px-3 py-2 text-sm mb-2"
                data-testid="payout-amount"
              />
              {payoutAmount && parseFloat(payoutAmount) > 0 && (
                <div className="bg-black/30 rounded-lg p-2 text-xs space-y-1 mb-2">
                  <div className="flex justify-between">
                    <span className="text-zinc-400">المبلغ المطلوب:</span>
                    <span data-no-translate="true">${parseFloat(payoutAmount).toFixed(2)}</span>
                  </div>
                  <div className="flex justify-between text-red-300">
                    <span>رسوم التحويل:</span>
                    <span data-no-translate="true">-${(payoutInfo?.fee_usd || 2).toFixed(2)}</span>
                  </div>
                  <div className="flex justify-between font-bold text-emerald-300 border-t border-zinc-800 pt-1">
                    <span>تستلم:</span>
                    <span data-no-translate="true">${(parseFloat(payoutAmount) - (payoutInfo?.fee_usd || 2)).toFixed(2)}</span>
                  </div>
                </div>
              )}
              <button
                onClick={requestPayout}
                disabled={requestingPayout || !paypalEmail || !payoutAmount}
                data-testid="request-payout-btn"
                className="w-full bg-gradient-to-r from-emerald-500 to-amber-500 text-zinc-950 rounded-lg py-2.5 font-bold disabled:opacity-50 flex items-center justify-center gap-1"
              >
                {requestingPayout ? <Loader2 className="w-4 h-4 animate-spin" /> : <Wallet className="w-4 h-4" />}
                طلب التحويل
              </button>
              <p className="text-[10px] text-zinc-500 mt-1 text-center">
                المعالجة خلال 24-48 ساعة
              </p>
            </div>
          </div>

          {/* History */}
          {payoutHistory.length > 0 && (
            <div className="mt-4 pt-4 border-t border-zinc-800">
              <div className="text-xs text-zinc-400 mb-2">سجل التحويلات</div>
              <div className="space-y-1.5">
                {payoutHistory.slice(0, 6).map((p) => (
                  <div key={p.id} className="bg-black/30 rounded p-2 flex items-center justify-between text-xs">
                    <div className="flex items-center gap-2">
                      {p.status === 'paid' ? <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" /> :
                       p.status === 'rejected' ? <XCircle className="w-3.5 h-3.5 text-red-400" /> :
                       <Loader2 className="w-3.5 h-3.5 text-amber-400 animate-spin" />}
                      <span data-no-translate="true">${p.amount_requested_usd}</span>
                      <span className="text-zinc-500">→</span>
                      <span data-no-translate="true">${p.amount_net_usd}</span>
                    </div>
                    <span className="text-zinc-500 text-[10px]" data-no-translate="true">{(p.requested_at || '').slice(0, 10)}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Link Builder */}
        <div className="bg-zinc-900/40 border border-zinc-800 rounded-2xl p-5 mb-6">
          <div className="flex items-center gap-2 mb-3">
            <Link2 className="w-5 h-5 text-blue-400" />
            <h3 className="font-bold">منشئ روابط ذكي</h3>
          </div>
          <div className="grid md:grid-cols-3 gap-3 mb-3">
            <select
              value={lbPlatform}
              onChange={(e) => setLbPlatform(e.target.value)}
              className="bg-black/40 border border-zinc-800 rounded-lg px-3 py-2 text-sm"
              data-no-translate="true"
              data-testid="lb-platform"
            >
              {['twitter','instagram','facebook','youtube','tiktok','whatsapp','telegram','snapchat','linkedin','email','blog','other'].map((p) =>
                <option key={p} value={p}>{p}</option>
              )}
            </select>
            <input
              value={lbCampaign}
              onChange={(e) => setLbCampaign(e.target.value)}
              placeholder="اسم الحملة (مثل: launch2026)"
              className="bg-black/40 border border-zinc-800 rounded-lg px-3 py-2 text-sm"
              data-testid="lb-campaign"
            />
            <button
              onClick={buildLink}
              className="bg-amber-500/15 border border-amber-400/40 text-amber-300 rounded-lg px-3 py-2 text-sm font-bold"
            >
              إنشاء
            </button>
          </div>
          {linkBuilder && (
            <div className="space-y-2">
              <div className="bg-black/40 border border-zinc-800 rounded-lg p-2 flex items-center gap-2">
                <code className="flex-1 text-xs text-emerald-300 truncate" data-no-translate="true">{linkBuilder.short_url}</code>
                <button onClick={() => copy(linkBuilder.short_url)} className="text-zinc-400 hover:text-white"><Copy className="w-4 h-4" /></button>
              </div>
              <div className="text-[10px] text-zinc-500">
                استبدل <code data-no-translate="true">POST_URL_HERE</code> برابط منشورك الفعلي عشان تتعقّبه:
                <code className="text-zinc-400 block mt-1 text-[10px]" data-no-translate="true">{linkBuilder.post_url_template}</code>
              </div>
            </div>
          )}
        </div>

        {/* Sources & Devices */}
        <div className="grid md:grid-cols-2 gap-4 mb-6">
          <div className="bg-zinc-900/40 border border-zinc-800 rounded-2xl p-5">
            <div className="flex items-center gap-2 mb-3">
              <BarChart3 className="w-5 h-5 text-purple-400" />
              <h3 className="font-bold">مصادر الزيارات (30 يوم)</h3>
            </div>
            {data.platforms?.length > 0 ? (
              <div className="space-y-2">
                {data.platforms.slice(0, 8).map((p) => {
                  const max = Math.max(...data.platforms.map((x) => x.clicks));
                  const pct = max ? (p.clicks / max * 100) : 0;
                  return (
                    <div key={p.platform}>
                      <div className="flex items-center justify-between mb-1 text-xs">
                        <span className="flex items-center gap-1.5"><PlatformIcon name={p.platform} /><span data-no-translate="true">{p.platform}</span></span>
                        <span className="text-zinc-500" data-no-translate="true">{p.clicks}</span>
                      </div>
                      <div className="w-full h-2 bg-zinc-800 rounded-full overflow-hidden">
                        <div className="h-full bg-gradient-to-r from-purple-500 to-pink-500" style={{ width: `${pct}%` }} />
                      </div>
                    </div>
                  );
                })}
              </div>
            ) : <div className="text-zinc-500 text-sm">لا توجد بيانات بعد</div>}
          </div>

          <div className="bg-zinc-900/40 border border-zinc-800 rounded-2xl p-5">
            <div className="flex items-center gap-2 mb-3">
              <Smartphone className="w-5 h-5 text-emerald-400" />
              <h3 className="font-bold">أجهزة الزوار</h3>
            </div>
            {data.devices?.length > 0 ? (
              <div className="grid grid-cols-3 gap-2">
                {data.devices.map((d) => {
                  const I = d.device === 'mobile' ? Smartphone : d.device === 'tablet' ? Tablet : Monitor;
                  return (
                    <div key={d.device} className="bg-black/30 rounded-lg p-3 text-center">
                      <I className="w-6 h-6 mx-auto text-emerald-400 mb-1" />
                      <div className="text-lg font-black" data-no-translate="true">{d.clicks}</div>
                      <div className="text-[10px] text-zinc-500" data-no-translate="true">{d.device}</div>
                    </div>
                  );
                })}
              </div>
            ) : <div className="text-zinc-500 text-sm">لا توجد بيانات بعد</div>}
          </div>
        </div>

        {/* Posts management */}
        <div className="bg-zinc-900/40 border border-zinc-800 rounded-2xl p-5 mb-6">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <Share2 className="w-5 h-5 text-pink-400" />
              <h3 className="font-bold">منشوراتك (سجّل وين نشرت الرابط)</h3>
            </div>
            <span className="text-[10px] text-zinc-500" data-no-translate="true">{posts.length} منشور</span>
          </div>

          {/* Add new post */}
          <div className="grid md:grid-cols-[2fr,1fr,1fr,auto] gap-2 mb-4">
            <input
              value={newPost.post_url}
              onChange={(e) => setNewPost({ ...newPost, post_url: e.target.value })}
              placeholder="رابط منشورك (مثل https://twitter.com/you/status/...)"
              className="bg-black/40 border border-zinc-800 rounded-lg px-3 py-2 text-sm"
              data-testid="new-post-url"
            />
            <select
              value={newPost.platform}
              onChange={(e) => setNewPost({ ...newPost, platform: e.target.value })}
              className="bg-black/40 border border-zinc-800 rounded-lg px-3 py-2 text-sm"
              data-no-translate="true"
              data-testid="new-post-platform"
            >
              {['twitter','instagram','facebook','youtube','tiktok','whatsapp','telegram','linkedin','blog','other'].map((p) =>
                <option key={p} value={p}>{p}</option>
              )}
            </select>
            <input
              value={newPost.note}
              onChange={(e) => setNewPost({ ...newPost, note: e.target.value })}
              placeholder="ملاحظة (اختياري)"
              className="bg-black/40 border border-zinc-800 rounded-lg px-3 py-2 text-sm"
            />
            <button
              onClick={addPost}
              disabled={adding}
              data-testid="add-post-btn"
              className="bg-amber-500 text-zinc-950 rounded-lg px-4 py-2 text-sm font-bold disabled:opacity-50 flex items-center gap-1"
            >
              {adding ? <Loader2 className="w-4 h-4 animate-spin" /> : <Plus className="w-4 h-4" />}
              <span>إضافة</span>
            </button>
          </div>

          {posts.length === 0 ? (
            <div className="text-zinc-500 text-sm text-center py-6">
              أضف رابط أي منشور نشرت فيه رابطك. سنحسب لك النقرات لكل منشور تلقائياً.
            </div>
          ) : (
            <div className="space-y-2">
              {posts.map((p) => (
                <div key={p.id} className="bg-black/30 border border-zinc-800 rounded-lg p-3 flex flex-wrap items-center gap-3">
                  <div className="text-amber-400"><PlatformIcon name={p.platform} /></div>
                  <a href={p.post_url} target="_blank" rel="noreferrer" className="flex-1 min-w-[200px] text-sm text-zinc-300 hover:text-amber-300 truncate" data-no-translate="true">
                    {p.post_url}
                  </a>
                  <div className="flex items-center gap-3 text-xs">
                    <span className="text-blue-300"><span data-no-translate="true">{p.clicks}</span> نقرة</span>
                    <span className="text-emerald-300"><span data-no-translate="true">{p.signups}</span> تسجيل</span>
                    <span className="text-purple-300" data-no-translate="true">{p.conversion_pct}%</span>
                  </div>
                  <a href={p.post_url} target="_blank" rel="noreferrer" className="text-zinc-500 hover:text-white"><ExternalLink className="w-4 h-4" /></a>
                  <button onClick={() => delPost(p.id)} className="text-zinc-500 hover:text-red-400"><Trash2 className="w-4 h-4" /></button>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Daily timeseries */}
        {data.daily?.length > 0 && (
          <div className="bg-zinc-900/40 border border-zinc-800 rounded-2xl p-5">
            <div className="flex items-center gap-2 mb-3">
              <TrendingUp className="w-5 h-5 text-cyan-400" />
              <h3 className="font-bold">نشاط 30 يوم</h3>
            </div>
            <div className="overflow-x-auto">
              <div className="flex items-end gap-1 min-w-max h-32">
                {data.daily.map((d) => {
                  const max = Math.max(...data.daily.map((x) => x.clicks), 1);
                  const h = (d.clicks / max * 100);
                  return (
                    <div key={d.date} className="flex flex-col items-center gap-1" title={`${d.date}: ${d.clicks} نقرة، ${d.signups} تسجيل`}>
                      <div className="w-4 bg-gradient-to-t from-cyan-500 to-blue-400 rounded-t" style={{ height: `${h}%`, minHeight: '2px' }} />
                      <div className="text-[8px] text-zinc-600" data-no-translate="true">{d.date.slice(5)}</div>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
