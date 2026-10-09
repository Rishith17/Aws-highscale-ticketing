import { v4 as uuidv4 } from 'uuid';
import { DynamoLockService } from '../services/dynamoLockService.js';
import { SqsQueueService } from '../services/sqsQueueService.js';

export class CheckoutController {
  /**
   * Acquire a temporary 10-minute hold lock on a seat via DynamoDB conditional update
   */
  static async lockSeat(req, res) {
    const { eventId, seatId, userId } = req.body;

    if (!eventId || !seatId || !userId) {
      return res.status(400).json({
        success: false,
        error: 'Missing required parameters: eventId, seatId, userId'
      });
    }

    try {
      const lockResult = await DynamoLockService.acquireSeatLock(eventId, seatId, userId, 600);

      if (!lockResult.success) {
        return res.status(409).json({
          success: false,
          code: 'SEAT_UNAVAILABLE',
          message: lockResult.message
        });
      }

      return res.json({
        success: true,
        message: `Seat ${seatId} successfully held for 10 minutes.`,
        data: {
          seatId,
          userId,
          lockExpiresAt: lockResult.lockExpiresAt,
          holdSeconds: 600
        }
      });
    } catch (err) {
      console.error('Error locking seat:', err);
      return res.status(500).json({ success: false, error: err.message });
    }
  }

  /**
   * Release a previously acquired seat lock
   */
  static async releaseLock(req, res) {
    const { eventId, seatId, userId } = req.body;
    try {
      const result = await DynamoLockService.releaseSeatLock(eventId, seatId, userId);
      return res.json({ success: true, ...result });
    } catch (err) {
      return res.status(500).json({ success: false, error: err.message });
    }
  }

  /**
   * Complete checkout and dispatch purchase order to SQS FIFO queue
   */
  static async submitPurchase(req, res) {
    const { eventId, seatId, userId, customerEmail, amount } = req.body;

    if (!eventId || !seatId || !userId || !customerEmail) {
      return res.status(400).json({
        success: false,
        error: 'Missing required checkout fields: eventId, seatId, userId, customerEmail'
      });
    }

    const orderId = `ORD-${Date.now()}-${uuidv4().substring(0, 8).toUpperCase()}`;

    try {
      // 1. Verify seat lock still belongs to this user
      const seats = await DynamoLockService.getEventSeats(eventId);
      const currentSeat = seats.find(s => s.seatId === seatId);

      if (!currentSeat || currentSeat.status !== 'LOCKED' || currentSeat.lockedByUserId !== userId) {
        return res.status(410).json({
          success: false,
          code: 'LOCK_EXPIRED',
          message: 'Your hold on this seat has expired or was not acquired. Please re-select a seat.'
        });
      }

      // 2. Dispatch to SQS FIFO queue for durable, ordered, decoupled fulfillment
      const sqsResult = await SqsQueueService.enqueuePurchase({
        orderId,
        eventId,
        seatId,
        userId,
        customerEmail,
        amount: amount || currentSeat.price || 150
      });

      // 3. Return 202 Accepted to the client immediately
      return res.status(202).json({
        success: true,
        status: 'PROCESSING',
        message: 'Order accepted and queued for fulfillment.',
        order: {
          orderId,
          eventId,
          seatId,
          customerEmail,
          amount: amount || currentSeat.price,
          queueMessageId: sqsResult.messageId
        }
      });
    } catch (err) {
      console.error('Checkout Submission Error:', err);
      return res.status(500).json({ success: false, error: err.message });
    }
  }
}
