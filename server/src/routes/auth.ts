import { Router } from 'express';
const router = Router();

// Placeholder endpoints for auth (signup/login) - implement as needed
router.post('/signup', (req, res) => res.json({ ok: true }));
router.post('/login', (req, res) => res.json({ ok: true }));

export default router;
