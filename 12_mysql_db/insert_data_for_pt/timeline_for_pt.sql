-- [수면 타임라인 요약] 실제 잠 시작/끝 시간 + 지속시간 + 잠 모드/순번 + 
-- 예상 잠 시작/끝 시간 + 중간 깸 횟수

SELECT * FROM sleep_prediction_log;

SELECT
	expected_start_at,
    expected_end_at
FROM sleep_prediction_log
WHERE baby_id=6 
	AND prediction_date='2025-06-17';
    
    
WITH ordered_logs AS (
    -- 1. device_environment_logs에서 각 로그에 대해 하루 기준 이전 로그의 sleep_mode를 가져옵니다.
    --    그리고 하루(device_id, date) 기준으로 정렬합니다.
    --    (성능을 위해 필요한 device_id와 날짜 범위로 미리 필터링)
    SELECT
        *,
        DATE(recorded_at) AS date_only, -- 날짜 부분만 추출
        LAG(sleep_mode) OVER (
            PARTITION BY device_id, DATE(recorded_at)
            ORDER BY recorded_at
        ) AS prev_sleep_mode
    FROM device_environment_logs
    WHERE device_id = 6
      AND recorded_at >= '2025-06-17 00:00:00'
      AND recorded_at < '2025-06-18 00:00:00'
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
report_all_joined_logs AS (
    -- 5. report 테이블과 logs_with_sequence 테이블을 조인합니다.
    --    각 report의 start_time과 end_time 범위에 해당하는 모든 환경 로그를 가져옵니다.
    --    이 CTE는 해당 report에 속한 '모든' 환경 로그 정보를 담습니다.
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
       AND lws.recorded_at < r.end_time -- end_time은 보통 포함하지 않음
    -- report 테이블 필터 (필요한 report만 처리)
    WHERE r.baby_id = 6
      AND r.start_time >= '2025-06-17 00:00:00'
      AND r.start_time < '2025-06-18 00:00:00'
),
report_first_log AS (
    -- 6. report_all_joined_logs에서 각 report의 가장 첫 번째 로그의 정보를 찾습니다.
    --    이 정보가 해당 report의 sleep_mode와 sleep_mode_seq가 됩니다.
    --    (QUALIFY 대신 서브쿼리와 ROW_NUMBER() 사용)
    SELECT
        rep_id,
        sleep_mode AS report_sleep_mode, -- 이 report의 sleep_mode (가장 첫 로그 기준)
        sleep_mode_seq AS report_sleep_mode_seq -- 이 report의 sleep_mode_seq (가장 첫 로그 기준)
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
-- 7. report 테이블과 report_first_log CTE를 rep_id로 조인하여 최종 결과를 만듭니다.
--    sleep_prediction_log 테이블은 제외합니다.
SELECT
    r.start_time,           -- report의 실제 잠 시작 시간
    r.end_time,             -- report의 실제 잠 끝 시간
    r.duration,             -- report의 실제 잠 지속 시간
    r.breaks_count,         -- report의 실제 깨어난 횟수
    rfl.report_sleep_mode AS sleep_mode,      -- 이 잠 청크의 sleep_mode (가장 첫 로그 기준)
    rfl.report_sleep_mode_seq AS sleep_mode_seq -- 이 잠 청크의 sleep_mode_seq (가장 첫 로그 기준)
FROM report r
JOIN report_first_log rfl ON r.rep_id = rfl.rep_id -- report와 report_first_log 조인
-- 최종 결과에 대한 필터 (report_all_joined_logs 필터와 동일하게 유지)
WHERE r.baby_id = 6
  AND r.start_time >= '2025-06-17 00:00:00'
  AND r.start_time < '2025-06-18 00:00:00'
ORDER BY r.start_time;