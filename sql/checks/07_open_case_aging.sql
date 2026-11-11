-- Open Case Aging
-- Every pending case with days open, aging bucket, days left, and a timeliness flag.
-- Days open is counted from the received date to the report date.
WITH open_cases AS (
    SELECT
        s.case_id,
        s.client_name,
        s.program,
        s.worker_id,
        s.received_date,
        CAST(julianday(r.report_date) - julianday(s.received_date) AS INTEGER) AS days_open,
        sla.target_days
    FROM system_cases s
    CROSS JOIN report_settings r
    LEFT JOIN sla_targets sla ON sla.program = s.program
    WHERE s.status = 'Pending'
)
SELECT
    case_id        AS "Case ID",
    client_name    AS "Client Name",
    program        AS "Program",
    worker_id      AS "Worker",
    received_date  AS "Received",
    days_open      AS "Days Open",
    CASE
        WHEN days_open <= 30 THEN '0-30'
        WHEN days_open <= 45 THEN '31-45'
        WHEN days_open <= 60 THEN '46-60'
        ELSE '61+'
    END            AS "Aging Bucket",
    target_days    AS "Target Days",
    target_days - days_open AS "Days Left",
    CASE
        WHEN days_open > target_days       THEN 'Overdue'
        WHEN target_days - days_open <= 7  THEN 'Due Soon'
        ELSE 'On Track'
    END            AS "Timeliness"
FROM open_cases
ORDER BY days_open DESC;
