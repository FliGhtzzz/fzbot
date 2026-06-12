# 導入Discord.py模組
import discord
import os
from dotenv import load_dotenv
import linkcf
import json
import cfrating
import duel
import auto_role
import views  # 互動式 UI 元件
import asyncio
import time
# 導入commands指令模組
from discord.ext import commands

# 載入 .env 環境變數
load_dotenv()
dctoken = os.getenv("DC_TOKEN")

# intents是要求機器人的權限
intents = discord.Intents.all()
# command_prefix是前綴符號，可以自由選擇($, #, &...)
bot = commands.Bot(command_prefix="%", intents=intents)

# 機器人完全就緒鎖（防止 startup 期間收到指令導致 404）
_startup_complete = False


# ============================================================
# 事件：機器人啟動
# ============================================================
@bot.event
async def on_ready():
    # 第一步：立刻同步 slash commands（完全就緒後才接受任何指令）
    synced = await bot.tree.sync()
    global _startup_complete
    _startup_complete = True  # 解鎖指令處理
    print(f"目前登入身份 --> {bot.user}")
    print(f"載入 {len(synced)} 個斜線指令")

    # 初始化 link.json 初始化的同時不阻斷 sync
    FILENAME = "link.json"
    # 初始化 link.json
    FILENAME = "link.json"
    if not os.path.exists(FILENAME) or os.path.getsize(FILENAME) == 0:
        with open(FILENAME, "w") as f:
            json.dump({}, f, indent=4)
    # 初始化 role_reactions.json
    RRFILE = "role_reactions.json"
    if not os.path.exists(RRFILE):
        with open(RRFILE, "w") as f:
            json.dump({"menus": {}}, f, ensure_ascii=False, indent=2)
    # 初始化 role_selects.json
    RSFILE = "role_selects.json"
    if not os.path.exists(RSFILE):
        with open(RSFILE, "w") as f:
            json.dump({"menus": {}}, f, ensure_ascii=False, indent=2)
    # 啟動 duel 結算 background task
    bot.loop.create_task(duel_check_loop())
    # 啟動驗證超時檢查 task
    bot.loop.create_task(check_expired_verifications())
    # 啟動 pending duel 過期檢查 task
    bot.loop.create_task(check_expired_pending_duels())


async def check_expired_verifications():
    """每分鐘檢查過期的驗證請求並通知用戶"""
    import linkcf
    await bot.wait_until_ready()
    print("[bot] 驗證過期檢查已啟動")
    while True:
        try:
            # 取得過期的驗證
            expired = linkcf.get_pending_and_expired()
            if expired:
                print(f"[verify] 發現 {len(expired)} 個過期驗證")

            for user_id, verify_data in expired:
                user_id_int = int(user_id)

                # 嘗試找到用戶
                user = None
                for guild in bot.guilds:
                    member = guild.get_member(user_id_int)
                    if member:
                        user = member
                        break

                if not user:
                    print(f"[verify] 找不到用戶 {user_id}")
                    continue

                cf_handle = verify_data.get("codeforces.handle", "Unknown")
                print(f"[verify] 準備通知 {user.name} ({user_id}) 驗證已過期")

                try:
                    embed = discord.Embed(
                        title="⏰ 驗證連結已過期",
                        description=(
                            f"你的 Codeforces 連結驗證已過期 (`{cf_handle}`)\n\n"
                            f"請使用 `/cnttocf` 重新發起驗證"
                        ),
                        color=0x903c3c
                    )
                    await user.send(embed=embed)
                    print(f"[verify] ✅ 已發送 DM 通知 {user.name}")
                except discord.Forbidden:
                    print(f"[verify] ❌ 無法發送 DM 给 {user.name}（可能關閉了私訊）")
                except Exception as e:
                    print(f"[verify] ❌ 發送 DM 時發生錯誤: {e}")

            # 清理過期記錄
            if expired:
                removed = linkcf.cleanup_expired()
                print(f"[verify] 已清理 {len(removed)} 筆過期驗證")

        except Exception as e:
            print(f"[verify check error] {e}")

        await asyncio.sleep(60)  # 每分鐘檢查一次


# ============================================================
# 任務：檢查過期的 pending duel 並取消
# ============================================================
async def check_expired_pending_duels():
    """每 30 秒檢查即將過期的 pending duels，2 分鐘後自動取消"""
    await bot.wait_until_ready()
    while True:
        try:
            data = duel._load_duel()
            pending = data.get("pending", {})
            current_time = time.time()
            expired_keys = []

            for key, pending_info in list(pending.items()):
                expires_at = pending_info.get("expires_at", 0)
                if expires_at > 0 and current_time > expires_at:
                    expired_keys.append(key)

            for key in expired_keys:
                pending_info = pending[key]
                # 嘗試找到 challenger 並發 DM 通知
                challenger_id = pending_info.get("challenger_id")
                if challenger_id:
                    for guild in bot.guilds:
                        member = guild.get_member(int(challenger_id))
                        if member:
                            try:
                                opponent_mention = pending_info.get("opponent_mention", "Unknown")
                                num_problems = pending_info.get("num_problems", 3)
                                duration = pending_info.get("duration_minutes", 10)
                                embed = discord.Embed(
                                    title="⏰ Duel 挑戰已取消",
                                    description=(
                                        f"你的 Duel 挑戰未被回應，已自動取消。\n\n"
                                        f"對手：{opponent_mention}\n"
                                        f"題目數：{num_problems} 題\n"
                                        f"時間限制：{duration} 分鐘"
                                    ),
                                    color=0x903c3c
                                )
                                await member.send(embed=embed)
                                print(f"[duel pending] 已通知 {member.name} 挑戰已取消")
                            except discord.Forbidden:
                                print(f"[duel pending] 無法發送 DM 给 {member.name}")
                            except Exception as e:
                                print(f"[duel pending] 發送 DM 失敗: {e}")

                # 刪除過期的 pending duel
                del pending[key]
                print(f"[duel pending] 已移除過期挑戰: {key}")

            if expired_keys:
                duel._save_duel(data)

        except Exception as e:
            print(f"[duel pending check error] {e}")

        await asyncio.sleep(30)  # 每 30 秒檢查一次


# ============================================================
# 任務：定期檢查進行的 duel 並結算
# ============================================================
async def duel_check_loop():
    """每 30 秒檢查一次 active duels 並結算"""
    await bot.wait_until_ready()
    while True:
        try:
            await check_and_finalize_duels()
        except Exception as e:
            print(f"[duel check error] {e}")
        await asyncio.sleep(30)


async def check_and_finalize_duels():
    """檢查所有 active duel 並結算，更新記分板"""
    data = duel._load_duel()
    changed = False
    to_complete = []
    to_update = []  # 需要更新記分板的 duel

    current_time = time.time()

    for key, duel_info in list(data.get("active", {}).items()):
        end_time = duel_info.get("end_time", duel_info["start_time"] + 300)
        remaining = int(end_time - current_time)

        # 判斷是否的最後一輪檢測（時間到前的最後 30 秒內）
        is_final_check = remaining <= 30 and remaining > 0

        # 如果是最後一輪檢測，強制完整結算
        if is_final_check:
            result = duel.check_duel_result(duel_info, force_check=True)
            if result["status"] == "completed":
                to_complete.append((key, result, duel_info))
            continue

        # 正常檢查是否完成（有人解完所有題目）
        result = duel.check_duel_result(duel_info)
        remaining = int(end_time - current_time)  # 重新計算剩餘時間

        # 如果已完成（有人解完），結算
        if result["status"] == "completed":
            to_complete.append((key, result, duel_info))
        elif remaining <= 0:
            # 時間到，強制結算（這是最後的 safety net）
            result = duel.check_duel_result(duel_info, force_check=True)
            if result["status"] == "completed":
                to_complete.append((key, result, duel_info))
        else:
            # 還在進行中，標記需要更新記分板
            if "update_message_id" in duel_info and "update_channel_id" in duel_info:
                to_update.append((key, duel_info, result, remaining))

    # 更新記分板
    for key, duel_info, result, remaining in to_update:
        try:
            guild = bot.guilds[0]
            channel_id = duel_info.get("update_channel_id")
            message_id = duel_info.get("update_message_id")

            channel = guild.get_channel(channel_id)
            if not channel:
                continue

            message = await channel.fetch_message(message_id)
            if not message:
                continue

            c_solves = result.get("challenger_solves_raw", {})
            o_solves = result.get("opponent_solves_raw", {})

            embed = views.build_duel_score_embed(duel_info, c_solves, o_solves, remaining)
            await message.edit(embed=embed, view=None)  # 移除按鈕
            print(f"[duel] 更新記分板 {key}")
        except Exception as e:
            print(f"[duel] 更新記分板失敗 {key}: {e}")

    # 結算已完成的 duel
    for key, result, duel_info in to_complete:
        # 更新 leaderboard
        is_tie = result.get("winner") is None

        if not is_tie:
            winner_dc = result.get("winner", "tie")
            winner_cf = result.get("winner_cf", "")
            loser_dc = result.get("loser", "tie")
            loser_cf = result.get("loser_cf", "")
            duel.update_leaderboard(
                winner_dc, winner_cf,
                loser_dc, loser_cf,
                False, duel_info
            )
        else:
            c_cf = duel_info.get("challenger_cf")
            o_cf = duel_info.get("opponent_cf")
            duel.update_leaderboard(
                duel_info["challenger_dc"], c_cf,
                duel_info["opponent_dc"], o_cf,
                True, duel_info
            )

        data["active"].pop(key, None)
        data["history"].append({
            "key": key,
            "result": result,
            "finalized_at": time.time()
        })
        changed = True

        # 更新訊息為結果（公佈題目）
        try:
            guild = bot.guilds[0]
            channel_id = duel_info.get("update_channel_id")
            message_id = duel_info.get("update_message_id")

            if channel_id and message_id:
                channel = guild.get_channel(channel_id)
                if channel:
                    message = await channel.fetch_message(message_id)
                    if message:
                        embed = views.build_duel_result_embed(duel_info, result)
                        await message.edit(embed=embed, view=None)
                        print(f"[duel] 已結算並更新訊息 {key}")
        except Exception as e:
            print(f"[duel] 更新結果訊息失敗 {key}: {e}")

        # 發 DM 通知雙方
        try:
            for member in guild.members:
                if member.name == duel_info["challenger_dc"]:
                    await send_duel_result_dm(member, result, duel_info)
                if member.name == duel_info["opponent_dc"]:
                    await send_duel_result_dm(member, result, duel_info)
        except Exception as e:
            print(f"[duel dm error] {e}")

    if changed:
        duel._save_duel(data)


async def send_duel_result_dm(user: discord.User, result: dict, duel_info: dict):
    """發 DM 通知 duel 結果"""
    try:
        is_tie = result["winner"] is None
        problems = result.get("problems", [])
        num_problems = len(problems)

        if is_tie:
            c_count = result.get("c_count", 0)
            o_count = result.get("o_count", 0)
            msg = (
                f"🤝 **Duel 平手！**\n\n"
                f"📊 雙方都解了 {c_count} / {num_problems} 題"
            )
        else:
            winner_name = result.get("winner", "Unknown")
            loser_name = result.get("loser", "Unknown")
            winner_count = result.get("winner_count", 0)
            loser_count = result.get("loser_count", 0)
            reason = result.get("reason", "")

            emoji = "🥇" if user.name == winner_name else "🥈"
            msg = (
                f"{emoji} **Duel 結束！**\n\n"
                f"{'🥇 勝利者' if user.name == winner_name else '🥈 落敗者'}：**{winner_name}**"
                f" (解 {winner_count} 題)\n"
                f"{'🥈 落敗者' if user.name != winner_name else '🥇 勝利者'}：**{loser_name}**"
                f" (解 {loser_count} 題)\n\n"
                f"📝 {num_problems} 題中完成全部或比較數量"
            )

            if "faster" in reason:
                msg += f"\n⏱️ {reason}"
            elif "time" in reason:
                msg += f"\n⏱️ 時間到結算"

        await user.send(msg)
    except Exception as e:
        print(f"[send_duel_result_dm error for {user.name}] {e}")


# ============================================================
# 指令：基本功能
# ============================================================
@bot.tree.command(name="searchcf", description="搜尋 Codeforces 用戶資訊")
async def searchcf(interaction: discord.Interaction, cfhandle: str):
    embed = auto_role.build_rating_embed(cfhandle, interaction.user)
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="help", description="列出所有指令")
async def help_cmd(interaction: discord.Interaction):
    des = {
        "help": "指令列表",
        "searchcf <cfhandle>": "搜尋 Codeforces 帳號資訊",
        "cnttocf <cfhandle>": "將 Discord 帳號與 Codeforces 帳號連結（需驗證）",
        "vercf": "驗證連結 Codeforces 帳號",
        "unlink": "解除 Codeforces 連結",
        "ratingcf <cfhandle>": "顯示 Rating 變化圖",
        "cfprob": "互動式找 Codeforces 題目 🎯",
        "duel_challenge": "向別人發起 duel 挑戰 ⚔️",
        "leaderboard": "查看 duel 排名 🏅",
        "duel_stats": "查看 duel 統計",
        "rolecolor <#hex>": "設定名字顏色 🎨",
        "roleselect": "選擇你的身份組 📋",
        "roleselect_admin": "建立/管理身份組選單（管理員）🔧",
        "ai <question>": "問 AI 問題 🤖",
        "summarize": "用 AI 總結頻道訊息（選單選擇時間）📝",
    }
    embed = discord.Embed(
        title="**指令列表**",
        description="\n".join([f"`{k}`：{v}" for k, v in des.items()]),
        color=0x3489da
    )
    await interaction.response.send_message(embed=embed)


# ============================================================
# 事件：偵測表情反應並給予/移除身份組
# ============================================================
@bot.event
async def on_raw_reaction_add(payload: discord.RawReactionActionEvent):
    """當使用者新增反應時"""
    # 檢查是否是機器人的訊息
    msg_id = str(payload.message_id)
    data = views.load_role_reactions()

    if msg_id not in data["menus"]:
        return

    menu = data["menus"][msg_id]
    guild_id = menu.get("guild_id")
    roles_map = menu.get("roles", {})

    # 把 emoji 轉換成字串
    emoji_str = str(payload.emoji)

    if emoji_str not in roles_map:
        return

    role_id = roles_map[emoji_str]

    # 取得伺服器和成員
    guild = bot.get_guild(guild_id)
    if not guild:
        return

    member = guild.get_member(payload.user_id)
    if not member or member.bot:
        return

    role = guild.get_role(role_id)
    if not role:
        return

    # 給予身份組
    if role not in member.roles:
        try:
            await member.add_roles(role)
            print(f"[role reaction] {member} 獲得了 {role.name}")
        except discord.Forbidden:
            print(f"[role reaction] 沒有權限給予 {role.name}")
        except Exception as e:
            print(f"[role reaction] 錯誤：{e}")


@bot.event
async def on_raw_reaction_remove(payload: discord.RawReactionActionEvent):
    """當使用者移除反應時"""
    msg_id = str(payload.message_id)
    data = views.load_role_reactions()

    if msg_id not in data["menus"]:
        return

    menu = data["menus"][msg_id]
    guild_id = menu.get("guild_id")
    roles_map = menu.get("roles", {})

    emoji_str = str(payload.emoji)
    if emoji_str not in roles_map:
        return

    role_id = roles_map[emoji_str]

    guild = bot.get_guild(guild_id)
    if not guild:
        return

    member = guild.get_member(payload.user_id)
    if not member or member.bot:
        return

    role = guild.get_role(role_id)
    if not role:
        return

    # 移除身份組
    if role in member.roles:
        try:
            await member.remove_roles(role)
            print(f"[role reaction] {member} 移除了 {role.name}")
        except discord.Forbidden:
            print(f"[role reaction] 沒有權限移除 {role.name}")
        except Exception as e:
            print(f"[role reaction] 錯誤：{e}")


# ============================================================
# 指令：帳號連結
# ============================================================
@bot.tree.command(name="cnttocf", description="將 Discord 與 Codeforces 連結")
async def cnttocf(interaction: discord.Interaction, cfhandle: str):
    await interaction.response.defer(ephemeral=True)
    user_id = str(interaction.user.id)
    result = linkcf.askforcf(user_id, interaction.user.name, cfhandle)
    await interaction.followup.send(result, ephemeral=True)

    # 如果建立成功，就設定 2 分鐘後的過期通知
    if not result.startswith("error:"):
        # 取出 cfhandle 從結果訊息或重新取得
        # 背景任務會處理，我們不需要額外通知了
        # 因為 askforcf 已經存了 expires_at，背景任務會在 2 分鐘後通知
        pass


@bot.tree.command(name="vercf", description="驗證連結 Codeforces")
async def vercf(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    result = linkcf.vertifycf(str(interaction.user.id), interaction.user.name)
    await interaction.followup.send(result, ephemeral=True)

    # 如果成功，發 DM 確認
    if "successfully linked" in result.lower():
        try:
            embed = discord.Embed(
                title="✅ 連結成功",
                description="你的 Discord 已成功連結到 Codeforces！",
                color=0x48c750
            )
            await interaction.user.send(embed=embed)
        except:
            pass
    # 如果過期，在原頻道發送提醒（編輯訊息或發新訊息都太限制，
    # 直接用 followup 已在同一頻道）
    elif "expired" in result.lower():
        cf_data = linkcf._load_link_data()
        # 嘗試取得這個用戶之前嘗試連結的 handle（已經被刪除了）
        pass  # handle 資訊已隨過期刪除，只能提示重新執行


@bot.tree.command(name="unlink", description="解除 Codeforces 連結")
async def unlink_cmd(interaction: discord.Interaction):
    """解除當前 Discord 與 Codeforces 的連結"""
    await interaction.response.defer(ephemeral=True)
    result = linkcf.unlink(str(interaction.user.id))
    await interaction.followup.send(result, ephemeral=True)



# ============================================================
# 指令：Rating 圖
# ============================================================
@bot.tree.command(name="ratingcf", description="顯示 Codeforces 帳號的 Rating 變化圖")
async def ratingcf(interaction: discord.Interaction, cfhandle: str):
    await interaction.response.defer()
    result = cfrating.rating(cfhandle)
    embed = discord.Embed()
    embed.set_author(
        name=f"Rating of {cfhandle}",
        url=f"https://codeforces.com/profile/{cfhandle}"
    )
    embed.set_footer(
        text="Required by " + interaction.user.name,
        icon_url=interaction.user.avatar.url if interaction.user.avatar else None
    )
    if isinstance(result, str):
        await interaction.followup.send(result)
    else:
        embed.set_image(url=f"attachment://{cfhandle}_rating.png")
        await interaction.followup.send(file=result, embed=embed)


# ============================================================
# 指令：找題目
# ============================================================
@bot.tree.command(name="cfprob", description="互動式找 Codeforces 題目 🎯")
async def cfprob(interaction: discord.Interaction):
    """互動式找題目"""
    cf_handle = linkcf.linked(str(interaction.user.id))

    embed = discord.Embed(
        title="🎯 找題目",
        description="1️⃣ 從 Tags 選單選擇想要的類型（可選）\n"
                    "2️⃣ 點「💫 設定」輸入 Rating 範圍與數量\n"
                    "3️⃣ 點「🔍 搜尋」"
    )
    if cf_handle:
        embed.set_footer(text=f"已連結：{cf_handle}｜將自動過濾已解題目 ✅")
    else:
        embed.set_footer(text="⚠️ 未連結 Codeforces｜使用 /cnttocf 連結")

    view = views.ProblemFinderView(bot, interaction.user.name, cf_handle)
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


# ============================================================
# 指令：Duel 系統
# ============================================================
@bot.tree.command(name="duel_challenge", description="⚔️ 向別人發起 duel 挑戰")
async def duel_challenge(interaction: discord.Interaction, opponent: discord.User):
    """以互動式選單發起 Duel 挑戰"""
    if interaction.user.id == opponent.id:
        await interaction.response.send_message("⚠️ 不能跟自己挑戰！", ephemeral=True)
        return

    # 檢查雙方都有連結 CF
    challenger_cf = linkcf.linked(str(interaction.user.id))
    opponent_cf = linkcf.linked(str(opponent.id))

    if not challenger_cf:
        await interaction.response.send_message(
            f"⚠️ 你還沒連結 Codeforces！使用 `/cnttocf <your_handle>` 連結後再試",
            ephemeral=True
        )
        return
    if not opponent_cf:
        await interaction.response.send_message(
            f"⚠️ {opponent.mention} 還沒連結 Codeforces",
            ephemeral=True
        )
        return

    # 建立互動式選單
    view = views.DuelChallengeView(bot, interaction.user, opponent)
    embed = await view._build_embed()

    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


@bot.tree.command(name="duel_stats", description="📊 查看 duel 統計")
async def duel_stats(interaction: discord.Interaction, usr: discord.User = None):
    """查看用戶 duel 統計"""
    target_name = usr.name if usr else interaction.user.name
    stats = duel.get_user_stats(target_name)

    if not stats:
        await interaction.response.send_message(
            f"📊 **{target_name}** 還沒有任何 duel 記錄\n"
            f"使用 `/duel_challenge @user` 發起挑戰！",
            ephemeral=True
        )
        return

    total = stats["wins"] + stats["losses"] + stats["ties"]
    points = stats.get("points", 0)
    win_rate = stats["wins"] / total * 100 if total > 0 else 0

    embed = discord.Embed(
        title=f"⚔️ {target_name} 的 Duel 統計",
        description=(
            f"**積分：{points} 分** | 勝率：{win_rate:.1f}%\n\n"
            f"🏆 勝：{stats['wins']} | 敗：{stats['losses']} | 平：{stats['ties']}\n"
            f"CF Handle：`{stats['cf_handle']}`"
        ),
        color=0xFF4500
    )
    await interaction.response.send_message(embed=embed)


# ============================================================
# 指令：Leaderboard
# ============================================================
@bot.tree.command(name="leaderboard", description="🏅 查看 Duel 排名")
async def leaderboard(interaction: discord.Interaction):
    items = duel.get_leaderboard()

    if not items:
        await interaction.response.send_message(
            "🏅 **Leaderboard 還是空的！**\n快使用 `/duel_challenge` 開始 duel 吧！",
            ephemeral=True
        )
        return

    lines = []
    medals = ["🥇", "🥈", "🥉"]
    for i, item in enumerate(items[:15]):
        medal = medals[i] if i < 3 else f"**{i+1}.**"
        wr = item["win_rate"] * 100
        lines.append(
            f"{medal} **{item['dc_name']}** (`{item['cf_handle']}`)\n"
            f"　　🏆 {item['wins']}/{item['losses']}/{item['ties']}｜"
            f"積分：{item.get('points', 0)}"
        )

    embed = discord.Embed(
        title="🏅 Duel Leaderboard",
        description="\n".join(lines),
        color=0xFFD700
    )
    await interaction.response.send_message(embed=embed)


# ============================================================
# 指令：名字顏色
# ============================================================
@bot.tree.command(name="rolecolor", description="🎨 設定你在伺服器中的名字顏色")
async def rolecolor(interaction: discord.Interaction, hexcode: str):
    """設定使用者在伺服器中的名字顏色"""
    # 驗證 hexcode
    hexcode = hexcode.strip()
    if not hexcode.startswith("#"):
        hexcode = "#" + hexcode

    # 驗證格式
    import re
    if not re.match(r"^#[0-9A-Fa-f]{6}$", hexcode):
        await interaction.response.send_message(
            "⚠️ 請輸入有效的 Hex 顏色代碼（例如：`#FF5500` 或 `FF5500`）",
            ephemeral=True
        )
        return

    guild = interaction.guild
    user = interaction.user
    color_int = int(hexcode.lstrip("#"), 16)

    # 尋找用戶現有的顏色身份組
    color_role = None
    for role in user.roles:
        if role.name.startswith("🎨 "):
            color_role = role
            break

    if color_role:
        # 更新現有身份組的名稱和顏色
        try:
            await color_role.edit(name=f"🎨 {hexcode}", color=discord.Color(color_int))
        except discord.Forbidden:
            await interaction.response.send_message(
                "⚠️ Bot 沒有足夠權限修改身份組", ephemeral=True
            )
            return
    else:
        # 建立新身份組
        try:
            color_role = await guild.create_role(
                name=f"🎨 {hexcode}",
                color=discord.Color(color_int),
                hoist=False,
                reason=f"由 {user} 使用 /rolecolor 建立"
            )
            # 移動到適當位置（低於 @everyone）
            for r in guild.roles:
                if r.name == "@everyone":
                    try:
                        await color_role.edit(position=r.position + 1)
                    except:
                        pass
                    break
        except discord.Forbidden:
            await interaction.response.send_message(
                "⚠️ Bot 沒有足夠權限建立身份組", ephemeral=True
            )
            return

    # 移除其他顏色身份組（防止殘留）
    for role in user.roles:
        if role.name.startswith("🎨 ") and role != color_role:
            try:
                await user.remove_roles(role)
            except:
                pass

    # 給予新的顏色身份組
    try:
        await user.add_roles(color_role)
    except discord.Forbidden:
        await interaction.response.send_message(
            "⚠️ Bot 沒有足夠權限賦予身份組", ephemeral=True
        )
        return

    # 顯示顏色預覽
    color_obj = discord.Color(color_int)
    embed = discord.Embed(
        title="✅ 顏色已更新！",
        description=f"**顏色代碼：** `{hexcode}`",
        color=color_obj
    )
    embed.add_field(
        name="預覽",
        value=f"▮ 這是你的名字顏色",
        inline=False
    )
    embed.set_footer(text="輸入 /rolecolor <新顏色> 可隨時更改")

    await interaction.response.send_message(embed=embed)


# ============================================================
# 指令：AI
# ============================================================
@bot.tree.command(name="ai", description="🤖 問 AI 問題")
async def ai(interaction: discord.Interaction, question: str):
    """呼叫 LLM API 回答問題"""
    # 如果有 llm.py 模組
    try:
        import llm
        await interaction.response.defer()
        response = await llm.call_llm_api(question)
        if len(response) > 1900:
            # 分段發送
            await interaction.followup.send(response[:1900])
            await interaction.channel.send(response[1900:])
        else:
            await interaction.followup.send(response)
    except ImportError:
        await interaction.response.send_message(
            "⚠️ AI 功能尚未設定（缺少 llm.py）", ephemeral=True
        )


# ============================================================
# 指令：訊息總結
# ============================================================
@bot.tree.command(name="summarize", description="📝 用 AI 總結頻道最近的聊天記錄")
async def summarize(interaction: discord.Interaction):
    """用 AI 總結頻道最近的聊天記錄"""

    # 安全閘：確保開機完全就緒，避免 404 Unknown interaction
    if not _startup_complete:
        await interaction.response.send_message(
            "⚠️ 機器人正在啟動中，請稍等幾秒後再試", ephemeral=True
        )
        return

    # User Install 檢查：guild_id 為 None 表示在 DM 環境
    # Bot 沒有辦法在未加入的伺服器讀取頻道歷史
    if interaction.guild_id is None:
        await interaction.response.send_message(
            "⚠️ 此指令需要在伺服器頻道中使用，且 Bot 必須已加入該伺服器並拥有「讀取訊息歷史」權限。\n"
            "❗目前無法使用 App 方法（User Install）跨伺服器讀取，因為 Bot 需要在目標頻道有權限。\n\n"
            "💡 解法：將 Bot 邀請到您想總結的伺服器，並給予讀取訊息歷史權限後再使用。",
            ephemeral=True
        )
        return

    await interaction.response.defer(ephemeral=True)

    channel = interaction.channel
    if not isinstance(channel, discord.TextChannel):
        await interaction.followup.send(
            "⚠️ 只能在文字頻道中使用這個指令", ephemeral=True
        )
        return

    from discord import ui

    class TimeSelectView(ui.View):
        def __init__(view_self):
            super().__init__(timeout=60)
            view_self.selected = False

        @ui.select(
            placeholder="選擇要總結的時間範圍",
            options=[
                discord.SelectOption(label="最近 15 分鐘", value="15m", emoji="⏱️"),
                discord.SelectOption(label="最近 30 分鐘", value="30m", emoji="⏱️"),
                discord.SelectOption(label="最近 1 小時", value="1h", emoji="🕐"),
                discord.SelectOption(label="最近 3 小時", value="3h", emoji="🕐"),
                discord.SelectOption(label="最近 6 小時", value="6h", emoji="🕓"),
                discord.SelectOption(label="最近 12 小時", value="12h", emoji="🕛"),
                discord.SelectOption(label="最近 1 天", value="1d", emoji="📅"),
                discord.SelectOption(label="最近 2 天", value="2d", emoji="📅"),
            ],
            min_values=1,
            max_values=1,
            row=0
        )
        async def time_select(view_self, interaction: discord.Interaction, select):
            view_self.selected = True
            time_value = select.values[0]

            # 解析選擇的時間
            time_seconds = parse_time_string(time_value)
            if time_seconds is None:
                await interaction.response.send_message(
                    "⚠️ 時間解析錯誤", ephemeral=True
                )
                return

            # 回應選擇（短暫載入中訊息，僅使用者可見）
            embed = discord.Embed(
                title="🔄 AI 正在分析訊息...",
                description=f"📊 時間範圍：最近 **{format_time_display(time_seconds)}**\n"
                            f"⏳ 正在讀取頻道訊息並生成摘要（最多讀取 **2000 筆**）\n"
                            f"請稍候...",
                color=0x3489da
            )
            embed.set_footer(text=f"由 {interaction.user.name} 發起")
            await interaction.response.send_message(embed=embed, ephemeral=True)

            # 開始總結
            await do_summarize(interaction, time_seconds)

    embed = discord.Embed(
        title="📝 頻道訊息總結",
        description="請選擇要總結的時間範圍\n"
                    "AI 會分析這段時間內的聊天內容並生成摘要\n\n",
        color=0x3489da
    )

    # 使用 followup.send() 並設定 ephemeral=True 讓訊息只有使用者可見
    await interaction.followup.send(embed=embed, view=TimeSelectView(), ephemeral=True)


async def do_summarize(interaction: discord.Interaction, time_seconds: int):
    """執行訊息總結的核心邏輯"""
    import llm
    import datetime

    channel = interaction.channel
    time_display = format_time_display(time_seconds)

    try:
        # 主動權限檢查（不必等到 API 回 403 才發現）
        if isinstance(channel, discord.TextChannel):
            permissions = channel.permissions_for(channel.guild.me)
            if not permissions.read_message_history:
                await interaction.edit_original_response(
                    embed=discord.Embed(
                        title="❌ 權限不足",
                        description="⚠️ Bot 需要「讀取訊息歷史」權限才能使用此功能\n"
                                    "請前往 Discord 伺服器設定 → 頻道權限 → 為 Bot 角色開啟「讀取訊息歷史」",
                        color=0xff0000
                    )
                )
                return
            if not permissions.send_messages:
                await interaction.edit_original_response(
                    embed=discord.Embed(
                        title="❌ 權限不足",
                        description="⚠️ Bot 需要「發送訊息」權限",
                        color=0xff0000
                    )
                )
                return

        cutoff_time = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(seconds=time_seconds)

        # 取得頻道歷史訊息
        messages = []
        async for message in channel.history(after=cutoff_time, limit=2000):
            if message.content and not message.content.strip().startswith('?'):
                messages.append({
                    "author": message.author.name,
                    "content": message.content,
                    "time": message.created_at.strftime("%H:%M")
                })

        if not messages:
            embed = discord.Embed(
                title="📝 頻道訊息總結",
                description=f"📭 在過去 {time_display} 內找不到任何訊息",
                color=0x808080
            )
            embed.set_footer(text=f"由 {interaction.user.name} 請求")
            await interaction.edit_original_response(embed=embed)
            return

        # 格式化訊息用於總結
        msg_list_text = "\n".join([
            f"[{m['time']}] {m['author']}: {m['content']}"
            for m in messages[-50:]
        ])

        # 詳細的總結 prompt（適用於 Discord Embed）
        prompt = f"""你是 Discord 頻道的聊天記錄分析師。請仔細閱讀以下聊天記錄，並提供詳細的摘要報告。

## 任務
分析這個 Discord 頻道在過去 {time_display} 內的聊天內容。

## 請用繁體中文回答，並使用 Discord 適用的格式：
- 使用 **粗體** 強調標題
- 使用 • 或 - 作為列表符號
- 使用 > 引言框 標示重要內容
- 不要使用表格（Discord 不支援），改用列表呈現
- 每個大標題使用 **標題** 格式

## 請包含以下結構：

**📌 主要話題**
列出 2-5 個主要討論的話題或主題，按照重要程度排序。

**💬 重要討論**
描述幾個重要的對話片段或爭論點，包括：
• 問題的背景
• 各方的觀點或論點
• 如果有結論，應該是什麼

**✅ 結論與決定**
如果有任何人做出了決定、承諾或需要後續跟進的事項，請列出來。

**💡 有價值的分享**
列出任何有用的資訊、建議、資源或分享。

**👥 參與者活躍度**
簡單提及最活躍的幾位成員（可匿名，只用「成員 A」等）。

## 聊天記錄（共 {len(messages)} 條訊息）：
{msg_list_text}

## 摘要報告："""

        response = await llm.call_llm_api(prompt, use_rate_limit=True, max_tokens=2048)

        if response.startswith("Error"):
            await interaction.edit_original_response(
                embed=discord.Embed(
                    title="📝 頻道訊息總結",
                    description="⚠️ AI 分析時發生錯誤，請稍後再試",
                    color=0x903c3c
                )
            )
            return

        # 發送公開訊息（所有人可見）
        # 檢查回應長度，Discord embed description 限制 4096 字元
        if len(response) > 4090:
            response = response[:4087] + "..."

        result_embed = discord.Embed(
            title="📝 頻道訊息總結",
            description=response,
            color=0x3489da
        )

        # 如果被截斷，添加提醒
        footer_text = f"📊 分析了 {len(messages)} 條訊息 | 時間範圍：{time_display}"
        if len(response) >= 4087:
            footer_text += " | ⚠️ 已截斷（內容過長）"

        result_embed.set_footer(text=footer_text)
        result_embed.set_author(
            name=f"由 {interaction.user.name} 請求",
            icon_url=interaction.user.avatar.url if interaction.user.avatar else None
        )

        # 發送到頻道
        await channel.send(embed=result_embed)

        # 更新原來只有使用者可見的訊息
        done_embed = discord.Embed(
            title="✅ 分析完成",
            description=f"📝 摘要已發送至頻道\n"
                        f"📊 分析了 {len(messages)} 條訊息",
            color=0x48c750
        )
        await interaction.edit_original_response(embed=done_embed)

    except discord.Forbidden:
        await interaction.edit_original_response(
            embed=discord.Embed(
                title="❌ 權限不足",
                description=" Bot 需要「讀取訊息歷史」權限才能使用此功能\n"
                            "請聯絡管理員將 Bot 的「讀取訊息歷史」權限開啟",
                color=0xff0000
            )
        )

    except Exception as e:
        print(f"[summarize error] {e}")
        import traceback
        traceback.print_exc()
        await interaction.edit_original_response(
            embed=discord.Embed(
                title="📝 頻道訊息總結",
                description="⚠️ 發生錯誤，無法總結訊息",
                color=0x903c3c
            )
        )


def parse_time_string(time_str: str) -> int | None:
    """
    解析時間字串為秒數

    Examples:
        "1h" -> 3600
        "30m" -> 1800
        "1d" -> 86400

    Returns:
        秒數，如果格式無效則返回 None
    """
    import re
    time_str = time_str.strip().lower()

    # 匹配格式：數字 + 單位（m/h/d/s）
    match = re.match(r'^(\d+)([mhdhs])$', time_str)
    if not match:
        return None

    value = int(match.group(1))
    unit = match.group(2)

    multipliers = {
        's': 1,
        'm': 60,
        'h': 3600,
        'd': 86400
    }

    return value * multipliers[unit]


def format_time_display(seconds: int) -> str:
    """將秒數轉換為可讀的時間顯示"""
    if seconds >= 86400:
        days = seconds // 86400
        return f"{days} 天"
    elif seconds >= 3600:
        hours = seconds // 3600
        return f"{hours} 小時"
    elif seconds >= 60:
        mins = seconds // 60
        return f"{mins} 分鐘"
    else:
        return f"{seconds} 秒"


# ============================================================
# 指令：角色選擇選單
# ============================================================
@bot.tree.command(name="roleselect", description="📋 選擇你的身份組")
async def roleselect(interaction: discord.Interaction):
    """為所有人顯示 select menu 選擇身份組"""
    guild_id = str(interaction.guild.id)
    selects_data = views.load_persistent_selects()

    # 找這個伺服器的最後一個選單
    menu = None
    for mid, m in selects_data.get("menus", {}).items():
        if str(m.get("guild_id")) == guild_id:
            menu = m  # 會被最後一個覆蓋

    if not menu:
        await interaction.response.send_message(
            "⚠️ 這個伺服器還沒有建立身份組選單\n請管理員使用 `/roleselect_admin` 建立",
            ephemeral=True
        )
        return

    # 獲取身份組對象
    guild = interaction.guild
    role_objs = []
    for rid_str, rname in menu.get("roles", {}).items():
        role = guild.get_role(int(rid_str))
        if role:
            role_objs.append(role)

    if not role_objs:
        await interaction.response.send_message(
            "⚠️ 選單中的身份組已不存在",
            ephemeral=True
        )
        return

    # 構建 Embed 和視圖（使用內嵌選擇）
    embed = discord.Embed(
        title=menu.get("title", "自選身份組"),
        description=menu.get("description", "選擇你想要的身份組") + "\n\n👇 點擊下方選擇身份組 👇",
        color=0x3489da
    )
    embed.set_footer(text="點擊「❌ 關閉」結束")

    # 使用內嵌選擇視圖
    view = views.build_user_role_select(role_objs, guild)

    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


@bot.tree.command(name="roleselect_admin", description="🔧 建立/管理身份組選單（管理員）")
async def roleselect_admin(interaction: discord.Interaction):
    """管理員建立和管理身份組選單"""
    # 檢查管理員權限
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message(
            "⚠️ 只有管理員才能使用這個指令",
            ephemeral=True
        )
        return

    view = views.RoleSelectBuilderView(bot, interaction.guild)
    embed = discord.Embed(
        title="🔧 身份組選單管理",
        description=(
            "**使用步驟：**\n"
            "1️⃣ 點「➕ 選擇身份組」選擇要加入的身份組\n"
            "2️⃣ （可選）用下拉選單選擇發送頻道\n"
            "3️⃣ （可選）點「✏️ 設定標題」自訂標題和說明\n"
            "4️⃣ 點「📨 發送選單」將選單發送到頻道\n\n"
            "**功能說明：**\n"
            "• 所有人可以使用 `/roleselect` 打開選單（只自己看得見）\n"
            "• 選擇身份組 → 自動添加\n"
            "• 取消選擇 → 自動移除"
        ),
        color=0x3489da
    )

    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)




# ============================================================
# 啟動
# ============================================================
if __name__ == "__main__":
    bot.run(dctoken)