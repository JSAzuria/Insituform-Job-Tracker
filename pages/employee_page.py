# pages/employee_page.py

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QLineEdit,
    QCheckBox,
    QDateEdit,
    QMessageBox,
    QLabel,
    QPushButton,
    QFrame,
    QGridLayout,
    QDialog,
    QListWidget,
    QListWidgetItem,
    QDialogButtonBox
)
from PyQt6.QtCore import QDate, Qt
from database import adhoc_connect
from config import APP_TITLE

class EmployeePage(QWidget):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.setObjectName("root")

        # --- Core Inputs & Interactive Controls ---
        self.operator_id = QLineEdit()
        self.operator_id.setPlaceholderText("Badge # (e.g. 90063675)")
        self.operator_id.setMinimumHeight(40)

        self.search_name = QLineEdit()
        self.search_name.setPlaceholderText("Search by name...")
        self.search_name.setMinimumHeight(40)

        self.full_name = QLineEdit()
        self.full_name.setPlaceholderText("First & Last Name")
        self.full_name.setMinimumHeight(40)

        self.department = QLineEdit()
        self.department.setMinimumHeight(40)

        self.shift = QLineEdit()
        self.shift.setMinimumHeight(40)

        self.role = QLineEdit()
        self.role.setMinimumHeight(40)

        self.hire_date = QDateEdit(QDate.currentDate())
        self.hire_date.setCalendarPopup(True)
        self.hire_date.setMinimumHeight(40)

        self.active = QCheckBox("Employee is Active")
        self.active.setChecked(True)
        self.active.setMinimumHeight(30)

        # Action Buttons
        load_btn = QPushButton("Load Employee")
        load_btn.setMinimumHeight(40)
        load_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        load_btn.clicked.connect(self.load_employee)

        save_btn = QPushButton("Save Employee")
        save_btn.setMinimumHeight(45)
        save_btn.setProperty("accent", True)
        save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        save_btn.clicked.connect(self.save_employee)

        home_btn = QPushButton("Home Menu")
        home_btn.setMinimumHeight(45)
        home_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        home_btn.clicked.connect(lambda: self.app.navigate("Home"))

        # --- Master Layout Assembly ---
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 24, 24, 24)
        main_layout.setSpacing(20)

        # --- SESSION BANNER ---
        top_bar = QHBoxLayout()
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
        main_layout.addLayout(top_bar)

        main_layout.addStretch(1)

        # --- MAIN CARD ---
        employee_card = QFrame()
        employee_card.setObjectName("glass_card")
        employee_card.setMinimumWidth(550)
        employee_card.setMaximumWidth(700)

        card_layout = QVBoxLayout(employee_card)
        card_layout.setContentsMargins(35, 30, 35, 35)
        card_layout.setSpacing(25)

        title_label = QLabel("Employee Management")
        title_label.setObjectName("menuMainTitle")
        title_label.setStyleSheet("font-size: 24px; font-weight: 900; color: #333333;")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(title_label)

        # --- Search block: Badge # OR Name ---
        search_frame = QFrame()
        search_frame.setStyleSheet("""
            QFrame {
                background-color: #F5F5F5;
                border-radius: 8px;
                border: 1px solid #E0E0E0;
            }
            QLabel { background: transparent; border: none; }
        """)
        search_inner = QVBoxLayout(search_frame)
        search_inner.setContentsMargins(15, 12, 15, 12)
        search_inner.setSpacing(10)

        search_title = QLabel("Search Employee")
        search_title.setStyleSheet("font-weight: 700; font-size: 13px; color: #555555; background: transparent; border: none;")
        search_inner.addWidget(search_title)

        # Badge # row
        badge_row = QHBoxLayout()
        badge_lbl = QLabel("Badge #:")
        badge_lbl.setFixedWidth(70)
        badge_lbl.setStyleSheet("font-weight: 600; color: #555555; background: transparent; border: none;")
        badge_row.addWidget(badge_lbl)
        badge_row.addWidget(self.operator_id)
        search_inner.addLayout(badge_row)

        # OR divider
        or_lbl = QLabel("— or —")
        or_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        or_lbl.setStyleSheet("color: #AAAAAA; font-size: 11px; background: transparent; border: none;")
        search_inner.addWidget(or_lbl)

        # Name row
        name_row = QHBoxLayout()
        name_lbl = QLabel("Name:")
        name_lbl.setFixedWidth(70)
        name_lbl.setStyleSheet("font-weight: 600; color: #555555; background: transparent; border: none;")
        name_row.addWidget(name_lbl)
        name_row.addWidget(self.search_name)
        search_inner.addLayout(name_row)

        search_inner.addWidget(load_btn)
        card_layout.addWidget(search_frame)

        # --- Divider ---
        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setFrameShadow(QFrame.Shadow.Sunken)
        divider.setStyleSheet("background-color: #E0E0E0; max-height: 1px; border: none;")
        card_layout.addWidget(divider)

        # --- Employee Details Grid ---
        grid = QGridLayout()
        grid.setHorizontalSpacing(20)
        grid.setVerticalSpacing(15)

        for row_idx, (lbl_text, widget) in enumerate([
            ("Full Name",   self.full_name),
            ("Department",  self.department),
            ("Shift",       self.shift),
            ("Role",        self.role),
            ("Hire Date",   self.hire_date),
            ("Status",      self.active),
        ]):
            lbl = QLabel(lbl_text)
            lbl.setStyleSheet("font-weight: 600;")
            grid.addWidget(lbl, row_idx, 0)
            grid.addWidget(widget, row_idx, 1)

        card_layout.addLayout(grid)

        # --- Footer ---
        footer = QHBoxLayout()
        footer.addWidget(home_btn)
        footer.addStretch(1)
        footer.addWidget(save_btn)
        card_layout.addLayout(footer)

        center_binder = QHBoxLayout()
        center_binder.addStretch(1)
        center_binder.addWidget(employee_card)
        center_binder.addStretch(1)
        main_layout.addLayout(center_binder)
        main_layout.addStretch(2)

    def _populate_fields(self, row):
        """Fills the form fields from a DB row and stamps the OperatorID box."""
        self.full_name.setText(row.FullName or "")
        self.department.setText(row.Department or "")
        self.shift.setText(str(row.Shift) if row.Shift is not None else "")
        self.role.setText(row.Role or "")
        self.active.setChecked(bool(row.IsActive))
        if row.HireDate:
            self.hire_date.setDate(QDate.fromString(str(row.HireDate), "yyyy-MM-dd"))
        # Always make sure the badge box reflects the loaded record
        self.operator_id.setText(str(row.OperatorID))

    def load_employee(self):
        badge  = self.operator_id.text().strip()
        name   = self.search_name.text().strip()

        if not badge and not name:
            QMessageBox.warning(self, APP_TITLE, "Enter a Badge # or a Name to search.")
            return

        try:
            with adhoc_connect() as conn:
                cur = conn.cursor()

                if badge:
                    # Exact badge lookup
                    row = cur.execute(
                        "SELECT OperatorID, FullName, Department, Shift, Role, IsActive, HireDate "
                        "FROM dbo.Operators WHERE OperatorID = ?", badge
                    ).fetchone()

                    if not row:
                        QMessageBox.information(self, APP_TITLE,
                            "No employee found with that Badge #. You can fill in the form to create a new record.")
                        return

                    self._populate_fields(row)
                    QMessageBox.information(self, APP_TITLE, f"Loaded: {row.FullName}")

                else:
                    # Partial name search — could return multiple matches
                    rows = cur.execute(
                        "SELECT OperatorID, FullName, Department, Shift, Role, IsActive, HireDate "
                        "FROM dbo.Operators WHERE FullName LIKE ? ORDER BY FullName ASC",
                        f"%{name}%"
                    ).fetchall()

                    if not rows:
                        QMessageBox.information(self, APP_TITLE,
                            "No employees found matching that name.")
                        return

                    if len(rows) == 1:
                        self._populate_fields(rows[0])
                        QMessageBox.information(self, APP_TITLE, f"Loaded: {rows[0].FullName}")
                    else:
                        # Multiple matches — show a selectable list dialog
                        chosen = self._pick_employee_dialog(rows)
                        if chosen:
                            self._populate_fields(chosen)
                            QMessageBox.information(self, APP_TITLE, f"Loaded: {chosen.FullName}")

        except Exception as exc:
            QMessageBox.critical(self, APP_TITLE, str(exc))

    def _pick_employee_dialog(self, rows):
        """
        Shows a modal dialog with a scrollable list of matching employees.
        Returns the selected row, or None if the user cancelled.
        """
        dlg = QDialog(self)
        dlg.setWindowTitle("Select Employee")
        dlg.setMinimumWidth(480)
        dlg.setMinimumHeight(320)

        layout = QVBoxLayout(dlg)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        lbl = QLabel(f"{len(rows)} employees found — select one to load:")
        lbl.setStyleSheet("font-weight: 700; font-size: 13px; color: #333333;")
        layout.addWidget(lbl)

        list_widget = QListWidget()
        list_widget.setAlternatingRowColors(False)
        list_widget.setStyleSheet("""
            QListWidget {
                border: 1px solid #DDDDDD;
                border-radius: 6px;
                font-size: 13px;
            }
            QListWidget::item {
                padding: 8px 12px;
            }
            QListWidget::item:selected {
                background-color: #E8650A;
                color: white;
            }
            QListWidget::item:hover:!selected {
                background-color: #F0F0F0;
            }
        """)

        for row in rows:
            display = f"{row.FullName}   |   Badge: {row.OperatorID}   |   {row.Department}"
            item = QListWidgetItem(display)
            item.setData(Qt.ItemDataRole.UserRole, row)
            list_widget.addItem(item)

        # Double-click accepts immediately
        list_widget.itemDoubleClicked.connect(lambda: dlg.accept())
        layout.addWidget(list_widget)

        btn_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        btn_box.accepted.connect(dlg.accept)
        btn_box.rejected.connect(dlg.reject)
        btn_box.setStyleSheet("""
            QPushButton {
                min-width: 90px;
                min-height: 34px;
                border-radius: 6px;
                font-weight: 700;
            }
        """)
        layout.addWidget(btn_box)

        if dlg.exec() == QDialog.DialogCode.Accepted:
            selected = list_widget.currentItem()
            if selected:
                return selected.data(Qt.ItemDataRole.UserRole)
        return None

    def save_employee(self):
        op_id     = self.operator_id.text().strip()
        full_name = self.full_name.text().strip()

        if not op_id or not full_name:
            QMessageBox.warning(self, APP_TITLE, "Badge # and Full Name are required to save.")
            return

        try:
            with adhoc_connect() as conn:
                cur = conn.cursor()
                exists = cur.execute(
                    "SELECT 1 FROM dbo.Operators WHERE OperatorID = ?", op_id
                ).fetchone()

                if exists:
                    cur.execute(
                        """
                        UPDATE dbo.Operators
                        SET FullName = ?, Department = ?, Shift = ?, Role = ?, IsActive = ?, HireDate = ?
                        WHERE OperatorID = ?
                        """,
                        full_name, self.department.text().strip(), self.shift.text().strip(),
                        self.role.text().strip(), 1 if self.active.isChecked() else 0,
                        self.hire_date.date().toPyDate(), op_id
                    )
                else:
                    cur.execute(
                        """
                        INSERT INTO dbo.Operators (OperatorID, FullName, Department, Shift, Role, IsActive, HireDate)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        op_id, full_name, self.department.text().strip(), self.shift.text().strip(),
                        self.role.text().strip(), 1 if self.active.isChecked() else 0,
                        self.hire_date.date().toPyDate()
                    )
                conn.commit()
            QMessageBox.information(self, APP_TITLE, "Employee saved successfully.")
        except Exception as exc:
            QMessageBox.critical(self, APP_TITLE, str(exc))