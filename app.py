# app.py
import json
from datetime import datetime
from pathlib import Path
from uuid import uuid4

import requests
import streamlit as st


BASE_URL = "http://localhost:8000/api"
COMPARE_URL = f"{BASE_URL}/compare/"
CHUNK_SIZE_OPTIONS = [500, 1000, 1500, 2000]
CHUNK_OVERLAP_OPTIONS = [50, 100, 200]
DEFAULT_TIMEOUT = 120
THREADS_FILE = Path(__file__).resolve().parent / "conversation_threads.json"

st.set_page_config(page_title="RAG Document Chat", page_icon="📄", layout="wide")


def inject_theme() -> None:
    st.markdown(
        """
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

            :root {
                --primary-color: #007BFF;
                --secondary-color: #FFC107;
                --background-color: #F8F9FA;
                --sidebar-color: #2C2F33;
                --text-color: #212529;
                --sidebar-text-color: #FFFFFF;
            }

            .stApp {
                background:
                    radial-gradient(circle at top left, rgba(0, 123, 255, 0.08), transparent 24%),
                    linear-gradient(180deg, #fbfcfe 0%, var(--background-color) 28%, #f4f6f9 100%);
                font-family: 'Inter', 'Segoe UI', sans-serif;
                color: var(--text-color);
            }

            .block-container {
                padding-top: 1.4rem;
                padding-bottom: 1.6rem;
                max-width: 1400px;
            }

            .stApp h1,
            .stApp h2,
            .stApp h3,
            .stApp h4,
            .stApp h5,
            .stApp h6,
            .stApp p,
            .stApp li,
            .stApp label,
            .stApp span,
            .stApp div {
                color: var(--text-color);
            }

            [data-testid="stSidebar"] {
                background:
                    linear-gradient(180deg, rgba(44, 47, 51, 0.98), rgba(31, 33, 37, 0.98));
                border-right: 1px solid rgba(255, 255, 255, 0.08);
            }

            [data-testid="stSidebar"] h1,
            [data-testid="stSidebar"] h2,
            [data-testid="stSidebar"] h3,
            [data-testid="stSidebar"] h4,
            [data-testid="stSidebar"] h5,
            [data-testid="stSidebar"] h6,
            [data-testid="stSidebar"] p,
            [data-testid="stSidebar"] label,
            [data-testid="stSidebar"] span,
            [data-testid="stSidebar"] div,
            [data-testid="stSidebar"] small {
                color: var(--sidebar-text-color) !important;
            }

            [data-testid="stSidebar"] .stCaption,
            [data-testid="stSidebar"] .stInfo,
            [data-testid="stSidebar"] .stSuccess,
            [data-testid="stSidebar"] .stWarning,
            [data-testid="stSidebar"] .stError {
                color: rgba(255, 255, 255, 0.88) !important;
            }

            [data-testid="stSidebar"] .stFileUploader,
            [data-testid="stSidebar"] .stFileUploader * {
                color: #FFFFFF !important;
            }

            .stButton button {
                border: 1px solid var(--primary-color);
                background: var(--primary-color);
                color: #FFFFFF;
                border-radius: 12px;
                font-weight: 700;
                box-shadow: 0 8px 18px rgba(0, 123, 255, 0.12);
            }

            .stButton button:hover {
                border: 1px solid var(--primary-color);
                background: #0069d9;
                color: #FFFFFF;
            }

            [data-testid="stSidebar"] .stButton button {
                border: 1px solid #e0a800;
                background: var(--secondary-color);
                color: #212529 !important;
                font-weight: 600;
                box-shadow: 0 8px 18px rgba(255, 193, 7, 0.12);
            }

            [data-testid="stSidebar"] .stButton button:hover {
                border: 1px solid #d39e00;
                background: #ffca2c;
                color: #212529 !important;
            }

            a {
                color: var(--primary-color) !important;
            }

            [data-testid="stFileUploaderDropzone"] {
                border-color: rgba(255, 193, 7, 0.8);
                background: rgba(255, 255, 255, 0.06);
                border-radius: 16px;
            }

            .hero-card,
            .panel-card,
            .info-card,
            .empty-card {
                background: rgba(255, 255, 255, 0.9);
                border: 1px solid rgba(15, 23, 42, 0.08);
                border-radius: 22px;
                box-shadow: 0 12px 28px rgba(15, 23, 42, 0.06);
            }

            .hero-card {
                padding: 1.25rem 1.35rem;
                margin-bottom: 1rem;
            }

            .hero-kicker {
                text-transform: uppercase;
                letter-spacing: 0.14em;
                font-size: 0.76rem;
                font-weight: 800;
                color: var(--primary-color);
                margin-bottom: 0.4rem;
            }

            .hero-title {
                font-size: 1.9rem;
                font-weight: 800;
                color: var(--text-color);
                margin: 0 0 0.35rem 0;
            }

            .hero-subtitle {
                color: rgba(33, 37, 41, 0.78);
                font-size: 0.98rem;
                line-height: 1.55;
            }

            .hero-chips {
                display: flex;
                flex-wrap: wrap;
                gap: 0.5rem;
                margin-top: 0.95rem;
            }

            .chip {
                display: inline-flex;
                align-items: center;
                gap: 0.35rem;
                padding: 0.35rem 0.7rem;
                border-radius: 999px;
                background: rgba(0, 123, 255, 0.1);
                color: var(--primary-color);
                font-size: 0.78rem;
                font-weight: 700;
            }

            .metric-card {
                background: rgba(255, 255, 255, 0.88);
                border: 1px solid rgba(15, 23, 42, 0.08);
                border-radius: 18px;
                padding: 0.85rem 1rem;
                box-shadow: 0 10px 22px rgba(15, 23, 42, 0.05);
            }

            .metric-label {
                font-size: 0.74rem;
                text-transform: uppercase;
                letter-spacing: 0.08em;
                color: rgba(33, 37, 41, 0.7);
                font-weight: 700;
                margin-bottom: 0.2rem;
            }

            .metric-value {
                font-size: 1.05rem;
                font-weight: 800;
                color: var(--text-color);
            }

            .section-title {
                font-size: 1.02rem;
                font-weight: 800;
                color: var(--text-color);
                margin: 0 0 0.65rem 0;
            }

            .panel-card {
                padding: 1rem 1rem 0.9rem 1rem;
                margin-bottom: 1rem;
            }

            .panel-head {
                display: flex;
                align-items: center;
                justify-content: space-between;
                margin-bottom: 0.8rem;
            }

            .panel-badge {
                display: inline-flex;
                align-items: center;
                padding: 0.28rem 0.65rem;
                border-radius: 999px;
                font-size: 0.72rem;
                font-weight: 800;
                letter-spacing: 0.04em;
                text-transform: uppercase;
            }

            .badge-rag {
                background: rgba(0, 123, 255, 0.12);
                color: var(--primary-color);
            }

            .badge-corag {
                background: rgba(255, 193, 7, 0.2);
                color: #7a5a00;
            }

            .insight-card {
                background: rgba(255, 255, 255, 0.9);
                border: 1px solid rgba(15, 23, 42, 0.08);
                border-radius: 22px;
                box-shadow: 0 12px 28px rgba(15, 23, 42, 0.06);
                padding: 1rem;
                margin-bottom: 1rem;
            }

            .insight-title {
                font-size: 0.74rem;
                text-transform: uppercase;
                letter-spacing: 0.12em;
                color: var(--primary-color);
                font-weight: 800;
                margin-bottom: 0.35rem;
            }

            .insight-body {
                color: var(--text-color);
                line-height: 1.6;
                font-size: 0.95rem;
            }

            .empty-card {
                padding: 1rem;
                color: rgba(33, 37, 41, 0.78);
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_header() -> None:
    document = st.session_state.document_meta
    document_name = document.get("file_name", "Chưa có tài liệu") if document else "Chưa có tài liệu"
    mode_text = "Compare RAG / CO-Rag" if st.session_state.compare_mode else "RAG only"
    thread_count = len(st.session_state.conversation_threads)
    chat_count = len(st.session_state.chat_history)

    st.markdown(
        f"""
        <div class="hero-card">
            <div class="hero-kicker">Document Intelligence Workspace</div>
            <div class="hero-title">Conversational RAG</div>
            <div class="hero-subtitle">
                Giao diện so sánh câu trả lời theo thời gian thực giữa RAG và CO-Rag,
                tối ưu cho demo và đánh giá chất lượng phản hồi trên cùng một câu hỏi.
            </div>
            <div class="hero-chips">
                <span class="chip">{mode_text}</span>
                <span class="chip">{document_name}</span>
                <span class="chip">{thread_count} threads</span>
                <span class="chip">{chat_count} messages</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )




def get_backend_session() -> requests.Session:
    if "backend_session" not in st.session_state:
        st.session_state.backend_session = requests.Session()
    return st.session_state.backend_session


def load_threads() -> list[dict]:
    if not THREADS_FILE.exists():
        return []

    try:
        data = json.loads(THREADS_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []

    return data if isinstance(data, list) else []


def save_threads() -> None:
    THREADS_FILE.write_text(
        json.dumps(st.session_state.conversation_threads, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def init_state() -> None:
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    if "document_meta" not in st.session_state:
        st.session_state.document_meta = None
    if "vector_store_ready" not in st.session_state:
        st.session_state.vector_store_ready = False
    if "chunk_size" not in st.session_state:
        st.session_state.chunk_size = 1000
    if "chunk_overlap" not in st.session_state:
        st.session_state.chunk_overlap = 100
    if "conversation_threads" not in st.session_state:
        st.session_state.conversation_threads = load_threads()
    if "active_thread_id" not in st.session_state:
        st.session_state.active_thread_id = None
    if "viewing_thread_id" not in st.session_state:
        st.session_state.viewing_thread_id = None
    if "compare_mode" not in st.session_state:
        st.session_state.compare_mode = True
    if "latest_compare" not in st.session_state:
        st.session_state.latest_compare = None


def get_latest_compare_from_history(history: list[dict]) -> dict | None:
    for item in reversed(history):
        if item.get("mode") == "compare":
            return {
                "question": item.get("question", ""),
                "rag_answer": item.get("rag_answer", ""),
                "corag_answer": item.get("corag_answer", ""),
                "rag_chunk_count": item.get("rag_chunk_count", item.get("rag_trace", {}).get("chunk_count", 0)),
                "corag_chunk_count": item.get("corag_chunk_count", item.get("corag_trace", {}).get("chunk_count", 0)),
                "rag_duration_ms": item.get("rag_duration_ms", item.get("rag_trace", {}).get("duration_ms", 0)),
                "corag_duration_ms": item.get("corag_duration_ms", item.get("corag_trace", {}).get("duration_ms", 0)),
                "rag_confidence": item.get("rag_confidence", item.get("rag_trace", {}).get("confidence", 0)),
                "corag_confidence": item.get("corag_confidence", item.get("corag_trace", {}).get("confidence", 0)),
                "corag_queries": item.get("corag_queries", item.get("corag_trace", {}).get("queries", [])),
            }
    return None


def render_compare_panels(compare_payload: dict) -> None:
    rag_answer = compare_payload.get("rag_answer") or "Không có câu trả lời RAG."
    corag_answer = compare_payload.get("corag_answer") or "Không có câu trả lời CO-Rag."

    rag_speed = compare_payload.get("rag_duration_ms", 0)
    corag_speed = compare_payload.get("corag_duration_ms", 0)
    rag_conf = compare_payload.get("rag_confidence", 0)
    corag_conf = compare_payload.get("corag_confidence", 0)
    rag_chunks = compare_payload.get("rag_chunk_count", 0)
    corag_chunks = compare_payload.get("corag_chunk_count", 0)
    corag_queries = compare_payload.get("corag_queries", [])

    st.markdown('<div class="section-title">So sánh realtime: RAG vs CO-Rag</div>', unsafe_allow_html=True)
    col_rag, col_corag = st.columns(2)

    with col_rag:
        st.markdown("#### RAG")
        st.caption(f"Tốc độ: {rag_speed} ms | Độ tin cậy: {rag_conf}% | Chunks: {rag_chunks}")
        st.markdown(rag_answer)

    with col_corag:
        st.markdown("#### CO-Rag")
        st.caption(
            f"Tốc độ: {corag_speed} ms | Độ tin cậy: {corag_conf}% | Chunks: {corag_chunks}"
        )
        if corag_queries:
            st.caption(f"Queries: {', '.join(corag_queries)}")
        st.markdown(corag_answer)


def build_messages_from_history() -> list[dict]:
    messages = []
    if st.session_state.document_meta:
        messages.append(
            {
                "role": "assistant",
                "content": "Tài liệu đã sẵn sàng. Bạn có thể tiếp tục hỏi thêm.",
            }
        )

    for item in st.session_state.chat_history:
        messages.append({"role": "user", "content": item["question"]})
        if item.get("mode") == "compare":
            rag_answer = item.get("rag_answer", "")
            corag_answer = item.get("corag_answer", "")
            compare_text = (
                "RAG:\n"
                f"{rag_answer}\n\n"
                "CoRAG:\n"
                f"{corag_answer}"
            ).strip()
            messages.append(
                {
                    "role": "assistant",
                    "content": compare_text,
                }
            )
        else:
            messages.append({"role": "assistant", "content": item["answer"]})

    return messages


def build_thread_title(messages: list[dict], document_meta: dict | None) -> str:
    for message in messages:
        if message["role"] == "user":
            text = message["content"].strip().replace("\n", " ")
            return text[:48] + ("..." if len(text) > 48 else "")

    if document_meta:
        return f"Chat với {document_meta.get('file_name', 'tài liệu')}"
    return "Cuộc trò chuyện mới"


def get_thread(thread_id: str | None) -> dict | None:
    if not thread_id:
        return None

    for thread in st.session_state.conversation_threads:
        if thread["id"] == thread_id:
            return thread
    return None


def find_thread_for_backend_state(chat_history: list[dict], document_meta: dict | None) -> str | None:
    if not st.session_state.conversation_threads:
        return None

    target_file = (document_meta or {}).get("file_name")

    # Match exact persisted backend state first to avoid creating duplicate threads on reload.
    for thread in st.session_state.conversation_threads:
        thread_meta = thread.get("document_meta") or {}
        if thread_meta.get("file_name") != target_file:
            continue
        if (thread.get("chat_history") or []) == chat_history:
            return thread.get("id")

    if not chat_history:
        return None

    # Fallback by last question and history length when older thread snapshots differ slightly.
    last_question = chat_history[-1].get("question")
    expected_len = len(chat_history)
    for thread in st.session_state.conversation_threads:
        thread_meta = thread.get("document_meta") or {}
        thread_history = thread.get("chat_history") or []
        if thread_meta.get("file_name") != target_file or len(thread_history) != expected_len:
            continue
        if thread_history and thread_history[-1].get("question") == last_question:
            return thread.get("id")

    return None


def delete_thread(thread_id: str) -> None:
    st.session_state.conversation_threads = [
        thread
        for thread in st.session_state.conversation_threads
        if thread["id"] != thread_id
    ]

    if st.session_state.active_thread_id == thread_id:
        st.session_state.active_thread_id = None
    if st.session_state.viewing_thread_id == thread_id:
        st.session_state.viewing_thread_id = st.session_state.active_thread_id

    save_threads()


def clear_all_threads() -> None:
    st.session_state.conversation_threads = []
    st.session_state.active_thread_id = None
    st.session_state.viewing_thread_id = None
    save_threads()


def create_or_update_active_thread() -> None:
    if not st.session_state.messages and not st.session_state.document_meta:
        return

    now = datetime.now().isoformat(timespec="seconds")
    active_thread = get_thread(st.session_state.active_thread_id)

    if active_thread is None:
        thread_id = str(uuid4())
        st.session_state.conversation_threads.insert(
            0,
            {
                "id": thread_id,
                "title": build_thread_title(st.session_state.messages, st.session_state.document_meta),
                "messages": list(st.session_state.messages),
                "chat_history": list(st.session_state.chat_history),
                "document_meta": st.session_state.document_meta,
                "updated_at": now,
            },
        )
        st.session_state.active_thread_id = thread_id
        st.session_state.viewing_thread_id = thread_id
    else:
        active_thread["title"] = build_thread_title(
            st.session_state.messages,
            st.session_state.document_meta,
        )
        active_thread["messages"] = list(st.session_state.messages)
        active_thread["chat_history"] = list(st.session_state.chat_history)
        active_thread["document_meta"] = st.session_state.document_meta
        active_thread["updated_at"] = now

    st.session_state.conversation_threads.sort(
        key=lambda item: item.get("updated_at", ""),
        reverse=True,
    )
    save_threads()


def restore_thread_for_view(thread_id: str) -> None:
    st.session_state.viewing_thread_id = thread_id
    thread = get_thread(thread_id)
    if thread:
        st.session_state.latest_compare = get_latest_compare_from_history(thread.get("chat_history", []))
    if thread_id == st.session_state.active_thread_id:
        return


def sync_from_backend() -> None:
    try:
        response = backend_session.get(
            f"{BASE_URL}/session-state/",
            timeout=15,
        )
        if response.status_code != 200:
            return
    except requests.RequestException:
        return

    payload = response.json()
    st.session_state.chat_history = payload.get("chat_history", [])
    st.session_state.document_meta = payload.get("document")
    st.session_state.vector_store_ready = st.session_state.document_meta is not None

    if get_thread(st.session_state.active_thread_id) is None:
        st.session_state.active_thread_id = None
    if get_thread(st.session_state.viewing_thread_id) is None:
        st.session_state.viewing_thread_id = None

    if st.session_state.active_thread_id is None:
        matched_thread_id = find_thread_for_backend_state(
            st.session_state.chat_history,
            st.session_state.document_meta,
        )
        if matched_thread_id:
            st.session_state.active_thread_id = matched_thread_id
            st.session_state.viewing_thread_id = matched_thread_id

    st.session_state.messages = build_messages_from_history()
    st.session_state.latest_compare = get_latest_compare_from_history(st.session_state.chat_history)
    create_or_update_active_thread()


def handle_upload(uploaded_file) -> None:
    if uploaded_file is None:
        return

    with st.sidebar:
        with st.spinner("Đang tải và xử lý tài liệu..."):
            try:
                response = backend_session.post(
                    f"{BASE_URL}/upload/",
                    files={"file": uploaded_file},
                    data={
                        "chunk_size": st.session_state.chunk_size,
                        "chunk_overlap": st.session_state.chunk_overlap,
                    },
                    timeout=DEFAULT_TIMEOUT,
                )
            except requests.RequestException as exc:
                st.error(f"Lỗi kết nối backend: {exc}")
                return

    if response.status_code != 200:
        st.sidebar.error(response.text)
        return

    payload = response.json()
    st.session_state.document_meta = payload.get("document")
    st.session_state.chat_history = payload.get("chat_history", [])
    st.session_state.vector_store_ready = True
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": (
                f"Đã tải tài liệu `{uploaded_file.name}` thành công. "
                "Bạn có thể bắt đầu đặt câu hỏi."
            ),
        }
    ]
    st.session_state.active_thread_id = None
    create_or_update_active_thread()
    st.sidebar.success("Tài liệu đã sẵn sàng để truy vấn.")


def refresh_chat_history_from_response(payload: dict) -> None:
    st.session_state.chat_history = payload.get("chat_history", st.session_state.chat_history)
    st.session_state.document_meta = payload.get("document", st.session_state.document_meta)
    st.session_state.messages = build_messages_from_history()
    create_or_update_active_thread()


def ask_compare_question(prompt: str) -> None:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.spinner("Đang chạy RAG và CoRAG song song..."):
        try:
            response = backend_session.post(
                COMPARE_URL,
                json={"query": prompt},
                timeout=DEFAULT_TIMEOUT,
            )
        except requests.RequestException as exc:
            st.error(f"Lỗi kết nối backend: {exc}")
            return

        if response.status_code == 200:
            payload = response.json()
            refresh_chat_history_from_response(payload)
            st.session_state.latest_compare = payload
        else:
            st.error(f"Lỗi backend: {response.text}")
            return

    if st.session_state.latest_compare:
        render_compare_panels(st.session_state.latest_compare)


def clear_history_action() -> None:
    try:
        response = backend_session.delete(
            f"{BASE_URL}/clear-history/",
            timeout=15,
        )
    except requests.RequestException as exc:
        st.sidebar.error(f"Lỗi kết nối backend: {exc}")
        return

    if response.status_code == 200:
        # Đồng bộ lại state từ backend để tránh lệch cookie/session.
        sync_from_backend()
        # Nếu đang xem thread cũ, chuyển về thread hiện tại để UI phản ánh kết quả xóa.
        st.session_state.viewing_thread_id = st.session_state.active_thread_id
        st.sidebar.success("Đã xóa lịch sử chat của session hiện tại.")
        st.rerun()

    st.sidebar.error(response.text)


def clear_document_action() -> None:
    try:
        response = backend_session.delete(
            f"{BASE_URL}/clear/",
            timeout=15,
        )
    except requests.RequestException as exc:
        st.sidebar.error(f"Lỗi kết nối backend: {exc}")
        return

    if response.status_code == 200:
        st.session_state.document_meta = None
        st.session_state.vector_store_ready = False
        st.session_state.chat_history = []
        st.session_state.messages = []
        st.session_state.latest_compare = None
        create_or_update_active_thread()
        st.rerun()

    st.sidebar.error(response.text)


def render_sidebar_history() -> None:
    st.sidebar.subheader("Các cuộc trò chuyện")
    if not st.session_state.conversation_threads:
        st.sidebar.caption("Chưa có cuộc trò chuyện nào được lưu.")
        return

    if st.sidebar.button("Xóa tất cả cuộc trò chuyện đã lưu", use_container_width=True):
        clear_all_threads()
        st.rerun()

    for thread in st.session_state.conversation_threads:
        label = thread.get("title", "Cuộc trò chuyện")
        if thread["id"] == st.session_state.active_thread_id:
            label = f"• {label}"

        col_open, col_delete = st.sidebar.columns([0.82, 0.18])
        with col_open:
            if st.button(label, key=f"thread-{thread['id']}", use_container_width=True):
                restore_thread_for_view(thread["id"])
                st.rerun()
        with col_delete:
            if st.button("✕", key=f"delete-thread-{thread['id']}", use_container_width=True):
                delete_thread(thread["id"])
                st.rerun()


@st.dialog("Xác nhận xóa lịch sử")
def confirm_clear_history_dialog() -> None:
    st.write("Bạn có chắc muốn xóa toàn bộ lịch sử chat của session hiện tại không?")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Xóa lịch sử", use_container_width=True):
            try:
                response = backend_session.delete(
                    f"{BASE_URL}/clear-history/",
                    timeout=15,
                )
                if response.status_code == 200:
                    st.session_state.chat_history = []
                    st.session_state.messages = []
                    create_or_update_active_thread()
                    st.rerun()
                else:
                    st.error(response.text)
            except requests.RequestException as exc:
                st.error(f"Lỗi kết nối backend: {exc}")
    with col2:
        if st.button("Hủy", use_container_width=True):
            st.rerun()


@st.dialog("Xác nhận xóa tài liệu")
def confirm_clear_vector_store_dialog() -> None:
    st.write("Bạn có chắc muốn xóa tài liệu đã upload và vector store hiện tại không?")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Xóa tài liệu", use_container_width=True):
            try:
                response = backend_session.delete(
                    f"{BASE_URL}/clear/",
                    timeout=15,
                )
                if response.status_code == 200:
                    st.session_state.document_meta = None
                    st.session_state.vector_store_ready = False
                    st.session_state.chat_history = []
                    st.session_state.messages = []
                    create_or_update_active_thread()
                    st.rerun()
                else:
                    st.error(response.text)
            except requests.RequestException as exc:
                st.error(f"Lỗi kết nối backend: {exc}")
    with col2:
        if st.button("Hủy", use_container_width=True):
            st.rerun()


def render_sidebar() -> None:
    st.sidebar.title("Workspace")
    st.sidebar.caption("Tài liệu và lịch sử hội thoại.")
    st.sidebar.subheader("Tài liệu")
    uploaded_file = st.sidebar.file_uploader(
        "Chọn PDF hoặc DOCX",
        type=["pdf", "docx"],
        accept_multiple_files=False,
    )

    if st.sidebar.button("Tải tài liệu", use_container_width=True, disabled=uploaded_file is None):
        handle_upload(uploaded_file)

    col1, col2 = st.sidebar.columns(2)
    with col1:
        if st.button("Xóa lịch sử", use_container_width=True):
            clear_history_action()
    with col2:
        if st.button("Xóa tài liệu", use_container_width=True):
            clear_document_action()

    st.sidebar.markdown("---")
    render_sidebar_history()


def render_messages() -> None:
    viewing_thread = get_thread(st.session_state.viewing_thread_id)
    messages = viewing_thread["messages"] if viewing_thread else st.session_state.messages

    if not messages:
        st.info("Upload một tài liệu rồi đặt câu hỏi để bắt đầu.")
        return

    for message in messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])


def ask_question(prompt: str) -> None:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    should_append_local = True
    with st.chat_message("assistant"):
        with st.spinner("Đang truy vấn tài liệu..."):
            try:
                response = backend_session.post(
                    f"{BASE_URL}/ask/",
                    json={"query": prompt},
                    timeout=DEFAULT_TIMEOUT,
                )
            except requests.RequestException as exc:
                answer = f"Lỗi kết nối backend: {exc}"
            else:
                if response.status_code == 200:
                    payload = response.json()
                    answer = payload.get("answer", "Không có câu trả lời.")
                    refresh_chat_history_from_response(payload)
                    should_append_local = False
                else:
                    answer = f"Lỗi backend: {response.text}"

            st.markdown(answer)

    if should_append_local:
        st.session_state.messages.append({"role": "assistant", "content": answer})


def render_main() -> None:
    render_header()

    if st.session_state.compare_mode and st.session_state.latest_compare:
        render_compare_panels(st.session_state.latest_compare)

    st.markdown('<div class="section-title">Chat</div>', unsafe_allow_html=True)
    render_messages()

    if not st.session_state.vector_store_ready:
        st.markdown(
            """
            <div class="empty-card">
                Chưa có tài liệu nào. Upload PDF/DOCX ở sidebar để bắt đầu.
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    if (
        st.session_state.viewing_thread_id
        and st.session_state.viewing_thread_id != st.session_state.active_thread_id
    ):
        st.info("Bạn đang xem lại một cuộc hội thoại cũ. Chọn thread hiện tại để tiếp tục chat.")
        return

    prompt = st.chat_input("Hỏi về nội dung tài liệu...")
    if prompt:
        if st.session_state.compare_mode:
            ask_compare_question(prompt)
        else:
            ask_question(prompt)


init_state()
inject_theme()
backend_session = get_backend_session()
sync_from_backend()
render_sidebar()
render_main()
