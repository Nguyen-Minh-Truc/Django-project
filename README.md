## 🚀 PDF QA App - Setup & Run Guide

### Prerequisites

- Python 3.10+
- Ollama chạy: `ollama serve`
- Model Qwen2.5 đã pull: `ollama pull qwen2.5:1.5b`
- Virtual environment created: `venv/`

### Project Structure

```
project/
├── core/                    # Business logic (PDF, LLM, session management)
├── myapp/                   # Django project
│   ├── manage.py
│   ├── myapp/settings.py
│   └── app/                 # Django REST app (views, urls)
├── app.py                   # Streamlit frontend
└── requirements.txt
```

### 🎯 How to Run

#### Option 1: Run Backend & Frontend Separately (for development)

**Terminal 1 - Django Backend:**

```bash
cd /path/to/project
source venv/bin/activate
cd myapp
python manage.py runserver 0.0.0.0:8000
# Backend runs on http://localhost:8000/api
```

**Terminal 2 - Streamlit Frontend:**

```bash
cd /path/to/project
source venv/bin/activate
streamlit run app.py
# Frontend runs on http://localhost:8501
```

### 🔌 API Endpoints

Once backend is running on `http://localhost:8000/api`:

- `POST /api/upload/` - Upload PDF
- `POST /api/ask/` - Ask question about PDF
- `POST /api/summary/` - Get PDF summary
- `DELETE /api/clear/` - Clear session
- `GET /api/health/` - Check system health

### 📝 Testing Django

```bash
source ../venv/bin/activate
python manage.py check       # Check configuration
python manage.py migrate    # Apply migrations (if needed)
python manage.py shell      # Interactive shell to test imports
```

### ⚠️ Troubleshooting

**"ModuleNotFoundError: No module named 'core'"**

- Make sure `core/` directory exists at project root
- Verify `sys.path` includes project root in manage.py, wsgi.py, asgi.py
- Check PYTHONPATH is set correctly when running

**"No module named 'app.urls'; 'app' is not a package"**

- Verify `myapp/app/__init__.py` exists
- Check 'app' is in INSTALLED_APPS in settings.py

**Ollama connection error**

- Run `ollama serve` in another terminal
- Verify model exists: `ollama list` (should show qwen2.5:1.5b)
- Check port 11434 is accessible

**Streamlit can't reach backend**

- Verify Django is running on http://localhost:8000
- Check BASE_URL in app.py is correct
- Look at Streamlit logs for connection details

### 🧪 Manual API Testing

```bash
# Upload PDF
curl -X POST -F "file=@document.pdf" http://localhost:8000/api/upload/

# Ask question
curl -X POST -H "Content-Type: application/json" \
  -d '{"query":"What is this document about?"}' \
  http://localhost:8000/api/ask/

# Get summary
curl -X POST http://localhost:8000/api/summary/

# Health check
curl http://localhost:8000/api/health/

# Clear session
curl -X DELETE http://localhost:8000/api/clear/
```

### 📦 Install Dependencies (if needed)

```bash
pip install -r requirements.txt
```

Key packages:

- Django 5.2.10
- djangorestframework
- langchain-community
- ollama
- pypdf
- streamlit
- requests
