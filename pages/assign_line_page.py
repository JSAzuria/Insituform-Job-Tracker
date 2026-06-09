# pages/assign_line_page.py

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
    QLineEdit
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

class AssignLinePage(QWidget):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.setObjectName("root")

        # --- Data Grid Assembly ---
        self.table = QTableView()
        self.model = QStandardItemModel()
        self.table.setModel(self.model)

        # Polishing table presentation profiles
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(38)  # Generous padding for shop floor environments
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setStyleSheet("font-weight: bold; color: #333333;")

        # --- STATE TRACKING FOR PALLET-GROUPED SORTING ---
        self.sort_col_idx = 8  # Default sort column index initialized to 8 (ShipBy)
        self.sort_desc = False # Default Ascending
        
# Map selectable data columns to their corresponding database fields
        self.column_map = {
            0: "j.PalletNumber",
            1: "j.JobNumber",
            2: "j.Diameter",
            3: "j.Thickness",
            4: "j.Length",
            5: "j.SP",           # Added
            6: "j.APP",          # Added
            7: "j.[DESC]",       # Added (using square brackets for keyword safety)
            8: "j.ShipBy"        # Shifted index
        }

        # --- Interactive Control Elements ---
        refresh_btn = QPushButton("Refresh Data")
        refresh_btn.setMinimumHeight(40)
        refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        refresh_btn.clicked.connect(self.refresh)

        home_btn = QPushButton("Home Menu")
        home_btn.setMinimumHeight(40)
        home_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        home_btn.clicked.connect(self.app.show_role_home)

        # --- Search Bar Configuration ---
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Search jobs by Pallet, Job #, Diameter, Thickness, Length, or Date...")
        self.search_bar.setClearButtonEnabled(True)
        self.search_bar.setMinimumHeight(38)
        self.search_bar.textChanged.connect(self.filter_table)

        save_btn = QPushButton("Save Allocations")
        save_btn.setProperty("accent", True)  # Stylesheet targeting identifier
        save_btn.setMinimumHeight(45)
        save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        save_btn.clicked.connect(self.save)

        # --- Master Layout Assembly ---
        master_layout = QVBoxLayout(self)
        master_layout.setContentsMargins(24, 24, 24, 24)
        master_layout.setSpacing(20)

        # --------------------------------------------------
        # TOP ROW: CONTEXTUAL USER SESSION BANNER (RIGHT-ALIGNED)
        # --------------------------------------------------
        top_bar = QHBoxLayout()

        # Orange Session Framework Container
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
                background: rgba(255, 255, 255, 0.22);
                color: white;
                border: 1px solid rgba(255, 255, 255, 0.4);
                border-radius: 6px;
                padding: 6px 14px;
                font-weight: 700;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.35);
            }
        """)

        session_layout = QHBoxLayout(session_frame)
        session_layout.setContentsMargins(15, 8, 15, 8)
        session_layout.setSpacing(15)

        name_str = self.app.operator.FullName if self.app.operator else "Unknown"
        user_label = QLabel(f"Logged in as: {name_str}")
        
        logout_btn = QPushButton("Logout")
        logout_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        logout_btn.clicked.connect(lambda: self.app.navigate("Logout"))

        session_layout.addWidget(user_label)
        session_layout.addWidget(logout_btn)
        
        top_bar.addStretch()
        top_bar.addWidget(session_frame)
        master_layout.addLayout(top_bar)

        # --------------------------------------------------
        # HEADER CONTROL RACK (Title & Global Actions)
        # --------------------------------------------------
        header_rack = QHBoxLayout()
        
        page_title = QLabel("Manufacturing Line Allocation")
        page_title.setObjectName("sectionTitle")
        page_title.setStyleSheet("font-size: 22px; font-weight: 800;")
        
        header_rack.addWidget(page_title)
        header_rack.addStretch()
        header_rack.addWidget(refresh_btn)
        header_rack.addWidget(home_btn)
        master_layout.addLayout(header_rack)

        # --------------------------------------------------
        # OPERATIONAL SUMMARY KPI CARD
        # --------------------------------------------------
        self.kpi_card = QFrame()
        self.kpi_card.setObjectName("glass")  # Attaches light glass styling rules safely
        self.kpi_card.setFixedHeight(75)
        
        kpi_layout = QHBoxLayout(self.kpi_card)
        kpi_layout.setContentsMargins(25, 0, 25, 0)
        
        kpi_title = QLabel("Unassigned Jobs Pending Allocation:")
        kpi_title.setStyleSheet("font-size: 15px; font-weight: bold; color: #555555;")
        
        self.kpi_val = QLabel("0")
        self.kpi_val.setStyleSheet("font-size: 26px; font-weight: 900; color: #E8650A; margin-left: 5px;")
        
        kpi_layout.addWidget(kpi_title)
        kpi_layout.addWidget(self.kpi_val)
        kpi_layout.addStretch()
        master_layout.addWidget(self.kpi_card)

        # Add Search Bar directly above the Central Data Display Runway
        master_layout.addWidget(self.search_bar)

        # --------------------------------------------------
        # CENTRAL DATA DISPLAY RUNWAY
        # --------------------------------------------------
        master_layout.addWidget(self.table)
        
        # Dock Save button prominently at base of table tracking area
        bottom_row = QHBoxLayout()
        bottom_row.addStretch()
        bottom_row.addWidget(save_btn)
        master_layout.addLayout(bottom_row)

        # Populate view matrix elements on startup context routing
        self.refresh()

    def sort_handler(self, logical_index):
        """
        Catches horizontal header clicks to toggle direction or update the active sort column.
        """
        if logical_index not in self.column_map:
            return  # Safety bypass for input/dropdown headers
            
        if logical_index == self.sort_col_idx:
            self.sort_desc = not self.sort_desc  # Toggle sort order on identical column selection
        else:
            self.sort_col_idx = logical_index
            self.sort_desc = False               # Default back to Ascending on clean target selection
            
        self.refresh()

    def _ensure_sorting_hook(self):
        """
        Disables native client-side row sorting and safely attaches our customized 
        relational database sorting handler.
        """
        self.table.setSortingEnabled(False)
        header = self.table.horizontalHeader()
        try:
            header.sectionClicked.disconnect(self.sort_handler)
        except TypeError:
            pass  # Signal wasn't connected yet
        header.sectionClicked.connect(self.sort_handler)

    # ----------------------------
    # LOAD DATA PIPELINE
    # ----------------------------
    def refresh(self):
        try:
            # Clear search filter bar during full records reload context update
            self.search_bar.blockSignals(True)
            self.search_bar.clear()
            self.search_bar.blockSignals(False)

            # --- DYNAMIC STRUCTURAL ORDER BY GENERATOR ---
            col_field = self.column_map.get(self.sort_col_idx, "j.ShipBy")
            # Strip the table alias prefix if it exists, since the CTE flattens the columns
            col_field = col_field.replace("j.", "") 
            direction = "DESC" if self.sort_desc else "ASC"
            
            if col_field == "PalletNumber":
                # Primary clean sort using pre-calculated CleanPallet field from the CTE
                order_by_clause = f"ORDER BY CleanPallet {direction}, JobNumber ASC"
            else:
                # The window function runs against the highly compressed pre-filtered subset
                order_by_clause = f"""
                    ORDER BY 
                        MIN({col_field}) OVER(PARTITION BY CleanPallet) {direction}, 
                        CleanPallet ASC, 
                        JobNumber ASC
                """

            # Isolated CTE dataset that targets unassigned active rows strictly from Today onwards
            sql = f"""
                WITH FilteredUnassignedJobs AS (
                    SELECT
                        LTRIM(RTRIM(j.PalletNumber)) AS CleanPallet,
                        j.PalletNumber, j.JobNumber, j.Diameter, j.Thickness, 
                        j.Length, j.SP, j.APP, j.[DESC], j.ShipBy
                    FROM dbo.JOBLOG j
                    LEFT JOIN dbo.JobEntry_MFGLine m ON m.JobNumber = j.JobNumber
                    WHERE j.Date_Completed IS NULL AND j.Length IS NOT NULL AND j.Length <> ''
                      AND j.ShipBy >= CONVERT(DATE, GETDATE())
                      AND (m.JobNumber IS NULL OR ... [rest of your logic])
                )
                SELECT * FROM FilteredUnassignedJobs {order_by_clause}
            """

            with adhoc_connect() as conn:
                rows = conn.cursor().execute(sql).fetchall()

            self.model.clear()

            headers = [
                "Pallet #", "Job #", "Diameter", "Thickness", "Length", 
                "SP", "APP", "DESC", "ShipBy", # Added to headers
                "Inner Join", "Outer Join", "Inner Sew", "Outer Sew", "Extrusion", "Inspection"
            ]
            self.model.setHorizontalHeaderLabels(headers)

            for row in rows:
                base_values = [
                    row.PalletNumber, row.JobNumber, row.Diameter, row.Thickness, 
                    row.Length, row.SP, row.APP, row.DESC, app_date_text(row.ShipBy)
                ]
                items = [QStandardItem("" if v is None else str(v)) for v in base_values]
                for it in items:
                    it.setEditable(False)

                self.model.appendRow(items + [QStandardItem("") for _ in range(6)])
                r = self.model.rowCount() - 1

                auto_nr = self._is_small_diameter(row.Diameter)

                # Track default drop states dynamically using item user role tracking hooks
                ij_init = "NR" if auto_nr else ""
                oj_init = "NR" if auto_nr else ""
                ext_init = "NR" if auto_nr else ""

                # Anchor the row's baseline allocation state directly onto the JobNumber field item
                items[1].setData([ij_init, oj_init, "", "", ext_init, ""], Qt.ItemDataRole.UserRole)

                self._add_combo(r, 6, JOIN_LINE_OPTIONS, ij_init)
                self._add_combo(r, 7, JOIN_LINE_OPTIONS, oj_init)
                self._add_combo(r, 8, INNER_SEW_OPTIONS, "")
                self._add_combo(r, 9, OUTER_SEW_OPTIONS, "")
                self._add_combo(r, 10, EXTRUSION_OPTIONS, ext_init)
                self._add_combo(r, 11, INSPECTION_OPTIONS, "")

            self.kpi_val.setText(str(len(rows)))
            self._ensure_sorting_hook()

        except Exception as exc:
            QMessageBox.critical(self, APP_TITLE, f"Failed to pull active job allocation states:\n{str(exc)}")

    # ----------------------------
    # WIDGET HANDLERS
    # ----------------------------
    def _add_combo(self, row, col, options, current):
        combo = QComboBox()
        combo.addItems([""] + [str(o) for o in options])
        combo.setCurrentText("" if current is None else str(current))
        combo.setMinimumHeight(28) 
        self.table.setIndexWidget(self.model.index(row, col), combo)

    def _combo_value(self, row, col):
        widget = self.table.indexWidget(self.model.index(row, col))
        if isinstance(widget, QComboBox):
            val = widget.currentText().strip()
            return None if val == "" else val
        return None

    def _is_small_diameter(self, diameter):
        try:
            return float(diameter) < 40
        except Exception:
            return False

    def filter_table(self, filter_text):
        """
        Dynamically filters rows based on text entered into the search bar.
        Matches text content against any baseline metadata data cell column.
        """
        search_term = filter_text.strip().lower()
        for row_idx in range(self.model.rowCount()):
            if not search_term:
                self.table.setRowHidden(row_idx, False)
                continue

            match_found = False
            # Check descriptive baseline matrix columns (Pallet, Job, Dia, Thick, Len, SPAPP, DESC, ShipBy)
            for col_idx in range(9): 
                item = self.model.item(row_idx, col_idx)
                if item and search_term in item.text().lower():
                    match_found = True
                    break
            
            self.table.setRowHidden(row_idx, not match_found)

    # ----------------------------
    # TRANSACTION PERSISTENCE
    # ----------------------------
    def save(self):
        try:
            # --- MODIFIED: NR now returns 999 ---
            def to_numeric_allocation(val):
                if val == "NR":
                    return 999  # Updated from 0 to 999
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

                    # Extract current UI configurations
                    ij  = self._combo_value(row, 6)
                    oj  = self._combo_value(row, 7)
                    isw = self._combo_value(row, 8)
                    osw = self._combo_value(row, 9)
                    ext = self._combo_value(row, 10)
                    ins = self._combo_value(row, 11)

                    # Safely extract initial drop configs from baseline user state storage roles
                    initial_states = job_item.data(Qt.ItemDataRole.UserRole) or ["", "", "", "", "", ""]
                    current_states = [ij or "", oj or "", isw or "", osw or "", ext or "", ins or ""]

                    # Only compile queries if there is a divergence from the initial data setup
                    if current_states == initial_states:
                        continue

                    # Parse verified values to database equivalents
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
                            INSERT (JobNumber, InnerJoinMFG, OuterJoinMFG, InnerSewMFG, OuterSewMFG, ExtrusionMFG, InspectionMFG)
                            VALUES (source.JobNumber, ?, ?, ?, ?, ?, ?);
                        """,
                        job_number,
                        db_ij, db_oj, db_isw, db_osw, db_ext, db_ins,
                        db_ij, db_oj, db_isw, db_osw, db_ext, db_ins
                    )
                    change_count += 1

                if change_count > 0:
                    conn.commit()
                    QMessageBox.information(self, APP_TITLE, f"Successfully saved mappings for {change_count} changed job record(s).")
                else:
                    QMessageBox.information(self, APP_TITLE, "No allocations modified; database commit skipped.")
                
            self.refresh()

        except Exception as e:
            QMessageBox.critical(self, "Transaction Failure", f"Failed to persist batch layout mappings:\n{str(e)}")