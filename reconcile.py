"""
Case Reconciliation & Aging Report

Compares a system export (CSV) against a team's manual tracker (Excel),
runs SQL checks, and writes a formatted Excel report for review.

Steps:
  1. Load both files with pandas and map the tracker's column names
  2. Clean values (spaces, capitalization, dates) and log anything invalid
  3. Load clean data into a SQLite database
  4. Run every .sql file in sql/checks/ and collect the results
  5. Write one Excel sheet per check, plus a Summary sheet
"""

import sqlite3
from datetime import date, datetime
from pathlib import Path

import pandas as pd
from openpyxl import Workbook
from openpyxl.formatting.rule import FormulaRule
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

# ---------------- Settings ----------------
BASE_DIR = Path(__file__).parent
SYSTEM_FILE = BASE_DIR / "data" / "system_export.csv"
TRACKER_FILE = BASE_DIR / "data" / "team_tracker.xlsx"
SCHEMA_FILE = BASE_DIR / "sql" / "schema.sql"
CHECKS_DIR = BASE_DIR / "sql" / "checks"
OUTPUT_FILE = BASE_DIR / "output" / "reconciliation_report.xlsx"
DB_FILE = BASE_DIR / "output" / "reconciliation.db"

# "As of" date for aging. Fixed so the sample output matches the README.
# Set to date.today() for live use.
REPORT_DATE = date(2026, 10, 31)

# Sample processing targets in days. Edit to match your program rules.
SLA_TARGETS = {"SNAP": 30, "TANF": 45, "Medicaid": 45}

VALID_STATUSES = ["Approved", "Denied", "Pending"]
VALID_PROGRAMS = ["SNAP", "TANF", "Medicaid"]
REQUIRED_FIELDS = ["case_id", "client_name", "program", "status", "received_date"]

# Tracker headers -> standard field names
TRACKER_COLUMNS = {
    "Case ID": "case_id",
    "Client Name": "client_name",
    "Program": "program",
    "Status": "status",
    "Date Received": "received_date",
    "Date Decided": "decision_date",
    "Assigned Worker": "worker_id",
    "Notes": "notes",
}

FIELD_LABELS = {
    "case_id": "Case ID", "client_name": "Client Name", "program": "Program",
    "status": "Status", "received_date": "Received Date",
    "decision_date": "Decision Date", "worker_id": "Worker",
}


# ---------------- Step 1: Load ----------------
def load_system():
    df = pd.read_csv(SYSTEM_FILE, dtype=str, keep_default_na=False)
    df["source_row"] = df.index + 2  # +2 = header row + 1-based rows
    return df


def load_tracker():
    df = pd.read_excel(TRACKER_FILE, dtype=object)
    missing = [c for c in TRACKER_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"Tracker is missing columns: {missing}")
    df = df.rename(columns=TRACKER_COLUMNS)[list(TRACKER_COLUMNS.values())]
    df["source_row"] = df.index + 2
    return df


# ---------------- Step 2: Clean and validate ----------------
def clean_text(value):
    """Trim and collapse extra spaces. Blank values become None."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    text = " ".join(str(value).split())
    return text or None


def clean_date(value):
    """Return (YYYY-MM-DD or None, error message or None)."""
    if value is None or (isinstance(value, float) and pd.isna(value)) or value is pd.NaT:
        return None, None
    if isinstance(value, (datetime, date)):
        return value.strftime("%Y-%m-%d"), None
    text = clean_text(value)
    if text is None:
        return None, None
    for fmt in ("%Y-%m-%d", "%m/%d/%Y"):
        try:
            return datetime.strptime(text, fmt).strftime("%Y-%m-%d"), None
        except ValueError:
            pass
    return None, "Invalid or impossible date"


def match_allowed(value, allowed):
    """Fix capitalization if the value matches an allowed value."""
    if value is None:
        return None, None
    for option in allowed:
        if value.lower() == option.lower():
            return option, None
    return value, "Not an allowed value"


def clean_frame(df, source, issues):
    """Clean every record and append problems to the issues list."""
    records = []
    for _, row in df.iterrows():
        rec = {"source_row": int(row["source_row"])}
        raw = {}
        for col in df.columns:
            if col == "source_row":
                continue
            raw[col] = row[col]
            if col in ("received_date", "decision_date"):
                rec[col], err = clean_date(row[col])
            else:
                rec[col] = clean_text(row[col])
                err = None
            if err:
                issues.append(issue(source, rec, row, col, raw[col], err))

        if rec["case_id"]:
            rec["case_id"] = rec["case_id"].upper()

        for col, allowed in (("status", VALID_STATUSES), ("program", VALID_PROGRAMS)):
            rec[col], err = match_allowed(rec[col], allowed)
            if err:
                issues.append(issue(source, rec, row, col, raw[col], err))

        for col in REQUIRED_FIELDS:
            already_flagged = any(
                i["source"] == source and i["source_row"] == rec["source_row"]
                and i["field"] == FIELD_LABELS[col] for i in issues)
            if rec[col] is None and not already_flagged:
                issues.append(issue(source, rec, row, col, "", "Required field is blank"))
        records.append(rec)
    return pd.DataFrame(records)


def issue(source, rec, row, col, raw_value, message):
    return {
        "source": source,
        "source_row": int(row["source_row"]),
        "case_id": rec.get("case_id") or clean_text(row.get("case_id")),
        "field": FIELD_LABELS.get(col, col),
        "raw_value": "" if raw_value is None or (isinstance(raw_value, float) and pd.isna(raw_value)) else str(raw_value),
        "issue": message,
    }


# ---------------- Step 3: Load into SQLite ----------------
def build_database(system_df, tracker_df, issues):
    DB_FILE.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_FILE)
    conn.executescript(SCHEMA_FILE.read_text(encoding="utf-8"))

    system_df.to_sql("system_cases", conn, if_exists="append", index=False)
    tracker_df.to_sql("tracker_cases", conn, if_exists="append", index=False)
    pd.DataFrame(issues, columns=["source", "source_row", "case_id", "field",
                                  "raw_value", "issue"]
                 ).to_sql("load_issues", conn, if_exists="append", index=False)
    conn.executemany("INSERT INTO sla_targets VALUES (?, ?)", SLA_TARGETS.items())
    conn.execute("INSERT INTO report_settings VALUES (?)", (REPORT_DATE.isoformat(),))
    conn.commit()
    return conn


# ---------------- Step 4: Run SQL checks ----------------
def run_checks(conn):
    """Run each .sql file in order. Line 1 of each file is the sheet name,
    line 2 is the description shown on the Summary sheet."""
    results = []
    for path in sorted(CHECKS_DIR.glob("*.sql")):
        lines = path.read_text(encoding="utf-8").splitlines()
        name = lines[0].lstrip("- ").strip()
        description = lines[1].lstrip("- ").strip()
        df = pd.read_sql_query(path.read_text(encoding="utf-8"), conn)
        results.append((name, description, df))
    return results


# ---------------- Step 5: Write Excel report ----------------
HEADER_FILL = PatternFill("solid", fgColor="1F4E78")
HEADER_FONT = Font(bold=True, color="FFFFFF")
RED_FILL = PatternFill("solid", fgColor="F8CBAD")
YELLOW_FILL = PatternFill("solid", fgColor="FFE699")
GREEN_FILL = PatternFill("solid", fgColor="C6EFCE")

# Checks where rows are expected (reporting), not problems to fix
REPORTING_SHEETS = {"Open Case Aging", "Worker Workload"}


def style_header(ws, row=1):
    for cell in ws[row]:
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = Alignment(vertical="center", wrap_text=True)


def print_setup(ws):
    """Landscape, fit all columns on one page width when printed."""
    ws.page_setup.orientation = "landscape"
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0


def autosize(ws):
    for col in ws.columns:
        longest = max(len(str(c.value)) if c.value is not None else 0 for c in col)
        ws.column_dimensions[get_column_letter(col[0].column)].width = min(max(longest + 2, 10), 60)


def write_report(results, system_count, tracker_count):
    OUTPUT_FILE.parent.mkdir(exist_ok=True)
    wb = Workbook()
    summary = wb.active
    summary.title = "Summary"

    summary["A1"] = "Case Reconciliation & Aging Report"
    summary["A1"].font = Font(bold=True, size=14)
    summary["A2"] = f"Report date: {REPORT_DATE.isoformat()}"
    summary["A3"] = f"System records: {system_count}    Tracker records: {tracker_count}"
    summary.append([])
    summary.append(["Check", "What It Finds", "Rows", "Type"])
    style_header(summary, 5)

    for name, description, df in results:
        ws = wb.create_sheet(name[:31])
        ws.append(list(df.columns))
        for record in df.itertuples(index=False):
            ws.append([None if pd.isna(v) else v for v in record])
        style_header(ws)
        for row in ws.iter_rows(min_row=2):
            for cell in row:
                if isinstance(cell.value, (int, float)):
                    cell.alignment = Alignment(horizontal="center")
        ws.freeze_panes = "A2"
        if ws.max_row > 1:
            ws.auto_filter.ref = ws.dimensions
        autosize(ws)
        print_setup(ws)

        # Row count is an Excel formula, so it updates if someone edits a sheet
        sheet_ref = f"'{ws.title}'"
        kind = "Report" if name in REPORTING_SHEETS else "Exception"
        summary.append([name, description, f"=MAX(COUNTA({sheet_ref}!A:A)-1,0)", kind])
        summary.cell(row=summary.max_row, column=3).alignment = Alignment(horizontal="center")
        link_cell = summary.cell(row=summary.max_row, column=1)
        link_cell.hyperlink = f"#{sheet_ref}!A1"
        link_cell.font = Font(color="0563C1", underline="single")

    # Color the Rows column: green when an exception check is clean, red when not
    first, last = 6, summary.max_row
    rng = f"C{first}:C{last}"
    summary.conditional_formatting.add(
        rng, FormulaRule(formula=[f'AND($D{first}="Exception",C{first}>0)'], fill=RED_FILL))
    summary.conditional_formatting.add(
        rng, FormulaRule(formula=[f'AND($D{first}="Exception",C{first}=0)'], fill=GREEN_FILL))

    # Highlight timeliness on the aging sheet
    if "Open Case Aging" in wb.sheetnames:
        ws = wb["Open Case Aging"]
        headers = [c.value for c in ws[1]]
        col = get_column_letter(headers.index("Timeliness") + 1)
        full = f"A2:{get_column_letter(ws.max_column)}{max(ws.max_row, 2)}"
        ws.conditional_formatting.add(
            full, FormulaRule(formula=[f'${col}2="Overdue"'], fill=RED_FILL))
        ws.conditional_formatting.add(
            full, FormulaRule(formula=[f'${col}2="Due Soon"'], fill=YELLOW_FILL))

    autosize(summary)
    summary.column_dimensions["A"].width = 24
    summary.column_dimensions["B"].width = 70
    summary.column_dimensions["C"].width = 8
    summary.column_dimensions["D"].width = 11
    print_setup(summary)
    wb.save(OUTPUT_FILE)


# ---------------- Run ----------------
def main():
    issues = []
    system_raw = load_system()
    tracker_raw = load_tracker()
    system_df = clean_frame(system_raw, "System", issues)
    tracker_df = clean_frame(tracker_raw, "Tracker", issues)

    conn = build_database(system_df, tracker_df, issues)
    results = run_checks(conn)
    conn.close()

    write_report(results, len(system_df), len(tracker_df))

    print(f"Report date: {REPORT_DATE}")
    print(f"System records: {len(system_df)} | Tracker records: {len(tracker_df)}\n")
    for name, _, df in results:
        print(f"  {name:<22} {len(df):>3} rows")
    print(f"\nSaved: {OUTPUT_FILE.relative_to(BASE_DIR)}")


if __name__ == "__main__":
    main()
