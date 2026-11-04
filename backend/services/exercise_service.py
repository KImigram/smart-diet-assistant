"""
运动教练服务（v2）
- 根据【当天饮食摄入 + 用户目标 + 偏好运动】由本地 LLM 生成当天多任务运动计划（1~N个任务可混合运动）
- 计划需用户确认后才生成打卡清单
- 打卡简化：仅确认"完成/未完成"
- 达标判定：当日全部任务完成 = 达标，LLM 结合饮食给出建议
"""
import json
import re
from datetime import date

from ai.llm_client import get_llm
from dao.exercise_dao import ExerciseDAO
from dao.user_dao import UserDAO
from services.stats_service import StatsService

# 支持的运动类型（前端多选同源）
SPORT_TYPES = [
    "跑步", "游泳", "骑行", "乒乓球", "羽毛球", "篮球", "足球", "网球",
    "排球", "跳绳", "健身", "瑜伽", "爬山", "舞蹈", "快走", "划船",
]
GOALS = ["减脂", "增肌", "保持健康", "提升耐力", "备战比赛", "体态改善", "综合提升"]


class ExerciseService:

    # ---------- 生成计划（与当天饮食挂钩） ----------
    @staticmethod
    def generate_plan(user_id: int, goal: str,
                      preferred_sports: list[str],
                      preferred_ratios: dict = None,
                      plan_date: str = None) -> dict:
        """
        1) 查当天饮食摄入与用户档案
        2) LLM 分析饮食 → 按用户选择的运动及占比生成当天 1~N 个任务
        3) 入库 status=pending（待用户确认）
        """
        preferred_ratios = preferred_ratios or {}
        plan_date = plan_date or date.today().strftime("%Y-%m-%d")

        # 当天饮食
        diet = StatsService.daily(user_id, plan_date)
        total = diet.get("total", {})
        targets = diet.get("targets", {})
        # 用户档案
        profile = UserDAO.get_profile(user_id) or {}

        # 运动偏好文本（含占比）
        if preferred_sports:
            ratio_txt = []
            for s in preferred_sports:
                r = preferred_ratios.get(s, 0)
                if r and r < 100:
                    ratio_txt.append(f"{s}约{r}%")
                elif r == 100:
                    ratio_txt.append(s)
                else:
                    ratio_txt.append(s)
            sports_txt = "、".join(ratio_txt)
        else:
            sports_txt = "不限（由你推荐）"

        llm = get_llm()
        prompt = (
            "你是运动+营养教练。根据用户今天的饮食摄入，为他定制【今天】的运动计划。\n"
            f"今日饮食摄入：总热量 {total.get('calorie', 0)} kcal，"
            f"蛋白质 {total.get('protein', 0)}g，脂肪 {total.get('fat', 0)}g，碳水 {total.get('carb', 0)}g\n"
            f"用户每日目标热量：{targets.get('calorie', 2000)} kcal\n"
            f"用户目标：{goal or '综合提升'}\n"
            f"用户信息：性别{profile.get('gender', '未知')}，年龄{profile.get('age', '未知')}，"
            f"身高{profile.get('height_cm', '未知')}cm，体重{profile.get('weight_kg', '未知')}kg\n"
            f"用户今天想做的运动及占比：{sports_txt}\n\n"
            "分析要求：\n"
            "1. 判断今天饮食相对目标热量是否超标/不足，结合三大营养素结构给出针对性运动建议；\n"
            "2. 为每个用户选择的运动各生成恰好一个任务（共N个任务，N=所选运动数，最多4个；"
            "若所选超过4个只取占比最高的4个）；\n"
            "3. 任务时长严格按占比分配：先按当天摄入确定总运动时长"
            "（摄入超标则总消耗≈超标热量，未超标则安排150~300kcal的维持性运动），"
            "然后每个运动任务的时长占总时长的比例=该运动占比（占比50%的运动时长是占比25%的两倍）；\n"
            "4. 只从用户选择的类型里挑（若用户没选则你推荐合适的）；\n"
            "5. 只输出一个JSON对象，不要任何其他文字：\n"
            '{"summary":"一两句说明为什么这样安排（引用今天摄入和目标热量的对比）",'
            '"tasks":[{"sport_type":"跑步","title":"慢跑30分钟","content":"中等配速慢跑，心率130-150","duration_min":30,"distance_km":4.0,"calories":250}]}'
        )
        text = llm.chat(
            [{"role": "system", "content": "你只输出JSON，不输出任何解释。"},
             {"role": "user", "content": prompt}],
            temperature=0.4, max_tokens=900,
        )
        data = ExerciseService._parse_plan_json(text)
        if not data or not data.get("tasks"):
            data = ExerciseService._fallback_plan(total.get("calorie", 0),
                                                  targets.get("calorie", 2000),
                                                  preferred_sports, preferred_ratios)
        tasks = [t for t in data["tasks"][:4]]
        # 校验：必须覆盖所有所选运动（按占比取前4），LLM 漏掉的用模板补齐
        tasks = ExerciseService._enforce_selected(tasks, preferred_sports,
                                                  preferred_ratios)
        # 硬保证：时长严格按占比分配（占比不同 → 计划必然不同）
        tasks = ExerciseService._enforce_ratio_durations(
            tasks, preferred_ratios,
            total.get("calorie", 0), targets.get("calorie", 2000))
        summary = data.get("summary", "根据今日饮食与目标生成的当日运动计划。")

        plan_id = ExerciseDAO.create_plan(user_id, plan_date, goal,
                                          json.dumps(tasks, ensure_ascii=False),
                                          summary)
        return ExerciseService._plan_dict(
            ExerciseDAO.get_plan(plan_id), checkins=[])

    @staticmethod
    def _parse_plan_json(text: str) -> dict | None:
        if not text:
            return None
        cleaned = re.sub(r"```(?:json)?", "", text).strip()
        start, end = cleaned.find("{"), cleaned.rfind("}")
        if start < 0 or end <= start:
            return None
        try:
            data = json.loads(cleaned[start:end + 1])
        except json.JSONDecodeError:
            return None
        if not isinstance(data, dict):
            return None
        tasks = []
        for item in data.get("tasks", [])[:4]:
            if not isinstance(item, dict):
                continue
            try:
                tasks.append({
                    "sport_type": str(item.get("sport_type", "")),
                    "title": str(item.get("title", "")),
                    "content": str(item.get("content", "")),
                    "duration_min": max(0, int(float(item.get("duration_min", 0) or 0))),
                    "distance_km": max(0.0, float(item.get("distance_km", 0) or 0)),
                    "calories": max(0, int(float(item.get("calories", 0) or 0))),
                })
            except (TypeError, ValueError):
                continue
        if not tasks:
            return None
        return {"summary": str(data.get("summary", "")), "tasks": tasks}

    @staticmethod
    def _enforce_selected(tasks: list, preferred: list[str],
                          ratios: dict) -> list:
        """保证计划覆盖用户选择的全部运动（按占比取前4），缺失的补模板任务"""
        if not preferred:
            return tasks
        sel = sorted(preferred, key=lambda s: -ratios.get(s, 0))[:4]
        existing = {t.get("sport_type") for t in tasks}
        for s in sel:
            if s not in existing:
                tasks.append({
                    "sport_type": s,
                    "title": f"{s} 30分钟",
                    "content": f"中等强度{s}，循序渐进",
                    "duration_min": 30,
                    "distance_km": 4.0 if s in ("跑步", "快走") else 0.0,
                    "calories": 180,
                })
        order = {s: i for i, s in enumerate(sel)}
        tasks.sort(key=lambda t: order.get(t.get("sport_type", ""), 99))
        return tasks[:4]

    @staticmethod
    def _enforce_ratio_durations(tasks: list, ratios: dict,
                                 today_cal: float, target_cal: float) -> list:
        """
        硬性保证任务时长/热量/距离严格按占比分配：
        - 摄入超标 → 总时长≈超标热量/6（最多150分钟）；未超标 → 基准60分钟+每任务15分钟
        - 每个运动时长 = 总时长 × 占比（10分钟取整，尾差补最后一项）
        - 热量/距离按运动强度系数换算，标题里的分钟数同步
        """
        ratios = ratios or {}
        if not tasks:
            return tasks
        surplus = today_cal - target_cal
        if surplus > 200:
            total_min = int(min(150, surplus / 6.0))
        else:
            total_min = 60 + 15 * max(0, len(tasks) - 1)
        total_min = max(30, min(150, total_min))

        ratio_sum = sum(ratios.get(t.get("sport_type", ""), 0) for t in tasks)
        if ratio_sum <= 0:
            ratio_sum = 100.0

        kcal_rate = {"跑步": 6.5, "快走": 5.5, "游泳": 8.0, "骑行": 6.5,
                     "跳绳": 10.0, "划船": 7.0, "篮球": 7.5, "足球": 8.0,
                     "羽毛球": 6.0, "乒乓球": 5.0, "网球": 7.0, "排球": 6.0,
                     "爬山": 7.5, "舞蹈": 6.5, "瑜伽": 4.0, "健身": 7.0}

        assigned = 0
        for i, t in enumerate(tasks):
            sport = t.get("sport_type", "")
            r = ratios.get(sport, 0)
            if i == len(tasks) - 1:
                dur = max(15, total_min - assigned)
            else:
                dur = max(15, int(total_min * r / ratio_sum / 10 + 0.5) * 10)
            assigned += dur
            t["duration_min"] = dur
            t["calories"] = max(40, int(dur * kcal_rate.get(sport, 6.0)))
            if sport in ("跑步", "快走"):
                t["distance_km"] = round(dur * 0.125, 1)
            elif sport == "骑行":
                t["distance_km"] = round(dur * 0.25, 1)
            else:
                t["distance_km"] = 0.0
            # 标题分钟数同步
            title = str(t.get("title", ""))
            m = re.search(r"(\d+)\s*分钟", title)
            if m:
                t["title"] = re.sub(r"\d+\s*分钟", f"{dur}分钟", title)
            else:
                t["title"] = f"{sport} {dur}分钟"
        return tasks

    @staticmethod
    def _fallback_plan(today_cal: float, target_cal: float,
                       preferred: list[str], ratios: dict = None) -> dict:
        """LLM 异常时内置模板：按占比给每个所选运动安排任务"""
        ratios = ratios or {}
        surplus = max(0.0, today_cal - target_cal)
        sel = (sorted(preferred, key=lambda s: -ratios.get(s, 0))[:4]
               if preferred else ["快走"])
        total_min = 90
        tasks = []
        for i, s in enumerate(sel):
            r = ratios.get(s, 100 // len(sel))
            dur = max(15, int(total_min * r / 100 / 5 + 0.5) * 5)
            # 尾差：最后一项补齐，保证总时长≈total_min
            if i == len(sel) - 1:
                used = sum(t["duration_min"] for t in tasks)
                dur = max(15, total_min - used)
            tasks.append({
                "sport_type": s,
                "title": f"{s} {dur}分钟",
                "content": f"中等强度{s}，循序渐进",
                "duration_min": dur,
                "distance_km": 4.0 if s in ("跑步", "快走") else 0.0,
                "calories": max(60, int(dur * 5)),
            })
        reason = (f"今日摄入 {today_cal:.0f} kcal，高于目标 {target_cal:.0f} kcal，"
                  f"建议通过运动消耗约 {surplus:.0f} kcal。" if surplus > 0
                  else f"今日摄入 {today_cal:.0f} kcal，处于目标范围，安排适度运动维持状态。")
        return {"summary": reason, "tasks": tasks}

    # ---------- 确认计划 → 生成打卡清单 ----------
    @staticmethod
    def confirm_plan(plan_id: int) -> dict:
        plan = ExerciseDAO.get_plan(plan_id)
        if not plan:
            return {"ok": False, "error": "计划不存在"}
        if plan["status"] == "confirmed":
            # 幂等：已确认则返回现有清单（无清单则补建）
            checkins = ExerciseDAO.list_checkins(plan_id)
            if not checkins:
                try:
                    tasks = json.loads(plan["tasks"] or "[]")
                except json.JSONDecodeError:
                    tasks = []
                ExerciseDAO.create_checkins(plan_id, tasks)
                checkins = ExerciseDAO.list_checkins(plan_id)
            return {"ok": True, "plan": ExerciseService._plan_dict(plan, checkins)}
        if not ExerciseDAO.confirm_plan(plan_id):
            return {"ok": False, "error": "计划状态异常"}
        try:
            tasks = json.loads(plan["tasks"] or "[]")
        except json.JSONDecodeError:
            tasks = []
        ExerciseDAO.create_checkins(plan_id, tasks)
        plan = ExerciseDAO.get_plan(plan_id)
        checkins = ExerciseDAO.list_checkins(plan_id)
        return {"ok": True, "plan": ExerciseService._plan_dict(plan, checkins)}

    # ---------- 查询 ----------
    @staticmethod
    def today_plan(user_id: int, plan_date: str = None) -> dict | None:
        plan_date = plan_date or date.today().strftime("%Y-%m-%d")
        plan = ExerciseDAO.get_plan_of_date(user_id, plan_date)
        if not plan:
            return None
        checkins = ExerciseDAO.list_checkins(plan["id"])
        return ExerciseService._plan_dict(plan, checkins)

    @staticmethod
    def list_plans_wrapper(user_id: int, days: int = 14):
        plans = ExerciseDAO.list_plans(user_id, days)
        result = []
        for p in plans:
            result.append(ExerciseService._plan_dict(p, ExerciseDAO.list_checkins(p["id"])))
        return result

    @staticmethod
    def _plan_dict(plan: dict, checkins: list) -> dict:
        try:
            tasks = json.loads(plan.get("tasks") or "[]")
        except json.JSONDecodeError:
            tasks = []
        # 合并打卡状态到任务
        checkin_map = {c["task_index"]: c for c in checkins}
        for i, t in enumerate(tasks):
            c = checkin_map.get(i)
            t["checkin_id"] = c["id"] if c else 0
            t["completed"] = bool(c and c["completed"])
        return {
            "plan_id": plan["id"],
            "plan_date": str(plan.get("plan_date")),
            "goal": plan.get("goal", ""),
            "status": plan.get("status", "pending"),
            "summary": plan.get("summary", ""),
            "tasks": tasks,
            "created_at": str(plan.get("created_at")) if plan.get("created_at") else "",
        }

    # ---------- 打卡（简化：仅确认完成与否） ----------
    @staticmethod
    def set_checkin(checkin_id: int, completed: bool) -> bool:
        return ExerciseDAO.set_checkin(checkin_id, completed)

    # ---------- 达标判定 ----------
    @staticmethod
    def analyze_day(user_id: int, plan_id: int, plan_date: str = None) -> dict:
        plan_date = plan_date or date.today().strftime("%Y-%m-%d")
        plan = ExerciseDAO.get_plan(plan_id)
        if not plan:
            return {"ok": False, "error": "计划不存在"}

        checkins = ExerciseDAO.list_checkins(plan_id)
        done = sum(1 for c in checkins if c["completed"])
        total_cnt = len(checkins)
        all_done = total_cnt > 0 and done == total_cnt
        met = all_done

        # 当天饮食（用于建议）
        diet = StatsService.daily(user_id, plan_date)
        today_cal = diet.get("total", {}).get("calorie", 0)
        target_cal = diet.get("targets", {}).get("calorie", 2000)

        reasons = []
        if total_cnt == 0:
            reasons.append("今日计划尚未确认")
            met = False
        else:
            for c in checkins:
                if not c["completed"]:
                    reasons.append(f"未完成：{c['title'] or c['sport_type']}（任务{c['task_index'] + 1}）")

        advice = ExerciseService._llm_advice(
            plan, done, total_cnt, today_cal, target_cal, met)

        return {
            "ok": True,
            "date": plan_date,
            "done": done,
            "total": total_cnt,
            "met": met,
            "reasons": reasons,
            "advice": advice,
            "summary": plan.get("summary", ""),
            "today_calorie": round(today_cal, 1),
            "target_calorie": round(target_cal, 1),
        }

    @staticmethod
    def _llm_advice(plan: dict, done: int, total: int,
                    today_cal: float, target_cal: float, met: bool) -> str:
        llm = get_llm()
        prompt = (
            f"用户今日饮食摄入 {today_cal:.0f} kcal（目标 {target_cal:.0f} kcal）。\n"
            f"今日运动计划任务共 {total} 个，已完成 {done} 个，"
            f"{'全部完成' if met else '部分完成'}。\n"
            f"计划说明：{plan.get('summary', '')}\n"
            "请用2-3句话点评今日运动完成情况，并结合饮食给出明日建议（中文，口语化）。"
        )
        try:
            reply = llm.chat(
                [{"role": "system", "content": "你是运动营养教练，回复简短实用。"},
                 {"role": "user", "content": prompt}],
                temperature=0.4, max_tokens=300,
            )
            return reply.strip()
        except Exception:
            return ("今日运动全部完成，配合饮食控制，继续保持！" if met
                    else "部分任务未完成，明天适当补足即可，注意劳逸结合。")

    # ---------- 运动统计（供统计报告页） ----------
    @staticmethod
    def stats(user_id: int, mode: str = "day", date_str: str = None) -> dict:
        """
        mode=day : 当天计划中【已完成打卡】的运动汇总（时长/热量/距离，按运动类型）
        mode=week: 最近 7 天（含 date_str）每天已完成运动的热量/时长趋势 + 按运动类型累计
        """
        from datetime import datetime, timedelta
        date_str = date_str or date.today().strftime("%Y-%m-%d")
        base = datetime.strptime(date_str, "%Y-%m-%d").date()

        def _completed_agg(plan):
            """给定计划行 → (任务总数, 完成数, 已完成任务的 by_sport 汇总)"""
            try:
                tasks = json.loads(plan.get("tasks") or "[]")
            except json.JSONDecodeError:
                tasks = []
            checkins = ExerciseDAO.list_checkins(plan["id"])
            done_idx = {c["task_index"] for c in checkins if c["completed"]}
            by_sport = {}
            total_min = total_kcal = total_km = 0.0
            for i, t in enumerate(tasks):
                if i not in done_idx:
                    continue
                sport = t.get("sport_type", "运动")
                d = max(0.0, float(t.get("duration_min", 0) or 0))
                k = max(0.0, float(t.get("calories", 0) or 0))
                km = max(0.0, float(t.get("distance_km", 0) or 0))
                s = by_sport.setdefault(sport, {"sport": sport, "duration_min": 0.0,
                                                "calories": 0.0, "distance_km": 0.0})
                s["duration_min"] = round(s["duration_min"] + d, 1)
                s["calories"] = round(s["calories"] + k, 1)
                s["distance_km"] = round(s["distance_km"] + km, 1)
                total_min += d
                total_kcal += k
                total_km += km
            return len(tasks), len(done_idx), by_sport, total_min, total_kcal, total_km

        if mode == "week":
            start = base - timedelta(days=6)
            labels, daily_cal, daily_min = [], [], []
            week_by_sport = {}
            total_min = total_kcal = 0.0
            task_total = completed_count = active_days = 0
            for i in range(7):
                d = (start + timedelta(days=i)).strftime("%Y-%m-%d")
                labels.append((start + timedelta(days=i)).strftime("%m/%d"))
                plan = ExerciseDAO.get_plan_of_date(user_id, d)
                cal = min_ = 0.0
                if plan and plan.get("status") == "confirmed":
                    tt, dc, by_sport, tm, tk, _ = _completed_agg(plan)
                    task_total += tt
                    completed_count += dc
                    for s in by_sport.values():
                        ws = week_by_sport.setdefault(s["sport"], {
                            "sport": s["sport"], "duration_min": 0.0,
                            "calories": 0.0, "distance_km": 0.0})
                        ws["duration_min"] = round(ws["duration_min"] + s["duration_min"], 1)
                        ws["calories"] = round(ws["calories"] + s["calories"], 1)
                        ws["distance_km"] = round(ws["distance_km"] + s["distance_km"], 1)
                    cal, min_ = tk, tm
                    total_kcal += tk
                    total_min += tm
                    if dc > 0:
                        active_days += 1
                daily_cal.append(round(cal, 1))
                daily_min.append(round(min_, 1))
            return {
                "mode": "week",
                "labels": labels,
                "daily_calories": daily_cal,
                "daily_duration": daily_min,
                "total_duration_min": round(total_min, 1),
                "total_calories": round(total_kcal, 1),
                "task_total": task_total,
                "completed_count": completed_count,
                "active_days": active_days,
                "by_sport": list(week_by_sport.values()),
            }

        # mode == day
        plan = ExerciseDAO.get_plan_of_date(user_id, date_str)
        if not plan:
            return {"mode": "day", "has_plan": False, "plan_status": "",
                    "task_total": 0, "completed_count": 0,
                    "total_duration_min": 0.0, "total_calories": 0.0,
                    "total_distance_km": 0.0, "by_sport": []}
        tt, dc, by_sport, tm, tk, tkm = _completed_agg(plan)
        rate = round(dc / tt * 100, 1) if tt else 0.0
        return {
            "mode": "day",
            "has_plan": True,
            "plan_status": plan.get("status", "pending"),
            "task_total": tt,
            "completed_count": dc,
            "completion_rate": rate,
            "total_duration_min": round(tm, 1),
            "total_calories": round(tk, 1),
            "total_distance_km": round(tkm, 1),
            "by_sport": list(by_sport.values()),
        }
