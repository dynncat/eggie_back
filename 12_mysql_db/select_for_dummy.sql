/* device_environment_logs에 device_id or baby_id 없을 때
SELECT
	del.environment_log_id,
    del.temperature,
    del.humidity,
    del.brightness,
    del.white_noise_level,
    del.recorded_at
FROM device_environment_logs del
INNER JOIN device_usage_logs dul
ON del.usage_log_id = dul.usage_log_id
INNER JOIN device_subcribe_logs dsl
ON dsl.subscribe_log_id = dul.subscribe_id
INNER JOIN babies b
ON dsl.baby_id = b.baby_id
WHERE b.baby_id=1 
	AND del.recorded_at >= CURDATE() - INTERVAL 1 DAY
    AND del.recorded_at < CURDATE() + INTERVAL 1 DAY;
*/

/* device_environment_logs에 device_id 있을 때, 현재 날짜 기준
SELECT
	dsl.device_id AS baby_id,
	del.environment_log_id,
    del.temperature,
    del.humidity,
    del.brightness,
    del.white_noise_level
FROM device_environment_logs del
JOIN device_subscribe_logs dsl
ON del.device_id = dsl.device_id;
WHERE del.recorded_at >= CURDATE() - INTERVAL 1 DAY
	AND del.recorded_at < CURDATE() + INTERVAL 1 DAY;
*/

SELECT
	dsl.device_id AS baby_id,
	del.environment_log_id,
    del.temperature,
    del.humidity,
    del.brightness,
    del.white_noise_level
FROM device_environment_logs del
JOIN device_subscribe_logs dsl
ON del.device_id = dsl.device_id
WHERE del.recorded_at >= '2024-05-28 00:00:00'
	AND del.recorded_at < '2024-05-29 00:00:00'
ORDER BY baby_id, environment_log_id;