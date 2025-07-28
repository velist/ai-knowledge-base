import asyncio
import hashlib
import json
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
import httpx
from loguru import logger
import redis.asyncio as redis
from app.config import settings
from app.models.schemas import AIRequest, AIResponse, UserTier
from app.core.exceptions import AIServiceError, RateLimitError

class SiliconFlowProvider:
    """硅基流动AI服务提供商"""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or settings.siliconflow_api_key or "sk-zxujtfllwsoftjelqgzbdwfxmneaoifsvlzvzluntpigkgkr"
        self.base_url = getattr(settings, 'siliconflow_base_url', 'https://api.siliconflow.cn/v1')
        self.model = getattr(settings, 'siliconflow_model', 'deepseek-chat')
        self.timeout = getattr(settings, 'ai_request_timeout', 60.0)
        self.max_retries = getattr(settings, 'ai_max_retries', 3)
        
    async def chat_completion(self, messages: List[Dict], **kwargs) -> Dict:
        """聊天完成API调用"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": kwargs.get("model", self.model),
            "messages": messages,
            "temperature": kwargs.get("temperature", 0.7),
            "max_tokens": kwargs.get("max_tokens", 2000),
            "stream": kwargs.get("stream", False)
        }
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                logger.error(f"SiliconFlow API error: {e.response.status_code} - {e.response.text}")
                raise AIServiceError(f"API调用失败: {e.response.status_code}")
            except Exception as e:
                logger.error(f"SiliconFlow API unexpected error: {str(e)}")
                raise AIServiceError(f"API调用异常: {str(e)}")
    
    async def embedding(self, text: str, **kwargs) -> List[float]:
        """文本嵌入API调用"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": kwargs.get("embedding_model", "BAAI/bge-large-zh-v1.5"),
            "input": text
        }
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/embeddings",
                    headers=headers,
                    json=payload
                )
                response.raise_for_status()
                result = response.json()
                return result["data"][0]["embedding"]
            except Exception as e:
                logger.error(f"SiliconFlow embedding error: {str(e)}")
                raise AIServiceError(f"嵌入向量生成失败: {str(e)}")

class OpenAIProvider:
    """OpenAI服务提供商（备用）"""
    
    def __init__(self):
        self.api_key = settings.openai_api_key
        self.base_url = settings.openai_base_url
        self.model = settings.openai_model
        self.timeout = settings.ai_request_timeout
        
    async def chat_completion(self, messages: List[Dict], **kwargs) -> Dict:
        """OpenAI聊天完成API调用"""
        if not self.api_key:
            raise AIServiceError("OpenAI API密钥未配置")
            
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": kwargs.get("model", self.model),
            "messages": messages,
            "temperature": kwargs.get("temperature", 0.7),
            "max_tokens": kwargs.get("max_tokens", 2000)
        }
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload
                )
                response.raise_for_status()
                return response.json()
            except Exception as e:
                logger.error(f"OpenAI API error: {str(e)}")
                raise AIServiceError(f"OpenAI API调用失败: {str(e)}")

class LocalModelProvider:
    """本地模型提供商（最后兜底）"""
    
    async def chat_completion(self, messages: List[Dict], **kwargs) -> Dict:
        """本地模型简单响应"""
        # 这里可以集成本地模型，目前返回简单响应
        content = "抱歉，当前AI服务暂时不可用，请稍后重试。"
        
        return {
            "choices": [{
                "message": {
                    "role": "assistant",
                    "content": content
                },
                "finish_reason": "stop"
            }],
            "usage": {
                "prompt_tokens": 0,
                "completion_tokens": len(content),
                "total_tokens": len(content)
            }
        }

class AIServiceRouter:
    """AI服务智能路由器"""
    
    def __init__(self):
        self.providers = {
            "siliconflow": SiliconFlowProvider(),
            "openai": OpenAIProvider(),
            "local": LocalModelProvider()
        }
        
    def select_provider(self, user_tier: str, request_type: str, current_usage: Dict) -> str:
        """根据用户等级和请求类型选择服务提供商"""
        if user_tier == "free":
            # 免费用户优先使用硅基流动免费额度
            if current_usage.get("siliconflow_daily", 0) < settings.free_tier_daily_limit:
                return "siliconflow"
            else:
                # 超出免费额度后降级到本地模型
                return "local"
        
        elif user_tier == "pro":
            # 专业版用户根据请求类型智能选择
            if request_type in ["complex_analysis", "creative_writing"]:
                return "openai" if settings.openai_api_key else "siliconflow"
            else:
                return "siliconflow"
        
        elif user_tier == "enterprise":
            # 企业版用户享受最佳服务
            return self.get_best_provider_for_task(request_type)
        
        return "siliconflow"  # 默认使用硅基流动
    
    def get_best_provider_for_task(self, request_type: str) -> str:
        """为特定任务选择最佳提供商"""
        task_provider_map = {
            "content_analysis": "siliconflow",
            "text_generation": "siliconflow",
            "creative_writing": "openai" if settings.openai_api_key else "siliconflow",
            "code_generation": "openai" if settings.openai_api_key else "siliconflow",
            "translation": "siliconflow",
            "summarization": "siliconflow"
        }
        return task_provider_map.get(request_type, "siliconflow")
    
    def get_fallback_provider(self, failed_provider: str) -> Optional[str]:
        """获取降级提供商"""
        fallback_map = {
            "openai": "siliconflow",
            "siliconflow": "local",
            "local": None
        }
        return fallback_map.get(failed_provider)

class UsageManager:
    """用量管理器"""
    
    def __init__(self):
        self.redis_client = None
        self.limits = {
            "free": settings.get_tier_limits("free"),
            "pro": settings.get_tier_limits("pro"),
            "enterprise": settings.get_tier_limits("enterprise")
        }
    
    async def get_redis_client(self):
        """获取Redis客户端"""
        if not self.redis_client:
            self.redis_client = redis.from_url(settings.redis_url)
        return self.redis_client
    
    async def check_usage_limit(self, user_id: str, user_tier: str, request_type: str) -> bool:
        """检查用量限制"""
        redis_client = await self.get_redis_client()
        current_usage = await self.get_current_usage(user_id)
        limits = self.limits[user_tier]
        
        # 检查日请求限制
        daily_limit = limits["daily_requests"]
        if daily_limit > 0:  # -1表示无限制
            if current_usage["daily_requests"] >= daily_limit:
                raise RateLimitError(f"已达到每日请求限制({daily_limit}次)")
        
        return True
    
    async def get_current_usage(self, user_id: str) -> Dict:
        """获取当前用量"""
        redis_client = await self.get_redis_client()
        
        # 获取今日用量
        today = datetime.now().strftime("%Y-%m-%d")
        daily_key = f"usage:{user_id}:daily:{today}"
        
        daily_requests = await redis_client.get(f"{daily_key}:requests") or 0
        daily_tokens = await redis_client.get(f"{daily_key}:tokens") or 0
        
        return {
            "daily_requests": int(daily_requests),
            "daily_tokens": int(daily_tokens),
            "siliconflow_daily": int(await redis_client.get(f"{daily_key}:siliconflow") or 0)
        }
    
    async def update_usage(self, user_id: str, provider: str, tokens_used: int, request_type: str):
        """更新用量统计"""
        redis_client = await self.get_redis_client()
        today = datetime.now().strftime("%Y-%m-%d")
        daily_key = f"usage:{user_id}:daily:{today}"
        
        # 更新请求次数
        await redis_client.incr(f"{daily_key}:requests")
        await redis_client.incr(f"{daily_key}:tokens", tokens_used)
        await redis_client.incr(f"{daily_key}:{provider}")
        
        # 设置过期时间（保留7天）
        await redis_client.expire(f"{daily_key}:requests", 7 * 24 * 3600)
        await redis_client.expire(f"{daily_key}:tokens", 7 * 24 * 3600)
        await redis_client.expire(f"{daily_key}:{provider}", 7 * 24 * 3600)

class AIResponseCache:
    """AI响应缓存"""
    
    def __init__(self):
        self.redis_client = None
        self.cache_ttl = {
            "content_analysis": 3600,  # 1小时
            "classification": 7200,    # 2小时
            "summary": 1800,          # 30分钟
            "qa_response": 300,       # 5分钟
            "translation": 86400      # 24小时
        }
    
    async def get_redis_client(self):
        """获取Redis客户端"""
        if not self.redis_client:
            self.redis_client = redis.from_url(settings.redis_url)
        return self.redis_client
    
    def generate_cache_key(self, request_data: Dict, request_type: str) -> str:
        """生成缓存键"""
        # 创建请求数据的哈希
        request_str = json.dumps(request_data, sort_keys=True, ensure_ascii=False)
        request_hash = hashlib.md5(request_str.encode()).hexdigest()
        return f"ai_cache:{request_type}:{request_hash}"
    
    async def get_cached_response(self, request_data: Dict, request_type: str) -> Optional[str]:
        """获取缓存的响应"""
        redis_client = await self.get_redis_client()
        cache_key = self.generate_cache_key(request_data, request_type)
        
        try:
            cached_response = await redis_client.get(cache_key)
            if cached_response:
                logger.info(f"Cache hit for {request_type}: {cache_key}")
                return json.loads(cached_response)
        except Exception as e:
            logger.warning(f"Cache get error: {str(e)}")
        
        return None
    
    async def cache_response(self, request_data: Dict, request_type: str, response: Dict):
        """缓存响应"""
        redis_client = await self.get_redis_client()
        cache_key = self.generate_cache_key(request_data, request_type)
        ttl = self.cache_ttl.get(request_type, 300)
        
        try:
            await redis_client.setex(
                cache_key, 
                ttl, 
                json.dumps(response, ensure_ascii=False)
            )
            logger.info(f"Cached response for {request_type}: {cache_key}")
        except Exception as e:
            logger.warning(f"Cache set error: {str(e)}")

class AIServiceManager:
    """AI服务管理器"""
    
    def __init__(self):
        self.router = AIServiceRouter()
        self.usage_manager = UsageManager()
        self.cache = AIResponseCache()
        
    async def process_request(self, request: AIRequest) -> AIResponse:
        """处理AI请求"""
        try:
            # 检查用量限制
            await self.usage_manager.check_usage_limit(
                request.user_id, 
                request.user_tier, 
                request.request_type
            )
            
            # 检查缓存
            cached_response = await self.cache.get_cached_response(
                request.dict(), 
                request.request_type
            )
            if cached_response:
                return AIResponse(**cached_response)
            
            # 选择服务提供商
            current_usage = await self.usage_manager.get_current_usage(request.user_id)
            provider_name = self.router.select_provider(
                request.user_tier, 
                request.request_type, 
                current_usage
            )
            
            # 调用AI服务
            provider = self.router.providers[provider_name]
            response = await self._call_provider(provider, request)
            
            # 更新用量统计
            tokens_used = response.get("usage", {}).get("total_tokens", 0)
            await self.usage_manager.update_usage(
                request.user_id, 
                provider_name, 
                tokens_used, 
                request.request_type
            )
            
            # 缓存响应
            ai_response = AIResponse(
                content=response["choices"][0]["message"]["content"],
                provider=provider_name,
                tokens_used=tokens_used,
                request_type=request.request_type
            )
            
            await self.cache.cache_response(
                request.dict(), 
                request.request_type, 
                ai_response.dict()
            )
            
            return ai_response
            
        except RateLimitError:
            raise
        except AIServiceError:
            raise
        except Exception as e:
            logger.error(f"AI service error: {str(e)}")
            # 尝试降级处理
            return await self._fallback_processing(request, str(e))
    
    async def _call_provider(self, provider, request: AIRequest) -> Dict:
        """调用AI服务提供商"""
        messages = [
            {"role": "system", "content": request.system_prompt or "你是一个智能助手。"},
            {"role": "user", "content": request.content}
        ]
        
        return await provider.chat_completion(
            messages=messages,
            temperature=request.temperature,
            max_tokens=request.max_tokens
        )
    
    async def _fallback_processing(self, request: AIRequest, error_msg: str) -> AIResponse:
        """降级处理"""
        # 尝试使用本地模型
        try:
            local_provider = self.router.providers["local"]
            response = await self._call_provider(local_provider, request)
            
            return AIResponse(
                content=response["choices"][0]["message"]["content"],
                provider="local",
                tokens_used=0,
                request_type=request.request_type,
                error=f"主要服务不可用，使用降级服务: {error_msg}"
            )
        except Exception as e:
            logger.error(f"Fallback processing failed: {str(e)}")
            return AIResponse(
                content="抱歉，AI服务暂时不可用，请稍后重试。",
                provider="none",
                tokens_used=0,
                request_type=request.request_type,
                error=f"所有服务不可用: {error_msg}"
            )

# 创建全局AI服务管理器实例
ai_service_manager = AIServiceManager()

# 导出
__all__ = [
    "AIServiceManager", 
    "SiliconFlowProvider", 
    "OpenAIProvider", 
    "ai_service_manager"
]