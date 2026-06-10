# constants.py

# ==============================================================================
# DATA FILTERS & TEXT STRING CRITERIA
# ==============================================================================
EXCLUDED_WORK_DESCRIPTION_TERMS = (
    "Plate",
    "Connector",
    "Additional",
    "Starter",
    "charge",
)

EXCLUDED_WORK_DESCRIPTION_WORDS = ("ME",)


# ==============================================================================
# OPERATOR ROLE ACCESS ROSTERS (Alphabetized Lists for UI Stability)
# ==============================================================================
ROLE_FULL_MENU = [
    "Admin Assistant",
    "Data Engineer",
    "Human Resources Generalist",
    "Production Supervisor",
    "Plant Manager",
    "Plant Production Manager",
]

ROLE_JOBLOG_MENU = [
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
    "Material Control Clerk MFG",
    "Material Planner",
    "Product Services Scheduler",
    "Production Control Lead",
    "Production Foreman",
    "Production Scheduler MFG",
    "Quality Control Engineer",
    "Scheduling Coordinator",
    "Senior Quality Manager",
    "Staff Accountant",
    "Supply Chain Manager",
]


# ==============================================================================
# SHOP FLOOR LINE & OPERATION SEQUENCING OPTIONS
# ==============================================================================
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

# Dynamically derived to keep processing matrices strictly DRY
TRACKING_PROCESS_OPTIONS = [opt for opt in PROCESS_OPTIONS if opt != "Allot"]

JOIN_LINE_OPTIONS = ["NR", "13", "14", "15", "17"]
INNER_SEW_OPTIONS = ["4", "6", "7", "9", "10", "11", "13", "14", "15"]
OUTER_SEW_OPTIONS = ["5", "6", "7", "9", "10", "11", "13", "14", "15"]
EXTRUSION_OPTIONS = ["NR", "1", "3", "12", "14", "15"]
INSPECTION_OPTIONS = ["1", "2", "12", "14", "15"]


# ==============================================================================
# ENTERPRISE DATA WAREHOUSE (EDW) DATABASE CONFIGURATIONS
# ==============================================================================
EDW_JOBLOG_VIEW = "dbo.vw_Dim_JOBLOG_Creation"

# Query injection filter used across job log tracking grid matrices
ACTIVE_JOBTRACKING_FILTER = """
    NOT EXISTS (
        SELECT 1
        FROM dbo.JobTracking jt
        WHERE jt.JobNumber = CONVERT(nvarchar(50), j.JobNumber)
          AND jt.Operation  = 'Special Apps'
          AND jt.EventType  = 'Complete'
    )
"""


# ==============================================================================
# LOGISTICS CUSTOMER BRANCH GLOSSARY MAPPINGS
# ==============================================================================
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