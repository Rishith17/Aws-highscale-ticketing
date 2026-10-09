import pg from 'pg';

const pool = new pg.Pool({
  host: process.env.DB_HOST || 'localhost',
  port: parseInt(process.env.DB_PORT || '5432', 10),
  database: process.env.DB_NAME || 'ticketdb',
  user: process.env.DB_USER || 'dbadmin',
  password: process.env.DB_PASSWORD || 'SecurePassword123!',
  max: 5,
  idleTimeoutMillis: 30000,
  connectionTimeoutMillis: 5000,
});

/**
 * Execute an ACID database transaction to record the finalized ticket purchase in RDS
 */
export async function persistOrderToRDS(orderData) {
  const { orderId, eventId, seatId, userId, customerEmail, amount } = orderData;
  const client = await pool.connect();

  try {
    await client.query('BEGIN');

    // 1. Ensure user exists or upsert user
    const userQuery = `
      INSERT INTO users (id, email, name, created_at)
      VALUES ($1, $2, $3, NOW())
      ON CONFLICT (id) DO UPDATE SET email = EXCLUDED.email
    `;
    await client.query(userQuery, [userId, customerEmail, customerEmail.split('@')[0]]);

    // 2. Insert order
    const orderQuery = `
      INSERT INTO orders (id, user_id, event_id, total_amount, status, created_at)
      VALUES ($1, $2, $3, $4, 'CONFIRMED', NOW())
      ON CONFLICT (id) DO NOTHING
    `;
    await client.query(orderQuery, [orderId, userId, eventId, amount]);

    // 3. Insert order item
    const itemQuery = `
      INSERT INTO order_items (order_id, seat_number, price)
      VALUES ($1, $2, $3)
      ON CONFLICT DO NOTHING
    `;
    await client.query(itemQuery, [orderId, seatId, amount]);

    await client.query('COMMIT');
    console.log(`[RDS] Successfully committed order ${orderId} to PostgreSQL.`);
    return true;
  } catch (err) {
    await client.query('ROLLBACK');
    console.error(`[RDS ERROR] Transaction rollback for order ${orderId}:`, err);
    throw err;
  } finally {
    client.release();
  }
}
