"""
Bounding Box Annotation Dialog with Manual Track ID Selection
"""

from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, 
                            QLabel, QComboBox, QLineEdit, 
                            QPushButton, QMessageBox, QSpinBox)
from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence, QShortcut


class CustomSpinBox(QSpinBox):
    """Custom SpinBox that passes special keys to parent dialog"""
    
    def __init__(self, parent_dialog):
        super().__init__()
        self.parent_dialog = parent_dialog
    
    def keyPressEvent(self, event):
        """Handle key events - pass special keys to dialog"""
        # W/S/Enter/Space -> Dialog
        if event.key() in (Qt.Key_W, Qt.Key_S, Qt.Key_Return, Qt.Key_Enter, Qt.Key_Space, Qt.Key_Escape):
            self.parent_dialog.keyPressEvent(event)
            return
        
        # Arrow Keys -> QSpinBox
        super().keyPressEvent(event)

class BBoxAnnotationDialog(QDialog):
    """Dialog for annotating bounding box with object type and track ID"""
    
    def __init__(self, available_objects, existing_track_ids=None, current_frame_track_ids=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Annotate Bounding Box")
        self.setModal(True)
        self.setFixedSize(380, 150)
        
        self.available_objects = available_objects
        self.existing_track_ids = existing_track_ids or {}
        self.current_frame_track_ids = current_frame_track_ids or []
        
        self.result_object_type = None
        self.result_track_id = None
        
        self.setup_ui()
        self.setup_shortcuts()
        
    def setup_ui(self):
        """Setup dialog UI"""
        layout = QVBoxLayout(self)
        
        # Object type selection
        object_layout = QHBoxLayout()
        object_layout.addWidget(QLabel("Object Type:"))
        
        self.object_combo = QComboBox()
        self.object_combo.addItems(self.available_objects)
        self.object_combo.currentTextChanged.connect(self.on_object_changed)
        object_layout.addWidget(self.object_combo)
        
        layout.addLayout(object_layout)
        
        # Track ID input with SpinBox
        track_layout = QHBoxLayout()
        track_layout.addWidget(QLabel("Track ID:"))
        
        # Object prefix (readonly)
        self.track_prefix_label = QLabel("")
        self.track_prefix_label.setStyleSheet("font-weight: bold; color: #333; min-width: 60px;")
        
        # Number SpinBox 
        # self.track_number_spinbox = QSpinBox()
        self.track_number_spinbox = CustomSpinBox(self)
        self.track_number_spinbox.setMinimum(1)
        self.track_number_spinbox.setMaximum(999)
        self.track_number_spinbox.setValue(1)
        self.track_number_spinbox.valueChanged.connect(self.on_track_number_changed)
        self.track_number_spinbox.setFixedWidth(80)

        self.track_number_spinbox.setButtonSymbols(QSpinBox.ButtonSymbols.UpDownArrows)
        self.track_number_spinbox.setFocus()
        
        # Arrow label
        arrow_label = QLabel("→")
        arrow_label.setStyleSheet("font-size: 14px; color: #666;")
        
        # Full track ID display (readonly)
        self.track_full_display = QLineEdit()
        self.track_full_display.setReadOnly(True)
        self.track_full_display.setStyleSheet("background-color: #f0f0f0;")
        self.track_full_display.setFocusPolicy(Qt.NoFocus)
        
        # Add all to track layout
        track_layout.addWidget(self.track_prefix_label)
        track_layout.addWidget(self.track_number_spinbox)
        track_layout.addWidget(arrow_label)
        track_layout.addWidget(self.track_full_display)
        
        layout.addLayout(track_layout)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.ok_button = QPushButton("OK (Enter/Space)")
        self.ok_button.clicked.connect(self.accept_annotation)
        
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        
        button_layout.addWidget(self.ok_button)
        button_layout.addWidget(self.cancel_button)
        
        layout.addLayout(button_layout)
        
        # Initialize with first object
        if self.available_objects:
            self.on_object_changed(self.available_objects[0])
        
        self.track_number_spinbox.setFocus()
    
    def setup_shortcuts(self):
        """Setup keyboard shortcuts"""
        # Enter key
        self.ok_button.setDefault(True)
        
        # ESC key for cancel
        self.escape_shortcut = QShortcut(QKeySequence(Qt.Key_Escape), self)
        self.escape_shortcut.activated.connect(self.reject)
        self.escape_shortcut.setContext(Qt.WidgetShortcut)
    
    def keyPressEvent(self, event):
        """Handle key press events"""

        # Enter & Space bar
        if event.key() in (Qt.Key_Return, Qt.Key_Enter, Qt.Key_Space):
            if self.ok_button.isEnabled():
                self.accept_annotation()
                event.accept()
                return

        # ESC
        elif event.key() == Qt.Key_Escape:
            self.reject()
            event.accept()
            return
        
        # W: Increase Track ID
        elif event.key() == Qt.Key_W:
            current_value = self.track_number_spinbox.value()
            max_value = self.track_number_spinbox.maximum()
            if current_value < max_value:
                self.track_number_spinbox.setValue(current_value+1)

            print(f'Track ID increased to {self.track_number_spinbox.value()}')
            event.accept()
            return

        # S: Decrease Track ID
        elif event.key() == Qt.Key_S:
            current_value = self.track_number_spinbox.value()
            min_value = self.track_number_spinbox.minimum()
            if current_value > min_value:
                self.track_number_spinbox.setValue(current_value-1)

            print(f'Track ID decreased to {self.track_number_spinbox.value()}')
            event.accept()
            return

        super().keyPressEvent(event)
            
    def on_object_changed(self, object_type):
        """Handle object type change"""
        if not object_type:
            return
        
        # Update prefix label
        self.track_prefix_label.setText(f"{object_type}_")
        
        # Suggest next available number (but user can change it)
        suggested_number = self.get_suggested_number(object_type)
        self.track_number_spinbox.setValue(suggested_number)
        self.on_track_number_changed(suggested_number)
    
    def get_suggested_number(self, object_type):
        """Get suggested number for object type"""
        if object_type in self.existing_track_ids and self.existing_track_ids[object_type]:
            # Extract numbers from existing track IDs
            existing_numbers = []
            for track_id in self.existing_track_ids[object_type]:
                if track_id.startswith(f"{object_type}_"):
                    try:
                        number = int(track_id.split("_")[-1])
                        existing_numbers.append(number)
                    except ValueError:
                        continue
            
            # Suggest the most recently used number (for tracking continuity)
            if existing_numbers:
                return max(existing_numbers)
            else:
                return 1
        else:
            return 1
    
    def on_track_number_changed(self, number):
        """Handle track number change"""
        object_type = self.object_combo.currentText()
        if not object_type:
            return
            
        track_id = f"{object_type}_{number:03d}"
        self.track_full_display.setText(track_id)
        
        # Check if this track ID already exists in current frame
        if track_id in self.current_frame_track_ids:
            self.track_full_display.setStyleSheet("background-color: #ffcccc; color: red;")
            self.ok_button.setEnabled(False)
        else:
            self.track_full_display.setStyleSheet("background-color: #ccffcc; color: green;")
            self.ok_button.setEnabled(True)
    
    def accept_annotation(self):
        """Accept and validate annotation"""
        object_type = self.object_combo.currentText()
        track_id = self.track_full_display.text().strip()
        
        if not object_type:
            QMessageBox.warning(self, "Error", "Please select an object type")
            return
            
        if not track_id:
            QMessageBox.warning(self, "Error", "Please enter a track ID")
            return
            
        # Check for duplicate track ID only in current frame
        if track_id in self.current_frame_track_ids:
            QMessageBox.warning(self, "Error", 
                            f"Track ID '{track_id}' already exists in current frame.\n"
                            f"Please use a different track ID for this frame.")
            return
            
        self.result_object_type = object_type
        self.result_track_id = track_id
        
        self.accept()
    
    def get_annotation_result(self):
        """Get the annotation result"""
        return self.result_object_type, self.result_track_id