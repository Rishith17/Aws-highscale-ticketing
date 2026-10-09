import { DynamoDBClient } from '@aws-sdk/client-dynamodb';
import { DynamoDBDocumentClient, UpdateCommand } from '@aws-sdk/lib-dynamodb';
import { persistOrderToRDS } from './db.js';
import { sendTicketEmail } from './emailService.js';

const region = process.env.AWS_REGION || 'us-east-1';
const tableName = process.env.DYNAMODB_TABLE_NAME || 'TicketInventory';
const localstackEndpoint = process.env.LOCALSTACK_ENDPOINT || null;

const dynamoRaw = new DynamoDBClient({
  region,
  ...(localstackEndpoint ? {
    endpoint: localstackEndpoint,
    credentials: { accessKeyId: 'test', secretAccessKey: 'test' }
  } : {})
});
const docClient = DynamoDBDocumentClient.from(dynamoRaw);

/**
 * AWS Lambda Event Handler for SQS FIFO purchase orders
 */
export async function handler(event, context) {
  console.log(`[LAMBDA] Invoked with ${event.Records?.length || 0} SQS record(s).`);

  const results = [];

  for (const record of event.Records || []) {
    let orderData;
    try {
      orderData = JSON.parse(record.body);
    } catch (parseErr) {
      console.error('[LAMBDA ERROR] Failed to parse message body:', record.body);
      continue;
    }

    const { orderId, eventId, seatId, userId, customerEmail, amount } = orderData;
    console.log(`[LAMBDA] Processing order: ${orderId} | Seat: ${seatId} | Event: ${eventId}`);

    try {
      // Step 1: ACID Database write to PostgreSQL (orders & items)
      await persistOrderToRDS(orderData);

      // Step 2: Finalize DynamoDB seat status as permanently SOLD
      await docClient.send(new UpdateCommand({
        TableName: tableName,
        Key: {
          PK: `EVENT#${eventId}`,
          SK: `SEAT#${seatId}`
        },
        UpdateExpression: 'SET #st = :sold, finalizedOrderId = :oid, finalizedAt = :now REMOVE lockExpiresAt',
        ExpressionAttributeNames: { '#st': 'status' },
        ExpressionAttributeValues: {
          ':sold': 'SOLD',
          ':oid': orderId,
          ':now': new Date().toISOString()
        }
      }));
      console.log(`[DYNAMODB] Seat ${seatId} marked as SOLD for order ${orderId}.`);

      // Step 3: Trigger SES Confirmation Email
      await sendTicketEmail(orderData);

      results.push({ orderId, status: 'SUCCESS' });
    } catch (orderErr) {
      console.error(`[LAMBDA FAILURE] Error processing order ${orderId}:`, orderErr);
      // Re-throwing causes SQS FIFO to retry and eventually send to DLQ if maxReceiveCount exceeded
      throw orderErr;
    }
  }

  return {
    statusCode: 200,
    body: JSON.stringify({ message: 'Batch completed successfully', results })
  };
}
