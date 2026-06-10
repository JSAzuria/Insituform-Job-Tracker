# JOBLOGTracker.py

import sys
import os
import ctypes  # Forces Windows to explicitly display the custom taskbar icon
from PyQt6.QtWidgets import QApplication, QMainWindow, QLabel
from PyQt6.QtGui import QPixmap, QIcon
from PyQt6.QtCore import Qt

from joblog_sync import run_automated_joblog_sync
from styles import STYLE
from constants import ROLE_FULL_MENU, ROLE_JOBLOG_MENU
from pages.login_page import LoginPage
from pages.menu_page import MenuPage
from pages.joblog_page import JoblogPage
from pages.assign_line_page import AssignLinePage
from pages.update_location_page import UpdateLocationPage
from pages.employee_page import EmployeePage
from pages.job_tracking_page import JobTrackingPage
from pages.headcount_page import HeadcountPage
from pages.assigned_line_page import AssignedLinePage
from pages.job_progress_page import JobProgressPage


class JoblogTracker(QMainWindow):
    def __init__(self):
        super().__init__()
        self.operator = None
        self.setWindowTitle("JOBLOG Tracker")
        
        # --- 1. Fix Windows Taskbar Icon Grouping ---
        try:
            myappid = 'insituform.joblogtracker.app.1'
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
        except Exception:
            pass

        # --- 2. Centralized Logo/Icon Path Resolution ---
        # Checks application directory root for deployment asset consistency
        self.logo_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "insituform-logo-png-transparent.ico")
        
        # Fallback to absolute standard workstation path if root hook isn't local
        if not os.path.exists(self.logo_path):
            fallback_path = r"C:\Users\jsartin\Documents\GitHub\Insituform_Job_Tracker\insituform-logo-png-transparent.ico"
            if os.path.exists(fallback_path):
                self.logo_path = fallback_path
            
        # --- 3. Set Application Window Icon ---
        if os.path.exists(self.logo_path):
            self.setWindowIcon(QIcon(self.logo_path))
        
        # Apply style layout sheets globally across elements
        try:
            self.setStyleSheet(STYLE)
        except Exception:
            pass
            
        self.show_login()
        
        # Forces the app to open full screen maximized across shop floor terminal layouts
        self.showMaximized()

    def get_logo_widget(self):
        """
        Generates the corporate brand logo label from the resolved icon path.
        """
        logo_label = QLabel()
        logo_label.setObjectName("logo")
        
        if os.path.exists(self.logo_path):
            pixmap = QPixmap(self.logo_path)
            # Smooth scaling ensures the asset looks crisp when sized for the header bar
            scaled_pixmap = pixmap.scaledToHeight(45, Qt.TransformationMode.SmoothTransformation)
            logo_label.setPixmap(scaled_pixmap)
        else:
            # High-contrast text fallback
            logo_label.setText("INSITUFORM")
            logo_label.setStyleSheet("font-size: 20px; font-weight: 900; color: #E8650A; letter-spacing: 1px;")
            
        return logo_label

    def show_login(self):
        self.operator = None
        self.login = LoginPage(self)
        self.setCentralWidget(self.login)

    def show_role_home(self):
        from constants import ROLE_FULL_MENU, ROLE_JOBLOG_MENU

        run_automated_joblog_sync()

        role = getattr(self.operator, "Role", "")

        if role in ROLE_FULL_MENU or role in ROLE_JOBLOG_MENU:
            self.menu = MenuPage(self)
            self.setCentralWidget(self.menu)
        else:
            self.navigate("Job Tracking")

    def available_pages(self):
        from constants import ROLE_FULL_MENU, ROLE_JOBLOG_MENU

        role = getattr(self.operator, "Role", "")

        if role in ROLE_FULL_MENU:
            return [
            "Job Progress",
            "View Current Headcount",
            "Add/Update Employee",
            "Assign Job to Line",
            "View/Update Assigned Production Lines",
            "Update Job Location",
            "View Joblog"
        ]

        elif role in ROLE_JOBLOG_MENU:
            return [
            "Assign Job to Line",
            "View/Update Assigned Production Lines",
            "Update Job Location",
            "View Joblog"
        ]

        else:
            return [
            "Job Tracking"
        ]

    def navigate(self, name):
        if name in ("Home", "Menu"):
            self.show_role_home()
        elif name == "Logout":
            self.show_login()
        elif name == "View Joblog":
            self.setCentralWidget(JoblogPage(self))
        elif name == "Assign Job to Line":
            self.setCentralWidget(AssignLinePage(self))
        elif name == "Update Job Location":
            self.setCentralWidget(UpdateLocationPage(self))
        elif name == "Add/Update Employee":
            self.setCentralWidget(EmployeePage(self))
        elif name == "Job Tracking":
            self.setCentralWidget(JobTrackingPage(self))
        elif name == "View Current Headcount":
            self.setCentralWidget(HeadcountPage(self))
        elif name == "View/Update Assigned Production Lines":
            self.setCentralWidget(AssignedLinePage(self))
        elif name == "Job Progress":
            self.setCentralWidget(JobProgressPage(self))


def main():
    app = QApplication(sys.argv)
    window = JoblogTracker()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()