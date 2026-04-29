import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { toast } from 'sonner';
import { ArrowRight, Plus, Trash2, Edit, Eye, Upload, Brain, BarChart3, Code, Image, Gamepad2, Globe, ShoppingCart, Layout, Search, CheckCircle, XCircle, Loader2, Sparkles, CheckCheck, X } from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;

const CATEGORIES = [
  { id: 'game', label: 'ألعاب', icon: Gamepad2, color: 'from-purple-500 to-pink-500' },
  { id: 'website', label: 'مواقع', icon: Globe, color: 'from-blue-500 to-cyan-500' },
  { id: 'landing', label: 'صفحات هبوط', icon: Layout, color: 'from-green-500 to-emerald-500' },
  { id: 'ecommerce', label: 'متاجر', icon: ShoppingCart, color: 'from-amber-500 to-orange-500' },
  { id: 'portfolio', label: 'معارض أعمال', icon: Image, color: 'from-rose-500 to-red-500' },
  { id: 'dashboard', label: 'لوحات تحكم', icon: BarChart3, color: 'from-indigo-500 to-violet-500' },
];

const SUBCATEGORIES = {
  game: ['استراتيجية', 'أكشن', 'سباق', 'ألغاز', 'مطعم', 'أطفال', 'منصات', 'قتال'],
  website: ['شركة', 'تقنية', 'طبي', 'تعليمي', 'عقاري', 'مطاعم'],
  landing: ['منتج', 'خدمة', 'تطبيق', 'حدث', 'إطلاق'],
  ecommerce: ['ملابس', 'إلكترونيات', 'طعام', 'عام'],
  portfolio: ['مصمم', 'مطور', 'مصور', 'فنان'],
  dashboard: ['إدارة', 'تحليلات', 'CRM', 'مالي'],
};

const FETCH_SUGGESTIONS = [
  { label: 'ألعاب استراتيجية بناء قرى', category: 'game', source: 'codepen' },
  { label: 'ألعاب سباق سيارات', category: 'game', source: 'codepen' },
  { label: 'ألعاب ألغاز ذكاء', category: 'game', source: 'codepen' },
  { label: 'ألعاب أكشن ومنصات', category: 'game', source: 'codepen' },
  { label: 'مواقع شركات تقنية', category: 'website', source: 'codepen' },
  { label: 'صفحات هبوط SaaS', category: 'landing', source: 'codepen' },
  { label: 'متاجر إلكترونية فاخرة', category: 'ecommerce', source: 'codepen' },
  { label: 'لوحات تحكم إدارية', category: 'dashboard', source: 'codepen' },
];

export default function AdminTraining({ user }) {
  const navigate = useNavigate();
  const token = localStorage.getItem('token');
  const [examples, setExamples] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState(null);
  const [previewId, setPreviewId] = useState(null);
  const [filterCategory, setFilterCategory] = useState('');
  
  // Fetch panel state
  const [showFetch, setShowFetch] = useState(false);
  const [fetchQuery, setFetchQuery] = useState('');
  const [fetchCategory, setFetchCategory] = useState('game');
  const [fetchCount, setFetchCount] = useState(3);
  const [fetchSource, setFetchSource] = useState('codepen');
  const [fetching, setFetching] = useState(false);
  const [pendingTemplates, setPendingTemplates] = useState([]);
  const [pendingPreviewId, setPendingPreviewId] = useState(null);
  const [approvingId, setApprovingId] = useState(null);

  const [form, setForm] = useState({
    category: 'game', subcategory: '', title: '', description: '', design_image_url: '', html_code: '', tags: [],
  });

  const headers = { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' };

  const fetchData = useCallback(async () => {
    try {
      const url = filterCategory 
        ? `${API}/api/admin/training/examples?category=${filterCategory}`
        : `${API}/api/admin/training/examples`;
      const [exRes, stRes, pendRes] = await Promise.all([
        fetch(url, { headers }),
        fetch(`${API}/api/admin/training/stats`, { headers }),
        fetch(`${API}/api/admin/training/pending`, { headers })
      ]);
      setExamples((await exRes.json()).examples || []);
      setStats(await stRes.json());
      setPendingTemplates((await pendRes.json()).templates || []);
    } catch (e) {
      toast.error('فشل تحميل البيانات');
    } finally {
      setLoading(false);
    }
  }, [filterCategory, token]);

  useEffect(() => { fetchData(); }, [fetchData]);

  const handleSubmit = async () => {
    if (!form.title || !form.html_code) { toast.error('العنوان والكود مطلوبين'); return; }
    try {
      const url = editingId ? `${API}/api/admin/training/examples/${editingId}` : `${API}/api/admin/training/examples`;
      const res = await fetch(url, { method: editingId ? 'PUT' : 'POST', headers, body: JSON.stringify(form) });
      if (res.ok) {
        toast.success(editingId ? 'تم التحديث' : 'تم الإضافة');
        setShowForm(false); setEditingId(null);
        setForm({ category: 'game', subcategory: '', title: '', description: '', design_image_url: '', html_code: '', tags: [] });
        fetchData();
      }
    } catch (e) { toast.error('خطأ في الاتصال'); }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('حذف هذا المثال؟')) return;
    await fetch(`${API}/api/admin/training/examples/${id}`, { method: 'DELETE', headers });
    toast.success('تم الحذف'); fetchData();
  };

  const handleEdit = (ex) => {
    setForm({ category: ex.category, subcategory: ex.subcategory || '', title: ex.title, description: ex.description || '', design_image_url: ex.design_image_url || '', html_code: ex.html_code, tags: ex.tags || [] });
    setEditingId(ex.id); setShowForm(true);
  };

  const handleImageUpload = async (e) => {
    const file = e.target.files[0]; if (!file) return;
    const formData = new FormData(); formData.append('file', file);
    try {
      const res = await fetch(`${API}/api/admin/training/upload-image`, { method: 'POST', headers: { 'Authorization': `Bearer ${token}` }, body: formData });
      const data = await res.json();
      if (data.image_url) { setForm(prev => ({ ...prev, design_image_url: data.image_url })); toast.success('تم رفع الصورة'); }
    } catch (e) { toast.error('فشل رفع الصورة'); }
  };

  // Fetch templates from AI
  const handleFetchTemplates = async () => {
    if (!fetchQuery.trim()) { toast.error('اكتب وصف للقوالب المطلوبة'); return; }
    setFetching(true);
    try {
      const res = await fetch(`${API}/api/admin/training/fetch`, {
        method: 'POST', headers,
        body: JSON.stringify({ query: fetchQuery, category: fetchCategory, count: fetchCount, source: fetchSource })
      });
      if (res.ok) {
        const data = await res.json();
        toast.success(`تم جلب ${data.count} قوالب! راجعها واعتمد اللي يعجبك`);
        fetchData();
      } else {
        const err = await res.json();
        toast.error(err.detail || 'فشل الجلب');
      }
    } catch (e) { toast.error('خطأ في الاتصال'); }
    finally { setFetching(false); }
  };

  const handleApprove = async (id) => {
    setApprovingId(id);
    try {
      const res = await fetch(`${API}/api/admin/training/approve/${id}`, { method: 'POST', headers });
      if (res.ok) { toast.success('تم اعتماد القالب'); fetchData(); }
    } catch (e) { toast.error('فشل الاعتماد'); }
    finally { setApprovingId(null); }
  };

  const handleReject = async (id) => {
    await fetch(`${API}/api/admin/training/pending/${id}`, { method: 'DELETE', headers });
    toast.success('تم رفض القالب'); fetchData();
  };

  const handleApproveAll = async () => {
    if (!window.confirm(`اعتماد كل ${pendingTemplates.length} قوالب؟`)) return;
    const res = await fetch(`${API}/api/admin/training/approve-all`, { method: 'POST', headers });
    if (res.ok) { const d = await res.json(); toast.success(d.message); fetchData(); }
  };

  const handleRejectAll = async () => {
    if (!window.confirm('رفض كل القوالب المعلّقة؟')) return;
    await fetch(`${API}/api/admin/training/pending-all`, { method: 'DELETE', headers });
    toast.success('تم رفض الكل'); fetchData();
  };

  const previewExample = [...examples, ...pendingTemplates].find(e => e.id === previewId || e.id === pendingPreviewId);

  if (loading) return (
    <div className="min-h-screen bg-[#0a0a12] flex items-center justify-center">
      <div className="animate-spin w-8 h-8 border-2 border-amber-500 border-t-transparent rounded-full" />
    </div>
  );

  return (
    <div className="min-h-screen bg-[#0a0a12] text-white" data-testid="admin-training">
      {/* Header */}
      <div className="bg-[#0d0d18] border-b border-slate-800">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Button variant="ghost" onClick={() => navigate('/admin')} className="text-gray-400"><ArrowRight className="w-4 h-4" /></Button>
            <Brain className="w-6 h-6 text-amber-400" />
            <h1 className="text-xl font-bold text-amber-400">تدريب الذكاء الاصطناعي</h1>
          </div>
          <div className="flex gap-2">
            <Button onClick={() => setShowFetch(true)} className="bg-gradient-to-r from-purple-600 to-pink-600 border-0" data-testid="fetch-templates-btn">
              <Sparkles className="w-4 h-4 me-2" /> جلب قوالب من الذكاء
            </Button>
            <Button onClick={() => { setShowForm(true); setEditingId(null); setForm({ category: 'game', subcategory: '', title: '', description: '', design_image_url: '', html_code: '', tags: [] }); }}
              className="bg-gradient-to-r from-amber-600 to-yellow-600 border-0" data-testid="add-example-btn">
              <Plus className="w-4 h-4 me-2" /> إضافة يدوي
            </Button>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-6 py-6 space-y-6">
        {/* Stats */}
        {stats && (
          <div className="space-y-4">
            {/* Learning Stats Banner */}
            <div className="bg-gradient-to-r from-emerald-500/10 to-cyan-500/10 border border-emerald-500/30 rounded-2xl p-5" data-testid="learning-stats">
              <div className="flex items-center gap-2 mb-3">
                <Brain className="w-5 h-5 text-emerald-400" />
                <h2 className="font-bold text-emerald-300">التعلم الذاتي</h2>
                <span className="text-xs px-2 py-0.5 bg-emerald-500/20 text-emerald-400 rounded-full animate-pulse">نشط</span>
              </div>
              <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
                <div className="bg-black/30 rounded-xl p-3 text-center">
                  <p className="text-xl font-bold text-emerald-400">{stats.auto_learned || 0}</p>
                  <p className="text-xs text-gray-400">تعلّم تلقائي</p>
                </div>
                <div className="bg-black/30 rounded-xl p-3 text-center">
                  <p className="text-xl font-bold text-cyan-400">{stats.knowledge_rules || 0}</p>
                  <p className="text-xs text-gray-400">قواعد مكتسبة</p>
                </div>
                <div className="bg-black/30 rounded-xl p-3 text-center">
                  <p className="text-xl font-bold text-blue-400">{stats.total_generations || 0}</p>
                  <p className="text-xs text-gray-400">مشروع تم بناؤه</p>
                </div>
                <div className="bg-black/30 rounded-xl p-3 text-center">
                  <p className="text-xl font-bold text-amber-400">{stats.avg_quality_score || 0}/10</p>
                  <p className="text-xs text-gray-400">متوسط الجودة</p>
                </div>
                <div className="bg-black/30 rounded-xl p-3 text-center">
                  <p className="text-xl font-bold text-purple-400">{stats.total_examples || 0}</p>
                  <p className="text-xs text-gray-400">إجمالي الأمثلة</p>
                </div>
              </div>
              <p className="text-xs text-gray-500 mt-3">الذكاء يتحسّن تلقائياً مع كل مشروع ناجح. لما العميل يوافق على التصميم، الكود ينحفظ كمثال تدريبي. لما يرفض، النظام يتعلم السبب.</p>
            </div>

            {/* Category Stats */}
            <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-3" data-testid="training-stats">
              <div className="bg-gradient-to-br from-amber-500/20 to-yellow-500/10 border border-amber-500/30 rounded-xl p-4 text-center">
                <p className="text-2xl font-bold text-amber-400">{stats.total_examples}</p>
                <p className="text-xs text-gray-400">إجمالي الأمثلة</p>
              </div>
              {CATEGORIES.map(cat => (
                <div key={cat.id} className="bg-slate-800/30 border border-slate-700 rounded-xl p-4 text-center">
                  <p className="text-2xl font-bold">{stats.by_category?.[cat.id] || 0}</p>
                  <p className="text-xs text-gray-400">{cat.label}</p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Pending Templates Section */}
        {pendingTemplates.length > 0 && (
          <div className="bg-gradient-to-r from-purple-500/10 to-pink-500/10 border border-purple-500/30 rounded-2xl p-6" data-testid="pending-section">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-3">
                <Sparkles className="w-5 h-5 text-purple-400" />
                <h2 className="text-lg font-bold text-purple-300">قوالب مجلوبة تنتظر المراجعة ({pendingTemplates.length})</h2>
              </div>
              <div className="flex gap-2">
                <Button size="sm" onClick={handleApproveAll} className="bg-green-600 hover:bg-green-700 border-0" data-testid="approve-all-btn">
                  <CheckCheck className="w-4 h-4 me-1" /> اعتماد الكل
                </Button>
                <Button size="sm" variant="outline" onClick={handleRejectAll} className="border-red-700 text-red-400 hover:bg-red-500/10" data-testid="reject-all-btn">
                  <XCircle className="w-4 h-4 me-1" /> رفض الكل
                </Button>
              </div>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {pendingTemplates.map(tmpl => (
                <div key={tmpl.id} className="bg-[#0d0d18] border border-purple-500/20 rounded-xl overflow-hidden">
                  {/* Mini preview */}
                  <div className="h-36 relative overflow-hidden bg-white">
                    <iframe srcDoc={tmpl.html_code} className="w-full h-full pointer-events-none" style={{ transform: 'scale(0.5)', transformOrigin: 'top right', width: '200%', height: '200%' }} title={tmpl.title} />
                    <button onClick={() => { setPendingPreviewId(tmpl.id); setPreviewId(tmpl.id); }} 
                      className="absolute inset-0 bg-black/0 hover:bg-black/40 flex items-center justify-center opacity-0 hover:opacity-100 transition-all">
                      <Eye className="w-8 h-8 text-white" />
                    </button>
                  </div>
                  <div className="p-4 space-y-2">
                    <h3 className="font-bold text-white text-sm">{tmpl.title}</h3>
                    <div className="flex gap-1 flex-wrap">
                      <span className="text-xs px-2 py-0.5 bg-purple-500/20 text-purple-300 rounded-full">{tmpl.category}</span>
                      {tmpl.subcategory && <span className="text-xs px-2 py-0.5 bg-blue-500/20 text-blue-300 rounded-full">{tmpl.subcategory}</span>}
                      {tmpl.source_url && <a href={tmpl.source_url} target="_blank" rel="noreferrer" className="text-xs px-2 py-0.5 bg-green-500/20 text-green-300 rounded-full hover:bg-green-500/30">GitHub</a>}
                      {tmpl.fetch_source === 'ai' && <span className="text-xs px-2 py-0.5 bg-pink-500/20 text-pink-300 rounded-full">AI</span>}
                    </div>
                    {tmpl.source_author && <p className="text-xs text-gray-500">بواسطة: {tmpl.source_author}</p>}
                    <p className="text-xs text-gray-500">{tmpl.html_code?.length || 0} حرف</p>
                    <div className="flex gap-2 pt-1">
                      <Button size="sm" onClick={() => handleApprove(tmpl.id)} disabled={approvingId === tmpl.id}
                        className="flex-1 bg-green-600 hover:bg-green-700 border-0 text-xs" data-testid={`approve-${tmpl.id}`}>
                        {approvingId === tmpl.id ? <Loader2 className="w-3 h-3 animate-spin" /> : <><CheckCircle className="w-3 h-3 me-1" /> اعتماد</>}
                      </Button>
                      <Button size="sm" variant="outline" onClick={() => handleReject(tmpl.id)}
                        className="flex-1 border-red-700 text-red-400 hover:bg-red-500/10 text-xs" data-testid={`reject-${tmpl.id}`}>
                        <XCircle className="w-3 h-3 me-1" /> رفض
                      </Button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Category Filter */}
        <div className="flex flex-wrap gap-2" data-testid="category-filter">
          <Button size="sm" variant={!filterCategory ? 'default' : 'outline'} onClick={() => setFilterCategory('')}
            className={!filterCategory ? 'bg-amber-600' : 'border-slate-700 text-gray-400'}>الكل</Button>
          {CATEGORIES.map(cat => (
            <Button key={cat.id} size="sm" variant={filterCategory === cat.id ? 'default' : 'outline'}
              onClick={() => setFilterCategory(cat.id)}
              className={filterCategory === cat.id ? 'bg-amber-600' : 'border-slate-700 text-gray-400'}>
              <cat.icon className="w-3 h-3 me-1" /> {cat.label}
            </Button>
          ))}
        </div>

        {/* Approved Examples Grid */}
        {examples.length === 0 ? (
          <div className="text-center py-20 text-gray-500">
            <Brain className="w-16 h-16 mx-auto mb-4 opacity-30" />
            <p className="text-lg">لا توجد أمثلة تدريبية معتمدة</p>
            <p className="text-sm mt-2">اجلب قوالب من الذكاء الاصطناعي أو أضف أمثلة يدوياً</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4" data-testid="examples-grid">
            {examples.map(ex => (
              <div key={ex.id} className="bg-[#0d0d18] border border-slate-800 rounded-xl overflow-hidden hover:border-amber-500/30 transition-all group">
                <div className="h-40 relative overflow-hidden bg-white">
                  {ex.design_image_url ? (
                    <img src={ex.design_image_url.startsWith('/') ? API + ex.design_image_url : ex.design_image_url} alt={ex.title} className="w-full h-full object-cover group-hover:scale-105 transition-transform" />
                  ) : (
                    <>
                      <iframe srcDoc={ex.html_code} className="w-full h-full pointer-events-none" style={{ transform: 'scale(0.5)', transformOrigin: 'top right', width: '200%', height: '200%' }} title={ex.title} />
                      <div className="absolute inset-0 bg-black/0 group-hover:bg-black/30 transition-all" />
                    </>
                  )}
                </div>
                <div className="p-4 space-y-3">
                  <div className="flex items-start justify-between">
                    <div>
                      <h3 className="font-bold text-white text-sm">{ex.title}</h3>
                      <div className="flex gap-2 mt-1">
                        <span className="text-xs px-2 py-0.5 bg-amber-500/20 text-amber-400 rounded-full">{ex.category}</span>
                        {ex.subcategory && <span className="text-xs px-2 py-0.5 bg-blue-500/20 text-blue-400 rounded-full">{ex.subcategory}</span>}
                        {ex.source === 'ai_fetched' && <span className="text-xs px-2 py-0.5 bg-purple-500/20 text-purple-400 rounded-full">AI</span>}
                      </div>
                    </div>
                    <span className="text-xs text-gray-500">{ex.usage_count || 0}x</span>
                  </div>
                  {ex.description && <p className="text-xs text-gray-400 line-clamp-2">{ex.description}</p>}
                  <div className="flex gap-2">
                    <Button size="sm" variant="outline" onClick={() => setPreviewId(ex.id)} className="flex-1 border-slate-700 text-gray-400 hover:text-white">
                      <Eye className="w-3 h-3 me-1" /> معاينة
                    </Button>
                    <Button size="sm" variant="outline" onClick={() => handleEdit(ex)} className="border-slate-700 text-gray-400 hover:text-white"><Edit className="w-3 h-3" /></Button>
                    <Button size="sm" variant="outline" onClick={() => handleDelete(ex.id)} className="border-red-800 text-red-400 hover:bg-red-500/10"><Trash2 className="w-3 h-3" /></Button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Fetch Templates Modal */}
      {showFetch && (
        <div className="fixed inset-0 bg-black/80 z-50 flex items-center justify-center">
          <div className="bg-[#0d0d18] border border-purple-500/30 rounded-2xl w-full max-w-2xl mx-4" data-testid="fetch-modal">
            <div className="p-6 border-b border-slate-800 flex justify-between items-center">
              <div className="flex items-center gap-3">
                <Sparkles className="w-5 h-5 text-purple-400" />
                <h2 className="text-lg font-bold text-purple-300">جلب قوالب من الذكاء الاصطناعي</h2>
              </div>
              <Button variant="ghost" onClick={() => setShowFetch(false)} className="text-gray-400"><X className="w-4 h-4" /></Button>
            </div>
            <div className="p-6 space-y-5">
              {/* Quick suggestions */}
              <div>
                <label className="text-sm text-gray-400 mb-2 block">اقتراحات سريعة:</label>
                <div className="flex flex-wrap gap-2">
                  {FETCH_SUGGESTIONS.map((s, i) => (
                    <button key={i} onClick={() => { setFetchQuery(s.label); setFetchCategory(s.category); setFetchSource(s.source || 'codepen'); }}
                      className={`px-3 py-1.5 rounded-lg text-xs transition-all ${fetchQuery === s.label ? 'bg-purple-600 text-white' : 'bg-slate-800 text-gray-400 hover:bg-slate-700'}`}>
                      {s.label}
                    </button>
                  ))}
                </div>
              </div>

              {/* Custom query */}
              <div>
                <label className="text-sm text-gray-400 mb-1 block">أو اكتب طلبك:</label>
                <input type="text" value={fetchQuery} onChange={e => setFetchQuery(e.target.value)}
                  className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-3 text-white placeholder-gray-500 focus:border-purple-500 focus:outline-none"
                  placeholder="مثلاً: قوالب ألعاب أطفال تعليمية ملونة" data-testid="fetch-query-input" />
              </div>

              {/* Category */}
              <div>
                <label className="text-sm text-gray-400 mb-2 block">التصنيف:</label>
                <div className="flex flex-wrap gap-2">
                  {CATEGORIES.map(cat => (
                    <button key={cat.id} onClick={() => setFetchCategory(cat.id)}
                      className={`px-4 py-2 rounded-lg text-sm flex items-center gap-2 transition-all ${
                        fetchCategory === cat.id ? `bg-gradient-to-r ${cat.color} text-white` : 'bg-slate-800 text-gray-400 hover:bg-slate-700'
                      }`}><cat.icon className="w-4 h-4" /> {cat.label}</button>
                  ))}
                </div>
              </div>

              {/* Source */}
              <div>
                <label className="text-sm text-gray-400 mb-2 block">المصدر:</label>
                <div className="flex gap-3">
                  <button onClick={() => setFetchSource('codepen')}
                    className={`flex-1 px-4 py-3 rounded-xl text-sm flex items-center justify-center gap-2 transition-all border ${
                      fetchSource === 'codepen' ? 'bg-gradient-to-r from-green-600 to-emerald-600 border-green-500 text-white' : 'bg-slate-800 border-slate-700 text-gray-400 hover:bg-slate-700'
                    }`}>
                    <Globe className="w-4 h-4" /> GitHub (أكواد حقيقية)
                  </button>
                  <button onClick={() => setFetchSource('ai')}
                    className={`flex-1 px-4 py-3 rounded-xl text-sm flex items-center justify-center gap-2 transition-all border ${
                      fetchSource === 'ai' ? 'bg-gradient-to-r from-purple-600 to-pink-600 border-purple-500 text-white' : 'bg-slate-800 border-slate-700 text-gray-400 hover:bg-slate-700'
                    }`}>
                    <Sparkles className="w-4 h-4" /> ذكاء اصطناعي (توليد)
                  </button>
                </div>
              </div>

              {/* Count */}
              <div>
                <label className="text-sm text-gray-400 mb-2 block">عدد القوالب:</label>
                <div className="flex gap-2">
                  {[1, 2, 3, 5].map(n => (
                    <button key={n} onClick={() => setFetchCount(n)}
                      className={`w-12 h-12 rounded-xl text-lg font-bold transition-all ${
                        fetchCount === n ? 'bg-purple-600 text-white' : 'bg-slate-800 text-gray-400 hover:bg-slate-700'
                      }`}>{n}</button>
                  ))}
                </div>
              </div>
            </div>
            <div className="p-6 border-t border-slate-800 flex gap-3 justify-end">
              <Button variant="outline" onClick={() => setShowFetch(false)} className="border-slate-700 text-gray-400">إلغاء</Button>
              <Button onClick={handleFetchTemplates} disabled={fetching} className="bg-gradient-to-r from-purple-600 to-pink-600 border-0" data-testid="fetch-submit-btn">
                {fetching ? <><Loader2 className="w-4 h-4 me-2 animate-spin" /> جاري الجلب...</> : <><Search className="w-4 h-4 me-2" /> جلب القوالب</>}
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Add/Edit Form Modal */}
      {showForm && (
        <div className="fixed inset-0 bg-black/80 z-50 flex items-start justify-center overflow-y-auto py-10">
          <div className="bg-[#0d0d18] border border-slate-800 rounded-2xl w-full max-w-4xl mx-4" data-testid="training-form">
            <div className="p-6 border-b border-slate-800 flex justify-between items-center">
              <h2 className="text-lg font-bold text-amber-400">{editingId ? 'تعديل المثال' : 'إضافة مثال تدريبي جديد'}</h2>
              <Button variant="ghost" onClick={() => { setShowForm(false); setEditingId(null); }} className="text-gray-400"><X className="w-4 h-4" /></Button>
            </div>
            <div className="p-6 space-y-4">
              <div>
                <label className="text-sm text-gray-400 mb-2 block">التصنيف</label>
                <div className="flex flex-wrap gap-2">
                  {CATEGORIES.map(cat => (
                    <button key={cat.id} onClick={() => setForm(p => ({ ...p, category: cat.id, subcategory: '' }))}
                      className={`px-4 py-2 rounded-lg text-sm flex items-center gap-2 transition-all ${form.category === cat.id ? `bg-gradient-to-r ${cat.color} text-white` : 'bg-slate-800 text-gray-400 hover:bg-slate-700'}`}>
                      <cat.icon className="w-4 h-4" /> {cat.label}</button>
                  ))}
                </div>
              </div>
              {SUBCATEGORIES[form.category] && (
                <div>
                  <label className="text-sm text-gray-400 mb-2 block">التصنيف الفرعي</label>
                  <div className="flex flex-wrap gap-2">
                    {SUBCATEGORIES[form.category].map(sub => (
                      <button key={sub} onClick={() => setForm(p => ({ ...p, subcategory: sub }))}
                        className={`px-3 py-1.5 rounded-lg text-xs transition-all ${form.subcategory === sub ? 'bg-amber-600 text-white' : 'bg-slate-800 text-gray-400 hover:bg-slate-700'}`}>{sub}</button>
                    ))}
                  </div>
                </div>
              )}
              <div>
                <label className="text-sm text-gray-400 mb-1 block">العنوان *</label>
                <input type="text" value={form.title} onChange={e => setForm(p => ({ ...p, title: e.target.value }))}
                  className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-2.5 text-white focus:border-amber-500 focus:outline-none" placeholder="مثلاً: لعبة استراتيجية بناء قرى" data-testid="training-title-input" />
              </div>
              <div>
                <label className="text-sm text-gray-400 mb-1 block">الوصف</label>
                <input type="text" value={form.description} onChange={e => setForm(p => ({ ...p, description: e.target.value }))}
                  className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-2.5 text-white focus:border-amber-500 focus:outline-none" placeholder="وصف مختصر" />
              </div>
              <div>
                <label className="text-sm text-gray-400 mb-1 block">صورة التصميم</label>
                <div className="flex gap-3 items-center">
                  <label className="flex items-center gap-2 px-4 py-2.5 bg-slate-800 border border-slate-700 rounded-lg cursor-pointer hover:border-amber-500/50 transition">
                    <Upload className="w-4 h-4 text-gray-400" /><span className="text-sm text-gray-400">رفع صورة</span>
                    <input type="file" accept="image/*" className="hidden" onChange={handleImageUpload} />
                  </label>
                  {form.design_image_url && <img src={form.design_image_url.startsWith('/') ? API + form.design_image_url : form.design_image_url} alt="preview" className="w-16 h-16 rounded-lg object-cover border border-slate-700" />}
                </div>
              </div>
              <div>
                <label className="text-sm text-gray-400 mb-1 block">كود HTML *</label>
                <textarea value={form.html_code} onChange={e => setForm(p => ({ ...p, html_code: e.target.value }))}
                  className="w-full h-64 bg-[#1a1a2e] border border-slate-700 rounded-lg px-4 py-3 text-green-400 font-mono text-xs focus:border-amber-500 focus:outline-none resize-none" dir="ltr" data-testid="training-code-input" />
                <p className="text-xs text-gray-500 mt-1">{form.html_code.length} حرف</p>
              </div>
              <div>
                <label className="text-sm text-gray-400 mb-1 block">الوسوم</label>
                <input type="text" value={form.tags.join(', ')} onChange={e => setForm(p => ({ ...p, tags: e.target.value.split(',').map(t => t.trim()).filter(Boolean) }))}
                  className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-2.5 text-white focus:border-amber-500 focus:outline-none" placeholder="كرتوني, تفاعلي" />
              </div>
            </div>
            <div className="p-6 border-t border-slate-800 flex gap-3 justify-end">
              <Button variant="outline" onClick={() => { setShowForm(false); setEditingId(null); }} className="border-slate-700 text-gray-400">إلغاء</Button>
              <Button onClick={handleSubmit} className="bg-gradient-to-r from-amber-600 to-yellow-600 border-0" data-testid="training-submit-btn">{editingId ? 'تحديث' : 'إضافة'}</Button>
            </div>
          </div>
        </div>
      )}

      {/* Preview Modal */}
      {(previewId || pendingPreviewId) && previewExample && (
        <div className="fixed inset-0 bg-black/90 z-50 flex flex-col">
          <div className="flex items-center justify-between p-4 bg-[#0d0d18] border-b border-slate-800">
            <h3 className="text-amber-400 font-bold">{previewExample.title}</h3>
            <Button variant="ghost" onClick={() => { setPreviewId(null); setPendingPreviewId(null); }} className="text-gray-400"><X className="w-4 h-4" /></Button>
          </div>
          <iframe srcDoc={previewExample.html_code} className="flex-1 w-full bg-white" title="Preview" sandbox="allow-scripts allow-same-origin" data-testid="training-preview-iframe" />
        </div>
      )}
    </div>
  );
}
