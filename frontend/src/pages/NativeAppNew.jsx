/**
 * Native App Builder — creator screen.
 *
 * Mirrors FreeBuild's "from scratch" flow but locks the project into mode="app"
 * (PWA / native app) with a chosen platform (iPhone / Android / both).
 *
 * On submit it creates a freebuild_project with mode='app' + platform metadata,
 * then redirects into the FreeBuildChat experience — which auto-detects the
 * mode and switches the live preview to a phone-frame.
 */
import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Smartphone, Apple, Bot, ArrowRight, Sparkles } from 'lucide-react';
import { Card } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Textarea } from '../components/ui/textarea';
import { toast } from 'sonner';

const API = process.env.REACT_APP_BACKEND_URL;

const PLATFORMS = [
  { id: 'ios',     label: 'iPhone',   icon: Apple,      tag: 'PWA + APK iOS',      color: 'from-zinc-200 to-zinc-400' },
  { id: 'android', label: 'Android',  icon: Smartphone, tag: 'PWA + APK',           color: 'from-green-400 to-emerald-500' },
  { id: 'both',    label: 'الاثنين',  icon: Bot,        tag: 'Universal PWA',       color: 'from-purple-400 to-pink-500' },
];

export default function NativeAppNew() {
  const navigate = useNavigate();
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [platform, setPlatform] = useState('both');
  const [submitting, setSubmitting] = useState(false);

  const token = localStorage.getItem('token') || sessionStorage.getItem('token');

  const handleCreate = async () => {
    if (!name.trim()) {
      toast.error('اكتب اسم التطبيق');
      return;
    }
    setSubmitting(true);
    try {
      const r = await fetch(`${API}/api/freebuild-chat/project`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          name: name.trim(),
          description: description.trim(),
          mode: 'app',
          // platform is custom metadata — backend will store it on the project doc
          platform,
        }),
      });
      if (!r.ok) {
        const t = await r.text();
        throw new Error(t.slice(0, 200));
      }
      const d = await r.json();
      toast.success('🚀 تم إنشاء المشروع — ندخل التصميم الآن');
      navigate(`/freebuild/chat/${d.id}?platform=${platform}`);
    } catch (e) {
      toast.error(`فشل الإنشاء: ${e.message}`);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100" dir="rtl" data-testid="native-new">
      <div className="max-w-5xl mx-auto px-4 py-10">
        <div className="text-center mb-10">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-purple-500/10 border border-purple-400/30 text-purple-300 text-xs mb-4">
            <Sparkles className="w-3.5 h-3.5" />
            <span>تطبيق جوال من الصفر</span>
          </div>
          <h1 className="text-3xl md:text-5xl font-extrabold mb-3 bg-gradient-to-r from-purple-300 via-pink-300 to-amber-300 bg-clip-text text-transparent">
            اصنع تطبيقك في دقائق
          </h1>
          <p className="text-zinc-400 max-w-2xl mx-auto">
            اكتب فكرتك بكلمات بسيطة، اختر النظام، وزنركس يبني لك تطبيق PWA قابل للتثبيت على iPhone و Android فوراً — بدون App Store.
          </p>
        </div>

        <div className="grid md:grid-cols-3 gap-6">
          {/* RIGHT side (RTL): Title + description input */}
          <div className="md:col-span-2 space-y-4">
            <Card className="bg-zinc-900 border-zinc-800 p-5">
              <label className="text-xs font-bold text-zinc-400 block mb-1.5">اسم التطبيق</label>
              <Input
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="مثال: تطبيق متجر العود، تطبيق متابعة لياقة، تطبيق توصيل…"
                className="bg-zinc-950 border-zinc-700 text-base"
                data-testid="app-name-input"
                autoFocus
              />
              <label className="text-xs font-bold text-zinc-400 block mt-4 mb-1.5">وصف مختصر (اختياري)</label>
              <Textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="اشرح فكرة التطبيق وأهم الميزات (يقدر يضيف الذكاء بنفسه إذا تركتها فاضية)"
                rows={4}
                className="bg-zinc-950 border-zinc-700"
                data-testid="app-desc-input"
              />
            </Card>

            <Button
              onClick={handleCreate}
              disabled={submitting || !name.trim()}
              className="w-full h-12 text-base font-bold bg-gradient-to-r from-purple-500 via-pink-500 to-amber-500 hover:opacity-90"
              data-testid="create-app-btn"
            >
              {submitting ? 'جاري الإنشاء...' : (
                <>
                  ابدأ التصميم
                  <ArrowRight className="w-5 h-5 mr-2" />
                </>
              )}
            </Button>
          </div>

          {/* LEFT side (RTL = left): Platform selector */}
          <div>
            <Card className="bg-zinc-900 border-zinc-800 p-5 sticky top-4">
              <label className="text-xs font-bold text-zinc-400 block mb-3">النظام المستهدف</label>
              <div className="space-y-2.5">
                {PLATFORMS.map((p) => {
                  const Icon = p.icon;
                  const selected = platform === p.id;
                  return (
                    <button
                      key={p.id}
                      onClick={() => setPlatform(p.id)}
                      data-testid={`platform-${p.id}`}
                      className={`w-full flex items-center gap-3 p-3 rounded-xl border-2 transition-all ${
                        selected
                          ? 'border-purple-500 bg-purple-500/10'
                          : 'border-zinc-700 hover:border-zinc-600 bg-zinc-950'
                      }`}
                    >
                      <span className={`w-10 h-10 rounded-full flex items-center justify-center bg-gradient-to-br ${p.color}`}>
                        <Icon className="w-5 h-5 text-zinc-900" />
                      </span>
                      <span className="text-right flex-1">
                        <div className="font-bold text-sm">{p.label}</div>
                        <div className="text-[10px] text-zinc-400">{p.tag}</div>
                      </span>
                      {selected && (
                        <span className="w-2.5 h-2.5 rounded-full bg-purple-400" />
                      )}
                    </button>
                  );
                })}
              </div>
              <p className="text-[11px] text-zinc-500 mt-4 leading-relaxed">
                💡 الذكاء سيحدد البرمجة الأنسب تلقائياً — لا تحتاج تختار framework.
              </p>
            </Card>
          </div>
        </div>

        {/* Trust strip */}
        <div className="mt-10 grid md:grid-cols-3 gap-3 text-center">
          <div className="bg-zinc-900/50 rounded-lg p-3 text-xs text-zinc-400">
            <div className="text-purple-300 font-bold mb-1">⚡ PWA فوري</div>
            يثبّت على الجوال مباشرة بدون متجر تطبيقات
          </div>
          <div className="bg-zinc-900/50 rounded-lg p-3 text-xs text-zinc-400">
            <div className="text-pink-300 font-bold mb-1">📦 APK / IPA حسب الطلب</div>
            تصدير native packages للنشر على المتاجر
          </div>
          <div className="bg-zinc-900/50 rounded-lg p-3 text-xs text-zinc-400">
            <div className="text-amber-300 font-bold mb-1">🛡️ Guardian يحرس</div>
            مشرف ذكي يصحّح الكود قبل ما يوصلك مكسور
          </div>
        </div>
      </div>
    </div>
  );
}
