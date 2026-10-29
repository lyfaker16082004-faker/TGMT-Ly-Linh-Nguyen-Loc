from ultralytics import YOLO
import multiprocessing

def main():
    
    model = YOLO('yolo11m.pt') 
    
    print("Bắt đầu dạy AI cách nhận biết ghế trống và bóng râm...")
    model.train(
        data='dataset/data.yaml', # 2. Trỏ tới bộ dataset
        epochs=150,         #  học khoảng 150 vòng 
        patience=15,       # Dừng sớm nếu sau 15 vòng không thấy tiến bộ
        imgsz=640,         # kích thước ảnh
        batch=16,          # Card RTX 4060 vẫn chạy mượt ở batch 16
        device=0,          
        project='runs/detect',
        name='yolo11m_v1' 
    )

if __name__ == '__main__':
    multiprocessing.freeze_support()
    main() 