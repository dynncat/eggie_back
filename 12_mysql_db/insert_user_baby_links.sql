-- user_baby_links 테이블 더미 데이터
-- users 테이블의 user_id (1~10)와 babies 테이블의 baby_id (1~5)가 존재해야 합니다.
INSERT INTO user_baby_links (user_id, baby_id, registered_at) VALUES
-- user_id 1 (남성) - baby_id 1
(1, 1, '2024-05-26 10:00:00'), 
-- user_id 2 (여성) - baby_id 1
(2, 1, '2024-05-26 10:00:00'), 

-- user_id 3 (남성) - baby_id 2
(3, 2, '2024-05-26 10:05:00'),
-- user_id 4 (여성) - baby_id 2
(4, 2, '2024-05-26 10:05:00'),

-- user_id 5 (남성) - baby_id 3
(5, 3, '2024-05-26 10:10:00'),
-- user_id 6 (여성) - baby_id 3
(6, 3, '2024-05-26 10:10:00'),

-- user_id 7 (남성) - baby_id 4
(7, 4, '2024-05-26 10:15:00'),
-- user_id 8 (여성) - baby_id 4
(8, 4, '2024-05-26 10:15:00'),

-- user_id 9 (남성) - baby_id 5
(9, 5, '2024-05-26 10:20:00'),
-- user_id 10 (여성) - baby_id 5
(10, 5, '2024-05-26 10:20:00');

SELECT * FROM babies;
SELECT * FROM user_baby_links;