SELECT * FROM device_environment_logs
WHERE recorded_at = '2024-05-27 00:00:00';

-- 1. 'device_id' 컬럼 추가 (FOREIGN KEY로 설정할 것이므로, 일단은 NULL 허용 또는 기본값 설정)
ALTER TABLE device_environment_logs
ADD COLUMN device_id INT;

SELECT * FROM device_environment_logs LIMIT 10;

-- 2. 외래 키 제약 조건 추가 (컬럼 추가 후, 기존 데이터가 NULL이 아닌 유효한 FOREIGN KEY 값이 들어간 후에 가능)
--    지금은 NULL로 추가했기 때문에 바로 FOREIGN KEY를 설정할 수 없습니다.
--    나중에 모든 device_id 값이 채워진 후에 이 ALTER TABLE 문을 실행해야 합니다.
--    (아래 쿼리를 먼저 실행하고, 데이터를 채운 후에 주석 해제하여 실행)
ALTER TABLE device_environment_logs
ADD CONSTRAINT fk_device_id
FOREIGN KEY (device_id) REFERENCES devices(device_id);

-- device_id = 1 할당
UPDATE device_environment_logs
SET device_id = 1
WHERE environment_log_id >= 1 AND environment_log_id <= 5922;

-- device_id = 2 할당
UPDATE device_environment_logs
SET device_id = 2
WHERE environment_log_id >= 5923 AND environment_log_id <= 11796;

-- device_id = 3 할당
UPDATE device_environment_logs
SET device_id = 3
WHERE environment_log_id >= 11797 AND environment_log_id <= 17754;

-- device_id = 4 할당
UPDATE device_environment_logs
SET device_id = 4
WHERE environment_log_id >= 17755 AND environment_log_id <= 23691;

-- device_id = 5 할당 (23692 이후 모든 값)
UPDATE device_environment_logs
SET device_id = 5
WHERE environment_log_id >= 23692;

-- Safe Update Mode 다시 활성화 (작업 후에는 항상 활성화하는 것이 좋습니다)
SET SQL_SAFE_UPDATES = 1;