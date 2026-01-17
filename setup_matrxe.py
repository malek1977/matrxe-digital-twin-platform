python
import os
import subprocess
from pathlib import Path

# إنشاء هيكل المجلدات
folders = [
    "backend/app/config",
    "backend/app/api/v1/endpoints",
    "backend/app/database",
    "backend/app/services",
    "backend/app/middleware",
    "backend/app/core",
    "backend/app/utils",
    "backend/app/ai_engine",
    "backend/app/schemas",
    "backend/app/models",
    "frontend/src/components",
    "frontend/src/pages/auth",
    "frontend/src/pages/twins",
    "frontend/src/pages/chat",
    "frontend/src/pages/tasks",
    "frontend/src/pages/billing",
    "frontend/src/pages/settings",
    "frontend/src/pages/profile",
    "frontend/src/contexts",
    "frontend/src/services/api",
    "frontend/src/utils",
    "frontend/src/hooks",
    "frontend/src/i18n",
    "frontend/src/assets",
    "frontend/src/styles",
    "deployment/nginx",
    "deployment/ssl",
    "deployment/monitoring",
    "deployment/scripts",
    "ai_models/voice_cloning",
    "ai_models/face_processing",
    "ai_models/chat_models",
    "ai_models/emotion_detection",
    "ai_models/training_scripts",
    "database/migrations",
    "database/seeds",
    "database/backups",
    "documentation/ARABIC",
    "documentation/API",
    "documentation/USER_GUIDE"
]

for folder in folders:
    Path(folder).mkdir(parents=True, exist_ok=True)
    print(f"✅ Created: {folder}")

# إنشاء الملفات الأساسية
files = {
    # ملفات Backend الأساسية
    "backend/app/main.py": """
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

app = FastAPI(
    title="MATRXe Digital Twin Platform",
    description="Advanced AI-powered digital twin creation",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {
        "message": "🚀 Welcome to MATRXe - Digital Twin Platform",
        "version": "1.0.0",
        "endpoints": {
            "docs": "/docs",
            "api": "/api/v1",
            "health": "/health"
        }
    }

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "matrxe-backend"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
""",
    
    "backend/requirements.txt": """fastapi==0.104.1
uvicorn[standard]==0.24.0
gunicorn==21.2.0
sqlalchemy==2.0.23
psycopg2-binary==2.9.9
asyncpg==0.29.0
alembic==1.12.1
openai==1.3.0
elevenlabs==0.2.11
transformers==4.35.2
torch==2.1.0
whisper==1.1.10
mediapipe==0.10.8
face-recognition==1.3.0
speechrecognition==3.10.0
pydub==0.25.1
moviepy==1.0.3
Pillow==10.1.0
opencv-python==4.8.1.78
python-multipart==0.0.6
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
pyjwt==2.8.0
cryptography==41.0.7
python-decouple==3.8
sendgrid==6.11.0
twilio==8.9.0
redis==5.0.1
aioredis==2.0.1
pydantic==2.5.0
pydantic-settings==2.1.0
email-validator==2.1.0
babel==2.13.1
googletrans==4.0.0rc1
loguru==0.7.2
sentry-sdk==1.38.0
prometheus-client==0.19.0
pytest==7.4.3
httpx==0.25.2
black==23.11.0
isort==5.12.0""",

    "backend/Dockerfile": """FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]""",

    # ملفات Frontend الأساسية
    "frontend/package.json": """{
  "name": "matrxe-frontend",
  "version": "1.0.0",
  "private": true,
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-router-dom": "^6.20.0",
    "react-query": "^3.39.3",
    "axios": "^1.6.2",
    "i18next": "^23.7.2",
    "react-i18next": "^13.3.1",
    "framer-motion": "^10.16.5",
    "zustand": "^4.4.7",
    "tailwindcss": "^3.3.6",
    "lucide-react": "^0.309.0"
  },
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview"
  },
  "devDependencies": {
    "@vitejs/plugin-react": "^4.2.0",
    "vite": "^5.0.0",
    "autoprefixer": "^10.4.16",
    "postcss": "^8.4.32"
  }
}""",

    "frontend/src/App.jsx": """import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';

function App() {
  return (
    <Router>
      <div className="min-h-screen bg-gray-900 text-white">
        <Routes>
          <Route path="/" element={<h1 className="text-4xl text-center mt-10">🚀 MATRXe Platform</h1>} />
          <Route path="/app" element={<h1 className="text-4xl text-center mt-10">📱 Dashboard</h1>} />
        </Routes>
      </div>
    </Router>
  );
}

export default App;""",

    "frontend/Dockerfile": """FROM node:18-alpine as builder

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]""",

    # ملفات Docker والنشر
    "docker-compose.yml": """version: '3.8'

services:
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: matrxe
      POSTGRES_USER: matrxe_user
      POSTGRES_PASSWORD: password123
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  redis:
    image: redis:7-alpine
    command: redis-server --requirepass redispass123
    volumes:
      - redis_data:/data
    ports:
      - "6379:6379"

  backend:
    build: ./backend
    ports:
      - "8000:8000"
    depends_on:
      - postgres
      - redis
    environment:
      DATABASE_URL: postgresql://matrxe_user:password123@postgres/matrxe
      REDIS_URL: redis://:redispass123@redis:6379/0
      SECRET_KEY: your-secret-key-change-in-production

  frontend:
    build: ./frontend
    ports:
      - "3000:80"
    depends_on:
      - backend

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    depends_on:
      - backend
      - frontend
    volumes:
      - ./deployment/nginx/nginx.conf:/etc/nginx/nginx.conf
      - ./deployment/ssl:/etc/nginx/ssl

volumes:
  postgres_data:
  redis_data:""",

    # ملفات التكوين
    ".env.example": """# Application
APP_NAME=MATRXe
DOMAIN=matrxe.com
ENVIRONMENT=development
DEBUG=true
PORT=8000

# Security
SECRET_KEY=your-secret-key-change-in-production
ALGORITHM=HS256

# Database
DATABASE_URL=postgresql://matrxe_user:password123@localhost/matrxe

# Redis
REDIS_URL=redis://localhost:6379/0
REDIS_PASSWORD=redispass123

# AI Services
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_DEFAULT_MODEL=llama3:8b

# Billing
DEFAULT_CURRENCY=USD
CREDIT_PRICE=0.01
TRIAL_CREDITS=1000
TRIAL_DAYS=30""",

    ".gitignore": """# Python
__pycache__/
*.py[cod]
*.so
.Python
build/
dist/
*.egg-info/

# Environment
.env
.env.local

# Database
*.db
*.sqlite3

# IDE
.vscode/
.idea/
*.swp
*.swo

# Logs
*.log
npm-debug.log*
yarn-debug.log*""",

    "README.md": """# 🚀 MATRXe - منصة النسخ الرقمية الذكية

## 📖 نظرة عامة
منصة متقدمة لإنشاء نسخ رقمية ذكية باستخدام الذكاء الاصطناعي.

## ✨ المميزات
- إنشاء نسخ رقمية بتقليد الصوت والوجه
- محادثات ذكية ثنائية الاتجاه
- مهام مجدولة تلقائية
- واجهة متعددة اللغات
- نظام دفع مؤجل

## 🏗️ الهيكل التقني
- **Backend:** FastAPI + PostgreSQL
- **Frontend:** React + TailwindCSS
- **AI:** Ollama + ElevenLabs + MediaPipe
- **النشر:** Docker + Nginx

## 🚀 النشر السريع
```bash
# Clone repository
git clone https://github.com/malek1977/matrxe.git
cd matrxe

# Start with Docker
docker-compose up -d

# Access applications
# Frontend: http://localhost:3000
# Backend API: http://localhost:8000
# API Docs: http://localhost:8000/docs
📁 هيكل المشروع
text
MATRXe/
├── backend/          # FastAPI application
├── frontend/         # React application
├── deployment/       # Deployment scripts
├── ai_models/        # AI models and training
├── database/         # Database schemas and migrations
└── documentation/    # Project documentation
📄 الترخيص
MIT License - أنشئه بمحبة ❤️"""
}

إنشاء الملفات
for file_path, content in files.items():
with open(file_path, 'w', encoding='utf-8') as f:
f.write(content.strip())
print(f"📄 Created: {file_path}")

print("\n" + "="*50)
print("✅ MATRXe Project Structure Created Successfully!")
print("="*50)
print("\n📦 To push to GitHub:")
print("""
git init
git add .
git commit -m "Initial commit: MATRXe Digital Twin Platform"
git branch -M main
git remote add origin https://github.com/malek1977/matrxe.git
git push -u origin main
""")

