-- Tables for the reconciliation run. Rebuilt from scratch on every run.
-- Dates are stored as text in YYYY-MM-DD format.

DROP TABLE IF EXISTS system_cases;
DROP TABLE IF EXISTS tracker_cases;
DROP TABLE IF EXISTS sla_targets;
DROP TABLE IF EXISTS report_settings;
DROP TABLE IF EXISTS load_issues;

-- System of record export
CREATE TABLE system_cases (
    case_id        TEXT,
    client_name    TEXT,
    program        TEXT,
    status         TEXT,
    received_date  TEXT,
    decision_date  TEXT,
    worker_id      TEXT,
    source_row     INTEGER   -- row number in the CSV, for tracing back
);

-- Team's manual Excel tracker
CREATE TABLE tracker_cases (
    case_id        TEXT,
    client_name    TEXT,
    program        TEXT,
    status         TEXT,
    received_date  TEXT,
    decision_date  TEXT,
    worker_id      TEXT,
    notes          TEXT,
    source_row     INTEGER   -- row number in the Excel sheet, for tracing back
);

-- Processing time targets by program (days from received to decision)
CREATE TABLE sla_targets (
    program     TEXT PRIMARY KEY,
    target_days INTEGER
);

-- One row: the "as of" date for aging calculations
CREATE TABLE report_settings (
    report_date TEXT
);

-- Problems found while loading the files (bad dates, blanks, invalid values)
CREATE TABLE load_issues (
    source      TEXT,
    source_row  INTEGER,
    case_id     TEXT,
    field       TEXT,
    raw_value   TEXT,
    issue       TEXT
);
