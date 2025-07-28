"""知识库API路由"""

from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from loguru import logger

from app.core.database import get_db
from app.core.auth import get_current_active_user, require_tier, check_resource_permission
from app.models.database import User, KnowledgeBase, File
from app.models.schemas import (
    KnowledgeBaseCreate, KnowledgeBaseUpdate, KnowledgeBaseResponse,
    KnowledgeBaseListResponse, UserTier, APIResponse
)
from app.core.exceptions import ValidationError, ResourceNotFoundError, PermissionDeniedError
from app.services.search_service import SearchService

router = APIRouter()
search_service = SearchService()

@router.post("/", response_model=KnowledgeBaseResponse, summary="创建知识库")
async def create_knowledge_base(
    kb_data: KnowledgeBaseCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    创建新的知识库
    
    - **name**: 知识库名称
    - **description**: 知识库描述
    - **is_public**: 是否公开（默认私有）
    - **tags**: 标签列表
    """
    try:
        # 检查用户等级限制
        tier_limits = {
            UserTier.FREE: 3,
            UserTier.PRO: 20,
            UserTier.ENTERPRISE: 100
        }
        
        user_tier = UserTier(current_user.tier)
        max_kbs = tier_limits.get(user_tier, 3)
        
        # 检查当前知识库数量
        current_kb_count = db.query(KnowledgeBase).filter(
            KnowledgeBase.owner_id == current_user.id
        ).count()
        
        if current_kb_count >= max_kbs:
            raise ValidationError(f"您的等级最多只能创建{max_kbs}个知识库")
        
        # 检查名称是否重复
        existing_kb = db.query(KnowledgeBase).filter(
            KnowledgeBase.owner_id == current_user.id,
            KnowledgeBase.name == kb_data.name
        ).first()
        
        if existing_kb:
            raise ValidationError("知识库名称已存在")
        
        # 创建知识库
        new_kb = KnowledgeBase(
            name=kb_data.name,
            description=kb_data.description,
            owner_id=current_user.id,
            is_public=kb_data.is_public,
            tags=kb_data.tags or [],
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        db.add(new_kb)
        db.commit()
        db.refresh(new_kb)
        
        logger.info(f"知识库创建成功: {new_kb.name} by {current_user.username}")
        
        return KnowledgeBaseResponse(
            kb_id=new_kb.kb_id,
            name=new_kb.name,
            description=new_kb.description,
            owner_id=new_kb.owner_id,
            is_public=new_kb.is_public,
            tags=new_kb.tags,
            file_count=0,
            total_size=0,
            created_at=new_kb.created_at,
            updated_at=new_kb.updated_at
        )
        
    except Exception as e:
        db.rollback()
        logger.error(f"创建知识库失败: {str(e)}")
        if isinstance(e, ValidationError):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="创建知识库失败，请稍后重试"
        )

@router.get("/", response_model=KnowledgeBaseListResponse, summary="获取知识库列表")
async def list_knowledge_bases(
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(20, ge=1, le=100, description="每页数量"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    tags: Optional[str] = Query(None, description="标签过滤（逗号分隔）"),
    is_public: Optional[bool] = Query(None, description="是否公开"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    获取知识库列表
    
    - **page**: 页码
    - **size**: 每页数量
    - **search**: 搜索关键词
    - **tags**: 标签过滤
    - **is_public**: 是否公开
    """
    try:
        # 构建查询
        query = db.query(KnowledgeBase).filter(
            or_(
                KnowledgeBase.owner_id == current_user.id,
                KnowledgeBase.is_public == True
            )
        )
        
        # 搜索过滤
        if search:
            query = query.filter(
                or_(
                    KnowledgeBase.name.ilike(f"%{search}%"),
                    KnowledgeBase.description.ilike(f"%{search}%")
                )
            )
        
        # 标签过滤
        if tags:
            tag_list = [tag.strip() for tag in tags.split(",")]
            for tag in tag_list:
                query = query.filter(KnowledgeBase.tags.contains([tag]))
        
        # 公开状态过滤
        if is_public is not None:
            query = query.filter(KnowledgeBase.is_public == is_public)
        
        # 计算总数
        total = query.count()
        
        # 分页查询
        offset = (page - 1) * size
        kbs = query.order_by(KnowledgeBase.updated_at.desc()).offset(offset).limit(size).all()
        
        # 获取每个知识库的文件统计
        kb_responses = []
        for kb in kbs:
            file_stats = db.query(
                func.count(File.id).label('file_count'),
                func.coalesce(func.sum(File.file_size), 0).label('total_size')
            ).filter(File.knowledge_base_id == kb.id).first()
            
            kb_responses.append(KnowledgeBaseResponse(
                kb_id=kb.kb_id,
                name=kb.name,
                description=kb.description,
                owner_id=kb.owner_id,
                is_public=kb.is_public,
                tags=kb.tags,
                file_count=file_stats.file_count or 0,
                total_size=file_stats.total_size or 0,
                created_at=kb.created_at,
                updated_at=kb.updated_at
            ))
        
        return KnowledgeBaseListResponse(
            items=kb_responses,
            total=total,
            page=page,
            size=size,
            pages=(total + size - 1) // size
        )
        
    except Exception as e:
        logger.error(f"获取知识库列表失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取知识库列表失败，请稍后重试"
        )

@router.get("/{kb_id}", response_model=KnowledgeBaseResponse, summary="获取知识库详情")
async def get_knowledge_base(
    kb_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    获取知识库详情
    """
    try:
        # 查找知识库
        kb = db.query(KnowledgeBase).filter(KnowledgeBase.kb_id == kb_id).first()
        
        if not kb:
            raise ResourceNotFoundError("知识库不存在")
        
        # 检查访问权限
        if not kb.is_public and kb.owner_id != current_user.id:
            raise PermissionDeniedError("无权访问此知识库")
        
        # 获取文件统计
        file_stats = db.query(
            func.count(File.id).label('file_count'),
            func.coalesce(func.sum(File.file_size), 0).label('total_size')
        ).filter(File.knowledge_base_id == kb.id).first()
        
        return KnowledgeBaseResponse(
            kb_id=kb.kb_id,
            name=kb.name,
            description=kb.description,
            owner_id=kb.owner_id,
            is_public=kb.is_public,
            tags=kb.tags,
            file_count=file_stats.file_count or 0,
            total_size=file_stats.total_size or 0,
            created_at=kb.created_at,
            updated_at=kb.updated_at
        )
        
    except Exception as e:
        logger.error(f"获取知识库详情失败: {str(e)}")
        if isinstance(e, (ResourceNotFoundError, PermissionDeniedError)):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND if isinstance(e, ResourceNotFoundError) else status.HTTP_403_FORBIDDEN,
                detail=str(e)
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取知识库详情失败，请稍后重试"
        )

@router.put("/{kb_id}", response_model=KnowledgeBaseResponse, summary="更新知识库")
async def update_knowledge_base(
    kb_id: str,
    kb_update: KnowledgeBaseUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    更新知识库信息
    
    - **name**: 知识库名称
    - **description**: 知识库描述
    - **is_public**: 是否公开
    - **tags**: 标签列表
    """
    try:
        # 查找知识库
        kb = db.query(KnowledgeBase).filter(KnowledgeBase.kb_id == kb_id).first()
        
        if not kb:
            raise ResourceNotFoundError("知识库不存在")
        
        # 检查权限
        if kb.owner_id != current_user.id:
            raise PermissionDeniedError("无权修改此知识库")
        
        # 检查名称是否重复（如果要修改名称）
        if kb_update.name and kb_update.name != kb.name:
            existing_kb = db.query(KnowledgeBase).filter(
                KnowledgeBase.owner_id == current_user.id,
                KnowledgeBase.name == kb_update.name,
                KnowledgeBase.id != kb.id
            ).first()
            
            if existing_kb:
                raise ValidationError("知识库名称已存在")
        
        # 更新字段
        if kb_update.name is not None:
            kb.name = kb_update.name
        
        if kb_update.description is not None:
            kb.description = kb_update.description
        
        if kb_update.is_public is not None:
            kb.is_public = kb_update.is_public
        
        if kb_update.tags is not None:
            kb.tags = kb_update.tags
        
        kb.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(kb)
        
        # 获取文件统计
        file_stats = db.query(
            func.count(File.id).label('file_count'),
            func.coalesce(func.sum(File.file_size), 0).label('total_size')
        ).filter(File.knowledge_base_id == kb.id).first()
        
        logger.info(f"知识库更新成功: {kb.name} by {current_user.username}")
        
        return KnowledgeBaseResponse(
            kb_id=kb.kb_id,
            name=kb.name,
            description=kb.description,
            owner_id=kb.owner_id,
            is_public=kb.is_public,
            tags=kb.tags,
            file_count=file_stats.file_count or 0,
            total_size=file_stats.total_size or 0,
            created_at=kb.created_at,
            updated_at=kb.updated_at
        )
        
    except Exception as e:
        db.rollback()
        logger.error(f"更新知识库失败: {str(e)}")
        if isinstance(e, (ResourceNotFoundError, PermissionDeniedError, ValidationError)):
            status_code = {
                ResourceNotFoundError: status.HTTP_404_NOT_FOUND,
                PermissionDeniedError: status.HTTP_403_FORBIDDEN,
                ValidationError: status.HTTP_400_BAD_REQUEST
            }[type(e)]
            raise HTTPException(status_code=status_code, detail=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="更新知识库失败，请稍后重试"
        )

@router.delete("/{kb_id}", summary="删除知识库")
async def delete_knowledge_base(
    kb_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    删除知识库
    
    注意：此操作将删除知识库及其所有文件
    """
    try:
        # 查找知识库
        kb = db.query(KnowledgeBase).filter(KnowledgeBase.kb_id == kb_id).first()
        
        if not kb:
            raise ResourceNotFoundError("知识库不存在")
        
        # 检查权限
        if kb.owner_id != current_user.id:
            raise PermissionDeniedError("无权删除此知识库")
        
        # 获取关联的文件
        files = db.query(File).filter(File.knowledge_base_id == kb.id).all()
        
        # TODO: 删除文件相关的数据
        # - 物理文件
        # - 向量数据
        # - 搜索索引
        
        # 删除文件记录
        for file in files:
            db.delete(file)
        
        # 删除知识库
        db.delete(kb)
        db.commit()
        
        logger.info(f"知识库删除成功: {kb.name} by {current_user.username}")
        
        return {"message": "知识库删除成功"}
        
    except Exception as e:
        db.rollback()
        logger.error(f"删除知识库失败: {str(e)}")
        if isinstance(e, (ResourceNotFoundError, PermissionDeniedError)):
            status_code = {
                ResourceNotFoundError: status.HTTP_404_NOT_FOUND,
                PermissionDeniedError: status.HTTP_403_FORBIDDEN
            }[type(e)]
            raise HTTPException(status_code=status_code, detail=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="删除知识库失败，请稍后重试"
        )

@router.get("/{kb_id}/files", summary="获取知识库文件列表")
async def list_knowledge_base_files(
    kb_id: str,
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(20, ge=1, le=100, description="每页数量"),
    file_type: Optional[str] = Query(None, description="文件类型过滤"),
    is_processed: Optional[bool] = Query(None, description="是否已处理"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    获取知识库的文件列表
    """
    try:
        # 查找知识库
        kb = db.query(KnowledgeBase).filter(KnowledgeBase.kb_id == kb_id).first()
        
        if not kb:
            raise ResourceNotFoundError("知识库不存在")
        
        # 检查访问权限
        if not kb.is_public and kb.owner_id != current_user.id:
            raise PermissionDeniedError("无权访问此知识库")
        
        # 构建查询
        query = db.query(File).filter(File.knowledge_base_id == kb.id)
        
        # 文件类型过滤
        if file_type:
            query = query.filter(File.file_type == file_type)
        
        # 处理状态过滤
        if is_processed is not None:
            query = query.filter(File.is_processed == is_processed)
        
        # 计算总数
        total = query.count()
        
        # 分页查询
        offset = (page - 1) * size
        files = query.order_by(File.created_at.desc()).offset(offset).limit(size).all()
        
        # 构建响应
        file_responses = [
            {
                "file_id": file.file_id,
                "original_filename": file.original_filename,
                "file_type": file.file_type,
                "file_size": file.file_size,
                "is_processed": file.is_processed,
                "processing_status": file.processing_status,
                "error_message": file.error_message,
                "language": file.language,
                "created_at": file.created_at,
                "updated_at": file.updated_at
            }
            for file in files
        ]
        
        return {
            "items": file_responses,
            "total": total,
            "page": page,
            "size": size,
            "pages": (total + size - 1) // size
        }
        
    except Exception as e:
        logger.error(f"获取知识库文件列表失败: {str(e)}")
        if isinstance(e, (ResourceNotFoundError, PermissionDeniedError)):
            status_code = {
                ResourceNotFoundError: status.HTTP_404_NOT_FOUND,
                PermissionDeniedError: status.HTTP_403_FORBIDDEN
            }[type(e)]
            raise HTTPException(status_code=status_code, detail=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取文件列表失败，请稍后重试"
        )

@router.post("/{kb_id}/reindex", summary="重建知识库索引")
async def reindex_knowledge_base(
    kb_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    重建知识库的搜索索引
    """
    try:
        # 查找知识库
        kb = db.query(KnowledgeBase).filter(KnowledgeBase.kb_id == kb_id).first()
        
        if not kb:
            raise ResourceNotFoundError("知识库不存在")
        
        # 检查权限
        if kb.owner_id != current_user.id:
            raise PermissionDeniedError("无权操作此知识库")
        
        # 获取知识库的所有已处理文件
        files = db.query(File).filter(
            File.knowledge_base_id == kb.id,
            File.is_processed == True
        ).all()
        
        if not files:
            return {"message": "知识库中没有已处理的文件"}
        
        # TODO: 异步重建索引
        # 这里应该启动后台任务来重建索引
        
        logger.info(f"开始重建知识库索引: {kb.name} by {current_user.username}")
        
        return {
            "message": "索引重建任务已启动",
            "file_count": len(files)
        }
        
    except Exception as e:
        logger.error(f"重建知识库索引失败: {str(e)}")
        if isinstance(e, (ResourceNotFoundError, PermissionDeniedError)):
            status_code = {
                ResourceNotFoundError: status.HTTP_404_NOT_FOUND,
                PermissionDeniedError: status.HTTP_403_FORBIDDEN
            }[type(e)]
            raise HTTPException(status_code=status_code, detail=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="重建索引失败，请稍后重试"
        )

@router.get("/{kb_id}/stats", summary="获取知识库统计")
async def get_knowledge_base_stats(
    kb_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    获取知识库的详细统计信息
    """
    try:
        # 查找知识库
        kb = db.query(KnowledgeBase).filter(KnowledgeBase.kb_id == kb_id).first()
        
        if not kb:
            raise ResourceNotFoundError("知识库不存在")
        
        # 检查访问权限
        if not kb.is_public and kb.owner_id != current_user.id:
            raise PermissionDeniedError("无权访问此知识库")
        
        # 文件统计
        file_stats = db.query(
            func.count(File.id).label('total_files'),
            func.count(File.id).filter(File.is_processed == True).label('processed_files'),
            func.coalesce(func.sum(File.file_size), 0).label('total_size')
        ).filter(File.knowledge_base_id == kb.id).first()
        
        # 按文件类型统计
        file_type_stats = db.query(
            File.file_type,
            func.count(File.id).label('count'),
            func.coalesce(func.sum(File.file_size), 0).label('size')
        ).filter(
            File.knowledge_base_id == kb.id
        ).group_by(File.file_type).all()
        
        # 按语言统计
        language_stats = db.query(
            File.language,
            func.count(File.id).label('count')
        ).filter(
            File.knowledge_base_id == kb.id,
            File.language.isnot(None)
        ).group_by(File.language).all()
        
        return {
            "knowledge_base": {
                "kb_id": kb.kb_id,
                "name": kb.name,
                "is_public": kb.is_public,
                "created_at": kb.created_at,
                "updated_at": kb.updated_at
            },
            "file_stats": {
                "total_files": file_stats.total_files or 0,
                "processed_files": file_stats.processed_files or 0,
                "processing_rate": round(
                    (file_stats.processed_files / file_stats.total_files * 100) 
                    if file_stats.total_files > 0 else 0, 1
                ),
                "total_size": file_stats.total_size or 0
            },
            "file_type_distribution": [
                {
                    "file_type": stat.file_type,
                    "count": stat.count,
                    "size": stat.size
                }
                for stat in file_type_stats
            ],
            "language_distribution": [
                {
                    "language": stat.language,
                    "count": stat.count
                }
                for stat in language_stats
            ]
        }
        
    except Exception as e:
        logger.error(f"获取知识库统计失败: {str(e)}")
        if isinstance(e, (ResourceNotFoundError, PermissionDeniedError)):
            status_code = {
                ResourceNotFoundError: status.HTTP_404_NOT_FOUND,
                PermissionDeniedError: status.HTTP_403_FORBIDDEN
            }[type(e)]
            raise HTTPException(status_code=status_code, detail=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取统计信息失败，请稍后重试"
        )