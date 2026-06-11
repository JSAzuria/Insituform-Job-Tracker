import csv
import re

from PyQt6.QtCore import QPointF, QRectF, Qt, QSortFilterProxyModel
from PyQt6.QtGui import QColor, QLinearGradient, QPainter, QPen, QStandardItem, QStandardItemModel
from PyQt6.QtWidgets import (
    QFileDialog,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QStyledItemDelegate,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from config import APP_TITLE

ROW_COLOR_ROLE = Qt.ItemDataRole.UserRole + 1

TEXT_HEAVY_HEADERS = {"Customer", "DESC", "Description", "Role", "Department", "SP APP"}


def normalized_pallet_key(value):
    text = str(value or "").strip()
    if text.startswith(("+", "-")):
        text = text[1:].strip()
    return text


class AdvancedFilterProxy(QSortFilterProxyModel):
    """Supports global text search plus key=value table filters."""

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
        key_map = {
            "pallet": 0,
            "p": 0,
            "job": 1,
            "j": 1,
            "customer": 2,
            "c": 2,
            "diameter": 3,
            "d": 3,
            "thickness": 4,
            "t": 4,
            "length": 5,
            "l": 5,
            "shipby": 6,
            "sp_app": 7,
            "desc": 8,
        }

        pattern = r"(\b[a-zA-Z_ ]+)\s*=\s*([^=]+?)(?=\s+\b[a-zA-Z_ ]+\s*=|$)"
        conditions = []
        for key, raw_value in re.findall(pattern, text):
            normalized_key = " ".join(key.split())
            if normalized_key in key_map:
                conditions.append((key_map[normalized_key], raw_value.strip()))

        if conditions:
            for col, value in conditions:
                idx = model.index(source_row, col, source_parent)
                if value not in str(model.data(idx) or "").lower():
                    return False
            return True

        for col in range(model.columnCount()):
            idx = model.index(source_row, col, source_parent)
            if text in str(model.data(idx) or "").lower():
                return True

        return False


class RowColorDelegate(QStyledItemDelegate):
    """Paints pallet group colors from row metadata instead of scanning on paint."""

    def paint(self, painter, option, index):
        color_name = index.data(ROW_COLOR_ROLE)
        color = QColor(color_name) if color_name else None
        text = str(index.data() or "")

        if color and color.isValid():
            painter.save()
            painter.fillRect(option.rect, color)
            painter.restore()

        if index.column() == 0 and text.strip().startswith(("+", "-")):
            self._paint_expander_cell(painter, option, text)
            return

        super().paint(painter, option, index)

    def _paint_expander_cell(self, painter, option, text):
        trimmed = text.strip()
        symbol = trimmed[0]
        pallet_text = trimmed[1:].strip()
        rect = option.rect
        button_size = min(18, max(16, rect.height() - 14))
        button_rect = QRectF(
            rect.left() + 8,
            rect.top() + (rect.height() - button_size) / 2,
            button_size,
            button_size,
        )

        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        glass = QLinearGradient(button_rect.topLeft(), button_rect.bottomLeft())
        glass.setColorAt(0, QColor(255, 255, 255, 245))
        glass.setColorAt(0.55, QColor(232, 240, 249, 220))
        glass.setColorAt(1, QColor(190, 212, 235, 210))

        painter.setBrush(glass)
        painter.setPen(QPen(QColor(92, 128, 165, 190), 1))
        painter.drawRoundedRect(button_rect, 5, 5)

        highlight_rect = QRectF(
            button_rect.left() + 3,
            button_rect.top() + 3,
            button_rect.width() - 6,
            max(5, button_rect.height() * 0.35),
        )
        painter.setBrush(QColor(255, 255, 255, 90))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(highlight_rect, 3, 3)

        icon_pen = QPen(QColor(7, 24, 44), 1.4)
        icon_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(icon_pen)
        center = button_rect.center()
        arm = max(3.0, button_rect.width() * 0.22)
        painter.drawLine(
            QPointF(center.x() - arm, center.y()),
            QPointF(center.x() + arm, center.y()),
        )
        if symbol == "+":
            painter.drawLine(
                QPointF(center.x(), center.y() - arm),
                QPointF(center.x(), center.y() + arm),
            )

        text_rect = QRectF(
            button_rect.right() + 8,
            rect.top(),
            max(0, rect.right() - button_rect.right() - 12),
            rect.height(),
        )
        painter.setFont(option.font)
        painter.setPen(QColor(7, 24, 44))
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, pallet_text)
        painter.restore()


class TablePanel(QWidget):
    """Reusable searchable/exportable table panel used by joblog pages."""

    def __init__(self, title, parent=None):
        super().__init__(parent)
        self.title = title
        self.headers = []

        self.source_model = QStandardItemModel()
        self.proxy_model = AdvancedFilterProxy()
        self.proxy_model.setSourceModel(self.source_model)
        self.filter_proxy = self.proxy_model

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search and filter rows...")
        self.search_input.setMinimumHeight(38)
        self.search_input.setClearButtonEnabled(True)
        self.search_input.textChanged.connect(self.filter_text)

        export_btn = QPushButton("Export CSV")
        export_btn.setObjectName("secondary_button")
        export_btn.setMinimumHeight(38)
        export_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        export_btn.clicked.connect(self.export_data)

        self.table_view = QTableView()
        self.table_view.setItemDelegate(RowColorDelegate())
        self.table_view.setAlternatingRowColors(False)
        self.table_view.setSortingEnabled(True)
        self.table_view.setModel(self.proxy_model)
        self.table_view.setWordWrap(False)
        self.table_view.verticalHeader().setVisible(False)
        self.table_view.verticalHeader().setDefaultSectionSize(34)

        actions_header = QHBoxLayout()
        actions_header.setContentsMargins(0, 0, 0, 0)
        actions_header.setSpacing(15)

        title_lbl = QLabel(title)
        title_lbl.setObjectName("panelTitle")

        actions_header.addWidget(title_lbl)
        actions_header.addStretch(1)
        actions_header.addWidget(self.search_input, stretch=2)
        actions_header.addWidget(export_btn)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        layout.addLayout(actions_header)
        layout.addWidget(self.table_view)

    def filter_text(self, text):
        self.proxy_model.set_search_text(text)

    def set_rows(self, headers, rows):
        self.headers = headers
        self.source_model.clear()
        self.source_model.setHorizontalHeaderLabels(headers)
        row_color_by_pallet = self._row_colors_by_pallet(rows)

        for row in rows:
            row_color = row_color_by_pallet.get(normalized_pallet_key(row[0]))
            items = [QStandardItem(" " if item is None else str(item)) for item in row]
            for item in items:
                item.setToolTip(item.text())
            if row_color:
                for item in items:
                    item.setData(row_color, ROW_COLOR_ROLE)
            self.source_model.appendRow(items)

        self._size_columns(headers)

    def _size_columns(self, headers):
        header = self.table_view.horizontalHeader()
        header.setStretchLastSection(False)
        header.setMinimumSectionSize(72)

        for col, name in enumerate(headers):
            mode = (
                QHeaderView.ResizeMode.Stretch
                if name in TEXT_HEAVY_HEADERS
                else QHeaderView.ResizeMode.ResizeToContents
            )
            header.setSectionResizeMode(col, mode)

        self.table_view.resizeColumnsToContents()

        for col, name in enumerate(headers):
            if name in {"Pallet #", "Job #", "Badge #"}:
                header.setSectionResizeMode(col, QHeaderView.ResizeMode.Interactive)
                header.resizeSection(col, max(self.table_view.columnWidth(col), 112))
            elif name in {"ShipBy", "Ship By", "Hire Date"}:
                header.setSectionResizeMode(col, QHeaderView.ResizeMode.Interactive)
                header.resizeSection(col, max(self.table_view.columnWidth(col), 100))

    @staticmethod
    def _row_colors_by_pallet(rows):
        pallet_flags = {}
        for row in rows:
            if len(row) <= 3:
                continue
            pallet = normalized_pallet_key(row[0])
            diameter = str(row[3] or "").lower()
            flags = pallet_flags.setdefault(pallet, {"trans": False, "taper": False})
            flags["trans"] = flags["trans"] or "trans" in diameter
            flags["taper"] = flags["taper"] or "taper" in diameter

        colors = {}
        for pallet, flags in pallet_flags.items():
            if flags["trans"]:
                colors[pallet] = "#D1EAFF"
            elif flags["taper"]:
                colors[pallet] = "#FFE5CC"
        return colors

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
                for row in range(self.proxy_model.rowCount()):
                    row_data = []
                    for col in range(self.proxy_model.columnCount()):
                        idx = self.proxy_model.index(row, col)
                        row_data.append(self.proxy_model.data(idx) or "")
                    writer.writerow(row_data)
            QMessageBox.information(
                self, APP_TITLE, "Data matrix registry exported successfully."
            )
        except Exception as exc:
            QMessageBox.critical(
                self, APP_TITLE, f"Export routine failure:\n{str(exc)}"
            )
