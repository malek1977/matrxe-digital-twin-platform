#!/bin/bash

# ============================================
# سكربت إنشاء هيكل مشروع Digital Twin Platform
# النسخة العربية - MATRXe Platform
# ============================================

set -e  # إيقاف عند حدوث خطأ

# ألوان للواجهة
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# رسالة الترحيب
echo -e "${PURPLE}"
echo "========================================="
echo "   Digital Twin Platform Generator"
echo "        مولد منصة النسخ الرقمية"
echo "========================================="
echo -e "${NC}"

# التحقق من وجود اسم للمشروع
if [ $# -eq 0 ]; then
    PROJECT_NAME="digital-twin-platform"
else
    PROJECT_NAME="$1"
fi

echo -e "${YELLOW}⚡ جاري إنشاء مشروع: ${PROJECT_NAME}${NC}"
echo ""

# تأخير قصير للرؤية
sleep 2

# ============================================
# 1. إنشاء الهيكل الأساسي
# ============================================
echo -e "${BLUE}📁 الخطوة 1: إنشاء الهيكل الأساسي...${NC}"

# المجلد الرئيسي
mkdir -p "${PROJECT_NAME}"
cd "${PROJECT_NAME}"

# هيكل Backend
mkdir -p backend/app/{routes,services,utils}
mkdir -p backend/migrations

# هيكل Frontend
mkdir -p frontend/src/{components,pages,services,styles,utils,hooks,context}
mkdir -p frontend/public

# هيكل AI Models
mkdir -p ai_models/{voice_processing,face_processing,chat_ai,training_scripts,models}

# هيكل النشر
mkdir -p deployment/{config,scripts}

# هيكل التوثيق
mkdir -p documentation/{images,api,guides}

# هيكل قاعدة البيانات
mkdir -p database/migrations

# مجلدات إضافية
mkdir -p uploads/{images,audio,videos,documents}
mkdir -p logs/{backend,frontend,ai}
mkdir -p tests/{unit,integration,e2e}
mkdir -p scripts/{deployment,maintenance,backup}
mkdir -p config/{development,production,staging}

echo -e "${GREEN}✅ تم إنشاء الهيكل الأساسي${NC}"
echo ""

# ============================================
# 2. إنشاء ملفات Backend
# ============================================
echo -e "${BLUE}🐍 الخطوة 2: إنشاء ملفات Backend (Python/FastAPI)...${NC}"

# ملف Backend الرئيسي
cat > backend/app/main.py << 'EOF'
"""
Digital Twin Platform - Backend API
منصة النسخ الرقمية - واجهة البرمجة الرئيسية
"""

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from contextlib import asynccontextmanager
import uvicorn
import logging
from datetime import datetime

from app.routes import users, digital_twins, chat, billing, files
from app.database import engine, Base
from app.middleware.auth import AuthMiddleware

# إعداد التسجيل
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """إدارة دورة حياة التطبيق"""
    # عند البدء
    logger.info("🚀 Starting Digital Twin Platform...")
    
    # إنشاء جداول قاعدة البيانات
    async with engine.begin() as conn:
        # في الإنتاج، استخدم Alembic للتهجير
        await conn.run_sync(Base.metadata.create_all)
    
    yield
    
    # عند الإغلاق
    logger.info("🛑 Shutting down Digital Twin Platform...")

# إنشاء تطبيق FastAPI
app = FastAPI(
    title="Digital Twin Platform API",
    description="منصة متكاملة لإدارة النسخ الرقمية الذكية",
    version="1.0.0",
    contact={
        "name": "MATRXe Team",
        "email": "support@matrxe.com",
    },
    lifespan=lifespan
)

# إضافة Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # في الإنتاج، حدد النطاقات المسموحة
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"]  # في الإنتاج، حدد النطاقات المسموحة
)

# إضافة Auth Middleware
app.add_middleware(AuthMiddleware)

# تسجيل routes
app.include_router(users.router, prefix="/api/v1/users", tags=["المستخدمين"])
app.include_router(digital_twins.router, prefix="/api/v1/twins", tags=["النسخ الرقمية"])
app.include_router(chat.router, prefix="/api/v1/chat", tags=["المحادثات"])
app.include_router(billing.router, prefix="/api/v1/billing", tags=["الفواتير"])
app.include_router(files.router, prefix="/api/v1/files", tags=["الملفات"])

# نقاط النهاية الرئيسية
@app.get("/")
async def root():
    """النقطة الرئيسية للتطبيق"""
    return {
        "message": "مرحباً بك في منصة النسخ الرقمية",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/health")
async def health_check():
    """فحص صحة التطبيق"""
    return {
        "status": "healthy",
        "service": "digital-twin-platform",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/v1/status")
async def api_status():
    """حالة واجهة البرمجة"""
    return {
        "api_version": "1.0.0",
        "status": "operational",
        "uptime": "100%",
        "services": {
            "database": "connected",
            "ai_models": "ready",
            "storage": "available"
        }
    }

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
EOF

# ملف نماذج قاعدة البيانات
cat > backend/app/models.py << 'EOF'
"""
نماذج قاعدة البيانات لمنصة النسخ الرقمية
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float, Text, ForeignKey, JSON, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.sql import func
import enum
import uuid

Base = declarative_base()

# أنواع البيانات الثابتة
class UserRole(str, enum.Enum):
    USER = "user"
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"

class SubscriptionTier(str, enum.Enum):
    FREE = "free"
    BASIC = "basic"
    PRO = "pro"
    ENTERPRISE = "enterprise"

class DigitalTwinStatus(str, enum.Enum):
    DRAFT = "draft"
    TRAINING = "training"
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"

class MessageType(str, enum.Enum):
    TEXT = "text"
    AUDIO = "audio"
    IMAGE = "image"
    VIDEO = "video"
    SYSTEM = "system"

# النماذج
class User(Base):
    """نموذج المستخدم"""
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(100), unique=True, nullable=False)
    full_name = Column(String(255))
    phone = Column(String(20))
    password_hash = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), default=UserRole.USER)
    
    # الملف الشخصي
    avatar_url = Column(String(500))
    bio = Column(Text)
    company = Column(String(255))
    job_title = Column(String(255))
    
    # الإعدادات
    language_code = Column(String(10), default="ar")
    timezone = Column(String(50), default="UTC")
    theme = Column(String(20), default="dark")
    email_verified = Column(Boolean, default=False)
    two_factor_enabled = Column(Boolean, default=False)
    two_factor_secret = Column(String(255))
    
    # نظام الائتمانات
    total_credits = Column(Integer, default=1000)  # رصيد مجاني ابتدائي
    used_credits = Column(Integer, default=0)
    subscription_tier = Column(Enum(SubscriptionTier), default=SubscriptionTier.FREE)
    
    # الأمان
    last_login = Column(DateTime)
    login_attempts = Column(Integer, default=0)
    locked_until = Column(DateTime)
    
    # التواريخ
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    deleted_at = Column(DateTime)
    
    # العلاقات
    digital_twins = relationship("DigitalTwin", back_populates="user")
    conversations = relationship("Conversation", back_populates="user")
    
    def __repr__(self):
        return f"<User(id={self.id}, email={self.email}, role={self.role})>"

class DigitalTwin(Base):
    """نموذج النسخة الرقمية"""
    __tablename__ = "digital_twins"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    
    # الشخصية
    personality_profile = Column(JSON)  # سمات الشخصية، نمط الحديث
    voice_settings = Column(JSON)      # إعدادات الصوت
    appearance_settings = Column(JSON) # إعدادات المظهر
    behavior_patterns = Column(JSON)   # أنماط السلوك
    
    # التدريب
    training_data = Column(JSON)       # بيانات التدريب
    training_status = Column(Enum(DigitalTwinStatus), default=DigitalTwinStatus.DRAFT)
    training_progress = Column(Float, default=0.0)  # 0-100%
    training_error = Column(Text)      # أخطاء التدريب
    trained_at = Column(DateTime)      # تاريخ الانتهاء من التدريب
    model_version = Column(String(50)) # إصدار النموذج
    
    # الإعدادات
    is_public = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    tags = Column(JSON, default=list)
    metadata = Column(JSON, default=dict)
    
    # الاستخدام
    total_conversations = Column(Integer, default=0)
    total_messages = Column(Integer, default=0)
    last_active = Column(DateTime)
    
    # التواريخ
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # العلاقات
    user = relationship("User", back_populates="digital_twins")
    conversations = relationship("Conversation", back_populates="digital_twin")
    
    def __repr__(self):
        return f"<DigitalTwin(id={self.id}, name={self.name}, status={self.training_status})>"

class Conversation(Base):
    """نموذج المحادثة"""
    __tablename__ = "conversations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    digital_twin_id = Column(UUID(as_uuid=True), ForeignKey("digital_twins.id"), nullable=True)
    
    # معلومات المحادثة
    title = Column(String(255))
    context = Column(JSON)      # سياق المحادثة
    language = Column(String(10), default="ar")
    
    # الحالة
    is_active = Column(Boolean, default=True)
    is_archived = Column(Boolean, default=False)
    
    # المقاييس
    message_count = Column(Integer, default=0)
    token_count = Column(Integer, default=0)  # عدد tokens المستخدمة
    total_cost = Column(Float, default=0.0)   # التكلفة بالائتمانات
    
    # التواريخ
    started_at = Column(DateTime, default=func.now())
    last_message_at = Column(DateTime)
    ended_at = Column(DateTime)
    
    # العلاقات
    user = relationship("User", back_populates="conversations")
    digital_twin = relationship("DigitalTwin", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation")
    
    def __repr__(self):
        return f"<Conversation(id={self.id}, user={self.user_id}, twin={self.digital_twin_id})>"

class Message(Base):
    """نموذج الرسالة"""
    __tablename__ = "messages"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("conversations.id"), nullable=False)
    
    # محتوى الرسالة
    content = Column(Text, nullable=False)
    message_type = Column(Enum(MessageType), default=MessageType.TEXT)
    media_url = Column(String(500))  # رابط الملف الوسائط
    metadata = Column(JSON)          # بيانات إضافية
    
    # معلومات المرسل
    sender_type = Column(String(20))  # 'user' أو 'twin' أو 'system'
    sender_id = Column(UUID(as_uuid=True))
    
    # توليد الذكاء الاصطناعي
    ai_model = Column(String(50))     # النموذج المستخدم
    tokens_used = Column(Integer)     # عدد tokens
    generation_time = Column(Float)   # وقت التوليد بالثواني
    
    # الإشراف
    is_flagged = Column(Boolean, default=False)
    moderation_score = Column(Float)
    
    # التواريخ
    created_at = Column(DateTime, default=func.now())
    read_at = Column(DateTime)
    
    # العلاقات
    conversation = relationship("Conversation", back_populates="messages")
    
    def __repr__(self):
        return f"<Message(id={self.id}, conversation={self.conversation_id}, type={self.message_type})>"

class CreditTransaction(Base):
    """نموذج معاملة الائتمان"""
    __tablename__ = "credit_transactions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    # تفاصيل المعاملة
    transaction_type = Column(String(50))  # 'purchase', 'usage', 'refund', 'bonus'
    credits_amount = Column(Integer, nullable=False)
    description = Column(Text)
    
    # معلومات الدفع
    payment_method = Column(String(50))
    payment_reference = Column(String(255))
    amount_paid = Column(Float)      # المبلغ المالي
    currency = Column(String(3), default="USD")
    
    # الحالة
    status = Column(String(20), default="completed")  # 'pending', 'completed', 'failed'
    
    # التواريخ
    created_at = Column(DateTime, default=func.now())
    processed_at = Column(DateTime)
    
    # العلاقات
    user = relationship("User")
    
    def __repr__(self):
        return f"<CreditTransaction(id={self.id}, user={self.user_id}, type={self.transaction_type})>"
EOF

# ملف routes للمستخدمين
cat > backend/app/routes/users.py << 'EOF'
"""
واجهات API لإدارة المستخدمين
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.database import get_db
from app.models import User
from app.schemas.user import UserCreate, UserUpdate, UserResponse
from app.services.auth import AuthService
from app.middleware.auth import get_current_user

router = APIRouter()

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db)
):
    """تسجيل مستخدم جديد"""
    auth_service = AuthService(db)
    
    # التحقق من وجود المستخدم
    existing_user = await auth_service.get_user_by_email(user_data.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="البريد الإلكتروني مسجل مسبقاً"
        )
    
    # إنشاء المستخدم
    user = await auth_service.create_user(user_data)
    
    return {
        "id": user.id,
        "email": user.email,
        "username": user.username,
        "full_name": user.full_name,
        "role": user.role,
        "created_at": user.created_at
    }

@router.post("/login")
async def login(
    email: str,
    password: str,
    db: AsyncSession = Depends(get_db)
):
    """تسجيل الدخول"""
    auth_service = AuthService(db)
    
    # التحقق من بيانات الدخول
    user = await auth_service.authenticate_user(email, password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="البريد الإلكتروني أو كلمة المرور غير صحيحة"
        )
    
    # إنشاء token
    access_token = auth_service.create_access_token({"sub": str(user.id)})
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "username": user.username,
            "full_name": user.full_name
        }
    }

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """الحصول على معلومات المستخدم الحالي"""
    return {
        "id": current_user.id,
        "email": current_user.email,
        "username": current_user.username,
        "full_name": current_user.full_name,
        "role": current_user.role,
        "avatar_url": current_user.avatar_url,
        "total_credits": current_user.total_credits,
        "used_credits": current_user.used_credits,
        "created_at": current_user.created_at
    }

@router.put("/me", response_model=UserResponse)
async def update_user_info(
    user_data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """تحديث معلومات المستخدم"""
    from sqlalchemy import update
    
    # تحديث الحقول المطلوبة فقط
    update_data = user_data.dict(exclude_unset=True)
    
    if update_data:
        stmt = (
            update(User)
            .where(User.id == current_user.id)
            .values(**update_data)
            .execution_options(synchronize_session="fetch")
        )
        
        await db.execute(stmt)
        await db.commit()
        
        # إعادة تحميل المستخدم
        await db.refresh(current_user)
    
    return current_user

@router.get("/{user_id}", response_model=UserResponse)
async def get_user_by_id(
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """الحصول على معلومات مستخدم بواسطة ID"""
    from sqlalchemy import select
    import uuid
    
    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="معرف المستخدم غير صالح"
        )
    
    stmt = select(User).where(User.id == user_uuid)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="المستخدم غير موجود"
        )
    
    # التحقق من الصلاحيات (المسؤول فقط يمكنه رؤية جميع المستخدمين)
    if current_user.role not in ["admin", "super_admin"] and user.id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="ليس لديك صلاحية لعرض معلومات هذا المستخدم"
        )
    
    return user

@router.get("/", response_model=List[UserResponse])
async def list_users(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """قائمة المستخدمين (للمسؤولين فقط)"""
    if current_user.role not in ["admin", "super_admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="الصلاحية مطلوبة لعرض قائمة المستخدمين"
        )
    
    from sqlalchemy import select
    
    stmt = select(User).offset(skip).limit(limit)
    result = await db.execute(stmt)
    users = result.scalars().all()
    
    return users

@router.delete("/{user_id}")
async def delete_user(
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """حذف مستخدم (للمسؤولين فقط)"""
    if current_user.role != "super_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="صلاحية المشرف المطلوبة لحذف المستخدمين"
        )
    
    from sqlalchemy import select, delete
    import uuid
    
    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="معرف المستخدم غير صالح"
        )
    
    # التحقق من عدم حذف المستخدم الحالي
    if user_uuid == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="لا يمكنك حذف حسابك الخاص"
        )
    
    # حذف المستخدم
    stmt = delete(User).where(User.id == user_uuid)
    result = await db.execute(stmt)
    await db.commit()
    
    if result.rowcount == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="المستخدم غير موجود"
        )
    
    return {"message": "تم حذف المستخدم بنجاح"}
EOF

# ملف routes للنسخ الرقمية
cat > backend/app/routes/digital_twins.py << 'EOF'
"""
واجهات API لإدارة النسخ الرقمية
"""

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
import uuid

from app.database import get_db
from app.models import User, DigitalTwin, DigitalTwinStatus
from app.schemas.digital_twin import DigitalTwinCreate, DigitalTwinUpdate, DigitalTwinResponse
from app.services.digital_twin_service import DigitalTwinService
from app.middleware.auth import get_current_user

router = APIRouter()

@router.post("/", response_model=DigitalTwinResponse, status_code=status.HTTP_201_CREATED)
async def create_digital_twin(
    twin_data: DigitalTwinCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """إنشاء نسخة رقمية جديدة"""
    twin_service = DigitalTwinService(db)
    
    # إنشاء النسخة الرقمية
    twin = await twin_service.create_digital_twin(
        user_id=current_user.id,
        name=twin_data.name,
        description=twin_data.description,
        personality_profile=twin_data.personality_profile,
        is_public=twin_data.is_public
    )
    
    return {
        "id": twin.id,
        "name": twin.name,
        "description": twin.description,
        "training_status": twin.training_status,
        "is_public": twin.is_public,
        "created_at": twin.created_at
    }

@router.get("/", response_model=List[DigitalTwinResponse])
async def list_digital_twins(
    skip: int = 0,
    limit: int = 50,
    public_only: bool = False,
    current_user: Optional[User] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """قائمة النسخ الرقمية"""
    from sqlalchemy import select, or_
    
    if public_only:
        # النسخ الرقمية العامة فقط
        stmt = select(DigitalTwin).where(
            DigitalTwin.is_public == True,
            DigitalTwin.training_status == DigitalTwinStatus.ACTIVE
        )
    elif current_user:
        # نسخ المستخدم الحالي + العامة
        stmt = select(DigitalTwin).where(
            or_(
                DigitalTwin.user_id == current_user.id,
                DigitalTwin.is_public == True
            )
        )
    else:
        # فقط العامة للزوار
        stmt = select(DigitalTwin).where(
            DigitalTwin.is_public == True,
            DigitalTwin.training_status == DigitalTwinStatus.ACTIVE
        )
    
    stmt = stmt.offset(skip).limit(limit).order_by(DigitalTwin.created_at.desc())
    result = await db.execute(stmt)
    twins = result.scalars().all()
    
    return twins

@router.get("/{twin_id}", response_model=DigitalTwinResponse)
async def get_digital_twin(
    twin_id: str,
    current_user: Optional[User] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """الحصول على نسخة رقمية بواسطة ID"""
    from sqlalchemy import select
    import uuid
    
    try:
        twin_uuid = uuid.UUID(twin_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="معرف النسخة الرقمية غير صالح"
        )
    
    stmt = select(DigitalTwin).where(DigitalTwin.id == twin_uuid)
    result = await db.execute(stmt)
    twin = result.scalar_one_or_none()
    
    if not twin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="النسخة الرقمية غير موجودة"
        )
    
    # التحقق من الصلاحيات
    if not twin.is_public and (not current_user or twin.user_id != current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="ليس لديك صلاحية لعرض هذه النسخة الرقمية"
        )
    
    return twin

@router.put("/{twin_id}", response_model=DigitalTwinResponse)
async def update_digital_twin(
    twin_id: str,
    twin_data: DigitalTwinUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """تحديث نسخة رقمية"""
    from sqlalchemy import select, update
    
    try:
        twin_uuid = uuid.UUID(twin_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="معرف النسخة الرقمية غير صالح"
        )
    
    # التحقق من الملكية
    stmt = select(DigitalTwin).where(
        DigitalTwin.id == twin_uuid,
        DigitalTwin.user_id == current_user.id
    )
    result = await db.execute(stmt)
    twin = result.scalar_one_or_none()
    
    if not twin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="النسخة الرقمية غير موجودة أو ليس لديك صلاحية لتعديلها"
        )
    
    # تحديث البيانات
    update_dict = twin_data.dict(exclude_unset=True)
    if update_dict:
        stmt = (
            update(DigitalTwin)
            .where(DigitalTwin.id == twin_uuid)
            .values(**update_dict)
            .execution_options(synchronize_session="fetch")
        )
        
        await db.execute(stmt)
        await db.commit()
        
        # إعادة تحميل البيانات
        await db.refresh(twin)
    
    return twin

@router.delete("/{twin_id}")
async def delete_digital_twin(
    twin_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """حذف نسخة رقمية"""
    from sqlalchemy import select, delete
    
    try:
        twin_uuid = uuid.UUID(twin_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="معرف النسخة الرقمية غير صالح"
        )
    
    # التحقق من الملكية
    stmt = select(DigitalTwin).where(
        DigitalTwin.id == twin_uuid,
        DigitalTwin.user_id == current_user.id
    )
    result = await db.execute(stmt)
    twin = result.scalar_one_or_none()
    
    if not twin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="النسخة الرقمية غير موجودة أو ليس لديك صلاحية لحذفها"
        )
    
    # حذف النسخة الرقمية
    stmt = delete(DigitalTwin).where(DigitalTwin.id == twin_uuid)
    await db.execute(stmt)
    await db.commit()
    
    return {"message": "تم حذف النسخة الرقمية بنجاح"}

@router.post("/{twin_id}/train")
async def train_digital_twin(
    twin_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """بدء تدريب النسخة الرقمية"""
    twin_service = DigitalTwinService(db)
    
    try:
        twin_uuid = uuid.UUID(twin_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="معرف النسخة الرقمية غير صالح"
        )
    
    # بدء التدريب
    result = await twin_service.start_training(twin_uuid, current_user.id)
    
    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["error"]
        )
    
    return {
        "message": "تم بدء تدريب النسخة الرقمية",
        "training_id": result["training_id"],
        "estimated_time": result["estimated_time"]
    }

@router.post("/{twin_id}/upload-training-data")
async def upload_training_data(
    twin_id: str,
    file: UploadFile = File(...),
    data_type: str = Form(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """رفع بيانات تدريب للنسخة الرقمية"""
    twin_service = DigitalTwinService(db)
    
    try:
        twin_uuid = uuid.UUID(twin_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="معرف النسخة الرقمية غير صالح"
        )
    
    # قراءة الملف
    content = await file.read()
    
    # رفع بيانات التدريب
    result = await twin_service.upload_training_data(
        twin_id=twin_uuid,
        user_id=current_user.id,
        data_type=data_type,
        content=content,
        filename=file.filename
    )
    
    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["error"]
        )
    
    return {
        "message": "تم رفع بيانات التدريب بنجاح",
        "file_id": result["file_id"],
        "data_type": data_type
    }

@router.get("/{twin_id}/training-status")
async def get_training_status(
    twin_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """الحصول على حالة تدريب النسخة الرقمية"""
    from sqlalchemy import select
    
    try:
        twin_uuid = uuid.UUID(twin_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="معرف النسخة الرقمية غير صالح"
        )
    
    stmt = select(DigitalTwin).where(
        DigitalTwin.id == twin_uuid,
        DigitalTwin.user_id == current_user.id
    )
    result = await db.execute(stmt)
    twin = result.scalar_one_or_none()
    
    if not twin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="النسخة الرقمية غير موجودة"
        )
    
    return {
        "training_status": twin.training_status,
        "training_progress": twin.training_progress,
        "training_error": twin.training_error,
        "trained_at": twin.trained_at
    }
EOF

# ملف requirements.txt
cat > backend/requirements.txt << 'EOF'
# Python Backend Requirements
# متطلبات Backend ببايثون

fastapi==0.104.1
uvicorn[standard]==0.24.0
sqlalchemy==2.0.23
asyncpg==0.29.0
alembic==1.13.1
python-dotenv==1.0.0
python-multipart==0.0.6
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
pydantic==2.5.0
pydantic-settings==2.1.0

# AI & Machine Learning
openai==1.3.0
transformers==4.36.0
torch==2.1.0
numpy==1.24.3
pandas==2.1.4
scikit-learn==1.3.2

# File Processing
Pillow==10.1.0
python-magic==0.4.27
aiofiles==23.2.1

# Email
jinja2==3.1.2
emails==0.6.0

# Redis
redis==5.0.1
aioredis==2.0.1

# HTTP Client
httpx==0.25.1

# Utils
python-dateutil==2.8.2
pytz==2023.3
tzlocal==5.2

# Development
pytest==7.4.3
pytest-asyncio==0.21.1
black==23.11.0
flake8==6.1.0

# Arabic Support
arabic-reshaper==3.0.0
python-bidi==0.4.2
EOF

# ملف Dockerfile للـ Backend
cat > backend/Dockerfile << 'EOF'
# Dockerfile for Digital Twin Platform Backend
# صورة Backend لمنصة النسخ الرقمية

FROM python:3.11-slim

LABEL maintainer="MATRXe Team <support@matrxe.com>"
LABEL description="Digital Twin Platform Backend API"

# تعيين متغيرات البيئة
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# تثبيت الاعتمادات النظامية
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# نسخ متطلبات بايثون
COPY requirements.txt .

# تثبيت متطلبات بايثون
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# نسخ التطبيق
COPY . .

# إنشاء مستخدم غير root
RUN useradd -m -u 1000 matrxe && \
    chown -R matrxe:matrxe /app

USER matrxe

# إنشاء مجلدات ضرورية
RUN mkdir -p /app/uploads /app/logs /app/temp

# المنفذ المعرض
EXPOSE 8000

# أمر التشغيل
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
EOF

# ملف .env.example
cat > backend/.env.example << 'EOF'
# Digital Twin Platform - Environment Configuration
# إعدادات البيئة لمنصة النسخ الرقمية

# ================ Application ================
APP_NAME="Digital Twin Platform"
APP_VERSION="1.0.0"
ENVIRONMENT="development"  # development, staging, production
DEBUG=true
SECRET_KEY="your-secret-key-change-this-in-production"
ALGORITHM="HS256"
ACCESS_TOKEN_EXPIRE_MINUTES=1440  # 24 hours

# ================ Database ================
DATABASE_URL="postgresql+asyncpg://matrxe:password@localhost/matrxe_db"
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=40

# ================ Redis ================
REDIS_URL="redis://localhost:6379/0"
REDIS_POOL_SIZE=10

# ================ AI Services ================
OPENAI_API_KEY="your-openai-api-key"
OLLAMA_BASE_URL="http://localhost:11434"
ELEVENLABS_API_KEY="your-elevenlabs-api-key"
HUGGINGFACE_TOKEN="your-huggingface-token"

# ================ File Storage ================
UPLOAD_DIR="/app/uploads"
MAX_UPLOAD_SIZE=104857600  # 100MB
ALLOWED_EXTENSIONS="jpg,jpeg,png,gif,webp,mp3,wav,ogg,m4a,mp4,webm,pdf,txt"

# ================ Email ================
SMTP_HOST="smtp.gmail.com"
SMTP_PORT=587
SMTP_USER="your-email@gmail.com"
SMTP_PASSWORD="your-app-password"
EMAIL_FROM="noreply@matrxe.com"

# ================ CORS ================
CORS_ORIGINS="http://localhost:3000,http://localhost:8000"

# ================ Billing ================
CREDIT_PRICE=0.01  # $0.01 per credit
DEFAULT_CURRENCY="USD"
TRIAL_DAYS=14
TRIAL_CREDITS=1000

# ================ Security ================
PASSWORD_MIN_LENGTH=8
RATE_LIMIT_ENABLED=true
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_PERIOD=60  # seconds

# ================ Monitoring ================
LOG_LEVEL="INFO"
SENTRY_DSN=""
EOF

echo -e "${GREEN}✅ تم إنشاء ملفات Backend${NC}"
echo ""

# ============================================
# 3. إنشاء ملفات Frontend
# ============================================
echo -e "${BLUE}⚛️  الخطوة 3: إنشاء ملفات Frontend (React/TypeScript)...${NC}"

# ملف package.json
cat > frontend/package.json << 'EOF'
{
  "name": "digital-twin-platform-frontend",
  "version": "1.0.0",
  "private": true,
  "description": "Digital Twin Platform Frontend - React Application",
  "author": "MATRxe Team <support@matrxe.com>",
  "license": "MIT",
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "lint": "eslint . --ext ts,tsx --report-unused-disable-directives --max-warnings 0",
    "preview": "vite preview",
    "format": "prettier --write \"src/**/*.{ts,tsx,css}\"",
    "test": "vitest",
    "test:ui": "vitest --ui",
    "test:coverage": "vitest --coverage"
  },
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-router-dom": "^6.20.0",
    "@tanstack/react-query": "^5.12.0",
    "axios": "^1.6.2",
    "zustand": "^4.4.7",
    "framer-motion": "^10.16.5",
    "react-hook-form": "^7.48.2",
    "@hookform/resolvers": "^3.3.2",
    "zod": "^3.22.4",
    "socket.io-client": "^4.7.2",
    "i18next": "^23.7.0",
    "react-i18next": "^13.2.2",
    "date-fns": "^3.0.6",
    "chart.js": "^4.4.0",
    "react-chartjs-2": "^5.2.0",
    "lucide-react": "^0.292.0",
    "sonner": "^1.2.0",
    "react-dropzone": "^14.2.3",
    "react-hot-toast": "^2.4.1",
    "react-markdown": "^9.0.1",
    "remark-gfm": "^14.0.0",
    "tailwind-merge": "^2.0.0",
    "class-variance-authority": "^0.7.0",
    "clsx": "^2.0.0"
  },
  "devDependencies": {
    "@types/react": "^18.2.37",
    "@types/react-dom": "^18.2.15",
    "@typescript-eslint/eslint-plugin": "^6.13.2",
    "@typescript-eslint/parser": "^6.13.2",
    "@vitejs/plugin-react": "^4.2.0",
    "autoprefixer": "^10.4.16",
    "eslint": "^8.54.0",
    "eslint-plugin-react": "^7.33.2",
    "eslint-plugin-react-hooks": "^4.6.0",
    "eslint-plugin-react-refresh": "^0.4.4",
    "postcss": "^8.4.32",
    "tailwindcss": "^3.3.6",
    "typescript": "^5.3.2",
    "vite": "^5.0.5",
    "vitest": "^1.0.4",
    "@vitest/ui": "^1.0.4",
    "jsdom": "^23.0.0",
    "@testing-library/react": "^14.1.0",
    "@testing-library/jest-dom": "^6.1.5",
    "prettier": "^3.1.0"
  },
  "browserslist": {
    "production": [
      ">0.2%",
      "not dead",
      "not op_mini all"
    ],
    "development": [
      "last 1 chrome version",
      "last 1 firefox version",
      "last 1 safari version"
    ]
  }
}
EOF

# ملف App.tsx الرئيسي
cat > frontend/src/App.tsx << 'EOF'
import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Toaster } from 'sonner';
import { ThemeProvider } from './contexts/ThemeContext';
import { AuthProvider } from './contexts/AuthContext';
import Layout from './components/layout/Layout';

// الصفحات
import HomePage from './pages/HomePage';
import LoginPage from './pages/auth/LoginPage';
import RegisterPage from './pages/auth/RegisterPage';
import DashboardPage from './pages/dashboard/DashboardPage';
import DigitalTwinsPage from './pages/digital-twins/DigitalTwinsPage';
import ChatPage from './pages/chat/ChatPage';
import BillingPage from './pages/billing/BillingPage';
import SettingsPage from './pages/settings/SettingsPage';
import AdminPage from './pages/admin/AdminPage';

// أنماط
import './styles/globals.css';

// إعداد React Query
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5, // 5 دقائق
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider>
        <AuthProvider>
          <Router>
            <div className="min-h-screen bg-gradient-to-br from-gray-900 to-black text-white">
              <Toaster 
                position="top-right"
                toastOptions={{
                  className: 'bg-gray-800 text-white border border-gray-700',
                  duration: 4000,
                }}
              />
              
              <Routes>
                {/* الصفحة الرئيسية */}
                <Route path="/" element={<HomePage />} />
                
                {/* المصادقة */}
                <Route path="/login" element={<LoginPage />} />
                <Route path="/register" element={<RegisterPage />} />
                
                {/* التطبيق الرئيسي (تحتاج مصادقة) */}
                <Route path="/app" element={<Layout />}>
                  <Route index element={<Navigate to="/app/dashboard" replace />} />
                  <Route path="dashboard" element={<DashboardPage />} />
                  <Route path="digital-twins" element={<DigitalTwinsPage />} />
                  <Route path="chat" element={<ChatPage />} />
                  <Route path="billing" element={<BillingPage />} />
                  <Route path="settings" element={<SettingsPage />} />
                  <Route path="admin" element={<AdminPage />} />
                </Route>
                
                {/* الصفحة غير موجودة */}
                <Route path="*" element={
                  <div className="flex items-center justify-center min-h-screen">
                    <div className="text-center">
                      <h1 className="text-4xl font-bold mb-4">404</h1>
                      <p className="text-gray-400 mb-6">الصفحة غير موجودة</p>
                      <a 
                        href="/" 
                        className="px-6 py-3 bg-gradient-to-r from-purple-600 to-pink-600 rounded-lg hover:opacity-90 transition-opacity"
                      >
                        العودة للرئيسية
                      </a>
                    </div>
                  </div>
                } />
              </Routes>
            </div>
          </Router>
        </AuthProvider>
      </ThemeProvider>
    </QueryClientProvider>
  );
}

export default App;
EOF

# ملف الصفحة الرئيسية
cat > frontend/src/pages/HomePage.tsx << 'EOF'
import React from 'react';
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { 
  Brain, 
  MessageSquare, 
  Users, 
  Zap, 
  Shield, 
  Globe,
  ArrowRight,
  Sparkles
} from 'lucide-react';
import Navbar from '../components/layout/Navbar';
import Footer from '../components/layout/Footer';

const HomePage: React.FC = () => {
  const features = [
    {
      icon: <Brain className="w-8 h-8" />,
      title: 'نسخ رقمية ذكية',
      description: 'أنشئ نسخاً رقمية ذكية تتعلم من سلوكك وتتفاعل بشكل طبيعي',
      color: 'from-purple-500 to-pink-500'
    },
    {
      icon: <MessageSquare className="w-8 h-8" />,
      title: 'محادثات طبيعية',
      description: 'تفاعل مع نسخك الرقمية بمحادثات صوتية وكتابية طبيعية',
      color: 'from-blue-500 to-cyan-500'
    },
    {
      icon: <Users className="w-8 h-8" />,
      title: 'مجتمع عالمي',
      description: 'شارك نسخك الرقمية وتفاعل مع نسخ الآخرين حول العالم',
      color: 'from-green-500 to-emerald-500'
    },
    {
      icon: <Zap className="w-8 h-8" />,
      title: 'سرعة فائقة',
      description: 'استجابات فورية باستخدام أحدث تقنيات الذكاء الاصطناعي',
      color: 'from-yellow-500 to-orange-500'
    },
    {
      icon: <Shield className="w-8 h-8" />,
      title: 'أمان تام',
      description: 'بياناتك مشفرة ومحمية بأعلى معايير الأمان والخصوصية',
      color: 'from-red-500 to-rose-500'
    },
    {
      icon: <Globe className="w-8 h-8" />,
      title: 'دعم عربي',
      description: 'واجهة ودعم فني باللغة العربية، مدعوم بتقنيات محلية',
      color: 'from-indigo-500 to-violet-500'
    }
  ];

  return (
    <>
      <Navbar />
      
      {/* Hero Section */}
      <section className="relative overflow-hidden pt-24 pb-20">
        <div className="absolute inset-0 bg-gradient-to-br from-purple-900/20 via-transparent to-pink-900/20" />
        
        <div className="container mx-auto px-4 relative z-10">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            className="text-center max-w-4xl mx-auto"
          >
            <div className="inline-flex items-center gap-2 mb-6 px-4 py-2 bg-gray-800 rounded-full">
              <Sparkles className="w-4 h-4 text-yellow-400" />
              <span className="text-sm font-medium">منصة النسخ الرقمية الرائدة عربياً</span>
            </div>
            
            <h1 className="text-5xl md:text-7xl font-bold mb-6 bg-gradient-to-r from-purple-400 to-pink-400 bg-clip-text text-transparent">
              أنشئ نسختك الرقمية
              <span className="block mt-2">بكل سهولة</span>
            </h1>
            
            <p className="text-xl text-gray-300 mb-10 max-w-2xl mx-auto">
              منصة متكاملة لإنشاء وإدارة وتفاعل النسخ الرقمية الذكية باللغة العربية.
              اجعل الذكاء الاصطناعي يتحدث بلغتك ويفهم ثقافتك.
            </p>
            
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <Link
                to="/register"
                className="px-8 py-4 bg-gradient-to-r from-purple-600 to-pink-600 text-white rounded-xl font-semibold hover:opacity-90 transition-opacity flex items-center justify-center gap-2"
              >
                ابدأ مجاناً
                <ArrowRight className="w-5 h-5" />
              </Link>
              
              <Link
                to="/login"
                className="px-8 py-4 bg-gray-800 text-white rounded-xl font-semibold hover:bg-gray-700 transition-colors border border-gray-700"
              >
                تسجيل الدخول
              </Link>
            </div>
          </motion.div>
        </div>
      </section>

      {/* Features Section */}
      <section className="py-20 bg-gradient-to-b from-transparent to-gray-900/50">
        <div className="container mx-auto px-4">
          <h2 className="text-4xl font-bold text-center mb-4">
            ميزات منصتنا
          </h2>
          <p className="text-gray-400 text-center mb-12 max-w-2xl mx-auto">
            نقدم لك تجربة فريدة في عالم النسخ الرقمية بأحدث التقنيات وأسهل الواجهات
          </p>
          
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
            {features.map((feature, index) => (
              <motion.div
                key={index}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5, delay: index * 0.1 }}
                className="bg-gray-800/50 backdrop-blur-sm rounded-2xl p-6 border border-gray-700 hover:border-gray-600 transition-colors group"
              >
                <div className={`w-14 h-14 rounded-xl bg-gradient-to-r ${feature.color} p-3 mb-6 group-hover:scale-110 transition-transform`}>
                  <div className="text-white">
                    {feature.icon}
                  </div>
                </div>
                
                <h3 className="text-xl font-bold mb-3">
                  {feature.title}
                </h3>
                
                <p className="text-gray-400">
                  {feature.description}
                </p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-20">
        <div className="container mx-auto px-4">
          <div className="max-w-4xl mx-auto bg-gradient-to-r from-purple-900/30 to-pink-900/30 rounded-3xl p-8 md:p-12 border border-purple-700/50">
            <div className="flex flex-col md:flex-row items-center justify-between gap-8">
              <div>
                <h2 className="text-3xl font-bold mb-4">
                  مستعد لبدء رحلتك مع النسخ الرقمية؟
                </h2>
                <p className="text-gray-300">
                  انضم إلى آلاف المستخدمين الذين بدأوا بالفعل في بناء عالمهم الرقمي
                </p>
              </div>
              
              <div className="flex flex-col sm:flex-row gap-4">
                <Link
                  to="/register"
                  className="px-8 py-4 bg-white text-purple-600 rounded-xl font-bold hover:bg-gray-100 transition-colors text-center"
                >
                  سجل مجاناً
                </Link>
                
                <Link
                  to="/login"
                  className="px-8 py-4 bg-transparent text-white rounded-xl font-bold hover:bg-white/10 transition-colors text-center border border-white/30"
                >
                  عرض نسخة تجريبية
                </Link>
              </div>
            </div>
          </div>
        </div>
      </section>

      <Footer />
    </>
  );
};

export default HomePage;
EOF

# ملف Dashboard
cat > frontend/src/pages/dashboard/DashboardPage.tsx << 'EOF'
import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { 
  Users, 
  MessageSquare, 
  Brain, 
  Zap, 
  TrendingUp, 
  Calendar,
  Activity,
  Clock,
  Rocket,
  Sparkles
} from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import StatCard from '../../components/dashboard/StatCard';
import QuickActions from '../../components/dashboard/QuickActions';
import RecentActivity from '../../components/dashboard/RecentActivity';
import UsageChart from '../../components/dashboard/UsageChart';
import { dashboardService } from '../../services/api/dashboard';

const DashboardPage: React.FC = () => {
  const [timeRange, setTimeRange] = useState<'day' | 'week' | 'month'>('week');

  // Fetch dashboard data
  const { data: dashboardData, isLoading } = useQuery({
    queryKey: ['dashboard', timeRange],
    queryFn: () => dashboardService.getDashboardData(timeRange),
  });

  // Stats data
  const stats = [
    {
      title: 'النسخ الرقمية',
      value: dashboardData?.twinsCount || 0,
      change: dashboardData?.twinsGrowth || 0,
      icon: <Users className="w-5 h-5" />,
      color: 'purple',
      link: '/app/digital-twins'
    },
    {
      title: 'المحادثات النشطة',
      value: dashboardData?.activeConversations || 0,
      change: dashboardData?.conversationsGrowth || 0,
      icon: <MessageSquare className="w-5 h-5" />,
      color: 'blue',
      link: '/app/chat'
    },
    {
      title: 'الائتمانات المتبقية',
      value: dashboardData?.creditsRemaining || 0,
      change: dashboardData?.creditsUsed || 0,
      icon: <Zap className="w-5 h-5" />,
      color: 'yellow',
      link: '/app/billing'
    },
    {
      title: 'النماذج المدربة',
      value: dashboardData?.trainedModels || 0,
      change: dashboardData?.modelsGrowth || 0,
      icon: <Brain className="w-5 h-5" />,
      color: 'green',
      link: '/app/digital-twins'
    }
  ];

  // Quick actions
  const quickActions = [
    {
      title: 'إنشاء نسخة رقمية',
      description: 'ابدأ بإنشاء نسختك الرقمية الأولى',
      icon: <Sparkles className="w-5 h-5" />,
      color: 'purple',
      action: () => window.location.href = '/app/digital-twins/create',
      disabled: false
    },
    {
      title: 'بدء محادثة',
      description: 'تحدث مع إحدى نسخك الرقمية',
      icon: <MessageSquare className="w-5 h-5" />,
      color: 'blue',
      action: () => window.location.href = '/app/chat',
      disabled: !dashboardData?.twinsCount
    },
    {
      title: 'إضافة ائتمانات',
      description: 'اشحن رصيدك لمواصلة الاستخدام',
      icon: <Zap className="w-5 h-5" />,
      color: 'yellow',
      action: () => window.location.href = '/app/billing',
      disabled: false
    },
    {
      title: 'تدريب نموذج',
      description: 'حسن أداء نسختك الرقمية',
      icon: <Brain className="w-5 h-5" />,
      color: 'green',
      action: () => window.location.href = '/app/digital-twins/train',
      disabled: !dashboardData?.twinsCount
    }
  ];

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <div className="w-16 h-16 border-4 border-purple-600 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-gray-400">جاري تحميل بيانات لوحة التحكم...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex flex-col md:flex-row md:items-center justify-between gap-4"
      >
        <div>
          <h1 className="text-3xl font-bold bg-gradient-to-r from-purple-400 to-pink-400 bg-clip-text text-transparent">
            لوحة التحكم
          </h1>
          <p className="text-gray-400 mt-2">
            مرحباً بك في منصة النسخ الرقمية. إليك نظرة عامة على نشاطك
          </p>
        </div>
        
        <div className="flex items-center space-x-4 rtl:space-x-reverse">
          {/* Time Range Selector */}
          <div className="flex items-center space-x-2 bg-gray-800 rounded-lg p-1">
            {(['day', 'week', 'month'] as const).map((range) => (
              <button
                key={range}
                onClick={() => setTimeRange(range)}
                className={`px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
                  timeRange === range
                    ? 'bg-purple-600 text-white'
                    : 'text-gray-400 hover:text-white hover:bg-gray-700'
                }`}
              >
                {range === 'day' && 'اليوم'}
                {range === 'week' && 'الأسبوع'}
                {range === 'month' && 'الشهر'}
              </button>
            ))}
          </div>
          
          {/* System Status */}
          <div className="flex items-center space-x-2 px-3 py-1.5 bg-green-500/20 text-green-400 rounded-lg text-sm font-medium">
            <div className="w-2 h-2 rounded-full bg-green-400 animate-pulse"></div>
            <span>النظام: نشط</span>
          </div>
        </div>
      </motion.div>

      {/* Stats Grid */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
        className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6"
      >
        {stats.map((stat, index) => (
          <StatCard key={index} {...stat} />
        ))}
      </motion.div>

      {/* Main Content */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Left Column */}
        <div className="lg:col-span-2 space-y-8">
          {/* Quick Actions */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
            className="bg-gray-800/50 backdrop-blur-sm rounded-2xl p-6 border border-gray-700"
          >
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-xl font-semibold text-white flex items-center space-x-2 rtl:space-x-reverse">
                <Rocket className="w-5 h-5" />
                <span>إجراءات سريعة</span>
              </h2>
              <div className="text-sm text-gray-400">
                ابدأ بسرعة
              </div>
            </div>
            <QuickActions actions={quickActions} />
          </motion.div>

          {/* Usage Chart */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
            className="bg-gray-800/50 backdrop-blur-sm rounded-2xl p-6 border border-gray-700"
          >
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-xl font-semibold text-white flex items-center space-x-2 rtl:space-x-reverse">
                <TrendingUp className="w-5 h-5" />
                <span>تحليل الاستخدام</span>
              </h2>
              <div className="text-sm text-gray-400">
                آخر {timeRange === 'day' ? '24 ساعة' : timeRange === 'week' ? 'أسبوع' : 'شهر'}
              </div>
            </div>
            <UsageChart data={dashboardData?.usageData || []} />
          </motion.div>
        </div>

        {/* Right Column */}
        <div className="space-y-8">
          {/* Recent Activity */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.4 }}
            className="bg-gray-800/50 backdrop-blur-sm rounded-2xl p-6 border border-gray-700"
          >
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-xl font-semibold text-white flex items-center space-x-2 rtl:space-x-reverse">
                <Clock className="w-5 h-5" />
                <span>النشاط الأخير</span>
              </h2>
              <a
                href="/app/activity"
                className="text-sm text-gray-400 hover:text-white"
              >
                عرض الكل
              </a>
            </div>
            <RecentActivity activities={dashboardData?.recentActivity || []} />
          </motion.div>

          {/* Tips */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.5 }}
            className="bg-gradient-to-br from-purple-900/50 to-pink-900/50 rounded-2xl p-6 border border-purple-700/50"
          >
            <h2 className="text-xl font-semibold text-white mb-4 flex items-center space-x-2 rtl:space-x-reverse">
              <Sparkles className="w-5 h-5" />
              <span>نصائح محترف</span>
            </h2>
            
            <div className="space-y-4">
              <div className="bg-white/10 rounded-lg p-4">
                <div className="text-sm font-medium text-white mb-1">
                  استخدم جمل كاملة
                </div>
                <div className="text-sm text-purple-200">
                  النسخ الرقمية تفهم بشكل أفضل عند استخدام جمل كاملة ومفصلة
                </div>
              </div>
              
              <div className="bg-white/10 rounded-lg p-4">
                <div className="text-sm font-medium text-white mb-1">
                  درّب على فترات
                </div>
                <div className="text-sm text-purple-200">
                  قسم تدريب النسخة الرقمية على عدة جلسات قصيرة لتحقيق أفضل النتائج
                </div>
              </div>
              
              <div className="bg-white/10 rounded-lg p-4">
                <div className="text-sm font-medium text-white mb-1">
                  احفظ ائتماناتك
                </div>
                <div className="text-sm text-purple-200">
                  استخدم النسخ المجانية للاختبار قبل تشغيل النسخ المدفوعة
                </div>
              </div>
            </div>
            
            <button className="w-full mt-6 py-3 bg-white text-purple-600 rounded-lg font-bold hover:bg-gray-100 transition-colors">
              استكشاف الميزات
            </button>
          </motion.div>
        </div>
      </div>
    </div>
  );
};

export default DashboardPage;
EOF

# ملف tailwind.config.js
cat > frontend/tailwind.config.js << 'EOF'
/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        primary: {
          50: '#f5f3ff',
          100: '#ede9fe',
          200: '#ddd6fe',
          300: '#c4b5fd',
          400: '#a78bfa',
          500: '#8b5cf6',
          600: '#7c3aed',
          700: '#6d28d9',
          800: '#5b21b6',
          900: '#4c1d95',
        },
        // ألوان مخصصة للمنصة
        matrxe: {
          purple: '#8B5CF6',
          pink: '#EC4899',
          blue: '#3B82F6',
          green: '#10B981',
          yellow: '#F59E0B',
        }
      },
      fontFamily: {
        'sans': ['Inter', 'system-ui', '-apple-system', 'Segoe UI', 'Roboto', 'Helvetica Neue', 'Arial', 'Noto Sans', 'sans-serif'],
        'arabic': ['Cairo', 'Inter', 'system-ui', 'sans-serif'],
      },
      animation: {
        'gradient': 'gradient 8s linear infinite',
        'float': 'float 6s ease-in-out infinite',
        'pulse-slow': 'pulse 4s cubic-bezier(0.4, 0, 0.6, 1) infinite',
      },
      keyframes: {
        gradient: {
          '0%, 100%': {
            'background-size': '200% 200%',
            'background-position': 'left center'
          },
          '50%': {
            'background-size': '200% 200%',
            'background-position': 'right center'
          },
        },
        float: {
          '0%, 100%': { transform: 'translateY(0px)' },
          '50%': { transform: 'translateY(-20px)' },
        }
      },
      backgroundImage: {
        'gradient-radial': 'radial-gradient(var(--tw-gradient-stops))',
        'gradient-conic': 'conic-gradient(from 180deg at 50% 50%, var(--tw-gradient-stops))',
      },
    },
  },
  plugins: [],
}
EOF

# ملف vite.config.ts
cat > frontend/vite.config.ts << 'EOF'
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
      '@components': path.resolve(__dirname, './src/components'),
      '@pages': path.resolve(__dirname, './src/pages'),
      '@services': path.resolve(__dirname, './src/services'),
      '@utils': path.resolve(__dirname, './src/utils'),
      '@styles': path.resolve(__dirname, './src/styles'),
    },
  },
  server: {
    port: 3000,
    host: true,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: false,