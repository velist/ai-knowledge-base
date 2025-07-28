"""自定义异常类模块"""

class BaseCustomException(Exception):
    """基础自定义异常类"""
    
    def __init__(self, message: str, error_code: str = None, details: dict = None):
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.details = details or {}
        super().__init__(self.message)
    
    def __str__(self):
        return f"[{self.error_code}] {self.message}"
    
    def to_dict(self):
        return {
            "error_code": self.error_code,
            "message": self.message,
            "details": self.details
        }

class ValidationError(BaseCustomException):
    """验证错误异常"""
    pass

class AuthenticationError(BaseCustomException):
    """认证错误异常"""
    pass

class AuthorizationError(BaseCustomException):
    """授权错误异常"""
    pass

class AIServiceError(BaseCustomException):
    """AI服务错误异常"""
    pass

class RateLimitError(BaseCustomException):
    """频率限制错误异常"""
    pass

class FileProcessingError(BaseCustomException):
    """文件处理错误异常"""
    pass

class DatabaseError(BaseCustomException):
    """数据库错误异常"""
    pass

class SearchError(BaseCustomException):
    """搜索错误异常"""
    pass

class ConfigurationError(BaseCustomException):
    """配置错误异常"""
    pass

class ExternalServiceError(BaseCustomException):
    """外部服务错误异常"""
    pass

# 导出所有异常类
__all__ = [
    "BaseCustomException",
    "ValidationError",
    "AuthenticationError", 
    "AuthorizationError",
    "AIServiceError",
    "RateLimitError",
    "FileProcessingError",
    "DatabaseError",
    "SearchError",
    "ConfigurationError",
    "ExternalServiceError"
]