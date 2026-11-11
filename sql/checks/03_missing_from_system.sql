-- Missing from System
-- Tracker entries with no matching Case ID in the system export.
-- Often a keying error in the Case ID, or a case never entered in the system.
SELECT
    t.case_id        AS "Case ID",
    t.client_name    AS "Client Name",
    t.program        AS "Program",
    t.status         AS "Tracker Status",
    t.received_date  AS "Received",
    t.worker_id      AS "Worker",
    t.notes          AS "Tracker Notes",
    t.source_row     AS "Tracker Row"
FROM tracker_cases t
LEFT JOIN system_cases s ON s.case_id = t.case_id
WHERE s.case_id IS NULL
ORDER BY t.case_id;
