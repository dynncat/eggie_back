-- 1. 안전을 위해 세이프 모드를 일시적으로 해제합니다.
--    작업 완료 후 반드시 다시 활성화해야 합니다.
SET SESSION sql_safe_updates = 0;

-- 2. 특정 기간 내 report와 prediction_log에 각각 시간 순으로 순번을 매깁니다.
WITH RankedReports AS (
    SELECT
        rep_id,
        baby_id,
        start_time, -- 순번 매기기 기준
        ROW_NUMBER() OVER(PARTITION BY baby_id ORDER BY start_time) as rn -- baby_id별 시간 순 순번
    FROM report
    WHERE baby_id = 1 -- 특정 baby_id 필터
      AND start_time >= '2024-09-16 00:00:00'
      AND start_time < '2024-09-24 00:00:00' -- 2024-09-16부터 2024-09-23까지
),
RankedPredictions AS (
    SELECT
        prediction_id,
        baby_id,
        expected_start_at, -- 순번 매기기 기준
        ROW_NUMBER() OVER(PARTITION BY baby_id ORDER BY expected_start_at) as rn -- baby_id별 시간 순 순번
    FROM sleep_prediction_log
    WHERE baby_id = 1 -- 특정 baby_id 필터
      AND expected_start_at >= '2024-09-16 00:00:00'
      AND expected_start_at < '2024-09-24 00:00:00' -- 2024-09-16부터 2024-09-23까지
      AND rep_id IS NULL -- rep_id가 아직 NULL인 데이터만 대상으로 할 수도 있습니다. (선택 사항)
)
-- 3. RankedReports와 RankedPredictions를 순번(rn)과 baby_id를 기준으로 조인하여
--    prediction_log 테이블의 rep_id를 업데이트합니다.
--    LEFT JOIN을 사용하여 prediction이 report보다 많더라도 report에 해당하는 순번만 업데이트되도록 합니다.
UPDATE sleep_prediction_log spl
JOIN RankedPredictions rp ON spl.prediction_id = rp.prediction_id -- 업데이트 대상 prediction_log
JOIN RankedReports rr ON rp.baby_id = rr.baby_id AND rp.rn = rr.rn -- 순번으로 매칭된 report
SET spl.rep_id = rr.rep_id
-- WHERE spl.baby_id = 1 -- 조인 조건에 baby_id가 있으므로 중복 가능
-- WHERE spl.expected_start_at >= '2024-09-16 00:00:00' AND spl.expected_start_at < '2024-09-24 00:00:00' -- 조인 조건에 expected_start_at 필터가 있으므로 중복 가능
; -- 최종 WHERE 절 없이 조인 조건만으로 업데이트 대상을 제한합니다.

-- 4. 세이프 모드를 다시 활성화합니다.
SET SESSION sql_safe_updates = 1;

SELECT * FROM sleep_prediction_log;