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
