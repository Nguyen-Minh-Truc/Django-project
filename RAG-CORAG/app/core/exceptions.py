"""
exceptions.py
-------------
Custom exceptions để phân loại lỗi rõ ràng.
Mỗi loại lỗi → HTTP status code và message riêng.
"""


class DocumentValidationError(ValueError):
    """
    File không hợp lệ trước khi xử lý.
    → HTTP 400
    Vd: sai định dạng, quá lớn, file rỗng, bị mã hóa.
    """
    pass


class DocumentProcessingError(RuntimeError):
    """
    Lỗi trong quá trình đọc / tách chunks / embed.
    → HTTP 422
    Vd: PDF là ảnh scan (không có text layer), bị corrupt.
    """
    pass


class OllamaConnectionError(RuntimeError):
    """
    Không kết nối được Ollama hoặc model chưa được pull.
    → HTTP 503
    Vd: Ollama chưa chạy, model không tồn tại.
    """
    pass


class OllamaTimeoutError(RuntimeError):
    """
    Ollama phản hồi quá chậm / quá thời gian chờ.
    → HTTP 504
    Vd: model quá nặng so với RAM, context quá dài.
    """
    pass


# Backward-compatible aliases for the rest of the codebase.
PDFValidationError = DocumentValidationError
PDFProcessingError = DocumentProcessingError
