"""管理员API路由"""

from typing import List, Optional
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from loguru import logger

from app.core.database import get_db
from app.core.auth import get_current_active_user
from app.models.database import (
    User, KnowledgeBase, File, Conversation, Message, 
    UsageStats, SystemConfig, AuditLog
)
from app.models.schemas import (
    UserResponse, UserTier, APIResponse
)
from app.core.exceptions import ValidationError, PermissionDeniedError
from app.core.redis_client import get_redis

router = APIRouter()

# 管理员权限检查装饰器
def require_admin(current_user: User = Depends(get_current_active_user)):
    """检查管理员权限"""
    if current_user.tier != UserTier.ENTERPRISE.value or not current_user.username.startswith('admin_'):
        raise PermissionDeniedError("需要管理员权限")
    return current_user

@router.get("/dashboard", summary="管理员仪表板")
async def admin_dashboard(
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    获取管理员仪表板数据
    """
    try:
        # 用户统计
        total_users = db.query(User).count()
        active_users = db.query(User).filter(User.is_active == True).count()
        verified_users = db.query(User).filter(User.is_verified == True).count()
        
        # 按等级统计用户
        tier_stats = db.query(
            User.tier,
            func.count(User.id).label('count')
        ).group_by(User.tier).all()
        
        # 知识库统计
        total_kbs = db.query(KnowledgeBase).count()
        public_kbs = db.query(KnowledgeBase).filter(KnowledgeBase.is_public == True).count()
        
        # 文件统计
        total_files = db.query(File).count()
        processed_files = db.query(File).filter(File.is_processed == True).count()
        total_storage = db.query(func.coalesce(func.sum(File.file_size), 0)).scalar() or 0
        
        # 对话统计
        total_conversations = db.query(Conversation).count()
        total_messages = db.query(Message).count()
        
        # 今日活跃用户
        today = datetime.utcnow().date()
        today_active = db.query(User).filter(
            func.date(User.last_login) == today
        ).count()
        
        # 最近7天新用户
        week_ago = datetime.utcnow() - timedelta(days=7)
        new_users_week = db.query(User).filter(
            User.created_at >= week_ago
        ).count()
        
        return {
            "users": {
                "total": total_users,
                "active": active_users,
                "verified": verified_users,
                "today_active": today_active,
                "new_this_week": new_users_week,
                "tier_distribution": [
                    {"tier": stat.tier, "count": stat.count}
                    for stat in tier_stats
                ]
            },
            "knowledge_bases": {
                "total": total_kbs,
                "public": public_kbs,
                "private": total_kbs - public_kbs
            },
            "files": {
                "total": total_files,
                "processed": processed_files,
                "processing_rate": round((processed_files / total_files * 100) if total_files > 0 else 0, 1),
                "total_storage_bytes": total_storage,
                "total_storage_mb": round(total_storage / (1024 * 1024), 2)
            },
            "conversations": {
                "total": total_conversations,
                "total_messages": total_messages,
                "avg_messages_per_conversation": round(total_messages / total_conversations if total_conversations > 0 else 0, 1)
            }
        }
        
    except Exception as e:
        logger.error(f"获取管理员仪表板失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取仪表板数据失败"
        )

@router.get("/users", summary="获取用户列表")
async def list_users(
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(20, ge=1, le=100, description="每页数量"),
    tier: Optional[str] = Query(None, description="用户等级过滤"),
    is_active: Optional[bool] = Query(None, description="是否活跃"),
    is_verified: Optional[bool] = Query(None, description="是否已验证"),
    search: Optional[str] = Query(None, description="搜索用户名或邮箱"),
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    获取用户列表（管理员）
    """
    try:
        # 构建查询
        query = db.query(User)
        
        # 过滤条件
        if tier:
            query = query.filter(User.tier == tier)
        
        if is_active is not None:
            query = query.filter(User.is_active == is_active)
        
        if is_verified is not None:
            query = query.filter(User.is_verified == is_verified)
        
        if search:
            query = query.filter(
                (User.username.ilike(f"%{search}%")) |
                (User.email.ilike(f"%{search}%"))
            )
        
        # 计算总数
        total = query.count()
        
        # 分页查询
        offset = (page - 1) * size
        users = query.order_by(desc(User.created_at)).offset(offset).limit(size).all()
        
        # 构建响应
        user_responses = []
        for user in users:
            # 获取用户统计
            kb_count = db.query(KnowledgeBase).filter(KnowledgeBase.owner_id == user.id).count()
            file_count = db.query(File).filter(File.owner_id == user.id).count()
            
            user_responses.append({
                "user_id": user.user_id,
                "username": user.username,
                "email": user.email,
                "full_name": user.full_name,
                "tier": user.tier,
                "is_active": user.is_active,
                "is_verified": user.is_verified,
                "created_at": user.created_at,
                "last_login": user.last_login,
                "knowledge_bases_count": kb_count,
                "files_count": file_count
            })
        
        return {
            "items": user_responses,
            "total": total,
            "page": page,
            "size": size,
            "pages": (total + size - 1) // size
        }
        
    except Exception as e:
        logger.error(f"获取用户列表失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取用户列表失败"
        )

@router.put("/users/{user_id}/status", summary="更新用户状态")
async def update_user_status(
    user_id: str,
    is_active: bool,
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    更新用户状态（激活/禁用）
    """
    try:
        # 查找用户
        user = db.query(User).filter(User.user_id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="用户不存在"
            )
        
        # 不能禁用自己
        if user.id == admin_user.id:
            raise ValidationError("不能修改自己的状态")
        
        # 更新状态
        old_status = user.is_active
        user.is_active = is_active
        user.updated_at = datetime.utcnow()
        
        # 记录审计日志
        audit_log = AuditLog(
            user_id=admin_user.id,
            action="update_user_status",
            resource_type="user",
            resource_id=user.id,
            details={
                "target_user": user.username,
                "old_status": old_status,
                "new_status": is_active
            },
            created_at=datetime.utcnow()
        )
        
        db.add(audit_log)
        db.commit()
        
        logger.info(f"用户状态更新: {user.username} -> {is_active} by {admin_user.username}")
        
        return {"message": f"用户状态已更新为{'激活' if is_active else '禁用'}"}
        
    except Exception as e:
        db.rollback()
        logger.error(f"更新用户状态失败: {str(e)}")
        if isinstance(e, ValidationError):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="更新用户状态失败"
        )

@router.put("/users/{user_id}/tier", summary="更新用户等级")
async def update_user_tier(
    user_id: str,
    new_tier: UserTier,
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    更新用户等级
    """
    try:
        # 查找用户
        user = db.query(User).filter(User.user_id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="用户不存在"
            )
        
        # 更新等级
        old_tier = user.tier
        user.tier = new_tier.value
        user.updated_at = datetime.utcnow()
        
        # 记录审计日志
        audit_log = AuditLog(
            user_id=admin_user.id,
            action="update_user_tier",
            resource_type="user",
            resource_id=user.id,
            details={
                "target_user": user.username,
                "old_tier": old_tier,
                "new_tier": new_tier.value
            },
            created_at=datetime.utcnow()
        )
        
        db.add(audit_log)
        db.commit()
        
        logger.info(f"用户等级更新: {user.username} {old_tier} -> {new_tier.value} by {admin_user.username}")
        
        return {"message": f"用户等级已更新为{new_tier.value}"}
        
    except Exception as e:
        db.rollback()
        logger.error(f"更新用户等级失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="更新用户等级失败"
        )

@router.get("/system/stats", summary="系统统计")
async def get_system_stats(
    days: int = Query(30, ge=1, le=365, description="统计天数"),
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    获取系统统计数据
    """
    try:
        end_date = datetime.utcnow().date()
        start_date = end_date - timedelta(days=days)
        
        # 使用统计
        usage_stats = db.query(UsageStats).filter(
            func.date(UsageStats.date) >= start_date,
            func.date(UsageStats.date) <= end_date
        ).all()
        
        # 聚合统计
        total_api_calls = sum(stat.api_calls for stat in usage_stats)
        total_chat_requests = sum(stat.chat_requests for stat in usage_stats)
        total_search_requests = sum(stat.search_requests for stat in usage_stats)
        total_files_uploaded = sum(stat.files_uploaded for stat in usage_stats)
        total_storage_used = sum(stat.storage_used for stat in usage_stats)
        
        # 按日期分组统计
        daily_stats = {}
        for stat in usage_stats:
            date_str = stat.date.strftime('%Y-%m-%d')
            if date_str not in daily_stats:
                daily_stats[date_str] = {
                    "api_calls": 0,
                    "chat_requests": 0,
                    "search_requests": 0,
                    "files_uploaded": 0
                }
            
            daily_stats[date_str]["api_calls"] += stat.api_calls
            daily_stats[date_str]["chat_requests"] += stat.chat_requests
            daily_stats[date_str]["search_requests"] += stat.search_requests
            daily_stats[date_str]["files_uploaded"] += stat.files_uploaded
        
        # 按用户等级统计
        tier_usage = db.query(
            User.tier,
            func.count(UsageStats.id).label('usage_count'),
            func.sum(UsageStats.api_calls).label('total_api_calls')
        ).join(UsageStats, User.id == UsageStats.user_id).filter(
            func.date(UsageStats.date) >= start_date
        ).group_by(User.tier).all()
        
        return {
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "days": days
            },
            "totals": {
                "api_calls": total_api_calls,
                "chat_requests": total_chat_requests,
                "search_requests": total_search_requests,
                "files_uploaded": total_files_uploaded,
                "storage_used_bytes": total_storage_used
            },
            "daily_stats": daily_stats,
            "tier_usage": [
                {
                    "tier": stat.tier,
                    "usage_count": stat.usage_count,
                    "total_api_calls": stat.total_api_calls or 0
                }
                for stat in tier_usage
            ]
        }
        
    except Exception as e:
        logger.error(f"获取系统统计失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取系统统计失败"
        )

@router.get("/system/config", summary="获取系统配置")
async def get_system_config(
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    获取系统配置
    """
    try:
        configs = db.query(SystemConfig).all()
        
        config_dict = {}
        for config in configs:
            config_dict[config.key] = {
                "value": config.value,
                "description": config.description,
                "updated_at": config.updated_at
            }
        
        return config_dict
        
    except Exception as e:
        logger.error(f"获取系统配置失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取系统配置失败"
        )

@router.put("/system/config/{key}", summary="更新系统配置")
async def update_system_config(
    key: str,
    value: str,
    description: Optional[str] = None,
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    更新系统配置
    """
    try:
        # 查找或创建配置
        config = db.query(SystemConfig).filter(SystemConfig.key == key).first()
        
        if config:
            old_value = config.value
            config.value = value
            if description:
                config.description = description
            config.updated_at = datetime.utcnow()
        else:
            config = SystemConfig(
                key=key,
                value=value,
                description=description or "",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            db.add(config)
            old_value = None
        
        # 记录审计日志
        audit_log = AuditLog(
            user_id=admin_user.id,
            action="update_system_config",
            resource_type="system_config",
            resource_id=config.id if config.id else 0,
            details={
                "key": key,
                "old_value": old_value,
                "new_value": value
            },
            created_at=datetime.utcnow()
        )
        
        db.add(audit_log)
        db.commit()
        
        logger.info(f"系统配置更新: {key} by {admin_user.username}")
        
        return {"message": "系统配置更新成功"}
        
    except Exception as e:
        db.rollback()
        logger.error(f"更新系统配置失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="更新系统配置失败"
        )

@router.get("/audit-logs", summary="获取审计日志")
async def get_audit_logs(
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(50, ge=1, le=100, description="每页数量"),
    action: Optional[str] = Query(None, description="操作类型过滤"),
    user_id: Optional[str] = Query(None, description="用户ID过滤"),
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    获取审计日志
    """
    try:
        # 构建查询
        query = db.query(AuditLog)
        
        if action:
            query = query.filter(AuditLog.action == action)
        
        if user_id:
            user = db.query(User).filter(User.user_id == user_id).first()
            if user:
                query = query.filter(AuditLog.user_id == user.id)
        
        # 计算总数
        total = query.count()
        
        # 分页查询
        offset = (page - 1) * size
        logs = query.order_by(desc(AuditLog.created_at)).offset(offset).limit(size).all()
        
        # 构建响应
        log_responses = []
        for log in logs:
            # 获取用户信息
            user = db.query(User).filter(User.id == log.user_id).first()
            
            log_responses.append({
                "id": log.id,
                "user_id": user.user_id if user else None,
                "username": user.username if user else "Unknown",
                "action": log.action,
                "resource_type": log.resource_type,
                "resource_id": log.resource_id,
                "details": log.details,
                "created_at": log.created_at
            })
        
        return {
            "items": log_responses,
            "total": total,
            "page": page,
            "size": size,
            "pages": (total + size - 1) // size
        }
        
    except Exception as e:
        logger.error(f"获取审计日志失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取审计日志失败"
        )

@router.post("/system/cleanup", summary="系统清理")
async def system_cleanup(
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    执行系统清理任务
    
    - 清理过期的缓存
    - 清理临时文件
    - 清理过期的会话
    """
    try:
        cleanup_results = {
            "cache_cleared": 0,
            "temp_files_removed": 0,
            "expired_sessions_removed": 0
        }
        
        # 清理Redis缓存
        redis_client = get_redis()
        # TODO: 实现缓存清理逻辑
        
        # 清理临时文件
        # TODO: 实现临时文件清理逻辑
        
        # 记录审计日志
        audit_log = AuditLog(
            user_id=admin_user.id,
            action="system_cleanup",
            resource_type="system",
            resource_id=0,
            details=cleanup_results,
            created_at=datetime.utcnow()
        )
        
        db.add(audit_log)
        db.commit()
        
        logger.info(f"系统清理完成 by {admin_user.username}: {cleanup_results}")
        
        return {
            "message": "系统清理完成",
            "results": cleanup_results
        }
        
    except Exception as e:
        logger.error(f"系统清理失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="系统清理失败"
        )