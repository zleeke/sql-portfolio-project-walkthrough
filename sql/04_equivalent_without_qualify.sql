-- The exact same result as 03_qualify_first_escalation_within_window.sql,
-- written the way you'd have to write it on a database WITHOUT a QUALIFY
-- clause (e.g. SQLite, or Postgres/MySQL): the window function has to be
-- computed in a CTE, then filtered in an outer WHERE clause.

WITH ranked_escalations AS (
    SELECT
        t.ticket_id,
        t.customer_name,
        t.product,
        n.note_type,
        n.note_text,
        n.created_at                                AS first_escalation_at,
        ROW_NUMBER() OVER (
            PARTITION BY n.ticket_id
            ORDER BY n.created_at ASC
        )                                            AS escalation_rank
    FROM ticket_notes n
    JOIN tickets t USING (ticket_id)
    WHERE n.note_type = 'escalation'
)
SELECT
    ticket_id,
    customer_name,
    product,
    note_type,
    note_text,
    first_escalation_at,
    DATE_DIFF('day', first_escalation_at, CURRENT_DATE) AS days_since_first_escalation
FROM ranked_escalations
WHERE escalation_rank = 1
    AND first_escalation_at >= CURRENT_DATE - INTERVAL 45 DAY
ORDER BY first_escalation_at DESC;

-- Same rows as the QUALIFY version, just more verbose. This is the pattern
-- to reach for on engines that don't support QUALIFY.
