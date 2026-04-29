import React, { useState, useEffect, useCallback } from 'react';
import { Navbar } from '@/components/Navbar';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { toast } from 'sonner';
import { 
  Coins, Users, Gift, Save, Plus, Trash2, Search, 
  TrendingUp, Percent, Tag, DollarSign, Edit, Check, X,
  Sparkles, Zap
} from 'lucide-react';

const AdminCredits = ({ user }) => {
  const [loading, setLoading] = useState(true);
  const [users, setUsers] = useState([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [editingUser, setEditingUser] = useState(null);
  const [newCredits, setNewCredits] = useState('');
  
  // Pricing settings
  const [pricing, setPricing] = useState({
    website: 15,
    game: 15,
    image: 5,
    video: 20,
    modification: 5,
    save_template: 10,
    export: 50,
    deploy: 100
  });
  
  // Offers
  const [offers, setOffers] = useState([]);
  const [newOffer, setNewOffer] = useState({
    name: '',
    credits: 100,
    price: 10,
    discount: 0,
    is_active: true
  });

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem('token');
      
      // Fetch users
      const usersRes = await fetch(`${process.env.REACT_APP_BACKEND_URL}/api/admin/users`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (usersRes.ok) {
        const data = await usersRes.json();
        setUsers(data.users || []);
      }
      
      // Fetch pricing
      const pricingRes = await fetch(`${process.env.REACT_APP_BACKEND_URL}/api/admin/service-pricing`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (pricingRes.ok) {
        const data = await pricingRes.json();
        if (data.pricing) setPricing(data.pricing);
      }
      
      // Fetch offers
      const offersRes = await fetch(`${process.env.REACT_APP_BACKEND_URL}/api/admin/offers`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (offersRes.ok) {
        const data = await offersRes.json();
        setOffers(data.offers || []);
      }
      
    } catch (error) {
      console.error('Error:', error);
    } finally {
      setLoading(false);
    }
  };

  const updateUserCredits = async (userId) => {
    try {
      const token = localStorage.getItem('token');
      const res = await fetch(`${process.env.REACT_APP_BACKEND_URL}/api/admin/users/${userId}/credits`, {
        method: 'PUT',
        headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({ credits: parseInt(newCredits) })
      });
      
      if (res.ok) {
        toast.success('تم تحديث النقاط بنجاح');
        setEditingUser(null);
        setNewCredits('');
        fetchData();
      } else {
        toast.error('فشل التحديث');
      }
    } catch (error) {
      toast.error('حدث خطأ');
    }
  };

  const savePricing = async () => {
    try {
      const token = localStorage.getItem('token');
      const res = await fetch(`${process.env.REACT_APP_BACKEND_URL}/api/admin/service-pricing`, {
        method: 'PUT',
        headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({ pricing })
      });
      
      if (res.ok) {
        toast.success('تم حفظ الأسعار بنجاح');
      } else {
        toast.error('فشل الحفظ');
      }
    } catch (error) {
      toast.error('حدث خطأ');
    }
  };

  const addOffer = async () => {
    if (!newOffer.name || newOffer.credits <= 0 || newOffer.price <= 0) {
      toast.error('أدخل جميع البيانات');
      return;
    }
    
    try {
      const token = localStorage.getItem('token');
      const res = await fetch(`${process.env.REACT_APP_BACKEND_URL}/api/admin/offers`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify(newOffer)
      });
      
      if (res.ok) {
        toast.success('تم إضافة العرض بنجاح');
        setNewOffer({ name: '', credits: 100, price: 10, discount: 0, is_active: true });
        fetchData();
      } else {
        toast.error('فشل الإضافة');
      }
    } catch (error) {
      toast.error('حدث خطأ');
    }
  };

  const deleteOffer = async (offerId) => {
    try {
      const token = localStorage.getItem('token');
      const res = await fetch(`${process.env.REACT_APP_BACKEND_URL}/api/admin/offers/${offerId}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      if (res.ok) {
        toast.success('تم حذف العرض');
        fetchData();
      }
    } catch (error) {
      toast.error('حدث خطأ');
    }
  };

  const toggleOfferStatus = async (offerId, isActive) => {
    try {
      const token = localStorage.getItem('token');
      const res = await fetch(`${process.env.REACT_APP_BACKEND_URL}/api/admin/offers/${offerId}`, {
        method: 'PUT',
        headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({ is_active: !isActive })
      });
      
      if (res.ok) {
        toast.success('تم تحديث حالة العرض');
        fetchData();
      }
    } catch (error) {
      toast.error('حدث خطأ');
    }
  };

  const filteredUsers = users.filter(u => 
    u.email?.toLowerCase().includes(searchTerm.toLowerCase()) ||
    u.name?.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const totalCredits = users.reduce((sum, u) => sum + (u.credits || 0), 0);

  return (
    <div className="min-h-screen bg-slate-900" data-testid="admin-credits-page">
      <Navbar user={user} transparent />
      
      <div className="container mx-auto px-4 md:px-8 max-w-6xl pt-24 pb-12">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-white mb-2">
            <Coins className="w-8 h-8 inline me-3 text-amber-400" />
            إدارة النقاط والعروض
          </h1>
          <p className="text-gray-400">التحكم في نقاط المستخدمين والأسعار والعروض</p>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
          <Card className="bg-gradient-to-br from-amber-500/20 to-yellow-500/20 border-amber-500/30">
            <CardContent className="p-4">
              <div className="flex items-center gap-3">
                <Coins className="w-8 h-8 text-amber-400" />
                <div>
                  <p className="text-gray-400 text-sm">إجمالي النقاط</p>
                  <p className="text-2xl font-bold text-amber-400">{totalCredits.toLocaleString()}</p>
                </div>
              </div>
            </CardContent>
          </Card>
          <Card className="bg-slate-800 border-slate-700">
            <CardContent className="p-4">
              <div className="flex items-center gap-3">
                <Users className="w-8 h-8 text-blue-400" />
                <div>
                  <p className="text-gray-400 text-sm">المستخدمين</p>
                  <p className="text-2xl font-bold text-white">{users.length}</p>
                </div>
              </div>
            </CardContent>
          </Card>
          <Card className="bg-slate-800 border-slate-700">
            <CardContent className="p-4">
              <div className="flex items-center gap-3">
                <Gift className="w-8 h-8 text-purple-400" />
                <div>
                  <p className="text-gray-400 text-sm">العروض النشطة</p>
                  <p className="text-2xl font-bold text-white">{offers.filter(o => o.is_active).length}</p>
                </div>
              </div>
            </CardContent>
          </Card>
          <Card className="bg-slate-800 border-slate-700">
            <CardContent className="p-4">
              <div className="flex items-center gap-3">
                <TrendingUp className="w-8 h-8 text-green-400" />
                <div>
                  <p className="text-gray-400 text-sm">متوسط النقاط</p>
                  <p className="text-2xl font-bold text-white">{users.length ? Math.round(totalCredits / users.length) : 0}</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Users Credits */}
          <Card className="bg-slate-800 border-slate-700">
            <CardHeader>
              <CardTitle className="text-white flex items-center gap-2">
                <Users className="w-5 h-5 text-blue-400" />
                نقاط المستخدمين
              </CardTitle>
              <div className="relative">
                <Search className="w-4 h-4 absolute right-3 top-1/2 -translate-y-1/2 text-gray-400" />
                <Input
                  placeholder="بحث..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="bg-slate-700 border-slate-600 text-white pr-10"
                />
              </div>
            </CardHeader>
            <CardContent className="max-h-96 overflow-y-auto">
              {loading ? (
                <p className="text-gray-400 text-center py-4">جاري التحميل...</p>
              ) : filteredUsers.length === 0 ? (
                <p className="text-gray-400 text-center py-4">لا توجد نتائج</p>
              ) : (
                <div className="space-y-2">
                  {filteredUsers.map(u => (
                    <div key={u.id} className="flex items-center justify-between p-3 bg-slate-700/50 rounded-lg">
                      <div>
                        <p className="text-white font-medium">{u.name || u.email}</p>
                        <p className="text-gray-400 text-sm">{u.email}</p>
                      </div>
                      <div className="flex items-center gap-2">
                        {editingUser === u.id ? (
                          <>
                            <Input
                              type="number"
                              value={newCredits}
                              onChange={(e) => setNewCredits(e.target.value)}
                              className="w-24 bg-slate-600 border-slate-500 text-white"
                              placeholder={u.credits}
                            />
                            <Button size="sm" onClick={() => updateUserCredits(u.id)} className="bg-green-600 hover:bg-green-700">
                              <Check className="w-4 h-4" />
                            </Button>
                            <Button size="sm" variant="outline" onClick={() => { setEditingUser(null); setNewCredits(''); }}>
                              <X className="w-4 h-4" />
                            </Button>
                          </>
                        ) : (
                          <>
                            <span className="text-amber-400 font-bold">{u.credits || 0}</span>
                            <Button 
                              size="sm" 
                              variant="outline" 
                              onClick={() => { setEditingUser(u.id); setNewCredits(u.credits?.toString() || '0'); }}
                              className="border-slate-600"
                            >
                              <Edit className="w-4 h-4" />
                            </Button>
                          </>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          {/* Pricing */}
          <Card className="bg-slate-800 border-slate-700">
            <CardHeader>
              <CardTitle className="text-white flex items-center gap-2">
                <Tag className="w-5 h-5 text-green-400" />
                أسعار الخدمات (بالنقاط)
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                {Object.entries(pricing).map(([key, value]) => (
                  <div key={key} className="space-y-1">
                    <Label className="text-gray-300 text-sm capitalize">
                      {key === 'website' ? 'موقع ويب' : 
                       key === 'game' ? 'لعبة' :
                       key === 'image' ? 'صورة' :
                       key === 'video' ? 'فيديو' :
                       key === 'modification' ? 'تعديل' :
                       key === 'save_template' ? 'حفظ قالب' :
                       key === 'export' ? 'تصدير' :
                       key === 'deploy' ? 'نشر' : key}
                    </Label>
                    <Input
                      type="number"
                      value={value}
                      onChange={(e) => setPricing({ ...pricing, [key]: parseInt(e.target.value) || 0 })}
                      className="bg-slate-700 border-slate-600 text-white"
                    />
                  </div>
                ))}
              </div>
              <Button onClick={savePricing} className="w-full bg-green-600 hover:bg-green-700">
                <Save className="w-4 h-4 me-2" />
                حفظ الأسعار
              </Button>
            </CardContent>
          </Card>

          {/* Offers */}
          <Card className="bg-slate-800 border-slate-700 lg:col-span-2">
            <CardHeader>
              <CardTitle className="text-white flex items-center gap-2">
                <Gift className="w-5 h-5 text-purple-400" />
                عروض شراء النقاط
              </CardTitle>
              <CardDescription className="text-gray-400">
                إضافة وإدارة عروض شراء النقاط للعملاء
              </CardDescription>
            </CardHeader>
            <CardContent>
              {/* Add New Offer */}
              <div className="bg-slate-700/50 rounded-lg p-4 mb-4">
                <h3 className="text-white font-medium mb-3 flex items-center gap-2">
                  <Plus className="w-4 h-4" />
                  إضافة عرض جديد
                </h3>
                <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
                  <div>
                    <Label className="text-gray-300 text-sm">اسم العرض</Label>
                    <Input
                      placeholder="عرض البداية"
                      value={newOffer.name}
                      onChange={(e) => setNewOffer({ ...newOffer, name: e.target.value })}
                      className="bg-slate-600 border-slate-500 text-white"
                    />
                  </div>
                  <div>
                    <Label className="text-gray-300 text-sm">عدد النقاط</Label>
                    <Input
                      type="number"
                      value={newOffer.credits}
                      onChange={(e) => setNewOffer({ ...newOffer, credits: parseInt(e.target.value) || 0 })}
                      className="bg-slate-600 border-slate-500 text-white"
                    />
                  </div>
                  <div>
                    <Label className="text-gray-300 text-sm">السعر ($)</Label>
                    <Input
                      type="number"
                      step="0.01"
                      value={newOffer.price}
                      onChange={(e) => setNewOffer({ ...newOffer, price: parseFloat(e.target.value) || 0 })}
                      className="bg-slate-600 border-slate-500 text-white"
                    />
                  </div>
                  <div>
                    <Label className="text-gray-300 text-sm">الخصم %</Label>
                    <Input
                      type="number"
                      value={newOffer.discount}
                      onChange={(e) => setNewOffer({ ...newOffer, discount: parseInt(e.target.value) || 0 })}
                      className="bg-slate-600 border-slate-500 text-white"
                    />
                  </div>
                  <div className="flex items-end">
                    <Button onClick={addOffer} className="w-full bg-purple-600 hover:bg-purple-700">
                      <Plus className="w-4 h-4 me-1" />
                      إضافة
                    </Button>
                  </div>
                </div>
              </div>

              {/* Offers List */}
              <div className="space-y-2">
                {offers.length === 0 ? (
                  <p className="text-gray-400 text-center py-4">لا توجد عروض</p>
                ) : (
                  offers.map(offer => (
                    <div 
                      key={offer.id} 
                      className={`flex items-center justify-between p-4 rounded-lg border ${
                        offer.is_active 
                          ? 'bg-gradient-to-r from-purple-500/10 to-pink-500/10 border-purple-500/30' 
                          : 'bg-slate-700/30 border-slate-600'
                      }`}
                    >
                      <div className="flex items-center gap-4">
                        <div className={`w-12 h-12 rounded-full flex items-center justify-center ${
                          offer.is_active ? 'bg-purple-500/20' : 'bg-slate-600'
                        }`}>
                          {offer.discount > 0 ? (
                            <Percent className="w-6 h-6 text-purple-400" />
                          ) : (
                            <Coins className="w-6 h-6 text-amber-400" />
                          )}
                        </div>
                        <div>
                          <p className="text-white font-medium">{offer.name}</p>
                          <p className="text-gray-400 text-sm">
                            {offer.credits} نقطة مقابل ${offer.price}
                            {offer.discount > 0 && (
                              <span className="text-green-400 ms-2">({offer.discount}% خصم)</span>
                            )}
                          </p>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <Button 
                          size="sm" 
                          variant={offer.is_active ? "default" : "outline"}
                          onClick={() => toggleOfferStatus(offer.id, offer.is_active)}
                          className={offer.is_active ? "bg-green-600 hover:bg-green-700" : ""}
                        >
                          {offer.is_active ? 'نشط' : 'معطل'}
                        </Button>
                        <Button 
                          size="sm" 
                          variant="outline" 
                          onClick={() => deleteOffer(offer.id)}
                          className="border-red-500/50 text-red-400 hover:bg-red-500/10"
                        >
                          <Trash2 className="w-4 h-4" />
                        </Button>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
};

export default AdminCredits;
