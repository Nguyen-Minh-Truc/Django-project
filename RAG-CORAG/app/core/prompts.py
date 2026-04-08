"""
prompts.py
----------
Tất cả prompt template tập trung ở một chỗ.
Dễ chỉnh sửa, A/B test, hoặc i18n sau này.
"""


def qa_prompt(context: str, question: str) -> str:
    return f"""Bạn là trợ lý đọc tài liệu. Chỉ dựa vào ngữ cảnh dưới đây để trả lời.
Nếu ngữ cảnh không đủ thông tin, hãy nói rõ "Tài liệu không đề cập đến vấn đề này."
Không được bịa đặt hoặc dùng kiến thức ngoài tài liệu.

=== Ngữ cảnh ===
{context}

=== Câu hỏi ===
{question}

=== Trả lời ==="""


def summary_prompt(context: str) -> str:
    return f"""Bạn là trợ lý tóm tắt tài liệu. Dựa vào các đoạn trích dưới đây,
hãy viết một bản tóm tắt ngắn gọn, súc tích, có cấu trúc rõ ràng bằng tiếng Việt.

=== Nội dung tài liệu ===
{context}

=== Tóm tắt ==="""