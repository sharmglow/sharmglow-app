"""
SmartSklad Desktop v1.1
Установка:  pip install PyQt6 openpyxl python-barcode reportlab
Запуск:     python sharmglow.py
Сборка exe: pyinstaller --onefile --windowed --name SmartSklad sharmglow.py
"""

import sys, os, json
from pathlib import Path
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon

from db import DB
from app.app_context import AppContext
from ui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("SmartSklad")
    app.setStyle("Fusion")

    # Dark palette base
    from PyQt6.QtGui import QPalette, QColor
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window,          QColor(250, 247, 240))
    palette.setColor(QPalette.ColorRole.WindowText,      QColor(26,  18,  8))
    palette.setColor(QPalette.ColorRole.Base,            QColor(255, 255, 255))
    palette.setColor(QPalette.ColorRole.AlternateBase,   QColor(240, 235, 224))
    palette.setColor(QPalette.ColorRole.Button,          QColor(240, 235, 224))
    palette.setColor(QPalette.ColorRole.ButtonText,      QColor(26,  18,  8))
    palette.setColor(QPalette.ColorRole.Highlight,       QColor(184, 134, 11))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))
    app.setPalette(palette)

    db = DB()
    ctx = AppContext(db)

    window = MainWindow(ctx)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
