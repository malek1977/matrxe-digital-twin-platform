#!/usr/bin/env bash
set -euo pipefail

BRANCH="feature/fullstack-mvp"
COMMIT_MSG="feat(scaffold): add backend scaffold, presign uploads, worker skeleton, frontend presign uploader, deploy script"

# تحذير عن .env
echo "تذكير: السكربت لن يُنشئ أو يُعدل ملفات .env. تأكد من إعداد server/.env يدوياً بعد الدفع."

# تأكد في مجلد git
if [ ! -d ".git" ]; then
  echo "خطأ: هذا المجلد ليس مستودع Git. الرجاء تشغيل هذا السكربت داخل جذر المستودع."
  exit 1
fi

# احفظ الفرع الحالي
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
echo "الفرع الحالي: $CURRENT_BRANCH"

# انشئ و/أو اذهب إلى الفرع الهدف
if git show-ref --verify --quiet "refs/heads/$BRANCH"; then
  git checkout "$BRANCH"
  git pull origin "$BRANCH" || true
else
  git checkout -b "$BRANCH"
fi

echo "سيتم إنشاء/استبدال الملفات التالية ضمن المستودع ثم عمل commit و push إلى الفرع $BRANCH"

# === اكتب الملفات المحدثة ===
# ملاحظة: السكربت يتجنّب إضافة أي ملف .env

# 1) server/package.json
mkdir -p server
cat > server/package.json <<'EOF'
{
  "name": "matrxe-backend",
  "version": "0.1.0",
  "private": true,
  "scripts": {
    "dev": "ts-node-dev --respawn --transpile-only src/index.ts",
    "build": "tsc -p tsconfig.json",
    "start": "node dist/index.js",
    "migrate": "prisma migrate deploy"
  },
  "dependencies": {
    "@aws-sdk/client-s3": "^3.385.0",
    "@aws-sdk/s3-request-presigner": "^3.385.0",
    "@prisma/client": "^5.5.0",
    "bcryptjs": "^2.4.3",
    "bullmq": "^2.9.0",
    "cors": "^2.8.5",
    "dotenv": "^16.3.1",
    "express": "^4.18.2",
    "express-rate-limit": "^6.7.0",
    "helmet": "^7.0.0",
    "ioredis": "^5.4.1",
    "jsonwebtoken": "^9.1.0",
    "multer": "^1.4.5-lts.1",
    "stripe": "^12.15.0",
    "uuid": "^9.0.0",
    "prisma": "^5.5.0"
  },
  "devDependencies": {
    "ts-node-dev": "^2.0.0",
    "typescript": "^5.2.2"
  }
}
EOF

# 2) server/tsconfig.json
cat > server/tsconfig.json <<'EOF'
{
  "compilerOptions": {
    "target": "ES2020",
    "module": "commonjs",
    "outDir": "dist",
    "rootDir": "src",
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "forceConsistentCasingInFileNames": true,
    "resolveJsonModule": true
  },
  "include": ["src"]
}
EOF

# 3) server/.env.example
cat > server/.env.example <<'EOF'
# Server
PORT=4000
FRONTEND_ORIGIN=https://matrxe.com

# Database (Postgres)
DATABASE_URL=postgresql://matrxe:password@postgres:5432/matrxe

# JWT
JWT_SECRET=change_this_to_a_secure_random_value

# AWS S3
AWS_REGION=us-east-1
S3_BUCKET=matrxe-prod-uploads
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret

# Redis (for queues)
REDIS_URL=redis://redis:6379

# Stripe
STRIPE_SECRET_KEY=sk_test_xxx
STRIPE_WEBHOOK_SECRET=whsec_xxx

# Email provider (SendGrid)
SENDGRID_API_KEY=sendgrid_key_here
EOF

# 4) prisma schema
mkdir -p server/prisma
cat > server/prisma/schema.prisma <<'EOF'
generator client {
  provider = "prisma-client-js"
}

datasource db {
  provider = "postgresql"
  url      = env("DATABASE_URL")
}

model User {
  id                String    @id @default(cuid())
  email             String    @unique
  passwordHash      String
  name              String?
  role              String    @default("user")
  stripeCustomerId  String?
  createdAt         DateTime  @default(now())
  updatedAt         DateTime  @updatedAt
  twins             DigitalTwin[]
  sessions          Session[]
}

model Session {
  id         String   @id @default(cuid())
  user       User     @relation(fields: [userId], references: [id])
  userId     String
  tokenHash  String
  expiresAt  DateTime
  createdAt  DateTime @default(now())
}

model DigitalTwin {
  id                String     @id @default(cuid())
  user              User?      @relation(fields: [userId], references: [id])
  userId            String?
  name              String
  description       String?
  language          String     @default("ar")
  voiceSettings     Json?
  personalityTags   Json?
  status            String     @default("draft")
  createdAt         DateTime   @default(now())
  updatedAt         DateTime   @updatedAt
  images            TwinImage[]
  sampleAudioUrl    String?
  previewVideoUrl   String?
}

model TwinImage {
  id        String   @id @default(cuid())
  twin      DigitalTwin @relation(fields: [twinId], references: [id])
  twinId    String
  url       String
  thumbUrl  String?
  meta      Json?
  createdAt DateTime @default(now())
}

model Subscription {
  id                 String   @id @default(cuid())
  user               User     @relation(fields: [userId], references: [id])
  userId             String
  stripeSubscriptionId String
  plan               String
  status             String
  currentPeriodEnd   DateTime?
  createdAt          DateTime @default(now())
}

model JobLog {
  id        String   @id @default(cuid())
  type      String
  payload   Json
  status    String
  result    Json?
  attempts  Int      @default(0)
  createdAt DateTime @default(now())
}
EOF

# 5) docker-compose.yml (جذر المشروع)
cat > docker-compose.yml <<'EOF'
version: "3.8"
services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_USER: matrxe
      POSTGRES_PASSWORD: password
      POSTGRES_DB: matrxe
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redisdata:/data

  backend:
    build:
      context: ./server
      dockerfile: Dockerfile
    environment:
      - DATABASE_URL=postgresql://matrxe:password@postgres:5432/matrxe
      - REDIS_URL=redis://redis:6379
      - FRONTEND_ORIGIN=https://matrxe.com
    ports:
      - "4000:4000"
    depends_on:
      - postgres
      - redis

  worker:
    build:
      context: ./server
      dockerfile: Dockerfile
    environment:
      - DATABASE_URL=postgresql://matrxe:password@postgres:5432/matrxe
      - REDIS_URL=redis://redis:6379
    depends_on:
      - redis
      - postgres

volumes:
  pgdata:
  redisdata:
EOF

# 6) server/Dockerfile
cat > server/Dockerfile <<'EOF'
FROM node:20-alpine

WORKDIR /app

# install deps
COPY package*.json ./
RUN npm ci --production=false

# copy source
COPY . .

# build
RUN npm run build

EXPOSE 4000
CMD ["node", "dist/index.js"]
EOF

# 7) server/src/index.ts and routes/services/worker
mkdir -p server/src/services server/src/routes server/src/workers
cat > server/src/index.ts <<'EOF'
import express from 'express';
import cors from 'cors';
import helmet from 'helmet';
import dotenv from 'dotenv';
import rateLimit from 'express-rate-limit';
import authRoutes from './routes/auth';
import uploadRoutes from './routes/uploads';
import twinRoutes from './routes/twins';
import stripeRoutes from './routes/stripe';

dotenv.config();

const app = express();
const FRONTEND = process.env.FRONTEND_ORIGIN || 'http://localhost:5173';

app.use(helmet());
app.use(cors({ origin: FRONTEND, credentials: true }));
app.use(express.json({ limit: '50mb' }));
app.use(express.urlencoded({ extended: true }));

app.use(rateLimit({ windowMs: 60_000, max: 120 }));

// routes
app.use('/api/auth', authRoutes);
app.use('/api/uploads', uploadRoutes);
app.use('/api/twins', twinRoutes);
app.use('/api/stripe', stripeRoutes);

// health
app.get('/api/status', (_, res) => res.json({ ok: true, ts: Date.now() }));

const PORT = Number(process.env.PORT || 4000);
app.listen(PORT, () => console.log(`MATRXe backend listening on ${PORT}`));
EOF

# create placeholder auth route (simple stub to avoid import errors)
cat > server/src/routes/auth.ts <<'EOF'
import { Router } from 'express';
const router = Router();

// Placeholder endpoints for auth (signup/login) - implement as needed
router.post('/signup', (req, res) => res.json({ ok: true }));
router.post('/login', (req, res) => res.json({ ok: true }));

export default router;
EOF

# s3 service
cat > server/src/services/s3.ts <<'EOF'
import { S3Client, PutObjectCommand, PutObjectCommandInput } from "@aws-sdk/client-s3";
import { getSignedUrl } from "@aws-sdk/s3-request-presigner";
import crypto from "crypto";

const s3 = new S3Client({ region: process.env.AWS_REGION });

export async function presignUpload(filename: string, contentType: string, expiresIn = 60) {
  const key = `uploads/${Date.now()}-${crypto.randomBytes(6).toString('hex')}-${filename}`;
  const cmd = new PutObjectCommand({
    Bucket: process.env.S3_BUCKET!,
    Key: key,
    ContentType: contentType,
    ACL: 'private'
  } as PutObjectCommandInput);
  const url = await getSignedUrl(s3, cmd, { expiresIn });
  return { url, key };
}

export async function uploadBuffer(buffer: Buffer, key: string, contentType: string) {
  const cmd = new PutObjectCommand({
    Bucket: process.env.S3_BUCKET!,
    Key: key,
    Body: buffer,
    ContentType: contentType,
    ACL: 'private'
  });
  await s3.send(cmd);
  return key;
}
EOF

# uploads route
cat > server/src/routes/uploads.ts <<'EOF'
import { Router } from "express";
import { presignUpload } from "../services/s3";

const router = Router();

router.post('/presign', async (req, res) => {
  const { filename, contentType } = req.body;
  if (!filename || !contentType) return res.status(400).json({ error: 'filename & contentType required' });
  try {
    const result = await presignUpload(filename, contentType);
    res.json(result);
  } catch (err) {
    console.error('presign error', err);
    res.status(500).json({ error: 'presign_failed' });
  }
});

export default router;
EOF

# twins route
cat > server/src/routes/twins.ts <<'EOF'
import { Router } from "express";
import multer from "multer";
import { PrismaClient } from "@prisma/client";
import { uploadBuffer } from "../services/s3";
import { v4 as uuidv4 } from "uuid";

const prisma = new PrismaClient();
const router = Router();
const upload = multer({ storage: multer.memoryStorage(), limits: { fileSize: 10 * 1024 * 1024 } });

router.post('/', upload.any(), async (req, res) => {
  try {
    const userId = (req as any).user?.id || null;
    const fields = req.body;
    const files = req.files as Express.Multer.File[] || [];

    if (!fields.name) return res.status(400).json({ error: 'name required' });

    const twin = await prisma.digitalTwin.create({
      data: {
        userId: userId ?? undefined,
        name: fields.name,
        description: fields.description || null,
        language: fields.language || 'ar',
        voiceSettings: fields.voiceSettings ? JSON.parse(fields.voiceSettings) : null,
        personalityTags: fields.personality_traits ? JSON.parse(fields.personality_traits) : null,
        status: 'processing'
      }
    });

    for (const file of files) {
      if (file.fieldname === 'voice_sample') {
        const key = `twins/${twin.id}/voice-${Date.now()}-${uuidv4()}.wav`;
        await uploadBuffer(file.buffer, key, file.mimetype);
        await prisma.digitalTwin.update({ where: { id: twin.id }, data: { sampleAudioUrl: key } });
      } else if (file.fieldname === 'face_images') {
        const key = `twins/${twin.id}/img-${Date.now()}-${uuidv4()}.jpg`;
        await uploadBuffer(file.buffer, key, file.mimetype);
        await prisma.twinImage.create({
          data: { twinId: twin.id, url: key }
        });
      }
    }

    await prisma.jobLog.create({
      data: {
        type: 'process_twin',
        payload: { twinId: twin.id },
        status: 'queued'
      }
    });

    res.status(201).json({ id: twin.id, status: 'queued' });
  } catch (err: any) {
    console.error(err);
    res.status(500).json({ error: 'create_failed', detail: String(err) });
  }
});

export default router;
EOF

# stripe route
cat > server/src/routes/stripe.ts <<'EOF'
import { Router } from "express";
import Stripe from "stripe";
import bodyParser from "body-parser";
import dotenv from "dotenv";

dotenv.config();
const stripe = new Stripe(process.env.STRIPE_SECRET_KEY || '', { apiVersion: '2023-11-15' });
const router = Router();

router.post('/create-checkout', async (req, res) => {
  const { priceId, successUrl, cancelUrl, customerEmail } = req.body;
  try {
    const session = await stripe.checkout.sessions.create({
      mode: 'subscription',
      payment_method_types: ['card'],
      line_items: [{ price: priceId, quantity: 1 }],
      success_url: successUrl,
      cancel_url: cancelUrl,
      customer_email: customerEmail
    });
    res.json({ id: session.id, url: session.url });
  } catch (err) {
    console.error(err);
    res.status(500).json({ error: 'stripe_error' });
  }
});

router.post('/webhook', bodyParser.raw({ type: 'application/json' }), (req, res) => {
  const sig = req.headers['stripe-signature'] as string | undefined;
  const webhookSecret = process.env.STRIPE_WEBHOOK_SECRET!;
  let event: Stripe.Event;
  try {
    if (!sig || !webhookSecret) throw new Error('webhook config missing');
    event = stripe.webhooks.constructEvent(req.body, sig, webhookSecret);
  } catch (err) {
    console.error('Webhook signature verification failed.', err);
    return res.status(400).send(`Webhook Error: ${err}`);
  }

  if (event.type === 'checkout.session.completed') {
    const session = event.data.object as Stripe.Checkout.Session;
    console.log('Checkout completed:', session.id);
  }

  res.json({ received: true });
});

export default router;
EOF

# queue service
cat > server/src/services/queue.ts <<'EOF'
import { Queue } from "bullmq";
import IORedis from "ioredis";
const connection = new IORedis(process.env.REDIS_URL || 'redis://localhost:6379');
export const mediaQueue = new Queue('media', { connection });
EOF

# worker
cat > server/src/workers/mediaWorker.ts <<'EOF'
import { Worker } from "bullmq";
import IORedis from "ioredis";
import { PrismaClient } from "@prisma/client";
const prisma = new PrismaClient();
const connection = new IORedis(process.env.REDIS_URL || 'redis://localhost:6379');

const worker = new Worker('media', async job => {
  console.log('Processing job', job.id, job.name, job.data);
  if (job.name === 'process_twin' || job.data?.type === 'process_twin') {
    const { twinId } = job.data;
    await prisma.digitalTwin.update({ where: { id: twinId }, data: { status: 'ready', previewVideoUrl: null } });
  }
}, { connection });

worker.on('failed', (job, err) => {
  console.error('Job failed', job?.id, err);
});
EOF

# server README
cat > server/README.md <<'EOF'
# MATRXe Backend (scaffold)

## Overview
Scaffold Backend for MATRXe:
- Express + TypeScript
- Prisma for Postgres
- S3 presign + simple upload helper
- Stripe skeleton
- BullMQ worker skeleton

## Quick start (local)
1. Copy `.env.example` to `.env` and fill values.
2. Start Postgres & Redis (docker-compose).
3. Install and run:
   cd server
   npm install
   npx prisma generate
   npx prisma migrate dev --name init
   npm run dev

## Worker
Run worker separately:
   npm run dev // or run built worker

## Notes
Use presigned uploads from frontend for production (S3).
EOF

# 8) frontend modifications
mkdir -p frontend/src/services/api frontend/src/components
cat > frontend/vite.config.js <<'EOF'
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': 'http://localhost:4000'
    }
  }
})
EOF

cat > frontend/src/services/api/twinService.js <<'EOF'
// TwinService - simple wrapper to post multipart FormData to /api/twins
export const TwinService = {
  async createDigitalTwin(formData) {
    const resp = await fetch('/api/twins', {
      method: 'POST',
      credentials: 'include',
      body: formData
    });
    if (!resp.ok) {
      const err = await resp.json().catch(()=>({ message: 'server_error' }));
      throw new Error(err?.message || `HTTP ${resp.status}`);
    }
    return resp.json();
  }
};
export default TwinService;
EOF

cat > frontend/src/components/ImageUploaderPresign.jsx <<'EOF'
import React from 'react';

export default function ImageUploaderPresign({ onUploaded }) {
  const inputRef = React.useRef();

  async function uploadFile(file) {
    const r = await fetch('/api/uploads/presign', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ filename: file.name, contentType: file.type })
    });
    if (!r.ok) throw new Error('presign failed');
    const { url, key } = await r.json();
    await fetch(url, { method: 'PUT', body: file, headers: { 'Content-Type': file.type } });
    onUploaded({ key });
  }

  return (
    <div>
      <input ref={inputRef} type="file" accept="image/*" onChange={e => uploadFile(e.target.files[0])} style={{display:'none'}} />
      <button type="button" onClick={() => inputRef.current?.click()}>Upload Image</button>
    </div>
  );
}
EOF

# deploy script
cat > deploy.sh <<'EOF'
#!/usr/bin/env bash
set -e
BRANCH=${1:-feature/fullstack-mvp}
echo "Deploying branch: $BRANCH"
git fetch origin
git checkout $BRANCH
git pull origin $BRANCH
cd frontend || true
npm ci
npm run build
sudo rm -rf /var/www/matrxe/* || true
sudo cp -r dist/* /var/www/matrxe/ || true
cd ..
sudo docker compose build
sudo docker compose up -d
sudo docker compose exec backend npx prisma migrate deploy || true
echo "Deployment finished."
EOF
chmod +x deploy.sh

# End writing files
echo "الملفات كتبت بنجاح. الآن إضافة إلى git و commit/push..."

# Git add, commit, push
git add -A
git commit -m "$COMMIT_MSG" || (echo "لا توجد تغييرات جديدة لالتزامها." )
git push -u origin "$BRANCH"

echo "تم دفع التغييرات إلى الفرع: $BRANCH"
echo "يمكنك تنزيل الأرشيف من: https://github.com/malek1977/matrxe-digital-twin-platform/archive/refs/heads/$BRANCH.zip"
EOF