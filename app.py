import streamlit as st
import pyodbc
import pandas as pd
from datetime import date

DB_CONFIG = {
    'driver': '{ODBC Driver 17 for SQL Server}',
    'server': r'(local)\SQLEXPRESS', # Thay bằng tên Server của cô
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

def execute_command(command, params):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(command, params)
        conn.commit()

# --- GIAO DIỆN CHÍNH ---
st.set_page_config(page_title="PetCareX System", layout="wide")
st.title("🐾 HỆ THỐNG QUẢN LÝ THÚ CƯNG PETCAREX")

# Menu phân quyền 
menu = ["Khách hàng", "Bác sĩ", "Nhân viên", "Quản lý"]
role = st.sidebar.selectbox("Chọn vai trò đăng nhập:", menu)

# --- 1. CHỨC NĂNG KHÁCH HÀNG ---
if role == "Khách hàng":
    st.header("👤 Cổng thông tin Khách hàng")
    tab1, tab2, tab3 = st.tabs(["Tìm kiếm & Mua hàng", "Đặt lịch khám", "Lịch sử"])
    
    with tab1: # Tìm kiếm & Đặt mua
        st.subheader("Tìm kiếm sản phẩm")
        keyword = st.text_input("Nhập tên sản phẩm (VD: Thức ăn)")
        if st.button("Tìm kiếm"):
            sql = "SELECT * FROM SAN_PHAM WHERE TEN_SAN_PHAM LIKE ?"
            df = run_query(sql, (f'%{keyword}%',))
            st.dataframe(df)
            
    with tab2: # Đặt lịch khám
        st.subheader("Đặt lịch khám bệnh")
        cccd = st.text_input("CCCD của bạn:")
        ma_tc = st.text_input("Mã thú cưng:")
        ngay_kham = st.date_input("Ngày mong muốn:")
        trieu_chung = st.text_area("Mô tả triệu chứng:")
        
        if st.button("Gửi yêu cầu đặt lịch"):
            try:
                # Gọi Stored Procedure sp_DatLichKham đã tạo ở Bước 2
                sql = "{CALL sp_DatLichKham (?, ?, ?, ?)}"
                execute_command(sql, (cccd, ma_tc, ngay_kham, trieu_chung))
                st.success("Đã đặt lịch thành công!")
            except Exception as e:
                st.error(f"Lỗi: {e}")

    with tab3: # Tra cứu lịch sử
        st.subheader("Lịch sử khám & Mua hàng")
        cccd_his = st.text_input("Nhập CCCD để tra cứu:")
        if st.button("Xem lịch sử"):
            st.write("Lịch sử hóa đơn:")
            st.dataframe(run_query("SELECT * FROM HOA_DON WHERE CCCD_KHACH_HANG = ?", (cccd_his,)))

# --- 2. CHỨC NĂNG BÁC SĨ---
elif role == "Bác sĩ":
    st.header("👨‍⚕️ Cổng làm việc Bác sĩ")
    
    st.subheader("Tra cứu hồ sơ bệnh án")
    ma_tc_bs = st.text_input("Nhập Mã thú cưng:")
    if st.button("Tra cứu hồ sơ"):
        sql = """
            SELECT P.THOI_GIAN_BAT_DAU, KB.TRIEU_CHUNG, KB.CHUAN_DOAN
            FROM PHIEU_SU_DUNG_DICH_VU P
            JOIN DICH_VU_KHAM_BENH KB ON P.MA_PHIEU_DICH_VU = KB.MA_PHIEU_DICH_VU
            WHERE P.MA_THU_CUNG = ?
        """
        df = run_query(sql, (ma_tc_bs,))
        if not df.empty:
            st.dataframe(df)
        else:
            st.warning("Chưa có lịch sử khám.")
            
    st.subheader("Tra cứu thuốc")
    if st.checkbox("Hiển thị danh mục thuốc"):
        st.dataframe(run_query("SELECT * FROM SAN_PHAM WHERE LOAI_SAN_PHAM = 'Thuoc'"))

# --- 3. CHỨC NĂNG NHÂN VIÊN---
elif role == "Nhân viên":
    st.header("staff Cổng Nhân viên Lễ tân")
    st.info("Chức năng: Tạo lịch khám trực tiếp & Xác định khách cũ/mới")
    
    check_cccd = st.text_input("Nhập CCCD khách đến:")
    if st.button("Kiểm tra khách hàng"):
        df = run_query("SELECT * FROM KHACH WHERE CCCD = ?", (check_cccd,))
        if not df.empty:
            st.success(f"Khách hàng cũ: {df.iloc[0]['HO_TEN']}")
        else:
            st.warning("Khách hàng mới. Vui lòng tạo hồ sơ.")

# --- 4. CHỨC NĂNG QUẢN LÝ ---
elif role == "Quản lý":
    st.header("📈 Báo cáo Quản trị")
    
    col1, col2 = st.columns(2)
    with col1: start = st.date_input("Từ ngày", date(2023,1,1))
    with col2: end = st.date_input("Đến ngày", date.today())
    
    if st.button("Xem thống kê doanh thu"):
        # Gọi SP BaoCaoDoanhThu đã tạo
        sql = "EXEC sp_BaoCaoDoanhThu ?, ?"
    
        sql_direct = f"""
            SELECT THOI_DIEM_LAP_HOA_DON, SUM(TONG_TIEN) as DOANH_THU 
            FROM HOA_DON 
            WHERE THOI_DIEM_LAP_HOA_DON BETWEEN '{start}' AND '{end}'
            GROUP BY THOI_DIEM_LAP_HOA_DON
            ORDER BY THOI_DIEM_LAP_HOA_DON
        """
        df = run_query(sql_direct)
        
        st.metric("Tổng doanh thu kỳ này", f"{df['DOANH_THU'].sum():,.0f} VNĐ")
        st.line_chart(df.set_index('THOI_DIEM_LAP_HOA_DON')['DOANH_THU'])
        st.dataframe(df)