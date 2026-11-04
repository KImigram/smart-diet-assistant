-- =====================================================
-- 日常营养饮食助手 - 数据库初始化脚本
-- MySQL 8.0+ / InnoDB / utf8mb4
-- 库名: nutrition_assistant（10张表, 3NF）
-- 执行方式见同目录 README 或直接:
--   cmd: mysql --default-character-set=utf8mb4 -u root -p < nutrition_assistant.sql
-- =====================================================

CREATE DATABASE IF NOT EXISTS nutrition_assistant
  DEFAULT CHARACTER SET utf8mb4
  DEFAULT COLLATE utf8mb4_unicode_ci;
USE nutrition_assistant;

-- 1. 用户表
CREATE TABLE IF NOT EXISTS users (
  user_id       INT UNSIGNED AUTO_INCREMENT COMMENT '用户ID',
  username      VARCHAR(50)  NOT NULL COMMENT '用户名',
  password_hash VARCHAR(255) NOT NULL COMMENT '密码哈希',
  email         VARCHAR(100) NULL COMMENT '邮箱',
  created_at    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '注册时间',
  PRIMARY KEY (user_id),
  UNIQUE KEY uk_username (username)
) ENGINE=InnoDB COMMENT='用户表';

-- 2. 健康档案 (1:1 用户)
CREATE TABLE IF NOT EXISTS health_profile (
  profile_id     INT UNSIGNED AUTO_INCREMENT COMMENT '档案ID',
  user_id        INT UNSIGNED NOT NULL COMMENT '用户ID',
  gender         ENUM('男','女','保密') NULL COMMENT '性别',
  birth_date     DATE NULL COMMENT '出生日期',
  height_cm      DECIMAL(5,1) NULL COMMENT '身高cm',
  weight_kg      DECIMAL(5,1) NULL COMMENT '体重kg',
  activity_level ENUM('久坐','轻度','中度','重度') NULL COMMENT '活动水平',
  goal           VARCHAR(50) NULL COMMENT '目标:减脂/增肌/维持',
  updated_at     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (profile_id),
  UNIQUE KEY uk_user (user_id),
  CONSTRAINT fk_profile_user FOREIGN KEY (user_id) REFERENCES users(user_id)
) ENGINE=InnoDB COMMENT='健康档案';

-- 3. 体重记录
CREATE TABLE IF NOT EXISTS weight_records (
  record_id   INT UNSIGNED AUTO_INCREMENT COMMENT '记录ID',
  user_id     INT UNSIGNED NOT NULL COMMENT '用户ID',
  weight_kg   DECIMAL(5,1) NOT NULL COMMENT '体重kg',
  record_date DATE NOT NULL COMMENT '记录日期',
  PRIMARY KEY (record_id),
  KEY idx_user_date (user_id, record_date),
  CONSTRAINT fk_weight_user FOREIGN KEY (user_id) REFERENCES users(user_id)
) ENGINE=InnoDB COMMENT='体重记录';

-- 4. 食物分类
CREATE TABLE IF NOT EXISTS food_categories (
  category_id INT UNSIGNED AUTO_INCREMENT COMMENT '分类ID',
  name        VARCHAR(50) NOT NULL COMMENT '分类名',
  PRIMARY KEY (category_id),
  UNIQUE KEY uk_cat_name (name)
) ENGINE=InnoDB COMMENT='食物分类';

-- 5. 食物/菜品表
CREATE TABLE IF NOT EXISTS foods (
  food_id          INT UNSIGNED AUTO_INCREMENT COMMENT '食物ID',
  category_id      INT UNSIGNED NOT NULL COMMENT '所属分类',
  name             VARCHAR(100) NOT NULL COMMENT '菜名/食物名',
  portion_g        DECIMAL(6,1) NULL COMMENT '标准份量(克)',
  main_ingredients VARCHAR(255) NULL COMMENT '主要食材(展示用)',
  source           VARCHAR(50)  NULL COMMENT '数据来源:估算/成分表',
  PRIMARY KEY (food_id),
  UNIQUE KEY uk_food_name (name),
  KEY idx_category (category_id),
  CONSTRAINT fk_food_category FOREIGN KEY (category_id) REFERENCES food_categories(category_id)
) ENGINE=InnoDB COMMENT='食物/菜品表';

-- 6. 食物营养素表 (EAV: 每行一个营养素, 满足3NF)
CREATE TABLE IF NOT EXISTS food_nutrition (
  food_id  INT UNSIGNED NOT NULL COMMENT '食物ID',
  nutrient VARCHAR(30) NOT NULL COMMENT '营养素:能量/蛋白质/脂肪/碳水/钠等',
  amount   DECIMAL(8,2) NOT NULL COMMENT '含量',
  unit     VARCHAR(20) NOT NULL DEFAULT 'kcal' COMMENT '单位',
  PRIMARY KEY (food_id, nutrient),
  CONSTRAINT fk_nutrition_food FOREIGN KEY (food_id) REFERENCES foods(food_id)
) ENGINE=InnoDB COMMENT='食物营养素表(每份)';

-- 7. 饮食记录
CREATE TABLE IF NOT EXISTS meal_records (
  record_id   INT UNSIGNED AUTO_INCREMENT COMMENT '记录ID',
  user_id     INT UNSIGNED NOT NULL COMMENT '用户ID',
  food_id     INT UNSIGNED NOT NULL COMMENT '食物ID',
  meal_type   ENUM('早餐','午餐','晚餐','加餐') NOT NULL COMMENT '餐次',
  portions    DECIMAL(4,1) NOT NULL DEFAULT 1.0 COMMENT '份数',
  record_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '记录时间',
  PRIMARY KEY (record_id),
  KEY idx_user_time (user_id, record_time),
  KEY idx_food (food_id),
  CONSTRAINT fk_meal_user FOREIGN KEY (user_id) REFERENCES users(user_id),
  CONSTRAINT fk_meal_food FOREIGN KEY (food_id) REFERENCES foods(food_id)
) ENGINE=InnoDB COMMENT='饮食记录';

-- 8. 识别纠错
CREATE TABLE IF NOT EXISTS recognition_corrections (
  correction_id      INT UNSIGNED AUTO_INCREMENT COMMENT '纠错ID',
  user_id            INT UNSIGNED NOT NULL COMMENT '用户ID',
  image_path         VARCHAR(255) NULL COMMENT '原图路径',
  original_food_id   INT UNSIGNED NULL COMMENT '模型识别结果',
  corrected_food_id  INT UNSIGNED NOT NULL COMMENT '用户纠正后',
  created_at         DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (correction_id),
  KEY idx_user (user_id),
  KEY idx_orig (original_food_id),
  KEY idx_corr (corrected_food_id),
  CONSTRAINT fk_corr_user FOREIGN KEY (user_id) REFERENCES users(user_id),
  CONSTRAINT fk_corr_orig FOREIGN KEY (original_food_id) REFERENCES foods(food_id),
  CONSTRAINT fk_corr_corr FOREIGN KEY (corrected_food_id) REFERENCES foods(food_id)
) ENGINE=InnoDB COMMENT='识别纠错记录';

-- 9. 对话会话
CREATE TABLE IF NOT EXISTS chat_sessions (
  session_id INT UNSIGNED AUTO_INCREMENT COMMENT '会话ID',
  user_id    INT UNSIGNED NOT NULL COMMENT '用户ID',
  title      VARCHAR(100) NULL COMMENT '会话标题',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (session_id),
  KEY idx_user (user_id),
  CONSTRAINT fk_session_user FOREIGN KEY (user_id) REFERENCES users(user_id)
) ENGINE=InnoDB COMMENT='对话会话';

-- 10. 对话消息
CREATE TABLE IF NOT EXISTS chat_messages (
  message_id INT UNSIGNED AUTO_INCREMENT COMMENT '消息ID',
  session_id INT UNSIGNED NOT NULL COMMENT '会话ID',
  role       ENUM('user','assistant','system') NOT NULL COMMENT '角色',
  content    TEXT NOT NULL COMMENT '消息内容',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (message_id),
  KEY idx_session (session_id),
  CONSTRAINT fk_msg_session FOREIGN KEY (session_id) REFERENCES chat_sessions(session_id)
) ENGINE=InnoDB COMMENT='对话消息';

-- 初始化: 食物分类
INSERT INTO food_categories (name) VALUES
('家常菜'), ('主食'), ('汤粥'), ('小吃面点'), ('甜品饮品'), ('其他');
