-- Worker Workload
-- Per worker: open cases, overdue open cases, late decisions, and oldest open case.
WITH settings AS (SELECT report_date FROM report_settings),
case_calc AS (
    SELECT
        s.worker_id,
        s.status,
        CASE WHEN s.status = 'Pending'
             THEN julianday((SELECT report_date FROM settings)) - julianday(s.received_date)
        END AS days_open,
        CASE WHEN s.status IN ('Approved', 'Denied') AND s.decision_date IS NOT NULL
             THEN julianday(s.decision_date) - julianday(s.received_date)
        END AS days_to_decide,
        sla.target_days
    FROM system_cases s
    LEFT JOIN sla_targets sla ON sla.program = s.program
)
SELECT
    worker_id AS "Worker",
    SUM(status = 'Pending')                        AS "Open Cases",
    COALESCE(SUM(days_open > target_days), 0)      AS "Overdue Open",
    COALESCE(SUM(days_to_decide > target_days), 0) AS "Late Decisions",
    CAST(MAX(days_open) AS INTEGER)                AS "Oldest Open (Days)"
FROM case_calc
GROUP BY worker_id
ORDER BY "Overdue Open" DESC, "Open Cases" DESC;
