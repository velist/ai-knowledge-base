"""Redis客户端连接模块"""

import redis.asyncio as redis
from typing import Optional, Any, Dict, List
from loguru import logger
import json
from datetime import timedelta

from app.config import settings
from app.core.exceptions import DatabaseError

class RedisClient:
    """Redis客户端封装类"""
    
    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
        self.connection_pool: Optional[redis.ConnectionPool] = None
    
    async def connect(self):
        """连接Redis"""
        try:
            # 创建连接池
            self.connection_pool = redis.ConnectionPool.from_url(
                settings.redis_url,
                max_connections=20,
                retry_on_timeout=True,
                socket_keepalive=True,
                socket_keepalive_options={}
            )
            
            # 创建Redis客户端
            self.redis_client = redis.Redis(
                connection_pool=self.connection_pool,
                decode_responses=True
            )
            
            # 测试连接
            await self.redis_client.ping()
            logger.info("✅ Redis连接成功")
            
        except Exception as e:
            logger.error(f"❌ Redis连接失败: {str(e)}")
            raise DatabaseError(f"Redis连接失败: {str(e)}")
    
    async def disconnect(self):
        """断开Redis连接"""
        try:
            if self.redis_client:
                await self.redis_client.close()
            if self.connection_pool:
                await self.connection_pool.disconnect()
            logger.info("✅ Redis连接已关闭")
        except Exception as e:
            logger.error(f"❌ 关闭Redis连接失败: {str(e)}")
    
    async def get_client(self) -> redis.Redis:
        """获取Redis客户端"""
        if not self.redis_client:
            await self.connect()
        return self.redis_client
    
    async def set(self, key: str, value: Any, expire: Optional[int] = None) -> bool:
        """设置键值"""
        try:
            client = await self.get_client()
            
            # 序列化值
            if isinstance(value, (dict, list)):
                value = json.dumps(value, ensure_ascii=False)
            elif not isinstance(value, str):
                value = str(value)
            
            if expire:
                return await client.setex(key, expire, value)
            else:
                return await client.set(key, value)
                
        except Exception as e:
            logger.error(f"Redis set error: {str(e)}")
            return False
    
    async def get(self, key: str, default: Any = None) -> Any:
        """获取键值"""
        try:
            client = await self.get_client()
            value = await client.get(key)
            
            if value is None:
                return default
            
            # 尝试反序列化JSON
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return value
                
        except Exception as e:
            logger.error(f"Redis get error: {str(e)}")
            return default
    
    async def delete(self, *keys: str) -> int:
        """删除键"""
        try:
            client = await self.get_client()
            return await client.delete(*keys)
        except Exception as e:
            logger.error(f"Redis delete error: {str(e)}")
            return 0
    
    async def exists(self, key: str) -> bool:
        """检查键是否存在"""
        try:
            client = await self.get_client()
            return await client.exists(key) > 0
        except Exception as e:
            logger.error(f"Redis exists error: {str(e)}")
            return False
    
    async def expire(self, key: str, seconds: int) -> bool:
        """设置键过期时间"""
        try:
            client = await self.get_client()
            return await client.expire(key, seconds)
        except Exception as e:
            logger.error(f"Redis expire error: {str(e)}")
            return False
    
    async def ttl(self, key: str) -> int:
        """获取键的剩余生存时间"""
        try:
            client = await self.get_client()
            return await client.ttl(key)
        except Exception as e:
            logger.error(f"Redis ttl error: {str(e)}")
            return -1
    
    async def incr(self, key: str, amount: int = 1) -> int:
        """递增键值"""
        try:
            client = await self.get_client()
            return await client.incrby(key, amount)
        except Exception as e:
            logger.error(f"Redis incr error: {str(e)}")
            return 0
    
    async def decr(self, key: str, amount: int = 1) -> int:
        """递减键值"""
        try:
            client = await self.get_client()
            return await client.decrby(key, amount)
        except Exception as e:
            logger.error(f"Redis decr error: {str(e)}")
            return 0
    
    async def hset(self, name: str, mapping: Dict[str, Any]) -> int:
        """设置哈希表"""
        try:
            client = await self.get_client()
            # 序列化值
            serialized_mapping = {}
            for k, v in mapping.items():
                if isinstance(v, (dict, list)):
                    serialized_mapping[k] = json.dumps(v, ensure_ascii=False)
                else:
                    serialized_mapping[k] = str(v)
            
            return await client.hset(name, mapping=serialized_mapping)
        except Exception as e:
            logger.error(f"Redis hset error: {str(e)}")
            return 0
    
    async def hget(self, name: str, key: str, default: Any = None) -> Any:
        """获取哈希表字段值"""
        try:
            client = await self.get_client()
            value = await client.hget(name, key)
            
            if value is None:
                return default
            
            # 尝试反序列化JSON
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return value
                
        except Exception as e:
            logger.error(f"Redis hget error: {str(e)}")
            return default
    
    async def hgetall(self, name: str) -> Dict[str, Any]:
        """获取哈希表所有字段"""
        try:
            client = await self.get_client()
            data = await client.hgetall(name)
            
            # 反序列化值
            result = {}
            for k, v in data.items():
                try:
                    result[k] = json.loads(v)
                except (json.JSONDecodeError, TypeError):
                    result[k] = v
            
            return result
            
        except Exception as e:
            logger.error(f"Redis hgetall error: {str(e)}")
            return {}
    
    async def hdel(self, name: str, *keys: str) -> int:
        """删除哈希表字段"""
        try:
            client = await self.get_client()
            return await client.hdel(name, *keys)
        except Exception as e:
            logger.error(f"Redis hdel error: {str(e)}")
            return 0
    
    async def lpush(self, name: str, *values: Any) -> int:
        """向列表左侧推入元素"""
        try:
            client = await self.get_client()
            # 序列化值
            serialized_values = []
            for v in values:
                if isinstance(v, (dict, list)):
                    serialized_values.append(json.dumps(v, ensure_ascii=False))
                else:
                    serialized_values.append(str(v))
            
            return await client.lpush(name, *serialized_values)
        except Exception as e:
            logger.error(f"Redis lpush error: {str(e)}")
            return 0
    
    async def rpop(self, name: str, default: Any = None) -> Any:
        """从列表右侧弹出元素"""
        try:
            client = await self.get_client()
            value = await client.rpop(name)
            
            if value is None:
                return default
            
            # 尝试反序列化JSON
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return value
                
        except Exception as e:
            logger.error(f"Redis rpop error: {str(e)}")
            return default
    
    async def llen(self, name: str) -> int:
        """获取列表长度"""
        try:
            client = await self.get_client()
            return await client.llen(name)
        except Exception as e:
            logger.error(f"Redis llen error: {str(e)}")
            return 0
    
    async def sadd(self, name: str, *values: Any) -> int:
        """向集合添加元素"""
        try:
            client = await self.get_client()
            # 序列化值
            serialized_values = []
            for v in values:
                if isinstance(v, (dict, list)):
                    serialized_values.append(json.dumps(v, ensure_ascii=False))
                else:
                    serialized_values.append(str(v))
            
            return await client.sadd(name, *serialized_values)
        except Exception as e:
            logger.error(f"Redis sadd error: {str(e)}")
            return 0
    
    async def smembers(self, name: str) -> List[Any]:
        """获取集合所有成员"""
        try:
            client = await self.get_client()
            members = await client.smembers(name)
            
            # 反序列化值
            result = []
            for member in members:
                try:
                    result.append(json.loads(member))
                except (json.JSONDecodeError, TypeError):
                    result.append(member)
            
            return result
            
        except Exception as e:
            logger.error(f"Redis smembers error: {str(e)}")
            return []
    
    async def srem(self, name: str, *values: Any) -> int:
        """从集合移除元素"""
        try:
            client = await self.get_client()
            # 序列化值
            serialized_values = []
            for v in values:
                if isinstance(v, (dict, list)):
                    serialized_values.append(json.dumps(v, ensure_ascii=False))
                else:
                    serialized_values.append(str(v))
            
            return await client.srem(name, *serialized_values)
        except Exception as e:
            logger.error(f"Redis srem error: {str(e)}")
            return 0
    
    async def keys(self, pattern: str = "*") -> List[str]:
        """获取匹配模式的所有键"""
        try:
            client = await self.get_client()
            return await client.keys(pattern)
        except Exception as e:
            logger.error(f"Redis keys error: {str(e)}")
            return []
    
    async def flushdb(self) -> bool:
        """清空当前数据库"""
        try:
            client = await self.get_client()
            return await client.flushdb()
        except Exception as e:
            logger.error(f"Redis flushdb error: {str(e)}")
            return False

# 创建全局Redis客户端实例
redis_client = RedisClient()

async def init_redis():
    """初始化Redis连接"""
    await redis_client.connect()

async def get_redis() -> RedisClient:
    """获取Redis客户端"""
    return redis_client

async def close_redis():
    """关闭Redis连接"""
    await redis_client.disconnect()

# 导出
__all__ = [
    "RedisClient",
    "redis_client",
    "init_redis",
    "get_redis",
    "close_redis"
]