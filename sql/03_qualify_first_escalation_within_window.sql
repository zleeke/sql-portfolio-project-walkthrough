-- Business case: tickets that are still unresolved (open/pending) whose
-- FIRST escalation note landed within the last 7 days -> high-risk /
-- at-risk-of-churn tickets that need urgent attention. Prioritized by
-- repeat-escalation count, then overall ticket age, since a ticket that's
-- been escalated more than once or has been open a long time is a bigger
-- risk than a fresh single escalation.

SELECT
    tickets.ticket_id
    , tickets.customer_name
    , tickets.product
    , tickets.status
    , tickets.initial_rep
    , ticket_notes.rep_name AS escalation_handled_by
    , ticket_notes.note_text AS first_escalation_note
    , ticket_notes.created_at AS first_escalation_at
    , DATE_DIFF('day', ticket_notes.created_at, CURRENT_DATE) AS days_since_escalation
    , DATE_DIFF('day', tickets.opened_at, CURRENT_DATE) AS ticket_age_days
    , COUNT(ticket_notes.note_id) OVER (PARTITION BY tickets.ticket_id) AS escalation_count
FROM tickets as tickets 
    INNER JOIN ticket_notes as ticket_notes 
        ON tickets.ticket_id = ticket_notes.ticket_id 
        AND ticket_notes.note_type = 'escalation'
WHERE 
    tickets.status IN ('pending', 'open')
QUALIFY
    ROW_NUMBER() OVER (PARTITION BY tickets.ticket_id ORDER BY ticket_notes.created_at asc) = 1
    AND ticket_notes.created_at >= CURRENT_DATE - INTERVAL 7 DAY
ORDER BY 
    escalation_count DESC
    , ticket_age_days DESC
    , first_escalation_at ASC
;


