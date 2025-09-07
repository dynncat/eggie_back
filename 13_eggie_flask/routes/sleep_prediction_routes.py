# routes/sleep_prediction_log_routes.py
from flask import Blueprint, jsonify
from mysql_config import get_mysql_connection

sleep_prediction_bp = Blueprint('sleep_prediction', __name__)



# final url = Uri.parse('${getBaseUrl()}/sleep-session-summary/1');
# final response = await http.get(url);

# if (response.statusCode == 200) {
#   List<dynamic> data = jsonDecode(response.body);
#   print(data); 
#   // [
#   //   { sleep_mode: "밤잠1", start_time: ..., expected_end_at: ... },
#   //   ...
#   // ]
# }
# 남은 잠 타이머: 실제 수면 시작 시간 + 예상 수면 종료 시간 + 낮잠 모드/순번
@sleep_prediction_bp.route('/sleep-session-summary/<int:baby_id>', methods=['GET'])
def get_sleep_session_summary(baby_id):
    conn = get_mysql_connection()
    cursor = conn.cursor(dictionary=True)

    query = """
    WITH ordered_logs AS (
        SELECT 
            *
        FROM device_environment_logs
        WHERE device_id = %s
    ),
    ordered_with_window AS (
        SELECT 
            *,
            DATE(recorded_at) AS date_only,
            LAG(sleep_mode) OVER (
                PARTITION BY DATE(recorded_at)
                ORDER BY recorded_at
            ) AS prev_sleep_mode,
            ROW_NUMBER() OVER (
                PARTITION BY DATE(recorded_at)
                ORDER BY recorded_at
            ) AS row_num
        FROM ordered_logs
    ),
    grouped_logs AS (
        SELECT 
            *,
            CASE WHEN sleep_mode = prev_sleep_mode THEN 0 ELSE 1 END AS is_new_group
        FROM ordered_with_window
    ),
    numbered_groups AS (
        SELECT 
            *,
            SUM(is_new_group) OVER (
                PARTITION BY date_only
                ORDER BY row_num
                ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
            ) AS group_number
        FROM grouped_logs
    ),
    final_seq AS (
        SELECT 
            *,
            ROW_NUMBER() OVER (
            PARTITION BY device_id, date_only, sleep_mode, group_number
            ORDER BY recorded_at
            ) AS sleep_mode_seq
        FROM numbered_groups
    ),
    matched_logs AS (
        SELECT 
            fs.device_id,
            fs.sleep_mode,
            fs.sleep_mode_seq,
            r.rep_id,
            r.start_time,
            spl.expected_end_at
        FROM final_seq fs
        JOIN report r
            ON fs.device_id = r.baby_id
           AND fs.recorded_at BETWEEN r.start_time AND r.end_time
        INNER JOIN sleep_prediction_log spl
            ON r.rep_id = spl.rep_id
        WHERE r.baby_id = %s
    )
    SELECT 
        start_time,
        expected_end_at,
        sleep_mode,
        sleep_mode_seq
    FROM matched_logs
    ORDER BY start_time DESC
    LIMIT 10;
    """

    cursor.execute(query, (baby_id, baby_id))
    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    def format_sleep_mode(mode, seq):
        if mode == 'day':
            return f"낮잠{seq}"
        elif mode == 'night':
            return f"밤잠{seq}"
        else:
            return f"기타{seq}"

    result = []
    for row in rows:
        result.append({
            "sleep_mode": format_sleep_mode(row["sleep_mode"], row["sleep_mode_seq"]),
            "start_time": row["start_time"],
            "expected_end_at": row["expected_end_at"]
        })

    return jsonify(result)