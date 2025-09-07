SELECT * FROM report
WHERE baby_id=1;
SELECT * FROM sleep_prediction_log;

WITH ordered_logs AS (
    SELECT 
        *
    FROM device_environment_logs
    WHERE device_id = 1
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
            PARTITION BY date_only, group_number
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
    LEFT JOIN sleep_prediction_log spl
        ON r.rep_id = spl.rep_id
    WHERE r.baby_id = 1
)
SELECT
	rep_id, -- 리포트 아이디
    start_time, -- 실제 수면 시작 시간
    expected_end_at, -- 예상 수면 종료 시간
    sleep_mode, -- 낮잠/밤잠 모드
    sleep_mode_seq -- 잠 순번
FROM matched_logs
ORDER BY start_time DESC
LIMIT 10;