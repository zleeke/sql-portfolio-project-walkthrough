select *
from tickets
limit 10
;

select 
    ticket_id
    , count(*) as row_count
from ticket_notes
group by
    ticket_id
having 
    count(*) > 1
order by 
    row_count desc
;

Select 
    tickets.*
    , ticket_notes.created_at
from 
    tickets as tickets
    inner join 
        ticket_notes as ticket_notes
            on tickets.ticket_id = ticket_notes.ticket_id
where 
    tickets.ticket_id = '4693'
;
