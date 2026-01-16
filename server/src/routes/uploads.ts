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
