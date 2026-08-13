-- Schema for the QUALIFY demo project.
-- Run this against db/support_tickets.duckdb before loading data.

DROP TABLE IF EXISTS ticket_notes;
DROP TABLE IF EXISTS tickets;
DROP TABLE IF EXISTS employee;
DROP TABLE IF EXISTS customer;

CREATE TABLE employee (
    employee_id           INTEGER PRIMARY KEY,
    employee_name         VARCHAR NOT NULL,
    role                  VARCHAR NOT NULL, -- 'rep' | 'first_line_leader' | 'second_line_leader'
    first_line_leader_id  INTEGER, -- NULL for first/second-line leaders; self-ref, no FK (bulk load ordering)
    second_line_leader_id INTEGER  -- NULL for second-line leaders; self-ref, no FK (bulk load ordering)
);

CREATE TABLE customer (
    customer_id    INTEGER PRIMARY KEY,
    customer_name  VARCHAR NOT NULL,
    city           VARCHAR NOT NULL,
    state          VARCHAR NOT NULL,
    email          VARCHAR NOT NULL,
    customer_since DATE NOT NULL
);

CREATE TABLE tickets (
    ticket_id               INTEGER PRIMARY KEY,
    customer_id             INTEGER NOT NULL REFERENCES customer (customer_id),
    product                 VARCHAR NOT NULL,
    opened_at               TIMESTAMP NOT NULL,
    status                  VARCHAR NOT NULL, -- 'new' | 'pending' | 'closed'
    initial_rep_employee_id INTEGER NOT NULL REFERENCES employee (employee_id) -- rep who took the first note on the ticket
);

CREATE TABLE ticket_notes (
    note_id     INTEGER PRIMARY KEY,
    ticket_id   INTEGER NOT NULL REFERENCES tickets (ticket_id),
    employee_id INTEGER NOT NULL REFERENCES employee (employee_id), -- rep who logged this specific note (may differ from tickets.initial_rep_employee_id)
    note_type   VARCHAR NOT NULL, -- 'general' | 'escalation' | 'escalation_resolved' | 'follow_up'
    note_text   VARCHAR NOT NULL,
    created_at  TIMESTAMP NOT NULL
);
