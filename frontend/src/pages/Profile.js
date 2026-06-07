import React, { useEffect, useState } from 'react';
import { Navbar } from '@/components/Navbar';
import { BackButton } from '@/components/BackButton';
import { useNavigate } from 'react-router-dom';
import { User, Mail, Lock, Smartphone, Crown, Sparkles, Calendar } from 'lucide-react';
import { toast } from 'sonner';

const Profile = ({ user, setUser }) => {
  const navigate = useNavigate();
  const [name, setName] = useState(user?.name || '');
  const [saving, setSaving] = useState(false);

  useEffect(() => { if (user?.name) setName(user.name); }, [user]);

  const saveName = async () => {
    if (!name.trim() || name === user?.name) return;
    setSaving(true);
    const token = localStorage.getItem('token');
    try {
      const r = await fetch(`${process.env.REACT_APP_BACKEND_URL}/api/auth/me`, {
        method: 'PATCH',
        headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({ name }),
      });
      if (r.ok) {
        const updated = await r.json();
        if (setUser) setUser(updated);
        toast.success('تم حفظ الاسم');
      } else {
        toast.info('تم حفظ الاسم محلياً');
        if (setUser) setUser({ ...user, name });
      }
    } catch (e) {
      toast.info('تم حفظ الاسم محلياً');
      if (setUser) setUser({ ...user, name });
    }
    setSaving(false);
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-[#0a0a14] via-[#0a0a18] to-[#0a0a12]" data-testid="profile-page">
      <Navbar user={user} setUser={setUser} transparent />
      <div className="container mx-auto px-4 md:px-8 max-w-3xl pt-24 pb-12">
        <div className="mb-6"><BackButton to="/dashboard" label="لوحة التحكم" /></div>

        <div className="mb-8">
          <h1 className="text-3xl md:text-4xl font-black text-white flex items-center gap-3">
            <User className="w-8 h-8 text-slate-400" />
            ملفي الشخصي
            {user?.is_owner && <Crown className="w-7 h-7 text-amber-400" />}
          </h1>
          <p className="text-gray-400 text-sm mt-1">إدارة معلوماتك وأمان حسابك</p>
        </div>

        {/* Profile card */}
        <div className="rounded-2xl bg-gradient-to-br from-slate-800/60 to-slate-900/60 border border-slate-700 p-6 mb-6">
          <div className="flex items-start gap-4 mb-6">
            <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-amber-500 to-orange-600 flex items-center justify-center text-3xl font-black text-black">
              {(user?.name || 'U').charAt(0).toUpperCase()}
            </div>
            <div className="flex-1">
              <h2 className="text-xl font-black text-white mb-1">{user?.name || 'مستخدم'}</h2>
              <p className="text-gray-400 text-sm flex items-center gap-1">
                <Mail className="w-3.5 h-3.5" /> {user?.email}
              </p>
              {user?.is_owner ? (
                <span className="inline-block mt-2 px-3 py-1 rounded-full bg-amber-500/20 text-amber-300 text-xs font-bold">
                  مالك المنصة · وصول كامل مجاني
                </span>
              ) : user?.subscription_type ? (
                <span className="inline-block mt-2 px-3 py-1 rounded-full bg-emerald-500/20 text-emerald-300 text-xs font-bold">
                  مشترك · {user.subscription_type === 'images' ? 'باقة الصور' : 'باقة الفيديو'}
                </span>
              ) : (
                <span className="inline-block mt-2 px-3 py-1 rounded-full bg-slate-700 text-gray-400 text-xs font-bold">
                  حساب مجاني
                </span>
              )}
            </div>
          </div>

          {/* Editable name */}
          <div>
            <label className="text-xs font-bold text-gray-400 mb-1.5 block">الاسم</label>
            <div className="flex gap-2">
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="flex-1 bg-slate-900/70 border border-slate-700 rounded-lg px-4 py-2.5 text-white text-sm"
                data-testid="profile-name-input"
              />
              <button
                type="button"
                onClick={saveName}
                disabled={saving || name === user?.name || !name.trim()}
                className="navbar-btn-primary px-5 py-2.5 rounded-lg text-sm font-black text-black disabled:opacity-40"
                data-testid="profile-save-btn"
              >
                {saving ? 'جاري الحفظ...' : 'حفظ'}
              </button>
            </div>
          </div>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-2 gap-3 mb-6">
          <div className="rounded-xl bg-gradient-to-br from-amber-500/15 to-yellow-700/5 border border-amber-500/25 p-4">
            <Sparkles className="w-5 h-5 text-amber-400 mb-2" />
            <p className="text-2xl font-black text-white">{user?.credits || 0}</p>
            <p className="text-xs text-amber-200/70">رصيد النقاط</p>
          </div>
          <div className="rounded-xl bg-gradient-to-br from-blue-500/15 to-cyan-700/5 border border-blue-500/25 p-4">
            <Calendar className="w-5 h-5 text-blue-400 mb-2" />
            <p className="text-base font-black text-white truncate">
              {user?.created_at ? new Date(user.created_at).toLocaleDateString('ar-SA') : '—'}
            </p>
            <p className="text-xs text-blue-200/70">تاريخ التسجيل</p>
          </div>
        </div>

        {/* Security */}
        <div className="rounded-2xl bg-slate-800/40 border border-slate-700 p-5 mb-4">
          <h3 className="text-white font-black text-sm mb-4 flex items-center gap-2">
            <Lock className="w-4 h-4 text-amber-400" /> الأمان
          </h3>
          <button
            type="button"
            onClick={() => toast.info('قريباً: تغيير كلمة المرور من هنا')}
            className="navbar-btn w-full text-right p-3 rounded-lg border border-slate-700 bg-slate-900/40 text-gray-300 text-sm font-medium flex items-center justify-between"
          >
            <span>تغيير كلمة المرور</span>
            <Lock className="w-4 h-4 text-gray-500" />
          </button>
        </div>

        {/* Devices */}
        <div className="rounded-2xl bg-slate-800/40 border border-slate-700 p-5">
          <h3 className="text-white font-black text-sm mb-4 flex items-center gap-2">
            <Smartphone className="w-4 h-4 text-amber-400" /> الأجهزة المتصلة
          </h3>
          <div className="flex items-center gap-3 p-3 rounded-lg bg-slate-900/40">
            <Smartphone className="w-8 h-8 text-emerald-400" />
            <div className="flex-1">
              <p className="text-white text-sm font-bold">هذا الجهاز</p>
              <p className="text-gray-400 text-xs">جلسة نشطة الآن</p>
            </div>
            <span className="px-2 py-1 rounded-full bg-emerald-500/20 text-emerald-300 text-[10px] font-bold">نشط</span>
          </div>
          <p className="text-xs text-gray-500 mt-3 text-center">قريباً: عرض كل الأجهزة + إدارة الجلسات</p>
        </div>
      </div>
    </div>
  );
};

export default Profile;
