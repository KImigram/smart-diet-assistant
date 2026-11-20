"""用户 DAO：users + health_profile + weight_records"""
import datetime
import hashlib
import hmac
import secrets
from database.connection import execute_query, execute_update


_PASSWORD_ITERATIONS = 600_000


def hash_password(password: str) -> str:
    """Return a salted PBKDF2 hash suitable for storage."""
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), bytes.fromhex(salt), _PASSWORD_ITERATIONS
    ).hex()
    return f"pbkdf2_sha256${_PASSWORD_ITERATIONS}${salt}${digest}"


def verify_password(password: str, stored_hash: str) -> bool:
    """Verify current hashes and the legacy unsalted SHA-256 demo hash."""
    if stored_hash.startswith("pbkdf2_sha256$"):
        try:
            _, iterations, salt, expected = stored_hash.split("$", 3)
            actual = hashlib.pbkdf2_hmac(
                "sha256", password.encode("utf-8"), bytes.fromhex(salt), int(iterations)
            ).hex()
            return hmac.compare_digest(actual, expected)
        except (TypeError, ValueError):
            return False

    legacy = hashlib.sha256(password.encode("utf-8")).hexdigest()
    return hmac.compare_digest(legacy, stored_hash)


class UserDAO:
    @staticmethod
    def create_user(username: str, password: str, nickname: str = ""):
        """注册新用户，返回 user_id；用户名重复返回 None"""
        # 检查用户名是否存在
        existing = execute_query("SELECT user_id FROM users WHERE username = %s", (username,))
        if existing:
            return None
        pwd_hash = hash_password(password)
        user_id = execute_update(
            "INSERT INTO users (username, password_hash, nickname) VALUES (%s, %s, %s)",
            (username, pwd_hash, nickname or username),
        )
        # 自动创建健康档案
        execute_update(
            "INSERT IGNORE INTO health_profile (user_id) VALUES (%s)",
            (user_id,),
        )
        return user_id

    @staticmethod
    def verify_user(username: str, password: str):
        """验证登录，成功返回 user_id，失败返回 None"""
        rows = execute_query(
            "SELECT user_id, password_hash FROM users WHERE username = %s",
            (username,),
        )
        if not rows or not verify_password(password, rows[0]["password_hash"]):
            return None

        # Upgrade the seeded legacy hash after the first successful login.
        if not rows[0]["password_hash"].startswith("pbkdf2_sha256$"):
            execute_update(
                "UPDATE users SET password_hash = %s WHERE user_id = %s",
                (hash_password(password), rows[0]["user_id"]),
            )
        return rows[0]["user_id"]

    @staticmethod
    def get_profile(user_id: int):
        sql = """
            SELECT u.user_id, u.username, u.nickname,
                   h.gender, h.age, h.height_cm, h.target_calorie,
                   h.activity_level, h.allergens,
                   (SELECT w.weight_kg FROM weight_records w
                    WHERE w.user_id = u.user_id
                    ORDER BY w.record_date DESC LIMIT 1) AS weight_kg
            FROM users u
            LEFT JOIN health_profile h ON u.user_id = h.user_id
            WHERE u.user_id = %s
        """
        rows = execute_query(sql, (user_id,))
        return rows[0] if rows else None

    @staticmethod
    def update_profile(user_id: int, **kwargs):
        """更新档案：nickname→users 表；weight_kg→weight_records（UPSERT到今天）；
        其余字段→health_profile 表"""
        if not kwargs:
            return None

        # 昵称 → users 表
        if "nickname" in kwargs:
            execute_update(
                "UPDATE users SET nickname = %s WHERE user_id = %s",
                (kwargs.pop("nickname"), user_id),
            )

        # 体重 → weight_records（写今天的记录）
        if "weight_kg" in kwargs:
            UserDAO.add_weight(user_id, kwargs.pop("weight_kg"),
                               datetime.date.today().strftime("%Y-%m-%d"))

        # 其余 → health_profile
        if kwargs:
            fields = ", ".join(f"{k} = %s" for k in kwargs)
            values = list(kwargs.values()) + [user_id]
            sql = f"UPDATE health_profile SET {fields} WHERE user_id = %s"
            execute_update(sql, values)
        return True

    @staticmethod
    def add_weight(user_id: int, weight_kg: float, record_date: str):
        return execute_update(
            """INSERT INTO weight_records (user_id, weight_kg, record_date)
               VALUES (%s, %s, %s)
               ON DUPLICATE KEY UPDATE weight_kg = %s""",
            (user_id, weight_kg, record_date, weight_kg),
        )

    @staticmethod
    def list_weight(user_id: int, days: int = 30):
        sql = """
            SELECT id, weight_kg, record_date
            FROM weight_records
            WHERE user_id = %s AND record_date >= DATE_SUB(CURDATE(), INTERVAL %s DAY)
            ORDER BY record_date
        """
        return execute_query(sql, (user_id, days))

    @staticmethod
    def latest_weight(user_id: int):
        sql = """
            SELECT weight_kg, record_date FROM weight_records
            WHERE user_id = %s ORDER BY record_date DESC LIMIT 1
        """
        rows = execute_query(sql, (user_id,))
        return rows[0] if rows else None
