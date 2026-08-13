/*
The business partner needs to have data to answer three questions:
    1) How many escalations notes are unresolved, still within SLO, but at risk of exceeding SLO and remaining unresolved?
    2) How many escalations notes were resolved outside of SLO?
    3) How many escalation notes our out of SLO, but still unresolved?

Service Level Objective (SLO) is to resolve escalations within 48 hours of being created
*/

-- Query 1: How many escalations notes are unresolved, still within SLO, but at risk of exceeding SLO and remaining unresolved?

-- First, check for a couple things:
    -- 1) Tickets that have multple escalations associated with them
        -- 545
        -- 926
        -- 2037
    -- 2) Tickets that have more escalation_resolved occurrences than escalations
        -- 6941
        -- 9089
        -- 2422
select distinct
    tickets.ticket_id
    , sum(case when ticket_notes.note_type = 'escalation' then 1 else 0 end) over (partition by tickets.ticket_id) as escalation_count
    , sum(case when ticket_notes.note_type = 'escalation_resolved' then 1 else 0 end) over (partition by tickets.ticket_id) as escalation_resolved_count
from tickets as tickets
    inner join ticket_notes as ticket_notes
        on tickets.ticket_id = ticket_notes.ticket_id
qualify
    -- escalation_count > 1 -- check for tickets that have more than one escalation note associated with them
    escalation_resolved_count > escalation_count -- check for tickets that have more escalation_resolved notes that escalation_notes
;

-- Spot check individual tickets to understand what is happening in the data
select
    tickets.ticket_id
    , tickets.initial_rep_employee_id
    , tickets.opened_at
    , ticket_notes.note_id
    , ticket_notes.note_type
    , ticket_notes.employee_id
    , ticket_notes.created_at
from tickets as tickets
    inner join ticket_notes as ticket_notes
        on tickets.ticket_id = ticket_notes.ticket_id
        and ticket_notes.note_type in ('escalation', 'escalation_resolved')
where 
    tickets.ticket_id = '6941'
;

WITH
escalations AS (
    SELECT 
        tickets.ticket_id
        , escalations.note_id
        , tickets.opened_at
        , tickets.customer_id
        , tickets.product
        , tickets.initial_rep_employee_id
        , escalations.note_type
        , escalations.employee_id as escalation_rep
        , escalations.created_at as escalation_tstmp
        , COALESCE(
            lag(escalations.created_at) over (partition by tickets.ticket_id order by escalations.created_at desc),
            TIMESTAMP '9999-12-31 23:59:59.999999'
        ) as next_escalation_tstmp
    FROM tickets AS tickets
        INNER JOIN ticket_notes AS escalations
            ON tickets.ticket_id = escalations.ticket_id
            AND escalations.note_type = 'escalation'
    -- WHERE 
    --     tickets.ticket_id = '6941' -- the one ticket that has multiple escalations associated with it
)
-- select * from escalations;
, service_level as (
    SELECT
        escalations.ticket_id
        , escalations.note_id
        , escalations.opened_at
        , escalations.customer_id
        , escalations.product
        , escalations.initial_rep_employee_id
        , escalations.escalation_rep
        , escalations.escalation_tstmp
        , case when ticket_notes.created_at is not null then 'Y' else 'N' end as escalation_resolved_ind
        , ticket_notes.employee_id as escalation_resolved_rep
        , ticket_notes.created_at as escalation_resolved_tstmp
        , case when ticket_notes.created_at is null then EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - escalations.escalation_tstmp)) / 3600.0 else EXTRACT(EPOCH FROM (ticket_notes.created_at - escalations.escalation_tstmp)) / 3600.0 end AS service_level_hours
        , case when service_level_hours <= 48 then 'Y' else 'N'
        END as within_slo_ind
        , case when escalation_resolved_ind = 'N' then case when service_level_hours > 38 then 'Y' else 'N' end else 'NA' end as high_risk_ind
    FROM
        escalations as escalations
        left outer join ticket_notes
            on escalations.ticket_id = ticket_notes.ticket_id
            and escalations.escalation_tstmp <= ticket_notes.created_at
            and escalations.next_escalation_tstmp > ticket_notes.created_at
            and ticket_notes.note_type = 'escalation_resolved'
    QUALIFY
        row_number() over (partition by escalations.ticket_id, escalations.note_id order by ticket_notes.created_at asc) = 1 -- if multple instances of 'escalation_resolved' occur after the escalation, only return the inital one
)
-- select * from service_level;
, summary as (
    -- How many escalations notes are unresolved, still within SLO, but at risk of exceeding SLO and remaining unresolved?
    SELECT
        'high_risk_escalations_within_slo_count' as metric
        , sum(case when escalation_resolved_ind = 'N' and within_slo_ind = 'Y' and high_risk_ind = 'Y' then 1 else 0 end) as metric_value 
    FROM service_level
    
    UNION

    SELECT
        'resolved_escalations_outside_slo_count' as metric
        , sum(case when escalation_resolved_ind = 'Y' and within_slo_ind = 'N' then 1 else 0 end) as metric_value
    FROM service_level

    UNION

    SELECT
        'unresolved_escalations_outside_slo_count' as metric
        , sum(case when escalation_resolved_ind = 'N' and within_slo_ind = 'N' then 1 else 0 end) as metric_value
    FROM service_level

)
select * from summary;


-- Query 2: How many escalations notes were resolved outside of SLO?



-- Query 3: How many escalation notes our out of SLO, but still unresolved?