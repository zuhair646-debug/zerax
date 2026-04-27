"""Dashboard renderer — admin/customer panel section + _dash_panel item builders."""
from typing import Dict, Any
from .renderer_helpers import _esc


# ---- Dashboard (admin / customer panel) ----
_DASH_ICONS = {
    "orders": "📦", "customers": "👥", "products": "🏷️", "analytics": "📊",
    "messages": "💬", "reports": "📈", "users": "🔐", "settings": "⚙️",
    "phone": "📞", "email": "📧", "notifications": "🔔", "calendar": "📅",
    "inventory": "📋", "payments": "💳", "reviews": "⭐",
}
_DASH_LABELS = {
    "orders": "الطلبات", "customers": "العملاء", "products": "المنتجات", "analytics": "الإحصائيات",
    "messages": "الرسائل", "reports": "التقارير", "users": "المستخدمون", "settings": "الإعدادات",
    "phone": "رقم الجوال", "email": "البريد الإلكتروني", "notifications": "الإشعارات", "calendar": "التقويم",
    "inventory": "المخزون", "payments": "المدفوعات", "reviews": "التقييمات",
}


def _dash_panel(item_id: str) -> str:
    """Rich panel HTML for each dashboard item — looks like a real admin interface."""
    panels = {
        "products": """<div class="dp-head"><h3>🏷️ إدارة المنتجات</h3><button class="dp-btn">+ إضافة منتج</button></div>
<div class="dp-form">
  <div class="dp-row"><label>اسم المنتج</label><input placeholder="مثال: بيتزا كلاسيك"/></div>
  <div class="dp-row-2">
    <div><label>السعر</label><input placeholder="45"/></div>
    <div><label>الفئة</label><select><option>وجبات</option><option>مشروبات</option></select></div>
  </div>
  <div class="dp-row"><label>الصورة</label><div class="dp-upload">📷 اسحب صورة هنا أو اضغط للرفع</div></div>
  <button class="dp-btn-primary">💾 حفظ المنتج</button>
</div>
<table class="dp-table"><thead><tr><th>المنتج</th><th>السعر</th><th>المخزون</th><th>الإجراء</th></tr></thead>
<tbody>
<tr><td>🍕 بيتزا كلاسيك</td><td>45 ر.س</td><td><span class="dp-badge-ok">متوفر</span></td><td>✏️ 🗑️</td></tr>
<tr><td>🍔 برجر دبل</td><td>38 ر.س</td><td><span class="dp-badge-ok">متوفر</span></td><td>✏️ 🗑️</td></tr>
<tr><td>🌮 تاكو خاص</td><td>28 ر.س</td><td><span class="dp-badge-warn">قليل</span></td><td>✏️ 🗑️</td></tr>
</tbody></table>""",

        "orders": """<div class="dp-head"><h3>📦 الطلبات الحديثة</h3><div class="dp-filters"><button class="dp-chip dp-chip-on">الكل</button><button class="dp-chip">جديد</button><button class="dp-chip">قيد التحضير</button><button class="dp-chip">مكتمل</button></div></div>
<table class="dp-table"><thead><tr><th>رقم الطلب</th><th>العميل</th><th>المبلغ</th><th>الحالة</th><th>الإجراء</th></tr></thead>
<tbody>
<tr><td>#1247</td><td>أحمد محمد</td><td>128 ر.س</td><td><span class="dp-badge-info">جديد</span></td><td>👁️ ✓</td></tr>
<tr><td>#1246</td><td>سارة عبدالله</td><td>85 ر.س</td><td><span class="dp-badge-warn">قيد التحضير</span></td><td>👁️ ✓</td></tr>
<tr><td>#1245</td><td>خالد الفهد</td><td>210 ر.س</td><td><span class="dp-badge-ok">مكتمل</span></td><td>👁️</td></tr>
<tr><td>#1244</td><td>نورة السالم</td><td>65 ر.س</td><td><span class="dp-badge-ok">مكتمل</span></td><td>👁️</td></tr>
</tbody></table>""",

        "customers": """<div class="dp-head"><h3>👥 العملاء</h3><div class="dp-search"><input placeholder="🔍 ابحث عن عميل..."/></div></div>
<div class="dp-stats-inline">
  <div class="dp-mini"><div class="dp-mini-val">248</div><div class="dp-mini-lbl">إجمالي</div></div>
  <div class="dp-mini"><div class="dp-mini-val">+12</div><div class="dp-mini-lbl">جدد اليوم</div></div>
  <div class="dp-mini"><div class="dp-mini-val">89%</div><div class="dp-mini-lbl">نشطون</div></div>
</div>
<table class="dp-table"><thead><tr><th>الاسم</th><th>الجوال</th><th>الطلبات</th><th>الإنفاق</th></tr></thead>
<tbody>
<tr><td>👤 أحمد محمد</td><td>0501234567</td><td>12</td><td>1,450 ر.س</td></tr>
<tr><td>👤 سارة عبدالله</td><td>0551234567</td><td>8</td><td>890 ر.س</td></tr>
<tr><td>👤 خالد الفهد</td><td>0541234567</td><td>23</td><td>3,200 ر.س</td></tr>
</tbody></table>""",

        "analytics": """<div class="dp-head"><h3>📊 الإحصائيات</h3><select class="dp-select"><option>آخر 7 أيام</option><option>آخر 30 يوم</option><option>آخر سنة</option></select></div>
<div class="dp-stats-grid">
  <div class="dp-stat"><div class="dp-stat-ico">💰</div><div class="dp-stat-val">24,850</div><div class="dp-stat-lbl">الإيرادات (ر.س)</div><div class="dp-stat-trend up">▲ 18%</div></div>
  <div class="dp-stat"><div class="dp-stat-ico">📦</div><div class="dp-stat-val">1,247</div><div class="dp-stat-lbl">طلبات</div><div class="dp-stat-trend up">▲ 12%</div></div>
  <div class="dp-stat"><div class="dp-stat-ico">👥</div><div class="dp-stat-val">+248</div><div class="dp-stat-lbl">عملاء جدد</div><div class="dp-stat-trend up">▲ 8%</div></div>
  <div class="dp-stat"><div class="dp-stat-ico">⭐</div><div class="dp-stat-val">4.8</div><div class="dp-stat-lbl">تقييم</div><div class="dp-stat-trend">●</div></div>
</div>
<div class="dp-chart">
  <div class="dp-chart-title">المبيعات الأسبوعية</div>
  <div class="dp-bars">""" + "".join(f'<div class="dp-bar" style="height:{h}%"></div>' for h in [45, 60, 35, 80, 55, 90, 75]) + """</div>
  <div class="dp-bars-lbl"><span>س</span><span>ح</span><span>ن</span><span>ث</span><span>ر</span><span>خ</span><span>ج</span></div>
</div>""",

        "reviews": """<div class="dp-head"><h3>⭐ التقييمات والآراء</h3><div class="dp-stats-inline">
  <div class="dp-mini"><div class="dp-mini-val">4.8</div><div class="dp-mini-lbl">متوسط</div></div>
  <div class="dp-mini"><div class="dp-mini-val">127</div><div class="dp-mini-lbl">مراجعة</div></div>
</div></div>
<div class="dp-review-list">
  <div class="dp-review"><div class="dp-rev-head"><b>أحمد محمد</b><span>★★★★★</span></div><p>"خدمة ممتازة وطعام لذيذ — سأعود قريباً"</p><div class="dp-rev-actions"><button class="dp-chip">رد</button><button class="dp-chip">عرض في الموقع</button></div></div>
  <div class="dp-review"><div class="dp-rev-head"><b>سارة عبدالله</b><span>★★★★☆</span></div><p>"جيد لكن التوصيل تأخر قليلاً"</p><div class="dp-rev-actions"><button class="dp-chip">رد</button><button class="dp-chip">عرض</button></div></div>
  <div class="dp-review"><div class="dp-rev-head"><b>خالد الفهد</b><span>★★★★★</span></div><p>"الأسعار مناسبة والطعام ممتاز"</p><div class="dp-rev-actions"><button class="dp-chip">رد</button></div></div>
</div>""",

        "messages": """<div class="dp-head"><h3>💬 الرسائل الواردة</h3><span class="dp-badge-info">3 جديدة</span></div>
<div class="dp-msg-list">
  <div class="dp-msg dp-msg-new"><div class="dp-msg-head"><b>أحمد محمد</b><span>منذ 5 د</span></div><p>هل تتوفر الدفعات الشهرية؟</p></div>
  <div class="dp-msg dp-msg-new"><div class="dp-msg-head"><b>سارة عبدالله</b><span>منذ 20 د</span></div><p>أبغى أعدّل طلبي رقم #1246</p></div>
  <div class="dp-msg"><div class="dp-msg-head"><b>خالد الفهد</b><span>أمس</span></div><p>شكراً على الخدمة الممتازة!</p></div>
</div>
<div class="dp-reply-box"><input placeholder="✍️ اكتب ردّك..."/><button class="dp-btn-primary">إرسال</button></div>""",

        "reports": """<div class="dp-head"><h3>📈 التقارير المالية</h3><button class="dp-btn">📥 تصدير PDF</button></div>
<table class="dp-table"><thead><tr><th>التقرير</th><th>التاريخ</th><th>القيمة</th><th>العملية</th></tr></thead>
<tbody>
<tr><td>📊 تقرير المبيعات الشهري</td><td>أكتوبر 2025</td><td>124,500 ر.س</td><td>📥 ⬇️</td></tr>
<tr><td>📊 تقرير المنتجات الأكثر مبيعاً</td><td>أكتوبر 2025</td><td>—</td><td>📥 ⬇️</td></tr>
<tr><td>📊 تقرير العملاء الجدد</td><td>أكتوبر 2025</td><td>+248</td><td>📥 ⬇️</td></tr>
</tbody></table>""",

        "users": """<div class="dp-head"><h3>🔐 المستخدمون والأدوار</h3><button class="dp-btn">+ إضافة مستخدم</button></div>
<table class="dp-table"><thead><tr><th>المستخدم</th><th>البريد</th><th>الدور</th><th>الإجراء</th></tr></thead>
<tbody>
<tr><td>محمد المالك</td><td>owner@site.com</td><td><span class="dp-badge-info">مدير</span></td><td>✏️</td></tr>
<tr><td>سارة الموظف</td><td>sara@site.com</td><td><span class="dp-badge-ok">موظف</span></td><td>✏️ 🗑️</td></tr>
<tr><td>أحمد الكاشير</td><td>cashier@site.com</td><td><span class="dp-badge-ok">كاشير</span></td><td>✏️ 🗑️</td></tr>
</tbody></table>""",

        "settings": """<div class="dp-head"><h3>⚙️ إعدادات الموقع</h3></div>
<div class="dp-form">
  <div class="dp-row"><label>اسم الموقع</label><input placeholder="موقعي"/></div>
  <div class="dp-row"><label>الوصف التعريفي</label><input placeholder="متجر إلكتروني احترافي"/></div>
  <div class="dp-row-2"><div><label>اللغة</label><select><option>العربية</option><option>English</option></select></div><div><label>العملة</label><select><option>ر.س</option><option>د.إ</option><option>USD</option></select></div></div>
  <div class="dp-row"><label>المنطقة الزمنية</label><select><option>Asia/Riyadh</option></select></div>
  <button class="dp-btn-primary">💾 حفظ الإعدادات</button>
</div>""",

        "calendar": """<div class="dp-head"><h3>📅 التقويم والحجوزات</h3><button class="dp-btn">+ إضافة موعد</button></div>
<div class="dp-cal">
  <div class="dp-cal-row"><span class="dp-cal-date">اليوم · 14:00</span><span class="dp-cal-title">حجز طاولة — سارة</span><span class="dp-badge-info">قادم</span></div>
  <div class="dp-cal-row"><span class="dp-cal-date">اليوم · 18:30</span><span class="dp-cal-title">حجز جلسة — أحمد</span><span class="dp-badge-info">قادم</span></div>
  <div class="dp-cal-row"><span class="dp-cal-date">الغد · 10:00</span><span class="dp-cal-title">اجتماع فريق</span><span class="dp-badge-warn">معلّق</span></div>
  <div class="dp-cal-row"><span class="dp-cal-date">الغد · 19:00</span><span class="dp-cal-title">حجز خالد</span><span class="dp-badge-ok">مؤكد</span></div>
</div>""",

        "inventory": """<div class="dp-head"><h3>📋 إدارة المخزون</h3><button class="dp-btn">🔄 تحديث</button></div>
<div class="dp-stats-inline">
  <div class="dp-mini"><div class="dp-mini-val">1,247</div><div class="dp-mini-lbl">كل المنتجات</div></div>
  <div class="dp-mini"><div class="dp-mini-val" style="color:#ef4444">23</div><div class="dp-mini-lbl">منخفض</div></div>
  <div class="dp-mini"><div class="dp-mini-val" style="color:#f59e0b">5</div><div class="dp-mini-lbl">نفد</div></div>
</div>
<table class="dp-table"><thead><tr><th>المنتج</th><th>المتوفر</th><th>الحد الأدنى</th><th>الحالة</th></tr></thead>
<tbody>
<tr><td>🍕 بيتزا</td><td>85</td><td>20</td><td><span class="dp-badge-ok">جيد</span></td></tr>
<tr><td>🍔 برجر</td><td>18</td><td>20</td><td><span class="dp-badge-warn">منخفض</span></td></tr>
<tr><td>🥤 كولا</td><td>0</td><td>50</td><td><span class="dp-badge-err">نفد</span></td></tr>
</tbody></table>""",

        "payments": """<div class="dp-head"><h3>💳 المدفوعات والفواتير</h3></div>
<div class="dp-stats-grid">
  <div class="dp-stat"><div class="dp-stat-ico">💰</div><div class="dp-stat-val">128,450</div><div class="dp-stat-lbl">إجمالي (ر.س)</div></div>
  <div class="dp-stat"><div class="dp-stat-ico">⏳</div><div class="dp-stat-val">4,200</div><div class="dp-stat-lbl">معلّق</div></div>
  <div class="dp-stat"><div class="dp-stat-ico">🔄</div><div class="dp-stat-val">890</div><div class="dp-stat-lbl">مسترجع</div></div>
</div>
<table class="dp-table"><thead><tr><th>رقم</th><th>العميل</th><th>الطريقة</th><th>المبلغ</th><th>الحالة</th></tr></thead>
<tbody>
<tr><td>TXN-8821</td><td>أحمد</td><td>💳 Visa</td><td>128 ر.س</td><td><span class="dp-badge-ok">مكتمل</span></td></tr>
<tr><td>TXN-8820</td><td>سارة</td><td>🏦 مدى</td><td>85 ر.س</td><td><span class="dp-badge-ok">مكتمل</span></td></tr>
<tr><td>TXN-8819</td><td>خالد</td><td>💵 كاش</td><td>210 ر.س</td><td><span class="dp-badge-warn">معلّق</span></td></tr>
</tbody></table>""",

        "phone": """<div class="dp-head"><h3>📞 إعدادات رقم الجوال</h3></div>
<div class="dp-form">
  <div class="dp-row"><label>رقم الجوال الرئيسي</label><input placeholder="+966 5x xxx xxxx" type="tel"/></div>
  <div class="dp-row"><label>واتساب</label><input placeholder="+966 5x xxx xxxx" type="tel"/></div>
  <div class="dp-row-2">
    <div><label>الرسائل القصيرة</label><select><option>مفعّل</option><option>معطّل</option></select></div>
    <div><label>استقبال مكالمات</label><select><option>دائماً</option><option>ساعات العمل</option></select></div>
  </div>
  <button class="dp-btn-primary">💾 حفظ</button>
</div>""",

        "email": """<div class="dp-head"><h3>📧 إعدادات البريد</h3></div>
<div class="dp-form">
  <div class="dp-row"><label>البريد الرسمي</label><input placeholder="info@yoursite.com" type="email"/></div>
  <div class="dp-row"><label>بريد الدعم</label><input placeholder="support@yoursite.com" type="email"/></div>
  <div class="dp-row"><label>إشعارات الطلبات</label><select><option>مفعّل</option><option>معطّل</option></select></div>
  <button class="dp-btn-primary">💾 حفظ</button>
</div>""",

        "notifications": """<div class="dp-head"><h3>🔔 الإشعارات</h3></div>
<div class="dp-notif-list">
  <div class="dp-notif">🆕 طلب جديد #1247 من أحمد — منذ دقيقتين</div>
  <div class="dp-notif">⭐ تقييم 5 نجوم جديد من سارة — منذ 5 دقائق</div>
  <div class="dp-notif">💰 دفعة مستلمة: 128 ر.س — منذ 10 دقائق</div>
  <div class="dp-notif">⚠️ المخزون منخفض: برجر دبل — منذ ساعة</div>
</div>""",
    }
    return f'<div class="dp-panel" id="panel-{item_id}">{panels.get(item_id, f"<h3>{_DASH_ICONS.get(item_id,chr(128123))} {_DASH_LABELS.get(item_id,item_id)}</h3><p class=dp-empty>لوحة فرعية قيد التطوير</p>")}</div>'


def _section_dashboard(d, theme) -> str:
    layout = d.get("layout", "cards")
    items = d.get("items", []) or []
    title = _esc(d.get("title", "لوحة التحكم"))

    empty_msg = '<div class="dp-hint">⬅ ارجع للشات وفعّل العناصر — كل عنصر سيظهر هنا لايف!</div>'

    panels = "\n".join(_dash_panel(i) for i in items) if items else empty_msg

    if layout == "sidebar":
        nav = "".join(
            f'<a href="#panel-{i}" class="dp-nav-item"><span class="dp-nav-ico">{_DASH_ICONS.get(i,"🔷")}</span><span>{_esc(_DASH_LABELS.get(i,i))}</span></a>'
            for i in items
        ) or '<div class="dp-empty">لا عناصر بعد</div>'
        return f"""<section class="dashboard dp-mode"><div class="dp-topbar"><div class="dp-topbar-brand">⚡ {title}</div><div class="dp-topbar-user">👤 المدير</div></div>
<div class="dp-layout">
  <aside class="dp-side"><div class="dp-side-title">القائمة</div>{nav}</aside>
  <main class="dp-main">{panels}</main>
</div></section>"""

    if layout == "tabs":
        tabs = "".join(
            f'<a href="#panel-{i}" class="dp-tab {"dp-tab-on" if idx==0 else ""}">{_DASH_ICONS.get(i,"🔷")} {_esc(_DASH_LABELS.get(i,i))}</a>'
            for idx, i in enumerate(items)
        ) or '<div class="dp-empty">لا تبويبات بعد</div>'
        return f"""<section class="dashboard dp-mode"><div class="dp-topbar"><div class="dp-topbar-brand">⚡ {title}</div><div class="dp-topbar-user">👤 المدير</div></div>
<div class="dp-tabsbar">{tabs}</div>
<div class="dp-main">{panels}</div></section>"""

    # cards (grid of panels)
    return f"""<section class="dashboard dp-mode"><div class="dp-topbar"><div class="dp-topbar-brand">⚡ {title}</div><div class="dp-topbar-user">👤 المدير</div></div>
<div class="dp-cards-grid">{panels}</div></section>"""


