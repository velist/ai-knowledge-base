"""认证API路由"""

from datetime import timedelta
from typing import Dict, Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from loguru import logger

from app.core.database import get_db
from app.core.auth import auth_manager, get_current_user, get_current_active_user
from app.models.database import User
from app.models.schemas import (
    UserCreate, UserResponse, Token, UserLogin,
    PasswordReset, PasswordResetConfirm, EmailVerification
)
from app.core.exceptions import AuthenticationError, ValidationError
from app.services.email_service import send_verification_email, send_password_reset_email

router = APIRouter()

@router.post("/register", response_model=UserResponse, summary="用户注册")
async def register(
    user_data: UserCreate,
    db: Session = Depends(get_db)
):
    """
    用户注册
    
    - **username**: 用户名（3-20字符，字母数字下划线）
    - **email**: 邮箱地址
    - **password**: 密码（至少8字符）
    - **full_name**: 全名（可选）
    """
    try:
        # 检查用户名是否已存在
        existing_user = db.query(User).filter(
            (User.username == user_data.username) | (User.email == user_data.email)
        ).first()
        
        if existing_user:
            if existing_user.username == user_data.username:
                raise ValidationError("用户名已存在")
            else:
                raise ValidationError("邮箱已被注册")
        
        # 创建新用户
        hashed_password = auth_manager.get_password_hash(user_data.password)
        
        db_user = User(
            username=user_data.username,
            email=user_data.email,
            password_hash=hashed_password,
            full_name=user_data.full_name,
            tier="free",
            is_active=True,
            is_verified=False
        )
        
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        
        # 发送验证邮件
        try:
            await send_verification_email(db_user.email, db_user.user_id)
        except Exception as e:
            logger.warning(f"发送验证邮件失败: {str(e)}")
        
        logger.info(f"用户注册成功: {user_data.username}")
        
        return UserResponse(
            user_id=db_user.user_id,
            username=db_user.username,
            email=db_user.email,
            full_name=db_user.full_name,
            tier=db_user.tier,
            is_active=db_user.is_active,
            is_verified=db_user.is_verified,
            created_at=db_user.created_at
        )
        
    except Exception as e:
        db.rollback()
        logger.error(f"用户注册失败: {str(e)}")
        if isinstance(e, (ValidationError, AuthenticationError)):
            raise e
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="注册失败，请稍后重试"
        )

@router.post("/login", response_model=Token, summary="用户登录")
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """
    用户登录
    
    支持用户名或邮箱登录
    """
    try:
        # 用户认证
        user = auth_manager.authenticate_user(
            db=db,
            username=form_data.username,
            password=form_data.password
        )
        
        if not user:
            raise AuthenticationError("用户名或密码错误")
        
        # 创建访问令牌
        access_token_expires = timedelta(minutes=auth_manager.access_token_expire)
        access_token = auth_manager.create_access_token(
            data={"sub": user.user_id},
            expires_delta=access_token_expires
        )
        
        # 创建刷新令牌
        refresh_token = auth_manager.create_refresh_token(
            data={"sub": user.user_id}
        )
        
        logger.info(f"用户登录成功: {user.username}")
        
        return Token(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=auth_manager.access_token_expire * 60
        )
        
    except Exception as e:
        logger.error(f"用户登录失败: {str(e)}")
        if isinstance(e, AuthenticationError):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=str(e),
                headers={"WWW-Authenticate": "Bearer"},
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="登录失败，请稍后重试"
        )

@router.post("/login-json", response_model=Token, summary="JSON格式登录")
async def login_json(
    login_data: UserLogin,
    db: Session = Depends(get_db)
):
    """
    JSON格式用户登录
    
    - **username**: 用户名或邮箱
    - **password**: 密码
    """
    try:
        # 用户认证
        user = auth_manager.authenticate_user(
            db=db,
            username=login_data.username,
            password=login_data.password
        )
        
        if not user:
            raise AuthenticationError("用户名或密码错误")
        
        # 创建访问令牌
        access_token_expires = timedelta(minutes=auth_manager.access_token_expire)
        access_token = auth_manager.create_access_token(
            data={"sub": user.user_id},
            expires_delta=access_token_expires
        )
        
        # 创建刷新令牌
        refresh_token = auth_manager.create_refresh_token(
            data={"sub": user.user_id}
        )
        
        logger.info(f"用户登录成功: {user.username}")
        
        return Token(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=auth_manager.access_token_expire * 60
        )
        
    except Exception as e:
        logger.error(f"用户登录失败: {str(e)}")
        if isinstance(e, AuthenticationError):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=str(e)
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="登录失败，请稍后重试"
        )

@router.post("/refresh", response_model=Token, summary="刷新令牌")
async def refresh_token(
    refresh_token: str,
    db: Session = Depends(get_db)
):
    """
    使用刷新令牌获取新的访问令牌
    """
    try:
        # 验证刷新令牌
        payload = auth_manager.verify_token(refresh_token, token_type="refresh")
        user_id = payload.get("sub")
        
        if user_id is None:
            raise AuthenticationError("无效的刷新令牌")
        
        # 获取用户
        user = db.query(User).filter(User.user_id == user_id).first()
        if not user or not user.is_active:
            raise AuthenticationError("用户不存在或已被禁用")
        
        # 创建新的访问令牌
        access_token_expires = timedelta(minutes=auth_manager.access_token_expire)
        access_token = auth_manager.create_access_token(
            data={"sub": user.user_id},
            expires_delta=access_token_expires
        )
        
        return Token(
            access_token=access_token,
            refresh_token=refresh_token,  # 刷新令牌保持不变
            token_type="bearer",
            expires_in=auth_manager.access_token_expire * 60
        )
        
    except Exception as e:
        logger.error(f"刷新令牌失败: {str(e)}")
        if isinstance(e, AuthenticationError):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=str(e)
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="刷新令牌失败，请稍后重试"
        )

@router.post("/logout", summary="用户登出")
async def logout(
    current_user: User = Depends(get_current_active_user)
):
    """
    用户登出
    
    注意：由于JWT是无状态的，实际的令牌失效需要在客户端处理
    """
    try:
        # TODO: 将令牌加入黑名单（如果需要服务端控制）
        
        logger.info(f"用户登出: {current_user.username}")
        
        return {"message": "登出成功"}
        
    except Exception as e:
        logger.error(f"用户登出失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="登出失败，请稍后重试"
        )

@router.post("/verify-email", summary="验证邮箱")
async def verify_email(
    verification_data: EmailVerification,
    db: Session = Depends(get_db)
):
    """
    验证邮箱地址
    
    - **token**: 邮箱验证令牌
    """
    try:
        # 验证令牌
        payload = auth_manager.verify_token(verification_data.token)
        user_id = payload.get("sub")
        
        if user_id is None:
            raise AuthenticationError("无效的验证令牌")
        
        # 获取用户
        user = db.query(User).filter(User.user_id == user_id).first()
        if not user:
            raise AuthenticationError("用户不存在")
        
        # 更新验证状态
        user.is_verified = True
        db.commit()
        
        logger.info(f"邮箱验证成功: {user.email}")
        
        return {"message": "邮箱验证成功"}
        
    except Exception as e:
        db.rollback()
        logger.error(f"邮箱验证失败: {str(e)}")
        if isinstance(e, AuthenticationError):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="邮箱验证失败，请稍后重试"
        )

@router.post("/resend-verification", summary="重发验证邮件")
async def resend_verification(
    email: str,
    db: Session = Depends(get_db)
):
    """
    重新发送邮箱验证邮件
    """
    try:
        # 查找用户
        user = db.query(User).filter(User.email == email).first()
        if not user:
            raise ValidationError("邮箱地址不存在")
        
        if user.is_verified:
            return {"message": "邮箱已验证，无需重复验证"}
        
        # 发送验证邮件
        await send_verification_email(user.email, user.user_id)
        
        logger.info(f"重发验证邮件: {email}")
        
        return {"message": "验证邮件已发送"}
        
    except Exception as e:
        logger.error(f"重发验证邮件失败: {str(e)}")
        if isinstance(e, ValidationError):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="发送验证邮件失败，请稍后重试"
        )

@router.post("/forgot-password", summary="忘记密码")
async def forgot_password(
    reset_data: PasswordReset,
    db: Session = Depends(get_db)
):
    """
    忘记密码，发送重置邮件
    
    - **email**: 邮箱地址
    """
    try:
        # 查找用户
        user = db.query(User).filter(User.email == reset_data.email).first()
        if not user:
            # 为了安全，即使邮箱不存在也返回成功
            return {"message": "如果邮箱存在，重置链接已发送"}
        
        # 发送密码重置邮件
        await send_password_reset_email(user.email, user.user_id)
        
        logger.info(f"发送密码重置邮件: {reset_data.email}")
        
        return {"message": "如果邮箱存在，重置链接已发送"}
        
    except Exception as e:
        logger.error(f"发送密码重置邮件失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="发送重置邮件失败，请稍后重试"
        )

@router.post("/reset-password", summary="重置密码")
async def reset_password(
    reset_data: PasswordResetConfirm,
    db: Session = Depends(get_db)
):
    """
    重置密码
    
    - **token**: 密码重置令牌
    - **new_password**: 新密码
    """
    try:
        # 验证令牌
        payload = auth_manager.verify_token(reset_data.token)
        user_id = payload.get("sub")
        
        if user_id is None:
            raise AuthenticationError("无效的重置令牌")
        
        # 获取用户
        user = db.query(User).filter(User.user_id == user_id).first()
        if not user:
            raise AuthenticationError("用户不存在")
        
        # 更新密码
        user.password_hash = auth_manager.get_password_hash(reset_data.new_password)
        db.commit()
        
        logger.info(f"密码重置成功: {user.username}")
        
        return {"message": "密码重置成功"}
        
    except Exception as e:
        db.rollback()
        logger.error(f"密码重置失败: {str(e)}")
        if isinstance(e, AuthenticationError):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="密码重置失败，请稍后重试"
        )

@router.get("/me", response_model=UserResponse, summary="获取当前用户信息")
async def get_current_user_info(
    current_user: User = Depends(get_current_active_user)
):
    """
    获取当前登录用户的信息
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

@router.get("/validate", summary="验证令牌")
async def validate_token(
    current_user: User = Depends(get_current_user)
):
    """
    验证当前令牌是否有效
    """
    return {
        "valid": True,
        "user_id": current_user.user_id,
        "username": current_user.username,
        "tier": current_user.tier
    }