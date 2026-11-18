CREATE TABLE IF NOT EXISTS food_nutrition_sources (
    food_id INT PRIMARY KEY,
    dataset VARCHAR(100) NOT NULL,
    source_url VARCHAR(500) NOT NULL,
    source_food VARCHAR(100) NOT NULL,
    source_portion_g DECIMAL(8,2) NOT NULL,
    source_values_json TEXT NOT NULL,
    note TEXT NOT NULL,
    FOREIGN KEY (food_id) REFERENCES foods(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
