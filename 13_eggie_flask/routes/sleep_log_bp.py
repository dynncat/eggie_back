# routes/sleep_log_bp.py
from flask import Blueprint, jsonify, request
from mysql_config import get_mysql_connection
from datetime import datetime, timedelta
from pytz import timezone, UTC

sleep_log_bp = Blueprint('sleep_log', __name__)

@sleep_log_bp.route('/today-sleep-detail', methods=['GET'])
def get_today_sleep_detail():
    baby_id = int(request.args.get("baby_id", 1))  # 기본값 1
    
    # ✅ start_dt 파라미터가 있으면 해당 날짜 기준 조회, 없으면 오늘 날짜 기준 조회
    kst = timezone('Asia/Seoul')
    start_dt_str = request.args.get("start_dt")
    if start_dt_str:
        hardcoded_date = datetime.strptime(start_dt_str, "%Y-%m-%d")
        hardcoded_date = kst.localize(hardcoded_date)
        start_of_day = hardcoded_date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = start_of_day + timedelta(days=1)
    else:
        now_kst = datetime.now(tz=kst)
        start_of_day = now_kst.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = start_of_day + timedelta(days=1)
    
    start_of_day_kst = start_of_day
    end_of_day_kst = end_of_day

    conn = get_mysql_connection()
    cursor = conn.cursor(dictionary=True)

    # 시간대 보정 추가
    cursor.execute("SET time_zone = '+09:00'")

    query = """
        WITH ordered_logs AS (
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
            SELECT
                *,
                CASE
                    WHEN sleep_mode = prev_sleep_mode THEN 0
                    ELSE 1
                END AS is_new_group
            FROM ordered_logs
        ),
        mode_block_identified_logs AS (
            SELECT
                *,
                SUM(is_new_group) OVER (
                    PARTITION BY device_id, date_only
                    ORDER BY recorded_at
                    ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
                ) AS mode_block_id
            FROM grouped_logs
        ),
        logs_with_sequence AS (
            SELECT
                *,
                ROW_NUMBER() OVER (
                    PARTITION BY device_id, date_only, mode_block_id
                    ORDER BY recorded_at
                ) AS sleep_mode_seq
            FROM mode_block_identified_logs
        ),
        report_all_joined_logs AS (
            SELECT
                r.rep_id,
                r.baby_id,
                r.start_time,
                r.end_time,
                lws.recorded_at,
                lws.sleep_mode,
                lws.sleep_mode_seq
            FROM report r
            JOIN logs_with_sequence lws
                ON r.baby_id = lws.device_id
            AND lws.recorded_at >= r.start_time
            AND lws.recorded_at < r.end_time
            WHERE r.baby_id = %s
            AND r.start_time >= %s
            AND r.start_time < %s
        ),
        report_first_log AS (
            SELECT
                rep_id,
                sleep_mode AS report_sleep_mode,
                sleep_mode_seq AS report_sleep_mode_seq
            FROM (
                SELECT
                    rep_id,
                    sleep_mode,
                    sleep_mode_seq,
                    ROW_NUMBER() OVER(PARTITION BY rep_id ORDER BY recorded_at ASC) as rn
                FROM report_all_joined_logs
            ) AS T
            WHERE rn = 1
        )
        SELECT
            r.start_time,           -- 실제 잠 시작 시간
            r.end_time,             -- 실제 잠 끝 시간
            r.duration,             -- 실제 잠 지속 시간
            r.breaks_count,         -- 실제 깨어난 횟수
            rfl.report_sleep_mode AS sleep_mode,      -- 잠 청크의 sleep_mode
            rfl.report_sleep_mode_seq AS sleep_mode_seq, -- 잠 청크의 sleep_mode_seq
            spl.expected_start_at,  -- 예측된 잠 시작 시간
            spl.expected_end_at     -- 예측된 잠 끝 시간
        FROM report r
        JOIN sleep_prediction_log spl ON r.rep_id = spl.rep_id
        JOIN report_first_log rfl ON r.rep_id = rfl.rep_id
        WHERE r.baby_id = %s
        AND r.start_time >= %s
        AND r.start_time < %s
        ORDER BY r.start_time;
        """

    cursor.execute(query, (
        baby_id, start_of_day_kst, end_of_day_kst,  # for ordered_logs
        baby_id, start_of_day_kst, end_of_day_kst,  # for report_all_joined_logs
        baby_id, start_of_day_kst, end_of_day_kst   # for final select
    ))
    rows = cursor.fetchall()

    # # ✅ 응답 확인용 print
    # print("✅ today-sleep-detail rows:", rows)
    result = []
    # print(f"✅ today-sleep-detail total rows: {len(rows)} → result len (before append): {len(result)}")
    for row in rows:
        try:
            # start_time, end_time → KST 변환
            utc_start = row['start_time'].replace(tzinfo=UTC)
            kst_start = utc_start.astimezone(kst)
            utc_end = row['end_time'].replace(tzinfo=UTC)
            kst_end = utc_end.astimezone(kst)

            duration_min = int((row['end_time'] - row['start_time']).total_seconds() / 60)

            sleep_mode = row["sleep_mode"]
            sleep_mode_seq = row["sleep_mode_seq"]
            sleep_mode_label = "낮잠" if sleep_mode == "day" else "밤잠"
            sleep_title = f"{sleep_mode_label} {sleep_mode_seq}"

            result.append({
                "startTime": kst_start.isoformat(),
                "endTime": kst_end.isoformat(),
                "durationMin": duration_min,
                "sleepMode": sleep_mode,
                "sleepModeSeq": sleep_mode_seq,
                "sleepTitle": sleep_title,
                "expectedStartAt": row["expected_start_at"].isoformat() if row["expected_start_at"] else None,
                "expectedEndAt": row["expected_end_at"].isoformat() if row["expected_end_at"] else None,
                "wakeCounts": row["breaks_count"] if row["breaks_count"] is not None else 0,
            })

        except Exception as e:
            print(f"❌ Error processing row: {row} → {e}")

    # Compute nap/night counts and durations
    nap_count = 0
    nap_duration_min = 0
    night_count = 0
    night_duration_min = 0

    for row in rows:
        if row['end_time'] is None:
            continue  # Skip rows without end_time
        duration_min = int((row['end_time'] - row['start_time']).total_seconds() / 60)
        if row['sleep_mode'] == 'day':
            nap_count += 1
            nap_duration_min += duration_min
        elif row['sleep_mode'] == 'night':
            night_count += 1
            night_duration_min += duration_min

    def format_duration(minutes):
        hours = minutes // 60
        mins = minutes % 60
        return f"{hours}시간 {mins}분"

    total_duration_min = nap_duration_min + night_duration_min

    result_payload = {
        "napCount": nap_count,
        "napDuration": format_duration(nap_duration_min),
        "nightCount": night_count,
        "nightDuration": format_duration(night_duration_min),
        "totalSleepDuration": format_duration(total_duration_min),
        "date": start_of_day.strftime('%Y-%m-%d'),
        "sleepRecords": result
    }

    cursor.close()
    conn.close()

    return jsonify(result_payload)

###################################
# 시연용 api
@sleep_log_bp.route('/today-sleep-detail-test', methods=['GET'])
def get_today_sleep_detail_test():
    baby_id = int(request.args.get("baby_id", 6))
    
    # ✅ 날짜 계산
    kst = timezone('Asia/Seoul')
    start_dt_str = request.args.get("start_dt")
    if start_dt_str:
        target_date = datetime.strptime(start_dt_str, "%Y-%m-%d")
        target_date = kst.localize(target_date)
    else:
        target_date = datetime.now(tz=kst)

    start_of_day = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_day = start_of_day + timedelta(days=1)

    conn = get_mysql_connection()
    cursor = conn.cursor(dictionary=True)

    ### 1번 쿼리: 실제 수면 기록 + 시퀀스 정보
    query_actual = """
        WITH ordered_logs AS (
            SELECT *, DATE(recorded_at) AS date_only,
                   LAG(sleep_mode) OVER (PARTITION BY device_id, DATE(recorded_at) ORDER BY recorded_at) AS prev_sleep_mode
            FROM device_environment_logs
            WHERE device_id = %(baby_id)s
              AND recorded_at >= %(start_dt)s
              AND recorded_at < %(end_dt)s
        ),
        grouped_logs AS (
            SELECT *,
                CASE WHEN sleep_mode = prev_sleep_mode THEN 0 ELSE 1 END AS is_new_group
            FROM ordered_logs
        ),
        mode_block_identified_logs AS (
            SELECT *,
                SUM(is_new_group) OVER (
                    PARTITION BY device_id, date_only
                    ORDER BY recorded_at ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
                ) AS mode_block_id
            FROM grouped_logs
        ),
        logs_with_sequence AS (
            SELECT *,
                   ROW_NUMBER() OVER (
                       PARTITION BY device_id, date_only, mode_block_id
                       ORDER BY recorded_at
                   ) AS sleep_mode_seq
            FROM mode_block_identified_logs
        ),
        report_all_joined_logs AS (
            SELECT r.rep_id, r.baby_id, r.start_time, r.end_time,
                   lws.recorded_at, lws.sleep_mode, lws.sleep_mode_seq
            FROM report r
            JOIN logs_with_sequence lws
              ON r.baby_id = lws.device_id
             AND lws.recorded_at >= r.start_time
             AND lws.recorded_at < r.end_time
            WHERE r.baby_id = %(baby_id)s
              AND r.start_time >= %(start_dt)s
              AND r.start_time < %(end_dt)s
        ),
        report_first_log AS (
            SELECT rep_id, sleep_mode AS report_sleep_mode, sleep_mode_seq AS report_sleep_mode_seq
            FROM (
                SELECT rep_id, sleep_mode, sleep_mode_seq,
                       ROW_NUMBER() OVER(PARTITION BY rep_id ORDER BY recorded_at ASC) as rn
                FROM report_all_joined_logs
            ) AS T
            WHERE rn = 1
        )
        SELECT r.start_time, r.end_time, r.duration,
               rfl.report_sleep_mode AS sleep_mode,
               rfl.report_sleep_mode_seq AS sleep_mode_seq
        FROM report r
        JOIN report_first_log rfl ON r.rep_id = rfl.rep_id
        WHERE r.baby_id = %(baby_id)s
          AND r.start_time >= %(start_dt)s
          AND r.start_time < %(end_dt)s
        ORDER BY r.start_time;
    """

    cursor.execute(query_actual, {
        "baby_id": baby_id,
        "start_dt": start_of_day,
        "end_dt": end_of_day
    })
    actual_rows = cursor.fetchall()

    ### 2번 쿼리: 예측 수면 기록
    query_pred = """
        SELECT expected_start_at, expected_end_at
        FROM sleep_prediction_log
        WHERE baby_id = %s
          AND prediction_date = %s
    """
    cursor.execute(query_pred, (baby_id, start_of_day.date()))
    pred_rows = cursor.fetchall()

    query_summary = """
        WITH ordered_logs AS (
            SELECT
                *,
                DATE(recorded_at) AS date_only,
                LAG(sleep_mode) OVER (
                    PARTITION BY device_id, DATE(recorded_at)
                    ORDER BY recorded_at
                ) AS prev_sleep_mode
            FROM device_environment_logs
            WHERE device_id = %(baby_id)s
              AND recorded_at >= %(start_dt)s
              AND recorded_at < %(end_dt)s
        ),
        grouped_logs AS (
            SELECT *,
                CASE WHEN sleep_mode = prev_sleep_mode THEN 0 ELSE 1 END AS is_new_group
            FROM ordered_logs
        ),
        mode_block_identified_logs AS (
            SELECT *,
                SUM(is_new_group) OVER (
                    PARTITION BY device_id, date_only
                    ORDER BY recorded_at
                    ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
                ) AS mode_block_id
            FROM grouped_logs
        ),
        logs_with_sequence AS (
            SELECT *,
                ROW_NUMBER() OVER (
                    PARTITION BY device_id, date_only, mode_block_id
                    ORDER BY recorded_at
                ) AS sleep_mode_seq
            FROM mode_block_identified_logs
        ),
        report_all_joined_logs AS (
            SELECT
                r.rep_id,
                r.baby_id,
                r.start_time,
                r.end_time,
                r.duration,
                lws.recorded_at,
                lws.sleep_mode,
                lws.sleep_mode_seq
            FROM report r
            JOIN logs_with_sequence lws
                ON r.baby_id = lws.device_id
               AND lws.recorded_at >= r.start_time
               AND lws.recorded_at < r.end_time
            WHERE r.baby_id = %(baby_id)s
              AND r.start_time >= %(start_dt)s
              AND r.start_time < %(end_dt)s
        ),
        report_first_log AS (
            SELECT
                rep_id,
                duration,
                sleep_mode AS report_sleep_mode,
                sleep_mode_seq AS report_sleep_mode_seq
            FROM (
                SELECT
                    rep_id,
                    duration,
                    sleep_mode,
                    sleep_mode_seq,
                    ROW_NUMBER() OVER(PARTITION BY rep_id ORDER BY recorded_at ASC) as rn
                FROM report_all_joined_logs
            ) AS T
            WHERE rn = 1
        )
        SELECT
            COUNT(CASE WHEN report_sleep_mode = 'day' THEN rep_id END) AS day_sleep_count,
            SUM(CASE WHEN report_sleep_mode = 'day' THEN duration ELSE 0 END) AS total_day_sleep_duration_minutes,
            COUNT(CASE WHEN report_sleep_mode = 'night' THEN rep_id END) AS night_sleep_count,
            SUM(CASE WHEN report_sleep_mode = 'night' THEN duration ELSE 0 END) AS total_night_sleep_duration_minutes
        FROM report_first_log;
    """

    cursor.execute(query_summary, {
        "baby_id": baby_id,
        "start_dt": start_of_day,
        "end_dt": end_of_day
    })
    summary_row = cursor.fetchone()

    nap_count = summary_row["day_sleep_count"] or 0
    nap_duration_min = summary_row["total_day_sleep_duration_minutes"] or 0
    night_count = summary_row["night_sleep_count"] or 0
    night_duration_min = summary_row["total_night_sleep_duration_minutes"] or 0

    # 총 수면 시간
    total_duration_min = nap_duration_min + night_duration_min

    def format_duration(mins):
        h, m = divmod(mins, 60)
        return f"{h}시간 {m}분"

    # Reconstruct result list with timezone and prediction info before building payload
    result = []
    for i, row in enumerate(actual_rows):
        try:
            utc_start = row['start_time'].replace(tzinfo=UTC)
            kst_start = utc_start.astimezone(kst)
            utc_end = row['end_time'].replace(tzinfo=UTC)
            kst_end = utc_end.astimezone(kst)

            duration_min = int((row['end_time'] - row['start_time']).total_seconds() / 60)

            pred_row = pred_rows[i] if i < len(pred_rows) else None

            result.append({
                "startTime": kst_start.isoformat(),
                "endTime": kst_end.isoformat(),
                "durationMin": duration_min,
                "sleepMode": row["sleep_mode"],
                "sleepModeSeq": row["sleep_mode_seq"],
                "expectedStartAt": pred_row["expected_start_at"].isoformat() if pred_row and pred_row["expected_start_at"] else None,
                "expectedEndAt": pred_row["expected_end_at"].isoformat() if pred_row and pred_row["expected_end_at"] else None,
                "wakeCounts": 0
            })

        except Exception as e:
            print(f"❌ Error processing row {i}: {e}")

    result_payload = {
        "napCount": int(nap_count),
        "napDuration": format_duration(int(nap_duration_min)),
        "nightCount": int(night_count),
        "nightDuration": format_duration(int(night_duration_min)),
        "totalSleepDuration": format_duration(int(total_duration_min)),
        "date": start_of_day.strftime('%Y-%m-%d'),
        "sleepRecords": result
    }

    cursor.close()
    conn.close()
    return jsonify(result_payload)
