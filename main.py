import streamlit as st
import sqlite3
import hashlib
import pandas as pd
from datetime import datetime
import google.generativeai as genai
import json
import ai_service as ai
import threading
# import os

# # --- ĐOẠN CODE CẤP CỨU: XÓA SẠCH DATABASE CŨ ---
# if os.path.exists("expense_db.db"):
#     os.remove("expense_db.db")
#     print("Đã xóa file database cũ!")

# if os.path.exists("expense_db.db-wal"):
#     os.remove("expense_db.db-wal")

# if os.path.exists("expense_db.db-shm"):
#     os.remove("expense_db.db-shm")

# Xóa cache của Streamlit để ép kết nối lại
st.cache_resource.clear()
# fix lỗi streamlit bị đơ vì locked db trên streamlit
# update: Lỗi bất đồng bộ quá nặng do việc mở kết nối bị delay
db_lock = threading.Lock()

@st.cache_resource
def get_connection():
    connection = sqlite3.connect('expense_db.db', check_same_thread=False)
    connection.execute("PRAGMA journal_mode=WAL;") 
    return connection

# tao bang
def init_db():
    # CHỈ MỘT NGƯỜI ĐƯỢC TẠO BẢNG 1 LÚC
    with db_lock:
        conn = get_connection()
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY,
                password TEXT
            )
        ''')
        c.execute('''
            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                owner TEXT,
                item_name TEXT,
                amount REAL,
                category TEXT,
                date DATE
            )
        ''')
        c.execute('''
            CREATE TABLE IF NOT EXISTS income (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                owner TEXT,
                source TEXT,
                amount REAL,
                category TEXT,
                date DATE
            )
        ''')
        conn.commit()
# encrypt password
def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()


def check_hashes(password, hashed_text):
    if make_hashes(password) == hashed_text:
        return True
    return False


# main funct

# tạo user
def create_user(username, password):
    with db_lock:
        conn = get_connection()
        c = conn.cursor()
        try:
            c.execute('INSERT INTO users(username, password) VALUES (?,?)',
                      (username, make_hashes(password)))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

# đăng nhập cho user
def login_user(username, password):
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE username =? AND password = ?',
              (username, make_hashes(password)))
    data = c.fetchall()
    return data


# funct expenses
def add_expense(owner, expense_name, amount, category, date):
    with db_lock:
        db=get_connection()
        c=db.cursor()
        # bug fixed: 4 out of 5 columns
        c.execute('insert into expenses(owner, item_name, amount, category, date) values (?,?,?,?,?)',
            (owner,expense_name,amount,category,date))
        db.commit()
    st.cache_data.clear()    

def add_income(owner, income_name, amount, category, date):
    with db_lock:
        db=get_connection()
        c=db.cursor()
        # bug fixed: 4 out of 5 columns
        c.execute('insert into income(owner, source, amount, category, date) values (?,?,?,?,?)',
            (owner,income_name,amount,category,date))
        db.commit()
    st.cache_data.clear()

def del_record(table_name,record_id,owner):
    with db_lock:
        db=get_connection()
        c=db.cursor()
        query = f"DELETE FROM {table_name} WHERE id=? and owner=?"
        c.execute(query,(record_id,owner))
        db.commit()
    st.cache_data.clear()
    # db.close()

@st.cache_data(ttl=10)
def view_expenses(user):
    conn = get_connection()
    # Không dùng with, không commit, chỉ đọc
    return pd.read_sql_query("SELECT item_name as ten, category as danh_muc, date as ngay, amount as so_tien FROM expenses WHERE owner=?", conn, params=(user,))

@st.cache_data(ttl=10)
def view_income(user):
    conn = get_connection()
    return pd.read_sql_query("SELECT source as ten, category as danh_muc, date as ngay, amount as so_tien FROM income WHERE owner=?", conn, params=(user,))

def get_data_with_id(table_name, owner):
    db = get_connection() 
    if table_name == "expenses":
        query = "SELECT * FROM expenses WHERE owner=?"
    else:
        query = "SELECT * FROM income WHERE owner=?"
    read_data = pd.read_sql_query(query, db, params=(owner,))
    return read_data
# main gui
def main():
    st.title("Quản Lý Chi Tiêu Cá Nhân")
    # Session state luu trang thai dang nhap
    if 'logged_in' not in st.session_state:
        st.session_state['logged_in'] = False
        st.session_state['username'] = ''

    # side bar
    if not st.session_state['logged_in']:#chưa đăng nhập
        menu = ["Đăng Nhập", "Đăng Ký"]
        choice = st.sidebar.selectbox("Menu", menu)

        if choice == "Đăng Ký":
            st.subheader("Tạo tài khoản")
            new_user = st.text_input("Username")
            new_password = st.text_input("Password", type='password')

            if st.button("Đăng Ký"):
                if create_user(new_user, new_password):
                    st.success("Đã tạo tài khoản thành công! Vui lòng chuyển sang tab Đăng Nhập.")
                else:
                    st.warning("Tài khoản đã tồn tại!")

        elif choice == "Đăng Nhập":
            st.subheader("Đăng nhập vào hệ thống quản lý chi tiêu")
            username = st.text_input("Username")
            password = st.text_input("Password", type='password')

            if st.button("Login"):
                result = login_user(username, password)
                if result:
                    st.success(f"Chào mừng {username} quay trở lại!")
                    st.session_state['logged_in'] = True
                    st.session_state['username'] = username
                    st.rerun()
                else:
                    st.error("Đăng nhập thất bại, vui lòng kiểm tra lại thông tin tài khoản")

    # đã đăng nhập
    else:
        user= st.session_state['username']
        st.sidebar.write(f"Xin chào, **{user}**")
        butt=st.sidebar.button("Đăng xuất")
        if butt:
            st.session_state['logged_in'] = False
            st.rerun()

        #set avatar user
        st.title("Dashboard")

        #METRICS
        df_expense = view_expenses(user)
        df_income = view_income(user)

        total_expense = df_expense['so_tien'].sum() if not df_expense.empty else 0
        total_income = df_income['so_tien'].sum() if not df_income.empty else 0
        balance = total_income - total_expense
        col1, col2, col3 = st.columns(3)
        col1.metric("Tổng Thu Nhập", f"{total_income:,.0f} VND", )
        col2.metric("Tổng Chi Tiêu", f"{total_expense:,.0f} VND", ) 
        col3.metric("Số Dư", f"{balance:,.0f} VND", )
        # main app
        tab1,tab4,tab2,tab3=st.tabs(["Thêm giao dịch","Thay đổi giao dịch","Lịch sử chi tiêu","Nhập từ file"])
        cat_out=["Ăn uống", "Di chuyển", "Nhà cửa", "Giải trí", "Khác"]
        cat_in=["Lương", "Hoa Hồng", "Nghề tay trái", "Rửa tiền","Khác"]
        
        # input form tab1
        with tab1:
            col_in, col_out = st.columns(2)
            with col_out:
                st.subheader("Thêm khoản chi")
                with st.form("expense_form", clear_on_submit=True):
                    item = st.text_input("Nội dung")
                    amt = st.number_input("Số tiền", min_value=0, step=1000)
                    cat = st.selectbox("Danh mục", cat_out)
                    dt = st.date_input("Ngày chi")
                    if st.form_submit_button("Lưu chi tiêu"):
                        add_expense(user, item, amt, cat, dt)
                        st.toast(f"Đã lưu: -{amt:,.0f} đ", icon="💸")
                        st.rerun()
            with col_in:
                st.subheader("Thêm khoản thu")
                with st.form("income_form", clear_on_submit=True):
                    src = st.text_input("Nguồn thu")
                    amt = st.number_input("Số tiền", min_value=0, step=1000)
                    cat = st.selectbox("Loại thu", cat_in)
                    dt = st.date_input("Ngày thu")
                    if st.form_submit_button("Lưu thu nhập"):
                        add_income(user, src, amt, cat, dt)
                        st.toast(f"Đã nhận: +{amt:,.0f} đ", icon="💰")
                        st.rerun()
        with tab4:
            st.header("Thay đổi giao dịch")
            option_delete = st.radio("Chọn loại dữ liệu muốn sửa đổi:", ["Chi tiêu", "Thu nhập"], horizontal=True)
            table_name = 'expenses' if option_delete == "Chi tiêu" else 'income'
            
            df_delete = get_data_with_id(table_name, user)
            
            if not df_delete.empty:
                select_all=st.checkbox("Chọn tất cả")
                df_delete['Delete'] = False
                if select_all:
                    df_delete['Delete']=True
                st.write(f"Danh sách {option_delete} (Tích vào ô 'Delete' ở cột cuối để chọn xóa):")
                
                # Sử dụng data_editor để tạo checkbox tương tác
                edited_df = st.data_editor(
                    
                    df_delete,
                    column_config={
                        "Delete": st.column_config.CheckboxColumn(
                            "Chọn xóa?",
                            default=False,
                        ),
                        "id": st.column_config.NumberColumn("ID", disabled=True) # khóa cột id  
                    },
                    disabled=False, 
                    hide_index=True
                )
                
                # execute
                to_delete = edited_df[edited_df['Delete'] == True]
                count_trans=len(to_delete)
                sum_trans=to_delete['amount'].sum()
                read_money=ai.ask_ai_to_read_money(sum_trans)
                if not to_delete.empty:
                    st.warning(f"""
                               Bạn đang chọn xóa {count_trans} giao dịch với tổng số tiền {sum_trans} VNĐ.\n
                               Bằng chữ: {read_money}.     
                               """)
                    if st.button("Xác nhận xóa"):
                        count = 0

                        for index, row in to_delete.iterrows():
                            del_record(table_name, row['id'], user)
                            count += 1
                        
                        st.success(f"Đã xóa thành công {count} giao dịch!")
                        reload = st.button("Reload")
                        if reload:
                            st.rerun()
            else:
                st.info("Chưa có dữ liệu nào để xóa.")
        with tab2:
            st.subheader("Lịch sử giao dịch")
            
            view_mode = st.radio("Xem dữ liệu:", ["Chi tiêu", "Thu nhập"], horizontal=True)
            
            if view_mode == "Chi tiêu":
                if not df_expense.empty:
                    st.dataframe(df_expense)
                    # Biểu đồ tròn cho chi tiêu
                    st.write("Cơ cấu chi tiêu:")
                    st.bar_chart(df_expense.groupby("danh_muc")['so_tien'].sum())
                else:
                    st.info("Chưa có dữ liệu chi tiêu.")
            else:
                if not df_income.empty:
                    st.dataframe(df_income)
                    # Biểu đồ cho thu nhập
                    st.write("Nguồn thu chính:")
                    st.bar_chart(df_income.groupby("danh_muc")['so_tien'].sum())
                else:
                    st.info("Chưa có dữ liệu thu nhập.")
        with tab3:
            st.header("Nhập liệu từ Excel/CSV")
            st.info("Hỗ trợ file .csv hoặc .xlsx. Dữ liệu sẽ được thêm vào bảng tương ứng.")
            uploaded_file = st.file_uploader("Chọn file", type=['xlsx', 'csv'])
            
            if uploaded_file is not None:
                try:
                    if uploaded_file.name.endswith('.csv'):
                        df_upload = pd.read_csv(uploaded_file)
                    else:
                        df_upload = pd.read_excel(uploaded_file)
                    
                    st.write("Dữ liệu trong file của bạn (5 cột đầu tiên):")

                    # ai_used=st.button("Sử dụng AI để đọc tài liệu của bạn")
                    manual,ai_serv = st.tabs(["Chọn thủ công","Sử dụng AI"])
                    with manual:
                        st.dataframe(df_upload.head()) 

                        st.subheader("Chọn cột để lấy dữ liệu")
                        st.caption("Chọn cột trong file tương ứng với dữ liệu cần nhập")
                        
                        cols = df_upload.columns.tolist()
                        
                        col1, col2, col3,col5,col6 = st.columns(5)
                        with col1:
                            col_user = st.selectbox("Cột Người dùng", cols)
                        with col2:
                            col_item = st.selectbox("Cột Nội dung", cols)
                        with col3:
                            col_amount = st.selectbox("Cột Số tiền", cols)
                        with col5:
                            col_date = st.selectbox("Cột ngày",cols)
                        with col6:
                            option_cat = st.radio("Danh mục:", ["Chọn chung cho tất cả bản ghi", "Lấy tên danh mục từ file"])
                            if option_cat == "Lấy tên danh mục từ file":
                                col_cat = st.selectbox("Chọn cột Danh mục", cols)
                            else:
                                fixed_cat = st.selectbox("Chọn danh mục chung", cat_out)

                        #  import 
                        if st.button("Bắt đầu nhập"):
                            count = 0
                            #loop row
                            for index, row in df_upload.iterrows():
                                try:
                                    # current row
                                    date_val = pd.to_datetime(row[col_date]).date()
                                    item_val = str(row[col_item])
                                    amount_val = float(row[col_amount])
                                    # cat_val = str(row[col_category])
                                    user_val = str(row[col_user])
                                    # xử lý cat
                                    if option_cat == "Lấy tên danh mục từ file":
                                        cat_val = str(row[col_cat])
                                    else:
                                        cat_val = fixed_cat
                                    
                                    # function call
                                    add_expense(user, item_val, amount_val, cat_val, date_val)
                                    count += 1
                                except Exception as e:
                                    st.error(f"Error at row {index}: {e}")

                            st.success(f"Đã thêm thành công {count} giao dịch.")
                            reload = st.button("Reload")
                            if reload:
                                st.rerun()
                    if 'ai_session' not in st.session_state:
                        st.session_state['ai_session']= None
                    with ai_serv:
                        st.caption("Mô hình AI được sử dụng: Gemini 2.5 Pro")
                        if st.button("Bắt đầu phân tích"):
                            with st.spinner("Đang tải..."):
                                csv_data = df_upload.to_csv(index=False)
                                ai_results = ai.ask_ai_to_parse(csv_data)


                                if ai_results:
                                    st.session_state['ai_session'] = pd.DataFrame(ai_results)
                                else:
                                    st.error("Không thể phân tích")
                        if st.session_state['ai_session'] is not None:
                                    
                            data_read_ai = st.session_state['ai_session']
                            edited_df = st.data_editor(data_read_ai, num_rows="dynamic")
                            st.write("Kết quả:")
            
                                    
                            if st.button("Lưu kết quả"):
                                count = 0
                                for idx, row in edited_df.iterrows():
                                # Kiểm tra column loại, cần phân biệt Thu nhập và Chi tiêu
                                    if row.get('type') == "Thu nhập":
                                        add_income(user, str(row['content']), float(row['amount']), str(row['category']), pd.to_datetime(row['date']).date())
                                        count+=1
                                    elif row.get('type') == "Chi tiêu":
                                        add_expense(user, str(row['content']), float(row['amount']), str(row['category']), pd.to_datetime(row['date']).date())
                                        count+=1
                                st.success(f"Đã thêm thành công {count} giao dịch.")
                            reload = st.button("Reload")
                            if reload:
                                st.session_state['ai_session'] = None
                                st.rerun()
                except Exception as e:
                    st.error(f"Lỗi đọc file: {e}")
if __name__ == '__main__':
    init_db()
    main()