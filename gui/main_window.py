# gui/main_window.py
"""
Main Window for Video QA Annotation Tool
"""

import os
import json
from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence, QShortcut
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
    QMessageBox,
    QTabWidget,
    QCheckBox
)

from gui.annotation_panel import AnnotationPanel
from gui.object_panel import ObjectPanel
from gui.qa_panel import QAPanel
from gui.config import PANEL_WIDTH, DEFAULT_360_MODE, HALF_PANEL_WIDTH
from gui.video_canvas import VideoCanvas



class MainWindow(QMainWindow):
    """Main Application Window"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Video QA Annotation Tool")
        self.setGeometry(100, 100, 1450, 700)

        # Annotation State
        self.sampled_frames = []
        self.current_segment_index = 0
        
        # 360 Video Mode Status (Padding for Bbox)
        self.is_360_mode = False
        self.current_video_name = None

        # Current Video and Annotation Data
        self.current_video_name = None
        self.current_annotation_data = None

        # Current Working JSON File
        self.current_json_file = None

        # Setup
        self.setup_ui()
        self.setup_connections()
        self.setup_keyboard_shortcuts()

    def setup_ui(self):
        """Setup UI layout"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(5, 5, 5, 5)

        # Create main splitter
        main_splitter = QSplitter(Qt.Horizontal)
        main_splitter.setHandleWidth(5)

        # Left panel (video canvas)
        left_panel = self.create_left_panel()

        # Right panel (controls)
        right_panel = self.create_right_panel()
        right_panel.setFixedWidth(PANEL_WIDTH + 20)

        main_splitter.addWidget(left_panel)
        main_splitter.addWidget(right_panel)

        window_width = 1600
        left_width = window_width - PANEL_WIDTH - 50
        main_splitter.setSizes([left_width, PANEL_WIDTH + 20])

        main_splitter.setStretchFactor(0, 1)
        main_splitter.setStretchFactor(1, 0)

        main_layout.addWidget(main_splitter)

    def create_left_panel(self):
        """Create left panel with video canvas and controls"""
        panel = QFrame()
        layout = QVBoxLayout(panel)

        # File operations
        file_group = QGroupBox("File Operations")
        file_layout = QHBoxLayout(file_group)

        self.mode_360_checkbox = QCheckBox("360 Video Mode")
        self.mode_360_checkbox.setChecked(DEFAULT_360_MODE)
        self.mode_360_checkbox.stateChanged.connect(self.on_360_mode_changed)
        file_layout.addWidget(self.mode_360_checkbox)

        self.load_video_btn = QPushButton("Load Video")
        self.load_annotation_btn = QPushButton("Load JSON")
        self.save_annotation_btn = QPushButton("Save")
        self.save_as_btn = QPushButton("Save As...")

        for btn in [self.load_video_btn, self.load_annotation_btn, self.save_annotation_btn, self.save_as_btn]:
            btn.setMinimumWidth(120)
            btn.setMinimumHeight(32)

        file_layout.addWidget(self.load_video_btn)
        file_layout.addWidget(self.load_annotation_btn)
        file_layout.addWidget(self.save_annotation_btn)
        file_layout.addWidget(self.save_as_btn)
        file_layout.addStretch()

        # Video canvas
        self.video_canvas = VideoCanvas()

        # Video controls
        video_controls_group = QGroupBox("Video Controls")
        video_controls_layout = QVBoxLayout(video_controls_group)

        # Frame info
        self.frame_info_label = QLabel("Frame: - / -")
        self.frame_info_label.setAlignment(Qt.AlignCenter)

        # Navigation buttons
        nav_layout = QHBoxLayout()
        self.prev_frame_btn = QPushButton("◀ Previous Frame (D=10, C=1)")
        self.next_frame_btn = QPushButton("Next Frame (F=10, V=1) ▶")
        nav_layout.addWidget(self.prev_frame_btn)
        nav_layout.addWidget(self.next_frame_btn)

        # Segment buttons
        segment_layout = QHBoxLayout()
        self.prev_segment_btn = QPushButton("◀◀ Previous Segment (D)")
        self.next_segment_btn = QPushButton("Next Segment (F) ▶▶")

        self.prev_segment_btn.setEnabled(False)
        self.next_segment_btn.setEnabled(False)

        segment_layout.addWidget(self.prev_segment_btn)
        segment_layout.addWidget(self.next_segment_btn)

        video_controls_layout.addWidget(self.frame_info_label)
        video_controls_layout.addLayout(nav_layout)
        video_controls_layout.addLayout(segment_layout)

        # Add to layout
        layout.addWidget(file_group)
        layout.addWidget(self.video_canvas, 1)  # Give video canvas most space
        layout.addWidget(video_controls_group)

        return panel

    def create_right_panel(self):
        """Create right panel with tabbed annotation controls"""
        panel = QFrame()
        panel.setFrameStyle(QFrame.StyledPanel)

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)

        # Tab Widget
        self.tab_widget = QTabWidget()
        
        # Grounding Tab
        grounding_tab = self.create_grounding_tab()
        self.tab_widget.addTab(grounding_tab, "Grounding")
        
        # QA Tab
        qa_tab = self.create_qa_tab()
        self.tab_widget.addTab(qa_tab, "QA")
        
        # Tab Changed Callback
        self.tab_widget.currentChanged.connect(self.on_tab_changed)
        
        layout.addWidget(self.tab_widget)
        
        return panel

    def create_grounding_tab(self):
        """Create grounding tab with improved layout"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(10)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Upper: Object Panel
        self.object_panel = ObjectPanel()
        layout.addWidget(self.object_panel, 1)
        
        # Lower: Annotation Panel + Annoation Status Panel
        bottom_row_layout = QHBoxLayout()
        bottom_row_layout.setSpacing(10)
        bottom_row_layout.setContentsMargins(0, 0, 0, 0)
        
        # Upper Left: Annotation controls panel
        self.annotation_panel = AnnotationPanel()
        
        # Upper Right: Annotation Status
        status_group = QGroupBox('3. BBox Annotation Status')
        status_layout = QVBoxLayout(status_group)
        
        # Status Label
        self.annotation_status_label = QLabel("Load video and select objects to start annotation")
        self.annotation_status_label.setStyleSheet(
            "color: #666; font-style: italic; padding: 8px; "
            "border: 1px solid #ddd; border-radius: 3px; "
            "background-color: #f9f9f9;"
        )
        self.annotation_status_label.setAlignment(Qt.AlignCenter)

        # Progress Label
        self.progress_label = QLabel('Progress: Not Started')
        self.progress_label.setStyleSheet(
            "color: #333; font-weight: bold; padding: 10px; "
            "border: 2px solid #9E9E9E; border-radius: 5px; "
            "background-color: #f5f5f5; font-size: 12px;"
        )
        self.progress_label.setAlignment(Qt.AlignCenter)

        # Button Layout
        button_layout = QHBoxLayout()

        # 1. Undo Last BBox
        self.undo_bbox_btn = QPushButton("↩️ Remove Last BBox")
        self.undo_bbox_btn.setMinimumHeight(35)
        self.undo_bbox_btn.setEnabled(False)

        # 2. New Grounding (Restart)
        self.new_grounding_btn = QPushButton('🆕 New Grounding')
        self.new_grounding_btn.setMinimumHeight(35)
        self.new_grounding_btn.setEnabled(False)

        button_layout.addWidget(self.undo_bbox_btn)
        button_layout.addWidget(self.new_grounding_btn)
        
        # Status Layout 구성
        status_layout.addWidget(self.annotation_status_label)
        status_layout.addSpacing(8)
        status_layout.addWidget(self.progress_label)
        status_layout.addSpacing(10)
        status_layout.addLayout(button_layout)
        status_layout.addStretch()
        
        # 하단 가로 배치
        bottom_row_layout.addWidget(self.annotation_panel, 2)
        bottom_row_layout.addWidget(status_group, 3)
        
        layout.addLayout(bottom_row_layout, 0)
        
        return tab
    
    def create_qa_tab(self):
        """Create QA tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # QA panel
        self.qa_panel = QAPanel()
        layout.addWidget(self.qa_panel)
        
        return tab
    
    def on_tab_changed(self, index):
        """Handle tab change"""
        tab_names = ["Grounding", "QA"]
        if index < len(tab_names):
            print(f"Switched to {tab_names[index]} tab")
            
            # Update track_ids when switching to QA tab
            if index == 1:  # QA tab
                self.update_qa_panel_track_ids()

                # Disable A Key on QA Tab
                self.a_shortcut.setEnabled(False)
            else:
                self.a_shortcut.setEnabled(True)

    def setup_connections(self):
        """Setup signal connections"""
        # File operations
        self.load_video_btn.clicked.connect(self.load_video)
        self.load_annotation_btn.clicked.connect(self.load_annotation)
        self.save_annotation_btn.clicked.connect(self.save_annotation)
        self.save_as_btn.clicked.connect(self.save_as_new_file)

        # Video controls
        self.prev_frame_btn.clicked.connect(self.navigate_prev)
        self.next_frame_btn.clicked.connect(self.navigate_next)
        self.prev_segment_btn.clicked.connect(self.prev_segment)
        self.next_segment_btn.clicked.connect(self.next_segment)

        # Annotation controls
        self.annotation_panel.apply_segment_btn.clicked.connect(self.apply_time_segment_and_start)
        self.annotation_panel.undo_segment_btn.clicked.connect(self.undo_time_segment)

        # Grounding Tab Buttons
        self.undo_bbox_btn.clicked.connect(self.remove_last_bbox)
        self.new_grounding_btn.clicked.connect(self.start_new_grounding)

        # Object Panel selection change detector
        self.object_panel.connect_selection_changed(self.on_object_selection_changed)

        self.annotation_panel.start_frame_input.editingFinished.connect(lambda: self.setFocus())
        self.annotation_panel.end_frame_input.editingFinished.connect(lambda: self.setFocus())
        self.annotation_panel.interval_input.editingFinished.connect(lambda: self.setFocus())

        if hasattr(self, 'qa_panel'):
            self.qa_panel.qa_data_changed.connect(self.on_qa_data_changed)

    def setup_keyboard_shortcuts(self):
        """Setup keyboard shortcuts"""

        # C Mapping: Prev 1 Frame
        self.c_shortcut = QShortcut(QKeySequence(Qt.Key_C), self)
        self.c_shortcut.activated.connect(self.navigate_prev)
        self.c_shortcut.setContext(Qt.WindowShortcut)

        # V Mapping: Next 1 Frame
        self.v_shortcut = QShortcut(QKeySequence(Qt.Key_V), self)
        self.v_shortcut.activated.connect(self.navigate_next)
        self.v_shortcut.setContext(Qt.WindowShortcut)

        # D Mapping: Next 10 Frame
        self.d_shortcut = QShortcut(QKeySequence(Qt.Key_D), self)
        self.d_shortcut.activated.connect(lambda: self.prev_n_frame(10))
        self.d_shortcut.setContext(Qt.WindowShortcut)

        # F Mapping: Next 10 Frame
        self.f_shortcut = QShortcut(QKeySequence(Qt.Key_F), self)
        self.f_shortcut.activated.connect(lambda: self.next_n_frame(10))
        self.f_shortcut.setContext(Qt.WindowShortcut)

        # A Mapping: Apply Time Segment
        self.a_shortcut = QShortcut(QKeySequence(Qt.Key_A), self)
        self.a_shortcut.activated.connect(self.apply_time_segment_and_start)
        self.a_shortcut.setContext(Qt.WindowShortcut)

        # Q Mapping: Switch to QA Tab
        self.q_shortcut = QShortcut(QKeySequence(Qt.Key_Q), self)
        self.q_shortcut.activated.connect(self.switch_to_qa_tab)
        self.q_shortcut.setContext(Qt.WindowShortcut)

        # Other shortcuts
        self.save_shortcut = QShortcut(QKeySequence("Ctrl+S"), self)
        self.save_shortcut.activated.connect(self.save_annotation)

        self.load_shortcut = QShortcut(QKeySequence("Ctrl+O"), self)
        self.load_shortcut.activated.connect(self.load_video)

        self.new_grounding_shortcut = QShortcut(QKeySequence("Ctrl+R"), self)
        self.new_grounding_shortcut.activated.connect(self.start_new_grounding)
        self.new_grounding_shortcut.setContext(Qt.WindowShortcut)

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
                self.current_video_name = os.path.splitext(os.path.basename(file_path))[0]
                print(f"Successfully loaded video: {file_path}")
                print(f'Video loaded: {self.current_video_name}')

                # Reset All Annotation State
                self.reset_all_for_new_video()

                self.update_frame_info()

                # Update annotation panel with video info
                self.annotation_panel.set_video_info(self.video_canvas.total_frames)

                # Detect 360 Panoramic Video
                self.auto_detect_360_mode()

                self.update_annotation_status(f"Video loaded: {self.current_video_name}")

                self.setFocus()
            else:
                print(f"Failed to load video: {file_path}")
    
    def reset_all_for_new_video(self):
        """When Load Video, Rest all status"""
        # 1. Reset JSON File Path
        self.current_json_file = None

        # 2. Reset Annotation Data
        self.current_annotation_data = None
        self.sampled_frames = []
        self.current_segment_index = 0

        # 3. Reset Video Canvas
        self.video_canvas.disable_bbox_mode()
        self.video_canvas.frame_bboxes = {}
        self.video_canvas.existing_track_ids = {}
        self.video_canvas.track_registry = {}
        self.video_canvas.color_index = 0
        self.video_canvas.edit_mode = False
        self.video_canvas.selected_bbox = None
        self.video_canvas.selected_bbox_index = None
        self.video_canvas.is_drawing = False
        self.video_canvas.last_selected_object_type = None
        self.video_canvas.update()

        # 4. Reset Object Panel
        self.object_panel.clear_selection()
        self.object_panel.setEnabled(True)

        # 5. Reset Annotation Panel
        self.annotation_panel.apply_segment_btn.setEnabled(False)
        self.annotation_panel.undo_segment_btn.setEnabled(False)
        self.annotation_panel.set_navigation_mode('frame')
        self.annotation_panel.start_frame_input.setValue(0)
        self.annotation_panel.end_frame_input.setValue(0)
        self.annotation_panel.interval_input.setValue(10)

        # 6. Reset QA Panel
        if hasattr(self, 'qa_panel'):
            self.qa_panel.reset_qa_panel()
            self.qa_panel.set_available_track_ids([])
            if hasattr(self.qa_panel, 'sampled_frames'):
                delattr(self.qa_panel, 'sampled_frames')
        
        # 7. Reset Navigation Button Status
        self.prev_segment_btn.setEnabled(False)
        self.next_segment_btn.setEnabled(False)

        # 8. Reset Action Button Status
        self.new_grounding_btn.setEnabled(True)
        self.undo_bbox_btn.setEnabled(False)
        self.save_annotation_btn.setEnabled(False)
        self.save_as_btn.setEnabled(False)

        # 9. Reset Progress
        self.progress_label.setText('Progress: Not Started')
        self.progress_label.setStyleSheet(
            "color: #333; font-weight: bold; padding: 10px; "
            "border: 2px solid #9E9E9E; border-radius: 5px; "
            "background-color: #f5f5f5; font-size: 12px;"
        )

        # 10. Reset Tab to Grounding Tab
        if hasattr(self, 'tab_widget'):
            self.tab_widget.setCurrentIndex(0)
        
        # 11. Keyboard Shortcuts Reset
        if hasattr(self, 'a_shortcut'):
            self.a_shortcut.setEnabled(True)
        
        print("Load Video: Overall Status Reset Complete.")

    def update_frame_info(self):
        """Update frame information display 0-Indexing"""

        if not self.video_canvas.video_cap:
            self.frame_info_label.setText('Frame: - / -')
            return
        
        # Frame Index Info
        current = self.video_canvas.current_frame
        total = self.video_canvas.total_frames
        frame_info = f"Frame: {current} / {total-1}"
    
        # Segment Index Info
        if self.sampled_frames:
            if current in self.sampled_frames:
                segment_index = self.sampled_frames.index(current)
                segment_total = len(self.sampled_frames)
                segment_info = f' | Segment: {segment_index} / {segment_total - 1}'
            else:
                segment_total = len(self.sampled_frames)
                segment_info = f' | Segment: - / {segment_total - 1}'

            frame_info += segment_info

        self.frame_info_label.setText(frame_info)

    def save_annotation(self):
        """Save annotation - 첫 저장시 Save As 처럼 동작"""
        if not self.get_current_annotation_with_qa():
            QMessageBox.warning(self, "No Annotation", "No annotation to save")
            return
        
        # JSON 파일이 로드되지 않은 경우 Save As처럼 동작
        if not self.current_json_file:
            default_filename = f"{self.current_video_name}.json"
            
            file_path, _ = QFileDialog.getSaveFileName(
                self, "Save Annotation", default_filename,
                "JSON files (*.json);;All files (*.*)"
            )
            
            if not file_path:
                return  # 사용자가 취소한 경우
            
            self.current_json_file = file_path
        
        # 파일 저장 실행
        if self.save_to_file(self.current_json_file):
            # 저장 성공 시 통계 표시
            bbox_count = sum(len(bboxes) for bboxes in self.video_canvas.frame_bboxes.values())
            qa_count = len(self.qa_panel.get_all_qa_data()) if hasattr(self, 'qa_panel') else 0
            
            QMessageBox.information(self, "Save Success", 
                                f"Annotation saved to {os.path.basename(self.current_json_file)}\n"
                                f"• {bbox_count} bounding boxes\n"
                                f"• {qa_count} QA sessions")
        else:
            QMessageBox.critical(self, "Save Failed", "Failed to save annotation")

    def save_as_new_file(self):
        """Save as new file"""
        default_filename = f"{self.current_video_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Annotation As", default_filename, "JSON files (*.json);;All files (*.*)"
        )
        
        if file_path:
            self.current_json_file = file_path
            if self.save_to_file(file_path):
                QMessageBox.information(self, "Save Success", f"Annotation saved to {os.path.basename(file_path)}")
            else:
                QMessageBox.critical(self, "Save Failed", "Failed to save annotation")

    def save_to_file(self, file_path):
        """Actual file saving logic - video-centric structure"""
        try:
            # Load existing file if it exists
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            else:
                data = {
                    "video_info": {
                        "filename": self.current_video_name,
                        "total_frames": self.video_canvas.total_frames,
                        "fps": self.video_canvas.fps,
                        "resolution": {
                            "width": self.video_canvas.video_resolution[0],
                            "height": self.video_canvas.video_resolution[1]
                        }
                    },
                    "groundings": []
                }
        
            current_annotation = self.get_current_annotation_with_qa()
            
            # 새 grounding ID 생성
            existing_ids = [g.get('grounding_id', 0) for g in data['groundings']]
            next_id = max(existing_ids) + 1 if existing_ids else 1
            
            # 새 grounding 추가
            new_grounding = {
                "grounding_id": next_id,
                "created_at": datetime.now().isoformat(),
                "time_segment": current_annotation["time_segment"],
                "selected_objects": current_annotation["selected_objects"],
                "annotations": current_annotation["annotations"],
                "qa_sessions": current_annotation.get("qa_data", [])
            }
            
            data["groundings"].append(new_grounding)
                
            # 파일 저장
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            grounding_count = len(data["groundings"])
            print(f"Saved grounding #{next_id} to {file_path} (Total: {grounding_count})")
            return True
            
            
        except Exception as e:
            print(f"Error saving: {e}")
            return False

    def start_new_grounding(self):
        """Start new grounding (확인 후 리셋)"""
        # 현재 작업이 있는지 확인
        if not self._has_current_work():
            # 작업이 없으면 단순히 리셋만
            self.reset_for_new_grounding()
            return
        
        # 작업이 날아간다고 경고
        total_bboxes = sum(len(bboxes) for bboxes in self.video_canvas.frame_bboxes.values()) if self.video_canvas.frame_bboxes else 0
        total_qas = len(self.qa_panel.get_all_qa_data()) if hasattr(self, 'qa_panel') else 0
        
        if total_bboxes > 0 or total_qas > 0:
            message = f"Current work will be lost:\n"
            if total_bboxes > 0:
                message += f"• {total_bboxes} bounding boxes\n"
            if total_qas > 0:
                message += f"• {total_qas} QA sessions\n"
            message += f"\nContinue anyway?"
            
            result = QMessageBox.question(
                self, "Start New Grounding", message,
                QMessageBox.Yes | QMessageBox.No
            )
            
            if result == QMessageBox.No:
                return
        
        # Reset
        self.reset_for_new_grounding()
        print("🆕 Started new grounding session")

    def _has_current_work(self):
        """현재 작업이 있는지 확인"""
        has_annotation_data = self.current_annotation_data is not None
        has_bboxes = bool(self.video_canvas.frame_bboxes)
        has_qa_data = False
        
        if hasattr(self, 'qa_panel'):
            qa_sessions = self.qa_panel.get_all_qa_data()
            has_qa_data = bool(qa_sessions)
        
        return has_annotation_data or has_bboxes or has_qa_data

    def reset_for_new_grounding(self):
        """Reset UI state for new grounding while keeping video loaded"""
        # Stop any active bbox annotation
        if self.video_canvas.bbox_mode:
            self.video_canvas.disable_bbox_mode()
        
        # Reset annotation data
        self.current_annotation_data = None
        self.sampled_frames = []
        self.current_segment_index = 0
        
        # Reset video canvas annotation data
        self.video_canvas.frame_bboxes = {}
        self.video_canvas.existing_track_ids = {}
        self.video_canvas.track_registry = {}
        self.video_canvas.color_index = 0
        self.video_canvas.last_selected_object_type = None
        self.video_canvas.update()  # Refresh display
        
        # Reset navigation
        self.prev_segment_btn.setEnabled(False)
        self.next_segment_btn.setEnabled(False)
        
        # Reset UI panels
        self.object_panel.clear_selection()
        self.object_panel.setEnabled(True)
        
        # Reset annotation panel
        self.annotation_panel.undo_segment_btn.setEnabled(False)
        self.annotation_panel.set_navigation_mode('frame')
        
        # Reset QA panel
        if hasattr(self, 'qa_panel'):
            self.qa_panel.reset_qa_panel()
        
        # Reset button states
        self.new_grounding_btn.setEnabled(True)  # Keep enabled for multiple restarts
        self.undo_bbox_btn.setEnabled(False)
        self.save_annotation_btn.setEnabled(False)
        self.save_as_btn.setEnabled(False)
        
        # Update status
        self.update_annotation_status("Ready for new grounding - Select objects and apply time segment")
        self.progress_label.setText("Progress: Ready for new grounding")
        self.progress_label.setStyleSheet(
            "color: #333; font-weight: bold; padding: 10px; "
            "border: 2px solid #9E9E9E; border-radius: 5px; "
            "background-color: #f5f5f5; font-size: 12px;"
        )
        
        # Switch to grounding tab
        if hasattr(self, 'tab_widget'):
            self.tab_widget.setCurrentIndex(0)
        
        print("🔄 Reset completed - ready for new grounding")

    def on_360_mode_changed(self, state):
        """360 Mode State Change"""
        self.is_360_mode = (state == Qt.CheckState.Checked.value)

        if self.is_360_mode:
            print("360 Video Mode: Enabled")
        else:
            print("360 Video Mode: Disabled")
        
        if self.video_canvas.current_frame_data is not None:
            self.video_canvas.set_360_mode(self.is_360_mode)
            self.video_canvas.update_display()
    
    def auto_detect_360_mode(self):
        """Detect 360 video based on its resolution"""
        if not self.video_canvas.video_resolution:
            return

        width, height = self.video_canvas.video_resolution
        aspect_ratio = width / height if height > 0 else 0

        # 360 video detect logic : if width : height == 2 : 1
        is_panoramic = 1.8 <= aspect_ratio <= 2.2
        
        if is_panoramic != self.is_360_mode:
            self.mode_360_checkbox.setChecked(is_panoramic)

            if is_panoramic:
                print(f"Auto-Detect 360 Video: {width}x{height} (ratio: {aspect_ratio:.2f})")
                self.update_annotation_status(f"360 mode enabled for video ({width}x{height})")
            else:
                print(f"Auto-Detect Standard Video: {width}x{height} (ratio: {aspect_ratio:.2f})")
                self.update_annotation_status(f"360 mode disabled for video ({width}x{height})")

    def load_annotation(self):
        """기존 영상 annotation 파일을 선택해서 이어서 작업"""
        if not self.current_video_name:
            QMessageBox.warning(self, "No Video", "Please load a video first")
            return
        
        # 기본 파일명 제안
        default_file = f"{self.current_video_name}.json"
        
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Load Annotation File", default_file,
            "JSON files (*.json);;All files (*.*)"
        )
        
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # 현재 작업할 파일로 설정
                self.current_json_file = file_path
                groundings = data.get("groundings", [])
                
                if groundings:
                    # 기존 grounding 정보 표시
                    QMessageBox.information(self, "Load Successful", 
                                        f"Loaded annotation file with {len(groundings)} existing groundings.\n"
                                        f"Latest: Grounding #{groundings[-1]['grounding_id']}\n"
                                        f"New groundings will be added to this file.")
                else:
                    QMessageBox.information(self, "Load Successful", 
                                        "Loaded empty annotation file.\n"
                                        "Start your first grounding!")
                
                print(f"Set working file: {file_path} (has {len(groundings)} groundings)")
                
            except Exception as e:
                QMessageBox.critical(self, "Load Failed", f"Failed to load file: {e}")

    def navigate_prev(self):
        # Segment mode
        if self.sampled_frames:
            self.prev_segment()
        else: # Frame mode
            self.prev_n_frame(1)

    def navigate_next(self):
        # segment mode
        if self.sampled_frames:
            self.next_segment()
        else: # frame mode
            self.next_n_frame(1)

    def prev_n_frame(self, n):
        """Go to previous n-frame"""
        if self.sampled_frames:
            min_frame = self.sampled_frames[0]
            max_frame = self.sampled_frames[-1]
            target_frame = max(min_frame, min(max_frame, self.video_canvas.current_frame - n))

        else:
            target_frame = max(0, self.video_canvas.current_frame - n)
        
        if self.video_canvas.set_frame(target_frame):
            self.update_frame_info()

    def next_n_frame(self, n):
        """Go to next n-frame"""
        if self.sampled_frames:
            min_frame = self.sampled_frames[0]
            max_frame = self.sampled_frames[-1]
            target_frame = max(min_frame, min(max_frame, self.video_canvas.current_frame + n))
            
        else:
            target_frame = min(self.video_canvas.total_frames - 1, self.video_canvas.current_frame + n)

        if self.video_canvas.set_frame(target_frame):
            self.update_frame_info()

    def prev_segment(self):
        """Go to previous segment"""
        if self.sampled_frames and self.current_segment_index > 0:
            self.current_segment_index -= 1
            frame_num = self.sampled_frames[self.current_segment_index]
            self.video_canvas.set_frame(frame_num)
            self.update_frame_info()
            # print(
                # f"Navigated to segment {self.current_segment_index} of {len(self.sampled_frames) - 1} (frame {frame_num})"
            # )

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
            # print(
            #     f"Navigated to segment {self.current_segment_index} of {len(self.sampled_frames) - 1} (frame {frame_num})"
            # )

    def apply_time_segment_and_start(self):
        """Apply time segment and automatically start BBox Annotation"""
        if not self.current_video_name:
            QMessageBox.warning(self, 'No Video', 'Please load video first.')
            return
        
        selected_objects = self.object_panel.get_selected_objects()
        if not selected_objects:
            QMessageBox.warning(self, 'No Objects', 'Please select objects to annotate.')
            return
        
        # 1. Set Time Segment Range
        segment_info = self.annotation_panel.get_segment_info()
        start_frame = segment_info['start_frame']
        end_frame = segment_info['end_frame']
        interval = segment_info['interval']

        if start_frame >= end_frame:
            QMessageBox.warning(self, 'Invalid Segment', 'Start Frame should be smaller than End Frame.')
            return
        
        if end_frame >= self.video_canvas.total_frames:
            QMessageBox.warning(self, 'Invalid Segment', 
                                f'End Frame should be smaller than {self.video_canvas.total_frames}.')
            return
        
        # 2. Uniform Sampling
        sampled_frames = list(range(start_frame, end_frame+1, interval))
        if not sampled_frames:
            QMessageBox.warning(self, 'Invalid Segment', 'No frame sampled with current settings.')
            return
        
        # 3. Check if previous work exists
        if self.current_annotation_data is not None or self.video_canvas.frame_bboxes:
            total_bboxes = sum(len(bboxes) for bboxes in self.video_canvas.frame_bboxes.values())
            if total_bboxes > 0:
                result = QMessageBox.question(self, "Start New Annotation", 
                                            f"Current annotation has {total_bboxes} bounding boxes.\n"
                                            f"Start new annotation? (Current work will be lost)",
                                            QMessageBox.Yes | QMessageBox.No)
                if result == QMessageBox.No:
                    return
        
        # 4. Initiate Annotation Data
        self.current_annotation_data = {
            'video_info': {
                'filename': self.current_video_name,
                'total_frames': self.video_canvas.total_frames,
                'fps': self.video_canvas.fps,
                'resolution': {
                    'width': self.video_canvas.video_resolution[0],
                    'height': self.video_canvas.video_resolution[1]
                }
            },
            'time_segment': {
                'start_frame': sampled_frames[0],
                'end_frame': sampled_frames[-1],
                'interval': interval,
                'sampled_frames': sampled_frames.copy()
            },
            'selected_objects': selected_objects.copy(),
            'annotations': {},
            'qa_data': None
        }

        # 5. Activate Segment Navigation
        self.sampled_frames = sampled_frames
        self.current_segment_index = 0
        self.prev_segment_btn.setEnabled(True)
        self.next_segment_btn.setEnabled(True)

        # 6. Activate BBox Annotation Mode
        self.video_canvas.frame_bboxes = {}
        self.video_canvas.existing_track_ids = {}
        self.video_canvas.track_registry = {}
        self.video_canvas.color_index = 0
        self.video_canvas.enable_bbox_mode(selected_objects)

        # Move to Segment 0
        self.video_canvas.set_frame(sampled_frames[0])
        self.update_frame_info()

        # Update UI
        self.annotation_panel.undo_segment_btn.setEnabled(True)
        self.annotation_panel.set_navigation_mode('segment')

        # Init QA Panel
        if hasattr(self, 'qa_panel'):
            self.qa_panel.reset_qa_panel()
            self.qa_panel.set_available_time_segments(sampled_frames)
        
        # Update Button States
        self.undo_bbox_btn.setEnabled(True)
        self.new_grounding_btn.setEnabled(True)
        self.object_panel.setEnabled(False)

        # Update Progress
        self.update_progress_display()
        self.update_annotation_status(f"🎯 BBox annotation started: {', '.join(selected_objects)}")

        self.setFocus()
        print(f"Start BBox annotation for: {selected_objects}")
        print(f"Segments: {len(sampled_frames)} frames to annotate")

    def undo_time_segment(self):
        """Reset annotation data, keep object selection"""
        
        # Backup selected objects
        selected_objects = self.object_panel.get_selected_objects()
        
        # Reset Annotation data
        self.reset_annotation_data_only()
        
        # Update backup object selection data
        self.restore_object_selection(selected_objects)
        
        print(f"🔄 Reset annotation data - kept object selection: {selected_objects}")
    def reset_annotation_data_only(self):
        """어노테이션 데이터만 초기화 (객체 선택은 유지)"""
        
        # 1. Deactivate Bbox mode
        if self.video_canvas.bbox_mode:
            self.video_canvas.disable_bbox_mode()
        
        # 2. Reset Annotation data
        self.current_annotation_data = None
        self.sampled_frames = []
        self.current_segment_index = 0
        
        # 3. Reset VideoCanvas Annotation data
        self.video_canvas.frame_bboxes = {}
        self.video_canvas.existing_track_ids = {}
        self.video_canvas.track_registry = {}
        self.video_canvas.color_index = 0
        self.video_canvas.edit_mode = False
        self.video_canvas.selected_bbox = None
        self.video_canvas.selected_bbox_index = None
        self.video_canvas.is_drawing = False
        self.video_canvas.last_selected_object_type = None
        self.video_canvas.update()
        
        # 4. Reset Annotation panel (Keep object panel)
        self.object_panel.setEnabled(True)
        self.annotation_panel.undo_segment_btn.setEnabled(False)
        self.annotation_panel.set_navigation_mode('frame')
        
        # 5. Init QA Panel
        if hasattr(self, 'qa_panel'):
            self.qa_panel.reset_qa_panel()
            self.qa_panel.set_available_track_ids([])
        
        # 6. Navigation Button status
        self.prev_segment_btn.setEnabled(False)
        self.next_segment_btn.setEnabled(False)
        
        # 7. Action Button Status
        self.undo_bbox_btn.setEnabled(False)
        self.save_annotation_btn.setEnabled(False)
        self.save_as_btn.setEnabled(False)
        
        # 8. Reset Progress Button
        self.progress_label.setText('Progress: Not Started')
        self.progress_label.setStyleSheet(
            "color: #333; font-weight: bold; padding: 10px; "
            "border: 2px solid #9E9E9E; border-radius: 5px; "
            "background-color: #f5f5f5; font-size: 12px;"
        )
        
        # 9. Move to Grounding Tab
        if hasattr(self, 'tab_widget'):
            self.tab_widget.setCurrentIndex(0)
        
        # 10. Focus
        self.setFocus()

    def restore_object_selection(self, selected_objects):
        """Restore Selected Objects"""
        self.object_panel.clear_selection()
        
        for category in selected_objects:
            self.object_panel.all_selected_categories.add(category)
        
        for category, checkbox in self.object_panel.checkboxes.items():
            if category in selected_objects:
                checkbox.setChecked(True)

    def update_annotation_status(self, message):
        """Update annotation status label"""
        self.annotation_status_label.setText(message)

    def update_progress_display(self):
        """Update BBox Annotation Progress"""
        if not self.sampled_frames:
            self.progress_label.setText("Progress: No segments defined")
            self.progress_label.setStyleSheet(
                "color: #666; padding: 10px; border: 2px solid #9E9E9E; "
                "border-radius: 5px; background-color: #f5f5f5; font-size: 11px;"
            )
            return
        
        total = len(self.sampled_frames)
        completed_frames = []
        
        for i, frame_idx in enumerate(self.sampled_frames):
            if frame_idx in self.video_canvas.frame_bboxes and self.video_canvas.frame_bboxes[frame_idx]:
                completed_frames.append(i)
        
        completed = len(completed_frames)
        remaining = [i for i in range(total) if i not in completed_frames]
        
        # Color according to progress rate
        rate = completed / total if total > 0 else 0.0
        if rate == 1.0:
            color = "#4CAF50"  # Finish - Green
            bg_color = "#E8F5E8"
            text = f"🎉 Progress: {completed}/{total} segments COMPLETED!"
        elif rate >= 0.7:
            color = "#2196F3" # Almost Finished - Blue
            bg_color = "#FFF3E0"
            if len(remaining) <= 5:
                remaining_str = ", ".join(map(str, remaining))
                text = f"Progress: {completed}/{total} segments | Remaining: [{remaining_str}]"
            else:
                text = f"Progress: {completed}/{total} segments | Remaining: {len(remaining)} more"
        elif rate >= 0.3:
            color = "#FF9800"  # On Progress - Orange
            bg_color = "#E3F2FD"
            if len(remaining) <= 5:
                remaining_str = ", ".join(map(str, remaining))
                text = f"Progress: {completed}/{total} segments | Remaining: [{remaining_str}]"
            else:
                text = f"Progress: {completed}/{total} segments | Remaining: {len(remaining)} more"
        else:
            color = "#F44336"  # Start state - Red
            bg_color = "#FFEBEE"
            if len(remaining) <= 5:
                remaining_str = ", ".join(map(str, remaining))
                text = f"Progress: {completed}/{total} segments | Remaining: [{remaining_str}]"
            else:
                text = f"Progress: {completed}/{total} segments | Remaining: {len(remaining)} more"
        
        self.progress_label.setText(text)
        self.progress_label.setStyleSheet(
            f"color: {color}; font-weight: bold; padding: 10px; "
            f"border: 2px solid {color}; border-radius: 5px; "
            f"background-color: {bg_color}; font-size: 11px;"
        )

    def switch_to_qa_tab(self):
        """Switch to QA Tab and update track IDDs"""
        if hasattr(self, 'tab_widget'):
            current_tab = self.tab_widget.currentIndex()

            if current_tab == 0:
                self.update_qa_panel_track_ids()

                self.tab_widget.setCurrentIndex(1)
                print('Switched to QA Tab via Q Key')
            else:
                # If already in QA Tab, switch back to grounding tab
                self.tab_widget.setCurrentIndex(0)
                print('Switched to Grounding Tab via Q Key')

    def on_object_selection_changed(self):
        """Call when Object Panel selection changes"""
        selected_objects = self.object_panel.get_selected_objects()

        # Start button activation conditions
        has_video = self.current_video_name is not None
        has_objects = len(selected_objects) > 0
        has_segments = len(self.sampled_frames) > 0
        
        # Status message
        if not has_video:
            self.update_annotation_status("Load video first")
        elif not has_objects:
            self.update_annotation_status("Select objects to continue")
        elif not has_segments:
            self.update_annotation_status("Apply time segment to continue")
        elif self.current_annotation_data is not None:
            current_objects = set(self.current_annotation_data["selected_objects"])
            new_objects = set(selected_objects)
            
            if current_objects == new_objects:
                self.update_annotation_status(f"In progress: {', '.join(selected_objects)}")
            else:
                current_str = ', '.join(sorted(current_objects))
                new_str = ', '.join(sorted(new_objects))
                self.update_annotation_status(f"Current: {current_str} → Click to restart with: {new_str}")
        else:
            self.update_annotation_status(f"Ready to start: {', '.join(selected_objects)}")

    def remove_last_bbox(self):
        """Remove last bbox on current frame"""
        if not self.video_canvas.bbox_mode:
            return
        
        if self.video_canvas.remove_last_bbox():
            print(f"Undid last bbox on frame {self.video_canvas.current_frame}")
        else:
            QMessageBox.information(self, "No BBox", "No bounding boxes to undo on current frame.")

    def update_qa_panel_track_ids(self):
        """Update QA panel with available track IDs"""
        if hasattr(self, 'qa_panel') and self.video_canvas.frame_bboxes:
            # Collect all track_ids
            all_track_ids = set()
            for frame_bboxes in self.video_canvas.frame_bboxes.values():
                for bbox in frame_bboxes:
                    all_track_ids.add(bbox['track_id'])
            
            track_ids = sorted(list(all_track_ids))
            self.qa_panel.set_available_track_ids(track_ids)
            print(f"Updated QA panel with track IDs: {track_ids}")
        else:
            if hasattr(self, 'qa_panel'):
                self.qa_panel.set_available_track_ids([])

    def get_current_annotation_with_qa(self):
        """Get current annotation data including QA"""
        if not self.current_annotation_data:
            return None
        
        # Add QA data
        annotation_data = self.current_annotation_data.copy()

        # Padded Coords -> Original Coords -> BFoV
        converted_annotations = {}
        for frame_idx, bboxes in self.video_canvas.frame_bboxes.items():
            converted_annotations[frame_idx] = []
            for bbox in bboxes:
                converted_bbox = self.video_canvas.convert_bbox_for_save(bbox)
                converted_annotations[frame_idx].append(converted_bbox)

        annotation_data['annotations'] = converted_annotations

        if hasattr(self, 'qa_panel'):
            annotation_data["qa_data"] = self.qa_panel.get_all_qa_data()
        
        return annotation_data

    def on_qa_data_changed(self, qa_data):
        """Call when QA data changes"""
        if self.current_annotation_data:
            self.current_annotation_data["qa_data"] = qa_data
            print(f'QA data changed: {qa_data}\t{len(qa_data)} QAs')
        
        # Enable Save Annotation Button
        self.save_annotation_btn.setEnabled(True)
        self.save_as_btn.setEnabled(True)