-- Duplicate Case IDs
-- Case IDs that appear more than once in either source.
SELECT
    'System'                    AS "Source",
    case_id                     AS "Case ID",
    COUNT(*)                    AS "Times Listed",
    GROUP_CONCAT(source_row, ', ') AS "Rows"
FROM system_cases
GROUP BY case_id
HAVING COUNT(*) > 1

UNION ALL

SELECT
    'Tracker',
    case_id,
    COUNT(*),
    GROUP_CONCAT(source_row, ', ')
FROM tracker_cases
GROUP BY case_id
HAVING COUNT(*) > 1

ORDER BY 1, 2;
