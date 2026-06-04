import csv
import re
import sys
import threading
import zipfile
from datetime import date, datetime, timedelta
from xml.sax.saxutils import escape

import pyodbc
from PyQt6.QtCore import QDate, QSortFilterProxyModel, Qt
from PyQt6.QtGui import QAction, QColor, QStandardItem, QStandardItemModel
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDateEdit,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QTableView,
    QVBoxLayout,
    QWidget,
)


APP_TITLE = "JOBLOG Tracker"

ADHOC_CONFIG = {
    "driver": "{SQL Server}",
    "server": "SQLPOWERBIPRD1",
    "database": "ADHOC",
    "user": "svc-adhoc-db",
    "password": "A7M9mGNd3caK5ntU6Rg9BPAv!",
}

EDW_CONFIG = {
    "driver": "{SQL Server}",
    "server": "SQLARGOSDEV1",
    "database": "EDW",
    "trusted": True,
}

EDW_JOBLOG_VIEWS = (
    "dbo.vw_Dim_JOBLOG_Creation",
    "dbo.vs_Dim_JOBLOG_Creation",
)

EXCLUDED_WORK_DESCRIPTION_TERMS = ("Plate", "Connector", "Additional", "Starter", "charge")
EXCLUDED_WORK_DESCRIPTION_WORDS = ("ME",)
ROLE_FULL_MENU = {
    "Admin Assistant",
    "Data Engineer",
    "Human Resources Generalist",
    "Plant Manager",
    "Plant Production Manager",
}
ROLE_JOBLOG_MENU = {
    "Area Administrator",
    "Continuous Lead",
    "Customer Service Support",
    "Customer Service Team Lead",
    "Electrical Maintenance Foreman",
    "Engineering Manager",
    "Intern",
    "Inventory/Purchasing Analyst",
    "Logistics Coordinator",
    "Logistics Manager",
    "Production Foreman",
    "Material Control Clerk MFG",
    "Material Planner",
    "Product Services Scheduler",
    "Production Control Lead",
    "Production Supervisor",
    "Production Scheduler MFG",
    "Quality Control Engineer",
    "Scheduling Coordinator",
    "Senior Quality Manager",
    "Staff Accountant",
    "Supply Chain Manager",
}

PROCESS_OPTIONS = [
    "Allot",
    "Slit Inner",
    "Slit Outer",
    "Inner Join",
    "Outer Join",
    "Inner Sew",
    "Outer Sew",
    "Extrusion",
    "Inspection",
    "Special Apps",
]
TRACKING_PROCESS_OPTIONS = [
    "Slit Inner",
    "Slit Outer",
    "Inner Join",
    "Outer Join",
    "Inner Sew",
    "Outer Sew",
    "Extrusion",
    "Inspection",
    "Special Apps",
]
JOIN_LINE_OPTIONS = ["NR", "13", "14", "15", "17"]
INNER_SEW_OPTIONS = ["4", "6", "7", "9", "10", "11", "13", "14", "15"]
OUTER_SEW_OPTIONS = ["5", "6", "7", "9", "10", "11", "13", "14", "15"]
EXTRUSION_OPTIONS = ["NR", "1", "3", "12", "14", "15"]
INSPECTION_OPTIONS = ["1", "2", "12", "14", "15"]
ACTIVE_JOBTRACKING_FILTER = """
    NOT EXISTS (
        SELECT 1
        FROM dbo.JobTracking jt
        WHERE jt.JobNumber = CONVERT(nvarchar(50), j.JobNumber)
          AND jt.Operation = 'Special Apps'
          AND jt.EventType = 'Complete'
    )
"""
CUSTOMER_MAP = {
    "ITI CEDAR CITY UTAH": "CD/UT",
    "Florida Wetout Branch": "OCA/FL",
    "Alabama Wetout Branch": "SC/BES",
    "ITI NEW YORK WETOUT": "TAPPAN/NY",
    "ITI INDIANA WETOUT BRANCH": "IN/IND",
    "WETOUT ITI": "ITI/VT",
    "PACIFIC BRANCH PLANT": "ITI/CA",
    "INSITUFORM TECHNOLOGIES LLC": "SLC/UT",
    "INSITUFORM TECHNOLOGIES-CANADA WEST": "ITI/EDM",
    "INSITUFORM TECHNOLOGIES LIMITED": "ITI/MON",
    "MTC Branch Plant": "MTC/PR",
}

NAV_DARK = "#07182C"
NAV_MID = "#0A3A66"
ACCENT = "#E8650A"
TEXT_DARK = "#0A1A2F"
TEXT_MID = "#4A5568"

STYLE = f"""
QMainWindow, QWidget#root {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #EAF1F8, stop:0.55 #D9E7F5, stop:1 #F7FAFD);
    color: {TEXT_DARK};
    font-family: Segoe UI;
    font-size: 10pt;
}}
QFrame#header {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 {NAV_DARK}, stop:0.65 #0C3157, stop:1 #123E68);
    border-bottom: 1px solid rgba(255,255,255,80);
}}
QFrame#glass {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 rgba(255,255,255,230), stop:0.5 rgba(255,255,255,190), stop:1 rgba(226,238,250,170));
    border: 1px solid rgba(255,255,255,170);
    border-top: 1px solid rgba(255,255,255,245);
    border-radius: 16px;
}}
QFrame#darkGlass {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 rgba(16,65,106,235), stop:0.48 rgba(7,39,70,230), stop:1 rgba(5,25,46,235));
    border: 1px solid rgba(255,255,255,90);
    border-top: 1px solid rgba(255,255,255,145);
    border-radius: 16px;
}}
QFrame#darkGlass QLabel {{
    color: #EAF2FA;
}}
QLabel#brand {{
    color: {ACCENT};
    font-size: 12px;
    font-weight: 800;
}}
QLabel#heading {{
    color: white;
    font-size: 22px;
    font-weight: 800;
}}
QLabel#subheading {{
    color: #B9C7D8;
}}
QLabel#sectionTitle {{
    color: {TEXT_DARK};
    font-size: 18px;
    font-weight: 800;
}}
QLabel#muted {{
    color: {TEXT_MID};
}}
QLineEdit, QComboBox, QDateEdit {{
    background: rgba(255,255,255,245);
    border: 1px solid rgba(78,119,163,185);
    border-top: 1px solid rgba(255,255,255,255);
    border-bottom: 1px solid rgba(62,92,126,170);
    border-radius: 8px;
    padding: 6px 10px;
    color: {TEXT_DARK};
}}
QComboBox::drop-down, QDateEdit::drop-down {{
    border: 0;
    width: 24px;
}}
QCalendarWidget QWidget {{
    background-color: white;
    color: {TEXT_DARK};
}}
QCalendarWidget QAbstractItemView {{
    background-color: white;
    color: {TEXT_DARK};
    selection-background-color: {ACCENT};
    selection-color: white;
}}
QCalendarWidget QToolButton {{
    background: white;
    color: {TEXT_DARK};
    border: 1px solid rgba(78,119,163,130);
    border-radius: 6px;
    padding: 5px 8px;
}}
QCalendarWidget QMenu {{
    background-color: white;
    color: {TEXT_DARK};
}}
QCheckBox {{
    color: {TEXT_DARK};
    spacing: 8px;
}}
QPushButton {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 rgba(255,255,255,220), stop:0.52 rgba(224,236,248,195), stop:1 rgba(192,212,232,190));
    border: 1px solid rgba(255,255,255,190);
    border-bottom: 1px solid rgba(80,105,130,120);
    border-radius: 11px;
    padding: 9px 18px;
    color: {TEXT_DARK};
    font-weight: 700;
}}
QPushButton:hover {{
    background: rgba(255,255,255,235);
}}
QPushButton[accent="true"] {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #FF8A35, stop:0.48 {ACCENT}, stop:1 #B94E0B);
    color: white;
    border: 1px solid rgba(255,220,190,210);
    border-bottom: 1px solid rgba(90,40,10,150);
}}
QTableView {{
    background: rgba(255,255,255,235);
    alternate-background-color: #F3F7FB;
    border: 1px solid rgba(105,135,168,150);
    border-radius: 8px;
    gridline-color: rgba(135,160,190,120);
    selection-background-color: #E8650A;
    selection-color: white;
}}
QTableView::item {{
    padding: 5px 8px;
}}
QHeaderView::section {{
    background: #0C3157;
    color: white;
    padding: 7px;
    border: 0;
    border-right: 1px solid rgba(255,255,255,65);
    font-weight: 800;
}}
"""

def app_date_text(value):
    if value is None:
        return ""

    if isinstance(value, datetime):
        return value.strftime("%m-%d-%Y")

    if isinstance(value, date):
        return value.strftime("%m-%d-%Y")

    if isinstance(value, str):
        try:
            return datetime.strptime(value, "%Y-%m-%d").strftime("%m-%d-%Y")
        except ValueError:
            pass

    return str(value)


def configure_date_edit(item, days_from_today=0):
    item.setCalendarPopup(True)
    item.setDisplayFormat("MM-dd-yyyy")
    item.setDate(QDate.currentDate().addDays(days_from_today))
    return item


def connection_string(config):
    if config.get("trusted"):
        return (
            f"DRIVER={config['driver']};SERVER={config['server']};"
            f"DATABASE={config['database']};Trusted_Connection=yes;"
        )
    return (
        f"DRIVER={config['driver']};SERVER={config['server']};DATABASE={config['database']};"
        f"UID={config['user']};PWD={config['password']};"
    )


def adhoc_connect():
    return pyodbc.connect(connection_string(ADHOC_CONFIG))


def edw_connect():
    return pyodbc.connect(connection_string(EDW_CONFIG), timeout=30)


def value(row, name, default=None):
    try:
        return getattr(row, name)
    except AttributeError:
        return default


def as_int_or_none(raw):
    if raw in (None, "", "NR"):
        return None
    try:
        return int(float(raw))
    except (TypeError, ValueError):
        return None


def description_is_excluded(description):
    text = (description or "").lower()
    if any(term.lower() in text for term in EXCLUDED_WORK_DESCRIPTION_TERMS):
        return True
    return any(re.search(rf"\b{re.escape(word.lower())}\b", text) for word in EXCLUDED_WORK_DESCRIPTION_WORDS)


def build_desc(work_order_description, customer):
    desc_parts = []
    work_text = (work_order_description or "").lower()
    customer_text = (customer or "").lower()
    if "flex" in work_text:
        desc_parts.append("FLEX SEAM")
    if "air" in work_text:
        desc_parts.append("AIRTEST")
    if "canada west" in customer_text:
        desc_parts.append("METERS")
    return "/".join(desc_parts) if desc_parts else None


def pull_sp_app_flags(sp_app):
    text = (sp_app or "").upper()
    return (
        1 if "ME" in text else None,
        1 if "SR" in text else None,
        1 if "PS" in text or "FPS" in text else None,
    )


def excel_col_name(index):
    name = ""
    index += 1
    while index:
        index, remainder = divmod(index - 1, 26)
        name = chr(65 + remainder) + name
    return name


def write_xlsx(path, headers, rows):
    all_rows = [headers] + rows
    sheet_rows = []
    for row_index, row in enumerate(all_rows, start=1):
        cells = []
        for col_index, cell in enumerate(row):
            ref = f"{excel_col_name(col_index)}{row_index}"
            text = escape("" if cell is None else str(cell))
            cells.append(f'<c r="{ref}" t="inlineStr"><is><t>{text}</t></is></c>')
        sheet_rows.append(f'<row r="{row_index}">{"".join(cells)}</row>')

    sheet_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        f'<sheetData>{"".join(sheet_rows)}</sheetData></worksheet>'
    )
    workbook_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        '<sheets><sheet name="Export" sheetId="1" r:id="rId1"/></sheets></workbook>'
    )
    content_types = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
        '<Override PartName="/xl/worksheets/sheet1.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        '</Types>'
    )
    root_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
        'Target="xl/workbook.xml"/></Relationships>'
    )
    workbook_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
        'Target="worksheets/sheet1.xml"/></Relationships>'
    )
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", content_types)
        archive.writestr("_rels/.rels", root_rels)
        archive.writestr("xl/workbook.xml", workbook_xml)
        archive.writestr("xl/_rels/workbook.xml.rels", workbook_rels)
        archive.writestr("xl/worksheets/sheet1.xml", sheet_xml)


def glass_frame(dark=False):
    frame = QFrame()
    frame.setObjectName("darkGlass" if dark else "glass")
    return frame


def label(text, object_name=None):
    item = QLabel(text)
    if object_name:
        item.setObjectName(object_name)
    return item


def button(text, accent=False):
    item = QPushButton(text)
    if accent:
        item.setProperty("accent", "true")
    return item


class ContainsFilterProxy(QSortFilterProxyModel):
    def __init__(self):
        super().__init__()
        self.search_text = ""

    def set_search_text(self, text):
        self.search_text = (text or "").lower()
        self.invalidateFilter()

    def filterAcceptsRow(self, source_row, source_parent):
        if not self.search_text:
            return True
        model = self.sourceModel()
        for col in range(model.columnCount()):
            index = model.index(source_row, col, source_parent)
            if self.search_text in str(model.data(index) or "").lower():
                return True
        return False


class TablePanel(QWidget):
    def __init__(self, title, parent=None):
        super().__init__(parent)
        self.model = QStandardItemModel()
        self.proxy = ContainsFilterProxy()
        self.proxy.setSourceModel(self.model)
        self.table = QTableView()
        self.table.setModel(self.proxy)
        self.table.setSortingEnabled(True)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(34)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search")
        self.search.textChanged.connect(self.proxy.set_search_text)
        self.export_btn = button("Export to Excel")
        self.export_btn.clicked.connect(self.export_visible_rows)

        top = QHBoxLayout()
        top.addWidget(label(title, "sectionTitle"))
        top.addStretch(1)
        top.addWidget(self.search)
        top.addWidget(self.export_btn)

        layout = QVBoxLayout(self)
        layout.addLayout(top)
        layout.addWidget(self.table)

    def set_rows(self, headers, rows):
        self.model.clear()
        self.model.setHorizontalHeaderLabels(headers)
        for row in rows:
            items = []
            for cell in row:
                text = app_date_text(cell)
                item = QStandardItem(text)
                item.setEditable(False)
                items.append(item)
            self.model.appendRow(items)
        self.table.resizeColumnsToContents()

    def export_visible_rows(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export", "", "Excel Workbook (*.xlsx);;CSV Files (*.csv)")
        if not path:
            return
        headers = [self.model.headerData(c, Qt.Orientation.Horizontal) for c in range(self.model.columnCount())]
        rows = [
            [self.proxy.data(self.proxy.index(row, col)) for col in range(self.proxy.columnCount())]
            for row in range(self.proxy.rowCount())
        ]
        if path.lower().endswith(".csv"):
            with open(path, "w", newline="", encoding="utf-8-sig") as handle:
                writer = csv.writer(handle)
                writer.writerow(headers)
                writer.writerows(rows)
        else:
            if not path.lower().endswith(".xlsx"):
                path += ".xlsx"
            write_xlsx(path, headers, rows)
        QMessageBox.information(self, APP_TITLE, f"Exported {self.proxy.rowCount()} rows.")


class Page(QWidget):
    def __init__(self, app, title):
        super().__init__()
        self.app = app
        self.title = title

    def refresh(self):
        pass


class LoginPage(Page):
    def __init__(self, app):
        super().__init__(app, "Login")
        card = glass_frame()
        form = QFormLayout(card)
        form.setContentsMargins(28, 26, 28, 26)
        self.badge = QLineEdit()
        self.badge.setPlaceholderText("Scan badge or type Operator ID")
        submit = button("Submit", True)
        submit.clicked.connect(self.login)
        self.badge.returnPressed.connect(self.login)
        form.addRow(label("Scan Badge", "sectionTitle"))
        form.addRow("Operator ID", self.badge)
        form.addRow("", submit)

        layout = QVBoxLayout(self)
        layout.addStretch(1)
        row = QHBoxLayout()
        row.addStretch(1)
        row.addWidget(card, 0)
        row.addStretch(1)
        layout.addLayout(row)
        layout.addStretch(2)

    def login(self):
        operator_id = self.badge.text().strip()
        if not operator_id:
            QMessageBox.warning(self, APP_TITLE, "Scan or enter an Operator ID.")
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
            QMessageBox.critical(self, APP_TITLE, f"Could not log in.\n\n{exc}")
            return
        if not row:
            QMessageBox.warning(self, APP_TITLE, "Operator not found or not active.")
            return
        self.app.operator = row
        self.app.show_role_home()


class MenuPage(Page):
    def __init__(self, app):
        super().__init__(app, "Home")
        self.grid = QGridLayout()
        card = glass_frame()
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(24, 22, 24, 24)
        card_layout.addWidget(label("JOBLOG", "sectionTitle"))
        card_layout.addLayout(self.grid)
        layout = QVBoxLayout(self)
        layout.addWidget(card)
        layout.addStretch(1)

    def refresh(self):
        while self.grid.count():
            item = self.grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        names = self.app.available_pages()
        for index, page_name in enumerate(names):
            item = button(page_name, index == 0)
            item.setMinimumHeight(54)
            item.clicked.connect(lambda _=False, name=page_name: self.app.navigate(name))
            self.grid.addWidget(item, index // 2, index % 2)


class JoblogPage(Page):
    def __init__(self, app):
        super().__init__(app, "View Joblog")
        self.panel = TablePanel("View Joblog")
        self.use_date_filter = QCheckBox("Use Date Range")
        self.start_date = configure_date_edit(QDateEdit(), -30)
        self.end_date = configure_date_edit(QDateEdit(), 90)
        refresh = button("Refresh", True)
        refresh.clicked.connect(self.refresh)
        filters = glass_frame()
        filter_layout = QHBoxLayout(filters)
        filter_layout.addWidget(self.use_date_filter)
        filter_layout.addWidget(label("Ship By From"))
        filter_layout.addWidget(self.start_date)
        filter_layout.addWidget(label("To"))
        filter_layout.addWidget(self.end_date)
        filter_layout.addStretch(1)
        filter_layout.addWidget(refresh)
        layout = QVBoxLayout(self)
        layout.addWidget(filters)
        layout.addWidget(self.panel)

    def refresh(self):
        try:
            self.app.start_background_joblog_pull()
            with adhoc_connect() as conn:
                sql = """
                    SELECT PalletNumber, JobNumber, Customer, Diameter, Thickness, Length,
                           ShipBy, SP_APP, [DESC], RUSH, PullBelt
                    FROM dbo.vw_JOBLOG_Open j
                """
                params = []
                filters = [ACTIVE_JOBTRACKING_FILTER]
                if self.use_date_filter.isChecked():
                    filters.append("ShipBy >= ? AND ShipBy <= ?")
                    params.extend([
                        self.start_date.date().toString("yyyy-MM-dd"),
                        self.end_date.date().toString("yyyy-MM-dd"),
                    ])
                sql += " WHERE " + " AND ".join(filters)
                sql += " ORDER BY PalletNumber, JobNumber"
                rows = conn.cursor().execute(sql, *params).fetchall()
            self.panel.set_rows(
                ["Pallet #", "Job #", "Customer", "Diameter", "Thickness", "Length", "ShipBy", "SP APP", "DESC", "Rush", "Pull Belt"],
                rows,
            )
        except Exception as exc:
            QMessageBox.critical(self, APP_TITLE, f"Could not load JOBLOG.\n\n{exc}")


class AssignLinePage(Page):
    def __init__(self, app):
        super().__init__(app, "Assign Job to Line")
        self.rows = []
        self.table = QTableView()
        self.model = QStandardItemModel()
        self.table.setModel(self.model)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(36)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        save = button("Save", True)
        save.clicked.connect(self.save)
        refresh = button("Refresh")
        refresh.clicked.connect(self.refresh)
        actions = QHBoxLayout()
        actions.addStretch(1)
        actions.addWidget(refresh)
        actions.addWidget(save)
        layout = QVBoxLayout(self)
        layout.addLayout(actions)
        layout.addWidget(self.table)

    def refresh(self):
        try:
            with adhoc_connect() as conn:
                rows = conn.cursor().execute(
                    """
                    SELECT j.PalletNumber, j.JobNumber, j.Diameter, j.Thickness, j.Length
                    FROM dbo.JOBLOG j
                    LEFT JOIN dbo.JobEntry_MFGLine m ON m.JobNumber = j.JobNumber
                    WHERE j.Date_Completed IS NULL AND m.JobNumber IS NULL
                      AND (j.PalletNumber = 'Stock' OR j.ShipBy >= DATEADD(day, -7, CAST(GETDATE() AS date)))
                      AND """ + ACTIVE_JOBTRACKING_FILTER + """
                    ORDER BY j.JobNumber
                    """
                ).fetchall()
            self.rows = rows
            self.model.clear()
            self.model.setHorizontalHeaderLabels(
                ["Pallet #", "Job #", "Diameter", "Thickness", "Length", "Inner Join", "Outer Join", "Inner Sew", "Outer Sew", "Extrusion", "Inspection"]
            )
            for row in rows:
                values = [row.PalletNumber, row.JobNumber, row.Diameter, row.Thickness, row.Length]
                items = [QStandardItem("" if item is None else str(item)) for item in values]
                for item in items:
                    item.setEditable(False)
                self.model.appendRow(items + [QStandardItem("") for _ in range(6)])
                view_row = self.model.rowCount() - 1
                auto_nr = as_int_or_none(row.Diameter) is not None and as_int_or_none(row.Diameter) < 40
                self.add_combo(view_row, 5, JOIN_LINE_OPTIONS, "NR" if auto_nr else "")
                self.add_combo(view_row, 6, JOIN_LINE_OPTIONS, "NR" if auto_nr else "")
                self.add_combo(view_row, 7, INNER_SEW_OPTIONS, "")
                self.add_combo(view_row, 8, OUTER_SEW_OPTIONS, "")
                self.add_combo(view_row, 9, EXTRUSION_OPTIONS, "NR" if auto_nr else "")
                self.add_combo(view_row, 10, INSPECTION_OPTIONS, "")
        except Exception as exc:
            QMessageBox.critical(self, APP_TITLE, f"Could not load unassigned jobs.\n\n{exc}")

    def add_combo(self, row, col, options, current):
        combo = QComboBox()
        combo.addItems([""] + [item for item in options if item])
        combo.setCurrentText(current)
        self.table.setIndexWidget(self.model.index(row, col), combo)

    def combo_value(self, row, col):
        widget = self.table.indexWidget(self.model.index(row, col))
        return widget.currentText() if widget else None

    def save(self):
        try:
            with adhoc_connect() as conn:
                cur = conn.cursor()
                for row in range(self.model.rowCount()):
                    job_number = as_int_or_none(self.model.item(row, 1).text())
                    cur.execute(
                        """
                        INSERT INTO dbo.JobEntry_MFGLine
                        (JobNumber, InnerJoinMFG, OuterJoinMFG, InnerSewMFG, OuterSewMFG, ExtrusionMFG, InspectionMFG)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        job_number,
                        as_int_or_none(self.combo_value(row, 5)),
                        as_int_or_none(self.combo_value(row, 6)),
                        as_int_or_none(self.combo_value(row, 7)),
                        as_int_or_none(self.combo_value(row, 8)),
                        as_int_or_none(self.combo_value(row, 9)),
                        as_int_or_none(self.combo_value(row, 10)),
                    )
                conn.commit()
            QMessageBox.information(self, APP_TITLE, "Line assignments saved.")
            self.refresh()
        except Exception as exc:
            QMessageBox.critical(self, APP_TITLE, f"Could not save line assignments.\n\n{exc}")


class AssignedLinesPage(Page):
    def __init__(self, app):
        super().__init__(app, "View/Update Assigned Production Lines")
        self.table = QTableView()
        self.model = QStandardItemModel()
        self.table.setModel(self.model)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(36)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        refresh = button("Refresh", True)
        refresh.clicked.connect(self.refresh)
        save = button("Save Changes", True)
        save.clicked.connect(self.save)
        actions = QHBoxLayout()
        actions.addStretch(1)
        actions.addWidget(refresh)
        actions.addWidget(save)
        layout = QVBoxLayout(self)
        layout.addLayout(actions)
        layout.addWidget(self.table)

    def refresh(self):
        try:
            with adhoc_connect() as conn:
                rows = conn.cursor().execute(
                    """
                    SELECT j.PalletNumber, j.JobNumber, j.Diameter, j.Thickness, j.Length,
                           m.InnerJoinMFG, m.OuterJoinMFG, m.InnerSewMFG, m.OuterSewMFG,
                           m.ExtrusionMFG, m.InspectionMFG
                    FROM dbo.JOBLOG j
                    INNER JOIN dbo.JobEntry_MFGLine m ON m.JobNumber = j.JobNumber
                    WHERE j.Date_Completed IS NULL
                      AND (j.PalletNumber = 'Stock' OR j.ShipBy >= DATEADD(day, -7, CAST(GETDATE() AS date)))
                      AND """ + ACTIVE_JOBTRACKING_FILTER + """
                    ORDER BY j.JobNumber
                    """
                ).fetchall()
            self.model.clear()
            self.model.setHorizontalHeaderLabels(
                ["Pallet #", "Job #", "Diameter", "Thickness", "Length", "Inner Join", "Outer Join", "Inner Sew", "Outer Sew", "Extrusion", "Inspection"]
            )
            for row in rows:
                values = [row.PalletNumber, row.JobNumber, row.Diameter, row.Thickness, row.Length]
                items = [QStandardItem(app_date_text(item)) for item in values]
                for item in items:
                    item.setEditable(False)
                self.model.appendRow(items + [QStandardItem("") for _ in range(6)])
                view_row = self.model.rowCount() - 1
                self.add_combo(view_row, 5, JOIN_LINE_OPTIONS, row.InnerJoinMFG)
                self.add_combo(view_row, 6, JOIN_LINE_OPTIONS, row.OuterJoinMFG)
                self.add_combo(view_row, 7, INNER_SEW_OPTIONS, row.InnerSewMFG)
                self.add_combo(view_row, 8, OUTER_SEW_OPTIONS, row.OuterSewMFG)
                self.add_combo(view_row, 9, EXTRUSION_OPTIONS, row.ExtrusionMFG)
                self.add_combo(view_row, 10, INSPECTION_OPTIONS, row.InspectionMFG)
        except Exception as exc:
            QMessageBox.critical(self, APP_TITLE, f"Could not load assigned lines.\n\n{exc}")

    def add_combo(self, row, col, options, current):
        combo = QComboBox()
        combo.addItems([""] + [str(item) for item in options if str(item)])
        combo.setCurrentText("" if current is None else str(current))
        self.table.setIndexWidget(self.model.index(row, col), combo)

    def combo_value(self, row, col):
        widget = self.table.indexWidget(self.model.index(row, col))
        return widget.currentText() if widget else None

    def save(self):
        try:
            with adhoc_connect() as conn:
                cur = conn.cursor()
                for row in range(self.model.rowCount()):
                    job_number = as_int_or_none(self.model.item(row, 1).text())
                    cur.execute(
                        """
                        UPDATE dbo.JobEntry_MFGLine
                        SET InnerJoinMFG = ?, OuterJoinMFG = ?, InnerSewMFG = ?,
                            OuterSewMFG = ?, ExtrusionMFG = ?, InspectionMFG = ?
                        WHERE JobNumber = ?
                        """,
                        as_int_or_none(self.combo_value(row, 5)),
                        as_int_or_none(self.combo_value(row, 6)),
                        as_int_or_none(self.combo_value(row, 7)),
                        as_int_or_none(self.combo_value(row, 8)),
                        as_int_or_none(self.combo_value(row, 9)),
                        as_int_or_none(self.combo_value(row, 10)),
                        job_number,
                    )
                conn.commit()
            QMessageBox.information(self, APP_TITLE, "Assigned production lines updated.")
            self.refresh()
        except Exception as exc:
            QMessageBox.critical(self, APP_TITLE, f"Could not update assigned lines.\n\n{exc}")


class UpdateLocationPage(Page):
    def __init__(self, app):
        super().__init__(app, "Update Job Location")
        self.panel = TablePanel("Update Job Location")
        self.job_input = QLineEdit()
        self.line_input = QLineEdit()
        self.process = QComboBox()
        self.process.addItems(PROCESS_OPTIONS)
        self.status = QComboBox()
        self.status.addItems(["On Line", "Complete"])
        save = button("Save", True)
        save.clicked.connect(self.save)
        refresh = button("Refresh")
        refresh.clicked.connect(self.refresh)

        form = glass_frame()
        form_layout = QHBoxLayout(form)
        form_layout.addWidget(label("Job #"))
        form_layout.addWidget(self.job_input)
        form_layout.addWidget(label("Line"))
        form_layout.addWidget(self.line_input)
        form_layout.addWidget(label("Process"))
        form_layout.addWidget(self.process)
        form_layout.addWidget(label("Status"))
        form_layout.addWidget(self.status)
        form_layout.addWidget(save)
        form_layout.addWidget(refresh)

        layout = QVBoxLayout(self)
        layout.addWidget(form)
        layout.addWidget(self.panel)

    def refresh(self):
        try:
            with adhoc_connect() as conn:
                rows = conn.cursor().execute(
                    """
                    WITH latest AS (
                        SELECT JobNumber, Line, Operation, EventType, EventTime,
                               ROW_NUMBER() OVER (PARTITION BY JobNumber ORDER BY EventTime DESC, JobTrackingPK DESC) rn
                        FROM dbo.JobTracking
                    )
                    SELECT j.PalletNumber, j.JobNumber, j.Customer, j.Diameter, j.Thickness, j.Length,
                           latest.Line, latest.Operation AS CurrentProcess
                    FROM dbo.JOBLOG j
                    LEFT JOIN latest ON latest.JobNumber = CONVERT(nvarchar(50), j.JobNumber) AND latest.rn = 1
                    WHERE j.Date_Completed IS NULL
                    ORDER BY j.PalletNumber, j.JobNumber
                    """
                ).fetchall()
            self.panel.set_rows(
                ["Pallet #", "Job #", "Customer", "Diameter", "Thickness", "Length", "Line", "Current Listed Process"],
                rows,
            )
        except Exception as exc:
            QMessageBox.critical(self, APP_TITLE, f"Could not load job locations.\n\n{exc}")

    def save(self):
        job_number = self.job_input.text().strip()
        line = self.line_input.text().strip()
        if not job_number or not line:
            QMessageBox.warning(self, APP_TITLE, "Job # and Line are required.")
            return
        event_type = "Active" if self.status.currentText() == "On Line" else "Complete"
        try:
            with adhoc_connect() as conn:
                exists = conn.cursor().execute(
                    "SELECT 1 FROM dbo.JOBLOG WHERE JobNumber = ?", job_number
                ).fetchone()
                if not exists:
                    QMessageBox.warning(self, APP_TITLE, "Job Number not found check that jobnumber is correct.")
                    return
                conn.cursor().execute(
                    """
                    INSERT INTO dbo.JobTracking (OperatorName, JobNumber, Line, Operation, EventType, EventTime)
                    VALUES (?, ?, ?, ?, ?, GETDATE())
                    """,
                    self.app.operator.FullName,
                    job_number,
                    line,
                    self.process.currentText(),
                    event_type,
                )
                if event_type == "Complete":
                    conn.cursor().execute("UPDATE dbo.JOBLOG SET Date_Completed = CAST(GETDATE() AS date) WHERE JobNumber = ?", job_number)
                conn.commit()
            QMessageBox.information(self, APP_TITLE, "Job location saved.")
            self.refresh()
        except Exception as exc:
            QMessageBox.critical(self, APP_TITLE, f"Could not save job location.\n\n{exc}")


class HeadcountPage(Page):
    def __init__(self, app):
        super().__init__(app, "View Current Employees")
        self.panel = TablePanel("View Current Employees")
        self.active_only = QCheckBox("Active only")
        self.active_only.setChecked(True)
        self.active_only.stateChanged.connect(lambda _=None: self.refresh())
        refresh = button("Refresh", True)
        refresh.clicked.connect(self.refresh)
        actions = QHBoxLayout()
        actions.addWidget(self.active_only)
        actions.addStretch(1)
        actions.addWidget(refresh)
        layout = QVBoxLayout(self)
        layout.addLayout(actions)
        layout.addWidget(self.panel)

    def refresh(self):
        try:
            with adhoc_connect() as conn:
                sql = """
                    SELECT OperatorID, FullName, Department, Shift, Role, IsActive, HireDate
                    FROM dbo.Operators
                """
                if self.active_only.isChecked():
                    sql += " WHERE ISNULL(IsActive, 1) = 1"
                sql += " ORDER BY FullName"
                rows = conn.cursor().execute(sql).fetchall()
            self.panel.set_rows(["Operator ID", "Full Name", "Department", "Shift", "Role", "IsActive", "HireDate"], rows)
        except Exception as exc:
            QMessageBox.critical(self, APP_TITLE, f"Could not load employees.\n\n{exc}")


class EmployeePage(Page):
    def __init__(self, app):
        super().__init__(app, "Add/Update Employee")
        self.operator_id = QLineEdit()
        self.full_name = QLineEdit()
        self.department = QLineEdit()
        self.shift = QLineEdit()
        self.role = QLineEdit()
        self.hire_date = configure_date_edit(QDateEdit())
        self.active = QCheckBox("Is Active")
        self.active.setChecked(True)

        load_btn = button("Load")
        load_btn.clicked.connect(self.load_employee)
        save_btn = button("Save", True)
        save_btn.clicked.connect(self.save_employee)
        form = glass_frame()
        layout = QFormLayout(form)
        layout.setContentsMargins(24, 22, 24, 24)
        layout.addRow(label("Add/Update Employee", "sectionTitle"))
        layout.addRow("Operator ID", self.operator_id)
        layout.addRow("", load_btn)
        layout.addRow("Full Name", self.full_name)
        layout.addRow("Department", self.department)
        layout.addRow("Shift", self.shift)
        layout.addRow("Role", self.role)
        layout.addRow("Hire Date", self.hire_date)
        layout.addRow("", self.active)
        layout.addRow("", save_btn)

        page_layout = QVBoxLayout(self)
        page_layout.addWidget(form)
        page_layout.addStretch(1)

    def load_employee(self):
        operator_id = self.operator_id.text().strip()
        if not operator_id:
            QMessageBox.warning(self, APP_TITLE, "Operator ID is required.")
            return
        try:
            with adhoc_connect() as conn:
                row = conn.cursor().execute(
                    """
                    SELECT FullName, Department, Shift, Role, IsActive, HireDate
                    FROM dbo.Operators WHERE OperatorID = ?
                    """,
                    operator_id,
                ).fetchone()
            if not row:
                QMessageBox.information(self, APP_TITLE, "No employee found. Fill the form to add one.")
                return
            self.full_name.setText(row.FullName or "")
            self.department.setText(row.Department or "")
            self.shift.setText(row.Shift or "")
            self.role.setText(row.Role or "")
            self.active.setChecked(bool(row.IsActive))
            if row.HireDate:
                self.hire_date.setDate(QDate(row.HireDate.year, row.HireDate.month, row.HireDate.day))
        except Exception as exc:
            QMessageBox.critical(self, APP_TITLE, f"Could not load employee.\n\n{exc}")

    def save_employee(self):
        operator_id = as_int_or_none(self.operator_id.text().strip())
        if operator_id is None or not self.full_name.text().strip():
            QMessageBox.warning(self, APP_TITLE, "Operator ID and Full Name are required.")
            return
        try:
            with adhoc_connect() as conn:
                exists = conn.cursor().execute("SELECT 1 FROM dbo.Operators WHERE OperatorID = ?", operator_id).fetchone()
                if exists:
                    conn.cursor().execute(
                        """
                        UPDATE dbo.Operators
                        SET FullName=?, Department=?, Shift=?, Role=?, IsActive=?, HireDate=?
                        WHERE OperatorID=?
                        """,
                        self.full_name.text().strip(),
                        self.department.text().strip(),
                        self.shift.text().strip(),
                        self.role.text().strip(),
                        1 if self.active.isChecked() else 0,
                        self.hire_date.date().toPyDate(),
                        operator_id,
                    )
                else:
                    conn.cursor().execute(
                        """
                        INSERT INTO dbo.Operators (OperatorID, FullName, Department, Shift, Role, IsActive, HireDate)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        operator_id,
                        self.full_name.text().strip(),
                        self.department.text().strip(),
                        self.shift.text().strip(),
                        self.role.text().strip(),
                        1,
                        self.hire_date.date().toPyDate(),
                    )
                conn.commit()
            QMessageBox.information(self, APP_TITLE, "Employee saved.")
        except Exception as exc:
            QMessageBox.critical(self, APP_TITLE, f"Could not save employee.\n\n{exc}")


class JobTrackingPage(Page):
    def __init__(self, app):
        super().__init__(app, "Job Tracking")
        self.job = QLineEdit()
        self.job.setPlaceholderText("Scan or type Job #")
        self.line = QLineEdit()
        self.line.setPlaceholderText("Line")
        self.operation = QComboBox()
        self.operation.addItems(TRACKING_PROCESS_OPTIONS)
        start = button("Start", True)
        stop = button("Stop")
        start.clicked.connect(lambda: self.save_event("Active"))
        stop.clicked.connect(lambda: self.save_event("Complete"))

        card = glass_frame()
        form = QFormLayout(card)
        form.setContentsMargins(28, 26, 28, 26)
        form.addRow(label("Job Tracking", "sectionTitle"))
        form.addRow("Job #", self.job)
        form.addRow("Line", self.line)
        form.addRow("Current Operation", self.operation)
        actions = QHBoxLayout()
        actions.addWidget(start)
        actions.addWidget(stop)
        form.addRow("", actions)

        layout = QVBoxLayout(self)
        layout.addWidget(card)
        layout.addStretch(1)

    def save_event(self, event_type):
        job_number = self.job.text().strip()
        line = self.line.text().strip()
        if not job_number or not line:
            QMessageBox.warning(self, APP_TITLE, "Job # and Line are required.")
            return
        try:
            with adhoc_connect() as conn:
                exists = conn.cursor().execute("SELECT 1 FROM dbo.JOBLOG WHERE JobNumber = ?", job_number).fetchone()
                if not exists:
                    QMessageBox.warning(self, APP_TITLE, "Job Number not found check that jobnumber is correct.")
                    return
                conn.cursor().execute(
                    """
                    INSERT INTO dbo.JobTracking (OperatorName, JobNumber, Line, Operation, EventType, EventTime)
                    VALUES (?, ?, ?, ?, ?, GETDATE())
                    """,
                    self.app.operator.FullName,
                    job_number,
                    line,
                    self.operation.currentText(),
                    event_type,
                )
                if event_type == "Complete":
                    conn.cursor().execute("UPDATE dbo.JOBLOG SET Date_Completed = CAST(GETDATE() AS date) WHERE JobNumber = ?", job_number)
                conn.commit()
            QMessageBox.information(self, APP_TITLE, f"Job marked {event_type}.")
        except Exception as exc:
            QMessageBox.critical(self, APP_TITLE, f"Could not save tracking event.\n\n{exc}")


class JoblogTracker(QMainWindow):
    def __init__(self):
        super().__init__()
        self.operator = None
        self.joblog_pull_lock = threading.Lock()
        self.joblog_pull_running = False
        self.setWindowTitle(APP_TITLE)
        self.resize(1280, 820)

        root = QWidget()
        root.setObjectName("root")
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.header = QFrame()
        self.header.setObjectName("header")
        header_layout = QHBoxLayout(self.header)
        header_layout.setContentsMargins(24, 14, 24, 14)
        title_box = QVBoxLayout()
        title_box.addWidget(label("INSITUFORM", "brand"))
        title_box.addWidget(label(APP_TITLE, "heading"))
        self.user_label = label("Not logged in", "subheading")
        title_box.addWidget(self.user_label)
        header_layout.addLayout(title_box)
        header_layout.addStretch(1)
        self.home_btn = button("Home")
        self.home_btn.clicked.connect(self.show_role_home)
        self.logout_btn = button("Logout")
        self.logout_btn.clicked.connect(self.logout)
        header_layout.addWidget(self.home_btn)
        header_layout.addWidget(self.logout_btn)
        layout.addWidget(self.header)

        self.stack = QStackedWidget()
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(20, 20, 20, 20)
        content_layout.addWidget(self.stack)
        layout.addWidget(content)

        self.pages = {
            "Login": LoginPage(self),
            "Home": MenuPage(self),
            "View Joblog": JoblogPage(self),
            "Assign Job to Line": AssignLinePage(self),
            "View Assigned Production Lines": AssignedLinesPage(self),
            "Update Job Location": UpdateLocationPage(self),
            "View Current Employees": HeadcountPage(self),
            "Add/Update Employee": EmployeePage(self),
            "Job Tracking": JobTrackingPage(self),
        }
        for page in self.pages.values():
            self.stack.addWidget(page)
        self.navigate("Login")

        pull_action = QAction("Pull JOBLOG Now", self)
        pull_action.triggered.connect(self.pull_joblog_now)
        self.menuBar().addAction(pull_action)

    def update_header(self):
        if self.operator:
            self.user_label.setText(f"Logged in as: {self.operator.FullName} ({self.operator.Role})")
        else:
            self.user_label.setText("Not logged in")

    def navigate(self, name):
        if name != "Login" and not self.operator:
            name = "Login"
        page = self.pages[name]
        self.stack.setCurrentWidget(page)
        self.home_btn.setVisible(name not in ("Login", "Home"))
        self.logout_btn.setVisible(name != "Login")
        self.update_header()
        page.refresh()

    def logout(self):
        self.operator = None
        self.navigate("Login")

    def show_role_home(self):
        if not self.operator:
            self.navigate("Login")
            return
        role = self.operator.Role or ""
        if role not in ROLE_FULL_MENU and role not in ROLE_JOBLOG_MENU:
            self.navigate("Job Tracking")
        else:
            self.navigate("Home")

    def available_pages(self):
        role = self.operator.Role or ""
        base = [
            "View Joblog",
            "Assign Job to Line",
            "View Assigned Production Lines",
            "Update Job Location",
        ]
        if role in ROLE_FULL_MENU:
            return base + ["View Current Employees", "Add/Update Employee"]
        if role in ROLE_JOBLOG_MENU:
            return base
        return ["Job Tracking"]

    def pull_joblog_now(self):
        try:
            count = self.pull_joblog(force=True)
            QMessageBox.information(self, APP_TITLE, f"JOBLOG pull complete. {count} rows inserted or updated.")
        except Exception as exc:
            QMessageBox.critical(self, APP_TITLE, f"JOBLOG pull failed.\n\n{exc}")

    def pull_joblog_if_due(self):
        with adhoc_connect() as conn:
            row = conn.cursor().execute("SELECT MAX(LastPull) FROM dbo.JOBLOG").fetchone()
        last_pull = row[0] if row else None
        if not last_pull or last_pull <= datetime.now() - timedelta(hours=1):
            self.pull_joblog(force=True)

    def start_background_joblog_pull(self):
        with self.joblog_pull_lock:
            if self.joblog_pull_running:
                return
            self.joblog_pull_running = True

        def worker():
            try:
                self.pull_joblog_if_due()
            except Exception:
                pass
            finally:
                with self.joblog_pull_lock:
                    self.joblog_pull_running = False

        threading.Thread(target=worker, daemon=True).start()

    def pull_joblog(self, force=False):
        pulled_at = datetime.now()
        source_rows = self.load_joblog_creation_rows()
        saved = 0
        with adhoc_connect() as conn:
            cur = conn.cursor()
            for row in source_rows:
                work_desc = value(row, "WorkOrder_Description")
                if description_is_excluded(work_desc):
                    continue
                job_number = as_int_or_none(value(row, "JobNumber"))
                pallet_number = value(row, "PalletNumber")
                customer = value(row, "Customer") or ""
                customer = CUSTOMER_MAP.get(customer, customer)
                if job_number is None or not customer:
                    continue
                ship_by = value(row, "ShipBy")
                if str(pallet_number or "").strip().lower() == "stock":
                    ship_by = None
                desc = build_desc(work_desc, customer)
                me, sr, ps = pull_sp_app_flags(value(row, "SP_APP"))
                cur.execute(
                    """
                    MERGE dbo.JOBLOG AS target
                    USING (SELECT ? AS JobNumber) AS source
                    ON target.JobNumber = source.JobNumber
                    WHEN MATCHED THEN UPDATE SET
                        PalletNumber = ?, Customer = ?, Diameter = ?, Thickness = ?, Length = ?,
                        ShipBy = ?, SP_APP = ?, [DESC] = ?, ME = ?, SR = ?, PS = ?,
                        OrderDate = ?, LastPull = ?, Date_Completed = ?, RUSH = ?
                    WHEN NOT MATCHED THEN INSERT
                        (JobNumber, PalletNumber, Customer, Diameter, Thickness, Length,
                         ShipBy, SP_APP, [DESC], ME, SR, PS, OrderDate, LastPull, Date_Completed, RUSH)
                    VALUES
                        (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                    """,
                    job_number,
                    pallet_number,
                    customer,
                    value(row, "Diameter"),
                    value(row, "Thickness"),
                    as_int_or_none(value(row, "Length")),
                    ship_by,
                    value(row, "SP_APP"),
                    desc,
                    me,
                    sr,
                    ps,
                    value(row, "OrderDate"),
                    pulled_at,
                    value(row, "Date_Completed"),
                    value(row, "RUSH"),
                    job_number,
                    pallet_number,
                    customer,
                    value(row, "Diameter"),
                    value(row, "Thickness"),
                    as_int_or_none(value(row, "Length")),
                    ship_by,
                    value(row, "SP_APP"),
                    desc,
                    me,
                    sr,
                    ps,
                    value(row, "OrderDate"),
                    pulled_at,
                    value(row, "Date_Completed"),
                    value(row, "RUSH"),
                )
                saved += 1
            conn.commit()
        return saved

    def load_joblog_creation_rows(self):
        errors = []
        for view_name in EDW_JOBLOG_VIEWS:
            try:
                with edw_connect() as conn:
                    cur = conn.cursor()
                    return cur.execute(
                        f"""
                        SELECT JobNumber, PalletNumber, Customer, WorkOrder_Description,
                               Diameter, Thickness, Length, OrderDate, ShipBy,
                               Date_Completed, SP_APP, RUSH
                        FROM {view_name}
                        """
                    ).fetchall()
            except Exception as exc:
                errors.append(f"{view_name}: {exc}")
        raise RuntimeError("Could not read JOBLOG_Creation source.\n\n" + "\n\n".join(errors))


def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(STYLE)
    window = JoblogTracker()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
