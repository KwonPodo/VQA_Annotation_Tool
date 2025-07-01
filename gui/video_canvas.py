import cv2

from PySide6.QtCore import Qt, QRect
from PySide6.QtGui import QPixmap, QImage, QCursor, QPen, QColor, QBrush, QPainter
from PySide6.QtWidgets import (
    QLabel,
    QDialog
)

from gui.config import track_id_color_palette

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

        # Store bboxes with track_id
        self.frame_bboxes = {} # Dict[frame_index: List[bbox_list]]

        # Track ID management
        self.existing_track_ids = {} # Dict[object_type: List[track_id]]

        self.track_registry = {} # Dict[object_type: List[track_id]]
        self.color_palette = track_id_color_palette
        self.color_index = 0


        # BBox Edit State
        self.edit_mode = False
        self.resize_handle = None
        self.last_mouse_pos = None
        self.selected_bbox = None
        self.selected_bbox_index = None
        self.move_start_img = None
        self.resize_start_img = None
        self.original_bbox = None

        self.setFocusPolicy(Qt.StrongFocus)

        # Zone Detection Threshold
        self.CORNER_THRESHOLD = 15
        self.EDGE_THRESHOLD = 10

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
        
        h, w, ch = self.current_frame_data.shape
        bytes_per_line = ch * w

        # Create QImage from current frame data
        qt_image = QImage(
            self.current_frame_data.data, w, h, bytes_per_line, QImage.Format_RGB888
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
    
    def add_bbox_with_annotation(self, x, y, width, height, object_type, track_id):
        """Add annotated bounding box to current frame"""
        # 최종 경계체크 및 보정
        x = max(0, min(x, self.original_width - 1))
        y = max(0, min(y, self.original_height - 1))

        # 너비/높이가 경계를 벗어나지 않도록 조정
        if x + width > self.original_width:
            width = self.original_width - x
        if y + height > self.original_height:
            height = self.original_height - y

        width = max(10, width)
        height = max(10, height)

        # 보정 후에도 경계를 벗어나는 경우 처리
        if x + width > self.original_width:
            x = self.original_width - width
        if y + height > self.original_height:
            y = self.original_height - height
        
        # 최종 검증
        if x < 0 or y < 0 or x + width > self.original_width or y + height > self.original_height:
            print(f" Invalid bbox after correction: x={x}, y={y}, w={width}, h={height}")
            print(f" Image bounds: {self.original_width}x{self.original_height}")
            return False

        # Assign color if new track_id
        if track_id not in self.track_registry:
            self.track_registry[track_id] = self.get_next_color()
        
        bbox = {
            'x': x,
            'y': y,
            'width': width,
            'height': height,
            'object_type': object_type,
            'track_id': track_id,
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

        self.notify_progress_update()
    
    def show_annotation_dialog(self, x, y, width, height):
        """Show annotation dialog for bounding box"""
        from gui.bbox_dialog import BBoxAnnotationDialog
        
        # Collect track_ids used in current frame
        current_frame_track_ids = []
        if self.current_frame in self.frame_bboxes:
            current_frame_track_ids = [bbox['track_id'] for bbox in self.frame_bboxes[self.current_frame]]
        
        dialog = BBoxAnnotationDialog(
            available_objects=self.available_objects,
            existing_track_ids=self.existing_track_ids.copy(),
            current_frame_track_ids=current_frame_track_ids,  # Pass current frame track_ids
            parent=self
        )
        
        if dialog.exec() == QDialog.Accepted:
            object_type, track_id = dialog.get_annotation_result()
            if object_type and track_id:
                self.add_bbox_with_annotation(x, y, width, height, object_type, track_id)
                return True
        return False

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

    def get_bbox_zone(self, canvas_point, bbox):
        """
        주어진 포인트가 BBox의 어느 존에 있는지 판단
        Returns: 'corner_tl', 'corner_tr', 'corner_bl', 'corner_br', 
                'edge_top', 'edge_bottom', 'edge_left', 'edge_right', 
                'inside', 'outside'
        """
        # BBox를 캔버스 좌표로 변환
        top_left = self.image_to_canvas_coords((bbox['x'], bbox['y']))
        bottom_right = self.image_to_canvas_coords((bbox['x'] + bbox['width'], bbox['y'] + bbox['height']))
        
        if not top_left or not bottom_right:
            return 'outside'
        
        x, y = canvas_point.x(), canvas_point.y()
        left, top = top_left
        right, bottom = bottom_right
        
        # 박스 외부 체크
        if x < left or x > right or y < top or y > bottom:
            return 'outside'
        
        # 꼭짓점 체크 (우선순위 높음)
        if (abs(x - left) <= self.CORNER_THRESHOLD and abs(y - top) <= self.CORNER_THRESHOLD):
            return 'corner_tl'  # Top-Left
        elif (abs(x - right) <= self.CORNER_THRESHOLD and abs(y - top) <= self.CORNER_THRESHOLD):
            return 'corner_tr'  # Top-Right
        elif (abs(x - left) <= self.CORNER_THRESHOLD and abs(y - bottom) <= self.CORNER_THRESHOLD):
            return 'corner_bl'  # Bottom-Left
        elif (abs(x - right) <= self.CORNER_THRESHOLD and abs(y - bottom) <= self.CORNER_THRESHOLD):
            return 'corner_br'  # Bottom-Right
        
        # 모서리 체크
        elif abs(y - top) <= self.EDGE_THRESHOLD:
            return 'edge_top'
        elif abs(y - bottom) <= self.EDGE_THRESHOLD:
            return 'edge_bottom'
        elif abs(x - left) <= self.EDGE_THRESHOLD:
            return 'edge_left'
        elif abs(x - right) <= self.EDGE_THRESHOLD:
            return 'edge_right'
        
        # 내부
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
        
        # 이동 시작점을 이미지 좌표로 저장
        self.move_start_img = self.canvas_to_image_coords(canvas_point)
        self.original_bbox = bbox.copy()  # 원본 좌표 백업

    def start_resize_mode(self, bbox, bbox_index, zone, canvas_point):
        """BBox 리사이즈 모드 시작"""
        self.edit_mode = True
        self.is_drawing = False
        self.selected_bbox = bbox
        self.selected_bbox_index = bbox_index
        self.resize_handle = zone
        self.last_mouse_pos = canvas_point
        
        # 리사이즈 시작점을 이미지 좌표로 저장
        self.resize_start_img = self.canvas_to_image_coords(canvas_point)
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
        if not self.move_start_img or not self.selected_bbox:
            return
        
        # 현재 마우스 위치를 이미지 좌표로 변환
        current_img = self.canvas_to_image_coords(canvas_point)
        if not current_img:
            return
        
        # 이동 거리 계산
        dx = current_img[0] - self.move_start_img[0]
        dy = current_img[1] - self.move_start_img[1]
        
        # 새 위치 계산
        new_x = self.original_bbox['x'] + dx
        new_y = self.original_bbox['y'] + dy
        
        # 경계 체크 (이미지 범위 내에서만 이동)
        new_x = max(0, min(new_x, self.original_width - self.selected_bbox['width']))
        new_y = max(0, min(new_y, self.original_height - self.selected_bbox['height']))
        
        # BBox 위치 업데이트
        self.selected_bbox['x'] = new_x
        self.selected_bbox['y'] = new_y

    def handle_bbox_resize(self, canvas_point):
        """BBox 리사이즈 처리 - 완전한 경계 체크"""
        if not self.resize_start_img or not self.selected_bbox:
            return
        
        # 현재 마우스 위치를 이미지 좌표로 변환
        current_img = self.canvas_to_image_coords(canvas_point)
        if not current_img:
            return
        
        # 원본 BBox 좌표 (리사이즈 시작 시점)
        orig_x = self.original_bbox['x']
        orig_y = self.original_bbox['y']
        orig_width = self.original_bbox['width']
        orig_height = self.original_bbox['height']
        
        # 리사이즈 핸들에 따른 처리
        if self.resize_handle == 'corner_tl':
            # Top-Left 코너: x, y, width, height 모두 변경
            new_x = min(current_img[0], orig_x + orig_width - 10)
            new_y = min(current_img[1], orig_y + orig_height - 10)
            new_width = (orig_x + orig_width) - new_x
            new_height = (orig_y + orig_height) - new_y
            
            # 경계 체크
            self.selected_bbox['x'] = max(0, new_x)
            self.selected_bbox['y'] = max(0, new_y)
            self.selected_bbox['width'] = max(10, new_width)
            self.selected_bbox['height'] = max(10, new_height)
            
        elif self.resize_handle == 'corner_tr':
            # Top-Right 코너
            new_width = current_img[0] - orig_x
            new_y = min(current_img[1], orig_y + orig_height - 10)
            new_height = (orig_y + orig_height) - new_y
            
            # 경계 체크
            self.selected_bbox['y'] = max(0, new_y)
            self.selected_bbox['width'] = max(10, min(new_width, self.original_width - orig_x))
            self.selected_bbox['height'] = max(10, new_height)
            
        elif self.resize_handle == 'corner_bl':
            # Bottom-Left 코너
            new_x = min(current_img[0], orig_x + orig_width - 10)
            new_width = (orig_x + orig_width) - new_x
            new_height = current_img[1] - orig_y
            
            # 경계 체크
            self.selected_bbox['x'] = max(0, new_x)
            self.selected_bbox['width'] = max(10, new_width)
            self.selected_bbox['height'] = max(10, min(new_height, self.original_height - orig_y))
            
        elif self.resize_handle == 'corner_br':
            # Bottom-Right 코너
            new_width = current_img[0] - orig_x
            new_height = current_img[1] - orig_y
            
            # 경계 체크
            self.selected_bbox['width'] = max(10, min(new_width, self.original_width - orig_x))
            self.selected_bbox['height'] = max(10, min(new_height, self.original_height - orig_y))
            
        elif self.resize_handle == 'edge_top':
            # 위쪽 모서리
            new_y = min(current_img[1], orig_y + orig_height - 10)
            new_height = (orig_y + orig_height) - new_y
            
            # 경계 체크
            self.selected_bbox['y'] = max(0, new_y)
            self.selected_bbox['height'] = max(10, new_height)
            
        elif self.resize_handle == 'edge_bottom':
            # 아래쪽 모서리 - 완전 수정
            current_y = self.selected_bbox['y']  # 현재 y 좌표 사용
            new_height = current_img[1] - current_y
            max_height = self.original_height - current_y  # 현재 y 기준 최대 높이
            self.selected_bbox['height'] = max(10, min(new_height, max_height))
            
        elif self.resize_handle == 'edge_left':
            # 왼쪽 모서리
            new_x = min(current_img[0], orig_x + orig_width - 10)
            new_width = (orig_x + orig_width) - new_x
            
            # 경계 체크
            self.selected_bbox['x'] = max(0, new_x)
            self.selected_bbox['width'] = max(10, new_width)
            
        elif self.resize_handle == 'edge_right':
            # 오른쪽 모서리 - 완전 수정
            current_x = self.selected_bbox['x']  # 현재 x 좌표 사용
            new_width = current_img[0] - current_x
            max_width = self.original_width - current_x  # 현재 x 기준 최대 너비
            self.selected_bbox['width'] = max(10, min(new_width, max_width))

        # 추가 안전장치: 최종 경계 체크
        # 어떤 리사이즈든 결국 경계를 벗어나면 안 됨
        if self.selected_bbox['x'] + self.selected_bbox['width'] > self.original_width:
            self.selected_bbox['width'] = self.original_width - self.selected_bbox['x']
        
        if self.selected_bbox['y'] + self.selected_bbox['height'] > self.original_height:
            self.selected_bbox['height'] = self.original_height - self.selected_bbox['y']
        
        # 디버그 로그
        x, y, w, h = self.selected_bbox['x'], self.selected_bbox['y'], self.selected_bbox['width'], self.selected_bbox['height']
        print(f"Resized: x={x}, y={y}, w={w}, h={h} | x+w={x+w}, y+h={y+h} | Bounds: {self.original_width}x{self.original_height}")

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
        """새 BBox 그리기 완료"""
        self.is_drawing = False
        
        # Convert to image coordinates
        start_img = self.canvas_to_image_coords(self.start_point)
        end_img = self.canvas_to_image_coords(self.end_point)
        
        if start_img and end_img:
            # Calculate bbox dimensions
            x = min(start_img[0], end_img[0])
            y = min(start_img[1], end_img[1])
            width = abs(end_img[0] - start_img[0])
            height = abs(end_img[1] - start_img[1])

            x = max(0, x)
            y = max(0, y)
            if x + width > self.original_width:
                width = self.original_width - x
            if y + height > self.original_height:
                height = self.original_height - y
            
            # Only add if bbox has minimum size
            if width > 10 and height > 10:
                print(f"Creating bbox: x={x}, y={y}, w={width}, h={height} (bounded)")
                self.show_annotation_dialog(x, y, width, height)
            else:
                print(f"Bbox too small or invalid after boundary check: w={width}, h={height}")

    def complete_bbox_editing(self):
        """BBox 편집 완료"""
        self.edit_mode = False
        self.resize_handle = None
        self.last_mouse_pos = None
        self.move_start_img = None
        self.resize_start_img = None
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
            # Draw existing bboxes
            self.draw_existing_bboxes(painter)
        
            # Draw preview bbox while drawing
            if self.is_drawing and self.start_point and self.end_point:
                self.draw_preview_bbox(painter)
        finally:
            if painter.isActive():
                painter.end()

    def draw_existing_bboxes(self, painter):
        """Draw all existing bboxes for current frame"""
        if self.current_frame not in self.frame_bboxes:
            return
        
        if not painter.isActive():
            return
        
        for i, bbox in enumerate(self.frame_bboxes[self.current_frame]):
            # Convert image coords to canvas coords
            top_left = self.image_to_canvas_coords((bbox['x'], bbox['y']))
            bottom_right = self.image_to_canvas_coords((bbox['x'] + bbox['width'], bbox['y'] + bbox['height']))
            
            if top_left and bottom_right:
                # Use track-specific color
                if bbox['track_id'] in self.track_registry:
                    color = QColor(*self.track_registry[bbox['track_id']])
                else:
                    color = QColor(255, 0, 0)

                is_selected = (self.selected_bbox_index == i)
                if is_selected:
                    pen_width = 4
                    bright_color = QColor(color)
                    bright_color.setAlpha(255)
                    bright_color = bright_color.lighter(150)
                    pen = QPen(bright_color, pen_width)
                else:
                    pen_width = 2
                    pen = QPen(color, pen_width)

                painter.setPen(pen)
                painter.setBrush(QBrush(Qt.NoBrush))
                
                # Draw rectangle
                rect = QRect(top_left[0], top_left[1], 
                        bottom_right[0] - top_left[0], 
                        bottom_right[1] - top_left[1])
                painter.drawRect(rect)
                
                # Draw label with track ID
                painter.setPen(QPen(color, 1))
                painter.drawText(top_left[0], top_left[1] - 5, f"{bbox['object_type']} - {bbox['track_id']}")

                if is_selected:
                    self.draw_resize_handles(painter, top_left, bottom_right, bright_color)

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
