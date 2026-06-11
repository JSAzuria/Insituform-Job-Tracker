"""Shared PyQt UI helpers for the JOBLOG Tracker screens.

Keeping page chrome here reduces repeated stylesheet blocks and keeps every
screen aligned when the terminal layout is tuned.
"""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QLabel, QPushButton, QFrame, QHBoxLayout, QVBoxLayout


def operator_name(app) -> str:
    """Return the signed-in operator name with a stable fallback."""
    operator = getattr(app, "operator", None)
    return getattr(operator, "FullName", None) or "Operator"


def action_button(text: str, callback=None, *, accent: bool = False, height: int = 40) -> QPushButton:
    """Create a consistently sized terminal-friendly action button."""
    button = QPushButton(text)
    button.setMinimumWidth(112)
    button.setMinimumHeight(height)
    button.setCursor(Qt.CursorShape.PointingHandCursor)
    if accent:
        button.setProperty("accent", True)
    if callback:
        button.clicked.connect(callback)
    return button


def session_banner(app, *, prefix: str = "Logged in as") -> QFrame:
    """Build the reusable signed-in operator banner used across pages."""
    frame = QFrame()
    frame.setObjectName("session_banner")

    layout = QHBoxLayout(frame)
    layout.setContentsMargins(16, 8, 12, 8)
    layout.setSpacing(12)

    label = QLabel(f"{prefix}: {operator_name(app)}")
    label.setObjectName("session_user")

    logout = action_button("Logout", lambda: app.navigate("Logout"), height=34)
    logout.setObjectName("session_logout")

    layout.addWidget(label)
    layout.addWidget(logout)
    return frame


def add_session_row(layout: QVBoxLayout, app, *, prefix: str = "Logged in as") -> None:
    """Append a right-aligned session banner to a page layout."""
    top_bar = QHBoxLayout()
    top_bar.addStretch(1)
    top_bar.addWidget(session_banner(app, prefix=prefix))
    layout.addLayout(top_bar)


def page_title(text: str) -> QLabel:
    """Create a standardized page title label."""
    label = QLabel(text)
    label.setObjectName("sectionTitle")
    return label


def add_header_row(layout: QVBoxLayout, title: str, *actions: QPushButton) -> None:
    """Append a title/action row to a page layout."""
    row = QHBoxLayout()
    row.setContentsMargins(0, 0, 0, 0)
    row.setSpacing(10)
    row.addWidget(page_title(title))
    row.addStretch(1)
    for button in actions:
        row.addWidget(button)
    layout.addLayout(row)
