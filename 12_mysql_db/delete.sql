-- Safe Update Mode 비활성화 (필요하다면)
SET SQL_SAFE_UPDATES = 0;

-- 1. device_environment_logs의 모든 데이터 삭제
DELETE FROM device_environment_logs;

-- 2. device_usage_logs의 모든 데이터 삭제
DELETE FROM device_usage_logs;

-- Safe Update Mode 다시 활성화
SET SQL_SAFE_UPDATES = 1;

ALTER TABLE device_usage_logs AUTO_INCREMENT = 1;
ALTER TABLE device_environment_logs AUTO_INCREMENT = 1;