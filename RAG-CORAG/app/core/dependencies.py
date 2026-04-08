"""
dependencies.py
---------------
Singleton / cached heavy objects (embeddings model, LLM).
Load một lần duy nhất khi server khởi động, tái sử dụng cho mọi request.
"""

import logging
import socket
from functools import lru_cache
from urllib.parse import urlparse

import requests
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.llms import Ollama

from .exceptions import OllamaConnectionError, OllamaTimeoutError

logger = logging.getLogger(__name__)

OLLAMA_BASE_URL = "http://localhost:11434"
OLLAMA_MODEL = "qwen2.5:1.5b"
OLLAMA_TIMEOUT_SECONDS = 60


# ------------------------------------------------------------------ #
#  Ollama health check                                                #
# ------------------------------------------------------------------ #
def check_ollama_health() -> None:
    """
    Kiểm tra Ollama đang chạy và model đã được pull.
    Gọi trước khi invoke LLM để trả về lỗi rõ ràng thay vì timeout mù.

    Raises:
        OllamaConnectionError — Ollama chưa chạy hoặc không kết nối được
        OllamaConnectionError — Model chưa được pull
    """
    # 1. Kiểm tra server có chạy không (ping TCP đơn giản)
    parsed = urlparse(OLLAMA_BASE_URL)
    host, port = parsed.hostname, parsed.port or 80
    try:
        with socket.create_connection((host, port), timeout=3):
            pass
    except (ConnectionRefusedError, socket.timeout, OSError) as e:
        raise OllamaConnectionError(
            f"Không kết nối được Ollama tại {OLLAMA_BASE_URL}. "
            "Hãy chạy lệnh: ollama serve"
        ) from e

    # 2. Kiểm tra model đã pull chưa
    try:
        resp = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
        resp.raise_for_status()
        models = [m["name"] for m in resp.json().get("models", [])]
        # So sánh tên model (bỏ tag :latest nếu có)
        base_model = OLLAMA_MODEL.split(":")[0]
        if not any(base_model in m for m in models):
            raise OllamaConnectionError(
                f"Model '{OLLAMA_MODEL}' chưa được pull. "
                f"Hãy chạy: ollama pull {OLLAMA_MODEL}\n"
                f"Các model hiện có: {', '.join(models) or '(trống)'}"
            )
    except requests.RequestException as e:
        raise OllamaConnectionError(
            f"Không truy vấn được danh sách model từ Ollama: {e}"
        ) from e


# ------------------------------------------------------------------ #
#  Singletons                                                         #
# ------------------------------------------------------------------ #
@lru_cache(maxsize=1)
def get_embeddings() -> HuggingFaceEmbeddings:
    """
    Load HuggingFace embeddings model một lần duy nhất (~300 MB).
    lru_cache đảm bảo không bao giờ load lại.
    """
    logger.info("Loading HuggingFace embeddings model (lần đầu có thể mất vài giây)...")
    return HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    )


@lru_cache(maxsize=1)
def get_llm() -> Ollama:
    """
    Khởi tạo Ollama LLM một lần.
    Nếu cần swap model, chỉ sửa OLLAMA_MODEL ở trên.
    """
    return Ollama(
        model=OLLAMA_MODEL,
        base_url=OLLAMA_BASE_URL,
        timeout=OLLAMA_TIMEOUT_SECONDS,
    )