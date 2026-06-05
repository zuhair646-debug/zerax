import { useState } from 'react';
import { Sparkles, ChevronDown, ChevronUp } from 'lucide-react';

// Preset prompts grouped by current phase for both web + mobile game studios
const PRESETS_BY_PHASE = {
  discovery: [
    { icon: '🎯', label: 'اشرح فكرة لعبتي بالتفصيل', prompt: 'اقترح لي فكرة لعبة مبتكرة ثم اشرحها بالتفصيل: الـgenre، الجمهور المستهدف، الـcore loop، نقاط التميّز التنافسية. اكتب GDD مختصر (Game Design Document).' },
    { icon: '📋', label: 'اعمل GDD كامل', prompt: 'اعمل لي Game Design Document (GDD) كامل: نظرة عامة، الـmechanics، الـart style، الـsound design، الـstory، الـlevels، الـmonetization، خطة التطوير المرحلية.' },
    { icon: '💡', label: 'اقترح ٥ أفكار', prompt: 'اقترح لي 5 أفكار ألعاب مختلفة في فئات متنوعة (puzzle / arcade / RPG / racing / platformer) مع شرح قصير لكل فكرة ومن جمهورها المستهدف.' },
  ],
  mechanics: [
    { icon: '⚙️', label: 'صمم آليات اللعبة', prompt: 'صمّم الـcore mechanics الأساسية للعبة بالتفصيل: الحركة، القفز، الاصطدامات، الفيزياء، نظام النقاط، شرط النصر/الخسارة.' },
    { icon: '🎮', label: 'controls', prompt: 'صمّم نظام التحكم (controls) — للجوّال (touch) وللكمبيوتر (keyboard/mouse). اشرح كل زر ووظيفته.' },
    { icon: '📐', label: 'flowchart اللعب', prompt: 'اعمل flowchart نصي لمسار اللعب من بداية تشغيل اللعبة لنهايتها.' },
  ],
  characters: [
    { icon: '🎭', label: 'صمم الشخصية الرئيسية', prompt: 'صمم الشخصية الرئيسية: مظهرها، شخصيتها، قدراتها، حركاتها (animations). أعطني character sheet كامل.' },
    { icon: '👥', label: 'شخصيات NPC', prompt: 'صمّم ٣-٥ شخصيات NPC ثانوية مع وصف كل واحدة (الشكل، الدور في اللعبة، الحوار النموذجي).' },
    { icon: '🖼️', label: 'concept art', prompt: 'ولّد لي concept art (وصف بصري + توليد صور) للشخصية الرئيسية وثلاث pose مختلفة (idle, running, jumping).' },
  ],
  environment: [
    { icon: '🏞️', label: 'صمم العالم', prompt: 'صمّم البيئة الرئيسية للعبة: الـsetting، الـmood، الـcolor palette. اقترح ٣ environments مختلفة لتنوّع المستويات.' },
    { icon: '🧱', label: 'tilesets', prompt: 'صمّم tileset متكامل: الأرضيات، الجدران، العقبات، الـplatforms. أعطني وصف بصري لكل tile.' },
  ],
  assets: [
    { icon: '🎨', label: 'UI Kit', prompt: 'صمّم UI Kit متكامل: زر البدء، شريط الصحة، شاشة النصر، شاشة الخسارة، قائمة الإعدادات. أسلوب موحّد مع باقي اللعبة.' },
    { icon: '🔊', label: 'sound effects', prompt: 'اقترح ١٠ مؤثرات صوتية أساسية للعبة (jump, hit, collect coin, victory, game over، إلخ) — مع وصف كل واحدة.' },
  ],
  programming: [
    { icon: '💻', label: 'اكتب الكود الأساسي', prompt: 'اكتب الكود الأساسي للعبة جاهز للتشغيل في المتصفح. أعطني ملف index.html + JavaScript كامل + التعليقات بالعربية.' },
    { icon: '🐛', label: 'افحص الأخطاء', prompt: 'افحص الكود اللي كتبته للأخطاء المنطقية والـbugs المحتملة. اقترح إصلاحات.' },
    { icon: '⚡', label: 'حسّن الأداء', prompt: 'حسّن أداء اللعبة: تقليل الـmemory leaks، تحسين الـrendering، تسريع الـcollision detection.' },
  ],
  testing: [
    { icon: '🧪', label: 'خطة اختبار', prompt: 'اكتب خطة اختبار شاملة للعبة: test cases للـmechanics، حالات الـedge cases، اختبار التوافق مع المتصفحات.' },
    { icon: '📊', label: 'تقرير QA', prompt: 'اعمل تقرير QA: قائمة الـbugs المحتملة + درجة خطورة كل واحد + خطة الإصلاح.' },
  ],
  deployment: [
    { icon: '🚀', label: 'انشر اللعبة', prompt: 'جهّز اللعبة للنشر: ضغط الـassets، minify الكود، اكتب README، اقترح خيارات الاستضافة (Vercel/Netlify/itch.io).' },
    { icon: '📦', label: 'package final', prompt: 'حضّر ZIP فيه كل ملفات اللعبة جاهزة للتسليم النهائي مع دليل المستخدم.' },
  ],
};

/**
 * Quick Action chips that show preset prompts for the current phase.
 * Props:
 *   currentPhase — string (discovery/mechanics/.../deployment)
 *   onSelect(prompt) — called when user clicks a preset
 *   accentColor — "amber" | "blue"
 */
export default function QuickActions({ currentPhase = 'discovery', onSelect, accentColor = 'amber' }) {
  const [expanded, setExpanded] = useState(false);
  const presets = PRESETS_BY_PHASE[currentPhase] || PRESETS_BY_PHASE.discovery;
  if (!presets?.length) return null;

  const accentText = accentColor === 'blue' ? 'text-blue-300' : 'text-amber-300';
  const chipHover = accentColor === 'blue'
    ? 'hover:border-blue-400/50 hover:bg-blue-500/10'
    : 'hover:border-amber-400/50 hover:bg-amber-500/10';

  return (
    <div className="mb-2.5" data-testid="quick-actions">
      <button
        type="button"
        onClick={() => setExpanded((v) => !v)}
        className={`inline-flex items-center gap-1.5 text-xs font-bold ${accentText} hover:text-white transition-colors mb-1.5`}
        data-testid="quick-actions-toggle"
      >
        <Sparkles className="w-3.5 h-3.5" />
        <span>اقتراحات سريعة لهذه المرحلة</span>
        {expanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
      </button>
      {expanded && (
        <div className="flex flex-wrap gap-1.5">
          {presets.map((p, i) => (
            <button
              key={i}
              type="button"
              onClick={() => onSelect?.(p.prompt)}
              className={`text-xs px-2.5 py-1.5 rounded-lg bg-white/5 border border-white/10 ${chipHover} text-white/90 transition-all flex items-center gap-1.5`}
              data-testid={`quick-action-${i}`}
              title={p.prompt}
            >
              <span>{p.icon}</span>
              <span>{p.label}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
