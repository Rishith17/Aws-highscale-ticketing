import dotenv from 'dotenv';
import { DynamoDBClient } from '@aws-sdk/client-dynamodb';
import { DynamoDBDocumentClient } from '@aws-sdk/lib-dynamodb';
import { SQSClient } from '@aws-sdk/client-sqs';
import pg from 'pg';

dotenv.config();

export const config = {
  port: process.env.PORT || 8080,
  awsRegion: process.env.AWS_REGION || 'ap-south-1',
  dynamoTableName: process.env.DYNAMODB_TABLE_NAME || 'TicketInventory',
  sqsQueueUrl: process.env.SQS_QUEUE_URL || '',
  accessKeyId: process.env.AWS_ACCESS_KEY_ID || '',
  secretAccessKey: process.env.AWS_SECRET_ACCESS_KEY || '',
  localstackEndpoint: process.env.LOCALSTACK_ENDPOINT || null,
  postgres: {
    host: process.env.DB_HOST || 'localhost',
    port: parseInt(process.env.DB_PORT || '5432', 10),
    database: process.env.DB_NAME || 'ticketdb',
    user: process.env.DB_USER || 'dbadmin',
    password: process.env.DB_PASSWORD || 'SecurePassword123!',
  }
};

// AWS Client configurations
const awsClientConfig = {
  region: config.awsRegion,
  ...(config.accessKeyId && config.secretAccessKey ? {
    credentials: {
      accessKeyId: config.accessKeyId,
      secretAccessKey: config.secretAccessKey,
    }
  } : {}),
  ...(config.localstackEndpoint ? {
    endpoint: config.localstackEndpoint,
    credentials: {
      accessKeyId: 'test',
      secretAccessKey: 'test',
    }
  } : {})
};

const rawDynamo = new DynamoDBClient(awsClientConfig);
export const docClient = DynamoDBDocumentClient.from(rawDynamo, {
  marshallOptions: { removeUndefinedValues: true }
});

export const sqsClient = new SQSClient(awsClientConfig);

// PostgreSQL pool
export const dbPool = new pg.Pool(config.postgres);
