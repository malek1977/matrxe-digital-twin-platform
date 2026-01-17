"""
Chat API Endpoints
"""

from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession
import logging
import uuid
import json
import asyncio
from datetime import datetime

from app.schemas.chat import (
    ChatMessage, ChatResponse, ConversationResponse,
    ConversationListResponse, StartConversationRequest
)
from app.services.chat_service import ChatService
from app.services.voice_service import VoiceService
from app.services.ai_service import AIService
from app.database.database import get_db
from app.middleware.auth import get_current_user, get_current_user_ws
from app.models.user import User
from app.models.digital_twin import DigitalTwin
from app.core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()

class ConnectionManager:
    """Manage WebSocket connections"""
    
    def __init__(self):
        self.active_connections: dict = {}
    
    async def connect(self, websocket: WebSocket, connection_id: str):
        await websocket.accept()
        self.active_connections[connection_id] = websocket
    
    def disconnect(self, connection_id: str):
        if connection_id in self.active_connections:
            del self.active_connections[connection_id]
    
    async def send_personal_message(self, message: dict, connection_id: str):
        if connection_id in self.active_connections:
            await self.active_connections[connection_id].send_json(message)
    
    async def broadcast(self, message: dict):
        for connection in self.active_connections.values():
            await connection.send_json(message)

manager = ConnectionManager()

@router.websocket("/ws/chat/{twin_id}")
async def websocket_chat(
    websocket: WebSocket,
    twin_id: uuid.UUID,
    token: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    WebSocket endpoint for real-time chat with digital twin
    """
    connection_id = None
    try:
        # Authenticate user
        if token:
            user = await get_current_user_ws(token, db)
        else:
            # Try to get token from query params or headers
            await websocket.close(code=1008)
            return
        
        if not user:
            await websocket.close(code=1008)
            return
        
        # Get digital twin
        chat_service = ChatService(db)
        twin = await chat_service.get_digital_twin(twin_id)
        if not twin or twin.user_id != user.id:
            await websocket.close(code=1008)
            return
        
        # Check if twin is trained
        if twin.training_status != "trained":
            await websocket.close(code=1008, reason="Digital twin is not trained yet")
            return
        
        # Create connection ID
        connection_id = f"{user.id}_{twin_id}_{uuid.uuid4()}"
        
        # Connect
        await manager.connect(websocket, connection_id)
        
        # Send welcome message
        welcome_msg = {
            "type": "system",
            "message": f"Connected to {twin.name}. How can I help you today?",
            "timestamp": datetime.utcnow().isoformat()
        }
        await manager.send_personal_message(welcome_msg, connection_id)
        
        # Create or get conversation
        conversation = await chat_service.get_or_create_conversation(
            user_id=user.id,
            twin_id=twin_id
        )
        
        # Main chat loop
        while True:
            try:
                # Receive message
                data = await websocket.receive_json()
                message_type = data.get("type", "message")
                
                if message_type == "message":
                    # Process text message
                    user_message = data.get("message", "").strip()
                    if not user_message:
                        continue
                    
                    # Save user message
                    user_msg_record = await chat_service.save_message(
                        conversation_id=conversation.id,
                        sender_type="user",
                        sender_id=user.id,
                        text_content=user_message
                    )
                    
                    # Send typing indicator
                    typing_msg = {
                        "type": "typing",
                        "twin_id": str(twin_id),
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    await manager.send_personal_message(typing_msg, connection_id)
                    
                    # Generate AI response
                    ai_response = await chat_service.generate_response(
                        twin_id=twin_id,
                        user_message=user_message,
                        conversation_history=await chat_service.get_conversation_history(conversation.id, limit=10)
                    )
                    
                    # Save AI response
                    ai_msg_record = await chat_service.save_message(
                        conversation_id=conversation.id,
                        sender_type="twin",
                        sender_id=twin_id,
                        text_content=ai_response["text"]
                    )
                    
                    # Check if voice response is requested
                    voice_response = None
                    if data.get("with_voice", False):
                        voice_service = VoiceService()
                        voice_response = await voice_service.generate_voice(
                            twin_id=twin_id,
                            text=ai_response["text"],
                            emotion=ai_response.get("emotion", "neutral")
                        )
                        
                        # Update message with voice URL
                        ai_msg_record.voice_url = voice_response.get("audio_url")
                        await db.commit()
                    
                    # Send AI response
                    response_msg = {
                        "type": "message",
                        "message_id": str(ai_msg_record.id),
                        "sender": "twin",
                        "content": ai_response["text"],
                        "voice_url": voice_response.get("audio_url") if voice_response else None,
                        "emotion": ai_response.get("emotion", "neutral"),
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    await manager.send_personal_message(response_msg, connection_id)
                    
                elif message_type == "voice":
                    # Process voice message
                    voice_data = data.get("voice_data")
                    language = data.get("language", "ar")
                    
                    if voice_data:
                        # Save voice file temporarily
                        voice_service = VoiceService()
                        text = await voice_service.speech_to_text(
                            audio_data=voice_data,
                            language=language
                        )
                        
                        if text:
                            # Process as text message
                            user_msg_record = await chat_service.save_message(
                                conversation_id=conversation.id,
                                sender_type="user",
                                sender_id=user.id,
                                text_content=text,
                                voice_url=data.get("voice_url")
                            )
                            
                            # Generate AI response
                            ai_response = await chat_service.generate_response(
                                twin_id=twin_id,
                                user_message=text,
                                conversation_history=await chat_service.get_conversation_history(conversation.id, limit=10)
                            )
                            
                            # Save and send response
                            ai_msg_record = await chat_service.save_message(
                                conversation_id=conversation.id,
                                sender_type="twin",
                                sender_id=twin_id,
                                text_content=ai_response["text"]
                            )
                            
                            response_msg = {
                                "type": "message",
                                "message_id": str(ai_msg_record.id),
                                "sender": "twin",
                                "content": ai_response["text"],
                                "emotion": ai_response.get("emotion", "neutral"),
                                "timestamp": datetime.utcnow().isoformat()
                            }
                            await manager.send_personal_message(response_msg, connection_id)
                
                elif message_type == "command":
                    # Handle commands
                    command = data.get("command")
                    
                    if command == "clear_history":
                        await chat_service.clear_conversation_history(conversation.id)
                        await manager.send_personal_message({
                            "type": "system",
                            "message": "Conversation history cleared",
                            "timestamp": datetime.utcnow().isoformat()
                        }, connection_id)
                    
                    elif command == "get_history":
                        history = await chat_service.get_conversation_history(conversation.id)
                        await manager.send_personal_message({
                            "type": "history",
                            "history": history,
                            "timestamp": datetime.utcnow().isoformat()
                        }, connection_id)
                    
                    elif command == "end_conversation":
                        await manager.send_personal_message({
                            "type": "system",
                            "message": "Conversation ended",
                            "timestamp": datetime.utcnow().isoformat()
                        }, connection_id)
                        break
                
                elif message_type == "typing":
                    # User is typing
                    pass
                
                elif message_type == "ping":
                    # Keep-alive ping
                    await manager.send_personal_message({
                        "type": "pong",
                        "timestamp": datetime.utcnow().isoformat()
                    }, connection_id)
                
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"WebSocket error: {e}")
                await manager.send_personal_message({
                    "type": "error",
                    "message": "An error occurred",
                    "timestamp": datetime.utcnow().isoformat()
                }, connection_id)
    
    except Exception as e:
        logger.error(f"WebSocket connection error: {e}")
    finally:
        if connection_id:
            manager.disconnect(connection_id)

@router.post("/start", response_model=ConversationResponse)
async def start_conversation(
    request: StartConversationRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Start a new conversation with digital twin
    """
    try:
        chat_service = ChatService(db)
        
        # Get digital twin
        twin = await chat_service.get_digital_twin(request.twin_id)
        if not twin or twin.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Digital twin not found"
            )
        
        # Check if twin is trained
        if twin.training_status != "trained":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Digital twin is not trained yet"
            )
        
        # Create conversation
        conversation = await chat_service.create_conversation(
            user_id=current_user.id,
            twin_id=request.twin_id,
            title=request.title,
            context_type=request.context_type,
            mood=request.mood
        )
        
        # Generate initial greeting if requested
        initial_message = None
        if request.generate_greeting:
            ai_service = AIService()
            greeting = await ai_service.generate_greeting(
                twin_id=request.twin_id,
                user_name=current_user.full_name or current_user.username,
                context=request.context_type,
                mood=request.mood
            )
            
            # Save greeting message
            initial_message = await chat_service.save_message(
                conversation_id=conversation.id,
                sender_type="twin",
                sender_id=request.twin_id,
                text_content=greeting
            )
        
        logger.info(f"Conversation started: {conversation.id}")
        
        response = ConversationResponse.from_orm(conversation)
        if initial_message:
            response.initial_message = ChatMessage.from_orm(initial_message)
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to start conversation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to start conversation"
        )

@router.post("/{conversation_id}/message")
async def send_message(
    conversation_id: uuid.UUID,
    message: ChatMessage,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Send a message in an existing conversation (REST API alternative)
    """
    try:
        chat_service = ChatService(db)
        
        # Get conversation
        conversation = await chat_service.get_conversation(conversation_id)
        if not conversation or conversation.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )
        
        # Save user message
        user_msg = await chat_service.save_message(
            conversation_id=conversation.id,
            sender_type="user",
            sender_id=current_user.id,
            text_content=message.content
        )
        
        # Generate AI response
        twin_id = conversation.twin_id
        ai_response = await chat_service.generate_response(
            twin_id=twin_id,
            user_message=message.content,
            conversation_history=await chat_service.get_conversation_history(conversation.id, limit=10)
        )
        
        # Save AI response
        ai_msg = await chat_service.save_message(
            conversation_id=conversation.id,
            sender_type="twin",
            sender_id=twin_id,
            text_content=ai_response["text"]
        )
        
        # Generate voice if requested
        voice_url = None
        if message.with_voice:
            voice_service = VoiceService()
            voice_response = await voice_service.generate_voice(
                twin_id=twin_id,
                text=ai_response["text"],
                emotion=ai_response.get("emotion", "neutral")
            )
            voice_url = voice_response.get("audio_url")
            
            # Update message with voice URL
            ai_msg.voice_url = voice_url
            await db.commit()
        
        logger.info(f"Message sent in conversation: {conversation_id}")
        
        return {
            "success": True,
            "user_message": ChatMessage.from_orm(user_msg),
            "ai_response": {
                "message": ChatMessage.from_orm(ai_msg),
                "voice_url": voice_url,
                "emotion": ai_response.get("emotion", "neutral")
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to send message: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send message"
        )

@router.get("/conversations", response_model=ConversationListResponse)
async def get_conversations(
    skip: int = 0,
    limit: int = 50,
    archived: bool = False,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Get user's conversations
    """
    try:
        chat_service = ChatService(db)
        
        conversations = await chat_service.get_user_conversations(
            user_id=current_user.id,
            skip=skip,
            limit=limit,
            archived=archived
        )
        
        total = await chat_service.get_user_conversation_count(
            user_id=current_user.id,
            archived=archived
        )
        
        return ConversationListResponse(
            conversations=[ConversationResponse.from_orm(conv) for conv in conversations],
            total=total,
            skip=skip,
            limit=limit
        )
        
    except Exception as e:
        logger.error(f"Failed to get conversations: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get conversations"
        )

@router.get("/conversations/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: uuid.UUID,
    include_messages: bool = True,
    message_limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Get specific conversation with messages
    """
    try:
        chat_service = ChatService(db)
        
        # Get conversation
        conversation = await chat_service.get_conversation(conversation_id)
        if not conversation or conversation.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )
        
        response = ConversationResponse.from_orm(conversation)
        
        # Include messages if requested
        if include_messages:
            messages = await chat_service.get_conversation_messages(
                conversation_id=conversation_id,
                limit=message_limit
            )
            response.messages = [ChatMessage.from_orm(msg) for msg in messages]
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get conversation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get conversation"
        )

@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Delete a conversation
    """
    try:
        chat_service = ChatService(db)
        
        # Get conversation
        conversation = await chat_service.get_conversation(conversation_id)
        if not conversation or conversation.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )
        
        # Delete conversation
        await chat_service.delete_conversation(conversation_id)
        
        logger.info(f"Conversation deleted: {conversation_id}")
        
        return {
            "success": True,
            "message": "Conversation deleted successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete conversation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete conversation"
        )

@router.post("/conversations/{conversation_id}/archive")
async def archive_conversation(
    conversation_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Archive a conversation
    """
    try:
        chat_service = ChatService(db)
        
        conversation = await chat_service.get_conversation(conversation_id)
        if not conversation or conversation.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )
        
        await chat_service.archive_conversation(conversation_id)
        
        logger.info(f"Conversation archived: {conversation_id}")
        
        return {
            "success": True,
            "message": "Conversation archived successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to archive conversation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to archive conversation"
        )

@router.post("/conversations/{conversation_id}/pin")
async def pin_conversation(
    conversation_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Pin a conversation
    """
    try:
        chat_service = ChatService(db)
        
        conversation = await chat_service.get_conversation(conversation_id)
        if not conversation or conversation.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )
        
        await chat_service.pin_conversation(conversation_id)
        
        logger.info(f"Conversation pinned: {conversation_id}")
        
        return {
            "success": True,
            "message": "Conversation pinned successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to pin conversation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to pin conversation"
        )

@router.get("/{twin_id}/suggestions")
async def get_chat_suggestions(
    twin_id: uuid.UUID,
    context: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Get suggested conversation starters for digital twin
    """
    try:
        chat_service = ChatService(db)
        ai_service = AIService()
        
        # Get digital twin
        twin = await chat_service.get_digital_twin(twin_id)
        if not twin or twin.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Digital twin not found"
            )
        
        # Get suggestions
        suggestions = await ai_service.generate_chat_suggestions(
            twin_id=twin_id,
            context=context,
            user_interests=None  # Could be extracted from user profile
        )
        
        return {
            "twin_id": twin_id,
            "twin_name": twin.name,
            "suggestions": suggestions,
            "context": context
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get chat suggestions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get chat suggestions"
        )

@router.get("/analytics/{twin_id}")
async def get_chat_analytics(
    twin_id: uuid.UUID,
    period: str = "week",  # day, week, month, year
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Get chat analytics for digital twin
    """
    try:
        chat_service = ChatService(db)
        
        # Get digital twin
        twin = await chat_service.get_digital_twin(twin_id)
        if not twin or twin.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Digital twin not found"
            )
        
        # Get analytics
        analytics = await chat_service.get_chat_analytics(
            twin_id=twin_id,
            period=period
        )
        
        return {
            "twin_id": twin_id,
            "twin_name": twin.name,
            "period": period,
            "analytics": analytics
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get chat analytics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get chat analytics"
        )