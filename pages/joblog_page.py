# joblog_page.py

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QCheckBox,
    QDateEdit,
    QMessageBox,
    QLabel,
    QAbstractItemView,
    QFrame,
    QCalendarWidget
)
from PyQt6.QtCore import QDate, Qt
from PyQt6.QtGui import QColor, QBrush
from database import adhoc_connect
from config import APP_TITLE
from widgets.table_panel import TablePanel
from helpers import app_date_text
from constants import shipped_special_apps_filter
from ui_components import add_header_row, add_session_row, action_button

CALENDAR_STYLE = """
    QCalendarWidget { background-color: #FFFFFF; color: #222222; }
    QCalendarWidget QAbstractItemView {
        background-color: #FFFFFF; color: #222222;
        selection-background-color: #E8650A; selection-color: #FFFFFF;
    }
    QCalendarWidget QAbstractItemView:disabled { color: #AAAAAA; }
    QCalendarWidget QWidget#qt_calendar_navigationbar { background-color: #F0F0F0; }
    QCalendarWidget QToolButton { background-color: transparent; color: #222222; font-weight: bold; }
    QCalendarWidget QToolButton:hover { background-color: #E8650A; color: #FFFFFF; border-radius: 4px; }
    QCalendarWidget QSpinBox { background-color: #FFFFFF; color: #222222; }
    QCalendarWidget QMenu { background-color: #FFFFFF; color: #222222; }
"""

def _apply_calendar_style(date_edit: QDateEdit):
    cal = date_edit.calendarWidget()
    if cal:
        cal.setStyleSheet(CALENDAR_STYLE)


class JoblogPage(QWidget):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.setObjectName("root")
        self.expanded_revision_pallets = set()
        self.current_formatted_rows = []
        self.current_changed_cells = {}

        self.panel = TablePanel("View Open Production Joblog")
        self.panel.search_input.textChanged.connect(self.filter_table)

        # BUG FIX 1: TablePanel only exposes table_view, never table.
        # Use table_view directly instead of probing both attributes.
        self.panel.table_view.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.panel.table_view.clicked.connect(self.toggle_revision_group)

        # --- SORTING INITIALIZATION ---
        # Column 6 = ShipBy per column_map below
        self.sort_col_idx = 6
        self.sort_desc = False

        # Display column index → SQL column name
        self.column_map = {
            0: "PalletNumber", 1: "JobNumber",  2: "Customer",  3: "Diameter",
            4: "Thickness",    5: "Length",      6: "ShipBy",    7: "SP_APP",
            8: "[DESC]",       9: "RUSH",       10: "PullBelt", 11: "Revision"
        }

        # Columns that are compared against JOBLOG_History for change highlighting.
        # Keys are display column indices; values match the history query field order:
        #   row[0]=JobNumber, row[1]=PalletNumber, row[2]=Customer, row[3]=Diameter,
        #   row[4]=Thickness, row[5]=ShipBy  (history snapshot)
        #   row[6]=cur_Pallet, row[7]=cur_Customer, row[8]=cur_Diameter,
        #   row[9]=cur_Thickness, row[10]=cur_ShipBy  (current live values)
        # BUG FIX 3: display_col values corrected to match column_map above.
        self.tracked_columns = {
            0: "PalletNumber",
            2: "Customer",
            3: "Diameter",
            4: "Thickness",
            6: "ShipBy",
        }

        # --- UI Elements ---
        self.use_date_filter = QCheckBox("Filter by Date")
        self.use_date_filter.setCursor(Qt.CursorShape.PointingHandCursor)
        self.use_date_filter.setStyleSheet("font-weight: bold; color: #555555;")
        self.use_date_filter.toggled.connect(self.refresh)

        self.show_batesville_stock = QCheckBox("Show Batesville Stock")
        self.show_batesville_stock.setCursor(Qt.CursorShape.PointingHandCursor)
        self.show_batesville_stock.setChecked(False)
        self.show_batesville_stock.setStyleSheet("font-weight: bold; color: #555555;")
        self.show_batesville_stock.toggled.connect(self.refresh)

        self.show_revisions = QCheckBox("Show Revisions")
        self.show_revisions.setCursor(Qt.CursorShape.PointingHandCursor)
        self.show_revisions.setChecked(False)
        self.show_revisions.setStyleSheet("font-weight: bold; color: #555555;")
        self.show_revisions.toggled.connect(self.refresh)

        self.start_date = QDateEdit(QDate.currentDate().addDays(-30))
        self.start_date.setCalendarPopup(True)
        self.start_date.setDisplayFormat("MM-dd-yyyy")
        self.start_date.setMinimumHeight(38)
        _apply_calendar_style(self.start_date)

        self.end_date = QDateEdit(QDate.currentDate().addDays(90))
        self.end_date.setCalendarPopup(True)
        self.end_date.setDisplayFormat("MM-dd-yyyy")
        self.end_date.setMinimumHeight(38)
        _apply_calendar_style(self.end_date)

        refresh_btn = action_button("Refresh Log", self.refresh, height=38)
        force_sync_btn = action_button("Force EDW Sync", self.force_sync, height=38)
        home_btn = action_button("Home Menu", lambda: self.app.navigate("Home"))

        # --- Layouts ---
        master_layout = QVBoxLayout(self)
        master_layout.setContentsMargins(24, 24, 24, 24)
        master_layout.setSpacing(20)

        add_session_row(master_layout, self.app)
        add_header_row(master_layout, "Master Production Joblog", home_btn)

        filter_card = QFrame()
        filter_card.setObjectName("glass")
        filter_layout = QHBoxLayout(filter_card)
        filter_layout.addWidget(self.use_date_filter)
        filter_layout.addWidget(QLabel("Start:"))
        filter_layout.addWidget(self.start_date)
        filter_layout.addWidget(QLabel("End:"))
        filter_layout.addWidget(self.end_date)
        filter_layout.addSpacing(10)
        filter_layout.addWidget(self.show_batesville_stock)
        filter_layout.addWidget(self.show_revisions)
        filter_layout.addStretch()
        filter_layout.addWidget(refresh_btn)
        filter_layout.addWidget(force_sync_btn)
        master_layout.addWidget(filter_card)

        master_layout.addWidget(self.panel, stretch=1)

        # Initialize sorting hook and load data
        self._ensure_sorting_hook()
        self.refresh()

    # --------------------------------------------------------------------------

    @staticmethod
    def _revision_text(row):
        return str(row[11] or "").strip().upper()

    @staticmethod
    def _clean_pallet_text(text):
        pallet = str(text or "").strip()
        if pallet.startswith(("+", "-")):
            return pallet[1:].strip()
        return pallet

    def _format_revision_pallet(self, pallet, expanded):
        return f"- {pallet}" if expanded else f"+ {pallet}"

    def _revision_display_rows(self, rows):
        grouped_rows = []
        pallet_groups = {}

        for row in rows:
            pallet = str(row[0] or "").strip()
            if pallet not in pallet_groups:
                pallet_groups[pallet] = []
                grouped_rows.append((pallet, pallet_groups[pallet]))
            pallet_groups[pallet].append(row)

        display_rows = []
        for pallet, group in grouped_rows:
            revisions = {self._revision_text(row) for row in group}
            has_revision_pair = "NEW" in revisions and "OLD" in revisions

            if not has_revision_pair:
                display_rows.extend(group)
                continue

            expanded = pallet in self.expanded_revision_pallets
            old_rows = [row for row in group if self._revision_text(row) == "OLD"]
            old_rows_inserted = False

            for row in group:
                revision = self._revision_text(row)
                if revision == "OLD":
                    continue

                display_row = list(row)
                if revision == "NEW":
                    display_row[0] = self._format_revision_pallet(pallet, expanded)
                display_rows.append(display_row)

                if expanded and revision == "NEW" and not old_rows_inserted:
                    for old_row in old_rows:
                        old_display_row = list(old_row)
                        old_display_row[0] = f"  {pallet}"
                        display_rows.append(old_display_row)
                    old_rows_inserted = True

            if expanded and not old_rows_inserted:
                display_rows.extend(old_rows)

        return display_rows

    def toggle_revision_group(self, index):
        if index.column() != 0:
            return

        source_index = self.panel.proxy_model.mapToSource(index)
        pallet_item = self.panel.source_model.item(source_index.row(), 0)
        if not pallet_item:
            return

        pallet_text = pallet_item.text()
        if not pallet_text.startswith(("+", "-")):
            return

        pallet = self._clean_pallet_text(pallet_text)
        if pallet in self.expanded_revision_pallets:
            self.expanded_revision_pallets.remove(pallet)
        else:
            self.expanded_revision_pallets.add(pallet)

        self._render_cached_rows()

    # --------------------------------------------------------------------------

    def _render_cached_rows(self):
        headers = [
            "Pallet #", "Job #", "Customer", "Diameter", "Thickness",
            "Length", "Ship By", "SP APP", "DESC", "Rush", "Pull Belt", "Revision",
        ]
        display_rows = self._revision_display_rows(self.current_formatted_rows)
        self.panel.set_rows(headers, display_rows)
        self.apply_row_colors(self.current_changed_cells)

    # --------------------------------------------------------------------------

    def filter_table(self, text):
        proxy = getattr(self.panel, "filter_proxy", None)
        if proxy:
            proxy.set_search_text(text)

    # --------------------------------------------------------------------------

    def _load_changed_cells(self):
        """
        Returns {job_number (int): set_of_display_col_indices_that_changed}.

        History query column layout (0-based):
            0  JobNumber
            1  h.PalletNumber   (snapshot)
            2  h.Customer       (snapshot)
            3  h.Diameter       (snapshot)
            4  h.Thickness      (snapshot)
            5  h.ShipBy         (snapshot)
            6  j.PalletNumber   (current)
            7  j.Customer       (current)
            8  j.Diameter       (current)
            9  j.Thickness      (current)
            10 j.ShipBy         (current)

        col_pairs: (history_snapshot_idx, current_live_idx, display_col_in_grid)
        BUG FIX 3: display_col values aligned with self.column_map.
        """
        changed = {}
        try:
            with adhoc_connect() as conn:
                cursor = conn.cursor()
                rows = cursor.execute("""
                    SELECT h.JobNumber,
                           h.PalletNumber, h.Customer, h.Diameter, h.Thickness, h.ShipBy,
                           j.PalletNumber AS cur_Pallet, j.Customer AS cur_Customer,
                           j.Diameter     AS cur_Diameter, j.Thickness AS cur_Thickness,
                           j.ShipBy       AS cur_ShipBy
                    FROM (
                        SELECT *, ROW_NUMBER() OVER (
                            PARTITION BY JobNumber ORDER BY ChangeDate DESC
                        ) AS rn
                        FROM dbo.JOBLOG_History
                        WHERE ChangeDate >= DATEADD(DAY, -7, GETDATE())
                    ) h
                    INNER JOIN dbo.JOBLOG j ON j.JobNumber = h.JobNumber
                    WHERE h.rn = 1
                """).fetchall()

            # (history_idx, current_idx, display_col)
            # display_col matches column_map: PalletNumber=0, Customer=2,
            # Diameter=3, Thickness=4, ShipBy=6
            col_pairs = [
                (1, 6,  0),   # PalletNumber
                (2, 7,  2),   # Customer
                (3, 8,  3),   # Diameter
                (4, 9,  4),   # Thickness
                (5, 10, 6),   # ShipBy
            ]

            for row in rows:
                job_num = row[0]
                flagged_cols = set()
                for hist_idx, cur_idx, display_col in col_pairs:
                    hist_val = str(row[hist_idx] or "").strip()
                    cur_val  = str(row[cur_idx]  or "").strip()
                    if hist_val != cur_val:
                        flagged_cols.add(display_col)
                if flagged_cols:
                    changed[job_num] = flagged_cols

        except Exception as exc:
            print(f"[CHANGE HIGHLIGHT] Failed to load history diff: {exc}")

        return changed

    # --------------------------------------------------------------------------

    def apply_row_colors(self, changed_cells: dict):
        # BUG FIX 1: use table_view directly — TablePanel has no `.table` attribute.
        view = self.panel.table_view
        model = view.model()
        source_model = model.sourceModel() if hasattr(model, "sourceModel") else model

        RED    = QColor("#FF4C4C")
        BLUE   = QColor("#D1EAFF")
        ORANGE = QColor("#FFE5CC")

        for row in range(source_model.rowCount()):
            dia_item = source_model.item(row, 3)
            row_color = None
            if dia_item:
                val = dia_item.text().lower()
                if "trans" in val:
                    row_color = BLUE
                elif "taper" in val:
                    row_color = ORANGE

            if row_color:
                for col in range(source_model.columnCount()):
                    cell = source_model.item(row, col)
                    if cell:
                        cell.setBackground(QBrush(row_color))

            job_item = source_model.item(row, 1)
            if not job_item:
                continue
            try:
                job_num = int(job_item.text())
                if job_num in changed_cells:
                    for col_idx in changed_cells[job_num]:
                        cell = source_model.item(row, col_idx)
                        if cell:
                            cell.setBackground(QBrush(RED))
            except ValueError:
                continue

    # --------------------------------------------------------------------------

    def refresh(self):
        try:
            changed_cells = self._load_changed_cells()
            sql = f"""
                SELECT j.PalletNumber, j.JobNumber, j.Customer, j.Diameter, j.Thickness,
                       j.Length, j.ShipBy, j.SP_APP, j.[DESC], j.RUSH, j.PullBelt, j.Revision
                FROM dbo.vw_JOBLOG_Open j
                WHERE 1 = 1
                  AND {shipped_special_apps_filter("j.JobNumber")}
            """
            params = []

            if self.use_date_filter.isChecked():
                sql += " AND ShipBy BETWEEN ? AND ?"
                params.extend([
                    self.start_date.date().toString("yyyy-MM-dd"),
                    self.end_date.date().toString("yyyy-MM-dd"),
                ])

            if self.show_batesville_stock.isChecked():
                sql += " AND (ShipBy IS NULL OR LTRIM(RTRIM(ShipBy)) = '')"
            else:
                sql += " AND (ShipBy IS NOT NULL AND LTRIM(RTRIM(ShipBy)) != '')"

            if self.show_revisions.isChecked():
                changed_job_numbers = list(changed_cells.keys())
                revision_filters = [
                    """PalletNumber IN (
                        SELECT PalletNumber
                        FROM dbo.vw_JOBLOG_Open
                        WHERE Revision = 'NEW'
                    )"""
                ]

                if changed_job_numbers:
                    placeholders = ", ".join("?" for _ in changed_job_numbers)
                    revision_filters.append(f"j.JobNumber IN ({placeholders})")
                    params.extend(changed_job_numbers)

                sql += " AND (" + " OR ".join(revision_filters) + ")"

            col_name  = self.column_map.get(self.sort_col_idx, "PalletNumber")
            direction = "DESC" if self.sort_desc else "ASC"
            safe_col  = col_name if col_name.startswith("[") else f"[{col_name}]"

            if col_name == "PalletNumber":
                sql += f" ORDER BY LTRIM(RTRIM(PalletNumber)) {direction}, JobNumber ASC"
            else:
                sql += (
                    f" ORDER BY MIN({safe_col}) OVER"
                    f"(PARTITION BY LTRIM(RTRIM(PalletNumber))) {direction},"
                    f" LTRIM(RTRIM(PalletNumber)) ASC, JobNumber ASC"
                )

            with adhoc_connect() as conn:
                # BUG FIX 4: pass params as a list, not unpacked with *.
                # pyodbc expects execute(sql, [p1, p2]) not execute(sql, p1, p2).
                rows = conn.cursor().execute(sql, params).fetchall()

            self.current_changed_cells = changed_cells
            self.current_formatted_rows = [
                [
                    r[0], r[1], r[2], r[3], r[4], r[5],
                    app_date_text(r[6]), r[7], r[8], r[9], r[10], r[11],
                ]
                for r in rows
            ]
            self._render_cached_rows()

        except Exception as exc:
            QMessageBox.critical(self, APP_TITLE, f"Error loading Joblog:\n{str(exc)}")

    # --------------------------------------------------------------------------

    def sort_handler(self, logical_index):
        if logical_index not in self.column_map:
            return
        self.sort_desc = (
            not self.sort_desc if logical_index == self.sort_col_idx else False
        )
        self.sort_col_idx = logical_index
        self.refresh()

    def _ensure_sorting_hook(self):
        # BUG FIX 1: table_view only — no need to probe for .table.
        table_obj = self.panel.table_view
        table_obj.setSortingEnabled(False)
        header = table_obj.horizontalHeader()
        try:
            header.sectionClicked.disconnect(self.sort_handler)
        except Exception:
            pass
        header.sectionClicked.connect(self.sort_handler)

    # --------------------------------------------------------------------------

    def force_sync(self):
        try:
            self.app.start_joblog_sync(force=True)
            QMessageBox.information(self, APP_TITLE, "Sync initiated in background.")
        except Exception as exc:
            QMessageBox.critical(self, APP_TITLE, f"Failed to sync:\n{str(exc)}")
