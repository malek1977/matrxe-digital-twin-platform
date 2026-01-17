"""
Security utilities for MATRXe platform
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from passlib.context import CryptContext
import secrets
import hashlib
import uuid
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT token utilities
def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    Create JWT access token
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def create_refresh_token(data: Dict[str, Any]) -> str:
    """
    Create JWT refresh token
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def verify_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Verify JWT token
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError as e:
        logger.error(f"Token verification failed: {e}")
        return None

def create_email_verification_token(user_id: uuid.UUID) -> str:
    """
    Create email verification token
    """
    to_encode = {
        "sub": str(user_id),
        "type": "email_verification",
        "exp": datetime.utcnow() + timedelta(hours=24)
    }
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

def create_password_reset_token(user_id: uuid.UUID) -> str:
    """
    Create password reset token
    """
    to_encode = {
        "sub": str(user_id),
        "type": "password_reset",
        "exp": datetime.utcnow() + timedelta(hours=1)
    }
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

def verify_email_token(token: str) -> Optional[uuid.UUID]:
    """
    Verify email verification token
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        if payload.get("type") != "email_verification":
            return None
        return uuid.UUID(payload.get("sub"))
    except (JWTError, ValueError):
        return None

def verify_password_reset_token(token: str) -> Optional[uuid.UUID]:
    """
    Verify password reset token
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        if payload.get("type") != "password_reset":
            return None
        return uuid.UUID(payload.get("sub"))
    except (JWTError, ValueError):
        return None

# Password utilities
def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify password against hash
    """
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """
    Hash password
    """
    return pwd_context.hash(password)

def generate_secure_password(length: int = 16) -> str:
    """
    Generate secure random password
    """
    alphabet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*"
    return ''.join(secrets.choice(alphabet) for _ in range(length))

# API key utilities
def generate_api_key() -> str:
    """
    Generate API key
    """
    return f"matrxe_{secrets.token_urlsafe(32)}"

def hash_api_key(api_key: str) -> str:
    """
    Hash API key for storage
    """
    return hashlib.sha256(api_key.encode()).hexdigest()

# CSRF protection
def generate_csrf_token() -> str:
    """
    Generate CSRF token
    """
    return secrets.token_urlsafe(32)

def verify_csrf_token(token: str, stored_token: str) -> bool:
    """
    Verify CSRF token
    """
    return secrets.compare_digest(token, stored_token)

# Rate limiting key
def get_rate_limit_key(identifier: str, endpoint: str) -> str:
    """
    Generate rate limit key
    """
    return f"rate_limit:{identifier}:{endpoint}"

# Security headers
def get_security_headers() -> Dict[str, str]:
    """
    Get security headers for responses
    """
    return {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "X-XSS-Protection": "1; mode=block",
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
        "Content-Security-Policy": (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self' data:; "
            "connect-src 'self' https: wss:;"
        )
    }

# File upload security
ALLOWED_EXTENSIONS = {
    'image': {'jpg', 'jpeg', 'png', 'gif', 'webp'},
    'audio': {'mp3', 'wav', 'ogg', 'm4a'},
    'video': {'mp4', 'webm', 'mov'},
    'document': {'pdf', 'txt', 'doc', 'docx'}
}

def is_allowed_file(filename: str, file_type: str) -> bool:
    """
    Check if file extension is allowed
    """
    if '.' not in filename:
        return False
    
    ext = filename.rsplit('.', 1)[1].lower()
    return ext in ALLOWED_EXTENSIONS.get(file_type, set())

def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename to prevent path traversal
    """
    # Keep only safe characters
    safe_chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_."
    safe_filename = ''.join(c for c in filename if c in safe_chars)
    
    # Remove path traversal attempts
    safe_filename = safe_filename.replace('..', '').replace('//', '').replace('\\', '')
    
    return safe_filename

def generate_secure_filename(original_filename: str) -> str:
    """
    Generate secure random filename
    """
    ext = original_filename.rsplit('.', 1)[1].lower() if '.' in original_filename else ''
    random_name = secrets.token_urlsafe(16)
    
    if ext and is_allowed_file(f"file.{ext}", 'image'):
        return f"{random_name}.{ext}"
    return random_name

# IP address utilities
def is_valid_ip(ip_address: str) -> bool:
    """
    Validate IP address
    """
    try:
        import ipaddress
        ipaddress.ip_address(ip_address)
        return True
    except ValueError:
        return False

def get_client_ip(request) -> str:
    """
    Get client IP address from request
    """
    # Try different headers
    headers = [
        'X-Real-IP',
        'X-Forwarded-For',
        'CF-Connecting-IP',
        'True-Client-IP'
    ]
    
    for header in headers:
        ip = request.headers.get(header)
        if ip and is_valid_ip(ip.split(',')[0].strip()):
            return ip.split(',')[0].strip()
    
    # Fallback to remote address
    return request.client.host if request.client else '0.0.0.0'

# Encryption utilities (for sensitive data)
def encrypt_data(data: str, key: Optional[str] = None) -> str:
    """
    Encrypt sensitive data
    """
    try:
        from cryptography.fernet import Fernet
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
        import base64
        
        if key is None:
            key = settings.SECRET_KEY
        
        # Derive key from secret
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b'matrxe_salt',
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(key.encode()))
        
        fernet = Fernet(key)
        encrypted = fernet.encrypt(data.encode())
        return encrypted.decode()
        
    except ImportError:
        logger.warning("cryptography not installed, using simple encryption")
        # Fallback to simple XOR encryption (not secure for production)
        import base64
        key = settings.SECRET_KEY.encode()
        encrypted = bytes([data[i] ^ key[i % len(key)] for i in range(len(data))])
        return base64.b64encode(encrypted).decode()

def decrypt_data(encrypted_data: str, key: Optional[str] = None) -> str:
    """
    Decrypt sensitive data
    """
    try:
        from cryptography.fernet import Fernet
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
        import base64
        
        if key is None:
            key = settings.SECRET_KEY
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b'matrxe_salt',
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(key.encode()))
        
        fernet = Fernet(key)
        decrypted = fernet.decrypt(encrypted_data.encode())
        return decrypted.decode()
        
    except ImportError:
        logger.warning("cryptography not installed, using simple decryption")
        import base64
        key = settings.SECRET_KEY.encode()
        encrypted = base64.b64decode(encrypted_data)
        decrypted = bytes([encrypted[i] ^ key[i % len(key)] for i in range(len(encrypted))])
        return decrypted.decode()

# Audit logging
def log_security_event(
    event_type: str,
    user_id: Optional[uuid.UUID] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None
):
    """
    Log security event
    """
    log_entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "event_type": event_type,
        "user_id": str(user_id) if user_id else None,
        "ip_address": ip_address,
        "user_agent": user_agent,
        "details": details or {}
    }
    
    logger.info(f"SECURITY_EVENT: {log_entry}")

# Password strength checker
def check_password_strength(password: str) -> Dict[str, Any]:
    """
    Check password strength
    """
    score = 0
    feedback = []
    
    # Length check
    if len(password) >= 12:
        score += 2
    elif len(password) >= 8:
        score += 1
    else:
        feedback.append("Password should be at least 8 characters long")
    
    # Complexity checks
    import re
    
    if re.search(r'[A-Z]', password):
        score += 1
    else:
        feedback.append("Add uppercase letters")
    
    if re.search(r'[a-z]', password):
        score += 1
    else:
        feedback.append("Add lowercase letters")
    
    if re.search(r'\d', password):
        score += 1
    else:
        feedback.append("Add numbers")
    
    if re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        score += 1
    else:
        feedback.append("Add special characters")
    
    # Common password check
    common_passwords = [
        'password', '123456', 'qwerty', 'admin', 'welcome',
        'password123', '123456789', '12345678', '12345'
    ]
    
    if password.lower() in common_passwords:
        score = 0
        feedback.append("Password is too common")
    
    # Determine strength level
    if score >= 5:
        strength = "strong"
    elif score >= 3:
        strength = "medium"
    else:
        strength = "weak"
    
    return {
        "score": score,
        "strength": strength,
        "feedback": feedback,
        "meets_requirements": score >= 3
    }

# Session management
def generate_session_id() -> str:
    """
    Generate secure session ID
    """
    return secrets.token_urlsafe(32)

def validate_session(session_id: str, user_id: uuid.UUID) -> bool:
    """
    Validate session (in production, check against database)
    """
    # This would typically check against a sessions table
    return True

# Two-factor authentication
def generate_totp_secret() -> str:
    """
    Generate TOTP secret for 2FA
    """
    import pyotp
    return pyotp.random_base32()

def generate_totp_qr_code(secret: str, email: str) -> str:
    """
    Generate QR code URI for TOTP
    """
    import pyotp
    totp = pyotp.TOTP(secret)
    return totp.provisioning_uri(name=email, issuer_name="MATRXe")

def verify_totp_code(secret: str, code: str) -> bool:
    """
    Verify TOTP code
    """
    import pyotp
    totp = pyotp.TOTP(secret)
    return totp.verify(code)

# Backup code generation
def generate_backup_codes(count: int = 10) -> list:
    """
    Generate backup codes for 2FA
    """
    codes = []
    for _ in range(count):
        code = f"{secrets.randbelow(1000000):06d}"
        codes.append({
            "code": code,
            "used": False,
            "created_at": datetime.utcnow()
        })
    return codes

# Security policy enforcement
class SecurityPolicy:
    """Security policy enforcement"""
    
    @staticmethod
    def enforce_password_policy(password: str) -> Dict[str, Any]:
        """
        Enforce password policy
        """
        result = check_password_strength(password)
        
        if not result["meets_requirements"]:
            raise ValueError(
                f"Password does not meet requirements: {', '.join(result['feedback'])}"
            )
        
        return result
    
    @staticmethod
    def enforce_rate_limit(identifier: str, endpoint: str) -> bool:
        """
        Check rate limit (simplified - implement with Redis in production)
        """
        # In production, use Redis for rate limiting
        return True
    
    @staticmethod
    def check_brute_force_protection(identifier: str) -> bool:
        """
        Check brute force protection
        """
        # In production, track failed attempts
        return True
    
    @staticmethod
    def validate_file_upload(file, max_size: int) -> bool:
        """
        Validate file upload
        """
        # Check file size
        if len(file) > max_size:
            return False
        
        # Check file type (simplified)
        # In production, use magic numbers or file type detection
        
        return True