/**
 * CreditsLedger — Full transparent transaction history.
 *
 * Shows every credit movement (debit / credit) with timestamp + reason.
 * Critical for trust: users can audit every point that left their balance.
 */
import React, { useEffect, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, RefreshCw, Loader2, TrendingDown, TrendingUp, Sparkles } from 'lucide-react';
import { toast } from 'sonner';

const API = process.env.REACT_APP_BACKEND_URL;

const fmtTime = (iso) => {
  try {
    return new Date(iso).toLocaleString('ar-SA', { dateStyle: 'short', timeStyle: 'short' });
  } catch (_) { return iso; }
};

const REASON_LABELS = {
  'service:text_claude_1k': 'محادثة AI',
  'service:nano_banana_image': 'توليد صورة',
  'service:gpt_image_1': 'توليد صورة (GPT)',
  'service:claude_text': 'محادثة AI',
  'admin_grant': 'منحة من الإدارة',
  'signup_bonus': 'هدية تسجيل',
  'referral_bonus': 'مكافأة دعوة',
  'lemonsqueezy_purchase': 'شراء حزمة (LemonSqueezy)',
  'paypal_purchase': 'شراء حزمة (PayPal)',
};

const labelFor = (reason) => {
  if (!reason) return 'غير معروف';
  if (REASON_LABELS[reason]) return REASON_LABELS[reason];
  if (reason.startsWith('service:')) return `خدمة: ${reason.slice(8)}`;
  return reason;
};

export default function CreditsLedger() {
  const nav = useNavigate();
  const [loading, setLoading] = useState(true);
  const [balance, setBalance] = useState(0);
  const [txns, setTxns] = useState([]);

  const load = useCallback(async () => {
    setLoading(true);
    const token = localStorage.getItem('token');
    try {
      const r = await fetch(`${API}/api/pricing/transactions?limit=200`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || 'فشل');
      setBalance(d.balance || 0);
      setTxns(d.transactions || []);
    } catch (e) {
      toast.error(e.message || 'تعذر التحميل');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const totalDebits = txns.filter((t) => t.type === 'debit').reduce((s, t) => s + (Number(t.amount) || 0), 0);
  const totalCredits = txns.filter((t) => t.type === 'credit').reduce((s, t) => s + (Number(t.amount) || 0), 0);

  return (
    <div className="min-h-screen bg-gradient-to-b from-zinc-950 to-black text-white" dir="rtl">
      <div className="max-w-4xl mx-auto px-4 sm:px-6 py-8">
        <div className="flex items-center gap-3 mb-6">
          <button
            onClick={() => nav(-1)}
            data-testid="ledger-back-btn"
            className="p-2 rounded-full bg-white/5 hover:bg-white/10"
            aria-label="رجوع"
          >
            <ArrowLeft className="w-5 h-5" />
          </button>
          <div className="flex-1">
            <h1 className="text-2xl sm:text-3xl font-black bg-gradient-to-r from-amber-200 to-yellow-400 bg-clip-text text-transparent">
              سجل النقاط
            </h1>
            <p className="text-zinc-400 text-sm mt-0.5">كل خصم أو إضافة على رصيدك، مع السبب والوقت</p>
          </div>
          <button
            onClick={load}
            disabled={loading}
            className="p-2 rounded-full bg-white/5 hover:bg-white/10 disabled:opacity-50"
            title="تحديث"
          >
            {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : <RefreshCw className="w-5 h-5" />}
          </button>
        </div>

        {/* Summary cards */}
        <div className="grid grid-cols-3 gap-3 mb-6">
          <div className="rounded-xl border-2 border-amber-500/40 bg-amber-500/10 p-4">
            <div className="flex items-center gap-1.5 text-amber-300 mb-1">
              <Sparkles className="w-4 h-4" /> <span className="text-[10px] font-bold">رصيدك الآن</span>
            </div>
            <p className="text-2xl font-black text-amber-200">{balance.toLocaleString('en-US')}</p>
          </div>
          <div className="rounded-xl border border-red-500/30 bg-red-500/5 p-4">
            <div className="flex items-center gap-1.5 text-red-300 mb-1">
              <TrendingDown className="w-4 h-4" /> <span className="text-[10px] font-bold">إجمالي المصروف</span>
            </div>
            <p className="text-2xl font-black text-red-200">{Math.round(totalDebits).toLocaleString('en-US')}</p>
          </div>
          <div className="rounded-xl border border-emerald-500/30 bg-emerald-500/5 p-4">
            <div className="flex items-center gap-1.5 text-emerald-300 mb-1">
              <TrendingUp className="w-4 h-4" /> <span className="text-[10px] font-bold">إجمالي المضاف</span>
            </div>
            <p className="text-2xl font-black text-emerald-200">{Math.round(totalCredits).toLocaleString('en-US')}</p>
          </div>
        </div>

        {/* Transaction list */}
        <div className="rounded-2xl border border-zinc-800 bg-zinc-900/50 overflow-hidden">
          {loading ? (
            <div className="flex items-center justify-center py-20">
              <Loader2 className="w-8 h-8 animate-spin text-amber-400" />
            </div>
          ) : txns.length === 0 ? (
            <div className="text-center py-16">
              <p className="text-zinc-500 text-sm">لا توجد حركات حتى الآن</p>
            </div>
          ) : (
            <div className="divide-y divide-zinc-800">
              {txns.map((t, i) => {
                const isDebit = t.type === 'debit';
                const amt = Math.round(Number(t.amount) || 0);
                return (
                  <div
                    key={t.id || i}
                    data-testid={`txn-${i}`}
                    className="flex items-center gap-3 p-3 hover:bg-zinc-800/40"
                  >
                    <div className={`w-9 h-9 flex-shrink-0 rounded-full flex items-center justify-center ${
                      isDebit ? 'bg-red-500/15 text-red-300' : 'bg-emerald-500/15 text-emerald-300'
                    }`}>
                      {isDebit ? <TrendingDown className="w-4 h-4" /> : <TrendingUp className="w-4 h-4" />}
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-bold truncate">{labelFor(t.reason)}</p>
                      <p className="text-[10px] text-zinc-400">{fmtTime(t.ts)}</p>
                    </div>
                    <div className={`text-left flex-shrink-0 ${isDebit ? 'text-red-300' : 'text-emerald-300'}`}>
                      <p className="font-black text-sm">
                        {isDebit ? '−' : '+'}{amt.toLocaleString('en-US')}
                      </p>
                      <p className="text-[10px] text-zinc-500">
                        رصيد: {Math.round(Number(t.balance_after) || 0).toLocaleString('en-US')}
                      </p>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        <p className="text-center text-[10px] text-zinc-500 mt-6">
          كل حركة مسجّلة بتاريخها ووقتها — للحساب الكامل، فتش حسب الوقت في الحركات المسجّلة فوق.
        </p>
      </div>
    </div>
  );
}
