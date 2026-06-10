# pages/assign_line_page.py

from __future__ import annotations

import re
from typing import Optional, NamedTuple

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTableView,
    QComboBox,
    QMessageBox,
    QHeaderView,
    QPushButton,
    QLabel,
    QFrame,
    QLineEdit,
)
from PyQt6.QtGui import QStandardItemModel, QStandardItem
from PyQt6.QtCore import Qt

from database import adhoc_connect
from config import APP_TITLE
from helpers import as_int_or_none, app_date_text
from constants import (
    JOIN_LINE_OPTIONS,
    INNER_SEW_OPTIONS,
    OUTER_SEW_OPTIONS,
    EXTRUSION_OPTIONS,
    INSPECTION_OPTIONS,
)

# ---------------------------------------------------------------------------
# LINE SUGGESTION ENGINE
# ---------------------------------------------------------------------------
#
# Full allocation rules per job type:
#
#  FLEX job (DESC contains FLEXSEAM, Dia ≤12, Thick <10, Len >1000)
#    InnerJoin  = NR
#    OuterJoin  = NR
#    InnerSew   = assigned sew line (6 or 10)
#    OuterSew   = assigned sew line (6 or 10)
#    Extrusion  = NR
#    Inspection = 1 or 2, alternating globally across the batch
#    Sew-line assignment: primary Line 10, overflow Line 6
#    Cap: 5 jobs per line per ShipBy date; keep like diameters together
#
#  EXT job (DESC contains EXT, Dia ≤15, Thick <10, Len >1000)
#    InnerJoin  = NR
#    OuterJoin  = NR
#    InnerSew   = assigned sew line (6 or 7)
#    OuterSew   = assigned sew line (6 or 7)
#    Extrusion  = 3
#    Inspection = 1 or 2, alternating globally across the batch
#    Sew-line assignment: primary Line 7, overflow Line 6
#    Cap: 5 jobs per line per ShipBy date; keep like diameters together
#    + Day-ahead diameter lookahead (see engine docstring)
#
#  Neither → skip entirely (no suggestion made)
#
# The engine is purely advisory.  apply_suggestions() only fills combos
# that are currently blank — operator assignments are never overwritten.
# ---------------------------------------------------------------------------

_LINE_DAY_MAX = 5

# Column indices in the raw SQL result rows.
# SELECT * FROM FilteredUnassignedJobs expands to:
#   0  CleanPallet   (computed alias — comes first because it's listed first)
#   1  PalletNumber
#   2  JobNumber
#   3  Diameter
#   4  Thickness
#   5  Length
#   6  SP_APP
#   7  DESC
#   8  ShipBy
#   9  AllocJob      (m.JobNumber AS AllocJob)
#  10  InnerJoinMFG
#  11  OuterJoinMFG
#  12  InnerSewMFG
#  13  OuterSewMFG
#  14  ExtrusionMFG
#  15  InspectionMFG
_C_PALLET    = 1
_C_JOB       = 2
_C_DIAMETER  = 3
_C_THICKNESS = 4
_C_LENGTH    = 5
_C_SP_APP    = 6
_C_DESC      = 7
_C_SHIPBY    = 8
_C_ALLOC_JOB = 9
_C_EXT_MFG   = 14   # ExtrusionMFG


class _Allocation(NamedTuple):
    """Full set of values the engine will write for one job."""
    inner_join: str   # "NR"
    outer_join: str   # "NR"
    inner_sew:  str   # line number string e.g. "6", "7", "10"
    outer_sew:  str   # same as inner_sew
    extrusion:  str   # "NR" for FLEX, "3" for EXT
    inspection: str   # "1" or "2"


def _safe_float(val, default: float = 0.0) -> float:
    try:
        return float(str(val).split()[0].replace('"', "").strip())
    except (ValueError, TypeError):
        return default


def _safe_int(val, default: int = 0) -> int:
    try:
        return int(float(str(val).strip()))
    except (ValueError, TypeError):
        return default


def _desc_has(desc_str, token: str) -> bool:
    if not desc_str:
        return False
    return token.upper() in str(desc_str).upper()


def _qualifies_flex(dia, thick, length) -> bool:
    return (
        _safe_float(dia)   <= 12
        and _safe_float(thick) <  10
        and _safe_int(length)  > 1000
    )


def _qualifies_ext(dia, thick, length) -> bool:
    return (
        _safe_float(dia)   <= 15
        and _safe_float(thick) <  10
        and _safe_int(length)  > 1000
    )


def suggest_line_allocations(rows: list) -> dict[int, _Allocation]:
    """
    Returns {job_number (int): _Allocation} for every job that:
      - has no existing ExtrusionMFG assignment, AND
      - qualifies as FLEX or EXT

    Algorithm
    ---------
    1. Bucket eligible jobs by type (FLEX / EXT) and ShipBy date.
    2. Within each date-bucket, sort by diameter DESC so like sizes stay
       together on the preferred line.
    3. FLEX  → fill Line 10 first (up to 5/day), spill to Line 6.
       EXT   → fill Line 7 first (up to 5/day), spill to Line 6.
       If both caps are exhausted the job is skipped (operator decides).
    4. EXT day-ahead diameter lookahead:
       When Line 7 slots for date D AND date D+1 are both full, scan date
       D+2 for EXT jobs whose diameter matches the Line-7 batch on date D.
       Those jobs are pre-assigned to Line 7 for D+2 (still counted against
       D+2's cap).  This mirrors the shop-floor practice of grouping e.g.
       Job 105 (8", 6/20), Job 107 (8", 6/21) together ahead of Job 106
       (7.5", 6/20).
    5. Inspection alternates globally (1, 2, 1, 2 …) in the order jobs are
       assigned, regardless of line or type.
    """

    suggestions: dict[int, _Allocation] = {}
    sew_line: dict[int, str] = {}
    job_type: dict[int, str] = {} 

    flex_buckets: dict[str, list] = {}
    ext_buckets:  dict[str, list] = {}

    for row in rows:
        job_no = _safe_int(row[_C_JOB])
        if not job_no:
            continue

        dia    = row[_C_DIAMETER]
        thick  = row[_C_THICKNESS]
        length = row[_C_LENGTH]
        desc   = str(row[_C_DESC] or "")
        shipby = str(row[_C_SHIPBY] or "")

        # 1. Parse baseline metrics
        d_val = _safe_float(dia)
        t_val = _safe_float(thick)
        l_val = _safe_int(length)

        # Regex Fallback: If metrics are empty/0, extract directly from DESC text (e.g. "8 x 4.5 4500")
        if (d_val == 0.0 or l_val == 0) and desc:
            match = re.search(r"(\d+(?:\.\d+)?)\s*[xX]\s*(\d+(?:\.\d+)?)\s+(\d+)", desc)
            if match:
                if d_val == 0.0:   d_val = float(match.group(1))
                if t_val == 0.0:   t_val = float(match.group(2))
                if l_val == 0:     l_val = int(match.group(3))

        # 2. Match type based on explicit criteria
        is_flex = _desc_has(desc, "FLEXSEAM") and (d_val <= 12 and t_val < 10 and l_val > 1000)
        is_ext  = _desc_has(desc, "EXT")      and (d_val <= 15 and t_val < 10 and l_val > 1000)

        item_payload = {
            "job_no": job_no,
            "d_val": d_val,
            "t_val": t_val,
            "l_val": l_val,
            "desc": desc,
        }

        if is_flex:
            flex_buckets.setdefault(shipby, []).append(item_payload)
        elif is_ext:
            ext_buckets.setdefault(shipby, []).append(item_payload)

    # ------------------------------------------------------------------
    # FLEX Processing (Line 10 Primary -> Line 6 Overflow -> Line 10 Default)
    # ------------------------------------------------------------------
    for date_str, bucket in sorted(flex_buckets.items()):
        bucket_sorted = sorted(bucket, key=lambda x: x["d_val"], reverse=True)
        l10 = 0
        l6  = 0
        for item in bucket_sorted:
            jno = item["job_no"]
            if l10 < _LINE_DAY_MAX:
                sew_line[jno] = "10"
                job_type[jno] = "FLEX"
                l10 += 1
            elif l6 < _LINE_DAY_MAX:
                sew_line[jno] = "6"
                job_type[jno] = "FLEX"
                l6 += 1
            else:
                # Capacity exceeded: Default back to Primary Line 10 instead of skipping
                sew_line[jno] = "10"
                job_type[jno] = "FLEX"

    # ------------------------------------------------------------------
    # EXT Processing (Line 7 Primary -> Line 6 Overflow -> Line 7 Default)
    # ------------------------------------------------------------------
    sorted_ext_dates = sorted(ext_buckets.keys())
    line7_fill: dict[str, int] = {d: 0 for d in sorted_ext_dates}
    line6_fill: dict[str, int] = {}

    for date_str in sorted_ext_dates:
        bucket_sorted = sorted(ext_buckets[date_str], key=lambda x: x["d_val"], reverse=True)
        l7 = line7_fill.get(date_str, 0)
        l6 = line6_fill.get(date_str, 0)
        
        for item in bucket_sorted:
            jno = item["job_no"]
            if jno in sew_line:
                continue
                
            if l7 < _LINE_DAY_MAX:
                sew_line[jno] = "7"
                job_type[jno] = "EXT"
                l7 += 1
            elif l6 < _LINE_DAY_MAX:
                sew_line[jno] = "6"
                job_type[jno] = "EXT"
                l6 += 1
            else:
                # Capacity exceeded: Default back to Primary Line 7 instead of skipping
                sew_line[jno] = "7"
                job_type[jno] = "EXT"
                
        line7_fill[date_str] = l7
        line6_fill[date_str] = l6

    # Lookahead adjustment sweep for EXT
    for i, date_str in enumerate(sorted_ext_dates):
        if line7_fill.get(date_str, 0) < _LINE_DAY_MAX or i + 2 >= len(sorted_ext_dates):
            continue
        if line7_fill.get(sorted_ext_dates[i + 1], 0) < _LINE_DAY_MAX:
            continue

        future_date = sorted_ext_dates[i + 2]
        future_bucket = ext_buckets.get(future_date, [])
        if not future_bucket:
            continue

        today_l7_dias: set[float] = {
            it["d_val"] for it in ext_buckets.get(date_str, []) if sew_line.get(it["job_no"]) == "7"
        }

        l7_future = line7_fill.get(future_date, 0)
        l6_future = line6_fill.get(future_date, 0)

        future_sorted = sorted(
            future_bucket,
            key=lambda x: (0 if x["d_val"] in today_l7_dias else 1, -x["d_val"]),
        )
        
        for item in future_sorted:
            jno = item["job_no"]
            if jno in sew_line or item["d_val"] not in today_l7_dias:
                continue
                
            if l7_future < _LINE_DAY_MAX:
                sew_line[jno] = "7"
                job_type[jno] = "EXT"
                l7_future += 1
            elif l6_future < _LINE_DAY_MAX:
                sew_line[jno] = "6"
                job_type[jno] = "EXT"
                l6_future += 1
                
        line7_fill[future_date] = l7_future
        line6_fill[future_date] = l6_future

    # ------------------------------------------------------------------
    # Build Object Packets (Deterministic globally alternated Inspection)
    # ------------------------------------------------------------------
    inspection_toggle = 1
    for jno in sorted(sew_line.keys()):
        line = sew_line[jno]
        jtype = job_type[jno]
        extrusion = "NR" if jtype == "FLEX" else "3"
        inspection = str(inspection_toggle)
        inspection_toggle = 2 if inspection_toggle == 1 else 1

        suggestions[jno] = _Allocation(
            inner_join="NR",
            outer_join="NR",
            inner_sew=line,
            outer_sew=line,
            extrusion=extrusion,
            inspection=inspection,
        )

    return suggestions


# ---------------------------------------------------------------------------
# PAGE
# ---------------------------------------------------------------------------

class AssignLinePage(QWidget):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.setObjectName("root")

        # --- Data Grid ---
        self.table = QTableView()
        self.model = QStandardItemModel()
        self.table.setModel(self.model)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(38)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setStyleSheet("font-weight: bold; color: #333333;")

        # --- Sorting state ---
        self.sort_col_idx = 7
        self.sort_desc    = False
        self.column_map   = {
            0: "j.PalletNumber",
            1: "j.JobNumber",
            2: "j.Diameter",
            3: "j.Thickness",
            4: "j.Length",
            5: "j.SP_APP",
            6: "j.[DESC]",
            7: "j.ShipBy",
        }

        # Cache of raw SQL rows for the suggestion engine (no extra DB call)
        self._last_rows: list = []

        # --- Buttons ---
        refresh_btn = QPushButton("Refresh Data")
        refresh_btn.setMinimumHeight(40)
        refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        refresh_btn.clicked.connect(self.refresh)

        home_btn = QPushButton("Home Menu")
        home_btn.setMinimumHeight(40)
        home_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        home_btn.clicked.connect(self.app.show_role_home)

        suggest_btn = QPushButton("⚡ Suggest Lines")
        suggest_btn.setToolTip(
            "Auto-fills blank allocation combos using diameter / thickness / length / DESC rules.\n"
            "Only blank cells are touched — existing assignments are never overwritten.\n\n"
            "FLEXSEAM (Dia ≤12, Thick <10, Len >1000) → Sew: Line 10 or 6 | Ext: NR\n"
            "EXT      (Dia ≤15, Thick <10, Len >1000) → Sew: Line 7 or 6  | Ext: 3\n"
            "InnerJoin / OuterJoin always set to NR.\n"
            "Inspection alternates 1 / 2 across the batch."
        )
        suggest_btn.setMinimumHeight(40)
        suggest_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        suggest_btn.clicked.connect(self.apply_suggestions)

        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText(
            "Search jobs by Pallet, Job #, Diameter, Thickness, Length, or Date…  "
            "e.g. D=8 T=16.5"
        )
        self.search_bar.setClearButtonEnabled(True)
        self.search_bar.setMinimumHeight(38)
        self.search_bar.textChanged.connect(self.filter_table)

        save_btn = QPushButton("Save Allocations")
        save_btn.setProperty("accent", True)
        save_btn.setMinimumHeight(45)
        save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        save_btn.clicked.connect(self.save)

        # --- Master Layout ---
        master_layout = QVBoxLayout(self)
        master_layout.setContentsMargins(24, 24, 24, 24)
        master_layout.setSpacing(20)

        # Session banner
        top_bar = QHBoxLayout()
        session_frame = QFrame()
        session_frame.setObjectName("session_banner")
        session_frame.setStyleSheet("""
            QFrame#session_banner {
                background-color: #E8650A;
                border-radius: 8px;
            }
            QLabel {
                color: #000000;
                font-weight: 800;
                font-size: 13px;
                background: transparent;
                border: none;
            }
            QPushButton {
                background: rgba(255,255,255,0.22);
                color: white;
                border: 1px solid rgba(255,255,255,0.4);
                border-radius: 6px;
                padding: 6px 14px;
                font-weight: 700;
            }
            QPushButton:hover { background: rgba(255,255,255,0.35); }
        """)
        session_layout = QHBoxLayout(session_frame)
        session_layout.setContentsMargins(15, 8, 15, 8)
        session_layout.setSpacing(15)
        name_str = self.app.operator.FullName if self.app.operator else "Unknown"
        session_layout.addWidget(QLabel(f"Logged in as: {name_str}"))
        logout_btn = QPushButton("Logout")
        logout_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        logout_btn.clicked.connect(lambda: self.app.navigate("Logout"))
        session_layout.addWidget(logout_btn)
        top_bar.addStretch()
        top_bar.addWidget(session_frame)
        master_layout.addLayout(top_bar)

        # Header rack
        header_rack = QHBoxLayout()
        page_title = QLabel("Manufacturing Line Allocation")
        page_title.setObjectName("sectionTitle")
        page_title.setStyleSheet("font-size: 22px; font-weight: 800;")
        header_rack.addWidget(page_title)
        header_rack.addStretch()
        header_rack.addWidget(suggest_btn)
        header_rack.addWidget(refresh_btn)
        header_rack.addWidget(home_btn)
        master_layout.addLayout(header_rack)

        # KPI card
        self.kpi_card = QFrame()
        self.kpi_card.setObjectName("glass")
        self.kpi_card.setFixedHeight(75)
        kpi_layout = QHBoxLayout(self.kpi_card)
        kpi_layout.setContentsMargins(25, 0, 25, 0)
        kpi_title = QLabel("Unassigned Jobs Pending Allocation:")
        kpi_title.setStyleSheet("font-size: 15px; font-weight: bold; color: #555555;")
        self.kpi_val = QLabel("0")
        self.kpi_val.setStyleSheet(
            "font-size: 26px; font-weight: 900; color: #E8650A; margin-left: 5px;"
        )
        kpi_layout.addWidget(kpi_title)
        kpi_layout.addWidget(self.kpi_val)
        kpi_layout.addStretch()
        master_layout.addWidget(self.kpi_card)

        master_layout.addWidget(self.search_bar)
        master_layout.addWidget(self.table)

        bottom_row = QHBoxLayout()
        bottom_row.addStretch()
        bottom_row.addWidget(save_btn)
        master_layout.addLayout(bottom_row)

        self.refresh()

    # -----------------------------------------------------------------------
    # SORTING
    # -----------------------------------------------------------------------

    def sort_handler(self, logical_index: int):
        if logical_index not in self.column_map:
            return
        if logical_index == self.sort_col_idx:
            self.sort_desc = not self.sort_desc
        else:
            self.sort_col_idx = logical_index
            self.sort_desc    = False
        self.refresh()

    def _ensure_sorting_hook(self):
        self.table.setSortingEnabled(False)
        header = self.table.horizontalHeader()
        try:
            header.sectionClicked.disconnect(self.sort_handler)
        except TypeError:
            pass
        header.sectionClicked.connect(self.sort_handler)

    # -----------------------------------------------------------------------
    # DATA LOAD
    # -----------------------------------------------------------------------

    def refresh(self):
        try:
            self.search_bar.blockSignals(True)
            self.search_bar.clear()
            self.search_bar.blockSignals(False)

            col_field = self.column_map.get(self.sort_col_idx, "j.ShipBy").replace("j.", "")
            direction = "DESC" if self.sort_desc else "ASC"

            if col_field == "PalletNumber":
                order_by_clause = f"ORDER BY CleanPallet {direction}, JobNumber ASC"
            else:
                order_by_clause = f"""
                    ORDER BY
                        MIN({col_field}) OVER(PARTITION BY CleanPallet) {direction},
                        CleanPallet ASC,
                        JobNumber ASC
                """

            sql = f"""
                WITH FilteredUnassignedJobs AS (
                    SELECT
                        LTRIM(RTRIM(j.PalletNumber)) AS CleanPallet,
                        j.PalletNumber, j.JobNumber, j.Diameter, j.Thickness,
                        j.Length, j.SP_APP, j.[DESC], j.ShipBy,
                        m.JobNumber      AS AllocJob,
                        m.InnerJoinMFG,  m.OuterJoinMFG,
                        m.InnerSewMFG,   m.OuterSewMFG,
                        m.ExtrusionMFG,  m.InspectionMFG
                    FROM dbo.JOBLOG j
                    LEFT JOIN dbo.JobEntry_MFGLine m ON m.JobNumber = j.JobNumber
                    WHERE j.Date_Completed IS NULL
                      AND j.Length IS NOT NULL AND j.Length <> ''
                      AND j.ShipBy >= CONVERT(DATE, GETDATE())
                      AND (
                          m.JobNumber     IS NULL
                          OR m.InnerSewMFG   IS NULL OR m.InnerSewMFG   = ''
                          OR m.ExtrusionMFG  IS NULL OR m.ExtrusionMFG  = ''
                          OR m.InspectionMFG IS NULL OR m.InspectionMFG = ''
                          OR m.OuterSewMFG   IS NULL OR m.OuterSewMFG   = ''
                      )
                )
                SELECT * FROM FilteredUnassignedJobs {order_by_clause}
            """

            with adhoc_connect() as conn:
                rows = conn.cursor().execute(sql).fetchall()

            self._last_rows = rows   # Cache for suggestion engine

            self.model.clear()
            headers = [
                "Pallet #", "Job #", "Diameter", "Thickness", "Length",
                "SP_APP", "DESC", "ShipBy",
                "Inner Join", "Outer Join", "Inner Sew", "Outer Sew",
                "Extrusion", "Inspection",
            ]
            self.model.setHorizontalHeaderLabels(headers)

            for row in rows:
                base_values = [
                    row.PalletNumber, row.JobNumber, row.Diameter, row.Thickness,
                    row.Length, row.SP_APP, row.DESC, app_date_text(row.ShipBy),
                ]
                items = [QStandardItem("" if v is None else str(v)) for v in base_values]
                for it in items:
                    it.setEditable(False)

                self.model.appendRow(items + [QStandardItem("") for _ in range(6)])
                r = self.model.rowCount() - 1

                if row.AllocJob is not None:
                    def parse_db_val(v):
                        if v == 999 or str(v) == "999":
                            return "NR"
                        return "" if v is None else str(v).split(".")[0]

                    ij_init  = parse_db_val(row.InnerJoinMFG)
                    oj_init  = parse_db_val(row.OuterJoinMFG)
                    isw_init = parse_db_val(row.InnerSewMFG)
                    osw_init = parse_db_val(row.OuterSewMFG)
                    ext_init = parse_db_val(row.ExtrusionMFG)
                    ins_init = parse_db_val(row.InspectionMFG)
                else:
                    auto_nr  = self._is_small_diameter(row.Diameter)
                    ij_init  = "NR" if auto_nr else ""
                    oj_init  = "NR" if auto_nr else ""
                    isw_init = ""
                    osw_init = ""
                    ext_init = "NR" if auto_nr else ""
                    ins_init = ""

                # Store baseline so save() can detect changes
                items[1].setData(
                    [ij_init, oj_init, isw_init, osw_init, ext_init, ins_init],
                    Qt.ItemDataRole.UserRole,
                )

                self._add_combo(r,  8, JOIN_LINE_OPTIONS,  ij_init)
                self._add_combo(r,  9, JOIN_LINE_OPTIONS,  oj_init)
                self._add_combo(r, 10, INNER_SEW_OPTIONS,  isw_init)
                self._add_combo(r, 11, OUTER_SEW_OPTIONS,  osw_init)
                self._add_combo(r, 12, EXTRUSION_OPTIONS,  ext_init)
                self._add_combo(r, 13, INSPECTION_OPTIONS, ins_init)

            self.kpi_val.setText(str(len(rows)))
            self._ensure_sorting_hook()

        except Exception as exc:
            QMessageBox.critical(
                self, APP_TITLE,
                f"Failed to pull active job allocation states:\n{str(exc)}",
            )

    # -----------------------------------------------------------------------
    # LINE SUGGESTION — apply to UI
    # -----------------------------------------------------------------------

    def apply_suggestions(self):
        """
        Runs the suggestion engine against cached row data and fills in all
        six allocation combos for each qualifying job, but ONLY where the
        combo is currently blank.  Existing values are never overwritten.
        Reports a summary to the operator when done.
        """
        if not self._last_rows:
            QMessageBox.information(self, APP_TITLE, "No data loaded — refresh first.")
            return

        suggestions = suggest_line_allocations(list(self._last_rows))

        if not suggestions:
            QMessageBox.information(
                self, APP_TITLE,
                "No automatic suggestions could be made for the current job set.\n\n"
                "Jobs must meet one of these criteria to be suggested:\n"
                "  FLEXSEAM — Dia ≤12, Thick <10, Length >1000  →  Lines 10 / 6\n"
                "  EXT      — Dia ≤15, Thick <10, Length >1000  →  Lines 7 / 6",
            )
            return

        # Map display column index → field name in _Allocation
        # Col 8=InnerJoin, 9=OuterJoin, 10=InnerSew, 11=OuterSew,
        #     12=Extrusion, 13=Inspection
        col_field_map = {
            8:  "inner_join",
            9:  "outer_join",
            10: "inner_sew",
            11: "outer_sew",
            12: "extrusion",
            13: "inspection",
        }

        applied = 0
        skipped = 0

        for model_row in range(self.model.rowCount()):
            job_item = self.model.item(model_row, 1)
            if not job_item:
                continue
            job_no = as_int_or_none(job_item.text())
            if job_no not in suggestions:
                continue

            alloc = suggestions[job_no]

            for col_idx, field_name in col_field_map.items():
                combo = self.table.indexWidget(self.model.index(model_row, col_idx))
                if not isinstance(combo, QComboBox):
                    continue

                current_val = combo.currentText().strip()
                if current_val not in ("", "None"):
                    # Respect existing operator choice
                    skipped += 1
                    continue

                suggested_val = getattr(alloc, field_name)
                idx = combo.findText(suggested_val)
                if idx >= 0:
                    combo.setCurrentIndex(idx)
                    if col_idx == 12:   # Count once per job (keyed on Extrusion)
                        applied += 1
                else:
                    # Value not in the combo list — leave blank, operator decides
                    skipped += 1

        QMessageBox.information(
            self, APP_TITLE,
            f"Line suggestions applied.\n\n"
            f"  Jobs filled : {applied}\n"
            f"  Cells skipped (already set or value not in list) : {skipped}\n\n"
            "Review the highlighted rows and hit Save Allocations when ready.",
        )

    # -----------------------------------------------------------------------
    # WIDGET HELPERS
    # -----------------------------------------------------------------------

    def _add_combo(self, row: int, col: int, options, current: str):
        combo = QComboBox()
        combo.addItems([""] + [str(o) for o in options])
        combo.setCurrentText("" if current is None else str(current))
        combo.setMinimumHeight(28)
        self.table.setIndexWidget(self.model.index(row, col), combo)

    def _combo_value(self, row: int, col: int) -> Optional[str]:
        widget = self.table.indexWidget(self.model.index(row, col))
        if isinstance(widget, QComboBox):
            val = widget.currentText().strip()
            return None if val == "" else val
        return None

    def _is_small_diameter(self, diameter) -> bool:
        try:
            return float(diameter) < 40
        except Exception:
            return False

    # -----------------------------------------------------------------------
    # FILTER
    # -----------------------------------------------------------------------

    def filter_table(self, filter_text: str):
        keys_pattern = (
            r"(?:pallet\s*#|pallet\s*number|pallet|p|"
            r"job\s*#|job\s*number|job|j|"
            r"diameter|dia|d|"
            r"thickness|thick|t|"
            r"length|len|l|"
            r"sp_app|sp\s*app|"
            r"desc|description|"
            r"shipby|ship\s*by|date)"
        )
        search_term = filter_text.strip().lower()
        pairs = re.findall(
            rf"\b({keys_pattern})\s*=\s*(.*?)(?=\s*\b{keys_pattern}\s*=|$)",
            search_term,
        )
        key_map = {
            "pallet": 0, "pallet #": 0, "pallet number": 0, "p": 0,
            "job": 1, "job #": 1, "job number": 1, "j": 1,
            "diameter": 2, "dia": 2, "d": 2,
            "thickness": 3, "thick": 3, "t": 3,
            "length": 4, "len": 4, "l": 4,
            "sp_app": 5, "sp app": 5,
            "desc": 6, "description": 6,
            "shipby": 7, "ship by": 7, "date": 7,
        }
        parsed_conditions = []
        for raw_k, raw_v in pairs:
            k = " ".join(raw_k.split())
            v = raw_v.strip()
            if v.endswith(" and"):
                v = v[:-4].strip()
            elif v.startswith("and "):
                v = v[4:].strip()
            if k in key_map and v:
                parsed_conditions.append((key_map[k], v))

        for row_idx in range(self.model.rowCount()):
            if not search_term:
                self.table.setRowHidden(row_idx, False)
                continue

            if parsed_conditions:
                row_matches = True
                for target_col, clean_val in parsed_conditions:
                    item = self.model.item(row_idx, target_col)
                    if not item:
                        row_matches = False
                        break
                    item_text = item.text().strip().lower()
                    if target_col in (2, 3, 4):
                        try:
                            if float(item_text) != float(clean_val):
                                row_matches = False
                                break
                        except ValueError:
                            if clean_val not in item_text:
                                row_matches = False
                                break
                    else:
                        if clean_val not in item_text:
                            row_matches = False
                            break
                self.table.setRowHidden(row_idx, not row_matches)
            else:
                match_found = any(
                    (item := self.model.item(row_idx, c)) and search_term in item.text().lower()
                    for c in range(8)
                )
                self.table.setRowHidden(row_idx, not match_found)

    # -----------------------------------------------------------------------
    # SAVE
    # -----------------------------------------------------------------------

    def save(self):
        try:
            def to_numeric_allocation(val):
                if val == "NR":
                    return 999
                if val in (None, ""):
                    return None
                try:
                    return int(float(val))
                except (ValueError, TypeError):
                    return val

            with adhoc_connect() as conn:
                cur = conn.cursor()
                change_count = 0

                for row in range(self.model.rowCount()):
                    job_item = self.model.item(row, 1)
                    if not job_item:
                        continue
                    job_number = as_int_or_none(job_item.text())
                    if not job_number:
                        continue

                    ij  = self._combo_value(row,  8)
                    oj  = self._combo_value(row,  9)
                    isw = self._combo_value(row, 10)
                    osw = self._combo_value(row, 11)
                    ext = self._combo_value(row, 12)
                    ins = self._combo_value(row, 13)

                    initial_states = job_item.data(Qt.ItemDataRole.UserRole) or ["", "", "", "", "", ""]
                    current_states = [ij or "", oj or "", isw or "", osw or "", ext or "", ins or ""]

                    if current_states == initial_states:
                        continue

                    db_ij  = to_numeric_allocation(ij)
                    db_oj  = to_numeric_allocation(oj)
                    db_isw = to_numeric_allocation(isw)
                    db_osw = to_numeric_allocation(osw)
                    db_ext = to_numeric_allocation(ext)
                    db_ins = to_numeric_allocation(ins)

                    cur.execute(
                        """
                        MERGE dbo.JobEntry_MFGLine AS target
                        USING (SELECT ? AS JobNumber) AS source
                        ON (target.JobNumber = source.JobNumber)
                        WHEN MATCHED THEN
                            UPDATE SET
                                InnerJoinMFG  = ?,
                                OuterJoinMFG  = ?,
                                InnerSewMFG   = ?,
                                OuterSewMFG   = ?,
                                ExtrusionMFG  = ?,
                                InspectionMFG = ?
                        WHEN NOT MATCHED THEN
                            INSERT (
                                JobNumber,    InnerJoinMFG, OuterJoinMFG,
                                InnerSewMFG,  OuterSewMFG,
                                ExtrusionMFG, InspectionMFG
                            )
                            VALUES (source.JobNumber, ?, ?, ?, ?, ?, ?);
                        """,
                        job_number,
                        db_ij, db_oj, db_isw, db_osw, db_ext, db_ins,
                        db_ij, db_oj, db_isw, db_osw, db_ext, db_ins,
                    )
                    change_count += 1

                if change_count > 0:
                    conn.commit()
                    QMessageBox.information(
                        self, APP_TITLE,
                        f"Successfully saved mappings for {change_count} changed job record(s).",
                    )
                else:
                    QMessageBox.information(
                        self, APP_TITLE,
                        "No allocations modified; database commit skipped.",
                    )

            self.refresh()

        except Exception as e:
            QMessageBox.critical(
                self, "Transaction Failure",
                f"Failed to persist batch layout mappings:\n{str(e)}",
            )