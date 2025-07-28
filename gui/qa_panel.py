import os
import json
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QWidget, QPushButton, QLabel,
    QGroupBox, QTextEdit, QComboBox, QCheckBox, QScrollArea,
    QMessageBox, QGridLayout, QSpinBox
)

from gui.config import PANEL_WIDTH, PANEL_SPACING

class QAPanel(QGroupBox):
    """QA panel for question-answer annotation"""

    # QA Signal Definition
    qa_data_changed = Signal(object)

    def __init__(self):
        super().__init__("Question & Answer")
        self.setMinimumWidth(PANEL_WIDTH - PANEL_SPACING * 2)
        
        # QA Data Management
        self.qa_sessions = []  # Save Several QAs
        self.current_qa_index = 0

        # Current Available Track IDs
        self.available_track_ids = []
        
        # Setup UI
        self.setup_ui()

        # Load Question Categories
        self.question_categories = self.load_question_categories()
        
    def setup_ui(self):
        """Setup QA panel UI"""
        layout = QVBoxLayout(self)
        
        # QA Session Info
        self.session_info_label = QLabel("No QA sessions")
        self.session_info_label.setStyleSheet("font-weight: bold; color: #333; margin-bottom: 10px;")
        layout.addWidget(self.session_info_label)
        
        # Question Category (Nested 2)
        category_layout = QVBoxLayout()

        ## Main Question Category
        main_cat_layout = QHBoxLayout()
        main_cat_layout.addWidget(QLabel("Main Category:"))
        self.main_category_combo = QComboBox()
        self.main_category_combo.currentTextChanged.connect(self.on_main_category_changed)
        main_cat_layout.addWidget(self.main_category_combo)
        category_layout.addLayout(main_cat_layout)

        ## Sub Question Category
        sub_cat_layout = QHBoxLayout()
        sub_cat_layout.addWidget(QLabel("Sub Category:"))
        self.sub_category_combo = QComboBox()
        sub_cat_layout.addWidget(self.sub_category_combo)
        category_layout.addLayout(sub_cat_layout)

        layout.addLayout(category_layout)
        
        # Question Input
        layout.addWidget(QLabel("Question:"))
        self.question_input = QTextEdit()
        self.question_input.setMaximumHeight(80)
        self.question_input.setPlaceholderText("Enter your question here...")
        ## Tab Keymapping Overrride
        self.question_input.keyPressEvent = self.question_key_press_event
        layout.addWidget(self.question_input)
        
        # Answer Input
        layout.addWidget(QLabel("Answer:"))
        self.answer_input = QTextEdit()
        self.answer_input.setMaximumHeight(80)
        self.answer_input.setPlaceholderText("Enter your answer here...")
        self.answer_input.keyPressEvent = self.answer_key_press_event
        layout.addWidget(self.answer_input)
        
        # Grounded Objects
        grounded_group = QGroupBox("Grounded Objects")
        grounded_layout = QVBoxLayout(grounded_group)
        
        # Scroll Area for Track IDs
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFixedHeight(120)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.grounded_widget = QWidget()
        self.grounded_layout = QGridLayout(self.grounded_widget)
        self.grounded_layout.setSpacing(2)
        
        scroll_area.setWidget(self.grounded_widget)
        grounded_layout.addWidget(scroll_area)
        
        self.grounded_checkboxes = {}
        
        layout.addWidget(grounded_group)

        # Time Segment Grounding for QAs
        temporal_group = QGroupBox('Time Segment Grounding')
        temporal_layout = QVBoxLayout(temporal_group)

        # Time Segment Range UI
        range_control_group = QGroupBox("Select Segment Range")
        range_control_layout = QVBoxLayout(range_control_group)

        ## Start Segment Index
        start_segment_layout = QHBoxLayout()
        start_segment_layout.addWidget(QLabel("Start Segment:"))
        self.start_segment_spinbox = QSpinBox()
        self.start_segment_spinbox.setMinimum(0)
        self.start_segment_spinbox.setMaximum(999)
        self.start_segment_spinbox.setValue(0)
        self.start_segment_spinbox.setSuffix(" (index)")
        start_segment_layout.addWidget(self.start_segment_spinbox)

        ## End Segment Index
        end_segment_layout = QHBoxLayout()
        end_segment_layout.addWidget(QLabel("End Segment:"))
        self.end_segment_spinbox = QSpinBox()
        self.end_segment_spinbox.setMinimum(0)
        self.end_segment_spinbox.setMaximum(999)
        self.end_segment_spinbox.setValue(10)
        self.end_segment_spinbox.setSuffix(" (index)")
        end_segment_layout.addWidget(self.end_segment_spinbox)

        ## Apply Button
        apply_range_btn = QPushButton("Apply Range")
        apply_range_btn.clicked.connect(self.apply_segment_range)

        ## Clear All Button
        clear_all_btn = QPushButton("Clear All")
        clear_all_btn.clicked.connect(self.clear_all_segments)
        ## Button Layout
        range_button_layout = QHBoxLayout()
        range_button_layout.addWidget(apply_range_btn)
        range_button_layout.addWidget(clear_all_btn)

        range_control_layout.addLayout(start_segment_layout)
        range_control_layout.addLayout(end_segment_layout)
        range_control_layout.addLayout(range_button_layout)

        temporal_layout.addWidget(range_control_group)

        # Scroll Area for Time Segment Grounding
        temporal_scroll_area = QScrollArea()
        temporal_scroll_area.setWidgetResizable(True)
        temporal_scroll_area.setFixedHeight(120)
        temporal_scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        temporal_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.temporal_widget = QWidget()
        self.temporal_layout = QGridLayout(self.temporal_widget)
        self.temporal_layout.setSpacing(2)

        temporal_scroll_area.setWidget(self.temporal_widget)
        temporal_layout.addWidget(temporal_scroll_area)

        self.temporal_checkboxes = {}

        layout.addWidget(temporal_group)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.save_qa_btn = QPushButton("Save QA")
        self.save_qa_btn.clicked.connect(self.save_current_qa)
        self.save_qa_btn.setEnabled(False)
        
        self.new_qa_btn = QPushButton("New QA")
        self.new_qa_btn.clicked.connect(self.create_new_qa)
        self.new_qa_btn.setEnabled(False)
        
        self.delete_qa_btn = QPushButton("Delete QA")
        self.delete_qa_btn.clicked.connect(self.delete_current_qa)
        self.delete_qa_btn.setEnabled(False)
        
        self.clear_qa_btn = QPushButton("Clear")
        self.clear_qa_btn.clicked.connect(self.clear_current_qa)
        
        button_layout.addWidget(self.save_qa_btn)
        button_layout.addWidget(self.new_qa_btn)
        button_layout.addWidget(self.delete_qa_btn)
        button_layout.addWidget(self.clear_qa_btn)
        
        layout.addLayout(button_layout)
        
        # Navigation Buttons
        nav_layout = QHBoxLayout()
        
        self.prev_qa_btn = QPushButton("◀ Previous QA")
        self.prev_qa_btn.clicked.connect(self.prev_qa_session)
        self.prev_qa_btn.setEnabled(False)
        
        self.next_qa_btn = QPushButton("Next QA ▶")
        self.next_qa_btn.clicked.connect(self.next_qa_session)
        self.next_qa_btn.setEnabled(False)
        
        nav_layout.addWidget(self.prev_qa_btn)
        nav_layout.addWidget(self.next_qa_btn)
        
        layout.addLayout(nav_layout)
        
    def load_question_categories(self):
        """Load question categories from JSON file"""
        json_path = os.path.join("data", "question_categories.json")
        if os.path.exists(json_path):
            with open(json_path, "r", encoding="utf-8") as f:
                categories_data = json.load(f)
                self.setup_category_combos(categories_data)
                return categories_data
        else:
            print(f"Warning: Question categories file not found at {json_path}")
            QMessageBox.warning(
                self, "File Not Found",
                f"The file 'question_categories.json' was not found at {json_path}"
            )
            default_categories = {"question_categories.json Error": ["ERROR!!"]}
            self.setup_category_combos(default_categories)
            return default_categories
    
    def setup_category_combos(self, categories_data):
        """Setup main & sub category combos"""
        self.categories_data = categories_data

        # Main category combo
        self.main_category_combo.clear()
        self.main_category_combo.addItems(list(categories_data.keys()))

        if categories_data:
            first_main = list(categories_data.keys())[0]
            self.update_sub_categories(first_main)
    
    def on_main_category_changed(self, main_category):
        """If Main Category changes, update sub category"""
        if main_category:
            self.update_sub_categories(main_category)
    
    def update_sub_categories(self, main_category):
        """Update sub category combo box"""
        self.sub_category_combo.clear()

        if main_category in self.categories_data:
            sub_categories = self.categories_data[main_category]
            self.sub_category_combo.addItems(sub_categories)
    
    def get_current_category(self):
        """Return currently selected categorie (Main > Sub)"""
        main_cat = self.main_category_combo.currentText()
        sub_cat = self.sub_category_combo.currentText()

        return {
            'main': main_cat,
            'sub': sub_cat
        }
    
    def set_available_track_ids(self, track_ids):
        """Update available track IDs for grounding"""
        self.available_track_ids = track_ids
        self.update_grounded_objects_list()
        
        # Enable QA Input
        if track_ids:
            self.save_qa_btn.setEnabled(True)
            self.new_qa_btn.setEnabled(True)
        
    def update_grounded_objects_list(self):
        """Update grounded objects checkboxes"""
        # Remove existing checkboxes
        for i in reversed(range(self.grounded_layout.count())):
            child = self.grounded_layout.itemAt(i)
            if child and child.widget():
                child.widget().setParent(None)
        
        self.grounded_checkboxes.clear()
        
        # Create checkboxes for each
        if not self.available_track_ids:
            no_objects_label = QLabel("No track IDs available")
            no_objects_label.setStyleSheet("color: #666; font-style: italic;")
            self.grounded_layout.addWidget(no_objects_label, 0, 0)
            return
        
        # Arrange in 2 columns
        for i, track_id in enumerate(self.available_track_ids):
            checkbox = QCheckBox(track_id)
            row = i // 2
            col = i % 2
            self.grounded_layout.addWidget(checkbox, row, col)
            self.grounded_checkboxes[track_id] = checkbox
    
    def set_available_time_segments(self, sampled_frames):
        """Update available time segments for grounding"""
        self.sampled_frames = sampled_frames
        self.update_time_segment_list()
    
    def update_time_segment_list(self):
        """Update time segment checkboxes"""
        # Clear existing checkboxes
        for i in reversed(range(self.temporal_layout.count())):
            child = self.temporal_layout.itemAt(i)
            if child and child.widget():
                child.widget().setParent(None)
        
        self.temporal_checkboxes.clear()
        self.update_segment_range_limits()

        if not hasattr(self, 'sampled_frames') or not self.sampled_frames:
            no_segments_label = QLabel("No segments available")
            no_segments_label.setStyleSheet("color: #666; font-style: italic;")
            self.temporal_layout.addWidget(no_segments_label, 0, 0)
            return
        
        # Create Checkboxes for each time segment
        for i, frame_index in enumerate(self.sampled_frames):
            checkbox = QCheckBox(f'Seg {i} (Frame {frame_index})')
            row = i // 2
            col = i % 2
            self.temporal_layout.addWidget(checkbox, row, col)
            self.temporal_checkboxes[i] = checkbox

    def save_current_qa(self):
        """Save current QA session"""
        question = self.question_input.toPlainText().strip()
        answer = self.answer_input.toPlainText().strip()
        category = self.get_current_category()
        
        if not question or not answer:
            QMessageBox.warning(self, "Incomplete QA", "Please enter both question and answer.")
            return
        
        # Collect selected grounded objects
        grounded_objects = []
        for track_id, checkbox in self.grounded_checkboxes.items():
            if checkbox.isChecked():
                grounded_objects.append(track_id)
        
        if not grounded_objects:
            result = QMessageBox.question(self, "No Grounded Objects",
                                        "No objects are selected for grounding. Continue anyway?",
                                        QMessageBox.Yes | QMessageBox.No)
            if result == QMessageBox.No:
                return
        
        # Collect selected time segments
        time_segments = []
        time_frames = []
        for segment_index, checkbox in self.temporal_checkboxes.items():
            if checkbox.isChecked():
                time_segments.append(segment_index)
                if hasattr(self, 'sampled_frames') and segment_index < len(self.sampled_frames):
                    time_frames.append(self.sampled_frames[segment_index])
        
        try:
            # Create QA Data
            qa_data = {
                "qa_id": len(self.qa_sessions) + 1,
                "question_category": category,
                "question": question,
                "answer": answer,
                "grounded_objects": grounded_objects,
                'temporal_grounding': {
                    'time_segment_indices': time_segments,
                    'frame_indices': time_frames
                }
            }
            
            # Save to current index (modify) or add new
            if self.current_qa_index < len(self.qa_sessions):
                self.qa_sessions[self.current_qa_index] = qa_data
                print(f"Updated QA {self.current_qa_index + 1}")
            else:
                self.qa_sessions.append(qa_data)
                print(f"Saved new QA {len(self.qa_sessions)}")
            
            self.update_session_info()
            self.update_navigation_buttons()

            # Signal: MainWindow gets notified for QA data change
            self.qa_data_changed.emit(self.qa_sessions.copy())
            
            # Automatically create new QA
            self.create_new_qa()
            
        except Exception as e:
            QMessageBox.critical(self, "Save Failed", f"Failed to save QA: {str(e)}")
            print(f"Failed to save QA: {e}")
    
    def create_new_qa(self):
        """Create new QA session"""
        # Check if current QA is not saved
        if self.has_unsaved_changes():
            result = QMessageBox.question(self, "Unsaved Changes",
                                        "Current QA has unsaved changes. Continue without saving?",
                                        QMessageBox.Yes | QMessageBox.No)
            if result == QMessageBox.No:
                return
        
        # Move to new QA session
        self.current_qa_index = len(self.qa_sessions)
        self.clear_current_qa()
        self.update_session_info()
        self.update_navigation_buttons()
        
        print(f"Created new QA session {self.current_qa_index + 1}")
    
    def delete_current_qa(self):
        """Delete current QA session"""
        if not self.qa_sessions or self.current_qa_index >= len(self.qa_sessions):
            QMessageBox.warning(self, "No QA", "No QA session to delete.")
            return
        
        result = QMessageBox.question(self, "Delete QA",
                                    f"Are you sure you want to delete QA {self.current_qa_index + 1}?",
                                    QMessageBox.Yes | QMessageBox.No)
        
        if result == QMessageBox.Yes:
            del self.qa_sessions[self.current_qa_index]
            
            # Adjust index
            if self.current_qa_index >= len(self.qa_sessions) and self.qa_sessions:
                self.current_qa_index = len(self.qa_sessions) - 1
            elif not self.qa_sessions:
                self.current_qa_index = 0
            
            # Update UI
            if self.qa_sessions:
                self.load_qa_session(self.current_qa_index)
            else:
                self.clear_current_qa()
                self.current_qa_index = 0
            
            self.update_session_info()
            self.update_navigation_buttons()
            
            print(f"Deleted QA session")
    
    def clear_current_qa(self):
        """Clear current QA inputs"""
        self.question_input.clear()
        self.answer_input.clear()
        self.main_category_combo.setCurrentIndex(0)
        
        # Clear all checkboxes
        for checkbox in self.grounded_checkboxes.values():
            checkbox.setChecked(False)
        
        for checkbox in self.temporal_checkboxes.values():
            checkbox.setChecked(False)
    
    def has_unsaved_changes(self):
        """Check if current QA has unsaved changes"""
        if self.current_qa_index >= len(self.qa_sessions):
            # New QA case
            return bool(self.question_input.toPlainText().strip() or 
                        self.answer_input.toPlainText().strip())
        
        # Check
        current_qa = self.qa_sessions[self.current_qa_index]
        return (current_qa["question"] != self.question_input.toPlainText().strip() or
                current_qa["answer"] != self.answer_input.toPlainText().strip() or
                current_qa["question_category"] != self.get_current_category())
    
    def prev_qa_session(self):
        """Go to previous QA session"""
        if self.current_qa_index > 0:
            self.current_qa_index -= 1
            self.load_qa_session(self.current_qa_index)
            self.update_session_info()
            self.update_navigation_buttons()
    
    def next_qa_session(self):
        """Go to next QA session"""
        if self.current_qa_index < len(self.qa_sessions) - 1:
            self.current_qa_index += 1
            self.load_qa_session(self.current_qa_index)
            self.update_session_info()
            self.update_navigation_buttons()
    
    def load_qa_session(self, index):
        """Load QA session by index"""
        if 0 <= index < len(self.qa_sessions):
            qa = self.qa_sessions[index]
            
            self.question_input.setPlainText(qa["question"])
            self.answer_input.setPlainText(qa["answer"])
            
            # 카테고리 설정
            category_data = qa.get('question_category', {})
            if isinstance(category_data, dict):
                main_cat = category_data.get('main', '')
                sub_cat = category_data.get('sub', '')

                main_index = self.main_category_combo.findText(main_cat)
                if main_index >= 0:
                    self.main_category_combo.setCurrentIndex(main_index)
                    sub_index = self.sub_category_combo.findText(sub_cat)
                    if sub_index >= 0:
                        self.sub_category_combo.setCurrentIndex(sub_index)
            
            # grounded objects 체크
            for track_id, checkbox in self.grounded_checkboxes.items():
                checkbox.setChecked(track_id in qa["grounded_objects"])
            
            # temporal grounding 체크
            temporal_grounding = qa.get('temporal_grounding', {})
            segment_indices = temporal_grounding.get('time_segment_indices', [])
            for segment_idx, checkbox in self.temporal_checkboxes.items():
                checkbox.setChecked(segment_idx in segment_indices)
    
    def update_session_info(self):
        """Update session info display"""
        if not self.qa_sessions:
            self.session_info_label.setText("No QA sessions")
            self.delete_qa_btn.setEnabled(False)
        else:
            current = self.current_qa_index + 1
            total = len(self.qa_sessions)
            if self.current_qa_index < len(self.qa_sessions):
                self.session_info_label.setText(f"QA Session {current} of {total}")
                self.delete_qa_btn.setEnabled(True)
            else:
                self.session_info_label.setText(f"New QA Session (will be {total + 1})")
                self.delete_qa_btn.setEnabled(False)
    
    def update_navigation_buttons(self):
        """Update navigation button states"""
        self.prev_qa_btn.setEnabled(self.current_qa_index > 0)
        self.next_qa_btn.setEnabled(self.current_qa_index < len(self.qa_sessions) - 1)
    
    def get_all_qa_data(self):
        """Get all QA sessions data"""
        return self.qa_sessions.copy()
    
    def set_qa_data(self, qa_data):
        """Set QA sessions data"""
        self.qa_sessions = qa_data.copy() if qa_data else []
        self.current_qa_index = 0
        
        if self.qa_sessions:
            self.load_qa_session(0)
        else:
            self.clear_current_qa()
        
        self.update_session_info()
        self.update_navigation_buttons()
    
    def reset_qa_panel(self):
        """Reset QA panel to initial state"""
        self.qa_sessions = []
        self.current_qa_index = 0
        self.available_track_ids = []
        
        self.clear_current_qa()
        self.update_grounded_objects_list()
        self.update_session_info()
        self.update_navigation_buttons()
        
        self.save_qa_btn.setEnabled(False)
        self.new_qa_btn.setEnabled(False)

        if hasattr(self, 'start_segment_spinbox'):
            self.start_segment_spinbox.setValue(0)
            self.start_segment_spinbox.setMaximum(0)
        if hasattr(self, 'end_segment_spinbox'):
            self.end_segment_spinbox.setValue(0)
            self.end_segment_spinbox.setMaximum(0)
    
    def question_key_press_event(self, event):
        """Tab Key for moving cursor from question -> answer"""
        is_tab_key = (event.key() == Qt.Key_Tab)
        is_shift_pressed = bool(event.modifiers() & Qt.ShiftModifier)

        if is_tab_key and not is_shift_pressed:
            self.answer_input.setFocus()
            print("Moved Focus: Question -> Answer")

            event.accept()
            return
        
        QTextEdit.keyPressEvent(self.question_input, event)
    
    def answer_key_press_event(self, event):
        """Handle key press events for answer input"""
        is_tab_key = (event.key() == Qt.Key_Tab)
        is_shift_pressed = bool(event.modifiers() & Qt.ShiftModifier)

        if is_tab_key and is_shift_pressed:
            self.question_input.setFocus()
            print("Moved Focus: Answer -> Question (Shift+Tab)")

            event.accept()
            return
        
        QTextEdit.keyPressEvent(self.answer_input, event)
    
    def apply_segment_range(self):
        """지정된 범위의 세그먼트들을 체크"""
        if not hasattr(self, 'sampled_frames') or not self.sampled_frames:
            QMessageBox.warning(self, "No Segments", "No segments available to select.")
            return
        
        start_idx = self.start_segment_spinbox.value()
        end_idx = self.end_segment_spinbox.value()
        
        # 유효성 검사
        max_idx = len(self.sampled_frames) - 1
        if start_idx > max_idx or end_idx > max_idx:
            QMessageBox.warning(self, "Invalid Range", 
                            f"Segment indices must be between 0 and {max_idx}")
            return
        
        if start_idx > end_idx:
            QMessageBox.warning(self, "Invalid Range", 
                            "Start segment must be less than or equal to end segment")
            return
        
        # 범위 내의 세그먼트 체크
        checked_count = 0
        for segment_idx in range(start_idx, end_idx + 1):
            if segment_idx in self.temporal_checkboxes:
                self.temporal_checkboxes[segment_idx].setChecked(True)
                checked_count += 1
        
        # print(f"Checked {checked_count} segments from index {start_idx} to {end_idx}")

    def clear_all_segments(self):
        """모든 세그먼트 체크 해제"""
        for checkbox in self.temporal_checkboxes.values():
            checkbox.setChecked(False)
        # print("Cleared all segment selections")

    def update_segment_range_limits(self):
        """세그먼트 범위 SpinBox의 최대값 업데이트"""
        if hasattr(self, 'sampled_frames') and self.sampled_frames:
            max_idx = len(self.sampled_frames) - 1
            self.start_segment_spinbox.setMaximum(max_idx)
            self.end_segment_spinbox.setMaximum(max_idx)
            self.end_segment_spinbox.setValue(min(10, max_idx))
        else:
            self.start_segment_spinbox.setMaximum(0)
            self.end_segment_spinbox.setMaximum(0)