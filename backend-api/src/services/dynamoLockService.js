import { QueryCommand, UpdateCommand, PutCommand } from '@aws-sdk/lib-dynamodb';
import { config, docClient } from '../config.js';

/**
 * Service handling ultra-fast seat locking and availability checks in DynamoDB
 */
export class DynamoLockService {
  /**
   * Fetch all seat statuses for an event
   */
  static async getEventSeats(eventId) {
    const params = {
      TableName: config.dynamoTableName,
      KeyConditionExpression: 'PK = :pk AND begins_with(SK, :skPrefix)',
      ExpressionAttributeValues: {
        ':pk': `EVENT#${eventId}`,
        ':skPrefix': 'SEAT#'
      }
    };

    try {
      const response = await docClient.send(new QueryCommand(params));
      const now = Math.floor(Date.now() / 1000);

      // Map raw items, evaluating TTL expiration dynamically
      return (response.Items || []).map(item => {
        let effectiveStatus = item.status || 'AVAILABLE';
        if (effectiveStatus === 'LOCKED' && item.lockExpiresAt && item.lockExpiresAt <= now) {
          effectiveStatus = 'AVAILABLE';
        }
        return {
          seatId: item.SK.replace('SEAT#', ''),
          section: item.section || 'General',
          tier: item.tier || 'Standard',
          price: item.price || 150,
          status: effectiveStatus,
          lockedByUserId: effectiveStatus === 'LOCKED' ? item.lockedByUserId : null,
          lockExpiresAt: item.lockExpiresAt
        };
      });
    } catch (err) {
      console.error('Error querying seats from DynamoDB:', err);
      throw err;
    }
  }

  /**
   * Acquire an atomic lock on a seat.
   * Condition: Seat must either not exist yet, be 'AVAILABLE', or have an expired lock TTL.
   */
  static async acquireSeatLock(eventId, seatId, userId, holdSeconds = 600) {
    const now = Math.floor(Date.now() / 1000);
    const lockExpiresAt = now + holdSeconds;

    const params = {
      TableName: config.dynamoTableName,
      Key: {
        PK: `EVENT#${eventId}`,
        SK: `SEAT#${seatId}`
      },
      UpdateExpression: 'SET #st = :locked, lockedByUserId = :uid, lockExpiresAt = :ttl, updatedAt = :now',
      ConditionExpression: 'attribute_not_exists(#st) OR #st = :avail OR lockExpiresAt < :now',
      ExpressionAttributeNames: {
        '#st': 'status'
      },
      ExpressionAttributeValues: {
        ':locked': 'LOCKED',
        ':avail': 'AVAILABLE',
        ':uid': userId,
        ':ttl': lockExpiresAt,
        ':now': now
      },
      ReturnValues: 'ALL_NEW'
    };

    try {
      const result = await docClient.send(new UpdateCommand(params));
      return {
        success: true,
        seatId,
        lockedByUserId: userId,
        lockExpiresAt,
        item: result.Attributes
      };
    } catch (err) {
      if (err.name === 'ConditionalCheckFailedException') {
        return {
          success: false,
          error: 'SEAT_ALREADY_RESERVED',
          message: `Seat ${seatId} is currently reserved or sold to another customer.`
        };
      }
      console.error('DynamoDB Lock Acquisition Error:', err);
      throw err;
    }
  }

  /**
   * Release seat lock if user cancels checkout or order fails
   */
  static async releaseSeatLock(eventId, seatId, userId) {
    const params = {
      TableName: config.dynamoTableName,
      Key: {
        PK: `EVENT#${eventId}`,
        SK: `SEAT#${seatId}`
      },
      UpdateExpression: 'SET #st = :avail REMOVE lockedByUserId, lockExpiresAt',
      ConditionExpression: '#st = :locked AND lockedByUserId = :uid',
      ExpressionAttributeNames: {
        '#st': 'status'
      },
      ExpressionAttributeValues: {
        ':locked': 'LOCKED',
        ':avail': 'AVAILABLE',
        ':uid': userId
      }
    };

    try {
      await docClient.send(new UpdateCommand(params));
      return { success: true };
    } catch (err) {
      if (err.name === 'ConditionalCheckFailedException') {
        return { success: false, message: 'Seat was not locked by this user.' };
      }
      throw err;
    }
  }

  /**
   * Initialize seat inventory for an event
   */
  static async seedSeats(eventId, seats) {
    for (const seat of seats) {
      await docClient.send(new PutCommand({
        TableName: config.dynamoTableName,
        Item: {
          PK: `EVENT#${eventId}`,
          SK: `SEAT#${seat.seatId}`,
          status: 'AVAILABLE',
          section: seat.section,
          tier: seat.tier,
          price: seat.price
        }
      }));
    }
  }
}
