# widgets/table_panel.py

import csv
import re

from PyQt6.QtWidgets import QStyledItemDelegate
from PyQt6.QtGui import QColor, QBrush
from PyQt6.QtCore import Qt, QSortFilterProxyModel
from PyQt6.QtGui import QStandardItem, QStandardItemModel
from PyQt6.QtWidgets import (
    QWidget,
    QTableView,
    QVBoxLayout,
    QHBoxLayout,
    QLineEdit,
    QFileDialog,
    QMessageBox,
    QHeaderView,
    QPushButton,
    QLabel,
)
from config import APP_TITLE


class AdvancedFilterProxy(QSortFilterProxyModel):
    def __init__(self):
        super().__init__()
        self.search_text = ""

    def set_search_text(self, text):
        self.search_text = (text or "").strip().lower()
        self.invalidateFilter()

    def filterAcceptsRow(self, source_row, source_parent):
        text = self.search_text
        if not text:
            return True

        model = self.sourceModel()

        # ------------------------------------------------------------------
        # KEY MAP  (column indices → friendly filter keys)
        # ------------------------------------------------------------------
        key_map = {
            "pallet":    0, "p":       0,
            "job":       1, "j":       1,
            "customer":  2, "c":       2,
            "diameter":  3, "d":       3,
            "thickness": 4, "t":       4,
            "length":    5, "l":       5,
            "sp_app":    7,
            "desc":      8,
            "shipby":    6,
        }

        # ------------------------------------------------------------------
        # Structured key=value pairs, e.g. "d=8 t=16.5"
        # ------------------------------------------------------------------
        pattern = r"(\b[a-zA-Z_ ]+)\s*=\s*([^=]+?)(?=\s+\b[a-zA-Z_ ]+\s*=|$)"
        pairs = re.findall(pattern, text)
        conditions = []
        for k, v in pairs:
            k = " ".join(k.split())
            v = v.strip()
            if k in key_map:
                conditions.append((key_map[k], v))

        if conditions:
            for col, val in conditions:
                idx = model.index(source_row, col, source_parent)
                cell = str(model.data(idx) or "").lower()
                if val not in cell:
                    return False
            return True

        # ------------------------------------------------------------------
        # Fallback: global substring search across all columns
        # ------------------------------------------------------------------
        for col in range(model.columnCount()):
            idx = model.index(source_row, col, source_parent)
            if text in str(model.data(idx) or "").lower():
                return True

        return False


class RowColorDelegate(QStyledItemDelegate):
    """
    Paints transition rows blue and taper rows orange by scanning all rows
    that share the same PalletNumber (column 0) and checking Diameter (col 3).
    Change-highlight red is applied directly to the source model items by
    JoblogPage.apply_row_colors(), so this delegate only handles group colors.
    """

    def paint(self, painter, option, index):
        proxy_model = index.model()

        # Current row's PalletNumber
        pallet_idx   = proxy_model.index(index.row(), 0)
        current_pallet = str(proxy_model.data(pallet_idx) or "").strip()

        has_trans = False
        has_taper = False

        for r in range(proxy_model.rowCount()):
            p_idx = proxy_model.index(r, 0)
            if str(proxy_model.data(p_idx) or "").strip() == current_pallet:
                diam_idx = proxy_model.index(r, 3)
                diam_val = str(proxy_model.data(diam_idx) or "").lower()
                if "trans" in diam_val:
                    has_trans = True
                if "taper" in diam_val:
                    has_taper = True

        color = None
        if has_trans:
            color = QColor("#D1EAFF")
        elif has_taper:
            color = QColor("#FFE5CC")

        if color:
            painter.save()
            painter.fillRect(option.rect, color)
            painter.restore()

        super().paint(painter, option, index)


class TablePanel(QWidget):
    def __init__(self, title, parent=None):
        super().__init__(parent)
        self.title   = title
        self.headers = []

        # ------------------------------------------------------------------
        # Models — must be created BEFORE any reference to self.proxy_model.
        # BUG FIX 1 (original): self.filter_proxy = self.proxy_model was
        # written before self.proxy_model was assigned, causing AttributeError
        # on every construction.  Models are now built first, then the search
        # input is wired up below.
        # ------------------------------------------------------------------
        self.source_model = QStandardItemModel()
        self.proxy_model  = AdvancedFilterProxy()
        self.proxy_model.setSourceModel(self.source_model)

        # Public alias used by consumers (e.g. joblog_page.filter_table)
        self.filter_proxy = self.proxy_model

        # ------------------------------------------------------------------
        # Search input
        # ------------------------------------------------------------------
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Search and filter rows...")
        self.search_input.setMinimumHeight(38)
        self.search_input.setClearButtonEnabled(True)
        self.search_input.textChanged.connect(self.filter_text)

        # ------------------------------------------------------------------
        # Export button
        # ------------------------------------------------------------------
        export_btn = QPushButton("Export CSV")
        export_btn.setObjectName("secondary_button")
        export_btn.setMinimumHeight(38)
        export_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        export_btn.clicked.connect(self.export_data)

        # ------------------------------------------------------------------
        # Table view
        # ------------------------------------------------------------------
        self.table_view = QTableView()
        self.table_view.setItemDelegate(RowColorDelegate())
        self.table_view.setAlternatingRowColors(False)
        self.table_view.setStyleSheet("QTableView { background-color: transparent; }")
        self.table_view.setSortingEnabled(True)
        self.table_view.setModel(self.proxy_model)

        # ------------------------------------------------------------------
        # Layout
        # ------------------------------------------------------------------
        actions_header = QHBoxLayout()
        actions_header.setContentsMargins(0, 0, 0, 0)
        actions_header.setSpacing(15)

        title_lbl = QLabel(title)
        title_lbl.setStyleSheet("font-size: 15px; font-weight: bold; color: #333333;")

        actions_header.addWidget(title_lbl)
        actions_header.addStretch(1)
        actions_header.addWidget(self.search_input, stretch=2)
        actions_header.addWidget(export_btn)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        layout.addLayout(actions_header)
        layout.addWidget(self.table_view)

    # --------------------------------------------------------------------------

    def filter_text(self, text):
        self.proxy_model.set_search_text(text)

    def set_rows(self, headers, rows):
        self.headers = headers
        self.source_model.clear()
        self.source_model.setHorizontalHeaderLabels(headers)
        for row in rows:
            items = [
                QStandardItem(" " if item is None else str(item))
                for item in row
            ]
            self.source_model.appendRow(items)
        self.table_view.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )

    def export_data(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Data Registry", "", "CSV Files (*.csv)"
        )
        if not path:
            return
        try:
            with open(path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(self.headers)
                for r in range(self.proxy_model.rowCount()):
                    row_data = []
                    for c in range(self.proxy_model.columnCount()):
                        idx = self.proxy_model.index(r, c)
                        row_data.append(self.proxy_model.data(idx) or "")
                    writer.writerow(row_data)
            QMessageBox.information(
                self, APP_TITLE, "Data matrix registry exported successfully."
            )
        except Exception as e:
            QMessageBox.critical(
                self, APP_TITLE, f"Export routine failure:\n{str(e)}"
            )