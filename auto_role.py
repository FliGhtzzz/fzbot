"""
Auto Role 系統：根據 CF Rating 自動分發身份組
"""
import os
import json
import requests
import discord

CONFIG_FILE = "autorole_config.json"

# 預設 Rating 等級對應
DEFAULT_RATING_TIERS = [
    ("Newbie", 0, 1199),
    ("Pupil", 1200, 1399),
    ("Specialist", 1400, 1599),
    ("Expert", 1600, 1899),
    ("Candidate Master", 1900, 2099),
    ("Master", 2100, 2299),
    ("International Master", 2300, 2399),
    ("Grandmaster", 2400, 2599),
    ("International Grandmaster", 2600, 2999),
    ("Legendary Grandmaster", 3000, 99999),
]

# 等級顏色
RATING_COLORS = {
    "Newbie": 0x808080,           # 灰
    "Pupil": 0x00CC00,            # 綠
    "Specialist": 0x03A89E,       # 青
    "Expert": 0x0000FF,           # 藍
    "Candidate Master": 0xAA00AA, # 紫
    "Master": 0xFF8C00,            # 橙
    "International Master": 0xFF8C00,
    "Grandmaster": 0xCC0000,      # 紅
    "International Grandmaster": 0xCC0000,
    "Legendary Grandmaster": 0xFFD700,  # 金
}


def _load_config() -> dict:
    if not os.path.exists(CONFIG_FILE):
        return {}
    with open(CONFIG_FILE, "r") as f:
        return json.load(f)


def _save_config(config: dict):
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=4, ensure_ascii=False)


def get_rating_tier(rating: int) -> tuple[str, int]:
    """根據 rating 取得等級名稱和顏色"""
    for name, lo, hi in DEFAULT_RATING_TIERS:
        if lo <= rating <= hi:
            return name, RATING_COLORS.get(name, 0x808080)
    return "Newbie", 0x808080


def get_cf_rating(handle: str) -> int | None:
    """從 CF API 取得用戶當前 rating"""
    try:
        resp = requests.get(f"https://codeforces.com/api/user.info?handles={handle}")
        data = resp.json()
        if data["status"] != "OK":
            return None
        info = data["result"][0]
        return info.get("rating") or info.get("maxRating")
    except:
        return None


def get_cf_rank(handle: str) -> str | None:
    """從 CF API 取得用戶 rank"""
    try:
        resp = requests.get(f"https://codeforces.com/api/user.info?handles={handle}")
        data = resp.json()
        if data["status"] != "OK":
            return None
        info = data["result"][0]
        return info.get("rank") or info.get("maxRank")
    except:
        return None


def get_role_by_rating(guild: discord.Guild, rating: int) -> discord.Role | None:
    """根據 rating 在伺服器中找到對應的身份組"""
    tier_name, _ = get_rating_tier(rating)

    # 優先找完全匹配的名稱
    role = discord.utils.get(guild.roles, name=tier_name)
    if role:
        return role

    # 嘗試模糊匹配（忽略大小寫、空格）
    rating_normalized = tier_name.lower().replace(" ", "")
    for r in guild.roles:
        if r.name.lower().replace(" ", "") == rating_normalized:
            return r

    return None


def get_cf_stats(handle: str) -> dict | None:
    """取得 CF 用戶詳細統計"""
    try:
        # user info
        resp = requests.get(f"https://codeforces.com/api/user.info?handles={handle}")
        data = resp.json()
        if data["status"] != "OK":
            return None
        info = data["result"][0]

        # 已解題目統計
        resp2 = requests.get(f"https://codeforces.com/api/user.status?handle={handle}&from=1&count=500")
        solved_set = set()
        tag_count = {}
        data2 = resp2.json()
        if data2["status"] == "OK":
            for sub in data2["result"]:
                if sub.get("verdict") == "OK":
                    prob = sub.get("problem", {})
                    solved_set.add((prob.get("contestId"), prob.get("index")))
                    for tag in prob.get("tags", []):
                        tag_count[tag] = tag_count.get(tag, 0) + 1

        # 最強標籤
        top_tags = sorted(tag_count.items(), key=lambda x: x[1], reverse=True)[:5]

        return {
            "handle": handle,
            "rating": info.get("rating"),
            "max_rating": info.get("maxRating"),
            "rank": info.get("rank"),
            "max_rank": info.get("maxRank"),
            "solved_count": len(solved_set),
            "top_tags": top_tags,
            "avatar": info.get("avatar"),
            "title_photo": info.get("titlePhoto"),
        }
    except:
        return None


def build_rating_embed(handle: str, user: discord.User = None) -> discord.Embed:
    """建立 CF 個人資訊 Embed"""
    stats = get_cf_stats(handle)
    if not stats:
        return discord.Embed(
            title="❌ 找不到用戶",
            description=f"找不到 Codeforces 用戶 `{handle}`",
            color=0x903c3c
        )

    rating = stats.get("rating") or "無"
    max_rating = stats.get("max_rating") or "無"
    rank = stats.get("rank") or "無"
    max_rank = stats.get("max_rank") or "無"

    tier_name, tier_color = get_rating_tier(rating if isinstance(rating, int) else 0)

    embed = discord.Embed(
        title=f"{handle}",
        color=tier_color
    )
    embed.set_author(
        name=f"CF Stats | {tier_name}",
        url=f"https://codeforces.com/profile/{handle}"
    )
    if user:
        embed.set_footer(text=f"Requested by {user.display_name}", icon_url=user.avatar.url if user.avatar else None)

    embed.add_field(name="📊 現有 Rating", value=f"**{rating}** ({rank})", inline=True)
    embed.add_field(name="🏆 最高 Rating", value=f"**{max_rating}** ({max_rank})", inline=True)
    embed.add_field(name="✅ 已解題數", value=str(stats.get("solved_count", 0)), inline=True)

    if stats.get("top_tags"):
        tags_str = "\n".join([f"`{tag}` ×{cnt}" for tag, cnt in stats["top_tags"]])
        embed.add_field(name="🧠 擅長領域", value=tags_str, inline=False)

    embed.add_field(
        name="🔗 連結",
        value=f"[Profile](https://codeforces.com/profile/{handle}) | [ submissions](https://codeforces.com/problemset/status?destek={handle})",
        inline=False
    )

    return embed