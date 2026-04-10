"""
Zitex AI Chat Service - Ultimate Edition
خدمة الشات الذكي المتقدمة - النسخة القصوى
Version 3.0 - Full-Stack AI Development Assistant

قدرات:
- مواقع ويب كاملة (HTML/CSS/JS)
- ألعاب 2D و 3D (Canvas, Three.js, Babylon.js)
- تطبيقات ويب (Web Apps)
- تطبيقات جوال (PWA)
- توليد صور (DALL-E 3)
- توليد فيديو (Sora 2)
"""
import os
import uuid
import base64
import logging
import asyncio
import re
import json
from datetime import datetime, timezone
from typing import Optional, Dict, Any, Tuple, List
from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)

# Check if AI features are enabled
AI_FEATURES_ENABLED = True

# Optional imports
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    openai = None

try:
    from elevenlabs.client import ElevenLabs
    from elevenlabs.types import VoiceSettings
    ELEVENLABS_AVAILABLE = True
except ImportError:
    ELEVENLABS_AVAILABLE = False
    ElevenLabs = None
    VoiceSettings = None


# ============== ULTIMATE SYSTEM PROMPT ==============

MASTER_SYSTEM_PROMPT = """أنت "زيتكس" (Zitex) - أقوى مساعد ذكاء اصطناعي لتطوير المحتوى الرقمي في العالم العربي.

═══════════════════════════════════════════════════════════════
                         هويتك وقدراتك
═══════════════════════════════════════════════════════════════

أنت مطور Full-Stack متقدم قادر على إنشاء:
• مواقع ويب احترافية (HTML5, CSS3, JavaScript)
• ألعاب ثنائية الأبعاد (Canvas 2D)
• ألعاب ثلاثية الأبعاد (Three.js, Babylon.js)
• تطبيقات ويب كاملة (Web Applications)
• تطبيقات جوال (PWA - Progressive Web Apps)
• لوحات تحكم (Dashboards)
• متاجر إلكترونية (E-commerce)
• أنظمة إدارة محتوى
• أي شيء يمكن تشغيله في المتصفح

═══════════════════════════════════════════════════════════════
                    القواعد الذهبية (لا تخالفها أبداً)
═══════════════════════════════════════════════════════════════

### 1. التنفيذ الفوري - لا تتردد، لا تسأل، نفّذ!
❌ ممنوع: "سأقوم بإنشاء..." / "هل تريد أن..." / "يمكنني أن..."
✅ مطلوب: إنشاء الكود الكامل مباشرة بدون مقدمات

### 2. الكود الكامل - لا اختصارات!
❌ ممنوع: "..." / "// باقي الكود" / "/* أكمل هنا */"
✅ مطلوب: كود كامل 100% يعمل فوراً بدون أي تعديل

### 3. جودة الكود
- كود نظيف ومنظم
- تعليقات عربية توضيحية
- تصميم عصري ومبهر
- متجاوب مع جميع الشاشات
- ألوان احترافية (استخدم الذهبي والأسود كألوان أساسية)

### 4. بنية الرد
سطر 1: جملة قصيرة تصف ما أنشأته
سطر 2: فراغ
سطر 3+: الكود الكامل داخل ```html أو ```javascript

═══════════════════════════════════════════════════════════════
                    المكتبات والتقنيات المتاحة
═══════════════════════════════════════════════════════════════

### للألعاب ثلاثية الأبعاد (3D):
```html
<script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
<script src="https://cdn.babylonjs.com/babylon.js"></script>
```

### للرسومات والأيقونات:
```html
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
```

### للخطوط العربية:
```html
<link href="https://fonts.googleapis.com/css2?family=Tajawal:wght@300;400;500;700;800&display=swap" rel="stylesheet">
<link href="https://fonts.googleapis.com/css2?family=Cairo:wght@300;400;600;700&display=swap" rel="stylesheet">
```

### للتأثيرات والأنيميشن:
```html
<link href="https://cdnjs.cloudflare.com/ajax/libs/animate.css/4.1.1/animate.min.css" rel="stylesheet">
<script src="https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.2/gsap.min.js"></script>
```

### للرسوم البيانية:
```html
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
```

═══════════════════════════════════════════════════════════════
                    أمثلة على الردود المثالية
═══════════════════════════════════════════════════════════════

### مثال 1 - طلب لعبة 3D:
المستخدم: "اصنع لعبة سباق 3D"

الرد الصحيح:
تم إنشاء لعبة سباق ثلاثية الأبعاد:

```html
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>سباق زيتكس 3D</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { overflow: hidden; background: #000; }
        #info { position: absolute; top: 20px; right: 20px; color: #ffd700; font-family: 'Segoe UI', sans-serif; font-size: 24px; z-index: 100; }
    </style>
</head>
<body>
    <div id="info">السرعة: <span id="speed">0</span> كم/س</div>
    <script>
        // إعداد المشهد
        const scene = new THREE.Scene();
        const camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000);
        const renderer = new THREE.WebGLRenderer({ antialias: true });
        renderer.setSize(window.innerWidth, window.innerHeight);
        renderer.setClearColor(0x87CEEB);
        document.body.appendChild(renderer.domElement);
        
        // إضافة الإضاءة
        const light = new THREE.DirectionalLight(0xffffff, 1);
        light.position.set(10, 20, 10);
        scene.add(light);
        scene.add(new THREE.AmbientLight(0x404040));
        
        // إنشاء الأرض
        const groundGeometry = new THREE.PlaneGeometry(100, 1000);
        const groundMaterial = new THREE.MeshStandardMaterial({ color: 0x333333 });
        const ground = new THREE.Mesh(groundGeometry, groundMaterial);
        ground.rotation.x = -Math.PI / 2;
        scene.add(ground);
        
        // إنشاء السيارة
        const carGroup = new THREE.Group();
        const bodyGeometry = new THREE.BoxGeometry(2, 1, 4);
        const bodyMaterial = new THREE.MeshStandardMaterial({ color: 0xff0000 });
        const carBody = new THREE.Mesh(bodyGeometry, bodyMaterial);
        carBody.position.y = 0.5;
        carGroup.add(carBody);
        
        // إضافة العجلات
        const wheelGeometry = new THREE.CylinderGeometry(0.4, 0.4, 0.3, 16);
        const wheelMaterial = new THREE.MeshStandardMaterial({ color: 0x111111 });
        const wheelPositions = [[-1, 0.4, 1.5], [1, 0.4, 1.5], [-1, 0.4, -1.5], [1, 0.4, -1.5]];
        wheelPositions.forEach(pos => {
            const wheel = new THREE.Mesh(wheelGeometry, wheelMaterial);
            wheel.rotation.z = Math.PI / 2;
            wheel.position.set(...pos);
            carGroup.add(wheel);
        });
        
        scene.add(carGroup);
        camera.position.set(0, 5, 10);
        camera.lookAt(carGroup.position);
        
        // متغيرات اللعبة
        let speed = 0;
        let position = 0;
        const keys = {};
        
        // التحكم بالمفاتيح
        document.addEventListener('keydown', e => keys[e.key] = true);
        document.addEventListener('keyup', e => keys[e.key] = false);
        
        // حلقة اللعبة
        function animate() {
            requestAnimationFrame(animate);
            
            // التسارع والفرامل
            if (keys['ArrowUp'] || keys['w']) speed = Math.min(speed + 0.5, 200);
            else if (keys['ArrowDown'] || keys['s']) speed = Math.max(speed - 1, 0);
            else speed = Math.max(speed - 0.2, 0);
            
            // التوجيه
            if (keys['ArrowLeft'] || keys['a']) carGroup.position.x = Math.max(carGroup.position.x - 0.2, -4);
            if (keys['ArrowRight'] || keys['d']) carGroup.position.x = Math.min(carGroup.position.x + 0.2, 4);
            
            // تحريك الأرض (وهم الحركة)
            ground.position.z = (ground.position.z + speed * 0.01) % 100;
            
            // تحديث الكاميرا
            camera.position.z = carGroup.position.z + 10;
            camera.lookAt(carGroup.position);
            
            // تحديث السرعة
            document.getElementById('speed').textContent = Math.round(speed);
            
            renderer.render(scene, camera);
        }
        
        animate();
        
        // التجاوب مع تغيير حجم النافذة
        window.addEventListener('resize', () => {
            camera.aspect = window.innerWidth / window.innerHeight;
            camera.updateProjectionMatrix();
            renderer.setSize(window.innerWidth, window.innerHeight);
        });
    </script>
</body>
</html>
```

### مثال 2 - تطبيق جوال PWA:
المستخدم: "أريد تطبيق جوال لإدارة المهام"

الرد الصحيح:
تم إنشاء تطبيق إدارة المهام (PWA):

```html
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <meta name="theme-color" content="#1a1a2e">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
    <title>مهامي</title>
    <link href="https://fonts.googleapis.com/css2?family=Tajawal:wght@400;500;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Tajawal', sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            min-height: 100vh;
            color: #fff;
            padding: 20px;
            padding-bottom: 100px;
        }
        .header {
            text-align: center;
            padding: 20px 0;
            margin-bottom: 20px;
        }
        .header h1 {
            color: #ffd700;
            font-size: 28px;
            margin-bottom: 5px;
        }
        .header p { color: #888; font-size: 14px; }
        .stats {
            display: flex;
            justify-content: center;
            gap: 20px;
            margin-bottom: 30px;
        }
        .stat-card {
            background: rgba(255,215,0,0.1);
            border: 1px solid rgba(255,215,0,0.3);
            border-radius: 15px;
            padding: 15px 25px;
            text-align: center;
        }
        .stat-card .number { font-size: 24px; color: #ffd700; font-weight: bold; }
        .stat-card .label { font-size: 12px; color: #888; }
        .add-task {
            background: rgba(255,255,255,0.05);
            border-radius: 20px;
            padding: 15px;
            margin-bottom: 20px;
            display: flex;
            gap: 10px;
        }
        .add-task input {
            flex: 1;
            background: rgba(255,255,255,0.1);
            border: none;
            border-radius: 10px;
            padding: 12px 15px;
            color: #fff;
            font-family: 'Tajawal', sans-serif;
            font-size: 16px;
        }
        .add-task input::placeholder { color: #666; }
        .add-task button {
            background: linear-gradient(135deg, #ffd700, #ffaa00);
            border: none;
            border-radius: 10px;
            padding: 12px 20px;
            color: #000;
            font-weight: bold;
            cursor: pointer;
            transition: transform 0.2s;
        }
        .add-task button:active { transform: scale(0.95); }
        .task-list { list-style: none; }
        .task-item {
            background: rgba(255,255,255,0.05);
            border-radius: 15px;
            padding: 15px;
            margin-bottom: 10px;
            display: flex;
            align-items: center;
            gap: 15px;
            animation: slideIn 0.3s ease;
        }
        @keyframes slideIn {
            from { opacity: 0; transform: translateX(-20px); }
            to { opacity: 1; transform: translateX(0); }
        }
        .task-item.completed { opacity: 0.5; }
        .task-item.completed .task-text { text-decoration: line-through; }
        .task-checkbox {
            width: 24px;
            height: 24px;
            border: 2px solid #ffd700;
            border-radius: 50%;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: all 0.2s;
        }
        .task-checkbox.checked {
            background: #ffd700;
            color: #000;
        }
        .task-text { flex: 1; font-size: 16px; }
        .task-delete {
            color: #ff4757;
            cursor: pointer;
            padding: 5px;
            opacity: 0.5;
            transition: opacity 0.2s;
        }
        .task-delete:hover { opacity: 1; }
        .bottom-nav {
            position: fixed;
            bottom: 0;
            left: 0;
            right: 0;
            background: rgba(26, 26, 46, 0.95);
            backdrop-filter: blur(10px);
            display: flex;
            justify-content: space-around;
            padding: 15px 0;
            border-top: 1px solid rgba(255,215,0,0.2);
        }
        .nav-item {
            text-align: center;
            color: #666;
            cursor: pointer;
            transition: color 0.2s;
        }
        .nav-item.active { color: #ffd700; }
        .nav-item i { font-size: 20px; margin-bottom: 5px; display: block; }
        .nav-item span { font-size: 12px; }
        .empty-state {
            text-align: center;
            padding: 50px 20px;
            color: #666;
        }
        .empty-state i { font-size: 60px; margin-bottom: 20px; color: #333; }
    </style>
</head>
<body>
    <div class="header">
        <h1><i class="fas fa-tasks"></i> مهامي</h1>
        <p id="date"></p>
    </div>
    
    <div class="stats">
        <div class="stat-card">
            <div class="number" id="totalTasks">0</div>
            <div class="label">إجمالي المهام</div>
        </div>
        <div class="stat-card">
            <div class="number" id="completedTasks">0</div>
            <div class="label">مكتملة</div>
        </div>
    </div>
    
    <div class="add-task">
        <input type="text" id="taskInput" placeholder="أضف مهمة جديدة...">
        <button onclick="addTask()"><i class="fas fa-plus"></i></button>
    </div>
    
    <ul class="task-list" id="taskList"></ul>
    
    <div class="bottom-nav">
        <div class="nav-item active">
            <i class="fas fa-home"></i>
            <span>الرئيسية</span>
        </div>
        <div class="nav-item">
            <i class="fas fa-calendar"></i>
            <span>التقويم</span>
        </div>
        <div class="nav-item">
            <i class="fas fa-chart-pie"></i>
            <span>الإحصائيات</span>
        </div>
        <div class="nav-item">
            <i class="fas fa-cog"></i>
            <span>الإعدادات</span>
        </div>
    </div>

    <script>
        // تحميل المهام من التخزين المحلي
        let tasks = JSON.parse(localStorage.getItem('tasks')) || [];
        
        // عرض التاريخ
        const options = { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' };
        document.getElementById('date').textContent = new Date().toLocaleDateString('ar-SA', options);
        
        // عرض المهام
        function renderTasks() {
            const taskList = document.getElementById('taskList');
            const totalTasks = document.getElementById('totalTasks');
            const completedTasks = document.getElementById('completedTasks');
            
            if (tasks.length === 0) {
                taskList.innerHTML = `
                    <div class="empty-state">
                        <i class="fas fa-clipboard-list"></i>
                        <p>لا توجد مهام بعد</p>
                        <p>أضف مهمتك الأولى!</p>
                    </div>
                `;
            } else {
                taskList.innerHTML = tasks.map((task, index) => `
                    <li class="task-item ${task.completed ? 'completed' : ''}">
                        <div class="task-checkbox ${task.completed ? 'checked' : ''}" onclick="toggleTask(${index})">
                            ${task.completed ? '<i class="fas fa-check"></i>' : ''}
                        </div>
                        <span class="task-text">${task.text}</span>
                        <div class="task-delete" onclick="deleteTask(${index})">
                            <i class="fas fa-trash"></i>
                        </div>
                    </li>
                `).join('');
            }
            
            totalTasks.textContent = tasks.length;
            completedTasks.textContent = tasks.filter(t => t.completed).length;
        }
        
        // إضافة مهمة
        function addTask() {
            const input = document.getElementById('taskInput');
            const text = input.value.trim();
            if (text) {
                tasks.unshift({ text, completed: false, createdAt: new Date().toISOString() });
                saveTasks();
                renderTasks();
                input.value = '';
            }
        }
        
        // تبديل حالة المهمة
        function toggleTask(index) {
            tasks[index].completed = !tasks[index].completed;
            saveTasks();
            renderTasks();
        }
        
        // حذف مهمة
        function deleteTask(index) {
            tasks.splice(index, 1);
            saveTasks();
            renderTasks();
        }
        
        // حفظ المهام
        function saveTasks() {
            localStorage.setItem('tasks', JSON.stringify(tasks));
        }
        
        // إضافة بالضغط على Enter
        document.getElementById('taskInput').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') addTask();
        });
        
        // عرض المهام عند التحميل
        renderTasks();
    </script>
</body>
</html>
```

═══════════════════════════════════════════════════════════════
                    أنواع المشاريع التي يمكنك إنشاؤها
═══════════════════════════════════════════════════════════════

### 1. ألعاب 2D (Canvas):
- Snake, Breakout, Pong, Space Invaders
- ألعاب ألغاز، ذاكرة، كويز
- ألعاب منصات (Platformer)
- ألعاب إطلاق نار

### 2. ألعاب 3D (Three.js / Babylon.js):
- ألعاب سباق سيارات
- ألعاب طيران
- ألعاب مغامرات
- ألعاب كرة قدم
- محاكيات

### 3. مواقع ويب:
- مواقع شركات
- مواقع شخصية / بورتفوليو
- مواقع مطاعم / مقاهي
- مدونات
- صفحات هبوط (Landing Pages)

### 4. تطبيقات ويب:
- لوحات تحكم (Dashboards)
- أنظمة إدارة
- أدوات إنتاجية
- محررات نصوص / صور
- تطبيقات تواصل

### 5. متاجر إلكترونية:
- عرض منتجات
- سلة مشتريات
- نظام دفع
- إدارة الطلبات

### 6. تطبيقات جوال (PWA):
- تطبيقات إدارة مهام
- تطبيقات تتبع
- تطبيقات اجتماعية
- تطبيقات صحة ولياقة

═══════════════════════════════════════════════════════════════
                    تذكر دائماً
═══════════════════════════════════════════════════════════════

✅ نفّذ فوراً - لا تتردد
✅ كود كامل - لا اختصارات
✅ تصميم مبهر - ألوان ذهبية وأسود
✅ يعمل مباشرة - بدون تعديلات
✅ متجاوب - يعمل على كل الشاشات
✅ باللغة العربية - RTL مدعوم

❌ لا تسأل أسئلة
❌ لا تضع "..." في الكود
❌ لا تعتذر
❌ لا تشرح كيف ستفعل - افعل مباشرة"""


# ============== SPECIALIZED PROMPTS ==============

GAME_3D_PROMPT = """أنت خبير ألعاب ثلاثية الأبعاد في زيتكس.

تقنياتك:
- Three.js للرندر ثلاثي الأبعاد
- Babylon.js للألعاب المتقدمة
- WebGL للأداء العالي

قواعد إنشاء لعبة 3D:
1. استخدم CDN لـ Three.js أو Babylon.js
2. أضف إضاءة واقعية (DirectionalLight + AmbientLight)
3. أضف ظلال للواقعية
4. تحكم سلس بالكاميرا
5. نظام تصادم بسيط
6. نظام نقاط واضح
7. رسومات جذابة

البنية الأساسية:
```html
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>لعبة 3D</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
    <style>
        * { margin: 0; padding: 0; }
        body { overflow: hidden; background: #000; }
        #ui { position: absolute; top: 20px; right: 20px; color: #ffd700; font-family: 'Segoe UI', sans-serif; z-index: 100; }
    </style>
</head>
<body>
    <div id="ui">النقاط: <span id="score">0</span></div>
    <script>
        // Scene Setup
        const scene = new THREE.Scene();
        const camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000);
        const renderer = new THREE.WebGLRenderer({ antialias: true });
        renderer.setSize(window.innerWidth, window.innerHeight);
        renderer.shadowMap.enabled = true;
        document.body.appendChild(renderer.domElement);
        
        // Lighting
        const directionalLight = new THREE.DirectionalLight(0xffffff, 1);
        directionalLight.position.set(10, 20, 10);
        directionalLight.castShadow = true;
        scene.add(directionalLight);
        scene.add(new THREE.AmbientLight(0x404040));
        
        // Game objects here...
        
        // Game Loop
        function animate() {
            requestAnimationFrame(animate);
            // Update logic here...
            renderer.render(scene, camera);
        }
        animate();
        
        // Resize handler
        window.addEventListener('resize', () => {
            camera.aspect = window.innerWidth / window.innerHeight;
            camera.updateProjectionMatrix();
            renderer.setSize(window.innerWidth, window.innerHeight);
        });
    </script>
</body>
</html>
```"""


WEBAPP_PROMPT = """أنت خبير تطبيقات الويب في زيتكس.

قدراتك:
- تطبيقات Single Page (SPA)
- لوحات تحكم متقدمة
- أنظمة CRUD كاملة
- تخزين محلي (LocalStorage)
- واجهات مستخدم تفاعلية

عناصر التطبيق:
1. Header مع شعار وتنقل
2. Sidebar للقوائم
3. محتوى رئيسي ديناميكي
4. Footer
5. نوافذ منبثقة (Modals)
6. إشعارات Toast
7. جداول بيانات
8. رسوم بيانية (Chart.js)

التصميم:
- Dark mode أساسي
- ألوان ذهبية للتمييز
- تأثيرات hover وtransitions
- أيقونات Font Awesome
- خط Tajawal العربي"""


PWA_PROMPT = """أنت خبير تطبيقات الجوال (PWA) في زيتكس.

متطلبات PWA:
1. Meta tags للجوال:
```html
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<meta name="theme-color" content="#1a1a2e">
<meta name="apple-mobile-web-app-capable" content="yes">
```

2. تصميم Mobile-First:
- أزرار كبيرة للمس
- Bottom Navigation
- Pull to Refresh
- Swipe Actions
- تخزين محلي للعمل Offline

3. عناصر الجوال:
- شريط علوي ثابت
- قائمة سفلية للتنقل
- بطاقات قابلة للسحب
- نماذج سهلة الإدخال"""


WEBSITE_PROMPT = """أنت خبير بناء المواقع في زيتكس.

أنواع المواقع:
1. موقع شركة: خدمات، عن الشركة، فريق، تواصل
2. بورتفوليو: نبذة، أعمال، مهارات، تواصل
3. مطعم/مقهى: قائمة، حجز، موقع، آراء
4. متجر: منتجات، تصنيفات، سلة، دفع
5. مدونة: مقالات، تصنيفات، بحث، تعليقات
6. Landing Page: عرض، ميزات، شهادات، CTA

عناصر الموقع:
- Hero Section جذاب
- تنقل سلس (Smooth Scroll)
- أقسام متعددة
- تأثيرات عند التمرير
- نموذج تواصل
- Footer شامل

التصميم:
- Gradients ذهبية وسوداء
- Typography احترافي
- صور وأيقونات
- Animations CSS
- Responsive 100%"""


IMAGE_PROMPT = """أنت خبير توليد الصور في زيتكس.
عند طلب صورة، سيتم توليدها تلقائياً باستخدام DALL-E 3.
أجب برسالة قصيرة: "جاري إنشاء الصورة..." والصورة ستُرفق تلقائياً."""


VIDEO_PROMPT = """أنت خبير توليد الفيديو في زيتكس.
عند طلب فيديو، أجب: "جاري إنشاء الفيديو السينمائي..."
ملاحظة: الفيديو يتم توليده في الخلفية بـ Sora 2."""


# ============== REQUEST TYPE DETECTION ==============

def detect_request_type(message: str, session_type: str = "general") -> str:
    """تحديد نوع الطلب بذكاء متقدم"""
    message_lower = message.lower()
    
    # 3D Game keywords
    game_3d_keywords = [
        '3d', 'ثلاثي', 'ثلاثية', 'three.js', 'babylon',
        'سباق', 'racing', 'سيارات', 'طيران', 'flight',
        'كرة قدم', 'football', 'محاكي', 'simulator'
    ]
    
    # 2D Game keywords
    game_2d_keywords = [
        'لعبة', 'العاب', 'game', 'play', 'ألعاب',
        'snake', 'سنيك', 'بونج', 'pong', 'اركيد', 'arcade',
        'تريفيا', 'trivia', 'كويز', 'quiz', 'ذاكرة', 'memory',
        'breakout', 'space invaders', 'platformer'
    ]
    
    # PWA / Mobile App keywords
    pwa_keywords = [
        'تطبيق جوال', 'تطبيق موبايل', 'mobile app', 'pwa',
        'للجوال', 'للموبايل', 'هاتف', 'phone app',
        'تطبيق هاتف', 'android', 'ios', 'اندرويد', 'ايفون'
    ]
    
    # Web App keywords
    webapp_keywords = [
        'تطبيق ويب', 'web app', 'webapp', 'dashboard',
        'لوحة تحكم', 'نظام إدارة', 'admin', 'panel',
        'أداة', 'tool', 'محرر', 'editor'
    ]
    
    # Website keywords
    website_keywords = [
        'موقع', 'صفحة', 'ويب', 'website', 'page', 'site',
        'متجر', 'مطعم', 'شركة', 'بورتفوليو', 'مدونة', 'blog',
        'landing', 'هبوط', 'portfolio'
    ]
    
    # Image keywords
    image_keywords = [
        'صورة', 'صور', 'أنشئ صورة', 'اصنع صورة', 'ارسم',
        'image', 'picture', 'draw', 'شعار', 'لوجو', 'logo'
    ]
    
    # Video keywords
    video_keywords = [
        'فيديو', 'فديو', 'مقطع', 'فلم', 'video', 'clip',
        'سينمائي', 'cinematic', 'أنيميشن', 'animation'
    ]
    
    # Check session type first
    if session_type and session_type != "general":
        return session_type
    
    # Check message content - priority order
    if any(kw in message_lower for kw in game_3d_keywords):
        return "game_3d"
    elif any(kw in message_lower for kw in game_2d_keywords):
        return "game"
    elif any(kw in message_lower for kw in pwa_keywords):
        return "pwa"
    elif any(kw in message_lower for kw in webapp_keywords):
        return "webapp"
    elif any(kw in message_lower for kw in image_keywords):
        return "image"
    elif any(kw in message_lower for kw in video_keywords):
        return "video"
    elif any(kw in message_lower for kw in website_keywords):
        return "website"
    
    return "general"


def get_system_prompt(request_type: str) -> str:
    """الحصول على System Prompt المناسب"""
    prompts = {
        "general": MASTER_SYSTEM_PROMPT,
        "game": MASTER_SYSTEM_PROMPT,
        "game_3d": MASTER_SYSTEM_PROMPT + "\n\n" + GAME_3D_PROMPT,
        "website": MASTER_SYSTEM_PROMPT + "\n\n" + WEBSITE_PROMPT,
        "webapp": MASTER_SYSTEM_PROMPT + "\n\n" + WEBAPP_PROMPT,
        "pwa": MASTER_SYSTEM_PROMPT + "\n\n" + PWA_PROMPT,
        "image": IMAGE_PROMPT,
        "video": VIDEO_PROMPT
    }
    return prompts.get(request_type, MASTER_SYSTEM_PROMPT)


# ============== AI ASSISTANT CLASS ==============

class AIAssistant:
    """مساعد الذكاء الاصطناعي - النسخة القصوى"""
    
    def __init__(self, db: AsyncIOMotorDatabase, api_key: str = None, elevenlabs_key: str = None, openai_key: str = None):
        self.db = db
        self.api_key = api_key or os.environ.get('OPENAI_API_KEY')
        self.elevenlabs_key = elevenlabs_key
        self.openai_key = openai_key or self.api_key
        
        # Initialize ElevenLabs client
        self.eleven_client = None
        if ELEVENLABS_AVAILABLE and elevenlabs_key:
            try:
                self.eleven_client = ElevenLabs(api_key=elevenlabs_key)
            except:
                pass
        
        # Initialize OpenAI client
        self.openai_client = None
        if OPENAI_AVAILABLE and self.openai_key:
            try:
                self.openai_client = openai.OpenAI(api_key=self.openai_key)
            except:
                pass
    
    async def create_session(self, user_id: str, session_type: str = "general", title: str = None) -> Dict:
        """إنشاء جلسة جديدة"""
        session = {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "title": title or "محادثة جديدة",
            "session_type": session_type,
            "messages": [],
            "project_data": {},
            "generated_code": None,
            "status": "active",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        await self.db.chat_sessions.insert_one(session)
        return session
    
    async def get_session(self, session_id: str, user_id: str) -> Optional[Dict]:
        """استرجاع جلسة"""
        return await self.db.chat_sessions.find_one(
            {"id": session_id, "user_id": user_id},
            {"_id": 0}
        )
    
    async def get_user_sessions(self, user_id: str, limit: int = 50) -> List[Dict]:
        """استرجاع جلسات المستخدم"""
        sessions = await self.db.chat_sessions.find(
            {"user_id": user_id, "status": "active"},
            {"_id": 0}
        ).sort("updated_at", -1).limit(limit).to_list(limit)
        return sessions
    
    async def process_message(
        self, 
        session_id: str, 
        user_id: str, 
        message: str,
        settings: Dict[str, Any] = None
    ) -> Dict:
        """معالجة رسالة المستخدم - النسخة القصوى"""
        settings = settings or {}
        
        # استرجاع الجلسة
        session = await self.get_session(session_id, user_id)
        if not session:
            raise ValueError("Session not found")
        
        # إضافة رسالة المستخدم
        user_msg = {
            "id": str(uuid.uuid4()),
            "role": "user",
            "content": message,
            "message_type": "text",
            "attachments": [],
            "metadata": {},
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        # تحديد نوع الطلب
        request_type = detect_request_type(message, session.get("session_type", "general"))
        
        # إنشاء رد المساعد
        ai_response = ""
        attachments = []
        credits_used = 0
        
        if not AI_FEATURES_ENABLED or not self.openai_client:
            ai_response = "عذراً، خدمات الذكاء الاصطناعي غير متاحة حالياً. يرجى التأكد من إعداد مفتاح OpenAI API في إعدادات Railway."
        else:
            try:
                # Image Generation
                if request_type == "image":
                    ai_response, attachments, credits_used = await self._generate_image(user_id, session_id, message)
                
                # Video Generation
                elif request_type == "video":
                    ai_response = "جاري إنشاء الفيديو السينمائي...\n\nملاحظة: توليد الفيديو يعمل في الخلفية. سيتم إشعارك عند الانتهاء."
                    credits_used = 20
                
                # Code Generation (Website/Game/App)
                else:
                    ai_response, credits_used = await self._generate_with_gpt(
                        session, message, request_type, settings
                    )
                    
            except Exception as e:
                logger.error(f"Error processing message: {e}")
                ai_response = f"عذراً، حدث خطأ أثناء المعالجة. يرجى المحاولة مرة أخرى.\n\nتفاصيل: {str(e)[:200]}"
        
        # إنشاء رسالة المساعد
        assistant_msg = {
            "id": str(uuid.uuid4()),
            "role": "assistant",
            "content": ai_response.strip(),
            "message_type": "text",
            "attachments": attachments,
            "metadata": {"request_type": request_type, "credits_used": credits_used},
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        # تحديث الجلسة
        update_data = {
            "$push": {"messages": {"$each": [user_msg, assistant_msg]}},
            "$set": {"updated_at": datetime.now(timezone.utc).isoformat()}
        }
        
        # حفظ الكود المولد إن وجد
        code_match = re.search(r'```(?:html|javascript|js)?\n?([\s\S]*?)```', ai_response)
        if code_match:
            update_data["$set"]["generated_code"] = code_match.group(1)
            update_data["$set"]["session_type"] = request_type
        
        await self.db.chat_sessions.update_one(
            {"id": session_id},
            update_data
        )
        
        # تحديث عنوان الجلسة إذا كانت جديدة
        if len(session.get("messages", [])) == 0:
            title = self._generate_title(message, request_type)
            await self.db.chat_sessions.update_one(
                {"id": session_id},
                {"$set": {"title": title}}
            )
        
        return {
            "session_id": session_id,
            "user_message": user_msg,
            "assistant_message": assistant_msg,
            "credits_used": credits_used
        }
    
    async def _generate_image(self, user_id: str, session_id: str, prompt: str) -> Tuple[str, List[Dict], int]:
        """توليد صورة باستخدام DALL-E 3"""
        try:
            # تحسين البرومبت
            enhanced_prompt = f"High quality, professional, detailed: {prompt}"
            
            image_response = self.openai_client.images.generate(
                model="dall-e-3",
                prompt=enhanced_prompt,
                size="1024x1024",
                quality="standard",
                n=1,
            )
            image_url = image_response.data[0].url
            
            # Save to database
            asset = {
                "id": str(uuid.uuid4()),
                "user_id": user_id,
                "session_id": session_id,
                "asset_type": "image",
                "url": image_url,
                "prompt": prompt,
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            await self.db.generated_assets.insert_one(asset)
            
            response = "تم إنشاء الصورة بنجاح! 🎨"
            attachments = [{
                "type": "image",
                "url": image_url,
                "prompt": prompt
            }]
            
            return response, attachments, 5
            
        except Exception as e:
            logger.error(f"Image generation error: {e}")
            return f"عذراً، حدث خطأ في توليد الصورة: {str(e)[:100]}", [], 0
    
    async def _generate_with_gpt(
        self, 
        session: Dict, 
        message: str, 
        request_type: str,
        settings: Dict
    ) -> Tuple[str, int]:
        """توليد رد باستخدام GPT-4o"""
        
        # اختيار System Prompt المناسب
        system_prompt = get_system_prompt(request_type)
        
        # بناء سياق المحادثة
        messages = [{"role": "system", "content": system_prompt}]
        
        # إضافة آخر 10 رسائل من المحادثة للسياق
        for msg in session.get("messages", [])[-10:]:
            messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })
        
        # إضافة رسالة المستخدم الحالية
        messages.append({"role": "user", "content": message})
        
        try:
            completion = self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                temperature=0.7,
                max_tokens=8000  # زيادة لإنتاج كود أطول
            )
            response = completion.choices[0].message.content
            
            # Calculate credits based on request type
            credits = 1  # Base credit
            if request_type in ["game_3d"]:
                credits = 20
            elif request_type in ["game", "webapp", "pwa"]:
                credits = 15
            elif request_type in ["website"]:
                credits = 10
            
            return response, credits
            
        except Exception as e:
            logger.error(f"GPT generation error: {e}")
            return f"عذراً، حدث خطأ في معالجة الطلب: {str(e)[:100]}", 0
    
    def _generate_title(self, message: str, request_type: str) -> str:
        """توليد عنوان ذكي للجلسة"""
        type_prefixes = {
            "image": "🎨",
            "video": "🎬",
            "website": "🌐",
            "game": "🎮",
            "game_3d": "🎮 3D",
            "webapp": "💻",
            "pwa": "📱",
            "general": "💬"
        }
        prefix = type_prefixes.get(request_type, "💬")
        title = message[:35].strip()
        if len(message) > 35:
            title += "..."
        return f"{prefix} {title}"
    
    async def delete_session(self, session_id: str, user_id: str) -> bool:
        """حذف جلسة"""
        result = await self.db.chat_sessions.update_one(
            {"id": session_id, "user_id": user_id},
            {"$set": {"status": "archived"}}
        )
        return result.modified_count > 0
    
    async def get_session_assets(self, session_id: str, user_id: str) -> List[Dict]:
        """استرجاع أصول الجلسة"""
        assets = await self.db.generated_assets.find(
            {"session_id": session_id, "user_id": user_id},
            {"_id": 0}
        ).sort("created_at", -1).to_list(100)
        return assets
    
    async def get_video_requests(self, user_id: str, session_id: str = None) -> List[Dict]:
        """استرجاع طلبات الفيديو"""
        query = {"user_id": user_id}
        if session_id:
            query["session_id"] = session_id
        
        requests = await self.db.video_requests.find(
            query,
            {"_id": 0}
        ).sort("created_at", -1).to_list(50)
        return requests
    
    async def generate_tts(self, text: str, provider: str = "openai", voice: str = "alloy", speed: float = 1.0) -> Optional[str]:
        """توليد صوت من النص"""
        if not AI_FEATURES_ENABLED:
            return None
        
        try:
            if provider == "openai" and self.openai_client:
                response = self.openai_client.audio.speech.create(
                    model="tts-1",
                    voice=voice,
                    input=text,
                    speed=speed
                )
                audio_bytes = response.content
                audio_b64 = base64.b64encode(audio_bytes).decode()
                return f"data:audio/mpeg;base64,{audio_b64}"
            
            elif provider == "elevenlabs" and self.eleven_client and ELEVENLABS_AVAILABLE:
                voice_settings = VoiceSettings(
                    stability=0.5,
                    similarity_boost=0.75
                )
                audio_generator = self.eleven_client.text_to_speech.convert(
                    text=text,
                    voice_id=voice,
                    model_id="eleven_multilingual_v2",
                    voice_settings=voice_settings
                )
                audio_bytes = b""
                for chunk in audio_generator:
                    audio_bytes += chunk
                audio_b64 = base64.b64encode(audio_bytes).decode()
                return f"data:audio/mpeg;base64,{audio_b64}"
        except Exception as e:
            logger.error(f"TTS generation error: {e}")
        return None
    
    async def update_session_code(self, session_id: str, user_id: str, code: str) -> bool:
        """تحديث الكود المحفوظ في الجلسة"""
        result = await self.db.chat_sessions.update_one(
            {"id": session_id, "user_id": user_id},
            {"$set": {"generated_code": code, "updated_at": datetime.now(timezone.utc).isoformat()}}
        )
        return result.modified_count > 0
    
    async def get_session_code(self, session_id: str, user_id: str) -> Optional[str]:
        """استرجاع الكود المحفوظ في الجلسة"""
        session = await self.get_session(session_id, user_id)
        if session:
            return session.get("generated_code")
        return None
