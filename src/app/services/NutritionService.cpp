#include "NutritionService.h"

#include <QDebug>

namespace {

// 构造演示食物库的辅助函数
FoodItem makeFood(const char *name, const char *category, double defaultPortionG,
                  double cal, double protein, double fat, double carb,
                  double fiber, double sodium)
{
    FoodItem f;
    f.name = QString::fromUtf8(name);
    f.category = QString::fromUtf8(category);
    f.defaultPortionG = defaultPortionG;
    f.per100g = Nutrition{cal, protein, fat, carb, fiber, sodium};
    return f;
}

} // namespace

NutritionService &NutritionService::instance()
{
    static NutritionService s;
    return s;
}

NutritionService::NutritionService()
{
    // ---------- 主食 ----------
    m_foods << makeFood("米饭", "主食", 150, 116, 2.6, 0.3, 25.9, 0.3, 2);
    m_foods << makeFood("馒头", "主食", 100, 223, 7.0, 1.1, 47.0, 1.3, 165);
    m_foods << makeFood("面条(煮)", "主食", 200, 110, 3.9, 0.4, 22.8, 0.4, 25);
    m_foods << makeFood("全麦面包", "主食", 50, 246, 10.0, 3.4, 46.0, 6.8, 380);
    m_foods << makeFood("红薯", "主食", 150, 86, 1.6, 0.2, 20.1, 3.0, 28);
    m_foods << makeFood("玉米(鲜)", "主食", 100, 112, 4.0, 1.2, 22.8, 2.9, 1);
    m_foods << makeFood("燕麦粥", "主食", 200, 68, 2.3, 1.4, 11.9, 1.7, 22);
    m_foods << makeFood("小米粥", "主食", 200, 46, 1.4, 0.7, 8.4, 0.2, 4);
    m_foods << makeFood("包子(猪肉)", "主食", 100, 227, 7.5, 6.0, 34.0, 1.5, 260);
    m_foods << makeFood("油条", "主食", 50, 388, 6.9, 17.6, 51.0, 0.9, 585);

    // ---------- 肉蛋水产 ----------
    m_foods << makeFood("鸡蛋(煮)", "肉蛋", 50, 144, 13.3, 8.8, 2.8, 0.0, 131);
    m_foods << makeFood("鸡胸肉", "肉蛋", 100, 133, 19.4, 5.0, 2.5, 0.0, 34);
    m_foods << makeFood("猪里脊", "肉蛋", 100, 155, 20.2, 7.9, 0.7, 0.0, 43);
    m_foods << makeFood("瘦牛肉", "肉蛋", 100, 106, 20.2, 2.3, 1.2, 0.0, 53);
    m_foods << makeFood("清蒸鱼", "肉蛋", 120, 113, 17.9, 4.1, 0.0, 0.0, 55);
    m_foods << makeFood("白灼虾", "肉蛋", 100, 93, 18.6, 0.8, 2.8, 0.0, 165);
    m_foods << makeFood("卤鸡腿", "肉蛋", 150, 215, 23.0, 12.0, 3.0, 0.0, 620);
    m_foods << makeFood("红烧肉", "肉蛋", 120, 478, 12.0, 45.0, 6.0, 0.0, 400);
    m_foods << makeFood("香肠", "肉蛋", 50, 508, 24.0, 40.0, 5.0, 0.0, 840);

    // ---------- 家常菜 ----------
    m_foods << makeFood("宫保鸡丁", "家常菜", 150, 178, 12.0, 11.0, 8.0, 1.0, 480);
    m_foods << makeFood("鱼香肉丝", "家常菜", 150, 154, 9.0, 8.0, 11.0, 1.2, 500);
    m_foods << makeFood("西红柿炒鸡蛋", "家常菜", 150, 95, 5.0, 6.0, 5.0, 0.8, 320);
    m_foods << makeFood("麻婆豆腐", "家常菜", 150, 124, 8.0, 8.0, 5.0, 1.5, 560);
    m_foods << makeFood("酸辣土豆丝", "家常菜", 150, 105, 2.0, 5.0, 14.0, 1.8, 380);
    m_foods << makeFood("清炒时蔬", "家常菜", 150, 55, 2.0, 3.0, 5.0, 2.2, 300);
    m_foods << makeFood("蒜蓉西兰花", "家常菜", 150, 45, 3.0, 2.0, 5.0, 3.0, 280);
    m_foods << makeFood("红烧茄子", "家常菜", 150, 128, 2.0, 7.0, 16.0, 3.0, 460);
    m_foods << makeFood("冬瓜排骨汤", "汤粥", 250, 58, 4.0, 3.0, 4.0, 0.5, 420);
    m_foods << makeFood("紫菜蛋花汤", "汤粥", 250, 24, 1.5, 0.8, 2.5, 0.4, 250);

    // ---------- 蔬菜 ----------
    m_foods << makeFood("西兰花", "蔬菜", 100, 36, 4.1, 0.6, 4.3, 2.5, 18);
    m_foods << makeFood("菠菜", "蔬菜", 100, 28, 2.6, 0.3, 4.5, 1.7, 85);
    m_foods << makeFood("生菜", "蔬菜", 100, 15, 1.3, 0.3, 2.0, 0.7, 32);
    m_foods << makeFood("西红柿", "蔬菜", 100, 20, 0.9, 0.2, 4.0, 0.5, 5);
    m_foods << makeFood("黄瓜", "蔬菜", 100, 16, 0.8, 0.2, 2.9, 0.5, 5);
    m_foods << makeFood("胡萝卜", "蔬菜", 100, 39, 1.0, 0.2, 8.8, 1.1, 71);
    m_foods << makeFood("土豆", "蔬菜", 100, 77, 2.0, 0.1, 17.2, 0.7, 6);
    m_foods << makeFood("茄子", "蔬菜", 100, 23, 1.1, 0.2, 4.9, 1.3, 5);
    m_foods << makeFood("大白菜", "蔬菜", 100, 17, 1.5, 0.1, 3.2, 0.8, 57);
    m_foods << makeFood("青椒", "蔬菜", 100, 22, 1.0, 0.2, 4.0, 1.4, 3);

    // ---------- 豆制品 ----------
    m_foods << makeFood("豆腐", "豆制品", 100, 84, 8.1, 3.7, 4.2, 0.4, 7);
    m_foods << makeFood("豆浆", "豆制品", 250, 31, 3.0, 1.6, 1.2, 0.3, 3);
    m_foods << makeFood("腐竹", "豆制品", 30, 461, 44.6, 21.7, 22.3, 1.0, 26);

    // ---------- 水果 ----------
    m_foods << makeFood("苹果", "水果", 150, 53, 0.4, 0.2, 13.7, 1.7, 1);
    m_foods << makeFood("香蕉", "水果", 120, 93, 1.4, 0.2, 22.0, 1.2, 1);
    m_foods << makeFood("橙子", "水果", 150, 48, 0.8, 0.2, 11.1, 0.6, 1);
    m_foods << makeFood("西瓜", "水果", 200, 26, 0.6, 0.1, 6.8, 0.3, 3);
    m_foods << makeFood("葡萄", "水果", 100, 45, 0.4, 0.2, 10.3, 0.4, 2);

    // ---------- 饮品 ----------
    m_foods << makeFood("纯牛奶", "饮品", 250, 54, 3.0, 3.2, 3.4, 0.0, 37);
    m_foods << makeFood("酸奶", "饮品", 150, 72, 2.5, 2.7, 9.3, 0.0, 40);
    m_foods << makeFood("可乐", "饮品", 330, 43, 0.0, 0.0, 10.8, 0.0, 12);
    m_foods << makeFood("美式咖啡", "饮品", 200, 2, 0.1, 0.0, 0.3, 0.0, 2);

    // ---------- 零食 ----------
    m_foods << makeFood("薯片", "零食", 40, 548, 5.5, 37.6, 49.2, 3.0, 525);
    m_foods << makeFood("黑巧克力", "零食", 30, 589, 4.3, 40.1, 53.4, 5.9, 10);
    m_foods << makeFood("坚果混合", "零食", 30, 607, 20.0, 53.0, 20.0, 6.0, 180);

    // 分配顺序ID（与数据库 foods 表 ID 对应）
    for (int i = 0; i < m_foods.size(); ++i)
        m_foods[i].id = i + 1;

    qInfo() << "[NutritionService] 演示食物库加载完成，共" << m_foods.size() << "条";
}

QVector<FoodItem> NutritionService::searchFoods(const QString &keyword) const
{
    const QString k = keyword.trimmed();
    QVector<FoodItem> out;
    for (const FoodItem &f : m_foods) {
        if (k.isEmpty() || f.name.contains(k, Qt::CaseInsensitive) || f.category.contains(k, Qt::CaseInsensitive))
            out << f;
        if (out.size() >= 30)
            break;
    }
    return out;
}

const FoodItem *NutritionService::findByName(const QString &name) const
{
    for (const FoodItem &f : m_foods)
        if (f.name == name)
            return &f;
    return nullptr;
}

Nutrition NutritionService::calcAmount(const FoodItem &food, double portionG) const
{
    const double r = portionG / 100.0;
    Nutrition n;
    n.cal     = food.per100g.cal     * r;
    n.protein = food.per100g.protein * r;
    n.fat     = food.per100g.fat     * r;
    n.carb    = food.per100g.carb    * r;
    n.fiber   = food.per100g.fiber   * r;
    n.sodium  = food.per100g.sodium  * r;
    return n;
}

QString NutritionService::formatKcal(double cal)
{
    return QString::number(qRound(cal)) + QStringLiteral(" kcal");
}

QString NutritionService::formatGram(double g)
{
    return QString::number(g, 'f', 1) + QStringLiteral(" g");
}
