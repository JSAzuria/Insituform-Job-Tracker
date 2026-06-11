# pages/menu_page.py

from PyQt6.QtWidgets import (
    QWidget, 
    QGridLayout, 
    QVBoxLayout, 
    QHBoxLayout, 
    QFrame, 
    QLabel
)
from PyQt6.QtCore import Qt
from config import APP_TITLE
from ui_components import add_session_row, action_button


class MenuPage(QWidget):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.setObjectName("root")

        # --- Master Layout Assembly ---
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 24, 24, 24)
        main_layout.setSpacing(20)

        add_session_row(main_layout, self.app)

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
            btn = action_button(name, lambda _, n=name: self.app.navigate(n), height=50)
            btn.setObjectName("menu_navigation_button")  # Stylesheet target hook
            
            row = i // 2
            col = i % 2
            self.grid.addWidget(btn, row, col)
