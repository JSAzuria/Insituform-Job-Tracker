# pages/update_location_page.py

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLineEdit,
    QComboBox,
    QMessageBox,
    QLabel,
    QPushButton,
    QFrame
)
from PyQt6.QtCore import Qt
from database import adhoc_connect
from config import APP_TITLE
from helpers import as_int_or_none
from constants import PROCESS_OPTIONS

class UpdateLocationPage(QWidget):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.setObjectName("root")

        # --- Initialize Form Inputs ---
        self.job_input = QLineEdit()
        self.job_input.setPlaceholderText("Scan or Enter Job #")
        self.job_input.setClearButtonEnabled(True)
        self.job_input.setMinimumHeight(38)
        
        # Connect returnPressed event to streamline shop floor barcode scanning sequences
        self.job_input.returnPressed.connect(self.save)
        
        # Standardized production line selection configuration
        self.line_selector = QComboBox()
        self.line_selector.addItems([
            "Slitter 1", "Slitter 2", "Slitter 3", "4", "5",
            "6", "7", "9", "10", "11",
            "12", "13", "14", "15", "17",
            "Special Apps"
        ])
        self.line_selector.setMinimumHeight(38)

        self.process = QComboBox()
        self.process.addItems(PROCESS_OPTIONS)
        self.process.setMinimumHeight(38)

        self.status = QComboBox()
        self.status.addItems(["On Line", "Complete"])
        self.status.setMinimumHeight(38)

        # --- Action Buttons ---
        save_btn = QPushButton("Save Transaction")
        save_btn.setMinimumHeight(45)
        save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        save_btn.clicked.connect(self.save)
        
        home_btn = QPushButton("Home Menu")
        home_btn.setMinimumHeight(40)
        home_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        home_btn.clicked.connect(lambda: self.app.navigate("Home"))

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
        
        page_title = QLabel("Tracking & Location Manager")
        page_title.setObjectName("sectionTitle")
        page_title.setStyleSheet("font-size: 22px; font-weight: 800;")
        
        header_rack.addWidget(page_title)
        header_rack.addStretch()
        header_rack.addWidget(home_btn)
        master_layout.addLayout(header_rack)

        # --------------------------------------------------
        # CENTERED FORM CARD PANEL (Flat Glass Card)
        # --------------------------------------------------
        master_layout.addStretch(1)

        card = QFrame()
        card.setObjectName("glass")
        card.setFixedWidth(500)
        
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(15)
        card_layout.setContentsMargins(35, 35, 35, 35)

        # Form Card Title
        form_title = QLabel("Update Job Log Status")
        form_title.setStyleSheet("font-size: 18px; font-weight: bold; color: #333333; margin-bottom: 5px;")
        card_layout.addWidget(form_title)

        # Job Number Field
        job_label = QLabel("Job Number / Barcode Scan")
        job_label.setStyleSheet("font-weight: bold; color: #555555; font-size: 13px;")
        card_layout.addWidget(job_label)
        card_layout.addWidget(self.job_input)

        # Line Selector Field
        line_label = QLabel("Production Line Allocation")
        line_label.setStyleSheet("font-weight: bold; color: #555555; font-size: 13px;")
        card_layout.addWidget(line_label)
        card_layout.addWidget(self.line_selector)

        # Operation Field
        op_label = QLabel("Current Operation Step")
        op_label.setStyleSheet("font-weight: bold; color: #555555; font-size: 13px;")
        card_layout.addWidget(op_label)
        card_layout.addWidget(self.process)

        # Status Field
        status_label = QLabel("Tracking Status Flag")
        status_label.setStyleSheet("font-weight: bold; color: #555555; font-size: 13px;")
        card_layout.addWidget(status_label)
        card_layout.addWidget(self.status)

        # Add explicit padding spacing before main confirmation button
        card_layout.addSpacing(10)
        card_layout.addWidget(save_btn)

        # Center the card layout panel horizontally inside the outer window layout
        center_row = QHBoxLayout()
        center_row.addStretch()
        center_row.addWidget(card)
        center_row.addStretch()
        
        master_layout.addLayout(center_row)
        master_layout.addStretch(2)

        # Direct operator cursor default behavior to the entry line immediately
        self.job_input.setFocus()

    def showEvent(self, event):
        """Overrides built-in PyQt view transitions to enforce hardware focus on entry."""
        super().showEvent(event)
        self.job_input.clear()
        self.job_input.setFocus()

    def save(self):
        raw_job_text = self.job_input.text().strip()
        line = self.line_selector.currentText()  
        event_type = self.status.currentText()

        # 1. Field validation constraints
        if not raw_job_text:
            QMessageBox.warning(self, APP_TITLE, "Job Number field cannot be empty. Please scan or enter a value.")
            self.job_input.setFocus()
            return

        if not line:
            QMessageBox.warning(self, APP_TITLE, "Production Line selection is required.")
            self.line_selector.setFocus()
            return

        # 2. Check if text is a valid integer format
        job_number = as_int_or_none(raw_job_text)
        if job_number is None:
            QMessageBox.warning(
                self, 
                APP_TITLE, 
                f"Invalid format: '{raw_job_text}' is not a valid numeric Job Number.\n"
                "Please verify the scan layout data and try again."
            )
            self.job_input.selectAll()
            self.job_input.setFocus()
            return

        # 3. Processing and Database Execution Runtime Subsystem
        try:
            with adhoc_connect() as conn:
                cur = conn.cursor()
                
                # Verify that the core job reference exists
                job_exists = cur.execute(
                    "SELECT 1 FROM dbo.JOBLOG WHERE JobNumber = ?", job_number
                ).fetchone()

                if not job_exists:
                    QMessageBox.warning(
                        self, 
                        APP_TITLE, 
                        f"Job Number {job_number} not found.\n\n"
                        "This record does not exist within the central database log tracking registry."
                    )
                    self.job_input.selectAll()
                    self.job_input.setFocus()
                    return

                # Record background transition event entry
                cur.execute(
                    """
                    INSERT INTO dbo.JobTracking (
                        OperatorName, JobNumber, Line, Operation, EventType, EventTime
                    )
                    VALUES (?, ?, ?, ?, ?, GETDATE())
                    """,
                    self.app.operator.FullName if self.app.operator else "Unknown",
                    job_number, line, self.process.currentText(), event_type
                )

                # Conditionally flag final completed timestamp mapping block variables
                if event_type == "Complete":
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
                APP_TITLE,
                f"A database connection or query exception occurred:\n\n{str(err)}"
            )
            self.job_input.selectAll()
            self.job_input.setFocus()
            return

        # Explicit UI alert signaling operation complete
        QMessageBox.information(self, APP_TITLE, f"Job {job_number} successfully marked as '{event_type}'.")
        
        # Clear scan strings and reset component focus states back to top for continuous scanning runs
        self.job_input.clear()
        self.job_input.setFocus()