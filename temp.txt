import streamlit as st
import sqlite3
import hashlib
import pandas as pd
from datetime import datetime
import ai_service as ai
import threading

# --- 1. CẤU HÌNH DATABASE CHUẨN (Singleton + Thread Lock) ---

# Tạo một cái khóa (Lock) để bắt buộc các lệnh Ghi phải xếp hàng
# Ngăn chặn triệt để lỗi "Database is Locked"
db_lock = threading.Lock()

@st.cache_resource
def get_connection():
    """
    Tạo một kết nối duy nhất và giữ nó sống mãi (Cached Resource).
    Không bao giờ đóng kết nối này cho đến khi App tắt.
    """
    conn = sqlite3.connect('expense_db.db', check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL;") 
    return conn

def init_db():
    # Dùng lock để đảm bảo chỉ 1 người được tạo bảng 1 lúc
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

# --- 2. AUTH FUNCTIONS ---
def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_hashes(password, hashed_text):
    return make_hashes(password) == hashed_text

def create_user(username, password):
    with db_lock: # Khóa lại khi ghi
        conn = get_connection()
        c = conn.cursor()
        try:
            c.execute('INSERT INTO users(username, password) VALUES (?,?)',
                      (username, make_hashes(password)))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

def login_user(username, password):
    # Đọc thì không cần khóa quá chặt, nhưng nên dùng cursor mới
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE username =? AND password = ?',
              (username, make_hashes(password)))
    data = c.fetchall()
    return data

# --- 3. WRITE FUNCTIONS (QUAN TRỌNG: CÓ LOCK & COMMIT) ---

def add_expense(owner, expense_name, amount, category, date):
    with db_lock: # <--- BẮT BUỘC CÓ LOCK
        conn = get_connection()
        c = conn.cursor()
        c.execute('INSERT INTO expenses(owner, item_name, amount, category, date) VALUES (?,?,?,?,?)',
            (owner, expense_name, amount, category, date))
        conn.commit()
    st.cache_data.clear() # Xóa cache để dashboard cập nhật

def add_income(owner, income_name, amount, category, date):
    with db_lock: # <--- BẮT BUỘC CÓ LOCK
        conn = get_connection()
        c = conn.cursor()
        c.execute('INSERT INTO income(owner, source, amount, category, date) VALUES (?,?,?,?,?)',
            (owner, income_name, amount, category, date))
        conn.commit()
    st.cache_data.clear()

def del_record(table_name, record_id, owner):
    with db_lock: # <--- BẮT BUỘC CÓ LOCK
        conn = get_connection()
        c = conn.cursor()
        query = f"DELETE FROM {table_name} WHERE id=? AND owner=?"
        c.execute(query, (record_id, owner))
        conn.commit()
    st.cache_data.clear()

# --- 4. READ FUNCTIONS (KHÔNG COMMIT - DÙNG CACHE) ---

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
    conn = get_connection()
    if table_name == "expenses":
        query = "SELECT * FROM expenses WHERE owner=?"
    else:
        query = "SELECT * FROM income WHERE owner=?"
    return pd.read_sql_query(query, conn, params=(owner,))

# --- 5. MAIN GUI (Giữ nguyên logic của bạn) ---
def main():
    st.set_page_config(page_title="Quản Lý Chi Tiêu", layout="wide") # Thêm config này cho đẹp
    
    # Init DB ngay đầu chương trình
    init_db()

    st.title("Quản Lý Chi Tiêu Cá Nhân")
    
    if 'logged_in' not in st.session_state:
        st.session_state['logged_in'] = False
        st.session_state['username'] = ''

    # --- SIDEBAR LOGIN ---
    if not st.session_state['logged_in']:
        menu = ["Đăng Nhập", "Đăng Ký"]
        choice = st.sidebar.selectbox("Menu", menu)

        if choice == "Đăng Ký":
            st.subheader("Tạo tài khoản")
            new_user = st.text_input("Username")
            new_password = st.text_input("Password", type='password')
            if st.button("Đăng Ký"):
                if create_user(new_user, new_password):
                    st.success("Tạo thành công! Vui lòng đăng nhập.")
                else:
                    st.warning("Tài khoản đã tồn tại!")

        elif choice == "Đăng Nhập":
            st.subheader("Đăng nhập")
            username = st.text_input("Username")
            password = st.text_input("Password", type='password')
            if st.button("Login"):
                result = login_user(username, password)
                if result:
                    st.success(f"Chào mừng {username}!")
                    st.session_state['logged_in'] = True
                    st.session_state['username'] = username
                    st.rerun()
                else:
                    st.error("Sai thông tin đăng nhập")

    # --- MAIN APP ---
    else:
        user = st.session_state['username']
        st.sidebar.write(f"Xin chào, **{user}**")
        if st.sidebar.button("Đăng xuất"):
            st.session_state['logged_in'] = False
            st.rerun()

        # METRICS
        df_expense = view_expenses(user)
        df_income = view_income(user)

        total_expense = df_expense['so_tien'].sum() if not df_expense.empty else 0
        total_income = df_income['so_tien'].sum() if not df_income.empty else 0
        balance = total_income - total_expense
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Tổng Thu Nhập", f"{total_income:,.0f} VND")
        c2.metric("Tổng Chi Tiêu", f"{total_expense:,.0f} VND", delta="-") 
        c3.metric("Số Dư", f"{balance:,.0f} VND")
        
        # TABS
        tab1, tab4, tab2, tab3 = st.tabs(["➕ Thêm giao dịch", "✏️ Sửa/Xóa", "📊 Lịch sử", "📥 Nhập File"])
        
        cat_out = ["Ăn uống", "Di chuyển", "Nhà cửa", "Giải trí", "Khác"]
        cat_in = ["Lương", "Hoa Hồng", "Nghề tay trái", "Rửa tiền", "Khác"]

        # TAB 1: ADD
        with tab1:
            col_in, col_out = st.columns(2)
            with col_out:
                st.subheader("Thêm khoản chi")
                with st.form("expense_form", clear_on_submit=True):
                    item = st.text_input("Nội dung")
                    amt = st.number_input("Số tiền", min_value=0.0, step=1000.0)
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
                    amt = st.number_input("Số tiền", min_value=0.0, step=1000.0)
                    cat = st.selectbox("Loại thu", cat_in)
                    dt = st.date_input("Ngày thu")
                    if st.form_submit_button("Lưu thu nhập"):
                        add_income(user, src, amt, cat, dt)
                        st.toast(f"Đã nhận: +{amt:,.0f} đ", icon="💰")
                        st.rerun()

        # TAB 4: EDIT/DELETE
        with tab4:
            st.header("Quản lý giao dịch")
            opt = st.radio("Loại dữ liệu:", ["Chi tiêu", "Thu nhập"], horizontal=True)
            tbl = 'expenses' if opt == "Chi tiêu" else 'income'
            
            df_del = get_data_with_id(tbl, user)
            
            if not df_del.empty:
                select_all = st.checkbox("Chọn tất cả", key="sel_all")
                if select_all:
                    df_del['Delete'] = True
                elif 'Delete' not in df_del.columns:
                    df_del['Delete'] = False

                edited_df = st.data_editor(
                    df_del,
                    column_config={
                        "Delete": st.column_config.CheckboxColumn("Xóa?", default=False),
                        "id": st.column_config.NumberColumn("ID", disabled=True)
                    },
                    hide_index=True,
                    use_container_width=True
                )
                
                to_delete = edited_df[edited_df['Delete'] == True]
                
                if not to_delete.empty:
                    st.warning(f"Chọn xóa {len(to_delete)} dòng.")
                    if st.button("🚨 Xác nhận xóa"):
                        cnt = 0
                        for i, row in to_delete.iterrows():
                            del_record(tbl, row['id'], user)
                            cnt += 1
                        st.success(f"Đã xóa {cnt} dòng!")
                        st.rerun()
            else:
                st.info("Chưa có dữ liệu.")

        # TAB 2: HISTORY
        with tab2:
            st.subheader("Lịch sử")
            mode = st.radio("Xem:", ["Chi tiêu", "Thu nhập"], horizontal=True)
            if mode == "Chi tiêu":
                if not df_expense.empty:
                    st.dataframe(df_expense, use_container_width=True)
                    st.bar_chart(df_expense.groupby("danh_muc")['so_tien'].sum())
                else: st.info("Trống")
            else:
                if not df_income.empty:
                    st.dataframe(df_income, use_container_width=True)
                    st.bar_chart(df_income.groupby("danh_muc")['so_tien'].sum())
                else: st.info("Trống")

        # TAB 3: IMPORT
        with tab3:
            st.header("Import Excel/CSV")
            uploaded_file = st.file_uploader("Chọn file", type=['xlsx', 'csv'])
            
            if uploaded_file:
                try:
                    if uploaded_file.name.endswith('.csv'):
                        df_up = pd.read_csv(uploaded_file)
                    else:
                        df_up = pd.read_excel(uploaded_file)
                    
                    sub1, sub2 = st.tabs(["Thủ công", "AI Auto"])
                    
                    with sub1: # Manual
                        cols = df_up.columns.tolist()
                        c1, c2, c3, c4 = st.columns(4)
                        col_item = c1.selectbox("Cột Nội dung", cols)
                        col_amt = c2.selectbox("Cột Tiền", cols)
                        col_date = c3.selectbox("Cột Ngày", cols)
                        fixed_cat = c4.selectbox("Danh mục chung", cat_out)
                        
                        if st.button("Nhập dữ liệu (Thủ công)"):
                            count = 0
                            for i, row in df_up.iterrows():
                                try:
                                    dt = pd.to_datetime(row[col_date]).date()
                                    add_expense(user, str(row[col_item]), float(row[col_amt]), fixed_cat, dt)
                                    count += 1
                                except: pass
                            st.success(f"Đã nhập {count} dòng.")
                            st.rerun()

                    with sub2: # AI
                        if 'ai_ss' not in st.session_state:
                            st.session_state['ai_ss'] = None
                        
                        if st.button("✨ Phân tích AI"):
                            with st.spinner("AI đang đọc..."):
                                csv_txt = df_up.to_csv(index=False)
                                res = ai.ask_ai_to_parse(csv_txt)
                                if res:
                                    st.session_state['ai_ss'] = pd.DataFrame(res)
                                else:
                                    st.error("AI lỗi")
                        
                        if st.session_state['ai_ss'] is not None:
                            edited_ai = st.data_editor(st.session_state['ai_ss'], num_rows="dynamic")
                            if st.button("Lưu kết quả AI"):
                                cnt = 0
                                for i, row in edited_ai.iterrows():
                                    try:
                                        t = row.get('type', 'Chi tiêu')
                                        d = pd.to_datetime(row['date']).date()
                                        if t == "Thu nhập":
                                            add_income(user, row['content'], row['amount'], row['category'], d)
                                        else:
                                            add_expense(user, row['content'], row['amount'], row['category'], d)
                                        cnt += 1
                                    except: pass
                                st.success(f"Lưu {cnt} dòng!")
                                st.session_state['ai_ss'] = None
                                st.rerun()

                except Exception as e:
                    st.error(f"Lỗi file: {e}")

if __name__ == '__main__':
    main()