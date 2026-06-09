import React, { useState, useEffect } from 'react';
import { Navbar } from '@/components/Navbar';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { toast } from 'sonner';
import { Settings, Building2, CreditCard, Save, MessageCircle } from 'lucide-react';
import PWAInstallCard from '@/components/PWAInstallCard';

const AdminSettings = ({ user }) => {
  const [loading, setLoading] = useState(false);
  const [settings, setSettings] = useState({
    bank_name: '',
    bank_iban: '',
    bank_account_name: '',
    paypal_email: '',
    owner_whatsapp: ''
  });

  useEffect(() => {
    fetchSettings();
  }, []);

  const fetchSettings = async () => {
    try {
      const res = await fetch(`${process.env.REACT_APP_BACKEND_URL}/api/settings/payment`);
      const data = await res.json();
      setSettings({
        bank_name: data.bank_name || '',
        bank_iban: data.bank_iban || '',
        bank_account_name: data.bank_account_name || '',
        paypal_email: data.paypal_email || '',
        owner_whatsapp: data.owner_whatsapp || '966507374438'
      });
    } catch (error) {
      console.error('Error:', error);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      const token = localStorage.getItem('token');
      const res = await fetch(`${process.env.REACT_APP_BACKEND_URL}/api/admin/settings/payment`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify(settings)
      });

      if (res.ok) {
        toast.success('تم حفظ الإعدادات بنجاح');
      } else {
        toast.error('فشل حفظ الإعدادات');
      }
    } catch (error) {
      toast.error('حدث خطأ');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-900" data-testid="admin-settings-page">
      <Navbar user={user} transparent />
      
      <div className="container mx-auto px-4 md:px-8 max-w-4xl pt-24 pb-12">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-white mb-2">
            <Settings className="w-8 h-8 inline me-3 text-blue-400" />
            إعدادات الموقع
          </h1>
          <p className="text-gray-400">إدارة معلومات الدفع والإشعارات</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-6">
          {/* WhatsApp Notifications */}
          <Card className="bg-slate-800 border-slate-700">
            <CardHeader>
              <CardTitle className="text-white flex items-center gap-2">
                <MessageCircle className="w-5 h-5 text-green-400" />
                إشعارات الواتساب
              </CardTitle>
              <CardDescription className="text-gray-400">
                سيتم إرسال إشعار عند كل دفعة جديدة
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                <Label className="text-gray-300">رقم الواتساب (بدون +)</Label>
                <Input
                  placeholder="966507374438"
                  value={settings.owner_whatsapp}
                  onChange={(e) => setSettings({ ...settings, owner_whatsapp: e.target.value })}
                  className="bg-slate-700 border-slate-600 text-white placeholder:text-gray-400 font-mono"
                  dir="ltr"
                  data-testid="whatsapp-input"
                />
                <p className="text-xs text-gray-500">
                  ملاحظة: للتفعيل، أرسل "I allow callmebot to send me messages" إلى الرقم +34 644 71 99 22 على الواتساب
                </p>
              </div>
            </CardContent>
          </Card>

          {/* Saudi Bank Info */}
          <Card className="bg-slate-800 border-slate-700">
            <CardHeader>
              <CardTitle className="text-white flex items-center gap-2">
                <Building2 className="w-5 h-5 text-green-400" />
                معلومات الحساب البنكي (السعودية)
              </CardTitle>
              <CardDescription className="text-gray-400">
                هذه المعلومات ستظهر للعملاء المقيمين في السعودية
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label className="text-gray-300">اسم البنك</Label>
                <Input
                  placeholder="مثال: بنك الراجحي"
                  value={settings.bank_name}
                  onChange={(e) => setSettings({ ...settings, bank_name: e.target.value })}
                  className="bg-slate-700 border-slate-600 text-white placeholder:text-gray-400"
                  data-testid="bank-name-input"
                />
              </div>
              <div className="space-y-2">
                <Label className="text-gray-300">رقم الآيبان</Label>
                <Input
                  placeholder="SA..."
                  value={settings.bank_iban}
                  onChange={(e) => setSettings({ ...settings, bank_iban: e.target.value })}
                  className="bg-slate-700 border-slate-600 text-white placeholder:text-gray-400 font-mono"
                  dir="ltr"
                  data-testid="bank-iban-input"
                />
              </div>
              <div className="space-y-2">
                <Label className="text-gray-300">اسم صاحب الحساب</Label>
                <Input
                  placeholder="الاسم كما يظهر في الحساب البنكي"
                  value={settings.bank_account_name}
                  onChange={(e) => setSettings({ ...settings, bank_account_name: e.target.value })}
                  className="bg-slate-700 border-slate-600 text-white placeholder:text-gray-400"
                  data-testid="bank-account-name-input"
                />
              </div>
            </CardContent>
          </Card>

          {/* PayPal Info */}
          <Card className="bg-slate-800 border-slate-700">
            <CardHeader>
              <CardTitle className="text-white flex items-center gap-2">
                <CreditCard className="w-5 h-5 text-blue-400" />
                معلومات PayPal (الدفع الدولي)
              </CardTitle>
              <CardDescription className="text-gray-400">
                هذه المعلومات ستظهر للعملاء من خارج السعودية
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                <Label className="text-gray-300">البريد الإلكتروني لـ PayPal</Label>
                <Input
                  type="email"
                  placeholder="your-email@paypal.com"
                  value={settings.paypal_email}
                  onChange={(e) => setSettings({ ...settings, paypal_email: e.target.value })}
                  className="bg-slate-700 border-slate-600 text-white placeholder:text-gray-400"
                  dir="ltr"
                  data-testid="paypal-email-input"
                />
              </div>
            </CardContent>
          </Card>

          <Button 
            type="submit" 
            disabled={loading}
            className="w-full bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-600 hover:to-purple-700"
            data-testid="save-settings-btn"
          >
            <Save className="w-4 h-4 me-2" />
            {loading ? 'جاري الحفظ...' : 'حفظ الإعدادات'}
          </Button>
        </form>

        {/* PWA Install Section — always available for re-install */}
        <div className="mt-6">
          <PWAInstallCard />
        </div>
      </div>
    </div>
  );
};

export default AdminSettings;
