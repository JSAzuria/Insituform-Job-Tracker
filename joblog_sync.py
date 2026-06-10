# joblog_sync.py

import threading
from datetime import datetime, timedelta

from database import adhoc_connect, edw_connect
from config import EDW_JOBLOG_VIEWS
from constants import CUSTOMER_MAP
from helpers import (
    value,
    as_int_or_none,
    pull_sp_app_flags
)

# Rule-based compliance matrices mapped directly from project specification requirements
# These are also enforced in the EDW view WHERE clause to reduce rows pulled (Option 5).
EXCLUDED_TERMS = ["Plate", "Connector", "Additional", "Starter", "charge"]
EXCLUDED_WORDS = ["ME"]

_NORMALIZED_CUSTOMER_MAP = {k.lower().strip(): v for k, v in CUSTOMER_MAP.items()}

_sync_lock = threading.Lock()
_sync_in_progress = False

_MERGE_SQL = """
MERGE dbo.JOBLOG AS target
USING dbo.STAGING_JOBLOG AS source
    ON target.JobNumber = source.JobNumber

WHEN MATCHED AND target.Date_Completed IS NULL THEN
    UPDATE SET
        PalletNumber = source.PalletNumber,
        Customer     = source.Customer,
        Diameter     = source.Diameter,
        Thickness    = source.Thickness,
        Length       = source.Length,
        ShipBy       = source.ShipBy,
        SP_APP       = source.SP_APP,
        [DESC]       = source.[DESC],
        ME           = source.ME,
        SR           = source.SR,
        PS           = source.PS,
        OrderDate    = source.OrderDate,
        RUSH         = source.RUSH,
        PullBelt     = source.PullBelt,
        Revision     = source.Revision,
        LastPull     = GETDATE()

WHEN NOT MATCHED BY TARGET THEN
    INSERT (JobNumber, PalletNumber, Customer, Diameter, Thickness, Length,
            ShipBy, SP_APP, [DESC], ME, SR, PS, OrderDate, RUSH, PullBelt, Revision, LastPull)
    VALUES (source.JobNumber, source.PalletNumber, source.Customer, source.Diameter,
            source.Thickness, source.Length, source.ShipBy, source.SP_APP, source.[DESC],
            source.ME, source.SR, source.PS, source.OrderDate, source.RUSH,
            source.PullBelt, source.Revision, GETDATE());
"""


def run_automated_joblog_sync(force=False):
    """
    Evaluates database log timestamps from dbo.JOBLOG [LastPull].
    If older than 1 hour, pulls, processes, and updates the local JOBLOG dataset.
    Natively blocks multi-thread spamming via an application-level memory lock.

    Optimizations applied:
      - Option 1: Batch INSERT into staging via executemany() — eliminates per-row round-trips.
      - Option 4: Single adhoc connection reused for LastPull check and write phase.
      - Option 5: Description exclusion pushed into the EDW view WHERE clause; Python-side
                  check retained as a safety net only.
      - Staging MERGE: All UPDATE/INSERT logic delegated to a single server-side MERGE
                  statement against STAGING_JOBLOG, eliminating Python-side set tracking.
    """
    global _sync_in_progress

    with _sync_lock:
        if _sync_in_progress:
            print("[SYNC ALERT] Synchronization already running. Denying duplicate thread request.")
            return
        _sync_in_progress = True

    def sync_worker():
        global _sync_in_progress
        print("\n[SYNC] Background thread spawned successfully.")
        try:
            view_target = EDW_JOBLOG_VIEWS[0]

            # Option 4: Single adhoc connection reused for LastPull check and write phase.
            print("[SYNC] Connecting to local DB to check LastPull timestamp...")
            with adhoc_connect() as adhoc_conn:
                adhoc_cursor = adhoc_conn.cursor()

                row = adhoc_cursor.execute("SELECT MAX(LastPull) FROM dbo.JOBLOG").fetchone()
                last_pull = row[0] if row else None
                print(f"[SYNC] Current MAX(LastPull) in database: {last_pull}")

                if not force and last_pull and (datetime.now() - last_pull) < timedelta(hours=1):
                    time_remaining = timedelta(hours=1) - (datetime.now() - last_pull)
                    print(f"[SYNC] Skipping sync. Last pull was less than 1 hour ago. Try again in: {time_remaining}")
                    return

                print("[SYNC] Gating threshold passed. Accessing EDW...")
                print(f"[SYNC] Target Data Warehouse Extraction View: {view_target}")

                # Option 5: Exclusion terms enforced in the EDW view WHERE clause so excluded
                # rows never travel across the network. Python check below is a safety net only.
                with edw_connect() as edw_conn:
                    edw_cursor = edw_conn.cursor()
                    edw_cursor.execute(f"""
                        SELECT JobNumber, PalletNumber, Customer, Diameter, Thickness, Length,
                               ShipBy, SP_APP, OrderDate, RUSH, WorkOrder_Description, Description_2,
                               PullBelt, Revision, [DESC]
                        FROM {view_target}
                        WHERE JobNumber IS NOT NULL
                    """)
                    all_fetched_records = edw_cursor.fetchall()

                if not all_fetched_records:
                    print("[SYNC] Process suspended: No valid rows extracted.")
                    return

                print(f"[SYNC] Successfully pulled {len(all_fetched_records)} total rows from EDW.")

                # Build the staging payload in Python — validation and mapping only.
                staging_rows = []

                for record in all_fetched_records:
                    wo_desc = value(record, "WorkOrder_Description", "")
                    desc_2  = value(record, "Description_2", "")

                    # Option 5: Safety net — filters anything the view WHERE missed.
                    combined_desc = f"{wo_desc} {desc_2}".lower()
                    if any(term.lower() in combined_desc for term in EXCLUDED_TERMS):
                        continue
                    if any(f" {word.lower()} " in f" {combined_desc} " for word in EXCLUDED_WORDS):
                        continue

                    raw_job = as_int_or_none(value(record, "JobNumber"))
                    if not raw_job:
                        continue
                    job_num = int(raw_job)

                    diameter      = value(record, "Diameter")
                    is_transition = "TRANSITION" in (diameter or "").upper()

                    revision_val  = value(record, "Revision")

                    length_raw = value(record, "Length")
                    if not is_transition and (length_raw is None or (isinstance(length_raw, str) and not length_raw.strip())):
                        continue

                    customer_raw    = str(value(record, "Customer") or "").strip()
                    customer_mapped = _NORMALIZED_CUSTOMER_MAP.get(customer_raw.lower(), customer_raw)

                    sp_app          = value(record, "SP_APP", "")
                    me_flag, sr_flag, ps_flag = pull_sp_app_flags(sp_app)

                    staging_rows.append((
                        job_num,
                        value(record, "PalletNumber") or "",
                        customer_mapped,
                        diameter,                            # View handles TRANSITION/TAPER logic
                        value(record, "Thickness"),
                        length_raw,
                        value(record, "ShipBy"),
                        sp_app,
                        value(record, "DESC", None),         # View handles DESC build logic
                        me_flag,
                        sr_flag,
                        ps_flag,
                        value(record, "OrderDate"),
                        value(record, "RUSH"),
                        value(record, "PullBelt"),
                        revision_val,
                    ))

                if not staging_rows:
                    print("[SYNC] Process suspended: No valid rows remained after filtering.")
                    return

                print(f"[SYNC] {len(staging_rows)} rows passed validation. Loading staging table...")

                # Truncate staging and bulk load in one round-trip each.
                adhoc_cursor.execute("TRUNCATE TABLE dbo.STAGING_JOBLOG")

                adhoc_cursor.executemany("""
                    INSERT INTO dbo.STAGING_JOBLOG (
                        JobNumber, PalletNumber, Customer, Diameter, Thickness, Length,
                        ShipBy, SP_APP, [DESC], ME, SR, PS, OrderDate, RUSH, PullBelt, Revision
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, staging_rows)

                print("[SYNC] Staging load complete. Executing server-side MERGE...")

                # Single MERGE handles all UPDATE and INSERT logic entirely in SQL Server.
                adhoc_cursor.execute(_MERGE_SQL)
                rows_affected = adhoc_cursor.rowcount

                adhoc_conn.commit()
                print(f"[SYNC] Commit successful. MERGE affected {rows_affected} rows in JOBLOG.")

            print("[SYNC] Data connections safely closed and recycled.")

        except Exception as e:
            print(f"\n!!! [SYNC ERROR TRAPPED] !!!\nDetails: {str(e)}\n")
        finally:
            with _sync_lock:
                _sync_in_progress = False

    threading.Thread(target=sync_worker, daemon=True).start()