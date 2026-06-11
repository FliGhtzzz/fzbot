import json
import random
import requests
import discord
import time

VERIFICATION_TIME_LIMIT = 120  # 2 分鐘（秒）


def _load_link_data():
    """載入連結資料"""
    try:
        with open("link.json", "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        with open("link.json", "w") as f:
            json.dump({}, f, indent=4)
        return {}


def _save_link_data(data):
    """儲存連結資料"""
    with open("link.json", "w") as f:
        json.dump(data, f, indent=4)


def _get_unsolved_problem(cfhandle: str):
    """取得一個用戶尚未 submit 的題目"""
    try:
        # 取得用戶的所有 submission
        status_url = "https://codeforces.com/api/user.status"
        params = {"handle": cfhandle, "from": 1, "count": 1000}
        response = requests.get(status_url, params=params, timeout=10)
        data = response.json()

        if data["status"] != "OK":
            return None

        submitted_problems = set()
        for sub in data.get("result", []):
            contest_id = sub.get("problem", {}).get("contestId", 0)
            index = sub.get("problem", {}).get("index", "")
            if contest_id and index:
                submitted_problems.add(f"{contest_id}-{index}")

        # 取得題目列表
        problems_url = "https://codeforces.com/api/problemset.problems"
        response = requests.get(problems_url, timeout=10)
        problems_data = response.json()

        if problems_data["status"] != "OK":
            return None

        unsolved = []
        for problem in problems_data.get("result", {}).get("problems", []):
            contest_id = problem.get("contestId", 0)
            index = problem.get("index", "")
            rating = problem.get("rating", 0)
            tags = problem.get("tags", [])
            pid = f"{contest_id}-{index}"

            if (pid not in submitted_problems
                and index in ["A", "B", "C", "A2", "B2"]
                and 800 <= rating <= 1200
                and "math" not in tags
                and contest_id):
                unsolved.append((contest_id, index))

        if not unsolved:
            for problem in problems_data.get("result", {}).get("problems", []):
                pid = f"{problem.get('contestId', 0)}-{problem.get('index', '')}"
                if pid not in submitted_problems and problem.get("contestId"):
                    unsolved.append((problem.get("contestId"), problem.get("index")))
            if not unsolved:
                return None

        return random.choice(unsolved)

    except Exception as e:
        print(f"[linkcf] Error: {e}")
        return None


def get_user_info(handle):
    url = "https://codeforces.com/api/user.info"
    params = {"handles": handle}

    try:
        response = requests.get(url, params=params, timeout=10)
        data = response.json()

        if data["status"] == "OK":
            user = data["result"][0]
            embed = discord.Embed(
                title="**" + user.get("handle") + "**",
                url="https://codeforces.com/profile/" + user.get("handle"),
                color=0x48c750
            )
            embed.set_thumbnail(url=user.get("avatar"))
            embed.set_footer(
                text="Rating: " + str(user.get("rating")) +
                     " | Max Rating: " + str(user.get("maxRating")) +
                     " | Rank: " + str(user.get("rank")) +
                     " | Max Rank: " + str(user.get("maxRank"))
            )
            return embed
        else:
            return discord.Embed(title="Error", description=data["comment"], color=0x903c3c)

    except Exception as e:
        return discord.Embed(title="Error", description=str(e), color=0x903c3c)


def linked(user_id: str):
    """檢查 user_id 是否已連結（用 user_id）"""
    link_data = _load_link_data()
    if user_id in link_data and link_data[user_id].get("linked"):
        return link_data[user_id]["codeforces.handle"]
    return False


def linked_cf(cfhandle: str):
    """檢查這個 CF 帳號是否已被任何人連結"""
    link_data = _load_link_data()
    for uid, entry in link_data.items():
        if entry.get("linked") and entry.get("codeforces.handle") == cfhandle:
            return uid  # 返回已連結的 user_id
    return None


def askforcf(user_id: str, user_name: str, cfhandle: str):
    """
    建立驗證請求
    user_id: Discord user id（唯一識別）
    user_name: Discord user name（顯示用）
    """
    link_data = _load_link_data()

    # 1. 檢查 Codeforces 帳號是否存在
    url = "https://codeforces.com/api/user.info"
    params = {"handles": cfhandle}
    try:
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        if data["status"] != "OK":
            return f"Error: {data.get('comment', 'Unknown error')}"
    except Exception as e:
        return f"Error: {e}"

    # 2. 清理過期驗證（只清理 linked=False 的）- 改由背景任務統一處理
    # （背景任務負責通知用戶後再清理，避免通知時記錄已被刪除）

    # 3. 檢查這個 CF 帳號是否已被連結（任何人的 Discord）
    existing_linked = linked_cf(cfhandle)
    if existing_linked:
        return "error: This Codeforces account is already linked to another Discord account."

    # 4. 檢查這個人自己是否已經連結過（linked=True）
    if user_id in link_data and link_data[user_id].get("linked"):
        cf = link_data[user_id].get("codeforces.handle", "")
        return f"error: Your Discord is already linked to `{cf}`. Use `/unlink` first."

    # 5. 如果有待驗證的記錄，檢查是否過期
    current_time = time.time()
    if user_id in link_data:
        entry = link_data[user_id]
        if not entry.get("linked"):
            expires_at = entry.get("expires_at", 0)
            if expires_at > 0 and expires_at < current_time:
                # 過期了，刪除後建立新的
                del link_data[user_id]
            else:
                # 還沒過期
                time_left = int(expires_at - current_time)
                cf = entry.get("codeforces.handle", "")
                return f"error: Verification in progress for `{cf}`. Time remaining: {time_left}s. Use `/vercf`."

    # 6. 取得未解決的題目
    problem = _get_unsolved_problem(cfhandle)
    if not problem:
        return "error: Could not find a suitable problem. You may have solved too many problems!"

    contest_id, problem_index = problem

    # 7. 建立驗證請求
    expires_at = time.time() + VERIFICATION_TIME_LIMIT
    link_data[user_id] = {
        "user_name": user_name,
        "linked": False,
        "cfproblem_id": contest_id,
        "cfproblem_index": problem_index,
        "codeforces.handle": cfhandle,
        "expires_at": expires_at,
        "created_at": time.time()
    }
    _save_link_data(link_data)

    return (
        f"✅ Verification created!\n\n"
        f"📝 Submit any code to:\n"
        f"<https://codeforces.com/problemset/problem/{contest_id}/{problem_index}>\n\n"
        f"⏱️ **Expires in 2 minutes!**\n\n"
        f"After submitting, use `/vercf` to verify."
    )


def vertifycf(user_id: str, user_name: str):
    """驗證連結"""
    link_data = _load_link_data()

    # 檢查這個人是否存在記錄
    if user_id not in link_data:
        return "No pending verification. Use `/cnttocf` first."

    entry = link_data[user_id]

    # 檢查是否已經連結
    if entry.get("linked"):
        return "Your Discord is already linked to a Codeforces account."

    # 檢查是否過期
    expires_at = entry.get("expires_at", 0)
    if expires_at > 0 and time.time() > expires_at:
        del link_data[user_id]
        _save_link_data(link_data)
        return "Verification expired! Please use `/cnttocf` again."

    cf_handle = entry["codeforces.handle"]
    contest_id = entry["cfproblem_id"]
    problem_index = entry["cfproblem_index"]

    # 檢查 Codeforces 提交
    url = f"https://codeforces.com/api/user.status?handle={cf_handle}&from=1&count=100"
    try:
        response = requests.get(url, timeout=10)
        data = response.json()

        for sub in data.get("result", []):
            pid = sub.get("problem", {}).get("contestId", 0)
            idx = sub.get("problem", {}).get("index", "")
            if pid == contest_id and idx == problem_index:
                link_data[user_id]["linked"] = True
                link_data[user_id]["verified_at"] = time.time()
                _save_link_data(link_data)
                return "✅ Your account has been successfully linked!"

        time_left = int(expires_at - time.time())
        return f"Verification failed. Make sure you've submitted to the problem.\nTime remaining: {time_left}s"

    except Exception as e:
        return f"error: Failed to check submissions. ({e})"


def unlink(user_id: str):
    """解除連結"""
    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    return loop.run_sync(lambda: _unlink_sync(user_id))


def _unlink_sync(user_id: str):
    link_data = _load_link_data()
    if user_id in link_data and link_data[user_id].get("linked"):
        del link_data[user_id]
        _save_link_data(link_data)
        return "Your account has been successfully unlinked!"
    return "No linked Codeforces account found."


def get_pending_and_expired():
    """取得所有過期但還沒處理的驗證（用於通知）"""
    link_data = _load_link_data()
    expired = []

    for key, entry in link_data.items():
        if not entry.get("linked"):
            expires_at = entry.get("expires_at", 0)
            if expires_at > 0 and time.time() > expires_at:
                expired.append((key, entry))

    return expired


def cleanup_expired():
    """清理所有過期的驗證請求"""
    link_data = _load_link_data()
    current_time = time.time()
    removed = []

    for key in list(link_data.keys()):
        entry = link_data[key]
        if not entry.get("linked"):
            expires_at = entry.get("expires_at", 0)
            if expires_at > 0 and current_time > expires_at:
                removed.append(entry)
                del link_data[key]

    if removed:
        _save_link_data(link_data)

    return removed


def remove_user(user_id: str):
    """刪除特定用戶的驗證記錄"""
    link_data = _load_link_data()
    if user_id in link_data:
        del link_data[user_id]
        _save_link_data(link_data)