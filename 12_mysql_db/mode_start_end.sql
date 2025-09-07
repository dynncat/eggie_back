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
            PARTITION BY device_id, date_only, group_number
            ORDER BY recorded_at
        ) AS sleep_mode_seq
    FROM numbered_groups
)
SELECT
	fs.sleep_mode, -- 낮잠/밤잠 모드
    fs.sleep_mode_seq, -- 잠 순번
    fs.recorded_at, -- 잠 시작 시간
    r.end_time -- 잠 끝 시간
FROM final_seq fs
JOIN report r
ON fs.device_id = r.baby_id
	AND fs.recorded_at BETWEEN r.start_time AND r.end_time
WHERE fs.device_id=1
	AND fs.recorded_at >= '2024-09-16 00:00:00'
	AND fs.recorded_at < '2024-09-17 00:00:00' 
ORDER BY fs.recorded_at
LIMIT 30;