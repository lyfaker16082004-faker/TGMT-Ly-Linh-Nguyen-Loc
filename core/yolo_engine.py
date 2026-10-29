import cv2
import threading
import time
import os
from collections import deque
from ultralytics import YOLO

class YOLOEngine:
    def __init__(self, model_path, cb_stats, cb_log, cb_stop, cb_error):
        self.model_path = model_path
        self.model = None
        self.load_error = None
        self._init_model(model_path)
        
        self.video_path = None
        self.cap = None
        self.is_running = False
        self.is_paused = False
        
        # Biến chia sẻ frame an toàn cho UI Polling (Chống đơ Tkinter 100%)
        self.latest_frame = None
        self.current_fps = 0.0
        
        # Cấu hình thông số AI
        self.conf_thresh = 0.40
        self.point_mode = "foot"  # "foot": Gót chân | "center": Tâm người
        self.invert_dir = False
        
        self.FRAME_W = 960
        self.FRAME_H = 540
        self.line_points = []
        
        self.track_trails = {}
        self.cooldown_ids = {}
        
        self.count_in = 0
        self.count_out = 0
        
        # Callbacks
        self.cb_stats = cb_stats
        self.cb_log = cb_log
        self.cb_stop = cb_stop
        self.cb_error = cb_error

    def _init_model(self, path):
        try:
            if not os.path.exists(path) and not path.startswith("yolo"):
                raise FileNotFoundError(f"Không tìm thấy file model tại: {path}")
            self.model = YOLO(path)
            self.model_path = path
            self.load_error = None
        except Exception as e:
            self.load_error = str(e)
            print(f"[LỖI NẠP MODEL]: {e}")

    def load_new_model(self, new_path):
        self._init_model(new_path)
        if self.load_error and self.cb_error:
            self.cb_error(self.load_error)

    def set_line(self, pt1, pt2):
        self.line_points = [list(pt1), list(pt2)]

    def reverse_line_direction(self):
        if len(self.line_points) == 2:
            self.line_points = [self.line_points[1], self.line_points[0]]
        else:
            self.invert_dir = not self.invert_dir

    def _intersect(self, A, B, C, D):
        def ccw(p1, p2, p3):
            return (p3[1] - p1[1]) * (p2[0] - p1[0]) > (p2[1] - p1[1]) * (p3[0] - p1[0])
        return ccw(A, C, D) != ccw(B, C, D) and ccw(A, B, C) != ccw(A, B, D)

    def draw_line_with_direction(self, frame):
        if len(self.line_points) != 2:
            return frame
        A, B = tuple(self.line_points[0]), tuple(self.line_points[1])
        
        cv2.line(frame, A, B, (0, 255, 255), 3, cv2.LINE_AA)
        cv2.circle(frame, A, 6, (0, 0, 255), -1, cv2.LINE_AA)
        cv2.circle(frame, B, 6, (0, 0, 255), -1, cv2.LINE_AA)
        
        mx, my = int((A[0] + B[0]) / 2), int((A[1] + B[1]) / 2)
        dx, dy = B[0] - A[0], B[1] - A[1]
        length = (dx**2 + dy**2) ** 0.5
        if length > 0:
            nx, ny = -dy / length, dx / length
            if self.invert_dir:
                nx, ny = -nx, -ny
            tip_x, tip_y = int(mx + nx * 45), int(my + ny * 45)
            cv2.arrowedLine(frame, (mx, my), (tip_x, tip_y), (0, 255, 0), 3, cv2.LINE_AA, tipLength=0.35)
            cv2.putText(frame, "HUONG VAO", (tip_x - 45, tip_y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 0), 2, cv2.LINE_AA)
            
        return frame

    def start(self, video_source):
        if self.model is None:
            if self.cb_error:
                self.cb_error(f"Chưa nạp được Model!\nChi tiết: {self.load_error}")
            self.cb_stop()
            return
            
        self.video_path = video_source
        self.is_running = True
        self.is_paused = False
        self.count_in = 0
        self.count_out = 0
        self.track_trails.clear()
        self.cooldown_ids.clear()
        threading.Thread(target=self._process_video, daemon=True).start()

    def toggle_pause(self):
        self.is_paused = not self.is_paused
        return self.is_paused

    def stop(self):
        self.is_running = False
        self.is_paused = False

    def _process_video(self):
        try:
            self.cap = cv2.VideoCapture(self.video_path)
            if not self.cap.isOpened():
                if self.cb_error:
                    self.cb_error("Không thể mở file Video này!")
                self.is_running = False
                self.cb_stop()
                return

            prev_time = time.time()
            tracker_type = "botsort.yaml"
            
            while self.cap.isOpened() and self.is_running:
                if self.is_paused:
                    time.sleep(0.05)
                    prev_time = time.time()
                    continue
                    
                ret, frame = self.cap.read()
                if not ret:
                    break
                    
                frame = cv2.resize(frame, (self.FRAME_W, self.FRAME_H))
                
                for tid in list(self.cooldown_ids.keys()):
                    self.cooldown_ids[tid] -= 1
                    if self.cooldown_ids[tid] <= 0:
                        del self.cooldown_ids[tid]

                self.draw_line_with_direction(frame)

                # Chạy Tracking (Tự động fallback nếu máy thiếu thư viện của botsort)
                try:
                    results = self.model.track(
                        frame, persist=True, tracker=tracker_type,iou=0.3,classes=[0],imgsz=1024,
                        conf=self.conf_thresh, verbose=False
                    )
                except Exception:
                    tracker_type = "bytetrack.yaml"
                    results = self.model.track(
                        frame, persist=True,iou=0.3,classes=[0],tracker=tracker_type,
                        conf=self.conf_thresh,imgsz=1024,verbose=False
                    )
                
                if results and results[0].boxes is not None and results[0].boxes.id is not None:
                    boxes = results[0].boxes.xyxy.cpu().numpy()
                    track_ids = results[0].boxes.id.int().cpu().numpy()
                    confs = results[0].boxes.conf.cpu().numpy()
                    
                    for box, track_id, conf in zip(boxes, track_ids, confs):
                        x1, y1, x2, y2 = map(int, box)
                        cx = (x1 + x2) // 2
                        cy = y2 if self.point_mode == "foot" else (y1 + y2) // 2
                        current_pt = (cx, cy)
                        
                        if track_id not in self.track_trails:
                            self.track_trails[track_id] = deque(maxlen=15)
                            
                        if len(self.track_trails[track_id]) > 0 and len(self.line_points) == 2:
                            prev_pt = self.track_trails[track_id][-1]
                            A, B = self.line_points[0], self.line_points[1]
                            
                            if track_id not in self.cooldown_ids and self._intersect(A, B, prev_pt, current_pt):
                                vAB = (B[0] - A[0], B[1] - A[1])
                                vP = (current_pt[0] - prev_pt[0], current_pt[1] - prev_pt[1])
                                cross_product = vAB[0] * vP[1] - vAB[1] * vP[0]
                                
                                if self.invert_dir:
                                    cross_product = -cross_product
                                    
                                if cross_product > 0:
                                    self.count_in += 1
                                    self.cooldown_ids[track_id] = 15
                                    self.cb_stats(self.count_in, self.count_out, 1, 0)
                                    self.cb_log(track_id, "Vào cổng", round(float(conf), 2))
                                    cv2.line(frame, tuple(A), tuple(B), (0, 255, 0), 6, cv2.LINE_AA)
                                elif cross_product < 0:
                                    self.count_out += 1
                                    self.cooldown_ids[track_id] = 15
                                    self.cb_stats(self.count_in, self.count_out, 0, 1)
                                    self.cb_log(track_id, "Ra cổng", round(float(conf), 2))
                                    cv2.line(frame, tuple(A), tuple(B), (0, 0, 255), 6, cv2.LINE_AA)

                        self.track_trails[track_id].append(current_pt)
                        
                        pts = list(self.track_trails[track_id])
                        for i in range(1, len(pts)):
                            cv2.line(frame, pts[i - 1], pts[i], (0, 255, 180), 2, cv2.LINE_AA)
                            
                        color = (25, 135, 84) if track_id not in self.cooldown_ids else (0, 215, 255)
                        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                        cv2.circle(frame, current_pt, 5, (0, 0, 255), -1)
                        
                        label = f"ID {track_id}"
                        (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 2)
                        cv2.rectangle(frame, (x1, y1 - th - 8), (x1 + tw + 6, y1), color, -1)
                        cv2.putText(frame, label, (x1 + 3, y1 - 4), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2, cv2.LINE_AA)

                curr_time = time.time()
                dt = curr_time - prev_time
                self.current_fps = (1.0 / dt) if dt > 0 else 0.0
                prev_time = curr_time
                
                # Cập nhật frame mới nhất cho UI Polling lấy
                self.latest_frame = frame
                time.sleep(0.005) # Nhường nhịp CPU cho Giao diện Tkinter mượt mà
                
        except Exception as e:
            if self.cb_error:
                self.cb_error(f"Lỗi trong lúc chạy Video:\n{str(e)}")
        finally:
            if self.cap:
                self.cap.release()
            self.is_running = False
            self.cb_stop()