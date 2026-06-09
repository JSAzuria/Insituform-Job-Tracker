# JOBLOG Tracker App

Python/PyQt6 desktop app for JOBLOG tracking.

## Run

```powershell
py JOBLOGTracker.py
```

## Architecture Overview
The system operates as a data pipeline and presentation layer decoupling heavy warehouse infrastructure from high-availability shop floor interfaces.

[SQLARGOSDEV1.EDW] (Data Warehouse Source View)
       │
       ▼ (hourly background sync thread via pyodbc)
[SQLPOWERBIPRD1.ADHOC.dbo.JOBLOG] (Local Shop Floor Cache Database)
       │
       ▼ (PyQt6 UI Layer)
[JOBLOG Tracker Desktop Application Windows]

## Main Features
1. Workstation & Interface Layout
Dynamic Taskbar Isolation: Employs Windows ctypes process mapping (insituform.joblogtracker.app.1) to override generic Python executable grouping, forcing the OS taskbar layer to crisply bind to the specific corporate icon asset.

Shop Floor Optimization: Enforces hardware-agnostic terminal scaling by maximizing layouts (showMaximized()) with custom styling states designed for high-visibility tactile input interaction.

2. Access Governance & Dynamic Navigation
Authentication is governed tightly via individual dbo.Operators.OperatorID parameters.

Application workspaces adapt gracefully depending on authorized access vectors (ROLE_FULL_MENU). Restricted production profiles are locked out of system-wide administrative views and routed directly into dedicated job telemetry pages.

3. Asynchronous Database Synchronization Loop
Non-Blocking Execution Engine: Synchronization processes run via a detached threading.Thread architecture to isolate system data mutations from UI operations.

Hourly Gatekeeper Validation: Evaluates the local database via a swift MAX(LastPull) scalar check. Processing is terminated silently if a data pull occurred within the past 60 minutes to prevent database contention unless an override signal is issued.

Network Failure-Safe Loop: View extractions utilize strict closed connection contexts. The application maintains an localized memory matrix tracking active operations (_sync_in_progress) with fallback parameters to guarantee worker threads recycle gracefully if transactional exceptions occur.

## Data Pipeline Logic Rules
Target Sources & Destinations
Extraction Origin: Server: SQLARGOSDEV1 | Database: EDW | Verified View Target: dbo.vw_Dim_JOBLOG_Creation

Storage Target: Server: SQLPOWERBIPRD1 | Database: ADHOC | Table: dbo.JOBLOG

## Record Matching & Persistence Matrix
Evaluates incoming files against a high-speed local memory cache tracking open records (WHERE Date_Completed IS NULL) to completely eliminate redundant row-by-row queries.

Matches are matched strictly by JobNumber. Existing entries are updated seamlessly with current dimensional properties, rush indicators, order dates, and network pull belt markers.

Zero-Deletion Policy: Missing data warehouse rows do not cause deletions in local tables; all current floor processes remain safely persisted.

Timestamp Tracking: Applies precise GETDATE() timestamps to the LastPull column of every inserted or modified database record.

## Source Exclusion Rules
Records are bypassed during compilation if WorkOrder_Description or Description_2 data string checks match any of the following parameters:

Plate

Connector

Additional

Starter

charge

Whole-word matches for ME

## Processing and String Formatting Engine
Diameter Corrections: If a description contains trans, the software forces a structural override to explicitly display "TRANSITION TO:" within the diameter metrics.

Customer Short-Codes: Resolves verbose branches using structural translation arrays (e.g., standardizing text such as "Alabama Wetout Branch" down to precise codes like "SC/BES").

Multi-End Stack Telemetry: Analyzes pallet records across data batches. If a single pallet contains matching layout tags for both the top and bottom of a product stack, the engine flags it as a mixed pallet and appends text such as "This end on bottom" or "ME on Top" to protect product orientation.

DESC Formatting Construction Matrix: Compiles structural field definitions based on keyword detections within the data warehouse string inputs:

Detections for Flex output FLEX SEAM.

Detections for Air output AIRTEST.

Detections for Canada West inside customer metadata output METERS.

Multiple matching flags are automatically concatenated cleanly using a forward slash separator (/).

## User Control Features
Grid Presentation Panels: Renders records inside optimized tabular views using explicit text alignment matrices and customized contrast states.

Data Export Subsystems: Features quick-access export components (QPushButton#secondary_button) allowing floor personnel to dump filtered tables into local .csv files for verification and analytical record-keeping.
