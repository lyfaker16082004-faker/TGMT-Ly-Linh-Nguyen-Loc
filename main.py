import os
import customtkinter as ctk
from tkinter import messagebox
import datetime
from core.yolo_engine import YOLOEngine
from ui.dashboard_pro import ProDashboard

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Hệ Thống Đếm Người Vào Ra Cổng - YOLOv11 & BoT-SORT Pro")
        self.geometry("1420x860")
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # ĐƯỜNG DẪN MODEL CỦA BẠN đã train nhé
        MODEL_PATH = r"runs\detect\runs\detect\yolo11m_v1\weights\best.pt"
        if not os.path.exists(MODEL_PATH):
            # Tự động tìm xem có file .pt nào sẵn trong thư mục gốc không
            if os.path.exists(r"weights\best.pt"):
                MODEL_PATH = r"weights\best.pt"
            elif os.path.exists("yolo11m.pt"):
                MODEL_PATH = "yolo11m.pt"
            elif os.path.exists("yolo11n.pt"):
                MODEL_PATH = "yolo11n.pt"
        
        self.engine = YOLOEngine(
            model_path=MODEL_PATH,
            cb_stats=self.on_stats,
            cb_log=self.on_log,
            cb_stop=self.on_stop,
            cb_error=self.on_error
        )
        
        self.dashboard = ProDashboard(self, self.engine)
        self.dashboard.pack(fill="both", expand=True)

        if self.engine.load_error:
            self.after(500, lambda: messagebox.showwarning(
                "Chú ý Đường dẫn Model", 
                f"Không tìm thấy model tại:\n{MODEL_PATH}\n\nHãy vào mục '⚙️ Cài đặt AI & Model' ở góc trái để chọn lại file best.pt của bạn!"
            ))

    # Vòng lặp lấy hình ảnh định kỳ mỗi 25ms (Không bao giờ làm treo giao diện)
    def start_ui_polling(self):
        if self.engine.is_running:
            if self.engine.latest_frame is not None and not self.engine.is_paused:
                self.dashboard.render_frame_on_canvas(self.engine.latest_frame)
                model_name = os.path.basename(self.engine.model_path)
                self.dashboard.lbl_status.configure(
                    text=f"FPS: {self.engine.current_fps:.1f}  |  Conf: {self.engine.conf_thresh:.2f}  |  Model: {model_name}"
                )
            self.after(25, self.start_ui_polling)

    def on_stats(self, count_in, count_out, add_in, add_out):
        def update():
            self.dashboard.lbl_in.configure(text=str(count_in))
            self.dashboard.lbl_out.configure(text=str(count_out))
            inside = max(0, count_in - count_out)
            self.dashboard.lbl_inside.configure(text=f"Đang ở bên trong: {inside} người")
            # Tự động cộng dồn vào file thong_ke_ngay.csv và cập nhật bảng + biểu đồ ngày
            self.dashboard.update_daily_csv(add_in, add_out)
        self.after(0, update)

    def on_log(self, track_id, event, conf):
        def add():
            now = datetime.datetime.now()
            d_str = now.strftime("%d/%m/%Y")
            t_str = now.strftime("%H:%M:%S")
            self.dashboard.tree.insert("", 0, values=(t_str, f"ID {track_id:02d}", event))
            self.dashboard.log_data.append({
                "Ngày": d_str,
                "Thời gian": t_str,
                "Mã Định Danh": int(track_id),
                "Hành Động": event,
                "Độ tin cậy": conf
            })
        self.after(0, add)

    def on_stop(self):
        def reset_ui():
            self.dashboard.btn_play.configure(text="▶ Bắt đầu", fg_color="#0D6EFD")
            self.dashboard.btn_pause.configure(state="disabled", text="⏸ Tạm dừng", fg_color="#F1F5F9", text_color="#2B3445")
            self.dashboard.btn_select.configure(state="normal")
            self.dashboard.lbl_cam_state.configure(text="⚪ Đã kết thúc phiên", text_color="#475569", fg_color="#F1F5F9")
        self.after(0, reset_ui)

    def on_error(self, err_msg):
        self.after(0, lambda: messagebox.showerror("Báo lỗi Hệ thống", err_msg))

    def on_closing(self):
        self.engine.stop()
        self.destroy()

if __name__ == "__main__":
    app = App()
    app.mainloop()