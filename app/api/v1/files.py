"""文件API路由"""

from typing import List, Optional
from datetime import datetime
import os

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File as FastAPIFile, Form, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from loguru import logger

from app.core.database import get_db
from app.core.auth import get_current_active_user, check_resource_permission
from app.models.database import User, KnowledgeBase, File
from app.models.schemas import (
    FileResponse, FileListResponse, FileUploadResponse,
    UserTier, APIResponse
)
from app.core.exceptions import (
    ValidationError, ResourceNotFoundError, PermissionDeniedError,
    FileProcessingError
)
from app.services.file_service import FileService
from app.config import settings

router = APIRouter()
file_service = FileService()

@router.post("/upload", response_model=FileUploadResponse, summary="上传文件")
async def upload_file(
    file: UploadFile = FastAPIFile(...),
    knowledge_base_id: str = Form(...),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    上传文件到指定知识库
    
    - **file**: 要上传的文件
    - **knowledge_base_id**: 目标知识库ID
    """
    try:
        # 验证知识库
        kb = db.query(KnowledgeBase).filter(KnowledgeBase.kb_id == knowledge_base_id).first()
        if not kb:
            raise ResourceNotFoundError("知识库不存在")
        
        # 检查权限
        if kb.owner_id != current_user.id:
            raise PermissionDeniedError("无权向此知识库上传文件")
        
        # 检查文件大小限制
        tier_limits = {
            UserTier.FREE: 10 * 1024 * 1024,      # 10MB
            UserTier.PRO: 50 * 1024 * 1024,       # 50MB
            UserTier.ENTERPRISE: 100 * 1024 * 1024 # 100MB
        }
        
        user_tier = UserTier(current_user.tier)
        max_file_size = tier_limits.get(user_tier, 10 * 1024 * 1024)
        
        # 读取文件内容以获取实际大小
        file_content = await file.read()
        file_size = len(file_content)
        
        if file_size > max_file_size:
            raise ValidationError(f"文件大小超过限制（{max_file_size // (1024*1024)}MB）")
        
        # 检查存储空间限制
        storage_limits = {
            UserTier.FREE: 100 * 1024 * 1024,        # 100MB
            UserTier.PRO: 1024 * 1024 * 1024,        # 1GB
            UserTier.ENTERPRISE: 10 * 1024 * 1024 * 1024  # 10GB
        }
        
        max_storage = storage_limits.get(user_tier, 100 * 1024 * 1024)
        
        # 计算当前使用的存储空间
        current_storage = db.query(
            func.coalesce(func.sum(File.file_size), 0)
        ).filter(File.owner_id == current_user.id).scalar() or 0
        
        if current_storage + file_size > max_storage:
            raise ValidationError(f"存储空间不足，当前已使用{current_storage // (1024*1024)}MB")
        
        # 检查支持的文件类型
        supported_extensions = {
            '.pdf', '.txt', '.md', '.docx', '.doc', 
            '.pptx', '.ppt', '.xlsx', '.xls', '.csv',
            '.jpg', '.jpeg', '.png', '.gif', '.bmp'
        }
        
        file_extension = os.path.splitext(file.filename)[1].lower()
        if file_extension not in supported_extensions:
            raise ValidationError(f"不支持的文件类型: {file_extension}")
        
        # 重置文件指针
        await file.seek(0)
        
        # 使用文件服务处理上传
        uploaded_file = await file_service.upload_file(
            file=file,
            knowledge_base_id=kb.id,
            user_id=current_user.id,
            db=db
        )
        
        logger.info(f"文件上传成功: {file.filename} by {current_user.username}")
        
        return FileUploadResponse(
            file_id=uploaded_file.file_id,
            original_filename=uploaded_file.original_filename,
            file_type=uploaded_file.file_type,
            file_size=uploaded_file.file_size,
            processing_status="pending",
            message="文件上传成功，正在处理中"
        )
        
    except Exception as e:
        logger.error(f"文件上传失败: {str(e)}")
        if isinstance(e, (ValidationError, ResourceNotFoundError, PermissionDeniedError)):
            status_code = {
                ValidationError: status.HTTP_400_BAD_REQUEST,
                ResourceNotFoundError: status.HTTP_404_NOT_FOUND,
                PermissionDeniedError: status.HTTP_403_FORBIDDEN
            }[type(e)]
            raise HTTPException(status_code=status_code, detail=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="文件上传失败，请稍后重试"
        )

@router.get("/", response_model=FileListResponse, summary="获取文件列表")
async def list_files(
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(20, ge=1, le=100, description="每页数量"),
    knowledge_base_id: Optional[str] = Query(None, description="知识库ID过滤"),
    file_type: Optional[str] = Query(None, description="文件类型过滤"),
    is_processed: Optional[bool] = Query(None, description="是否已处理"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    获取用户的文件列表
    
    - **page**: 页码
    - **size**: 每页数量
    - **knowledge_base_id**: 知识库ID过滤
    - **file_type**: 文件类型过滤
    - **is_processed**: 是否已处理
    - **search**: 搜索关键词
    """
    try:
        # 构建查询
        query = db.query(File).filter(File.owner_id == current_user.id)
        
        # 知识库过滤
        if knowledge_base_id:
            kb = db.query(KnowledgeBase).filter(
                KnowledgeBase.kb_id == knowledge_base_id,
                KnowledgeBase.owner_id == current_user.id
            ).first()
            if not kb:
                raise ResourceNotFoundError("知识库不存在")
            query = query.filter(File.knowledge_base_id == kb.id)
        
        # 文件类型过滤
        if file_type:
            query = query.filter(File.file_type == file_type)
        
        # 处理状态过滤
        if is_processed is not None:
            query = query.filter(File.is_processed == is_processed)
        
        # 搜索过滤
        if search:
            query = query.filter(
                or_(
                    File.original_filename.ilike(f"%{search}%"),
                    File.extracted_text.ilike(f"%{search}%")
                )
            )
        
        # 计算总数
        total = query.count()
        
        # 分页查询
        offset = (page - 1) * size
        files = query.order_by(File.created_at.desc()).offset(offset).limit(size).all()
        
        # 构建响应
        file_responses = []
        for file in files:
            # 获取知识库信息
            kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == file.knowledge_base_id).first()
            
            file_responses.append(FileResponse(
                file_id=file.file_id,
                original_filename=file.original_filename,
                file_type=file.file_type,
                file_size=file.file_size,
                knowledge_base_id=kb.kb_id if kb else None,
                knowledge_base_name=kb.name if kb else None,
                is_processed=file.is_processed,
                processing_status=file.processing_status,
                error_message=file.error_message,
                language=file.language,
                created_at=file.created_at,
                updated_at=file.updated_at
            ))
        
        return FileListResponse(
            items=file_responses,
            total=total,
            page=page,
            size=size,
            pages=(total + size - 1) // size
        )
        
    except Exception as e:
        logger.error(f"获取文件列表失败: {str(e)}")
        if isinstance(e, ResourceNotFoundError):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e)
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取文件列表失败，请稍后重试"
        )

@router.get("/{file_id}", response_model=FileResponse, summary="获取文件详情")
async def get_file(
    file_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    获取文件详情
    """
    try:
        # 查找文件
        file = db.query(File).filter(File.file_id == file_id).first()
        
        if not file:
            raise ResourceNotFoundError("文件不存在")
        
        # 检查权限
        if file.owner_id != current_user.id:
            # 检查是否是公开知识库的文件
            kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == file.knowledge_base_id).first()
            if not kb or not kb.is_public:
                raise PermissionDeniedError("无权访问此文件")
        
        # 获取知识库信息
        kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == file.knowledge_base_id).first()
        
        return FileResponse(
            file_id=file.file_id,
            original_filename=file.original_filename,
            file_type=file.file_type,
            file_size=file.file_size,
            knowledge_base_id=kb.kb_id if kb else None,
            knowledge_base_name=kb.name if kb else None,
            is_processed=file.is_processed,
            processing_status=file.processing_status,
            error_message=file.error_message,
            language=file.language,
            created_at=file.created_at,
            updated_at=file.updated_at
        )
        
    except Exception as e:
        logger.error(f"获取文件详情失败: {str(e)}")
        if isinstance(e, (ResourceNotFoundError, PermissionDeniedError)):
            status_code = {
                ResourceNotFoundError: status.HTTP_404_NOT_FOUND,
                PermissionDeniedError: status.HTTP_403_FORBIDDEN
            }[type(e)]
            raise HTTPException(status_code=status_code, detail=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取文件详情失败，请稍后重试"
        )

@router.get("/{file_id}/content", summary="获取文件内容")
async def get_file_content(
    file_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    获取文件的提取内容
    """
    try:
        # 查找文件
        file = db.query(File).filter(File.file_id == file_id).first()
        
        if not file:
            raise ResourceNotFoundError("文件不存在")
        
        # 检查权限
        if file.owner_id != current_user.id:
            # 检查是否是公开知识库的文件
            kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == file.knowledge_base_id).first()
            if not kb or not kb.is_public:
                raise PermissionDeniedError("无权访问此文件")
        
        if not file.is_processed:
            raise ValidationError("文件尚未处理完成")
        
        return {
            "file_id": file.file_id,
            "original_filename": file.original_filename,
            "extracted_text": file.extracted_text,
            "language": file.language,
            "metadata": file.metadata
        }
        
    except Exception as e:
        logger.error(f"获取文件内容失败: {str(e)}")
        if isinstance(e, (ResourceNotFoundError, PermissionDeniedError, ValidationError)):
            status_code = {
                ResourceNotFoundError: status.HTTP_404_NOT_FOUND,
                PermissionDeniedError: status.HTTP_403_FORBIDDEN,
                ValidationError: status.HTTP_400_BAD_REQUEST
            }[type(e)]
            raise HTTPException(status_code=status_code, detail=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取文件内容失败，请稍后重试"
        )

@router.get("/{file_id}/download", summary="下载文件")
async def download_file(
    file_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    下载原始文件
    """
    try:
        # 查找文件
        file = db.query(File).filter(File.file_id == file_id).first()
        
        if not file:
            raise ResourceNotFoundError("文件不存在")
        
        # 检查权限
        if file.owner_id != current_user.id:
            # 检查是否是公开知识库的文件
            kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == file.knowledge_base_id).first()
            if not kb or not kb.is_public:
                raise PermissionDeniedError("无权下载此文件")
        
        # 检查文件是否存在
        file_path = os.path.join(settings.UPLOAD_DIR, file.stored_filename)
        if not os.path.exists(file_path):
            raise ResourceNotFoundError("文件不存在")
        
        return FileResponse(
            path=file_path,
            filename=file.original_filename,
            media_type='application/octet-stream'
        )
        
    except Exception as e:
        logger.error(f"下载文件失败: {str(e)}")
        if isinstance(e, (ResourceNotFoundError, PermissionDeniedError)):
            status_code = {
                ResourceNotFoundError: status.HTTP_404_NOT_FOUND,
                PermissionDeniedError: status.HTTP_403_FORBIDDEN
            }[type(e)]
            raise HTTPException(status_code=status_code, detail=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="下载文件失败，请稍后重试"
        )

@router.post("/{file_id}/reprocess", summary="重新处理文件")
async def reprocess_file(
    file_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    重新处理文件
    """
    try:
        # 查找文件
        file = db.query(File).filter(File.file_id == file_id).first()
        
        if not file:
            raise ResourceNotFoundError("文件不存在")
        
        # 检查权限
        if file.owner_id != current_user.id:
            raise PermissionDeniedError("无权操作此文件")
        
        # 重置处理状态
        file.is_processed = False
        file.processing_status = "pending"
        file.error_message = None
        file.extracted_text = None
        file.language = None
        file.metadata = {}
        file.updated_at = datetime.utcnow()
        
        db.commit()
        
        # TODO: 启动异步处理任务
        
        logger.info(f"文件重新处理启动: {file.original_filename} by {current_user.username}")
        
        return {"message": "文件重新处理任务已启动"}
        
    except Exception as e:
        db.rollback()
        logger.error(f"重新处理文件失败: {str(e)}")
        if isinstance(e, (ResourceNotFoundError, PermissionDeniedError)):
            status_code = {
                ResourceNotFoundError: status.HTTP_404_NOT_FOUND,
                PermissionDeniedError: status.HTTP_403_FORBIDDEN
            }[type(e)]
            raise HTTPException(status_code=status_code, detail=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="重新处理文件失败，请稍后重试"
        )

@router.delete("/{file_id}", summary="删除文件")
async def delete_file(
    file_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    删除文件
    """
    try:
        # 查找文件
        file = db.query(File).filter(File.file_id == file_id).first()
        
        if not file:
            raise ResourceNotFoundError("文件不存在")
        
        # 检查权限
        if file.owner_id != current_user.id:
            raise PermissionDeniedError("无权删除此文件")
        
        # 使用文件服务删除文件
        await file_service.delete_file(file.id, db)
        
        logger.info(f"文件删除成功: {file.original_filename} by {current_user.username}")
        
        return {"message": "文件删除成功"}
        
    except Exception as e:
        logger.error(f"删除文件失败: {str(e)}")
        if isinstance(e, (ResourceNotFoundError, PermissionDeniedError)):
            status_code = {
                ResourceNotFoundError: status.HTTP_404_NOT_FOUND,
                PermissionDeniedError: status.HTTP_403_FORBIDDEN
            }[type(e)]
            raise HTTPException(status_code=status_code, detail=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="删除文件失败，请稍后重试"
        )

@router.get("/stats/overview", summary="获取文件统计概览")
async def get_files_stats(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    获取用户文件的统计概览
    """
    try:
        # 总文件统计
        total_files = db.query(File).filter(File.owner_id == current_user.id).count()
        processed_files = db.query(File).filter(
            File.owner_id == current_user.id,
            File.is_processed == True
        ).count()
        
        # 总存储使用量
        total_storage = db.query(
            func.coalesce(func.sum(File.file_size), 0)
        ).filter(File.owner_id == current_user.id).scalar() or 0
        
        # 按文件类型统计
        file_type_stats = db.query(
            File.file_type,
            func.count(File.id).label('count'),
            func.coalesce(func.sum(File.file_size), 0).label('size')
        ).filter(
            File.owner_id == current_user.id
        ).group_by(File.file_type).all()
        
        # 按处理状态统计
        status_stats = db.query(
            File.processing_status,
            func.count(File.id).label('count')
        ).filter(
            File.owner_id == current_user.id
        ).group_by(File.processing_status).all()
        
        # 按语言统计
        language_stats = db.query(
            File.language,
            func.count(File.id).label('count')
        ).filter(
            File.owner_id == current_user.id,
            File.language.isnot(None)
        ).group_by(File.language).all()
        
        # 获取用户存储限制
        storage_limits = {
            UserTier.FREE: 100 * 1024 * 1024,        # 100MB
            UserTier.PRO: 1024 * 1024 * 1024,        # 1GB
            UserTier.ENTERPRISE: 10 * 1024 * 1024 * 1024  # 10GB
        }
        
        user_tier = UserTier(current_user.tier)
        storage_limit = storage_limits.get(user_tier, 100 * 1024 * 1024)
        
        return {
            "overview": {
                "total_files": total_files,
                "processed_files": processed_files,
                "processing_rate": round((processed_files / total_files * 100) if total_files > 0 else 0, 1),
                "total_storage": total_storage,
                "storage_limit": storage_limit,
                "storage_usage_percentage": round((total_storage / storage_limit * 100), 1)
            },
            "file_type_distribution": [
                {
                    "file_type": stat.file_type,
                    "count": stat.count,
                    "size": stat.size,
                    "percentage": round((stat.count / total_files * 100) if total_files > 0 else 0, 1)
                }
                for stat in file_type_stats
            ],
            "processing_status_distribution": [
                {
                    "status": stat.processing_status,
                    "count": stat.count,
                    "percentage": round((stat.count / total_files * 100) if total_files > 0 else 0, 1)
                }
                for stat in status_stats
            ],
            "language_distribution": [
                {
                    "language": stat.language,
                    "count": stat.count,
                    "percentage": round((stat.count / processed_files * 100) if processed_files > 0 else 0, 1)
                }
                for stat in language_stats
            ]
        }
        
    except Exception as e:
        logger.error(f"获取文件统计失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取文件统计失败，请稍后重试"
        )