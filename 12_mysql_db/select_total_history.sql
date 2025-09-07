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
    -- 필요한 device_id와 날짜 범위 필터링
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
    WHERE r.baby_id = 1
      AND r.start_time >= '2024-09-16 00:00:00'
      AND r.start_time < '2024-09-17 00:00:00'
),
first_log_info AS (
    -- 6. 각 report (rep_id) 별로, 해당 report 기간 내 가장 먼저 기록된 환경 로그의 sleep_mode와 sleep_mode_seq를 찾습니다.
    --    이 값이 해당 report 청크의 대표 sleep_mode와 sleep_mode_seq가 됩니다.
    SELECT
        rep_id,
        sleep_mode AS report_sleep_mode, -- 첫 번째 로그의 sleep_mode (이 잠 청크의 모드)
        sleep_mode_seq AS report_sleep_mode_seq -- 첫 번째 로그의 sleep_mode_seq (이 잠 청크의 하루/블록 내 순번)
    FROM (
        SELECT
            *,
            ROW_NUMBER() OVER(PARTITION BY rep_id ORDER BY recorded_at ASC) as rn -- rep_id 별로 기록 시간 순서대로 순번 부여
        FROM report_joined_logs
    ) AS T
    WHERE rn = 1 -- 첫 번째 로그만 선택
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
    r.start_time, -- report의 잠 시작 시간 (원본 report 테이블에서 가져옴)
    r.end_time,   -- report의 잠 끝 시간 (원본 report 테이블에서 가져옴)
    r.duration,
    fli.report_sleep_mode AS sleep_mode, -- 이 잠 청크의 sleep_mode (시작점 기준)
    fli.report_sleep_mode_seq AS sleep_mode_seq, -- 이 잠 청크의 sleep_mode_seq (시작점 기준, 하루/블록 내 순번)
    am.avg_temperature, -- 이 잠 청크 내 평균 온도
    am.avg_humidity,    -- 이 잠 청크 내 평균 습도
    am.avg_brightness,  -- 이 잠 청크 내 평균 조도
    am.avg_white_noise_level -- 이 잠 청크 내 평균 백색소음
FROM report r -- 원본 report 테이블 사용
JOIN first_log_info fli ON r.rep_id = fli.rep_id -- 첫 번째 로그 정보와 조인
JOIN avg_metrics am ON r.rep_id = am.rep_id -- 평균 환경 정보와 조인
-- 필요한 report만 선택 (이미 CTE에서 필터링되었지만, 명시적으로)
WHERE r.baby_id = 1
  AND r.start_time >= '2024-09-16 00:00:00'
  AND r.start_time < '2024-09-17 00:00:00'
ORDER BY r.start_time; -- report 시작 시간 기준으로 정렬