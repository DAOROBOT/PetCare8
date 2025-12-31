import streamlit as st
import pyodbc
import pandas as pd
from datetime import date

# --- CẤU HÌNH KẾT NỐI ---
DB_CONFIG = {
    'driver': '{ODBC Driver 17 for SQL Server}',
    'server': r'(local)\SQLEXPRESS', # Kiểm tra lại tên server của bạn lần cuối
    'database': 'PETCAREX',
    'trusted_connection': 'yes'
}

def get_connection():
    return pyodbc.connect(
        f"DRIVER={DB_CONFIG['driver']};SERVER={DB_CONFIG['server']};"
        f"DATABASE={DB_CONFIG['database']};Trusted_Connection={DB_CONFIG['trusted_connection']}"
    )

# Hàm chuyên để ĐỌC dữ liệu (SELECT)
def run_query(query, params=None):
    with get_connection() as conn:
        return pd.read_sql(query, conn, params=params)



def execute_sp(sql, params):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(sql, params)
        conn.commit() # Quan trọng: Phải commit thì DB mới lưu
        return True, "Thành công"
    except Exception as e:
        return False, str(e)
    finally:
        conn.close()

st.set_page_config(page_title="PetCareX Ultimate", layout="wide", page_icon="🐾")
st.title("HỆ THỐNG QUẢN LÝ THÚ CƯNG PETCAREX")

menu = ["Khách hàng", "Bác sĩ", "Nhân viên", "Quản lý"]
role = st.sidebar.selectbox("Vui lòng chọn vai trò:", menu)


# 1. KHÁCH HÀNG

if role == "Khách hàng":
    st.header("Cổng thông tin Khách hàng")
    tab1, tab2, tab3 = st.tabs(["Tra cứu sản phẩm", "Đặt lịch khám", "Lịch sử"])
    
    with tab1: # Tìm kiếm (READ)
        kw = st.text_input("Tìm sản phẩm:")
        if st.button("Tìm"):
            df = run_query("SELECT * FROM SAN_PHAM WHERE LOAI_SAN_PHAM LIKE ?", (f'%{kw}%',))
            st.dataframe(df)

    with tab2: # Đặt lịch (WRITE)
        with st.form("booking"):
            st.write("Điền thông tin đặt lịch")
            c_cccd = st.text_input("CCCD của bạn (12 số ví dụ 079090000001):")
            c_matc = st.text_input("Mã thú cưng:")
            c_ngay = st.date_input("Ngày khám:", min_value=date.today())
            c_trieuchung = st.text_input("Triệu chứng:")
            
            if st.form_submit_button("Gửi yêu cầu"):
                if len(c_cccd) != 12:
                    st.error("⚠️ CCCD phải đủ 12 số!")
                else:
                    status, msg = execute_sp("{CALL sp_DatLichKham (?, ?, ?, ?)}", (c_cccd, c_matc, c_ngay, c_trieuchung))
                    if status: st.success("✅ Đặt lịch thành công!")
                    else: st.error(f"❌ Lỗi: {msg}")

    with tab3: # Lịch sử (READ)
        his_cccd = st.text_input("Nhập CCCD để xem lịch sử:")
        if st.button("Xem lịch sử"):
            df = run_query("SELECT * FROM HOA_DON WHERE CCCD_KHACH_HANG = ?", (his_cccd,))
            st.dataframe(df)


# 2. BÁC SĨ 
elif role == "Bác sĩ":
    st.header("Cổng làm việc Bác sĩ")
    
    # Chia giao diện làm 2 cột: Trái (DS Chờ) - Phải (Xử lý)
    col_wait, col_action = st.columns([3, 2])
    
    with col_wait:
        st.subheader("Danh sách bệnh nhân chờ khám")
        # Query lấy các ca có CHUAN_DOAN là NULL
        query_wait = """
            SELECT P.MA_PHIEU_DICH_VU, K.HO_TEN AS CHU_NUOI, T.TEN AS THU_CUNG, KB.TRIEU_CHUNG 
            FROM PHIEU_SU_DUNG_DICH_VU P
            JOIN KHACH K ON P.MA_KHACH_HANG = K.CCCD
            JOIN THU_CUNG T ON P.MA_THU_CUNG = T.MA_THU_CUNG
            JOIN DICH_VU_KHAM_BENH KB ON P.MA_PHIEU_DICH_VU = KB.MA_PHIEU_DICH_VU
            WHERE KB.CHUAN_DOAN IS NULL
        """
        df_wait = run_query(query_wait)
        
        if not df_wait.empty:
            st.dataframe(df_wait, use_container_width=True)
            st.info("Đảm bảo MA_PHIEU_DICH_VU giống nhau")
        else:
            st.success("Tuyệt vời! Hiện tại không có bệnh nhân nào đang chờ.")
            
    with col_action:
        st.subheader("Nhập kết quả khám")
        with st.form("doctor_form"):
            ma_phieu = st.text_input("Điền Mã phiếu vào đây:", placeholder="VD: P999")
            chuan_doan = st.text_area("Kết luận chẩn đoán:", placeholder="VD: Viêm đường ruột...")
            
            # Chọn thuốc từ danh sách có sẵn
            df_thuoc = run_query("SELECT MA_SAN_PHAM, TEN_SAN_PHAM FROM SAN_PHAM WHERE LOAI_SAN_PHAM = 'Thuoc'")
            if not df_thuoc.empty:
                map_thuoc = {row['TEN_SAN_PHAM']: row['MA_SAN_PHAM'] for i, row in df_thuoc.iterrows()}
                chon_thuoc = st.selectbox("Kê thuốc:", list(map_thuoc.keys()))
            else:
                chon_thuoc = None
                st.warning("Kho thuốc đang trống.")

            if st.form_submit_button("Lưu bệnh án & Kê toa"):
                if ma_phieu and chon_thuoc:
                    ma_thuoc_chon = map_thuoc[chon_thuoc]
                    # Gọi SP xử lý
                    status, msg = execute_sp("{CALL sp_BacSiChanDoan (?, ?, ?)}", (ma_phieu, chuan_doan, ma_thuoc_chon))
                    if status: 
                        st.success("Đã lưu hồ sơ thành công!")
                        st.experimental_rerun() # Tự động load lại trang để cập nhật danh sách
                    else: st.error(f"Lỗi: {msg}")
                else:
                    st.error("Vui lòng nhập Mã phiếu!")


# 3. NHÂN VIÊN 
elif role == "Nhân viên":
    st.header("Quản lý Khách hàng & Thú cưng")
    
    tab_search, tab_add_cust, tab_add_pet = st.tabs(["Tra cứu", "Thêm Khách", "Thêm Thú Cưng"])
    
    with tab_search:
        st.write("Tra cứu thông tin khách hàng và thú cưng của họ.")
        search_cccd = st.text_input("Nhập CCCD khách:", placeholder="VD: 079090000001")
        if st.button("Tra cứu ngay"):
            # Lấy thông tin khách + SĐT 
            q_khach = """
                SELECT K.CCCD, K.HO_TEN, K.EMAIL, S.SO_DIEN_THOAI 
                FROM KHACH K 
                LEFT JOIN SODIENTHOAI_KHACHHANG S ON K.CCCD = S.KHACH_HANG
                WHERE K.CCCD = ?
            """
            df_k = run_query(q_khach, (search_cccd,))
            
            if not df_k.empty:
                st.success(f"Khách hàng: {df_k.iloc[0]['HO_TEN']}")
                st.table(df_k)
                
                st.write("Danh sách thú cưng:")
                df_tc = run_query("SELECT * FROM THU_CUNG WHERE CCCD = ?", (search_cccd,))
                if not df_tc.empty:
                    st.dataframe(df_tc)
                else:
                    st.info("Khách này chưa có thú cưng nào.")
            else:
                st.warning("Không tìm thấy khách hàng. Hãy tạo hồ sơ mới.")

    with tab_add_cust:
        with st.form("add_c"):
            st.subheader("Hồ sơ Khách hàng mới")
            n_cccd = st.text_input("CCCD (12 số):")
            n_ten = st.text_input("Họ tên:")
            n_email = st.text_input("Email:")
            n_sex = st.selectbox("Giới tính", ["Nam", "Nữ"])
            n_sdt = st.text_input("Số điện thoại:")
            
            if st.form_submit_button("Lưu Khách Hàng"):
                status, msg = execute_sp("{CALL sp_ThemKhachHang (?, ?, ?, ?, ?)}", (n_cccd, n_ten, n_email, n_sex, n_sdt))
                if status: st.success("✅ Thêm khách thành công!")
                else: st.error(f"❌ {msg}")

    with tab_add_pet:
        st.subheader("Hồ sơ Thú cưng mới (Đầy đủ)")
        with st.form("add_p_full"):
            # Chia làm 2 cột cho gọn đẹp
            c1, c2 = st.columns(2)
            with c1:
                p_ma = st.text_input("Mã thú cưng:", placeholder="VD: TC0000000001")
                p_ten = st.text_input("Tên thú cưng:", placeholder="VD: Milu")
                p_loai = st.selectbox("Loài:", ["Chó", "Mèo", "Chuột", "Khác"])
                p_giong = st.text_input("Giống loài:", placeholder="VD: Poodle, Mướp...")
            with c2:
                p_ngaysinh = st.date_input("Ngày sinh:", min_value=date(2000,1,1))
                p_gioitinh = st.selectbox("Giới tính thú:", ["Đực", "Cái"])
                p_suckhoe = st.text_input("Sức khỏe:", value="Bình thường")
                p_chunhan = st.text_input("CCCD Chủ nuôi:", placeholder="Nhập đúng 12 số CCCD")
            
            if st.form_submit_button("Lưu Thú Cưng"):
                # Gọi SP mới với đủ 8 tham số
                status, msg = execute_sp("{CALL sp_ThemThuCung (?, ?, ?, ?, ?, ?, ?, ?)}", 
                                         (p_ma, p_ten, p_loai, p_giong, p_ngaysinh, p_gioitinh, p_suckhoe, p_chunhan))
                if status: st.success("✅ Thêm thú cưng thành công! Hãy qua tab Tra cứu để kiểm tra.")
                else: st.error(f"❌ {msg}")

# 4. QUẢN LÝ 
elif role == "Quản lý":
    st.header("📈 Báo cáo Doanh thu")
    
    # Giao diện chọn ngày như bản V1 cũ
    c1, c2 = st.columns(2)
    with c1: d_start = st.date_input("Từ ngày", date(2023,1,1))
    with c2: d_end = st.date_input("Đến ngày", date.today())
    
    if st.button("Xem báo cáo"):
        # Gọi SP
        df = run_query(f"EXEC sp_BaoCaoDoanhThu '{d_start}', '{d_end}'")
        
        if not df.empty:
            # Tính tổng tiền
            total = df['TONG_DOANH_THU'].sum()
            st.metric("TỔNG DOANH THU KỲ NÀY", f"{total:,.0f} VND")
            
            # Vẽ biểu đồ
            st.line_chart(df.set_index('THOI_DIEM_LAP_HOA_DON')['TONG_DOANH_THU'])
            st.dataframe(df)
        else:
            st.warning("Không có dữ liệu trong khoảng thời gian này.")