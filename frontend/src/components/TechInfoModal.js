import React from 'react';
import { X, Check, AlertTriangle, Target, Box, Cpu, Gauge } from 'lucide-react';

// ─── Detailed info for every programming type (web + mobile games) ───
export const TECH_INFO = {
  // ═══════════ WEB GAMES ═══════════
  html5_canvas: {
    title: 'HTML5 Canvas (Pure)',
    description: 'برمجة مباشرة بـJavaScript خام بدون أي مكتبة. أنت تتحكم في كل بكسل — أعلى مرونة، لكن أكثر كود.',
    features: ['تحكّم كامل في الرسم', 'بدون اعتمادات خارجية (مكتبات صفر)', 'حجم النهائي صغير جداً (~50KB)', 'أسرع تنفيذ ممكن', 'مناسب لتعلّم الأساسيات'],
    drawbacks: ['تكتب كل شي من الصفر (فيزياء، اصطدامات، إلخ)', 'وقت تطوير أطول', 'لا يدعم 3D مباشرة'],
    bestFor: 'ألعاب 2D بسيطة، أدوات تعليمية، تجارب فنية، حالات تبي حجم خفيف جداً.',
    badges: ['2D', 'سريع', 'خفيف'],
  },
  phaser: {
    title: 'Phaser.js',
    description: 'محرّك ألعاب 2D الأكثر شعبية في العالم للويب. يجي بكل شي جاهز: فيزياء، صوت، animations، tile maps.',
    features: ['فيزياء جاهزة (Arcade + Matter)', 'دعم ممتاز لـsprites + animations', 'صوت + موسيقى مدمج', 'tilemaps + tilesets للمستويات', 'مجتمع ضخم + أمثلة كثيرة'],
    drawbacks: ['حجم المكتبة أكبر (~1MB)', 'منحنى تعلم متوسط', 'لا يدعم 3D (للويب 3D استخدم Three.js)'],
    bestFor: 'ألعاب 2D احترافية: platformers، puzzles، RPG، arcade — أي شي يتنافس مع ألعاب App Store الـ2D.',
    badges: ['2D Pro', 'فيزياء', 'الأشهر'],
  },
  threejs: {
    title: 'Three.js',
    description: 'المعيار الذهبي للـ3D في المتصفح. يستخدم WebGL تحت الغطاء، ويسمح لك ببناء عوالم 3D كاملة (مثل ألعاب Steam البسيطة).',
    features: ['دعم 3D كامل (مودلز، textures، إضاءة)', 'يدعم WebXR (VR + AR)', 'استيراد مودلز Blender + glTF + FBX', 'فيزياء عبر إضافات (Cannon.js / Ammo)', 'يشتغل على الجوّال والكمبيوتر'],
    drawbacks: ['منحنى تعلّم أعلى من 2D', 'يستهلك بطارية الجوّال أسرع', 'حاجة لمعرفة بأساسيات 3D (vectors, materials)'],
    bestFor: 'ألعاب 3D واقعية في المتصفح، تجارب VR/AR، تصور المنتجات ثلاثي الأبعاد، ألعاب racing بسيطة.',
    badges: ['3D Full', 'VR/AR', 'WebGL'],
  },
  unity_webgl: {
    title: 'Unity WebGL Export',
    description: 'تبني لعبتك بمحرّك Unity الاحترافي (مثل ألعاب Steam) ثم تصدّرها كـbuild للمتصفح. أقوى محرّك متاح للويب.',
    features: ['محرّك AAA quality — نفس اللي يستخدمه استوديوهات كبار', 'دعم 3D كامل بأعلى مستوى', 'Asset Store ضخم (مودلز، شخصيات، أصوات جاهزة)', 'AI + Networking + Multiplayer', 'فيزياء PhysX جودة الاستوديو'],
    drawbacks: ['حجم Build الويب كبير (5-50MB)', 'وقت تحميل أبطأ عند الفتح', 'يحتاج تثبيت Unity Editor', 'بعض الميزات لا تشتغل في المتصفح'],
    bestFor: 'الناشرين الجادّين اللي يبون نقل ألعابهم من Unity للويب، أو يبون أعلى جودة 3D ممكنة في المتصفح.',
    badges: ['3D AAA', 'Asset Store', 'احترافي'],
  },
  custom: {
    title: 'Custom Framework',
    description: 'إطار عمل خاص بك — استخدم PixiJS، Babylon.js، PlayCanvas، أو أي مكتبة. مرونة كاملة للخبراء.',
    features: ['أي مكتبة تبيها (PixiJS، Babylon.js، إلخ)', 'تحكّم كامل في bundle size', 'دمج مع React/Vue/Svelte', 'يدعم 2D أو 3D حسب اختيارك', 'مناسب لتجارب فريدة'],
    drawbacks: ['تحتاج خبرة تقنية أعلى', 'لازم تختار وتدير مكتباتك بنفسك', 'دعم أقل من المسارات الجاهزة'],
    bestFor: 'المطوّرين الخبراء، الفرق التي تعرف الـstack المثالي لها، تجارب مهجّنة (مثلاً React + WebGL).',
    badges: ['مرن', 'خبراء', 'أي 2D/3D'],
  },

  // ═══════════ APP GAMES ═══════════
  flutter: {
    title: 'Flutter',
    description: 'محرّك Google لبناء تطبيقات تشتغل على Android + iOS من كود واحد. ممتاز للألعاب 2D وتطبيقات بألعاب صغيرة.',
    features: ['كود واحد لـAndroid + iOS + Web', 'واجهات حديثة وسريعة (60fps طبيعي)', 'مدعوم من Google', 'Hot Reload أثناء التطوير', 'دعم Flame engine للألعاب 2D'],
    drawbacks: ['ضعيف لألعاب 3D الثقيلة', 'حجم التطبيق أكبر من Native (~15MB+)', 'لغة Dart مش شائعة'],
    bestFor: 'ألعاب 2D خفيفة، ألعاب puzzle، casual games، Hyper-casual games اللي تبي تنزل في المتجرين.',
    badges: ['2D', 'Android+iOS', 'سريع'],
  },
  native_android: {
    title: 'Native Android (Kotlin)',
    description: 'بناء لعبة بـKotlin مباشرة على Android فقط. أعلى أداء ممكن على Android — مناسب للألعاب التنافسية.',
    features: ['أداء أصلي بنسبة 100%', 'وصول كامل لـAPIs أندرويد (sensors، Bluetooth، NFC)', 'حجم تطبيق صغير', 'تكامل مع Google Play Games', 'مدعوم رسمياً من Google'],
    drawbacks: ['يشتغل على Android فقط (لا iOS)', 'تحتاج Android Studio', 'منحنى تعلّم Kotlin'],
    bestFor: 'الألعاب التي تستهدف السوق الأندرويد فقط، الألعاب التنافسية اللي تبي أعلى أداء.',
    badges: ['Native', 'Android فقط', 'أقوى أداء'],
  },
  native_ios: {
    title: 'Native iOS (Swift)',
    description: 'بناء لعبة بـSwift مباشرة على iOS فقط. أعلى أداء على iPhone/iPad — مناسب لألعاب App Store الفاخرة.',
    features: ['أداء iOS الكامل', 'وصول لـMetal API (3D فاخر)', 'تكامل عميق مع iCloud + Game Center', 'يدعم Vision Pro', 'تجربة Apple-quality'],
    drawbacks: ['iOS فقط (لا Android)', 'تحتاج Mac + Xcode', 'حساب Apple Developer ($99/سنة) للنشر'],
    bestFor: 'الألعاب التي تستهدف جمهور iOS الفاخر (premium games)، ألعاب Apple Arcade.',
    badges: ['Native', 'iOS فقط', 'Metal 3D'],
  },
  react_native: {
    title: 'React Native',
    description: 'تطبيق واحد بـJavaScript يشتغل على Android + iOS. ممتاز لألعاب 2D خفيفة + تطبيقات بألعاب صغيرة جوّاها.',
    features: ['كود واحد لـAndroid + iOS', 'JavaScript شائع وسهل التعلم', 'يعيد استخدام مكتبات React/web', 'دمج مع AR (Viro)', 'مجتمع ضخم جداً'],
    drawbacks: ['أبطأ من Native للألعاب الثقيلة', 'ضعيف لـ3D متقدم', 'يحتاج "bridges" لميزات النظام المتقدمة'],
    bestFor: 'ألعاب 2D خفيفة، casual games، تطبيقات فيها مكوّن لعبة صغير (مثل تطبيق تعليمي بألعاب).',
    badges: ['2D', 'Cross-platform', 'JavaScript'],
  },
  unity: {
    title: 'Unity Engine',
    description: 'المحرّك الأشهر في العالم للألعاب — يستخدمه أكثر من 50% من ألعاب الجوّال الناجحة. يدعم 2D و3D + AR + VR + multiplayer.',
    features: ['Asset Store ضخم (آلاف الأصول الجاهزة)', '3D AAA-quality (مثل ألعاب Steam)', 'تصدير لـAndroid + iOS + PC + Console', 'AR Foundation + XR كامل', 'Networking + Multiplayer جاهز'],
    drawbacks: ['حجم التطبيق كبير (50MB+)', 'منحنى تعلّم متوسط-عالي', 'الإصدار المجاني محدود الإيرادات ($200K/سنة)'],
    bestFor: 'الألعاب الجادّة 3D، استوديوهات الألعاب الناشئة، الألعاب التي تبي تنافس Fortnite/PUBG mobile.',
    badges: ['3D AAA', 'Asset Store', 'الأشهر'],
  },
  godot: {
    title: 'Godot Engine',
    description: 'محرّك ألعاب مفتوح المصدر 100% — مجاني تماماً بدون رسوم. منافس Unity الصاعد، خفيف وسريع.',
    features: ['مجاني 100% — بدون رسوم على أي إيراد', 'مفتوح المصدر — يمكنك تعديله', 'خفيف جداً (~60MB Editor)', 'يدعم 2D و3D', 'GDScript لغة بسيطة (مشابهة Python)'],
    drawbacks: ['Asset Store أصغر من Unity', 'دعم Mobile أقل نضجاً (تحسّن بسرعة)', 'بعض ميزات 3D أقل من Unity'],
    bestFor: 'الاستوديوهات المستقلة (indie)، الألعاب 2D، المطوّرين اللي ما يبون يدفعون رسوم Unity.',
    badges: ['مجاني', 'مفتوح', '2D + 3D'],
  },
};

export default function TechInfoModal({ techId, onClose, onSelect }) {
  const info = TECH_INFO[techId];
  if (!info) return null;

  return (
    <div
      className="fixed inset-0 z-[200] flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-in fade-in duration-200"
      onClick={onClose}
      data-testid="tech-info-modal"
    >
      <div
        className="relative w-full max-w-lg max-h-[88vh] overflow-y-auto rounded-2xl border border-amber-500/20 bg-gradient-to-br from-[#13131c] to-[#0a0a12] shadow-2xl shadow-amber-500/10 p-6 sm:p-7"
        onClick={(e) => e.stopPropagation()}
        dir="rtl"
      >
        {/* Close */}
        <button
          type="button"
          onClick={onClose}
          className="absolute top-3 left-3 w-8 h-8 rounded-full bg-white/5 hover:bg-white/10 border border-white/10 flex items-center justify-center transition-all hover:scale-110"
          data-testid="tech-info-close-btn"
          aria-label="إغلاق"
        >
          <X className="w-4 h-4 text-white/80" />
        </button>

        {/* Title + badges */}
        <div className="mb-5 pl-10">
          <div className="text-[10px] font-bold tracking-widest text-amber-300/70 mb-1">📘 تعرّف على هذه التقنية</div>
          <h3 className="text-xl sm:text-2xl font-black text-white leading-tight mb-2" data-testid="tech-info-title">
            {info.title}
          </h3>
          {info.badges && (
            <div className="flex flex-wrap gap-1.5">
              {info.badges.map((b, i) => (
                <span key={i} className="text-[10px] px-2 py-0.5 rounded-full bg-amber-500/15 border border-amber-400/30 text-amber-200 font-bold">
                  {b}
                </span>
              ))}
            </div>
          )}
        </div>

        {/* Description */}
        <div className="mb-5 p-4 rounded-xl bg-white/[0.03] border border-white/10">
          <p className="text-sm sm:text-base text-white/85 leading-relaxed">{info.description}</p>
        </div>

        {/* Features */}
        <div className="mb-4">
          <div className="flex items-center gap-2 mb-2.5">
            <div className="w-6 h-6 rounded-full bg-emerald-500/20 border border-emerald-400/40 flex items-center justify-center">
              <Check className="w-3.5 h-3.5 text-emerald-300" />
            </div>
            <h4 className="text-sm font-black text-emerald-300">المميزات</h4>
          </div>
          <ul className="space-y-1.5 pr-2">
            {info.features.map((f, i) => (
              <li key={i} className="text-xs sm:text-sm text-white/80 flex items-start gap-2">
                <span className="text-emerald-400 mt-1">•</span>
                <span>{f}</span>
              </li>
            ))}
          </ul>
        </div>

        {/* Drawbacks */}
        <div className="mb-4">
          <div className="flex items-center gap-2 mb-2.5">
            <div className="w-6 h-6 rounded-full bg-amber-500/20 border border-amber-400/40 flex items-center justify-center">
              <AlertTriangle className="w-3.5 h-3.5 text-amber-300" />
            </div>
            <h4 className="text-sm font-black text-amber-300">السلبيات / القيود</h4>
          </div>
          <ul className="space-y-1.5 pr-2">
            {info.drawbacks.map((d, i) => (
              <li key={i} className="text-xs sm:text-sm text-white/80 flex items-start gap-2">
                <span className="text-amber-400 mt-1">•</span>
                <span>{d}</span>
              </li>
            ))}
          </ul>
        </div>

        {/* Best For */}
        <div className="mb-5 p-4 rounded-xl bg-gradient-to-br from-cyan-500/10 to-blue-500/10 border border-cyan-400/20">
          <div className="flex items-center gap-2 mb-2">
            <Target className="w-4 h-4 text-cyan-300" />
            <h4 className="text-sm font-black text-cyan-300">الأفضل لمن؟</h4>
          </div>
          <p className="text-xs sm:text-sm text-white/85 leading-relaxed">{info.bestFor}</p>
        </div>

        {/* CTA */}
        {onSelect && (
          <button
            onClick={() => { onSelect(techId); onClose(); }}
            className="w-full bg-gradient-to-r from-amber-500 to-orange-600 hover:from-amber-400 hover:to-orange-500 text-black font-black rounded-xl py-3 transition-all"
            data-testid="tech-info-select-btn"
          >
            ✓ اختر {info.title}
          </button>
        )}
      </div>
    </div>
  );
}
