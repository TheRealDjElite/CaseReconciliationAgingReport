-- Late Decisions
-- Decided cases where processing time went past the program's target.
SELECT
    s.case_id        AS "Case ID",
    s.program        AS "Program",
    s.status         AS "Status",
    s.worker_id      AS "Worker",
    s.received_date  AS "Received",
    s.decision_date  AS "Decided",
    CAST(julianday(s.decision_date) - julianday(s.received_date) AS INTEGER) AS "Days to Decide",
    sla.target_days  AS "Target Days",
    CAST(julianday(s.decision_date) - julianday(s.received_date) AS INTEGER)
        - sla.target_days AS "Days Over"
FROM system_cases s
JOIN sla_targets sla ON sla.program = s.program
WHERE s.status IN ('Approved', 'Denied')
  AND s.decision_date IS NOT NULL
  AND julianday(s.decision_date) - julianday(s.received_date) > sla.target_days
ORDER BY "Days Over" DESC;
