import cv2
import numpy as np

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QImage
from PySide6.QtWidgets import (
    QLabel,
    QDialog
)

from gui.config import PANEL_WIDTH, PANEL_SPACING, track_id_color_palette

class VideoCanvas(QLabel):
    """Video Display Canvas"""

    def __init__(self):
        super().__init__()
        self.setMinimumSize(500, 300)
        self.setStyleSheet("border: 2px solid #cccccc; background-color: #f5f5f5;")
        self.setAlignment(Qt.AlignCenter)
        self.setText("Load Video File\n(Video Canvas)")

        # Video properties
        self.video_cap = None
        self.current_frame = 0
        self.total_frames = 0
        self.fps = 0
        self.video_resolution = (0, 0)

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

    def load_video(self, file_path):
        """Load video file"""
        if self.video_cap:
            self.video_cap.release()

        self.video_cap = cv2.VideoCapture(file_path)
        if self.video_cap.isOpened():
            self.total_frames = int(self.video_cap.get(cv2.CAP_PROP_FRAME_COUNT))
            self.fps = self.video_cap.get(cv2.CAP_PROP_FPS)
            self.current_frame = 0
            self.set_frame(0)
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

            # Convert BGR to RGB
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb_frame.shape
            bytes_per_line = ch * w

            # Store Original image size
            self.original_width = w
            self.original_height = h

            # Create QImage and scale to fit canvas
            qt_image = QImage(
                rgb_frame.data, w, h, bytes_per_line, QImage.Format_RGB888
            )
            canvas_size = self.size()
            scaled_pixmap = QPixmap.fromImage(qt_image).scaled(
                canvas_size, Qt.KeepAspectRatio, Qt.SmoothTransformation
            )

            # Calculate actual scale factor
            self.scale_factor = min(
                canvas_size.width() / w,
                canvas_size.height() / h
            )

            self.setPixmap(scaled_pixmap)

            return True
        return False

    def next_frame(self):
        """Go to next frame"""
        if self.current_frame < self.total_frames - 1:
            return self.set_frame(self.current_frame + 1)
        return False

    def prev_frame(self):
        """Go to previous frame"""
        if self.current_frame > 0:
            return self.set_frame(self.current_frame - 1)
        return False
    
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

    def undo_last_bbox(self):
        """Remove the last bounding box from current frame"""
        if self.current_frame in self.frame_bboxes:
            bboxes = self.frame_bboxes[self.current_frame]
            if bboxes:
                removed = bboxes.pop()
                print(f"Removed bbox: {removed['object_type']} - {removed['track_id']}")
                self.update()  # Trigger repaint
                return True
        return False

    def clear_current_frame_bboxes(self):
        """Clear all bboxes from current frame"""
        if self.current_frame in self.frame_bboxes:
            count = len(self.frame_bboxes[self.current_frame])
            self.frame_bboxes[self.current_frame] = []
            print(f"Cleared {count} bboxes from frame {self.current_frame}")
            self.update()  # Trigger repaint
            return count
        return 0

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

    # Mouse events for bounding box drawing
    def mousePressEvent(self, event):
        """Handle mouse press for bbox drawing"""
        if not self.bbox_mode or event.button() != Qt.LeftButton:
            return
        
        self.is_drawing = True
        self.start_point = event.position().toPoint()
        self.end_point = self.start_point

    def mouseMoveEvent(self, event):
        """Handle mouse move for bbox preview"""
        if not self.bbox_mode or not self.is_drawing:
            return
        
        self.end_point = event.position().toPoint()
        self.update()  # Trigger repaint for preview

    def mouseReleaseEvent(self, event):
        """Handle mouse release to complete bbox and show annotation dialog"""
        if not self.bbox_mode or event.button() != Qt.LeftButton or not self.is_drawing:
            return
        
        self.is_drawing = False
        self.end_point = event.position().toPoint()
        
        # Convert to image coordinates
        start_img = self.canvas_to_image_coords(self.start_point)
        end_img = self.canvas_to_image_coords(self.end_point)
        
        if start_img and end_img:
            # Calculate bbox dimensions
            x = min(start_img[0], end_img[0])
            y = min(start_img[1], end_img[1])
            width = abs(end_img[0] - start_img[0])
            height = abs(end_img[1] - start_img[1])
            
            # Only add if bbox has minimum size
            if width > 10 and height > 10:
                self.show_annotation_dialog(x, y, width, height)

    def paintEvent(self, event):
        """Paint event to draw bboxes and preview"""
        super().paintEvent(event)
        
        if not self.pixmap():
            return
        
        from PySide6.QtGui import QPainter
        painter = QPainter(self)
        
        # Draw existing bboxes
        self.draw_existing_bboxes(painter)
        
        # Draw preview bbox while drawing
        if self.is_drawing and self.start_point and self.end_point:
            self.draw_preview_bbox(painter)

    def draw_existing_bboxes(self, painter):
        """Draw all existing bboxes for current frame"""
        if self.current_frame not in self.frame_bboxes:
            return
        
        from PySide6.QtGui import QPen, QColor
        from PySide6.QtCore import QRect
        
        for bbox in self.frame_bboxes[self.current_frame]:
            # Convert image coords to canvas coords
            top_left = self.image_to_canvas_coords((bbox['x'], bbox['y']))
            bottom_right = self.image_to_canvas_coords((bbox['x'] + bbox['width'], bbox['y'] + bbox['height']))
            
            if top_left and bottom_right:
                # Use track-specific color
                if bbox['track_id'] in self.track_registry:
                    color = QColor(*self.track_registry[bbox['track_id']])
                else:
                    color = QColor(255, 0, 0)
                pen = QPen(color, 2)
                painter.setPen(pen)
                
                # Draw rectangle
                rect = QRect(top_left[0], top_left[1], 
                        bottom_right[0] - top_left[0], 
                        bottom_right[1] - top_left[1])
                painter.drawRect(rect)
                
                # Draw label with track ID
                label = f"{bbox['object_type']} - {bbox['track_id']}"
                painter.setPen(QPen(color, 1))
                painter.drawText(top_left[0], top_left[1] - 5, label)

    def draw_preview_bbox(self, painter):
        """Draw preview bbox while drawing"""
        from PySide6.QtGui import QPen, QColor
        from PySide6.QtCore import QRect
        
        pen = QPen(QColor(255, 0, 0), 2, Qt.DashLine)  # Red dashed line
        painter.setPen(pen)
        
        x = min(self.start_point.x(), self.end_point.x())
        y = min(self.start_point.y(), self.end_point.y())
        width = abs(self.end_point.x() - self.start_point.x())
        height = abs(self.end_point.y() - self.start_point.y())
        
        rect = QRect(x, y, width, height)
        painter.drawRect(rect)

    def get_frame_annotations(self, frame_num):
        """Get all annotations for a specific frame"""
        return self.frame_bboxes.get(frame_num, [])

    def get_all_annotations(self):
        """Get all annotations across all frames"""
        return self.frame_bboxes.copy()
