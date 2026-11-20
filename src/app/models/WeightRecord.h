#pragma once
// ============================================================
// 体重记录实体（对应数据库 weight_records 表）
// ============================================================
#include <QDate>

struct WeightRecord {
    int    id = 0;
    double weightKg = 0.0;
    QDate  date;          // 称重日期
};
