"""
Zitex Deployment API Router
راوتر API للنشر
"""
from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import Response
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import jwt
import os
import base64

router = APIRouter(prefix="/deploy", tags=["Deployment"])
security = HTTPBearer()

JWT_SECRET = os.environ.get('JWT_SECRET', 'your-secret-key')


class CreateProjectRequest(BaseModel):
    project_name: str
    project_type: str = "react"  # react, html
    files: Dict[str, str]
    metadata: Optional[Dict[str, Any]] = None


class ProjectResponse(BaseModel):
    id: str
    name: str
    type: str
    files_count: int
    status: str
    created_at: str


# Dependency to get current user
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=['HS256'])
        user_id = payload.get('user_id')
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")
        return {'user_id': user_id}
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


# Global deployment service instance
deployment_service = None


def set_deployment_service(service):
    """Set the deployment service instance"""
    global deployment_service
    deployment_service = service


@router.post("/projects")
async def create_project(
    request: CreateProjectRequest,
    current_user: dict = Depends(get_current_user)
):
    """إنشاء مشروع جديد وتجهيزه للنشر"""
    if not deployment_service:
        raise HTTPException(status_code=503, detail="Deployment service not available")
    
    try:
        result = await deployment_service.create_project_package(
            user_id=current_user['user_id'],
            session_id="manual",
            project_name=request.project_name,
            project_type=request.project_type,
            files=request.files,
            metadata=request.metadata
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/projects")
async def get_projects(
    limit: int = 20,
    current_user: dict = Depends(get_current_user)
):
    """استرجاع مشاريع المستخدم"""
    if not deployment_service:
        raise HTTPException(status_code=503, detail="Deployment service not available")
    
    projects = await deployment_service.get_user_projects(
        user_id=current_user['user_id'],
        limit=limit
    )
    return projects


@router.get("/projects/{project_id}")
async def get_project(
    project_id: str,
    current_user: dict = Depends(get_current_user)
):
    """استرجاع مشروع محدد"""
    if not deployment_service:
        raise HTTPException(status_code=503, detail="Deployment service not available")
    
    project = await deployment_service.get_project(
        project_id=project_id,
        user_id=current_user['user_id']
    )
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    return project


@router.get("/projects/{project_id}/download")
async def download_project(
    project_id: str,
    current_user: dict = Depends(get_current_user)
):
    """تحميل مشروع كملف ZIP"""
    if not deployment_service:
        raise HTTPException(status_code=503, detail="Deployment service not available")
    
    zip_base64 = await deployment_service.regenerate_zip(
        project_id=project_id,
        user_id=current_user['user_id']
    )
    
    if not zip_base64:
        raise HTTPException(status_code=404, detail="Project not found or files unavailable")
    
    # تحويل base64 إلى bytes
    zip_bytes = base64.b64decode(zip_base64)
    
    return Response(
        content=zip_bytes,
        media_type="application/zip",
        headers={
            "Content-Disposition": f"attachment; filename=project-{project_id[:8]}.zip"
        }
    )


@router.get("/instructions/{project_type}")
async def get_deployment_instructions(
    project_type: str,
    current_user: dict = Depends(get_current_user)
):
    """الحصول على تعليمات النشر لنوع مشروع محدد"""
    if not deployment_service:
        raise HTTPException(status_code=503, detail="Deployment service not available")
    
    instructions = deployment_service._get_deployment_instructions(project_type)
    return instructions

