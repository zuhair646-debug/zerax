import React, { useState, useEffect } from 'react';
import { useNavigate, Link, useSearchParams } from 'react-router-dom';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { toast } from 'sonner';
import { ZitexLogo } from '@/components/Navbar';
import { Gift, Sparkles } from 'lucide-react';

const RegisterPage = ({ setUser }) => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [loading, setLoading] = useState(false);
  const [formData, setFormData] = useState({ 
    name: '', 
    email: '', 
    password: '', 
    country: 'SA',
    referral_code: ''
  });

  useEffect(() => {
    const refCode = searchParams.get('ref');
    if (refCode) {
      setFormData(prev => ({ ...prev, referral_code: refCode }));
    }
  }, [searchParams]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      const res = await fetch(`${process.env.REACT_APP_BACKEND_URL}/api/auth/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData)
      });

      const data = await res.json();

      if (res.ok) {
        localStorage.setItem('token', data.token);
        setUser(data.user);
        
        if (data.welcome_message) {
          toast.success(data.welcome_message);
        } else {
          toast.success('تم إنشاء الحساب بنجاح!');
        }
        
        navigate('/chat');
      } else {
        toast.error(data.detail || 'فشل إنشاء الحساب');
      }
    } catch (error) {
      toast.error('حدث خطأ. يرجى المحاولة لاحقاً');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-4 bg-[#0a0a12]" data-testid="register-page">
      {/* Background Effects */}
      <div className="absolute inset-0 bg-gradient-to-br from-amber-600/5 via-yellow-600/5 to-transparent"></div>
      <div className="absolute top-1/4 right-1/4 w-96 h-96 bg-amber-500/10 rounded-full blur-3xl"></div>
      <div className="absolute bottom-1/4 left-1/4 w-96 h-96 bg-yellow-500/10 rounded-full blur-3xl"></div>
      
      <Card className="w-full max-w-md bg-[#0d0d18]/90 backdrop-blur-xl border-amber-500/20 relative z-10 shadow-2xl shadow-amber-500/5">
        <CardHeader className="text-center">
          <Link to="/" className="flex justify-center mb-4">
            <ZitexLogo size="xl" />
          </Link>
          <CardTitle className="text-2xl text-transparent bg-clip-text bg-gradient-to-r from-amber-400 to-yellow-500" data-testid="register-title">
            إنشاء حساب جديد
          </CardTitle>
          <CardDescription className="text-gray-400">ابدأ رحلتك مع Zitex</CardDescription>
          
          {/* مكافأة التسجيل */}
          <div className="mt-4 p-3 bg-gradient-to-r from-amber-900/30 to-yellow-900/30 border border-amber-500/30 rounded-lg">
            <div className="flex items-center justify-center gap-2 text-amber-400">
              <Gift className="w-5 h-5" />
              <span className="font-semibold">احصل على 20 نقطة + 3 صور + 2 فيديو مجاناً!</span>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="name" className="text-gray-300">الاسم الكامل</Label>
              <Input
                id="name"
                type="text"
                placeholder="أحمد محمد"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                required
                className="bg-slate-800/50 border-slate-700 text-white placeholder:text-gray-500 focus:border-amber-500/50"
                data-testid="name-input"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="email" className="text-gray-300">البريد الإلكتروني</Label>
              <Input
                id="email"
                type="email"
                placeholder="example@domain.com"
                value={formData.email}
                onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                required
                className="bg-slate-800/50 border-slate-700 text-white placeholder:text-gray-500 focus:border-amber-500/50"
                data-testid="email-input"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="password" className="text-gray-300">كلمة المرور</Label>
              <Input
                id="password"
                type="password"
                placeholder="********"
                value={formData.password}
                onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                required
                minLength={6}
                className="bg-slate-800/50 border-slate-700 text-white placeholder:text-gray-500 focus:border-amber-500/50"
                data-testid="password-input"
              />
            </div>
            <div className="space-y-2">
              <Label className="text-gray-300">الدولة</Label>
              <Select value={formData.country} onValueChange={(value) => setFormData({ ...formData, country: value })}>
                <SelectTrigger className="bg-slate-800/50 border-slate-700 text-white focus:border-amber-500/50">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent className="bg-slate-800 border-slate-700">
                  <SelectItem value="SA">السعودية</SelectItem>
                  <SelectItem value="AE">الإمارات</SelectItem>
                  <SelectItem value="KW">الكويت</SelectItem>
                  <SelectItem value="QA">قطر</SelectItem>
                  <SelectItem value="BH">البحرين</SelectItem>
                  <SelectItem value="OM">عمان</SelectItem>
                  <SelectItem value="EG">مصر</SelectItem>
                  <SelectItem value="JO">الأردن</SelectItem>
                  <SelectItem value="OTHER">دولة أخرى</SelectItem>
                </SelectContent>
              </Select>
            </div>
            
            {/* كود الدعوة */}
            <div className="space-y-2">
              <Label htmlFor="referral" className="text-gray-300 flex items-center gap-2">
                كود الدعوة <span className="text-xs text-gray-500">(اختياري)</span>
                {formData.referral_code && <Sparkles className="w-4 h-4 text-amber-400" />}
              </Label>
              <Input
                id="referral"
                type="text"
                placeholder="أدخل كود الدعوة للحصول على 20 نقطة إضافية"
                value={formData.referral_code}
                onChange={(e) => setFormData({ ...formData, referral_code: e.target.value.toUpperCase() })}
                className="bg-slate-800/50 border-slate-700 text-white placeholder:text-gray-500 font-mono focus:border-amber-500/50"
                data-testid="referral-input"
              />
              {formData.referral_code && (
                <p className="text-xs text-amber-400">+20 نقطة إضافية عند استخدام كود الدعوة!</p>
              )}
            </div>
            
            <Button 
              type="submit" 
              className="w-full bg-gradient-to-r from-amber-600 to-yellow-600 hover:from-amber-700 hover:to-yellow-700 shadow-lg shadow-amber-500/20" 
              disabled={loading} 
              data-testid="register-submit-btn"
            >
              {loading ? 'جاري إنشاء الحساب...' : 'إنشاء حساب مجاناً'}
            </Button>
          </form>
          <div className="mt-4 text-center text-sm">
            <span className="text-gray-400">لديك حساب بالفعل؟ </span>
            <Link to="/login" className="text-amber-400 hover:text-amber-300 hover:underline transition-colors" data-testid="login-link">
              تسجيل الدخول
            </Link>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default RegisterPage;

