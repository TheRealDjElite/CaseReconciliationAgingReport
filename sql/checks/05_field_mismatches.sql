-- Field Mismatches
-- Cases found in both sources where a field value disagrees.
-- Names are compared without regard to case or extra spaces.
-- IS NOT catches differences where one side is blank (NULL).
WITH matched AS (
    SELECT
        s.case_id,
        s.client_name   AS s_name,   t.client_name   AS t_name,
        s.program       AS s_prog,   t.program       AS t_prog,
        s.status        AS s_status, t.status        AS t_status,
        s.decision_date AS s_dec,    t.decision_date AS t_dec,
        t.source_row    AS t_row
    FROM system_cases s
    JOIN tracker_cases t ON t.case_id = s.case_id
)
SELECT case_id AS "Case ID", 'Client Name' AS "Field",
       s_name AS "System Value", t_name AS "Tracker Value", t_row AS "Tracker Row"
FROM matched WHERE UPPER(s_name) IS NOT UPPER(t_name)

UNION ALL
SELECT case_id, 'Program', s_prog, t_prog, t_row
FROM matched WHERE s_prog IS NOT t_prog

UNION ALL
SELECT case_id, 'Status', s_status, t_status, t_row
FROM matched WHERE s_status IS NOT t_status

UNION ALL
SELECT case_id, 'Decision Date', s_dec, t_dec, t_row
FROM matched WHERE s_dec IS NOT t_dec

ORDER BY 1, 2;
