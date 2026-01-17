-- MATRXe Database Schema
-- Version 1.0
-- Created: 2024

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================
-- 1. USERS TABLE
-- ============================================
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    phone VARCHAR(20),
    country_code VARCHAR(5),
    language_code VARCHAR(10) DEFAULT 'ar',
    
    -- Profile
    profile_image_url TEXT,
    bio TEXT,
    
    -- Subscription & Billing (for deferred payment model)
    subscription_tier VARCHAR(20) DEFAULT 'trial',
    trial_start_date TIMESTAMP,
    trial_end_date TIMESTAMP,
    trial_extended BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    is_verified BOOLEAN DEFAULT FALSE,
    verified_at TIMESTAMP,
    
    -- Usage tracking
    total_credits INTEGER DEFAULT 1000, -- Initial free credits
    used_credits INTEGER DEFAULT 0,
    total_spent DECIMAL(10, 2) DEFAULT 0.00,
    
    -- Payment info (for deferred payment)
    deferred_payment_balance DECIMAL(10, 2) DEFAULT 0.00,
    last_payment_date TIMESTAMP,
    next_payment_due_date TIMESTAMP,
    
    -- Security
    two_factor_enabled BOOLEAN DEFAULT FALSE,
    last_login TIMESTAMP,
    login_attempts INTEGER DEFAULT 0,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP,
    
    -- Indexes
    INDEX idx_users_email (email),
    INDEX idx_users_subscription (subscription_tier, trial_end_date),
    INDEX idx_users_created (created_at)
);

-- ============================================
-- 2. DIGITAL TWINS TABLE
-- ============================================
CREATE TABLE digital_twins (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Basic Info
    name VARCHAR(255) NOT NULL,
    nickname VARCHAR(100),
    gender VARCHAR(20),
    age_range VARCHAR(20),
    
    -- Personality Traits (JSON)
    personality_config JSONB DEFAULT '{
        "communication_style": "friendly",
        "formality_level": "medium",
        "humor_level": 5,
        "empathy_level": 7,
        "creativity_level": 6,
        "detail_oriented": 8
    }',
    
    -- Voice Model
    voice_model_id VARCHAR(255),
    voice_samples_urls TEXT[], -- Array of voice sample URLs
    voice_training_status VARCHAR(50) DEFAULT 'pending',
    voice_similarity_score DECIMAL(3, 2),
    
    -- Face Model
    face_model_id VARCHAR(255),
    face_images_urls TEXT[], -- Array of face image URLs
    face_training_status VARCHAR(50) DEFAULT 'pending',
    face_similarity_score DECIMAL(3, 2),
    
    -- AI Model References
    chat_model_id VARCHAR(255),
    personality_model_id VARCHAR(255),
    
    -- Status
    training_status VARCHAR(50) DEFAULT 'not_started', -- not_started, training, trained, failed
    training_progress INTEGER DEFAULT 0,
    training_started_at TIMESTAMP,
    training_completed_at TIMESTAMP,
    training_errors TEXT,
    
    -- Configuration
    is_public BOOLEAN DEFAULT FALSE,
    can_be_cloned BOOLEAN DEFAULT FALSE,
    allow_learning BOOLEAN DEFAULT TRUE,
    
    -- Usage Stats
    total_chats INTEGER DEFAULT 0,
    total_voice_minutes DECIMAL(10, 2) DEFAULT 0.00,
    last_interaction TIMESTAMP,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Indexes
    INDEX idx_twins_user (user_id),
    INDEX idx_twins_status (training_status),
    INDEX idx_twins_created (created_at)
);

-- ============================================
-- 3. MULTILINGUAL SUPPORT
-- ============================================
CREATE TABLE languages (
    code VARCHAR(10) PRIMARY KEY, -- ar, en, fr, etc.
    name VARCHAR(100) NOT NULL,
    native_name VARCHAR(100) NOT NULL,
    direction VARCHAR(10) DEFAULT 'ltr', -- ltr or rtl
    is_active BOOLEAN DEFAULT TRUE,
    flag_emoji VARCHAR(10),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert default languages
INSERT INTO languages (code, name, native_name, direction, flag_emoji) VALUES
('ar', 'Arabic', 'العربية', 'rtl', '🇸🇦'),
('en', 'English', 'English', 'ltr', '🇺🇸'),
('fr', 'French', 'Français', 'ltr', '🇫🇷'),
('es', 'Spanish', 'Español', 'ltr', '🇪🇸'),
('de', 'German', 'Deutsch', 'ltr', '🇩🇪'),
('ru', 'Russian', 'Русский', 'ltr', '🇷🇺'),
('tr', 'Turkish', 'Türkçe', 'ltr', '🇹🇷'),
('ur', 'Urdu', 'اردو', 'rtl', '🇵🇰');

CREATE TABLE translations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    key VARCHAR(255) NOT NULL,
    language_code VARCHAR(10) REFERENCES languages(code),
    value TEXT NOT NULL,
    context VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(key, language_code),
    INDEX idx_translations_key (key),
    INDEX idx_translations_language (language_code)
);

-- ============================================
-- 4. CHAT CONVERSATIONS
-- ============================================
CREATE TABLE conversations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    twin_id UUID NOT NULL REFERENCES digital_twins(id) ON DELETE CASCADE,
    
    -- Conversation info
    title VARCHAR(255),
    context_type VARCHAR(50), -- general, professional, casual, etc.
    mood VARCHAR(50), -- happy, sad, serious, funny
    
    -- Stats
    message_count INTEGER DEFAULT 0,
    total_duration INTEGER DEFAULT 0, -- in seconds
    language_used VARCHAR(10) DEFAULT 'ar',
    
    -- Status
    is_archived BOOLEAN DEFAULT FALSE,
    is_pinned BOOLEAN DEFAULT FALSE,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_message_at TIMESTAMP,
    
    -- Indexes
    INDEX idx_conversations_user (user_id),
    INDEX idx_conversations_twin (twin_id),
    INDEX idx_conversations_updated (updated_at)
);

CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    sender_type VARCHAR(20) NOT NULL, -- user or twin
    sender_id UUID, -- Could be user_id or twin_id
    
    -- Message content
    content_type VARCHAR(20) DEFAULT 'text', -- text, voice, image, file
    text_content TEXT,
    voice_url TEXT,
    voice_duration INTEGER, -- in seconds
    language VARCHAR(10),
    
    -- AI Processing
    sentiment_score DECIMAL(3, 2),
    emotion_detected VARCHAR(50),
    ai_metadata JSONB,
    
    -- Status
    is_processed BOOLEAN DEFAULT FALSE,
    processing_errors TEXT,
    
    -- Read receipts
    is_read BOOLEAN DEFAULT FALSE,
    read_at TIMESTAMP,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Indexes
    INDEX idx_messages_conversation (conversation_id),
    INDEX idx_messages_sender (sender_type, sender_id),
    INDEX idx_messages_created (created_at)
);

-- ============================================
-- 5. SCHEDULED TASKS
-- ============================================
CREATE TABLE scheduled_tasks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    twin_id UUID NOT NULL REFERENCES digital_twins(id) ON DELETE CASCADE,
    
    -- Task details
    title VARCHAR(255) NOT NULL,
    description TEXT,
    task_type VARCHAR(50) NOT NULL, -- reminder, checkup, followup, routine
    priority VARCHAR(20) DEFAULT 'medium', -- low, medium, high, urgent
    
    -- Schedule
    schedule_type VARCHAR(50) NOT NULL, -- once, daily, weekly, monthly, custom
    start_date DATE NOT NULL,
    end_date DATE,
    recurrence_rule TEXT, -- Cron expression or custom rule
    
    -- Execution time
    execution_time TIME,
    timezone VARCHAR(50),
    
    -- Action configuration
    action_type VARCHAR(50) NOT NULL, -- message, call, update, reminder
    action_config JSONB NOT NULL, -- Message template, settings, etc.
    
    -- Voice/Video call settings
    use_voice BOOLEAN DEFAULT FALSE,
    use_video BOOLEAN DEFAULT FALSE,
    call_duration INTEGER, -- in minutes
    
    -- Status
    status VARCHAR(20) DEFAULT 'active', -- active, paused, completed, cancelled
    is_recurring BOOLEAN DEFAULT FALSE,
    last_executed TIMESTAMP,
    next_execution TIMESTAMP,
    
    -- Results tracking
    execution_count INTEGER DEFAULT 0,
    success_count INTEGER DEFAULT 0,
    failure_count INTEGER DEFAULT 0,
    last_execution_result TEXT,
    
    -- Notifications
    notify_user BOOLEAN DEFAULT TRUE,
    notification_channels TEXT[], -- email, push, sms
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Indexes
    INDEX idx_tasks_user (user_id),
    INDEX idx_tasks_twin (twin_id),
    INDEX idx_tasks_status (status),
    INDEX idx_tasks_next_execution (next_execution)
);

CREATE TABLE task_executions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    task_id UUID NOT NULL REFERENCES scheduled_tasks(id) ON DELETE CASCADE,
    
    -- Execution details
    scheduled_for TIMESTAMP NOT NULL,
    executed_at TIMESTAMP,
    execution_status VARCHAR(20), -- pending, success, failed, skipped
    
    -- Results
    result_data JSONB,
    error_message TEXT,
    logs TEXT,
    
    -- Cost tracking (for billing)
    credits_used INTEGER DEFAULT 0,
    processing_time INTEGER, -- in seconds
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Indexes
    INDEX idx_executions_task (task_id),
    INDEX idx_executions_scheduled (scheduled_for),
    INDEX idx_executions_status (execution_status)
);

-- ============================================
-- 6. VOICE MODELS & PROCESSING
-- ============================================
CREATE TABLE voice_models (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    twin_id UUID NOT NULL REFERENCES digital_twins(id) ON DELETE CASCADE,
    
    -- Model info
    provider VARCHAR(50), -- elevenlabs, google, custom
    model_id VARCHAR(255),
    voice_name VARCHAR(255),
    
    -- Voice characteristics
    gender VARCHAR(20),
    age_range VARCHAR(20),
    accent VARCHAR(50),
    language_support TEXT[], -- Array of languages
    
    -- Training data
    training_samples_urls TEXT[],
    training_samples_count INTEGER DEFAULT 0,
    sample_duration_total INTEGER DEFAULT 0, -- in seconds
    
    -- Model performance
    similarity_score DECIMAL(3, 2),
    clarity_score DECIMAL(3, 2),
    stability_score DECIMAL(3, 2),
    
    -- Status
    training_status VARCHAR(50) DEFAULT 'not_started',
    is_active BOOLEAN DEFAULT TRUE,
    
    -- Cost tracking
    training_cost_credits INTEGER DEFAULT 0,
    usage_cost_per_minute DECIMAL(5, 4) DEFAULT 0.001,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Indexes
    INDEX idx_voice_models_twin (twin_id),
    INDEX idx_voice_models_status (training_status)
);

-- ============================================
-- 7. FACE MODELS & PROCESSING
-- ============================================
CREATE TABLE face_models (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    twin_id UUID NOT NULL REFERENCES digital_twins(id) ON DELETE CASCADE,
    
    -- Model info
    provider VARCHAR(50), -- mediapipe, deepface, custom
    model_id VARCHAR(255),
    
    -- Training data
    training_images_urls TEXT[],
    training_images_count INTEGER DEFAULT 0,
    
    -- Model characteristics
    detected_features JSONB, -- facial features, expressions
    base_avatar_url TEXT, -- 3D avatar or base image
    
    -- Model performance
    similarity_score DECIMAL(3, 2),
    expression_accuracy DECIMAL(3, 2),
    
    -- Status
    training_status VARCHAR(50) DEFAULT 'not_started',
    is_active BOOLEAN DEFAULT TRUE,
    
    -- Cost tracking
    training_cost_credits INTEGER DEFAULT 0,
    usage_cost_per_image DECIMAL(5, 4) DEFAULT 0.0005,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Indexes
    INDEX idx_face_models_twin (twin_id)
);

-- ============================================
-- 8. AI MODEL INTEGRATIONS
-- ============================================
CREATE TABLE ai_providers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) NOT NULL,
    provider_type VARCHAR(50), -- chat, voice, face, translation
    api_base_url TEXT,
    api_key_env_var VARCHAR(100),
    
    -- Rate limiting
    requests_per_minute INTEGER DEFAULT 60,
    requests_per_day INTEGER DEFAULT 1000,
    
    -- Cost
    cost_per_request DECIMAL(10, 6) DEFAULT 0.0001,
    cost_per_token DECIMAL(10, 6) DEFAULT 0.000002,
    
    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    priority INTEGER DEFAULT 1, -- Lower number = higher priority
    
    -- Capabilities
    supported_languages TEXT[],
    max_tokens INTEGER DEFAULT 4096,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert default AI providers
INSERT INTO ai_providers (name, provider_type, supported_languages) VALUES
('Ollama (Local)', 'chat', ARRAY['ar', 'en', 'fr', 'es', 'de']),
('ElevenLabs', 'voice', ARRAY['ar', 'en', 'fr', 'es', 'de', 'ru']),
('Google TTS', 'voice', ARRAY['ar', 'en', 'fr', 'es', 'de', 'ru', 'tr', 'ur']),
('MediaPipe', 'face', ARRAY[]::VARCHAR[]),
('Hugging Face', 'translation', ARRAY['ar', 'en', 'fr', 'es', 'de', 'ru']);

-- ============================================
-- 9. CREDIT & BILLING SYSTEM (for deferred payment)
-- ============================================
CREATE TABLE credit_transactions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Transaction details
    transaction_type VARCHAR(50) NOT NULL, -- purchase, usage, refund, bonus
    amount DECIMAL(10, 2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'USD',
    
    -- Credit conversion
    credits_granted INTEGER,
    credits_used INTEGER,
    
    -- For usage transactions
    service_type VARCHAR(50), -- voice, chat, face, storage
    resource_id UUID, -- Reference to specific resource
    duration_seconds INTEGER,
    quantity INTEGER,
    
    -- Pricing
    unit_price DECIMAL(10, 4),
    total_price DECIMAL(10, 2),
    
    -- Status
    status VARCHAR(20) DEFAULT 'completed', -- pending, completed, failed, refunded
    is_deferred BOOLEAN DEFAULT FALSE,
    deferred_payment_date DATE,
    
    -- Payment info (for actual payments)
    payment_method VARCHAR(50),
    payment_reference VARCHAR(255),
    
    -- Metadata
    metadata JSONB,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMP,
    
    -- Indexes
    INDEX idx_transactions_user (user_id),
    INDEX idx_transactions_type (transaction_type),
    INDEX idx_transactions_created (created_at),
    INDEX idx_transactions_deferred (is_deferred, deferred_payment_date)
);

CREATE TABLE deferred_payments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id),
    
    -- Payment details
    invoice_number VARCHAR(100) UNIQUE NOT NULL,
    total_amount DECIMAL(10, 2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'USD',
    description TEXT,
    
    -- Period covered
    billing_period_start DATE NOT NULL,
    billing_period_end DATE NOT NULL,
    
    -- Usage summary
    usage_summary JSONB NOT NULL, -- Breakdown of services used
    
    -- Status
    status VARCHAR(20) DEFAULT 'pending', -- pending, sent, viewed, paid, overdue
    payment_due_date DATE NOT NULL,
    payment_date DATE,
    
    -- Reminders
    reminder_sent_count INTEGER DEFAULT 0,
    last_reminder_sent DATE,
    
    -- Late payment
    is_overdue BOOLEAN DEFAULT FALSE,
    overdue_days INTEGER DEFAULT 0,
    late_fee DECIMAL(10, 2) DEFAULT 0.00,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    paid_at TIMESTAMP,
    
    -- Indexes
    INDEX idx_payments_user (user_id),
    INDEX idx_payments_status (status),
    INDEX idx_payments_due_date (payment_due_date),
    INDEX idx_payments_invoice (invoice_number)
);

-- ============================================
-- 10. MULTIMEDIA STORAGE
-- ============================================
CREATE TABLE media_files (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- File info
    file_type VARCHAR(50) NOT NULL, -- voice, image, video, document
    original_filename VARCHAR(255),
    stored_filename VARCHAR(255) UNIQUE NOT NULL,
    file_path TEXT NOT NULL,
    file_size BIGINT,
    
    -- Metadata
    mime_type VARCHAR(100),
    duration_seconds INTEGER, -- for audio/video
    width INTEGER, -- for images/video
    height INTEGER, -- for images/video
    
    -- Processing status
    processing_status VARCHAR(50) DEFAULT 'uploaded',
    processing_errors TEXT,
    
    -- Privacy
    is_public BOOLEAN DEFAULT FALSE,
    access_token VARCHAR(100),
    
    -- Usage tracking
    times_accessed INTEGER DEFAULT 0,
    last_accessed TIMESTAMP,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    
    -- Indexes
    INDEX idx_media_user (user_id),
    INDEX idx_media_type (file_type),
    INDEX idx_media_created (created_at)
);

-- ============================================
-- 11. NOTIFICATIONS
-- ============================================
CREATE TABLE notifications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Notification details
    type VARCHAR(50) NOT NULL, -- system, billing, reminder, update
    title VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    
    -- Localization
    title_ar VARCHAR(255),
    message_ar TEXT,
    title_en VARCHAR(255),
    message_en TEXT,
    
    -- Action
    action_url TEXT,
    action_label VARCHAR(100),
    
    -- Status
    is_read BOOLEAN DEFAULT FALSE,
    read_at TIMESTAMP,
    
    -- Delivery
    channels TEXT[] DEFAULT ARRAY['in_app'], -- in_app, email, push, sms
    sent_via TEXT[],
    
    -- Priority
    priority VARCHAR(20) DEFAULT 'normal', -- low, normal, high, urgent
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    scheduled_for TIMESTAMP,
    sent_at TIMESTAMP,
    
    -- Indexes
    INDEX idx_notifications_user (user_id),
    INDEX idx_notifications_read (is_read, created_at),
    INDEX idx_notifications_type (type)
);

-- ============================================
-- 12. AUDIT LOGS
-- ============================================
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Who
    user_id UUID REFERENCES users(id),
    user_ip INET,
    user_agent TEXT,
    
    -- What
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(50),
    resource_id UUID,
    
    -- Details
    old_values JSONB,
    new_values JSONB,
    changes JSONB,
    
    -- Status
    status VARCHAR(20) DEFAULT 'success', -- success, failed
    error_message TEXT,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Indexes
    INDEX idx_audit_user (user_id),
    INDEX idx_audit_action (action),
    INDEX idx_audit_created (created_at)
);

-- ============================================
-- 13. SITE SETTINGS & CONFIGURATION
-- ============================================
CREATE TABLE site_settings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    setting_key VARCHAR(100) UNIQUE NOT NULL,
    setting_value TEXT,
    setting_type VARCHAR(50) DEFAULT 'string', -- string, number, boolean, json
    category VARCHAR(50),
    is_public BOOLEAN DEFAULT FALSE,
    description TEXT,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Indexes
    INDEX idx_settings_key (setting_key),
    INDEX idx_settings_category (category)
);

-- Insert default settings
INSERT INTO site_settings (setting_key, setting_value, category, description) VALUES
-- Trial settings
('trial_duration_days', '30', 'trial', 'عدد أيام الفترة التجريبية'),
('trial_credits', '1000', 'trial', 'الرصيد الابتدائي للمستخدمين التجريبيين'),
('trial_max_twins', '1', 'trial', 'الحد الأقصى للنسخ الرقمية خلال التجربة'),

-- Pricing
('credit_price', '0.01', 'pricing', 'سعر كل رصيد بالدولار'),
('voice_minute_cost', '10', 'pricing', 'تكلفة الدقيقة من الصوت (بالرصيد)'),
('chat_message_cost', '1', 'pricing', 'تكلفة كل رسالة محادثة (بالرصيد)'),
('face_processing_cost', '5', 'pricing', 'تكلفة معالجة صورة وجه (بالرصيد)'),

-- Deferred payment
('deferred_payment_grace_days', '7', 'billing', 'أيام السماح بعد انتهاء التجربة'),
('min_deferred_amount', '10', 'billing', 'الحد الأدنى للدفع المؤجل'),
('late_fee_percentage', '5', 'billing', 'نسبة الرسوم المتأخرة'),

-- Platform settings
('default_language', 'ar', 'platform', 'اللغة الافتراضية'),
('supported_languages', 'ar,en,fr,es,de,ru,tr,ur', 'platform', 'اللغات المدعومة'),
('max_file_size_mb', '100', 'platform', 'الحد الأقصى لحجم الملف بالميجابايت'),

-- AI Settings
('default_chat_model', 'llama3:8b', 'ai', 'نموذج المحادثة الافتراضي'),
('default_voice_provider', 'elevenlabs', 'ai', 'مزود الصوت الافتراضي'),
('default_face_provider', 'mediapipe', 'ai', 'مزوج معالجة الوجه الافتراضي');

-- ============================================
-- 14. MULTILINGUAL CONTENT
-- ============================================
CREATE TABLE multilingual_content (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    content_key VARCHAR(255) NOT NULL,
    content_type VARCHAR(50), -- page, section, label, message
    
    -- Translations
    content_ar TEXT,
    content_en TEXT,
    content_fr TEXT,
    content_es TEXT,
    content_de TEXT,
    content_ru TEXT,
    content_tr TEXT,
    content_ur TEXT,
    
    -- Context
    context VARCHAR(100),
    page VARCHAR(100),
    
    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Indexes
    INDEX idx_content_key (content_key),
    INDEX idx_content_type (content_type),
    UNIQUE(content_key)
);

-- Insert default multilingual content
INSERT INTO multilingual_content (content_key, content_type, content_ar, content_en) VALUES
-- Platform name
('platform_name', 'label', 'ماتركس إي', 'MATRXe'),
('platform_tagline', 'label', 'نسخك الرقمية الذكية', 'Your Intelligent Digital Twins'),

-- Navigation
('nav_dashboard', 'label', 'لوحة التحكم', 'Dashboard'),
('nav_my_twins', 'label', 'نسخي الرقمية', 'My Digital Twins'),
('nav_create_twin', 'label', 'إنشاء نسخة جديدة', 'Create New Twin'),
('nav_conversations', 'label', 'المحادثات', 'Conversations'),
('nav_scheduled_tasks', 'label', 'المهام المجدولة', 'Scheduled Tasks'),
('nav_billing', 'label', 'الفواتير والرصيد', 'Billing & Credits'),

-- Buttons
('btn_create', 'label', 'إنشاء', 'Create'),
('btn_save', 'label', 'حفظ', 'Save'),
('btn_cancel', 'label', 'إلغاء', 'Cancel'),
('btn_delete', 'label', 'حذف', 'Delete'),
('btn_start_chat', 'label', 'بدء محادثة', 'Start Chat'),
('btn_schedule_task', 'label', 'جدولة مهمة', 'Schedule Task'),

-- Messages
('welcome_message', 'message', 'مرحباً بك في ماتركس إي!', 'Welcome to MATRXe!'),
('twin_creation_started', 'message', 'بدأنا إنشاء نسختك الرقمية...', 'Started creating your digital twin...'),
('voice_training_in_progress', 'message', 'جاري تدريب الصوت...', 'Voice training in progress...'),

-- Billing messages
('free_trial_active', 'message', 'فترة تجريبية فعالة حتى', 'Free trial active until'),
('credits_remaining', 'message', 'الرصيد المتبقي', 'Credits remaining'),
('deferred_payment_due', 'message', 'دفعة مؤجلة مستحقة بتاريخ', 'Deferred payment due on');

-- ============================================
-- TRIGGERS FOR UPDATED_AT TIMESTAMP
-- ============================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply triggers to tables that need updated_at
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_digital_twins_updated_at BEFORE UPDATE ON digital_twins 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_conversations_updated_at BEFORE UPDATE ON conversations 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_scheduled_tasks_updated_at BEFORE UPDATE ON scheduled_tasks 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_voice_models_updated_at BEFORE UPDATE ON voice_models 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_face_models_updated_at BEFORE UPDATE ON face_models 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_ai_providers_updated_at BEFORE UPDATE ON ai_providers 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_deferred_payments_updated_at BEFORE UPDATE ON deferred_payments 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_notifications_updated_at BEFORE UPDATE ON notifications 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_site_settings_updated_at BEFORE UPDATE ON site_settings 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_multilingual_content_updated_at BEFORE UPDATE ON multilingual_content 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================
-- VIEWS FOR REPORTING
-- ============================================
CREATE VIEW user_usage_summary AS
SELECT 
    u.id as user_id,
    u.email,
    u.subscription_tier,
    u.trial_end_date,
    u.total_credits,
    u.used_credits,
    (u.total_credits - u.used_credits) as remaining_credits,
    u.deferred_payment_balance,
    COUNT(DISTINCT dt.id) as total_twins,
    COUNT(DISTINCT c.id) as total_conversations,
    COUNT(DISTINCT st.id) as total_scheduled_tasks,
    COALESCE(SUM(st.execution_count), 0) as total_task_executions,
    COALESCE(SUM(dt.total_chats), 0) as total_chat_messages,
    COALESCE(SUM(dt.total_voice_minutes), 0) as total_voice_minutes
FROM users u
LEFT JOIN digital_twins dt ON u.id = dt.user_id
LEFT JOIN conversations c ON u.id = c.user_id
LEFT JOIN scheduled_tasks st ON u.id = st.user_id
GROUP BY u.id, u.email, u.subscription_tier;

CREATE VIEW deferred_payments_due AS
SELECT 
    dp.*,
    u.email,
    u.full_name,
    u.phone,
    dp.payment_due_date - CURRENT_DATE as days_until_due,
    CASE 
        WHEN dp.payment_due_date < CURRENT_DATE THEN CURRENT_DATE - dp.payment_due_date
        ELSE 0
    END as days_overdue
FROM deferred_payments dp
JOIN users u ON dp.user_id = u.id
WHERE dp.status IN ('pending', 'overdue')
ORDER BY dp.payment_due_date;

-- ============================================
-- INDEXES FOR PERFORMANCE
-- ============================================
CREATE INDEX idx_messages_conversation_created ON messages(conversation_id, created_at DESC);
CREATE INDEX idx_tasks_next_execution_status ON scheduled_tasks(next_execution, status);
CREATE INDEX idx_transactions_user_created ON credit_transactions(user_id, created_at DESC);
CREATE INDEX idx_notifications_user_created ON notifications(user_id, created_at DESC);

-- ============================================
-- END OF DATABASE SCHEMA
-- ============================================

COMMENT ON DATABASE current_database() IS 'MATRXe - Digital Twin Platform Database';