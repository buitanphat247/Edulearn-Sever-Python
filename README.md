# EduLearn AI Python Server 🚀

## 📌 Tổng quan dự án (Project Overview)
**EduLearn AI Python Server** là hạ tầng Backend chuyên biệt xử lý các tác vụ AI phức tạp cho hệ sinh thái EduLearn. Server được xây dựng trên Flask, đóng vai trò là "bộ não" AI, xử lý các tác vụ nặng về tính toán mà Server NestJS chính không đảm nhận.

---

## 🛠 Luồng hoạt động chính (Core Activity Flows)

### 1. Quy trình tạo đề thi AI (RAG Pipeline)
Hệ thống sử dụng kỹ thuật **Retrieval-Augmented Generation (RAG)** để đảm bảo đề thi bám sát nội dung tài liệu của giáo viên.

```mermaid
sequenceDiagram
    participant T as Giáo viên
    participant P as Python Server
    participant DB as MySQL Database
    participant AI as OpenAI/LLM
    
    T->>P: Tải file .docx/.pdf
    P->>P: Trích xuất văn bản (Text Extraction)
    P->>P: Chia nhỏ văn bản (Semantic Chunking)
    P->>DB: Lưu các Chunks vào RagChunk
    T->>P: Yêu cầu tạo đề (Topic, Độ khó, Số câu)
    P->>DB: Tìm kiếm văn bản liên quan (Retrieval)
    DB-->>P: Danh sách Chunks phù hợp
    P->>AI: Gửi Context + Prompt tạo câu hỏi
    AI-->>P: Trả về JSON (Questions, Answers, Explanations)
    P->>DB: Lưu vào RagQuestion & RagTest
    P-->>T: Trả về ID đề thi hoàn chỉnh
```

### 2. Hệ thống giám sát thi cử Real-time (Anti-Cheat)
Sử dụng **Socket.IO** để duy trì kết nối liên tục giữa Client và Server nhằm phát hiện gian lận ngay lập tức.

```mermaid
sequenceDiagram
    participant S as Học sinh
    participant P as Python Server
    participant DB as MySQL Database
    
    S->>P: Start Attempt (HTTP POST)
    P->>DB: Kiểm tra max_attempts & Init phiên
    P-->>S: OK + attempt_id
    S->>P: Kết nối Socket (Join Room: attempt_id)
    Note over S,P: Quá trình làm bài
    S->>P: Phát hiện Chuyển tab / Thoát Fullscreen (Socket Event)
    P->>DB: Ghi log vi phạm vào RagTestAttemptSecurity
    S->>P: Submit bài thi (HTTP POST)
    P->>DB: Tính điểm & Đóng phiên làm bài
    P-->>S: Kết quả cuối cùng
```

### 3. Số hóa tài liệu Word (Digitalization)
Quy trình chuyển đổi tài liệu thô sang cấu hình hệ thống (Structured Data).

```mermaid
sequenceDiagram
    participant A as Admin
    participant P as Python Server
    participant R2 as Cloudflare R2
    
    A->>P: Gửi file Word phức tạp (Toán, Hình ảnh, Bảng)
    P->>P: Phân tích cấu trúc (AST Parsing)
    P->>P: Trích xuất hình ảnh (Media Extraction)
    P->>R2: Upload ảnh lên Cloud Storage
    R2-->>P: URL ảnh công khai
    P->>P: AI-OCR nhận diện công thức Toán (LaTeX)
    P->>P: Chuyển đổi định dạng bảng lồng nhau
    P-->>A: Trả về JSON Schema chuẩn 100%
```

---

## 🛡 Kiến trúc Bảo mật chi tiết (Security Deep-Dive)

### 1. Tầng Giao thức (Protocol Level)
*   **Secure Filename:** Sử dụng `werkzeug.utils.secure_filename` để ngăn chặn tấn công chèn mã lệnh qua tên file.
*   **CORS Management:** Chỉ cho phép các Domain được cấu hình trong `CORS_ORIGINS` truy cập vào tài nguyên AI nhạy cảm.

### 2. Tầng Ứng dụng (Application Level)
*   **Transaction Integrity:** Các thao tác tạo đề thi phức tạp được bao bọc trong Transaction. Nếu AI lỗi giữa chừng, hệ thống tự động Rollback dữ liệu trong Database.
*   **Rate Limiting:** (Thiết kế dựa trên khả năng chịu tải của API LLM) Ngăn chặn việc spam yêu cầu tạo nội dung AI liên tục làm cạn kiệt Token.

### 3. Tầng Dữ liệu & AI (Data & AI Security)
*   **SQL Parameterization:** Tuyệt đối không cộng chuỗi SQL. Mọi thao tác đều qua `DatabaseService` với placeholder `%s`.
*   **Prompt Shielding:** Các Prompt gửi lên AI được thiết kế để "Grounding" (ép AI chỉ trả về nội dung dựa trên tài liệu đã có), hạn chế tình trạng AI bị dắt mũi (Hallucination).

---

## 📄 Danh mục API trọng tâm (Key API Reference)

| Endpoint | Method | Chức năng | Security |
| :--- | :--- | :--- | :--- |
| `/ai-exam/create_test` | POST | Tạo đề thi từ tài liệu (RAG) | Validate Doc Extension |
| `/exams/attempt/start` | POST | Kiểm tra lượt làm nốt/lượt mới | Check Max Attempts |
| `/exams/attempt/log` | POST | Ghi nhật ký vi phạm bảo mật | ID Attempt Validation |
| `/digital-document/process`| POST | Số hóa văn bản sang JSON/LaTeX | Secure IO + R2 Upload |
| `/writing-chat-bot/generate`| POST | AI tạo hội thoại luyện viết | CEFR Level Validation |

---

## ⚙️ Hướng dẫn cài đặt & Chạy (Quick Start)

1.  **Clone & Venv:**
    ```bash
    git clone ...
    cd Edu_Learn_Python_Sever
    python -m venv venv
    source venv/bin/activate
    ```
2.  **Cài đặt Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
3.  **Cấu hình Environment:**
    Copy file `.env.example` thành `.env` và điền đủ thông tin:
    *   `PORT=5000`
    *   `OPENAI_API_KEY`: Key cho GPT-4o.
    *   `CLIENT_API_URL`: URL Server NestJS để đồng bộ dữ liệu.
4.  **Khởi chạy:**
    ```bash
    python main.py
    ```

---

*Biên soạn bởi Antigravity AI - System Architecture Division.*
