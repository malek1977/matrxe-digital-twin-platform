"""
Authentication API Endpoints
"""

from datetime import datetime, timedelta
from typing import Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from app.schemas.auth import (
    Token, UserCreate, UserResponse, 
    LoginRequest, ResetPasswordRequest, VerifyEmailRequest
)
from app.schemas.user import User as UserSchema
from app.services.auth_service import AuthService
from app.services.user_service import UserService
from app.services.email_service import EmailService
from app.database.database import get_db
from app.core.security import create_access_token, create_refresh_token, verify_password
from app.core.config import settings
from app.models.user import User
from app.middleware.auth import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Register a new user
    """
    try:
        auth_service = AuthService(db)
        user_service = UserService(db)
        email_service = EmailService()
        
        # Check if user exists
        existing_user = await user_service.get_user_by_email(user_data.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User with this email already exists"
            )
        
        # Create user
        user = await auth_service.register_user(user_data)
        
        # Send verification email
        verification_token = auth_service.create_verification_token(user.id)
        background_tasks.add_task(
            email_service.send_verification_email,
            user.email,
            user.full_name or user.username,
            verification_token
        )
        
        # Start free trial
        await auth_service.start_free_trial(user.id)
        
        # Log registration
        logger.info(f"New user registered: {user.email}")
        
        return UserResponse.from_orm(user)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed"
        )

@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Login user and return access token
    """
    try:
        auth_service = AuthService(db)
        user_service = UserService(db)
        
        # Get user
        user = await user_service.get_user_by_email(form_data.username)
        if not user or not verify_password(form_data.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Check if user is active
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is deactivated"
            )
        
        # Update last login
        user.last_login = datetime.utcnow()
        await db.commit()
        
        # Create tokens
        access_token = create_access_token(data={"sub": str(user.id)})
        refresh_token = create_refresh_token(data={"sub": str(user.id)})
        
        # Log login
        logger.info(f"User logged in: {user.email}")
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "user": UserSchema.from_orm(user)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed"
        )

@router.post("/refresh", response_model=Token)
async def refresh_token(
    refresh_token: str,
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Refresh access token using refresh token
    """
    try:
        auth_service = AuthService(db)
        
        # Verify refresh token
        user_id = auth_service.verify_refresh_token(refresh_token)
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
        
        # Get user
        user_service = UserService(db)
        user = await user_service.get_user_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Create new tokens
        access_token = create_access_token(data={"sub": str(user.id)})
        new_refresh_token = create_refresh_token(data={"sub": str(user.id)})
        
        return {
            "access_token": access_token,
            "refresh_token": new_refresh_token,
            "token_type": "bearer",
            "user": UserSchema.from_orm(user)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token refresh failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token refresh failed"
        )

@router.post("/verify-email")
async def verify_email(
    verify_data: VerifyEmailRequest,
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Verify user email
    """
    try:
        auth_service = AuthService(db)
        user_service = UserService(db)
        
        # Verify token
        user_id = auth_service.verify_email_token(verify_data.token)
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid verification token"
            )
        
        # Get user
        user = await user_service.get_user_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Update user
        user.is_verified = True
        user.verified_at = datetime.utcnow()
        await db.commit()
        
        logger.info(f"Email verified: {user.email}")
        
        return {
            "success": True,
            "message": "Email verified successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Email verification failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Email verification failed"
        )

@router.post("/forgot-password")
async def forgot_password(
    email: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Send password reset email
    """
    try:
        auth_service = AuthService(db)
        user_service = UserService(db)
        email_service = EmailService()
        
        # Get user
        user = await user_service.get_user_by_email(email)
        if not user:
            # Don't reveal that user doesn't exist
            return {
                "success": True,
                "message": "If the email exists, a reset link has been sent"
            }
        
        # Create reset token
        reset_token = auth_service.create_password_reset_token(user.id)
        
        # Send reset email
        background_tasks.add_task(
            email_service.send_password_reset_email,
            user.email,
            user.full_name or user.username,
            reset_token
        )
        
        logger.info(f"Password reset requested: {user.email}")
        
        return {
            "success": True,
            "message": "Password reset email sent"
        }
        
    except Exception as e:
        logger.error(f"Forgot password failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process request"
        )

@router.post("/reset-password")
async def reset_password(
    reset_data: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Reset user password
    """
    try:
        auth_service = AuthService(db)
        user_service = UserService(db)
        
        # Verify token
        user_id = auth_service.verify_password_reset_token(reset_data.token)
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid reset token"
            )
        
        # Get user
        user = await user_service.get_user_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Update password
        await auth_service.update_password(user.id, reset_data.new_password)
        
        logger.info(f"Password reset: {user.email}")
        
        return {
            "success": True,
            "message": "Password reset successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Password reset failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Password reset failed"
        )

@router.post("/logout")
async def logout(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Logout user (invalidate token on client side)
    """
    # Note: For JWT tokens, we can't invalidate them server-side
    # without implementing a token blacklist. This endpoint is
    # for client-side cleanup.
    
    logger.info(f"User logged out: {current_user.email}")
    
    return {
        "success": True,
        "message": "Logged out successfully"
    }

@router.get("/me", response_model=UserSchema)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Get current user information
    """
    return current_user

@router.post("/resend-verification")
async def resend_verification(
    email: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Resend verification email
    """
    try:
        auth_service = AuthService(db)
        user_service = UserService(db)
        email_service = EmailService()
        
        # Get user
        user = await user_service.get_user_by_email(email)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        if user.is_verified:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already verified"
            )
        
        # Create new verification token
        verification_token = auth_service.create_verification_token(user.id)
        
        # Send verification email
        background_tasks.add_task(
            email_service.send_verification_email,
            user.email,
            user.full_name or user.username,
            verification_token
        )
        
        logger.info(f"Verification email resent: {user.email}")
        
        return {
            "success": True,
            "message": "Verification email sent"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Resend verification failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to resend verification"
        )

@router.post("/change-password")
async def change_password(
    old_password: str,
    new_password: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Change user password
    """
    try:
        auth_service = AuthService(db)
        
        # Verify old password
        if not verify_password(old_password, current_user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Incorrect current password"
            )
        
        # Update password
        await auth_service.update_password(current_user.id, new_password)
        
        logger.info(f"Password changed: {current_user.email}")
        
        return {
            "success": True,
            "message": "Password changed successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Password change failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to change password"
        )

@router.get("/trial-status")
async def get_trial_status(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Get user trial status and remaining time
    """
    try:
        auth_service = AuthService(db)
        
        trial_info = await auth_service.get_trial_status(current_user.id)
        
        return trial_info
        
    except Exception as e:
        logger.error(f"Failed to get trial status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get trial status"
        )