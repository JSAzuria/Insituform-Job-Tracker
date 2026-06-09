# pages/menu_page.py

from PyQt6.QtWidgets import (
    QWidget, 
    QGridLayout, 
    QVBoxLayout, 
    QHBoxLayout, 
    QFrame, 
    QLabel, 
    QPushButton
)
from PyQt6.QtCore import Qt
from config import APP_TITLE


class MenuPage(QWidget):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.setObjectName("root")

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

        # Safely capture signed-in routing states
        op_name = "Operator"
        if self.app.operator and hasattr(self.app.operator, "FullName"):
            op_name = self.app.operator.FullName

        user_label = QLabel(f"Logged in as: {op_name}")
        
        logout_btn = QPushButton("Logout")
        logout_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        logout_btn.clicked.connect(lambda: self.app.navigate("Logout"))

        # Add session container components
        session_layout.addWidget(user_label)
        session_layout.addWidget(logout_btn)
        
        # Position banner cleanly along the right margin
        top_bar.addStretch()
        top_bar.addWidget(session_frame)
        main_layout.addLayout(top_bar)

        # --------------------------------------------------
        # CENTER CARD: SYSTEM INTERACTIVE PORTAL HUB
        # --------------------------------------------------
        main_layout.addStretch(1)

        # Main interactive card module
        menu_card = QFrame()
        menu_card.setObjectName("glass")  # Standard flat transparent style sheet hook
        menu_card.setMinimumWidth(500)
        menu_card.setMaximumWidth(650)

        card_layout = QVBoxLayout(menu_card)
        card_layout.setContentsMargins(40, 35, 40, 40)
        card_layout.setSpacing(25)

        title_label = QLabel(APP_TITLE)
        title_label.setObjectName("menuMainTitle")
        title_label.setStyleSheet("font-size: 24px; font-weight: 900; color: #333333;")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(title_label)

        # Navigation Options Distribution Matrix
        self.grid = QGridLayout()
        self.grid.setSpacing(16)
        card_layout.addLayout(self.grid)

        # Center the control module card frame horizontally
        center_binder = QHBoxLayout()
        center_binder.addStretch(1)
        center_binder.addWidget(menu_card)
        center_binder.addStretch(1)

        main_layout.addLayout(center_binder)
        main_layout.addStretch(2)

        # Populate action options roster
        self.refresh()

    def refresh(self):
        """
        Dynamically fetches accessible system paths based on permission 
        routing matrix boundaries and maps choices cleanly into a two-column layout.
        """
        # Safely flush stale grid elements on view updates
        while self.grid.count():
            item = self.grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        pages = self.app.available_pages()

        # Mount target entries systematically across a 2-column grid distribution block
        for i, name in enumerate(pages):
            btn = QPushButton(name)
            btn.setObjectName("menu_navigation_button")  # Stylesheet target hook
            btn.setMinimumHeight(48)                      # Robust clickable footprint on shop terminals
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            
            # Safely capture variable scope states at evaluation execution phase
            btn.clicked.connect(lambda _, n=name: self.app.navigate(n))
            
            row = i // 2
            col = i % 2
            self.grid.addWidget(btn, row, col)