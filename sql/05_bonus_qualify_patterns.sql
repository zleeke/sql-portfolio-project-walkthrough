-- A few more common "return the latest/top N per group" patterns using
-- QUALIFY, since this shape of problem comes up constantly outside of the
-- "first within a window" scenario above.

-- 1. The single most recent note of any type, per ticket.
SELECT
    n.ticket_id,
    n.note_type,
    n.note_text,
    n.created_at
FROM ticket_notes n
QUALIFY ROW_NUMBER() OVER (
    PARTITION BY n.ticket_id
    ORDER BY n.created_at DESC
) = 1
ORDER BY n.created_at DESC
LIMIT 20;

-- 2. The 3 most recent notes per ticket (top-N per group), for tickets that
--    have at least 3 notes.
SELECT
    n.ticket_id,
    n.note_type,
    n.note_text,
    n.created_at,
    RANK() OVER (
        PARTITION BY n.ticket_id
        ORDER BY n.created_at DESC
    ) AS recency_rank
FROM ticket_notes n
QUALIFY recency_rank <= 3
ORDER BY n.ticket_id, recency_rank;

-- 3. Tickets where the most recent note is a resolution note logged in the
--    last 7 days (e.g. "recently closed out" report).
SELECT
    t.ticket_id,
    t.customer_name,
    n.note_type,
    n.created_at
FROM ticket_notes n
JOIN tickets t USING (ticket_id)
QUALIFY ROW_NUMBER() OVER (
    PARTITION BY n.ticket_id
    ORDER BY n.created_at DESC
) = 1
    AND n.note_type = 'resolution'
    AND n.created_at >= CURRENT_DATE - INTERVAL 7 DAY
ORDER BY n.created_at DESC;
