"""搜索服务模块"""

import asyncio
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import json
from concurrent.futures import ThreadPoolExecutor

from sqlalchemy.orm import Session
from loguru import logger
import jieba
from elasticsearch import AsyncElasticsearch
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue

from app.config import settings
from app.models.database import File, KnowledgeBase, User
from app.models.schemas import SearchRequest, SearchResponse, SearchResult
from app.core.exceptions import SearchError, ExternalServiceError
from app.services.ai_service import AIServiceManager
from app.core.redis_client import get_redis

class ElasticsearchService:
    """Elasticsearch搜索服务"""
    
    def __init__(self):
        self.client: Optional[AsyncElasticsearch] = None
        self.index_name = "knowledge_base"
    
    async def connect(self):
        """连接Elasticsearch"""
        try:
            self.client = AsyncElasticsearch(
                [settings.elasticsearch_url],
                timeout=30,
                max_retries=3,
                retry_on_timeout=True
            )
            
            # 测试连接
            await self.client.ping()
            
            # 创建索引
            await self._create_index()
            
            logger.info("✅ Elasticsearch连接成功")
            
        except Exception as e:
            logger.error(f"❌ Elasticsearch连接失败: {str(e)}")
            raise ExternalServiceError(f"Elasticsearch连接失败: {str(e)}")
    
    async def disconnect(self):
        """断开连接"""
        if self.client:
            await self.client.close()
    
    async def _create_index(self):
        """创建索引"""
        try:
            # 检查索引是否存在
            if await self.client.indices.exists(index=self.index_name):
                return
            
            # 创建索引映射
            mapping = {
                "mappings": {
                    "properties": {
                        "file_id": {"type": "keyword"},
                        "knowledge_base_id": {"type": "integer"},
                        "owner_id": {"type": "integer"},
                        "title": {
                            "type": "text",
                            "analyzer": "ik_max_word",
                            "search_analyzer": "ik_smart"
                        },
                        "content": {
                            "type": "text",
                            "analyzer": "ik_max_word",
                            "search_analyzer": "ik_smart"
                        },
                        "file_type": {"type": "keyword"},
                        "language": {"type": "keyword"},
                        "tags": {"type": "keyword"},
                        "created_at": {"type": "date"},
                        "updated_at": {"type": "date"}
                    }
                }
            }
            
            await self.client.indices.create(index=self.index_name, body=mapping)
            logger.info(f"创建Elasticsearch索引: {self.index_name}")
            
        except Exception as e:
            logger.error(f"创建Elasticsearch索引失败: {str(e)}")
            raise
    
    async def index_document(self, doc_id: str, document: Dict[str, Any]):
        """索引文档"""
        try:
            await self.client.index(
                index=self.index_name,
                id=doc_id,
                body=document
            )
            logger.debug(f"文档索引成功: {doc_id}")
            
        except Exception as e:
            logger.error(f"文档索引失败: {str(e)}")
            raise SearchError(f"文档索引失败: {str(e)}")
    
    async def search_documents(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        size: int = 10,
        from_: int = 0
    ) -> Dict[str, Any]:
        """搜索文档"""
        try:
            # 构建搜索查询
            search_body = {
                "query": {
                    "bool": {
                        "must": [
                            {
                                "multi_match": {
                                    "query": query,
                                    "fields": ["title^2", "content"],
                                    "type": "best_fields",
                                    "fuzziness": "AUTO"
                                }
                            }
                        ]
                    }
                },
                "highlight": {
                    "fields": {
                        "title": {},
                        "content": {
                            "fragment_size": 150,
                            "number_of_fragments": 3
                        }
                    }
                },
                "size": size,
                "from": from_,
                "sort": [{"_score": {"order": "desc"}}]
            }
            
            # 添加过滤条件
            if filters:
                filter_conditions = []
                
                if "knowledge_base_id" in filters:
                    filter_conditions.append({
                        "term": {"knowledge_base_id": filters["knowledge_base_id"]}
                    })
                
                if "owner_id" in filters:
                    filter_conditions.append({
                        "term": {"owner_id": filters["owner_id"]}
                    })
                
                if "file_type" in filters:
                    filter_conditions.append({
                        "term": {"file_type": filters["file_type"]}
                    })
                
                if "language" in filters:
                    filter_conditions.append({
                        "term": {"language": filters["language"]}
                    })
                
                if filter_conditions:
                    search_body["query"]["bool"]["filter"] = filter_conditions
            
            # 执行搜索
            response = await self.client.search(
                index=self.index_name,
                body=search_body
            )
            
            return response
            
        except Exception as e:
            logger.error(f"Elasticsearch搜索失败: {str(e)}")
            raise SearchError(f"搜索失败: {str(e)}")
    
    async def delete_document(self, doc_id: str):
        """删除文档"""
        try:
            await self.client.delete(index=self.index_name, id=doc_id)
            logger.debug(f"文档删除成功: {doc_id}")
            
        except Exception as e:
            logger.error(f"文档删除失败: {str(e)}")
            raise SearchError(f"文档删除失败: {str(e)}")

class VectorSearchService:
    """向量搜索服务"""
    
    def __init__(self):
        self.client: Optional[QdrantClient] = None
        self.collection_name = "knowledge_vectors"
        self.vector_size = 1536  # OpenAI embedding维度
    
    async def connect(self):
        """连接Qdrant"""
        try:
            self.client = QdrantClient(
                url=settings.qdrant_url,
                timeout=30
            )
            
            # 创建集合
            await self._create_collection()
            
            logger.info("✅ Qdrant连接成功")
            
        except Exception as e:
            logger.error(f"❌ Qdrant连接失败: {str(e)}")
            raise ExternalServiceError(f"Qdrant连接失败: {str(e)}")
    
    async def _create_collection(self):
        """创建向量集合"""
        try:
            # 检查集合是否存在
            collections = self.client.get_collections()
            collection_names = [col.name for col in collections.collections]
            
            if self.collection_name in collection_names:
                return
            
            # 创建集合
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=self.vector_size,
                    distance=Distance.COSINE
                )
            )
            
            logger.info(f"创建Qdrant集合: {self.collection_name}")
            
        except Exception as e:
            logger.error(f"创建Qdrant集合失败: {str(e)}")
            raise
    
    async def add_vectors(
        self,
        vectors: List[Dict[str, Any]]
    ):
        """添加向量"""
        try:
            points = []
            for i, vector_data in enumerate(vectors):
                point = PointStruct(
                    id=vector_data.get("id", i),
                    vector=vector_data["embedding"],
                    payload={
                        "file_id": vector_data["file_id"],
                        "text": vector_data["text"],
                        "knowledge_base_id": vector_data.get("knowledge_base_id"),
                        "owner_id": vector_data.get("owner_id"),
                        "created_at": datetime.utcnow().isoformat()
                    }
                )
                points.append(point)
            
            self.client.upsert(
                collection_name=self.collection_name,
                points=points
            )
            
            logger.debug(f"向量添加成功: {len(points)} 个")
            
        except Exception as e:
            logger.error(f"向量添加失败: {str(e)}")
            raise SearchError(f"向量添加失败: {str(e)}")
    
    async def search_vectors(
        self,
        query_vector: List[float],
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 10,
        score_threshold: float = 0.7
    ) -> List[Dict[str, Any]]:
        """搜索相似向量"""
        try:
            # 构建过滤条件
            search_filter = None
            if filters:
                conditions = []
                
                if "knowledge_base_id" in filters:
                    conditions.append(
                        FieldCondition(
                            key="knowledge_base_id",
                            match=MatchValue(value=filters["knowledge_base_id"])
                        )
                    )
                
                if "owner_id" in filters:
                    conditions.append(
                        FieldCondition(
                            key="owner_id",
                            match=MatchValue(value=filters["owner_id"])
                        )
                    )
                
                if "file_id" in filters:
                    conditions.append(
                        FieldCondition(
                            key="file_id",
                            match=MatchValue(value=filters["file_id"])
                        )
                    )
                
                if conditions:
                    search_filter = Filter(must=conditions)
            
            # 执行搜索
            results = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_vector,
                query_filter=search_filter,
                limit=limit,
                score_threshold=score_threshold
            )
            
            # 格式化结果
            formatted_results = []
            for result in results:
                formatted_results.append({
                    "id": result.id,
                    "score": result.score,
                    "text": result.payload.get("text", ""),
                    "file_id": result.payload.get("file_id", ""),
                    "knowledge_base_id": result.payload.get("knowledge_base_id"),
                    "owner_id": result.payload.get("owner_id")
                })
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"向量搜索失败: {str(e)}")
            raise SearchError(f"向量搜索失败: {str(e)}")
    
    async def delete_vectors(self, file_id: str):
        """删除文件相关的所有向量"""
        try:
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=Filter(
                    must=[
                        FieldCondition(
                            key="file_id",
                            match=MatchValue(value=file_id)
                        )
                    ]
                )
            )
            
            logger.debug(f"向量删除成功: {file_id}")
            
        except Exception as e:
            logger.error(f"向量删除失败: {str(e)}")
            raise SearchError(f"向量删除失败: {str(e)}")

class SearchService:
    """搜索服务"""
    
    def __init__(self):
        self.es_service = ElasticsearchService()
        self.vector_service = VectorSearchService()
        self.ai_service = AIServiceManager()
    
    async def initialize(self):
        """初始化搜索服务"""
        await self.es_service.connect()
        await self.vector_service.connect()
    
    async def close(self):
        """关闭搜索服务"""
        await self.es_service.disconnect()
    
    async def index_file_content(
        self,
        file_id: str,
        content: str,
        metadata: Dict[str, Any]
    ):
        """索引文件内容"""
        try:
            # 准备文档数据
            document = {
                "file_id": file_id,
                "knowledge_base_id": metadata.get("knowledge_base_id"),
                "owner_id": metadata.get("owner_id"),
                "title": metadata.get("title", ""),
                "content": content,
                "file_type": metadata.get("file_type", ""),
                "language": metadata.get("language", ""),
                "tags": metadata.get("tags", []),
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            }
            
            # 索引到Elasticsearch
            await self.es_service.index_document(file_id, document)
            
            # 生成向量嵌入并索引到Qdrant
            await self._index_vectors(file_id, content, metadata)
            
            logger.info(f"文件内容索引成功: {file_id}")
            
        except Exception as e:
            logger.error(f"文件内容索引失败: {str(e)}")
            raise
    
    async def _index_vectors(
        self,
        file_id: str,
        content: str,
        metadata: Dict[str, Any]
    ):
        """生成并索引向量"""
        try:
            # 文本分块
            chunks = self._split_text(content)
            
            # 生成向量嵌入
            vectors = []
            for i, chunk in enumerate(chunks):
                try:
                    embedding = await self.ai_service.get_embedding(chunk)
                    vectors.append({
                        "id": f"{file_id}_{i}",
                        "file_id": file_id,
                        "text": chunk,
                        "embedding": embedding,
                        "knowledge_base_id": metadata.get("knowledge_base_id"),
                        "owner_id": metadata.get("owner_id")
                    })
                except Exception as e:
                    logger.warning(f"生成嵌入向量失败: {str(e)}")
                    continue
            
            # 添加到向量数据库
            if vectors:
                await self.vector_service.add_vectors(vectors)
                logger.debug(f"为文件 {file_id} 生成了 {len(vectors)} 个向量")
            
        except Exception as e:
            logger.error(f"向量索引失败: {str(e)}")
            raise
    
    def _split_text(self, text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
        """文本分块"""
        if len(text) <= chunk_size:
            return [text]
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + chunk_size
            
            # 如果不是最后一块，尝试在句号处分割
            if end < len(text):
                # 寻找最近的句号
                last_period = text.rfind('。', start, end)
                if last_period > start:
                    end = last_period + 1
                else:
                    # 寻找最近的空格
                    last_space = text.rfind(' ', start, end)
                    if last_space > start:
                        end = last_space
            
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            
            start = end - overlap if end < len(text) else end
        
        return chunks
    
    async def search(
        self,
        request: SearchRequest,
        user: User
    ) -> SearchResponse:
        """执行搜索"""
        try:
            # 检查缓存
            cache_key = f"search:{user.id}:{hash(request.query)}:{request.knowledge_base_id}"
            redis_client = await get_redis()
            cached_result = await redis_client.get(cache_key)
            
            if cached_result and not request.use_ai:
                logger.debug(f"返回缓存的搜索结果: {cache_key}")
                return SearchResponse.parse_raw(cached_result)
            
            # 准备过滤条件
            filters = {
                "owner_id": user.id
            }
            
            if request.knowledge_base_id:
                filters["knowledge_base_id"] = request.knowledge_base_id
            
            if request.file_type:
                filters["file_type"] = request.file_type
            
            # 执行混合搜索
            results = await self._hybrid_search(
                query=request.query,
                filters=filters,
                limit=request.limit,
                use_vector=request.use_vector,
                use_ai=request.use_ai
            )
            
            # 构建响应
            response = SearchResponse(
                query=request.query,
                total=len(results),
                results=results,
                search_time=0,  # TODO: 计算搜索时间
                use_ai=request.use_ai
            )
            
            # 缓存结果
            await redis_client.set(
                cache_key,
                response.json(),
                expire=settings.cache_ttl
            )
            
            return response
            
        except Exception as e:
            logger.error(f"搜索失败: {str(e)}")
            raise SearchError(f"搜索失败: {str(e)}")
    
    async def _hybrid_search(
        self,
        query: str,
        filters: Dict[str, Any],
        limit: int = 10,
        use_vector: bool = True,
        use_ai: bool = False
    ) -> List[SearchResult]:
        """混合搜索（关键词 + 向量）"""
        results = []
        
        try:
            # 1. 关键词搜索
            es_results = await self.es_service.search_documents(
                query=query,
                filters=filters,
                size=limit
            )
            
            # 处理Elasticsearch结果
            for hit in es_results["hits"]["hits"]:
                source = hit["_source"]
                highlight = hit.get("highlight", {})
                
                result = SearchResult(
                    file_id=source["file_id"],
                    title=source.get("title", ""),
                    content=source.get("content", "")[:500],
                    highlight=highlight.get("content", []),
                    score=hit["_score"],
                    search_type="keyword",
                    file_type=source.get("file_type", ""),
                    created_at=source.get("created_at")
                )
                results.append(result)
            
            # 2. 向量搜索
            if use_vector:
                try:
                    # 生成查询向量
                    query_embedding = await self.ai_service.get_embedding(query)
                    
                    # 向量搜索
                    vector_results = await self.vector_service.search_vectors(
                        query_vector=query_embedding,
                        filters=filters,
                        limit=limit,
                        score_threshold=0.7
                    )
                    
                    # 处理向量搜索结果
                    for vector_result in vector_results:
                        # 避免重复
                        if any(r.file_id == vector_result["file_id"] for r in results):
                            continue
                        
                        result = SearchResult(
                            file_id=vector_result["file_id"],
                            title="",  # 向量搜索没有标题
                            content=vector_result["text"],
                            highlight=[],
                            score=vector_result["score"],
                            search_type="vector",
                            file_type="",
                            created_at=None
                        )
                        results.append(result)
                
                except Exception as e:
                    logger.warning(f"向量搜索失败: {str(e)}")
            
            # 3. AI增强搜索
            if use_ai and results:
                try:
                    results = await self._ai_enhance_results(query, results)
                except Exception as e:
                    logger.warning(f"AI增强搜索失败: {str(e)}")
            
            # 按分数排序并限制结果数量
            results.sort(key=lambda x: x.score, reverse=True)
            return results[:limit]
            
        except Exception as e:
            logger.error(f"混合搜索失败: {str(e)}")
            raise
    
    async def _ai_enhance_results(
        self,
        query: str,
        results: List[SearchResult]
    ) -> List[SearchResult]:
        """AI增强搜索结果"""
        try:
            # 构建上下文
            context = "\n\n".join([f"文档{i+1}: {r.content[:300]}" for i, r in enumerate(results[:5])])
            
            # AI重新排序和总结
            prompt = f"""
            用户查询: {query}
            
            相关文档:
            {context}
            
            请根据用户查询的相关性，重新评估这些文档的重要性，并为每个文档生成一个简短的相关性说明。
            返回JSON格式，包含每个文档的新分数(0-1)和说明。
            """
            
            ai_response = await self.ai_service.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                user_tier="pro",  # AI增强功能需要Pro以上
                temperature=0.3
            )
            
            # 解析AI响应并更新结果
            # TODO: 实现AI响应解析和结果更新
            
            return results
            
        except Exception as e:
            logger.error(f"AI增强失败: {str(e)}")
            return results
    
    async def delete_file_index(self, file_id: str):
        """删除文件索引"""
        try:
            # 删除Elasticsearch索引
            await self.es_service.delete_document(file_id)
            
            # 删除向量索引
            await self.vector_service.delete_vectors(file_id)
            
            logger.info(f"文件索引删除成功: {file_id}")
            
        except Exception as e:
            logger.error(f"文件索引删除失败: {str(e)}")
            raise
    
    async def get_search_suggestions(
        self,
        query: str,
        user: User,
        limit: int = 5
    ) -> List[str]:
        """获取搜索建议"""
        try:
            # 基于历史搜索和文档内容生成建议
            # TODO: 实现搜索建议逻辑
            
            suggestions = [
                f"{query} 相关内容",
                f"{query} 详细说明",
                f"{query} 实例",
                f"{query} 应用",
                f"{query} 总结"
            ]
            
            return suggestions[:limit]
            
        except Exception as e:
            logger.error(f"获取搜索建议失败: {str(e)}")
            return []

# 创建搜索服务实例
search_service = SearchService()

# 导出
__all__ = [
    "SearchService",
    "search_service"
]