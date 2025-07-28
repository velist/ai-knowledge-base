"""用户API路由"""

from typing import List, Optional
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from loguru import logger

from app.core.database import get_db
from app.core.auth import get_current_active_user, auth_manager
from app.models.database import User, UsageStats, KnowledgeBase, File
from app.models.schemas import (
    UserResponse, UserUpdate, PasswordChange,
    UserUsageStats, UserTier, APIResponse
)
from app.core.exceptions import ValidationError, AuthenticationError

router = APIRouter()

@router.get("/profile", response_model=UserResponse, summary="获取用户资料")
async def get_user_profile(
    current_user: User = Depends(get_current_active_user)
):
    """
    获取当前用户的详细资料
    """
    return UserResponse(
        user_id=current_user.user_id,
        username=current_user.username,
        email=current_user.email,
        full_name=current_user.full_name,
        avatar_url=current_user.avatar_url,
        tier=current_user.tier,
        is_active=current_user.is_active,
        is_verified=current_user.is_verified,
        created_at=current_user.created_at,
        last_login=current_user.last_login
    )

@router.put("/profile", response_model=UserResponse, summary="更新用户资料")
async def update_user_profile(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    更新用户资料
    
    - **full_name**: 全名
    - **avatar_url**: 头像URL
    """
    try:
        # 更新用户信息
        if user_update.full_name is not None:
            current_user.full_name = user_update.full_name
        
        if user_update.avatar_url is not None:
            current_user.avatar_url = user_update.avatar_url
        
        current_user.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(current_user)
        
        logger.info(f"用户资料更新成功: {current_user.username}")
        
        return UserResponse(
            user_id=current_user.user_id,
            username=current_user.username,
            email=current_user.email,
            full_name=current_user.full_name,
            avatar_url=current_user.avatar_url,
            tier=current_user.tier,
            is_active=current_user.is_active,
            is_verified=current_user.is_verified,
            created_at=current_user.created_at,
            last_login=current_user.last_login
        )
        
    except Exception as e:
        db.rollback()
        logger.error(f"用户资料更新失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="更新用户资料失败，请稍后重试"
        )

@router.post("/change-password", summary="修改密码")
async def change_password(
    password_data: PasswordChange,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    修改用户密码
    
    - **current_password**: 当前密码
    - **new_password**: 新密码
    """
    try:
        # 验证当前密码
        if not auth_manager.verify_password(password_data.current_password, current_user.password_hash):
            raise AuthenticationError("当前密码错误")
        
        # 检查新密码是否与当前密码相同
        if auth_manager.verify_password(password_data.new_password, current_user.password_hash):
            raise ValidationError("新密码不能与当前密码相同")
        
        # 更新密码
        current_user.password_hash = auth_manager.get_password_hash(password_data.new_password)
        current_user.updated_at = datetime.utcnow()
        
        db.commit()
        
        logger.info(f"用户密码修改成功: {current_user.username}")
        
        return {"message": "密码修改成功"}
        
    except Exception as e:
        db.rollback()
        logger.error(f"密码修改失败: {str(e)}")
        if isinstance(e, (ValidationError, AuthenticationError)):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="密码修改失败，请稍后重试"
        )

@router.get("/usage-stats", response_model=UserUsageStats, summary="获取使用统计")
async def get_usage_stats(
    days: int = Query(30, ge=1, le=365, description="统计天数"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    获取用户使用统计
    
    - **days**: 统计天数（1-365天）
    """
    try:
        # 计算日期范围
        end_date = datetime.utcnow().date()
        start_date = end_date - timedelta(days=days)
        
        # 查询使用统计
        stats = db.query(UsageStats).filter(
            UsageStats.user_id == current_user.id,
            func.date(UsageStats.date) >= start_date,
            func.date(UsageStats.date) <= end_date
        ).all()
        
        # 聚合统计数据
        total_api_calls = sum(stat.api_calls for stat in stats)
        total_chat_requests = sum(stat.chat_requests for stat in stats)
        total_embedding_requests = sum(stat.embedding_requests for stat in stats)
        total_tokens = sum(stat.total_tokens for stat in stats)
        total_files_uploaded = sum(stat.files_uploaded for stat in stats)
        total_files_processed = sum(stat.files_processed for stat in stats)
        total_storage_used = sum(stat.storage_used for stat in stats)
        total_search_requests = sum(stat.search_requests for stat in stats)
        
        # 获取知识库和文件统计
        kb_count = db.query(KnowledgeBase).filter(
            KnowledgeBase.owner_id == current_user.id
        ).count()
        
        file_count = db.query(File).filter(
            File.owner_id == current_user.id
        ).count()
        
        # 获取用户等级限制
        tier_limits = {
            UserTier.FREE: {
                "api_calls_per_day": 100,
                "storage_limit": 100 * 1024 * 1024,  # 100MB
                "knowledge_bases_limit": 3
            },
            UserTier.PRO: {
                "api_calls_per_day": 1000,
                "storage_limit": 1024 * 1024 * 1024,  # 1GB
                "knowledge_bases_limit": 20
            },
            UserTier.ENTERPRISE: {
                "api_calls_per_day": 10000,
                "storage_limit": 10 * 1024 * 1024 * 1024,  # 10GB
                "knowledge_bases_limit": 100
            }
        }
        
        user_tier = UserTier(current_user.tier)
        limits = tier_limits.get(user_tier, tier_limits[UserTier.FREE])
        
        # 计算今日使用量
        today_stats = db.query(UsageStats).filter(
            UsageStats.user_id == current_user.id,
            func.date(UsageStats.date) == end_date
        ).first()
        
        today_api_calls = today_stats.api_calls if today_stats else 0
        
        return UserUsageStats(
            period_days=days,
            total_api_calls=total_api_calls,
            total_chat_requests=total_chat_requests,
            total_embedding_requests=total_embedding_requests,
            total_tokens=total_tokens,
            total_files_uploaded=total_files_uploaded,
            total_files_processed=total_files_processed,
            total_storage_used=total_storage_used,
            total_search_requests=total_search_requests,
            knowledge_bases_count=kb_count,
            files_count=file_count,
            current_tier=current_user.tier,
            daily_api_limit=limits["api_calls_per_day"],
            storage_limit=limits["storage_limit"],
            knowledge_bases_limit=limits["knowledge_bases_limit"],
            today_api_calls=today_api_calls,
            storage_usage_percentage=min(100, (total_storage_used / limits["storage_limit"]) * 100)
        )
        
    except Exception as e:
        logger.error(f"获取使用统计失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取使用统计失败，请稍后重试"
        )

@router.get("/tier-info", summary="获取等级信息")
async def get_tier_info(
    current_user: User = Depends(get_current_active_user)
):
    """
    获取用户等级信息和限制
    """
    tier_info = {
        UserTier.FREE: {
            "name": "免费版",
            "price": 0,
            "features": [
                "每日100次API调用",
                "100MB存储空间",
                "最多3个知识库",
                "基础搜索功能",
                "社区支持"
            ],
            "limits": {
                "api_calls_per_day": 100,
                "storage_limit": 100 * 1024 * 1024,
                "knowledge_bases_limit": 3,
                "file_size_limit": 10 * 1024 * 1024,
                "ai_features": False
            }
        },
        UserTier.PRO: {
            "name": "专业版",
            "price": 29,
            "features": [
                "每日1000次API调用",
                "1GB存储空间",
                "最多20个知识库",
                "高级搜索功能",
                "AI增强搜索",
                "优先支持"
            ],
            "limits": {
                "api_calls_per_day": 1000,
                "storage_limit": 1024 * 1024 * 1024,
                "knowledge_bases_limit": 20,
                "file_size_limit": 50 * 1024 * 1024,
                "ai_features": True
            }
        },
        UserTier.ENTERPRISE: {
            "name": "企业版",
            "price": 99,
            "features": [
                "每日10000次API调用",
                "10GB存储空间",
                "最多100个知识库",
                "全功能搜索",
                "AI增强搜索",
                "API访问",
                "专属支持"
            ],
            "limits": {
                "api_calls_per_day": 10000,
                "storage_limit": 10 * 1024 * 1024 * 1024,
                "knowledge_bases_limit": 100,
                "file_size_limit": 100 * 1024 * 1024,
                "ai_features": True
            }
        }
    }
    
    current_tier = UserTier(current_user.tier)
    
    return {
        "current_tier": current_tier.value,
        "current_tier_info": tier_info[current_tier],
        "all_tiers": tier_info,
        "upgrade_available": current_tier != UserTier.ENTERPRISE
    }

@router.post("/upgrade-tier", summary="升级用户等级")
async def upgrade_tier(
    target_tier: UserTier,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    升级用户等级
    
    注意：这里只是演示接口，实际应该集成支付系统
    """
    try:
        current_tier = UserTier(current_user.tier)
        
        # 检查升级是否有效
        tier_hierarchy = {
            UserTier.FREE: 0,
            UserTier.PRO: 1,
            UserTier.ENTERPRISE: 2
        }
        
        if tier_hierarchy[target_tier] <= tier_hierarchy[current_tier]:
            raise ValidationError("无法降级或升级到相同等级")
        
        # TODO: 集成支付系统验证支付
        
        # 更新用户等级
        current_user.tier = target_tier.value
        current_user.updated_at = datetime.utcnow()
        
        db.commit()
        
        logger.info(f"用户等级升级成功: {current_user.username} -> {target_tier.value}")
        
        return {
            "message": f"成功升级到{target_tier.value}",
            "new_tier": target_tier.value
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"用户等级升级失败: {str(e)}")
        if isinstance(e, ValidationError):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="升级失败，请稍后重试"
        )

@router.delete("/account", summary="删除账户")
async def delete_account(
    password: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    删除用户账户
    
    注意：此操作不可逆，将删除所有相关数据
    """
    try:
        # 验证密码
        if not auth_manager.verify_password(password, current_user.password_hash):
            raise AuthenticationError("密码错误")
        
        # TODO: 删除用户相关的所有数据
        # - 知识库
        # - 文件
        # - 对话记录
        # - 使用统计
        # - 向量数据
        # - 搜索索引
        
        # 软删除用户（设置为非活跃状态）
        current_user.is_active = False
        current_user.updated_at = datetime.utcnow()
        
        db.commit()
        
        logger.info(f"用户账户删除成功: {current_user.username}")
        
        return {"message": "账户删除成功"}
        
    except Exception as e:
        db.rollback()
        logger.error(f"删除账户失败: {str(e)}")
        if isinstance(e, AuthenticationError):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="删除账户失败，请稍后重试"
        )

@router.get("/dashboard", summary="获取用户仪表板数据")
async def get_dashboard(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    获取用户仪表板数据
    """
    try:
        # 获取基本统计
        kb_count = db.query(KnowledgeBase).filter(
            KnowledgeBase.owner_id == current_user.id
        ).count()
        
        file_count = db.query(File).filter(
            File.owner_id == current_user.id
        ).count()
        
        processed_files = db.query(File).filter(
            File.owner_id == current_user.id,
            File.is_processed == True
        ).count()
        
        # 获取最近的知识库
        recent_kbs = db.query(KnowledgeBase).filter(
            KnowledgeBase.owner_id == current_user.id
        ).order_by(KnowledgeBase.updated_at.desc()).limit(5).all()
        
        # 获取最近的文件
        recent_files = db.query(File).filter(
            File.owner_id == current_user.id
        ).order_by(File.created_at.desc()).limit(5).all()
        
        # 获取今日使用统计
        today = datetime.utcnow().date()
        today_stats = db.query(UsageStats).filter(
            UsageStats.user_id == current_user.id,
            func.date(UsageStats.date) == today
        ).first()
        
        return {
            "user_info": {
                "username": current_user.username,
                "tier": current_user.tier,
                "is_verified": current_user.is_verified
            },
            "statistics": {
                "knowledge_bases": kb_count,
                "total_files": file_count,
                "processed_files": processed_files,
                "processing_rate": round((processed_files / file_count * 100) if file_count > 0 else 0, 1)
            },
            "today_usage": {
                "api_calls": today_stats.api_calls if today_stats else 0,
                "chat_requests": today_stats.chat_requests if today_stats else 0,
                "search_requests": today_stats.search_requests if today_stats else 0
            },
            "recent_knowledge_bases": [
                {
                    "kb_id": kb.kb_id,
                    "name": kb.name,
                    "file_count": kb.file_count,
                    "updated_at": kb.updated_at
                }
                for kb in recent_kbs
            ],
            "recent_files": [
                {
                    "file_id": file.file_id,
                    "filename": file.original_filename,
                    "file_type": file.file_type,
                    "is_processed": file.is_processed,
                    "created_at": file.created_at
                }
                for file in recent_files
            ]
        }
        
    except Exception as e:
        logger.error(f"获取仪表板数据失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取仪表板数据失败，请稍后重试"
        )