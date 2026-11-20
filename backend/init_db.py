"""数据库初始化：执行 schema.sql + init_data.sql
用法：python init_db.py
需要 MySQL 已启动，连接信息在 config.py
"""
import mysql.connector
from config import DB_CONFIG


def execute_sql_file(cursor, filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        sql = f.read()
    # 按分号拆分执行（处理存储过程等复杂语句时需更谨慎，此处建表够用）
    statements = [s.strip() for s in sql.split(";") if s.strip()]
    for stmt in statements:
        if stmt.upper().startswith("USE "):
            continue  # 连接时已指定 database
        try:
            cursor.execute(stmt)
        except Exception as e:
            print(f"  [skip] {e}")


def main():
    print("连接 MySQL...")
    conn = mysql.connector.connect(
        host=DB_CONFIG["host"], port=DB_CONFIG["port"],
        user=DB_CONFIG["user"], password=DB_CONFIG["password"],
        charset="utf8mb4",
    )
    cursor = conn.cursor()

    print("创建数据库...")
    cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DB_CONFIG['database']} "
                   f"DEFAULT CHARACTER SET utf8mb4")
    cursor.execute(f"USE {DB_CONFIG['database']}")

    print("执行 schema.sql（建表）...")
    execute_sql_file(cursor, "database/schema.sql")

    print("执行 init_data.sql（食物数据）...")
    execute_sql_file(cursor, "database/init_data.sql")

    conn.commit()

    # 验证
    cursor.execute("SHOW TABLES")
    tables = [r[0] for r in cursor.fetchall()]
    print(f"\n数据库 '{DB_CONFIG['database']}' 初始化完成，共 {len(tables)} 张表：")
    for t in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {t}")
        cnt = cursor.fetchone()[0]
        print(f"  {t}: {cnt} 行")

    cursor.close()
    conn.close()


if __name__ == "__main__":
    main()
