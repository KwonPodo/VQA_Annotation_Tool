# gui/main_window.py
"""
Main Window for Video QA Annotation Tool
"""

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
    QGridLayout,
    QDialog
)

from gui.annotation_panel import AnnotationPanel
from gui.object_panel import ObjectPanel
from gui.qa_panel import QAPanel
from gui.config import PANEL_WIDTH, PANEL_SPACING, track_id_color_palette


class VideoCanvas(QLabel):
    """Video Display Canvas"""

    def __init__(self):
        super().__init__()
        self.setMinimumSize(500, 300)
        self.setStyleSheet("border: 2px solid #cccccc; background-color: #f5f5f5;")
        self.setAlignment(Qt.AlignCenter)
        self.setText("Load Video File\n(Video Canvas)")

        # Video properties
        self.video_cap = None
        self.current_frame = 0
        self.total_frames = 0
        self.fps = 0

        # Bounding box annotation state
        self.bbox_mode = False
        self.available_objects = [] # objects selected from object panel
        self.is_drawing = False
        self.start_point = None
        self.end_point = None
        self.scale_factor = 1.0

        # Store bboxes with track_id
        self.frame_bboxes = {} # Dict[frame_index: List[bbox_list]]

        # Track ID management
        self.existing_track_ids = {} # Dict[object_type: List[track_id]]

        self.track_registry = {} # Dict[object_type: List[track_id]]
        self.color_palette = track_id_color_palette
        self.color_index = 0

    def load_video(self, file_path):
        """Load video file"""
        if self.video_cap:
            self.video_cap.release()

        self.video_cap = cv2.VideoCapture(file_path)
        if self.video_cap.isOpened():
            self.total_frames = int(self.video_cap.get(cv2.CAP_PROP_FRAME_COUNT))
            self.fps = self.video_cap.get(cv2.CAP_PROP_FPS)
            self.current_frame = 0
            self.set_frame(0)
            return True

        return False

    def set_frame(self, frame_index):
        """Set current frame index"""
        if not self.video_cap or frame_index < 0 or frame_index >= self.total_frames:
            return False

        self.video_cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
        ret, frame = self.video_cap.read()

        if ret:
            self.current_frame = frame_index

            # Convert BGR to RGB
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb_frame.shape
            bytes_per_line = ch * w

            # Create QImage and scale to fit canvas
            qt_image = QImage(
                rgb_frame.data, w, h, bytes_per_line, QImage.Format_RGB888
            )
            canvas_size = self.size()
            scaled_pixmap = QPixmap.fromImage(qt_image).scaled(
                canvas_size, Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            self.setPixmap(scaled_pixmap)
            return True
        return False

    def next_frame(self):
        """Go to next frame"""
        if self.current_frame < self.total_frames - 1:
            return self.set_frame(self.current_frame + 1)
        return False

    def prev_frame(self):
        """Go to previous frame"""
        if self.current_frame > 0:
            return self.set_frame(self.current_frame - 1)
        return False
    
    def enable_bbox_mode(self, available_objects):
        """Enable bbox annotation mode"""
        self.bbox_mode = True
        self.available_objects = available_objects
        self.set_Cursor(Qt.CrossCursor)
        print(f'BBox mode enabled for {available_objects}')
    
    def disable_bbox_mode(self):
        """Disable bbox annotation mode"""
        self.bbox_mode = False
        self.available_objects = []
        self.setCursor(Qt.ArrowCursor)
        self.is_drawing = False
        print('BBox mode disabled')
    
    def get_next_color(self):
        """Get next color from color palette"""
        color = self.color_palette[self.color_index % len(self.color_palette)]
        self.color_index += 1
        return color
    
    def add_bbox_with_annotation(self, x, y, width, height, object_type, track_id):
        """Add annotated bounding box to current frame"""
        # Assign color if new track_id
        if track_id not in self.track_registry:
            self.track_registry[track_id] = self.get_next_color()
        
        bbox = {
            'id' : f'bbox_{len(self.frame_bboxes.get(self.current_frame, []))}',
            'x': x,
            'y': y,
            'width': width,
            'height': height,
            'object_type': object_type,
            'track_id': track_id,
            'color': self.track_registry[track_id]
        }

        if self.current_frame not in self.frame_bboxes:
            self.frame_bboxes[self.current_frame] = []
        
        self.frame_bboxes[self.current_frame].append(bbox)

        # Update track_id registry
        if object_type not in self.existing_track_ids:
            self.existing_track_ids[object_type] = []
        
        if track_id not in self.existing_track_ids[object_type]:
            self.existing_track_ids[object_type].append(track_id)
        print(f'Added bbox: {object_type} - {track_id}')
        self.update()
    
    def show_annotation_dialog(self, x, y, width, height):
        """Show annotation dialog for bounding box"""
        from gui.bbox_dialog import BBoxAnnotationDialog
        
        dialog = BBoxAnnotationDialog(
            available_objects=self.available_objects,
            existing_track_ids=self.existing_track_ids.copy(),
            parent=self
        )
        
        if dialog.exec() == QDialog.Accepted:
            object_type, track_id = dialog.get_annotation_result()
            if object_type and track_id:
                self.add_bbox_with_annotation(x, y, width, height, object_type, track_id)
                return True
        return False

    def undo_last_bbox(self):
        """Remove the last bounding box from current frame"""
        if self.current_frame in self.frame_bboxes:
            bboxes = self.frame_bboxes[self.current_frame]
            if bboxes:
                removed = bboxes.pop()
                print(f"Removed bbox: {removed['object_type']} - {removed['track_id']}")
                self.update()  # Trigger repaint
                return True
        return False

    def clear_current_frame_bboxes(self):
        """Clear all bboxes from current frame"""
        if self.current_frame in self.frame_bboxes:
            count = len(self.frame_bboxes[self.current_frame])
            self.frame_bboxes[self.current_frame] = []
            print(f"Cleared {count} bboxes from frame {self.current_frame}")
            self.update()  # Trigger repaint
            return count
        return 0

    def canvas_to_image_coords(self, canvas_point):
        """Convert canvas coordinates to image coordinates"""
        if not self.pixmap():
            return None
        
        pixmap = self.pixmap()
        canvas_rect = self.rect()
        pixmap_rect = pixmap.rect()
        
        # Calculate offset (image is centered in canvas)
        x_offset = (canvas_rect.width() - pixmap_rect.width()) // 2
        y_offset = (canvas_rect.height() - pixmap_rect.height()) // 2
        
        # Convert to image coordinates
        img_x = int((canvas_point.x() - x_offset) / self.scale_factor)
        img_y = int((canvas_point.y() - y_offset) / self.scale_factor)
        
        return (img_x, img_y)

    def image_to_canvas_coords(self, img_point):
        """Convert image coordinates to canvas coordinates"""
        if not self.pixmap():
            return None
        
        pixmap = self.pixmap()
        canvas_rect = self.rect()
        pixmap_rect = pixmap.rect()
        
        x_offset = (canvas_rect.width() - pixmap_rect.width()) // 2
        y_offset = (canvas_rect.height() - pixmap_rect.height()) // 2
        
        canvas_x = int(img_point[0] * self.scale_factor + x_offset)
        canvas_y = int(img_point[1] * self.scale_factor + y_offset)
        
        return (canvas_x, canvas_y)

    # Mouse events for bounding box drawing
    def mousePressEvent(self, event):
        """Handle mouse press for bbox drawing"""
        if not self.bbox_mode or event.button() != Qt.LeftButton:
            return
        
        self.is_drawing = True
        self.start_point = event.position().toPoint()
        self.end_point = self.start_point

    def mouseMoveEvent(self, event):
        """Handle mouse move for bbox preview"""
        if not self.bbox_mode or not self.is_drawing:
            return
        
        self.end_point = event.position().toPoint()
        self.update()  # Trigger repaint for preview

    def mouseReleaseEvent(self, event):
        """Handle mouse release to complete bbox and show annotation dialog"""
        if not self.bbox_mode or event.button() != Qt.LeftButton or not self.is_drawing:
            return
        
        self.is_drawing = False
        self.end_point = event.position().toPoint()
        
        # Convert to image coordinates
        start_img = self.canvas_to_image_coords(self.start_point)
        end_img = self.canvas_to_image_coords(self.end_point)
        
        if start_img and end_img:
            # Calculate bbox dimensions
            x = min(start_img[0], end_img[0])
            y = min(start_img[1], end_img[1])
            width = abs(end_img[0] - start_img[0])
            height = abs(end_img[1] - start_img[1])
            
            # Only add if bbox has minimum size
            if width > 10 and height > 10:
                self.show_annotation_dialog(x, y, width, height)

    def paintEvent(self, event):
        """Paint event to draw bboxes and preview"""
        super().paintEvent(event)
        
        if not self.pixmap():
            return
        
        from PySide6.QtGui import QPainter
        painter = QPainter(self)
        
        # Draw existing bboxes
        self.draw_existing_bboxes(painter)
        
        # Draw preview bbox while drawing
        if self.is_drawing and self.start_point and self.end_point:
            self.draw_preview_bbox(painter)

    def draw_existing_bboxes(self, painter):
        """Draw all existing bboxes for current frame"""
        if self.current_frame not in self.frame_bboxes:
            return
        
        from PySide6.QtGui import QPen, QColor
        from PySide6.QtCore import QRect
        
        for bbox in self.frame_bboxes[self.current_frame]:
            # Convert image coords to canvas coords
            top_left = self.image_to_canvas_coords((bbox['x'], bbox['y']))
            bottom_right = self.image_to_canvas_coords((bbox['x'] + bbox['width'], bbox['y'] + bbox['height']))
            
            if top_left and bottom_right:
                # Use track-specific color
                color = QColor(*bbox['color'])
                pen = QPen(color, 2)
                painter.setPen(pen)
                
                # Draw rectangle
                rect = QRect(top_left[0], top_left[1], 
                           bottom_right[0] - top_left[0], 
                           bottom_right[1] - top_left[1])
                painter.drawRect(rect)
                
                # Draw label with track ID
                label = f"{bbox['object_type']} - {bbox['track_id']}"
                painter.setPen(QPen(color, 1))
                painter.drawText(top_left[0], top_left[1] - 5, label)

    def draw_preview_bbox(self, painter):
        """Draw preview bbox while drawing"""
        from PySide6.QtGui import QPen, QColor
        from PySide6.QtCore import QRect
        
        pen = QPen(QColor(255, 0, 0), 2, Qt.DashLine)  # Red dashed line
        painter.setPen(pen)
        
        x = min(self.start_point.x(), self.end_point.x())
        y = min(self.start_point.y(), self.end_point.y())
        width = abs(self.end_point.x() - self.start_point.x())
        height = abs(self.end_point.y() - self.start_point.y())
        
        rect = QRect(x, y, width, height)
        painter.drawRect(rect)

    def get_frame_annotations(self, frame_num):
        """Get all annotations for a specific frame"""
        return self.frame_bboxes.get(frame_num, [])

    def get_all_annotations(self):
        """Get all annotations across all frames"""
        return self.frame_bboxes.copy()


class MainWindow(QMainWindow):
    """Main Application Window"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Video QA Annotation Tool")
        self.setGeometry(100, 100, 1200, 400)

        # Annotation State
        self.current_annotation = None
        self.sampled_frames = []
        self.current_segment_index = 0

        # Navigation mode : 'frame' or 'segment'
        self.navigation_mode = "frame"

        # Setup
        self.setup_ui()
        self.setup_connections()
        self.setup_keyboard_shortcuts()

        def print_sizes():
            print(f"ObjectPanel height: {self.object_panel.sizeHint().height()}")
            print(f"ObjectPanel width: {self.object_panel.sizeHint().width()}")
            print(
                f"AnnotationPanel height: {self.annotation_panel.sizeHint().height()}"
            )
            print(
                f"AnnotationPanel width: {self.annotation_panel.sizeHint().width()}"
            )
            print(f"QAPanel height: {self.qa_panel.sizeHint().height()}")
            print(f"QAPanel width: {self.qa_panel.sizeHint().width()}")
            print(f"VideoCanvas height: {self.video_canvas.sizeHint().height()}")
            print(f"VideoCanvas width: {self.video_canvas.sizeHint().width()}")

        # 윈도우가 보인 후에 크기 확인
        from PySide6.QtCore import QTimer

        QTimer.singleShot(100, print_sizes)

    def setup_ui(self):
        """Setup UI layout"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QHBoxLayout(central_widget)

        # Create main splitter
        main_splitter = QSplitter(Qt.Horizontal)

        # Left panel (video canvas)
        left_panel = self.create_left_panel()

        # Right panel (controls)
        right_panel = self.create_right_panel()

        main_splitter.addWidget(left_panel)
        main_splitter.addWidget(right_panel)

        # Set splitter proportions (left : video, right : panels)
        main_splitter.setSizes([800, PANEL_WIDTH])

        main_layout.addWidget(main_splitter)

    def create_left_panel(self):
        """Create left panel with video canvas and controls"""
        panel = QFrame()
        layout = QVBoxLayout(panel)

        # File operations
        file_group = QGroupBox("File Operations")
        file_layout = QHBoxLayout(file_group)

        self.load_video_btn = QPushButton("Load Video")
        self.save_annotation_btn = QPushButton("Save Annotation")
        self.load_annotation_btn = QPushButton("Load Annotation")

        file_layout.addWidget(self.load_video_btn)
        file_layout.addWidget(self.save_annotation_btn)
        file_layout.addWidget(self.load_annotation_btn)
        file_layout.addStretch()

        # Video canvas
        self.video_canvas = VideoCanvas()

        # Video controls
        video_controls_group = QGroupBox("Video Controls")
        video_controls_layout = QVBoxLayout(video_controls_group)

        # Frame info
        self.frame_info_label = QLabel("Frame: - / -")
        self.frame_info_label.setAlignment(Qt.AlignCenter)

        # Frame step controls
        step_layout = QHBoxLayout()
        step_layout.addWidget(QLabel('Frame Step:'))
        self.frame_step_input = QSpinBox()
        self.frame_step_input.setMinimum(1)
        self.frame_step_input.setMaximum(100)
        self.frame_step_input.setValue(1)
        self.frame_step_input.setSuffix(" frames")
        step_layout.addWidget(self.frame_step_input)
        step_layout.addStretch()

        # Navigation buttons
        nav_layout = QHBoxLayout()
        self.prev_frame_btn = QPushButton("◀ Previous Frame")
        self.next_frame_btn = QPushButton("Next Frame ▶")
        nav_layout.addWidget(self.prev_frame_btn)
        nav_layout.addWidget(self.next_frame_btn)

        # Segment buttons
        segment_layout = QHBoxLayout()
        self.prev_segment_btn = QPushButton("◀◀ Previous Segment")
        self.next_segment_btn = QPushButton("Next Segment ▶▶")

        self.prev_segment_btn.setEnabled(False)
        self.next_segment_btn.setEnabled(False)

        segment_layout.addWidget(self.prev_segment_btn)
        segment_layout.addWidget(self.next_segment_btn)

        video_controls_layout.addWidget(self.frame_info_label)
        video_controls_layout.addLayout(step_layout)
        video_controls_layout.addLayout(nav_layout)
        video_controls_layout.addLayout(segment_layout)

        # Add to layout
        layout.addWidget(file_group)
        layout.addWidget(self.video_canvas, 1)  # Give video canvas most space
        layout.addWidget(video_controls_group)

        return panel

    def create_right_panel(self):
        """Create right panel with annotation controls"""
        panel = QFrame()
        layout = QVBoxLayout(panel)

        # Top row: Object panel + Annotation panel
        top_row_layout = QHBoxLayout()

        # Object selection panel
        self.object_panel = ObjectPanel()

        # Annotation controls panel
        self.annotation_panel = AnnotationPanel()

        top_row_layout.addWidget(self.object_panel)
        top_row_layout.addWidget(self.annotation_panel)

        # Bottom Row : QA panel
        self.qa_panel = QAPanel()

        # Action buttons
        action_group = QGroupBox("Actions")
        action_layout = QVBoxLayout(action_group)

        self.start_annotation_btn = QPushButton("Start New Annotation")
        self.finish_annotation_btn = QPushButton("Finish Current Annotation")
        self.reset_annotation_btn = QPushButton("Reset Annotation")

        # Initially disable some buttons
        self.finish_annotation_btn.setEnabled(False)
        self.reset_annotation_btn.setEnabled(False)
        self.save_annotation_btn.setEnabled(False)

        action_layout.addWidget(self.start_annotation_btn)
        action_layout.addWidget(self.finish_annotation_btn)
        action_layout.addWidget(self.reset_annotation_btn)

        # Add to layout
        layout.addLayout(top_row_layout)
        layout.addWidget(self.qa_panel)
        layout.addWidget(action_group)
        layout.addStretch()

        return panel

    def setup_connections(self):
        """Setup signal connections"""
        # File operations
        self.load_video_btn.clicked.connect(self.load_video)
        self.save_annotation_btn.clicked.connect(self.save_annotation)
        self.load_annotation_btn.clicked.connect(self.load_annotation)

        # Video controls
        self.prev_frame_btn.clicked.connect(self.prev_frame)
        self.next_frame_btn.clicked.connect(self.next_frame)
        self.prev_segment_btn.clicked.connect(self.prev_segment)
        self.next_segment_btn.clicked.connect(self.next_segment)

        # Annotation controls
        self.annotation_panel.apply_segment_btn.clicked.connect(self.apply_time_segment)
        self.annotation_panel.undo_segment_btn.clicked.connect(self.undo_time_segment)
        self.annotation_panel.frame_mode_btn.clicked.connect(
            lambda: self.set_navigation_mode("frame")
        )
        self.annotation_panel.segment_mode_btn.clicked.connect(
            lambda: self.set_navigation_mode("segment")
        )

        # Action buttons
        self.start_annotation_btn.clicked.connect(self.start_annotation)
        self.finish_annotation_btn.clicked.connect(self.finish_annotation)
        self.reset_annotation_btn.clicked.connect(self.reset_annotation)

        # SpinBox Focus
        self.frame_step_input.editingFinished.connect(lambda: self.setFocus())
        self.annotation_panel.start_frame_input.editingFinished.connect(lambda: self.setFocus())
        self.annotation_panel.end_frame_input.editingFinished.connect(lambda: self.setFocus())
        self.annotation_panel.interval_input.editingFinished.connect(lambda: self.setFocus())

    def setup_keyboard_shortcuts(self):
        """Setup keyboard shortcuts"""
        # Frame navigation
        self.left_shortcut = QShortcut(QKeySequence(Qt.Key_Left), self)
        self.left_shortcut.activated.connect(self.navigate_left)
        self.left_shortcut.setContext(Qt.ApplicationShortcut)

        self.right_shortcut = QShortcut(QKeySequence(Qt.Key_Right), self)
        self.right_shortcut.activated.connect(self.navigate_right)
        self.right_shortcut.setContext(Qt.ApplicationShortcut)

        # Other shortcuts
        self.save_shortcut = QShortcut(QKeySequence("Ctrl+S"), self)
        self.save_shortcut.activated.connect(self.save_annotation)

        self.load_shortcut = QShortcut(QKeySequence("Ctrl+O"), self)
        self.load_shortcut.activated.connect(self.load_video)

    # Event handlers
    def load_video(self):
        """Load video file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Video File",
            "",
            "Video files (*.mp4 *.avi *.mov *.mkv);;All files (*.*)",
        )

        if file_path:
            if self.video_canvas.load_video(file_path):
                print(f"Successfully loaded video: {file_path}")
                self.update_frame_info()
                self.start_annotation_btn.setEnabled(True)

                # Update annotation panel with video info
                self.annotation_panel.set_video_info(self.video_canvas.total_frames)

                # Reset annotation state
                self.reset_annotation_state()
            else:
                print(f"Failed to load video: {file_path}")

    def update_frame_info(self):
        """Update frame information display"""
        if self.video_canvas.video_cap:
            current = self.video_canvas.current_frame + 1
            total = self.video_canvas.total_frames
            self.frame_info_label.setText(f"Frame: {current} / {total}")
        else:
            self.frame_info_label.setText("Frame: - / -")

    def reset_annotation_state(self):
        """Reset annotation state"""
        self.current_annotation = None
        self.sampled_frames = []
        self.current_segment_index = 0
        self.prev_segment_btn.setEnabled(False)
        self.next_segment_btn.setEnabled(False)
        self.finish_annotation_btn.setEnabled(False)
        self.reset_annotation_btn.setEnabled(False)
        self.save_annotation_btn.setEnabled(False)

    def enable_segment_navigation(self, sampled_frames):
        """Enable segment navigation with sampled frames"""
        self.sampled_frames = sampled_frames
        self.current_segment_index = 0

        if len(self.sampled_frames) > 1:
            self.prev_segment_btn.setEnabled(True)
            self.next_segment_btn.setEnabled(True)

            if self.sampled_frames:
                self.video_canvas.set_frame(self.sampled_frames[0])
                self.update_frame_info()
                print(
                    f"Segment navigation enabled with {len(self.sampled_frames)} segments"
                )

    def save_annotation(self):
        """Save annotation to JSON"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Annotation", "", "JSON files (*.json);;All files (*.*)"
        )

        if file_path:
            print(f"Saving annotation: {file_path}")
            # TODO: Implement annotation saving

    def load_annotation(self):
        """Load annotation from JSON"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Load Annotation", "", "JSON files (*.json);;All files (*.*)"
        )

        if file_path:
            print(f"Loading annotation: {file_path}")
            # TODO: Implement annotation loading

    def prev_frame(self):
        """Go to previous frame"""
        step = self.frame_step_input.value()
        target_frame = max(0, self.video_canvas.current_frame - step)
        if self.video_canvas.set_frame(target_frame):
            self.update_frame_info()

    def next_frame(self):
        """Go to next frame"""
        step = self.frame_step_input.value()
        target_frame = min(self.video_canvas.total_frames - 1, self.video_canvas.current_frame + step)
        if self.video_canvas.set_frame(target_frame):
            self.update_frame_info()

    def prev_segment(self):
        """Go to previous segment"""
        if self.sampled_frames and self.current_segment_index > 0:
            self.current_segment_index -= 1
            frame_num = self.sampled_frames[self.current_segment_index]
            self.video_canvas.set_frame(frame_num)
            self.update_frame_info()
            print(
                f"Navigated to segment {self.current_segment_index + 1} of {len(self.sampled_frames)} (frame {frame_num})"
            )

    def next_segment(self):
        """Go to next segment"""
        if (
            self.sampled_frames
            and self.current_segment_index < len(self.sampled_frames) - 1
        ):
            self.current_segment_index += 1
            frame_num = self.sampled_frames[self.current_segment_index]
            self.video_canvas.set_frame(frame_num)
            self.update_frame_info()
            print(
                f"Navigated to segment {self.current_segment_index + 1} of {len(self.sampled_frames)} (frame {frame_num})"
            )

    def start_annotation(self):
        """Start new annotation"""
        print("Starting new annotation")
        self.finish_annotation_btn.setEnabled(True)
        self.reset_annotation_btn.setEnabled(True)
        self.save_annotation_btn.setEnabled(True)
        # TODO: This will be called after time segment is selected and objects are chosen
        # For now, simulate uniform sampling (example: every 10th frames)
        if self.video_canvas.video_cap:
            # Example: sample every 10 frames from frame 100 to 200
            start_frame = 100
            end_frame = min(200, self.video_canvas.total_frames - 1)
            sample_interval = 10

            sampled = list(range(start_frame, end_frame + 1, sample_interval))
            self.enable_segment_navigation(sampled)

    def finish_annotation(self):
        """Finish current annotation"""
        print("Finishing annotation")
        self.finish_annotation_btn.setEnabled(False)
        self.reset_annotation_btn.setEnabled(False)
        # TODO: Implement annotation completion

    def reset_annotation(self):
        """Reset current annotation"""
        print("Resetting annotation")
        # TODO: Implement annotation reset

    def apply_time_segment(self):
        """Apply time segment and create uniform sampling"""
        segment_info = self.annotation_panel.get_segment_info()
        start_frame = segment_info["start_frame"]
        end_frame = segment_info["end_frame"]
        interval = segment_info["interval"]

        # Validate input
        if start_frame >= end_frame:
            QMessageBox.warning(
                self, "Invalid Segment", "Start frame must be less than end frame!"
            )
            return

        if end_frame >= self.video_canvas.total_frames:
            QMessageBox.warning(
                self,
                "Invalid Segment",
                f"End frame must be less than {self.video_canvas.total_frames}!",
            )
            return

        # Create uniform sampling
        sampled_frames = list(range(start_frame, end_frame + 1, interval))

        if not sampled_frames:
            QMessageBox.warning(
                self, "Invalid Segment", "No frames sampled with current settings!"
            )
            return

        # Enable segment navigation
        self.enable_segment_navigation(sampled_frames)

        # Update annotation panel
        self.annotation_panel.update_segment_info(sampled_frames)

        # Switch to segment mode
        self.set_navigation_mode("segment")

        # Enable undo button
        self.annotation_panel.undo_segment_btn.setEnabled(True)

        # Change keyboard focus to main window
        self.setFocus()

        print(f"Applied time segment: {start_frame}-{end_frame}, interval: {interval}")
        print(f"Sampled frames: {sampled_frames}")

    def undo_time_segment(self):
        """Undo time segment"""
        self.set_navigation_mode("frame")

        self.sampled_frames = []
        self.current_segment_index = 0

        self.prev_segment_btn.setEnabled(False)
        self.next_segment_btn.setEnabled(False)

        self.annotation_panel.undo_segment_btn.setEnabled(False)
        self.annotation_panel.update_segment_info([])

        self.setFocus()

        print("Undo time segment sampling - return to frame navigation mode")

    def set_navigation_mode(self, mode):
        """Set navigation mode (frame or segment)"""
        self.navigation_mode = mode
        self.annotation_panel.set_navigation_mode(mode)

        if mode == "segment":
            print("Switched to segment navigation mode (arrow keys = segments)")
        else:
            print("Switched to frame navigation mode (arrow keys = frames)")

    def navigate_left(self):
        """Navigate left based on current mode"""
        if self.navigation_mode == "segment":
            self.prev_segment()
        else:
            self.prev_frame()

    def navigate_right(self):
        """Navigate right based on current mode"""
        if self.navigation_mode == "segment":
            self.next_segment()
        else:
            self.next_frame()
