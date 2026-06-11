# JOBLOGTracker.py

import sys
import os
import ctypes  # Forces Windows to explicitly display the custom taskbar icon
from datetime import datetime
from PyQt6.QtWidgets import QApplication, QMainWindow, QLabel, QProgressBar, QStatusBar
from PyQt6.QtGui import QPixmap, QIcon
from PyQt6.QtCore import Qt, QTimer, pyqtSignal

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
    sync_status_changed = pyqtSignal(str, bool)

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

        self._setup_sync_status()
            
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

    def _setup_sync_status(self):
        status_bar = QStatusBar()
        status_bar.setObjectName("sync_status_bar")

        self.sync_status_label = QLabel("JOBLOG sync idle")
        self.sync_status_label.setObjectName("sync_status_label")

        self.sync_progress = QProgressBar()
        self.sync_progress.setObjectName("sync_progress")
        self.sync_progress.setRange(0, 100)
        self.sync_progress.setValue(0)
        self.sync_progress.setTextVisible(False)
        self.sync_progress.setFixedWidth(180)
        self.sync_progress.hide()

        self.sync_progress_timer = QTimer(self)
        self.sync_progress_timer.setInterval(1500)
        self.sync_progress_timer.timeout.connect(self._advance_sync_progress)
        self.sync_has_staged_rows = False
        self.sync_started_at = None
        self.sync_base_message = "JOBLOG sync idle"

        status_bar.addWidget(self.sync_status_label, 1)
        status_bar.addPermanentWidget(self.sync_progress)
        self.setStatusBar(status_bar)
        self.sync_status_changed.connect(self._set_sync_status)

    def _progress_floor_for_message(self, message):
        text = message.lower()
        if "background thread spawned" in text or "connected to database" in text:
            return 4
        if "connecting to local db" in text:
            return 8
        if "gating threshold" in text:
            return 14
        if "opening edw connection" in text or "opening database connection" in text:
            return 18
        if "executing edw extract query" in text or "executing database extract query" in text:
            return 24
        if "edw query accepted" in text or "database query accepted" in text:
            return 32
        if "pulled " in text and "staged " in text:
            self.sync_has_staged_rows = True
            return min(88, max(self.sync_progress.value() + 3, 36))
        if "executing server-side merge" in text:
            return 92
        if "commit successful" in text:
            return 100
        if "data connections safely closed" in text:
            return 100
        if "skipping sync" in text:
            return 100
        if "error trapped" in text or "suspended" in text:
            return 100
        return self.sync_progress.value()

    def _advance_sync_progress(self):
        current = self.sync_progress.value()
        cap = 49 if not self.sync_has_staged_rows else 90
        if current >= cap:
            self._update_sync_label()
            return

        if current < 35:
            self.sync_progress.setValue(current + 1)
        elif current < 75:
            self.sync_progress.setValue(min(current + 2, cap))
        elif current < 90:
            self.sync_progress.setValue(min(current + 1, cap))
        self._update_sync_label()

    def _elapsed_sync_text(self):
        if not self.sync_started_at:
            return "00:00"
        elapsed_seconds = max(0, int((datetime.now() - self.sync_started_at).total_seconds()))
        minutes, seconds = divmod(elapsed_seconds, 60)
        return f"{minutes:02d}:{seconds:02d}"

    def _update_sync_label(self):
        self.sync_status_label.setText(f"{self.sync_base_message}  |  {self._elapsed_sync_text()}")

    def _set_sync_status(self, message, busy):
        clean_message = str(message).replace("\n", " ").strip()
        if clean_message.startswith("[SYNC] "):
            clean_message = clean_message[7:]
        elif clean_message.startswith("[SYNC ALERT] "):
            clean_message = clean_message[13:]

        self.sync_base_message = clean_message or "JOBLOG sync idle"
        next_value = self._progress_floor_for_message(clean_message)

        if busy:
            self.sync_progress.setVisible(True)
            if self.sync_started_at is None or "background thread spawned" in clean_message.lower():
                self.sync_has_staged_rows = False
                self.sync_started_at = datetime.now()
                self.sync_progress.setValue(0)
            self.sync_progress.setValue(max(self.sync_progress.value(), next_value))
            if not self.sync_progress_timer.isActive():
                self.sync_progress_timer.start()
            self._update_sync_label()
        else:
            self.sync_progress_timer.stop()
            self.sync_progress.setVisible(True)
            self.sync_progress.setValue(next_value)
            self._update_sync_label()
            QTimer.singleShot(5000, self._hide_finished_sync_progress)

    def _hide_finished_sync_progress(self):
        if not self.sync_progress_timer.isActive():
            self.sync_progress.hide()
            self.sync_progress.setValue(0)
            self.sync_started_at = None

    def start_joblog_sync(self, *, force=False):
        from joblog_sync import run_automated_joblog_sync

        run_automated_joblog_sync(
            force=force,
            progress_callback=lambda message, busy=True: self.sync_status_changed.emit(message, busy),
        )

    def show_login(self):
        self.operator = None
        self.login = LoginPage(self)
        self.setCentralWidget(self.login)

    def show_role_home(self):
        from constants import ROLE_FULL_MENU, ROLE_JOBLOG_MENU

        self.start_joblog_sync()

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
            pages = [
                "View Current Headcount",
                "Add/Update Employee",
                "Assign Job to Line",
                "View/Update Assigned Production Lines",
                "Update Job Location",
                "View Joblog"
            ]
            if role == "Data Engineer":
                pages.insert(0, "Job Progress")
            return pages

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
