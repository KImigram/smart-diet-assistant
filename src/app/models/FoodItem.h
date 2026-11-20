#pragma once
// ============================================================
// 食物与营养素实体（对应数据库 foods / food_nutrition 表）
// ============================================================
#include <QString>

// 每 100g 食物的营养素含量
struct Nutrition {
    double cal    = 0.0;   // 热量 kcal
    double protein = 0.0;  // 蛋白质 g
    double fat     = 0.0;  // 脂肪 g
    double carb    = 0.0;  // 碳水化合物 g
    double fiber   = 0.0;  // 膳食纤维 g
    double sodium  = 0.0;  // 钠 mg
};

// 食物条目
struct FoodItem {
    int      id = 0;              // 食物ID（对应数据库 foods.id）
    QString  name;                // 食物/菜品名
    QString  category;            // 分类：主食/肉蛋/蔬菜/水果/饮品/零食/家常菜/汤粥/豆制品
    double   defaultPortionG = 100.0;  // 默认一份的克数
    Nutrition per100g;            // 每 100g 营养含量
};
