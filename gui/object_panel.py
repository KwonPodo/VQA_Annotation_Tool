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
    QFrame,
)

from gui.config import PANEL_WIDTH


class ObjectPanel(QGroupBox):
    """Enhanced object selection panel with search and selected objects display"""

    def __init__(self):
        super().__init__("1. Object Categories")
        self.setFixedWidth(PANEL_WIDTH - 20)

        main_layout = QVBoxLayout(self)

        self.original_categories = self.load_object_categories()
        self.custom_categories = []
        self.checkboxes = {}
        self.filtered_categories = []

        # Init Callbacks
        self.selection_changed_callback = None

        # 상단: 검색 및 커스텀 객체 추가
        top_section = self.create_top_section()
        main_layout.addWidget(top_section, 0)

        # 중단: 선택된 객체 표시
        selected_section = self.create_selected_objects_section()
        main_layout.addWidget(selected_section, 0)

        # 하단: 객체 목록
        objects_section = self.create_objects_section()
        main_layout.addWidget(objects_section, 1)

        # 초기 체크박스 업데이트
        self.update_checkbox_list()

    def create_top_section(self):
        """상단: 검색 및 커스텀 객체 추가 섹션"""
        section = QFrame()
        layout = QHBoxLayout(section)
        
        # 검색 입력
        search_group = QGroupBox("Search Objects")
        search_layout = QVBoxLayout(search_group)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Type to search objects...")
        self.search_input.textChanged.connect(self.on_search_text_changed)
        
        clear_search_btn = QPushButton("Clear")
        clear_search_btn.setMaximumWidth(60)
        clear_search_btn.clicked.connect(self.clear_search)
        
        search_input_layout = QHBoxLayout()
        search_input_layout.addWidget(self.search_input)
        search_input_layout.addWidget(clear_search_btn)
        
        search_layout.addLayout(search_input_layout)
        
        # 커스텀 객체 추가
        custom_group = QGroupBox("Add Custom Object")
        custom_layout = QVBoxLayout(custom_group)
        
        self.custom_object_input = QLineEdit()
        self.custom_object_input.setPlaceholderText("Enter new object")
        self.add_object_btn = QPushButton("Add")
        self.add_object_btn.setMaximumWidth(60)
        self.add_object_btn.clicked.connect(self.add_custom_object)
        self.custom_object_input.returnPressed.connect(self.add_custom_object)
        
        custom_input_layout = QHBoxLayout()
        custom_input_layout.addWidget(self.custom_object_input)
        custom_input_layout.addWidget(self.add_object_btn)
        
        custom_layout.addLayout(custom_input_layout)
        
        layout.addWidget(search_group)
        layout.addWidget(custom_group)
        
        return section

    def create_selected_objects_section(self):
        """Display Selected Objects Section"""
        section = QGroupBox("Selected Objects")
        section.setMaximumHeight(80)
        layout = QVBoxLayout(section)
        
        self.selected_objects_label = QLabel("No objects selected")
        self.selected_objects_label.setStyleSheet(
            "color: #666; font-style: italic; padding: 5px; "
            "border: 1px solid #ddd; border-radius: 3px; "
            "background-color: #f9f9f9;"
        )
        self.selected_objects_label.setWordWrap(True)
        
        layout.addWidget(self.selected_objects_label)
        
        return section

    def create_objects_section(self):
        """Object Categories Section"""
        section = QGroupBox("Available Objects")
        layout = QVBoxLayout(section)
        
        # Scroll Area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        # Checkbox Container
        self.checkbox_widget = QWidget()
        self.checkbox_layout = QGridLayout(self.checkbox_widget)
        self.checkbox_layout.setSpacing(2)

        scroll_area.setWidget(self.checkbox_widget)
        layout.addWidget(scroll_area)
        
        return section

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

    def on_search_text_changed(self, text):
        """검색 텍스트 변경 시 호출"""
        self.update_checkbox_list()

    def clear_search(self):
        """검색 텍스트 지우기"""
        self.search_input.clear()
        self.update_checkbox_list()

    def filter_categories(self, categories, search_text):
        """카테고리 필터링"""
        if not search_text:
            return categories
        
        search_text = search_text.lower()
        return [cat for cat in categories if search_text in cat.lower()]

    def update_checkbox_list(self):
        """체크박스 목록 업데이트 (검색 필터링 적용)"""
        # 기존 체크박스 제거
        for i in reversed(range(self.checkbox_layout.count())):
            child = self.checkbox_layout.itemAt(i)
            if child and child.widget():
                child.widget().setParent(None)

        # 선택 상태 백업
        selected_states = {}
        for category, checkbox in self.checkboxes.items():
            selected_states[category] = checkbox.isChecked()

        self.checkboxes.clear()

        # 검색 필터링 적용
        search_text = self.search_input.text().strip()
        
        original_filtered = self.filter_categories(
            sorted(self.original_categories), search_text
        )
        custom_filtered = self.filter_categories(
            sorted(self.custom_categories), search_text
        )

        row = 0

        # 원본 카테고리 추가
        if original_filtered:
            for i, category in enumerate(original_filtered):
                checkbox = QCheckBox(category)
                
                # 이전 선택 상태 복원
                if category in selected_states:
                    checkbox.setChecked(selected_states[category])
                
                col = i % 3  # 3열로 변경 (더 많은 객체 표시)
                current_row = row + i // 3
                
                self.checkbox_layout.addWidget(checkbox, current_row, col)
                self.checkboxes[category] = checkbox

            row = row + (len(original_filtered) + 2) // 3

        # 구분선 및 커스텀 객체
        if original_filtered and custom_filtered:
            separator = QLabel("─────── Custom Objects ───────")
            separator.setStyleSheet("color: #999; font-size: 10px; margin: 5px 0;")
            self.checkbox_layout.addWidget(separator, row, 0, 1, 3)
            row += 1

            for i, category in enumerate(custom_filtered):
                container = QWidget()
                container_layout = QHBoxLayout(container)
                container_layout.setContentsMargins(0, 0, 0, 0)
                container_layout.setSpacing(5)

                checkbox = QCheckBox(category)
                
                # 이전 선택 상태 복원
                if category in selected_states:
                    checkbox.setChecked(selected_states[category])

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

                col = i % 3
                current_row = row + i // 3

                self.checkbox_layout.addWidget(container, current_row, col)
                self.checkboxes[category] = checkbox

        # 검색 결과 없음 표시
        if not original_filtered and not custom_filtered and search_text:
            no_results_label = QLabel("No objects found for your search")
            no_results_label.setStyleSheet("color: #666; font-style: italic;")
            self.checkbox_layout.addWidget(no_results_label, 0, 0, 1, 3)

        # 위젯 크기 조정
        total_rows = max(1, row + (len(custom_filtered) + 2) // 3 if custom_filtered else row)
        min_height = max(total_rows * 25, 50)
        self.checkbox_widget.setMinimumHeight(min_height)
        self.checkbox_widget.updateGeometry()

        # 콜백 연결
        if self.selection_changed_callback is not None:
            for checkbox in self.checkboxes.values():
                checkbox.stateChanged.connect(self.selection_changed_callback)
                checkbox.stateChanged.connect(self.update_selected_objects_display)

        # 선택된 객체 표시 업데이트
        self.update_selected_objects_display()

    def update_selected_objects_display(self):
        """선택된 객체 표시 업데이트"""
        selected = self.get_selected_objects()
        
        if not selected:
            self.selected_objects_label.setText("No objects selected")
            self.selected_objects_label.setStyleSheet(
                "color: #666; font-style: italic; padding: 5px; "
                "border: 1px solid #ddd; border-radius: 3px; "
                "background-color: #f9f9f9;"
            )
        else:
            count = len(selected)
            text = f"Selected ({count}): {', '.join(selected)}"
            self.selected_objects_label.setText(text)
            self.selected_objects_label.setStyleSheet(
                "color: #2196F3; font-weight: bold; padding: 5px; "
                "border: 2px solid #2196F3; border-radius: 3px; "
                "background-color: #E3F2FD;"
            )

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
        """Clear all selections"""
        for checkbox in self.checkboxes.values():
            checkbox.setChecked(False)
        self.update_selected_objects_display()

    def has_selection(self):
        """Check if any objects are selected"""
        return len(self.get_selected_objects()) > 0

    def connect_selection_changed(self, callback):
        """Connect selection changed callback"""
        self.selection_changed_callback = callback

        for checkbox in self.checkboxes.values():
            checkbox.stateChanged.connect(callback)
            checkbox.stateChanged.connect(self.update_selected_objects_display)