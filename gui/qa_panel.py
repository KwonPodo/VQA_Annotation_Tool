import os
import json
import cv2
import numpy as np

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence, QShortcut, QPixmap, QImage
from PySide6.QtWidgets import (
    QMainWindow,
    QHBoxLayout,
    QVBoxLayout,
    QWidget,
    QPushButton,
    QLabel,
    QFileDialog,
    QGroupBox,
    QSplitter,
    QFrame,
    QCheckBox,
    QMessageBox,
    QScrollBar,
    QLineEdit,
    QScrollArea,
    QSpinBox,
    QGridLayout
)

from gui.annotation_panel import AnnotationPanel
from gui.object_panel import ObjectPanel
from gui.config import PANEL_WIDTH, PANEL_SPACING
class QAPanel(QGroupBox):
    """QA panel placeholder"""

    def __init__(self):
        super().__init__("Question & Answer")
        self.setMinimumWidth(PANEL_WIDTH - PANEL_SPACING * 2)
        layout = QVBoxLayout(self)

        # Placeholder content
        label = QLabel("QA categories and\ntext input will be here")
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet("color: #666; font-style: italic;")
        layout.addWidget(label)
