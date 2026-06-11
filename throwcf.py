import requests
import discord
import random
import json

# 熱門標籤列表
POPULAR_TAGS = [
    "dp", "math", "graphs", "greedy", "data-structures",
    "sortings", "binary-search", "number-theory", "constructive-algorithms",
    "strings", "geometry", "brute-force", "two-pointers", "divide-and-conquer",
    "bitmasks", "combinatorics", "trees", "hashing", "implementation", "probability"
]

# Rating 等級選項
RATING_TIERS = [
    ("800-1200 初學者", 800, 1200),
    ("1200-1400 Pupil", 1200, 1400),
    ("1400-1600 Specialist", 1400, 1600),
    ("1600-1900 Expert", 1600, 1900),
    ("1900-2200 Master", 1900, 2200),
    ("2200+", 2200, 3500),
]


def askprob(
    mnrating: int,
    mxrating: int,
    num: int,
    solved: bool,
    linktxt: str = "",
    cf_handle: str = None,
    tags: list = None,
    indices: list = None
) -> tuple[list, str]:
    """
    找 Codeforces 題目

    Args:
        mnrating: 最小 rating
        mxrating: 最大 rating
        num: 要找幾題
        solved: 是否包含已解題目 (True=只找未解, False=不考慮)
        linktxt: 額外提示文字
        cf_handle: Codeforces 使用者名稱（用於过滤已解題目）
        tags: 標籤列表（只找有這些標籤的題目）
        indices: 題目等級列表，如 ["A", "B", "C"]

    Returns:
        (題目列表, 回傳訊息/embed)
        - 如果找到題目，回傳 (列表, "")
        - 如果失敗，回傳 ([], "錯誤訊息")
    """
    if num > 50:
        embed = discord.Embed(
            title="Error",
            description="The maximum number of problems that can be requested is 50."
        )
        return [], embed

    if mxrating < mnrating:
        embed = discord.Embed(
            title="Error",
            description="Maximum rating must be greater than or equal to minimum rating."
        )
        return [], embed

    url = "https://codeforces.com/api/problemset.problems"

    try:
        response = requests.get(url)
        data = response.json()

        # 預先載入已解題目集合（效能優化）
        solved_problems = set()
        if cf_handle:
            try:
                urlpro = f"https://codeforces.com/api/user.status?handle={cf_handle}&from=1&count=100"
                responsepro = requests.get(urlpro)
                datapro = responsepro.json()
                for sub in datapro.get("result", []):
                    if sub.get("verdict") == "OK":
                        prob = sub.get("problem", {})
                        solved_problems.add(
                            (prob.get("contestId"), prob.get("index"))
                        )
            except Exception:
                # 無法取得已解題目，不過濾
                pass

        temp = []
        for prob in data.get("result", {}).get("problems", []):
            rating = prob.get("rating")

            # Rating 範圍過濾
            if rating is None or not (mnrating <= rating <= mxrating):
                continue

            # 標籤過濾
            if tags:
                prob_tags = prob.get("tags", [])
                if not any(t in prob_tags for t in tags):
                    continue

            # 等級過濾 (A, B, C, ...)
            if indices:
                if prob["index"] not in indices:
                    continue

            # 已解題目過濾
            if not solved:
                problem_key = (prob["contestId"], prob["index"])
                if problem_key in solved_problems:
                    continue

            temp.append({
                "contestId": prob["contestId"],
                "index": prob["index"],
                "name": prob.get("name", ""),
                "rating": rating,
                "tags": prob.get("tags", []),
            })

        if len(temp) < num:
            txt = ""
            for i in temp[:10]:  # 最多顯示 10 個
                txt += f"https://codeforces.com/problemset/problem/{i['contestId']}/{i['index']}\n"
            if len(temp) == 0:
                embed = discord.Embed(
                    title="No Problems Found",
                    description=f"找不到符合條件的題目。請嘗試放寬篩選條件。",
                    color=0x903c3c
                )
            else:
                embed = discord.Embed(
                    title="Not Enough Problems",
                    description=f"在指定範圍內只找到 {len(temp)} 題：\n{txt}\n...还有更多",
                    color=0x903c3c
                )
            return [], embed

        rand = random.sample(temp, num)
        txt = ""
        for i in rand:
            txt += f"https://codeforces.com/problemset/problem/{i['contestId']}/{i['index']}\n"

        embed = discord.Embed(
            title="Here are your problems",
            description=txt + "\n" + linktxt,
            color=0x48c750
        )
        return rand, embed

    except Exception as e:
        embed = discord.Embed(title="Error", description=str(e), color=0x903c3c)
        return [], embed