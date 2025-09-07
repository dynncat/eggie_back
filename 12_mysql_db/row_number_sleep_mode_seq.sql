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
    environment_log_id,
    device_id,
    recorded_at,
    sleep_mode,
    sleep_mode_seq
FROM final_seq
ORDER BY device_id, recorded_at
LIMIT 100;