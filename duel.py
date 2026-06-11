"""
Duel 系統：兩位使用者 PK 解題數量與速度
Bot 主動查 CF API 判斷誰先 AC
"""
import os
import time
import requests
import json
import throwcf

DUEL_FILE = "duel_data.json"


def _load_duel():
    if not os.path.exists(DUEL_FILE):
        with open(DUEL_FILE, "w") as f:
            json.dump({"pending": {}, "active": {}, "history": []}, f)
    with open(DUEL_FILE, "r") as f:
        return json.load(f)


def _save_duel(data):
    with open(DUEL_FILE, "w") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def _check_solved_problems(handle: str, problems: list) -> dict:
    """
    檢查使用者已解出哪些題目
    回傳：{problem_index: submit_time, ...}
    """
    solved = {}
    try:
        resp = requests.get(
            f"https://codeforces.com/api/user.status?handle={handle}&from=1&count=200"
        )
        data = resp.json()
        if data["status"] != "OK":
            return solved
        for sub in data["result"]:
            if sub.get("verdict") != "OK":
                continue
            prob = sub.get("problem", {})
            cid = prob.get("contestId")
            idx = prob.get("index")
            for p in problems:
                if p["contestId"] == cid and p["index"] == idx:
                    if idx not in solved or sub["creationTimeSeconds"] < solved[idx]:
                        solved[idx] = sub["creationTimeSeconds"]
    except:
        pass
    return solved


def start_duel(challenger_dc: str, challenger_cf: str,
               opponent_dc: str, opponent_cf: str,
               mnrating: int, mxrating: int, num: int = 3,
               tags: list = None, duration_minutes: int = 5) -> tuple[dict, str]:
    """
    創建一場多題 duel 並抽題
    回傳 (duel_info, error_message)
    """
    # 抽多題
    problems, result = throwcf.askprob(
        mnrating=mnrating,
        mxrating=mxrating,
        num=num,
        solved=False,
        cf_handle=challenger_cf,
        tags=tags,
        indices=None
    )

    if not problems:
        return {}, result if isinstance(result, str) else "找不到符合條件的題目"

    total_rating = sum(p["rating"] for p in problems)
    avg_rating = total_rating // len(problems) if problems else 0

    duel_info = {
        "challenger_dc": challenger_dc,
        "challenger_cf": challenger_cf,
        "opponent_dc": opponent_dc,
        "opponent_cf": opponent_cf,
        "problems": [
            {
                "contestId": p["contestId"],
                "index": p["index"],
                "name": p["name"],
                "rating": p["rating"],
                "url": f"https://codeforces.com/problemset/problem/{p['contestId']}/{p['index']}"
            }
            for p in problems
        ],
        "num_problems": num,
        "avg_rating": avg_rating,
        "tags": tags or [],
        "mnrating": mnrating,
        "mxrating": mxrating,
        "start_time": time.time(),
        "duration_minutes": duration_minutes,
        "end_time": time.time() + duration_minutes * 60,
        "challenger_solves": {},
        "opponent_solves": {},
        "status": "active"
    }
    return duel_info, ""


def check_duel_result(duel_info: dict, force_check: bool = False) -> dict:
    """
    檢查 duel 結果
    - 如果有人解完所有題目 → 立即結束，比較完成時間
    - 如果時間到 → 比較解題數量
    回傳結果 dict
    """
    current_time = time.time()
    end_time = duel_info.get("end_time", duel_info["start_time"] + 300)
    problems = duel_info["problems"]
    num_problems = duel_info["num_problems"]

    c_cf = duel_info["challenger_cf"]
    o_cf = duel_info["opponent_cf"]

    # 檢查雙方已解題目
    challenger_solves = _check_solved_problems(c_cf, problems)
    opponent_solves = _check_solved_problems(o_cf, problems)

    # 更新 duel_info 中的 solved 記錄
    duel_info["challenger_solves"] = challenger_solves
    duel_info["opponent_solves"] = opponent_solves

    c_count = len(challenger_solves)
    o_count = len(opponent_solves)

    # 取得每題的最早 solve time
    def get_first_solve_times(solves: dict) -> dict:
        return {idx: t for idx, t in solves.items()}

    c_all_solved = c_count >= num_problems
    o_all_solved = o_count >= num_problems

    result = {
        "status": "active",
        "c_count": c_count,
        "o_count": o_count,
        "challenger_solves_raw": challenger_solves,
        "opponent_solves_raw": opponent_solves
    }

    # 檢查是否有人全部完成
    if c_all_solved and o_all_solved:
        # 雙方都完成，比較最後一題時間
        c_last_time = max(challenger_solves.values())
        o_last_time = max(opponent_solves.values())
        if c_last_time < o_last_time:
            result = _build_win_result(duel_info, "challenger", challenger_solves, opponent_solves, "all solved, faster")
        elif o_last_time < c_last_time:
            result = _build_win_result(duel_info, "opponent", challenger_solves, opponent_solves, "all solved, faster")
        else:
            result = _build_tie_result(duel_info, challenger_solves, opponent_solves, "all solved, tie")
    elif c_all_solved:
        result = _build_win_result(duel_info, "challenger", challenger_solves, opponent_solves, "all solved first")
    elif o_all_solved:
        result = _build_win_result(duel_info, "opponent", challenger_solves, opponent_solves, "all solved first")
    elif current_time >= end_time or force_check:
        # 時間到或強制檢查，比較解題數量
        if c_count > o_count:
            result = _build_win_result(duel_info, "challenger", challenger_solves, opponent_solves, "time up, more solves")
        elif o_count > c_count:
            result = _build_win_result(duel_info, "opponent", challenger_solves, opponent_solves, "time up, more solves")
        else:
            result = _build_tie_result(duel_info, challenger_solves, opponent_solves, "time up, tie")

    result["duel_info"] = duel_info
    return result


def _build_win_result(duel_info: dict, winner_side: str,
                      c_solves: dict, o_solves: dict,
                      reason: str) -> dict:
    """建立勝方 result"""
    if winner_side == "challenger":
        winner_dc = duel_info["challenger_dc"]
        winner_cf = duel_info["challenger_cf"]
        loser_dc = duel_info["opponent_dc"]
        loser_cf = duel_info["opponent_cf"]
        winner_solves = c_solves
        loser_solves = o_solves
    else:
        winner_dc = duel_info["opponent_dc"]
        winner_cf = duel_info["opponent_cf"]
        loser_dc = duel_info["challenger_dc"]
        loser_cf = duel_info["challenger_cf"]
        winner_solves = o_solves
        loser_solves = c_solves

    return {
        "status": "completed",
        "winner": winner_dc,
        "winner_cf": winner_cf,
        "loser": loser_dc,
        "loser_cf": loser_cf,
        "winner_solves": winner_solves,
        "loser_solves": loser_solves,
        "winner_count": len(winner_solves),
        "loser_count": len(loser_solves),
        "problems": duel_info["problems"],
        "reason": reason
    }


def _build_tie_result(duel_info: dict, c_solves: dict, o_solves: dict, reason: str) -> dict:
    """建立平手 result"""
    return {
        "status": "completed",
        "winner": None,
        "c_solves": c_solves,
        "o_solves": o_solves,
        "c_count": len(c_solves),
        "o_count": len(o_solves),
        "problems": duel_info["problems"],
        "reason": reason
    }


def update_leaderboard(winner_dc: str, winner_cf: str,
                       loser_dc: str, loser_cf: str,
                       is_tie: bool, duel_info: dict):
    """更新 leaderboard.json"""
    lb_file = "leaderboard.json"
    if not os.path.exists(lb_file):
        with open(lb_file, "w") as f:
            json.dump({}, f)

    with open(lb_file, "r") as f:
        lb = json.load(f)

    def record(dc, cf):
        if dc not in lb:
            lb[dc] = {"cf_handle": cf, "wins": 0, "losses": 0, "ties": 0, "points": 0}
        lb[dc]["cf_handle"] = cf  # 保持更新 handle
        # 確保舊資料有所有必要欄位
        for key in ["wins", "losses", "ties", "points"]:
            if key not in lb[dc]:
                lb[dc][key] = 0

    record(winner_dc, winner_cf)
    record(loser_dc, loser_cf)

    if is_tie:
        lb[winner_dc]["ties"] += 1
        lb[loser_dc]["ties"] += 1
        lb[winner_dc]["points"] += 1
        lb[loser_dc]["points"] += 1
    else:
        lb[winner_dc]["wins"] += 1
        lb[loser_dc]["losses"] += 1
        lb[winner_dc]["points"] += 3  # 勝利 3 分
        lb[loser_dc]["points"] += 0

    with open(lb_file, "w") as f:
        json.dump(lb, f, indent=4, ensure_ascii=False)


def get_leaderboard() -> list:
    """取得排序過的 leaderboard"""
    lb_file = "leaderboard.json"
    if not os.path.exists(lb_file):
        return []
    with open(lb_file, "r") as f:
        lb = json.load(f)

    # 計算勝率並排序（按積分）
    items = []
    for dc_name, data in lb.items():
        total = data.get("wins", 0) + data.get("losses", 0) + data.get("ties", 0)
        win_rate = data.get("wins", 0) / total if total > 0 else 0
        items.append({
            "dc_name": dc_name,
            "cf_handle": data.get("cf_handle", ""),
            "wins": data.get("wins", 0),
            "losses": data.get("losses", 0),
            "ties": data.get("ties", 0),
            "points": data.get("points", 0),
            "total": total,
            "win_rate": win_rate
        })

    # 按積分排序
    items.sort(key=lambda x: (x["points"], x["win_rate"]), reverse=True)
    return items


def get_user_stats(dc_name: str) -> dict | None:
    """取得特定用戶的 duel 統計"""
    lb_file = "leaderboard.json"
    if not os.path.exists(lb_file):
        return None
    with open(lb_file, "r") as f:
        lb = json.load(f)
    stats = lb.get(dc_name)
    if stats:
        stats["wins"] = stats.get("wins", 0)
        stats["losses"] = stats.get("losses", 0)
        stats["ties"] = stats.get("ties", 0)
        stats["points"] = stats.get("points", 0)
        stats["cf_handle"] = stats.get("cf_handle", "")
    return stats