import { useState } from 'react';
import { Palette, Check, Loader2 } from 'lucide-react';
import { toast } from 'sonner';

const API = process.env.REACT_APP_BACKEND_URL;

const PROFILES = [
  { id: 'realistic', label: '📸 واقعي AAA', desc: 'Unreal Engine 5 — photorealistic' },
  { id: 'stylized',  label: '🎮 Fortnite Stylized', desc: 'Stylized realism + cinematic' },
  { id: 'anime',     label: '🌸 أنمي Genshin', desc: 'Cel-shaded anime, vibrant' },
  { id: 'low_poly',  label: '🔷 Low-Poly', desc: 'Modern flat-shaded, clean' },
  { id: 'pixel',     label: '🕹️ Pixel Art', desc: '32-bit retro premium' },
];

export default function StyleProfileSelector({ projectId, current = 'stylized', onChange, accentColor = 'amber' }) {
  const token = localStorage.getItem('token');
  const [active, setActive] = useState(current);
  const [saving, setSaving] = useState(null);

  const accent = {
    amber: { ring: 'ring-amber-500/50', bg: 'bg-amber-500/15', text: 'text-amber-200', border: 'border-amber-400/40' },
    blue:  { ring: 'ring-blue-500/50',  bg: 'bg-blue-500/15',  text: 'text-blue-200',  border: 'border-blue-400/40' },
  }[accentColor] || { ring: 'ring-amber-500/50', bg: 'bg-amber-500/15', text: 'text-amber-200', border: 'border-amber-400/40' };

  const apply = async (id) => {
    setSaving(id);
    try {
      const r = await fetch(`${API}/api/games/project/${projectId}/style-profile`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ style_profile: id }),
      });
      if (!r.ok) throw new Error('failed');
      setActive(id);
      toast.success('🎨 تم تغيير style profile');
      onChange?.(id);
    } catch (_) {
      toast.error('فشل التغيير');
    } finally {
      setSaving(null);
    }
  };

  return (
    <div className="space-y-2" data-testid="style-profile-selector">
      <div className="flex items-center gap-2 text-sm font-bold text-zinc-300">
        <Palette className="w-4 h-4" />
        <span>اختر الـ Style — كل صورة تنولّد راح تتبع هذا الـ profile</span>
      </div>
      <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
        {PROFILES.map(p => {
          const isActive = active === p.id;
          const isLoading = saving === p.id;
          return (
            <button
              key={p.id}
              type="button"
              onClick={() => apply(p.id)}
              disabled={isLoading}
              data-testid={`style-profile-${p.id}`}
              className={`text-right p-3 rounded-lg border transition-all ${
                isActive
                  ? `${accent.bg} ${accent.border} ${accent.text} ring-1 ${accent.ring}`
                  : 'bg-black/30 border-white/10 hover:border-white/20 text-zinc-300'
              }`}
            >
              <div className="flex items-center justify-between gap-2">
                <span className="font-bold text-sm">{p.label}</span>
                {isLoading ? <Loader2 className="w-3.5 h-3.5 animate-spin" />
                 : isActive ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : null}
              </div>
              <div className="text-[10px] opacity-70 mt-1">{p.desc}</div>
            </button>
          );
        })}
      </div>
    </div>
  );
}
