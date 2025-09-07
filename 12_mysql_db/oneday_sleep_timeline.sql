SELECT COUNT(rep_id) FROM sleep_prediction_log
WHERE baby_id = 1
	AND expected_start_at >= '2024-09-16 00:00:00'
	AND expected_start_at < '2024-09-17 00:00:00';
SELECT COUNT(rep_id) FROM report
WHERE baby_id=1
	AND start_time >= '2024-09-16 00:00:00'
    AND start_time < '2024-09-17 00:00:00';
    
SET time_zone = '+09:00';
SELECT NOW();

WITH ordered_logs AS (
    -- 1. device_environment_logs에서 각 로그에 대해 하루 기준 이전 로그의 sleep_mode를 가져옵니다.
    --    그리고 하루(device_id, date) 기준으로 정렬합니다.
    SELECT
        *,
        DATE(recorded_at) AS date_only,
        LAG(sleep_mode) OVER (
            PARTITION BY device_id, DATE(recorded_at)
            ORDER BY recorded_at
        ) AS prev_sleep_mode
    FROM device_environment_logs
    WHERE device_id = 1 
		AND recorded_at >= '2024-09-16 00:00:00'
        AND recorded_at < '2024-09-17 00:00:00'
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
    SELECT
        *,
        ROW_NUMBER() OVER (
            PARTITION BY device_id, date_only, mode_block_id
            ORDER BY recorded_at -- 시간 순으로 순번 부여
        ) AS sleep_mode_seq -- 블록 내에서의 순번 (1부터 시작)
    FROM mode_block_identified_logs
),
report_all_joined_logs AS (
    -- 5. report 테이블과 logs_with_sequence 테이블을 조인합니다.
    SELECT
        r.rep_id,
        r.baby_id,
        r.start_time,
        r.end_time,
        lws.recorded_at,
        lws.sleep_mode,
        lws.sleep_mode_seq -- 계산된 sleep_mode_seq
    FROM report r
    JOIN logs_with_sequence lws
        ON r.baby_id = lws.device_id
       AND lws.recorded_at >= r.start_time
       AND lws.recorded_at < r.end_time
    WHERE r.baby_id = 1
      AND r.start_time >= '2024-09-16 00:00:00'
      AND r.start_time < '2024-09-17 00:00:00'
),
report_first_log AS (
    -- 6. report_all_joined_logs에서 각 report의 가장 첫 번째 로그의 정보를 찾습니다.
    SELECT
        rep_id,
        sleep_mode AS report_sleep_mode,
        sleep_mode_seq AS report_sleep_mode_seq
    FROM (
        SELECT
            rep_id,
            sleep_mode,
            sleep_mode_seq,
            ROW_NUMBER() OVER(PARTITION BY rep_id ORDER BY recorded_at ASC) as rn -- rep_id 별로 기록 시간 순서대로 순번 부여
        FROM report_all_joined_logs
    ) AS T
    WHERE rn = 1 -- 첫 번째 로그만 선택
)
-- 7. report 테이블, sleep_prediction_log 테이블, 그리고 report_first_log CTE를 rep_id로 조인합니다.
--    report와 sleep_prediction_log는 rep_id가 일치하는 경우만 가져옵니다 (INNER JOIN).
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
JOIN sleep_prediction_log spl ON r.rep_id = spl.rep_id -- rep_id 일치하는 report와 prediction 조인
JOIN report_first_log rfl ON r.rep_id = rfl.rep_id
WHERE r.baby_id = 1
  AND r.start_time >= '2024-09-16 00:00:00'
  AND r.start_time < '2024-09-17 00:00:00'
ORDER BY r.start_time; -- report 시작 시간 기준으로 정렬