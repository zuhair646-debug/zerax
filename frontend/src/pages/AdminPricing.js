import React, { useState, useEffect } from 'react';
import { Navbar } from '@/components/Navbar';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { toast } from 'sonner';
import { 
  DollarSign, Save, Plus, Trash2, Tag, Percent, 
  Package, Settings, Gift, ArrowLeft, Star, Users, ShoppingBag
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
    max_uses: 0,
    for_first_order: false
  });

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
      } else {
        // Initialize default pricing
        setPricing({
          currency: 'USD',
          exchange_rate: 3.75,
          packages: [
            { id: 'starter', name: 'باقة المبتدئ', credits: 100, price: 13, bonus: 0, popular: false },
            { id: 'pro', name: 'باقة المحترف', credits: 500, price: 53, bonus: 50, popular: true },
            { id: 'enterprise', name: 'باقة الأعمال', credits: 2000, price: 187, bonus: 300, popular: false },
          ],
          services: {
            image: 5,
            video_4s: 10,
            video_8s: 18,
            video_12s: 25,
            video_60s: 100,
            website_simple: 50,
            website_advanced: 150,
          },
          first_order_discount: 0,
          signup_bonus: 20,
          referral_bonus: 30,
          offers: []
        });
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
    if (field === 'popular') {
      updated.packages[index][field] = value;
    } else if (['price', 'credits', 'bonus'].includes(field)) {
      updated.packages[index][field] = Number(value) || 0;
    } else {
      updated.packages[index][field] = value;
    }
    setPricing(updated);
  };

  const addPackage = () => {
    const newPkg = {
      id: `pkg_${Date.now()}`,
      name: 'باقة جديدة',
      credits: 100,
      price: 10,
      bonus: 0,
      popular: false
    };
    setPricing({
      ...pricing,
      packages: [...(pricing.packages || []), newPkg]
    });
    toast.success('تم إضافة باقة جديدة');
  };

  const deletePackage = (index) => {
    if (!confirm('هل تريد حذف هذه الباقة؟')) return;
    const updated = { ...pricing };
    updated.packages.splice(index, 1);
    setPricing(updated);
    toast.success('تم حذف الباقة');
  };

  const updateService = (key, value) => {
    setPricing({
      ...pricing,
      services: { ...pricing.services, [key]: Number(value) || 0 }
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
        setNewOffer({ name: '', code: '', discount_percent: 0, max_uses: 0, for_first_order: false });
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

  const getDisplayPrice = (price) => {
    if (pricing?.currency === 'SAR') {
      return `${price} ر.س`;
    }
    return `$${price}`;
  };

  const getConvertedPrice = (price) => {
    const rate = pricing?.exchange_rate || 3.75;
    if (pricing?.currency === 'SAR') {
      return `≈ $${(price / rate).toFixed(0)}`;
    }
    return `≈ ${Math.round(price * rate)} ر.س`;
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
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div className="flex items-center gap-4">
            <Button variant="ghost" onClick={() => navigate('/admin')} className="text-gray-400">
              <ArrowLeft className="w-5 h-5" />
            </Button>
            <div>
              <h1 className="text-3xl font-bold text-white">إدارة الأسعار</h1>
              <p className="text-gray-400">تحكم كامل بالباقات والعروض</p>
            </div>
          </div>
          <Button onClick={savePricing} disabled={saving} className="bg-green-600 hover:bg-green-700">
            <Save className="w-4 h-4 me-2" />
            {saving ? 'جاري الحفظ...' : 'حفظ التغييرات'}
          </Button>
        </div>

        {/* إعدادات العملة */}
        <Card className="bg-slate-800 border-slate-700 mb-6">
          <CardContent className="p-6">
            <div className="flex items-center gap-3 mb-4">
              <DollarSign className="w-6 h-6 text-green-400" />
              <h2 className="text-xl font-semibold text-white">إعدادات العملة</h2>
            </div>
            
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="bg-slate-700/50 rounded-lg p-4">
                <label className="text-gray-400 text-sm block mb-2">العملة الأساسية</label>
                <select
                  value={pricing?.currency || 'USD'}
                  onChange={(e) => setPricing({ ...pricing, currency: e.target.value })}
                  className="w-full bg-slate-600 border-slate-500 text-white rounded-lg px-3 py-2"
                >
                  <option value="USD">🇺🇸 دولار أمريكي (USD)</option>
                  <option value="SAR">🇸🇦 ريال سعودي (SAR)</option>
                </select>
              </div>
              
              <div className="bg-slate-700/50 rounded-lg p-4">
                <label className="text-gray-400 text-sm block mb-2">سعر الصرف (1 USD = ؟ SAR)</label>
                <Input
                  type="number"
                  step="0.01"
                  value={pricing?.exchange_rate || 3.75}
                  onChange={(e) => setPricing({ ...pricing, exchange_rate: Number(e.target.value) })}
                  className="bg-slate-600 border-slate-500 text-white"
                />
              </div>
              
              <div className="bg-slate-700/50 rounded-lg p-4">
                <label className="text-gray-400 text-sm block mb-2">خصم أول طلب %</label>
                <div className="flex items-center gap-2">
                  <Input
                    type="number"
                    value={pricing?.first_order_discount || 0}
                    onChange={(e) => setPricing({ ...pricing, first_order_discount: Number(e.target.value) })}
                    className="bg-slate-600 border-slate-500 text-white"
                  />
                  <Percent className="w-5 h-5 text-pink-400" />
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* مكافآت التسجيل والإحالة */}
        <Card className="bg-slate-800 border-slate-700 mb-6">
          <CardContent className="p-6">
            <div className="flex items-center gap-3 mb-4">
              <Users className="w-6 h-6 text-blue-400" />
              <h2 className="text-xl font-semibold text-white">مكافآت التسجيل والإحالة</h2>
            </div>
            
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="bg-slate-700/50 rounded-lg p-4">
                <label className="text-gray-400 text-sm block mb-2">مكافأة التسجيل (نقاط)</label>
                <Input
                  type="number"
                  value={pricing?.signup_bonus || 0}
                  onChange={(e) => setPricing({ ...pricing, signup_bonus: Number(e.target.value) })}
                  className="bg-slate-600 border-slate-500 text-white"
                />
              </div>
              
              <div className="bg-slate-700/50 rounded-lg p-4">
                <label className="text-gray-400 text-sm block mb-2">مكافأة الإحالة للداعي (نقاط)</label>
                <Input
                  type="number"
                  value={pricing?.referral_bonus || 0}
                  onChange={(e) => setPricing({ ...pricing, referral_bonus: Number(e.target.value) })}
                  className="bg-slate-600 border-slate-500 text-white"
                />
              </div>
              
              <div className="bg-slate-700/50 rounded-lg p-4">
                <label className="text-gray-400 text-sm block mb-2">مكافأة المدعو (نقاط)</label>
                <Input
                  type="number"
                  value={pricing?.invited_bonus || 0}
                  onChange={(e) => setPricing({ ...pricing, invited_bonus: Number(e.target.value) })}
                  className="bg-slate-600 border-slate-500 text-white"
                />
              </div>
            </div>
          </CardContent>
        </Card>

        {/* الباقات */}
        <Card className="bg-slate-800 border-slate-700 mb-6">
          <CardContent className="p-6">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-3">
                <Package className="w-6 h-6 text-purple-400" />
                <h2 className="text-xl font-semibold text-white">باقات النقاط</h2>
              </div>
              <Button onClick={addPackage} className="bg-purple-600 hover:bg-purple-700">
                <Plus className="w-4 h-4 me-2" /> إضافة باقة
              </Button>
            </div>

            <div className="space-y-4">
              {pricing?.packages?.map((pkg, index) => (
                <div key={pkg.id} className="bg-slate-700/50 rounded-lg p-4">
                  <div className="grid grid-cols-2 md:grid-cols-7 gap-3 items-center">
                    <div className="col-span-2 md:col-span-1">
                      <label className="text-gray-400 text-xs block mb-1">الاسم</label>
                      <Input
                        value={pkg.name}
                        onChange={(e) => updatePackage(index, 'name', e.target.value)}
                        className="bg-slate-600 border-slate-500 text-white"
                      />
                    </div>
                    
                    <div>
                      <label className="text-gray-400 text-xs block mb-1">النقاط</label>
                      <Input
                        type="number"
                        value={pkg.credits}
                        onChange={(e) => updatePackage(index, 'credits', e.target.value)}
                        className="bg-slate-600 border-slate-500 text-white text-center"
                      />
                    </div>
                    
                    <div>
                      <label className="text-gray-400 text-xs block mb-1">السعر</label>
                      <div className="flex items-center gap-1">
                        <Input
                          type="number"
                          value={pkg.price}
                          onChange={(e) => updatePackage(index, 'price', e.target.value)}
                          className="bg-slate-600 border-slate-500 text-white text-center"
                        />
                      </div>
                    </div>
                    
                    <div>
                      <label className="text-gray-400 text-xs block mb-1">تحويل</label>
                      <p className="text-yellow-400 text-sm font-medium py-2">
                        {getConvertedPrice(pkg.price)}
                      </p>
                    </div>
                    
                    <div>
                      <label className="text-gray-400 text-xs block mb-1">مكافأة</label>
                      <Input
                        type="number"
                        value={pkg.bonus}
                        onChange={(e) => updatePackage(index, 'bonus', e.target.value)}
                        className="bg-slate-600 border-slate-500 text-white text-center"
                      />
                    </div>
                    
                    <div className="flex items-center gap-3">
                      <label className="flex items-center gap-2 cursor-pointer">
                        <input
                          type="checkbox"
                          checked={pkg.popular}
                          onChange={(e) => updatePackage(index, 'popular', e.target.checked)}
                          className="w-4 h-4 rounded"
                        />
                        <Star className={`w-4 h-4 ${pkg.popular ? 'text-yellow-400' : 'text-gray-500'}`} />
                      </label>
                      
                      <Button 
                        variant="ghost" 
                        size="sm" 
                        onClick={() => deletePackage(index)}
                        className="text-red-400 hover:text-red-300 hover:bg-red-500/20"
                      >
                        <Trash2 className="w-4 h-4" />
                      </Button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* أسعار الخدمات */}
        <Card className="bg-slate-800 border-slate-700 mb-6">
          <CardContent className="p-6">
            <div className="flex items-center gap-3 mb-4">
              <ShoppingBag className="w-6 h-6 text-orange-400" />
              <h2 className="text-xl font-semibold text-white">أسعار الخدمات (بالنقاط)</h2>
            </div>

            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {[
                { key: 'image', label: 'توليد صورة', icon: '🖼️' },
                { key: 'video_4s', label: 'فيديو 4 ثواني', icon: '🎬' },
                { key: 'video_8s', label: 'فيديو 8 ثواني', icon: '🎬' },
                { key: 'video_12s', label: 'فيديو 12 ثانية', icon: '🎬' },
                { key: 'video_60s', label: 'فيديو دقيقة', icon: '🎥' },
                { key: 'website_simple', label: 'موقع بسيط', icon: '🌐' },
                { key: 'website_advanced', label: 'موقع متقدم', icon: '💻' },
              ].map(({ key, label, icon }) => (
                <div key={key} className="bg-slate-700/50 rounded-lg p-4">
                  <label className="text-gray-400 text-sm flex items-center gap-2 mb-2">
                    <span>{icon}</span> {label}
                  </label>
                  <div className="flex items-center gap-2">
                    <Input
                      type="number"
                      value={pricing?.services?.[key] || 0}
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
            <div className="flex items-center gap-3 mb-4">
              <Gift className="w-6 h-6 text-pink-400" />
              <h2 className="text-xl font-semibold text-white">أكواد الخصم والعروض</h2>
            </div>

            {/* إضافة عرض جديد */}
            <div className="bg-slate-700/50 rounded-lg p-4 mb-6">
              <h3 className="text-white font-medium mb-4">إضافة كود خصم جديد</h3>
              <div className="grid grid-cols-1 md:grid-cols-6 gap-3 items-end">
                <div>
                  <label className="text-gray-400 text-xs block mb-1">اسم العرض</label>
                  <Input
                    placeholder="عرض الصيف"
                    value={newOffer.name}
                    onChange={(e) => setNewOffer({ ...newOffer, name: e.target.value })}
                    className="bg-slate-600 border-slate-500 text-white"
                  />
                </div>
                <div>
                  <label className="text-gray-400 text-xs block mb-1">كود الخصم</label>
                  <Input
                    placeholder="SUMMER24"
                    value={newOffer.code}
                    onChange={(e) => setNewOffer({ ...newOffer, code: e.target.value.toUpperCase() })}
                    className="bg-slate-600 border-slate-500 text-white uppercase font-mono"
                  />
                </div>
                <div>
                  <label className="text-gray-400 text-xs block mb-1">نسبة الخصم %</label>
                  <Input
                    type="number"
                    placeholder="20"
                    value={newOffer.discount_percent || ''}
                    onChange={(e) => setNewOffer({ ...newOffer, discount_percent: Number(e.target.value) })}
                    className="bg-slate-600 border-slate-500 text-white"
                  />
                </div>
                <div>
                  <label className="text-gray-400 text-xs block mb-1">الحد الأقصى (0 = لا نهائي)</label>
                  <Input
                    type="number"
                    placeholder="100"
                    value={newOffer.max_uses || ''}
                    onChange={(e) => setNewOffer({ ...newOffer, max_uses: Number(e.target.value) })}
                    className="bg-slate-600 border-slate-500 text-white"
                  />
                </div>
                <div className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    id="firstOrder"
                    checked={newOffer.for_first_order}
                    onChange={(e) => setNewOffer({ ...newOffer, for_first_order: e.target.checked })}
                    className="w-4 h-4 rounded"
                  />
                  <label htmlFor="firstOrder" className="text-gray-400 text-xs">أول طلب فقط</label>
                </div>
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
                          كود: <span className="text-pink-400 font-mono bg-pink-500/20 px-2 py-0.5 rounded">{offer.code}</span>
                          {offer.discount_percent > 0 && <span className="ms-2">• خصم {offer.discount_percent}%</span>}
                          {offer.max_uses > 0 && <span className="ms-2">• استخدم {offer.used_count || 0}/{offer.max_uses}</span>}
                          {offer.for_first_order && <span className="ms-2 text-yellow-400">• أول طلب فقط</span>}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className={`px-2 py-1 rounded text-xs ${offer.active ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'}`}>
                        {offer.active ? 'نشط' : 'متوقف'}
                      </span>
                      <Button variant="ghost" size="sm" onClick={() => deleteOffer(offer.id)} className="text-red-400 hover:text-red-300">
                        <Trash2 className="w-4 h-4" />
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-gray-500 text-center py-8">لا توجد أكواد خصم حالياً</p>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default AdminPricing;
