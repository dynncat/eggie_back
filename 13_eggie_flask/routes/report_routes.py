# routes/report_routes.py
from flask import Blueprint, request, jsonify
from datetime import datetime
from mysql_config import get_mysql_connection

report_bp = Blueprint('report', __name__)


# flutter 에서 POST 요청을 통해 리포트에 start_time INSERT
# import 'dart:convert';
# import 'package:http/http.dart' as http;

# Future<void> sendStartTime(DateTime startTime) async {
#   final baseUrl = getBaseUrl();
#   final url = Uri.parse('$baseUrl/report');

#   final response = await http.post(
#     url,
#     headers: {'Content-Type': 'application/json'},
#     body: jsonEncode({
#       "baby_id": 1,
#       "start_time": startTime.toIso8601String(),  // 예: 2025-06-02T17:04:31.332690
#     }),
#   );

#   if (response.statusCode == 200) {
#     print('등록 성공: ${response.body}');
#   } else {
#     print('등록 실패: ${response.body}');
#   }
# }
@report_bp.route('/report/<int:baby_id>', methods=['POST'])
def insert_report(baby_id):
    data = request.json
    start_time_str = data.get('start_time')

    try:
        start_time = datetime.fromisoformat(start_time_str).strftime("%Y-%m-%d %H:%M:%S")
    except ValueError as e:
        return jsonify({"error": f"날짜 형식 오류: {str(e)}"}), 400

    conn = get_mysql_connection()
    cursor = conn.cursor()

    # 1. report 테이블에 삽입
    query = """
        INSERT INTO report (baby_id, start_time)
        VALUES (%s, %s)
    """
    cursor.execute(query, (baby_id, start_time))
    inserted_id = cursor.lastrowid

    # 2. device_environment_logs 테이블에 recorded_at 업데이트
    update_query = """
        UPDATE device_environment_logs
        SET recorded_at = %s
        WHERE device_id = 6 AND recorded_at IS NULL
        ORDER BY environment_log_id ASC
        LIMIT 1;
    """
    cursor.execute(update_query, (start_time,))

    conn.commit()
    cursor.close()
    conn.close()

    return jsonify({"message": "Report inserted", "rep_id": inserted_id})



# flutter에서 end_time을 POST 요청으로 전송 후 duration 계산해 report 테이블에 업데이트
# Future<void> updateEndTimeForBaby1(DateTime endTime) async {
#   final url = Uri.parse('${getBaseUrl()}/report/end');

#   final response = await http.put(
#     url,
#     headers: {'Content-Type': 'application/json'},
#     body: jsonEncode({
#       "end_time": endTime.toIso8601String(),
#     }),
#   );

#   if (response.statusCode == 200) {
#     print('종료시간 업데이트 완료');
#   } else {
#     print('에러: ${response.body}');
#   }
# }
@report_bp.route('/report/<int:baby_id>/end', methods=['PUT'])
def update_latest_report_end_time(baby_id):
    data = request.json
    end_time_str = data.get('end_time')

    if not end_time_str:
        return jsonify({"error": "end_time is required"}), 400

    try:
        # ISO 형식 문자열 → MySQL DATETIME 형식으로 포맷
        end_time = datetime.fromisoformat(end_time_str).strftime("%Y-%m-%d %H:%M:%S")
    except ValueError as e:
        return jsonify({"error": f"Invalid datetime format: {str(e)}"}), 400

    conn = get_mysql_connection()
    cursor = conn.cursor()

    query = """
        UPDATE report
        JOIN (
            SELECT rep_id
            FROM report
            WHERE baby_id = %s
            ORDER BY start_time DESC
            LIMIT 1
        ) AS latest
        ON report.rep_id = latest.rep_id
        SET 
            end_time = %s,
            duration = TIMESTAMPDIFF(MINUTE, start_time, %s)
    """

    cursor.execute(query, (baby_id, end_time, end_time))
    conn.commit()
    cursor.close()
    conn.close()

    return jsonify({"message": f"Latest report updated for baby_id={baby_id}"})