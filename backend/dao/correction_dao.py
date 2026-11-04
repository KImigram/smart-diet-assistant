"""识别纠错 DAO：recognition_corrections"""
from database.connection import execute_query, execute_update


class CorrectionDAO:
    @staticmethod
    def add(user_id: int, original_name: str, corrected_food_id: int):
        return execute_update(
            """INSERT INTO recognition_corrections (user_id, original_name, corrected_food_id)
               VALUES (%s, %s, %s)""",
            (user_id, original_name, corrected_food_id),
        )

    @staticmethod
    def find_correction(original_name: str):
        """根据原始识别名查找修正记录（取最新）"""
        sql = """
            SELECT rc.id, rc.original_name, rc.corrected_food_id,
                   f.name AS corrected_name
            FROM recognition_corrections rc
            JOIN foods f ON rc.corrected_food_id = f.id
            WHERE rc.original_name = %s
            ORDER BY rc.created_at DESC LIMIT 1
        """
        rows = execute_query(sql, (original_name,))
        return rows[0] if rows else None
