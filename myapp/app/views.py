from rest_framework.decorators import api_view
from rest_framework.response import Response
from pypdf import PdfReader

from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_community.llms import Ollama
from langchain_text_splitters import RecursiveCharacterTextSplitter

VECTOR_DB = None

# Hàm khởi tạo LLM trong hàm, tránh RecursionError
def get_llm():
     return Ollama(model="qwen2.5:1.5b")

# Load PDF
def load_pdf(file_path):
    reader = PdfReader(file_path)
    text = ""
    for page in reader.pages:
        text += page.extract_text()
    return text

# Tạo DB vector
def create_db(text):
    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=50)
    chunks = splitter.split_text(text)
    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    db = FAISS.from_texts(chunks, embeddings)
    return db

# Upload PDF
@api_view(['POST'])
def upload_pdf(request):
    global VECTOR_DB
    file = request.FILES['file']
    path = "temp.pdf"
    with open(path, "wb+") as f:
        for chunk in file.chunks():
            f.write(chunk)
    text = load_pdf(path)
    VECTOR_DB = create_db(text)
    return Response({"message": "Upload thành công!"})

# Hỏi PDF
@api_view(['POST'])
def ask_pdf(request):
    global VECTOR_DB
    query = request.data.get("query")
    if VECTOR_DB is None:
        return Response({"answer": "⚠️ Chưa upload PDF!"})

    docs = VECTOR_DB.similarity_search(query, k=3)  # chỉ lấy 3 chunk
    context = "\n".join([doc.page_content for doc in docs])
    prompt = f"Dựa vào nội dung sau trả lời:\n{context}\nCâu hỏi: {query}"

    llm = get_llm()
    answer = llm.invoke(prompt)
    return Response({"answer": answer})

# Tóm tắt PDF
@api_view(['POST'])
def summary_pdf(request):
    global VECTOR_DB
    if VECTOR_DB is None:
        return Response({"summary": "⚠️ Chưa upload PDF!"})

    docs = VECTOR_DB.similarity_search("tóm tắt nội dung", k=5)  # lấy 5 chunk
    context = "\n".join([doc.page_content for doc in docs])
    prompt = f"Tóm tắt nội dung:\n{context}"

    llm = get_llm()
    summary = llm.invoke(prompt)
    return Response({"summary": summary})