import mysql.connector # MySQL DB에 연결하기 위한 라이브러리
from datetime import datetime, timedelta # 날짜와 시간 계산을 위한 라이브러리
import random # 랜덤 값을 생성하기 위한 라이브러리

from db_config import DB_CONFIG

# --- MySQL 데이터베이스 연결 설정 ---
# 이 부분을 본인의 MySQL DB 정보에 맞게 수정해야 합니다.
# 'your_user', 'your_password', 'your_database_name'을 실제 값으로 바꿔주세요!

# --- 데이터 생성 및 업데이트 대상 설정 ---
# 우리가 더미 데이터를 넣고 업데이트할 아기들의 ID 목록입니다.
# 현재는 baby_id 1, 2, 3만 처리하기로 했으므로 이렇게 설정합니다.
TARGET_BABY_IDS = [1, 2, 3, 4, 5]

def fill_usage_and_env_logs():
    conn = None # DB 연결 객체를 저장할 변수
    cursor = None # SQL 쿼리 실행기 객체를 저장할 변수
    try:
        # 1. MySQL 데이터베이스에 연결
        print("Connecting to MySQL database...")
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(buffered=True)
        print("Successfully connected to MySQL database.")

        # 2. device_subscribe_logs에서 subscribe_log_id 정보 가져오기
        #    device_usage_logs를 채울 때 subscribe_id가 필요하기 때문입니다.
        print("\n--- Step 1: Fetch subscribe_log_ids for target babies ---")
        subscribe_map_query = f"""
        SELECT baby_id, subscribe_log_id 
        FROM device_subscribe_logs 
        WHERE baby_id IN ({', '.join(map(str, TARGET_BABY_IDS))});
        """
        cursor.execute(subscribe_map_query)
        subscribe_id_by_baby_id = {row[0]: row[1] for row in cursor.fetchall()}
        
        if not subscribe_id_by_baby_id:
            print("Error: No subscription data found for target babies. Please ensure 'device_subscribe_logs' is populated.")
            return

        print(f"Found subscribe_ids mapping: {subscribe_id_by_baby_id}")

        # 3. device_environment_logs에서 사용해야 할 recorded_at 및 device_id(또는 baby_id) 정보 가져오기
        #    이 정보를 바탕으로 device_usage_logs 레코드를 생성할 것입니다.
        #    (여기서는 device_environment_logs에 device_id 컬럼이 이미 추가되고 채워져 있다는 전제 하에 작성됩니다.)
        print("\n--- Step 2: Fetch unique (recorded_at, device_id) from device_environment_logs ---")
        env_logs_data_query = f"""
        SELECT DISTINCT del.recorded_at, del.device_id
        FROM device_environment_logs del
        WHERE del.device_id IS NOT NULL AND del.device_id IN ({', '.join(map(str, TARGET_BABY_IDS))}) -- target_baby_ids와 device_id가 1:1 매핑된다고 가정
        ORDER BY del.device_id, del.recorded_at;
        """
        cursor.execute(env_logs_data_query)
        records_to_process = cursor.fetchall()
        cursor.reset()
        print(f"Found {len(records_to_process)} unique (recorded_at, device_id) pairs from existing env logs for processing.")

        if not records_to_process:
            print("No relevant data found in device_environment_logs for target babies to create usage logs. Exiting.")
            return

        # 4. device_usage_logs에 데이터 삽입 및 생성된 usage_log_id 기록
        print("\n--- Step 3: Inserting into device_usage_logs and storing new usage_log_ids ---")
        
        usage_logs_to_insert = [] # device_usage_logs에 삽입할 데이터를 모을 리스트
        
        # (baby_id, recorded_at_as_datetime_object) -> usage_log_id 매핑을 저장할 딕셔너리
        # 이 딕셔너리는 나중에 device_environment_logs를 업데이트할 때 사용됩니다.
        generated_usage_log_ids_map = {} 

        insert_count = 0
        batch_size_for_usage_logs = 500 # 한 번에 INSERT 할 device_usage_logs 레코드 수
        
        for recorded_at_dt, device_id in records_to_process:
            # device_id에 해당하는 baby_id와 subscribe_id를 찾습니다.
            baby_id_for_device = device_id # 가정: device_id와 baby_id가 1:1 매핑
            subscribe_id_for_device = subscribe_id_by_baby_id.get(baby_id_for_device)

            if not subscribe_id_for_device:
                print(f"Warning: No subscribe_id found for device_id {device_id} (mapped to baby_id {baby_id_for_device}). Skipping.")
                continue

            # device_usage_logs에 삽입할 데이터 튜플 준비
            # power_mode는 항상 TRUE
            usage_logs_to_insert.append((subscribe_id_for_device, True, recorded_at_dt))

            # 일정 배치 크기가 되면 한꺼번에 INSERT 실행
            if len(usage_logs_to_insert) >= batch_size_for_usage_logs:
                # INSERT 실행 후, 방금 삽입된 usage_log_id들을 가져와 generated_usage_log_ids_map에 저장해야 합니다.
                # 그러나 mysql.connector의 executemany는 lastrowid를 여러 개 반환하지 않습니다.
                # 따라서, 각 레코드마다 개별적으로 INSERT하고 lastrowid를 얻거나,
                # 아니면 INSERT 후 SELECT LAST_INSERT_ID()를 사용하여 ID 범위를 추정해야 합니다.
                # 여기서는 삽입 후 바로 ID를 가져오기 위해 각 레코드를 개별적으로 INSERT하는 방식으로 하겠습니다.
                # (성능이 조금 떨어질 수 있으나 정확하고 이해하기 쉽습니다.)

                for data_tuple in usage_logs_to_insert:
                    cursor.execute("INSERT INTO device_usage_logs (subscribe_id, power_mode, recorded_at) VALUES (%s, %s, %s);", data_tuple)
                    new_usage_log_id = cursor.lastrowid # 방금 삽입된 레코드의 ID 가져오기
                    
                    # 맵에 저장: (baby_id, recorded_at_datetime_object) -> usage_log_id
                    # recorded_at_dt는 datetime 객체이므로 그대로 키로 사용 가능
                    generated_usage_log_ids_map[(baby_id_for_device, data_tuple[2])] = new_usage_log_id
                    insert_count += 1
                
                conn.commit() # 주기적으로 커밋하여 데이터 손실 방지
                usage_logs_to_insert = [] # 리스트 비우기
                print(f"  Inserted {insert_count} usage logs so far. Last: {recorded_at_dt}")

        # 남아있는 데이터 삽입 (마지막 배치)
        if usage_logs_to_insert:
            for data_tuple in usage_logs_to_insert:
                cursor.execute("INSERT INTO device_usage_logs (subscribe_id, power_mode, recorded_at) VALUES (%s, %s, %s);", data_tuple)
                new_usage_log_id = cursor.lastrowid
                generated_usage_log_ids_map[(baby_id_for_device, data_tuple[2])] = new_usage_log_id
                insert_count += 1
            conn.commit()
            print(f"  Inserted final {insert_count} usage logs.")
        
        print(f"\nSuccessfully inserted total {insert_count} records into device_usage_logs.")


        print("\n--- Step 4: Updating usage_log_id in device_environment_logs ---")
        # device_environment_logs의 usage_log_id를 업데이트하기 위한 데이터 준비
        # 이 쿼리는 environment_log_id가 PK이므로, 이를 WHERE 조건으로 사용하는 것이 가장 효율적입니다.
        update_env_logs_batch_data = [] # (new_usage_log_id, environment_log_id) 튜플 리스트

        # MySQL의 "Safe Update Mode"를 일시적으로 비활성화
        cursor.execute("SET SQL_SAFE_UPDATES = 0;") 
        
        # device_environment_logs에서 업데이트할 레코드들을 가져옵니다.
        # 이전에 가져온 generated_usage_log_ids_map을 사용하기 위해 recorded_at과 device_id도 가져옵니다.
        # usage_log_id가 NULL이거나 0인 경우만 업데이트 대상으로 합니다.
        env_logs_to_update_query = f"""
        SELECT del.environment_log_id, del.recorded_at, dsl.baby_id
        FROM device_environment_logs del
        INNER JOIN devices d ON del.device_id = d.device_id
        INNER JOIN device_subscribe_logs dsl ON d.device_id = dsl.device_id AND dsl.baby_id IN ({', '.join(map(str, TARGET_BABY_IDS))})
        WHERE del.usage_log_id IS NULL OR del.usage_log_id = 0; -- NULL 또는 0인 경우만 업데이트
        """
        cursor.execute(env_logs_to_update_query)
        env_logs_for_update_processing = cursor.fetchall()
        cursor.reset()

        update_count = 0
        update_batch_size_env = 1000 # environment_logs 업데이트 배치 사이즈

        for env_log_id, recorded_at_dt, baby_id in env_logs_for_update_processing:
            key = (baby_id, recorded_at_dt)
            new_usage_log_id = generated_usage_log_ids_map.get(key)
            
            if new_usage_log_id:
                update_env_logs_batch_data.append((new_usage_log_id, env_log_id))
                update_count += 1
                
                if len(update_env_logs_batch_data) >= update_batch_size_env:
                    update_env_logs_in_batch(cursor, update_env_logs_batch_data)
                    update_env_logs_batch_data = []
                    conn.commit() # 중간 커밋
                    print(f"  Updated {update_count} env logs so far. Last environment_log_id: {env_log_id}")
            else:
                print(f"Warning: No new usage_log_id found for env log_id {env_log_id} (baby_id {baby_id}, recorded_at {recorded_at_dt}). Skipping update.")

        # 남아있는 env logs 업데이트
        if update_env_logs_batch_data:
            update_env_logs_in_batch(cursor, update_env_logs_batch_data)
            conn.commit()
            print(f"  Updated final {update_count} environment logs.")

        print(f"\nSuccessfully updated total {update_count} records in device_environment_logs.")

    except mysql.connector.Error as err:
        print(f"Database error: {err}")
        if conn:
            conn.rollback() # 오류 발생 시 모든 작업 롤백
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    finally:
        if conn:
            # MySQL의 "Safe Update Mode"를 다시 활성화
            try:
                cursor.execute("SET SQL_SAFE_UPDATES = 1;")
                conn.commit() # 최종 커밋
            except Exception as e:
                print(f"Error re-enabling safe updates: {e}")
            
            cursor.close()
            conn.close()
            print("DB connection closed.")

def update_env_logs_in_batch(cursor, env_logs_batch_data):
    # Safe Update Mode는 상위 함수에서 비활성화했으므로 여기서 다시 비활성화할 필요는 없습니다.
    # 단일 트랜잭션 내에서 실행되므로 별도 커밋은 상위 함수에서 담당합니다.

    update_env_query = """
    UPDATE device_environment_logs
    SET usage_log_id = %s
    WHERE environment_log_id = %s;
    """
    
    try:
        cursor.executemany(update_env_query, env_logs_batch_data)
    except mysql.connector.Error as err:
        print(f"  Batch update error for env logs: {err}")
        raise # 에러를 상위 호출자에게 전파 (롤백을 위해)

# 스크립트가 실행될 때 main 함수 호출
if __name__ == "__main__":
    fill_usage_and_env_logs()
    print("\n--- All MySQL dummy data filling process complete ---")