import React, { useState, useEffect, useMemo } from 'react';
import { Navbar } from '@/components/Navbar';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { toast } from 'sonner';
import {
  AlertTriangle,
  Bot,
  Brain,
  Check,
  CreditCard,
  DollarSign,
  LineChart,
  Loader2,
  RefreshCw,
  Save,
  ShieldCheck,
  Sparkles,
  Target,
  TrendingUp,
  Users,
  X,
  Zap
} from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;

const money = (value, currency = 'SAR') => {
  const n = Number(value || 0);
  return `${n.toLocaleString('ar-SA', { maximumFractionDigits: 2 })} ${currency}`;
};

const levelStyle = (level) => {
  if (level === 'high') return 'border-red-500/40 bg-red-500/10 text-red-100';
  if (level === 'medium') return 'border-amber-500/40 bg-amber-500/10 text-amber-100';
  return 'border-emerald-500/40 bg-emerald-500/10 text-emerald-100';
};

const priorityText = (priority) => {
  if (priority === 'high') return 'عالية';
  if (priority === 'medium') return 'متوسطة';
  return 'منخفضة';
};

const statusLabel = (status) => {
  const s = String(status || '').toLowerCase();
  if (s === 'pending') return 'معلق';
  if (s === 'approved' || s === 'paid' || s === 'completed') return 'مقبول';
  if (s === 'rejected' || s === 'failed') return 'مرفوض';
  return status || 'غير معروف';
};

const AdminPayments = ({ user }) => {
  const [payments, setPayments] = useState([]);
  const [financeAI, setFinanceAI] = useState(null);
  const [snapshots, setSnapshots] = useState([]);
  const [loading, setLoading] = useState(true);
  const [aiLoading, setAiLoading] = useState(true);
  const [savingSnapshot, setSavingSnapshot] = useState(false);
  const [adminNotes, setAdminNotes] = useState({});

  useEffect(() => {
    fetchAll();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const authHeaders = () => {
    const token = localStorage.getItem('token');
    return { Authorization: `Bearer ${token}` };
  };

  const fetchPayments = async () => {
    const res = await fetch(`${API}/api/payments`, { headers: authHeaders() });
    if (!res.ok) throw new Error('فشل تحميل المدفوعات');
    const data = await res.json();
    setPayments(Array.isArray(data) ? data : []);
  };

  const fetchFinanceAI = async () => {
    setAiLoading(true);
    try {
      const [overviewRes, snapshotsRes] = await Promise.all([
        fetch(`${API}/api/admin/finance-ai/overview`, { headers: authHeaders() }),
        fetch(`${API}/api/admin/finance-ai/snapshots?limit=5`, { headers: authHeaders() })
      ]);

      if (overviewRes.ok) {
        setFinanceAI(await overviewRes.json());
      } else if (overviewRes.status === 403 || overviewRes.status === 401) {
        setFinanceAI({ forbidden: true, message: 'مركز الذكاء المالي مخصص للمالك فقط.' });
      } else {
        throw new Error('تعذر تشغيل الذكاء المالي');
      }

      if (snapshotsRes.ok) {
        const data = await snapshotsRes.json();
        setSnapshots(data.snapshots || []);
      }
    } catch (error) {
      console.error('Finance AI error:', error);
      toast.error(error.message || 'تعذر تحميل الذكاء المالي');
    } finally {
      setAiLoading(false);
    }
  };

  const fetchAll = async () => {
    setLoading(true);
    try {
      await Promise.all([fetchPayments(), fetchFinanceAI()]);
    } catch (error) {
      console.error('Error:', error);
      toast.error(error.message || 'فشل تحميل البيانات');
    } finally {
      setLoading(false);
    }
  };

  const approvePayment = async (paymentId) => {
    try {
      const notes = adminNotes[paymentId] || '';
      const res = await fetch(`${API}/api/payments/${paymentId}/approve?admin_notes=${encodeURIComponent(notes)}`, {
        method: 'PUT',
        headers: authHeaders()
      });

      if (res.ok) {
        toast.success('تم قبول الدفع');
        await fetchAll();
      } else {
        toast.error('فشل القبول');
      }
    } catch (error) {
      toast.error('فشل القبول');
    }
  };

  const rejectPayment = async (paymentId) => {
    try {
      const notes = adminNotes[paymentId] || '';
      const res = await fetch(`${API}/api/payments/${paymentId}/reject?admin_notes=${encodeURIComponent(notes)}`, {
        method: 'PUT',
        headers: authHeaders()
      });

      if (res.ok) {
        toast.success('تم رفض الدفع');
        await fetchAll();
      } else {
        toast.error('فشل الرفض');
      }
    } catch (error) {
      toast.error('فشل الرفض');
    }
  };

  const saveSnapshot = async () => {
    setSavingSnapshot(true);
    try {
      const res = await fetch(`${API}/api/admin/finance-ai/snapshot`, {
        method: 'POST',
        headers: authHeaders()
      });
      if (!res.ok) throw new Error('فشل حفظ اللقطة');
      toast.success('تم حفظ لقطة الذكاء المالي');
      await fetchFinanceAI();
    } catch (error) {
      toast.error(error.message || 'فشل حفظ اللقطة');
    } finally {
      setSavingSnapshot(false);
    }
  };

  const pendingPayments = useMemo(
    () => payments.filter((p) => String(p.status || '').toLowerCase() === 'pending'),
    [payments]
  );

  const confirmedRevenue = financeAI?.summary?.confirmed_revenue || {};
  const pendingRevenue = financeAI?.summary?.pending_revenue || {};
  const healthScore = financeAI?.health_score || 0;

  return (
    <div dir="rtl" className="min-h-screen bg-zinc-950 text-white" data-testid="admin-payments-page">
      <Navbar user={user} />

      <div className="max-w-7xl mx-auto px-4 md:px-8 pt-24 pb-12">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 mb-8">
          <div>
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-amber-500/10 border border-amber-400/20 text-amber-200 text-sm mb-3">
              <Brain className="w-4 h-4" />
              مركز الذكاء المالي — قراءة وتحليل بلا تعديل تلقائي
            </div>
            <h1 className="text-3xl md:text-4xl font-black mb-2">إدارة المدفوعات الذكية</h1>
            <p className="text-zinc-400">تحليل المدفوعات، كشف المخاطر، مراقبة النقاط، وتوصيات تشغيلية للمالك.</p>
          </div>
          <div className="flex gap-2">
            <Button
              onClick={fetchAll}
              variant="outline"
              className="bg-white/10 border-white/15 text-white hover:bg-white/15"
              data-testid="refresh-finance-ai"
            >
              <RefreshCw className="w-4 h-4 ms-2" />
              تحديث
            </Button>
            <Button
              onClick={saveSnapshot}
              disabled={savingSnapshot || aiLoading || financeAI?.forbidden}
              className="bg-amber-500 hover:bg-amber-400 text-black font-bold"
              data-testid="save-finance-snapshot"
            >
              {savingSnapshot ? <Loader2 className="w-4 h-4 ms-2 animate-spin" /> : <Save className="w-4 h-4 ms-2" />}
              حفظ لقطة
            </Button>
          </div>
        </div>

        {aiLoading ? (
          <Card className="bg-zinc-900/60 border-white/10 mb-8">
            <CardContent className="p-6 flex items-center gap-3 text-zinc-300">
              <Loader2 className="w-5 h-5 animate-spin text-amber-400" />
              الذكاء المالي يقرأ المدفوعات والنقاط ويحسب المخاطر...
            </CardContent>
          </Card>
        ) : financeAI?.forbidden ? (
          <Card className="bg-red-500/10 border-red-500/30 mb-8">
            <CardContent className="p-6 flex items-center gap-3 text-red-100">
              <ShieldCheck className="w-5 h-5" />
              {financeAI.message}
            </CardContent>
          </Card>
        ) : financeAI ? (
          <div className="space-y-6 mb-8" data-testid="finance-ai-center">
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-5 gap-4">
              <Card className="bg-gradient-to-br from-amber-500/20 to-orange-500/10 border-amber-400/30 xl:col-span-1">
                <CardContent className="p-5">
                  <div className="flex items-center justify-between mb-3">
                    <Bot className="w-7 h-7 text-amber-300" />
                    <span className="text-3xl font-black">{healthScore}</span>
                  </div>
                  <div className="text-sm text-amber-100">درجة الصحة المالية</div>
                  <div className="h-2 mt-3 bg-black/30 rounded-full overflow-hidden">
                    <div className="h-full bg-amber-400" style={{ width: `${Math.min(100, healthScore)}%` }} />
                  </div>
                </CardContent>
              </Card>

              <Card className="bg-zinc-900/60 border-white/10">
                <CardContent className="p-5">
                  <DollarSign className="w-6 h-6 text-emerald-400 mb-3" />
                  <div className="text-2xl font-bold">{money(confirmedRevenue.SAR || 0, 'SAR')}</div>
                  <div className="text-sm text-zinc-400">إيراد مؤكد SAR</div>
                  {confirmedRevenue.USD ? <div className="text-xs text-zinc-500 mt-1">+ {money(confirmedRevenue.USD, 'USD')}</div> : null}
                </CardContent>
              </Card>

              <Card className="bg-zinc-900/60 border-white/10">
                <CardContent className="p-5">
                  <CreditCard className="w-6 h-6 text-sky-400 mb-3" />
                  <div className="text-2xl font-bold">{financeAI.summary?.payments_total || 0}</div>
                  <div className="text-sm text-zinc-400">إجمالي المدفوعات</div>
                  <div className="text-xs text-zinc-500 mt-1">معلق: {financeAI.summary?.payments_pending || 0}</div>
                </CardContent>
              </Card>

              <Card className="bg-zinc-900/60 border-white/10">
                <CardContent className="p-5">
                  <Zap className="w-6 h-6 text-purple-400 mb-3" />
                  <div className="text-2xl font-bold">{Number(financeAI.summary?.credits_liability || 0).toLocaleString('ar-SA')}</div>
                  <div className="text-sm text-zinc-400">التزام النقاط</div>
                  <div className="text-xs text-zinc-500 mt-1">نقاط غير مستخدمة تقريباً</div>
                </CardContent>
              </Card>

              <Card className="bg-zinc-900/60 border-white/10">
                <CardContent className="p-5">
                  <TrendingUp className="w-6 h-6 text-lime-400 mb-3" />
                  <div className="text-2xl font-bold">{money(financeAI.forecast?.next_30_days_sar || 0, 'SAR')}</div>
                  <div className="text-sm text-zinc-400">توقع 30 يوم</div>
                  <div className="text-xs text-zinc-500 mt-1">ثقة: {financeAI.forecast?.confidence || 'low'}</div>
                </CardContent>
              </Card>
            </div>

            <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
              <Card className="bg-zinc-900/60 border-white/10 xl:col-span-2">
                <CardContent className="p-6">
                  <div className="flex items-center gap-2 mb-4">
                    <AlertTriangle className="w-5 h-5 text-amber-300" />
                    <h2 className="text-xl font-bold">المخاطر المكتشفة</h2>
                  </div>
                  <div className="space-y-3">
                    {(financeAI.risks || []).slice(0, 5).map((risk, idx) => (
                      <div key={`${risk.title}-${idx}`} className={`rounded-2xl border p-4 ${levelStyle(risk.level)}`} data-testid={`finance-risk-${idx}`}>
                        <div className="flex items-start justify-between gap-3">
                          <div>
                            <div className="font-bold mb-1">{risk.title}</div>
                            <div className="text-sm opacity-90 mb-2">{risk.detail}</div>
                            <div className="text-xs opacity-80">الإجراء: {risk.action}</div>
                          </div>
                          <span className="text-lg font-black">{risk.score}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>

              <Card className="bg-zinc-900/60 border-white/10">
                <CardContent className="p-6">
                  <div className="flex items-center gap-2 mb-4">
                    <Target className="w-5 h-5 text-emerald-300" />
                    <h2 className="text-xl font-bold">توصيات تنفيذية</h2>
                  </div>
                  <div className="space-y-3">
                    {(financeAI.recommendations || []).slice(0, 5).map((rec, idx) => (
                      <div key={`${rec.title}-${idx}`} className="rounded-2xl bg-black/30 border border-white/10 p-4" data-testid={`finance-recommendation-${idx}`}>
                        <div className="flex items-center gap-2 mb-1">
                          <Sparkles className="w-4 h-4 text-amber-300" />
                          <span className="text-xs text-amber-200">أولوية {priorityText(rec.priority)}</span>
                        </div>
                        <div className="font-bold mb-1">{rec.title}</div>
                        <div className="text-sm text-zinc-400 mb-2">{rec.why}</div>
                        <div className="text-xs text-zinc-300">الخطوة: {rec.next_step}</div>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              <Card className="bg-zinc-900/60 border-white/10">
                <CardContent className="p-6">
                  <h3 className="font-bold mb-3 flex items-center gap-2"><Users className="w-5 h-5 text-sky-300" /> أعلى العملاء قيمة</h3>
                  <div className="space-y-2">
                    {(financeAI.top_customers || []).slice(0, 6).map((c) => (
                      <div key={c.user_id} className="flex items-center justify-between text-sm border-b border-white/5 pb-2">
                        <div className="min-w-0">
                          <div className="font-medium truncate">{c.name}</div>
                          <div className="text-zinc-500 truncate">{c.email}</div>
                        </div>
                        <div className="text-emerald-300 font-bold">{money(c.SAR || 0, 'SAR')}</div>
                      </div>
                    ))}
                    {!(financeAI.top_customers || []).length && <div className="text-sm text-zinc-500">لا توجد بيانات عملاء مؤكدة بعد.</div>}
                  </div>
                </CardContent>
              </Card>

              <Card className="bg-zinc-900/60 border-white/10">
                <CardContent className="p-6">
                  <h3 className="font-bold mb-3 flex items-center gap-2"><AlertTriangle className="w-5 h-5 text-red-300" /> قائمة مراقبة</h3>
                  <div className="space-y-2 text-sm text-zinc-300">
                    <div className="flex justify-between"><span>معلّق قديم</span><b>{financeAI.watchlist?.stale_pending_payments?.length || 0}</b></div>
                    <div className="flex justify-between"><span>اشتباه تكرار</span><b>{financeAI.watchlist?.duplicate_payment_signals?.length || 0}</b></div>
                    <div className="flex justify-between"><span>أرصدة سالبة</span><b>{financeAI.watchlist?.negative_credit_users?.length || 0}</b></div>
                    <div className="flex justify-between"><span>أرصدة عالية</span><b>{financeAI.watchlist?.high_credit_users?.length || 0}</b></div>
                  </div>
                </CardContent>
              </Card>

              <Card className="bg-zinc-900/60 border-white/10">
                <CardContent className="p-6">
                  <h3 className="font-bold mb-3 flex items-center gap-2"><LineChart className="w-5 h-5 text-amber-300" /> اللقطات المحفوظة</h3>
                  <div className="space-y-2">
                    {snapshots.map((s) => (
                      <div key={s.id} className="rounded-xl bg-black/25 border border-white/10 p-3 text-sm">
                        <div className="flex justify-between mb-1"><span>Score</span><b>{s.health_score}</b></div>
                        <div className="text-zinc-500">{new Date(s.created_at).toLocaleString('ar-SA')}</div>
                      </div>
                    ))}
                    {!snapshots.length && <div className="text-sm text-zinc-500">لا توجد لقطات بعد. احفظ أول لقطة الآن.</div>}
                  </div>
                </CardContent>
              </Card>
            </div>
          </div>
        ) : null}

        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-2xl font-bold">قائمة المدفوعات</h2>
            <p className="text-zinc-500 text-sm">{pendingPayments.length} دفعة معلقة تحتاج مراجعة.</p>
          </div>
        </div>

        {loading ? (
          <div className="text-center py-12 text-zinc-400">جاري التحميل...</div>
        ) : (
          <div className="grid grid-cols-1 gap-4">
            {payments.map((payment) => (
              <Card key={payment.id} data-testid={`payment-card-${payment.id}`} className="bg-zinc-900/60 border-white/10">
                <CardContent className="p-6">
                  <div className="flex flex-col lg:flex-row items-start justify-between gap-5">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-4 mb-4">
                        <div className="w-12 h-12 rounded-2xl bg-emerald-500/10 border border-emerald-400/20 flex items-center justify-center">
                          <CreditCard className="w-7 h-7 text-emerald-300" />
                        </div>
                        <div>
                          <h3 className="text-xl font-bold">المبلغ: {money(payment.amount, payment.currency || 'ريال')}</h3>
                          <p className="text-sm text-zinc-400">الطلب: {payment.request_id || payment.payment_type || '—'}</p>
                          <p className="text-sm text-zinc-500">العميل: {payment.user_name || 'غير معروف'} · {payment.user_email || ''}</p>
                        </div>
                      </div>
                      <div className="flex flex-wrap items-center gap-2 mb-4">
                        <span className={`px-3 py-1 rounded-full border text-sm ${
                          String(payment.status).toLowerCase() === 'pending'
                            ? 'bg-amber-500/10 border-amber-500/30 text-amber-200'
                            : String(payment.status).toLowerCase() === 'approved'
                              ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-200'
                              : 'bg-red-500/10 border-red-500/30 text-red-200'
                        }`}>
                          {statusLabel(payment.status)}
                        </span>
                        <span className="text-sm text-zinc-500">
                          {payment.created_at ? new Date(payment.created_at).toLocaleDateString('ar-SA') : 'بدون تاريخ'}
                        </span>
                      </div>
                      {payment.proof_image_url ? (
                        <Dialog>
                          <DialogTrigger asChild>
                            <Button variant="outline" size="sm" className="bg-white/10 border-white/15 text-white hover:bg-white/15">عرض إثبات الدفع</Button>
                          </DialogTrigger>
                          <DialogContent className="max-w-2xl bg-zinc-950 border-white/10 text-white">
                            <DialogHeader>
                              <DialogTitle>إثبات الدفع</DialogTitle>
                            </DialogHeader>
                            <img src={payment.proof_image_url} alt="إثبات الدفع" className="w-full rounded-xl" />
                          </DialogContent>
                        </Dialog>
                      ) : (
                        <span className="text-sm text-zinc-500">لا يوجد إثبات مرفق</span>
                      )}
                    </div>
                    {String(payment.status || '').toLowerCase() === 'pending' && (
                      <div className="flex flex-col gap-2 w-full lg:w-72">
                        <Input
                          placeholder="ملاحظات (اختياري)"
                          value={adminNotes[payment.id] || ''}
                          onChange={(e) => setAdminNotes({ ...adminNotes, [payment.id]: e.target.value })}
                          className="bg-black/30 border-white/15 text-white placeholder:text-zinc-500"
                          data-testid={`payment-notes-${payment.id}`}
                        />
                        <Button
                          size="sm"
                          onClick={() => approvePayment(payment.id)}
                          className="bg-emerald-500 hover:bg-emerald-400 text-black font-bold"
                          data-testid={`approve-payment-${payment.id}`}
                        >
                          <Check className="w-4 h-4 ms-2" />
                          قبول
                        </Button>
                        <Button
                          size="sm"
                          variant="destructive"
                          onClick={() => rejectPayment(payment.id)}
                          data-testid={`reject-payment-${payment.id}`}
                        >
                          <X className="w-4 h-4 ms-2" />
                          رفض
                        </Button>
                      </div>
                    )}
                  </div>
                </CardContent>
              </Card>
            ))}
            {!payments.length && (
              <Card className="bg-zinc-900/60 border-white/10">
                <CardContent className="p-10 text-center text-zinc-400">لا توجد مدفوعات حالياً.</CardContent>
              </Card>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default AdminPayments;
