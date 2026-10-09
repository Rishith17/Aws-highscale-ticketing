import { SESClient, SendEmailCommand } from '@aws-sdk/client-ses';

const region = process.env.AWS_REGION || 'us-east-1';
const localstackEndpoint = process.env.LOCALSTACK_ENDPOINT || null;

const ses = new SESClient({
  region,
  ...(localstackEndpoint ? {
    endpoint: localstackEndpoint,
    credentials: { accessKeyId: 'test', secretAccessKey: 'test' }
  } : {})
});

const SENDER_EMAIL = process.env.SES_SENDER_EMAIL || 'tickets@concerts-india.com';

/**
 * Send ticket confirmation email via Amazon SES
 */
export async function sendTicketEmail(orderData) {
  const { orderId, eventId, seatId, customerEmail, amount } = orderData;

  const htmlBody = `
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="utf-8">
      <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #0b0f19; color: #f8fafc; margin: 0; padding: 20px; }
        .ticket-card { max-width: 580px; margin: 0 auto; background: #131b2e; border-radius: 16px; border: 1px solid #1e293b; overflow: hidden; }
        .header { background: linear-gradient(135deg, #f97316 0%, #dc2626 50%, #9333ea 100%); padding: 28px; text-align: center; }
        .header h1 { margin: 0; font-size: 24px; color: #ffffff; letter-spacing: 0.5px; }
        .header p { margin: 6px 0 0; color: #ffedd5; font-size: 14px; }
        .body { padding: 28px; }
        .info-row { display: flex; justify-content: space-between; border-bottom: 1px solid #1e293b; padding: 12px 0; }
        .label { color: #94a3b8; font-size: 14px; }
        .value { color: #f8fafc; font-weight: 700; font-size: 15px; }
        .qr-placeholder { text-align: center; margin: 24px 0; background: #090d16; padding: 24px; border-radius: 12px; border: 2px dashed #f97316; }
        .footer { text-align: center; padding: 18px; color: #64748b; font-size: 12px; background: #0d1322; }
      </style>
    </head>
    <body>
      <div class="ticket-card">
        <div class="header">
          <h1>🎟️ Official Concert Entry Pass</h1>
          <p>Diljit Dosanjh — DIL-LUMINATI Tour India</p>
        </div>
        <div class="body">
          <div class="info-row">
            <span class="label">Booking Ref:</span>
            <span class="value">${orderId}</span>
          </div>
          <div class="info-row">
            <span class="label">Concert Venue:</span>
            <span class="value">DY Patil Stadium, Navi Mumbai</span>
          </div>
          <div class="info-row">
            <span class="label">Seat / Zone:</span>
            <span class="value" style="color: #38bdf8; font-size: 18px;">${seatId}</span>
          </div>
          <div class="info-row">
            <span class="label">Amount Paid:</span>
            <span class="value" style="color: #22c55e;">₹${Number(amount).toLocaleString('en-IN')} INR</span>
          </div>
          <div class="qr-placeholder">
            <p style="color: #f97316; font-weight: 800; font-size: 16px; margin: 0;">SCAN AT GATE ENTRY</p>
            <p style="color: #64748b; font-size: 11px; margin: 6px 0 0;">Digital Signature: ${orderId}-DYPATIL-SECURE</p>
          </div>
        </div>
        <div class="footer">
          Processed via AWS Event-Driven Architecture (SQS FIFO ➔ AWS Lambda ➔ RDS PostgreSQL ➔ Amazon SES)
        </div>
      </div>
    </body>
    </html>
  `;

  const params = {
    Source: SENDER_EMAIL,
    Destination: {
      ToAddresses: [customerEmail]
    },
    Message: {
      Subject: {
        Data: `🎟️ Concert Tickets Confirmed! Booking #${orderId} (Diljit DIL-LUMINATI Tour)`,
        Charset: 'UTF-8'
      },
      Body: {
        Html: { Data: htmlBody, Charset: 'UTF-8' },
        Text: { Data: `Your ticket booking ${orderId} for seat ${seatId} at DY Patil Stadium is confirmed! Total: ₹${amount}`, Charset: 'UTF-8' }
      }
    }
  };

  try {
    const result = await ses.send(new SendEmailCommand(params));
    return result;
  } catch (err) {
    console.error(`[SES ERROR]`, err);
    return null;
  }
}
