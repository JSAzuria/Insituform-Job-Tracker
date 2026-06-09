# database.py

import pyodbc
from config import ADHOC_CONFIG, EDW_CONFIG


def connection_string(config: dict) -> str:
    if config.get("trusted"):
        return (
            f"DRIVER={config['driver']};"
            f"SERVER={config['server']};"
            f"DATABASE={config['database']};"
            "Trusted_Connection=yes;"
        )

    return (
        f"DRIVER={config['driver']};"
        f"SERVER={config['server']};"
        f"DATABASE={config['database']};"
        f"UID={config['user']};"
        f"PWD={config['password']};"
    )


def adhoc_connect():
    return pyodbc.connect(connection_string(ADHOC_CONFIG))


def edw_connect():
    return pyodbc.connect(connection_string(EDW_CONFIG), timeout=30)