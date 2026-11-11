-- Date Logic Errors
-- System records where status and dates contradict each other.
SELECT
    case_id        AS "Case ID",
    status         AS "Status",
    received_date  AS "Received",
    decision_date  AS "Decided",
    CASE
        WHEN status IN ('Approved', 'Denied') AND decision_date IS NULL
            THEN 'Decided case has no decision date'
        WHEN status = 'Pending' AND decision_date IS NOT NULL
            THEN 'Pending case has a decision date'
        WHEN decision_date < received_date
            THEN 'Decision date is before received date'
    END            AS "Issue",
    source_row     AS "System Row"
FROM system_cases
WHERE (status IN ('Approved', 'Denied') AND decision_date IS NULL)
   OR (status = 'Pending' AND decision_date IS NOT NULL)
   OR (decision_date < received_date)
ORDER BY case_id;
