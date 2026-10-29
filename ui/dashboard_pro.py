import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import customtkinter as ctk
import cv2
from PIL import Image, ImageTk
import datetime
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

ctk.set_appearance_mode("Light")
BG_COLOR = "#F0F4F8"
SIDEBAR_COLOR = "#0D2546"
CARD_COLOR = "#FFFFFF"
TEXT_MAIN = "#2B3445"
GREEN_ACCENT = "#198754"
BLUE_ACCENT = "#0D6EFD"
RED_ACCENT = "#DC3545"
ORANGE_ACCENT = "#FD7E14"

DAILY_CSV_FILE = "thong_ke_ngay.csv"

class ProDashboard(ctk.CTkFrame):
    def __init__(self, master, engine):
        super().__init__(master, fg_color=BG_COLOR)
        self.engine = engine
        self.preview_frame = None
        self.current_display_frame = None
        self.click_points = []
        self.log_data = []
        
        self.img_scale = 1.0
        self.img_offset_x = 0
        self.img_offset_y = 0
        
        self.init_daily_csv()
        self.setup_ui()
        self.refresh_daily_summary_ui()
        self.update_clock()

    # ================= QUẢN LÝ FILE CSV THỐNG KÊ THEO NGÀY =================
    def init_daily_csv(self):
        if not os.path.exists(DAILY_CSV_FILE):
            df = pd.DataFrame(columns=["Ngày", "Tổng Vào", "Tổng Ra", "Cập nhật cuối"])
            df.to_csv(DAILY_CSV_FILE, index=False, encoding="utf-8-sig")

    def update_daily_csv(self, add_in=0, add_out=0):
        today_str = datetime.datetime.now().strftime("%d/%m/%Y")
        now_time = datetime.datetime.now().strftime("%H:%M:%S")
        
        try:
            df = pd.read_csv(DAILY_CSV_FILE, encoding="utf-8-sig")
        except Exception:
            df = pd.DataFrame(columns=["Ngày", "Tổng Vào", "Tổng Ra", "Cập nhật cuối"])

        if today_str in df["Ngày"].values:
            idx = df.index[df["Ngày"] == today_str][0]
            df.loc[idx, "Tổng Vào"] = int(df.loc[idx, "Tổng Vào"]) + add_in
            df.loc[idx, "Tổng Ra"] = int(df.loc[idx, "Tổng Ra"]) + add_out
            df.loc[idx, "Cập nhật cuối"] = now_time
        else:
            new_row = pd.DataFrame([{
                "Ngày": today_str,
                "Tổng Vào": add_in,
                "Tổng Ra": add_out,
                "Cập nhật cuối": now_time
            }])
            df = pd.concat([df, new_row], ignore_index=True)

        df.to_csv(DAILY_CSV_FILE, index=False, encoding="utf-8-sig")
        self.refresh_daily_summary_ui()

    def setup_ui(self):
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=5)
        self.grid_columnconfigure(2, weight=2)
        self.grid_rowconfigure(0, weight=0)
        self.grid_rowconfigure(1, weight=6)
        self.grid_rowconfigure(2, weight=3)

        self.setup_sidebar()
        self.setup_header()
        self.setup_video_section()
        self.setup_kpi_section()
        self.setup_daily_csv_section() # Thay cho biểu đồ theo giờ cũ
        self.setup_table_section()

    # ================= 1. SIDEBAR =================
    def setup_sidebar(self):
        sidebar = ctk.CTkFrame(self, width=220, fg_color=SIDEBAR_COLOR, corner_radius=0)
        sidebar.grid(row=0, column=0, rowspan=3, sticky="nsew")
        sidebar.grid_propagate(False)
        
        ctk.CTkLabel(sidebar, text="TDV", font=("Arial", 19, "bold"), text_color="white", justify="left").pack(pady=(25, 30), padx=20, anchor="w")
        
        self.nav_btns = {}
        menu_items = [
            ("overview", "🏠 Tổng quan", lambda: None),
            ("camera", "📹 Nguồn Video", self.select_video),
            ("webcam", "📷 Webcam Live", self.open_webcam),
            ("history", "🕒 Chi tiết", self.open_full_history_modal),
            ("settings", "⚙️ Cài đặt AI & Model", self.open_settings_modal)
        ]
        
        for key, text, cmd in menu_items:
            btn = ctk.CTkButton(
                sidebar, text=text, fg_color=BLUE_ACCENT if key == "overview" else "transparent",
                text_color="white", hover_color="#1B3A68", font=("Arial", 13, "bold"),
                anchor="w", height=42, corner_radius=8,
                command=lambda k=key, c=cmd: self.activate_nav(k, c)
            )
            btn.pack(pady=4, padx=15, fill="x")
            self.nav_btns[key] = btn

        ctk.CTkLabel(
            sidebar, text="DEV:Lý-Linh-Nguyên-Lộc\nPhiên bản Pro", 
            text_color="#A0ABC0", justify="left", font=("Arial", 11)
        ).pack(side="bottom", pady=20, padx=20, anchor="w")

    def activate_nav(self, key, callback):
        for k, b in self.nav_btns.items():
            b.configure(fg_color=BLUE_ACCENT if k == key else "transparent")
        callback()

    # ================= 2. HEADER =================
    def setup_header(self):
        header = ctk.CTkFrame(self, fg_color=BG_COLOR, corner_radius=0, height=55)
        header.grid(row=0, column=1, columnspan=2, sticky="ew", padx=20, pady=(10, 0))
        
        ctk.CTkLabel(header, text="👥 HỆ THỐNG ĐẾM NGƯỜI VÀO - RA CỔNG", font=("Arial", 21, "bold"), text_color=TEXT_MAIN).pack(side="left", pady=5)
        self.lbl_clock = ctk.CTkLabel(header, text="", font=("Arial", 13, "bold"), text_color="#555555", justify="right")
        self.lbl_clock.pack(side="right", pady=5)

    # ================= 3. KHU VỰC VIDEO =================
    def setup_video_section(self):
        video_card = ctk.CTkFrame(self, fg_color=CARD_COLOR, corner_radius=12)
        video_card.grid(row=1, column=1, sticky="nsew", padx=(20, 10), pady=10)
        video_card.grid_rowconfigure(1, weight=1)
        video_card.grid_columnconfigure(0, weight=1)
        
        top_bar = ctk.CTkFrame(video_card, fg_color="transparent")
        top_bar.grid(row=0, column=0, sticky="ew", padx=15, pady=(10, 5))
        self.lbl_cam_title = ctk.CTkLabel(top_bar, text="Màn hình Giám sát (Click 2 điểm lên hình để kẻ vạch)", font=("Arial", 13, "bold"), text_color=TEXT_MAIN)
        self.lbl_cam_title.pack(side="left")
        
        self.lbl_badge = ctk.CTkLabel(top_bar, text=" YOLOv11 + Tracking ", fg_color="#E2E8F0", text_color="#334155", corner_radius=6, font=("Arial", 11, "bold"))
        self.lbl_badge.pack(side="right", padx=5)

        self.video_canvas = tk.Canvas(video_card, bg="#181C24", highlightthickness=0, cursor="crosshair")
        self.video_canvas.grid(row=1, column=0, sticky="nsew", padx=15, pady=5)
        self.video_canvas.bind("<Button-1>", self.on_canvas_click)
        self.video_canvas.bind("<Configure>", self.on_canvas_resize)
        
        # Tạo text hướng dẫn và tự động neo vào tâm Canvas
        self.canvas_text = self.video_canvas.create_text(
            0, 0, text="1. Nhấn '📁 Chọn video'\n2. Click 2 điểm kẻ vạch\n3. Nhấn '▶ Bắt đầu'",
            fill="#CBD5E1", font=("Arial", 13, "bold"), justify="center", anchor="center"
        )
        # Tự động dời chữ về giữa mỗi khi khung Canvas thay đổi kích thước
        self.video_canvas.bind("<Configure>", lambda e: self.video_canvas.coords(self.canvas_text, e.width // 2, e.height // 2))

        ctrl_bar = ctk.CTkFrame(video_card, fg_color="transparent")
        ctrl_bar.grid(row=2, column=0, sticky="ew", padx=15, pady=(5, 12))
        
        btn_cfg = {"height": 34, "corner_radius": 6, "font": ("Arial", 12, "bold")}
        
        self.btn_select = ctk.CTkButton(ctrl_bar, text="📁 Chọn video", fg_color="#F1F5F9", text_color=TEXT_MAIN, hover_color="#E2E8F0", width=105, command=self.select_video, **btn_cfg)
        self.btn_select.pack(side="left", padx=4)
        
        self.btn_play = ctk.CTkButton(ctrl_bar, text="▶ Bắt đầu", fg_color=BLUE_ACCENT, hover_color="#0B5ED7", width=95, command=self.toggle_tracking, **btn_cfg)
        self.btn_play.pack(side="left", padx=4)
        
        self.btn_pause = ctk.CTkButton(ctrl_bar, text="⏸ Tạm dừng", fg_color="#F1F5F9", text_color=TEXT_MAIN, hover_color="#E2E8F0", width=100, state="disabled", command=self.pause_tracking, **btn_cfg)
        self.btn_pause.pack(side="left", padx=4)

        self.btn_redraw = ctk.CTkButton(ctrl_bar, text="🔄 Kẻ lại vạch", fg_color="#F1F5F9", text_color=TEXT_MAIN, hover_color="#E2E8F0", width=100, command=self.reset_line, **btn_cfg)
        self.btn_redraw.pack(side="left", padx=4)

        self.btn_flip = ctk.CTkButton(ctrl_bar, text="⇅ Đảo hướng Vào/Ra", fg_color="#F1F5F9", text_color=TEXT_MAIN, hover_color="#E2E8F0", width=130, command=self.flip_direction, **btn_cfg)
        self.btn_flip.pack(side="left", padx=4)

        self.lbl_status = ctk.CTkLabel(ctrl_bar, text="FPS: 0.0 | Conf: 0.40", font=("Arial", 11, "bold"), text_color="#64748B")
        self.lbl_status.pack(side="right", padx=5)

    # ================= 4. KHU VỰC KPI (PHẢI) =================
    def setup_kpi_section(self):
        kpi_frame = ctk.CTkFrame(self, fg_color="transparent")
        kpi_frame.grid(row=1, column=2, sticky="nsew", padx=(10, 20), pady=10)
        kpi_frame.grid_rowconfigure((0, 1, 2), weight=1)
        kpi_frame.grid_columnconfigure(0, weight=1)

        card_in = ctk.CTkFrame(kpi_frame, fg_color=CARD_COLOR, corner_radius=12)
        card_in.grid(row=0, column=0, sticky="nsew", pady=(0, 8))
        ctk.CTkLabel(card_in, text="🚶Lượt vào hiện tại ", font=("Arial", 14, "bold"), text_color=TEXT_MAIN).pack(pady=(14, 0))
        self.lbl_in = ctk.CTkLabel(card_in, text="0", font=("Arial", 48, "bold"), text_color=GREEN_ACCENT)
        self.lbl_in.pack(pady=2)

        card_out = ctk.CTkFrame(kpi_frame, fg_color=CARD_COLOR, corner_radius=12)
        card_out.grid(row=1, column=0, sticky="nsew", pady=8)
        ctk.CTkLabel(card_out, text="🚶Lượt ra hiện tại", font=("Arial", 14, "bold"), text_color=TEXT_MAIN).pack(pady=(12, 0))
        self.lbl_out = ctk.CTkLabel(card_out, text="0", font=("Arial", 44, "bold"), text_color=RED_ACCENT)
        self.lbl_out.pack(pady=0)
        self.lbl_inside = ctk.CTkLabel(card_out, text="Đang ở bên trong: 0 người", font=("Arial", 12, "bold"), text_color=BLUE_ACCENT)
        self.lbl_inside.pack(pady=(0, 8))

        card_cam = ctk.CTkFrame(kpi_frame, fg_color=CARD_COLOR, corner_radius=12)
        card_cam.grid(row=2, column=0, sticky="nsew", pady=(8, 0))
        ctk.CTkLabel(card_cam, text="📡 Trạng thái hệ thống", font=("Arial", 14, "bold"), text_color=TEXT_MAIN).pack(pady=(14, 6))
        self.lbl_cam_state = ctk.CTkLabel(
            card_cam, text="⚪ Chưa chọn video", font=("Arial", 13, "bold"), 
            text_color="#475569", fg_color="#F1F5F9", corner_radius=6, padx=14, pady=6
        )
        self.lbl_cam_state.pack()

    # ================= 5. THỐNG KÊ TỔNG HỢP THEO NGÀY (LƯU CSV) =================
    def setup_daily_csv_section(self):
        daily_card = ctk.CTkFrame(self, fg_color=CARD_COLOR, corner_radius=12)
        daily_card.grid(row=2, column=1, sticky="nsew", padx=(20, 10), pady=(5, 15))
        daily_card.grid_columnconfigure(0, weight=3) # Biểu đồ cột theo ngày
        daily_card.grid_columnconfigure(1, weight=2) # Bảng số liệu CSV theo ngày
        daily_card.grid_rowconfigure(1, weight=1)
        
        top = ctk.CTkFrame(daily_card, fg_color="transparent")
        top.grid(row=0, column=0, columnspan=2, sticky="ew", padx=15, pady=(10, 2))
        ctk.CTkLabel(
            top, text="📅 Thống kê Tổng Vào / Ra theo Ngày (Tự động lưu)", 
            font=("Arial", 14, "bold"), text_color=TEXT_MAIN
        ).pack(side="left")
        
        ctk.CTkButton(
            top, text="🗑️ Xóa dữ liệu ngày", fg_color="#F1F5F9", text_color=RED_ACCENT, hover_color="#FEE2E2",
            height=26, width=110, font=("Arial", 11, "bold"), command=self.clear_daily_csv
        ).pack(side="right", padx=4)
        
        ctk.CTkButton(
            top, text="📥 Xuất CSV ra chỗ khác", fg_color="#E8F5E9", text_color=GREEN_ACCENT, hover_color="#C8E6C9",
            height=26, width=135, font=("Arial", 11, "bold"), command=self.export_daily_csv_copy
        ).pack(side="right", padx=4)

        # Trái: Biểu đồ Cột theo Ngày
        self.fig, self.ax = plt.subplots(figsize=(4.2, 1.9), dpi=100)
        self.fig.patch.set_facecolor('#FFFFFF')
        self.chart_canvas = FigureCanvasTkAgg(self.fig, master=daily_card)
        self.chart_canvas.get_tk_widget().grid(row=1, column=0, sticky="nsew", padx=(10, 5), pady=5)

        # Phải: Bảng CSV theo Ngày
        cols = ("Date", "In", "Out", "Updated")
        self.tree_daily = ttk.Treeview(daily_card, columns=cols, show="headings", height=4)
        self.tree_daily.heading("Date", text="Ngày"); self.tree_daily.column("Date", width=85, anchor="center")
        self.tree_daily.heading("In", text="Tổng Vào"); self.tree_daily.column("In", width=65, anchor="center")
        self.tree_daily.heading("Out", text="Tổng Ra"); self.tree_daily.column("Out", width=65, anchor="center")
        self.tree_daily.heading("Updated", text="Cập nhật"); self.tree_daily.column("Updated", width=75, anchor="center")
        self.tree_daily.grid(row=1, column=1, sticky="nsew", padx=(5, 15), pady=(5, 10))

    def refresh_daily_summary_ui(self):
        try:
            df = pd.read_csv(DAILY_CSV_FILE, encoding="utf-8-sig")
        except Exception:
            return

        # Cập nhật bảng Treeview
        for item in self.tree_daily.get_children():
            self.tree_daily.delete(item)
        for _, row in df.iloc[::-1].iterrows():
            self.tree_daily.insert("", "end", values=(row["Ngày"], int(row["Tổng Vào"]), int(row["Tổng Ra"]), row["Cập nhật cuối"]))

        # Cập nhật biểu đồ cột (Lấy tối đa 7 ngày gần nhất)
        df_recent = df.tail(7)
        dates = df_recent["Ngày"].tolist() if not df_recent.empty else [datetime.datetime.now().strftime("%d/%m/%Y")]
        in_vals = df_recent["Tổng Vào"].astype(int).tolist() if not df_recent.empty else [0]
        out_vals = df_recent["Tổng Ra"].astype(int).tolist() if not df_recent.empty else [0]

        self.ax.clear()
        self.ax.set_facecolor('#FFFFFF')
        x = range(len(dates))
        w = 0.32
        bars1 = self.ax.bar([i - w/2 for i in x], in_vals, width=w, color='#28C76F', label='Tổng Vào')
        bars2 = self.ax.bar([i + w/2 for i in x], out_vals, width=w, color='#EA5455', label='Tổng Ra')
        
        self.ax.set_xticks(list(x))
        self.ax.set_xticklabels(dates, fontsize=8, color='#333333', fontweight='bold')
        self.ax.tick_params(axis='y', labelsize=8, colors='#555555')
        self.ax.spines['top'].set_visible(False)
        self.ax.spines['right'].set_visible(False)
        self.ax.spines['left'].set_color('#E2E8F0')
        self.ax.spines['bottom'].set_color('#E2E8F0')
        self.ax.set_ylim(0, max(max(in_vals + out_vals, default=5) + 4, 5))
        self.ax.legend(frameon=False, fontsize=8, loc='upper right')

        for bar in bars1:
            h = bar.get_height()
            if h > 0:
                self.ax.text(bar.get_x() + bar.get_width()/2, h + 0.1, int(h), ha='center', va='bottom', fontsize=8, color='#198754', fontweight='bold')
        for bar in bars2:
            h = bar.get_height()
            if h > 0:
                self.ax.text(bar.get_x() + bar.get_width()/2, h + 0.1, int(h), ha='center', va='bottom', fontsize=8, color='#DC3545', fontweight='bold')

        self.fig.tight_layout()
        self.chart_canvas.draw_idle()

    def export_daily_csv_copy(self):
        save_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            initialfile=f"ThongKe_TheoNgay_{datetime.datetime.now().strftime('%Y%m%d')}.csv",
            filetypes=[("CSV File", "*.csv"), ("Excel File", "*.xlsx")]
        )
        if save_path:
            df = pd.read_csv(DAILY_CSV_FILE, encoding="utf-8-sig")
            if save_path.endswith(".xlsx"):
                df.to_excel(save_path, index=False)
            else:
                df.to_csv(save_path, index=False, encoding="utf-8-sig")
            messagebox.showinfo("Thành công", f"Đã xuất bảng tổng hợp theo ngày tại:\n{save_path}")

    def clear_daily_csv(self):
        if messagebox.askyesno("Xác nhận", "Bạn có chắc muốn xóa làm mới lịch sử thống kê các ngày trong CSV?"):
            df = pd.DataFrame(columns=["Ngày", "Tổng Vào", "Tổng Ra", "Cập nhật cuối"])
            df.to_csv(DAILY_CSV_FILE, index=False, encoding="utf-8-sig")
            self.refresh_daily_summary_ui()

    # ================= 6. BẢNG LỊCH SỬ TỪNG LƯỢT (PHẢI DƯỚI) =================
    def setup_table_section(self):
        table_card = ctk.CTkFrame(self, fg_color=CARD_COLOR, corner_radius=12)
        table_card.grid(row=2, column=2, sticky="nsew", padx=(10, 20), pady=(5, 15))
        
        top_bar = ctk.CTkFrame(table_card, fg_color="transparent")
        top_bar.pack(fill="x", padx=15, pady=(10, 5))
        ctk.CTkLabel(top_bar, text="🕒 Lịch sử từng người", font=("Arial", 14, "bold"), text_color=TEXT_MAIN).pack(side="left")
        
        ctk.CTkButton(
            top_bar, text="Xem tất cả ➔", fg_color="transparent", text_color=BLUE_ACCENT,
            hover_color="#EFF6FF", font=("Arial", 12, "bold"), width=80, height=24,
            command=self.open_full_history_modal
        ).pack(side="right")

        style = ttk.Style()
        style.theme_use("default")
        style.configure("Treeview", background="white", foreground="#2B3445", rowheight=26, fieldbackground="white", borderwidth=0, font=("Arial", 10))
        style.configure("Treeview.Heading", background="#F8FAFC", foreground="#475569", font=('Arial', 10, 'bold'), borderwidth=0)

        self.tree = ttk.Treeview(table_card, columns=("Time", "ID", "Event"), show="headings", height=5)
        self.tree.heading("Time", text="Thời gian"); self.tree.column("Time", width=75, anchor="center")
        self.tree.heading("ID", text="Mã ID"); self.tree.column("ID", width=70, anchor="center")
        self.tree.heading("Event", text="Sự kiện"); self.tree.column("Event", width=85, anchor="center")
        self.tree.pack(fill="both", expand=True, padx=12, pady=(0, 10))

    # ================= LOGIC HIỂN THỊ & VẼ VẠCH =================
    def update_clock(self):
        now = datetime.datetime.now()
        days = ["Chủ nhật", "Thứ 2", "Thứ 3", "Thứ 4", "Thứ 5", "Thứ 6", "Thứ 7"]
        self.lbl_clock.configure(text=f"{days[now.isoweekday()%7]}, {now.strftime('%d/%m/%Y')}  |  {now.strftime('%H:%M:%S')}")
        self.after(1000, self.update_clock)

    def on_canvas_resize(self, event):
        if self.current_display_frame is not None and not self.engine.is_running:
            self.render_frame_on_canvas(self.current_display_frame)

    def render_frame_on_canvas(self, frame_bgr):
        self.current_display_frame = frame_bgr
        cw = self.video_canvas.winfo_width()
        ch = self.video_canvas.winfo_height()
        if cw < 50 or ch < 50:
            cw, ch = 800, 450
            
        fh, fw = frame_bgr.shape[:2]
        scale = min(cw / fw, ch / fh)
        new_w, new_h = int(fw * scale), int(fh * scale)
        
        self.img_scale = scale
        self.img_offset_x = (cw - new_w) // 2
        self.img_offset_y = (ch - new_h) // 2
        
        resized = cv2.resize(frame_bgr, (new_w, new_h))
        img_rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
        self.tk_img = ImageTk.PhotoImage(Image.fromarray(img_rgb))
        
        self.video_canvas.delete("all")
        self.video_canvas.create_image(self.img_offset_x, self.img_offset_y, anchor="nw", image=self.tk_img)

    def on_canvas_click(self, event):
        if self.engine.is_running:
            messagebox.showinfo("Đang chạy", "Hãy nhấn 'Dừng hẳn' trước khi kẻ lại vạch mới.")
            return
        if self.preview_frame is None:
            messagebox.showwarning("Chưa có video", "Vui lòng nhấn '📁 Chọn video' trước khi kẻ vạch!")
            return
            
        if len(self.click_points) >= 2:
            self.click_points.clear()

        orig_x = int((event.x - self.img_offset_x) / self.img_scale)
        orig_y = int((event.y - self.img_offset_y) / self.img_scale)
        
        orig_x = max(0, min(orig_x, self.engine.FRAME_W - 1))
        orig_y = max(0, min(orig_y, self.engine.FRAME_H - 1))
        
        self.click_points.append([orig_x, orig_y])
        self.redraw_preview_line()

    def redraw_preview_line(self):
        if self.preview_frame is None:
            return
        temp = self.preview_frame.copy()
        if len(self.click_points) == 1:
            cv2.circle(temp, tuple(self.click_points[0]), 6, (0, 0, 255), -1, cv2.LINE_AA)
            cv2.putText(temp, "Diem 1 (Click diem thu 2...)", (self.click_points[0][0] + 10, self.click_points[0][1]), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 255), 2)
        elif len(self.click_points) == 2:
            self.engine.set_line(self.click_points[0], self.click_points[1])
            self.engine.draw_line_with_direction(temp)
            
        self.render_frame_on_canvas(temp)

    # ================= CÁC HÀM SỰ KIỆN NÚT BẤM =================
    def select_video(self):
        if self.engine.is_running:
            self.engine.stop()
        path = filedialog.askopenfilename(filetypes=[("Video files", "*.mp4 *.avi *.mkv *.mov"), ("All files", "*.*")])
        if path:
            self.load_video_source(path, f"📹 Video: {os.path.basename(path)}")

    def open_webcam(self):
        if self.engine.is_running:
            self.engine.stop()
        self.load_video_source(0, "📷 Camera trực tiếp (Webcam 0)")

    def load_video_source(self, source, title_text):
        cap = cv2.VideoCapture(source)
        ret, frame = cap.read()
        cap.release()
        if not ret:
            messagebox.showerror("Lỗi", "Không thể đọc nguồn Video này!")
            return
            
        self.engine.video_path = source
        self.lbl_cam_title.configure(text=title_text)
        self.preview_frame = cv2.resize(frame, (self.engine.FRAME_W, self.engine.FRAME_H))
        
        if len(self.engine.line_points) != 2:
            p1 = [int(self.engine.FRAME_W * 0.2), int(self.engine.FRAME_H * 0.65)]
            p2 = [int(self.engine.FRAME_W * 0.8), int(self.engine.FRAME_H * 0.65)]
            self.click_points = [p1, p2]
            self.engine.set_line(p1, p2)
            
        self.redraw_preview_line()
        self.lbl_cam_state.configure(text="🟢 Đã sẵn sàng (Nhấn Bắt đầu)", text_color=GREEN_ACCENT, fg_color="#E8F5E9")

    def reset_line(self):
        self.click_points.clear()
        self.engine.line_points.clear()
        if self.preview_frame is not None:
            self.render_frame_on_canvas(self.preview_frame)

    def flip_direction(self):
        self.engine.reverse_line_direction()
        if len(self.engine.line_points) == 2:
            self.click_points = list(self.engine.line_points)
        if not self.engine.is_running and self.preview_frame is not None:
            self.redraw_preview_line()

    def toggle_tracking(self):
        if self.engine.video_path is None:
            messagebox.showwarning("Chưa chọn Video", "Vui lòng nhấn '📁 Chọn video' trước!")
            return
        if not self.engine.is_running:
            if len(self.engine.line_points) != 2:
                messagebox.showwarning("Chưa kẻ vạch", "Vui lòng click chuột 2 điểm trên hình để kẻ vạch đếm!")
                return
                
            self.btn_play.configure(text="⏹ Dừng hẳn", fg_color=RED_ACCENT, hover_color="#BB2D3B")
            self.btn_pause.configure(state="normal", text="⏸ Tạm dừng", fg_color="#F1F5F9", text_color=TEXT_MAIN)
            self.btn_select.configure(state="disabled")
            self.lbl_in.configure(text="0")
            self.lbl_out.configure(text="0")
            self.lbl_inside.configure(text="Đang ở bên trong: 0 người")
            self.lbl_cam_state.configure(text="🟢 Đang chạy Tracking...", text_color=GREEN_ACCENT, fg_color="#E8F5E9")
            
            self.engine.start(self.engine.video_path)
            self.master.start_ui_polling() # Kích hoạt vòng lặp vẽ hình chống đơ
        else:
            self.engine.stop()

    def pause_tracking(self):
        if not self.engine.is_running:
            return
        paused = self.engine.toggle_pause()
        if paused:
            self.btn_pause.configure(text="▶ Tiếp tục", fg_color=ORANGE_ACCENT, text_color="white")
            self.lbl_cam_state.configure(text="🟠 Đang tạm dừng", text_color=ORANGE_ACCENT, fg_color="#FFF3CD")
        else:
            self.btn_pause.configure(text="⏸ Tạm dừng", fg_color="#F1F5F9", text_color=TEXT_MAIN)
            self.lbl_cam_state.configure(text="🟢 Đang chạy Tracking...", text_color=GREEN_ACCENT, fg_color="#E8F5E9")

    # ================= CỬA SỔ POPUP =================
    def open_full_history_modal(self):
        win = ctk.CTkToplevel(self)
        win.title("Lịch sử chi tiết từng lượt người")
        win.geometry("620x450")
        win.attributes("-topmost", True)
        
        ctk.CTkLabel(win, text="🕒 CHI TIẾT TỪNG LƯỢT QUA CỔNG TRONG PHIÊN", font=("Arial", 16, "bold")).pack(pady=12)
        
        cols = ("STT", "Ngày", "Thời gian", "Mã ID", "Sự kiện", "Độ tin cậy")
        tree_all = ttk.Treeview(win, columns=cols, show="headings")
        for c in cols:
            tree_all.heading(c, text=c)
            tree_all.column(c, anchor="center", width=95)
        tree_all.pack(fill="both", expand=True, padx=15, pady=10)
        
        for idx, item in enumerate(reversed(self.log_data), 1):
            tree_all.insert("", "end", values=(idx, item["Ngày"], item["Thời gian"], f"ID {item['Mã Định Danh']}", item["Hành Động"], item["Độ tin cậy"]))

    def open_settings_modal(self):
        win = ctk.CTkToplevel(self)
        win.title("Cài đặt thông số AI & Tracking")
        win.geometry("420x360")
        win.attributes("-topmost", True)
        
        ctk.CTkLabel(win, text="⚙️ CÀI ĐẶT HỆ THỐNG AI", font=("Arial", 16, "bold")).pack(pady=15)
        
        lbl_c = ctk.CTkLabel(win, text=f"Ngưỡng tin cậy (Confidence): {self.engine.conf_thresh:.2f}", font=("Arial", 13, "bold"))
        lbl_c.pack(pady=(5, 2))
        
        def on_conf_change(val):
            self.engine.conf_thresh = round(float(val), 2)
            lbl_c.configure(text=f"Ngưỡng tin cậy (Confidence): {self.engine.conf_thresh:.2f}")
            
        slider = ctk.CTkSlider(win, from_=0.15, to=0.85, number_of_steps=70, command=on_conf_change)
        slider.set(self.engine.conf_thresh)
        slider.pack(pady=5, padx=30, fill="x")

        ctk.CTkLabel(win, text="Điểm xét va chạm qua vạch:", font=("Arial", 13, "bold")).pack(pady=(15, 5))
        pt_var = ctk.StringVar(value=self.engine.point_mode)
        
        def change_pt():
            self.engine.point_mode = pt_var.get()
            
        ctk.CTkRadioButton(win, text="Gót chân (Khuyên dùng cho góc cam nghiêng)", variable=pt_var, value="foot", command=change_pt).pack(pady=3)
        ctk.CTkRadioButton(win, text="Tâm cơ thể (Dùng cho cam ngang tầm mắt)", variable=pt_var, value="center", command=change_pt).pack(pady=3)

        def pick_model():
            p = filedialog.askopenfilename(filetypes=[("YOLO Weights", "*.pt")])
            if p:
                self.engine.load_new_model(p)
                if not self.engine.load_error:
                    messagebox.showinfo("Đã đổi Model", f"Đã nạp thành công trọng số:\n{p}")
                
        ctk.CTkButton(win, text="🧠 Đổi file trọng số (.pt) khác...", fg_color=BLUE_ACCENT, command=pick_model).pack(pady=20)