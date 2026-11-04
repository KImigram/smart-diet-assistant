-- ============================================================
-- 智能营养饮食助手 · 数据库建表脚本
-- 10张表，全部满足第三范式(3NF)
-- 字符集：utf8mb4，引擎：InnoDB
-- ============================================================

CREATE DATABASE IF NOT EXISTS nutritious_diet
    DEFAULT CHARACTER SET utf8mb4
    DEFAULT COLLATE utf8mb4_unicode_ci;

USE nutritious_diet;

-- ---------- 用户域 ----------

-- 1. 用户主表
CREATE TABLE IF NOT EXISTS users (
    user_id       INT AUTO_INCREMENT PRIMARY KEY,
    username      VARCHAR(50)  NOT NULL UNIQUE COMMENT '登录名',
    password_hash VARCHAR(255) NOT NULL COMMENT '密码哈希',
    nickname      VARCHAR(50)  DEFAULT '' COMMENT '昵称',
    created_at    DATETIME     DEFAULT CURRENT_TIMESTAMP,
    updated_at    DATETIME     DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB COMMENT='用户主表';

-- 2. 健康档案（与用户 1:1）
CREATE TABLE IF NOT EXISTS health_profile (
    user_id        INT PRIMARY KEY,
    gender         VARCHAR(10)  DEFAULT '男' COMMENT '性别',
    age            INT          DEFAULT 22 COMMENT '年龄',
    height_cm      DECIMAL(5,1) DEFAULT 170.0 COMMENT '身高cm',
    target_calorie INT          DEFAULT 2000 COMMENT '每日目标热量kcal',
    activity_level VARCHAR(20)  DEFAULT '轻度活动' COMMENT '活动水平',
    allergens      VARCHAR(255) DEFAULT '' COMMENT '过敏原/忌口，逗号分隔',
    updated_at     DATETIME     DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
) ENGINE=InnoDB COMMENT='健康档案';

-- 3. 体重记录（与用户 1:N）
CREATE TABLE IF NOT EXISTS weight_records (
    id        INT AUTO_INCREMENT PRIMARY KEY,
    user_id   INT NOT NULL,
    weight_kg DECIMAL(5,1) NOT NULL COMMENT '体重kg',
    record_date DATE NOT NULL COMMENT '称重日期',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    UNIQUE KEY uk_user_date (user_id, record_date)
) ENGINE=InnoDB COMMENT='体重记录';

-- ---------- 食物域 ----------

-- 4. 食物分类
CREATE TABLE IF NOT EXISTS food_categories (
    id   INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(30) NOT NULL UNIQUE COMMENT '分类名：主食/肉蛋/蔬菜等'
) ENGINE=InnoDB COMMENT='食物分类';

-- 5. 食物主表
CREATE TABLE IF NOT EXISTS foods (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    name            VARCHAR(100) NOT NULL COMMENT '食物/菜品名',
    category_id     INT NOT NULL COMMENT '所属分类',
    default_portion_g DECIMAL(6,1) DEFAULT 100.0 COMMENT '默认份量g',
    FOREIGN KEY (category_id) REFERENCES food_categories(id),
    KEY idx_name (name)
) ENGINE=InnoDB COMMENT='食物主表';

-- 6. 营养成分表（EAV行存储，复合主键 food_id+nutrient）
CREATE TABLE IF NOT EXISTS food_nutrition (
    food_id        INT NOT NULL,
    nutrient       VARCHAR(20) NOT NULL COMMENT '营养素：calorie/protein/fat/carb/fiber/sodium',
    value_per_100g DECIMAL(8,2) NOT NULL COMMENT '每100g含量',
    PRIMARY KEY (food_id, nutrient),
    FOREIGN KEY (food_id) REFERENCES foods(id) ON DELETE CASCADE
) ENGINE=InnoDB COMMENT='食物营养成分（每100g）';

-- ---------- 记录域 ----------

-- 7. 饮食记录
CREATE TABLE IF NOT EXISTS meal_records (
    id        INT AUTO_INCREMENT PRIMARY KEY,
    user_id   INT NOT NULL,
    food_id   INT NOT NULL,
    meal_type VARCHAR(10) NOT NULL COMMENT '早餐/午餐/晚餐/加餐',
    portion_g DECIMAL(6,1) NOT NULL COMMENT '实际摄入份量g',
    eaten_at  DATETIME NOT NULL COMMENT '食用时间',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (food_id) REFERENCES foods(id),
    KEY idx_user_date (user_id, eaten_at),
    KEY idx_meal_type (meal_type)
) ENGINE=InnoDB COMMENT='饮食记录';

-- 8. 识别纠错记录
CREATE TABLE IF NOT EXISTS recognition_corrections (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    user_id         INT NOT NULL,
    original_name   VARCHAR(100) NOT NULL COMMENT 'API原始识别名',
    corrected_food_id INT NOT NULL COMMENT '用户修正后的食物id',
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (corrected_food_id) REFERENCES foods(id),
    KEY idx_original (original_name)
) ENGINE=InnoDB COMMENT='识别纠错记录';

-- 9. 对话会话
CREATE TABLE IF NOT EXISTS chat_sessions (
    id         INT AUTO_INCREMENT PRIMARY KEY,
    user_id    INT NOT NULL,
    title      VARCHAR(100) DEFAULT '新对话',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    KEY idx_user (user_id)
) ENGINE=InnoDB COMMENT='对话会话';

-- 10. 对话消息
CREATE TABLE IF NOT EXISTS chat_messages (
    id         INT AUTO_INCREMENT PRIMARY KEY,
    session_id INT NOT NULL,
    role       VARCHAR(20) NOT NULL COMMENT 'user/assistant/system',
    content    TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES chat_sessions(id) ON DELETE CASCADE,
    KEY idx_session (session_id)
) ENGINE=InnoDB COMMENT='对话消息';

-- 11. 运动计划（当日，含多任务，v2）
CREATE TABLE IF NOT EXISTS exercise_plans (
    id           INT AUTO_INCREMENT PRIMARY KEY,
    user_id      INT NOT NULL,
    plan_date    DATE NOT NULL COMMENT '计划日期',
    goal         VARCHAR(100) DEFAULT '' COMMENT '目标',
    status       VARCHAR(20) DEFAULT 'pending' COMMENT 'pending待确认/confirmed已确认',
    tasks        TEXT COMMENT '任务JSON[{sport_type,title,content,duration_min,distance_km,calories}]',
    summary      TEXT COMMENT 'AI生成说明（与当天饮食挂钩）',
    created_at   DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    KEY idx_user_date (user_id, plan_date)
) ENGINE=InnoDB COMMENT='运动计划（当日）';

-- 12. 运动打卡清单（确认计划后生成，仅完成/未完成）
CREATE TABLE IF NOT EXISTS exercise_checkins (
    id           INT AUTO_INCREMENT PRIMARY KEY,
    plan_id      INT NOT NULL,
    task_index   INT NOT NULL,
    sport_type   VARCHAR(50) DEFAULT '',
    title        VARCHAR(100) DEFAULT '',
    completed    TINYINT DEFAULT 0,
    completed_at DATETIME NULL,
    created_at   DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (plan_id) REFERENCES exercise_plans(id) ON DELETE CASCADE,
    KEY idx_plan (plan_id)
) ENGINE=InnoDB COMMENT='运动打卡清单';