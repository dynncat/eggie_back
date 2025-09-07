import mysql.connector

# 제공받은 mysql connection
def get_mysql_connection():
    return mysql.connector.connect(
        host='your-db-host-name',  # ✅ 외부 MySQL 서버 주소
        port=1234,
        user='your-db-user-name',            # ✅ 사용자 ID
        password='your-db-password',              # ✅ 비밀번호
        database='your-db-name'         # ✅ 연결할 DB 이름 (테이블 존재 여부 확인 필요)
    )