# config.py
import os

# Global application identity token
APP_TITLE = "JOBLOG Tracker"

# ==============================================================================
# DATABASE SERVICE CONNECTIONS & ACCESS CREDENTIALS
# ==============================================================================

# Adhoc Core Database Configuration Registry
ADHOC_CONFIG = {
    "driver": "{SQL Server}",
    "server": os.getenv("ADHOC_SERVER", "SQLPOWERBIPRD1"),
    "database": os.getenv("ADHOC_DATABASE", "ADHOC"),
    "user": os.getenv("ADHOC_USER", "svc-adhoc-db"),
    "password": os.getenv("ADHOC_PASSWORD", "A7M9mGNd3caK5ntU6Rg9BPAv!"),
}

# Enterprise Data Warehouse (EDW) Service Context Configuration
EDW_CONFIG = {
    "driver": "{SQL Server}",
    "server": os.getenv("EDW_SERVER", "SQLARGOSDEV1"),
    "database": os.getenv("EDW_DATABASE", "EDW"),
    "trusted": True,
}

# Aligned with standard tracking view targets declared in constants.py
EDW_JOBLOG_VIEWS = (
    "dbo.vw_Dim_JOBLOG_Creation",
)