import math
import cv2
import numpy as np

from PySide6.QtCore import Qt, QRect
from PySide6.QtGui import QPixmap, QImage, QCursor, QPen, QColor, QBrush, QPainter
from PySide6.QtWidgets import (
    QLabel,
    QDialog
)

from gui.config import track_id_color_palette, PADDING_RATIO

class VideoCanvas(QLabel):
    """Video Display Canvas"""

    def __init__(self):
        super().__init__()
        self.setMinimumSize(500, 300)
        self.setStyleSheet("border: 2px solid #cccccc; background-color: #f5f5f5;")
        self.setAlignment(Qt.AlignCenter)
        self.setText("Load Video File\n(Video Canvas)")

        self.setMouseTracking(True)

        # Video properties
        self.video_cap = None
        self.current_frame = 0
        self.total_frames = 0
        self.fps = 0
        self.video_resolution = (0, 0)
        self.current_frame_data = None # np.ndarray RGB Pixel data

        # Bounding box annotation state
        self.bbox_mode = False
        self.available_objects = [] # objects selected from object panel
        self.is_drawing = False
        self.start_point = None
        self.end_point = None
        self.scale_factor = 1.0

        # 360 Bbox
        self.BOUNDARY_THRESHOLD = 50

        # Store bboxes with track_id
        self.frame_bboxes = {} # Dict[frame_index: List[bbox_list]]

        # Track ID management
        self.existing_track_ids = {} # Dict[object_type: List[track_id]]

        self.track_registry = {} # Dict[object_type: List[track_id]]
        self.color_palette = track_id_color_palette
        self.color_index = 0

        # Remember last selected object type
        self.last_selected_object_type = None


        # BBox Edit State
        self.edit_mode = False
        self.resize_handle = None
        self.last_mouse_pos = None
        self.selected_bbox = None
        self.selected_bbox_index = None
        self.move_start_padded = None
        self.resize_start_padded = None
        self.original_bbox = None

        self.setFocusPolicy(Qt.StrongFocus)

        # Zone Detection Threshold
        self.CORNER_THRESHOLD = 15
        self.EDGE_THRESHOLD = 10

        # 360 Video Mode
        self.is_360_mode = False
        self.padding_ratio = PADDING_RATIO

    def load_video(self, file_path):
        """Load video file"""
        if self.video_cap:
            self.video_cap.release()

        self.video_cap = cv2.VideoCapture(file_path)
        if self.video_cap.isOpened():
            self.total_frames = int(self.video_cap.get(cv2.CAP_PROP_FRAME_COUNT))
            self.fps = self.video_cap.get(cv2.CAP_PROP_FPS)
            self.current_frame = 0

            # Load first frame and get dimensions
            self.set_frame(0)

            # Set video resolution metadata after loading first frame
            if self.current_frame_data is not None:
                self.video_resolution = (self.original_width, self.original_height)

            return True
        return False

    def set_360_mode(self, is_360_mode):
        """360 Video Mode"""
        self.is_360_mode = is_360_mode
        print(f"VideoCanvas: 360 mode set to {is_360_mode}")

    def create_360_padded_image(self, original_image):
        """360도 모드를 위한 패딩된 이미지 생성"""
        if not self.is_360_mode:
            return original_image
        
        h, w, ch = original_image.shape
        padding_width = int(w * self.padding_ratio)
        
        # 새로운 이미지 크기 (좌우 25%씩 추가)
        padded_width = w + 2 * padding_width
        padded_image = np.zeros((h, padded_width, ch), dtype=original_image.dtype)
        
        # 중앙에 원본 이미지 배치
        padded_image[:, padding_width:padding_width + w, :] = original_image
        
        # 좌측 패딩: 원본 이미지의 오른쪽 끝 부분을 복사
        padded_image[:, :padding_width, :] = original_image[:, -padding_width:, :]
        
        # 우측 패딩: 원본 이미지의 왼쪽 끝 부분을 복사  
        padded_image[:, padding_width + w:, :] = original_image[:, :padding_width, :]
        
        return padded_image

    def set_frame(self, frame_index):
        """Set current frame index"""
        if not self.video_cap or frame_index < 0 or frame_index >= self.total_frames:
            return False

        self.video_cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
        ret, frame = self.video_cap.read()

        if ret:
            self.current_frame = frame_index

            # Convert BGR to RGB and store current frame data
            self.current_frame_data = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch  = self.current_frame_data.shape

            self.original_width = w
            self.original_height = h

            # Update display with current canvas size
            self.update_display()

            return True
        return False

    def update_display(self):
        """Update video display with current canvas size"""
        if self.current_frame_data is None:
            return
        
        if self.is_360_mode:
            display_image = self.create_360_padded_image(self.current_frame_data)
        else:
            display_image = self.current_frame_data

        h, w, ch = display_image.shape
        bytes_per_line = ch * w

        # Create QImage from current frame data
        qt_image = QImage(
            display_image.data, w, h, bytes_per_line, QImage.Format_RGB888
        )
        
        # Get current canvas size
        canvas_size = self.size()
        
        # Scale to fit current canvas while maintaining aspect ratio
        scaled_pixmap = QPixmap.fromImage(qt_image).scaled(
            canvas_size, Qt.KeepAspectRatio, Qt.SmoothTransformation
        )

        # Calculate current scale factor
        self.scale_factor = min(
            canvas_size.width() / w,
            canvas_size.height() / h
        )

        self.setPixmap(scaled_pixmap)

    def resizeEvent(self, event):
        """Handle resize events to update video display"""
        super().resizeEvent(event)
        
        # Update video display when canvas is resized
        if self.current_frame_data is not None:
            self.update_display()

    def enable_bbox_mode(self, available_objects):
        """Enable bbox annotation mode"""
        self.bbox_mode = True
        self.available_objects = available_objects
        self.setCursor(Qt.CrossCursor)
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
    
    def remove_last_bbox(self):
        """Remove the last bounding box from current frame"""
        if self.current_frame in self.frame_bboxes:
            bboxes = self.frame_bboxes[self.current_frame]
            if bboxes:
                removed = bboxes.pop()
                print(f"Removed bbox: {removed['object_type']} - {removed['track_id']}")
                self.update()  # Trigger repaint

                self.notify_progress_update()

                return True
        return False

    def notify_progress_update(self):
        """Update BBox Annotation Progress to Main Window"""
        # Find MainWindow through Parent Chain
        parent_widget = self.parent()
        while parent_widget:
            if hasattr(parent_widget, 'update_progress_display'):
                parent_widget.update_progress_display()
                break
            parent_widget = parent_widget.parent()

    def get_bbox_zone(self, canvas_point, bbox):
        """BBox 존 판별 - 패딩 좌표 사용"""
        # 패딩 좌표를 캔버스 좌표로 변환
        top_left = self.padded_to_canvas_coords((bbox['x'], bbox['y']))
        bottom_right = self.padded_to_canvas_coords((bbox['x'] + bbox['width'], bbox['y'] + bbox['height']))
        
        if not top_left or not bottom_right:
            return 'outside'
        
        x, y = canvas_point.x(), canvas_point.y()
        left, top = top_left
        right, bottom = bottom_right
        
        # 나머지는 기존과 동일...
        if x < left or x > right or y < top or y > bottom:
            return 'outside'
        
        # 꼭짓점 체크
        if (abs(x - left) <= self.CORNER_THRESHOLD and abs(y - top) <= self.CORNER_THRESHOLD):
            return 'corner_tl'
        elif (abs(x - right) <= self.CORNER_THRESHOLD and abs(y - top) <= self.CORNER_THRESHOLD):
            return 'corner_tr'
        elif (abs(x - left) <= self.CORNER_THRESHOLD and abs(y - bottom) <= self.CORNER_THRESHOLD):
            return 'corner_bl'
        elif (abs(x - right) <= self.CORNER_THRESHOLD and abs(y - bottom) <= self.CORNER_THRESHOLD):
            return 'corner_br'
        elif abs(y - top) <= self.EDGE_THRESHOLD:
            return 'edge_top'
        elif abs(y - bottom) <= self.EDGE_THRESHOLD:
            return 'edge_bottom'
        elif abs(x - left) <= self.EDGE_THRESHOLD:
            return 'edge_left'
        elif abs(x - right) <= self.EDGE_THRESHOLD:
            return 'edge_right'
        else:
            return 'inside'

    def get_target_bbox_at_position(self, canvas_point):
        """
        주어진 위치에서 가장 작은 BBox를 찾아 반환
        Returns: (bbox_dict, bbox_index) 또는 (None, None)
        """
        if self.current_frame not in self.frame_bboxes:
            return None, None
        
        candidates = []
        
        for i, bbox in enumerate(self.frame_bboxes[self.current_frame]):
            zone = self.get_bbox_zone(canvas_point, bbox)
            if zone != 'outside':
                # 면적 계산
                area = bbox['width'] * bbox['height']
                candidates.append((bbox, i, area, zone))
        
        if not candidates:
            return None, None
        
        # 면적이 가장 작은 것 선택
        candidates.sort(key=lambda x: x[2])  # area로 정렬
        selected_bbox, bbox_index, _, zone = candidates[0]
        
        return selected_bbox, bbox_index

    def get_cursor_for_zone(self, zone):
        """존에 따른 커서 모양 반환"""
        cursor_map = {
            'corner_tl': Qt.SizeFDiagCursor,    # ↖↘
            'corner_br': Qt.SizeFDiagCursor,    # ↖↘
            'corner_tr': Qt.SizeBDiagCursor,    # ↗↙
            'corner_bl': Qt.SizeBDiagCursor,    # ↗↙
            'edge_top': Qt.SizeVerCursor,       # ↕
            'edge_bottom': Qt.SizeVerCursor,    # ↕
            'edge_left': Qt.SizeHorCursor,      # ↔
            'edge_right': Qt.SizeHorCursor,     # ↔
            'inside': Qt.SizeAllCursor,         # ✋ (이동)
            'outside': Qt.CrossCursor           # + (그리기)
        }
        return cursor_map.get(zone, Qt.ArrowCursor)

    # Mouse events for bounding box drawing
    def mousePressEvent(self, event):
        """Handle mouse press for bbox drawing and editing"""
        if not self.bbox_mode:
            return
        
        canvas_point = event.position().toPoint()
        
        
        # 우클릭:  삭제
        if event.button() == Qt.RightButton:
            self.handle_right_click(canvas_point)
            return
        
        # 좌클릭 처리
        if event.button() != Qt.LeftButton:
            return
        
        # Ctrl+좌클릭: 무조건 새 박스 그리기
        if event.modifiers() & Qt.ControlModifier:
            self.clear_selection()
            self.start_new_bbox_drawing(canvas_point)
            return
        
        # 기존 BBox 위에서 클릭한 경우
        target_bbox, bbox_index = self.get_target_bbox_at_position(canvas_point)
        
        if target_bbox:
            zone = self.get_bbox_zone(canvas_point, target_bbox)
            self.set_selected_bbox(target_bbox, bbox_index)
            
            if zone in ['corner_tl', 'corner_tr', 'corner_bl', 'corner_br']:
                # 리사이즈 모드 시작
                self.start_resize_mode(target_bbox, bbox_index, zone, canvas_point)
            elif zone in ['edge_top', 'edge_bottom', 'edge_left', 'edge_right']:
                # 리사이즈 모드 시작  
                self.start_resize_mode(target_bbox, bbox_index, zone, canvas_point)
            elif zone == 'inside':
                # 이동 모드 시작
                self.start_move_mode(target_bbox, bbox_index, canvas_point)
        else:
            # 빈 공간: 새 박스 그리기
            self.clear_selection()
            self.start_new_bbox_drawing(canvas_point)

    def start_new_bbox_drawing(self, canvas_point):
        """새 BBox 그리기 시작"""
        self.is_drawing = True
        self.edit_mode = False
        self.selected_bbox = None
        self.start_point = canvas_point
        self.end_point = canvas_point

    def start_move_mode(self, bbox, bbox_index, canvas_point):
        """BBox 이동 모드 시작"""
        self.edit_mode = True
        self.is_drawing = False
        self.selected_bbox = bbox
        self.selected_bbox_index = bbox_index
        self.resize_handle = 'move'
        self.last_mouse_pos = canvas_point
        
        # 패딩 좌표로 저장
        self.move_start_padded = self.canvas_to_padded_coords(canvas_point)
        self.original_bbox = bbox.copy()

    def start_resize_mode(self, bbox, bbox_index, zone, canvas_point):
        """BBox 리사이즈 모드 시작"""
        self.edit_mode = True
        self.is_drawing = False
        self.selected_bbox = bbox
        self.selected_bbox_index = bbox_index
        self.resize_handle = zone
        self.last_mouse_pos = canvas_point
        
        # 리사이즈 시작점을 이미지 좌표로 저장
        self.resize_start_padded = self.canvas_to_padded_coords(canvas_point)
        self.original_bbox = bbox.copy()  # 원본 좌표 백업

    def handle_right_click(self, canvas_point):
        """우클릭 처리 - BBox 삭제"""
        target_bbox, bbox_index = self.get_target_bbox_at_position(canvas_point)
        
        if target_bbox:
            # 선택된 BBox 삭제
            self.delete_bbox_at_index(bbox_index)
            print(f"Deleted bbox: {target_bbox['object_type']} - {target_bbox['track_id']} (Right-click)")
        else:
            print("No bbox to delete at this position")

    def set_selected_bbox(self, bbox, bbox_index):
        """BBox 선택 상태 설정"""
        self.selected_bbox = bbox
        self.selected_bbox_index = bbox_index
        self.update()  # 시각적 피드백을 위해 다시 그리기
        print(f"Selected bbox: {bbox['object_type']} - {bbox['track_id']}")

    def clear_selection(self):
        """선택 상태 해제"""
        if self.selected_bbox:  # 선택된게 있었다면 화면 업데이트
            print(f"Deselected bbox: {self.selected_bbox['object_type']} - {self.selected_bbox['track_id']}")
            self.selected_bbox = None
            self.selected_bbox_index = None
            self.update()

    def delete_bbox_at_index(self, bbox_index):
        """지정된 인덱스의 BBox 삭제"""
        if self.current_frame not in self.frame_bboxes:
            return False
        
        bboxes = self.frame_bboxes[self.current_frame]
        if 0 <= bbox_index < len(bboxes):
            deleted_bbox = bboxes.pop(bbox_index)
            
            # 선택된 BBox가 삭제된 경우 선택 해제
            if self.selected_bbox_index == bbox_index:
                self.clear_selection()
            elif self.selected_bbox_index is not None and self.selected_bbox_index > bbox_index:
                # 삭제된 BBox보다 뒤에 있던 선택된 BBox의 인덱스 조정
                self.selected_bbox_index -= 1
            
            self.update()
            self.notify_progress_update()
            return True
        
        return False

    def delete_selected_bbox(self):
        """현재 선택된 BBox 삭제"""
        if self.selected_bbox_index is not None:
            deleted_bbox = self.frame_bboxes[self.current_frame][self.selected_bbox_index]
            success = self.delete_bbox_at_index(self.selected_bbox_index)
            if success:
                print(f"Deleted selected bbox: {deleted_bbox['object_type']} - {deleted_bbox['track_id']}")
            return success
        return False

    def keyPressEvent(self, event):
        """키보드 이벤트 처리"""
        if not self.bbox_mode:
            return
        
        # Delete/Backspace: 선택된 BBox 삭제
        if event.key() in (Qt.Key_Delete, Qt.Key_Backspace):
            if self.delete_selected_bbox():
                event.accept()
                return
            else:
                print("No bbox selected for deletion")
        
        # 부모 클래스의 keyPressEvent 호출
        super().keyPressEvent(event)

    def mouseMoveEvent(self, event):
        """Handle mouse move for bbox preview, cursor changes, and editing"""
        if not self.bbox_mode:
            return
        
        canvas_point = event.position().toPoint()
        
        # 새 박스 그리기 중
        if self.is_drawing:
            self.end_point = canvas_point
            self.update()
            return
        
        # BBox 편집 중
        if self.edit_mode and self.selected_bbox:
            if self.resize_handle == 'move':
                self.handle_bbox_move(canvas_point)
            elif self.resize_handle.startswith('corner_') or self.resize_handle.startswith('edge_'):
                self.handle_bbox_resize(canvas_point)
            self.update()
            return
        
        # 커서 변경 로직 (편집 중이 아닐 때만)
        target_bbox, _ = self.get_target_bbox_at_position(canvas_point)
        
        if target_bbox:
            zone = self.get_bbox_zone(canvas_point, target_bbox)
            cursor = self.get_cursor_for_zone(zone)
            self.setCursor(cursor)
        else:
            self.setCursor(Qt.CrossCursor)

    def handle_bbox_move(self, canvas_point):
        """BBox 이동 처리"""
        if not self.move_start_padded or not self.selected_bbox:
            return
        
        current_padded = self.canvas_to_padded_coords(canvas_point)
        if not current_padded:
            return
        
        # 이동 거리 계산
        dx = current_padded[0] - self.move_start_padded[0]
        dy = current_padded[1] - self.move_start_padded[1]
        
        # 새 위치
        new_x = self.original_bbox['x'] + dx
        new_y = self.original_bbox['y'] + dy
        
        # 경계 체크
        if self.is_360_mode:
            padding_width = int(self.original_width * self.padding_ratio)
            total_width = self.original_width + 2 * padding_width
            new_x = max(0, min(new_x, total_width - self.selected_bbox['width']))
        else:
            new_x = max(0, min(new_x, self.original_width - self.selected_bbox['width']))
        
        new_y = max(0, min(new_y, self.original_height - self.selected_bbox['height']))
        
        # 업데이트
        self.selected_bbox['x'] = new_x
        self.selected_bbox['y'] = new_y

    def handle_bbox_resize(self, canvas_point):
        """BBox 리사이즈 처리 - 패딩 좌표 사용"""
        if not self.resize_start_padded or not self.selected_bbox:
            return
        
        # 현재 마우스 위치를 패딩 좌표로 변환
        current_padded = self.canvas_to_padded_coords(canvas_point)
        if not current_padded:
            return
        
        # 원본 BBox 좌표 (리사이즈 시작 시점)
        orig_x = self.original_bbox['x']
        orig_y = self.original_bbox['y']
        orig_width = self.original_bbox['width']
        orig_height = self.original_bbox['height']
        
        # 현재 좌표
        current_x, current_y = current_padded
        
        # 패딩 모드에서 최대 범위 계산
        if self.is_360_mode:
            padding_width = int(self.original_width * self.padding_ratio)
            max_width = self.original_width + 2 * padding_width
        else:
            max_width = self.original_width
        max_height = self.original_height
        
        # 리사이즈 핸들에 따른 처리
        if self.resize_handle == 'corner_tl':
            # Top-Left 코너: x, y, width, height 모두 변경
            new_x = min(current_x, orig_x + orig_width - 10)
            new_y = min(current_y, orig_y + orig_height - 10)
            new_width = (orig_x + orig_width) - new_x
            new_height = (orig_y + orig_height) - new_y
            
            self.selected_bbox['x'] = max(0, new_x)
            self.selected_bbox['y'] = max(0, new_y)
            self.selected_bbox['width'] = max(10, new_width)
            self.selected_bbox['height'] = max(10, new_height)
            
        elif self.resize_handle == 'corner_tr':
            # Top-Right 코너
            new_width = current_x - orig_x
            new_y = min(current_y, orig_y + orig_height - 10)
            new_height = (orig_y + orig_height) - new_y
            
            self.selected_bbox['y'] = max(0, new_y)
            self.selected_bbox['width'] = max(10, min(new_width, max_width - orig_x))
            self.selected_bbox['height'] = max(10, new_height)
            
        elif self.resize_handle == 'corner_bl':
            # Bottom-Left 코너
            new_x = min(current_x, orig_x + orig_width - 10)
            new_width = (orig_x + orig_width) - new_x
            new_height = current_y - orig_y
            
            self.selected_bbox['x'] = max(0, new_x)
            self.selected_bbox['width'] = max(10, new_width)
            self.selected_bbox['height'] = max(10, min(new_height, max_height - orig_y))
            
        elif self.resize_handle == 'corner_br':
            # Bottom-Right 코너
            new_width = current_x - orig_x
            new_height = current_y - orig_y
            
            self.selected_bbox['width'] = max(10, min(new_width, max_width - orig_x))
            self.selected_bbox['height'] = max(10, min(new_height, max_height - orig_y))
            
        elif self.resize_handle == 'edge_top':
            # 위쪽 모서리
            new_y = min(current_y, orig_y + orig_height - 10)
            new_height = (orig_y + orig_height) - new_y
            
            self.selected_bbox['y'] = max(0, new_y)
            self.selected_bbox['height'] = max(10, new_height)
            
        elif self.resize_handle == 'edge_bottom':
            # 아래쪽 모서리
            current_y_box = self.selected_bbox['y']
            new_height = current_y - current_y_box
            max_height_from_current = max_height - current_y_box
            self.selected_bbox['height'] = max(10, min(new_height, max_height_from_current))
            
        elif self.resize_handle == 'edge_left':
            # 왼쪽 모서리
            new_x = min(current_x, orig_x + orig_width - 10)
            new_width = (orig_x + orig_width) - new_x
            
            self.selected_bbox['x'] = max(0, new_x)
            self.selected_bbox['width'] = max(10, new_width)
            
        elif self.resize_handle == 'edge_right':
            # 오른쪽 모서리
            current_x_box = self.selected_bbox['x']
            new_width = current_x - current_x_box
            max_width_from_current = max_width - current_x_box
            self.selected_bbox['width'] = max(10, min(new_width, max_width_from_current))

        # 최종 경계 체크
        if self.selected_bbox['x'] + self.selected_bbox['width'] > max_width:
            self.selected_bbox['width'] = max_width - self.selected_bbox['x']
        
        if self.selected_bbox['y'] + self.selected_bbox['height'] > max_height:
            self.selected_bbox['height'] = max_height - self.selected_bbox['y']

    def mouseReleaseEvent(self, event):
        """Handle mouse release for bbox completion and editing end"""
        if not self.bbox_mode or event.button() != Qt.LeftButton:
            return
        
        # 새 박스 그리기 완료
        if self.is_drawing:
            self.complete_new_bbox_drawing()
            return
        
        # 편집 모드 종료
        if self.edit_mode:
            self.complete_bbox_editing()
            return

    def complete_new_bbox_drawing(self):
        """새 BBox 그리기 완료 - 단순화된 버전"""
        self.is_drawing = False
        
        # 새로운 좌표 변환 함수 사용
        start_padded = self.canvas_to_padded_coords(self.start_point)
        end_padded = self.canvas_to_padded_coords(self.end_point)
        
        if start_padded and end_padded:
            print(f"Drawing BBox: {start_padded} -> {end_padded}")
            
            # 간단한 BBox 생성
            start_x, start_y = start_padded
            end_x, end_y = end_padded
            
            x = min(start_x, end_x)
            y = min(start_y, end_y)
            width = abs(end_x - start_x)
            height = abs(end_y - start_y)
            
            # 최소 크기 체크
            if width > 10 and height > 10:
                self.show_simple_annotation_dialog(x, y, width, height)
            else:
                print(f"BBox too small: w={width}, h={height}")

    def complete_bbox_editing(self):
        """BBox 편집 완료"""
        self.edit_mode = False
        self.resize_handle = None
        self.last_mouse_pos = None
        self.move_start_padded = None
        self.resize_start_padded = None
        self.original_bbox = None
        
        # Progress 업데이트
        self.notify_progress_update()
        print(f"BBox editing completed")

    def paintEvent(self, event):
        """Paint event to draw bboxes and preview"""
        super().paintEvent(event)
        
        if not self.pixmap() or not self.bbox_mode:
            return
        
        painter = QPainter(self)

        if not painter.isActive():
            return

        try:
            if self.is_360_mode:
                self.draw_360_boundary_indicators(painter)
                
            # Draw existing bboxes
            self.draw_existing_bboxes(painter)
        
            # Draw preview bbox while drawing
            if self.is_drawing and self.start_point and self.end_point:
                self.draw_preview_bbox(painter)
        finally:
            if painter.isActive():
                painter.end()
    
    def draw_360_boundary_indicators(self, painter):
        """Show Left-Right Boundary"""
        if not self.pixmap():
            return
        
        pixmap_rect = self.pixmap().rect()
        canvas_rect = self.rect()
        
        # 이미지가 캔버스에서 차지하는 실제 영역 계산
        x_offset = (canvas_rect.width() - pixmap_rect.width()) // 2
        y_offset = (canvas_rect.height() - pixmap_rect.height()) // 2
        
        # 실제 이미지 영역
        image_left = x_offset
        image_right = x_offset + pixmap_rect.width()
        image_top = y_offset
        image_bottom = y_offset + pixmap_rect.height()

        if self.is_360_mode:
            total_padded_width = self.original_width * (1 + 2 * self.padding_ratio)
            padded_pixel_width = self.original_width * self.padding_ratio

            display_padding_width = int(pixmap_rect.width() * padded_pixel_width / total_padded_width)

            original_left = image_left + display_padding_width
            original_right = image_right - display_padding_width
        
            # 흰색 세로선으로 좌우 경계 표시
            painter.setPen(QPen(QColor(255, 0, 0, 255), 2)) # RGB, Pen Width
            
            # 왼쪽 경계선 (이미지 시작점)
            painter.drawLine(original_left, image_top, original_left, image_bottom)
            
            # 오른쪽 경계선 (이미지 끝점)
            painter.drawLine(original_right, image_top, original_right, image_bottom)

    def draw_resize_handles(self, painter, top_left, bottom_right, color):
        """선택된 BBox의 리사이즈 핸들 그리기"""
        
        if not painter.isActive():
            return

        left, top = top_left
        right, bottom = bottom_right
        
        # 핸들 크기
        handle_size = 8
        half_size = handle_size // 2
        
        # 핸들 색상 설정 (배경: 흰색, 테두리: BBox 색상)
        handle_brush = QBrush(QColor(255, 255, 255))  # 흰색 배경
        handle_pen = QPen(color, 2)  # BBox 색상 테두리
        
        painter.setPen(handle_pen)
        painter.setBrush(handle_brush)
        
        # 8개 핸들 위치 계산 및 그리기
        handle_positions = [
            # 4개 꼭짓점
            (left, top),           # Top-Left
            (right, top),          # Top-Right
            (left, bottom),        # Bottom-Left
            (right, bottom),       # Bottom-Right
            
            # 4개 모서리 중점
            ((left + right) // 2, top),     # Top-Center
            ((left + right) // 2, bottom),  # Bottom-Center
            (left, (top + bottom) // 2),    # Left-Center
            (right, (top + bottom) // 2),   # Right-Center
        ]
        
        for handle_x, handle_y in handle_positions:
            # 핸들을 중심점 기준으로 그리기
            handle_rect = QRect(
                handle_x - half_size, 
                handle_y - half_size, 
                handle_size, 
                handle_size
            )
            painter.drawRect(handle_rect)
            painter.setBrush(QBrush(Qt.NoBrush))

    def draw_preview_bbox(self, painter):
        """Draw preview bbox while drawing"""
        
        pen = QPen(QColor(255, 0, 0), 2, Qt.DashLine)  # Red dashed line
        painter.setPen(pen)
        
        x = min(self.start_point.x(), self.end_point.x())
        y = min(self.start_point.y(), self.end_point.y())
        width = abs(self.end_point.x() - self.start_point.x())
        height = abs(self.end_point.y() - self.start_point.y())
        
        rect = QRect(x, y, width, height)
        painter.drawRect(rect)

    def draw_existing_bboxes(self, painter):
        """기존 BBox들 그리기 - 디버그 버전"""
        if self.current_frame not in self.frame_bboxes:
            return
        
        if not painter.isActive():
            return
        
        print(f"Drawing bboxes for frame {self.current_frame}: {len(self.frame_bboxes[self.current_frame])} boxes")
        
        for i, bbox in enumerate(self.frame_bboxes[self.current_frame]):
            # 색상 설정
            if bbox['track_id'] in self.track_registry:
                color = QColor(*self.track_registry[bbox['track_id']])
            else:
                color = QColor(255, 0, 0)

            is_selected = (self.selected_bbox_index == i)
            
            print(f"Drawing original box {i}: {bbox['track_id']} at ({bbox['x']}, {bbox['y']})")
            
            # 원본 박스 그리기
            self.draw_single_bbox_simple(painter, bbox, color, is_selected, is_original=True)
            
            # 360도 모드에서만 미러 박스 그리기
            if self.is_360_mode:
                mirrors = self.get_simple_mirrors(bbox)
                print(f"Found {len(mirrors)} mirrors for box {i}")
                for j, mirror in enumerate(mirrors):
                    print(f"Drawing mirror {j}: at ({mirror['x']}, {mirror['y']})")
                    self.draw_single_bbox_simple(painter, mirror, color, False, is_original=False)

    def canvas_to_padded_coords(self, canvas_point):
        """캔버스 좌표 → 패딩 포함 좌표 (새로운 함수)"""
        if not self.pixmap():
            return None
        
        pixmap = self.pixmap()
        canvas_rect = self.rect()
        pixmap_rect = pixmap.rect()
        
        # 캔버스에서 픽맵으로 변환
        x_offset = (canvas_rect.width() - pixmap_rect.width()) // 2
        y_offset = (canvas_rect.height() - pixmap_rect.height()) // 2
        
        pixmap_x = canvas_point.x() - x_offset
        pixmap_y = canvas_point.y() - y_offset
        
        # 범위 체크
        if pixmap_x < 0 or pixmap_x >= pixmap_rect.width() or pixmap_y < 0 or pixmap_y >= pixmap_rect.height():
            return None
        
        if self.is_360_mode:
            # 360도: 패딩 포함 좌표
            padding_width = int(self.original_width * self.padding_ratio)
            total_width = self.original_width + 2 * padding_width
            
            padded_x = pixmap_x * total_width / pixmap_rect.width()
            padded_y = pixmap_y * self.original_height / pixmap_rect.height()
            
            return (int(round(padded_x)), int(round(padded_y)))
        else:
            # 일반 모드
            img_x = pixmap_x * self.original_width / pixmap_rect.width()
            img_y = pixmap_y * self.original_height / pixmap_rect.height()
            
            return (int(round(img_x)), int(round(img_y)))

    def padded_to_canvas_coords(self, padded_point):
        """패딩 포함 좌표 → 캔버스 좌표 (새로운 함수)"""
        if not self.pixmap():
            return None
        
        padded_x, padded_y = padded_point
        pixmap = self.pixmap()
        canvas_rect = self.rect()
        pixmap_rect = pixmap.rect()
        
        if self.is_360_mode:
            padding_width = int(self.original_width * self.padding_ratio)
            total_width = self.original_width + 2 * padding_width
            
            pixmap_x = padded_x * pixmap_rect.width() / total_width
            pixmap_y = padded_y * pixmap_rect.height() / self.original_height
        else:
            pixmap_x = padded_x * pixmap_rect.width() / self.original_width
            pixmap_y = padded_y * pixmap_rect.height() / self.original_height
        
        # 캔버스 좌표로 변환
        x_offset = (canvas_rect.width() - pixmap_rect.width()) // 2
        y_offset = (canvas_rect.height() - pixmap_rect.height()) // 2
        
        canvas_x = int(round(pixmap_x + x_offset))
        canvas_y = int(round(pixmap_y + y_offset))
        
        return (canvas_x, canvas_y)

    def show_simple_annotation_dialog(self, x, y, width, height):
        """간단한 어노테이션 다이얼로그 (새로운 함수)"""
        from gui.bbox_dialog import BBoxAnnotationDialog
        
        # 현재 프레임 트랙 ID 수집
        current_frame_track_ids = []
        if self.current_frame in self.frame_bboxes:
            current_frame_track_ids = [bbox['track_id'] for bbox in self.frame_bboxes[self.current_frame]]
        
        dialog = BBoxAnnotationDialog(
            available_objects=self.available_objects,
            existing_track_ids=self.existing_track_ids.copy(),
            current_frame_track_ids=current_frame_track_ids,
            last_selected_object=self.last_selected_object_type,
            parent=self
        )
        
        if dialog.exec() == QDialog.Accepted:
            object_type, track_id = dialog.get_annotation_result()
            if object_type and track_id:
                self.last_selected_object_type = object_type
                self.add_simple_bbox(x, y, width, height, object_type, track_id)
                return True
        return False

    def add_simple_bbox(self, x, y, width, height, object_type, track_id):
        """간단한 BBox 추가 (새로운 함수)"""
        print(f"Adding simple bbox: {object_type}-{track_id} at ({x}, {y}) size {width}x{height}")
        
        # 색상 할당
        if track_id not in self.track_registry:
            self.track_registry[track_id] = self.get_next_color()
        
        # BBox 데이터 생성 (패딩 좌표로 저장)
        bbox = {
            'x': x,
            'y': y,
            'width': width,
            'height': height,
            'object_type': object_type,
            'track_id': track_id,
        }
        
        # 프레임에 추가
        if self.current_frame not in self.frame_bboxes:
            self.frame_bboxes[self.current_frame] = []
        
        self.frame_bboxes[self.current_frame].append(bbox)
        
        # 트랙 ID 레지스트리 업데이트
        if object_type not in self.existing_track_ids:
            self.existing_track_ids[object_type] = []
        
        if track_id not in self.existing_track_ids[object_type]:
            self.existing_track_ids[object_type].append(track_id)
        
        print(f'Successfully added bbox: {object_type}-{track_id}')
        self.update()
        self.notify_progress_update()
        
        return True

    def get_simple_mirrors(self, bbox):
        """360도 미러링"""
        if not self.is_360_mode:
            return []
        
        mirrors = []
        padding_width = int(self.original_width * self.padding_ratio)
        
        x = bbox['x']
        y = bbox['y']
        width = bbox['width']
        height = bbox['height']
        
        # Define Area
        main_start = padding_width
        main_end = padding_width + self.original_width
        
        if x < padding_width:
            offset = x
            mirror_x = main_end - padding_width + offset
            mirrors.append({
                'x': mirror_x, 'y': y, 'width': width, 'height': height,
                'object_type': bbox.get('object_type', ''),
                'track_id': bbox.get('track_id', '')
            })
        elif x >= main_end:
            offset = x - main_end
            mirror_x = main_start + offset
            mirrors.append({
                'x': mirror_x, 'y': y, 'width': width, 'height': height,
                'object_type': bbox.get('object_type', ''),
                'track_id': bbox.get('track_id', '')
            })
        elif x >= main_start and x < main_end:
            if x - main_start < padding_width:
                mirror_x = main_end + (x - main_start)
                mirrors.append({
                    'x': mirror_x, 'y': y, 'width': width, 'height': height,
                    'object_type': bbox.get('object_type', ''),
                    'track_id': bbox.get('track_id', '')
                })
            if main_end - (x + width) < padding_width:
                mirror_x = padding_width - (main_end - x)
                mirrors.append({
                    'x': mirror_x, 'y': y, 'width': width, 'height': height,
                    'object_type': bbox.get('object_type', ''),
                    'track_id': bbox.get('track_id', '')
                })
        if x < main_start and (x + width) > main_start:
            main_part_width = (x + width) - main_start
            mirrors.append({
                'x': mirror_x, 'y': y, 'width': main_part_width, 'height': height,
                'object_type': bbox.get('object_type', ''),
                'track_id': bbox.get('track_id', '')
            })
        elif x < main_end and (x + width) > main_end:
            main_part_width = main_end - x
            mirrors.append({
                'x': 0, 'y': y, 'width': main_part_width, 'height': height,
                'object_type': bbox.get('object_type', ''),
                'track_id': bbox.get('track_id', '')
            })
        
        return mirrors

    def draw_single_bbox_simple(self, painter, bbox, color, is_selected=False, is_original=True):
        """디버그가 포함된 단일 BBox 그리기"""
        
        bbox_x, bbox_y = bbox['x'], bbox['y']
        bbox_w, bbox_h = bbox['width'], bbox['height']
        
        print(f"Drawing {'original' if is_original else 'mirror'} box at padded coords: ({bbox_x}, {bbox_y}) size {bbox_w}x{bbox_h}")
        
        # 패딩 좌표를 캔버스 좌표로 변환
        top_left = self.padded_to_canvas_coords((bbox_x, bbox_y))
        bottom_right = self.padded_to_canvas_coords((bbox_x + bbox_w, bbox_y + bbox_h))
        
        if not top_left or not bottom_right:
            print(f"❌ Coordinate conversion failed for {'original' if is_original else 'mirror'}")
            return
        
        canvas_x1, canvas_y1 = top_left
        canvas_x2, canvas_y2 = bottom_right
        canvas_w = canvas_x2 - canvas_x1
        canvas_h = canvas_y2 - canvas_y1
        
        print(f"  → Canvas coords: ({canvas_x1}, {canvas_y1}) to ({canvas_x2}, {canvas_y2}) = {canvas_w}x{canvas_h}")
        
        # 화면 범위 체크
        canvas_rect = self.rect()
        visible = (canvas_x2 > 0 and canvas_x1 < canvas_rect.width() and 
                canvas_y2 > 0 and canvas_y1 < canvas_rect.height())
        
        print(f"  → Visible: {visible} (canvas size: {canvas_rect.width()}x{canvas_rect.height()})")
        
        if not visible:
            print(f"  → Box is outside visible area!")
            return
        
        # 스타일 설정
        if is_selected and is_original:
            pen = QPen(color.lighter(150), 4)
        elif is_original:
            pen = QPen(color, 2)
        else:
            # 미러는 점선 + 더 눈에 띄는 색상
            pen = QPen(QColor(255, 255, 0), 2, Qt.DashLine)  # 노란색 점선으로 변경

        painter.setPen(pen)
        painter.setBrush(QBrush(Qt.NoBrush))
        
        # 사각형 그리기
        rect = QRect(canvas_x1, canvas_y1, canvas_w, canvas_h)
        painter.drawRect(rect)
        
        # 라벨
        if is_original:
            painter.setPen(QPen(color, 1))
            label = f"{bbox.get('track_id', 'unknown')}"
        else:
            painter.setPen(QPen(QColor(255, 255, 0), 1))
            label = f"[MIRROR]{bbox.get('track_id', 'unknown')}"
        
        painter.drawText(canvas_x1, canvas_y1 - 5, label)
        
        # 리사이즈 핸들 (선택된 원본만)
        if is_selected and is_original:
            self.draw_resize_handles(painter, top_left, bottom_right, color.lighter(150))
        
        print(f"  → Successfully drew {'original' if is_original else 'MIRROR'} box")

    def convert_padded_to_original_coords(self, bbox):
        """저장용: 패딩 좌표를 원본 영상 좌표로 변환"""
        if not self.is_360_mode:
            # 일반 모드: 변환 불필요 (이미 원본 좌표)
            return {
                'x': bbox['x'],
                'y': bbox['y'],
                'width': bbox['width'],
                'height': bbox['height'],
                'object_type': bbox['object_type'],
                'track_id': bbox['track_id'],
                'coordinate_system': 'original'
            }
        
        # 360도 모드: 패딩 좌표 → 원본 좌표 변환
        padding_width = int(self.original_width * self.padding_ratio)  # 960
        
        padded_x = bbox['x']
        padded_y = bbox['y']
        padded_width = bbox['width']
        padded_height = bbox['height']
        
        print(f"Converting padded ({padded_x}, {padded_y}) w={padded_width} h={padded_height}")
        print(f"Padding areas: Left[0~{padding_width}] Main[{padding_width}~{padding_width + self.original_width}] Right[{padding_width + self.original_width}~{padding_width + self.original_width + padding_width}]")
        
        # 1. 왼쪽 패딩 영역 (0 ~ 960) → 원본 오른쪽 끝으로 매핑
        if padded_x < padding_width:
            # 왼쪽 패딩에서의 위치를 원본 오른쪽 끝 위치로 변환
            # 예: padded_x=775 → original_x = 3840-960+775 = 3655
            offset_in_padding = padded_x  # 패딩 시작점(0)에서의 거리
            original_x = self.original_width - padding_width + offset_in_padding
            
            # 폭이 패딩 경계를 넘어가는 경우 (경계 걸치는 박스)
            if padded_x + padded_width > padding_width:
                # 경계를 걸치는 박스: 오른쪽 끝에서 시작해서 왼쪽 시작점까지
                overflow_into_main = (padded_x + padded_width) - padding_width
                original_width = (padding_width - padded_x) + overflow_into_main
                is_boundary_box = True
                print(f"  → Boundary box: starts at right end ({original_x}), crosses to left")
            else:
                # 패딩 영역 내에만 있는 박스
                original_width = padded_width
                is_boundary_box = False
                print(f"  → Left padding → Right end: {padded_x} → {original_x}")
        
        # 2. 메인 영역 (960 ~ 4800) → 원본 좌표 (0 ~ 3840)
        elif padded_x >= padding_width and padded_x < (padding_width + self.original_width):
            # 메인 영역: 단순히 패딩 오프셋 제거
            original_x = padded_x - padding_width
            
            # 폭이 메인 영역을 벗어나지 않도록 제한
            max_width = self.original_width - original_x
            original_width = min(padded_width, max_width)
            is_boundary_box = False
            
            print(f"  → Main area: {padded_x} → {original_x}")
        
        # 3. 오른쪽 패딩 영역 (4800 ~ 5760) → 원본 왼쪽 시작으로 매핑
        else:
            # 오른쪽 패딩에서의 상대 위치를 원본 왼쪽 시작으로 변환
            offset_in_right_padding = padded_x - (padding_width + self.original_width)
            original_x = offset_in_right_padding
            original_width = padded_width
            is_boundary_box = True
            
            print(f"  → Right padding → Left start: {padded_x} → {original_x}")
        
        # 경계 체크 및 보정
        original_x = max(0, min(original_x, self.original_width - 1))
        original_y = max(0, min(padded_y, self.original_height - 1))
        original_width = max(1, min(original_width, self.original_width - original_x))
        original_height = max(1, min(padded_height, self.original_height - original_y))
        
        result = {
            'x': original_x,
            'y': original_y,
            'width': original_width,
            'height': original_height,
            'object_type': bbox['object_type'],
            'track_id': bbox['track_id'],
            'coordinate_system': 'original',
            'is_boundary_box': is_boundary_box
        }
        
        print(f"  → Final original coords: ({original_x}, {original_y}) w={original_width} h={original_height}")
        return result

    def calculate_bfov_from_original_coords(self, original_bbox):
        """원본 좌표에서 BFoV 계산 (논문 방식)"""
        if not self.is_360_mode:
            # 일반 모드에서는 BFoV 불필요
            return None
        
        x = original_bbox['x']
        y = original_bbox['y'] 
        width = original_bbox['width']
        height = original_bbox['height']
        
        print(f"Calculating BFoV for original coords: ({x}, {y}) w={width} h={height}")
        
        # 중심점 계산
        center_x = x + width / 2
        center_y = y + height / 2
        
        print(f"  → Center point: ({center_x}, {center_y})")
        
        # 정규화 좌표 (0~1 범위)
        norm_x = center_x / self.original_width
        norm_y = center_y / self.original_height
        
        print(f"  → Normalized: ({norm_x:.4f}, {norm_y:.4f})")
        
        # 구면 좌표로 변환 (라디안)
        # φ (경도/longitude): -π ~ π 
        # 왼쪽이 음수(-π), 오른쪽이 양수(π), 중앙이 0
        phi = (norm_x - 0.5) * 2 * math.pi
        
        # θ (위도/latitude): -π/2 ~ π/2
        # 위쪽이 양수(π/2), 아래쪽이 음수(-π/2), 중앙이 0  
        theta = (0.5 - norm_y) * math.pi
        
        # 각도 크기 계산 (라디안)
        width_angle = (width / self.original_width) * 2 * math.pi
        height_angle = (height / self.original_height) * math.pi
        
        # 도(degree) 변환
        phi_deg = math.degrees(phi)
        theta_deg = math.degrees(theta)
        width_angle_deg = math.degrees(width_angle)
        height_angle_deg = math.degrees(height_angle)
        
        # 경도 정규화 (-180 ~ 180도)
        if phi_deg > 180:
            phi_deg -= 360
        elif phi_deg < -180:
            phi_deg += 360
        
        print(f"  → Spherical coords: φ={phi_deg:.2f}°, θ={theta_deg:.2f}°")
        print(f"  → Angular size: {width_angle_deg:.2f}° x {height_angle_deg:.2f}°")
        
        # BFoV 데이터 생성 (논문 형식)
        bfov_data = {
            # 중심점 (구면 좌표)
            'phi': phi,                    # 경도 (라디안)
            'theta': theta,                # 위도 (라디안)
            'phi_degrees': phi_deg,        # 경도 (도)
            'theta_degrees': theta_deg,    # 위도 (도)
            
            # 각도 크기
            'width_angle': width_angle,           # 너비 각도 (라디안)
            'height_angle': height_angle,         # 높이 각도 (라디안)
            'width_angle_degrees': width_angle_deg,   # 너비 각도 (도)
            'height_angle_degrees': height_angle_deg, # 높이 각도 (도)
            
            # 메타데이터
            'center_pixel': {
                'x': center_x,
                'y': center_y
            },
            'pixel_size': {
                'width': width,
                'height': height
            },
            'original_resolution': {
                'width': self.original_width,
                'height': self.original_height
            },
            
            # 논문 포맷 (φ, θ, h, w)
            'bfov_format': {
                'phi': phi,          # 중심점 경도
                'theta': theta,      # 중심점 위도  
                'h': height_angle,   # 높이 각도
                'w': width_angle     # 너비 각도
            }
        }
        
        return bfov_data

    # BFoV 역변환 함수 (나중에 로드할 때 사용)
    def bfov_to_original_coords(self, bfov_data):
        """BFoV → 원본 픽셀 좌표 역변환"""
        if not self.is_360_mode:
            return None
        
        phi = bfov_data['bfov_format']['phi']
        theta = bfov_data['bfov_format']['theta'] 
        height_angle = bfov_data['bfov_format']['h']
        width_angle = bfov_data['bfov_format']['w']
        
        # 구면 좌표를 정규화 좌표로 변환
        norm_x = (phi / (2 * math.pi)) + 0.5
        norm_y = 0.5 - (theta / math.pi)
        
        # 정규화 좌표를 픽셀 좌표로 변환
        center_x = norm_x * self.original_width
        center_y = norm_y * self.original_height
        
        # 각도 크기를 픽셀 크기로 변환
        width = (width_angle / (2 * math.pi)) * self.original_width
        height = (height_angle / math.pi) * self.original_height
        
        # 좌상단 좌표 계산
        x = center_x - width / 2
        y = center_y - height / 2
        
        # 경계 체크
        x = max(0, min(x, self.original_width - width))
        y = max(0, min(y, self.original_height - height))
        
        return {
            'x': int(round(x)),
            'y': int(round(y)),
            'width': int(round(width)),
            'height': int(round(height))
        }

    def convert_bbox_for_save(self, bbox):
        """저장용: 패딩 좌표 → 원본 좌표 + BFoV 변환"""
        
        # 1. 패딩 좌표를 원본 좌표로 변환
        original_bbox = self.convert_padded_to_original_coords(bbox)
        
        # 2. BFoV 계산 (360도 모드에서만)
        bfov_data = None
        if self.is_360_mode:
            bfov_data = self.calculate_bfov_from_original_coords(original_bbox)
        
        # 3. 저장용 최종 형식 생성
        save_data = {
            # 기본 정보
            'object_type': original_bbox['object_type'],
            'track_id': original_bbox['track_id'],
            
            # 픽셀 좌표 (원본 영상 기준)
            'pixel_coords': {
                'x': original_bbox['x'],
                'y': original_bbox['y'],
                'width': original_bbox['width'],
                'height': original_bbox['height']
            },
        }
        
        # 360도 추가 정보
        if self.is_360_mode:
            # BFoV 데이터 추가
            if bfov_data:
                save_data['bfov'] = {
                    # 논문 표준 형식 (φ, θ, h, w)
                    'phi': bfov_data['phi'],                    # 중심점 경도 (라디안)
                    'theta': bfov_data['theta'],                # 중심점 위도 (라디안)  
                    'height_angle': bfov_data['height_angle'],  # 높이 각도 (라디안)
                    'width_angle': bfov_data['width_angle'],    # 너비 각도 (라디안)
                    
                    # 도 단위 (가독성)
                    'phi_degrees': bfov_data['phi_degrees'],
                    'theta_degrees': bfov_data['theta_degrees'],
                    'height_angle_degrees': bfov_data['height_angle_degrees'],
                    'width_angle_degrees': bfov_data['width_angle_degrees']
                }
        
        print(f"Converted for save: {bbox['track_id']}")
        print(f"  Pixel: ({save_data['pixel_coords']['x']}, {save_data['pixel_coords']['y']}) "
            f"{save_data['pixel_coords']['width']}x{save_data['pixel_coords']['height']}")
        if bfov_data:
            print(f"  BFoV: φ={bfov_data['phi_degrees']:.1f}°, θ={bfov_data['theta_degrees']:.1f}°, "
                f"size={bfov_data['width_angle_degrees']:.1f}°x{bfov_data['height_angle_degrees']:.1f}°")
        
        return save_data

    # main_window.py의 get_current_annotation_with_qa() 함수에서 사용
    def get_save_format_annotations(self):
        """저장용으로 변환된 어노테이션 데이터 반환"""
        save_annotations = {}
        
        for frame_idx, bboxes in self.video_canvas.frame_bboxes.items():
            save_annotations[frame_idx] = []
            for bbox in bboxes:
                # 각 박스를 저장용 형식으로 변환
                converted_bbox = self.video_canvas.convert_bbox_for_save(bbox)
                save_annotations[frame_idx].append(converted_bbox)
        
        return save_annotations