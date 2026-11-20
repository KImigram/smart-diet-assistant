"""运动教练 DAO：exercise_plans（当日计划，含多任务）+ exercise_checkins（打卡清单）"""
from database.connection import execute_query, execute_update


class ExerciseDAO:
    # ---------- 计划 ----------
    @staticmethod
    def create_plan(user_id: int, plan_date: str, goal: str,
                    tasks: str, summary: str) -> int:
        return execute_update(
            """INSERT INTO exercise_plans (user_id, plan_date, goal, tasks, summary)
               VALUES (%s, %s, %s, %s, %s)""",
            (user_id, plan_date, goal, tasks, summary),
        )

    @staticmethod
    def get_plan(plan_id: int):
        rows = execute_query(
            "SELECT * FROM exercise_plans WHERE id = %s", (plan_id,))
        return rows[0] if rows else None

    @staticmethod
    def get_plan_of_date(user_id: int, plan_date: str):
        rows = execute_query(
            """SELECT * FROM exercise_plans
               WHERE user_id = %s AND plan_date = %s
               ORDER BY id DESC LIMIT 1""",
            (user_id, plan_date))
        return rows[0] if rows else None

    @staticmethod
    def list_plans(user_id: int, days: int = 14):
        return execute_query(
            """SELECT * FROM exercise_plans
               WHERE user_id = %s AND plan_date >= DATE_SUB(CURDATE(), INTERVAL %s DAY)
               ORDER BY plan_date DESC, id DESC""",
            (user_id, days))

    @staticmethod
    def confirm_plan(plan_id: int) -> bool:
        """pending → confirmed；返回是否成功（非 pending 返回 False）"""
        rows = execute_query(
            "SELECT status FROM exercise_plans WHERE id = %s", (plan_id,))
        if not rows or rows[0]["status"] != "pending":
            return False
        execute_update(
            "UPDATE exercise_plans SET status = 'confirmed' WHERE id = %s",
            (plan_id,))
        return True

    # ---------- 打卡清单 ----------
    @staticmethod
    def create_checkins(plan_id: int, tasks: list) -> None:
        for i, t in enumerate(tasks):
            execute_update(
                """INSERT INTO exercise_checkins (plan_id, task_index, sport_type, title)
                   VALUES (%s, %s, %s, %s)""",
                (plan_id, i,
                 t.get("sport_type", ""),
                 t.get("title", "") or t.get("content", "")[:40]))

    @staticmethod
    def list_checkins(plan_id: int):
        return execute_query(
            "SELECT * FROM exercise_checkins WHERE plan_id = %s ORDER BY task_index ASC",
            (plan_id,))

    @staticmethod
    def set_checkin(checkin_id: int, completed: bool) -> bool:
        rows = execute_query(
            "SELECT id FROM exercise_checkins WHERE id = %s", (checkin_id,))
        if not rows:
            return False
        if completed:
            execute_update(
                "UPDATE exercise_checkins SET completed = 1, completed_at = NOW() WHERE id = %s",
                (checkin_id,))
        else:
            execute_update(
                "UPDATE exercise_checkins SET completed = 0, completed_at = NULL WHERE id = %s",
                (checkin_id,))
        return True
