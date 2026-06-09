# helpers.py

import re
from datetime import datetime, date


def app_date_text(value):
  """Converts a datetime, date, or string representation to an MM-DD-YYYY formatted string."""
  if value is None:
    return ""

  # 1. Handle native datetime/date objects directly returned by database cursors
  if isinstance(value, (datetime, date)):
    return value.strftime("%m-%d-%Y")

  # 2. Handle string representation variations
  if isinstance(value, str):
    cleaned_value = value.strip()
    if not cleaned_value:
      return ""

    # Robustly pull out the core date component by splitting off trailing times or ISO 'T' separators
    # This safely isolates the date portion from strings like "MM/DD/YYYY HH:MM:SS" or "YYYY-MM-DDTHH:MM:SS"
    date_part = cleaned_value.split()[0].split('T')[0].strip()

    # Fallback matrix parsing for varying spreadsheet or manually entered date layouts
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%Y/%m/%d", "%m-%d-%Y"):
      try:
        return datetime.strptime(date_part, fmt).strftime("%m-%d-%Y")
      except ValueError:
        continue

  # Fall back to raw string conversion if all parsing formats fail
  return str(value)


def as_int_or_none(raw):
  """Converts a raw string/number scanner value into an integer or returns None for fallback values."""
  if raw in (None, "", "NR"):
    return None
  try:
    return int(float(raw))
  except (TypeError, ValueError):
    return None


def value(row, name, default=None):
  """Safely returns an attribute value from a row dataset object with a fallback default."""
  try:
    return getattr(row, name)
  except AttributeError:
    return default


def pull_sp_app_flags(sp_app):
  """Parses a special application token string and extracts specific flag criteria matches."""
  text = (sp_app or "").upper()

  return (
    1 if "ME" in text else None,
    1 if "SR" in text else None,
    1 if "PS" in text or "FPS" in text else None,
  )


def excel_col_name(index):
  """Converts a 0-indexed column integer count cleanly to an Excel alpha reference string (e.g. A, B, Z, AA)."""
  name = ""
  index += 1

  while index:
    index, remainder = divmod(index - 1, 26)
    name = chr(65 + remainder) + name

  return name


def configure_date_edit(date_edit):
  """Configures a QDateEdit widget with a calendar popup, standard format,
  sets it to the current date, and applies standard terminal touch cursor prompts.
  """
  from PyQt6.QtCore import QDate
  from PyQt6.QtCore import Qt

  date_edit.setCalendarPopup(True)
  date_edit.setDisplayFormat("MM-dd-yyyy")
  date_edit.setDate(QDate.currentDate())

  # Enforces high-visibility cursor boundaries for shop floor touch screen terminals
  date_edit.setCursor(Qt.CursorShape.PointingHandCursor)