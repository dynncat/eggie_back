from flask import Blueprint, request, jsonify
from mysql_config import get_mysql_connection
from datetime import datetime

# Blueprint 선언
sleep_schedule_bp = Blueprint('sleep_schedule', __name__)

@sleep_schedule_bp.route('/sleep-schedule', methods=['GET'])
def get_sleep_schedule():
    device_id = int(request.args.get("device_id"))
    date_str = request.args.get("date")  # YYYY-MM-DD

    conn = get_mysql_connection()
    cursor = conn.cursor(dictionary=True)

    # Step 1: 오늘 사용 내역 마지막 recorded_at 조회
    last_usage_query = """
        SELECT MAX(recorded_at) as last_usage_time
        FROM device_environment_logs
        WHERE device_id = %s
          AND DATE(recorded_at) = %s
    """
    cursor.execute(last_usage_query, (device_id, date_str))
    last_usage_result = cursor.fetchone()
    last_usage_time = last_usage_result['last_usage_time']
    if last_usage_time is None:
        last_usage_time = f"{date_str} 00:00:00"

    # Step 2: 예측 스케줄 조회
    sleep_schedule_query = """
        SELECT expected_start_at, expected_end_at
        FROM sleep_prediction_log
        WHERE baby_id = (
            SELECT baby_id
            FROM device_subscribe_logs
            WHERE device_id = %s AND is_subscription_active = 1
            LIMIT 1
        )
        AND DATE(prediction_date) = %s
        AND expected_start_at > %s
        ORDER BY expected_start_at ASC
    """
    cursor.execute(sleep_schedule_query, (device_id, date_str, last_usage_time))
    rows = cursor.fetchall()

    # 낮잠/밤잠 태그 함수
    def get_sleep_mode_by_time(dt):
        hour = dt.hour
        if 6 <= hour < 20:
            return '낮잠'
        else:
            return '밤잠'

    result = []
    for idx, row in enumerate(rows, start=1):
        start_dt = row['expected_start_at']
        sleep_mode_label = get_sleep_mode_by_time(start_dt) + str(idx)
        result.append({
            "sleep_mode": sleep_mode_label,
            "expected_start_at": row["expected_start_at"],
            "expected_end_at": row["expected_end_at"]
        })

    cursor.close()
    conn.close()

    return jsonify(result)