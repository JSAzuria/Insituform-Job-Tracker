# JOBLOG Tracker App

Python/PyQt6 desktop app for JOBLOG tracking.

## Run

```powershell
py JOBLOGTracker.py
```

## Main Features

- Login by `dbo.Operators.OperatorID`.
- Role-based menu from the JOBLOG SQL spec.
- Hourly pull from `SQLARGOSDEV1.EDW` into `SQLPOWERBIPRD1.ADHOC.dbo.JOBLOG`.
- Updates existing `JOBLOG` rows by `JobNumber`; does not delete missing jobs.
- Saves `LastPull` timestamp on each inserted/updated `JOBLOG` row.
- Skips source rows when `WorkOrder_Description` contains `Plate`, `Connector`, `Additional`, whole-word `ME`, `Starter`, or `charge`.
- Builds `DESC` from source rows:
  - `Flex` in `WorkOrder_Description` returns `FLEX SEAM`.
  - `Air` in `WorkOrder_Description` returns `AIRTEST`.
  - `Canada West` in `Customer` returns `METERS`.
  - Multiple matches are joined with `/`.
- Sortable/searchable tables and Excel workbook export.
