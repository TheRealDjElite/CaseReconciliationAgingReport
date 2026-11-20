# 🔀 Source-to-Target Data Mapping

How each field in the system export and the team tracker maps to the database tables, what cleaning happens on load, and which checks use each field. Every rule below comes from `reconcile.py` and the queries in `sql/checks/`.

## 📥 Sources

| Source | File | Format | Role | Target Table |
|---|---|---|---|---|
| System export | `data/system_export.csv` | CSV, all values read as text | System of record | `system_cases` |
| Team tracker | `data/team_tracker.xlsx` | Excel, first sheet | Team's working copy | `tracker_cases` |

The system export is the system of record. Date logic, aging, late decision, and workload checks run on system data only. The tracker gets compared against the system, not the other way around.

## 🔑 Match Key

Records match on **Case ID** after cleaning: spaces trimmed and uppercased. Matching is exact after cleaning, so a tracker ID keyed as `1O24` (letter O) does not match system ID `1024`. The unmatched record lands on Missing from System for a person to correct.

## 🗺️ Field Mapping

| Target Field | System Column | Tracker Column | Cleaning on Load | Validation | Compared Across Sources |
|---|---|---|---|---|---|
| `case_id` | `case_id` | Case ID | Trim, collapse spaces, uppercase | Required | Match key |
| `client_name` | `client_name` | Client Name | Trim, collapse spaces | Required | Yes, ignoring capitalization |
| `program` | `program` | Program | Trim, fix capitalization to the allowed value | Required. SNAP, TANF, or Medicaid | Yes |
| `status` | `status` | Status | Trim, fix capitalization to the allowed value | Required. Approved, Denied, or Pending | Yes |
| `received_date` | `received_date` | Date Received | Convert to YYYY-MM-DD | Required. Real date in YYYY-MM-DD or MM/DD/YYYY, or an Excel date cell | No (see GAP-01) |
| `decision_date` | `decision_date` | Date Decided | Convert to YYYY-MM-DD | Optional. Same date rules | Yes |
| `worker_id` | `worker_id` | Assigned Worker | Trim, collapse spaces | Not required | No (see GAP-02) |
| `notes` | Not in source | Notes | Trim, collapse spaces | Not required | Tracker only |
| `source_row` | Generated | Generated | Spreadsheet row number (row 1 is the header) | None | Used to trace issues back to the file |

## 🔄 Transformation Rules

| Rule | Applies To | Example |
|---|---|---|
| Trim and collapse spaces | All text fields | `"  ana  LOPEZ "` becomes `ana LOPEZ` |
| Blank becomes NULL | All fields | Empty cell or spaces only becomes NULL |
| Uppercase | Case ID | `1o24` becomes `1O24` |
| Match capitalization to allowed list | Program, Status | `denied` becomes `Denied` |
| Keep invalid value and log | Program, Status | `Aproved` stays `Aproved` and gets logged |
| Standardize date format | Received, Decision dates | `10/01/2026` becomes `2026-10-01` |
| Invalid date becomes NULL and gets logged | Received, Decision dates | `2026-02-30` becomes NULL |
| Rename tracker headers | All tracker columns | Date Received becomes `received_date` (set in `TRACKER_COLUMNS`) |

## 📚 Reference Data

| Table | Source | Contents |
|---|---|---|
| `sla_targets` | `SLA_TARGETS` in `reconcile.py` | Processing target in days by program: SNAP 30, TANF 45, Medicaid 45 |
| `report_settings` | `REPORT_DATE` in `reconcile.py` | "As of" date for aging. Sample uses 2026-10-31 |
| `load_issues` | Built during load | Source, row, Case ID, field, value found, and issue for every failed validation |

## 🔗 Field Usage by Check

| Check | Fields Used | Data Used |
|---|---|---|
| 01 Load Issues | All validated fields | Both sources |
| 02 Missing from Tracker | `case_id` | System records with no tracker match |
| 03 Missing from System | `case_id`, `notes` | Tracker records with no system match |
| 04 Duplicate Case IDs | `case_id`, `source_row` | Both sources, checked separately |
| 05 Field Mismatches | `client_name`, `program`, `status`, `decision_date` | Matched records |
| 06 Date Logic Errors | `status`, `received_date`, `decision_date` | System only |
| 07 Open Case Aging | `status`, `program`, `received_date` | System only, Pending cases |
| 08 Late Decisions | `status`, `program`, `received_date`, `decision_date` | System only, decided cases |
| 09 Worker Workload | `worker_id`, `status`, `program`, dates | System only |

## ⚠️ Mapping Gaps and Notes

| ID | Finding | Impact |
|---|---|---|
| GAP-01 | Received date gets loaded from both sources but never compared. | A tracker received date keyed wrong goes unflagged. Aging uses the system date, so the report stays correct, but the tracker stays wrong. |
| GAP-02 | Worker gets loaded from both sources but never compared. | A case reassigned in one source and not the other goes unflagged. Workload uses the system worker only. |
| NOTE-01 | A bad tracker value shows up on two sheets. | A blank or invalid tracker value for status or decision date appears on Load Issues and again on Field Mismatches. In the sample, cases 1019, 1025, and 1028 each appear twice. Both rows point to the same fix. |
| NOTE-02 | Date logic checks run on system data only. | A tracker row marked Approved with no decision date, such as case 1009, gets caught as a status mismatch, not as a date logic error. |
