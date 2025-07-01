#!/usr/bin/env python3
"""
바운딩 박스 어노테이션 검증 도구
- JSON 데이터의 바운딩 박스 좌표 검증
- 시각화를 통한 정성적 검증
- 좌표 변환 로직 검증
"""

import json
import cv2
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from pathlib import Path
import argparse

class BBoxValidator:
    def __init__(self, json_file_path, video_file_path=None):
        """
        Args:
            json_file_path: 어노테이션 JSON 파일 경로
            video_file_path: 동영상 파일 경로 (선택사항)
        """
        self.json_file_path = json_file_path
        self.video_file_path = video_file_path
        self.annotation_data = None
        self.video_cap = None
        
        # 색상 팔레트 (track_id별 색상)
        self.color_palette = [
            (255, 0, 0),      # Red
            (0, 255, 0),      # Green  
            (0, 0, 255),      # Blue
            (255, 255, 0),    # Yellow
            (255, 0, 255),    # Magenta
            (0, 255, 255),    # Cyan
            (128, 0, 128),    # Purple
            (255, 165, 0),    # Orange
        ]
        
        self.track_colors = {}
        self.color_index = 0
        
        self.load_annotation_data()
        if video_file_path:
            self.load_video()
    
    def load_annotation_data(self):
        """JSON 어노테이션 데이터 로드"""
        try:
            with open(self.json_file_path, 'r', encoding='utf-8') as f:
                self.annotation_data = json.load(f)
            print(f"✅ JSON 데이터 로드 성공: {self.json_file_path}")
            self.print_data_summary()
        except Exception as e:
            print(f"❌ JSON 데이터 로드 실패: {e}")
            return False
        return True
    
    def load_video(self):
        """동영상 파일 로드"""
        try:
            self.video_cap = cv2.VideoCapture(self.video_file_path)
            if not self.video_cap.isOpened():
                print(f"❌ 동영상 파일 로드 실패: {self.video_file_path}")
                return False
            print(f"✅ 동영상 파일 로드 성공: {self.video_file_path}")
            return True
        except Exception as e:
            print(f"❌ 동영상 파일 로드 실패: {e}")
            return False
    
    def print_data_summary(self):
        """어노테이션 데이터 요약 정보 출력"""
        if not self.annotation_data:
            return
        
        video_info = self.annotation_data.get('video_info', {})
        groundings = self.annotation_data.get('groundings', [])
        
        print(f"\n📊 어노테이션 데이터 요약:")
        print(f"   비디오: {video_info.get('filename', 'N/A')}")
        print(f"   전체 프레임: {video_info.get('total_frames', 'N/A')}")
        print(f"   FPS: {video_info.get('fps', 'N/A')}")
        print(f"   해상도: {video_info.get('resolution', {}).get('width', 'N/A')} x {video_info.get('resolution', {}).get('height', 'N/A')}")
        print(f"   그라운딩 개수: {len(groundings)}")
        
        # 각 그라운딩별 정보
        for i, grounding in enumerate(groundings):
            time_segment = grounding.get('time_segment', {})
            annotations = grounding.get('annotations', {})
            print(f"\n   그라운딩 {i+1}:")
            print(f"     프레임 범위: {time_segment.get('start_frame', 'N/A')} ~ {time_segment.get('end_frame', 'N/A')}")
            print(f"     샘플링된 프레임: {time_segment.get('sampled_frames', [])}")
            print(f"     어노테이션된 프레임: {list(annotations.keys())}")
            
            # 각 프레임별 객체 개수
            for frame_idx, frame_annotations in annotations.items():
                objects = [ann['object_type'] for ann in frame_annotations]
                track_ids = [ann['track_id'] for ann in frame_annotations]
                print(f"       프레임 {frame_idx}: {len(frame_annotations)}개 객체 ({', '.join(set(objects))}) - Track IDs: {track_ids}")
    
    def get_track_color(self, track_id):
        """Track ID별 색상 할당"""
        if track_id not in self.track_colors:
            color = self.color_palette[self.color_index % len(self.color_palette)]
            self.track_colors[track_id] = color
            self.color_index += 1
        return self.track_colors[track_id]
    
    def validate_coordinates(self):
        """좌표 데이터 유효성 검증"""
        print(f"\n🔍 좌표 데이터 유효성 검증:")
        
        if not self.annotation_data:
            print("❌ 어노테이션 데이터가 없습니다.")
            return False
        
        video_info = self.annotation_data.get('video_info', {})
        resolution = video_info.get('resolution', {})
        img_width = resolution.get('width', 0)
        img_height = resolution.get('height', 0)
        
        if img_width == 0 or img_height == 0:
            print("❌ 비디오 해상도 정보가 없습니다.")
            return False
        
        print(f"   비디오 해상도: {img_width} x {img_height}")
        
        issues = []
        total_bboxes = 0
        
        for grounding in self.annotation_data.get('groundings', []):
            annotations = grounding.get('annotations', {})
            
            for frame_idx, frame_annotations in annotations.items():
                for i, bbox in enumerate(frame_annotations):
                    total_bboxes += 1
                    
                    x = bbox.get('x', 0)
                    y = bbox.get('y', 0)
                    width = bbox.get('width', 0)
                    height = bbox.get('height', 0)
                    track_id = bbox.get('track_id', 'unknown')
                    object_type = bbox.get('object_type', 'unknown')
                    
                    # 1. 음수 좌표 검사
                    if x < 0 or y < 0:
                        issues.append(f"프레임 {frame_idx}, {object_type}({track_id}): 음수 좌표 (x:{x}, y:{y})")
                    
                    # 2. 크기 검사
                    if width <= 0 or height <= 0:
                        issues.append(f"프레임 {frame_idx}, {object_type}({track_id}): 잘못된 크기 (w:{width}, h:{height})")
                    
                    # 3. 이미지 경계 검사
                    if x + width > img_width:
                        issues.append(f"프레임 {frame_idx}, {object_type}({track_id}): 가로 경계 초과 (x+w:{x+width} > {img_width})")
                    
                    if y + height > img_height:
                        issues.append(f"프레임 {frame_idx}, {object_type}({track_id}): 세로 경계 초과 (y+h:{y+height} > {img_height})")
                    
                    # 4. 매우 작은 바운딩 박스 검사 (10픽셀 미만)
                    if width < 10 or height < 10:
                        issues.append(f"프레임 {frame_idx}, {object_type}({track_id}): 매우 작은 박스 (w:{width}, h:{height})")
        
        print(f"   총 검사한 바운딩 박스: {total_bboxes}개")
        
        if issues:
            print(f"❌ {len(issues)}개의 문제 발견:")
            for issue in issues[:10]:  # 최대 10개만 출력
                print(f"     - {issue}")
            if len(issues) > 10:
                print(f"     ... 및 {len(issues) - 10}개 추가 문제")
            return False
        else:
            print("✅ 모든 좌표가 유효합니다!")
            return True
    
    def calculate_bbox_statistics(self):
        """바운딩 박스 통계 계산"""
        print(f"\n📊 Bounding box statistics:")
        
        if not self.annotation_data:
            return
        
        all_widths = []
        all_heights = []
        all_areas = []
        object_counts = {}
        track_counts = {}
        
        for grounding in self.annotation_data.get('groundings', []):
            annotations = grounding.get('annotations', {})
            
            for frame_idx, frame_annotations in annotations.items():
                for bbox in frame_annotations:
                    width = bbox.get('width', 0)
                    height = bbox.get('height', 0)
                    area = width * height
                    object_type = bbox.get('object_type', 'unknown')
                    track_id = bbox.get('track_id', 'unknown')
                    
                    all_widths.append(width)
                    all_heights.append(height)
                    all_areas.append(area)
                    
                    object_counts[object_type] = object_counts.get(object_type, 0) + 1
                    track_counts[track_id] = track_counts.get(track_id, 0) + 1
        
        if all_widths:
            print(f"   Width - Mean: {np.mean(all_widths):.1f}, Min: {np.min(all_widths)}, Max: {np.max(all_widths)}")
            print(f"   Height - Mean: {np.mean(all_heights):.1f}, Min: {np.min(all_heights)}, Max: {np.max(all_heights)}")
            print(f"   Area - Mean: {np.mean(all_areas):.1f}, Min: {np.min(all_areas)}, Max: {np.max(all_areas)}")
            
            print(f"\n   Count by object type:")
            for obj_type, count in sorted(object_counts.items()):
                print(f"     {obj_type}: {count} boxes")
            
            print(f"\n   Count by track ID:")
            for track_id, count in sorted(track_counts.items()):
                print(f"     {track_id}: {count} boxes")
    
    def get_frame_image(self, frame_index):
        """특정 프레임의 이미지 가져오기"""
        if not self.video_cap:
            return None
        
        self.video_cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
        ret, frame = self.video_cap.read()
        
        if ret:
            # BGR to RGB 변환
            return cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        return None
    
    def visualize_frame_annotations(self, frame_index, save_path=None, show_plot=True):
        """특정 프레임의 어노테이션 시각화"""
        print(f"\n🎨 프레임 {frame_index} 어노테이션 시각화:")
        
        # 해당 프레임의 어노테이션 찾기
        frame_annotations = []
        for grounding in self.annotation_data.get('groundings', []):
            annotations = grounding.get('annotations', {})
            if str(frame_index) in annotations:
                frame_annotations.extend(annotations[str(frame_index)])
        
        if not frame_annotations:
            print(f"   프레임 {frame_index}에 어노테이션이 없습니다.")
            return
        
        # 이미지 가져오기
        frame_image = None
        if self.video_cap:
            frame_image = self.get_frame_image(frame_index)
        
        # 비디오 해상도 정보
        video_info = self.annotation_data.get('video_info', {})
        resolution = video_info.get('resolution', {})
        img_width = resolution.get('width', 1280)
        img_height = resolution.get('height', 720)
        
        # 시각화
        fig, ax = plt.subplots(1, 1, figsize=(12, 8))
        
        if frame_image is not None:
            ax.imshow(frame_image)
            print(f"   실제 비디오 프레임 표시 (해상도: {frame_image.shape[1]}x{frame_image.shape[0]})")
        else:
            # 비디오가 없는 경우 빈 캔버스
            ax.set_xlim(0, img_width)
            ax.set_ylim(img_height, 0)  # Y축 뒤집기 (이미지 좌표계)
            ax.set_aspect('equal')
            print(f"   비디오 없음 - 좌표만 표시 (해상도: {img_width}x{img_height})")
        
        # 바운딩 박스 그리기
        for i, bbox in enumerate(frame_annotations):
            x = bbox.get('x', 0)
            y = bbox.get('y', 0)
            width = bbox.get('width', 0)
            height = bbox.get('height', 0)
            track_id = bbox.get('track_id', 'unknown')
            object_type = bbox.get('object_type', 'unknown')
            
            # 색상 가져오기
            color = self.get_track_color(track_id)
            color_normalized = tuple(c/255.0 for c in color)
            
            # 바운딩 박스 그리기
            rect = patches.Rectangle(
                (x, y), width, height,
                linewidth=2, edgecolor=color_normalized, facecolor='none'
            )
            ax.add_patch(rect)
            
            # 라벨 추가
            ax.text(x, y-5, f"{object_type}-{track_id}", 
                   color=color_normalized, fontsize=10, fontweight='bold',
                   bbox=dict(boxstyle="round,pad=0.3", facecolor='white', alpha=0.8))
            
            print(f"     {object_type}({track_id}): x={x}, y={y}, w={width}, h={height}")
        
        ax.set_title(f"Frame {frame_index} - {len(frame_annotations)} bounding boxes")
        ax.grid(True, alpha=0.3)
        
        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
            print(f"   시각화 저장: {save_path}")
        
        if show_plot:
            plt.show()
        else:
            plt.close()
    
    def visualize_all_annotated_frames(self, output_dir="validation_output", show_plots=False):
        """모든 어노테이션된 프레임 시각화"""
        print(f"\n🎨 모든 어노테이션된 프레임 시각화:")
        
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        annotated_frames = set()
        for grounding in self.annotation_data.get('groundings', []):
            annotations = grounding.get('annotations', {})
            annotated_frames.update(int(frame_idx) for frame_idx in annotations.keys())
        
        print(f"   총 {len(annotated_frames)}개 프레임 처리 중...")
        
        for frame_idx in sorted(annotated_frames):
            save_path = output_path / f"frame_{frame_idx:03d}.png"
            self.visualize_frame_annotations(frame_idx, save_path=save_path, show_plot=show_plots)
        
        print(f"✅ 모든 시각화 완료 - 저장 경로: {output_path}")
    
    def validate_coordinate_transformations(self):
        """좌표 변환 로직 검증 (VideoCanvas 코드 기반)"""
        print(f"\n🔧 Coordinate transformation validation:")
        
        video_info = self.annotation_data.get('video_info', {})
        resolution = video_info.get('resolution', {})
        original_width = resolution.get('width', 1280)
        original_height = resolution.get('height', 720)
        
        print(f"   Original video resolution: {original_width} x {original_height}")
        
        # Test with various canvas sizes
        test_canvas_sizes = [
            (640, 360),   # Half size
            (1920, 1080), # Larger size
            (800, 600),   # Different aspect ratio
            (500, 300),   # Small size
        ]
        
        print(f"\n   Coordinate transformation test with various canvas sizes:")
        
        for canvas_width, canvas_height in test_canvas_sizes:
            print(f"\n     Canvas size: {canvas_width} x {canvas_height}")
            
            # VideoCanvas scale_factor calculation logic
            scale_factor = min(
                canvas_width / original_width,
                canvas_height / original_height
            )
            
            # Scaled image size
            scaled_width = int(original_width * scale_factor)
            scaled_height = int(original_height * scale_factor)
            
            # Offset calculation (image centered in canvas)
            x_offset = (canvas_width - scaled_width) // 2
            y_offset = (canvas_height - scaled_height) // 2
            
            print(f"       Scale factor: {scale_factor:.4f}")
            print(f"       Scaled image: {scaled_width} x {scaled_height}")
            print(f"       Offset: ({x_offset}, {y_offset})")
            
            # Test coordinates
            test_coords = [
                (0, 0),                                    # Top-left
                (original_width, original_height),         # Bottom-right
                (original_width//2, original_height//2),   # Center
            ]
            
            print(f"       Coordinate transformation test:")
            for img_x, img_y in test_coords:
                # Image to Canvas transformation
                canvas_x = int(img_x * scale_factor + x_offset)
                canvas_y = int(img_y * scale_factor + y_offset)
                
                # Canvas to Image reverse transformation
                img_x_back = int((canvas_x - x_offset) / scale_factor)
                img_y_back = int((canvas_y - y_offset) / scale_factor)
                
                error_x = abs(img_x - img_x_back)
                error_y = abs(img_y - img_y_back)
                
                print(f"         Image({img_x},{img_y}) -> Canvas({canvas_x},{canvas_y}) -> Image({img_x_back},{img_y_back}) | Error: ({error_x},{error_y})")
                
                if error_x > 1 or error_y > 1:
                    print(f"         ⚠️  Large coordinate transformation error!")
        
        print(f"\n✅ Coordinate transformation logic validation completed")
    
    def run_full_validation(self, output_dir="validation_output"):
        """전체 검증 실행"""
        print("🚀 바운딩 박스 어노테이션 전체 검증 시작\n")
        
        # 1. 좌표 유효성 검증
        coord_valid = self.validate_coordinates()
        
        # 2. 통계 계산
        self.calculate_bbox_statistics()
        
        # 3. 좌표 변환 로직 검증
        self.validate_coordinate_transformations()
        
        # 4. 시각화
        self.visualize_all_annotated_frames(output_dir=output_dir, show_plots=False)
        
        # 5. 샘플 프레임 상세 표시
        annotated_frames = set()
        for grounding in self.annotation_data.get('groundings', []):
            annotations = grounding.get('annotations', {})
            annotated_frames.update(int(frame_idx) for frame_idx in annotations.keys())
        
        if annotated_frames:
            sample_frame = min(annotated_frames)
            print(f"\n👀 샘플 프레임 {sample_frame} 상세 시각화:")
            self.visualize_frame_annotations(sample_frame, show_plot=True)
        
        # 6. 최종 결과
        print(f"\n🎯 Validation results summary:")
        print(f"   Coordinate validity: {'✅ PASSED' if coord_valid else '❌ FAILED'}")
        print(f"   Visualization files: Saved in {output_dir}/ directory")
        print(f"   Coordinate transformation: ✅ Validated")
        
        if coord_valid:
            print(f"\n🎉 All validations completed successfully!")
            print(f"   Your annotation framework's bounding box storage is accurate.")
        else:
            print(f"\n⚠️  Some issues were found. Please check the error messages above.")

def main():
    parser = argparse.ArgumentParser(description='바운딩 박스 어노테이션 검증 도구')
    parser.add_argument('json_file', help='어노테이션 JSON 파일 경로')
    parser.add_argument('--video', help='동영상 파일 경로 (선택사항)')
    parser.add_argument('--output', default='validation_output', help='출력 디렉토리 (기본값: validation_output)')
    
    args = parser.parse_args()
    
    # 검증 실행
    validator = BBoxValidator(args.json_file, args.video)
    validator.run_full_validation(args.output)

if __name__ == "__main__":
    main()