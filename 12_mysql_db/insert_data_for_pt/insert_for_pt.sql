INSERT INTO users VALUES (11, '이주은', '1997-12-31', 'female', '2025-06-01', 'abc.lee@example.com');

INSERT INTO babies VALUES (6, '2025-06-01', 'female', 50, 3.5, 52);

INSERT INTO user_baby_links VALUES (11, 11, 6, '2025-06-01 00:00:10');

INSERT INTO devices VALUES (6, 'EGGIE_SN_006', 'EGGie', 1);

INSERT INTO device_subscribe_logs VALUES (6, 6, 6, '2025-05-31 09:00:00', '2026-06-01 09:00:00', 1);

INSERT INTO device_usage_logs (subscribe_id) VALUES (6);
-- usage_log_id = 29590

INSERT INTO device_environment_logs 
			(usage_log_id,
            device_id,
            sleep_mode,
            temperature,
            humidity,
            brightness,
            white_noise_level) 
            VALUES (29590, 6, 'day', 21.2, 68.6, 17.1, 38);
-- environment_log_id=29589
            
INSERT INTO report (baby_id) VALUES (6);
-- rep_id=29599

INSERT INTO sleep_prediction_log (baby_id) VALUES (6);
-- prediction_id=255
-- rep_id 위에서 생기는 거랑 매칭 필요
-- prediction_date는 '2025-06-17'로 통일
-- expected_start_at, expected_end_at은 2025-06-17 날짜는 고정, 시간만 2024-09-22 때의 타임라인을 고정.

SELECT * FROM device_usage_logs WHERE subscribe_id = 6;
SELECT * FROM device_environment_logs ORDER BY environment_log_id DESC;
SELECT * FROM report ORDER BY rep_id DESC;
SELECT * FROM sleep_prediction_log ORDER BY prediction_id DESC;