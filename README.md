# EduLearn AI Python Server 🚀

## 📌 Tổng quan dự án (Project Overview)
**EduLearn AI Python Server** là hạ tầng Backend chuyên biệt xử lý các tác vụ AI phức tạp cho hệ sinh thái EduLearn. Server được xây dựng trên ngôn ngữ Python (Flask) để tận dụng tối đa các thư viện xử lý ngôn ngữ tự nhiên (NLP), OCR và LLM.

Các nhiệm vụ chính:
1.  **AI Exam Generation (RAG):** Tự động tạo đề thi trắc nghiệm từ tài liệu người dùng tải lên.
2.  **Intelligent Writing Chatbot:** Gia sư AI hỗ trợ học sinh luyện tập kỹ năng viết qua hội thoại tương tác.
3.  **Digital Document Processing:** Chuyển đổi tài liệu Word (.docx) sang định dạng JSON/LaTeX chất lượng cao.
4.  **Real-time Anti-cheat System:** Hệ thống giám sát thi cử qua Socket.IO.

---

## 🛠 Pipeline & Quy trình thực hiện (System Pipeline)

### 1. Luồng tạo đề thi AI (RAG Pipeline)
*   **Bước 1 (Extraction):** Trích xuất văn bản từ file `.docx` hoặc `.pdf`.
*   **Bước 2 (Splitting):** Chia nhỏ văn bản thành các *Semantic Chunks* (đoạn nhỏ có nghĩa).
*   **Bước 3 (Indexing):** Lưu trữ các đoạn văn bản vào cơ sở dữ liệu (Database-based Indexing).
*   **Bước 4 (Retrieval):** Tìm kiếm các đoạn văn bản liên quan nhất dựa trên yêu cầu đề thi (chủ đề, độ khó).
*   **Bước 5 (LLM Processing):** Gửi context thu thập được cho mô hình LLM (GPT-4o/Ollama) để tạo câu hỏi trắc nghiệm, đáp án và giải thích chi tiết.

### 2. Luồng số hóa tài liệu (Digitization Pipeline)
*   **Word to Structure:** Phân tích cấu trúc file Word (Headings, Tables, Lists).
*   **AI-OCR:** Sử dụng mô hình AI nhận diện công thức toán học (LaTeX) và các bảng lồng nhau.
*   **Media Management:** Tự động tách hình ảnh, đẩy lên Cloudflare R2 và thay thế bằng URL công khai.
*   **Final Output:** Xuất ra file JSON chuẩn để đẩy vào hệ thống CMS của NestJS.

---

## 🛡 Bảo mật chi tiết (Security Architecture)

Dự án được thiết kế với nhiều tầng bảo mật để đảm bảo an toàn dữ liệu và tính minh bạch trong thi cử:

### A. Bảo mật API & Dữ liệu
*   **Sanitization:** Tất cả file tải lên được kiểm tra định dạng nghiêm ngặt và xử lý tên file qua `secure_filename` để chống tấn công **Path Traversal**.
*   **SQL Injection Prevention:** Sử dụng parameterized queries cho tất cả các tương tác với MySQL qua lớp `DatabaseService`.
*   **Environment Isolation:** Toàn bộ thông tin nhạy cảm (API Key, DB Credential, R2 Token) được lưu trữ trong `.env` và không bao giờ hard-code.

### B. Bảo mật thi cử (Anti-Cheat Security)
*   **Unique Session ID:** Mỗi lượt làm bài thi được cấp một `attempt_id` duy nhất. Các sự kiện Socket.IO bắt buộc phải đính kèm ID này để xác thực.
*   **Event Logging:** Hệ thống ghi lại mọi hành vi bất thường:
    *   `tab_hidden`: Chuyển tab hoặc rời trình duyệt.
    *   `reload`: Tải lại trang bài làm.
    *   `disconnect`: Mất kết nối mạng.
*   **Server-side Timing:** Thời gian làm bài được quản lý tại Server. Khi hết giờ, Server sẽ tự động đóng kết nối và force-submit bài làm để tránh học sinh gian lận thời gian.

---

## 📄 Danh mục API Chi tiết (Detailed API Reference)

Hệ thống cung cấp tài liệu Swagger (Flasgger) chi tiết tại `/docs`. Dưới đây là mô tả các module chính:

### 1. AI Exam Management (`/api/ai-exam`)
*   `POST /create_test`: Nhận tài liệu và cấu hình để tạo đề thi hoàn chỉnh qua RAG.
*   `GET /tests/class/<class_id>`: Lấy danh sách đề thi của một lớp học, tích hợp thông tin lượt làm bài của học sinh.
*   `GET /test/<test_id>`: Lấy chi tiết đề thi gồm danh sách câu hỏi và cấu hình giới hạn thời gian.

### 2. Exam Attempt & Security (`/api/exams/attempt`)
*   `POST /start`: Khởi tạo phiên làm bài mới, kiểm tra giới hạn lượt làm bài (`max_attempts`).
*   `POST /submit`: Nộp bài, chấm điểm tự động và đóng phiên làm bài.
*   **Socket.IO Events:**
    *   `client_log_event`: Nhận và lưu trữ nhật ký vi phạm từ Client.

### 3. Writing AI Tutor (`/api/writing-chat-bot`)
*   `POST /generate`: Tạo nội dung luyện viết (Dialogue/Essay) bằng AI dựa trên CEFR Level (1-5).
*   `GET /topics`: Trả về danh sách chủ đề luyện tập đa dạng (IELTS, Business, General).
*   `PUT /history/<id>/index`: Lưu vạch tiến độ (checkpoint) của học sinh trong phiên luyện tập.

### 4. Digital Document (`/api/digital-document`)
*   `POST /process`: Endpoint xử lý nặng nhất, thực hiện chuyển đổi Word sang JSON/LaTeX và quản lý media.

---

## ⚙️ Hướng dẫn cài đặt (Setup Guide)

1.  **Cài đặt môi trường:**
    ```bash
    python -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    ```
2.  **Cấu hình biến môi trường (`.env`):**
    ```env
    PORT=5000
    OPENAI_API_KEY=your_key_here
    DB_MYSQL_HOST=localhost
    DB_MYSQL_USER=root
    DB_MYSQL_PASS=123456
    CLOUDFLARE_R2_BUCKET=...
    ```
3.  **Khởi chạy:**
    ```bash
    python main.py
    ```

---

*Tài liệu được biên soạn bởi Antigravity AI cho dự án EduLearn.*
