import React from 'react';
import { useNavigate } from 'react-router-dom';
import { XCircle, ArrowLeft } from 'lucide-react';

export default function BillingCancel() {
  const navigate = useNavigate();
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 to-slate-900 flex items-center justify-center p-4 text-white" dir="rtl">
      <div className="max-w-md w-full rounded-3xl border border-white/10 bg-slate-900/80 backdrop-blur-xl p-8 text-center" data-testid="billing-cancel-card">
        <div className="flex justify-center mb-4">
          <XCircle className="w-16 h-16 text-red-400" />
        </div>
        <h1 className="text-2xl md:text-3xl font-bold mb-3">تم إلغاء الدفع</h1>
        <p className="text-white/70 mb-6">لم يتم خصم أي مبلغ. يمكنك المحاولة مرة أخرى في أي وقت.</p>
        <button
          onClick={() => navigate('/websites')}
          className="w-full rounded-xl bg-gradient-to-r from-yellow-400 to-orange-500 text-slate-900 font-bold py-3 px-4 hover:scale-[1.02] transition flex items-center justify-center gap-2"
          data-testid="back-to-studio-btn"
        >
          <ArrowLeft className="w-5 h-5 rotate-180" />
          المحاولة مجدداً
        </button>
      </div>
    </div>
  );
}
