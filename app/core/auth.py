"""用户认证和授权模块"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from passlib.context import CryptContext
from jose import JWTError, jwt
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from loguru import logger

from app.config import settings
from app.core.database import get_db
from app.models.database import User, APIKey
from app.models.schemas import UserTier
from app.core.exceptions import AuthenticationError, AuthorizationError

# 密码加密上下文
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# HTTP Bearer认证
security = HTTPBearer(auto_error=False)

class AuthManager:
    """认证管理器"""
    
    def __init__(self):
        self.secret_key = settings.jwt_secret_key
        self.algorithm = settings.jwt_algorithm
        self.access_token_expire = settings.jwt_access_token_expire_minutes
        self.refresh_token_expire = settings.jwt_refresh_token_expire_days
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """验证密码"""
        try:
            return pwd_context.verify(plain_password, hashed_password)
        except Exception as e:
            logger.error(f"密码验证失败: {str(e)}")
            return False
    
    def get_password_hash(self, password: str) -> str:
        """获取密码哈希"""
        return pwd_context.hash(password)
    
    def create_access_token(self, data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        """创建访问令牌"""
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=self.access_token_expire)
        
        to_encode.update({
            "exp": expire,
            "type": "access",
            "iat": datetime.utcnow()
        })
        
        try:
            encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
            return encoded_jwt
        except Exception as e:
            logger.error(f"创建访问令牌失败: {str(e)}")
            raise AuthenticationError("令牌创建失败")
    
    def create_refresh_token(self, data: Dict[str, Any]) -> str:
        """创建刷新令牌"""
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(days=self.refresh_token_expire)
        
        to_encode.update({
            "exp": expire,
            "type": "refresh",
            "iat": datetime.utcnow()
        })
        
        try:
            encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
            return encoded_jwt
        except Exception as e:
            logger.error(f"创建刷新令牌失败: {str(e)}")
            raise AuthenticationError("令牌创建失败")
    
    def verify_token(self, token: str, token_type: str = "access") -> Dict[str, Any]:
        """验证令牌"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            
            # 检查令牌类型
            if payload.get("type") != token_type:
                raise AuthenticationError("令牌类型错误")
            
            # 检查过期时间
            exp = payload.get("exp")
            if exp is None or datetime.utcnow() > datetime.fromtimestamp(exp):
                raise AuthenticationError("令牌已过期")
            
            return payload
            
        except JWTError as e:
            logger.error(f"令牌验证失败: {str(e)}")
            raise AuthenticationError("令牌无效")
        except Exception as e:
            logger.error(f"令牌验证异常: {str(e)}")
            raise AuthenticationError("令牌验证失败")
    
    def authenticate_user(self, db: Session, username: str, password: str) -> Optional[User]:
        """用户认证"""
        try:
            # 查找用户（支持用户名或邮箱登录）
            user = db.query(User).filter(
                (User.username == username) | (User.email == username)
            ).first()
            
            if not user:
                return None
            
            if not self.verify_password(password, user.password_hash):
                return None
            
            if not user.is_active:
                raise AuthenticationError("用户账户已被禁用")
            
            # 更新最后登录时间
            user.last_login = datetime.utcnow()
            db.commit()
            
            return user
            
        except Exception as e:
            logger.error(f"用户认证失败: {str(e)}")
            db.rollback()
            return None
    
    def get_user_by_token(self, db: Session, token: str) -> Optional[User]:
        """通过令牌获取用户"""
        try:
            payload = self.verify_token(token)
            user_id = payload.get("sub")
            
            if user_id is None:
                return None
            
            user = db.query(User).filter(User.user_id == user_id).first()
            
            if not user or not user.is_active:
                return None
            
            return user
            
        except Exception as e:
            logger.error(f"通过令牌获取用户失败: {str(e)}")
            return None
    
    def verify_api_key(self, db: Session, api_key: str) -> Optional[User]:
        """验证API密钥"""
        try:
            # API密钥格式: ak-{prefix}-{hash}
            if not api_key.startswith("ak-"):
                return None
            
            # 计算密钥哈希
            key_hash = self.get_password_hash(api_key)
            
            # 查找API密钥
            api_key_obj = db.query(APIKey).filter(
                APIKey.key_hash == key_hash,
                APIKey.is_active == True
            ).first()
            
            if not api_key_obj:
                return None
            
            # 检查过期时间
            if api_key_obj.expires_at and api_key_obj.expires_at < datetime.utcnow():
                return None
            
            # 获取用户
            user = db.query(User).filter(
                User.id == api_key_obj.user_id,
                User.is_active == True
            ).first()
            
            if not user:
                return None
            
            # 更新使用统计
            api_key_obj.last_used = datetime.utcnow()
            api_key_obj.usage_count += 1
            db.commit()
            
            return user
            
        except Exception as e:
            logger.error(f"API密钥验证失败: {str(e)}")
            db.rollback()
            return None

# 创建认证管理器实例
auth_manager = AuthManager()

# 依赖注入函数
async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """获取当前用户"""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未提供认证凭据",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = credentials.credentials
    
    # 尝试JWT令牌认证
    user = auth_manager.get_user_by_token(db, token)
    
    # 如果JWT认证失败，尝试API密钥认证
    if not user:
        user = auth_manager.verify_api_key(db, token)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的认证凭据",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user

async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """获取当前活跃用户"""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户账户已被禁用"
        )
    return current_user

async def get_current_verified_user(current_user: User = Depends(get_current_active_user)) -> User:
    """获取当前已验证用户"""
    if not current_user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户邮箱未验证"
        )
    return current_user

# 权限检查装饰器
def require_tier(required_tier: UserTier):
    """要求特定用户等级"""
    def decorator(current_user: User = Depends(get_current_active_user)):
        user_tier_value = {
            UserTier.FREE: 0,
            UserTier.PRO: 1,
            UserTier.ENTERPRISE: 2
        }
        
        current_tier_value = user_tier_value.get(UserTier(current_user.tier), 0)
        required_tier_value = user_tier_value.get(required_tier, 0)
        
        if current_tier_value < required_tier_value:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"需要 {required_tier.value} 或更高等级的账户"
            )
        
        return current_user
    
    return decorator

# 权限检查函数
def check_resource_permission(user: User, resource_owner_id: int, allow_public: bool = False) -> bool:
    """检查资源访问权限"""
    # 资源所有者有完全权限
    if user.id == resource_owner_id:
        return True
    
    # 企业用户可以访问公共资源
    if allow_public and user.tier == UserTier.ENTERPRISE.value:
        return True
    
    return False

def require_resource_permission(resource_owner_id: int, allow_public: bool = False):
    """要求资源访问权限"""
    def decorator(current_user: User = Depends(get_current_active_user)):
        if not check_resource_permission(current_user, resource_owner_id, allow_public):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="没有访问此资源的权限"
            )
        return current_user
    
    return decorator

# 可选认证（不强制要求登录）
async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """获取当前用户（可选）"""
    if not credentials:
        return None
    
    try:
        token = credentials.credentials
        
        # 尝试JWT令牌认证
        user = auth_manager.get_user_by_token(db, token)
        
        # 如果JWT认证失败，尝试API密钥认证
        if not user:
            user = auth_manager.verify_api_key(db, token)
        
        return user if user and user.is_active else None
        
    except Exception as e:
        logger.warning(f"可选认证失败: {str(e)}")
        return None

# 导出
__all__ = [
    "AuthManager",
    "auth_manager",
    "get_current_user",
    "get_current_active_user",
    "get_current_verified_user",
    "get_current_user_optional",
    "require_tier",
    "require_resource_permission",
    "check_resource_permission"
]