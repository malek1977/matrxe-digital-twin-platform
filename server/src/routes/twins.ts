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
