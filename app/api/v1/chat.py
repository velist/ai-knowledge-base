"""聊天API路由"""

from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from loguru import logger

from app.core.database import get_db
from app.core.auth import get_current_active_user
from app.models.database import User, KnowledgeBase, Conversation, Message
from app.models.schemas import (
    ChatRequest, ChatResponse, ConversationCreate, ConversationResponse,
    ConversationListResponse, MessageResponse, UserTier, APIResponse
)
from app.core.exceptions import ValidationError, ResourceNotFoundError, RateLimitError, PermissionDeniedError
from app.services.ai_service import AIServiceManager
from app.services.search_service import SearchService
from app.core.redis_client import get_redis

router = APIRouter()
ai_service = AIServiceManager()
search_service = SearchService()

@router.post("/conversations", response_model=ConversationResponse, summary="创建对话")
async def create_conversation(
    conversation_data: ConversationCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    创建新的对话
    
    - **title**: 对话标题
    - **knowledge_base_ids**: 关联的知识库ID列表（可选）
    """
    try:
        # 验证知识库权限
        accessible_kb_ids = []
        if conversation_data.knowledge_base_ids:
            for kb_id in conversation_data.knowledge_base_ids:
                kb = db.query(KnowledgeBase).filter(KnowledgeBase.kb_id == kb_id).first()
                if not kb:
                    continue
                
                # 检查访问权限（自己的或公开的）
                if kb.owner_id == current_user.id or kb.is_public:
                    accessible_kb_ids.append(kb.id)
        
        # 创建对话
        new_conversation = Conversation(
            title=conversation_data.title,
            user_id=current_user.id,
            knowledge_base_ids=accessible_kb_ids,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        db.add(new_conversation)
        db.commit()
        db.refresh(new_conversation)
        
        logger.info(f"对话创建成功: {new_conversation.title} by {current_user.username}")
        
        return ConversationResponse(
            conversation_id=new_conversation.conversation_id,
            title=new_conversation.title,
            knowledge_base_ids=[],  # 需要转换为kb_id
            message_count=0,
            created_at=new_conversation.created_at,
            updated_at=new_conversation.updated_at
        )
        
    except Exception as e:
        db.rollback()
        logger.error(f"创建对话失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="创建对话失败，请稍后重试"
        )

@router.get("/conversations", response_model=ConversationListResponse, summary="获取对话列表")
async def list_conversations(
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(20, ge=1, le=100, description="每页数量"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    获取用户的对话列表
    
    - **page**: 页码
    - **size**: 每页数量
    """
    try:
        # 查询对话
        query = db.query(Conversation).filter(Conversation.user_id == current_user.id)
        
        # 计算总数
        total = query.count()
        
        # 分页查询
        offset = (page - 1) * size
        conversations = query.order_by(Conversation.updated_at.desc()).offset(offset).limit(size).all()
        
        # 构建响应
        conversation_responses = []
        for conv in conversations:
            # 获取消息数量
            message_count = db.query(Message).filter(Message.conversation_id == conv.id).count()
            
            # 获取知识库信息
            kb_ids = []
            if conv.knowledge_base_ids:
                kbs = db.query(KnowledgeBase).filter(KnowledgeBase.id.in_(conv.knowledge_base_ids)).all()
                kb_ids = [kb.kb_id for kb in kbs]
            
            conversation_responses.append(ConversationResponse(
                conversation_id=conv.conversation_id,
                title=conv.title,
                knowledge_base_ids=kb_ids,
                message_count=message_count,
                created_at=conv.created_at,
                updated_at=conv.updated_at
            ))
        
        return ConversationListResponse(
            items=conversation_responses,
            total=total,
            page=page,
            size=size,
            pages=(total + size - 1) // size
        )
        
    except Exception as e:
        logger.error(f"获取对话列表失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取对话列表失败，请稍后重试"
        )

@router.get("/conversations/{conversation_id}", response_model=ConversationResponse, summary="获取对话详情")
async def get_conversation(
    conversation_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    获取对话详情
    """
    try:
        # 查找对话
        conversation = db.query(Conversation).filter(
            Conversation.conversation_id == conversation_id
        ).first()
        
        if not conversation:
            raise ResourceNotFoundError("对话不存在")
        
        # 检查权限
        if conversation.user_id != current_user.id:
            raise PermissionDeniedError("无权访问此对话")
        
        # 获取消息数量
        message_count = db.query(Message).filter(Message.conversation_id == conversation.id).count()
        
        # 获取知识库信息
        kb_ids = []
        if conversation.knowledge_base_ids:
            kbs = db.query(KnowledgeBase).filter(KnowledgeBase.id.in_(conversation.knowledge_base_ids)).all()
            kb_ids = [kb.kb_id for kb in kbs]
        
        return ConversationResponse(
            conversation_id=conversation.conversation_id,
            title=conversation.title,
            knowledge_base_ids=kb_ids,
            message_count=message_count,
            created_at=conversation.created_at,
            updated_at=conversation.updated_at
        )
        
    except Exception as e:
        logger.error(f"获取对话详情失败: {str(e)}")
        if isinstance(e, (ResourceNotFoundError, PermissionDeniedError)):
            status_code = {
                ResourceNotFoundError: status.HTTP_404_NOT_FOUND,
                PermissionDeniedError: status.HTTP_403_FORBIDDEN
            }[type(e)]
            raise HTTPException(status_code=status_code, detail=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取对话详情失败，请稍后重试"
        )

@router.delete("/conversations/{conversation_id}", summary="删除对话")
async def delete_conversation(
    conversation_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    删除对话及其所有消息
    """
    try:
        # 查找对话
        conversation = db.query(Conversation).filter(
            Conversation.conversation_id == conversation_id
        ).first()
        
        if not conversation:
            raise ResourceNotFoundError("对话不存在")
        
        # 检查权限
        if conversation.user_id != current_user.id:
            raise PermissionDeniedError("无权删除此对话")
        
        # 删除相关消息
        db.query(Message).filter(Message.conversation_id == conversation.id).delete()
        
        # 删除对话
        db.delete(conversation)
        db.commit()
        
        logger.info(f"对话删除成功: {conversation.title} by {current_user.username}")
        
        return {"message": "对话删除成功"}
        
    except Exception as e:
        db.rollback()
        logger.error(f"删除对话失败: {str(e)}")
        if isinstance(e, (ResourceNotFoundError, PermissionDeniedError)):
            status_code = {
                ResourceNotFoundError: status.HTTP_404_NOT_FOUND,
                PermissionDeniedError: status.HTTP_403_FORBIDDEN
            }[type(e)]
            raise HTTPException(status_code=status_code, detail=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="删除对话失败，请稍后重试"
        )

@router.post("/conversations/{conversation_id}/chat", response_model=ChatResponse, summary="发送聊天消息")
async def chat(
    conversation_id: str,
    chat_request: ChatRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    在指定对话中发送消息
    
    - **message**: 用户消息
    - **use_knowledge_base**: 是否使用知识库增强回答
    - **temperature**: AI回答的创造性（0-1）
    """
    try:
        # 验证消息
        if not chat_request.message or len(chat_request.message.strip()) < 1:
            raise ValidationError("消息不能为空")
        
        # 查找对话
        conversation = db.query(Conversation).filter(
            Conversation.conversation_id == conversation_id
        ).first()
        
        if not conversation:
            raise ResourceNotFoundError("对话不存在")
        
        # 检查权限
        if conversation.user_id != current_user.id:
            raise PermissionDeniedError("无权访问此对话")
        
        # 检查用户聊天限制
        redis_client = get_redis()
        chat_key = f"chat_limit:{current_user.id}:{datetime.utcnow().date()}"
        
        # 获取今日聊天次数
        today_chats = await redis_client.get(chat_key) or 0
        today_chats = int(today_chats)
        
        # 检查聊天限制
        chat_limits = {
            UserTier.FREE: 20,
            UserTier.PRO: 200,
            UserTier.ENTERPRISE: 2000
        }
        
        user_tier = UserTier(current_user.tier)
        max_chats = chat_limits.get(user_tier, 20)
        
        if today_chats >= max_chats:
            raise RateLimitError(f"今日聊天次数已达上限（{max_chats}次）")
        
        # 保存用户消息
        user_message = Message(
            conversation_id=conversation.id,
            role="user",
            content=chat_request.message,
            created_at=datetime.utcnow()
        )
        
        db.add(user_message)
        db.flush()  # 获取ID但不提交
        
        # 准备AI回答的上下文
        context = ""
        sources = []
        
        # 如果启用知识库增强
        if chat_request.use_knowledge_base and conversation.knowledge_base_ids:
            # 在知识库中搜索相关内容
            search_results = await search_service.search(
                query=chat_request.message,
                knowledge_base_ids=conversation.knowledge_base_ids,
                search_type="hybrid",
                limit=5
            )
            
            if search_results:
                context_parts = []
                for result in search_results[:3]:  # 使用前3个结果
                    context_parts.append(result.get('content', ''))
                    sources.append({
                        "file_id": result.get('file_id'),
                        "filename": result.get('filename', ''),
                        "score": result.get('score', 0.0)
                    })
                
                context = "\n\n".join(context_parts)
        
        # 获取对话历史
        recent_messages = db.query(Message).filter(
            Message.conversation_id == conversation.id
        ).order_by(Message.created_at.desc()).limit(10).all()
        
        conversation_history = []
        for msg in reversed(recent_messages):
            conversation_history.append({
                "role": msg.role,
                "content": msg.content
            })
        
        # 调用AI服务生成回答
        ai_response = await ai_service.chat_completion(
            message=chat_request.message,
            context=context,
            conversation_history=conversation_history,
            temperature=chat_request.temperature,
            user_id=current_user.id
        )
        
        # 保存AI回答
        ai_message = Message(
            conversation_id=conversation.id,
            role="assistant",
            content=ai_response.get('content', ''),
            metadata={
                "sources": sources,
                "model": ai_response.get('model', ''),
                "tokens": ai_response.get('tokens', 0)
            },
            created_at=datetime.utcnow()
        )
        
        db.add(ai_message)
        
        # 更新对话时间
        conversation.updated_at = datetime.utcnow()
        
        db.commit()
        
        # 更新聊天计数
        await redis_client.set(chat_key, today_chats + 1, ex=86400)  # 24小时过期
        
        logger.info(f"聊天完成: {conversation.title} by {current_user.username}")
        
        return ChatResponse(
            message_id=ai_message.message_id,
            content=ai_message.content,
            sources=sources,
            model=ai_response.get('model', ''),
            tokens_used=ai_response.get('tokens', 0),
            created_at=ai_message.created_at
        )
        
    except Exception as e:
        db.rollback()
        logger.error(f"聊天失败: {str(e)}")
        if isinstance(e, (ValidationError, ResourceNotFoundError, PermissionDeniedError, RateLimitError)):
            status_code = {
                ValidationError: status.HTTP_400_BAD_REQUEST,
                ResourceNotFoundError: status.HTTP_404_NOT_FOUND,
                PermissionDeniedError: status.HTTP_403_FORBIDDEN,
                RateLimitError: status.HTTP_429_TOO_MANY_REQUESTS
            }[type(e)]
            raise HTTPException(status_code=status_code, detail=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="聊天失败，请稍后重试"
        )

@router.get("/conversations/{conversation_id}/messages", summary="获取对话消息")
async def get_conversation_messages(
    conversation_id: str,
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(50, ge=1, le=100, description="每页数量"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    获取对话的消息列表
    
    - **page**: 页码
    - **size**: 每页数量
    """
    try:
        # 查找对话
        conversation = db.query(Conversation).filter(
            Conversation.conversation_id == conversation_id
        ).first()
        
        if not conversation:
            raise ResourceNotFoundError("对话不存在")
        
        # 检查权限
        if conversation.user_id != current_user.id:
            raise PermissionDeniedError("无权访问此对话")
        
        # 查询消息
        query = db.query(Message).filter(Message.conversation_id == conversation.id)
        
        # 计算总数
        total = query.count()
        
        # 分页查询（按时间正序）
        offset = (page - 1) * size
        messages = query.order_by(Message.created_at.asc()).offset(offset).limit(size).all()
        
        # 构建响应
        message_responses = []
        for msg in messages:
            message_responses.append(MessageResponse(
                message_id=msg.message_id,
                role=msg.role,
                content=msg.content,
                metadata=msg.metadata or {},
                created_at=msg.created_at
            ))
        
        return {
            "items": message_responses,
            "total": total,
            "page": page,
            "size": size,
            "pages": (total + size - 1) // size
        }
        
    except Exception as e:
        logger.error(f"获取对话消息失败: {str(e)}")
        if isinstance(e, (ResourceNotFoundError, PermissionDeniedError)):
            status_code = {
                ResourceNotFoundError: status.HTTP_404_NOT_FOUND,
                PermissionDeniedError: status.HTTP_403_FORBIDDEN
            }[type(e)]
            raise HTTPException(status_code=status_code, detail=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取对话消息失败，请稍后重试"
        )

@router.put("/conversations/{conversation_id}/title", summary="更新对话标题")
async def update_conversation_title(
    conversation_id: str,
    title: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    更新对话标题
    
    - **title**: 新标题
    """
    try:
        # 验证标题
        if not title or len(title.strip()) < 1:
            raise ValidationError("标题不能为空")
        
        # 查找对话
        conversation = db.query(Conversation).filter(
            Conversation.conversation_id == conversation_id
        ).first()
        
        if not conversation:
            raise ResourceNotFoundError("对话不存在")
        
        # 检查权限
        if conversation.user_id != current_user.id:
            raise PermissionDeniedError("无权修改此对话")
        
        # 更新标题
        conversation.title = title.strip()
        conversation.updated_at = datetime.utcnow()
        
        db.commit()
        
        logger.info(f"对话标题更新: {title} by {current_user.username}")
        
        return {"message": "标题更新成功"}
        
    except Exception as e:
        db.rollback()
        logger.error(f"更新对话标题失败: {str(e)}")
        if isinstance(e, (ValidationError, ResourceNotFoundError, PermissionDeniedError)):
            status_code = {
                ValidationError: status.HTTP_400_BAD_REQUEST,
                ResourceNotFoundError: status.HTTP_404_NOT_FOUND,
                PermissionDeniedError: status.HTTP_403_FORBIDDEN
            }[type(e)]
            raise HTTPException(status_code=status_code, detail=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="更新标题失败，请稍后重试"
        )

@router.get("/stats", summary="获取聊天统计")
async def get_chat_stats(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    获取用户聊天统计
    """
    try:
        # 对话统计
        total_conversations = db.query(Conversation).filter(
            Conversation.user_id == current_user.id
        ).count()
        
        # 消息统计
        total_messages = db.query(Message).join(Conversation).filter(
            Conversation.user_id == current_user.id
        ).count()
        
        user_messages = db.query(Message).join(Conversation).filter(
            Conversation.user_id == current_user.id,
            Message.role == "user"
        ).count()
        
        ai_messages = db.query(Message).join(Conversation).filter(
            Conversation.user_id == current_user.id,
            Message.role == "assistant"
        ).count()
        
        # 今日使用量
        redis_client = get_redis()
        chat_key = f"chat_limit:{current_user.id}:{datetime.utcnow().date()}"
        today_chats = await redis_client.get(chat_key) or 0
        
        # 用户限制
        chat_limits = {
            UserTier.FREE: 20,
            UserTier.PRO: 200,
            UserTier.ENTERPRISE: 2000
        }
        
        user_tier = UserTier(current_user.tier)
        daily_limit = chat_limits.get(user_tier, 20)
        
        return {
            "conversations": {
                "total": total_conversations
            },
            "messages": {
                "total": total_messages,
                "user_messages": user_messages,
                "ai_messages": ai_messages
            },
            "usage": {
                "today_chats": int(today_chats),
                "daily_limit": daily_limit,
                "remaining": max(0, daily_limit - int(today_chats))
            }
        }
        
    except Exception as e:
        logger.error(f"获取聊天统计失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取聊天统计失败，请稍后重试"
        )