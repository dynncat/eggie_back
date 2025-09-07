from flask import Blueprint, Response, jsonify
import csv
import io
from mysql_config import get_mysql_connection

device_env_bp = Blueprint('device_env', __name__)

# 모델 input용 CSV 다운로드
# curl -o logs.csv http://localhost:5050/device-env/1
@device_env_bp.route('/device-env/<int:baby_id>', methods=['GET'])
def get_device_environment_logs_by_baby(baby_id):
    conn = get_mysql_connection()
    cursor = conn.cursor(dictionary=True)

    query = """
        WITH ordered_logs AS (
    SELECT 
        *,
        DATE(recorded_at) AS date_only,
        LAG(sleep_mode) OVER (
            PARTITION BY device_id, DATE(recorded_at)
            ORDER BY recorded_at
        ) AS prev_sleep_mode,
        ROW_NUMBER() OVER (
            PARTITION BY device_id, DATE(recorded_at)
            ORDER BY recorded_at
        ) AS row_num
    FROM device_environment_logs
    ),
    grouped_logs AS (
        SELECT 
            *,
            CASE 
                WHEN sleep_mode = prev_sleep_mode THEN 0 
                ELSE 1 
            END AS is_new_group
        FROM ordered_logs
    ),
    numbered_groups AS (
        SELECT 
            *,
            SUM(is_new_group) OVER (
                PARTITION BY device_id, date_only
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
    )
    SELECT 
        environment_log_id,
        recorded_at, -- 모드 시작 시간
        temperature,
        humidity,
        brightness,
        white_noise_level
    FROM final_seq
    WHERE device_id=1
    ORDER BY device_id, recorded_at
    LIMIT 100;
    """
    cursor.execute(query, (baby_id,))
    logs = cursor.fetchall()
    cursor.close()
    conn.close()

    # CSV 생성
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=logs[0].keys())
    writer.writeheader()
    writer.writerows(logs)

    csv_data = output.getvalue()
    output.close()

    return Response(
        csv_data,
        mimetype='text/csv',
        headers={"Content-Disposition": f"attachment;filename=device_env_logs_baby_{baby_id}.csv"}
    )


# final url = Uri.parse('${getBaseUrl()}/sleep-mode-report/1');
# final response = await http.get(url);
# if (response.statusCode == 200) {
#   List sleepReports = jsonDecode(response.body);
#   print(sleepReports); // [{sleep_mode: 밤잠2, start_time: ..., end_time: ...}, ...]
# }
# 낮잠 모드 + 순번, 모드 시작 시간 ~ 모드 끝 시간
@device_env_bp.route('/sleep-mode-format/<int:device_id>', methods=['GET'])
def get_sleep_mode_report(device_id):
    conn = get_mysql_connection()
    cursor = conn.cursor(dictionary=True)

    query = """
    WITH ordered_logs AS (
        SELECT 
            *,
            DATE(recorded_at) AS date_only,
            LAG(sleep_mode) OVER (
                PARTITION BY device_id, DATE(recorded_at)
                ORDER BY recorded_at
            ) AS prev_sleep_mode,
            ROW_NUMBER() OVER (
                PARTITION BY device_id, DATE(recorded_at)
                ORDER BY recorded_at
            ) AS row_num
        FROM device_environment_logs
    ),
    grouped_logs AS (
        SELECT 
            *,
            CASE 
                WHEN sleep_mode = prev_sleep_mode THEN 0 
                ELSE 1 
            END AS is_new_group
        FROM ordered_logs
    ),
    numbered_groups AS (
        SELECT 
            *,
            SUM(is_new_group) OVER (
                PARTITION BY device_id, date_only
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
    )
    SELECT
        fs.sleep_mode,
        fs.sleep_mode_seq,
        r.start_time,
        r.end_time,
        fs.recorded_at
    FROM final_seq fs
    JOIN report r
      ON fs.device_id = r.baby_id
     AND fs.recorded_at BETWEEN r.start_time AND r.end_time
    WHERE fs.device_id = %s
    ORDER BY fs.recorded_at DESC
    LIMIT 100
    """

    cursor.execute(query, (device_id,))

    rows = cursor.fetchall()

    def to_iso8601(dt):
        from pytz import timezone, UTC
        kst = timezone('Asia/Seoul')
        utc_dt = dt.replace(tzinfo=UTC)
        kst_dt = utc_dt.astimezone(kst)
        return kst_dt.isoformat()

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
            "recorded_at": to_iso8601(row["recorded_at"]),
            "end_time": to_iso8601(row["end_time"]) if row["end_time"] else None
        })

    cursor.close()
    conn.close()

    return jsonify(result)

# 날짜 필터링 사용이력 조회
@device_env_bp.route('/sleep-mode-format', methods=['GET'])
def get_sleep_mode_report_by_date():
    from datetime import datetime
    from flask import request

    device_id = int(request.args.get("device_id"))
    start_dt = datetime.strptime(request.args.get("start_dt"), "%Y-%m-%d")
    end_dt = datetime.strptime(request.args.get("end_dt"), "%Y-%m-%d")

    conn = get_mysql_connection()
    cursor = conn.cursor(dictionary=True)

    query = '''
    WITH ordered_logs AS (
        -- 1. device_environment_logs에서 각 로그에 대해 하루 기준 이전 로그의 sleep_mode를 가져옵니다.
        --    그리고 하루(device_id, date) 기준으로 정렬합니다.
        --    (성능을 위해 필요한 device_id와 날짜 범위로 미리 필터링)
        SELECT
            *,
            DATE(recorded_at) AS date_only,
            LAG(sleep_mode) OVER (
                PARTITION BY device_id, DATE(recorded_at)
                ORDER BY recorded_at
            ) AS prev_sleep_mode
        FROM device_environment_logs
        WHERE device_id = %s
          AND recorded_at >= %s
          AND recorded_at < %s
    ),
    grouped_logs AS (
        -- 2. 이전 로그와 현재 로그의 sleep_mode가 다르면 새로운 그룹 시작을 표시합니다.
        SELECT
            *,
            CASE
                WHEN sleep_mode = prev_sleep_mode THEN 0 -- 모드가 같으면 동일 그룹
                ELSE 1 -- 모드가 바뀌면 새 그룹 시작
            END AS is_new_group
        FROM ordered_logs
    ),
    mode_block_identified_logs AS (
        -- 3. 하루(device_id, date) 기준으로 새로운 그룹 시작 플래그를 누적하여 mode 그룹 식별자(mode_block_id)를 계산합니다.
        --    이 값은 같은 sleep_mode가 연속되는 블록을 구분합니다.
        SELECT
            *,
            SUM(is_new_group) OVER (
                PARTITION BY device_id, date_only
                ORDER BY recorded_at -- 시간 순으로 누적 합계를 계산
                ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
            ) AS mode_block_id -- 같은 모드가 연속되는 블록을 구분하는 ID (0부터 시작 가능)
        FROM grouped_logs
    ),
    logs_with_sequence AS (
        -- 4. mode_block_identified_logs에서 각 모드 블록(device_id, date_only, mode_block_id) 내에서 순번(sleep_mode_seq)을 계산합니다.
        --    이것이 원하시는 sleep_mode_seq (1부터 시작) 입니다.
        SELECT
            *,
            ROW_NUMBER() OVER (
                PARTITION BY device_id, date_only, mode_block_id -- 장치, 날짜, 모드 블록별로 파티션
                ORDER BY recorded_at -- 시간 순으로 순번 부여
            ) AS sleep_mode_seq -- 블록 내에서의 순번 (1부터 시작)
        FROM mode_block_identified_logs
    ),
    report_joined_logs AS (
        -- 5. report 테이블과 logs_with_sequence 테이블을 조인합니다.
        --    각 report의 start_time과 end_time 범위에 해당하는 모든 환경 로그를 가져옵니다.
        --    (report 테이블도 필요한 범위로 미리 필터링)
        SELECT
            r.rep_id,
            r.baby_id, -- baby_id (device_id와 동일)
            r.start_time, -- report 시작 시간 (잠 청크 시작)
            r.end_time,   -- report 종료 시간 (잠 청크 종료)
            lws.recorded_at, -- 환경 로그 기록 시간
            lws.sleep_mode, -- 해당 로그의 sleep_mode
            lws.sleep_mode_seq, -- 새로 계산된, 블록 내에서의 sleep_mode_seq
            lws.temperature,
            lws.humidity,
            lws.brightness,
            lws.white_noise_level
        FROM report r
        JOIN logs_with_sequence lws -- 올바른 sequence가 포함된 CTE와 조인
            ON r.baby_id = lws.device_id
        AND lws.recorded_at >= r.start_time
        AND lws.recorded_at < r.end_time -- end_time은 보통 포함하지 않음
        -- report 테이블 필터 (logs_with_sequence 필터와 일관성 유지)
        WHERE r.baby_id = %s
          AND r.start_time >= %s
          AND r.start_time < %s
    ),
    first_log_info AS (
    -- 6. 각 report (rep_id) 별로, 해당 report 기간 내 가장 먼저 기록된 환경 로그의 sleep_mode와 sleep_mode_seq를 찾습니다.
    --    이 값이 해당 report 청크의 대표 sleep_mode와 sleep_mode_seq가 됩니다.
        SELECT
            rep_id,
            sleep_mode AS report_sleep_mode,
            sleep_mode_seq AS report_sleep_mode_seq
        FROM (
            SELECT
                *,
                ROW_NUMBER() OVER(PARTITION BY rep_id ORDER BY recorded_at ASC) as rn
            FROM report_joined_logs
        ) AS T
        WHERE rn = 1
    ),
    avg_metrics AS (
        -- 7. 각 report (rep_id) 별로, 해당 report 기간 내 모든 환경 로그의 평균 값을 계산합니다.
    SELECT
        rep_id,
        AVG(temperature) AS avg_temperature,
        AVG(humidity) AS avg_humidity,
        AVG(brightness) AS avg_brightness,
        AVG(white_noise_level) AS avg_white_noise_level
    FROM report_joined_logs
    GROUP BY rep_id
    )
    -- 8. 원본 report 테이블, 첫 번째 로그 정보, 평균 환경 정보를 report ID로 조인하여 최종 결과를 만듭니다.
    --    rep_id 당 하나의 행만 조인되므로 GROUP BY가 필요 없습니다.
    SELECT
        r.start_time, -- 잠 시작 시간
        r.end_time,   -- 잠 끝 시간
        r.duration,   -- 잠 지속시간
        fli.report_sleep_mode AS sleep_mode, -- 낮잠/밤잠 모드
        fli.report_sleep_mode_seq AS sleep_mode_seq, -- 잠 순번
        am.avg_temperature, -- 잠 청크 내 평균 온도
        am.avg_humidity,    -- 잠 청크 내 평균 습도
        am.avg_brightness,  -- 잠 청크 내 평균 조도
        am.avg_white_noise_level -- 잠 청크 내 평균 백색소음
    FROM report r
    JOIN first_log_info fli ON r.rep_id = fli.rep_id
    JOIN avg_metrics am ON r.rep_id = am.rep_id
    WHERE r.baby_id = %s
      AND r.start_time >= %s
      AND r.start_time < %s
    ORDER BY r.start_time;
    '''

    cursor.execute(query, (device_id, start_dt, end_dt, device_id, start_dt, end_dt, device_id, start_dt, end_dt))
    rows = cursor.fetchall()

    def to_iso8601(dt):
        return dt.isoformat() if dt else None

    result = []
    for row in rows:
        result.append({
            "sleep_mode": f"{'낮잠' if row['sleep_mode'] == 'day' else '밤잠'}{row['sleep_mode_seq']}",
            "start_time": to_iso8601(row["start_time"]),
            "end_time": to_iso8601(row["end_time"]),
            "duration": row["duration"],
            "avg_temperature": row["avg_temperature"],
            "avg_humidity": row["avg_humidity"],
            "avg_brightness": row["avg_brightness"],
            "avg_white_noise_level": row["avg_white_noise_level"]
        })

    cursor.close()
    conn.close()

    return jsonify(result)

# final url = Uri.parse('${getBaseUrl()}/detailed-history/1');
# final response = await http.get(url);
# if (response.statusCode == 200) {
#   List<dynamic> data = jsonDecode(response.body);
#   print(data); // Flutter에서 필요한 항목만 골라서 사용
# }
# (상세 이력) 모드 시작 시간 + 온습조소 flutter에 보내주기~
@device_env_bp.route('/detailed-history/<int:device_id>', methods=['GET'])
def get_detailed_history(device_id):
    conn = get_mysql_connection()
    cursor = conn.cursor(dictionary=True)

    query = """
    WITH ordered_logs AS (
    SELECT 
        *,
        DATE(recorded_at) AS date_only,
        LAG(sleep_mode) OVER (
            PARTITION BY device_id, DATE(recorded_at)
            ORDER BY recorded_at
        ) AS prev_sleep_mode,
        ROW_NUMBER() OVER (
            PARTITION BY device_id, DATE(recorded_at)
            ORDER BY recorded_at
        ) AS row_num
    FROM device_environment_logs
    ),
    grouped_logs AS (
        SELECT 
            *,
            CASE 
                WHEN sleep_mode = prev_sleep_mode THEN 0 
                ELSE 1 
            END AS is_new_group
        FROM ordered_logs
    ),
    numbered_groups AS (
        SELECT 
            *,
            SUM(is_new_group) OVER (
                PARTITION BY device_id, date_only
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
    )
    SELECT 
        environment_log_id,
        sleep_mode, -- 낮잠/밤잠 모드
        sleep_mode_seq, -- 잠 순번
        recorded_at, -- 잠든 시간
        temperature,
        humidity,
        brightness,
        white_noise_level
    FROM final_seq
    WHERE device_id=%s
    ORDER BY device_id, recorded_at DESC
    LIMIT 500;
    """

    cursor.execute(query, (device_id,))
    rows = cursor.fetchall()

    cursor.close()
    conn.close()

    return jsonify(rows)
