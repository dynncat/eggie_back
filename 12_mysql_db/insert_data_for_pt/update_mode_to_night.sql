UPDATE device_environment_logs
SET
	sleep_mode='night'
WHERE 
	environment_log_id=29592
    OR environment_log_id=29593;
    
INSERT INTO report (baby_id, start_time, end_time, duration, breaks_count, sleep_efficiency_percent) VALUES
(6, '2025-06-17 00:20:00', '2025-06-17 01:15:00', 55, NULL, NULL),
(6, '2025-06-17 02:05:00', '2025-06-17 03:30:00', 85, NULL, NULL),
(6, '2025-06-17 04:00:00', '2025-06-17 04:05:00', 5, NULL, NULL),
(6, '2025-06-17 07:30:00', '2025-06-17 08:45:00', 75, NULL, NULL),
(6, '2025-06-17 08:50:00', '2025-06-17 08:58:00', 8, NULL, NULL);

UPDATE device_environment_logs
SET
	recorded_at='2025-06-17 00:20:00'
WHERE
	environment_log_id=29594;
    
UPDATE device_environment_logs
SET
	recorded_at='2025-06-17 02:05:00'
WHERE
	environment_log_id=29595;
    
UPDATE device_environment_logs
SET
	recorded_at='2025-06-17 04:00:00'
WHERE
	environment_log_id=29596;
    
UPDATE device_environment_logs
SET
	recorded_at='2025-06-17 07:30:00'
WHERE
	environment_log_id=29597;
    
UPDATE device_environment_logs
SET
	recorded_at='2025-06-17 08:50:00'
WHERE
	environment_log_id=29598;

UPDATE device_environment_logs
SET
	sleep_mode='night'
WHERE
	environment_log_id in (29594, 29595, 29596);