/**
 * VrmPreview — full-screen preview page to verify a user's VRM character.
 * Accessed at /vrm-preview (no auth needed — diagnostic only).
 */
import React from 'react';
import { Link } from 'react-router-dom';
import Avatar3D from '@/components/Avatar3D';

export default function VrmPreview() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-[#1a0a2e] via-[#0a0a12] to-[#2a0a1e] text-white p-6" dir="rtl">
      <div className="max-w-6xl mx-auto">
        <div className="flex justify-between items-center mb-6">
          <h1 className="text-2xl font-black">معاينة شخصيتك 3D</h1>
          <Link to="/" className="px-4 py-2 bg-white/10 rounded-xl text-sm font-bold hover:bg-white/20" data-testid="back-home">← الرئيسية</Link>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="bg-black/40 rounded-2xl border border-amber-400/30 p-4">
            <h2 className="text-amber-300 font-black mb-2">زارا (Z.vrm)</h2>
            <div className="h-[500px] bg-gradient-to-b from-amber-500/10 to-transparent rounded-xl overflow-hidden">
              <Avatar3D
                url="/avatars-3d/zara.vrm"
                className="w-full h-full"
                dataTestId="preview-zara"
                cameraPos={[0, 1.3, 2.2]}
                fov={28}
              />
            </div>
            <p className="text-xs text-white/60 mt-2">camera: close-up upper body (y=1.3, z=2.2)</p>
          </div>

          <div className="bg-black/40 rounded-2xl border border-purple-400/30 p-4">
            <h2 className="text-purple-300 font-black mb-2">ليلى (نفس الملف حالياً)</h2>
            <div className="h-[500px] bg-gradient-to-b from-purple-500/10 to-transparent rounded-xl overflow-hidden">
              <Avatar3D
                url="/avatars-3d/layla.vrm"
                className="w-full h-full"
                dataTestId="preview-layla"
                cameraPos={[0, 1.3, 2.2]}
                fov={28}
              />
            </div>
            <p className="text-xs text-white/60 mt-2">camera: close-up upper body</p>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-6">
          <CameraTest url="/avatars-3d/zara.vrm" label="Full Body" pos={[0, 0.8, 2.5]} fov={35} />
          <CameraTest url="/avatars-3d/zara.vrm" label="Medium" pos={[0, 1.1, 2.0]} fov={30} />
          <CameraTest url="/avatars-3d/zara.vrm" label="Face Close" pos={[0, 1.5, 1.2]} fov={25} />
        </div>

        <div className="mt-8 bg-blue-500/10 border border-blue-400/30 rounded-xl p-4 text-sm">
          <p className="font-black text-blue-200 mb-2">💡 ملاحظة:</p>
          <p className="text-white/80">
            الشخصية اللي صمّمتها مرفوعة كـ <code className="bg-white/10 px-2 py-0.5 rounded">zara.vrm</code> و <code className="bg-white/10 px-2 py-0.5 rounded">layla.vrm</code> (نفس الملف مؤقتاً).
            لما تصمم ليلى (الشخصية الثانية) ارسلها لي وأنا أرفعها مكان <code className="bg-white/10 px-2 py-0.5 rounded">layla.vrm</code> الحالية.
          </p>
        </div>
      </div>
    </div>
  );
}

function CameraTest({ url, label, pos, fov }) {
  return (
    <div className="bg-black/40 rounded-2xl border border-white/10 p-3">
      <p className="text-xs font-black text-white/70 mb-2">{label} — pos: [{pos.join(', ')}], fov: {fov}</p>
      <div className="h-64 bg-black/30 rounded-lg overflow-hidden">
        <Avatar3D url={url} className="w-full h-full" cameraPos={pos} fov={fov} dataTestId={`camtest-${label}`} />
      </div>
    </div>
  );
}
