from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QFrame,
    QAbstractItemView
)
from PyQt6.QtCore import Qt
from database import adhoc_connect
from config import APP_TITLE
from widgets.table_panel import TablePanel
from helpers import app_date_text
from constants import shipped_special_apps_filter
from ui_components import add_header_row, add_session_row, action_button

class AssignedLinePage(QWidget):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.setObjectName("root")

        # --- Interactive Control Elements ---
        refresh_btn = action_button("Refresh Data", self.refresh)
        home_btn = action_button("Home Menu", lambda: self.app.navigate("Home"))

        # --- Master Layout Assembly ---
        master_layout = QVBoxLayout(self)
        master_layout.setContentsMargins(24, 24, 24, 24)
        master_layout.setSpacing(20)

        add_session_row(master_layout, self.app)
        add_header_row(master_layout, "Assigned Production Tracking", refresh_btn, home_btn)

        # --- OPERATIONAL SUMMARY KPI CARD ---
        self.kpi_card = QFrame()
        self.kpi_card.setObjectName("glass")
        self.kpi_card.setFixedHeight(75)
        kpi_layout = QHBoxLayout(self.kpi_card)
        kpi_layout.setContentsMargins(25, 0, 25, 0)
        kpi_title = QLabel("Total Active Assigned Jobs:")
        kpi_title.setStyleSheet("font-size: 15px; font-weight: bold; color: #555555;")
        self.kpi_val = QLabel("0")
        self.kpi_val.setStyleSheet("font-size: 26px; font-weight: 900; color: #E8650A; margin-left: 5px;")
        kpi_layout.addWidget(kpi_title)
        kpi_layout.addWidget(self.kpi_val)
        kpi_layout.addStretch()
        master_layout.addWidget(self.kpi_card)

        # --- CENTRAL DATA PRESENTATION ---
        self.panel = TablePanel("View/Update Assigned Production Lines")
        master_layout.addWidget(self.panel)
        
        self.refresh()

    def refresh(self):
        try:
            # The filter logic has been added to the WHERE clause to exclude 
            # rows where specific columns are NULL, empty, or 0.
            sql = f"""
                SELECT j.PalletNumber, j.JobNumber, j.Customer, j.Diameter, j.Thickness, 
                       j.Length, j.ShipBy, m.InnerJoinMFG, m.OuterJoinMFG, 
                       m.InnerSewMFG, m.OuterSewMFG, m.ExtrusionMFG, m.InspectionMFG
                FROM dbo.vw_JOBLOG_Open j
                INNER JOIN dbo.JobEntry_MFGLine m ON j.JobNumber = m.JobNumber
                WHERE j.Length IS NOT NULL AND j.Length <> ''
                AND j.ShipBy >= DATEADD(week, DATEDIFF(week, 0, GETDATE()), 0)
                AND {shipped_special_apps_filter("j.JobNumber")}
                -- Only show jobs where these 3 columns are fully filled (Not Null, Not Empty, Not 0)
                AND (m.InnerSewMFG IS NOT NULL AND m.InnerSewMFG <> '' AND m.InnerSewMFG <> 0)
                AND (m.OuterSewMFG IS NOT NULL AND m.OuterSewMFG <> '' AND m.OuterSewMFG <> 0)
                AND (m.InspectionMFG IS NOT NULL AND m.InspectionMFG <> '' AND m.InspectionMFG <> 0)
                ORDER BY j.PalletNumber, j.JobNumber
            """
            with adhoc_connect() as conn:
                rows = conn.cursor().execute(sql).fetchall()

            headers = ["Pallet #", "Job #", "Customer", "Diameter", "Thickness", 
                       "Length", "ShipBy", "Inner Join", "Outer Join", 
                       "Inner Sew", "Outer Sew", "Extrusion", "Inspection"]

            processed_rows = []
            for row in rows:
                def format_val(val):
                    # Keep mapping 999 to "NR"
                    if val in [999, "999"]: 
                        return "NR"
                    return "" if val in [0, "0", None, ""] else str(val)

                processed_rows.append([
                    row.PalletNumber, row.JobNumber, row.Customer, row.Diameter,
                    row.Thickness, row.Length, app_date_text(row.ShipBy),
                    format_val(row.InnerJoinMFG), format_val(row.OuterJoinMFG),
                    format_val(row.InnerSewMFG), format_val(row.OuterSewMFG),
                    format_val(row.ExtrusionMFG), format_val(row.InspectionMFG)
                ])

            self.panel.set_rows(headers, processed_rows)
            self.kpi_val.setText(str(len(rows)))

            # Enable editing for columns 7 through 12
            view = getattr(self.panel, "table", None) or getattr(self.panel, "table_view", None)
            model = view.model()
            source_model = model.sourceModel() if hasattr(model, "sourceModel") else model
            
            for row in range(source_model.rowCount()):
                for col in range(7, 13):
                    item = source_model.item(row, col)
                    if item:
                        item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable)

            try: source_model.itemChanged.disconnect(self.handle_item_changed)
            except: pass
            source_model.itemChanged.connect(self.handle_item_changed)

        except Exception as exc:
            QMessageBox.critical(self, APP_TITLE, f"Failed to sync data:\n{str(exc)}")

    def handle_item_changed(self, item):
        try:
            row = item.row()
            col = item.column()
            model = item.model()
            source_model = model.sourceModel() if hasattr(model, "sourceModel") else model
            job_number = source_model.item(row, 1).text()
            
            val = item.text().strip()

            # --- UPDATED LOGIC ---
            # 1. Determine the value to save
            if val.upper() == "NR":
                save_val = 999
            elif val == "":
                save_val = None # This will set the DB to NULL
            else:
                save_val = val

            column_map = {
                7: "InnerJoinMFG", 8: "OuterJoinMFG", 9: "InnerSewMFG",
                10: "OuterSewMFG", 11: "ExtrusionMFG", 12: "InspectionMFG"
            }
            column_name = column_map.get(col)

            if column_name:
                with adhoc_connect() as conn:
                    conn.cursor().execute(
                        f"UPDATE dbo.JobEntry_MFGLine SET {column_name} = ? WHERE JobNumber = ?",
                        (save_val, job_number)
                    )
                    conn.commit()
                    
        except Exception as exc:
            QMessageBox.critical(self, APP_TITLE, f"Failed to save update:\n{str(exc)}")
