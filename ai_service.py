import google.generativeai as genai
import json
import streamlit as st
def configure_genai():
    try:
        api_key = "AIzaSyCSITa2qpc_0VE7xah5u4vA8WWOiY3sIaA"
        genai.configure(api_key=api_key)
        return True
    except Exception as e:
        st.error(f"Lỗi API Key: {e}.")
        return False
    
def ask_ai_to_parse(csv_data):
    model = genai.GenerativeModel('gemini-2.5-pro')
    prompt = f"""
    Bạn là một trợ lý kế toán chuyên nghiệp. Tôi có một đoạn dữ liệu giao dịch dưới dạng CSV thô.
    Nhiệm vụ của bạn:
    1. Trích xuất: Người giao dịch, Nội dung khoản tiền, Khoản tiền, Phân loại danh mục, Ngày Giao dịch, Loại tương ứng với các cột user,content,amount,category,date,type
    2. Phân loại: Tự động chọn danh mục cho mỗi khoản chi dựa trên dữ liệu đọc (chỉ chọn trong: "Ăn uống", "Di chuyển", "Nhà cửa", "Giải trí", "Khác").
    3. Chú ý: Cột loại chỉ nhận 2 giá trị là "Thu nhập" và "Chi tiêu"
    4. Định dạng: Trả về kết quả dưới dạng JSON List.
    Lưu ý:
    - Nếu số tiền là số âm, hãy chuyển thành số dương.
    - Định dạng ngày trả về: YYYY-MM-DD.
    - Không giải thích thêm, chỉ trả về JSON.
    Dữ liệu CSV:
    {csv_data}
    """
    
    try:
        response = model.generate_content(prompt)
        text_response = response.text.replace("```json", "").replace("```", "").strip()
        return json.loads(text_response)
    except Exception as e:
        print(f"AI Error: {e}")
        return []
def ask_ai_to_read_money(amount):
    model=genai.GenerativeModel('gemini-2.5-flash')
    prompt = f"""
    Bạn là một công cụ chuyển đổi số liệu thành văn bản tiếng Việt chuẩn. Nhiệm vụ của bạn là nhận vào một chuỗi số và trả về cách đọc của số đó bằng tiếng Việt.
    Quy tắc:

    Chỉ trả về văn bản cách đọc số, không được thêm bất kỳ lời dẫn hay giải thích nào (như "Đây là cách đọc...").

    Đọc đúng chuẩn ngữ pháp tiếng Việt (ví dụ: dùng "lẻ" hoặc "linh" cho số 0 ở giữa, "mốt" cho số 1 tận cùng hàng chục, "tư" cho số 4, v.v.).

    Nếu số quá lớn, hãy đọc theo lớp (tỷ, triệu, nghìn).
    Đây là số bạn cần đọc:
    {amount}
    """
    try:
        response= model.generate_content(prompt)
        text_response = response.text.strip()
        return text_response
    except Exception as e:
        return []