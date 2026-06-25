/**
 * EngineerAuditModal — المهندس
 *
 * Paid Playwright-driven audit that crawls the published site, finds defects,
 * and presents a phased fix report. When the user clicks "أصلح هذي" on an
 * issue, we forward a structured instruction to the chat input (the parent
 * handles actually sending it via the existing agent chat stream).
 */
import React, { useState, useEffect } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from './ui/dialog';
import { Button } from './ui/button';
import { ScrollArea } from './ui/scroll-area';
import { Badge } from './ui/badge';
import { Loader2, Wrench, AlertTriangle, CheckCircle2, ExternalLink, X } from 'lucide-react';
import { toast } from 'sonner';

const SEV_STYLES = {
  critical: { bg: 'bg-red-500/15', border: 'border-red-400/40', text: 'text-red-300', label: '🔴 حرج', sortKey: 0 },
  high:     { bg: 'bg-orange-500/15', border: 'border-orange-400/40', text: 'text-orange-300', label: '🟠 مرتفع', sortKey: 1 },
  medium:   { bg: 'bg-amber-500/15', border: 'border-amber-400/40', text: 'text-amber-300', label: '🟡 متوسط', sortKey: 2 },
  low:      { bg: 'bg-zinc-500/15', border: 'border-zinc-400/40', text: 'text-zinc-300', label: '⚪ منخفض', sortKey: 3 },
};

const CATEGORY_LABELS = {
  console_error: 'خطأ JavaScript',
  broken_link: 'رابط مكسور',
  button_no_handler: 'زر بلا وظيفة',
  form_no_handler: 'نموذج بلا handler',
  broken_image: 'صورة مكسورة',
  missing_payment_integration: 'دفع مفقود',
  missing_shipping_fields: 'حقول شحن ناقصة',
  page_load_failed: 'فشل تحميل صفحة',
};

export const EngineerAuditModal = ({ open, onClose, projectId, projectPublished, apiBase, authToken, onIssueDispatchToChat }) => {
  const [stage, setStage] = useState('confirm'); // confirm | running | report | error
  const [report, setReport] = useState(null);
  const [errorMsg, setErrorMsg] = useState('');

  useEffect(() => {
    if (open) {
      setStage('confirm');
      setReport(null);
      setErrorMsg('');
    }
  }, [open]);

  const runAudit = async () => {
    setStage('running');
    setErrorMsg('');
    try {
      const res = await fetch(`${apiBase}/api/freebuild-chat/project/${projectId}/engineer/audit`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${authToken}` },
      });
      const data = await res.json();
      if (!res.ok) {
        setErrorMsg(data.detail || data.message || `HTTP ${res.status}`);
        setStage('error');
        return;
      }
      setReport(data);
      setStage('report');
      toast.success('🧑‍💻 المهندس انتهى من الفحص');
    } catch (e) {
      setErrorMsg(String(e?.message || e));
      setStage('error');
    }
  };

  const dispatchFix = (issue) => {
    const sevLabel = SEV_STYLES[issue.severity]?.label || issue.severity;
    const text = (
      `🧑‍💻 [تقرير المهندس — مرحلة ${issue.phase}/${report?.stats?.phases || 1}] ${sevLabel}\n\n` +
      `**الصفحة:** ${issue.page}\n` +
      `**التصنيف:** ${CATEGORY_LABELS[issue.category] || issue.category}\n` +
      (issue.element_text ? `**العنصر:** ${issue.element_text}\n` : '') +
      `**الوصف:** ${issue.description}\n` +
      `**الحل المقترح:** ${issue.fix_suggestion}\n\n` +
      `طبّق الإصلاح في الكود مباشرة، ثم انشر نسخة جديدة.`
    );
    onIssueDispatchToChat && onIssueDispatchToChat(text);
    toast.success('🛠️ تم تمرير الإصلاح للذكاء — يبدأ الآن');
    onClose();
  };

  const issues = report?.issues || [];
  const phases = {};
  issues.forEach(i => {
    if (!phases[i.phase]) phases[i.phase] = [];
    phases[i.phase].push(i);
  });

  return (
    <Dialog open={open} onOpenChange={(o) => !o && onClose()}>
      <DialogContent
        data-testid="engineer-modal"
        className="max-w-2xl bg-zinc-950 border border-amber-500/30 text-zinc-100"
        dir="rtl"
      >
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-amber-300">
            <Wrench className="w-5 h-5" />
            المهندس — فحص دقيق للموقع المنشور
          </DialogTitle>
        </DialogHeader>

        {stage === 'confirm' && (
          <div className="space-y-4 py-2">
            {!projectPublished ? (
              <div className="bg-amber-500/10 border border-amber-400/30 rounded-lg p-4 text-sm text-amber-200">
                ⚠️ يجب نشر الموقع أولاً قبل استدعاء المهندس. ارجع للشات واطلب من الذكاء النشر.
              </div>
            ) : (
              <>
                <p className="text-sm text-zinc-300 leading-7">
                  المهندس يفتح موقعك المنشور في متصفح حقيقي ويفحص كل صفحة:
                </p>
                <ul className="text-sm text-zinc-400 space-y-1.5 pr-4">
                  <li>✓ كل الروابط فعلاً تشتغل وتنقل لصفحات موجودة</li>
                  <li>✓ كل زر له وظيفة (مو ديكور)</li>
                  <li>✓ النماذج عندها backend handler</li>
                  <li>✓ الصور تُحمَّل بدون 404</li>
                  <li>✓ صفحات الدفع/الشحن عندها SDK + حقول كاملة</li>
                  <li>✓ صفر console errors</li>
                </ul>
                <div className="bg-zinc-900/60 border border-zinc-700 rounded-lg p-3 text-sm">
                  <div className="flex items-center justify-between">
                    <span className="text-zinc-300">التكلفة:</span>
                    <span className="text-amber-300 font-bold">500 نقطة</span>
                  </div>
                  <div className="text-xs text-zinc-500 mt-1">تُسترد كاملة لو فشل المهندس.</div>
                </div>
                <Button
                  data-testid="engineer-start-btn"
                  onClick={runAudit}
                  className="w-full bg-amber-500 hover:bg-amber-600 text-zinc-950 font-bold"
                >
                  استدعاء المهندس الآن (500 نقطة)
                </Button>
              </>
            )}
          </div>
        )}

        {stage === 'running' && (
          <div className="py-8 text-center space-y-4">
            <Loader2 className="w-12 h-12 animate-spin mx-auto text-amber-300" />
            <p className="text-lg text-amber-200 font-bold">المهندس يفحص الموقع الآن...</p>
            <p className="text-sm text-zinc-400">يفتح كل صفحة في متصفح حقيقي ويختبر كل عنصر. (30–90 ثانية)</p>
          </div>
        )}

        {stage === 'error' && (
          <div className="space-y-3 py-4">
            <div className="bg-red-500/10 border border-red-400/40 rounded-lg p-4 text-sm text-red-200">
              <div className="flex items-center gap-2 mb-2">
                <AlertTriangle className="w-4 h-4" />
                <span className="font-bold">المهندس واجه مشكلة</span>
              </div>
              <div className="text-xs text-red-300/80">{errorMsg}</div>
              <div className="text-xs text-zinc-400 mt-2">تمت إعادة النقاط لرصيدك.</div>
            </div>
            <Button onClick={() => setStage('confirm')} variant="outline" className="w-full">
              حاول مرة ثانية
            </Button>
          </div>
        )}

        {stage === 'report' && report && (
          <div className="space-y-3 py-2">
            <div className={`rounded-lg p-4 ${
              report.stats.total === 0 ? 'bg-emerald-500/10 border border-emerald-400/40' :
              report.stats.critical > 2 ? 'bg-red-500/10 border border-red-400/40' :
              'bg-amber-500/10 border border-amber-400/40'
            }`}>
              <div className="text-lg font-bold mb-1">{report.verdict}</div>
              <div className="text-xs text-zinc-400 flex flex-wrap gap-3">
                <span>📊 الدرجة: <b className="text-zinc-200">{report.stats.score}/100</b></span>
                <span>🔴 حرج: {report.stats.critical}</span>
                <span>🟠 مرتفع: {report.stats.high}</span>
                <span>🟡 متوسط: {report.stats.medium}</span>
                <span>📋 مراحل: {report.stats.phases}</span>
              </div>
              <a
                href={report.live_url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-xs text-cyan-300 hover:underline inline-flex items-center gap-1 mt-2"
              >
                <ExternalLink className="w-3 h-3" /> {report.live_url}
              </a>
            </div>

            {report.stats.total === 0 ? (
              <div className="py-6 text-center text-emerald-300">
                <CheckCircle2 className="w-12 h-12 mx-auto mb-2" />
                موقعك نظيف — لا توجد ثغرات.
              </div>
            ) : (
              <ScrollArea className="max-h-[420px] pr-2">
                <div className="space-y-4">
                  {Object.keys(phases).sort((a,b) => Number(a) - Number(b)).map(phaseId => (
                    <div key={phaseId}>
                      <div className="text-sm font-bold text-amber-300 mb-2 sticky top-0 bg-zinc-950/95 py-1">
                        المرحلة {phaseId} ({phases[phaseId].length} ثغرة)
                      </div>
                      <div className="space-y-2">
                        {phases[phaseId].map((issue, idx) => {
                          const sty = SEV_STYLES[issue.severity] || SEV_STYLES.low;
                          return (
                            <div
                              key={issue.id || idx}
                              data-testid={`audit-issue-${phaseId}-${idx}`}
                              className={`${sty.bg} ${sty.border} border rounded-lg p-3 text-sm`}
                            >
                              <div className="flex items-start justify-between gap-2 mb-1.5">
                                <div className="flex items-center gap-2 flex-wrap">
                                  <Badge variant="outline" className={`${sty.text} ${sty.border} text-[10px]`}>
                                    {sty.label}
                                  </Badge>
                                  <Badge variant="outline" className="text-[10px] text-zinc-400 border-zinc-600">
                                    {CATEGORY_LABELS[issue.category] || issue.category}
                                  </Badge>
                                  <span className="text-[10px] text-zinc-500">{issue.page}</span>
                                </div>
                              </div>
                              <div className="text-zinc-200 leading-6">{issue.description}</div>
                              {issue.element_text && (
                                <div className="text-xs text-zinc-400 mt-1 italic">「 {issue.element_text} 」</div>
                              )}
                              <div className="text-xs text-emerald-300/80 mt-2">💡 {issue.fix_suggestion}</div>
                              <Button
                                data-testid={`audit-fix-btn-${phaseId}-${idx}`}
                                size="sm"
                                onClick={() => dispatchFix(issue)}
                                className="mt-2 h-7 text-xs bg-emerald-600 hover:bg-emerald-700 text-white"
                              >
                                🛠️ أصلح هذي
                              </Button>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  ))}
                </div>
              </ScrollArea>
            )}
          </div>
        )}

        <button
          data-testid="engineer-close-btn"
          onClick={onClose}
          className="absolute top-3 left-3 text-zinc-500 hover:text-white"
          aria-label="إغلاق"
        >
          <X className="w-4 h-4" />
        </button>
      </DialogContent>
    </Dialog>
  );
};
