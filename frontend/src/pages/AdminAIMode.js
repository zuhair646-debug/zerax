/**
 * AdminAIMode — Owner-only toggle between Claude-Only and Hybrid AI orchestration.
 * Route: /admin/ai-mode
 *
 * • claude_only : Claude Sonnet 4.5 handles every phase (default, safer).
 * • hybrid      : GPT-5.5 handles first creative build; Claude handles edits.
 *
 * Both modes share the same 7 server-side guards
 * (SURGICAL-HARDBLOCK, DESIGN-DESTRUCTION GUARD, etc.) so projects stay protected.
 */
import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Navbar } from '@/components/Navbar';
import { Button } from '@/components/ui/button';
import { Loader2, Brain, Sparkles, Shield, Check } from 'lucide-react';
import { toast } from 'sonner';

const API = process.env.REACT_APP_BACKEND_URL;

const MODE_META = {
  claude_only: {
    title: 'Claude Only',
    subtitle: 'Claude Sonnet 4.5 لكل المراحل',
    description:
      'النموذج الحالي يتعامل مع كل شي — المحادثة، البناء الأول، التعديلات الجراحية، وحل المشاكل. الانضباط أعلى، التصاميم جيدة.',
    badge: 'الافتراضي · مستقر',
    icon: Brain,
    color: 'from-indigo-500/20 to-blue-500/20 border-indigo-400/40',
    iconColor: 'text-indigo-300',
  },
  hybrid: {
    title: 'Hybrid (GPT-5.5 + Claude)',
    subtitle: 'توليفة: GPT للتصميم الإبداعي، Claude للانضباط',
    description:
      'GPT-5.5 يبني التصميم الأول الإبداعي (HTML/CSS). Claude Sonnet 4.5 يستلم كل التعديلات الجراحية والإصلاحات. توليفة قوية بصرياً وانضباطياً.',
    badge: 'تجريبي · تصاميم أجمل',
    icon: Sparkles,
    color: 'from-amber-500/20 to-pink-500/20 border-amber-400/40',
    iconColor: 'text-amber-300',
  },
};

export default function AdminAIMode() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [currentMode, setCurrentMode] = useState('claude_only');

  useEffect(() => {
    (async () => {
      try {
        const token = localStorage.getItem('token');
        const r = await fetch(`${API}/api/admin/ai-mode`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        const data = await r.json();
        setCurrentMode(data.mode || 'claude_only');
      } catch (e) {
        toast.error('تعذر قراءة الإعدادات: ' + e.message);
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const handleSelect = async (mode) => {
    if (mode === currentMode || saving) return;
    setSaving(true);
    try {
      const token = localStorage.getItem('token');
      const r = await fetch(`${API}/api/admin/ai-mode`, {
        method: 'PUT',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ mode }),
      });
      if (!r.ok) {
        const err = await r.json().catch(() => ({}));
        throw new Error(err.detail || `HTTP ${r.status}`);
      }
      setCurrentMode(mode);
      toast.success(`تم التبديل إلى: ${MODE_META[mode].title}`);
    } catch (e) {
      toast.error('فشل الحفظ: ' + e.message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-white" dir="rtl">
      <Navbar />
      <main className="max-w-5xl mx-auto px-6 py-10">
        <header className="mb-8">
          <button
            onClick={() => navigate('/admin/dashboard')}
            data-testid="admin-ai-mode-back-btn"
            className="text-sm opacity-60 hover:opacity-100 mb-3"
          >
            ← لوحة التحكم
          </button>
          <h1 className="text-3xl font-extrabold mb-2">
            <Sparkles className="inline ml-2 text-amber-400" size={28} />
            وضع الذكاء الاصطناعي (FreeBuild)
          </h1>
          <p className="text-slate-300 max-w-3xl">
            اختر النموذج الذي يتعامل مع بناء المواقع داخل FreeBuild. التغيير
            <strong> فوري </strong>
            على كل المشاريع الجديدة. لا restart مطلوب.
          </p>
        </header>

        {loading ? (
          <div className="flex items-center gap-3 text-slate-400">
            <Loader2 className="animate-spin" />
            جارٍ التحميل...
          </div>
        ) : (
          <>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
              {Object.entries(MODE_META).map(([key, meta]) => {
                const Icon = meta.icon;
                const isActive = currentMode === key;
                return (
                  <button
                    key={key}
                    data-testid={`ai-mode-card-${key}`}
                    onClick={() => handleSelect(key)}
                    disabled={saving}
                    className={`text-right bg-gradient-to-br ${meta.color} border-2 rounded-2xl p-6 transition-all hover:scale-[1.01] disabled:opacity-50 ${
                      isActive ? 'ring-4 ring-emerald-400/60' : 'ring-0'
                    }`}
                  >
                    <div className="flex items-start justify-between mb-3">
                      <Icon className={meta.iconColor} size={32} />
                      {isActive && (
                        <span className="flex items-center gap-1 text-xs font-bold bg-emerald-500/30 text-emerald-200 px-3 py-1 rounded-full border border-emerald-400/40">
                          <Check size={14} /> مفعّل
                        </span>
                      )}
                    </div>
                    <h2 className="text-xl font-bold mb-1">{meta.title}</h2>
                    <p className="text-sm text-slate-300 mb-3">{meta.subtitle}</p>
                    <p className="text-sm text-slate-200 leading-relaxed mb-3">
                      {meta.description}
                    </p>
                    <span className="text-xs px-3 py-1 rounded-full bg-black/30 text-slate-200">
                      {meta.badge}
                    </span>
                  </button>
                );
              })}
            </div>

            <section className="mt-10 bg-slate-900/70 border border-slate-700 rounded-2xl p-6">
              <div className="flex items-start gap-3">
                <Shield className="text-emerald-400 mt-1" size={22} />
                <div>
                  <h3 className="font-bold text-emerald-300 mb-2">
                    الحماية مفعّلة في كلا الوضعين
                  </h3>
                  <ul className="text-sm text-slate-300 space-y-1.5 list-disc mr-5">
                    <li>SURGICAL-HARDBLOCK يمنع write_full_html من تدمير التصميم.</li>
                    <li>DESIGN-DESTRUCTION GUARD يرفض أي إعادة بناء كاملة لقسم موجود.</li>
                    <li>BLANK PAGE DETECTOR يجبر AI على ملء الصفحات الجديدة بمحتوى حقيقي.</li>
                    <li>ORPHAN-PAGE DETECTOR يضمن ترابط الصفحات بالـnav.</li>
                    <li>SURGICAL-EDIT GUARD يبلوك إضافة أقسام لم يطلبها العميل.</li>
                    <li>Auto-Snapshot قبل كل تعديل (rollback متاح دائماً).</li>
                    <li>Post-Write Verification يكشف التكرارات تلقائياً.</li>
                  </ul>
                </div>
              </div>
            </section>

            <div className="mt-6 text-xs text-slate-500">
              💡 ملاحظة: التبديل لا يؤثر على المشاريع المفتوحة حالياً — فقط
              الطلبات الجديدة بعد التبديل.
            </div>
          </>
        )}
      </main>
    </div>
  );
}
