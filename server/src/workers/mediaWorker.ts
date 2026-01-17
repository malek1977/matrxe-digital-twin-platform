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
