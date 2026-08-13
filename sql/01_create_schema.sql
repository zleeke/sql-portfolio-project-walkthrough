-- Schema for the QUALIFY demo project.
-- Run this against db/support_tickets.duckdb before loading data.

DROP TABLE IF EXISTS ticket_notes;
DROP TABLE IF EXISTS tickets;

CREATE TABLE tickets (
    ticket_id     INTEGER PRIMARY KEY,
    customer_name VARCHAR NOT NULL,
    product       VARCHAR NOT NULL,
    opened_at     TIMESTAMP NOT NULL,
    status        VARCHAR NOT NULL,
    initial_rep   VARCHAR NOT NULL -- rep who took the first note on the ticket
);

CREATE TABLE ticket_notes (
    note_id    INTEGER PRIMARY KEY,
    ticket_id  INTEGER NOT NULL REFERENCES tickets (ticket_id),
    rep_name   VARCHAR NOT NULL, -- rep who logged this specific note (may differ from tickets.initial_rep)
    note_type  VARCHAR NOT NULL, -- 'general' | 'escalation' | 'follow_up' | 'resolution'
    note_text  VARCHAR NOT NULL,
    created_at TIMESTAMP NOT NULL
);
