CREATE TYPE recurrance AS ENUM(
    'irregular', 'monthly', 'annual'
);

CREATE TABLE order(
        id SERIAL PRIMARY KEY,
        customer_id integer REFERENCES customer(id),
        total_amount money, /* testing if comma is stripped */
        order_status_id integer NOT NULL REFERENCES order_status(id)
);

CREATE TABLE customer(
    id SERIAL PRIMARY KEY,
    name text NOT NULL,
    phone_number text,
    address text UNIQUE NOT NULL
);

CREATE TABLE order_status(
    id SERIAL PRIMARY KEY,
    status string
);