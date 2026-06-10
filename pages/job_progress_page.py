from __future__ import annotations

import re
from typing import Optional, Any
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTableView,
    QMessageBox,
    QHeaderView,
    QPushButton,
    QLabel,
    QFrame,
    QLineEdit,
    QStyledItemDelegate,
    QComboBox,
)
from PyQt6.QtGui import QStandardItemModel, QStandardItem
from PyQt6.QtCore import Qt, QTimer

from database import adhoc_connect
from config import APP_TITLE
from helpers import app_date_text


class LineDropdownDelegate(QStyledItemDelegate):
    """Custom delegate providing a standardized shop floor dropdown editor for allocation cells."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.options = [
            "", "1", "2", "3", "4", "5",
            "6", "7", "9", "10", "11", "12", "13", "14", "15",
            "17", "Special Apps", "NR"
        ]

    def createEditor(self, parent, option, index):
        editor = QComboBox(parent)
        editor.addItems(self.options)
        return editor

    def setEditorData(self, editor, index):
        text = index.model().data(index, Qt.ItemDataRole.EditRole) or ""
        idx = editor.findText(text)
        if idx >= 0:
            editor.setCurrentIndex(idx)
        else:
            editor.setCurrentIndex(0)

    def setModelData(self, editor, model, index):
        model.setData(index, editor.currentText(), Qt.ItemDataRole.EditRole)


class JobProgressPage(QWidget):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.setObjectName("root")

        # --- Data Grid Setup ---
        self.table = QTableView()
        self.model = QStandardItemModel()
        self.table.setModel(self.model)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(36)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setStyleSheet("font-weight: bold; color: #333333;")

        # Attach dropdown delegates to manufacturing allocations (columns 8 to 14)
        self.dropdown_delegate = LineDropdownDelegate(self)
        for col_idx in range(8, 15):
            self.table.setItemDelegateForColumn(col_idx, self.dropdown_delegate)

        # Connect the inline edit persistence hook
        self.model.itemChanged.connect(self.handle_inline_edit)

        # --- Sorting State Map ---
        self.sort_col_idx = 7  # Default to ShipBy
        self.sort_desc = False
        self.column_map = {
            0: "j.PalletNumber",
            1: "j.JobNumber",
            2: "j.Diameter",
            3: "j.Thickness",
            4: "j.Length",
            5: "j.SP_APP",
            6: "j.[DESC]",
            7: "j.ShipBy",
            15: "Step",
            16: "EventType",
        }

        # --- Column-to-Operation Name Mapping ---
        self.operation_map = {
            8: "Inner Join",
            9: "Outer Join",
            10: "Inner Sew",
            11: "Outer Sew",
            12: "Extrusion",
            13: "Inspection",
            14: "Special Apps"
        }

        # --- Control Actions ---
        refresh_btn = QPushButton("Refresh Status")
        refresh_btn.setMinimumHeight(40)
        refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        refresh_btn.clicked.connect(self.refresh)

        home_btn = QPushButton("Home Menu")
        home_btn.setMinimumHeight(40)
        home_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        home_btn.clicked.connect(self.app.show_role_home)

        # --- Tokenized Search Bar ---
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText(
            "Search tracking log... e.g. line=10 step=Extrusion D=8"
        )
        self.search_bar.setClearButtonEnabled(True)
        self.search_bar.setMinimumHeight(38)
        self.search_bar.textChanged.connect(self.filter_table)

        # --- Mass Update Controls Layout ---
        mass_panel = QHBoxLayout()
        mass_panel.setSpacing(10)
        
        lbl_mass = QLabel("Bulk Actions:")
        lbl_mass.setStyleSheet("font-weight: bold; color: #444444; font-size: 13px;")
        mass_panel.addWidget(lbl_mass)
        
        self.mass_line_selector = QComboBox()
        self.mass_line_selector.setMinimumHeight(34)
        self.mass_line_selector.addItems([opt for opt in self.dropdown_delegate.options if opt != ""])
        mass_panel.addWidget(self.mass_line_selector)
        
        self.mass_op_selector = QComboBox()
        self.mass_op_selector.setMinimumHeight(34)
        self.mass_op_selector.addItem("All Shop Columns", "all")
        for col_idx, name in self.operation_map.items():
            self.mass_op_selector.addItem(name, col_idx)
        mass_panel.addWidget(self.mass_op_selector)
        
        mass_run_btn = QPushButton("Mark Target as Complete")
        mass_run_btn.setMinimumHeight(34)
        mass_run_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        mass_run_btn.setStyleSheet("""
            QPushButton { background-color: #0A5C2C; color: white; font-weight: bold; padding: 0 16px; border-radius: 4px; }
            QPushButton:hover { background-color: #0D7337; }
        """)
        mass_run_btn.clicked.connect(self.handle_mass_complete)
        mass_panel.addWidget(mass_run_btn)
        mass_panel.addStretch()

        # --- Master Layout Assembly ---
        master_layout = QVBoxLayout(self)
        master_layout.setContentsMargins(24, 24, 24, 24)
        master_layout.setSpacing(20)

        # Session Frame
        top_bar = QHBoxLayout()
        session_frame = QFrame()
        session_frame.setObjectName("session_banner")
        session_frame.setStyleSheet("""
            QFrame#session_banner { background-color: #E8650A; border-radius: 8px; }
            QLabel { color: #000000; font-weight: 800; font-size: 13px; background: transparent; }
            QPushButton {
                background: rgba(255,255,255,0.22); color: white;
                border: 1px solid rgba(255,255,255,0.4); border-radius: 6px;
                padding: 6px 14px; font-weight: 700;
            }
            QPushButton:hover { background: rgba(255,255,255,0.35); }
        """)
        session_layout = QHBoxLayout(session_frame)
        session_layout.setContentsMargins(15, 8, 15, 8)
        name_str = self.app.operator.FullName if self.app.operator else "Unknown"
        session_layout.addWidget(QLabel(f"Tracking Console | Active User: {name_str}"))
        logout_btn = QPushButton("Logout")
        logout_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        logout_btn.clicked.connect(lambda: self.app.navigate("Logout"))
        session_layout.addWidget(logout_btn)
        top_bar.addStretch()
        top_bar.addWidget(session_frame)
        master_layout.addLayout(top_bar)

        # Title Rack
        header_rack = QHBoxLayout()
        page_title = QLabel("Live Production Progress Log")
        page_title.setObjectName("sectionTitle")
        page_title.setStyleSheet("font-size: 22px; font-weight: 800;")
        header_rack.addWidget(page_title)
        header_rack.addStretch()
        header_rack.addWidget(refresh_btn)
        header_rack.addWidget(home_btn)
        master_layout.addLayout(header_rack)

        # KPI Dashboard Cards
        kpi_rack = QHBoxLayout()
        self.card_total = self._create_kpi_card("Total Jobs Monitored", "0", "#555555")
        self.card_active = self._create_kpi_card("In Production", "0", "#E8650A")
        kpi_rack.addWidget(self.card_total)
        kpi_rack.addWidget(self.card_active)
        master_layout.addLayout(kpi_rack)

        master_layout.addWidget(self.search_bar)
        master_layout.addLayout(mass_panel)  # Injected Bulk Control Panel
        master_layout.addWidget(self.table)

        self.refresh()

    def _create_kpi_card(self, title: str, value: str, color: str) -> QFrame:
        card = QFrame()
        card.setObjectName("glass")
        card.setFixedHeight(70)
        layout = QHBoxLayout(card)
        layout.setContentsMargins(20, 0, 20, 0)
        
        lbl_title = QLabel(title)
        lbl_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #555555;")
        
        lbl_val = QLabel(value)
        lbl_val.setStyleSheet(f"font-size: 24px; font-weight: 900; color: {color}; margin-left: 10px;")
        
        layout.addWidget(lbl_title)
        layout.addWidget(lbl_val)
        layout.addStretch()
        card.setProperty("val_label", lbl_val)
        return card

    def sort_handler(self, logical_index: int):
        if logical_index not in self.column_map:
            return
        if logical_index == self.sort_col_idx:
            self.sort_desc = not self.sort_desc
        else:
            self.sort_col_idx = logical_index
            self.sort_desc = False
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
    # DATA EXTRACTION & DYNAMIC STATE MACHINE
    # -----------------------------------------------------------------------
    def refresh(self):
        try:
            self.model.blockSignals(True)
            self.search_bar.blockSignals(True)
            self.search_bar.clear()
            self.search_bar.blockSignals(False)

            col_field = self.column_map.get(self.sort_col_idx, "j.ShipBy").replace("j.", "")
            direction = "DESC" if self.sort_desc else "ASC"

            if col_field == "PalletNumber":
                order_by_clause = f"ORDER BY CleanPallet {direction}, JobNumber ASC"
            elif col_field in ("Step", "EventType"):
                order_by_clause = f"ORDER BY {col_field} {direction}, JobNumber ASC"
            else:
                order_by_clause = f"""
                    ORDER BY 
                        MIN({col_field}) OVER(PARTITION BY CleanPallet) {direction},
                        CleanPallet ASC, JobNumber ASC
                """

            sql = f"""
                WITH HighestTracking AS (
                    SELECT t.JobNumber, t.Operation, t.EventType,
                           ROW_NUMBER() OVER (
                               PARTITION BY t.JobNumber 
                               ORDER BY CASE LTRIM(RTRIM(t.Operation))
                                   WHEN 'Allot' THEN 1
                                   WHEN 'Inner Slit' THEN 2
                                   WHEN 'Outer Slit' THEN 3
                                   WHEN 'Inner Join' THEN 4
                                   WHEN 'Outer Join' THEN 5
                                   WHEN 'Inner Sew' THEN 6
                                   WHEN 'Outer Sew' THEN 7
                                   WHEN 'Extrusion' THEN 8
                                   WHEN 'Inspection' THEN 9
                                   WHEN 'Special Apps' THEN 10
                                   ELSE 0
                               END DESC, t.EventTime DESC
                           ) as rn
                    FROM dbo.JobTracking t
                ),
                ProgressLog AS (
                    SELECT 
                        AppPallet.CleanPallet,
                        j.PalletNumber, j.JobNumber, j.Diameter, j.Thickness, 
                        j.Length, j.SP_APP, j.[DESC], j.ShipBy, j.Date_Completed,
                        m.InnerJoinMFG, m.OuterJoinMFG, m.InnerSewMFG, m.OuterSewMFG, 
                        m.ExtrusionMFG, m.InspectionMFG,
                        ISNULL(th.Operation, '') AS Step,
                        ISNULL(th.EventType, '') AS EventType
                    FROM dbo.JOBLOG j
                    CROSS APPLY (SELECT LTRIM(RTRIM(j.PalletNumber)) AS CleanPallet) AppPallet
                    LEFT JOIN dbo.JobEntry_MFGLine m ON m.JobNumber = j.JobNumber
                    LEFT JOIN HighestTracking th ON th.JobNumber = j.JobNumber AND th.rn = 1
                    WHERE j.ShipBy >= CONVERT(DATE, DATEADD(day, -7, GETDATE()))
                )
                SELECT * FROM ProgressLog {order_by_clause}
            """

            with adhoc_connect() as conn:
                rows = conn.cursor().execute(sql).fetchall()

            self.model.clear()
            headers = [
                "Pallet #", "Job #", "Diameter", "Thickness", "Length",
                "SP_APP", "DESC", "ShipBy",
                "Inner Join", "Outer Join", "Inner Sew", "Outer Sew", "Extrusion", "Inspection", "Special Apps",
                "Step", "Event Type"
            ]
            self.model.setHorizontalHeaderLabels(headers)

            active_count = 0

            for row in rows:
                def clean_alloc(v):
                    if v == 999 or str(v) == "999" or str(v).strip().upper() == "NR":
                        return "NR"
                    if v is None:
                        return ""
                    val_str = str(v).strip()
                    if val_str.upper() == "SPECIAL APPS":
                        return "Special Apps"
                    val_str_clean = val_str.split(".")[0]
                    if val_str_clean == "1": return "Slitter 1"
                    if val_str_clean == "2": return "Slitter 2"
                    if val_str_clean == "3": return "Slitter 3"
                    return val_str_clean

                display_values = [
                    str(row.PalletNumber or ""),
                    str(row.JobNumber or ""),
                    str(row.Diameter or ""),
                    str(row.Thickness or ""),
                    str(row.Length or ""),
                    str(row.SP_APP or ""),
                    str(row.DESC or ""),
                    app_date_text(row.ShipBy),
                    clean_alloc(row.InnerJoinMFG),
                    clean_alloc(row.OuterJoinMFG),
                    clean_alloc(row.InnerSewMFG),
                    clean_alloc(row.OuterSewMFG),
                    clean_alloc(row.ExtrusionMFG),
                    clean_alloc(row.InspectionMFG),
                    "",  # Placeholder slot for index 14 ("Special Apps")
                    str(row.Step),
                    str(row.EventType)
                ]

                row_items = [QStandardItem(v) for v in display_values]
                
                for idx, item in enumerate(row_items):
                    if 8 <= idx <= 14:  # Allocation modification bounds
                        item.setEditable(True)
                    else:
                        item.setEditable(False)
                        
                self.model.appendRow(row_items)

                if row.Step != "":
                    active_count += 1

            self.card_total.property("val_label").setText(str(len(rows)))
            self.card_active.property("val_label").setText(str(active_count))
            
            self._ensure_sorting_hook()

        except Exception as exc:
            QMessageBox.critical(
                self, APP_TITLE, f"Failed to retrieve progress log matrix:\n{str(exc)}"
            )
        finally:
            self.model.blockSignals(False)

    # -----------------------------------------------------------------------
    # DATABASE PERSISTENCE LAYER
    # -----------------------------------------------------------------------
    def handle_inline_edit(self, item: QStandardItem):
        """Processes live view edits, updating production tables with dynamic validation."""
        col = item.column()
        if col not in self.operation_map:
            return

        row = item.row()
        job_item = self.model.item(row, 1)
        if not job_item or not job_item.text():
            return

        try:
            job_number = int(job_item.text())
        except ValueError:
            return

        current_operation = self.operation_map[col]
        current_line = item.text().strip()
        current_event_type = None

        if current_line == "Special Apps":
            current_operation = "Special Apps"

        if current_line and current_line.upper() != "NR":
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("Log Tracking Event")
            msg_box.setText(
                f"Line allocation modified for Job: {job_number}\n"
                f"Operation Step Identified: {current_operation}\n"
                f"Selected Line Parameter: {current_line}\n\n"
                f"Please specify the production log tracking status flag to record:"
            )
            
            on_line_btn = msg_box.addButton("On Line", QMessageBox.ButtonRole.ActionRole)
            complete_btn = msg_box.addButton("Complete", QMessageBox.ButtonRole.ActionRole)
            cancel_btn = msg_box.addButton("Cancel/Abort", QMessageBox.ButtonRole.RejectRole)
            
            msg_box.exec()
            
            if msg_box.clickedButton() == cancel_btn:
                QTimer.singleShot(0, self.refresh)
                return
                
            current_event_type = "On Line" if msg_box.clickedButton() == on_line_btn else "Complete"

        def to_numeric_allocation(val_str: str) -> Optional[Any]:
            t = val_str.upper().strip()
            if not t or t == "NONE": return None
            if t == "NR" or "999" in t: return 999
            if "SLITTER 1" in t: return 1
            if "SLITTER 2" in t: return 2
            if "SLITTER 3" in t: return 3
            if "SPECIAL APPS" in t: return "Special Apps"
            match = re.search(r'\d+', t)
            return int(match.group()) if match else val_str

        allocations = []
        for c in range(8, 15):
            cell_text = self.model.item(row, c).text()
            allocations.append(to_numeric_allocation(cell_text))

        db_ij, db_oj, db_isw, db_osw, db_ext, db_ins, db_sa = allocations

        try:
            self.model.blockSignals(True)
            with adhoc_connect() as conn:
                cur = conn.cursor()
                
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
                            JobNumber, InnerJoinMFG, OuterJoinMFG,
                            InnerSewMFG, OuterSewMFG,
                            ExtrusionMFG, InspectionMFG
                        )
                        VALUES (source.JobNumber, ?, ?, ?, ?, ?, ?);
                    """,
                    job_number,
                    db_ij, db_oj, db_isw, db_osw, db_ext, db_ins,
                    db_ij, db_oj, db_isw, db_osw, db_ext, db_ins
                )

                if current_event_type:
                    cur.execute(
                        """
                        INSERT INTO dbo.JobTracking (
                            OperatorName, JobNumber, Line, Operation, EventType, EventTime
                        )
                        VALUES (?, ?, ?, ?, ?, GETDATE())
                        """,
                        self.app.operator.FullName if self.app.operator else "Unknown",
                        job_number, current_line, current_operation, current_event_type
                    )

                    if current_event_type == "Complete":
                        cur.execute(
                            """
                            UPDATE dbo.JOBLOG
                            SET Date_Completed = CAST(GETDATE() AS date)
                            WHERE JobNumber = ? AND Date_Completed IS NULL
                            """,
                            job_number
                        )
                
                conn.commit()

        except Exception as err:
            QMessageBox.critical(
                self,
                "Transaction Sync Fault",
                f"Failed to commit tracking variations to database cluster data logs:\n\n{str(err)}"
            )
        finally:
            self.model.blockSignals(False)
            QTimer.singleShot(0, self.refresh)

    # -----------------------------------------------------------------------
    # TOKENIZED MULTI-FIELD SEARCH FILTER ENGINE
    # -----------------------------------------------------------------------
    def filter_table(self):
        """Processes dynamic search strings matching token conditions or direct sub-string lookups."""
        raw_query = self.search_bar.text().strip().lower()
        if not raw_query:
            for row_idx in range(self.model.rowCount()):
                self.table.setRowHidden(row_idx, False)
            return

        tokens = raw_query.split()
        
        # Field shorthand map matching table column layouts
        alias_map = {
            "pallet": 0, "p": 0,
            "job": 1, "j": 1,
            "diameter": 2, "d": 2,
            "thickness": 3, "t": 3,
            "length": 4, "l": 4,
            "sp": 5, "app": 5, "sp_app": 5,
            "desc": 6,
            "ship": 7, "shipby": 7,
            "step": 15, "op": 15, "operation": 15,
            "event": 16, "type": 16
        }

        for row_idx in range(self.model.rowCount()):
            row_match = True
            
            for token in tokens:
                if "=" in token:
                    key, val = token.split("=", 1)
                    key = key.strip()
                    val = val.strip()
                    
                    if key in alias_map:
                        col_idx = alias_map[key]
                        cell_item = self.model.item(row_idx, col_idx)
                        cell_text = cell_item.text().lower() if cell_item else ""
                        if val not in cell_text:
                            row_match = False
                            break
                    elif key in ("line", "mfg"):
                        # 'line' modifier cross-scans through allocation cell values (columns 8 to 14)
                        line_found = False
                        for col_idx in range(8, 15):
                            cell_item = self.model.item(row_idx, col_idx)
                            cell_text = cell_item.text().lower() if cell_item else ""
                            if val in cell_text:
                                line_found = True
                                break
                        if not line_found:
                            row_match = False
                            break
                    else:
                        # Fallback row aggregation check for unknown field keys
                        combined_row_text = ""
                        for col_idx in range(self.model.columnCount()):
                            item = self.model.item(row_idx, col_idx)
                            if item:
                                combined_row_text += " " + item.text().lower()
                        if token not in combined_row_text:
                            row_match = False
                            break
                else:
                    # Global unstructured text fallback match
                    combined_row_text = ""
                    for col_idx in range(self.model.columnCount()):
                        item = self.model.item(row_idx, col_idx)
                        if item:
                            combined_row_text += " " + item.text().lower()
                    if token not in combined_row_text:
                        row_match = False
                        break
            
            self.table.setRowHidden(row_idx, not row_match)

    # -----------------------------------------------------------------------
    # MASS BULK DATA UPDATE CONTROLLER
    # -----------------------------------------------------------------------
    def handle_mass_complete(self):
        """Processes a complete transaction push across all currently filtered/visible items matching line selection criteria."""
        target_line = self.mass_line_selector.currentText().strip()
        operation_target = self.mass_op_selector.currentData()
        
        if not target_line:
            return

        confirm = QMessageBox.question(
            self,
            "Confirm Bulk Completion Rollout",
            f"Are you sure you want to batch mark jobs containing Line '{target_line}' as Complete across the active view selection?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        operator_name = self.app.operator.FullName if self.app.operator else "Unknown"
        jobs_processed = 0

        def to_numeric_allocation(val_str: str) -> Optional[Any]:
            t = val_str.upper().strip()
            if not t or t == "NONE": return None
            if t == "NR" or "999" in t: return 999
            if "SLITTER 1" in t: return 1
            if "SLITTER 2" in t: return 2
            if "SLITTER 3" in t: return 3
            if "SPECIAL APPS" in t: return "Special Apps"
            match = re.search(r'\d+', t)
            return int(match.group()) if match else val_str

        try:
            self.model.blockSignals(True)
            
            with adhoc_connect() as conn:
                cur = conn.cursor()
                
                for row_idx in range(self.model.rowCount()):
                    # Respects the search engine by entirely skipping rows hidden by filter_table
                    if self.table.isRowHidden(row_idx):
                        continue
                        
                    job_item = self.model.item(row_idx, 1)
                    if not job_item or not job_item.text():
                        continue
                        
                    try:
                        job_number = int(job_item.text())
                    except ValueError:
                        continue

                    columns_to_evaluate = list(self.operation_map.keys()) if operation_target == "all" else [operation_target]
                    line_matched = False
                    matched_operations = []
                    
                    for col_idx in columns_to_evaluate:
                        cell_item = self.model.item(row_idx, col_idx)
                        if cell_item and cell_item.text().strip().lower() == target_line.lower():
                            line_matched = True
                            matched_operations.append((col_idx, self.operation_map[col_idx]))

                    if not line_matched:
                        continue

                    allocations = []
                    for c in range(8, 15):
                        cell_item = self.model.item(row_idx, c)
                        cell_text = cell_item.text() if cell_item else ""
                        allocations.append(to_numeric_allocation(cell_text))

                    db_ij, db_oj, db_isw, db_osw, db_ext, db_ins, db_sa = allocations

                    # 1. Update/Synchronize State Table parameters
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
                                JobNumber, InnerJoinMFG, OuterJoinMFG,
                                InnerSewMFG, OuterSewMFG,
                                ExtrusionMFG, InspectionMFG
                            )
                            VALUES (source.JobNumber, ?, ?, ?, ?, ?, ?);
                        """,
                        job_number,
                        db_ij, db_oj, db_isw, db_osw, db_ext, db_ins,
                        db_ij, db_oj, db_isw, db_osw, db_ext, db_ins
                    )

                    # 2. Add Tracking Logs for each matching column step
                    for col_idx, op_name in matched_operations:
                        exec_op = "Special Apps" if target_line == "Special Apps" else op_name
                        cur.execute(
                            """
                            INSERT INTO dbo.JobTracking (
                                OperatorName, JobNumber, Line, Operation, EventType, EventTime
                            )
                            VALUES (?, ?, ?, ?, 'Complete', GETDATE())
                            """,
                            operator_name, job_number, target_line, exec_op
                        )

                    # 3. Finalize core JOBLOG completion timestamps
                    cur.execute(
                        """
                        UPDATE dbo.JOBLOG
                        SET Date_Completed = CAST(GETDATE() AS date)
                        WHERE JobNumber = ? AND Date_Completed IS NULL
                        """,
                        job_number
                    )
                    
                    jobs_processed += 1
                
                conn.commit()
                
            QMessageBox.information(
                self, 
                "Success", 
                f"Successfully marked {jobs_processed} operations on Line {target_line} as Complete."
            )

        except Exception as err:
            QMessageBox.critical(
                self,
                "Bulk Transaction Sync Error",
                f"Failed to post bulk updates out to storage:\n\n{str(err)}"
            )
        finally:
            self.model.blockSignals(False)
            QTimer.singleShot(0, self.refresh)