"""
Digital Twins API Endpoints
"""

from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
import logging
import uuid

from app.schemas.digital_twin import (
    DigitalTwinCreate, DigitalTwinResponse, DigitalTwinUpdate,
    DigitalTwinTrainingStatus, DigitalTwinListResponse
)
from app.services.digital_twin_service import DigitalTwinService
from app.services.voice_service import VoiceService
from app.services.face_service import FaceService
from app.services.ai_service import AIService
from app.database.database import get_db
from app.middleware.auth import get_current_user
from app.models.user import User
from app.models.digital_twin import DigitalTwin
from app.core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/create", response_model=DigitalTwinResponse, status_code=status.HTTP_201_CREATED)
async def create_digital_twin(
    name: str = Form(...),
    voice_sample: UploadFile = File(...),
    face_images: List[UploadFile] = File(...),
    personality_traits: Optional[str] = Form(None),
    background_tasks: BackgroundTasks = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Create a new digital twin
    """
    try:
        twin_service = DigitalTwinService(db)
        voice_service = VoiceService()
        face_service = FaceService()
        ai_service = AIService()
        
        # Check user's twin limit based on subscription
        twin_count = await twin_service.get_user_twin_count(current_user.id)
        max_twins = twin_service.get_max_twins_for_user(current_user)
        
        if twin_count >= max_twins:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"You can only create {max_twins} digital twins with your current plan"
            )
        
        # Create twin record
        twin = await twin_service.create_digital_twin(
            user_id=current_user.id,
            name=name,
            personality_traits=personality_traits
        )
        
        # Save uploaded files
        voice_path = await twin_service.save_voice_sample(twin.id, voice_sample)
        face_paths = await twin_service.save_face_images(twin.id, face_images)
        
        # Update twin with file paths
        twin.voice_samples_urls = [voice_path]
        twin.face_images_urls = face_paths
        await db.commit()
        
        # Start training in background
        if background_tasks:
            background_tasks.add_task(
                train_digital_twin_background,
                twin_id=twin.id,
                voice_path=voice_path,
                face_paths=face_paths,
                personality_traits=personality_traits
            )
        else:
            # Start training immediately
            await train_digital_twin_background(
                twin_id=twin.id,
                voice_path=voice_path,
                face_paths=face_paths,
                personality_traits=personality_traits
            )
        
        logger.info(f"Digital twin created: {twin.id} for user: {current_user.email}")
        
        return DigitalTwinResponse.from_orm(twin)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create digital twin: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create digital twin"
        )

async def train_digital_twin_background(
    twin_id: uuid.UUID,
    voice_path: str,
    face_paths: List[str],
    personality_traits: Optional[str] = None
):
    """
    Background task to train digital twin models
    """
    try:
        from app.database.database import async_session
        
        async with async_session() as session:
            twin_service = DigitalTwinService(session)
            voice_service = VoiceService()
            face_service = FaceService()
            ai_service = AIService()
            
            # Get twin
            twin = await twin_service.get_digital_twin(twin_id)
            if not twin:
                logger.error(f"Twin not found: {twin_id}")
                return
            
            # Update status to training
            twin.training_status = "training"
            twin.training_started_at = datetime.utcnow()
            await session.commit()
            
            try:
                # 1. Train voice model
                logger.info(f"Training voice model for twin: {twin_id}")
                twin.voice_training_status = "training"
                await session.commit()
                
                voice_result = await voice_service.train_voice_model(
                    twin_id=twin_id,
                    audio_path=voice_path,
                    twin_name=twin.name
                )
                
                twin.voice_model_id = voice_result.get("model_id")
                twin.voice_training_status = "trained"
                twin.voice_similarity_score = voice_result.get("similarity_score", 0.0)
                await session.commit()
                
                logger.info(f"Voice training completed for twin: {twin_id}")
                
                # 2. Train face model
                logger.info(f"Training face model for twin: {twin_id}")
                twin.face_training_status = "training"
                await session.commit()
                
                face_result = await face_service.train_face_model(
                    twin_id=twin_id,
                    image_paths=face_paths
                )
                
                twin.face_model_id = face_result.get("model_id")
                twin.face_training_status = "trained"
                twin.face_similarity_score = face_result.get("similarity_score", 0.0)
                await session.commit()
                
                logger.info(f"Face training completed for twin: {twin_id}")
                
                # 3. Train personality model
                logger.info(f"Training personality model for twin: {twin_id}")
                personality_result = await ai_service.train_personality_model(
                    twin_id=twin_id,
                    personality_traits=personality_traits,
                    twin_name=twin.name
                )
                
                twin.personality_model_id = personality_result.get("model_id")
                twin.chat_model_id = personality_result.get("chat_model_id")
                await session.commit()
                
                logger.info(f"Personality training completed for twin: {twin_id}")
                
                # Update final status
                twin.training_status = "trained"
                twin.training_completed_at = datetime.utcnow()
                twin.training_progress = 100
                await session.commit()
                
                logger.info(f"Digital twin training completed: {twin_id}")
                
                # Send notification to user
                await twin_service.send_training_complete_notification(
                    user_id=twin.user_id,
                    twin_name=twin.name
                )
                
            except Exception as training_error:
                logger.error(f"Training failed for twin {twin_id}: {training_error}")
                
                twin.training_status = "failed"
                twin.training_errors = str(training_error)
                await session.commit()
                
                # Send failure notification
                await twin_service.send_training_failed_notification(
                    user_id=twin.user_id,
                    twin_name=twin.name,
                    error=str(training_error)
                )
                
    except Exception as e:
        logger.error(f"Background training task failed: {e}")

@router.get("/", response_model=DigitalTwinListResponse)
async def get_digital_twins(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Get all digital twins for current user
    """
    try:
        twin_service = DigitalTwinService(db)
        
        twins = await twin_service.get_user_digital_twins(
            user_id=current_user.id,
            skip=skip,
            limit=limit
        )
        
        total = await twin_service.get_user_twin_count(current_user.id)
        
        return DigitalTwinListResponse(
            twins=[DigitalTwinResponse.from_orm(twin) for twin in twins],
            total=total,
            skip=skip,
            limit=limit
        )
        
    except Exception as e:
        logger.error(f"Failed to get digital twins: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get digital twins"
        )

@router.get("/{twin_id}", response_model=DigitalTwinResponse)
async def get_digital_twin(
    twin_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Get specific digital twin by ID
    """
    try:
        twin_service = DigitalTwinService(db)
        
        twin = await twin_service.get_digital_twin(twin_id)
        if not twin:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Digital twin not found"
            )
        
        # Check ownership
        if twin.user_id != current_user.id and not current_user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to access this digital twin"
            )
        
        return DigitalTwinResponse.from_orm(twin)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get digital twin: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get digital twin"
        )

@router.put("/{twin_id}", response_model=DigitalTwinResponse)
async def update_digital_twin(
    twin_id: uuid.UUID,
    twin_update: DigitalTwinUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Update digital twin
    """
    try:
        twin_service = DigitalTwinService(db)
        
        twin = await twin_service.get_digital_twin(twin_id)
        if not twin:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Digital twin not found"
            )
        
        # Check ownership
        if twin.user_id != current_user.id and not current_user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to update this digital twin"
            )
        
        # Update twin
        updated_twin = await twin_service.update_digital_twin(twin_id, twin_update)
        
        logger.info(f"Digital twin updated: {twin_id}")
        
        return DigitalTwinResponse.from_orm(updated_twin)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update digital twin: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update digital twin"
        )

@router.delete("/{twin_id}")
async def delete_digital_twin(
    twin_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Delete digital twin
    """
    try:
        twin_service = DigitalTwinService(db)
        
        twin = await twin_service.get_digital_twin(twin_id)
        if not twin:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Digital twin not found"
            )
        
        # Check ownership
        if twin.user_id != current_user.id and not current_user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to delete this digital twin"
            )
        
        # Delete twin and associated files/models
        await twin_service.delete_digital_twin(twin_id)
        
        logger.info(f"Digital twin deleted: {twin_id}")
        
        return {
            "success": True,
            "message": "Digital twin deleted successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete digital twin: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete digital twin"
        )

@router.get("/{twin_id}/training-status", response_model=DigitalTwinTrainingStatus)
async def get_training_status(
    twin_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Get training status of digital twin
    """
    try:
        twin_service = DigitalTwinService(db)
        
        twin = await twin_service.get_digital_twin(twin_id)
        if not twin:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Digital twin not found"
            )
        
        # Check ownership
        if twin.user_id != current_user.id and not current_user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to access this digital twin"
            )
        
        status_info = {
            "twin_id": twin.id,
            "twin_name": twin.name,
            "overall_status": twin.training_status,
            "progress": twin.training_progress,
            "voice_training": {
                "status": twin.voice_training_status,
                "similarity_score": twin.voice_similarity_score,
                "model_id": twin.voice_model_id
            },
            "face_training": {
                "status": twin.face_training_status,
                "similarity_score": twin.face_similarity_score,
                "model_id": twin.face_model_id
            },
            "personality_training": {
                "model_id": twin.personality_model_id,
                "chat_model_id": twin.chat_model_id
            },
            "started_at": twin.training_started_at,
            "completed_at": twin.training_completed_at,
            "errors": twin.training_errors
        }
        
        return status_info
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get training status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get training status"
        )

@router.post("/{twin_id}/retrain")
async def retrain_digital_twin(
    twin_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Retrain digital twin models
    """
    try:
        twin_service = DigitalTwinService(db)
        
        twin = await twin_service.get_digital_twin(twin_id)
        if not twin:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Digital twin not found"
            )
        
        # Check ownership
        if twin.user_id != current_user.id and not current_user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to retrain this digital twin"
            )
        
        # Check if training is already in progress
        if twin.training_status == "training":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Training is already in progress"
            )
        
        # Start retraining in background
        background_tasks.add_task(
            retrain_digital_twin_background,
            twin_id=twin_id,
            voice_path=twin.voice_samples_urls[0] if twin.voice_samples_urls else None,
            face_paths=twin.face_images_urls
        )
        
        logger.info(f"Retraining started for digital twin: {twin_id}")
        
        return {
            "success": True,
            "message": "Retraining started successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to start retraining: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to start retraining"
        )

async def retrain_digital_twin_background(
    twin_id: uuid.UUID,
    voice_path: Optional[str] = None,
    face_paths: Optional[List[str]] = None
):
    """
    Background task to retrain digital twin
    """
    # Similar to train_digital_twin_background but with existing files
    pass

@router.post("/{twin_id}/clone")
async def clone_digital_twin(
    twin_id: uuid.UUID,
    new_name: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Clone an existing digital twin
    """
    try:
        twin_service = DigitalTwinService(db)
        
        # Get source twin
        source_twin = await twin_service.get_digital_twin(twin_id)
        if not source_twin:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Source digital twin not found"
            )
        
        # Check if source twin can be cloned
        if not source_twin.can_be_cloned and source_twin.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This digital twin cannot be cloned"
            )
        
        # Check user's twin limit
        twin_count = await twin_service.get_user_twin_count(current_user.id)
        max_twins = twin_service.get_max_twins_for_user(current_user)
        
        if twin_count >= max_twins:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"You can only create {max_twins} digital twins with your current plan"
            )
        
        # Clone twin
        cloned_twin = await twin_service.clone_digital_twin(
            source_twin_id=twin_id,
            user_id=current_user.id,
            new_name=new_name
        )
        
        logger.info(f"Digital twin cloned: {twin_id} -> {cloned_twin.id}")
        
        return DigitalTwinResponse.from_orm(cloned_twin)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to clone digital twin: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to clone digital twin"
        )

@router.get("/{twin_id}/usage-stats")
async def get_twin_usage_stats(
    twin_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Get usage statistics for digital twin
    """
    try:
        twin_service = DigitalTwinService(db)
        
        twin = await twin_service.get_digital_twin(twin_id)
        if not twin:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Digital twin not found"
            )
        
        # Check ownership
        if twin.user_id != current_user.id and not current_user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to access this digital twin"
            )
        
        stats = await twin_service.get_twin_usage_stats(twin_id)
        
        return {
            "twin_id": twin.id,
            "twin_name": twin.name,
            "total_chats": twin.total_chats,
            "total_voice_minutes": twin.total_voice_minutes,
            "last_interaction": twin.last_interaction,
            "detailed_stats": stats
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get usage stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get usage stats"
        )