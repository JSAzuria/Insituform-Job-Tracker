import json
import threading
from datetime import date, datetime, timedelta

from database import adhoc_connect, edw_connect
from config import EDW_JOBLOG_VIEWS
from constants import CUSTOMER_MAP
from helpers import (
    value,
    as_int_or_none,
    pull_sp_app_flags
)

# Rule-based compliance matrices mapped directly from project specification requirements.
# These are also enforced in the EDW view WHERE clause to reduce rows pulled.
EXCLUDED_TERMS = ["Plate", "Connector", "Additional", "Starter", "charge"]
EXCLUDED_WORDS = ["ME"]

_NORMALIZED_CUSTOMER_MAP = {k.lower().strip(): v for k, v in CUSTOMER_MAP.items()}

_sync_lock = threading.Lock()
_sync_in_progress = False
_json_staging_available = True
_SYNC_BATCH_SIZE = 200
_PROGRESS_NOTIFY_EVERY = 1000
_SQL_INT_MIN = -2147483648
_SQL_INT_MAX = 2147483647
_STAGING_COLUMNS = (
    "JobNumber",
    "PalletNumber",
    "Customer",
    "Diameter",
    "Thickness",
    "Length",
    "ShipBy",
    "SP_APP",
    "DESC",
    "ME",
    "SR",
    "PS",
    "OrderDate",
    "RUSH",
    "PullBelt",
    "Revision",
)

_EDW_SELECT_SQL = """
SELECT JobNumber, PalletNumber, Customer, Diameter, Thickness, Length,
       ShipBy, SP_APP, OrderDate, RUSH, WorkOrder_Description, Description_2,
       PullBelt, Revision, [DESC]
FROM {view_target}
WHERE JobNumber IS NOT NULL
"""

_STAGING_INSERT_SQL = """
INSERT INTO dbo.STAGING_JOBLOG WITH (TABLOCK) (
    JobNumber, PalletNumber, Customer, Diameter, Thickness, Length,
    ShipBy, SP_APP, [DESC], ME, SR, PS, OrderDate, RUSH, PullBelt, Revision
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
"""

_STAGING_INSERT_JSON_SQL = """
INSERT INTO dbo.STAGING_JOBLOG WITH (TABLOCK) (
    JobNumber, PalletNumber, Customer, Diameter, Thickness, Length,
    ShipBy, SP_APP, [DESC], ME, SR, PS, OrderDate, RUSH, PullBelt, Revision
)
SELECT JobNumber, PalletNumber, Customer, Diameter, Thickness, Length,
       ShipBy, SP_APP, [DESC], ME, SR, PS, OrderDate, RUSH, PullBelt, Revision
FROM OPENJSON(CAST(? AS nvarchar(max)))
WITH (
    JobNumber int '$.JobNumber',
    PalletNumber nvarchar(50) '$.PalletNumber',
    Customer varchar(255) '$.Customer',
    Diameter varchar(50) '$.Diameter',
    Thickness varchar(50) '$.Thickness',
    Length int '$.Length',
    ShipBy date '$.ShipBy',
    SP_APP nvarchar(100) '$.SP_APP',
    [DESC] nvarchar(255) '$.DESC',
    ME int '$.ME',
    SR int '$.SR',
    PS int '$.PS',
    OrderDate date '$.OrderDate',
    RUSH char(1) '$.RUSH',
    PullBelt nvarchar(10) '$.PullBelt',
    Revision varchar(50) '$.Revision'
);
"""

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


def _disable_fast_executemany(cursor):
    try:
        cursor.fast_executemany = False
    except Exception:
        pass


def _sql_int_or_none(raw):
    value_as_int = as_int_or_none(raw)
    if value_as_int is None:
        return None
    if not (_SQL_INT_MIN <= value_as_int <= _SQL_INT_MAX):
        return None
    return value_as_int


def _json_default(raw):
    if isinstance(raw, datetime):
        return raw.date().isoformat()
    if isinstance(raw, date):
        return raw.isoformat()
    return str(raw)


def _rows_to_json_payload(staging_rows):
    return json.dumps(
        [dict(zip(_STAGING_COLUMNS, row)) for row in staging_rows],
        default=_json_default,
        separators=(",", ":"),
    )


def _record_to_staging_row(record):
    wo_desc = value(record, "WorkOrder_Description", "")
    desc_2 = value(record, "Description_2", "")

    # Safety net only. Main exclusion belongs in the EDW view.
    combined_desc = f"{wo_desc} {desc_2}".lower()
    if any(term.lower() in combined_desc for term in EXCLUDED_TERMS):
        return None
    if any(f" {word.lower()} " in f" {combined_desc} " for word in EXCLUDED_WORDS):
        return None

    job_num = _sql_int_or_none(value(record, "JobNumber"))
    if not job_num:
        return None

    diameter = value(record, "Diameter")
    is_transition = "TRANSITION" in (diameter or "").upper()

    length_value = _sql_int_or_none(value(record, "Length"))
    if not is_transition and length_value is None:
        return None

    customer_raw = str(value(record, "Customer") or "").strip()
    customer_mapped = _NORMALIZED_CUSTOMER_MAP.get(customer_raw.lower(), customer_raw)

    sp_app = value(record, "SP_APP", "")
    me_flag, sr_flag, ps_flag = pull_sp_app_flags(sp_app)

    return (
        job_num,
        value(record, "PalletNumber") or "",
        customer_mapped,
        diameter,
        value(record, "Thickness"),
        length_value,
        value(record, "ShipBy"),
        sp_app,
        value(record, "DESC", None),
        _sql_int_or_none(me_flag),
        _sql_int_or_none(sr_flag),
        _sql_int_or_none(ps_flag),
        value(record, "OrderDate"),
        value(record, "RUSH"),
        value(record, "PullBelt"),
        value(record, "Revision"),
    )


def _flush_staging_rows(cursor, staging_rows):
    global _json_staging_available

    if not staging_rows:
        return 0

    if _json_staging_available:
        cursor.execute("SAVE TRANSACTION staging_chunk")
        try:
            cursor.execute(_STAGING_INSERT_JSON_SQL, _rows_to_json_payload(staging_rows))
            return len(staging_rows)
        except Exception as batch_error:
            _json_staging_available = False
            cursor.execute("ROLLBACK TRANSACTION staging_chunk")
            print(f"[SYNC WARNING] Fast JSON staging failed, falling back to row batch: {batch_error}")

    cursor.execute("SAVE TRANSACTION staging_chunk")
    try:
        cursor.executemany(_STAGING_INSERT_SQL, staging_rows)
        return len(staging_rows)
    except Exception as batch_error:
        cursor.execute("ROLLBACK TRANSACTION staging_chunk")
        print(f"[SYNC WARNING] Batch insert failed, checking rows one at a time: {batch_error}")

    inserted_count = 0
    for row in staging_rows:
        try:
            cursor.execute(_STAGING_INSERT_SQL, row)
            inserted_count += 1
        except Exception as row_error:
            print(
                "[SYNC WARNING] Skipping bad staging row "
                f"JobNumber={row[0]}, PalletNumber={row[1]}, Length={row[5]}, PS={row[11]}: {row_error}"
            )

    return inserted_count


def _notify(progress_callback, message, busy=True):
    print(message)
    if progress_callback:
        try:
            progress_callback(message, busy)
        except Exception:
            pass


def run_automated_joblog_sync(force=False, progress_callback=None):
    """
    Evaluates dbo.JOBLOG LastPull. If stale, pulls EDW rows in small batches,
    loads dbo.STAGING_JOBLOG, then lets SQL Server merge into dbo.JOBLOG.
    """
    global _sync_in_progress

    with _sync_lock:
        if _sync_in_progress:
            return
        _sync_in_progress = True

    def sync_worker():
        global _sync_in_progress
        _notify(progress_callback, "\n[SYNC] Connected to database successfully...")
        try:
            view_target = EDW_JOBLOG_VIEWS[0]

            _notify(progress_callback, "[SYNC] Checking Last Update...")
            with adhoc_connect() as adhoc_conn:
                adhoc_cursor = adhoc_conn.cursor()

                row = adhoc_cursor.execute("SELECT MAX(LastPull) FROM dbo.JOBLOG").fetchone()
                last_pull = row[0] if row else None
                _notify(progress_callback, f"[SYNC] Last Pull from database: {last_pull}")

                if not force and last_pull and (datetime.now() - last_pull) < timedelta(hours=1):
                    time_remaining = timedelta(hours=1) - (datetime.now() - last_pull)
                    _notify(
                        progress_callback,
                        f"[SYNC] Skipping sync. Last pull was less than 1 hour ago. Try again in: {time_remaining}",
                        False,
                    )
                    return

                _notify(progress_callback, "[SYNC] Gating threshold passed. Accessing Database...")
                _notify(progress_callback, f"[SYNC] Target Data Warehouse Extraction View: {view_target}")

                _notify(progress_callback, "[SYNC] Clearing staging table...")
                _disable_fast_executemany(adhoc_cursor)
                adhoc_cursor.execute("TRUNCATE TABLE dbo.STAGING_JOBLOG")

                fetched_count = 0
                staged_count = 0
                last_progress_fetched = 0

                _notify(progress_callback, "[SYNC] Opening database connection...")
                with edw_connect() as edw_conn:
                    edw_cursor = edw_conn.cursor()
                    edw_cursor.arraysize = _SYNC_BATCH_SIZE

                    _notify(progress_callback, "[SYNC] Executing database extract query...")
                    edw_cursor.execute(_EDW_SELECT_SQL.format(view_target=view_target))
                    _notify(
                        progress_callback,
                        f"[SYNC] Database query accepted. Fetching and staging first {_SYNC_BATCH_SIZE} rows...",
                    )

                    while True:
                        records = edw_cursor.fetchmany(_SYNC_BATCH_SIZE)
                        if not records:
                            break

                        fetched_count += len(records)
                        staging_rows = []

                        for record in records:
                            staging_row = _record_to_staging_row(record)
                            if staging_row:
                                staging_rows.append(staging_row)

                        staged_count += _flush_staging_rows(adhoc_cursor, staging_rows)
                        should_notify_progress = (
                            fetched_count == _SYNC_BATCH_SIZE
                            or fetched_count - last_progress_fetched >= _PROGRESS_NOTIFY_EVERY
                        )
                        if should_notify_progress:
                            last_progress_fetched = fetched_count
                            _notify(
                                progress_callback,
                                f"[SYNC] Pulled {fetched_count} rows from {view_target}; staged {staged_count} valid rows...",
                            )

                if fetched_count == 0:
                    _notify(progress_callback, "[SYNC] Process suspended: No valid rows extracted.", False)
                    return

                if staged_count == 0:
                    _notify(progress_callback, "[SYNC] Process suspended: No valid rows remained after filtering.", False)
                    return

                _notify(
                    progress_callback,
                    f"[SYNC] Chunked staging complete. {staged_count} rows ready. Executing server-side MERGE...",
                )

                adhoc_cursor.execute(_MERGE_SQL)
                rows_affected = adhoc_cursor.rowcount

                adhoc_conn.commit()
                _notify(
                    progress_callback,
                    f"[SYNC] Commit successful. MERGE affected {rows_affected} rows in JOBLOG.",
                    False,
                )

            _notify(progress_callback, "[SYNC] Data connections safely closed and recycled.", False)

        except Exception as e:
            _notify(progress_callback, f"!!! [SYNC ERROR TRAPPED] !!! Details: {str(e)}", False)
        finally:
            with _sync_lock:
                _sync_in_progress = False

    threading.Thread(target=sync_worker, daemon=True).start()
