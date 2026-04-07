"""
dependencies.py
---------------
Singleton / cached heavy objects (embeddings model, LLM).
Load một lần duy nhất khi server khởi động, tái sử dụng cho mọi request.
"""

from functools import lru_cache

from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.llms import Ollama


@lru_cache(maxsize=1)
def get_embeddings() -> HuggingFaceEmbeddings:
    """
    Load HuggingFace embeddings model một lần duy nhất (~300 MB).
    lru_cache đảm bảo không bao giờ load lại.
    """
    return HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    )


@lru_cache(maxsize=1)
def get_llm() -> Ollama:
    """
    Khởi tạo Ollama LLM một lần.
    Nếu cần swap model, chỉ sửa ở đây.
    """
    return Ollama(model="qwen2.5:1.5b")