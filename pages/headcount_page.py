from PyQt6.QtWidgets import (
    QWidget, 
    QVBoxLayout, 
    QHBoxLayout, 
    QLabel, 
    QMessageBox,
    QFrame,
    QAbstractItemView,
    QComboBox
)
from PyQt6.QtCore import Qt
from widgets.table_panel import TablePanel
from database import adhoc_connect
from config import APP_TITLE
from ui_components import add_header_row, add_session_row, action_button

class HeadcountPage(QWidget):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.setObjectName("root")

        self.panel = TablePanel("Current Headcount")
        
        # Configure Table behavior
        if hasattr(self.panel, "table"):
            self.panel.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
            self.panel.table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
            self.panel.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        elif hasattr(self.panel, "table_view"):
            self.panel.table_view.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
            self.panel.table_view.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
            self.panel.table_view.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        # --- UI ELEMENTS ---
        self.shift_filter = QComboBox()
        self.shift_filter.addItems(["All", "1", "2", "3"])
        self.shift_filter.setMinimumHeight(30)
        self.shift_filter.currentIndexChanged.connect(self.refresh)

        refresh_btn = action_button("Refresh Data", self.refresh)
        home_btn = action_button("Home Menu", lambda: self.app.navigate("Home"))

        # --- LAYOUTS ---
        master_layout = QVBoxLayout(self)
        master_layout.setContentsMargins(24, 24, 24, 24)
        master_layout.setSpacing(20)

        add_session_row(master_layout, self.app)
        add_header_row(master_layout, "Personnel Roster Management", refresh_btn, home_btn)

        # --- KPI CARD ---
        self.kpi_card = QFrame()
        self.kpi_card.setObjectName("glass")
        self.kpi_card.setFixedHeight(85)
        kpi_layout = QHBoxLayout(self.kpi_card)
        kpi_layout.setContentsMargins(25, 0, 25, 0)
        kpi_layout.setSpacing(20)
        
        self.counter_label = QLabel("Total: --")
        self.budget_label = QLabel("Sewing Budget: --")
        self.small_label = QLabel("Small: --")
        self.large_label = QLabel("Large: --")
        self.slitter_label = QLabel("Slitter: --")
        
        # Add metric widgets to KPI
        labels = [self.counter_label, self.budget_label, self.small_label, self.large_label, self.slitter_label]
        for lbl in labels:
            lbl.setStyleSheet("font-size: 14px; font-weight: bold; color: #555555;")
            kpi_layout.addWidget(lbl)
            # Add divider
            div = QFrame(); div.setFrameShape(QFrame.Shape.VLine); div.setStyleSheet("color: #cccccc;")
            kpi_layout.addWidget(div)
        
        # Add Shift Filter to KPI box on the right
        kpi_layout.addStretch() # Pushes everything after this to the right
        kpi_layout.addWidget(QLabel("Filter Shift:"))
        kpi_layout.addWidget(self.shift_filter)
        
        master_layout.addWidget(self.kpi_card)
        master_layout.addWidget(self.panel, stretch=1)
        
        self.refresh()

    def refresh(self):
        try:
            shift_val = self.shift_filter.currentText()
            sql = "SELECT OperatorID, FullName, Department, Shift, Role, IsActive FROM dbo.Operators WHERE IsActive = 1"
            params = []
            
            if shift_val != "All":
                sql += " AND Shift = ?"
                params.append(shift_val)
            
            sql += " ORDER BY Department ASC, FullName ASC"

            with adhoc_connect() as conn:
                rows = conn.cursor().execute(sql, params).fetchall()

            self.panel.set_rows(["Badge #", "Full Name", "Department", "Shift", "Role", "Is Active"], rows)

            # Calculations
            small_count   = sum(1 for r in rows if "small"   in str(r[2] or "").lower())
            large_count   = sum(1 for r in rows if "large"   in str(r[2] or "").lower())
            slitter_count = sum(1 for r in rows if "slitter" in str(r[2] or "").lower())
            
            total_sewing_budget = small_count + large_count + slitter_count
            total_active  = len(rows)

            # Update Labels
            orange = "#E8650A"
            num_style = f"color: {orange}; font-weight: 900; font-size: 20px; margin-left: 4px;"
            
            self.counter_label.setText(f"Total: <span style='{num_style}'>{total_active}</span>")
            self.budget_label.setText(f"Sewing Budget: <span style='{num_style}'>{total_sewing_budget}</span>")
            self.small_label.setText(f"Small: <span style='{num_style}'>{small_count}</span>")
            self.large_label.setText(f"Large: <span style='{num_style}'>{large_count}</span>")
            self.slitter_label.setText(f"Slitter: <span style='{num_style}'>{slitter_count}</span>")

        except Exception as e:
            QMessageBox.critical(self, APP_TITLE, f"Failed to fetch updated roster data:\n{str(e)}")
