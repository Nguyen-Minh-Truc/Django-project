"""
session_store.py
----------------
Quản lý FAISS vector store theo session_id.
Mỗi user/session có DB riêng → tránh race condition khi dùng global.
"""

import threading
import logging
from typing import Optional

from langchain_community.vectorstores import FAISS

logger = logging.getLogger(__name__)


class VectorStoreRegistry:
    """
    Thread-safe in-memory registry: session_id → FAISS store.

    Với production thật sự nên thay bằng Redis + ChromaDB persistent,
    nhưng class này đủ dùng cho single-server deployment.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._stores: dict[str, FAISS] = {}

    def set(self, session_id: str, store: FAISS) -> None:
        with self._lock:
            self._stores[session_id] = store
            logger.info(f"[{session_id}] Vector store đã lưu.")

    def get(self, session_id: str) -> Optional[FAISS]:
        with self._lock:
            return self._stores.get(session_id)

    def delete(self, session_id: str) -> None:
        with self._lock:
            self._stores.pop(session_id, None)

    def exists(self, session_id: str) -> bool:
        with self._lock:
            return session_id in self._stores


# Singleton registry dùng chung toàn app
registry = VectorStoreRegistry()