import os
import json

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QVBoxLayout,
    QWidget,
    QPushButton,
    QLabel,
    QGroupBox,
    QCheckBox,
    QMessageBox,
    QLineEdit,
    QScrollArea,
    QGridLayout,
)

from gui.config import HALF_PANEL_WIDTH, PANEL_SPACING


class ObjectPanel(QGroupBox):
    """Object selection panel placeholder"""

    def __init__(self):
        super().__init__("1. Object Categories")
        self.setFixedWidth(HALF_PANEL_WIDTH)
        self.setMaximumHeight(320)

        main_layout = QVBoxLayout(self)

        self.original_categories = self.load_object_categories()
        self.custom_categories = []
        self.checkboxes = {}

        # Init Callbacks
        self.selection_changed_callback = None

        # Manual object addition section
        add_section = QGroupBox("Add Custom Object")
        add_layout = QVBoxLayout(add_section)

        input_layout = QHBoxLayout()
        self.custom_object_input = QLineEdit()
        self.custom_object_input.setPlaceholderText("Enter new object")
        self.add_object_btn = QPushButton("Add")
        self.add_object_btn.clicked.connect(self.add_custom_object)
        self.custom_object_input.returnPressed.connect(
            self.add_custom_object
        )  # Enable adding by pressing Enter

        input_layout.addWidget(self.custom_object_input)
        input_layout.addWidget(self.add_object_btn)
        add_layout.addLayout(input_layout)

        # Scroll
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFixedHeight(180)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        # Widget to contain checkboxes
        self.checkbox_widget = QWidget()
        self.checkbox_layout = QGridLayout(self.checkbox_widget)
        self.checkbox_layout.setSpacing(2)

        scroll_area.setWidget(self.checkbox_widget)

        # Add to Main Layout
        main_layout.addWidget(add_section)
        main_layout.addWidget(QLabel("Available Objects:"))
        main_layout.addWidget(scroll_area)
        main_layout.addStretch()

        # Init checkboxes
        self.update_checkbox_list()


    def load_object_categories(self):
        """Load object categories from JSON file"""
        json_path = os.path.join("data", "object_categories.json")
        if os.path.exists(json_path):
            with open(json_path, "r") as f:
                return json.load(f)
        else:
            print(f"Warning: Object categories file not found at {json_path}")
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Critical)
            msg_box.setWindowTitle("File Not Found")
            msg_box.setText(
                f"The file 'object_categories.json' was not found at {json_path}"
            )
            msg_box.setDetailedText(f"Expected file at: {os.path.abspath(json_path)}")
            msg_box.exec()
            return []

    def get_all_categories(self):
        """Get combined list of json and custom categories"""
        return self.original_categories + self.custom_categories

    def update_checkbox_list(self):
        # Clear existing checkboxes
        for i in reversed(range(self.checkbox_layout.count())):
            child = self.checkbox_layout.itemAt(i)
            if child and child.widget():
                child.widget().setParent(None)

        self.checkboxes.clear()

        # Sort categories (original first, then custom)
        original_sorted = sorted(self.original_categories)
        custom_sorted = sorted(self.custom_categories)

        row = 0

        # Add original checkboxes in 2-column grid
        if original_sorted:
            for i, category in enumerate(original_sorted):
                checkbox = QCheckBox(category)

                # 2열 배치: col = i % 2, row = i // 2
                col = i % 2
                current_row = row + i // 2

                self.checkbox_layout.addWidget(checkbox, current_row, col)
                self.checkboxes[category] = checkbox

            # 다음 섹션을 위한 row 계산
            row = row + (len(original_sorted) + 1) // 2

        # Add separator and custom objects
        if original_sorted and custom_sorted:
            separator = QLabel("─────── Custom Objects ───────")
            separator.setStyleSheet("color: #999; font-size: 10px; margin: 5px 0;")
            self.checkbox_layout.addWidget(separator, row, 0, 1, 2)  # Span 2 columns
            row += 1

            # Add custom checkboxes with remove buttons
            for i, category in enumerate(custom_sorted):
                # Create container for checkbox + remove button
                container = QWidget()
                container_layout = QHBoxLayout(container)
                container_layout.setContentsMargins(0, 0, 0, 0)
                container_layout.setSpacing(5)

                checkbox = QCheckBox(category)

                remove_btn = QPushButton("×")
                remove_btn.setFixedSize(20, 20)
                remove_btn.setStyleSheet(
                    "color: red; font-weight: bold; font-size: 10px;"
                )
                remove_btn.clicked.connect(
                    lambda checked, cat=category: self.remove_custom_object(cat)
                )

                container_layout.addWidget(checkbox)
                container_layout.addWidget(remove_btn)
                container_layout.addStretch()

                # 2열 배치
                col = i % 2
                current_row = row + i // 2

                self.checkbox_layout.addWidget(container, current_row, col)
                self.checkboxes[category] = checkbox

        total_rows = 0
        if original_sorted:
            total_rows += (len(original_sorted) + 1) // 2
        if custom_sorted:
            total_rows += 1
            total_rows += (len(custom_sorted) + 1) // 2

        min_height = max(total_rows * 25, 50)
        self.checkbox_widget.setMinimumHeight(min_height)
        self.checkbox_widget.resize(260, min_height)
        self.checkbox_widget.updateGeometry()
        scroll_area = self.checkbox_widget.parent()
        if scroll_area:
            scroll_area.updateGeometry()

        if self.selection_changed_callback is not None:
            for checkbox in self.checkboxes.values():
                checkbox.stateChanged.connect(self.selection_changed_callback)

    def add_custom_object(self):
        """Add a custom object category"""
        object_name = self.custom_object_input.text().strip()

        if not object_name:
            return

        # Check if object already exists
        all_categories = self.get_all_categories()
        if object_name.lower() in [cat.lower() for cat in all_categories]:
            QMessageBox.warning(
                self, "Duplicate Object", f"Object '{object_name}' already exists!"
            )
            return

        # Add to custom categories
        self.custom_categories.append(object_name)
        self.custom_object_input.clear()

        # Update checkbox list
        self.update_checkbox_list()

        print(f"Added custom object: {object_name}")

    def remove_custom_object(self, category):
        """Remove a custom object category"""
        if category in self.custom_categories:
            self.custom_categories.remove(category)
            self.update_checkbox_list()
            print(f"Removed custom object: {category}")

    def get_selected_objects(self):
        """Get list of selected objects"""
        selected = []
        for category, checkbox in self.checkboxes.items():
            if checkbox.isChecked():
                selected.append(category)
        return selected

    def clear_selection(self):
        """ "Clear all selections"""
        for checkbox in self.checkboxes.values():
            checkbox.setChecked(False)

    def has_selection(self):
        """Check if any objects are selected"""
        return len(self.get_selected_objects()) > 0

    def connect_selection_changed(self, callback):
        """Connect selection changed callback"""
        self.selection_changed_callback = callback

        for checkbox in self.checkboxes.values():
            checkbox.stateChanged.connect(callback)
