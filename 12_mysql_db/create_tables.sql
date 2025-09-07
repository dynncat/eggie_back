CREATE TABLE users (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100),
    birth_date DATE,
    gender VARCHAR(10),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    email VARCHAR(100) NOT NULL UNIQUE
);

CREATE TABLE babies (
    baby_id INT AUTO_INCREMENT PRIMARY KEY,
    birth_date DATE,
    gender VARCHAR(10),
    height FLOAT,
    weight FLOAT,
    week_age INT,
    INDEX(week_age)
);

CREATE TABLE user_baby_links (
    link_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    baby_id INT NOT NULL,
    registered_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id),
    FOREIGN KEY (baby_id) REFERENCES babies(baby_id),
    -- 중복 연결 방지 (한 유저가 같은 아기 중복 등록 불가)
    UNIQUE(user_id, baby_id)
);

CREATE TABLE devices (
    device_id INT AUTO_INCREMENT PRIMARY KEY,
    serial_number VARCHAR(100) NOT NULL UNIQUE,
    device_name VARCHAR(100),
    subscription_status BOOLEAN DEFAULT TRUE
);

CREATE TABLE device_subscribe_logs (
    subscribe_log_id INT AUTO_INCREMENT PRIMARY KEY,
    device_id INT NOT NULL,
    baby_id INT NOT NULL,
    started_at DATETIME,
    ended_at DATETIME,
    is_subscription_active BOOLEAN,
    FOREIGN KEY (device_id) REFERENCES devices(device_id),
    FOREIGN KEY (baby_id) REFERENCES babies(baby_id),
    INDEX(baby_id),
    INDEX(device_id)
);

CREATE TABLE device_usage_logs (
    usage_log_id INT AUTO_INCREMENT PRIMARY KEY,
    subscribe_id INT NOT NULL,
    power_mode VARCHAR(50), -- 전원
    recorded_at DATETIME,
    FOREIGN KEY (subscribe_id) REFERENCES device_subscribe_logs(subscribe_log_id),
    INDEX(recorded_at)
);

CREATE TABLE device_environment_logs ( 
    environment_log_id INT AUTO_INCREMENT PRIMARY KEY,
    usage_log_id INT NOT NULL,
    sleep_mode ENUM('day', 'night') NOT NULL,
    temperature FLOAT,
    humidity FLOAT,
    brightness FLOAT,
    white_noise_level FLOAT,
    recorded_at DATETIME,
    FOREIGN KEY (usage_log_id) REFERENCES device_usage_logs(usage_log_id),
    INDEX(recorded_at)
);

CREATE TABLE report (
    rep_id INT AUTO_INCREMENT PRIMARY KEY,
    baby_id INT NOT NULL,
    start_time DATETIME,
    end_time DATETIME,
    duration INT,
    breaks_count INT,
    sleep_efficiency_percent FLOAT,
    FOREIGN KEY (baby_id) REFERENCES babies(baby_id),
    INDEX(baby_id)
);

CREATE TABLE sleep_prediction_log (
    prediction_id INT AUTO_INCREMENT PRIMARY KEY,
    baby_id INT NOT NULL,
    prediction_date DATE,
    expected_start_at DATETIME,
    expected_end_at DATETIME,
    expected_duration INT,
    rep_id INT,
    FOREIGN KEY (baby_id) REFERENCES babies(baby_id),
    FOREIGN KEY (rep_id) REFERENCES report(rep_id),
    INDEX(baby_id)
);