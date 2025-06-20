"""
Bounding Box Annotation Dialog
"""

from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, 
                            QLabel, QComboBox, QLineEdit, 
                            QPushButton, QMessageBox)
from PySide6.QtCore import Qt

class BBoxAnnotationDialog(QDialog):
    """Dialog for annotating bounding box with object type and track ID"""
    
    def __init__(self, available_objects, existing_track_ids=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Annotate Bounding Box")
        self.setModal(True)
        self.setFixedSize(300, 150)
        
        self.available_objects = available_objects
        self.existing_track_ids = existing_track_ids or {}
        
        self.result_object_type = None
        self.result_track_id = None
        
        self.setup_ui()
        
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
        
        # Track ID input
        track_layout = QHBoxLayout()
        track_layout.addWidget(QLabel("Track ID:"))
        
        self.track_input = QLineEdit()
        self.track_input.setPlaceholderText("auto-generated")
        track_layout.addWidget(self.track_input)
        
        layout.addLayout(track_layout)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.ok_button = QPushButton("OK")
        self.ok_button.clicked.connect(self.accept_annotation)
        
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        
        button_layout.addWidget(self.ok_button)
        button_layout.addWidget(self.cancel_button)
        
        layout.addLayout(button_layout)
        
        # Initialize with first object
        if self.available_objects:
            self.on_object_changed(self.available_objects[0])
            
    def on_object_changed(self, object_type):
        """Handle object type change"""
        if not object_type:
            return
            
        # Generate suggested track ID
        suggested_id = self.generate_track_id(object_type)
        self.track_input.setText(suggested_id)
        
    def generate_track_id(self, object_type):
        """Generate next available track ID for object type"""
        if object_type not in self.existing_track_ids:
            self.existing_track_ids[object_type] = []
        
        existing_ids = self.existing_track_ids[object_type]
        
        # Find next available number
        counter = 1
        while f"{object_type}_{counter:03d}" in existing_ids:
            counter += 1
            
        return f"{object_type}_{counter:03d}"
    
    def accept_annotation(self):
        """Accept and validate annotation"""
        object_type = self.object_combo.currentText()
        track_id = self.track_input.text().strip()
        
        if not object_type:
            QMessageBox.warning(self, "Error", "Please select an object type")
            return
            
        if not track_id:
            QMessageBox.warning(self, "Error", "Please enter a track ID")
            return
            
        # Check for duplicate track ID across all object types
        all_existing_ids = []
        for ids in self.existing_track_ids.values():
            all_existing_ids.extend(ids)
            
        if track_id in all_existing_ids:
            QMessageBox.warning(self, "Error", f"Track ID '{track_id}' already exists")
            return
            
        self.result_object_type = object_type
        self.result_track_id = track_id
        
        self.accept()
    
    def get_annotation_result(self):
        """Get the annotation result"""
        return self.result_object_type, self.result_track_id