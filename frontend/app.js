/**
 * DesiConcerts | Indian Concert High-Scale AWS Architecture Frontend
 */

const API_BASE = window.location.port === '8080' || window.location.pathname.startsWith('/api')
  ? ''
  : 'http://localhost:8080';

const EVENT_ID = 'ev-diljit-mumbai';
const CURRENT_USER_ID = 'user-' + Math.floor(1000 + Math.random() * 9000);

// Default Indian Concert Seats Layout (Currency in ₹ INR)
const DEFAULT_INDIAN_SEATS = [
  // Diamond Fan Pit (VIP Front)
  { seatId: 'PIT-01', section: 'Fan Pit (VIP)', tier: 'Diamond', price: 11999, status: 'AVAILABLE' },
  { seatId: 'PIT-02', section: 'Fan Pit (VIP)', tier: 'Diamond', price: 11999, status: 'AVAILABLE' },
  { seatId: 'PIT-03', section: 'Fan Pit (VIP)', tier: 'Diamond', price: 11999, status: 'AVAILABLE' },
  { seatId: 'PIT-04', section: 'Fan Pit (VIP)', tier: 'Diamond', price: 11999, status: 'SOLD' },
  { seatId: 'PIT-05', section: 'Fan Pit (VIP)', tier: 'Diamond', price: 11999, status: 'AVAILABLE' },
  { seatId: 'PIT-06', section: 'Fan Pit (VIP)', tier: 'Diamond', price: 11999, status: 'AVAILABLE' },

  // Platinum Lounge
  { seatId: 'PLT-01', section: 'Platinum Lounge', tier: 'Platinum', price: 6999, status: 'AVAILABLE' },
  { seatId: 'PLT-02', section: 'Platinum Lounge', tier: 'Platinum', price: 6999, status: 'AVAILABLE' },
  { seatId: 'PLT-03', section: 'Platinum Lounge', tier: 'Platinum', price: 6999, status: 'AVAILABLE' },
  { seatId: 'PLT-04', section: 'Platinum Lounge', tier: 'Platinum', price: 6999, status: 'AVAILABLE' },
  { seatId: 'PLT-05', section: 'Platinum Lounge', tier: 'Platinum', price: 6999, status: 'LOCKED' },
  { seatId: 'PLT-06', section: 'Platinum Lounge', tier: 'Platinum', price: 6999, status: 'AVAILABLE' },

  // Gold Seating
  { seatId: 'GLD-01', section: 'Gold Seating', tier: 'Gold', price: 3499, status: 'AVAILABLE' },
  { seatId: 'GLD-02', section: 'Gold Seating', tier: 'Gold', price: 3499, status: 'AVAILABLE' },
  { seatId: 'GLD-03', section: 'Gold Seating', tier: 'Gold', price: 3499, status: 'AVAILABLE' },
  { seatId: 'GLD-04', section: 'Gold Seating', tier: 'Gold', price: 3499, status: 'AVAILABLE' },
  { seatId: 'GLD-05', section: 'Gold Seating', tier: 'Gold', price: 3499, status: 'AVAILABLE' },
  { seatId: 'GLD-06', section: 'Gold Seating', tier: 'Gold', price: 3499, status: 'AVAILABLE' },

  // Silver Standing
  { seatId: 'SLV-01', section: 'Silver Standing', tier: 'Silver', price: 1499, status: 'AVAILABLE' },
  { seatId: 'SLV-02', section: 'Silver Standing', tier: 'Silver', price: 1499, status: 'AVAILABLE' },
  { seatId: 'SLV-03', section: 'Silver Standing', tier: 'Silver', price: 1499, status: 'AVAILABLE' },
  { seatId: 'SLV-04', section: 'Silver Standing', tier: 'Silver', price: 1499, status: 'AVAILABLE' },
  { seatId: 'SLV-05', section: 'Silver Standing', tier: 'Silver', price: 1499, status: 'AVAILABLE' },
  { seatId: 'SLV-06', section: 'Silver Standing', tier: 'Silver', price: 1499, status: 'AVAILABLE' }
];

let seatsList = [...DEFAULT_INDIAN_SEATS];
let selectedSeat = null;
let holdInterval = null;
let holdSecondsLeft = 600;

// DOM Elements
const seatsGrid = document.getElementById('seatsGrid');
const noSelectionState = document.getElementById('noSelectionState');
const activeSelectionPanel = document.getElementById('activeSelectionPanel');
const confirmedTicketCard = document.getElementById('confirmedTicketCard');

const billSection = document.getElementById('billSection');
const billSeatId = document.getElementById('billSeatId');
const billPrice = document.getElementById('billPrice');
const billTotal = document.getElementById('billTotal');
const btnPayAmount = document.getElementById('btnPayAmount');
const timerDigits = document.getElementById('timerDigits');

const ticketBookingForm = document.getElementById('ticketBookingForm');
const cancelSeatBtn = document.getElementById('cancelSeatBtn');
const bookAnotherBtn = document.getElementById('bookAnotherBtn');
const flowStatusText = document.getElementById('flowStatusText');

// Inspector pre elements
const inspectDynamoJson = document.getElementById('inspectDynamoJson');
const inspectSqsJson = document.getElementById('inspectSqsJson');
const inspectRdsSql = document.getElementById('inspectRdsSql');
const inspectSesJson = document.getElementById('inspectSesJson');

// Pipeline nodes
const pipeCf = document.getElementById('f-cf');
const pipeAlb = document.getElementById('f-alb');
const pipeEc2 = document.getElementById('f-ec2');
const pipeDdb = document.getElementById('f-ddb');
const pipeSqs = document.getElementById('f-sqs');
const pipeLambda = document.getElementById('f-lambda');

// 1. Tab Switching Logic
document.querySelectorAll('.tab-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.tab-view').forEach(v => v.classList.remove('active'));

    btn.classList.add('active');
    const tabId = btn.getAttribute('data-tab');
    document.getElementById(tabId).classList.add('active');
  });
});

// 2. Fetch seats from Backend API or fallback to default
async function fetchSeats() {
  try {
    const res = await fetch(`${API_BASE}/api/events/${EVENT_ID}/seats`);
    if (res.ok) {
      const json = await res.json();
      if (json.success && Array.isArray(json.data) && json.data.length > 0) {
        seatsList = json.data;
      }
    }
  } catch (e) {
    // offline/mock fallback
  }
  renderSeatGrid();
}

// 3. Render Seating Zones
function renderSeatGrid() {
  seatsGrid.innerHTML = '';

  seatsList.forEach(seat => {
    const box = document.createElement('div');
    box.className = `seat-box ${seat.status.toLowerCase()}`;
    if (selectedSeat && selectedSeat.seatId === seat.seatId) {
      box.classList.add('selected');
    }

    box.innerHTML = `
      <span class="s-id">${seat.seatId}</span>
      <span class="s-zone">${seat.section}</span>
      <span class="s-price">₹${seat.price.toLocaleString('en-IN')}</span>
    `;

    box.addEventListener('click', () => handleSeatSelect(seat));
    seatsGrid.appendChild(box);
  });
}

// 4. Handle Seat Click & DynamoDB Hold
async function handleSeatSelect(seat) {
  if (seat.status === 'SOLD') {
    alert('This seat is already sold out!');
    return;
  }
  if (seat.status === 'LOCKED' && (!selectedSeat || selectedSeat.seatId !== seat.seatId)) {
    alert(`Seat ${seat.seatId} is temporarily locked by another user! DynamoDB conditional check prevented double-booking.`);
    return;
  }

  // Visual flow animation
  pulsePipeline(pipeDdb);
  flowStatusText.innerHTML = `<strong>DynamoDB:</strong> Conditional write locked seat <code>${seat.seatId}</code> with 10-min TTL.`;

  // Backend API lock attempt
  try {
    await fetch(`${API_BASE}/api/checkout/lock`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        eventId: EVENT_ID,
        seatId: seat.seatId,
        userId: CURRENT_USER_ID
      })
    });
  } catch (e) {
    // mock fallback
  }

  selectedSeat = seat;
  seat.status = 'LOCKED';
  renderSeatGrid();
  updateCheckoutPanel(seat);
  updateInspector(seat);
}

// 5. Update Checkout Sidebar
function updateCheckoutPanel(seat) {
  noSelectionState.classList.add('hidden');
  confirmedTicketCard.classList.add('hidden');
  activeSelectionPanel.classList.remove('hidden');

  billSection.textContent = `${seat.section} (${seat.tier})`;
  billSeatId.textContent = seat.seatId;
  billPrice.textContent = `₹${seat.price.toLocaleString('en-IN')}`;
  billTotal.textContent = `₹${seat.price.toLocaleString('en-IN')}`;
  btnPayAmount.textContent = `₹${seat.price.toLocaleString('en-IN')}`;

  startHoldTimer(600);
}

// 6. Hold Timer
function startHoldTimer(seconds) {
  clearInterval(holdInterval);
  holdSecondsLeft = seconds;

  function tick() {
    const m = Math.floor(holdSecondsLeft / 60);
    const s = holdSecondsLeft % 60;
    timerDigits.textContent = `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;

    if (holdSecondsLeft <= 0) {
      clearInterval(holdInterval);
      alert('10-minute hold has expired. Seat returned to pool.');
      cancelHold();
    }
    holdSecondsLeft--;
  }

  tick();
  holdInterval = setInterval(tick, 1000);
}

function cancelHold() {
  if (selectedSeat) {
    selectedSeat.status = 'AVAILABLE';
  }
  selectedSeat = null;
  clearInterval(holdInterval);

  activeSelectionPanel.classList.add('hidden');
  noSelectionState.classList.remove('hidden');
  flowStatusText.textContent = 'Hold released. Ready for next seat selection.';
  renderSeatGrid();
}

cancelSeatBtn.addEventListener('click', cancelHold);

// 7. Complete Booking via SQS FIFO
ticketBookingForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  if (!selectedSeat) return;

  const name = document.getElementById('custName').value;
  const email = document.getElementById('custEmail').value;
  const orderId = `ORD-MUM-${Date.now().toString().slice(-6)}`;

  const bookBtn = document.getElementById('bookTicketBtn');
  bookBtn.disabled = true;
  bookBtn.innerHTML = `<span>Processing Order...</span>`;

  // Step 1: SQS Push
  pulsePipeline(pipeSqs);
  flowStatusText.innerHTML = `<strong>Amazon SQS FIFO:</strong> Order <code>${orderId}</code> pushed to FIFO purchase queue.`;

  try {
    await fetch(`${API_BASE}/api/checkout/purchase`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        eventId: EVENT_ID,
        seatId: selectedSeat.seatId,
        userId: CURRENT_USER_ID,
        customerEmail: email,
        amount: selectedSeat.price
      })
    });
  } catch (e) {
    // mock fallback
  }

  // Step 2: Lambda & RDS Commit Simulation
  setTimeout(() => {
    pulsePipeline(pipeLambda);
    flowStatusText.innerHTML = `<strong>AWS Lambda & RDS:</strong> Pulled from SQS ➔ ACID write to PostgreSQL ➔ Email dispatched via SES to <code>${email}</code>!`;
  }, 700);

  // Step 3: Show E-Ticket
  setTimeout(() => {
    clearInterval(holdInterval);
    selectedSeat.status = 'SOLD';
    renderSeatGrid();

    activeSelectionPanel.classList.add('hidden');
    confirmedTicketCard.classList.remove('hidden');

    document.getElementById('passBookingId').textContent = orderId;
    document.getElementById('passSeat').textContent = `${selectedSeat.seatId} (${selectedSeat.section})`;
    document.getElementById('passName').textContent = name;
    document.getElementById('passAmount').textContent = `₹${selectedSeat.price.toLocaleString('en-IN')}`;

    bookBtn.disabled = false;
    bookBtn.innerHTML = `
      <span>Pay <span id="btnPayAmount">₹${selectedSeat.price.toLocaleString('en-IN')}</span> & Confirm Booking</span>
      <small>Dispatches to AWS SQS FIFO Queue</small>
    `;

    updateInspectorAfterBooking(orderId, name, email);
  }, 1200);
});

bookAnotherBtn.addEventListener('click', () => {
  selectedSeat = null;
  confirmedTicketCard.classList.add('hidden');
  noSelectionState.classList.remove('hidden');
  fetchSeats();
});

// 8. Pipeline Visual Indicator
function pulsePipeline(node) {
  if (!node) return;
  node.classList.add('firing');
  setTimeout(() => {
    node.classList.remove('firing');
    node.classList.add('active');
  }, 1000);
}

// 9. Update Inspector with Live Data
function updateInspector(seat) {
  const now = Math.floor(Date.now() / 1000);
  inspectDynamoJson.textContent = JSON.stringify({
    PK: `EVENT#${EVENT_ID}`,
    SK: `SEAT#${seat.seatId}`,
    section: seat.section,
    tier: seat.tier,
    price: seat.price,
    currency: 'INR',
    status: 'LOCKED',
    lockedByUserId: CURRENT_USER_ID,
    lockExpiresAt: now + 600,
    _comment: 'DynamoDB atomic lock active for 10 mins'
  }, null, 2);
}

function updateInspectorAfterBooking(orderId, name, email) {
  inspectSqsJson.textContent = JSON.stringify({
    QueueUrl: "https://sqs.us-east-1.amazonaws.com/12345/ticket-purchases.fifo",
    MessageGroupId: `EVENT-${EVENT_ID}`,
    MessageDeduplicationId: `${orderId}-${selectedSeat.seatId}`,
    Body: {
      orderId,
      seatId: selectedSeat.seatId,
      amount: selectedSeat.price,
      currency: "INR",
      customerEmail: email,
      customerName: name,
      timestamp: new Date().toISOString()
    }
  }, null, 2);

  inspectRdsSql.textContent = `BEGIN;

INSERT INTO users (id, email, name)
VALUES ('${CURRENT_USER_ID}', '${email}', '${name}')
ON CONFLICT (id) DO UPDATE SET email = EXCLUDED.email;

INSERT INTO orders (id, user_id, event_id, total_amount, status)
VALUES ('${orderId}', '${CURRENT_USER_ID}', '${EVENT_ID}', ${selectedSeat.price}.00, 'CONFIRMED');

INSERT INTO order_items (order_id, seat_number, price)
VALUES ('${orderId}', '${selectedSeat.seatId}', ${selectedSeat.price}.00);

COMMIT;`;

  inspectSesJson.textContent = JSON.stringify({
    Source: "tickets@concerts-india.com",
    Destination: { ToAddresses: [email] },
    Message: {
      Subject: `🎟️ Diljit DIL-LUMINATI Tour — Booking Confirmed (#${orderId})`,
      Body: `Official Gate Entry Pass attached for Seat ${selectedSeat.seatId}. Total Paid: ₹${selectedSeat.price.toLocaleString('en-IN')} INR.`
    }
  }, null, 2);
}

// Initialize
fetchSeats();
