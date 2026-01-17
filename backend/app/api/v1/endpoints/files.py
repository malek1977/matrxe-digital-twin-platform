"""
File Upload API Endpoints
"""

from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Query
from sqlalchemy.ext.asyncio import AsyncSession
import logging
import uuid
from pathlib import Path

from app.schemas.files import (
    FileUploadResponse, FileListResponse, FileResponse,
    StorageUsageResponse, FileProcessRequest
)
from app.services.file_service import FileService
from app.database.database import get_db
from app.middleware.auth import get_current_user
from app.models.user import User
from app.core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/upload", response_model=FileUploadResponse)
async def upload_file(
    file_type: str = Form(...),
    file: UploadFile = File(...),
    is_public: bool = Form(False),
    metadata: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Upload a single file
    """
    try:
        file_service = FileService(db)
        
        # Parse metadata if provided
        file_metadata = None
        if metadata:
            import json
            file_metadata = json.loads(metadata)
        
        result = await file_service.upload_file(
            user_id=current_user.id,
            file=file,
            file_type=file_type,
            metadata=file_metadata,
            is_public=is_public
        )
        
        if not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("error", "Upload failed")
            )
        
        logger.info(f"File uploaded: {file.filename} by user {current_user.id}")
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"File upload failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="File upload failed"
        )

@router.post("/upload/multiple")
async def upload_multiple_files(
    file_type: str = Form(...),
    files: List[UploadFile] = File(...),
    is_public: bool = Form(False),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Upload multiple files at once
    """
    try:
        file_service = FileService(db)
        
        results = await file_service.upload_multiple_files(
            user_id=current_user.id,
            files=files,
            file_type=file_type,
            is_public=is_public
        )
        
        successful = [r for r in results if r["success"]]
        failed = [r for r in results if not r["success"]]
        
        logger.info(f"Multiple files uploaded: {len(successful)} successful, {len(failed)} failed")
        
        return {
            "total": len(results),
            "successful": len(successful),
            "failed": len(failed),
            "results": results
        }
        
    except Exception as e:
        logger.error(f"Multiple file upload failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Multiple file upload failed"
        )

@router.get("/", response_model=FileListResponse)
async def get_files(
    file_type: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Get user's files
    """
    try:
        file_service = FileService(db)
        
        files, total = await file_service.get_user_files(
            user_id=current_user.id,
            file_type=file_type,
            skip=skip,
            limit=limit
        )
        
        return {
            "files": [
                {
                    "id": file.id,
                    "file_type": file.file_type,
                    "original_filename": file.original_filename,
                    "stored_filename": file.stored_filename,
                    "file_size": file.file_size,
                    "mime_type": file.mime_type,
                    "duration_seconds": file.duration_seconds,
                    "width": file.width,
                    "height": file.height,
                    "is_public": file.is_public,
                    "access_token": file.access_token,
                    "processing_status": file.processing_status,
                    "times_accessed": file.times_accessed,
                    "last_accessed": file.last_accessed,
                    "created_at": file.created_at,
                    "expires_at": file.expires_at,
                    "metadata": file.metadata
                }
                for file in files
            ],
            "total": total,
            "skip": skip,
            "limit": limit
        }
        
    except Exception as e:
        logger.error(f"Failed to get files: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get files"
        )

@router.get("/{file_id}", response_model=FileResponse)
async def get_file(
    file_id: uuid.UUID,
    token: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Get specific file information
    """
    try:
        file_service = FileService(db)
        
        file = await file_service.get_file(
            file_id=file_id,
            user_id=current_user.id,
            access_token=token
        )
        
        if not file:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found or access denied"
            )
        
        # Generate file URL
        from app.core.config import settings
        file_url = f"{settings.BASE_URL}/api/v1/files/{file_id}/download"
        if not file.is_public and file.access_token:
            file_url += f"?token={file.access_token}"
        
        return {
            "id": file.id,
            "file_type": file.file_type,
            "original_filename": file.original_filename,
            "stored_filename": file.stored_filename,
            "file_size": file.file_size,
            "mime_type": file.mime_type,
            "duration_seconds": file.duration_seconds,
            "width": file.width,
            "height": file.height,
            "is_public": file.is_public,
            "access_token": file.access_token,
            "file_url": file_url,
            "processing_status": file.processing_status,
            "times_accessed": file.times_accessed,
            "last_accessed": file.last_accessed,
            "created_at": file.created_at,
            "expires_at": file.expires_at,
            "metadata": file.metadata
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get file: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get file"
        )

@router.get("/{file_id}/download")
async def download_file(
    file_id: uuid.UUID,
    token: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Download a file
    """
    try:
        file_service = FileService(db)
        
        file = await file_service.get_file(
            file_id=file_id,
            user_id=current_user.id,
            access_token=token
        )
        
        if not file:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found or access denied"
            )
        
        # Get file path
        from app.core.config import settings
        import os
        file_path = os.path.join(settings.UPLOAD_DIR, file.file_path)
        
        if not os.path.exists(file_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found on server"
            )
        
        # Return file as streaming response
        from fastapi.responses import FileResponse
        return FileResponse(
            path=file_path,
            filename=file.original_filename,
            media_type=file.mime_type
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to download file: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to download file"
        )

@router.delete("/{file_id}")
async def delete_file(
    file_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Delete a file
    """
    try:
        file_service = FileService(db)
        
        success = await file_service.delete_file(
            file_id=file_id,
            user_id=current_user.id
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found or access denied"
            )
        
        logger.info(f"File deleted: {file_id} by user {current_user.id}")
        
        return {
            "success": True,
            "message": "File deleted successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete file: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete file"
        )

@router.get("/storage/usage", response_model=StorageUsageResponse)
async def get_storage_usage(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Get user's storage usage
    """
    try:
        file_service = FileService(db)
        
        usage = await file_service.get_storage_usage(current_user.id)
        
        if "error" in usage:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=usage["error"]
            )
        
        return usage
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get storage usage: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get storage usage"
        )

@router.post("/{file_id}/process")
async def process_file(
    file_id: uuid.UUID,
    process_request: FileProcessRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Process a file (audio, image, video)
    """
    try:
        file_service = FileService(db)
        
        # Get file
        file = await file_service.get_file(
            file_id=file_id,
            user_id=current_user.id
        )
        
        if not file:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found or access denied"
            )
        
        # Get file path
        from app.core.config import settings
        import os
        file_path = Path(os.path.join(settings.UPLOAD_DIR, file.file_path))
        
        if not file_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found on server"
            )
        
        # Process based on file type
        if file.file_type == "audio":
            result = await file_service.process_audio_file(
                file_path=file_path,
                operations=process_request.operations
            )
        elif file.file_type == "image":
            result = await file_service.process_image_file(
                file_path=file_path,
                operations=process_request.operations
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Processing not supported for file type: {file.file_type}"
            )
        
        if "error" in result:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["error"]
            )
        
        # Update file metadata if processing created new files
        if result.get("processed_files"):
            # Store processing results in metadata
            if not file.metadata:
                file.metadata = {}
            
            file.metadata["processing_results"] = result
            await db.commit()
        
        return {
            "success": True,
            "file_id": file_id,
            "original_file": file.original_filename,
            "processing_result": result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"File processing failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="File processing failed"
        )

@router.post("/cleanup/expired")
async def cleanup_expired_files(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Clean up expired files (admin only)
    """
    try:
        if not current_user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required"
            )
        
        file_service = FileService(db)
        
        result = await file_service.cleanup_expired_files()
        
        return {
            "success": True,
            "cleanup_result": result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cleanup expired files: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cleanup expired files"
        )

@router.post("/{file_id}/share")
async def share_file(
    file_id: uuid.UUID,
    is_public: bool = True,
    expiry_hours: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Share a file (generate access token or make public)
    """
    try:
        file_service = FileService(db)
        
        # Get file
        file = await file_service.get_file(
            file_id=file_id,
            user_id=current_user.id
        )
        
        if not file:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found or access denied"
            )
        
        # Update sharing settings
        file.is_public = is_public
        
        if not is_public:
            # Generate new access token
            import secrets
            file.access_token = secrets.token_urlsafe(32)
        else:
            file.access_token = None
        
        # Set expiry if specified
        if expiry_hours:
            from datetime import datetime, timedelta
            file.expires_at = datetime.utcnow() + timedelta(hours=expiry_hours)
        
        await db.commit()
        
        # Generate share URL
        from app.core.config import settings
        if is_public:
            share_url = f"{settings.BASE_URL}/api/v1/files/{file_id}/download"
        else:
            share_url = f"{settings.BASE_URL}/api/v1/files/{file_id}/download?token={file.access_token}"
        
        logger.info(f"File shared: {file_id} by user {current_user.id}")
        
        return {
            "success": True,
            "file_id": file_id,
            "is_public": is_public,
            "access_token": file.access_token if not is_public else None,
            "share_url": share_url,
            "expires_at": file.expires_at.isoformat() if file.expires_at else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to share file: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to share file"
        )

@router.get("/{file_id}/thumbnail")
async def get_file_thumbnail(
    file_id: uuid.UUID,
    token: Optional[str] = Query(None),
    size: str = Query("256x256", regex="^\d+x\d+$"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get file thumbnail
    """
    try:
        file_service = FileService(db)
        
        # Get file
        file = await file_service.get_file(
            file_id=file_id,
            user_id=current_user.id,
            access_token=token
        )
        
        if not file:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found or access denied"
            )
        
        # Check if file is image or video
        if file.file_type not in ["image", "video"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Thumbnail not available for this file type"
            )
        
        # Get file path
        from app.core.config import settings
        import os
        file_path = Path(os.path.join(settings.UPLOAD_DIR, file.file_path))
        
        if not file_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found on server"
            )
        
        # Parse size
        width, height = map(int, size.split('x'))
        
        # Generate thumbnail
        thumb_path = await file_service.generate_thumbnail(
            file_path=file_path,
            size=(width, height)
        )
        
        if not thumb_path or not thumb_path.exists():
            # Return default thumbnail based on file type
            from fastapi.responses import FileResponse
            default_thumb = Path("static/images/default-thumbnail.png")
            return FileResponse(
                path=default_thumb,
                media_type="image/png"
            )
        
        # Return thumbnail
        from fastapi.responses import FileResponse
        return FileResponse(
            path=thumb_path,
            media_type="image/jpeg",
            filename=f"thumb_{file.original_filename}.jpg"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get thumbnail: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get thumbnail"
        )