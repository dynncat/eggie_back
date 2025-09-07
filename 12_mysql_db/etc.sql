SELECT 
	*,
    ROW_NUMBER() OVER (partition by sleep_mode, DATE(recorded_at)
    ORDER BY recorded_at) AS sleep_mode_seq
FROM device_environment_logs
ORDER BY sleep_mode_seq;

SELECT * FROM sleep_prediction_log;
SELECT * FROM device_usage_logs;
SELECT 
	r.start_time,
    r.end_time,
    enl.recorded_at,
	r.duration,
    enl.temperature
FROM device_environment_logs enl
JOIN report r ON r.baby_id = enl.device_id;
SELECT * FROM report LIMIT 10;
SELECT * FROM device_environment_logs;
SELECT * FROM report r
JOIN sleep_prediction_log spl
ON r.rep_id = spl.rep_id;

SELECT * FROM report;

INSERT INTO report (baby_id, start_time) VALUES (1, %s);

UPDATE report
JOIN (
    SELECT rep_id
    FROM report
    WHERE baby_id = %s
    ORDER BY start_time DESC
    LIMIT 1
) AS latest
ON report.rep_id = latest.rep_id
SET 
    end_time = %s,
    duration = TIMESTAMPDIFF(MINUTE, start_time, %s)