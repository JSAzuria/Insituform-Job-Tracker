# styles.py

NAV_DARK = "#07182C"
NAV_MID = "#0A3A66"
ACCENT = "#E8650A"
TEXT_DARK = "#0A1A2F"
TEXT_MID = "#4A5568"

STYLE = f"""
/* Root main container window assignment */
QMainWindow {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #EAF1F8, stop:0.55 #D9E7F5, stop:1 #F7FAFD);
    font-family: 'Segoe UI';
}}

/* Base structural element styling */
QWidget {{
    color: {TEXT_DARK};
    font-family: 'Segoe UI';
    font-size: 10pt;
}}

QCheckBox {{
    color: #0A1A2F;
    spacing: 8px;
    font-weight: 600;
}}

QCheckBox::indicator {{
    width: 18px;
    height: 18px;
}}

/* Insituform Logo styling constraint */
QLabel#logo {{
    max-height: 60px;
    max-width: 250px;
    qproperty-alignment: 'AlignLeft | AlignVCenter';
}}

QFrame#header {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 {NAV_DARK}, stop:0.65 #0C3157, stop:1 #123E68);
    border-bottom: 1px solid rgba(255,255,255,80);
}}

QFrame#glass, QFrame#glass_card {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 rgba(255,255,255,230),
        stop:0.5 rgba(255,255,255,190),
        stop:1 rgba(226,238,250,170));
    border: 1px solid rgba(255,255,255,170);
    border-top: 1px solid rgba(255,255,255,245);
    border-radius: 16px;
}}

/* GLOBAL FIX: Force absolute background transparency for text labels 
   and checkboxes inside any light glass card layout variation.
*/
QFrame#glass QLabel, QFrame#glass_card QLabel,
QFrame#glass QCheckBox, QFrame#glass_card QCheckBox {{
    background: transparent;
    background-color: transparent;
    border: none;
}}

QFrame#darkGlass {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 rgba(16,65,106,235),
        stop:0.48 rgba(7,39,70,230),
        stop:1 rgba(5,25,46,235));
    border: 1px solid rgba(255,255,255,90);
    border-top: 1px solid rgba(255,255,255,145);
    border-radius: 16px;
}}

QFrame#darkGlass QLabel {{
    color: #EAF2FA;
    background: transparent;
    border: none;
}}

QLabel#brand {{
    color: {ACCENT};
    font-size: 12px;
    font-weight: 800;
}}

QLabel#heading {{
    color: white;
    font-size: 22px;
    font-weight: 800;
}}

QLabel#subheading {{
    color: #B9C7D8;
}}

QLabel#sectionTitle {{
    color: {TEXT_DARK};
    font-size: 18px;
    font-weight: 800;
}}

QLabel#muted {{
    color: {TEXT_MID};
}}

/* Inputs & Form Element Base Structure */
QLineEdit, QComboBox, QDateEdit {{
    background: rgba(255,255,255,245);
    border: 1px solid rgba(78,119,163,185);
    border-top: 1px solid rgba(255,255,255,255);
    border-bottom: 1px solid rgba(62,92,126,170);
    border-radius: 8px;
    padding: 6px 10px;
    color: {TEXT_DARK};
}}

QLineEdit:focus, QComboBox:focus, QDateEdit:focus {{
    border: 2px solid {NAV_MID};
    background: #FFFFFF;
}}

/* Button Interface Matrix */
QPushButton {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 rgba(255,255,255,220),
        stop:0.52 rgba(224,236,248,195),
        stop:1 rgba(192,212,232,190));
    border: 1px solid rgba(255,255,255,190);
    border-bottom: 1px solid rgba(80,105,130,120);
    border-radius: 11px;
    padding: 9px 18px;
    font-weight: 700;
    color: {TEXT_DARK};
}}

QPushButton:hover {{
    background: rgba(255,255,255,235);
}}

QPushButton[accent="true"] {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #FF8A35,
        stop:0.48 {ACCENT},
        stop:1 #B94E0B);
    color: white;
    border: 1px solid rgba(255,220,190,210);
    border-bottom: 1px solid rgba(90,40,10,150);
}}

/* Secondary Action Layouts (e.g., Panel CSV Data Exports) */
QPushButton#secondary_button {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #FFFFFF,
        stop:1 #EAF1F8);
    border: 1px solid #A2C0D9;
    border-bottom: 1px solid #6E91AF;
    color: {NAV_MID};
}}

QPushButton#secondary_button:hover {{
    background: #F2F7FC;
    border-color: {NAV_MID};
}}

/* Grid Representation Output Views */
QTableView {{
    background: rgba(255,255,255,235);
    alternate-background-color: #F3F7FB;
    border: 1px solid rgba(105,135,168,150);
    border-radius: 8px;
    gridline-color: rgba(135,160,190,120);
    selection-background-color: {ACCENT};
    selection-color: white;
}}

QHeaderView::section {{
    background: #0C3157;
    color: white;
    padding: 7px;
    border: 0;
    border-right: 1px solid rgba(255,255,255,65);
    font-weight: 800;
}}
"""