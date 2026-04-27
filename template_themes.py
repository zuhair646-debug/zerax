"""
Zitex Deployment Service
خدمة نشر المواقع والتطبيقات
"""
import os
import uuid
import json
import zipfile
import base64
import shutil
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

# Templates for different project types
REACT_TEMPLATE = {
    "package.json": '''{
  "name": "{project_name}",
  "version": "1.0.0",
  "private": true,
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-scripts": "5.0.1"
  },
  "scripts": {
    "start": "react-scripts start",
    "build": "react-scripts build",
    "test": "react-scripts test",
    "eject": "react-scripts eject"
  },
  "browserslist": {
    "production": [">0.2%", "not dead", "not op_mini all"],
    "development": ["last 1 chrome version", "last 1 firefox version", "last 1 safari version"]
  }
}''',
    "public/index.html": '''<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <meta name="theme-color" content="#000000" />
  <meta name="description" content="{description}" />
  <title>{title}</title>
  <script src="https://cdn.tailwindcss.com"></script>
</head>
<body>
  <noscript>You need to enable JavaScript to run this app.</noscript>
  <div id="root"></div>
</body>
</html>''',
    "src/index.js": '''import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);''',
    "README.md": '''# {title}

{description}

## التشغيل المحلي

```bash
npm install
npm start
```

## البناء للنشر

```bash
npm run build
```

## النشر على Vercel

1. ارفع المجلد على GitHub
2. اذهب إلى vercel.com
3. اربط المستودع
4. انشر!

---
تم إنشاؤه بواسطة Zitex AI
'''
}

HTML_TEMPLATE = {
    "index.html": '''<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title}</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <style>
    body {{ font-family: 'Segoe UI', Tahoma, sans-serif; }}
  </style>
</head>
<body class="bg-gray-100">
{content}
</body>
</html>''',
    "README.md": '''# {title}

{description}

## النشر

يمكنك رفع هذا الملف مباشرة على:
- Netlify (netlify.com)
- GitHub Pages
- أي استضافة ويب

---
تم إنشاؤه بواسطة Zitex AI
'''
}


class DeploymentService:
    """خدمة نشر المشاريع"""
    
    def __init__(self, db, storage_path: str = "/tmp/zitex_projects"):
        self.db = db
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
    
    async def create_project_package(
        self,
        user_id: str,
        session_id: str,
        project_name: str,
        project_type: str,  # react, html, nextjs
        files: Dict[str, str],
        metadata: Dict[str, Any] = None
    ) -> Dict:
        """إنشاء حزمة مشروع قابلة للتحميل"""
        
        project_id = str(uuid.uuid4())
        project_dir = self.storage_path / project_id
        project_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            # تحديد القالب
            if project_type == "react":
                template = REACT_TEMPLATE.copy()
            else:
                template = HTML_TEMPLATE.copy()
            
            # استبدال المتغيرات في القالب
            title = metadata.get("title", project_name) if metadata else project_name
            description = metadata.get("description", "موقع تم إنشاؤه بواسطة Zitex AI") if metadata else ""
            
            # كتابة ملفات القالب
            for filename, content in template.items():
                file_path = project_dir / filename
                file_path.parent.mkdir(parents=True, exist_ok=True)
                
                formatted_content = content.format(
                    project_name=project_name.lower().replace(" ", "-"),
                    title=title,
                    description=description,
                    content=""
                )
                file_path.write_text(formatted_content, encoding="utf-8")
            
            # كتابة ملفات المشروع المُنشأة
            for filename, content in files.items():
                if project_type == "react":
                    file_path = project_dir / "src" / filename
                else:
                    file_path = project_dir / filename
                
                file_path.parent.mkdir(parents=True, exist_ok=True)
                file_path.write_text(content, encoding="utf-8")
            
            # إنشاء ملف ZIP
            zip_filename = f"{project_name.lower().replace(' ', '-')}-{project_id[:8]}.zip"
            zip_path = self.storage_path / zip_filename
            
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for file_path in project_dir.rglob('*'):
                    if file_path.is_file():
                        arcname = file_path.relative_to(project_dir)
                        zipf.write(file_path, arcname)
            
            # قراءة ZIP كـ base64
            with open(zip_path, 'rb') as f:
                zip_base64 = base64.b64encode(f.read()).decode()
            
            # حفظ في قاعدة البيانات
            project_record = {
                "id": project_id,
                "user_id": user_id,
                "session_id": session_id,
                "name": project_name,
                "type": project_type,
                "files": list(files.keys()),
                "zip_filename": zip_filename,
                "status": "ready",
                "deployment_url": None,
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            await self.db.projects.insert_one(project_record)
            
            # تنظيف
            shutil.rmtree(project_dir)
            
            return {
                "id": project_id,
                "name": project_name,
                "type": project_type,
                "zip_base64": zip_base64,
                "zip_filename": zip_filename,
                "files_count": len(files),
                "status": "ready",
                "instructions": self._get_deployment_instructions(project_type)
            }
            
        except Exception as e:
            logger.error(f"Error creating project package: {e}")
            if project_dir.exists():
                shutil.rmtree(project_dir)
            raise
    
    def _get_deployment_instructions(self, project_type: str) -> Dict:
        """الحصول على تعليمات النشر"""
        
        if project_type == "react":
            return {
                "vercel": {
                    "title": "النشر على Vercel (مجاني)",
                    "steps": [
                        "1. فك ضغط الملف",
                        "2. ارفع المجلد على GitHub",
                        "3. اذهب إلى vercel.com وسجل دخول",
                        "4. اضغط 'New Project'",
                        "5. اربط مستودع GitHub",
                        "6. اضغط 'Deploy'",
                        "✅ موقعك جاهز على رابط .vercel.app"
                    ],
                    "url": "https://vercel.com/new"
                },
                "netlify": {
                    "title": "النشر على Netlify (مجاني)",
                    "steps": [
                        "1. فك ضغط الملف",
                        "2. شغّل: npm install && npm run build",
                        "3. اذهب إلى netlify.com",
                        "4. اسحب مجلد 'build' إلى الصفحة",
                        "✅ موقعك جاهز!"
                    ],
                    "url": "https://app.netlify.com/drop"
                }
            }
        else:
            return {
                "netlify": {
                    "title": "النشر على Netlify (مجاني)",
                    "steps": [
                        "1. فك ضغط الملف",
                        "2. اذهب إلى app.netlify.com/drop",
                        "3. اسحب المجلد إلى الصفحة",
                        "✅ موقعك جاهز!"
                    ],
                    "url": "https://app.netlify.com/drop"
                },
                "github_pages": {
                    "title": "النشر على GitHub Pages (مجاني)",
                    "steps": [
                        "1. أنشئ مستودع جديد على GitHub",
                        "2. ارفع الملفات",
                        "3. اذهب إلى Settings > Pages",
                        "4. اختر main branch",
                        "✅ موقعك على username.github.io/repo"
                    ],
                    "url": "https://github.com/new"
                }
            }
    
    async def get_user_projects(self, user_id: str, limit: int = 20) -> List[Dict]:
        """استرجاع مشاريع المستخدم"""
        projects = await self.db.projects.find(
            {"user_id": user_id},
            {"_id": 0, "zip_base64": 0}
        ).sort("created_at", -1).limit(limit).to_list(limit)
        return projects
    
    async def get_project(self, project_id: str, user_id: str) -> Optional[Dict]:
        """استرجاع مشروع محدد"""
        return await self.db.projects.find_one(
            {"id": project_id, "user_id": user_id},
            {"_id": 0}
        )
    
    async def regenerate_zip(self, project_id: str, user_id: str) -> Optional[str]:
        """إعادة إنشاء ملف ZIP للمشروع"""
        project = await self.get_project(project_id, user_id)
        if not project:
            return None
        
        # استرجاع الملفات من الجلسة
        session = await self.db.chat_sessions.find_one(
            {"id": project.get("session_id"), "user_id": user_id}
        )
        
        if not session:
            return None
        
        # البحث عن آخر موقع تم إنشاؤه في الجلسة
        for msg in reversed(session.get("messages", [])):
            for attachment in msg.get("attachments", []):
                if attachment.get("type") == "website":
                    files = attachment.get("files", {})
                    result = await self.create_project_package(
                        user_id=user_id,
                        session_id=project.get("session_id"),
                        project_name=project.get("name"),
                        project_type=project.get("type"),
                        files=files
                    )
                    return result.get("zip_base64")
        
        return None
