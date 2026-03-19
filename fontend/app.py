# app.py
import streamlit as st
import requests

# --------- Cấu hình ---------
BASE_URL = "http://localhost:8000/api"  # URL backend Django
st.set_page_config(page_title="PDF QA App", layout="wide")

# --------- Sidebar ---------
st.sidebar.title("Hướng dẫn")
st.sidebar.markdown("""
1. Upload file PDF.
2. Chờ hệ thống xử lý.
3. Nhập câu hỏi về nội dung PDF.
4. Xem câu trả lời hiển thị ngay.
""")
st.sidebar.markdown("---")
st.sidebar.title("Cấu hình")
st.sidebar.write("Mẫu backend: Ollama / Qwen2.5")
st.sidebar.write("Max chunk: 1000, Overlap: 50")

# --------- Session state init ---------
if "pdf_uploaded" not in st.session_state:
    st.session_state.pdf_uploaded = None
if "vector_db_ready" not in st.session_state:
    st.session_state.vector_db_ready = False

# --------- Main area ---------
st.title("📄 Ứng dụng Hỏi đáp PDF")

# Upload PDF
uploaded_file = st.file_uploader("Kéo thả hoặc chọn file PDF", type="pdf")

if uploaded_file:
    # Nếu lần đầu upload hoặc file khác
    if st.session_state.pdf_uploaded != uploaded_file:
        st.session_state.pdf_uploaded = uploaded_file
        st.session_state.vector_db_ready = False  # Reset trạng thái

        # Upload file lên backend
        with st.spinner("Đang tải file lên backend..."):
            try:
                files = {"file": uploaded_file.getvalue()}
                response = requests.post(f"{BASE_URL}/upload/", files={"file": uploaded_file})
                if response.status_code == 200:
                    st.success("✅ Upload PDF thành công!")
                    st.session_state.vector_db_ready = True
                else:
                    st.error(f"❌ Upload thất bại: {response.text}")
            except Exception as e:
                st.error(f"❌ Lỗi kết nối backend: {e}")

# Nhập câu hỏi
if st.session_state.vector_db_ready:
    question = st.text_input("Nhập câu hỏi về PDF:")

    if question:
        with st.spinner("Đang xử lý câu hỏi..."):
            try:
                response = requests.post(f"{BASE_URL}/ask/", json={"query": question})
                if response.status_code == 200:
                    answer = response.json().get("answer", "Không có câu trả lời.")
                    st.markdown(f"**Câu trả lời:** {answer}")
                else:
                    st.error(f"❌ Lỗi backend: {response.text}")
            except Exception as e:
                st.error(f"❌ Lỗi kết nối backend: {e}")

# Nút tóm tắt PDF
if st.session_state.vector_db_ready:
    if st.button("Tóm tắt PDF"):
        with st.spinner("Đang tóm tắt..."):
            try:
                response = requests.post(f"{BASE_URL}/summary/")
                if response.status_code == 200:
                    summary = response.json().get("summary", "Không có tóm tắt.")
                    st.markdown("### 📝 Tóm tắt PDF")
                    st.write(summary)
                else:
                    st.error(f"❌ Lỗi backend: {response.text}")
            except Exception as e:
                st.error(f"❌ Lỗi kết nối backend: {e}")