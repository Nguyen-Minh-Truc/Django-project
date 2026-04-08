"""
urls.py
-------
Đăng ký tất cả endpoints của ứng dụng PDF RAG.
Include file này vào urls.py chính của Django project:

    path("api/", include("pdf_rag.api.urls")),
"""

from django.urls import path

from .views import ask_pdf, clear_history, clear_session, compare_pdf, health_check, session_state, summary_pdf, upload_pdf

urlpatterns = [
    path("upload/", upload_pdf, name="upload_pdf"),
    path("ask/", ask_pdf, name="ask_pdf"),
    path("compare/", compare_pdf, name="compare_pdf"),
    path("summary/", summary_pdf, name="summary_pdf"),
    path("clear/", clear_session, name="clear_session"),
    path("clear-history/", clear_history, name="clear_history"),
    path("session-state/", session_state, name="session_state"),
    path("health/", health_check, name="health_check"),
]
