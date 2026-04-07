"""
views.py
--------
Django REST Framework views.
Mỗi view chỉ lo orchestration; business logic nằm trong core/.

Error handling map:
  DocumentValidationError   → 400  (client gửi sai)
  DocumentProcessingError   → 422  (file hợp lệ nhưng không xử lý được)
  OllamaConnectionError→ 503  (Ollama chưa chạy / model chưa pull)
  OllamaTimeoutError   → 504  (Ollama quá chậm)
  Exception            → 500  (lỗi không lường trước)
"""

import logging
import socket
from functools import wraps
from typing import Callable

import requests
from rest_framework.decorators import api_view
from rest_framework.request import Request
from rest_framework.response import Response

from .core.dependencies import check_ollama_health, get_llm
from .core.exceptions import (
    DocumentProcessingError,
    DocumentValidationError,
    OllamaConnectionError,
    OllamaTimeoutError,
)
from .core.pdf_service import create_vector_store, get_summary_chunks, load_document, temp_document
from .core.prompts import qa_prompt, summary_prompt
from .core.session_store import registry

logger = logging.getLogger(__name__)
CHAT_HISTORY_KEY = "chat_history"
DOCUMENT_META_KEY = "document_meta"
DEFAULT_CHUNK_SIZE = 1000
DEFAULT_CHUNK_OVERLAP = 100


def _get_chat_history(request: Request) -> list[dict]:
    return list(request.session.get(CHAT_HISTORY_KEY, []))


def _set_chat_history(request: Request, history: list[dict]) -> None:
    request.session[CHAT_HISTORY_KEY] = history
    request.session.modified = True


def _append_chat_history(request: Request, question: str, answer: str) -> list[dict]:
    history = _get_chat_history(request)
    history.append({"question": question, "answer": answer})
    _set_chat_history(request, history)
    return history


def _clear_chat_history(request: Request) -> None:
    request.session[CHAT_HISTORY_KEY] = []
    request.session.modified = True


def _get_document_meta(request: Request) -> dict | None:
    return request.session.get(DOCUMENT_META_KEY)


def _set_document_meta(request: Request, metadata: dict) -> None:
    request.session[DOCUMENT_META_KEY] = metadata
    request.session.modified = True


def _clear_document_meta(request: Request) -> None:
    request.session.pop(DOCUMENT_META_KEY, None)
    request.session.modified = True


def _parse_chunk_params(request: Request) -> tuple[int, int]:
    raw_chunk_size = request.data.get("chunk_size", DEFAULT_CHUNK_SIZE)
    raw_chunk_overlap = request.data.get("chunk_overlap", DEFAULT_CHUNK_OVERLAP)
    try:
        chunk_size = int(raw_chunk_size)
        chunk_overlap = int(raw_chunk_overlap)
    except (TypeError, ValueError) as exc:
        raise DocumentValidationError(
            "chunk_size và chunk_overlap phải là số nguyên."
        ) from exc
    return chunk_size, chunk_overlap


# ------------------------------------------------------------------ #
#  Helper: lấy session id                                             #
# ------------------------------------------------------------------ #
def _get_session_id(request: Request) -> str:
    if not request.session.session_key:
        request.session.create()
    return request.session.session_key


# ------------------------------------------------------------------ #
#  Decorator: bắt tất cả LLM errors tập trung                        #
# ------------------------------------------------------------------ #
def handle_llm_errors(view_func: Callable) -> Callable:
    """
    Decorator wrap các exception của Ollama thành Response chuẩn.
    Dùng cho các view có gọi LLM (ask, summary).
    """
    @wraps(view_func)
    def wrapper(request: Request, *args, **kwargs):
        try:
            return view_func(request, *args, **kwargs)
        except OllamaConnectionError as e:
            logger.error(f"Ollama connection error: {e}")
            return Response(
                {
                    "error": str(e),
                    "hint": (
                        "1. Kiểm tra Ollama đang chạy: ollama serve\n"
                        "2. Kiểm tra model đã pull: ollama pull qwen2.5:1.5b\n"
                        "3. Kiểm tra port 11434 không bị firewall chặn"
                    ),
                },
                status=503,
            )
        except OllamaTimeoutError as e:
            logger.error(f"Ollama timeout: {e}")
            return Response(
                {
                    "error": str(e),
                    "hint": (
                        "Model phản hồi quá chậm. Thử:\n"
                        "1. Dùng model nhỏ hơn (vd: qwen2.5:0.5b)\n"
                        "2. Giảm số chunk (k=2 thay vì k=3)\n"
                        "3. Kiểm tra RAM/CPU đang dùng bao nhiêu"
                    ),
                },
                status=504,
            )
        except Exception as e:
            logger.exception(f"Unexpected error in {view_func.__name__}: {e}")
            return Response(
                {
                    "error": "Lỗi server không mong đợi.",
                    "detail": str(e),
                    "hint": "Xem log server để biết chi tiết. Thử lại sau.",
                },
                status=500,
            )
    return wrapper


# ------------------------------------------------------------------ #
#  Helper: gọi LLM với xử lý timeout và connection error             #
# ------------------------------------------------------------------ #
def _invoke_llm(prompt: str) -> str:
    """
    Gọi LLM, map exception của requests/socket thành custom exceptions.
    Raises OllamaConnectionError hoặc OllamaTimeoutError.
    """
    check_ollama_health()   # kiểm tra trước khi invoke
    try:
        llm = get_llm()
        return llm.invoke(prompt)
    except requests.exceptions.ConnectionError as e:
        raise OllamaConnectionError(
            "Mất kết nối tới Ollama trong khi đang xử lý. "
            "Kiểm tra 'ollama serve' vẫn còn chạy."
        ) from e
    except (requests.exceptions.Timeout, TimeoutError, socket.timeout) as e:
        raise OllamaTimeoutError(
            "Ollama không trả lời trong thời gian cho phép. "
            "Context có thể quá dài hoặc máy đang quá tải."
        ) from e


# ------------------------------------------------------------------ #
#  POST /api/upload/                                                  #
# ------------------------------------------------------------------ #
@api_view(["POST"])
def upload_pdf(request: Request) -> Response:
    """
    Upload và index tài liệu cho session hiện tại.
    Body: multipart/form-data với field 'file'.
    """
    if "file" not in request.FILES:
        return Response(
            {
                "error": "Thiếu field 'file' trong request.",
                "hint": "Gửi request dạng multipart/form-data với key là 'file'.",
            },
            status=400,
        )

    uploaded_file = request.FILES["file"]
    session_id = _get_session_id(request)

    try:
        chunk_size, chunk_overlap = _parse_chunk_params(request)
        with temp_document(uploaded_file) as path:
            text = load_document(path)

        vector_store = create_vector_store(
            text,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )
        registry.set(session_id, vector_store)
        _clear_chat_history(request)
        _set_document_meta(
            request,
            {
                "file_name": uploaded_file.name,
                "file_type": uploaded_file.name.rsplit(".", 1)[-1].lower(),
                "chunk_size": chunk_size,
                "chunk_overlap": chunk_overlap,
            },
        )

        return Response(
            {
                "message": "Upload thành công! Bạn có thể đặt câu hỏi.",
                "document": _get_document_meta(request),
                "chat_history": _get_chat_history(request),
            }
        )

    except DocumentValidationError as e:
        logger.warning(f"[{session_id}] Validation failed: {e}")
        return Response(
            {
                "error": str(e),
                "hint": (
                    "Kiểm tra:\n"
                    "• File có đuôi .pdf hoặc .docx và thực sự đúng định dạng\n"
                    "• Kích thước file < 50 MB\n"
                    "• PDF không bị bảo vệ bằng mật khẩu"
                ),
            },
            status=400,
        )

    except DocumentProcessingError as e:
        logger.warning(f"[{session_id}] Processing failed: {e}")
        return Response(
            {
                "error": str(e),
                "hint": (
                    "Nếu tài liệu không đọc được, hãy thử:\n"
                    "• Dùng Adobe Acrobat → 'Recognize Text'\n"
                    "• Với DOCX, mở lại bằng Word và Save As một bản mới\n"
                    "• Hoặc dùng công cụ online: smallpdf.com, ilovepdf.com\n"
                    "• Hoặc chạy: ocrmypdf input.pdf output.pdf"
                ),
            },
            status=422,
        )

    except Exception as e:
        logger.exception(f"[{session_id}] Upload unexpected error: {e}")
        return Response(
            {
                "error": "Lỗi server không mong đợi khi xử lý PDF.",
                "detail": str(e),
                "hint": "Thử lại. Nếu vẫn lỗi, xem log server để biết thêm.",
            },
            status=500,
        )


# ------------------------------------------------------------------ #
#  POST /api/ask/                                                     #
# ------------------------------------------------------------------ #
@api_view(["POST"])
@handle_llm_errors
def ask_pdf(request: Request) -> Response:
    """
    Hỏi đáp dựa trên PDF đã upload.
    Body JSON: { "query": "câu hỏi của bạn" }
    """
    query = request.data.get("query", "").strip()
    if not query:
        return Response(
            {"error": "Field 'query' không được rỗng."},
            status=400,
        )

    session_id = _get_session_id(request)
    vector_store = registry.get(session_id)

    if vector_store is None:
        return Response(
            {
                "error": "Chưa có PDF nào được upload trong session này.",
                "hint": "Gọi POST /api/upload/ trước với file PDF.",
            },
            status=400,
        )

    docs = vector_store.similarity_search(query, k=3)
    if not docs:
        return Response(
            {"answer": "Không tìm thấy nội dung liên quan trong tài liệu."}
        )

    context = "\n\n".join(doc.page_content for doc in docs)
    answer = _invoke_llm(qa_prompt(context, query))
    history = _append_chat_history(request, query, answer)
    return Response(
        {
            "answer": answer,
            "chat_history": history,
            "document": _get_document_meta(request),
        }
    )


# ------------------------------------------------------------------ #
#  POST /api/summary/                                                 #
# ------------------------------------------------------------------ #
@api_view(["POST"])
@handle_llm_errors
def summary_pdf(request: Request) -> Response:
    """
    Tóm tắt nội dung PDF đã upload.
    """
    session_id = _get_session_id(request)
    vector_store = registry.get(session_id)

    if vector_store is None:
        return Response(
            {
                "error": "Chưa có PDF nào được upload trong session này.",
                "hint": "Gọi POST /api/upload/ trước với file PDF.",
            },
            status=400,
        )

    context = get_summary_chunks(vector_store, top_k=5)
    result = _invoke_llm(summary_prompt(context))
    history = _append_chat_history(
        request,
        "Tóm tắt tài liệu",
        result,
    )
    return Response(
        {
            "summary": result,
            "chat_history": history,
            "document": _get_document_meta(request),
        }
    )


# ------------------------------------------------------------------ #
#  GET /api/health/                                                   #
# ------------------------------------------------------------------ #
@api_view(["GET"])
def health_check(request: Request) -> Response:
    """
    Kiểm tra trạng thái toàn bộ hệ thống.
    Frontend có thể ping endpoint này để hiển thị trạng thái.
    """
    status_report = {
        "api": "ok",
        "ollama": "unknown",
        "model": "unknown",
    }

    try:
        check_ollama_health()
        status_report["ollama"] = "ok"
        status_report["model"] = "ok"
        return Response(status_report, status=200)
    except OllamaConnectionError as e:
        error_msg = str(e)
        if "model" in error_msg.lower():
            status_report["ollama"] = "ok"
            status_report["model"] = "not_found"
        else:
            status_report["ollama"] = "unreachable"
        return Response(
            {**status_report, "error": error_msg},
            status=503,
        )


# ------------------------------------------------------------------ #
#  DELETE /api/clear/                                                 #
# ------------------------------------------------------------------ #
@api_view(["DELETE"])
def clear_session(request: Request) -> Response:
    """
    Xóa vector store của session hiện tại (reset để upload PDF mới).
    """
    session_id = _get_session_id(request)
    registry.delete(session_id)
    _clear_document_meta(request)
    return Response({"message": "Đã xóa tài liệu đã upload của session."})


@api_view(["DELETE"])
def clear_history(request: Request) -> Response:
    """
    Xóa lịch sử hỏi đáp trong session hiện tại.
    """
    _clear_chat_history(request)
    return Response({"message": "Đã xóa toàn bộ lịch sử chat."})


@api_view(["GET"])
def session_state(request: Request) -> Response:
    """
    Trả về metadata tài liệu và lịch sử chat của session hiện tại.
    """
    return Response(
        {
            "document": _get_document_meta(request),
            "chat_history": _get_chat_history(request),
        }
    )
