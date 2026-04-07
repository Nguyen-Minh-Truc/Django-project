# app.py
import json
from datetime import datetime
from pathlib import Path
from uuid import uuid4

import requests
import streamlit as st


BASE_URL = "http://localhost:8000/api"
CHUNK_SIZE_OPTIONS = [500, 1000, 1500, 2000]
CHUNK_OVERLAP_OPTIONS = [50, 100, 200]
DEFAULT_TIMEOUT = 120
THREADS_FILE = Path("conversation_threads.json")

st.set_page_config(page_title="RAG Document Chat", page_icon="📄", layout="wide")


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
        active_thread["document_meta"] = st.session_state.document_meta
        active_thread["updated_at"] = now

    st.session_state.conversation_threads.sort(
        key=lambda item: item.get("updated_at", ""),
        reverse=True,
    )
    save_threads()


def restore_thread_for_view(thread_id: str) -> None:
    st.session_state.viewing_thread_id = thread_id
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
    st.session_state.messages = build_messages_from_history()
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


def render_sidebar_history() -> None:
    st.sidebar.subheader("Các cuộc trò chuyện")
    if not st.session_state.conversation_threads:
        st.sidebar.caption("Chưa có cuộc trò chuyện nào được lưu.")
        return

    for thread in st.session_state.conversation_threads:
        label = thread.get("title", "Cuộc trò chuyện")
        if thread["id"] == st.session_state.active_thread_id:
            label = f"• {label}"
        if st.sidebar.button(label, key=f"thread-{thread['id']}", use_container_width=True):
            restore_thread_for_view(thread["id"])
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
    st.sidebar.title("RAG Controls")
    st.sidebar.caption("Hỗ trợ PDF và DOCX, có lưu lịch sử chat theo session.")
    st.sidebar.markdown("---")

    st.sidebar.markdown("---")
    st.sidebar.subheader("Tài liệu")
    uploaded_file = st.sidebar.file_uploader(
        "Upload PDF hoặc DOCX",
        type=["pdf", "docx"],
        accept_multiple_files=False,
    )

    if st.sidebar.button("Tải tài liệu", use_container_width=True, disabled=uploaded_file is None):
        handle_upload(uploaded_file)

    if st.session_state.document_meta:
        meta = st.session_state.document_meta
        st.sidebar.info(
            "\n".join(
                [
                    f"File: {meta.get('file_name', 'Không rõ')}",
                    f"Loại: {meta.get('file_type', 'Không rõ').upper()}",
                    f"Chunk size: {meta.get('chunk_size', '-')}",
                    f"Chunk overlap: {meta.get('chunk_overlap', '-')}",
                ]
            )
        )

    col1, col2 = st.sidebar.columns(2)
    with col1:
        if st.button("xoá lịch sử", use_container_width=True):
            confirm_clear_history_dialog()
    with col2:
        if st.button("xoá tài liệu đang upload", use_container_width=True):
            confirm_clear_vector_store_dialog()

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
                else:
                    answer = f"Lỗi backend: {response.text}"

            st.markdown(answer)

    st.session_state.messages.append({"role": "assistant", "content": answer})


def render_main() -> None:
    st.title("Conversational RAG")
    st.caption("Chat nhiều lượt với tài liệu PDF/DOCX và lưu từng cuộc hội thoại như một thread riêng.")

    render_messages()

    if not st.session_state.vector_store_ready:
        st.markdown(
            """
            ### Những gì đã sẵn sàng
            - Upload được cả `PDF` và `DOCX`
            - Điều chỉnh `chunk_size` và `chunk_overlap` trước khi index
            - Lưu từng cuộc hội thoại riêng và xem lại ở sidebar
            - Xóa lịch sử hoặc vector store bằng nút riêng có xác nhận
            """
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
        ask_question(prompt)


init_state()
backend_session = get_backend_session()
sync_from_backend()
render_sidebar()
render_main()
