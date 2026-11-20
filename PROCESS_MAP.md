# 🧭 Process Map: Current State and Future State

How tracker reconciliation runs as a manual process, and how the process runs with this tool. The current state describes the manual comparison this tool replaces. The future state follows the steps in `reconcile.py`.

## 📍 Current State (Manual)

```mermaid
flowchart TD
    subgraph A["Analyst"]
        A1["Export case list from the system"] --> A2["Open the export and the tracker side by side"]
        A2 --> A3["Look up each Case ID in the other file"]
        A3 --> A4["Compare name, program, status, and dates by eye"]
        A4 --> A5["Count days open for each pending case"]
        A5 --> A6["Write down each mismatch found"]
        A6 --> A7["Correct the tracker or report the system issue"]
    end
    subgraph S["Supervisor"]
        S1["Receive the list of issues"] --> S2["Build workload and overdue counts by hand"]
    end
    A7 --> S1
```

### Pain Points

| ID | Pain Point | Effect |
|---|---|---|
| PP-01 | Every Case ID gets looked up one at a time | Review time grows with every case added |
| PP-02 | Fields get compared by eye | Near matches such as `1O24` and `1024` or `Akina` and `Akana` slip through |
| PP-03 | No row numbers on findings | Each correction starts with another search through the file |
| PP-04 | Days open counted by hand | Aging and overdue status depend on who does the math and when |
| PP-05 | No record of what got checked | No proof the review happened, and no way to repeat the same review |

## 🎯 Future State (With This Tool)

```mermaid
flowchart TD
    subgraph A["Analyst"]
        A1["Save the system export and tracker to the data folder"] --> A2["Run reconcile.py"]
        A8["Open the Summary sheet"] --> A9{"Any exception counts above zero?"}
        A9 -- Yes --> A10["Fix the tracker or route the system issue, using the row number"]
        A10 --> A2
    end
    subgraph T["Tool"]
        T1["Load and clean both files"] --> T2["Log blank, invalid, and impossible values"]
        T2 --> T3["Load clean data into SQLite"]
        T3 --> T4["Run 9 SQL checks"]
        T4 --> T5["Write the Excel report, one sheet per check"]
    end
    subgraph S["Supervisor"]
        S1["Review Open Case Aging and Worker Workload"] --> S2["Report with confirmed numbers"]
    end
    A2 --> T1
    T5 --> A8
    A9 -- No --> S1
```

## 🔄 Current vs. Future State

| Step | Current State | Future State |
|---|---|---|
| Matching records | Each Case ID looked up by hand | Every record matched at once on a cleaned Case ID |
| Comparing fields | By eye, case by case | Name, program, status, and decision date compared on every matched case |
| Bad values | Found only if someone notices | Blank, invalid, and impossible values logged on load with source and row number |
| Duplicates | Found only if someone notices | Duplicate Case IDs listed for each source |
| Aging | Days counted by hand | Days open, aging bucket, and Overdue, Due Soon, or On Track set for every pending case |
| Late decisions | Not tracked | Decided cases past target listed with days over |
| Workload | Built by hand | Open, overdue, and late cases summarized by worker |
| Fixing issues | Search the file again for each finding | Row number on every finding |
| Proof of review | None | Saved Excel report with a Summary sheet |
| Repeat review | Start over | Run the script again |

## 📝 Notes

- The analyst still decides every correction. The tool finds and lists issues, and a person fixes them in the tracker or routes them to the system owner.
- The loop between the analyst and the tool repeats until every exception count on the Summary sheet reads zero, or the remaining issues get routed to someone else.
- Two fields stay outside the future state comparison: received date and worker. See GAP-01 and GAP-02 in [`DATA_MAPPING.md`](DATA_MAPPING.md).
