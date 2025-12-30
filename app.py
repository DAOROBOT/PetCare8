import streamlit as st
import pyodbc
import pandas as pd
from datetime import date

# --- CẤU HÌNH ---
DB_CONFIG = {
    'driver': '{ODBC Driver 17 for SQL Server}',
    'server': r'(local)\SQLEXPRESS', # Sửa đúng tên server của bạn
    'database': 'PETCAREX',
    'trusted_connection': 'yes'
}

def get_connection():
    return pyodbc.connect(
        f"DRIVER={DB_CONFIG['driver']};SERVER={DB_CONFIG['server']};"
        f"DATABASE={DB_CONFIG['database']};Trusted_Connection={DB_CONFIG['trusted_connection']}"
    )

def run_query(query, params=None):
    with get_connection() as conn:
        return pd.read_sql(query, conn, params=params)

def execute_sp(sql, params):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(sql, params)
        conn.commit()

# --- UI ---
st.set_page_config(page_title="PetCareX System", layout="wide", page_icon="🐾")
st.title("🐾 HỆ THỐNG QUẢN LÝ THÚ CƯNG PETCAREX")

menu = ["Khách hàng", "Bác sĩ", "Nhân viên", "Quản lý"]
role = st.sidebar.selectbox("Đăng nhập với vai trò:", menu)


# 1. KHÁCH HÀNG
if role == "Khách hàng":
    st.header("Cổng thông tin Khách hàng")
    tab1, tab2 = st.tabs(["Đặt lịch khám", "Lịch sử mua hàng"])
    
    with tab1:
        st.subheader("Đăng ký lịch khám bệnh")
        with st.form("booking_form"):
            cccd = st.text_input("Nhập CCCD của bạn (VD: 001):")
            ma_tc = st.text_input("Nhập Mã thú cưng (VD: TC01):")
            ngay_kham = st.date_input("Ngày muốn khám:", min_value=date.today())
            trieu_chung = st.text_area("Mô tả triệu chứng:")
            submit = st.form_submit_button("Đặt lịch ngay")
            
            if submit:
                try:
                    # Gọi SP đã fix logic kiểm tra chủ sở hữu
                    execute_sp("{CALL sp_DatLichKham (?, ?, ?, ?)}", (cccd, ma_tc, ngay_kham, trieu_chung))
                    st.success("✅ Đặt lịch thành công! Bác sĩ đã nhận được yêu cầu.")
                except Exception as e:
                    # Hiển thị lỗi từ SQL Server (VD: Thú cưng không thuộc về khách)
                    st.error(f"❌ Không thể đặt lịch: {e}")

    with tab2:
        cccd_his = st.text_input("Nhập CCCD để tra cứu lịch sử:", key="his")
        if st.button("Tra cứu"):
            df = run_query("SELECT * FROM HOA_DON WHERE CCCD_KHACH_HANG = ?", (cccd_his,))
            st.dataframe(df)


# 2. BÁC SĨ 

elif role == "Bác sĩ":
    st.header("Cổng làm việc Bác sĩ")
    
    col1, col2 = st.columns([1, 2])
    with col1:
        st.subheader("Danh sách chờ khám")
        # Lấy các phiếu chưa có chẩn đoán
        df_wait = run_query("""
            SELECT P.MA_PHIEU_DICH_VU, K.HO_TEN, T.TEN as THU_CUNG, KB.TRIEU_CHUNG 
            FROM PHIEU_SU_DUNG_DICH_VU P
            JOIN KHACH K ON P.MA_KHACH_HANG = K.CCCD
            JOIN THU_CUNG T ON P.MA_THU_CUNG = T.MA_THU_CUNG
            JOIN DICH_VU_KHAM_BENH KB ON P.MA_PHIEU_DICH_VU = KB.MA_PHIEU_DICH_VU
            WHERE KB.CHUAN_DOAN IS NULL
        """)
        st.dataframe(df_wait)

    with col2:
        st.subheader("Chẩn đoán & Kê toa")
        with st.form("doctor_form"):
            ma_phieu = st.text_input("Nhập Mã phiếu dịch vụ:")
            chuan_doan = st.text_area("Kết luận chẩn đoán:")
            
            # Lấy danh sách thuốc để bác sĩ chọn (Dropdown)
            df_thuoc = run_query("SELECT MA_SAN_PHAM, TEN_SAN_PHAM FROM SAN_PHAM WHERE LOAI_SAN_PHAM = 'Thuoc'")
            thuoc_options = {row['TEN_SAN_PHAM']: row['MA_SAN_PHAM'] for index, row in df_thuoc.iterrows()}
            chon_thuoc = st.selectbox("Kê thuốc:", list(thuoc_options.keys()))
            
            submit_bs = st.form_submit_button("Lưu bệnh án")
            
            if submit_bs:
                try:
                    ma_thuoc = thuoc_options[chon_thuoc]
                    execute_sp("{CALL sp_BacSiChanDoan (?, ?, ?)}", (ma_phieu, chuan_doan, ma_thuoc))
                    st.success("✅ Đã cập nhật bệnh án và kê toa!")
                except Exception as e:
                    st.error(f"Lỗi: {e}")


# 3. NHÂN VIÊN (NHẬP LIỆU KHÁCH & THÚ CƯNG)
elif role == "Nhân viên":
    st.header("Reception - Quản lý hồ sơ")
    tab_k, tab_tc = st.tabs(["Thêm Khách Hàng Mới", "Thêm Thú Cưng Mới"])
    
    with tab_k:
        with st.form("add_customer"):
            st.write("Thông tin khách hàng")
            new_cccd = st.text_input("CCCD:")
            new_name = st.text_input("Họ tên:")
            new_email = st.text_input("Email:")
            new_gender = st.selectbox("Giới tính", ["Nam", "Nữ"])
            new_phone = st.text_input("Số điện thoại:")
            
            if st.form_submit_button("Tạo hồ sơ khách hàng"):
                try:
                    execute_sp("{CALL sp_ThemKhachHang (?, ?, ?, ?, ?)}", 
                               (new_cccd, new_name, new_email, new_gender, new_phone))
                    st.success(f"Đã thêm khách hàng {new_name}!")
                except Exception as e:
                    st.error(f"Lỗi: {e}")

    with tab_tc:
        with st.form("add_pet"):
            st.write("Đăng ký thú cưng")
            pet_id = st.text_input("Mã thú cưng (VD: TC99):")
            pet_name = st.text_input("Tên thú cưng:")
            pet_type = st.selectbox("Loại:", ["Chó", "Mèo", "Khác"])
            owner_id = st.text_input("CCCD Chủ nuôi:")
            
            if st.form_submit_button("Thêm thú cưng"):
                try:
                    execute_sp("{CALL sp_ThemThuCung (?, ?, ?, ?)}", 
                               (pet_id, pet_name, pet_type, owner_id))
                    st.success(f"Đã thêm bé {pet_name} vào hệ thống!")
                except Exception as e:
                    st.error(f"Lỗi: {e}")


# 4. QUẢN LÝ
elif role == "Quản lý":
    st.header("📈 Dashboard Quản Trị")
    st.write("Thống kê doanh thu thời gian thực")
    if st.button("Cập nhật dữ liệu"):
        # Gọi lại SP doanh thu cũ
        df_rev = run_query("EXEC sp_BaoCaoDoanhThu '2023-01-01', '2025-12-31'")
        st.line_chart(df_rev.set_index('THOI_DIEM_LAP_HOA_DON')['TONG_DOANH_THU'])
        st.metric("Tổng doanh thu", f"{df_rev['TONG_DOANH_THU'].sum():,.0f} VND")