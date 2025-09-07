-- device_subscribe_logs 테이블 더미 데이터
-- devices 테이블의 device_id (1~5)와 babies 테이블의 baby_id (1~5)가 존재해야 합니다.
INSERT INTO device_subscribe_logs (device_id, baby_id, started_at, ended_at, is_subscription_active) VALUES
(1, 1, '2024-05-25 09:00:00', '2026-05-25 09:00:00', TRUE),
(2, 2, '2024-05-25 09:05:00', '2026-05-25 09:05:00', TRUE),
(3, 3, '2024-05-25 09:10:00', '2026-05-25 09:10:00', TRUE),
(4, 4, '2024-05-25 09:15:00', '2026-05-25 09:15:00', TRUE),
(5, 5, '2024-05-25 09:20:00', '2026-05-25 09:20:00', TRUE);

SELECT * FROM device_subscribe_logs;