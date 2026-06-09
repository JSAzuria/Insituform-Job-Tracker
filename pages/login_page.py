# pages/login_page.py

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLineEdit,
    QMessageBox,
    QLabel,
    QPushButton,
    QFrame
)
from PyQt6.QtCore import Qt
from database import adhoc_connect
from config import APP_TITLE

class LoginPage(QWidget):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.setObjectName("root")

        # --- Initialize Inputs & Buttons ---
        self.badge = QLineEdit()
        self.badge.setPlaceholderText("Scan barcode or enter Operator ID...")
        self.badge.setMinimumHeight(42)
        self.badge.setClearButtonEnabled(True)

        submit = QPushButton("Log In / Submit")
        submit.setMinimumHeight(45)
        submit.setCursor(Qt.CursorShape.PointingHandCursor)
        
        # Wire events
        submit.clicked.connect(self.login)
        self.badge.returnPressed.connect(self.login)

        # --- Centered Card Panel Container ---
        card = QFrame()
        card.setObjectName("glass")  # Fits flat transparent label standards cleanly
        card.setFixedWidth(420)     # Locked width for consistent layout across screen models
        
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(15)
        card_layout.setContentsMargins(35, 40, 35, 40)

        # 1. Header Logo Block
        if hasattr(self.app, 'get_logo_widget'):
            logo_widget = self.app.get_logo_widget()
            card_layout.addWidget(logo_widget, alignment=Qt.AlignmentFlag.AlignCenter)
            card_layout.addSpacing(10)
        else:
            app_title_label = QLabel("INSITUFORM")
            app_title_label.setStyleSheet("font-size: 24px; font-weight: 900; color: #E8650A; letter-spacing: 1px;")
            card_layout.addWidget(app_title_label, alignment=Qt.AlignmentFlag.AlignCenter)

        # 2. Section Descriptive Title
        scan_title = QLabel("Operator Portal Access")
        scan_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #333333;")
        card_layout.addWidget(scan_title, alignment=Qt.AlignmentFlag.AlignCenter)

        # 3. Input Label & Field Assembly
        badge_label = QLabel("Operator ID / Badge Code")
        badge_label.setStyleSheet("font-weight: bold; color: #555555; font-size: 13px; margin-top: 5px;")
        card_layout.addWidget(badge_label)
        card_layout.addWidget(self.badge)

        card_layout.addSpacing(10)
        card_layout.addWidget(submit)

        # --- Master Centering Layout Assembly ---
        master_layout = QVBoxLayout(self)
        master_layout.setContentsMargins(24, 24, 24, 24)

        center_row = QHBoxLayout()
        center_row.addStretch()
        center_row.addWidget(card)
        center_row.addStretch()

        master_layout.addStretch()
        master_layout.addLayout(center_row)
        master_layout.addStretch()

        # Set default focus to input box for immediate badge scanner reads
        self.badge.setFocus()

    def showEvent(self, event):
        """Overrides built-in PyQt view events to capture focus whenever page switches on screen."""
        super().showEvent(event)
        self.badge.clear()
        self.badge.setFocus()

    def login(self):
        operator_id = self.badge.text().strip()
        if not operator_id:
            QMessageBox.warning(self, APP_TITLE, "Operator ID entry criteria is required to proceed.")
            self.badge.setFocus()
            return

        try:
            with adhoc_connect() as conn:
                row = conn.cursor().execute(
                    """
                    SELECT TOP 1 OperatorID, FullName, Department, Shift, Role, IsActive
                    FROM dbo.Operators
                    WHERE OperatorID = ? AND ISNULL(IsActive, 1) = 1
                    """,
                    operator_id,
                ).fetchone()

        except Exception as exc:
            QMessageBox.critical(self, APP_TITLE, f"Database Login Connection Failure:\n{str(exc)}")
            self.badge.selectAll()
            self.badge.setFocus()
            return

        if not row:
            QMessageBox.warning(self, APP_TITLE, "Invalid or inactive Operator ID. Verify credentials and try again.")
            self.badge.selectAll()
            self.badge.setFocus()
            return

        # Store structural row array and change app viewport context
        self.app.operator = row
        self.app.show_role_home()