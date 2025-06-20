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

from gui.config import HALF_PANEL_WIDTH, PANEL_SPACING

class AnnotationPanel(QGroupBox):
    """Annotation control panel placeholder"""

    def __init__(self):
        super().__init__("Annotation Controls")
        self.setFixedWidth(HALF_PANEL_WIDTH)
        self.setMaximumHeight(380)
        layout = QVBoxLayout(self)

        # Current navigation mode display
        self.mode_label = QLabel("Mode: Frame Navigation")
        self.mode_label.setStyleSheet(
            "font-weight: bold; color: #333; margin-bottom: 5px;"
        )
        layout.addWidget(self.mode_label)

        # Time segment input
        segment_input_group = QGroupBox("Set Time Segment")
        segment_layout = QVBoxLayout(segment_input_group)

        # Start frame input
        start_layout = QHBoxLayout()
        start_layout.addWidget(QLabel("Start Frame:"))
        self.start_frame_input = QSpinBox()
        self.start_frame_input.setMinimum(0)
        self.start_frame_input.setMaximum(999999)
        self.start_frame_input.setValue(0)
        start_layout.addWidget(self.start_frame_input)

        # End frame input
        end_layout = QHBoxLayout()
        end_layout.addWidget(QLabel("End Frame:"))
        self.end_frame_input = QSpinBox()
        self.end_frame_input.setMinimum(0)
        self.end_frame_input.setMaximum(999999)
        self.end_frame_input.setValue(100)
        end_layout.addWidget(self.end_frame_input)

        # Interval input
        interval_layout = QHBoxLayout()
        interval_layout.addWidget(QLabel("Sample Interval:"))
        self.interval_input = QSpinBox()
        self.interval_input.setMinimum(1)
        self.interval_input.setMaximum(999999)
        self.interval_input.setValue(10)
        self.interval_input.setSuffix(" frames")
        interval_layout.addWidget(self.interval_input)

        # Apply & Undo segment button
        self.apply_segment_btn = QPushButton("Apply Time Segment")
        self.apply_segment_btn.setEnabled(False)
        self.apply_segment_btn.setMinimumWidth(30)

        self.undo_segment_btn = QPushButton("Undo Time Segment")
        self.undo_segment_btn.setEnabled(False)
        self.undo_segment_btn.setMinimumWidth(30)


        segment_layout.addLayout(start_layout)
        segment_layout.addLayout(end_layout)
        segment_layout.addLayout(interval_layout)
        segment_layout.addWidget(self.apply_segment_btn)
        segment_layout.addWidget(self.undo_segment_btn)

        # Segment info display
        self.segment_info_label = QLabel("No segment selected")
        self.segment_info_label.setStyleSheet(
            "color: #666; font-style: italic; margin: 5px 0;"
        )

        # Navigation mode controls
        nav_group = QGroupBox("Navigation Mode")
        nav_layout = QVBoxLayout(nav_group)

        self.frame_mode_btn = QPushButton("Switch to Frame Mode")
        self.segment_mode_btn = QPushButton("Switch to Segment Mode")
        self.frame_mode_btn.setEnabled(False)
        self.segment_mode_btn.setEnabled(False)

        nav_layout.addWidget(self.frame_mode_btn)
        nav_layout.addWidget(self.segment_mode_btn)

        # Add to main layout
        layout.addWidget(segment_input_group)
        layout.addWidget(self.segment_info_label)
        layout.addWidget(nav_group)
        layout.addStretch()

    def set_video_info(self, total_frames):
        """Update input limits based on video info"""
        self.start_frame_input.setMaximum(total_frames - 1)
        self.end_frame_input.setMaximum(total_frames - 1)
        self.end_frame_input.setValue(min(100, total_frames - 1))
        self.apply_segment_btn.setEnabled(True)

    def get_segment_info(self):
        """Get current segment configuration"""
        return {
            "start_frame": self.start_frame_input.value(),
            "end_frame": self.end_frame_input.value(),
            "interval": self.interval_input.value(),
        }

    def update_segment_info(self, sampled_frames):
        """Update segment info display"""
        if sampled_frames:
            start = sampled_frames[0]
            end = sampled_frames[-1]
            count = len(sampled_frames)
            self.segment_info_label.setText(
                f"Segment: {start}-{end}\n{count} sampled frames"
            )
            self.segment_mode_btn.setEnabled(True)
        else:
            self.segment_info_label.setText("No segment selected")
            self.segment_mode_btn.setEnabled(False)

    def set_navigation_mode(self, mode):
        """Update navigation mode display"""
        if mode == "frame":
            self.mode_label.setText("Mode: Frame Navigation")
            self.mode_label.setStyleSheet("font-weight: bold; color: #333;")
            self.frame_mode_btn.setEnabled(False)
            self.segment_mode_btn.setEnabled(True)
        elif mode == "segment":
            self.mode_label.setText("Mode: Segment Navigation")
            self.mode_label.setStyleSheet("font-weight: bold; color: #007acc;")
            self.frame_mode_btn.setEnabled(True)
            self.segment_mode_btn.setEnabled(False)