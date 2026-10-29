from ultralytics import YOLO

def main():
    # 1. Trỏ chính xác vào "bộ não" tốt nhất vừa train xong
    model = YOLO(r'runs\detect\runs\detect\yolo11m_v1\weights\best.pt')

    # 2. Sử dụng luôn thư mục test mà Roboflow đã chia sẵn cho bạn
    thu_muc_test = 'test_images/' 
    
    print(f"Đang tiến hành nhận diện hàng loạt toàn bộ ảnh trong: {thu_muc_test}")
    
    # 3. Chạy dự đoán (Inference)
    results = model.predict(
        source=thu_muc_test, 
        conf=0.4,       # Chỉ vẽ khung nếu độ tự tin >= 60%
        save=True,       # Bắt buộc True để máy lưu ảnh ra thư mục
        show=False,      # Bắt buộc False để không bật popup hàng trăm ảnh gây treo máy
        stream=True      # Tối ưu hóa bộ nhớ RAM/VRAM
    )
    
    # Vòng lặp này bắt buộc phải có để lệnh predict(stream=True) thực sự chạy
    for r in results:
        pass
        
    print("\n✅ Hoàn tất! Hãy kiểm tra thư mục kết quả mới nhất (thường là runs/detect/predict...) để xem ảnh.")

if __name__ == '__main__':
    main()