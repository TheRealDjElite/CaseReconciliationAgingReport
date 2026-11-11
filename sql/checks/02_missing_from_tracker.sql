-- Missing from Tracker
-- Cases in the system export with no matching Case ID in the team tracker.
SELECT
    s.case_id        AS "Case ID",
    s.client_name    AS "Client Name",
    s.program        AS "Program",
    s.status         AS "System Status",
    s.received_date  AS "Received",
    s.worker_id      AS "Worker",
    s.source_row     AS "System Row"
FROM system_cases s
LEFT JOIN tracker_cases t ON t.case_id = s.case_id
WHERE t.case_id IS NULL
ORDER BY s.case_id;
