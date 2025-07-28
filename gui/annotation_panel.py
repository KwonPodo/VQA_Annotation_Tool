
from PySide6.QtWidgets import (
    QHBoxLayout,
    QVBoxLayout,
    QPushButton,
    QLabel,
    QGroupBox,
    QSpinBox,
)

from gui.config import HALF_PANEL_WIDTH, PANEL_SPACING

class AnnotationPanel(QGroupBox):
    """Annotation control panel placeholder"""

    def __init__(self):
        super().__init__("2. Annotation Controls")
        self.setMinimumWidth(200)
        self.setMaximumWidth(280)
        self.setMaximumHeight(480)
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
        segment_layout.setSpacing(8)
        segment_layout.setContentsMargins(10, 15, 10, 15)

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
        self.apply_segment_btn = QPushButton("Apply Time Segment (A)")
        self.apply_segment_btn.setEnabled(False)
        
        self.apply_segment_btn.setMinimumWidth(30)
        self.apply_segment_btn.setMinimumHeight(35)

        self.undo_segment_btn = QPushButton("Undo Time Segment")
        self.undo_segment_btn.setEnabled(False)
        self.undo_segment_btn.setMinimumWidth(30)
        self.undo_segment_btn.setMinimumHeight(35)


        segment_layout.addLayout(start_layout)
        segment_layout.addLayout(end_layout)
        segment_layout.addLayout(interval_layout)
        segment_layout.addSpacing(10)
        segment_layout.addWidget(self.apply_segment_btn)
        segment_layout.addSpacing(5)
        segment_layout.addWidget(self.undo_segment_btn)
        segment_layout.addSpacing(10)

        # Add to main layout
        layout.addWidget(segment_input_group)
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

    def set_navigation_mode(self, mode):
        """Update navigation mode display"""
        if mode == "frame":
            self.mode_label.setText("Mode: Frame Navigation")
            self.mode_label.setStyleSheet("font-weight: bold; color: #333;")
        elif mode == "segment":
            self.mode_label.setText("Mode: Segment Navigation")
            self.mode_label.setStyleSheet("font-weight: bold; color: #007acc;")