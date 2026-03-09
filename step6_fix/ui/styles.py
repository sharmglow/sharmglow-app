"""ui/styles.py — Shared stylesheet and color constants"""

GOLD   = "#b8860b"
GOLD_L = "#d4a017"
INK    = "#1a1208"
CREAM  = "#faf7f0"
PAPER  = "#f0ebe0"
MUTED  = "#8a7f6e"
BORDER = "#d4c9b0"
WB     = "#7b1fa2"
WB_LT  = "#f3e5f5"
OZ     = "#0d47a1"
OZ_LT  = "#e3f2fd"
OK     = "#1b5e20"
OK_BG  = "#e8f5e9"
WARN   = "#e65100"
WARN_BG= "#fff3e0"
DANGER = "#b71c1c"
DANGER_BG = "#ffebee"

APP_STYLE = f"""
QMainWindow, QDialog {{
    background: {CREAM};
}}
QWidget {{
    font-family: 'Segoe UI', Arial, sans-serif;
    font-size: 13px;
    color: {INK};
}}
QTabWidget::pane {{
    border: 1px solid {BORDER};
    background: white;
    border-radius: 4px;
}}
QTabBar::tab {{
    background: {PAPER};
    color: {MUTED};
    padding: 8px 20px;
    border: 1px solid {BORDER};
    border-bottom: none;
    border-top-left-radius: 5px;
    border-top-right-radius: 5px;
    font-weight: 500;
    min-width: 100px;
}}
QTabBar::tab:selected {{
    background: white;
    color: {INK};
    font-weight: 600;
    border-bottom: 2px solid {GOLD};
}}
QTabBar::tab:hover:!selected {{
    background: {CREAM};
    color: {INK};
}}
QPushButton {{
    background: {PAPER};
    border: 1px solid {BORDER};
    border-radius: 5px;
    padding: 7px 16px;
    font-weight: 500;
    min-height: 28px;
}}
QPushButton:hover {{
    background: {BORDER};
}}
QPushButton:pressed {{
    background: {GOLD};
    color: white;
}}
QPushButton#primary {{
    background: {INK};
    color: #d4a017;
    border-color: {INK};
    font-weight: 600;
}}
QPushButton#primary:hover {{
    background: {GOLD};
    color: {INK};
}}
QPushButton#danger {{
    background: white;
    color: {DANGER};
    border-color: {DANGER};
}}
QPushButton#danger:hover {{
    background: {DANGER};
    color: white;
}}
QPushButton#wb {{
    background: {WB_LT};
    color: {WB};
    border-color: {WB};
    font-weight: 700;
}}
QPushButton#ozon {{
    background: {OZ_LT};
    color: {OZ};
    border-color: {OZ};
    font-weight: 700;
}}
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox, QTextEdit {{
    background: white;
    border: 1px solid {BORDER};
    border-radius: 5px;
    padding: 6px 10px;
    min-height: 28px;
}}
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus,
QComboBox:focus, QTextEdit:focus {{
    border: 2px solid {GOLD};
}}
QTableWidget {{
    background: white;
    border: 1px solid {BORDER};
    border-radius: 4px;
    gridline-color: {PAPER};
    alternate-background-color: {CREAM};
}}
QTableWidget::item {{
    padding: 4px 8px;
}}
QTableWidget::item:selected {{
    background: #fff8e7;
    color: {INK};
}}
QHeaderView::section {{
    background: {PAPER};
    border: none;
    border-bottom: 2px solid {BORDER};
    border-right: 1px solid {BORDER};
    padding: 6px 10px;
    font-weight: 600;
    font-size: 11px;
    color: {MUTED};
    text-transform: uppercase;
    letter-spacing: 0.05em;
}}
QLabel#title {{
    font-size: 18px;
    font-weight: 700;
    color: {INK};
}}
QLabel#subtitle {{
    font-size: 11px;
    color: {MUTED};
    letter-spacing: 0.1em;
    text-transform: uppercase;
}}
QLabel#section {{
    font-size: 11px;
    font-weight: 600;
    color: {MUTED};
    text-transform: uppercase;
    letter-spacing: 0.12em;
    padding-bottom: 4px;
    border-bottom: 1px solid {PAPER};
}}
QGroupBox {{
    border: 1px solid {BORDER};
    border-radius: 6px;
    margin-top: 14px;
    padding: 10px;
    font-weight: 600;
    color: {MUTED};
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 6px;
    color: {MUTED};
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.1em;
}}
QScrollBar:vertical {{
    background: {CREAM};
    width: 8px;
    border-radius: 4px;
}}
QScrollBar::handle:vertical {{
    background: {BORDER};
    border-radius: 4px;
    min-height: 20px;
}}
QScrollBar::handle:vertical:hover {{
    background: {MUTED};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QStatusBar {{
    background: {INK};
    color: #888;
    font-size: 11px;
    padding: 0 10px;
}}
QMenuBar {{
    background: {INK};
    color: #ccc;
    padding: 2px;
}}
QMenuBar::item:selected {{
    background: {GOLD};
    color: {INK};
    border-radius: 3px;
}}
QMenu {{
    background: white;
    border: 1px solid {BORDER};
    border-radius: 4px;
    padding: 4px;
}}
QMenu::item {{
    padding: 6px 20px 6px 12px;
    border-radius: 3px;
}}
QMenu::item:selected {{
    background: {CREAM};
}}
QSplitter::handle {{
    background: {BORDER};
    width: 1px;
}}
"""
