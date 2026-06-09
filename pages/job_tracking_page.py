# pages/job_tracking_page.py

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
from constants import TRACKING_PROCESS_OPTIONS
from helpers import as_int_or_none

class JobTrackingPage(QWidget):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.setObjectName("root")

        # Define the complete list of manufacturing lines
        self.ALL_LINES = [
            "Slitter 1", "Slitter 2", "Slitter 3", "4", "5",
            "6", "7", "9", "10", "11", "12", "13", "14", "15", "17", "Special Apps"
        ]

        # --- Core Inputs & Action Controls ---
        self.job = QLineEdit()
        self.job.setPlaceholderText("Scan or enter Job #")
        self.job.setMinimumHeight(42)
        
        self.line = QComboBox()
        self.line.setMinimumHeight(42)
        
        self.operation = QComboBox()
        self.operation.setMinimumHeight(42)

        # Guard flag to prevent infinite loops during reciprocal cross-filtering updates
        self._is_updating = False

        # Initialize both drop-downs with all available floor options
        self.reset_dropdowns_to_all()

        # Connect mutual cross-filtering listeners
        self.operation.currentTextChanged.connect(self.on_operation_changed)
        self.line.currentTextChanged.connect(self.on_line_changed)

        # Process Operations Control Stack
        start_btn = QPushButton("Start Job Process")
        start_btn.setProperty("accent", True)  # Adopts dynamic green/orange branding
        start_btn.setMinimumHeight(46)
        start_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        start_btn.clicked.connect(lambda: self.save_event("Active"))
        
        stop_btn = QPushButton("Stop / Complete")
        stop_btn.setMinimumHeight(46)
        stop_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        stop_btn.clicked.connect(lambda: self.save_event("Complete"))

        home_btn = QPushButton("Home Menu")
        home_btn.setMinimumHeight(40)
        home_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        home_btn.clicked.connect(lambda: self.app.navigate("Home"))

        # --- Master Layout Assembly ---
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 24, 24, 24)
        main_layout.setSpacing(20)

        # --------------------------------------------------
        # TOP ROW: CONTEXTUAL USER SESSION BANNER (RIGHT-ALIGNED)
        # --------------------------------------------------
        top_bar = QHBoxLayout()

        # Orange Session Framework Container (Anchored Top-Right)
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

        op_name = "Operator"
        if self.app.operator and hasattr(self.app.operator, "FullName"):
            op_name = self.app.operator.FullName

        user_label = QLabel(f"Logged in as: {op_name}")
        
        logout_btn = QPushButton("Logout")
        logout_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        logout_btn.clicked.connect(lambda: self.app.navigate("Logout"))

        session_layout.addWidget(user_label)
        session_layout.addWidget(logout_btn)
        
        top_bar.addStretch()
        top_bar.addWidget(session_frame)
        main_layout.addLayout(top_bar)

        # --------------------------------------------------
        # HEADER CONTROL RACK (Title & Global Actions)
        # --------------------------------------------------
        header_rack = QHBoxLayout()
        
        page_title = QLabel("Floor Operations Tracking")
        page_title.setObjectName("sectionTitle")
        page_title.setStyleSheet("font-size: 22px; font-weight: 800;")
        
        header_rack.addWidget(page_title)
        header_rack.addStretch()
        header_rack.addWidget(home_btn)
        main_layout.addLayout(header_rack)

        # --------------------------------------------------
        # CENTER CARD: SYSTEM INTERACTIVE PORTAL HUB
        # --------------------------------------------------
        main_layout.addStretch(1)

        # Form card container ensures crisp presentation constraints across wide layouts
        tracking_card = QFrame()
        tracking_card.setObjectName("glass")  # Light flat background overlay hook
        tracking_card.setMinimumWidth(500)
        tracking_card.setMaximumWidth(600)

        card_layout = QVBoxLayout(tracking_card)
        card_layout.setContentsMargins(40, 35, 40, 40)
        card_layout.setSpacing(18)

        title_label = QLabel("Scan Station Entry")
        title_label.setStyleSheet("font-size: 20px; font-weight: 800; color: #E8650A; padding-bottom: 5px;")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(title_label)

        # Standardizing Label Fields (Vertical Structure Stack)
        job_lbl = QLabel("Job Number")
        job_lbl.setStyleSheet("font-weight: bold; color: #555555; font-size: 13px; margin-top: 5px;")
        card_layout.addWidget(job_lbl)
        card_layout.addWidget(self.job)

        line_lbl = QLabel("Manufacturing Line / Station")
        line_lbl.setStyleSheet("font-weight: bold; color: #555555; font-size: 13px; margin-top: 5px;")
        card_layout.addWidget(line_lbl)
        card_layout.addWidget(self.line)

        op_lbl = QLabel("Active Operation Stage")
        op_lbl.setStyleSheet("font-weight: bold; color: #555555; font-size: 13px; margin-top: 5px;")
        card_layout.addWidget(op_lbl)
        card_layout.addWidget(self.operation)

        # Execution Command Runway Layout
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(15)
        btn_layout.setContentsMargins(0, 10, 0, 0)
        btn_layout.addWidget(start_btn, stretch=1)
        btn_layout.addWidget(stop_btn, stretch=1)
        card_layout.addLayout(btn_layout)

        # Center the control module card frame horizontally
        center_binder = QHBoxLayout()
        center_binder.addStretch(1)
        center_binder.addWidget(tracking_card)
        center_binder.addStretch(1)

        main_layout.addLayout(center_binder)
        main_layout.addStretch(2)

    def reset_dropdowns_to_all(self):
        """Helper to reset both combo boxes to full default sets with blank headers."""
        self._is_updating = True
        
        self.operation.clear()
        self.operation.addItems([""] + TRACKING_PROCESS_OPTIONS)
        
        self.line.clear()
        self.line.addItems([""] + self.ALL_LINES)
        
        self.operation.setCurrentIndex(0)
        self.line.setCurrentIndex(0)
        
        self._is_updating = False

    def get_allowed_lines(self, operation_text):
        """Returns the specific manufacturing line restrictions for a given process step."""
        op = operation_text.strip().lower()
        if not op:
            return self.ALL_LINES
        
        if "slit" in op:
            return ["Slitter 1", "Slitter 2", "Slitter 3"]
        elif "join" in op:
            return ["13", "14", "15", "17"]
        elif "sew" in op:
            return ["4", "5", "6", "7", "9", "10", "11", "13", "14", "15"]
        elif "extrusion" in op:
            return ["1", "3", "12", "14", "15"]
        elif "inspection" in op:
            return ["1", "2", "12", "14", "15"]
        elif "special" in op:
            return ["Special Apps"]
        return self.ALL_LINES

    def get_allowed_operations(self, line_text):
        """Inversely calculates which process steps are allowed on a chosen line."""
        line = line_text.strip()
        if not line:
            return TRACKING_PROCESS_OPTIONS
        
        return [op for op in TRACKING_PROCESS_OPTIONS if line in self.get_allowed_lines(op)]

    def on_operation_changed(self, op_text):
        """Fires when the operation choice changes to filter available lines."""
        if self._is_updating:
            return
        self._is_updating = True

        current_line = self.line.currentText()

        if op_text == "":
            if current_line != "":
                allowed_ops = self.get_allowed_operations(current_line)
                self.operation.clear()
                self.operation.addItems([""] + allowed_ops)
                self.operation.setCurrentText("")
                
                self.line.clear()
                self.line.addItems([""] + self.ALL_LINES)
                self.line.setCurrentText(current_line)
            else:
                self.line.clear()
                self.line.addItems([""] + self.ALL_LINES)
                self.line.setCurrentText("")
        else:
            allowed_lines = self.get_allowed_lines(op_text)
            self.line.clear()
            self.line.addItems([""] + allowed_lines)
            
            if current_line in allowed_lines:
                self.line.setCurrentText(current_line)
            else:
                self.line.setCurrentText("")

        self._is_updating = False

    def on_line_changed(self, line_text):
        """Fires when the line choice changes to filter available operations."""
        if self._is_updating:
            return
        self._is_updating = True

        current_op = self.operation.currentText()

        if line_text == "":
            if current_op != "":
                allowed_lines = self.get_allowed_lines(current_op)
                self.line.clear()
                self.line.addItems([""] + allowed_lines)
                self.line.setCurrentText("")
                
                self.operation.clear()
                self.operation.addItems([""] + TRACKING_PROCESS_OPTIONS)
                self.operation.setCurrentText(current_op)
            else:
                self.operation.clear()
                self.operation.addItems([""] + TRACKING_PROCESS_OPTIONS)
                self.operation.setCurrentText("")
        else:
            allowed_ops = self.get_allowed_operations(line_text)
            self.operation.clear()
            self.operation.addItems([""] + allowed_ops)
            
            if current_op in allowed_ops:
                self.operation.setCurrentText(current_op)
            else:
                self.operation.setCurrentText("")

        self._is_updating = False

    def save_event(self, event_type):
        job_number = as_int_or_none(self.job.text().strip())
        line = self.line.currentText().strip()
        operation = self.operation.currentText().strip()
        
        if not job_number or not line or not operation:
            QMessageBox.warning(self, APP_TITLE, "Job #, Line, and Operation are all required fields.")
            return

        try:
            with adhoc_connect() as conn:
                cur = conn.cursor()
                
                job_check = cur.execute(
                    "SELECT 1 FROM dbo.JOBLOG WHERE JobNumber = ?", 
                    job_number
                ).fetchone()
                
                if not job_check:
                    QMessageBox.warning(
                        self, 
                        APP_TITLE, 
                        f"Warning: Job #{job_number} does not exist in the master database log. Process aborted."
                    )
                    return

                dup = cur.execute(
                    """
                    SELECT TOP 1 EventType FROM dbo.JobTracking
                    WHERE JobNumber = ? AND Operation = ? AND Line = ?
                    ORDER BY EventTime DESC
                    """, job_number, operation, line
                ).fetchone()

                if dup and dup.EventType == event_type:
                    QMessageBox.warning(self, APP_TITLE, "Duplicate event ignored.")
                    return

                cur.execute(
                    """
                    INSERT INTO dbo.JobTracking (OperatorName, JobNumber, Line, Operation, EventType, EventTime)
                    VALUES (?, ?, ?, ?, ?, GETDATE())
                    """,
                    self.app.operator.FullName if self.app.operator else "Unknown",
                    job_number, line, operation, event_type
                )

                if event_type == "Complete":
                    cur.execute(
                        """
                        UPDATE dbo.JOBLOG
                        SET Date_Completed = CAST(GETDATE() AS date)
                        WHERE JobNumber = ? AND Date_Completed IS NULL
                        """, job_number
                    )
                conn.commit()

            QMessageBox.information(self, APP_TITLE, f"Job marked {event_type}.")
            
            self.job.clear()
            self.reset_dropdowns_to_all()
                
        except Exception as exc:
            QMessageBox.critical(self, APP_TITLE, str(exc))