SELECT
    del.environment_log_id,           -- 업데이트 대상
    dul.usage_log_id                  -- 새로 연결할 usage_log_id
FROM
    device_environment_logs del
INNER JOIN
    devices d ON del.device_id = d.device_id
INNER JOIN
    device_subscribe_logs dsl ON d.device_id = dsl.device_id -- del.device_id와 dsl.device_id를 통해 baby_id 매핑
INNER JOIN
    device_usage_logs dul ON dsl.subscribe_log_id = dul.subscribe_id -- subscribe_id를 통해 usage_log_id 연결
    AND del.recorded_at = dul.recorded_at  -- 가장 중요: 시간으로 두 사용 로그를 매칭
WHERE
    dsl.baby_id IN (1, 2, 3, 4, 5) -- 특정 baby_id만 업데이트 (스크립트에서 설정한 대상과 동일)
    -- 그리고 아직 usage_log_id가 설정되지 않은 경우만 업데이트
    AND (del.usage_log_id IS NULL OR del.usage_log_id = 0)
ORDER BY
    del.environment_log_id;
    
-- Safe Update Mode 비활성화 (필요하다면)
SET SQL_SAFE_UPDATES = 0;

UPDATE
    device_environment_logs del
INNER JOIN
    devices d ON del.device_id = d.device_id
INNER JOIN
    device_subscribe_logs dsl ON d.device_id = dsl.device_id
INNER JOIN
    device_usage_logs dul ON dsl.subscribe_log_id = dul.subscribe_id
    AND del.recorded_at = dul.recorded_at
SET
    del.usage_log_id = dul.usage_log_id
WHERE
    dsl.baby_id IN (1, 2, 3, 4, 5) -- 스크립트에서 처리했던 baby_id 범위와 동일
    AND (del.usage_log_id IS NULL OR del.usage_log_id = 0); -- 아직 업데이트되지 않은 레코드만
    
-- Safe Update Mode 다시 활성화 (작업 후에는 항상 활성화하는 것이 좋습니다)
SET SQL_SAFE_UPDATES = 1;