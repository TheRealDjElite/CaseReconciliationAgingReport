-- Load Issues
-- Values that failed validation while the files were loaded.
SELECT
    source      AS "Source",
    source_row  AS "Source Row",
    case_id     AS "Case ID",
    field       AS "Field",
    raw_value   AS "Value Found",
    issue       AS "Issue"
FROM load_issues
ORDER BY source, source_row;
