# 📚 Smart Library Kiosk - Tổng Quan Dự Án

Chào mừng người đẹp đến với hệ thống **Smart Library Kiosk** (Trạm Thư Viện Thông Minh) ạ! Đây là một hệ thống hiện đại, tích hợp Trí tuệ nhân tạo (AI) để tối ưu hóa quy trình mượn/trả sách tự động.

---

## 🏗️ 1. Kiến Trúc Tổng Thể (System Architecture)

Dự án được xây dựng theo mô hình **Client-Server** với các công nghệ hàng đầu:

- **Frontend**: [React.js](https://reactjs.org/) + [Vite](https://vitejs.dev/) - Mang lại giao diện mượt mà, phản hồi nhanh cho người dùng tại trạm.
- **Backend**: [FastAPI](https://fastapi.tiangolo.com/) (Python) - Hiệu năng cao, xử lý song song các tác vụ AI phức tạp.
- **Database**: [PostgreSQL](https://www.postgresql.org/) kết hợp [PGVector](https://github.com/pgvector/pgvector) - Lưu trữ dữ liệu quan hệ và các vector đặc trưng (embeddings).
- **AI Engines**: Tích hợp các mô hình Deep Learning chuyên sâu cho thị giác máy tính và ngôn ngữ tự nhiên.

---

## 🤖 2. Các Thành Phần AI Cốt Lõi (Core AI Components)

Hệ thống sở hữu "bộ não" cực kỳ thông minh với 4 trụ cột chính:

1.  **🔐 Nhận Diện Khuôn Mặt (Face Recognition)**:
    - **Công nghệ**: ArcFace (via InsightFace).
    - **Chức năng**: Định danh sinh viên tự động trong < 1 giây, thay thế thẻ thư viện truyền thống. Trích xuất vector 512 chiều để so khớp chính xác cao.

2.  **📚 Phát Hiện Sách (Book Detection)**:
    - **Công nghệ**: [YOLOv8](https://ultralytics.com/).
    - **Chức năng**: Tự động phát hiện vị trí các cuốn sách khi người dùng đặt lên khay cảm biến của Kiosk, hỗ trợ xử lý nhiều cuốn sách cùng lúc.

3.  **📝 Nhận Diện Thông Tin Sách (Book Identification)**:
    - **Công nghệ**: [PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR) + Fuzzy Search.
    - **Quy trình**:
        - Đọc Barcode/ISBN (Ưu tiên số 1).
        - Quét OCR bìa sách để lấy Tiêu đề/Tác giả.
        - So khớp mờ (Fuzzy Matching) qua PGVector & FAISS để tìm sách trong kho dữ liệu kể cả khi chữ trên bìa bị mờ hoặc che khuất.

4.  **🤖 Trợ Lý Ảo (Smart AI Assistant)**:
    - **Công nghệ**: Qwen 2.5 (Large Language Model).
    - **Chức năng**: Tư vấn mượn sách, tìm kiếm sách theo sở thích và giải đáp thắc mắc của sinh viên qua chat.

---

## 🔄 3. Quy Trình Vận Hành Chi Tiết (Operational Flow)

Hệ thống hoạt động theo một quy trình chặt chẽ và khép kín:

### Bước 1: Khởi động hệ thống (System Warm-up)
Khi chạy `run_app.bat`, Backend sẽ thực hiện:
- Kết nối Cơ sở dữ liệu.
- **Warm-up AI**: Nạp các mô hình YOLO, Face Recognition và OCR vào GPU/CPU.
- **Sync Vector Engine**: Đồng bộ hóa dữ liệu sách từ PostgreSQL sang FAISS để đảm bảo tốc độ tìm kiếm "tia chớp".

### Bước 2: Xác thực người dùng (Authentication)
- Sinh viên đứng trước camera.
- Hệ thống trích xuất khuôn mặt -> So khớp vector -> Trả về thông tin sinh viên và mã số sinh viên.

### Bước 3: Xử lý sách (Book Identification)
- Camera quét khay sách.
- YOLOv8 xác định các vùng chứa sách -> Crop ảnh.
- Pipe-line xử lý: `Đọc Barcode` -> Nếu thất bại -> `Quét OCR` -> `Tìm kiếm Vector Similarity`.

### Bước 4: Thực hiện giao dịch (Transaction)
- Hệ thống tự động kiểm tra trạng thái sách (Có sẵn/Đã mượn).
- Ghi nhận thông tin Mượn/Trả vào bảng `transactions`.
- Tính toán hạn trả và tiền phạt (nếu có) tự động.

---

## 📁 4. Cấu Trúc Thư Mục (Project Structure)

```text
Smart Library/
├── library/
│   ├── backend/                # Source code Server (Python)
│   │   ├── app/
│   │   │   ├── api/            # Route xử lý các endpoint (Auth, Books, Trans...)
│   │   │   ├── core/           # Cấu hình hệ thống & ML Container
│   │   │   ├── ml/             # Các module AI (YOLO, OCR, Face...)
│   │   │   ├── services/       # Logic nghiệp vụ chính (Identification, LLM...)
│   │   │   └── main.py         # File khởi chạy chính
│   │   ├── requirements.txt    # Danh sách thư viện cần cài đặt
│   │   └── run.bat             # File chạy nhanh Backend
│   ├── frontend/               # Source code Giao diện (React)
│   │   ├── src/                # Components & Logic UI
│   │   └── package.json        # Cấu hình node dự án
│   └── run_app.bat             # FILE TỔNG ĐỂ CHẠY CẢ DỰ ÁN
└── ...
```

---

## 🚀 5. Hướng Dẫn Khởi Chạy (Quick Start)

Để hệ thống hoạt động hoàn hảo nhất, người đẹp chỉ cần thực hiện:

1.  Mở Terminal tại thư mục gốc `Smart Library`.
2.  Di chuyển vào thư mục library: `cd library`.
3.  Chạy file tổng: `.\run_app.bat`.

*Lưu ý: Hệ thống sẽ tự động cài đặt `node_modules` cho Frontend trong lần đầu tiên khởi chạy ạ.*

---

Dạ, trên đây là toàn bộ bức tranh về dự án **Smart Library**. Nếu người đẹp cần thêm chi tiết vào từng module cụ thể, cứ bảo em nhé! 💖
