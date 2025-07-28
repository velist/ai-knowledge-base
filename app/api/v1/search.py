"""搜索API路由"""

from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from loguru import logger

from app.core.database import get_db
from app.core.auth import get_current_active_user
from app.models.database import User, KnowledgeBase, File
from app.models.schemas import (
    SearchRequest, SearchResponse, SearchResult,
    UserTier, APIResponse
)
from app.core.exceptions import ValidationError, ResourceNotFoundError, RateLimitError
from app.services.search_service import SearchService
from app.services.ai_service import AIServiceManager
from app.core.redis_client import get_redis

router = APIRouter()
search_service = SearchService()
ai_service = AIServiceManager()

@router.post("/", response_model=SearchResponse, summary="搜索知识库")
async def search_knowledge_base(
    search_request: SearchRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    在知识库中搜索内容
    
    - **query**: 搜索查询
    - **knowledge_base_ids**: 要搜索的知识库ID列表（可选）
    - **search_type**: 搜索类型（keyword/semantic/hybrid）
    - **limit**: 返回结果数量限制
    - **filters**: 搜索过滤条件
    """
    try:
        # 验证搜索查询
        if not search_request.query or len(search_request.query.strip()) < 2:
            raise ValidationError("搜索查询至少需要2个字符")
        
        # 检查用户搜索限制
        redis_client = get_redis()
        search_key = f"search_limit:{current_user.id}:{datetime.utcnow().date()}"
        
        # 获取今日搜索次数
        today_searches = await redis_client.get(search_key) or 0
        today_searches = int(today_searches)
        
        # 检查搜索限制
        search_limits = {
            UserTier.FREE: 50,
            UserTier.PRO: 500,
            UserTier.ENTERPRISE: 5000
        }
        
        user_tier = UserTier(current_user.tier)
        max_searches = search_limits.get(user_tier, 50)
        
        if today_searches >= max_searches:
            raise RateLimitError(f"今日搜索次数已达上限（{max_searches}次）")
        
        # 验证知识库权限
        accessible_kb_ids = []
        if search_request.knowledge_base_ids:
            for kb_id in search_request.knowledge_base_ids:
                kb = db.query(KnowledgeBase).filter(KnowledgeBase.kb_id == kb_id).first()
                if not kb:
                    continue
                
                # 检查访问权限（自己的或公开的）
                if kb.owner_id == current_user.id or kb.is_public:
                    accessible_kb_ids.append(kb.id)
        else:
            # 如果没有指定知识库，搜索用户有权访问的所有知识库
            user_kbs = db.query(KnowledgeBase).filter(
                KnowledgeBase.owner_id == current_user.id
            ).all()
            public_kbs = db.query(KnowledgeBase).filter(
                KnowledgeBase.is_public == True
            ).all()
            
            accessible_kb_ids = [kb.id for kb in user_kbs + public_kbs]
        
        if not accessible_kb_ids:
            return SearchResponse(
                query=search_request.query,
                results=[],
                total=0,
                search_type=search_request.search_type,
                processing_time=0.0
            )
        
        # 执行搜索
        start_time = datetime.utcnow()
        
        search_results = await search_service.search(
            query=search_request.query,
            knowledge_base_ids=accessible_kb_ids,
            search_type=search_request.search_type,
            limit=search_request.limit,
            filters=search_request.filters
        )
        
        end_time = datetime.utcnow()
        processing_time = (end_time - start_time).total_seconds()
        
        # 构建搜索结果
        results = []
        for result in search_results:
            # 获取文件和知识库信息
            file = db.query(File).filter(File.id == result.get('file_id')).first()
            if not file:
                continue
            
            kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == file.knowledge_base_id).first()
            if not kb:
                continue
            
            results.append(SearchResult(
                file_id=file.file_id,
                filename=file.original_filename,
                knowledge_base_id=kb.kb_id,
                knowledge_base_name=kb.name,
                content=result.get('content', ''),
                highlight=result.get('highlight', ''),
                score=result.get('score', 0.0),
                metadata=result.get('metadata', {})
            ))
        
        # 更新搜索计数
        await redis_client.set(search_key, today_searches + 1, ex=86400)  # 24小时过期
        
        # 记录搜索历史（可选）
        # TODO: 保存搜索历史到数据库
        
        logger.info(f"搜索完成: {search_request.query} by {current_user.username}, 结果数: {len(results)}")
        
        return SearchResponse(
            query=search_request.query,
            results=results,
            total=len(results),
            search_type=search_request.search_type,
            processing_time=processing_time
        )
        
    except Exception as e:
        logger.error(f"搜索失败: {str(e)}")
        if isinstance(e, (ValidationError, RateLimitError)):
            status_code = {
                ValidationError: status.HTTP_400_BAD_REQUEST,
                RateLimitError: status.HTTP_429_TOO_MANY_REQUESTS
            }[type(e)]
            raise HTTPException(status_code=status_code, detail=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="搜索失败，请稍后重试"
        )

@router.get("/suggestions", summary="获取搜索建议")
async def get_search_suggestions(
    query: str = Query(..., min_length=1, description="搜索查询"),
    limit: int = Query(10, ge=1, le=20, description="建议数量"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    获取搜索建议
    
    - **query**: 搜索查询前缀
    - **limit**: 返回建议数量
    """
    try:
        # 获取用户可访问的知识库
        user_kbs = db.query(KnowledgeBase).filter(
            KnowledgeBase.owner_id == current_user.id
        ).all()
        public_kbs = db.query(KnowledgeBase).filter(
            KnowledgeBase.is_public == True
        ).all()
        
        accessible_kb_ids = [kb.id for kb in user_kbs + public_kbs]
        
        if not accessible_kb_ids:
            return {"suggestions": []}
        
        # 获取搜索建议
        suggestions = await search_service.get_search_suggestions(
            query=query,
            knowledge_base_ids=accessible_kb_ids,
            limit=limit
        )
        
        return {"suggestions": suggestions}
        
    except Exception as e:
        logger.error(f"获取搜索建议失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取搜索建议失败，请稍后重试"
        )

@router.get("/history", summary="获取搜索历史")
async def get_search_history(
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(20, ge=1, le=100, description="每页数量"),
    current_user: User = Depends(get_current_active_user)
):
    """
    获取用户搜索历史
    
    - **page**: 页码
    - **size**: 每页数量
    """
    try:
        # TODO: 从数据库获取搜索历史
        # 这里返回模拟数据
        
        redis_client = get_redis()
        history_key = f"search_history:{current_user.id}"
        
        # 从Redis获取最近的搜索历史
        history_data = await redis_client.lrange(history_key, 0, -1)
        
        # 解析历史数据
        history = []
        for item in history_data:
            try:
                import json
                search_item = json.loads(item)
                history.append(search_item)
            except:
                continue
        
        # 分页
        total = len(history)
        start = (page - 1) * size
        end = start + size
        page_history = history[start:end]
        
        return {
            "items": page_history,
            "total": total,
            "page": page,
            "size": size,
            "pages": (total + size - 1) // size
        }
        
    except Exception as e:
        logger.error(f"获取搜索历史失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取搜索历史失败，请稍后重试"
        )

@router.delete("/history", summary="清空搜索历史")
async def clear_search_history(
    current_user: User = Depends(get_current_active_user)
):
    """
    清空用户搜索历史
    """
    try:
        redis_client = get_redis()
        history_key = f"search_history:{current_user.id}"
        
        # 删除搜索历史
        await redis_client.delete(history_key)
        
        logger.info(f"搜索历史清空: {current_user.username}")
        
        return {"message": "搜索历史已清空"}
        
    except Exception as e:
        logger.error(f"清空搜索历史失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="清空搜索历史失败，请稍后重试"
        )

@router.post("/ai-enhanced", summary="AI增强搜索")
async def ai_enhanced_search(
    search_request: SearchRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    AI增强搜索（仅限Pro和Enterprise用户）
    
    提供智能查询理解、结果总结和相关推荐
    """
    try:
        # 检查用户等级
        user_tier = UserTier(current_user.tier)
        if user_tier == UserTier.FREE:
            raise ValidationError("AI增强搜索功能仅限Pro和Enterprise用户")
        
        # 执行基础搜索
        basic_search_response = await search_knowledge_base(search_request, current_user, db)
        
        if not basic_search_response.results:
            return {
                "basic_results": basic_search_response,
                "ai_summary": "未找到相关内容",
                "query_understanding": None,
                "recommendations": []
            }
        
        # AI查询理解
        query_understanding = await ai_service.analyze_query(
            query=search_request.query,
            user_id=current_user.id
        )
        
        # 生成搜索结果摘要
        result_contents = [result.content for result in basic_search_response.results[:5]]
        ai_summary = await ai_service.summarize_search_results(
            query=search_request.query,
            results=result_contents,
            user_id=current_user.id
        )
        
        # 生成相关推荐
        recommendations = await ai_service.generate_search_recommendations(
            query=search_request.query,
            results=basic_search_response.results,
            user_id=current_user.id
        )
        
        logger.info(f"AI增强搜索完成: {search_request.query} by {current_user.username}")
        
        return {
            "basic_results": basic_search_response,
            "ai_summary": ai_summary,
            "query_understanding": query_understanding,
            "recommendations": recommendations
        }
        
    except Exception as e:
        logger.error(f"AI增强搜索失败: {str(e)}")
        if isinstance(e, ValidationError):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="AI增强搜索失败，请稍后重试"
        )

@router.get("/analytics", summary="搜索分析")
async def get_search_analytics(
    days: int = Query(30, ge=1, le=365, description="分析天数"),
    current_user: User = Depends(get_current_active_user)
):
    """
    获取搜索分析数据
    
    - **days**: 分析天数
    """
    try:
        # TODO: 实现搜索分析
        # 这里返回模拟数据
        
        redis_client = get_redis()
        
        # 获取搜索统计
        search_stats = {
            "total_searches": 0,
            "avg_results_per_search": 0,
            "popular_queries": [],
            "search_trends": [],
            "knowledge_base_usage": []
        }
        
        # 从Redis获取统计数据
        stats_key = f"search_stats:{current_user.id}"
        cached_stats = await redis_client.get(stats_key)
        
        if cached_stats:
            import json
            search_stats = json.loads(cached_stats)
        
        return search_stats
        
    except Exception as e:
        logger.error(f"获取搜索分析失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取搜索分析失败，请稍后重试"
        )

@router.post("/feedback", summary="搜索反馈")
async def submit_search_feedback(
    query: str,
    result_id: str,
    feedback_type: str,  # 'helpful', 'not_helpful', 'irrelevant'
    comment: Optional[str] = None,
    current_user: User = Depends(get_current_active_user)
):
    """
    提交搜索结果反馈
    
    - **query**: 搜索查询
    - **result_id**: 结果ID
    - **feedback_type**: 反馈类型
    - **comment**: 可选评论
    """
    try:
        # 验证反馈类型
        valid_feedback_types = ['helpful', 'not_helpful', 'irrelevant']
        if feedback_type not in valid_feedback_types:
            raise ValidationError(f"无效的反馈类型，支持: {', '.join(valid_feedback_types)}")
        
        # 保存反馈到Redis（或数据库）
        redis_client = get_redis()
        feedback_key = f"search_feedback:{current_user.id}:{result_id}"
        
        feedback_data = {
            "query": query,
            "result_id": result_id,
            "feedback_type": feedback_type,
            "comment": comment,
            "timestamp": datetime.utcnow().isoformat(),
            "user_id": current_user.id
        }
        
        import json
        await redis_client.set(feedback_key, json.dumps(feedback_data), ex=86400 * 30)  # 30天过期
        
        logger.info(f"搜索反馈提交: {feedback_type} by {current_user.username}")
        
        return {"message": "反馈提交成功"}
        
    except Exception as e:
        logger.error(f"提交搜索反馈失败: {str(e)}")
        if isinstance(e, ValidationError):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="提交反馈失败，请稍后重试"
        )