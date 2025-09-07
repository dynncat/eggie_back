-- device_usage_logs 테이블의 power_mode 컬럼을 BOOLEAN 타입으로 변경
ALTER TABLE device_usage_logs
MODIFY COLUMN power_mode BOOLEAN NOT NULL DEFAULT TRUE; -- NOT NULL과 기본값 TRUE 추가

SELECT COUNT(recorded_at) FROM device_usage_logs;

SELECT COUNT(recorded_at) FROM device_environment_logs;

SELECT * FROM device_usage_logs;

ALTER TABLE device_usage_logs
ADD CONSTRAINT UQ_subscribe_id_recorded_at UNIQUE (subscribe_id, recorded_at);

SHOW CREATE TABLE device_usage_logs;
SHOW CREATE TABLE device_environment_logs;