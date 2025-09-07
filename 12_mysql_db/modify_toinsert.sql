-- ALTER TABLE device_usage_logs MODIFY COLUMN subscribe_id INT NULL;
-- ALTER TABLE device_environment_logs MODIFY COLUMN usage_log_id INT NULL;
-- ALTER TABLE report MODIFY COLUMN duration FLOAT;

-- UPDATE babies SET week_age = week_age +4
-- WHERE baby_id BETWEEN 1 AND 5;

SELECT * FROM device_environment_logs WHERE device_id=1;
SELECT * FROM device_usage_logs LIMIT 10;
SELECT * FROM report LIMIT 10;
SELECT * FROM babies;

-- ALTER TABLE device_environment_logs MODIFY COLUMN usage_log_id INT NOT NULL;
-- ALTER TABLE device_usage_logs MODIFY COLUMN subscribe_id INT NOT NULL;