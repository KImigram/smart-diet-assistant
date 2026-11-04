-- ============================================================
-- 食物营养成分库初始化数据
-- 分类 + 约50种常见食物 + 每100g营养成分
-- 营养素：calorie(kcal) protein(g) fat(g) carb(g) fiber(g) sodium(mg)
-- ============================================================
USE nutritious_diet;

-- 分类
INSERT IGNORE INTO food_categories (id, name) VALUES
(1, '主食'), (2, '肉蛋'), (3, '家常菜'), (4, '蔬菜'),
(5, '豆制品'), (6, '水果'), (7, '饮品'), (8, '零食'), (9, '汤粥');

-- 食物主表 (id, name, category_id, default_portion_g)
INSERT IGNORE INTO foods (id, name, category_id, default_portion_g) VALUES
-- 主食
(1, '米饭', 1, 150), (2, '馒头', 1, 100), (3, '面条', 1, 200),
(4, '面包', 1, 80), (5, '燕麦粥', 1, 250), (6, '红薯', 1, 150),
(7, '玉米', 1, 200), (8, '饺子', 1, 200), (9, '包子', 1, 150),
-- 肉蛋
(10, '鸡蛋', 2, 60), (11, '鸡胸肉', 2, 150), (12, '牛肉', 2, 150),
(13, '猪肉', 2, 150), (14, '三文鱼', 2, 150), (15, '虾', 2, 150),
(16, '牛奶', 2, 250), (17, '酸奶', 2, 200),
-- 家常菜
(18, '番茄炒蛋', 3, 200), (19, '红烧肉', 3, 150), (20, '宫保鸡丁', 3, 200),
(21, '鱼香肉丝', 3, 200), (22, '麻婆豆腐', 3, 200), (23, '糖醋里脊', 3, 150),
(24, '清蒸鱼', 3, 200), (25, '炒青菜', 3, 200),
-- 蔬菜
(26, '西兰花', 4, 200), (27, '菠菜', 4, 200), (28, '胡萝卜', 4, 150),
(29, '黄瓜', 4, 200), (30, '番茄', 4, 200), (31, '白菜', 4, 200),
-- 豆制品
(32, '豆腐', 5, 200), (33, '豆浆', 5, 250), (34, '豆干', 5, 100),
-- 水果
(35, '苹果', 6, 200), (36, '香蕉', 6, 150), (37, '橙子', 6, 200),
(38, '葡萄', 6, 150), (39, '西瓜', 6, 300),
-- 饮品
(40, '可乐', 7, 330), (41, '橙汁', 7, 250), (42, '咖啡', 7, 250),
(43, '绿茶', 7, 250),
-- 零食
(44, '薯片', 8, 50), (45, '巧克力', 8, 30), (46, '饼干', 8, 50),
(47, '坚果', 8, 30),
-- 汤粥
(48, '紫菜蛋花汤', 9, 250), (49, '小米粥', 9, 300), (50, '排骨汤', 9, 300);

-- 营养成分 (food_id, nutrient, value_per_100g)
-- calorie
INSERT IGNORE INTO food_nutrition (food_id, nutrient, value_per_100g) VALUES
(1,'calorie',116),(2,'calorie',223),(3,'calorie',110),(4,'calorie',313),(5,'calorie',88),
(6,'calorie',86),(7,'calorie',112),(8,'calorie',253),(9,'calorie',227),
(10,'calorie',144),(11,'calorie',133),(12,'calorie',125),(13,'calorie',395),(14,'calorie',139),
(15,'calorie',93),(16,'calorie',54),(17,'calorie',72),
(18,'calorie',86),(19,'calorie',470),(20,'calorie',180),(21,'calorie',170),(22,'calorie',110),
(23,'calorie',290),(24,'calorie',113),(25,'calorie',50),
(26,'calorie',36),(27,'calorie',28),(28,'calorie',41),(29,'calorie',16),(30,'calorie',19),
(31,'calorie',17),
(32,'calorie',81),(33,'calorie',31),(34,'calorie',140),
(35,'calorie',54),(36,'calorie',93),(37,'calorie',48),(38,'calorie',45),(39,'calorie',26),
(40,'calorie',43),(41,'calorie',45),(42,'calorie',2),(43,'calorie',1),
(44,'calorie',547),(45,'calorie',586),(46,'calorie',433),(47,'calorie',600),
(48,'calorie',30),(49,'calorie',46),(50,'calorie',80);

-- protein
INSERT IGNORE INTO food_nutrition (food_id, nutrient, value_per_100g) VALUES
(1,'protein',2.6),(2,'protein',7.0),(3,'protein',3.0),(4,'protein',8.3),(5,'protein',3.0),
(6,'protein',1.6),(7,'protein',4.0),(8,'protein',8.5),(9,'protein',7.5),
(10,'protein',13.3),(11,'protein',19.4),(12,'protein',19.9),(13,'protein',13.2),(14,'protein',17.2),
(15,'protein',18.6),(16,'protein',3.0),(17,'protein',2.5),
(18,'protein',5.0),(19,'protein',7.7),(20,'protein',15.0),(21,'protein',12.0),(22,'protein',8.0),
(23,'protein',16.0),(24,'protein',17.0),(25,'protein',2.0),
(26,'protein',4.1),(27,'protein',2.6),(28,'protein',1.0),(29,'protein',0.8),(30,'protein',0.9),
(31,'protein',1.5),
(32,'protein',8.1),(33,'protein',1.8),(34,'protein',16.0),
(35,'protein',0.2),(36,'protein',1.4),(37,'protein',0.8),(38,'protein',0.5),(39,'protein',0.6),
(40,'protein',0),(41,'protein',0.7),(42,'protein',0.1),(43,'protein',0),
(44,'protein',7.0),(45,'protein',4.3),(46,'protein',9.0),(47,'protein',20.0),
(48,'protein',2.0),(49,'protein',1.4),(50,'protein',6.0);

-- fat
INSERT IGNORE INTO food_nutrition (food_id, nutrient, value_per_100g) VALUES
(1,'fat',0.3),(2,'fat',1.1),(3,'fat',0.5),(4,'fat',5.1),(5,'fat',1.5),
(6,'fat',0.1),(7,'fat',1.2),(8,'fat',13.0),(9,'fat',5.0),
(10,'fat',8.8),(11,'fat',5.0),(12,'fat',4.2),(13,'fat',37.0),(14,'fat',7.8),
(15,'fat',0.8),(16,'fat',3.2),(17,'fat',2.7),
(18,'fat',5.0),(19,'fat',35.0),(20,'fat',10.0),(21,'fat',8.0),(22,'fat',5.0),
(23,'fat',18.0),(24,'fat',4.0),(25,'fat',3.0),
(26,'fat',0.6),(27,'fat',0.3),(28,'fat',0.2),(29,'fat',0.2),(30,'fat',0.2),
(31,'fat',0.1),
(32,'fat',3.7),(33,'fat',1.6),(34,'fat',8.0),
(35,'fat',0.2),(36,'fat',0.2),(37,'fat',0.2),(38,'fat',0.2),(39,'fat',0.1),
(40,'fat',0),(41,'fat',0.2),(42,'fat',0),(43,'fat',0),
(44,'fat',37.0),(45,'fat',40.0),(46,'fat',12.0),(47,'fat',50.0),
(48,'fat',1.5),(49,'fat',0.7),(50,'fat',5.0);

-- carb
INSERT IGNORE INTO food_nutrition (food_id, nutrient, value_per_100g) VALUES
(1,'carb',25.9),(2,'carb',47.0),(3,'carb',22.0),(4,'carb',58.6),(5,'carb',15.0),
(6,'carb',20.1),(7,'carb',22.8),(8,'carb',26.0),(9,'carb',35.0),
(10,'carb',2.8),(11,'carb',2.5),(12,'carb',2.0),(13,'carb',2.4),(14,'carb',0),
(15,'carb',0.2),(16,'carb',3.4),(17,'carb',9.3),
(18,'carb',4.0),(19,'carb',15.0),(20,'carb',12.0),(21,'carb',10.0),(22,'carb',6.0),
(23,'carb',18.0),(24,'carb',1.0),(25,'carb',3.0),
(26,'carb',4.3),(27,'carb',4.5),(28,'carb',8.8),(29,'carb',2.9),(30,'carb',4.0),
(31,'carb',3.2),
(32,'carb',4.2),(33,'carb',1.1),(34,'carb',11.0),
(35,'carb',13.5),(36,'carb',22.0),(37,'carb',11.1),(38,'carb',10.3),(39,'carb',6.8),
(40,'carb',10.6),(41,'carb',10.4),(42,'carb',0.3),(43,'carb',0),
(44,'carb',48.0),(45,'carb',53.0),(46,'carb',70.0),(47,'carb',20.0),
(48,'carb',2.0),(49,'carb',8.4),(50,'carb',3.0);

-- fiber
INSERT IGNORE INTO food_nutrition (food_id, nutrient, value_per_100g) VALUES
(1,'fiber',0.3),(2,'fiber',1.5),(3,'fiber',1.2),(4,'fiber',5.6),(5,'fiber',1.7),
(6,'fiber',3.0),(7,'fiber',2.9),(8,'fiber',1.8),(9,'fiber',1.5),
(10,'fiber',0),(11,'fiber',0),(12,'fiber',0),(13,'fiber',0),(14,'fiber',0),
(15,'fiber',0),(16,'fiber',0),(17,'fiber',0),
(18,'fiber',1.0),(19,'fiber',0.5),(20,'fiber',1.5),(21,'fiber',1.0),(22,'fiber',1.5),
(23,'fiber',0.5),(24,'fiber',0),(25,'fiber',1.5),
(26,'fiber',1.6),(27,'fiber',1.7),(28,'fiber',2.8),(29,'fiber',0.5),(30,'fiber',0.5),
(31,'fiber',0.8),
(32,'fiber',0.4),(33,'fiber',0.1),(34,'fiber',1.0),
(35,'fiber',2.4),(36,'fiber',1.2),(37,'fiber',0.6),(38,'fiber',0.4),(39,'fiber',0.3),
(40,'fiber',0),(41,'fiber',0.2),(42,'fiber',0),(43,'fiber',0),
(44,'fiber',3.0),(45,'fiber',3.0),(46,'fiber',1.0),(47,'fiber',5.0),
(48,'fiber',0.5),(49,'fiber',0.7),(50,'fiber',0.5);

-- sodium (mg)
INSERT IGNORE INTO food_nutrition (food_id, nutrient, value_per_100g) VALUES
(1,'sodium',2),(2,'sodium',165),(3,'sodium',15),(4,'sodium',350),(5,'sodium',2),
(6,'sodium',28),(7,'sodium',3),(8,'sodium',800),(9,'sodium',500),
(10,'sodium',132),(11,'sodium',65),(12,'sodium',57),(13,'sodium',59),(14,'sodium',59),
(15,'sodium',165),(16,'sodium',37),(17,'sodium',39),
(18,'sodium',300),(19,'sodium',800),(20,'sodium',600),(21,'sodium',500),(22,'sodium',400),
(23,'sodium',350),(24,'sodium',100),(25,'sodium',200),
(26,'sodium',18),(27,'sodium',85),(28,'sodium',71),(29,'sodium',5),(30,'sodium',5),
(31,'sodium',57),
(32,'sodium',7),(33,'sodium',3),(34,'sodium',200),
(35,'sodium',1),(36,'sodium',1),(37,'sodium',1),(38,'sodium',1),(39,'sodium',1),
(40,'sodium',12),(41,'sodium',5),(42,'sodium',3),(43,'sodium',1),
(44,'sodium',500),(45,'sodium',50),(46,'sodium',200),(47,'sodium',10),
(48,'sodium',300),(49,'sodium',3),(50,'sodium',500);

-- 演示用户（密码: 123456）
INSERT IGNORE INTO users (user_id, username, password_hash, nickname)
VALUES (1, 'demo', '8d969eef6ecad3c29a3a629280e686cf0c3f5d5a86aff3ca12020c923adc6c92', '用户');
INSERT IGNORE INTO health_profile (user_id, gender, age, height_cm, target_calorie, activity_level, allergens)
VALUES (1, '男', 22, 175.0, 2000, '轻度活动', '');
