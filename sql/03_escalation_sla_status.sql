-- Business case: the support desk has a 48-hour SLO for addressing an
-- escalation once it's raised (marked by a ticket_notes row with
-- note_type = 'escalation_resolved'). Leadership wants every escalation
-- classified into one of three buckets:
--   1. At risk        - not yet resolved, still inside the 48-hour SLO,
--                        but close enough to breaching (>= 32h elapsed)
--                        that it needs attention now.
--   2. Resolved late   - resolved, but the resolution landed outside the
--                        48-hour SLO.
--   3. Breached        - not resolved, and the 48-hour SLO has already
--                        passed.
-- ('Within SLO' escalations - resolved on time, or too fresh to be at
-- risk yet - are healthy and excluded from this report.)
--
-- A ticket can be escalated more than once, so each escalation note is
-- paired with the *next* escalation_resolved note that follows it, using
-- the same QUALIFY + ROW_NUMBER() pattern as before - just matching an
-- event to its resolution this time, instead of keeping the first row
-- per ticket.

WITH escalation_resolution_pairs AS (
    SELECT
        e.ticket_id
        , e.note_id AS escalation_note_id
        , e.rep_name AS escalated_by
        , e.created_at AS escalation_at
        , r.rep_name AS resolved_by
        , r.created_at AS resolved_at
    FROM ticket_notes AS e
        LEFT JOIN ticket_notes AS r
            ON r.ticket_id = e.ticket_id
            AND r.note_type = 'escalation_resolved'
            AND r.created_at > e.created_at
    WHERE e.note_type = 'escalation'
    QUALIFY
        ROW_NUMBER() OVER (
            PARTITION BY e.ticket_id, e.note_id
            ORDER BY r.created_at ASC
        ) = 1
)
, classified AS (
    SELECT
        pairs.ticket_id
        , tickets.customer_name
        , tickets.product
        , tickets.status
        , pairs.escalated_by
        , pairs.escalation_at
        , pairs.resolved_by
        , pairs.resolved_at
        , DATE_DIFF('hour', pairs.escalation_at, COALESCE(pairs.resolved_at, CURRENT_TIMESTAMP)) AS hours_since_escalation
        , CASE
            WHEN pairs.resolved_at IS NOT NULL
                 AND DATE_DIFF('hour', pairs.escalation_at, pairs.resolved_at) > 48
                THEN 'Resolved late (outside 48h SLO)'
            -- An escalation with no escalation_resolved note on a ticket that's
            -- already closed/resolved isn't actionable - treat it as healthy
            -- rather than flagging a ticket nobody is going to look at again.
            WHEN pairs.resolved_at IS NULL
                 AND tickets.status NOT IN ('open', 'pending')
                THEN 'Within SLO'
            WHEN pairs.resolved_at IS NULL
                 AND DATE_DIFF('hour', pairs.escalation_at, CURRENT_TIMESTAMP) >= 48
                THEN 'Breached - still unresolved'
            WHEN pairs.resolved_at IS NULL
                 AND DATE_DIFF('hour', pairs.escalation_at, CURRENT_TIMESTAMP) >= 32
                THEN 'At risk - unresolved, approaching SLO'
            ELSE 'Within SLO'
          END AS slo_status
    FROM escalation_resolution_pairs AS pairs
        INNER JOIN tickets AS tickets
            ON tickets.ticket_id = pairs.ticket_id
)
SELECT *
FROM classified
WHERE slo_status <> 'Within SLO'
ORDER BY
    CASE slo_status
        WHEN 'Breached - still unresolved' THEN 1
        WHEN 'At risk - unresolved, approaching SLO' THEN 2
        WHEN 'Resolved late (outside 48h SLO)' THEN 3
    END
    , hours_since_escalation DESC
;


