/* Phase 2 dashboard tabs: Courses, Memberships, Events, Driver Analytics */
import React, { useCallback, useEffect, useState } from 'react';
import { BookOpen, CreditCard, Calendar, BarChart3, Plus, Trash2, RefreshCw, TrendingUp, Clock, Star, Award } from 'lucide-react';
import { toast } from 'sonner';

const API = process.env.REACT_APP_BACKEND_URL;
const authH = (token) => ({ Authorization: `ClientToken ${token}` });

/* ═════════════════════════════════════════════════════════════════
   🎓 COURSES TAB — academy vertical
   ═════════════════════════════════════════════════════════════════ */
export function CoursesTab({ token }) {
  const [courses, setCourses] = useState([]);
  const [enrollments, setEnrollments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [form, setForm] = useState({ title: '', description: '', price: 0, duration_hours: 1, instructor: '', level: 'beginner' });

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [c, e] = await Promise.all([
        fetch(`${API}/api/websites/client/courses`, { headers: authH(token) }).then(r => r.json()),
        fetch(`${API}/api/websites/client/enrollments`, { headers: authH(token) }).then(r => r.json()),
      ]);
      setCourses(c.courses || []);
      setEnrollments(e.enrollments || []);
    } catch (_) {} finally { setLoading(false); }
  }, [token]);

  useEffect(() => { load(); }, [load]);

  const create = async () => {
    if (!form.title.trim()) { toast.error('أدخل عنوان الدورة'); return; }
    try {
      await fetch(`${API}/api/websites/client/courses`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...authH(token) },
        body: JSON.stringify({ ...form, price: parseFloat(form.price) || 0, duration_hours: parseFloat(form.duration_hours) || 0 }),
      });
      toast.success('تمت إضافة الدورة');
      setCreating(false);
      setForm({ title: '', description: '', price: 0, duration_hours: 1, instructor: '', level: 'beginner' });
      load();
    } catch (_) { toast.error('فشل'); }
  };

  const del = async (id) => {
    if (!window.confirm('حذف الدورة نهائياً؟')) return;
    try {
      await fetch(`${API}/api/websites/client/courses/${id}`, { method: 'DELETE', headers: authH(token) });
      toast.success('تم الحذف');
      load();
    } catch (_) {}
  };

  return (
    <div className="space-y-4" data-testid="courses-tab">
      <div className="bg-gradient-to-br from-amber-600/10 to-orange-600/10 border border-amber-500/30 rounded-2xl p-4 flex items-start gap-3">
        <BookOpen className="w-6 h-6 text-amber-400 shrink-0 mt-1" />
        <div className="flex-1">
          <h3 className="font-bold mb-1">🎓 محرك الدورات</h3>
          <div className="text-xs opacity-80">أضف الدورات، حدد السعر والمدرب، وتابع التسجيلات من لوحة واحدة.</div>
        </div>
        <button onClick={() => setCreating(true)} className="px-4 py-2 bg-amber-500 hover:bg-amber-600 text-black rounded-lg text-sm font-bold flex items-center gap-1.5" data-testid="add-course-btn">
          <Plus className="w-4 h-4" />دورة جديدة
        </button>
      </div>

      {creating && (
        <div className="bg-white/3 border border-amber-500/30 rounded-xl p-4 space-y-2">
          <h4 className="font-bold mb-2">دورة جديدة</h4>
          <input placeholder="عنوان الدورة" value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} className="w-full px-3 py-2 bg-white/5 border border-white/15 rounded-lg text-sm" data-testid="course-title-input" />
          <textarea placeholder="وصف مختصر" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} className="w-full px-3 py-2 bg-white/5 border border-white/15 rounded-lg text-sm" rows={2} />
          <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
            <input type="number" placeholder="السعر" value={form.price} onChange={(e) => setForm({ ...form, price: e.target.value })} className="px-3 py-2 bg-white/5 border border-white/15 rounded-lg text-sm" />
            <input type="number" placeholder="ساعات" value={form.duration_hours} onChange={(e) => setForm({ ...form, duration_hours: e.target.value })} className="px-3 py-2 bg-white/5 border border-white/15 rounded-lg text-sm" />
            <input placeholder="المدرب" value={form.instructor} onChange={(e) => setForm({ ...form, instructor: e.target.value })} className="px-3 py-2 bg-white/5 border border-white/15 rounded-lg text-sm" />
            <select value={form.level} onChange={(e) => setForm({ ...form, level: e.target.value })} className="px-3 py-2 bg-white/5 border border-white/15 rounded-lg text-sm">
              <option value="beginner">مبتدئ</option><option value="intermediate">متوسط</option><option value="advanced">متقدم</option>
            </select>
          </div>
          <div className="flex gap-2">
            <button onClick={create} className="px-4 py-2 bg-green-500 text-black rounded-lg text-sm font-bold" data-testid="save-course-btn">احفظ</button>
            <button onClick={() => setCreating(false)} className="px-4 py-2 bg-white/10 rounded-lg text-sm">إلغاء</button>
          </div>
        </div>
      )}

      <div>
        <h3 className="font-bold mb-2">الدورات ({courses.length})</h3>
        {loading ? <div className="opacity-60">...</div> : courses.length === 0 ? (
          <div className="text-center py-10 opacity-60 bg-white/3 rounded-2xl">لا توجد دورات بعد</div>
        ) : (
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {courses.map((c) => (
              <div key={c.id} className="bg-white/5 border border-white/10 rounded-xl p-3" data-testid={`course-${c.id}`}>
                <div className="flex items-start justify-between mb-2">
                  <div className="flex-1 min-w-0">
                    <div className="font-bold truncate">{c.title}</div>
                    <div className="text-xs opacity-60 truncate">{c.instructor || '—'}</div>
                  </div>
                  <button onClick={() => del(c.id)} className="p-1 hover:bg-red-500/20 rounded text-red-400"><Trash2 className="w-4 h-4" /></button>
                </div>
                <div className="text-xs opacity-80 line-clamp-2 mb-2">{c.description}</div>
                <div className="flex items-center gap-2 text-xs">
                  <span className="px-2 py-0.5 bg-amber-500/20 text-amber-300 rounded">{c.price} ر.س</span>
                  <span className="px-2 py-0.5 bg-blue-500/20 text-blue-300 rounded">{c.duration_hours || 0}س</span>
                  <span className="px-2 py-0.5 bg-purple-500/20 text-purple-300 rounded">{c.level}</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <div>
        <h3 className="font-bold mb-2">التسجيلات ({enrollments.length})</h3>
        {enrollments.length === 0 ? (
          <div className="text-center py-6 opacity-60 text-sm">لا تسجيلات بعد</div>
        ) : (
          <div className="space-y-1">
            {enrollments.slice().reverse().map((e) => (
              <div key={e.id} className="bg-white/3 border border-white/10 rounded-lg p-2.5 flex items-center gap-2 text-sm">
                <div className="flex-1">
                  <span className="font-bold">{e.customer_name}</span> · <span className="opacity-70">{e.course_title}</span>
                </div>
                <span className="text-xs opacity-60">{e.customer_phone}</span>
                <span className="text-xs px-2 py-0.5 bg-green-500/20 text-green-300 rounded">{e.price} ر.س</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

/* ═════════════════════════════════════════════════════════════════
   🏋️ MEMBERSHIPS TAB — gym, sports_club verticals
   ═════════════════════════════════════════════════════════════════ */
export function MembershipsTab({ token }) {
  const [plans, setPlans] = useState([]);
  const [subs, setSubs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [form, setForm] = useState({ name: '', price: 0, period_days: 30, benefits: '', featured: false });

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [p, s] = await Promise.all([
        fetch(`${API}/api/websites/client/membership-plans`, { headers: authH(token) }).then(r => r.json()),
        fetch(`${API}/api/websites/client/subscriptions`, { headers: authH(token) }).then(r => r.json()),
      ]);
      setPlans(p.plans || []);
      setSubs(s.subscriptions || []);
    } catch (_) {} finally { setLoading(false); }
  }, [token]);

  useEffect(() => { load(); }, [load]);

  const create = async () => {
    if (!form.name.trim()) { toast.error('أدخل اسم الخطة'); return; }
    try {
      await fetch(`${API}/api/websites/client/membership-plans`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...authH(token) },
        body: JSON.stringify({
          ...form,
          price: parseFloat(form.price) || 0,
          period_days: parseInt(form.period_days) || 30,
          benefits: form.benefits.split('\n').map(x => x.trim()).filter(Boolean),
        }),
      });
      toast.success('تمت الإضافة');
      setCreating(false);
      setForm({ name: '', price: 0, period_days: 30, benefits: '', featured: false });
      load();
    } catch (_) { toast.error('فشل'); }
  };

  const del = async (id) => {
    if (!window.confirm('حذف الخطة؟')) return;
    try {
      await fetch(`${API}/api/websites/client/membership-plans/${id}`, { method: 'DELETE', headers: authH(token) });
      toast.success('حُذفت');
      load();
    } catch (_) {}
  };

  const activeSubs = subs.filter(s => s.status_computed === 'active').length;
  const expiredSubs = subs.length - activeSubs;
  const revenue = subs.reduce((a, s) => a + (parseFloat(s.price) || 0), 0);

  return (
    <div className="space-y-4" data-testid="memberships-tab">
      <div className="bg-gradient-to-br from-cyan-600/10 to-blue-600/10 border border-cyan-500/30 rounded-2xl p-4 flex items-start gap-3">
        <CreditCard className="w-6 h-6 text-cyan-400 shrink-0 mt-1" />
        <div className="flex-1">
          <h3 className="font-bold mb-1">🏋️ محرك العضويات</h3>
          <div className="text-xs opacity-80">خطط قابلة للتجديد، اشتراكات نشطة، تتبع تلقائي لتواريخ الانتهاء.</div>
        </div>
        <button onClick={() => setCreating(true)} className="px-4 py-2 bg-cyan-500 hover:bg-cyan-600 text-black rounded-lg text-sm font-bold flex items-center gap-1.5" data-testid="add-plan-btn">
          <Plus className="w-4 h-4" />خطة جديدة
        </button>
      </div>

      <div className="grid grid-cols-3 gap-2">
        <div className="bg-green-500/10 border border-green-500/20 rounded-lg p-3 text-center">
          <div className="text-2xl font-black text-green-400">{activeSubs}</div>
          <div className="text-xs opacity-70">نشطة</div>
        </div>
        <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-3 text-center">
          <div className="text-2xl font-black text-red-400">{expiredSubs}</div>
          <div className="text-xs opacity-70">منتهية</div>
        </div>
        <div className="bg-amber-500/10 border border-amber-500/20 rounded-lg p-3 text-center">
          <div className="text-2xl font-black text-amber-400">{revenue.toFixed(0)}</div>
          <div className="text-xs opacity-70">ريال إجمالي</div>
        </div>
      </div>

      {creating && (
        <div className="bg-white/3 border border-cyan-500/30 rounded-xl p-4 space-y-2">
          <input placeholder="اسم الخطة (مثل: شهري VIP)" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} className="w-full px-3 py-2 bg-white/5 border border-white/15 rounded-lg text-sm" data-testid="plan-name-input" />
          <div className="grid grid-cols-3 gap-2">
            <input type="number" placeholder="السعر" value={form.price} onChange={(e) => setForm({ ...form, price: e.target.value })} className="px-3 py-2 bg-white/5 border border-white/15 rounded-lg text-sm" />
            <input type="number" placeholder="المدة بالأيام" value={form.period_days} onChange={(e) => setForm({ ...form, period_days: e.target.value })} className="px-3 py-2 bg-white/5 border border-white/15 rounded-lg text-sm" />
            <label className="flex items-center gap-1 px-3 py-2 bg-white/5 border border-white/15 rounded-lg text-sm cursor-pointer">
              <input type="checkbox" checked={form.featured} onChange={(e) => setForm({ ...form, featured: e.target.checked })} /> مميّزة
            </label>
          </div>
          <textarea placeholder="المميزات (سطر لكل ميزة)" value={form.benefits} onChange={(e) => setForm({ ...form, benefits: e.target.value })} className="w-full px-3 py-2 bg-white/5 border border-white/15 rounded-lg text-sm" rows={3} />
          <div className="flex gap-2">
            <button onClick={create} className="px-4 py-2 bg-green-500 text-black rounded-lg text-sm font-bold" data-testid="save-plan-btn">احفظ</button>
            <button onClick={() => setCreating(false)} className="px-4 py-2 bg-white/10 rounded-lg text-sm">إلغاء</button>
          </div>
        </div>
      )}

      <div>
        <h3 className="font-bold mb-2">الخطط ({plans.length})</h3>
        {loading ? <div className="opacity-60">...</div> : plans.length === 0 ? (
          <div className="text-center py-10 opacity-60 bg-white/3 rounded-2xl">لا خطط بعد</div>
        ) : (
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {plans.map((p) => (
              <div key={p.id} className={`rounded-xl p-3 border ${p.featured ? 'bg-cyan-500/10 border-cyan-500/50' : 'bg-white/5 border-white/10'}`} data-testid={`plan-${p.id}`}>
                <div className="flex items-start justify-between mb-1">
                  <div className="flex-1">
                    <div className="font-bold flex items-center gap-1">{p.name}{p.featured && <span className="text-[9px] px-1.5 bg-cyan-500/30 rounded">مميّزة</span>}</div>
                    <div className="text-xs opacity-60">{p.period_days} يوم</div>
                  </div>
                  <button onClick={() => del(p.id)} className="p-1 hover:bg-red-500/20 rounded text-red-400"><Trash2 className="w-4 h-4" /></button>
                </div>
                <div className="text-2xl font-black text-amber-400 my-2">{p.price} <span className="text-xs opacity-60">ر.س</span></div>
                <ul className="space-y-0.5 text-xs opacity-80">
                  {(p.benefits || []).map((b, i) => <li key={i}>✓ {b}</li>)}
                </ul>
              </div>
            ))}
          </div>
        )}
      </div>

      {subs.length > 0 && (
        <div>
          <h3 className="font-bold mb-2">الاشتراكات الأخيرة</h3>
          <div className="space-y-1">
            {subs.slice().reverse().slice(0, 10).map((s) => (
              <div key={s.id} className="bg-white/3 border border-white/10 rounded-lg p-2.5 flex items-center gap-2 text-sm">
                <div className="flex-1">
                  <span className="font-bold">{s.customer_name}</span> · <span className="opacity-70">{s.plan_name}</span>
                </div>
                <span className={`text-xs px-2 py-0.5 rounded ${s.status_computed === 'active' ? 'bg-green-500/20 text-green-300' : 'bg-red-500/20 text-red-300'}`}>
                  {s.status_computed === 'active' ? 'نشطة' : 'منتهية'}
                </span>
                <span className="text-xs opacity-60">حتى {new Date(s.ends_at).toLocaleDateString('ar-SA')}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

/* ═════════════════════════════════════════════════════════════════
   🎫 EVENTS TAB — ticketed events
   ═════════════════════════════════════════════════════════════════ */
export function EventsTab({ token }) {
  const [events, setEvents] = useState([]);
  const [tickets, setTickets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [form, setForm] = useState({ title: '', description: '', starts_at: '', price: 0, capacity: 100, venue: '' });

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [e, t] = await Promise.all([
        fetch(`${API}/api/websites/client/events`, { headers: authH(token) }).then(r => r.json()),
        fetch(`${API}/api/websites/client/tickets`, { headers: authH(token) }).then(r => r.json()),
      ]);
      setEvents(e.events || []);
      setTickets(t.tickets || []);
    } catch (_) {} finally { setLoading(false); }
  }, [token]);

  useEffect(() => { load(); }, [load]);

  const create = async () => {
    if (!form.title.trim() || !form.starts_at) { toast.error('أدخل العنوان والتاريخ'); return; }
    try {
      await fetch(`${API}/api/websites/client/events`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...authH(token) },
        body: JSON.stringify({
          ...form,
          price: parseFloat(form.price) || 0,
          capacity: parseInt(form.capacity) || 100,
          starts_at: new Date(form.starts_at).toISOString(),
        }),
      });
      toast.success('تمت الإضافة');
      setCreating(false);
      setForm({ title: '', description: '', starts_at: '', price: 0, capacity: 100, venue: '' });
      load();
    } catch (_) { toast.error('فشل'); }
  };

  const del = async (id) => {
    if (!window.confirm('حذف الفعالية؟')) return;
    try {
      await fetch(`${API}/api/websites/client/events/${id}`, { method: 'DELETE', headers: authH(token) });
      load();
    } catch (_) {}
  };

  const totalRevenue = tickets.reduce((a, t) => a + (parseFloat(t.total) || 0), 0);

  return (
    <div className="space-y-4" data-testid="events-tab">
      <div className="bg-gradient-to-br from-pink-600/10 to-purple-600/10 border border-pink-500/30 rounded-2xl p-4 flex items-start gap-3">
        <Calendar className="w-6 h-6 text-pink-400 shrink-0 mt-1" />
        <div className="flex-1">
          <h3 className="font-bold mb-1">🎫 فعاليات وتذاكر</h3>
          <div className="text-xs opacity-80">أنشئ فعاليات بيع تذاكر، حدد السعة والسعر، وراقب الحجوزات فوراً.</div>
        </div>
        <button onClick={() => setCreating(true)} className="px-4 py-2 bg-pink-500 hover:bg-pink-600 text-white rounded-lg text-sm font-bold flex items-center gap-1.5" data-testid="add-event-btn">
          <Plus className="w-4 h-4" />فعالية جديدة
        </button>
      </div>

      <div className="grid grid-cols-3 gap-2">
        <div className="bg-pink-500/10 border border-pink-500/20 rounded-lg p-3 text-center">
          <div className="text-2xl font-black text-pink-400">{events.length}</div>
          <div className="text-xs opacity-70">فعاليات</div>
        </div>
        <div className="bg-blue-500/10 border border-blue-500/20 rounded-lg p-3 text-center">
          <div className="text-2xl font-black text-blue-400">{tickets.reduce((a, t) => a + (t.quantity || 1), 0)}</div>
          <div className="text-xs opacity-70">تذاكر مباعة</div>
        </div>
        <div className="bg-green-500/10 border border-green-500/20 rounded-lg p-3 text-center">
          <div className="text-2xl font-black text-green-400">{totalRevenue.toFixed(0)}</div>
          <div className="text-xs opacity-70">ريال إجمالي</div>
        </div>
      </div>

      {creating && (
        <div className="bg-white/3 border border-pink-500/30 rounded-xl p-4 space-y-2">
          <input placeholder="عنوان الفعالية" value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} className="w-full px-3 py-2 bg-white/5 border border-white/15 rounded-lg text-sm" data-testid="event-title-input" />
          <textarea placeholder="الوصف" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} className="w-full px-3 py-2 bg-white/5 border border-white/15 rounded-lg text-sm" rows={2} />
          <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
            <input type="datetime-local" value={form.starts_at} onChange={(e) => setForm({ ...form, starts_at: e.target.value })} className="px-3 py-2 bg-white/5 border border-white/15 rounded-lg text-sm" />
            <input type="number" placeholder="السعر" value={form.price} onChange={(e) => setForm({ ...form, price: e.target.value })} className="px-3 py-2 bg-white/5 border border-white/15 rounded-lg text-sm" />
            <input type="number" placeholder="السعة" value={form.capacity} onChange={(e) => setForm({ ...form, capacity: e.target.value })} className="px-3 py-2 bg-white/5 border border-white/15 rounded-lg text-sm" />
            <input placeholder="المكان" value={form.venue} onChange={(e) => setForm({ ...form, venue: e.target.value })} className="px-3 py-2 bg-white/5 border border-white/15 rounded-lg text-sm" />
          </div>
          <div className="flex gap-2">
            <button onClick={create} className="px-4 py-2 bg-green-500 text-black rounded-lg text-sm font-bold" data-testid="save-event-btn">احفظ</button>
            <button onClick={() => setCreating(false)} className="px-4 py-2 bg-white/10 rounded-lg text-sm">إلغاء</button>
          </div>
        </div>
      )}

      {loading ? <div className="opacity-60">...</div> : events.length === 0 ? (
        <div className="text-center py-10 opacity-60 bg-white/3 rounded-2xl">لا فعاليات بعد</div>
      ) : (
        <div className="grid sm:grid-cols-2 gap-3">
          {events.map((e) => {
            const pct = e.capacity > 0 ? Math.round(100 * (e.tickets_sold || 0) / e.capacity) : 0;
            return (
              <div key={e.id} className="bg-white/5 border border-white/10 rounded-xl p-3" data-testid={`event-${e.id}`}>
                <div className="flex items-start justify-between mb-1">
                  <div className="flex-1 min-w-0">
                    <div className="font-bold truncate">{e.title}</div>
                    <div className="text-xs opacity-60">{e.venue || '—'}</div>
                  </div>
                  <button onClick={() => del(e.id)} className="p-1 hover:bg-red-500/20 rounded text-red-400"><Trash2 className="w-4 h-4" /></button>
                </div>
                <div className="text-xs opacity-70 mb-2">{new Date(e.starts_at).toLocaleString('ar-SA')}</div>
                <div className="h-2 bg-white/10 rounded-full overflow-hidden mb-1">
                  <div className="h-full bg-gradient-to-r from-pink-500 to-purple-500" style={{ width: `${pct}%` }} />
                </div>
                <div className="flex items-center justify-between text-xs">
                  <span className="opacity-70">{e.tickets_sold || 0} / {e.capacity}</span>
                  <span className="font-bold text-amber-400">{e.price} ر.س</span>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

/* ═════════════════════════════════════════════════════════════════
   📊 DRIVER ANALYTICS TAB
   ═════════════════════════════════════════════════════════════════ */
export function DriverAnalyticsTab({ token }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [days, setDays] = useState(7);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const r = await fetch(`${API}/api/websites/client/drivers/analytics?days=${days}`, { headers: authH(token) });
      setData(await r.json());
    } catch (_) {} finally { setLoading(false); }
  }, [token, days]);

  useEffect(() => { load(); }, [load]);

  const stat = (icon, label, value, color = 'text-white') => (
    <div className="bg-white/5 border border-white/10 rounded-xl p-3">
      <div className="flex items-center gap-1.5 text-xs opacity-70 mb-1">{icon}{label}</div>
      <div className={`text-2xl font-black ${color}`}>{value}</div>
    </div>
  );

  return (
    <div className="space-y-4" data-testid="driver-analytics-tab">
      <div className="bg-gradient-to-br from-green-600/10 to-emerald-600/10 border border-green-500/30 rounded-2xl p-4 flex items-center gap-3 flex-wrap">
        <BarChart3 className="w-6 h-6 text-green-400 shrink-0" />
        <div className="flex-1 min-w-0">
          <h3 className="font-bold">📊 أداء السائقين الأسبوعي</h3>
          <div className="text-xs opacity-80">KPIs لكل سائق — أوقات توصيل، تقييمات، إيرادات</div>
        </div>
        <div className="flex gap-1">
          {[7, 14, 30].map(d => (
            <button key={d} onClick={() => setDays(d)} className={`px-3 py-1.5 rounded-lg text-xs font-bold ${days === d ? 'bg-green-500 text-black' : 'bg-white/5 hover:bg-white/10'}`} data-testid={`days-${d}`}>
              {d} يوم
            </button>
          ))}
        </div>
        <button onClick={load} className="p-2 hover:bg-white/10 rounded-lg" data-testid="refresh-analytics"><RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} /></button>
      </div>

      {!data ? <div className="opacity-60">جاري التحميل...</div> : (
        <>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
            {stat(<TrendingUp className="w-3.5 h-3.5 text-green-400" />, 'إجمالي الطلبات', data.total_orders, 'text-green-400')}
            {stat(<Award className="w-3.5 h-3.5 text-blue-400" />, 'عدد السائقين', data.total_drivers, 'text-blue-400')}
            {stat(<Clock className="w-3.5 h-3.5 text-amber-400" />, 'فترة التحليل', `${data.window_days} يوم`, 'text-amber-400')}
            {stat(<Star className="w-3.5 h-3.5 text-purple-400" />, 'أعلى أداء',
              (data.drivers?.[0]?.driver_name || '—') + ` (${data.drivers?.[0]?.orders_completed || 0})`, 'text-purple-400')}
          </div>
          {data.drivers?.length === 0 ? (
            <div className="text-center py-10 opacity-60 bg-white/3 rounded-2xl">لا سائقين بعد — أضفهم من تبويب "السائقين"</div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-white/5 text-right">
                    <th className="p-2 text-right">السائق</th>
                    <th className="p-2">الطلبات</th>
                    <th className="p-2">مكتمل</th>
                    <th className="p-2">نسبة</th>
                    <th className="p-2">وقت توصيل متوسط</th>
                    <th className="p-2">تقييم</th>
                    <th className="p-2">إيرادات</th>
                  </tr>
                </thead>
                <tbody>
                  {data.drivers.map((d) => (
                    <tr key={d.driver_id} className="border-b border-white/5" data-testid={`driver-row-${d.driver_id}`}>
                      <td className="p-2 text-right">
                        <div className="font-bold">{d.driver_name || '—'}</div>
                        <div className="text-xs opacity-60">{d.phone}</div>
                      </td>
                      <td className="p-2 text-center">{d.orders_assigned}</td>
                      <td className="p-2 text-center text-green-400 font-bold">{d.orders_completed}</td>
                      <td className="p-2 text-center">
                        <span className={`text-xs px-2 py-0.5 rounded ${d.completion_rate >= 90 ? 'bg-green-500/20 text-green-300' : d.completion_rate >= 70 ? 'bg-amber-500/20 text-amber-300' : 'bg-red-500/20 text-red-300'}`}>
                          {d.completion_rate}%
                        </span>
                      </td>
                      <td className="p-2 text-center">{d.avg_delivery_min != null ? `${d.avg_delivery_min} د` : '—'}</td>
                      <td className="p-2 text-center">{d.avg_rating != null ? `⭐ ${d.avg_rating}` : '—'}</td>
                      <td className="p-2 text-center text-amber-400">{d.total_earnings.toFixed(0)} ر.س</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}
    </div>
  );
}
