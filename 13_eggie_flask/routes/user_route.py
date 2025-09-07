from flask import Blueprint, request, jsonify
from mysql_config import get_mysql_connection

user_bp = Blueprint('user', __name__)

def serialize_user(row):
    return {
        'user_id': row['user_id'],
        'name': row['name'],
        'email': row['email'],
        'gender': row['gender'],
        'birth_date': row['birth_date'].isoformat() if row['birth_date'] else None,
        'created_at': row['created_at'].isoformat() if row['created_at'] else None,
    }

 # ✅ 단일 사용자 조회
 # curl http://localhost:5050/user/1
@user_bp.route('/user/<int:user_id>', methods=['GET'])
def get_user(user_id):
    conn = get_mysql_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()

    if user is None:
        return jsonify({'error': 'User not found'}), 404

    return jsonify(serialize_user(user))

 # ✅ 전체 사용자 목록 조회
 # curl http://localhost:5050/users
@user_bp.route('/users', methods=['GET'])
def get_all_users():
    conn = get_mysql_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM users")
    users = cursor.fetchall()
    cursor.close()
    conn.close()

    return jsonify([serialize_user(u) for u in users])