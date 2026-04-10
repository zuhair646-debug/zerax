import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { toast } from 'sonner';
import { ZitexLogo } from '@/components/Navbar';

const LoginPage = ({ setUser }) => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [formData, setFormData] = useState({ email: '', password: '' });

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      const res = await fetch(`${process.env.REACT_APP_BACKEND_URL}/api/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData)
      });

      const data = await res.json();

      if (res.ok) {
        localStorage.setItem('token', data.token);
        setUser(data.user);
        toast.success('تم تسجيل الدخول بنجاح!');
        const isAdmin = data.user.role === 'admin' || data.user.role === 'super_admin' || data.user.role === 'owner' || data.user.is_owner;
        navigate(isAdmin ? '/admin' : '/dashboard');
      } else {
        toast.error(data.detail || 'فشل تسجيل الدخول');
      }
    } catch (error) {
      toast.error('حدث خطأ. يرجى المحاولة لاحقاً');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-4 bg-[#0a0a12]" data-testid="login-page">
      {/* Background Effects */}
      <div className="absolute inset-0 bg-gradient-to-br from-amber-600/5 via-yellow-600/5 to-transparent"></div>
      <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-amber-500/10 rounded-full blur-3xl"></div>
      <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-yellow-500/10 rounded-full blur-3xl"></div>
      
      <Card className="w-full max-w-md bg-[#0d0d18]/90 backdrop-blur-xl border-amber-500/20 relative z-10 shadow-2xl shadow-amber-500/5">
        <CardHeader className="text-center">
          <Link to="/" className="flex justify-center mb-4">
            <ZitexLogo size="xl" />
          </Link>
          <CardTitle className="text-2xl text-transparent bg-clip-text bg-gradient-to-r from-amber-400 to-yellow-500" data-testid="login-title">
            تسجيل الدخول
          </CardTitle>
          <CardDescription className="text-gray-400">أدخل بياناتك للوصول إلى حسابك</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="email" className="text-gray-300">البريد الإلكتروني</Label>
              <Input
                id="email"
                type="email"
                placeholder="example@domain.com"
                value={formData.email}
                onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                required
                className="bg-slate-800/50 border-slate-700 text-white placeholder:text-gray-500 focus:border-amber-500/50 focus:ring-amber-500/20"
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
                className="bg-slate-800/50 border-slate-700 text-white placeholder:text-gray-500 focus:border-amber-500/50 focus:ring-amber-500/20"
                data-testid="password-input"
              />
            </div>
            <Button 
              type="submit" 
              className="w-full bg-gradient-to-r from-amber-600 to-yellow-600 hover:from-amber-700 hover:to-yellow-700 shadow-lg shadow-amber-500/20 text-white font-medium" 
              disabled={loading} 
              data-testid="login-submit-btn"
            >
              {loading ? 'جاري تسجيل الدخول...' : 'تسجيل الدخول'}
            </Button>
          </form>
          <div className="mt-4 text-center text-sm">
            <span className="text-gray-400">ليس لديك حساب؟ </span>
            <Link to="/register" className="text-amber-400 hover:text-amber-300 hover:underline transition-colors" data-testid="register-link">
              إنشاء حساب جديد
            </Link>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default LoginPage;
