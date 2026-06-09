# widgets/table_panel.py

import csv
from PyQt6.QtWidgets import QStyledItemDelegate
from PyQt6.QtGui import QColor, QBrush
from PyQt6.QtCore import Qt
from PyQt6.QtCore import QSortFilterProxyModel, Qt
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
    QLabel
)
from config import APP_TITLE

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
class RowColorDelegate(QStyledItemDelegate):
    def paint(self, painter, option, index):
        proxy_model = index.model()
        
        # 1. Get the PalletNumber for the current row (Column 0)
        pallet_idx = proxy_model.index(index.row(), 0)
        current_pallet = str(proxy_model.data(pallet_idx) or "").strip()
        
        # 2. Scan the whole model for this PalletNumber
        has_trans = False
        has_taper = False
        
        for r in range(proxy_model.rowCount()):
            # Check PalletNumber column (0)
            p_idx = proxy_model.index(r, 0)
            if str(proxy_model.data(p_idx) or "").strip() == current_pallet:
                # Check Diameter column (3)
                diam_idx = proxy_model.index(r, 3)
                diam_val = str(proxy_model.data(diam_idx) or "").lower()
                
                if "trans" in diam_val: has_trans = True
                if "taper" in diam_val: has_taper = True

        # 3. Apply color based on group findings
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
        self.title = title

        # --- Inline Search Input ---
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Search and filter rows...")
        self.search_input.setMinimumHeight(38)
        self.search_input.setClearButtonEnabled(True)
        self.search_input.textChanged.connect(self.filter_text)

        # --- Data Export Action ---
        export_btn = QPushButton("Export CSV")
        export_btn.setObjectName("secondary_button")
        export_btn.setMinimumHeight(38)
        export_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        export_btn.clicked.connect(self.export_data)

        # --- Grid Presentation Views ---
        self.table_view = QTableView()
        
        # 1. Use the delegate for custom colors
        self.table_view.setItemDelegate(RowColorDelegate())
        
        # 2. IMPORTANT: Keep this FALSE so the stylesheet/view 
        # doesn't paint over your delegate's work.
        self.table_view.setAlternatingRowColors(False) 
        
        # 3. Transparent background allows the delegate to control the full row
        self.table_view.setStyleSheet("QTableView { background-color: transparent; }")
        
        self.table_view.setSortingEnabled(True)


        self.source_model = QStandardItemModel()
        self.proxy_model = ContainsFilterProxy()
        self.proxy_model.setSourceModel(self.source_model)
        self.table_view.setModel(self.proxy_model)

        # --- Component Layout Construction ---
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
        # 0 margins prevent compounding outer padding boundaries when embedded inside main page layouts
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        
        layout.addLayout(actions_header)
        layout.addWidget(self.table_view)

        self.headers = []

    def filter_text(self, text):
        self.proxy_model.set_search_text(text)

    def set_rows(self, headers, rows):
        self.headers = headers
        self.source_model.clear()
        self.source_model.setHorizontalHeaderLabels(headers)

        for row in rows:
            items = []
            for item in row:
                # Standardize empty/null fields to non-breaking structural spacing tokens
                items.append(QStandardItem(" " if item is None else str(item)))
            self.source_model.appendRow(items)
            
        self.table_view.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

    def export_data(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export Data Registry", "", "CSV Files (*.csv)")
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
            QMessageBox.information(self, APP_TITLE, "Data matrix registry exported successfully.")
        except Exception as e:
            QMessageBox.critical(self, APP_TITLE, f"Export routine failure:\n{str(e)}")