import streamlit as st
import sqlite3
import hashlib
import pandas as pd
from datetime import datetime

# tao bang
def init_db():
    db = sqlite3.connect('expense_db.db')
    c = db.cursor()
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
        Create table if not exists income(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            owner TEXT,
            source text,
            amount REAL,
            category TEXT,
            date DATE
              )
              ''')
    db.commit()
    db.close()
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
    conn = sqlite3.connect('expense_db.db')
    c = conn.cursor()
    try:
        c.execute('INSERT into users(username, password) VALUES (?,?)',
                  (username, make_hashes(password)))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False  # Username đã tồn tại
    finally:
        conn.close()

# đăng nhập cho user
def login_user(username, password):
    conn = sqlite3.connect('expense_db.db')
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE username =? AND password = ?',
              (username, make_hashes(password)))
    data = c.fetchall()
    conn.close()
    return data


# funct expenses
def add_expense(owner, expense_name, amount, category, date):
    db=sqlite3.connect('expense_db.db')
    c=db.cursor()
    # bug fixed: 4 out of 5 columns
    c.execute('insert into expenses(owner, item_name, amount, category, date) values (?,?,?,?,?)',
        (owner,expense_name,amount,category,date))
    db.commit()
    db.close()

def add_income(owner, income_name, amount, category, date):
    db=sqlite3.connect('expense_db.db')
    c=db.cursor()
    # bug fixed: 4 out of 5 columns
    c.execute('insert into income(owner, source, amount, category, date) values (?,?,?,?,?)',
        (owner,income_name,amount,category,date))
    db.commit()
    db.close()

def view_expenses(user):
    db = sqlite3.connect('expense_db.db')
    c=db.cursor()
    # pandas to display
    data_to_display = pd.read_sql_query("SELECT item_name as ten, category as danh_muc,date as ngay,amount as so_tien FROM expenses where owner=?", db, params=(user,))
    db.close()
    return data_to_display
def view_income(user):
    db = sqlite3.connect('expense_db.db')
    c=db.cursor()
    # pandas to display
    data_to_display = pd.read_sql_query("SELECT source as ten, category as danh_muc,date as ngay,amount as so_tien FROM income where owner=?", db, params=(user,))
    db.close()
    return data_to_display
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
        st.title("Dashboard Tài Chính")

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
        tab1,tab2,tab3=st.tabs(["Thêm khoản chi","Lịch sử chi tiêu","Nhập từ file"])
        cat_out=["Ăn uống", "Di chuyển", "Nhà cửa", "Giải trí", "Khác"]
        cat_in=["Lương", "Hoa Hồng", "Nghề tay trái", "Rửa tiền","Khác"]
        # input form tab1
        with tab1:
            get_income,get_expense=st.columns(2)
            with get_expense:
                st.header("Thêm khoản chi")
                with st.form("expense_form"):
                    st.write("Thêm khoản chi mới")
                    col1, col2 = st.columns(2)
                    with col1:
                        item_name = st.text_input("Tên khoản chi")
                    with col2:
                        amount = st.number_input("Số tiền", min_value=0)

                    category = st.selectbox("Danh mục", cat_out)
                    date = st.date_input("Ngày chi")

                    submitted = st.form_submit_button("Thêm khoản chi")
                    if submitted:
                        add_expense(user, item_name, amount, category,date)
                        st.success(f"Đã thêm: -{item_name} {amount} VNĐ")
                        st.rerun()
            with get_income:
                st.header("Thêm khoản thu")
                with st.form("income_form"):
                    st.write("Thêm khoản thu mới")
                    col1, col2 = st.columns(2)
                    with col1:
                        source = st.text_input("Tên khoản thu")
                    with col2:
                        amount = st.number_input("Số tiền", min_value=0)

                    category = st.selectbox("Nguồn thu", cat_in)
                    # category = st.text_input("Nguồn tiền")
                    date = st.date_input("Ngày thu")

                    submitted = st.form_submit_button("Thêm khoản thu")
                    if submitted:
                        add_income(user, source, amount, category,date)
                        st.success(f"Đã thêm: + {source} {amount} VNĐ")
                        st.rerun()
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
            st.info("Hỗ trợ file .csv hoặc .xlsx. Dữ liệu sẽ được thêm vào bảng chi tiêu.")
            
            uploaded_file = st.file_uploader("Chọn file", type=['xlsx', 'csv'])
            
            if uploaded_file is not None:
                try:
                    if uploaded_file.name.endswith('.csv'):
                        df_upload = pd.read_csv(uploaded_file)
                    else:
                        df_upload = pd.read_excel(uploaded_file)
                    
                    st.write("Dữ liệu trong file của bạn (5 cột đầu tiên):")
                    st.dataframe(df_upload.head()) 

                    st.subheader("Chọn cột để lấy dữ liệu")
                    st.caption("Chọn cột trong file tương ứng với dữ liệu cần nhập")
                    
                    cols = df_upload.columns.tolist()
                    
                    col1, col2, col3, col4,col5,col6 = st.columns(6)
                    with col1:
                        col_user = st.selectbox("Cột Người dùng", cols)
                    with col2:
                        col_item = st.selectbox("Cột Nội dung", cols)
                    with col3:
                        col_amount = st.selectbox("Cột Số tiền", cols)
                    with col4:
                        col_category = st.selectbox("Cột danh mục",cols)
                    with col5:
                        col_date = st.selectbox("Cột ngày",cols)
                    with col6:
                        # choose category // for long code only=))
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
                                cat_val = str(row[col_category])
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

                except Exception as e:
                    st.error(f"Lỗi đọc file: {e}")
if __name__ == '__main__':
    init_db()
    main()