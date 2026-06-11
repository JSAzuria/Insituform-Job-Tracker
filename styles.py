# styles.py

NAV_DARK = "#07182C"
NAV_MID = "#0A3A66"
GLASS_BLUE = "#1D5C86"
ACCENT = "#E8650A"
SUCCESS = "#0A6A3A"
TEXT_DARK = "#0A1A2F"
TEXT_MID = "#4A5568"
SURFACE = "rgba(255,255,255,205)"

STYLE = f"""
/* Root main container window assignment */
QMainWindow {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #E7F2FB, stop:0.38 #CFE3F4, stop:0.72 #E9F2F8, stop:1 #F9FCFF);
    font-family: 'Segoe UI';
}}

/* Base structural element styling */
QWidget {{
    color: {TEXT_DARK};
    font-family: 'Segoe UI';
    font-size: 10pt;
}}

QWidget#root {{
    background: transparent;
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

QFrame#session_banner {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 rgba(255,139,53,245),
        stop:0.48 rgba(232,101,10,238),
        stop:1 rgba(180,70,8,230));
    border: 1px solid rgba(255,235,215,185);
    border-top: 1px solid rgba(255,255,255,210);
    border-left: 1px solid rgba(255,255,255,165);
    border-radius: 10px;
}}

QFrame#session_banner QLabel,
QLabel#session_user {{
    color: #081421;
    font-size: 13px;
    font-weight: 800;
    background: transparent;
    border: none;
}}

QPushButton#session_logout {{
    min-height: 30px;
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 rgba(255,255,255,108),
        stop:1 rgba(255,255,255,45));
    color: white;
    border: 1px solid rgba(255,255,255,150);
    border-radius: 6px;
    padding: 5px 14px;
    font-weight: 800;
}}

QPushButton#session_logout:hover {{
    background: rgba(255,255,255,90);
}}

QFrame#glass, QFrame#glass_card {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 rgba(255,255,255,238),
        stop:0.46 rgba(240,248,255,212),
        stop:1 rgba(202,225,244,178));
    border: 1px solid rgba(112,154,194,150);
    border-top: 1px solid rgba(255,255,255,245);
    border-left: 1px solid rgba(255,255,255,220);
    border-radius: 14px;
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
    font-size: 22px;
    font-weight: 800;
}}

QLabel#menuMainTitle {{
    color: {TEXT_DARK};
    font-size: 24px;
    font-weight: 900;
}}

QLabel#muted {{
    color: {TEXT_MID};
}}

QStatusBar#sync_status_bar {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 rgba(255,255,255,220),
        stop:1 rgba(210,230,246,190));
    border-top: 1px solid rgba(105,135,168,150);
    color: {TEXT_DARK};
    min-height: 30px;
}}

QLabel#sync_status_label {{
    color: {TEXT_DARK};
    font-weight: 700;
    padding-left: 8px;
}}

QProgressBar#sync_progress {{
    border: 1px solid rgba(78,119,163,185);
    border-radius: 5px;
    background: rgba(255,255,255,155);
    min-height: 12px;
    max-height: 12px;
}}

QProgressBar#sync_progress::chunk {{
    background: {ACCENT};
    border-radius: 4px;
}}

/* Inputs & Form Element Base Structure */
QLineEdit, QComboBox, QDateEdit {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 rgba(255,255,255,238),
        stop:1 rgba(235,245,253,205));
    border: 1px solid rgba(78,119,163,165);
    border-top: 1px solid rgba(255,255,255,255);
    border-left: 1px solid rgba(255,255,255,230);
    border-bottom: 1px solid rgba(62,92,126,150);
    border-radius: 10px;
    padding: 7px 10px;
    color: {TEXT_DARK};
    min-height: 28px;
}}

QLineEdit:focus, QComboBox:focus, QDateEdit:focus {{
    border: 2px solid {NAV_MID};
    background: rgba(255,255,255,245);
}}

QComboBox::drop-down {{
    width: 30px;
    border: none;
    background: transparent;
}}

/* Button Interface Matrix */
QPushButton {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 rgba(255,255,255,235),
        stop:0.52 rgba(233,244,253,205),
        stop:1 rgba(196,220,240,185));
    border: 1px solid rgba(116,145,176,150);
    border-top: 1px solid rgba(255,255,255,240);
    border-left: 1px solid rgba(255,255,255,210);
    border-bottom: 1px solid rgba(80,105,130,130);
    border-radius: 10px;
    padding: 9px 18px;
    font-weight: 700;
    color: {TEXT_DARK};
}}

QPushButton:hover {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 rgba(255,255,255,250),
        stop:1 rgba(226,240,251,225));
    border-color: {NAV_MID};
}}

QPushButton:pressed {{
    background: rgba(201,222,240,220);
    border-top: 1px solid rgba(72,103,135,140);
}}

QPushButton[accent="true"] {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #FF8A35,
        stop:0.48 {ACCENT},
        stop:1 #B84A08);
    color: white;
    border: 1px solid rgba(255,226,202,215);
    border-top: 1px solid rgba(255,255,255,190);
    border-bottom: 1px solid rgba(90,40,10,150);
}}

QPushButton[success="true"] {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #13A05B,
        stop:1 {SUCCESS});
    color: white;
    border: 1px solid rgba(170,220,190,190);
}}

QPushButton#menu_navigation_button {{
    min-height: 50px;
    text-align: left;
    padding-left: 18px;
    font-size: 13px;
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
    background: rgba(255,255,255,228);
    alternate-background-color: rgba(239,247,253,220);
    border: 1px solid rgba(105,135,168,150);
    border-top: 1px solid rgba(255,255,255,230);
    border-left: 1px solid rgba(255,255,255,210);
    border-radius: 12px;
    gridline-color: rgba(135,160,190,120);
    selection-background-color: {ACCENT};
    selection-color: white;
}}

QTableView::item {{
    padding: 5px;
}}

QTableView::item:hover {{
    background: #FFF0E6;
}}

QHeaderView::section {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #16476F,
        stop:1 #0C3157);
    color: white;
    padding: 8px;
    border: 0;
    border-right: 1px solid rgba(255,255,255,65);
    font-weight: 800;
}}
"""
