import { DynamoLockService } from '../services/dynamoLockService.js';
import { dbPool } from '../config.js';

// Indian Concert Event Catalog
const DEFAULT_EVENTS = [
  {
    id: 'ev-diljit-mumbai',
    title: 'Diljit Dosanjh — DIL-LUMINATI Tour India',
    venue: 'DY Patil Stadium, Navi Mumbai',
    date: '2026-11-14T19:00:00+05:30',
    currency: '₹',
    price: 3499,
    bannerUrl: 'https://images.unsplash.com/photo-1470225620780-dba8ba36b745?auto=format&fit=crop&w=1200&q=80',
    totalSeats: 30
  },
  {
    id: 'ev-arijit-bengaluru',
    title: 'Arijit Singh Live — Soulful Symphony',
    venue: 'NICE Grounds, Bengaluru',
    date: '2026-12-12T18:30:00+05:30',
    currency: '₹',
    price: 2999,
    bannerUrl: 'https://images.unsplash.com/photo-1540575467063-178a50c2df87?auto=format&fit=crop&w=1200&q=80',
    totalSeats: 30
  }
];

export class EventController {
  static async listEvents(req, res) {
    return res.json({ success: true, data: DEFAULT_EVENTS });
  }

  static async getSeats(req, res) {
    const { eventId } = req.params;
    try {
      let seats = await DynamoLockService.getEventSeats(eventId);

      // Seed Indian Concert Seat Layout if empty
      if (!seats || seats.length === 0) {
        const seedLayout = [
          // Fan Pit (VIP Front)
          { seatId: 'PIT-01', section: 'Fan Pit (VIP)', tier: 'Diamond', price: 11999 },
          { seatId: 'PIT-02', section: 'Fan Pit (VIP)', tier: 'Diamond', price: 11999 },
          { seatId: 'PIT-03', section: 'Fan Pit (VIP)', tier: 'Diamond', price: 11999 },
          { seatId: 'PIT-04', section: 'Fan Pit (VIP)', tier: 'Diamond', price: 11999 },
          { seatId: 'PIT-05', section: 'Fan Pit (VIP)', tier: 'Diamond', price: 11999 },
          { seatId: 'PIT-06', section: 'Fan Pit (VIP)', tier: 'Diamond', price: 11999 },
          
          // Platinum Lounge
          { seatId: 'PLT-01', section: 'Platinum Lounge', tier: 'Platinum', price: 6999 },
          { seatId: 'PLT-02', section: 'Platinum Lounge', tier: 'Platinum', price: 6999 },
          { seatId: 'PLT-03', section: 'Platinum Lounge', tier: 'Platinum', price: 6999 },
          { seatId: 'PLT-04', section: 'Platinum Lounge', tier: 'Platinum', price: 6999 },
          { seatId: 'PLT-05', section: 'Platinum Lounge', tier: 'Platinum', price: 6999 },
          { seatId: 'PLT-06', section: 'Platinum Lounge', tier: 'Platinum', price: 6999 },
          
          // Gold Seating
          { seatId: 'GLD-01', section: 'Gold Seating', tier: 'Gold', price: 3499 },
          { seatId: 'GLD-02', section: 'Gold Seating', tier: 'Gold', price: 3499 },
          { seatId: 'GLD-03', section: 'Gold Seating', tier: 'Gold', price: 3499 },
          { seatId: 'GLD-04', section: 'Gold Seating', tier: 'Gold', price: 3499 },
          { seatId: 'GLD-05', section: 'Gold Seating', tier: 'Gold', price: 3499 },
          { seatId: 'GLD-06', section: 'Gold Seating', tier: 'Gold', price: 3499 },

          // Silver Standing
          { seatId: 'SLV-01', section: 'Silver Standing', tier: 'Silver', price: 1499 },
          { seatId: 'SLV-02', section: 'Silver Standing', tier: 'Silver', price: 1499 },
          { seatId: 'SLV-03', section: 'Silver Standing', tier: 'Silver', price: 1499 },
          { seatId: 'SLV-04', section: 'Silver Standing', tier: 'Silver', price: 1499 },
          { seatId: 'SLV-05', section: 'Silver Standing', tier: 'Silver', price: 1499 },
          { seatId: 'SLV-06', section: 'Silver Standing', tier: 'Silver', price: 1499 }
        ];

        try {
          await DynamoLockService.seedSeats(eventId, seedLayout);
          seats = await DynamoLockService.getEventSeats(eventId);
        } catch (e) {
          return res.json({
            success: true,
            eventId,
            data: seedLayout.map(s => ({ ...s, status: 'AVAILABLE' }))
          });
        }
      }

      return res.json({ success: true, eventId, data: seats });
    } catch (err) {
      return res.status(500).json({ success: false, error: err.message });
    }
  }
}
