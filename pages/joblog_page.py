from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QCheckBox,
    QDateEdit,
    QMessageBox,
    QPushButton,
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

        self.panel = TablePanel("View Open Production Joblog")
        if hasattr(self.panel, "table"):
            self.panel.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        elif hasattr(self.panel, "table_view"):
            self.panel.table_view.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)

        # --- SORTING INITIALIZATION ---
        # 6 is ShipBy in the column_map below
        self.sort_col_idx = 6 
        self.sort_desc = False 

        self.column_map = {
            0: "PalletNumber", 1: "JobNumber", 2: "Customer", 3: "Diameter",
            4: "Thickness", 5: "Length", 6: "ShipBy", 7: "SP_APP",
            8: "[DESC]", 9: "RUSH", 10: "PullBelt"
        }

        self.tracked_columns = {
            0: "PalletNumber",
            2: "Customer",
            3: "Diameter",
            4: "Thickness",
            6: "ShipBy"
        }

        # --- UI Elements ---
        self.use_date_filter = QCheckBox("Filter by Date")
        self.use_date_filter.setCursor(Qt.CursorShape.PointingHandCursor)
        self.use_date_filter.setStyleSheet("font-weight: bold; color: #555555;")

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

        refresh_btn = QPushButton("Refresh Log")
        refresh_btn.setMinimumHeight(38)
        refresh_btn.clicked.connect(self.refresh)

        force_sync_btn = QPushButton("Force EDW Sync")
        force_sync_btn.setMinimumHeight(38)
        force_sync_btn.clicked.connect(self.force_sync)

        home_btn = QPushButton("Home Menu")
        home_btn.setMinimumHeight(40)
        home_btn.clicked.connect(lambda: self.app.navigate("Home"))

        # --- Layouts ---
        master_layout = QVBoxLayout(self)
        master_layout.setContentsMargins(24, 24, 24, 24)
        master_layout.setSpacing(20)

        top_bar = QHBoxLayout()
        session_frame = QFrame()
        session_frame.setObjectName("session_banner")
        session_frame.setStyleSheet("QFrame#session_banner { background-color: #E8650A; border-radius: 8px; }")
        session_layout = QHBoxLayout(session_frame)
        name_str = self.app.operator.FullName if self.app.operator else "Unknown"
        session_layout.addWidget(QLabel(f"Logged in as: {name_str}"))
        session_layout.addWidget(QPushButton("Logout", clicked=lambda: self.app.navigate("Logout")))
        top_bar.addStretch()
        top_bar.addWidget(session_frame)
        master_layout.addLayout(top_bar)

        header_rack = QHBoxLayout()
        page_title = QLabel("Master Production Joblog")
        page_title.setStyleSheet("font-size: 22px; font-weight: 800;")
        header_rack.addWidget(page_title)
        header_rack.addStretch()
        header_rack.addWidget(home_btn)
        master_layout.addLayout(header_rack)

        filter_card = QFrame()
        filter_card.setObjectName("glass")
        filter_layout = QHBoxLayout(filter_card)
        filter_layout.addWidget(self.use_date_filter)
        filter_layout.addWidget(QLabel("Start:"))
        filter_layout.addWidget(self.start_date)
        filter_layout.addWidget(QLabel("End:"))
        filter_layout.addWidget(self.end_date)
        filter_layout.addStretch()
        filter_layout.addWidget(refresh_btn)
        filter_layout.addWidget(force_sync_btn)
        master_layout.addWidget(filter_card)

        master_layout.addWidget(self.panel, stretch=1)
        
        # Initialize sorting hook and load data
        self._ensure_sorting_hook()
        self.refresh()

    def _load_changed_cells(self):
        changed = {}
        try:
            with adhoc_connect() as conn:
                cursor = conn.cursor()
                rows = cursor.execute("""
                    SELECT h.JobNumber, h.PalletNumber, h.Customer, h.Diameter,
                           h.Thickness, h.ShipBy,
                           j.PalletNumber AS cur_Pallet, j.Customer AS cur_Customer,
                           j.Diameter AS cur_Diameter, j.Thickness AS cur_Thickness,
                           j.ShipBy AS cur_ShipBy
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

            col_pairs = [(1, 6, 0), (2, 7, 2), (3, 8, 3), (4, 9, 4), (5, 10, 6)]

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

    def apply_row_colors(self, changed_cells: dict):
        view = getattr(self.panel, "table", None) or getattr(self.panel, "table_view", None)
        if not view: return
        model = view.model()
        source_model = model.sourceModel() if hasattr(model, "sourceModel") else model
        RED, BLUE, ORANGE = QColor("#FF4C4C"), QColor("#D1EAFF"), QColor("#FFE5CC")
        for row in range(source_model.rowCount()):
            dia_item = source_model.item(row, 3)
            row_color = None
            if dia_item:
                val = dia_item.text().lower()
                if "trans" in val: row_color = BLUE
                elif "taper" in val: row_color = ORANGE
            if row_color:
                for col in range(source_model.columnCount()):
                    cell = source_model.item(row, col)
                    if cell: cell.setBackground(QBrush(row_color))
            job_item = source_model.item(row, 1)
            if not job_item: continue
            try:
                job_num = int(job_item.text())
                if job_num in changed_cells:
                    for col_idx in changed_cells[job_num]:
                        cell = source_model.item(row, col_idx)
                        if cell: cell.setBackground(QBrush(RED))
            except ValueError: continue

    def refresh(self):
        try:
            sql = """
                SELECT PalletNumber, JobNumber, Customer, Diameter, Thickness,
                       Length, ShipBy, SP_APP, [DESC], RUSH, PullBelt
                FROM dbo.vw_JOBLOG_Open WHERE 1 = 1
            """
            params = []
            if self.use_date_filter.isChecked():
                sql += " AND ShipBy BETWEEN ? AND ?"
                params.extend([
                    self.start_date.date().toString("yyyy-MM-dd"),
                    self.end_date.date().toString("yyyy-MM-dd")
                ])

            col_name  = self.column_map.get(self.sort_col_idx, "PalletNumber")
            direction = "DESC" if self.sort_desc else "ASC"
            safe_col  = col_name if col_name.startswith("[") else f"[{col_name}]"

            if col_name == "PalletNumber":
                sql += f" ORDER BY LTRIM(RTRIM(PalletNumber)) {direction}, JobNumber ASC"
            else:
                sql += f" ORDER BY MIN({safe_col}) OVER(PARTITION BY LTRIM(RTRIM(PalletNumber))) {direction}, LTRIM(RTRIM(PalletNumber)) ASC, JobNumber ASC"

            with adhoc_connect() as conn:
                rows = conn.cursor().execute(sql, *params).fetchall()

            formatted_rows = [
                [r[0], r[1], r[2], r[3], r[4], r[5],
                 app_date_text(r[6]), r[7], r[8], r[9], r[10]]
                for r in rows
            ]

            headers = ["Pallet #", "Job #", "Customer", "Diameter", "Thickness",
                       "Length", "Ship By", "SP APP", "DESC", "Rush", "Pull Belt"]
            self.panel.set_rows(headers, formatted_rows)

            changed_cells = self._load_changed_cells()
            self.apply_row_colors(changed_cells)

        except Exception as exc:
            QMessageBox.critical(self, APP_TITLE, f"Error loading Joblog:\n{str(exc)}")

    def sort_handler(self, logical_index):
        if logical_index not in self.column_map:
            return
        self.sort_desc = not self.sort_desc if logical_index == self.sort_col_idx else False
        self.sort_col_idx = logical_index
        self.refresh()

    def _ensure_sorting_hook(self):
        table_obj = getattr(self.panel, "table", None) or getattr(self.panel, "table_view", None)
        if table_obj:
            table_obj.setSortingEnabled(False)
            header = table_obj.horizontalHeader()
            try: header.sectionClicked.disconnect(self.sort_handler)
            except: pass
            header.sectionClicked.connect(self.sort_handler)

    def force_sync(self):
        try:
            from joblog_sync import run_automated_joblog_sync
            run_automated_joblog_sync(force=True)
            QMessageBox.information(self, APP_TITLE, "Sync initiated in background.")
        except Exception as exc:
            QMessageBox.critical(self, APP_TITLE, f"Failed to sync:\n{str(exc)}")