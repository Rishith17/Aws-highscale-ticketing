import express from 'express';
import cors from 'cors';
import { config } from './config.js';
import { healthRouter } from './routes/healthRoutes.js';
import { apiRouter } from './routes/apiRoutes.js';

const app = express();

// Middlewares
app.use(cors());
app.use(express.json());

// Request logger for CloudWatch debugging
app.use((req, res, next) => {
  const start = Date.now();
  res.on('finish', () => {
    const duration = Date.now() - start;
    console.log(`[HTTP] ${req.method} ${req.originalUrl} ${res.statusCode} (${duration}ms)`);
  });
  next();
});

// Mount Routes
app.use(healthRouter);         // /health for ALB probes
app.use('/api', apiRouter);    // /api/* for application endpoints

// Error Handler
app.use((err, req, res, next) => {
  console.error('[SERVER ERROR]', err);
  res.status(500).json({
    success: false,
    error: 'Internal Server Error',
    message: err.message
  });
});

app.listen(config.port, '0.0.0.0', () => {
  console.log(`====================================================`);
  console.log(`🚀 Ticketing API Server running on port ${config.port}`);
  console.log(`📍 Region: ${config.awsRegion}`);
  console.log(`📦 DynamoDB Table: ${config.dynamoTableName}`);
  console.log(`📬 SQS Queue URL: ${config.sqsQueueUrl || 'Not set (Local Mock)'}`);
  console.log(`====================================================`);
});
