import React, { useState, useEffect } from 'react';
import { Navbar } from '@/components/Navbar';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { toast } from 'sonner';
import { 
  DollarSign, Save, Plus, Trash2, Tag, Percent, 
  Package, Settings, Gift, ArrowLeft 
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';

const AdminPricing = ({ user }) => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [pricing, setPricing] = useState(null);
  const [newOffer, setNewOffer] = useState({
    name: '',
    code: '',
    discount_percent: 0,
    discount_amount: 0,
    max_uses: 0
  });

  const exchangeRate = pricing?.exchange_rate || 3.75;

  useEffect(() => {
    fetchPricing();
  }, []);

  const fetchPricing = async () => {
    try {
      const token = localStorage.getItem('token');
      const res = await fetch(`${process.env.REACT_APP_BACKEND_URL}/api/admin/pricing`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setPricing(data);
      }
    } catch (error) {
      toast.error('فشل تحميل الأسعار');
    }
    setLoading(false);
  };

  const savePricing = async () => {
    setSaving(true);
    try {
      const token = localStorage.getItem('token');
      const res = await fetch(`${process.env.REACT_APP_BACKEND_URL}/api/admin/pricing`, {
        method: 'PUT',
        headers: { 
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(pricing)
      });
      if (res.ok) {
        toast.success('تم حفظ الأسعار بنجاح');
      }
    } catch (error) {
      toast.error('فشل حفظ الأسعار');
    }
    setSaving(false);
  };

  const updatePackage = (index, field, value) => {
    const updated = { ...pricing };
    updated.packages[index][field] = field.includes('price') || field === 'credits' || field === 'bonus' 
      ? Number(value) 
      : value;
    setPricing(updated);
  };

  const updateService = (key, value) => {
    setPricing({
      ...pricing,
      services: { ...pricing.services, [key]: Number(value) }
    });
  };

  const addOffer = async () => {
    if (!newOffer.name || !newOffer.code) {
      toast.error('أدخل اسم العرض والكود');
      return;
    }
    try {
      const token = localStorage.getItem('token');
      const res = await fetch(`${process.env.REACT_APP_BACKEND_URL}/api/admin/offers`, {
        method: 'POST',
        headers: { 
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(newOffer)
      });
      if (res.ok) {
        toast.success('تم إضافة العرض');
        setNewOffer({ name: '', code: '', discount_percent: 0, discount_amount: 0, max_uses: 0 });
        fetchPricing();
      }
    } catch (error) {
      toast.error('فشل إضافة العرض');
    }
  };

  const deleteOffer = async (offerId) => {
    if (!confirm('حذف هذا العرض؟')) return;
    try {
      const token = localStorage.getItem('token');
      await fetch(`${process.env.REACT_APP_BACKEND_URL}/api/admin/offers/${offerId}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      toast.success('تم حذف العرض');
      fetchPricing();
    } catch (error) {
      toast.error('فشل حذف العرض');
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-900 flex items-center justify-center">
        <div className="animate-spin w-10 h-10 border-4 border-purple-500 border-t-transparent rounded-full"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-900">
      <Navbar user={user} transparent />
      
      <div className="container mx-auto px-4 md:px-8 max-w-6xl pt-24 pb-12">
        <div className="flex items-center justify-between mb-8">
          <div className="flex items-center gap-4">
            <Button variant="ghost" onClick={() => navigate('/admin')} className="text-gray-400">
              <ArrowLeft className="w-5 h-5" />
            </Button>
            <div>
              <h1 className="text-3xl font-bold text-white">إدارة الأسعار</h1>
              <p className="text-gray-400">تحكم بالباقات والعروض</p>
            </div>
          </div>
          <Button onClick={savePricing} disabled={saving} className="bg-green-600 hover:bg-green-700">
            <Save className="w-4 h-4 me-2" />
            {saving ? 'جاري الحفظ...' : 'حفظ التغييرات'}
          </Button>
        </div>

        {/* سعر الصرف */}
        <Card className="bg-slate-800 border-slate-700 mb-6">
          <CardContent className="p-6">
            <div className="flex items-center gap-4">
              <DollarSign className="w-8 h-8 text-green-400" />
              <div className="flex-1">
                <h3 className="text-white font-semibold">سعر الصرف</h3>
                <p className="text-gray-400 text-sm">1 دولار = كم ريال؟</p>
              </div>
              <Input
                type="number"
                step="0.01"
                value={pricing?.exchange_rate || 3.75}
                onChange={(e) => setPricing({ ...pricing, exchange_rate: Number(e.target.value) })}
                className="w-32 bg-slate-700 border-slate-600 text-white text-center"
              />
              <span className="text-gray-400">ريال</span>
            </div>
          </CardContent>
        </Card>

        {/* الباقات */}
        <Card className="bg-slate-800 border-slate-700 mb-6">
          <CardContent className="p-6">
            <div className="flex items-center gap-3 mb-6">
              <Package className="w-6 h-6 text-purple-400" />
              <h2 className="text-xl font-semibold text-white">باقات النقاط</h2>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="text-gray-400 text-sm border-b border-slate-700">
                    <th className="text-right py-3 px-2">الاسم</th>
                    <th className="text-center py-3 px-2">النقاط</th>
                    <th className="text-center py-3 px-2">السعر ($)</th>
                    <th className="text-center py-3 px-2">بالريال ≈</th>
                    <th className="text-center py-3 px-2">المكافأة</th>
                    <th className="text-center py-3 px-2">مميز</th>
                  </tr>
                </thead>
                <tbody>
                  {pricing?.packages?.map((pkg, index) => (
                    <tr key={pkg.id} className="border-b border-slate-700/50">
                      <td className="py-3 px-2">
                        <Input
                          value={pkg.name}
                          onChange={(e) => updatePackage(index, 'name', e.target.value)}
                          className="bg-slate-700 border-slate-600 text-white"
                        />
                      </td>
                      <td className="py-3 px-2">
                        <Input
                          type="number"
                          value={pkg.credits}
                          onChange={(e) => updatePackage(index, 'credits', e.target.value)}
                          className="bg-slate-700 border-slate-600 text-white text-center w-24 mx-auto"
                        />
                      </td>
                      <td className="py-3 px-2">
                        <div className="flex items-center justify-center gap-1">
                          <span className="text-green-400">$</span>
                          <Input
                            type="number"
                            value={pkg.price_usd}
                            onChange={(e) => updatePackage(index, 'price_usd', e.target.value)}
                            className="bg-slate-700 border-slate-600 text-white text-center w-20"
                          />
                        </div>
                      </td>
                      <td className="py-3 px-2 text-center">
                        <span className="text-yellow-400 font-semibold">
                          {Math.round(pkg.price_usd * exchangeRate)} ر.س
                        </span>
                      </td>
                      <td className="py-3 px-2">
                        <Input
                          type="number"
                          value={pkg.bonus}
                          onChange={(e) => updatePackage(index, 'bonus', e.target.value)}
                          className="bg-slate-700 border-slate-600 text-white text-center w-20 mx-auto"
                        />
                      </td>
                      <td className="py-3 px-2 text-center">
                        <input
                          type="checkbox"
                          checked={pkg.popular}
                          onChange={(e) => updatePackage(index, 'popular', e.target.checked)}
                          className="w-5 h-5 rounded"
                        />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>

        {/* أسعار الخدمات */}
        <Card className="bg-slate-800 border-slate-700 mb-6">
          <CardContent className="p-6">
            <div className="flex items-center gap-3 mb-6">
              <Settings className="w-6 h-6 text-blue-400" />
              <h2 className="text-xl font-semibold text-white">أسعار الخدمات (بالنقاط)</h2>
            </div>

            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {pricing?.services && Object.entries(pricing.services).map(([key, value]) => (
                <div key={key} className="bg-slate-700/50 rounded-lg p-4">
                  <label className="text-gray-400 text-sm block mb-2">
                    {key === 'image' && 'توليد صورة'}
                    {key === 'video_4s' && 'فيديو 4 ثواني'}
                    {key === 'video_8s' && 'فيديو 8 ثواني'}
                    {key === 'video_12s' && 'فيديو 12 ثانية'}
                    {key === 'video_60s' && 'فيديو دقيقة'}
                    {key === 'website_simple' && 'موقع بسيط'}
                    {key === 'website_advanced' && 'موقع متقدم'}
                  </label>
                  <div className="flex items-center gap-2">
                    <Input
                      type="number"
                      value={value}
                      onChange={(e) => updateService(key, e.target.value)}
                      className="bg-slate-600 border-slate-500 text-white text-center"
                    />
                    <span className="text-purple-400 text-sm">نقطة</span>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* العروض والخصومات */}
        <Card className="bg-slate-800 border-slate-700">
          <CardContent className="p-6">
            <div className="flex items-center gap-3 mb-6">
              <Gift className="w-6 h-6 text-pink-400" />
              <h2 className="text-xl font-semibold text-white">العروض والخصومات</h2>
            </div>

            {/* إضافة عرض جديد */}
            <div className="bg-slate-700/50 rounded-lg p-4 mb-6">
              <h3 className="text-white font-medium mb-4">إضافة عرض جديد</h3>
              <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
                <Input
                  placeholder="اسم العرض"
                  value={newOffer.name}
                  onChange={(e) => setNewOffer({ ...newOffer, name: e.target.value })}
                  className="bg-slate-600 border-slate-500 text-white"
                />
                <Input
                  placeholder="كود الخصم"
                  value={newOffer.code}
                  onChange={(e) => setNewOffer({ ...newOffer, code: e.target.value.toUpperCase() })}
                  className="bg-slate-600 border-slate-500 text-white uppercase"
                />
                <div className="flex items-center gap-1">
                  <Input
                    type="number"
                    placeholder="نسبة %"
                    value={newOffer.discount_percent || ''}
                    onChange={(e) => setNewOffer({ ...newOffer, discount_percent: Number(e.target.value) })}
                    className="bg-slate-600 border-slate-500 text-white"
                  />
                  <Percent className="w-4 h-4 text-gray-400" />
                </div>
                <Input
                  type="number"
                  placeholder="الحد الأقصى"
                  value={newOffer.max_uses || ''}
                  onChange={(e) => setNewOffer({ ...newOffer, max_uses: Number(e.target.value) })}
                  className="bg-slate-600 border-slate-500 text-white"
                />
                <Button onClick={addOffer} className="bg-pink-600 hover:bg-pink-700">
                  <Plus className="w-4 h-4 me-1" /> إضافة
                </Button>
              </div>
            </div>

            {/* قائمة العروض */}
            {pricing?.offers?.length > 0 ? (
              <div className="space-y-3">
                {pricing.offers.map((offer) => (
                  <div key={offer.id} className="flex items-center justify-between bg-slate-700/30 rounded-lg p-4">
                    <div className="flex items-center gap-4">
                      <Tag className="w-5 h-5 text-pink-400" />
                      <div>
                        <p className="text-white font-medium">{offer.name}</p>
                        <p className="text-gray-400 text-sm">
                          كود: <span className="text-pink-400 font-mono">{offer.code}</span>
                          {offer.discount_percent > 0 && ` • خصم ${offer.discount_percent}%`}
                          {offer.max_uses > 0 && ` • استخدم ${offer.used_count || 0}/${offer.max_uses}`}
                        </p>
                      </div>
                    </div>
                    <Button variant="ghost" size="sm" onClick={() => deleteOffer(offer.id)} className="text-red-400 hover:text-red-300">
                      <Trash2 className="w-4 h-4" />
                    </Button>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-gray-500 text-center py-8">لا توجد عروض حالياً</p>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default AdminPricing;
