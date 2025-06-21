import os
import json
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QWidget, QPushButton, QLabel,
    QGroupBox, QTextEdit, QComboBox, QCheckBox, QScrollArea,
    QMessageBox, QGridLayout
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
        
        # Load Question Categories
        self.question_categories = self.load_question_categories()
        
        # Current Available Track IDs
        self.available_track_ids = []
        
        self.setup_ui()
        
    def setup_ui(self):
        """Setup QA panel UI"""
        layout = QVBoxLayout(self)
        
        # QA Session Info
        self.session_info_label = QLabel("No QA sessions")
        self.session_info_label.setStyleSheet("font-weight: bold; color: #333; margin-bottom: 10px;")
        layout.addWidget(self.session_info_label)
        
        # Question Category
        category_layout = QHBoxLayout()
        category_layout.addWidget(QLabel("Question Category:"))
        
        self.category_combo = QComboBox()
        self.category_combo.addItems(self.question_categories)
        category_layout.addWidget(self.category_combo)
        layout.addLayout(category_layout)
        
        # Question Input
        layout.addWidget(QLabel("Question:"))
        self.question_input = QTextEdit()
        self.question_input.setMaximumHeight(80)
        self.question_input.setPlaceholderText("Enter your question here...")
        layout.addWidget(self.question_input)
        
        # Answer Input
        layout.addWidget(QLabel("Answer:"))
        self.answer_input = QTextEdit()
        self.answer_input.setMaximumHeight(80)
        self.answer_input.setPlaceholderText("Enter your answer here...")
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
            with open(json_path, "r") as f:
                return json.load(f)
        else:
            print(f"Warning: Question categories file not found at {json_path}")
            QMessageBox.warning(
                self, "File Not Found",
                f"The file 'question_categories.json' was not found at {json_path}"
            )
            return ["General"]
    
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
    
    def save_current_qa(self):
        """Save current QA session"""
        question = self.question_input.toPlainText().strip()
        answer = self.answer_input.toPlainText().strip()
        category = self.category_combo.currentText()
        
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
        
        # Create QA Data
        qa_data = {
            "qa_id": len(self.qa_sessions) + 1,
            "question_category": category,
            "question": question,
            "answer": answer,
            "grounded_objects": grounded_objects
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
        
        QMessageBox.information(self, "QA Saved", f"QA session saved successfully!")
    
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
        self.category_combo.setCurrentIndex(0)
        
        # Clear all checkboxes
        for checkbox in self.grounded_checkboxes.values():
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
                current_qa["question_category"] != self.category_combo.currentText())
    
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
            category_index = self.category_combo.findText(qa["question_category"])
            if category_index >= 0:
                self.category_combo.setCurrentIndex(category_index)
            
            # grounded objects 체크
            for track_id, checkbox in self.grounded_checkboxes.items():
                checkbox.setChecked(track_id in qa["grounded_objects"])
    
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