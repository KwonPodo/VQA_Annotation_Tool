# main.py
"""
Video Question Answering Annotation Tool
- Visual Grounding (Temporal/Spatial)
- Question/Answer Annotation
"""

import os
import sys
from PySide6.QtWidgets import QApplication
from gui.main_window import MainWindow

def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()