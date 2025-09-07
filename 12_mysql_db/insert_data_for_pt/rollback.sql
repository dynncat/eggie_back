-- report 테이블에서 필요 없는 데이터를 삭제합니다.
DELETE FROM report
WHERE rep_id=29600; -- 또는 삽입했던 시간 범위를 기준으로 삭제 등

-- AUTO_INCREMENT 카운터를 초기값으로 재설정
ALTER TABLE report AUTO_INCREMENT = 29599;


DELETE FROM sleep_prediction_log
WHERE baby_id=6;

ALTER TABLE sleep_prediction_log AUTO_INCREMENT = 255;