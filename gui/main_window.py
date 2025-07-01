# gui/main_window.py
"""
Main Window for Video QA Annotation Tool
"""

import os
import json
from datetime import datetime

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
    QMessageBox,
    QSpinBox,
    QTabWidget,
    QListWidget,
    QListWidgetItem
)

from gui.annotation_panel import AnnotationPanel
from gui.object_panel import ObjectPanel
from gui.qa_panel import QAPanel
from gui.config import PANEL_WIDTH
from gui.video_canvas import VideoCanvas



class MainWindow(QMainWindow):
    """Main Application Window"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Video QA Annotation Tool")
        self.setGeometry(100, 100, 1400, 700)

        # Annotation State
        self.current_annotation = None
        self.sampled_frames = []
        self.current_segment_index = 0

        # Navigation mode : 'frame' or 'segment'
        self.navigation_mode = "frame"

        # Bbox Annotation State
        self.bbox_annotation_active = False
        self.selected_objects_for_bbox = []

        # Current Video and Annotation Data
        self.current_video_name = None
        self.current_annotation_data = None
        self.saved_annotations = {}

        # Current Working JSON File
        self.current_json_file = None


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
        self.save_as_btn = QPushButton("Save As...")
        self.load_annotation_btn = QPushButton("Load Annotation")

        for btn in [self.load_video_btn, self.save_annotation_btn, self.save_as_btn, self.load_annotation_btn]:
            btn.setMinimumWidth(120)
            btn.setMinimumHeight(32)

        file_layout.addWidget(self.load_video_btn)
        file_layout.addWidget(self.save_annotation_btn)
        file_layout.addWidget(self.save_as_btn)
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

        # Navigation buttons
        nav_layout = QHBoxLayout()
        self.prev_frame_btn = QPushButton("◀ Previous Frame (D, C)")
        self.next_frame_btn = QPushButton("Next Frame (F, V) ▶")
        nav_layout.addWidget(self.prev_frame_btn)
        nav_layout.addWidget(self.next_frame_btn)

        # Segment buttons
        segment_layout = QHBoxLayout()
        self.prev_segment_btn = QPushButton("◀◀ Previous Segment (D, C)")
        self.next_segment_btn = QPushButton("Next Segment (F, V) ▶▶")

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
        layout = QVBoxLayout(panel)

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
        """Create grounding tab with existing controls"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Top row: Object panel + Annotation panel
        top_row_layout = QHBoxLayout()
        
        # Object selection panel
        self.object_panel = ObjectPanel()
        
        # Annotation controls panel
        self.annotation_panel = AnnotationPanel()
        
        top_row_layout.addWidget(self.object_panel)
        top_row_layout.addWidget(self.annotation_panel)
        
        # Action buttons
        action_group = QGroupBox("Annotation Controls")
        action_layout = QVBoxLayout(action_group)
        
        # Status Label
        self.annotation_status_label = QLabel("Load video and select objects to start annotation")
        self.annotation_status_label.setStyleSheet(
            "color: #666; font-style: italic; padding: 5px; "
            "border: 1px solid #ddd; border-radius: 3px;"
        )
        
        # Main Buttons
        main_button_layout = QHBoxLayout()
        self.start_annotation_btn = QPushButton("Start Annotation")
        main_button_layout.addWidget(self.start_annotation_btn)
        main_button_layout.addWidget(self.save_annotation_btn)
        
        # Bbox Annotation Buttons
        bbox_layout = QHBoxLayout()
        self.start_bbox_btn = QPushButton("Start BBox Mode")
        self.stop_bbox_btn = QPushButton("Stop BBox Mode")
        bbox_layout.addWidget(self.start_bbox_btn)
        bbox_layout.addWidget(self.stop_bbox_btn)
        
        # BBox Edit Buttons
        edit_layout = QHBoxLayout()
        self.undo_bbox_btn = QPushButton("Undo Last BBox")
        self.clear_frame_btn = QPushButton("Clear Frame")
        edit_layout.addWidget(self.undo_bbox_btn)
        edit_layout.addWidget(self.clear_frame_btn)
        
        # Initial Disable
        self.start_annotation_btn.setEnabled(False)
        self.save_annotation_btn.setEnabled(False)
        self.start_bbox_btn.setEnabled(False)
        self.stop_bbox_btn.setEnabled(False)
        self.undo_bbox_btn.setEnabled(False)
        self.clear_frame_btn.setEnabled(False)
        
        action_layout.addWidget(self.annotation_status_label)
        action_layout.addLayout(main_button_layout)
        action_layout.addLayout(bbox_layout)
        action_layout.addLayout(edit_layout)
        
        layout.addLayout(top_row_layout)
        layout.addWidget(action_group)
        layout.addStretch()
        
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

    def setup_connections(self):
        """Setup signal connections"""
        # File operations
        self.load_video_btn.clicked.connect(self.load_video)
        self.save_annotation_btn.clicked.connect(self.save_annotation)
        self.save_as_btn.clicked.connect(self.save_as_new_file)
        self.load_annotation_btn.clicked.connect(self.load_annotation)

        # Video controls
        self.prev_frame_btn.clicked.connect(self.navigate_prev)
        self.next_frame_btn.clicked.connect(self.navigate_next)
        self.prev_segment_btn.clicked.connect(self.prev_segment)
        self.next_segment_btn.clicked.connect(self.next_segment)

        # Annotation controls
        self.annotation_panel.apply_segment_btn.clicked.connect(self.apply_time_segment)
        self.annotation_panel.undo_segment_btn.clicked.connect(self.undo_time_segment)

        # Action buttons
        self.start_annotation_btn.clicked.connect(self.start_annotation)

        # BBox Annotation Buttons
        self.start_bbox_btn.clicked.connect(self.start_bbox_annotation)
        self.stop_bbox_btn.clicked.connect(self.stop_bbox_annotation)
        self.undo_bbox_btn.clicked.connect(self.undo_last_bbox)
        self.clear_frame_btn.clicked.connect(self.clear_current_frame)

        # Object Panel selection change detector
        self.object_panel.connect_selection_changed(self.on_object_selection_changed)

        self.annotation_panel.start_frame_input.editingFinished.connect(lambda: self.setFocus())
        self.annotation_panel.end_frame_input.editingFinished.connect(lambda: self.setFocus())
        self.annotation_panel.interval_input.editingFinished.connect(lambda: self.setFocus())

        if hasattr(self, 'qa_panel'):
            self.qa_panel.qa_data_changed.connect(self.on_qa_data_changed)

    def setup_keyboard_shortcuts(self):
        """Setup keyboard shortcuts"""

        # D Mapping: Prev Frame
        self.d_shortcut = QShortcut(QKeySequence(Qt.Key_D), self)
        self.d_shortcut.activated.connect(self.navigate_prev)
        self.d_shortcut.setContext(Qt.ApplicationShortcut)

        # F Mapping: Next Frame
        self.f_shortcut = QShortcut(QKeySequence(Qt.Key_F), self)
        self.f_shortcut.activated.connect(self.navigate_next)
        self.f_shortcut.setContext(Qt.ApplicationShortcut)

        # C Mapping: Next Frame
        self.c_shortcut = QShortcut(QKeySequence(Qt.Key_C), self)
        self.c_shortcut.activated.connect(lambda: self.prev_n_frame(10))
        self.c_shortcut.setContext(Qt.ApplicationShortcut)

        # V Mapping: Next Frame
        self.v_shortcut = QShortcut(QKeySequence(Qt.Key_V), self)
        self.v_shortcut.activated.connect(lambda: self.next_n_frame(10))
        self.v_shortcut.setContext(Qt.ApplicationShortcut)


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
                self.current_video_name = os.path.splitext(os.path.basename(file_path))[0]
                print(f"Successfully loaded video: {file_path}")
                print(f'Video loaded: {self.current_video_name}')

                self.update_frame_info()

                # Update annotation panel with video info
                self.annotation_panel.set_video_info(self.video_canvas.total_frames)

                # Reset annotation state
                self.reset_annotation_state()

                self.update_annotation_status(f"Video loaded: {self.current_video_name}")
            else:
                print(f"Failed to load video: {file_path}")

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

    def reset_annotation_state(self):
        """Reset annotation state"""
        self.current_annotation = None
        self.sampled_frames = []
        self.current_segment_index = 0
        self.prev_segment_btn.setEnabled(False)
        self.next_segment_btn.setEnabled(False)

        self.current_annotation_data = None
        self.bbox_annotation_active = False
        self.selected_objects_for_bbox = []

        # Reset Button State
        self.start_annotation_btn.setEnabled(False)
        self.save_annotation_btn.setEnabled(False)
        self.save_as_btn.setEnabled(False)
        self.start_bbox_btn.setEnabled(False)
        self.stop_bbox_btn.setEnabled(False)
        self.undo_bbox_btn.setEnabled(False)
        self.clear_frame_btn.setEnabled(False)

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
        """Save annotation to JSON - Concat to current loaded JSON file"""
        if not self.get_current_annotation_with_qa():
            QMessageBox.warning(self, "No Annotation", "No annotation to save")
            return
        
        # If Current working JSON File is set, save at that file
        if self.current_json_file:
            if self.save_to_file(self.current_json_file):
                QMessageBox.information(self, "Save Success", f"Annotation saved to {os.path.basename(self.current_json_file)}")
            else:
                QMessageBox.critical(self, "Save Failed", "Failed to save annotation")
        else:
            # Load 하지 않고 처음 작업하는 경우 새 파일로 저장
            self.save_as_new_file()
        
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
                data = {"videos": {}}
            
            video_name = self.current_video_name
            current_annotation = self.get_current_annotation_with_qa()
            
            # Initialize video entry (if not exists)
            if video_name not in data["videos"]:
                data["videos"][video_name] = {
                    "video_info": current_annotation["video_info"],
                    "groundings": []
                }
            
            existing_ids = [g.get('grounding_id') for g in data['videos'][video_name]['groundings']]
            next_id = max(existing_ids) + 1 if existing_ids else 1

            # Add new grounding
            new_grounding = {
                "grounding_id": next_id,
                "created_at": datetime.now().isoformat(),
                "time_segment": current_annotation["time_segment"],
                "selected_objects": current_annotation["selected_objects"],
                "annotations": current_annotation["annotations"],
                "qa_sessions": current_annotation.get("qa_data", [])
            }
            
            data["videos"][video_name]["groundings"].append(new_grounding)
            
            # Save to file
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            grounding_count = len(data["videos"][video_name]["groundings"])
            print(f"Saved grounding #{grounding_count} for {video_name}")
            return True
            
        except Exception as e:
            print(f"Error saving: {e}")
            return False

    def load_annotation(self):
        """Load annotation - 비디오별 최신 grounding 로드"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Load Annotation", "",
            "JSON files (*.json);;All files (*.*)"
        )

        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # 현재 파일로 설정
                self.current_json_file = file_path
                
                # 현재 비디오 찾기
                if self.current_video_name not in data["videos"]:
                    QMessageBox.warning(self, "Video Not Found", 
                                        f"No annotations found for video '{self.current_video_name}'")
                    return
                
                video_data = data["videos"][self.current_video_name]
                groundings = video_data["groundings"]
                
                if not groundings:
                    QMessageBox.warning(self, "No Groundings", 
                                        f"No groundings found for video '{self.current_video_name}'")
                    return
                
                # 가장 최근 grounding 로드 (마지막 것)
                latest_grounding = groundings[-1]
                self.load_grounding_data(latest_grounding)
                
                QMessageBox.information(self, "Load Successful", 
                                        f"Loaded grounding #{latest_grounding['grounding_id']} from {os.path.basename(file_path)}\n"
                                        f"Total groundings for this video: {len(groundings)}")
                
            except Exception as e:
                QMessageBox.critical(self, "Load Failed", f"Failed to load: {e}")

    def load_grounding_data(self, grounding_data):
        """grounding 데이터를 UI에 로드"""
        try:
            # Time segment 설정
            time_segment = grounding_data["time_segment"]
            self.annotation_panel.start_frame_input.setValue(time_segment["start_frame"])
            self.annotation_panel.end_frame_input.setValue(time_segment["end_frame"])
            self.annotation_panel.interval_input.setValue(time_segment["interval"])
            
            # Time segment 적용
            self.apply_time_segment()
            
            # Objects 선택
            self.object_panel.clear_selection()
            for obj in grounding_data["selected_objects"]:
                if obj in self.object_panel.checkboxes:
                    self.object_panel.checkboxes[obj].setChecked(True)
            
            # Annotation 시작
            self.start_annotation()
            
            # BBox 데이터 로드
            self.video_canvas.frame_bboxes = grounding_data["annotations"]
            self.rebuild_track_registries()
            
            # QA 데이터 로드
            if hasattr(self, 'qa_panel'):
                self.qa_panel.set_qa_data(grounding_data.get("qa_sessions", []))
                self.update_qa_panel_track_ids()
            
            self.update_annotation_status(f"Loaded grounding #{grounding_data['grounding_id']} - ready to continue")
            
        except Exception as e:
            QMessageBox.critical(self, "Load Error", f"Error loading grounding: {e}")

    def rebuild_track_registries(self):
        """Track registry 재구축"""
        self.video_canvas.existing_track_ids = {}
        self.video_canvas.track_registry = {}
        color_index = 0
        
        for frame_bboxes in self.video_canvas.frame_bboxes.values():
            for bbox in frame_bboxes:
                track_id = bbox['track_id']
                object_type = bbox['object_type']
                
                # existing_track_ids 업데이트
                if object_type not in self.video_canvas.existing_track_ids:
                    self.video_canvas.existing_track_ids[object_type] = []
                if track_id not in self.video_canvas.existing_track_ids[object_type]:
                    self.video_canvas.existing_track_ids[object_type].append(track_id)
                
                # 색상 할당
                if track_id not in self.video_canvas.track_registry:
                    color = self.video_canvas.color_palette[color_index % len(self.video_canvas.color_palette)]
                    self.video_canvas.track_registry[track_id] = color
                    color_index += 1
        
        self.video_canvas.color_index = color_index
        self.video_canvas.update()
        print(f"Rebuilt registries: {len(self.video_canvas.track_registry)} tracks")

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
        target_frame = max(0, self.video_canvas.current_frame - n)
        if self.video_canvas.set_frame(target_frame):
            self.update_frame_info()

    def next_n_frame(self, n):
        """Go to next n-frame"""
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
            print(
                f"Navigated to segment {self.current_segment_index} of {len(self.sampled_frames) - 1} (frame {frame_num})"
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
                f"Navigated to segment {self.current_segment_index} of {len(self.sampled_frames) - 1} (frame {frame_num})"
            )

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
        self.navigation_mode = 'segment'

        # Enable undo button
        self.annotation_panel.undo_segment_btn.setEnabled(True)

        # Change keyboard focus to main window
        self.setFocus()

        # Update Butto State
        self.on_object_selection_changed()

        # Update QA Panel with time segment info
        if hasattr(self, 'qa_panel'):
            self.qa_panel.set_available_time_segments(sampled_frames)

        print(f"Applied time segment: {start_frame}-{end_frame}, interval: {interval}")
        print(f"Sampled frames: {sampled_frames}")

    def undo_time_segment(self):
        """Undo time segment"""
        self.navigation_mode = 'frame'

        self.sampled_frames = []
        self.current_segment_index = 0

        self.prev_segment_btn.setEnabled(False)
        self.next_segment_btn.setEnabled(False)

        self.annotation_panel.undo_segment_btn.setEnabled(False)
        self.annotation_panel.update_segment_info([])

        self.setFocus()

        # Update Button State
        self.on_object_selection_changed()

        print("Undo time segment sampling - return to frame navigation mode")

    def start_annotation(self):
        """Start Annotation (If current annotation is ongoing, ask for confirmation)"""
        # Check if there is ongoing annotation
        if self.current_annotation_data is not None or self.video_canvas.frame_bboxes:
            total_bboxes = sum(len(bboxes) for bboxes in self.video_canvas.frame_bboxes.values())
            if total_bboxes > 0:
                result = QMessageBox.question(self, "Start New Annotation", 
                                            f"Current annotation has {total_bboxes} bounding boxes.\n"
                                            f"Start new annotation? (Current work will be lost)",
                                            QMessageBox.Yes | QMessageBox.No)
                if result == QMessageBox.No:
                    return
        
        # Check required conditions
        if not self.current_video_name:
            QMessageBox.warning(self, "No Video", "Please load a video first.")
            return
            
        selected_objects = self.object_panel.get_selected_objects()
        if not selected_objects:
            QMessageBox.warning(self, "No Objects", "Please select objects first.")
            return
            
        if not self.sampled_frames:
            QMessageBox.warning(self, "No Time Segment", "Please apply time segment first.")
            return

        # Start new annotation
        self.current_annotation_data = {
            "video_info": {
                "filename": self.current_video_name,
                "total_frames": self.video_canvas.total_frames,
                "fps": self.video_canvas.fps
            },
            "time_segment": {
                "start_frame": self.sampled_frames[0] if self.sampled_frames else 0,
                "end_frame": self.sampled_frames[-1] if self.sampled_frames else 0,
                "interval": self.annotation_panel.get_segment_info()["interval"],
                "sampled_frames": self.sampled_frames.copy()
            },
            "selected_objects": selected_objects.copy(),
            "annotations": {},
            "qa_data": None
        }

        # Initialize BBox data
        self.video_canvas.frame_bboxes = {}
        self.video_canvas.existing_track_ids = {}
        self.video_canvas.track_registry = {}
        self.video_canvas.color_index = 0

        if hasattr(self, 'qa_panel'):
            self.qa_panel.reset_qa_panel()
            self.qa_panel.set_available_time_segments(self.sampled_frames)

        # Update UI state
        self.start_bbox_btn.setEnabled(True)
        self.update_annotation_status(f"Annotation started: {', '.join(selected_objects)}")
        
        print(f"Started annotation for {self.current_video_name}")
        print(f"Objects: {selected_objects}")

    def update_annotation_status(self, message):
        """Update annotation status label"""
        self.annotation_status_label.setText(message)

    def on_object_selection_changed(self):
        """Call when Object Panel selection changes"""
        selected_objects = self.object_panel.get_selected_objects()

        # Start button activation conditions
        has_video = self.current_video_name is not None
        has_objects = len(selected_objects) > 0
        has_segments = len(self.sampled_frames) > 0
        
        self.start_annotation_btn.setEnabled(has_video and has_objects and has_segments)
        
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
                self.start_annotation_btn.setText('Start Annotation')
            else:
                current_str = ', '.join(sorted(current_objects))
                new_str = ', '.join(sorted(new_objects))
                self.update_annotation_status(f"Current: {current_str} → Click to restart with: {new_str}")
                self.start_annotation_btn.setText('Restart Annotation')
        else:
            self.update_annotation_status(f"Ready to start: {', '.join(selected_objects)}")
            self.start_annotation_btn.setText('Start Annotation')

    def start_bbox_annotation(self):
        """Start Bbox Annotation"""
        selected_objects = self.object_panel.get_selected_objects()
        
        if not selected_objects:
            QMessageBox.warning(self, "No Objects Selected", 
                                "Please select at least one object type before starting annotation.")
            return
        
        if not self.sampled_frames:
            QMessageBox.warning(self, "No Time Segment", 
                                "Please apply time segment first before starting annotation.")
            return
        
        # Activate Bbox Annotation Mode
        self.bbox_annotation_active = True
        self.selected_objects_for_bbox = selected_objects.copy()
        
        # Activate Bbox Annotation Mode on Video Canvas
        self.video_canvas.enable_bbox_mode(self.selected_objects_for_bbox)
        
        # Move to first segment frame
        if self.sampled_frames:
            self.current_segment_index = 0
            self.video_canvas.set_frame(self.sampled_frames[0])
            self.update_frame_info()
            
            # Change to segment mode
            self.navigation_mode = 'segment'
        
        # Update button states
        self.start_bbox_btn.setEnabled(False)
        self.stop_bbox_btn.setEnabled(True)
        self.undo_bbox_btn.setEnabled(True)
        self.clear_frame_btn.setEnabled(True)
        
        # Disable Object Selection (cannot change during annotation)
        self.object_panel.setEnabled(False)
        
        print(f"Started bbox annotation for objects: {self.selected_objects_for_bbox}")
        print(f"Annotation will be done on {len(self.sampled_frames)} frames")

    def stop_bbox_annotation(self):
        """End Bbox Annotation"""
        if not self.bbox_annotation_active:
            return
        
        # Save bbox data to current annotation
        if self.current_annotation_data:
            self.current_annotation_data["annotations"] = self.video_canvas.get_all_annotations()
        
        # Deactivate Bbox Annotation Mode
        self.bbox_annotation_active = False
        self.video_canvas.disable_bbox_mode()

        # Update UI State
        self.start_bbox_btn.setEnabled(True)
        self.stop_bbox_btn.setEnabled(False)
        self.undo_bbox_btn.setEnabled(False)
        self.clear_frame_btn.setEnabled(False)

        # Activate Object Selection
        self.object_panel.setEnabled(True)

        # Update Status
        annotated_frames = len(self.video_canvas.frame_bboxes)
        total_frames = len(self.sampled_frames)
        self.update_annotation_status(f"BBox Completed: {annotated_frames}/{total_frames} frames - Ready for QA")

        # Update QA Panel
        self.update_qa_panel_track_ids()
        
        # Switch to QA tab (optional)
        if hasattr(self, 'tab_widget'):
            result = QMessageBox.question(self, "Switch to QA", 
                                        "BBox annotation completed. Switch to QA tab?",
                                        QMessageBox.Yes | QMessageBox.No)
            if result == QMessageBox.Yes:
                self.tab_widget.setCurrentIndex(1)  # QA tab

        print(f"BBox Annotation Completed: {annotated_frames}/{total_frames} frames")

    def undo_last_bbox(self):
        """Remove last bbox on current frame"""
        if not self.bbox_annotation_active:
            return
        
        if self.video_canvas.undo_last_bbox():
            print(f"Undid last bbox on frame {self.video_canvas.current_frame}")
        else:
            QMessageBox.information(self, "No BBox", "No bounding boxes to undo on current frame.")

    def clear_current_frame(self):
        """Remove all bboxes on current frame"""
        if not self.bbox_annotation_active:
            return
        
        current_frame = self.video_canvas.current_frame
        bbox_count = len(self.video_canvas.frame_bboxes.get(current_frame, []))
        
        if bbox_count == 0:
            QMessageBox.information(self, "No BBoxes", "No bounding boxes to clear on current frame.")
            return
        
        result = QMessageBox.question(self, "Clear Frame", 
                                    f"Are you sure you want to clear all {bbox_count} bounding boxes from current frame?",
                                    QMessageBox.Yes | QMessageBox.No)
        
        if result == QMessageBox.Yes:
            cleared_count = self.video_canvas.clear_current_frame_bboxes()
            print(f"Cleared {cleared_count} bboxes from frame {current_frame}")

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