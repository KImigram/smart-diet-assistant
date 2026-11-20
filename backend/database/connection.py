"""MySQL 连接池管理"""
import mysql.connector.pooling
from mysql.connector import Error
from config import DB_CONFIG, DB_POOL_SIZE

_pool = None


def get_pool():
    """懒加载单例连接池"""
    global _pool
    if _pool is None:
        _pool = mysql.connector.pooling.MySQLConnectionPool(
            pool_name="nutritious_pool",
            pool_size=DB_POOL_SIZE,
            **DB_CONFIG,
        )
    return _pool


def get_connection():
    """从连接池获取一个连接"""
    return get_pool().get_connection()


def execute_query(sql, params=None, fetch=True):
    """
    执行查询（SELECT），自动管理连接。
    返回 list[dict]。
    """
    conn = get_connection()
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(sql, params or ())
        return cursor.fetchall() if fetch else []
    finally:
        if cursor is not None:
            cursor.close()
        conn.close()


def execute_update(sql, params=None):
    """
    执行写操作（INSERT/UPDATE/DELETE），自动提交。
    返回 lastrowid。
    """
    conn = get_connection()
    cursor = None
    try:
        cursor = conn.cursor()
        cursor.execute(sql, params or ())
        conn.commit()
        return cursor.lastrowid
    except Error:
        conn.rollback()
        raise
    finally:
        if cursor is not None:
            cursor.close()
        conn.close()


def execute_batch(sql, params_list):
    """批量执行写操作，一个事务"""
    conn = get_connection()
    cursor = None
    try:
        cursor = conn.cursor()
        cursor.executemany(sql, params_list)
        conn.commit()
        return cursor.rowcount
    except Error:
        conn.rollback()
        raise
    finally:
        if cursor is not None:
            cursor.close()
        conn.close()
