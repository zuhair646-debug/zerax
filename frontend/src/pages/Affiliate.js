import React, { useEffect, useMemo, useState } from 'react';
import { toast } from 'sonner';

const API = process.env.REACT_APP_BACKEND_URL;

/**
 * /affiliate — Marketer's dashboard.
 * Apply if not enrolled, otherwise see referrals, earnings, payouts.
 */
export default function Affiliate({ user }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const token = useMemo(() => localStorage.getItem('token') || '', []);
  const H = useMemo(() => ({ Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' }), [token]);

  const load = async () => {
    setLoading(true);
    try {
      const d = await fetch(`${API}/api/affiliate/me`, { headers: H }).then(r => r.json());
      setData(d);
    } catch (_) { /* */ }
    setLoading(false);
  };
  useEffect(() => { load(); /* eslint-disable-next-line */ }, []);

  if (loading) return <div className="min-h-screen bg-[#0a0b14] text-white flex items-center justify-center">⏳ تحميل...</div>;

  return (
    <div className="min-h-screen bg-[#0a0b14] text-white" dir="rtl" data-testid="affiliate-page">
      <div className="max-w-5xl mx-auto p-4 md:p-8">
        <div className="mb-6 flex items-center justify-between">
          <div>
            <h1 className="text-3xl md:text-4xl font-black mb-1">🤝 برنامج التسويق بالعمولة</h1>
            <p className="text-sm text-white/60">اربح نسبة من كل عميل تجلبه — مدى الحياة</p>
          </div>
          <a href="/" className="text-xs text-white/50 hover:text-white">← العودة</a>
        </div>

        {!data?.enrolled ? <ApplyForm onApplied={load} H={H} /> : <Dashboard data={data} reload={load} />}
      </div>
    </div>
  );
}

function ApplyForm({ onApplied, H }) {
  const [method, setMethod] = useState('');
  const [notes, setNotes] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const submit = async () => {
    setSubmitting(true);
    try {
      await fetch(`${API}/api/affiliate/apply`, { method: 'POST', headers: H, body: JSON.stringify({ method, notes }) });
      toast.success('✅ تم تقديم طلبك — سيتم الموافقة قريباً');
      onApplied();
    } catch (_) { toast.error('فشل'); }
    setSubmitting(false);
  };

  const benefits = [
    { icon: '💰', title: 'عمولة مدى الحياة', desc: 'احصل على نسبة من كل عملية شحن لكل عميل تجلبه — وليس فقط أول دفعة.' },
    { icon: '🔗', title: 'رابط ثابت دائم', desc: 'تحصل على رابط فريد بكودك الخاص. شاركه على وسائل التواصل أو قنواتك.' },
    { icon: '📊', title: 'لوحة تتبّع', desc: 'شاهد كل عميل جاء عبر رابطك، شحناته، وأرباحك الفورية والمتراكمة.' },
    { icon: '⚡', title: 'صرف سريع', desc: 'اطلب الصرف في أي وقت بمجرد تجاوز رصيدك ٥٠ ر.س.' },
  ];

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {benefits.map((b, i) => (
          <div key={i} className="bg-gradient-to-br from-yellow-500/10 to-orange-500/5 border border-yellow-500/20 rounded-xl p-4">
            <div className="text-3xl mb-2">{b.icon}</div>
            <div className="font-black mb-1">{b.title}</div>
            <div className="text-xs text-white/65 leading-relaxed">{b.desc}</div>
          </div>
        ))}
      </div>

      <div className="bg-white/[.03] border border-white/10 rounded-xl p-5">
        <h3 className="font-black mb-3">📝 قدّم طلبك</h3>
        <label className="block mb-3">
          <span className="text-xs text-white/60">طريقة التسويق</span>
          <select value={method} onChange={e => setMethod(e.target.value)} className="w-full mt-1 px-3 py-2 bg-black/30 border border-white/10 rounded-lg text-sm" data-testid="apply-method">
            <option value="">اختر...</option>
            <option value="social">وسائل التواصل (Twitter, Instagram...)</option>
            <option value="blog">مدوّنة / موقع شخصي</option>
            <option value="youtube">يوتيوب</option>
            <option value="whatsapp">واتساب / Telegram</option>
            <option value="agency">وكالة / استشارات</option>
            <option value="other">أخرى</option>
          </select>
        </label>
        <label className="block mb-4">
          <span className="text-xs text-white/60">ملاحظات (اختياري)</span>
          <textarea rows={3} value={notes} onChange={e => setNotes(e.target.value)}
            placeholder="عرّف عن نفسك وعن جمهورك..."
            className="w-full mt-1 px-3 py-2 bg-black/30 border border-white/10 rounded-lg text-sm" data-testid="apply-notes" />
        </label>
        <button onClick={submit} disabled={submitting}
          className="px-6 py-2.5 bg-yellow-500 hover:bg-yellow-600 text-black font-black rounded-xl text-sm disabled:opacity-50"
          data-testid="apply-submit">
          {submitting ? '⏳ جاري الإرسال...' : '🚀 تقديم طلب الانضمام'}
        </button>
      </div>
    </div>
  );
}

function Dashboard({ data, reload }) {
  const aff = data.affiliate || {};
  const [copied, setCopied] = useState(false);

  if (aff.status === 'pending') {
    return (
      <div className="bg-yellow-500/10 border border-yellow-500/30 rounded-xl p-8 text-center">
        <div className="text-5xl mb-3">⏳</div>
        <h3 className="font-black text-lg mb-2">طلبك قيد المراجعة</h3>
        <p className="text-sm text-white/65">سنوافق على طلبك قريباً وستحصل على كودك الفريد ورابط التسويق.</p>
      </div>
    );
  }
  if (aff.status === 'rejected') {
    return (
      <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-8 text-center">
        <div className="text-5xl mb-3">❌</div>
        <h3 className="font-black text-lg mb-2">طلبك لم يُقبل</h3>
        <p className="text-sm text-white/65">تواصل معنا لمعرفة المزيد.</p>
      </div>
    );
  }

  const link = `${window.location.origin}/register?aff=${aff.code}`;
  const copyLink = async () => {
    await navigator.clipboard.writeText(link);
    setCopied(true);
    toast.success('✅ تم نسخ الرابط');
    setTimeout(() => setCopied(false), 2000);
  };

  const refs = data.referrals || [];
  const paidRefs = refs.filter(r => r.paid_at);

  return (
    <div className="space-y-5">
      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <Stat label="💰 الرصيد المتاح" value={`${(aff.pending_balance || 0).toFixed(2)} $`} accent="emerald" />
        <Stat label="✅ تم صرفه" value={`${(aff.paid_total || 0).toFixed(2)} $`} accent="blue" />
        <Stat label="👥 إجمالي المشتركين" value={aff.lifetime_referrals_signups || 0} accent="amber" />
        <Stat label="💳 دفعوا فعلاً" value={aff.lifetime_referrals_paid || 0} accent="violet" />
      </div>

      {/* Link */}
      <div className="bg-gradient-to-br from-emerald-500/15 to-cyan-500/10 border border-emerald-400/40 rounded-2xl p-5">
        <div className="flex items-center justify-between mb-2 flex-wrap gap-2">
          <h3 className="font-black text-lg">🔗 رابط التسويق الخاص بك</h3>
          <span className="text-[11px] bg-emerald-500/20 px-2 py-0.5 rounded-full">عمولة {aff.commission_pct}% مدى الحياة</span>
        </div>
        <div className="flex gap-2 items-stretch flex-wrap">
          <code className="flex-1 min-w-0 px-3 py-2 bg-black/40 border border-white/10 rounded-lg text-xs md:text-sm font-mono break-all text-emerald-300" data-testid="affiliate-link">{link}</code>
          <button onClick={copyLink} className={`px-4 py-2 rounded-lg font-black text-sm ${copied ? 'bg-emerald-500 text-black' : 'bg-white/10 hover:bg-white/20'}`} data-testid="copy-link">
            {copied ? '✓ نُسخ' : '📋 نسخ'}
          </button>
          <a href={`https://wa.me/?text=${encodeURIComponent('انضم لـ Zitex: ' + link)}`} target="_blank" rel="noopener" className="px-4 py-2 bg-emerald-500 text-black rounded-lg font-black text-sm">📱 واتساب</a>
        </div>
        <p className="text-[11px] text-white/55 mt-3 leading-relaxed">
          🎯 شارك هذا الرابط على وسائل التواصل أو مع شبكة معارفك. عند تسجيل أي عميل عبر هذا الرابط ودفعه لاشتراك Zitex،
          ستحصل تلقائياً على <b className="text-emerald-300">{aff.commission_pct}%</b> من قيمة كل دفعة <b>مدى الحياة</b>.
        </p>
      </div>

      {/* Referrals */}
      <div className="bg-white/[.03] border border-white/10 rounded-xl p-4">
        <h3 className="font-black mb-3">👥 العملاء المشتركون عبر رابطك</h3>
        {refs.length === 0 ? (
          <div className="text-center text-white/40 text-sm py-6">لم يشترك أحد بعد. شارك رابطك للبدء!</div>
        ) : (
          <div className="space-y-1.5">
            {refs.map((r, i) => (
              <div key={i} className="flex items-center gap-3 p-2.5 bg-white/[.03] border border-white/5 rounded-lg text-sm" data-testid={`ref-${i}`}>
                <span className="text-xl">{r.paid_at ? '💳' : '👤'}</span>
                <div className="flex-1 min-w-0">
                  <div className="truncate">{r.referred_user?.name || '(عميل)'} · <span className="text-white/50">{r.referred_user?.email}</span></div>
                  <div className="text-[10px] text-white/40">انضم {new Date(r.signup_at).toLocaleDateString('ar-SA')}</div>
                </div>
                {r.paid_at && (
                  <div className="text-left">
                    <div className="text-emerald-300 font-bold text-sm">+{(r.commission || 0).toFixed(2)} $</div>
                    <div className="text-[10px] text-white/50">من ${(r.amount || 0).toFixed(2)}</div>
                  </div>
                )}
                {!r.paid_at && <span className="text-[10px] text-white/40">لم يدفع بعد</span>}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Payouts */}
      {(data.payouts || []).length > 0 && (
        <div className="bg-white/[.03] border border-white/10 rounded-xl p-4">
          <h3 className="font-black mb-3">💸 سجلّ الصرف</h3>
          <div className="space-y-1.5">
            {data.payouts.map((p, i) => (
              <div key={i} className="flex items-center justify-between p-2.5 bg-white/[.03] rounded-lg text-sm">
                <div>
                  <div className="font-bold text-emerald-300">${(p.amount || 0).toFixed(2)}</div>
                  <div className="text-[10px] text-white/50">{p.method} · {new Date(p.at).toLocaleDateString('ar-SA')}</div>
                </div>
                <div className="text-[11px] text-white/60">{p.note || ''}</div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function Stat({ label, value, accent }) {
  const colors = {
    emerald: 'from-emerald-500/15 to-emerald-500/5 border-emerald-500/30 text-emerald-300',
    blue: 'from-blue-500/15 to-blue-500/5 border-blue-500/30 text-blue-300',
    amber: 'from-amber-500/15 to-amber-500/5 border-amber-500/30 text-amber-300',
    violet: 'from-violet-500/15 to-violet-500/5 border-violet-500/30 text-violet-300',
  };
  return (
    <div className={`bg-gradient-to-br ${colors[accent]} border rounded-xl p-4`}>
      <div className="text-[11px] text-white/65 mb-1">{label}</div>
      <div className={`text-2xl font-black ${colors[accent].split(' ').pop()}`}>{value}</div>
    </div>
  );
}
