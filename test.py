import pyodbc
try:
    # Thử kết nối với server của bạn
    conn = pyodbc.connect('DRIVER={ODBC Driver 17 for SQL Server};SERVER=DESKTOP-TCP80HR\\SQLEXPRESS;DATABASE=PETCAREX;Trusted_Connection=yes;')
    print("KẾT NỐI THÀNH CÔNG!")
except Exception as e:
    print(f"LỖI KẾT NỐI: {e}")