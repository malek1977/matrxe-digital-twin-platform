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
