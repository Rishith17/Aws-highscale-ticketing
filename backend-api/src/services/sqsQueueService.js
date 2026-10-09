import { SendMessageCommand } from '@aws-sdk/client-sqs';
import { config, sqsClient } from '../config.js';

/**
 * Service to publish purchase orders into Amazon SQS FIFO Queue
 */
export class SqsQueueService {
  /**
   * Enqueue order payload into FIFO queue
   */
  static async enqueuePurchase(orderData) {
    const { orderId, eventId, seatId, userId, customerEmail, amount } = orderData;

    // FIFO Deduplication ID: unique combination of order ID and seat ID
    const deduplicationId = `${orderId}-${seatId}`;
    
    // FIFO Message Group ID: orders for the same event are sequenced in FIFO order
    const messageGroupId = `EVENT-${eventId}`;

    const payload = {
      orderId,
      eventId,
      seatId,
      userId,
      customerEmail,
      amount,
      createdAt: new Date().toISOString()
    };

    if (!config.sqsQueueUrl) {
      console.warn('[SQS WARN] SQS_QUEUE_URL not defined. Mocking SQS dispatch locally:', payload);
      return {
        messageId: `mock-${orderId}`,
        sequenceNumber: '1000000000',
        mock: true
      };
    }

    const command = new SendMessageCommand({
      QueueUrl: config.sqsQueueUrl,
      MessageBody: JSON.stringify(payload),
      MessageGroupId: messageGroupId,
      MessageDeduplicationId: deduplicationId,
      MessageAttributes: {
        EventType: {
          DataType: 'String',
          StringValue: 'TICKET_PURCHASE_REQUEST'
        }
      }
    });

    try {
      const response = await sqsClient.send(command);
      console.log(`[SQS] Dispatched order ${orderId} to FIFO queue. MessageId: ${response.MessageId}`);
      return {
        messageId: response.MessageId,
        sequenceNumber: response.SequenceNumber
      };
    } catch (err) {
      console.error('[SQS ERROR] Failed to push to FIFO queue:', err);
      throw err;
    }
  }
}
