-- The main demo: find tickets whose INITIAL escalation note occurred within
-- the last 45 days. A ticket with a later escalation note does NOT count if
-- its *first* escalation note falls outside the window.
--
-- QUALIFY lets us filter on the ROW_NUMBER() window function result without
-- wrapping the query in an extra CTE/subquery.

SELECT
    t.ticket_id,
    t.customer_name,
    t.product,
    n.note_type,
    n.note_text,
    n.created_at                                   AS first_escalation_at,
    DATE_DIFF('day', n.created_at, CURRENT_DATE)    AS days_since_first_escalation,
    ROW_NUMBER() OVER (
        PARTITION BY n.ticket_id
        ORDER BY n.created_at ASC
    )                                               AS escalation_rank
FROM ticket_notes n
JOIN tickets t USING (ticket_id)
WHERE n.note_type = 'escalation'
QUALIFY escalation_rank = 1
    AND n.created_at >= CURRENT_DATE - INTERVAL 45 DAY
ORDER BY n.created_at DESC;

-- Expected, given the curated demo tickets described in README.md:
--   ticket_id 2 (first escalation 40 days ago)  -> included
--   ticket_id 4 (first escalation 10 days ago)  -> included
--   ticket_id 1 (first escalation 47 days ago)  -> excluded, even though it
--                                                   has a second escalation
--                                                   note only 35 days ago
--   ticket_id 3 (first escalation 50 days ago)  -> excluded
--   ticket_id 5 (no escalation notes)           -> excluded

SELECT
    tickets.ticket_id
    , tickets.customer_name
    , tickets.product
    , ticket_notes.created_at
    , COUNT(tickets.ticket_id) OVER (PARTITION BY tickets.ticket_id) AS ticket_count
FROM 
    tickets as tickets 
    INNER JOIN
        ticket_notes as ticket_notes 
            ON tickets.ticket_id = ticket_notes.ticket_id 
            and ticket_notes.note_type = 'escalation'
-- QUALIFY
--     ticket_count > 1
;

SELECT
    tickets.ticket_id
    , ticket_notes.note_id
    , tickets.customer_name
    , tickets.product
    , ticket_notes.created_at
FROM 
    tickets as tickets 
    INNER JOIN
        ticket_notes as ticket_notes 
            ON tickets.ticket_id = ticket_notes.ticket_id 
            and ticket_notes.note_type = 'escalation'
WHERE 
    tickets.status = 'pending'
QUALIFY
    ROW_NUMBER() OVER (PARTITION BY tickets.ticket_id ORDER BY ticket_notes.created_at asc) = 1
    AND ticket_notes.created_at::DATE >= CURRENT_DATE - 45
;


