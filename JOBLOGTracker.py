import csv
import re
import sys
import zipfile
from datetime import datetime, timedelta
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
