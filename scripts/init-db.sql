-- PostgreSQL Schema initialization for RDS Ticketing Database

CREATE TABLE IF NOT EXISTS users (
    id VARCHAR(64) PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    name VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS events (
    id VARCHAR(64) PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    venue VARCHAR(255) NOT NULL,
    event_date TIMESTAMP WITH TIME ZONE NOT NULL,
    base_price NUMERIC(10, 2) NOT NULL,
    total_tickets INT NOT NULL,
    banner_url TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS orders (
    id VARCHAR(64) PRIMARY KEY,
    user_id VARCHAR(64) REFERENCES users(id),
    event_id VARCHAR(64) REFERENCES events(id),
    total_amount NUMERIC(10, 2) NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'CONFIRMED',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS order_items (
    id SERIAL PRIMARY KEY,
    order_id VARCHAR(64) REFERENCES orders(id),
    seat_number VARCHAR(32) NOT NULL,
    price NUMERIC(10, 2) NOT NULL
);

-- Seed initial event
INSERT INTO events (id, title, venue, event_date, base_price, total_tickets)
VALUES (
    'ev-rock-2026',
    'Neon Odyssey: Global Cyber Rock Tour',
    'Cyber Arena, Los Angeles (Multi-AZ Live)',
    '2026-11-20 20:00:00+00',
    180.00,
    24
)
ON CONFLICT (id) DO NOTHING;
