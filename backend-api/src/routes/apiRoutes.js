import { Router } from 'express';
import { EventController } from '../controllers/eventController.js';
import { CheckoutController } from '../controllers/checkoutController.js';

export const apiRouter = Router();

// Events & Inventory
apiRouter.get('/events', EventController.listEvents);
apiRouter.get('/events/:eventId/seats', EventController.getSeats);

// Checkout & Lock Flow
apiRouter.post('/checkout/lock', CheckoutController.lockSeat);
apiRouter.post('/checkout/release', CheckoutController.releaseLock);
apiRouter.post('/checkout/purchase', CheckoutController.submitPurchase);
