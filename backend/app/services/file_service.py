"""
File Upload and Processing Service for MATRXe
"""

import logging
import os
import shutil
import uuid
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from pathlib import Path
import magic
from fastapi import UploadFile, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
import aiofiles
from PIL import Image
import ffmpeg
import wave
import json

from app.core.config import settings
from app.models.media import MediaFile
from app.core.security import sanitize_filename, generate_secure_filename
from app.utils.storage import StorageManager

logger = logging.getLogger(__name__)

class FileService:
    """
    Service for handling file uploads and processing
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.storage = StorageManager()
        self.upload_dir = Path(settings.UPLOAD_DIR)
        self.max_size = settings.MAX_UPLOAD_SIZE
        
        # Create upload directory if not exists
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        
        # Allowed MIME types
        self.allowed_mimes = {
            'image': ['image/jpeg', 'image/png', 'image/gif', 'image/webp', 'image/svg+xml'],
            'audio': ['audio/mpeg', 'audio/wav', 'audio/ogg', 'audio/m4a', 'audio/x-m4a'],
            'video': ['video/mp4', 'video/webm', 'video/ogg', 'video/quicktime'],
            'document': ['application/pdf', 'text/plain', 'application/msword', 
                        'application/vnd.openxmlformats-officedocument.wordprocessingml.document']
        }
    
    async def upload_file(
        self,
        user_id: uuid.UUID,
        file: UploadFile,
        file_type: str,
        metadata: Optional[Dict] = None,
        is_public: bool = False
    ) -> Dict[str, Any]:
        """
        Upload and process a file
        """
        try:
            # Validate file type
            if file_type not in self.allowed_mimes:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid file type: {file_type}"
                )
            
            # Read file content
            content = await file.read()
            
            # Check file size
            if len(content) > self.max_size:
                raise HTTPException(
                    status_code=400,
                    detail=f"File too large. Maximum size is {self.max_size / 1024 / 1024}MB"
                )
            
            # Detect MIME type
            mime_type = magic.from_buffer(content[:2048], mime=True)
            
            # Validate MIME type
            if mime_type not in self.allowed_mimes[file_type]:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid file format. Allowed: {', '.join(self.allowed_mimes[file_type])}"
                )
            
            # Generate secure filename
            original_filename = sanitize_filename(file.filename)
            secure_filename = generate_secure_filename(original_filename)
            file_extension = Path(original_filename).suffix.lower()
            
            if not file_extension:
                # Determine extension from MIME type
                file_extension = self._get_extension_from_mime(mime_type)
            
            final_filename = f"{secure_filename}{file_extension}"
            
            # Create user directory
            user_dir = self.upload_dir / str(user_id)
            user_dir.mkdir(exist_ok=True)
            
            # Create type-specific directory
            type_dir = user_dir / file_type
            type_dir.mkdir(exist_ok=True)
            
            # Create date directory (for organization)
            date_dir = type_dir / datetime.now().strftime("%Y/%m/%d")
            date_dir.mkdir(parents=True, exist_ok=True)
            
            # Save file
            file_path = date_dir / final_filename
            async with aiofiles.open(file_path, 'wb') as f:
                await f.write(content)
            
            # Process file based on type
            file_info = await self._process_file(
                file_path=file_path,
                file_type=file_type,
                mime_type=mime_type,
                original_filename=original_filename
            )
            
            # Generate access token for private files
            access_token = None
            if not is_public:
                access_token = str(uuid.uuid4())
            
            # Create media record
            media_file = MediaFile(
                id=uuid.uuid4(),
                user_id=user_id,
                file_type=file_type,
                original_filename=original_filename,
                stored_filename=final_filename,
                file_path=str(file_path.relative_to(self.upload_dir)),
                file_size=len(content),
                mime_type=mime_type,
                duration_seconds=file_info.get('duration'),
                width=file_info.get('width'),
                height=file_info.get('height'),
                is_public=is_public,
                access_token=access_token,
                metadata=metadata or {},
                processing_status='completed',
                expires_at=datetime.utcnow() + timedelta(days=30)  # Auto-cleanup after 30 days
            )
            
            self.db.add(media_file)
            await self.db.commit()
            
            # Generate URL for accessing the file
            file_url = self._generate_file_url(media_file)
            
            logger.info(f"File uploaded: {final_filename} for user {user_id}")
            
            return {
                "success": True,
                "file_id": media_file.id,
                "filename": original_filename,
                "file_type": file_type,
                "mime_type": mime_type,
                "size": len(content),
                "url": file_url,
                "access_token": access_token,
                "metadata": file_info,
                "uploaded_at": datetime.utcnow().isoformat()
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to upload file: {e}")
            raise HTTPException(
                status_code=500,
                detail="Failed to upload file"
            )
    
    async def upload_multiple_files(
        self,
        user_id: uuid.UUID,
        files: List[UploadFile],
        file_type: str,
        metadata_list: Optional[List[Dict]] = None,
        is_public: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Upload multiple files at once
        """
        results = []
        
        for i, file in enumerate(files):
            try:
                metadata = metadata_list[i] if metadata_list and i < len(metadata_list) else None
                
                result = await self.upload_file(
                    user_id=user_id,
                    file=file,
                    file_type=file_type,
                    metadata=metadata,
                    is_public=is_public
                )
                
                results.append({
                    "success": True,
                    "original_filename": file.filename,
                    **result
                })
                
            except Exception as e:
                results.append({
                    "success": False,
                    "original_filename": file.filename,
                    "error": str(e)
                })
        
        return results
    
    async def get_file(
        self,
        file_id: uuid.UUID,
        user_id: Optional[uuid.UUID] = None,
        access_token: Optional[str] = None
    ) -> Optional[MediaFile]:
        """
        Get file with access control
        """
        try:
            media_file = await self.db.get(MediaFile, file_id)
            if not media_file:
                return None
            
            # Check access
            if not self._check_file_access(media_file, user_id, access_token):
                return None
            
            # Update access count
            media_file.times_accessed += 1
            media_file.last_accessed = datetime.utcnow()
            await self.db.commit()
            
            return media_file
            
        except Exception as e:
            logger.error(f"Failed to get file: {e}")
            return None
    
    async def delete_file(
        self,
        file_id: uuid.UUID,
        user_id: uuid.UUID
    ) -> bool:
        """
        Delete a file
        """
        try:
            media_file = await self.db.get(MediaFile, file_id)
            if not media_file or media_file.user_id != user_id:
                return False
            
            # Delete physical file
            file_path = self.upload_dir / media_file.file_path
            if file_path.exists():
                file_path.unlink()
            
            # Delete from database
            await self.db.delete(media_file)
            await self.db.commit()
            
            logger.info(f"File deleted: {file_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete file: {e}")
            await self.db.rollback()
            return False
    
    async def get_user_files(
        self,
        user_id: uuid.UUID,
        file_type: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> Tuple[List[MediaFile], int]:
        """
        Get user's files with pagination
        """
        try:
            from sqlalchemy import select, func
            
            # Build query
            query = select(MediaFile).where(MediaFile.user_id == user_id)
            
            if file_type:
                query = query.where(MediaFile.file_type == file_type)
            
            # Get total count
            count_query = select(func.count()).select_from(MediaFile).where(
                MediaFile.user_id == user_id
            )
            if file_type:
                count_query = count_query.where(MediaFile.file_type == file_type)
            
            count_result = await self.db.execute(count_query)
            total = count_result.scalar()
            
            # Get paginated results
            query = query.order_by(MediaFile.created_at.desc()).offset(skip).limit(limit)
            result = await self.db.execute(query)
            files = result.scalars().all()
            
            return files, total
            
        except Exception as e:
            logger.error(f"Failed to get user files: {e}")
            return [], 0
    
    async def process_audio_file(
        self,
        file_path: Path,
        operations: List[str] = None
    ) -> Dict[str, Any]:
        """
        Process audio file (normalize, trim, convert format)
        """
        try:
            if not operations:
                operations = ['normalize', 'convert']
            
            result = {
                "original_path": str(file_path),
                "operations": operations,
                "processed_files": []
            }
            
            # Generate output filename
            output_path = file_path.parent / f"processed_{file_path.name}"
            
            # Apply operations
            stream = ffmpeg.input(str(file_path))
            
            if 'normalize' in operations:
                stream = ffmpeg.filter(stream, 'loudnorm')
            
            if 'trim' in operations:
                # Trim to first 60 seconds for processing
                stream = ffmpeg.filter(stream, 'atrim', duration=60)
            
            if 'convert' in operations:
                # Convert to WAV for compatibility
                output_path = output_path.with_suffix('.wav')
                stream = ffmpeg.output(stream, str(output_path), acodec='pcm_s16le', ar=16000)
            else:
                stream = ffmpeg.output(stream, str(output_path))
            
            # Run ffmpeg
            ffmpeg.run(stream, overwrite_output=True, capture_stdout=True, capture_stderr=True)
            
            # Get processed file info
            if output_path.exists():
                processed_info = await self._get_audio_info(output_path)
                result["processed_files"].append({
                    "path": str(output_path),
                    "size": output_path.stat().st_size,
                    "info": processed_info
                })
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to process audio: {e}")
            return {
                "error": str(e),
                "original_path": str(file_path)
            }
    
    async def process_image_file(
        self,
        file_path: Path,
        operations: List[str] = None
    ) -> Dict[str, Any]:
        """
        Process image file (resize, compress, convert format)
        """
        try:
            if not operations:
                operations = ['compress', 'resize']
            
            result = {
                "original_path": str(file_path),
                "operations": operations,
                "processed_files": []
            }
            
            with Image.open(file_path) as img:
                original_info = {
                    "format": img.format,
                    "mode": img.mode,
                    "size": img.size,
                    "width": img.width,
                    "height": img.height
                }
                
                result["original_info"] = original_info
                
                # Apply operations
                processed_img = img.copy()
                
                if 'resize' in operations:
                    # Resize to maximum 1024px on longest side
                    max_size = 1024
                    if max(processed_img.width, processed_img.height) > max_size:
                        ratio = max_size / max(processed_img.width, processed_img.height)
                        new_size = (
                            int(processed_img.width * ratio),
                            int(processed_img.height * ratio)
                        )
                        processed_img = processed_img.resize(new_size, Image.Resampling.LANCZOS)
                
                if 'convert' in operations:
                    # Convert to RGB and JPEG format
                    if processed_img.mode != 'RGB':
                        processed_img = processed_img.convert('RGB')
                    
                    output_path = file_path.with_suffix('.jpg')
                    processed_img.save(
                        output_path,
                        'JPEG',
                        quality=85,
                        optimize=True
                    )
                else:
                    # Save with compression
                    output_path = file_path.parent / f"compressed_{file_path.name}"
                    
                    if processed_img.format == 'JPEG':
                        processed_img.save(
                            output_path,
                            quality=85,
                            optimize=True
                        )
                    elif processed_img.format == 'PNG':
                        processed_img.save(
                            output_path,
                            optimize=True
                        )
                    else:
                        processed_img.save(output_path)
                
                # Get processed file info
                if output_path.exists():
                    processed_info = {
                        "format": processed_img.format,
                        "mode": processed_img.mode,
                        "size": processed_img.size,
                        "width": processed_img.width,
                        "height": processed_img.height,
                        "file_size": output_path.stat().st_size
                    }
                    
                    result["processed_files"].append({
                        "path": str(output_path),
                        "info": processed_info
                    })
                
                return result
                
        except Exception as e:
            logger.error(f"Failed to process image: {e}")
            return {
                "error": str(e),
                "original_path": str(file_path)
            }
    
    async def generate_thumbnail(
        self,
        file_path: Path,
        size: Tuple[int, int] = (256, 256)
    ) -> Optional[Path]:
        """
        Generate thumbnail for image or video
        """
        try:
            # Check if file is image or video
            mime_type = magic.from_file(str(file_path), mime=True)
            
            thumbnail_path = file_path.parent / f"thumb_{file_path.stem}.jpg"
            
            if mime_type.startswith('image/'):
                with Image.open(file_path) as img:
                    img.thumbnail(size, Image.Resampling.LANCZOS)
                    img.save(thumbnail_path, 'JPEG', quality=85)
                    
            elif mime_type.startswith('video/'):
                # Extract thumbnail from video
                ffmpeg.input(
                    str(file_path),
                    ss='00:00:01'  # Capture at 1 second
                ).output(
                    str(thumbnail_path),
                    vframes=1,
                    **{'qscale:v': 2}
                ).run(overwrite_output=True, capture_stdout=True, capture_stderr=True)
            
            else:
                return None
            
            return thumbnail_path if thumbnail_path.exists() else None
            
        except Exception as e:
            logger.error(f"Failed to generate thumbnail: {e}")
            return None
    
    async def cleanup_expired_files(self) -> Dict[str, int]:
        """
        Clean up expired files
        """
        try:
            from sqlalchemy import select
            from datetime import datetime
            
            deleted_count = 0
            freed_space = 0
            
            # Find expired files
            stmt = select(MediaFile).where(
                MediaFile.expires_at < datetime.utcnow()
            )
            result = await self.db.execute(stmt)
            expired_files = result.scalars().all()
            
            for media_file in expired_files:
                try:
                    # Delete physical file
                    file_path = self.upload_dir / media_file.file_path
                    if file_path.exists():
                        file_size = file_path.stat().st_size
                        file_path.unlink()
                        freed_space += file_size
                    
                    # Delete from database
                    await self.db.delete(media_file)
                    deleted_count += 1
                    
                except Exception as e:
                    logger.error(f"Failed to delete expired file {media_file.id}: {e}")
            
            await self.db.commit()
            
            logger.info(f"Cleaned up {deleted_count} expired files, freed {freed_space} bytes")
            
            return {
                "deleted_count": deleted_count,
                "freed_space": freed_space,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to cleanup expired files: {e}")
            await self.db.rollback()
            return {"deleted_count": 0, "freed_space": 0, "error": str(e)}
    
    async def get_storage_usage(self, user_id: uuid.UUID) -> Dict[str, Any]:
        """
        Get user's storage usage
        """
        try:
            from sqlalchemy import select, func
            
            # Calculate total storage used
            stmt = select(func.sum(MediaFile.file_size)).where(
                MediaFile.user_id == user_id
            )
            result = await self.db.execute(stmt)
            total_used = result.scalar() or 0
            
            # Get file count by type
            type_stmt = select(
                MediaFile.file_type,
                func.count(MediaFile.id),
                func.sum(MediaFile.file_size)
            ).where(
                MediaFile.user_id == user_id
            ).group_by(MediaFile.file_type)
            
            type_result = await self.db.execute(type_stmt)
            type_stats = {}
            
            for file_type, count, size in type_result:
                type_stats[file_type] = {
                    "count": count,
                    "size": size or 0,
                    "size_mb": round((size or 0) / 1024 / 1024, 2)
                }
            
            return {
                "user_id": user_id,
                "total_used": total_used,
                "total_used_mb": round(total_used / 1024 / 1024, 2),
                "total_used_gb": round(total_used / 1024 / 1024 / 1024, 2),
                "by_type": type_stats,
                "last_updated": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get storage usage: {e}")
            return {"error": str(e)}
    
    # Private helper methods
    
    async def _process_file(
        self,
        file_path: Path,
        file_type: str,
        mime_type: str,
        original_filename: str
    ) -> Dict[str, Any]:
        """
        Process file and extract metadata
        """
        file_info = {
            "original_filename": original_filename,
            "file_path": str(file_path),
            "file_type": file_type,
            "mime_type": mime_type,
            "size_bytes": file_path.stat().st_size,
            "created": datetime.fromtimestamp(file_path.stat().st_ctime).isoformat()
        }
        
        try:
            if file_type == 'image':
                with Image.open(file_path) as img:
                    file_info.update({
                        "width": img.width,
                        "height": img.height,
                        "format": img.format,
                        "mode": img.mode,
                        "has_alpha": img.mode in ('RGBA', 'LA', 'P')
                    })
                    
                    # Generate thumbnail
                    thumb_path = await self.generate_thumbnail(file_path)
                    if thumb_path:
                        file_info["thumbnail_path"] = str(thumb_path)
            
            elif file_type == 'audio':
                audio_info = await self._get_audio_info(file_path)
                file_info.update(audio_info)
            
            elif file_type == 'video':
                video_info = await self._get_video_info(file_path)
                file_info.update(video_info)
                
                # Generate thumbnail
                thumb_path = await self.generate_thumbnail(file_path)
                if thumb_path:
                    file_info["thumbnail_path"] = str(thumb_path)
            
            return file_info
            
        except Exception as e:
            logger.error(f"Failed to process file metadata: {e}")
            return file_info
    
    async def _get_audio_info(self, file_path: Path) -> Dict[str, Any]:
        """Get audio file information"""
        try:
            if file_path.suffix.lower() == '.wav':
                with wave.open(str(file_path), 'rb') as wav_file:
                    return {
                        "duration": wav_file.getnframes() / wav_file.getframerate(),
                        "sample_rate": wav_file.getframerate(),
                        "channels": wav_file.getnchannels(),
                        "sample_width": wav_file.getsampwidth(),
                        "frames": wav_file.getnframes(),
                        "compression_type": wav_file.getcomptype()
                    }
            else:
                # Use ffprobe for other formats
                probe = ffmpeg.probe(str(file_path))
                audio_stream = next(
                    (stream for stream in probe['streams'] if stream['codec_type'] == 'audio'),
                    None
                )
                
                if audio_stream:
                    return {
                        "duration": float(audio_stream.get('duration', 0)),
                        "sample_rate": int(audio_stream.get('sample_rate', 0)),
                        "channels": int(audio_stream.get('channels', 0)),
                        "codec": audio_stream.get('codec_name'),
                        "bit_rate": audio_stream.get('bit_rate')
                    }
                else:
                    return {"duration": 0}
                    
        except Exception as e:
            logger.error(f"Failed to get audio info: {e}")
            return {"duration": 0}
    
    async def _get_video_info(self, file_path: Path) -> Dict[str, Any]:
        """Get video file information"""
        try:
            probe = ffmpeg.probe(str(file_path))
            
            video_info = {
                "duration": 0,
                "width": 0,
                "height": 0,
                "codec": None,
                "bit_rate": None,
                "frame_rate": None,
                "streams": []
            }
            
            for stream in probe.get('streams', []):
                stream_info = {
                    "type": stream.get('codec_type'),
                    "codec": stream.get('codec_name'),
                    "profile": stream.get('profile'),
                    "bit_rate": stream.get('bit_rate')
                }
                
                if stream.get('codec_type') == 'video':
                    video_info.update({
                        "duration": float(stream.get('duration', 0)) or float(probe.get('format', {}).get('duration', 0)),
                        "width": int(stream.get('width', 0)),
                        "height": int(stream.get('height', 0)),
                        "frame_rate": stream.get('r_frame_rate'),
                        "aspect_ratio": stream.get('display_aspect_ratio'),
                        "pix_fmt": stream.get('pix_fmt')
                    })
                
                elif stream.get('codec_type') == 'audio':
                    stream_info.update({
                        "sample_rate": stream.get('sample_rate'),
                        "channels": stream.get('channels'),
                        "channel_layout": stream.get('channel_layout')
                    })
                
                video_info["streams"].append(stream_info)
            
            # Get format info
            format_info = probe.get('format', {})
            video_info.update({
                "format_name": format_info.get('format_name'),
                "format_long_name": format_info.get('format_long_name'),
                "size_bytes": int(format_info.get('size', 0)),
                "bit_rate": format_info.get('bit_rate')
            })
            
            return video_info
            
        except Exception as e:
            logger.error(f"Failed to get video info: {e}")
            return {"duration": 0, "width": 0, "height": 0}
    
    def _check_file_access(
        self,
        media_file: MediaFile,
        user_id: Optional[uuid.UUID] = None,
        access_token: Optional[str] = None
    ) -> bool:
        """Check if user has access to file"""
        # Public files are accessible to everyone
        if media_file.is_public:
            return True
        
        # File owner has access
        if user_id and media_file.user_id == user_id:
            return True
        
        # Check access token
        if access_token and media_file.access_token == access_token:
            return True
        
        return False
    
    def _generate_file_url(self, media_file: MediaFile) -> str:
        """Generate URL for accessing file"""
        if media_file.is_public:
            return f"/uploads/{media_file.file_path}"
        else:
            return f"/uploads/{media_file.file_path}?token={media_file.access_token}"
    
    def _get_extension_from_mime(self, mime_type: str) -> str:
        """Get file extension from MIME type"""
        mime_to_ext = {
            'image/jpeg': '.jpg',
            'image/png': '.png',
            'image/gif': '.gif',
            'image/webp': '.webp',
            'image/svg+xml': '.svg',
            'audio/mpeg': '.mp3',
            'audio/wav': '.wav',
            'audio/ogg': '.ogg',
            'audio/m4a': '.m4a',
            'video/mp4': '.mp4',
            'video/webm': '.webm',
            'video/ogg': '.ogv',
            'video/quicktime': '.mov',
            'application/pdf': '.pdf',
            'text/plain': '.txt'
        }
        
        return mime_to_ext.get(mime_type, '')