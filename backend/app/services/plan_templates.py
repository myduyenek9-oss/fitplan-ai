from datetime import date, timedelta
from typing import Any, Mapping

from app.schemas.plan import PlanDay

_MEALS = [
    {
        "breakfast": ("燕麦鸡蛋早餐", [("燕麦", "50g"), ("低脂牛奶", "250ml"), ("水煮蛋", "2 个"), ("香蕉", "1 根")]),
        "lunch": ("鸡胸肉米饭午餐", [("熟米饭", "180g"), ("鸡胸肉", "160g"), ("西兰花", "200g"), ("橄榄油", "10g")]),
        "snack": ("酸奶水果加餐", [("无糖希腊酸奶", "200g"), ("蓝莓", "80g"), ("杏仁", "10g")]),
        "dinner": ("三文鱼土豆晚餐", [("三文鱼", "140g"), ("土豆", "250g"), ("生菜番茄沙拉", "250g"), ("油醋汁", "10g")]),
    },
    {
        "breakfast": ("全麦吐司能量早餐", [("全麦吐司", "2 片"), ("煎蛋", "2 个"), ("低脂奶酪", "1 片"), ("橙子", "1 个")]),
        "lunch": ("牛肉荞麦面午餐", [("瘦牛肉", "150g"), ("荞麦面", "干重 80g"), ("彩椒洋葱", "180g"), ("芝麻油", "5g")]),
        "snack": ("蛋白奶昔加餐", [("乳清蛋白粉", "1 勺"), ("低脂牛奶", "250ml"), ("苹果", "1 个")]),
        "dinner": ("虾仁藜麦晚餐", [("虾仁", "180g"), ("熟藜麦", "160g"), ("芦笋", "200g"), ("牛油果", "50g")]),
    },
    {
        "breakfast": ("酸奶麦片早餐", [("无糖酸奶", "250g"), ("原味麦片", "45g"), ("奇异果", "1 个"), ("花生酱", "10g")]),
        "lunch": ("番茄牛腩饭", [("瘦牛肉", "160g"), ("熟米饭", "170g"), ("番茄", "200g"), ("油麦菜", "150g")]),
        "snack": ("豆浆鸡蛋加餐", [("无糖豆浆", "300ml"), ("茶叶蛋", "2 个"), ("小番茄", "150g")]),
        "dinner": ("鸡腿肉意面晚餐", [("去皮鸡腿肉", "170g"), ("全麦意面", "干重 75g"), ("蘑菇番茄酱", "200g"), ("帕玛森奶酪", "8g")]),
    },
    {
        "breakfast": ("豆腐鸡蛋早餐", [("嫩豆腐", "200g"), ("鸡蛋", "2 个"), ("全麦馒头", "1 个（约 80g）"), ("小番茄", "150g")]),
        "lunch": ("照烧鸡肉饭", [("去皮鸡腿肉", "180g"), ("熟米饭", "180g"), ("胡萝卜西兰花", "220g"), ("低糖照烧汁", "15g")]),
        "snack": ("奶酪水果加餐", [("低脂奶酪", "2 片"), ("梨", "1 个"), ("核桃", "10g")]),
        "dinner": ("鳕鱼红薯晚餐", [("鳕鱼", "180g"), ("红薯", "280g"), ("炒菠菜", "200g"), ("橄榄油", "8g")]),
    },
    {
        "breakfast": ("玉米鸡蛋早餐", [("甜玉米", "1 根"), ("鸡蛋", "2 个"), ("无糖豆浆", "300ml"), ("小番茄", "150g")]),
        "lunch": ("虾仁杂粮饭", [("虾仁", "180g"), ("熟杂粮饭", "180g"), ("西兰花", "200g"), ("橄榄油", "8g")]),
        "snack": ("紫薯酸奶加餐", [("无糖酸奶", "250g"), ("紫薯", "120g"), ("核桃", "10g")]),
        "dinner": ("牛肉土豆晚餐", [("瘦牛肉", "160g"), ("土豆", "250g"), ("彩椒洋葱", "200g"), ("橄榄油", "8g")]),
    },
    {
        "breakfast": ("里脊荞麦早餐", [("猪里脊", "100g"), ("荞麦面包", "2 片"), ("鸡蛋", "1 个"), ("苹果", "1 个")]),
        "lunch": ("鳕鱼藜麦午餐", [("鳕鱼", "180g"), ("熟藜麦", "170g"), ("芦笋", "180g"), ("橄榄油", "8g")]),
        "snack": ("奶昔坚果加餐", [("低脂牛奶", "250ml"), ("乳清蛋白粉", "1 勺"), ("香蕉", "1 根"), ("杏仁", "10g")]),
        "dinner": ("番茄鸡腿晚餐", [("去皮鸡腿肉", "170g"), ("全麦意面", "干重 75g"), ("番茄蘑菇", "200g"), ("生菜", "150g")]),
    },
    {
        "breakfast": ("紫薯牛奶早餐", [("紫薯", "180g"), ("低脂牛奶", "250ml"), ("水煮蛋", "2 个"), ("蓝莓", "80g")]),
        "lunch": ("鸡肉玉米午餐", [("鸡胸肉", "160g"), ("甜玉米", "150g"), ("熟米饭", "150g"), ("西兰花", "200g")]),
        "snack": ("水果奶酪加餐", [("低脂奶酪", "2 片"), ("橙子", "1 个"), ("腰果", "10g")]),
        "dinner": ("三文鱼荞麦晚餐", [("三文鱼", "150g"), ("荞麦面", "干重 75g"), ("菠菜", "200g"), ("蘑菇", "120g")]),
    },
]

_WORKOUTS = [
    {
        "kind": "workout", "title": "上肢 A · 推拉基础", "split": "上下肢四分化 · 第 1 练", "focus": "胸、背、肩和手臂基础动作。保留 2–3 次余力，不追求力竭。", "duration_minutes": 60,
        "warmup": "跑步机快走 5 分钟，再做肩胛绕环和主动作轻重量热身。", "instructions": "重量以动作稳定为准；前两周优先熟悉器械轨迹。",
        "exercises": [("坐姿器械卧推", 3, "8–12 次", "肩胛后收，手肘不要完全外张"), ("高位下拉", 3, "8–12 次", "拉到锁骨附近，避免大幅后仰"), ("坐姿划船", 3, "10–12 次", "先收肩胛，再拉手肘"), ("坐姿哑铃肩推", 2, "8–10 次", "核心收紧，重量宁轻勿晃"), ("绳索下压", 2, "10–12 次", "固定上臂"), ("哑铃弯举", 2, "10–12 次", "避免借力甩动")], "cooldown": "胸、背和肩各拉伸 30 秒。",
    },
    {
        "kind": "workout", "title": "下肢 A · 深蹲模式", "split": "上下肢四分化 · 第 2 练", "focus": "股四头肌、臀腿后侧和核心，先把动作做稳。", "duration_minutes": 60,
        "warmup": "单车 5 分钟，髋关节活动，徒手深蹲 2 组。", "instructions": "膝盖方向跟脚尖一致；腰背不适就减重并请教练看动作。",
        "exercises": [("腿举机", 3, "10–12 次", "下放到骨盆不卷起"), ("高脚杯深蹲", 3, "8–10 次", "双脚稳定，躯干自然直立"), ("哑铃罗马尼亚硬拉", 3, "8–10 次", "髋向后送，背部中立"), ("坐姿腿弯举", 2, "10–12 次", "缓慢还原"), ("站姿提踵", 3, "12–15 次", "顶峰停 1 秒"), ("平板支撑", 3, "30–45 秒", "腰不要塌")], "cooldown": "股四头、臀肌和小腿各拉伸 30 秒。",
    },
    {"kind": "rest", "title": "主动恢复日", "split": "恢复与活动度", "focus": "让关节和肌肉恢复，为下一次训练留状态。", "duration_minutes": 25, "warmup": None, "instructions": "轻松步行 20–30 分钟，加 5 分钟胸椎、髋部和踝关节活动。", "exercises": [], "cooldown": "睡前做 5 分钟温和拉伸。"},
    {
        "kind": "workout", "title": "上肢 B · 稳定与增肌", "split": "上下肢四分化 · 第 3 练", "focus": "换角度练胸背，补足后束和肩部稳定。", "duration_minutes": 60,
        "warmup": "椭圆机 5 分钟，弹力带拉开 2 组，主动作轻重量热身。", "instructions": "放慢下放阶段；若酸痛明显，每个动作减少 1 组。",
        "exercises": [("上斜哑铃卧推", 3, "8–12 次", "长凳约 30 度，避免耸肩"), ("辅助引体向上", 3, "6–10 次", "辅助重量以动作完整为准"), ("单臂哑铃划船", 3, "10–12 次/侧", "躯干稳定"), ("反向飞鸟机", 2, "12–15 次", "轻重量控制"), ("侧平举", 2, "12–15 次", "抬到肩高即可"), ("绳索面拉", 2, "12–15 次", "拉向眉眼高度")], "cooldown": "胸肌、背阔肌和后肩各拉伸 30 秒。",
    },
    {"kind": "rest", "title": "轻活动与恢复", "split": "恢复与活动度", "focus": "恢复下肢和肩背，保持日常活动量。", "duration_minutes": 25, "warmup": None, "instructions": "安排步行、轻松骑车或瑜伽 20–30 分钟。", "exercises": [], "cooldown": "晚间做髋屈肌和胸肌拉伸。"},
    {
        "kind": "workout", "title": "下肢 B · 臀腿后侧", "split": "上下肢四分化 · 第 4 练", "focus": "臀肌、腿后侧和单腿稳定，与下肢 A 交替。", "duration_minutes": 60,
        "warmup": "单车 5 分钟，臀桥 2 组，髋部动态活动。", "instructions": "保持约 2 次余力；分腿蹲先徒手或轻哑铃。",
        "exercises": [("史密斯臀推", 3, "8–12 次", "顶峰夹臀 1 秒"), ("史密斯分腿蹲", 3, "8–10 次/侧", "步距稳定"), ("哑铃罗马尼亚硬拉", 3, "8–10 次", "感受臀腿后侧拉伸"), ("坐姿腿弯举", 3, "10–12 次", "下放控制 2 秒"), ("腿屈伸机", 2, "12–15 次", "不锁死膝盖"), ("死虫式", 3, "8–10 次/侧", "腰背贴稳地面")], "cooldown": "臀肌、腿后侧和髋屈肌各拉伸 30 秒。",
    },
    {"kind": "rest", "title": "完全恢复日", "split": "恢复与活动度", "focus": "一周四练完成，专注恢复和下周准备。", "duration_minutes": None, "warmup": None, "instructions": "正常走动即可；可做 10 分钟轻拉伸。", "exercises": [], "cooldown": None},
]


def detailed_plan_days(start_date: date, context: Mapping[str, Any] | None = None) -> list[PlanDay]:
    goal = ((context or {}).get("daily_summary") or {}).get("goal") or {}
    calories = _number(goal, "daily_calories", 2000, 1400, 3600)
    protein = _number(goal, "protein_g", 140, 80, 260)
    carb = _number(goal, "carb_g", 230, 120, 500)
    fat = _number(goal, "fat_g", 60, 35, 130)
    specs = (("breakfast", .25), ("lunch", .30), ("snack", .15), ("dinner", .30))
    result = []
    for index in range(7):
        meals = []
        for meal_type, ratio in specs:
            name, foods = _MEALS[index % len(_MEALS)][meal_type]
            meals.append({"name": name, "meal_type": meal_type, "calories": round(calories * ratio), "protein_g": round(protein * ratio), "carb_g": round(carb * ratio), "fat_g": round(fat * ratio), "foods": [{"name": n, "amount": a} for n, a in foods]})
        workout = _WORKOUTS[index]
        meals = meals
        training = {key: value for key, value in workout.items() if key != "exercises"}
        training["exercises"] = [{"name": n, "sets": sets, "reps": reps, "rest_seconds": 90, "notes": notes} for n, sets, reps, notes in workout["exercises"]]
        result.append(PlanDay(date=start_date + timedelta(days=index), calorie_target=calories, meals=meals, training_instruction=training))
    return result


def _number(goal: Mapping[str, Any], key: str, default: float, minimum: float, maximum: float) -> float:
    try:
        return max(minimum, min(maximum, float(goal.get(key, default))))
    except (TypeError, ValueError):
        return default
