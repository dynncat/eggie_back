WITH ordered_logs AS (
    SELECT
        *,
        DATE(recorded_at) AS date_only,
        LAG(sleep_mode) OVER (
            PARTITION BY device_id, DATE(recorded_at)
            ORDER BY recorded_at
        ) AS prev_sleep_mode
    FROM device_environment_logs
    WHERE device_id = 6
      AND recorded_at >= '2025-06-16 00:00:00'
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
        r.duration,
        lws.recorded_at,
        lws.sleep_mode,
        lws.sleep_mode_seq
    FROM report r
    JOIN logs_with_sequence lws
        ON r.baby_id = lws.device_id
       AND lws.recorded_at >= r.start_time
       AND lws.recorded_at < r.end_time
    WHERE r.baby_id = 6
      AND r.start_time >= '2025-06-16 00:00:00'
      AND r.start_time < '2025-06-17 00:00:00'
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
    WHERE rn = 1 -- 첫 번째 로그만 선택
)
-- 7. report_first_log CTE의 결과를 집계하여 낮잠/밤잠 개수와 총 시간을 계산합니다.
SELECT
    COUNT(CASE WHEN report_sleep_mode = 'day' THEN rep_id END) AS day_sleep_count,
    SUM(CASE WHEN report_sleep_mode = 'day' THEN duration ELSE 0 END) AS total_day_sleep_duration_minutes,
    COUNT(CASE WHEN report_sleep_mode = 'night' THEN rep_id END) AS night_sleep_count,
    SUM(CASE WHEN report_sleep_mode = 'night' THEN duration ELSE 0 END) AS total_night_sleep_duration_minutes
FROM report_first_log;