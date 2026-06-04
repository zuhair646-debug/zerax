import React from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, Gamepad2, Zap, Sparkles, Box, Palette, Move3d } from 'lucide-react';

export default function GamesHub({ user, kind = 'web' }) {
  const nav = useNavigate();
  const isWeb = kind === 'web';

  const tools = isWeb
    ? [
        { icon: Zap, label: 'Phaser 3', desc: 'محرك 2D HTML5 الأشهر', tag: 'مفتوح المصدر' },
        { icon: Box, label: 'Three.js', desc: 'WebGL ثلاثي الأبعاد', tag: '3D' },
        { icon: Sparkles, label: 'PixiJS', desc: 'رسم 2D فائق الأداء', tag: 'سريع' },
        { icon: Palette, label: 'p5.js', desc: 'فن إبداعي تفاعلي', tag: 'تعليمي' },
      ]
    : [
        { icon: Box, label: 'Unity', desc: 'محرك ألعاب احترافي 2D/3D', tag: 'الأشهر عالمياً' },
        { icon: Move3d, label: 'Godot', desc: 'مفتوح المصدر — مرن', tag: 'مجاني' },
        { icon: Sparkles, label: 'Unreal Engine', desc: 'رسومات هوليوود', tag: 'AAA' },
        { icon: Palette, label: 'Blender', desc: 'نمذجة + رسم + Animation', tag: '3D Studio' },
      ];

  const palette = isWeb
    ? { color: '#84cc16', bg: 'from-lime-500/15 to-green-500/5', border: 'border-lime-500/30' }
    : { color: '#22c55e', bg: 'from-green-500/15 to-emerald-500/5', border: 'border-green-500/30' };

  return (
    <div className="min-h-screen bg-gradient-to-b from-zinc-950 via-black to-zinc-950 text-zinc-100">
      <div className="border-b border-zinc-800/60 sticky top-0 z-30 bg-zinc-950/85 backdrop-blur-xl">
        <div className="max-w-6xl mx-auto px-5 py-4 flex items-center gap-4">
          <button onClick={() => nav('/')} className="p-2 hover:bg-zinc-800 rounded-lg text-zinc-400">
            <ArrowLeft className="w-5 h-5" />
          </button>
          <div className="flex-1">
            <div className="flex items-center gap-2">
              <Gamepad2 className="w-5 h-5" style={{ color: palette.color }} />
              <h1 className="text-xl font-bold">
                {isWeb ? 'مواقع الألعاب' : 'تطبيقات الألعاب'}
              </h1>
              <span
                className="text-[10px] px-2 py-0.5 rounded-full border"
                style={{ borderColor: `${palette.color}40`, color: palette.color, background: `${palette.color}10` }}
              >
                قريباً
              </span>
            </div>
            <p className="text-xs text-zinc-500 mt-0.5">
              {isWeb
                ? 'ألعاب HTML5 و WebGL تشتغل مباشرة في المتصفح'
                : 'ألعاب iOS و Android بأدوات تطوير 3D متكاملة'}
            </p>
          </div>
        </div>
      </div>

      <div className="max-w-6xl mx-auto px-5 py-8">
        <div className="text-center mb-10">
          <div
            className="inline-flex p-4 rounded-2xl mb-4"
            style={{ background: `${palette.color}15`, border: `1px solid ${palette.color}40` }}
          >
            <Gamepad2 className="w-10 h-10" style={{ color: palette.color }} />
          </div>
          <h2 className="text-3xl sm:text-4xl font-black mb-3">
            {isWeb ? 'استوديو ألعاب المتصفح' : 'استوديو ألعاب الموبايل'}
          </h2>
          <p className="text-zinc-400 text-sm max-w-xl mx-auto leading-relaxed">
            {isWeb
              ? 'قسم متكامل لتطوير ألعاب HTML5 تشتغل على أي متصفح بدون تنزيل. هنحضر لك المحركات والذكاء يصمم لك المنطق واللعب.'
              : 'قسم متخصص لتطوير ألعاب iOS و Android باستخدام أقوى محركات الألعاب 2D و 3D. يشمل أدوات النمذجة والرسم والـ animation الكاملة.'}
          </p>
        </div>

        <div className="mb-8">
          <h3 className="text-sm font-bold text-zinc-400 uppercase tracking-wider mb-3">
            الأدوات المخططة
          </h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {tools.map((t, i) => {
              const Icon = t.icon;
              return (
                <div
                  key={i}
                  className={`rounded-xl border ${palette.border} bg-gradient-to-br ${palette.bg} p-4`}
                >
                  <div className="flex items-start gap-3">
                    <div
                      className="p-2.5 rounded-lg"
                      style={{ background: `${palette.color}20` }}
                    >
                      <Icon className="w-5 h-5" style={{ color: palette.color }} />
                    </div>
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <h4 className="font-bold">{t.label}</h4>
                        <span className="text-[10px] px-1.5 py-0.5 bg-zinc-800 rounded text-zinc-400">
                          {t.tag}
                        </span>
                      </div>
                      <p className="text-xs text-zinc-400">{t.desc}</p>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {!isWeb && (
          <div className="rounded-xl border border-zinc-800 bg-zinc-900/40 p-5 mb-8">
            <h3 className="text-sm font-bold mb-3 flex items-center gap-2">
              <Move3d className="w-4 h-4 text-emerald-400" /> أدوات الرسم ثلاثي الأبعاد
            </h3>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs">
              {[
                'نمذجة 3D من نص',
                'تحريك الشخصيات',
                'إضاءة ذكية',
                'مواد و textures',
                'فيزياء واقعية',
                'تصدير لـ Unity/Unreal',
                'AR/VR support',
                'Optimization تلقائي',
              ].map((f, i) => (
                <div key={i} className="px-2.5 py-2 bg-zinc-800/60 rounded text-zinc-300">
                  ✓ {f}
                </div>
              ))}
            </div>
          </div>
        )}

        <div className="rounded-xl border border-zinc-800 bg-zinc-900/30 p-5 text-center">
          <div className="text-xs text-zinc-500 mb-2">⏳ هذا القسم قيد التطوير</div>
          <p className="text-sm text-zinc-400">
            الذكاء الصناعي المختص لهذا القسم جاهز ومُعتمد. نعمل حالياً على إنهاء الأدوات والواجهات.
          </p>
          <button
            onClick={() => nav('/')}
            className="mt-4 px-4 py-2 text-xs bg-zinc-800 hover:bg-zinc-700 rounded-lg transition"
            data-testid="games-back-home"
          >
            العودة للرئيسية
          </button>
        </div>
      </div>
    </div>
  );
}
