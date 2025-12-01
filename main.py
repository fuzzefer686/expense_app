import streamlit as st
import sqlite3
import hashlib
import pandas as pd


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
def view_expenses(user):
    db = sqlite3.connect('expense_db.db')
    c=db.cursor()
    # pandas to display
    data_to_display = pd.read_sql_query("SELECT item_name as ten, category as danh_muc,date as ngay,amount as so_tien FROM expenses where owner=?", db, params=(user,))
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
        #set avatar user
        st.sidebar.write(f"Xin chào, **{user}**")
        butt=st.sidebar.button("Đăng xuất")
        if butt:
            st.session_state['logged_in'] = False
            st.rerun()

        # main app
        tab1,tab2=st.tabs(["Thêm khoản chi","Lịch sử chi tiêu"])
        # input form tab1
        with tab1:
            st.header("Thêm khoản chi")
            with st.form("expense_form"):
                st.write("Thêm khoản chi mới")
                col1, col2 = st.columns(2)
                with col1:
                    item_name = st.text_input("Tên khoản chi")
                with col2:
                    amount = st.number_input("Số tiền", min_value=0)

                category = st.selectbox("Danh mục", ["Ăn uống", "Di chuyển", "Nhà cửa", "Giải trí"])
                date = st.date_input("Ngày chi")

                submitted = st.form_submit_button("Thêm khoản chi")
                if submitted:
                    add_expense(user, item_name, amount, category,date)
                    st.success(f"Đã thêm: {item_name} {amount} VNĐ")
        with tab2:
            st.header("Lịch sử chi tiêu của bạn")
            data_to_display = view_expenses(user)
            if data_to_display.empty:
                st.info("Bạn chưa có khoản chi nào.")
            else:
                total_spent = data_to_display['so_tien'].sum()
                st.metric(label="Tổng chi",value=f"{total_spent:,.0f} VND")

                column_filter1,column_filter2=st.columns(2)
                with column_filter1:
                        #filter by categories
                        cat_filter=st.multiselect("Lọc theo danh mục",options=data_to_display['danh_muc'].unique(),default=[category])
                df=data_to_display[data_to_display['danh_muc'].isin(cat_filter)]#apply filter

                st.dataframe(df)

                st.subheader("Biểu đồ")
                chart=df.groupby("danh_muc")["so_tien"].sum()
                st.bar_chart(chart)

if __name__ == '__main__':
    init_db()
    main()