# RAG Document Chat

Ứng dụng hỏi đáp tài liệu dùng `Django + Streamlit + LangChain + Ollama`.

Project hiện hỗ trợ:

- Upload và xử lý `PDF`
- Upload và xử lý `DOCX`
- Hỏi đáp nhiều lượt trên cùng tài liệu
- Tóm tắt tài liệu
- Lưu lịch sử chat theo session
- Lưu từng cuộc hội thoại thành thread riêng ở frontend
- Xóa lịch sử chat
- Xóa tài liệu đã upload khỏi vector store

## Công nghệ sử dụng

- `Django 5`
- `Django REST Framework`
- `Streamlit`
- `LangChain`
- `FAISS`
- `Ollama`
- `pypdf`
- `python-docx`

## Cấu trúc thư mục

```text
project/
├── app.py
├── requirements.txt
├── conversation_threads.json
├── RAG-CORAG/
│   ├── manage.py
│   ├── myapp/
│   │   ├── settings.py
│   │   ├── urls.py
│   │   ├── asgi.py
│   │   └── wsgi.py
│   └── app/
│       ├── views.py
│       ├── urls.py
│       ├── apps.py
│       └── core/
│           ├── dependencies.py
│           ├── exceptions.py
│           ├── pdf_service.py
│           ├── prompts.py
│           └── session_store.py
```

## Yêu cầu trước khi chạy

- Python `3.10+`
- Đã tạo virtual environment `venv`
- Ollama đang chạy:

```bash
ollama serve
```

- Đã pull model:

```bash
ollama pull qwen2.5:1.5b
```

## Cài thư viện

```bash
source venv/bin/activate
pip install -r requirements.txt
```

Nếu muốn dùng `DOCX`, cần có:

```bash
pip install python-docx
```

## Cách chạy

Mở 2 terminal riêng.

### Terminal 1: chạy Django backend

```bash
source venv/bin/activate
cd RAG-CORAG
python manage.py runserver
```

Backend chạy tại:

```text
http://localhost:8000/api
```

### Terminal 2: chạy Streamlit frontend

```bash
cd /Users/nguyenminhtruc/Desktop/WorkSpace/SGU/SGU_HK2_25-26/OpenSource/project
source venv/bin/activate
streamlit run app.py
```

Frontend chạy tại:

```text
http://localhost:8501
```

## Luồng sử dụng

1. Mở frontend Streamlit
2. Upload `PDF` hoặc `DOCX`
3. Đợi hệ thống tạo vector store
4. Nhập câu hỏi trong khung chat
5. Xem câu trả lời ngay trên giao diện
6. Có thể hỏi tiếp nhiều câu trên cùng tài liệu
7. Có thể bấm `xoá lịch sử`
8. Có thể bấm `xoá tài liệu đang upload`

## Các API endpoint

- `POST /api/upload/`
  - Upload tài liệu và tạo vector store
  - Hỗ trợ `pdf`, `docx`

- `POST /api/ask/`
  - Hỏi đáp trên tài liệu đã upload

- `POST /api/summary/`
  - Tóm tắt tài liệu hiện tại

- `DELETE /api/clear/`
  - Xóa tài liệu đã upload khỏi session hiện tại

- `DELETE /api/clear-history/`
  - Xóa toàn bộ lịch sử chat trong session hiện tại

- `GET /api/session-state/`
  - Lấy metadata tài liệu và lịch sử chat hiện tại

- `GET /api/health/`
  - Kiểm tra trạng thái API và Ollama

## Kiểm tra nhanh backend

```bash
cd RAG-CORAG
python manage.py check
python manage.py test
```

## Test API thủ công

### Upload file

```bash
curl -X POST -F "file=@document.pdf" http://localhost:8000/api/upload/
```

### Hỏi tài liệu

```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{"query":"Tài liệu này nói về gì?"}' \
  http://localhost:8000/api/ask/
```

### Tóm tắt tài liệu

```bash
curl -X POST http://localhost:8000/api/summary/
```

### Xóa lịch sử chat

```bash
curl -X DELETE http://localhost:8000/api/clear-history/
```

### Xóa tài liệu hiện tại

```bash
curl -X DELETE http://localhost:8000/api/clear/
```

## Các lỗi thường gặp

### `ModuleNotFoundError: No module named 'docx'`

Nguyên nhân: môi trường chưa cài `python-docx`.

Khắc phục:

```bash
source venv/bin/activate
pip install python-docx
```

### `Bad Request: /api/ask/`

Nguyên nhân thường gặp:

- chưa upload tài liệu trước
- session cookie không được giữ giữa các request

Trong frontend hiện tại, app đã dùng chung `requests.Session()` để giữ session backend.

### Không kết nối được Ollama

Kiểm tra:

```bash
ollama serve
ollama list
```

Model mặc định đang dùng là:

```text
qwen2.5:1.5b
```

### LangChain cảnh báo deprecated `Ollama`

Đây là warning, chưa làm app hỏng. Hệ thống vẫn chạy được bình thường.

## Ghi chú hiện tại

- Phần `chunk_size` và `chunk_overlap` vẫn được backend hỗ trợ, nhưng đang được ẩn khỏi UI.
- Lịch sử hội thoại hiện được lưu thành thread ở file `conversation_threads.json`.
- Lịch sử hỏi đáp trong backend vẫn được lưu theo `session`.
