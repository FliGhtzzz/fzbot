import discord
import time
import json
import os
from discord import ui
from discord.ext.commands import Bot
import throwcf
import duel as duel_mod
import linkcf

try:
    import emoji as emoji_lib
except ImportError:
    emoji_lib = None


# Discord 內建表情對照表（常見的）
DISCORD_EMOJI_ALIASES = {
    # 臉部表情
    "pensive": "😔",
    "confused": "😕",
    "lying_face": "🤥",
    "zipper_mouth_face": "🤐",
    "money_mouth_face": "🤑",
    "face_with_thermometer": "🤒",
    "nerd_face": "🤓",
    "sunglasses": "🕶️",
    "hugging_face": "🤗",
    "smirk": "😏",
    "no_mouth": "🚫",
    "neutral_face": "😐",
    "expressionless": "😑",
    "unamused": "😒",
    "slightly_frowning_face": "🙁",
    "frowning_face": "☹️",
    "face_with_rolling_eyes": "🙄",
    "thinking_face": "🤔",
    "robot": "🤖",
    "wave": "👋",
    "thumbsup": "👍",
    "thumbsdown": "👎",
    "point_up": "☝️",
    "point_down": "👇",
    "point_left": "👈",
    "point_right": "👉",
    "clap": "👏",
    "fist": "✊",
    "v": "✌️",
    "sparkles": "✨",
    "star": "⭐",
    "heart": "❤️",
    "fire": "🔥",
    "eyes": "👀",
    # 其他常見
    "arrow_up": "⬆️",
    "arrow_down": "⬇️",
    "arrow_left": "⬅️",
    "arrow_right": "➡️",
    "white_check_mark": "✅",
    "x": "❌",
    "negative_squared_cross_mark": "❎",
    "question": "❓",
    "exclamation": "❗",
    "warning": "⚠️",
    "cat": "🐱",
    "dog": "🐶",
    "smile_cat": "😺",
    "smile": "😄",
    "laughing": "😆",
    "blush": "😊",
    "heart_eyes": "😍",
    "kissing_heart": "😘",
    "stuck_out_tongue_winking_eye": "😜",
    "stuck_out_tongue_closed_eyes": "😝",
    "sweat_smile": "😅",
    "joy": "😂",
    "rofl": "🤣",
    "relaxed": "☺️",
    "cry": "😢",
    "sob": "😭",
    "angry": "😠",
    "rage": "😡",
    "triumph": "😤",
    "weary": "😩",
    "tired_face": "😫",
    "fearful": "😨",
    "scream": "😱",
    "flushed": "😳",
    "open_mouth": "😮",
    "astonished": "😲",
    "dizzy_face": "😵",
    "zipper_mouth": "🤐",
    "sleeping": "😴",
    "sleepy": "😪",
    "mask": "😷",
    "face_with_head_bandage": "🤕",
    "sneezing_face": "🤧",
    "cowboy_hat_face": "🤠",
    "upside_down_face": "🙃",
    "hatching_chick": "🐣",
    "baby_chick": "🐤",
    "hatched_chick": "🐥",
    "bird": "🐦",
    "penguin": "🐧",
    "fish": "🐟",
    "tropical_fish": "🐠",
    "blowfish": "🐡",
    "dolphin": "🐬",
    "mouse": "🐭",
    "hamster": "🐹",
    "rabbit": "🐰",
    "bear": "🐻",
    "panda_face": "🐼",
    "koala": "🐨",
    "tiger": "🐯",
    "lion_face": "🦁",
    "pig": "🐷",
    "boar": "🐗",
    "monkey_face": "🐵",
    "monkey": "🐒",
    "gorilla": "🦍",
    "poodle": "🐩",
    "wolf": "🐺",
    "fox_face": "🦊",
    "crab": "🦀",
    "snake": "🐍",
    "turtle": "🐢",
    "bug": "🐛",
    "ant": "🐜",
    "bee": "🐝",
    "beetle": "🪲",
    "snail": "🐌",
    "octopus": "🐙",
    "dragon_face": "🐲",
    "crocodile": "🐊",
}


def parse_emoji(text):
    """將 colon 格式或 Unicode 轉換為標準 emoji 字符"""
    if not text:
        return text

    text = text.strip()

    # Discord 自訂 emoji（<:name:id> 格式），直接返回
    if text.startswith('<') and text.endswith('>'):
        return text

    # colon 格式 (e.g. :pensive:、:man_with_chinese_cap:)
    if text.startswith(':') and text.endswith(':'):
        # 先從自訂對照表查找（Discord 內建表情）
        alias = text[1:-1].lower().strip()
        if alias in DISCORD_EMOJI_ALIASES:
            return DISCORD_EMOJI_ALIASES[alias]

        # 再嘗試 emoji 庫
        if emoji_lib:
            try:
                result = emoji_lib.emojize(text, language='alias')
                if result != text:  # 成功轉換
                    return result
            except Exception:
                pass

    return text


# Codeforces 熱門標籤（最多25個，含不清選）
POPULAR_TAGS = [
    "dp", "math", "greedy", "graphs", "data-structures",
    "sortings", "binary-search", "number-theory", "constructive-algorithms",
    "strings", "geometry", "brute-force", "two-pointers", "divide-and-conquer",
    "bitmasks", "combinatorics", "trees", "hashing", "implementation", "probability",
    "segment-tree", "flows", "graph-matchings", "games"
]

# 標籤對應中文
TAG_NAMES = {
    "dp": "動態規劃", "math": "數學", "greedy": "貪心", "graphs": "圖論",
    "data-structures": "資料結構", "sortings": "排序", "binary-search": "二分搜尋",
    "number-theory": "數論", "constructive-algorithms": "構造性演算法",
    "strings": "字串處理", "geometry": "幾何", "brute-force": "暴力枚舉",
    "two-pointers": "雙指標", "divide-and-conquer": "分治法",
    "bitmasks": "位元運算", "combinatorics": "組合數學", "trees": "樹論",
    "hashing": "雜湊", "implementation": "實作題", "probability": "機率",
    "segment-tree": "線段樹", "flows": "網路流", "graph-matchings": "圖匹配",
    "games": "博弈論"
}


def load_role_reactions():
    """載入角色反應設定，並將舊的 :emoji: 格式自動轉換為實際 emoji"""
    if not os.path.exists("role_reactions.json"):
        return {"menus": {}}
    with open("role_reactions.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    # 修補舊資料：將所有 roles_map 的 key 從 :emoji: 格式轉為實際 emoji
    for msg_id, menu in data.get("menus", {}).items():
        if "roles" in menu:
            fixed_roles = {}
            changed = False
            for emoji_key, role_id in menu["roles"].items():
                parsed = parse_emoji(emoji_key)
                if parsed != emoji_key:
                    changed = True
                fixed_roles[parsed] = role_id
            if changed:
                menu["roles"] = fixed_roles

    return data


def save_role_reactions(data):
    """儲存角色反應設定"""
    with open("role_reactions.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ============================================================
# 角色反應選單相關 UI
# ============================================================

class RoleReactionSetupView(ui.View):
    """管理員設定角色反應選單的 View"""

    def __init__(self, bot: Bot):
        super().__init__(timeout=300)
        self.bot = bot
        self.guild = None
        self.selected_roles = []
        self.menu_title = None
        self.menu_description = None
        self.custom_emojis = {}

    @ui.button(label="➕ 選擇身份組", style=discord.ButtonStyle.primary, row=0)
    async def select_roles(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.guild:
            self.guild = interaction.guild

        # 取得所有身份組選項（排除 @everyone、managed、顏色身份組）
        options = [
            discord.SelectOption(label=role.name, value=str(role.id))
            for role in self.guild.roles
            if role.name != "@everyone" and not role.managed and not role.name.startswith("🎨 ")
        ]

        if not options:
            await interaction.response.send_message(
                "⚠️ 伺服器中沒有可用的身份組",
                ephemeral=True
            )
            return

        # 使用選擇視窗
        select_view = RoleSelectMenuView(self)
        select_view.role_select.options = options[:25]  # Discord 限制最多 25 個
        select_view.role_select.max_values = min(20, len(options))  # 依實際數量調整
        await interaction.response.send_message(
            "請選擇身份組（可多選）：",
            view=select_view,
            ephemeral=True
        )

    @ui.button(label="🔧 自訂 Emoji", style=discord.ButtonStyle.secondary, row=0)
    async def set_emojis(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.selected_roles:
            await interaction.response.send_message(
                "⚠️ 請先選擇身份組",
                ephemeral=True
            )
            return
        self.guild = interaction.guild
        modal = RoleReactionEmojiModal(self)
        await interaction.response.send_modal(modal)

    @ui.button(label="✏️ 設定標題與說明", style=discord.ButtonStyle.primary, row=1)
    async def set_info(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.guild:
            self.guild = interaction.guild
        modal = RoleReactionInfoModal(self)
        await interaction.response.send_modal(modal)

    @ui.button(label="📨 發送選單", style=discord.ButtonStyle.success, row=1)
    async def send_menu(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.selected_roles:
            await interaction.response.send_message(
                "⚠️ 請先點「➕ 選擇身份組」",
                ephemeral=True
            )
            return

        if not self.menu_title:
            await interaction.response.send_message(
                "⚠️ 請先點「✏️ 設定標題與說明」",
                ephemeral=True
            )
            return

        channel = interaction.channel
        guild = interaction.guild

        # 預設表情
        default_emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟",
                         "🅰️", "🅱️", "🅲️", "🅳️", "🅴️", "🅵️", "🅶️", "🅷️", "🅸️", "🅹️"]

        role_lines = []
        emoji_to_role = {}

        for i, role in enumerate(self.selected_roles):
            if role.id in self.custom_emojis:
                emoji = self.custom_emojis[role.id]
            else:
                emoji = default_emojis[i] if i < len(default_emojis) else f"#{i+1}"
            emoji_to_role[emoji] = role.id
            role_lines.append(f"{emoji} → {role.mention}")

        embed = discord.Embed(
            title=self.menu_title,
            description=self.menu_description + "\n\n" + "\n".join(role_lines),
            color=0x3489da
        )
        embed.set_footer(text="點擊下方表情符號來獲得身份組 ✅")

        message = await channel.send(embed=embed)

        # 嘗試添加反應，無效的 emoji 會跳過
        valid_emojis = {}
        for emoji, role_id in emoji_to_role.items():
            try:
                await message.add_reaction(emoji)
                valid_emojis[emoji] = role_id
            except Exception:
                print(f"[role menu] 無效的 emoji '{emoji}'，已跳過")

        # 儲存
        data = load_role_reactions()
        data["menus"][str(message.id)] = {
            "title": self.menu_title,
            "description": self.menu_description,
            "channel_id": channel.id,
            "guild_id": guild.id,
            "roles": valid_emojis
        }
        save_role_reactions(data)

        self.selected_roles = []
        self.menu_title = None
        self.menu_description = None
        self.custom_emojis = {}

        await interaction.response.edit_message(
            content=f"✅ 選單已發送至 <#{channel.id}>",
            view=RoleSentView()
        )

    @ui.button(label="🔄 重置", style=discord.ButtonStyle.danger, row=2)
    async def reset(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.selected_roles = []
        self.menu_title = None
        self.menu_description = None
        self.custom_emojis = {}
        new_view = RoleReactionSetupView(self.bot)
        await interaction.response.edit_message(content="✅ 已重置", view=new_view)


class RoleSelectMenuView(ui.View):
    """選擇身份組的視窗"""

    def __init__(self, parent_view: RoleReactionSetupView):
        super().__init__(timeout=60)
        self.parent = parent_view
        self.role_select = ui.Select(
            placeholder="選擇身份組（可多選）",
            options=[discord.SelectOption(label="...", value="...")],
            min_values=1,
            max_values=20
        )
        self.role_select.callback = self._select_callback
        self.add_item(self.role_select)

    async def _select_callback(self, interaction: discord.Interaction):
        # 選擇時只需要 defer，避免 Discord 顯示 "This interaction failed"
        await interaction.response.defer()

    @ui.button(label="✅ 確認", style=discord.ButtonStyle.success, row=1)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            if self.role_select.values:
                self.parent.selected_roles = [
                    interaction.guild.get_role(int(rid))
                    for rid in self.role_select.values
                    if interaction.guild.get_role(int(rid))
                ]
            await interaction.response.edit_message(
                content=f"已選擇：{'、'.join([r.name for r in self.parent.selected_roles])}",
                view=None
            )
        except Exception as e:
            print(f"[RoleSelectMenuView.confirm error] {e}")
            import traceback
            traceback.print_exc()
            try:
                await interaction.response.send_message("❌ 發生錯誤，請再試一次", ephemeral=True)
            except:
                pass

    @ui.button(label="❌ 取消", style=discord.ButtonStyle.danger, row=1)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content="已取消選擇", view=None)


class RoleSentView(ui.View):
    """選單發送後的空 View（用於禁用按鈕）"""

    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(ui.Button(label="✅ 已發送", style=discord.ButtonStyle.secondary, disabled=True))


class RoleReactionInfoModal(ui.Modal, title="設定選單資訊"):
    """管理員輸入標題和說明"""

    title_input = ui.TextInput(
        label="標題",
        placeholder="例：選擇你的程式語言",
        required=True,
        max_length=100
    )
    description_input = ui.TextInput(
        label="說明",
        placeholder="例：選擇你擅長的語言（可多選，按多次可切換）",
        required=True,
        max_length=500
    )

    def __init__(self, view: RoleReactionSetupView):
        super().__init__()
        self.callback_view = view

    async def on_submit(self, interaction: discord.Interaction):
        self.callback_view.menu_title = self.title_input.value
        self.callback_view.menu_description = self.description_input.value
        await interaction.response.send_message(
            f"✅ 已設定！\n標題：{self.title_input.value}\n說明：{self.description_input.value}",
            ephemeral=True
        )


class RoleReactionEmojiModal(ui.Modal, title="自訂 Emoji"):
    """管理員為每個角色設定自訂 emoji"""

    def __init__(self, view: RoleReactionSetupView):
        super().__init__()
        self.callback_view = view

        # 動態建立 TextInput
        self.custom_items = []
        for i, role in enumerate(view.selected_roles[:10]):  # 最多10個
            txt = ui.TextInput(
                label=f"{role.name} 的 Emoji",
                placeholder=f"例：🔥（{i+1}）",
                required=False,
                max_length=30
            )
            self.custom_items.append(txt)
            self.add_item(txt)

    async def on_submit(self, interaction: discord.Interaction):
        # 儲存輸入的 emoji（使用 parse_emoji 轉換）
        valid = {}
        for i, txt in enumerate(self.custom_items):
            if txt.value and i < len(self.callback_view.selected_roles):
                role = self.callback_view.selected_roles[i]
                emoji = parse_emoji(txt.value.strip())
                valid[role.id] = emoji
        self.callback_view.custom_emojis = valid

        # 建立回報訊息
        guild = interaction.guild
        if guild and self.callback_view.custom_emojis:
            lines = []
            for rid, emoji in self.callback_view.custom_emojis.items():
                role_obj = guild.get_role(rid)
                role_name = role_obj.name if role_obj else "Unknown"
                lines.append(f"{role_name} → {emoji}")
            mappings = "\n".join(lines)
            count = len(self.callback_view.custom_emojis)
            msg = f"✅ 已設定 {count} 個自訂 Emoji：\n{mappings}\n\n📌 如果在發送選單時某個 emoji 無效，該角色將使用預設表情。"
        else:
            msg = "📌 沒有設定自訂 Emoji，將使用預設表情。"

        await interaction.response.send_message(msg, ephemeral=True)


# ============================================================
# 現有的其他 View 類別
# ============================================================

class ProblemResultView(ui.View):
    """顯示題目結果的 view，支援分頁和刷新"""

    def __init__(self, problems: list, page: int = 0, original_params: dict = None):
        super().__init__(timeout=180)
        self.problems = problems
        self.page = page
        self.per_page = 5
        self.original_params = original_params or {}
        self._update_buttons()

    def _update_buttons(self):
        max_page = max(0, (len(self.problems) - 1) // self.per_page) if self.problems else 0
        prev_button = self.children[0]
        next_button = self.children[1]
        prev_button.disabled = self.page <= 0
        next_button.disabled = self.page >= max_page

    async def _render_embed(self) -> discord.Embed:
        start = self.page * self.per_page
        end = min(start + self.per_page, len(self.problems))
        max_page = max(1, (len(self.problems) - 1) // self.per_page + 1) if self.problems else 1
        lines = []
        for i, p in enumerate(self.problems[start:end], start + 1):
            lines.append(
                f"{i}. [{p['name']}](https://codeforces.com/problemset/problem/{p['contestId']}/{p['index']}) ⭐{p['rating']}"
            )
        embed = discord.Embed(
            title="🎯 推薦題目",
            description="\n".join(lines),
            color=0x48c750
        )
        embed.set_footer(text=f"第 {self.page + 1} / {max_page} 頁")
        return embed

    @ui.button(label="⬅️ 上一頁", style=discord.ButtonStyle.secondary, disabled=True)
    async def prev_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.page > 0:
            self.page -= 1
            self._update_buttons()
            await interaction.response.edit_message(embed=await self._render_embed(), view=self)

    @ui.button(label="➡️ 下一頁", style=discord.ButtonStyle.secondary, disabled=True)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        max_page = max(0, (len(self.problems) - 1) // self.per_page) if self.problems else 0
        if self.page < max_page:
            self.page += 1
            self._update_buttons()
            await interaction.response.edit_message(embed=await self._render_embed(), view=self)

    @ui.button(label="🔄 再抽一批", style=discord.ButtonStyle.primary)
    async def refresh_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        params = self.original_params
        new_problems, result = throwcf.askprob(
            mnrating=params.get("mnrating", 800),
            mxrating=params.get("mxrating", 3500),
            num=params.get("num", 5),
            solved=params.get("solved", False),
            linktxt="",
            cf_handle=params.get("cf_handle"),
            tags=params.get("tags"),
            indices=params.get("indices"),
        )
        if not new_problems:
            await interaction.response.send_message(embed=result if result else discord.Embed(title="Error", description="找不到符合條件的題目", color=0x903c3c), ephemeral=True)
            return
        new_view = ProblemResultView(problems=new_problems, page=0, original_params=params)
        await interaction.response.edit_message(embed=await new_view._render_embed(), view=new_view)


class SettingsModal(ui.Modal, title="設定搜尋條件"):
    min_rating = ui.TextInput(label="最小 Rating", placeholder="例：800", required=True, min_length=3, max_length=4)
    max_rating = ui.TextInput(label="最大 Rating", placeholder="例：2000", required=True, min_length=3, max_length=4)
    count = ui.TextInput(label="題目數量", placeholder="例：5", required=True, min_length=1, max_length=2)

    def __init__(self, callback_view):
        super().__init__()
        self.callback_view = callback_view

    async def on_submit(self, interaction: discord.Interaction):
        try:
            mn = int(self.min_rating.value)
            mx = int(self.max_rating.value)
            nc = int(self.count.value)
            if mn > mx:
                await interaction.response.send_message("⚠️ 最小不能大於最大", ephemeral=True)
                return
            if nc < 1 or nc > 50:
                await interaction.response.send_message("⚠️ 數量需在 1-50", ephemeral=True)
                return
            self.callback_view.selections["rating_min"] = mn
            self.callback_view.selections["rating_max"] = mx
            self.callback_view.selections["count"] = nc
            self.callback_view.custom_rating = f"{mn}-{mx}"
            await interaction.response.send_message(f"✅ 已設定：Rating {mn}-{mx}，{nc} 題", ephemeral=True)
        except ValueError:
            await interaction.response.send_message("⚠️ 請輸入有效數字", ephemeral=True)


class ProblemFinderView(ui.View):
    def __init__(self, bot: Bot, user_name: str, cf_handle: str):
        super().__init__(timeout=180)
        self.bot = bot
        self.user_name = user_name
        self.cf_handle = cf_handle
        self.current_problems = []
        self.original_params = {}
        self.selections = {}
        self.custom_rating = None

    async def build_embed(self) -> discord.Embed:
        rating = self.custom_rating if self.custom_rating else "未設定"
        count = str(self.selections.get("count", "未設定"))
        tags = ", ".join(self.selections.get("tags", [])) or "未設定"
        embed = discord.Embed(
            title="🎯 找題目",
            description="1️⃣ （可選）從下方選擇 Tags\n2️⃣ 點「💫 設定」輸入 Rating 範圍與數量\n3️⃣ 點「🔍 搜尋」",
            color=0x3489da
        )
        embed.add_field(name="當前設定", value=f"Rating={rating} | 數量={count} | Tags={tags}", inline=False)
        if self.cf_handle:
            embed.set_footer(text=f"已連結：{self.cf_handle}｜自動過濾已解題目")
        else:
            embed.set_footer(text="⚠️ 未連結 Codeforces")
        return embed

    @ui.select(placeholder="選擇 Tags（可選，最多5個）",
        options=[discord.SelectOption(label=f"{t} ({TAG_NAMES.get(t, t)})", value=t) for t in POPULAR_TAGS] + [discord.SelectOption(label="不清選", value="__none__")],
        min_values=0, max_values=5, row=0)
    async def tags_select(self, interaction: discord.Interaction, select):
        tags = [v for v in select.values if v != "__none__"]
        self.selections["tags"] = tags or None
        await interaction.response.defer()

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return True

    @ui.button(label="💫 設定 Rating 與數量", style=discord.ButtonStyle.primary, row=1)
    async def settings(self, i, b):
        await i.response.send_modal(SettingsModal(self))

    @ui.button(label="🔍 搜尋", style=discord.ButtonStyle.success, row=1)
    async def find_button(self, i, b):
        if "rating_min" not in self.selections:
            await i.response.send_message("⚠️ 請先點「💫 設定」輸入 Rating 範圍與數量", ephemeral=True)
            return
        mn = self.selections["rating_min"]
        mx = self.selections["rating_max"]
        tags = self.selections.get("tags")
        num = self.selections["count"]
        solved = bool(self.cf_handle)
        params = {"mnrating": mn, "mxrating": mx, "num": num, "solved": solved, "cf_handle": self.cf_handle, "tags": tags, "indices": None}
        problems, result = throwcf.askprob(**params)
        if not problems:
            await i.response.send_message(embed=result, ephemeral=True); return
        self.current_problems = problems
        self.original_params = params
        rv = ProblemResultView(problems=problems, page=0, original_params=params)
        await i.response.send_message(embed=await rv._render_embed(), view=rv)

    @ui.button(label="↩️ 重置", style=discord.ButtonStyle.secondary, row=2)
    async def reset(self, i, b):
        self.selections = {}; self.current_problems = []
        self.original_params = {}; self.custom_rating = None
        new_view = ProblemFinderView(self.bot, self.user_name, self.cf_handle)
        await i.response.edit_message(content="✅ 已重置", embed=await new_view.build_embed(), view=new_view)


# ============================================================
# Duel 相關 UI
# ============================================================

class DuelChallengeView(ui.View):
    """Duel 挑戰設定視圖"""

    def __init__(self, bot: Bot, challenger: discord.User, opponent: discord.User):
        super().__init__(timeout=300)
        self.bot = bot
        self.challenger = challenger
        self.challenger_name = challenger.name
        self.opponent = opponent
        self.opponent_name = opponent.name
        self.min_rating = 800
        self.max_rating = 1600
        self.num_problems = 3
        self.duration_minutes = 10
        self.selected_tags = []
        self._setup_ui()

    def _setup_ui(self):
        """建立 UI 元件"""
        self.clear_items()

        # Tags 選擇
        tags_options = [
            discord.SelectOption(label=f"{t} ({TAG_NAMES.get(t, t)})", value=t)
            for t in POPULAR_TAGS
        ] + [discord.SelectOption(label="不清選", value="__none__")]

        tags_select = ui.Select(
            placeholder="🏷️ 選擇 Tags（可選，最多5個）",
            options=tags_options,
            min_values=0,
            max_values=5,
            row=0
        )

        async def tags_cb(i: discord.Interaction):
            self.selected_tags = [v for v in tags_select.values if v != "__none__"]
            await i.response.send_message(
                f"✅ 已選擇 {len(self.selected_tags)} 個 Tags",
                ephemeral=True
            )

        tags_select.callback = tags_cb
        self.add_item(tags_select)

        # 時間限制選擇（row=1，只能放一個 Select）
        time_options = [
            discord.SelectOption(label="1 分鐘", value="1", emoji="⏱️"),
            discord.SelectOption(label="10 分鐘", value="10", emoji="⏱️"),
            discord.SelectOption(label="15 分鐘", value="15", emoji="⏱️"),
            discord.SelectOption(label="30 分鐘", value="30", emoji="⏱️"),
            discord.SelectOption(label="45 分鐘", value="45", emoji="⏱️"),
            discord.SelectOption(label="60 分鐘", value="60", emoji="⏱️"),
            discord.SelectOption(label="90 分鐘", value="90", emoji="⏱️"),
            discord.SelectOption(label="120 分鐘", value="120", emoji="⏱️"),
        ]
        time_select = ui.Select(
            placeholder=f"⏰ 時間：{self.duration_minutes} 分鐘",
            options=time_options,
            row=1
        )

        async def time_cb(i: discord.Interaction):
            self.duration_minutes = int(time_select.values[0])
            self._setup_ui()
            new_embed = await self._build_embed()
            await i.response.edit_message(embed=new_embed, view=self)

        time_select.callback = time_cb
        self.add_item(time_select)

        # 設定 Rating & 題目數按鈕（row=2）
        settings_b = ui.Button(label="⚙️ 設定 Rating 與題目數", style=discord.ButtonStyle.primary, row=2)

        async def settings_cb(i: discord.Interaction):
            modal = DuelSettingsModal(self)
            await i.response.send_modal(modal)

        settings_b.callback = settings_cb
        self.add_item(settings_b)

        # 發起挑戰按鈕（row=2）
        start_b = ui.Button(label="⚔️ 發起挑戰", style=discord.ButtonStyle.success, row=2)

        async def start_cb(i: discord.Interaction):
            # 檢查 CF 連結
            challenger_cf = linkcf.linked(str(self.challenger.id))
            opponent_cf = linkcf.linked(str(self.opponent.id))

            if not challenger_cf:
                await i.response.send_message(
                    f"⚠️ 你還沒連結 Codeforces！使用 `/cnttocf <your_handle>` 連結後再試",
                    ephemeral=True
                )
                return

            if not opponent_cf:
                await i.response.send_message(
                    f"⚠️ {self.opponent.mention} 還沒連結 Codeforces",
                    ephemeral=True
                )
                return

            # 抽題
            duel_info, err = duel_mod.start_duel(
                challenger_cf=challenger_cf,
                challenger_dc=self.challenger_name,
                opponent_cf=opponent_cf,
                opponent_dc=self.opponent_name,
                mnrating=self.min_rating,
                mxrating=self.max_rating,
                num=self.num_problems,
                tags=self.selected_tags if self.selected_tags else None,
                duration_minutes=self.duration_minutes
            )

            if err:
                await i.response.send_message(f"⚠️ {err}", ephemeral=True)
                return

            # 存入 pending，2 分鐘後過期
            data = duel_mod._load_duel()
            challenge_key = f"{self.challenger_name}_vs_{self.opponent_name}"
            data["pending"][challenge_key] = {
                **duel_info,
                "expires_at": time.time() + 120,  # 2 分鐘
                "tags": self.selected_tags,
                "min_rating": self.min_rating,
                "max_rating": self.max_rating,
                "duration_minutes": self.duration_minutes,
                "num_problems": self.num_problems,
                "challenger_mention": self.challenger.mention,
                "opponent_mention": self.opponent.mention,
                "challenger_id": str(self.challenger.id),
                "opponent_id": str(self.opponent.id)
            }
            duel_mod._save_duel(data)

            # 發送挑戰訊息到頻道（@兩人）
            tags_str = f"｜🏷️ {', '.join(self.selected_tags)}" if self.selected_tags else ""

            embed = discord.Embed(
                title="⚔️ Duel 挑戰！",
                description=(
                    f"{self.challenger.mention} 向 {self.opponent.mention} 發起 Duel 挑戰！\n\n"
                    f"📝 **題目數量：** {self.num_problems} 題\n"
                    f"⏱️ **時間限制：** {self.duration_minutes} 分鐘\n"
                    f"📊 Rating：~{duel_info['avg_rating']}{tags_str}\n\n"
                    f"⏳ 等待對手接受...（2 分鐘後自動取消）"
                ),
                color=0xFF4500
            )
            embed.set_footer(text=f"🤖 由 {self.challenger_name} 發起")

            view = DuelAcceptView(self.challenger_name, self.opponent_name, duel_info, challenge_key)
            await i.response.send_message(embed=embed, view=view)
            self.stop()

        start_b.callback = start_cb
        self.add_item(start_b)

        # 重置按鈕（row=3）
        reset_b = ui.Button(label="🔄 重置", style=discord.ButtonStyle.danger, row=3)

        async def reset_cb(i: discord.Interaction):
            self.min_rating = 800
            self.max_rating = 1600
            self.num_problems = 3
            self.duration_minutes = 10
            self.selected_tags = []
            self._setup_ui()
            new_embed = await self._build_embed()
            await i.response.edit_message(embed=new_embed, view=self)

        reset_b.callback = reset_cb
        self.add_item(reset_b)

    async def _build_embed(self) -> discord.Embed:
        tags_str = ", ".join(self.selected_tags) if self.selected_tags else "未設定"
        embed = discord.Embed(
            title="⚔️ 發起 Duel 挑戰",
            description=(
                f"**對手：** {self.opponent.mention}\n\n"
                f"**當前設定：**\n"
                f"• 📝 題目數量：{self.num_problems} 題（1-7）\n"
                f"• ⏱️ 時間限制：{self.duration_minutes} 分鐘\n"
                f"• 📊 Rating：{self.min_rating}-{self.max_rating}\n"
                f"• 🏷️ Tags：{tags_str}\n\n"
                f"**步驟：**\n"
                f"1️⃣ 選擇時間限制\n"
                f"2️⃣ （可選）選擇 Tags\n"
                f"3️⃣ 點「⚙️」設定 Rating 和題目數量\n"
                f"4️⃣ 點「⚔️ 發起挑戰」"
            ),
            color=0xFF4500
        )
        if linkcf.linked(str(self.challenger.id)):
            embed.set_footer(text=f"已連結：{linkcf.linked(str(self.challenger.id))} ✅")
        else:
            embed.set_footer(text="⚠️ 未連結 Codeforces")
        return embed


class DuelSettingsModal(ui.Modal, title="設定 Rating 與題目數量"):
    """設定 Duel 的 Rating 範圍和題目數量"""

    min_rating = ui.TextInput(
        label="最小 Rating",
        placeholder="例：800",
        default="800",
        required=True,
        min_length=3,
        max_length=4
    )
    max_rating = ui.TextInput(
        label="最大 Rating",
        placeholder="例：1600",
        default="1600",
        required=True,
        min_length=3,
        max_length=4
    )
    num_problems = ui.TextInput(
        label="題目數量（1-7）",
        placeholder="例：3",
        default="3",
        required=True,
        min_length=1,
        max_length=1
    )

    def __init__(self, view: DuelChallengeView):
        super().__init__()
        self.callback_view = view

    async def on_submit(self, interaction: discord.Interaction):
        try:
            mn = int(self.min_rating.value)
            mx = int(self.max_rating.value)
            num = int(self.num_problems.value)

            if mn > mx:
                await interaction.response.send_message(
                    "⚠️ 最小不能大於最大",
                    ephemeral=True
                )
                return
            if mn < 800 or mx > 3500:
                await interaction.response.send_message(
                    "⚠️ Rating 範圍需在 800-3500",
                    ephemeral=True
                )
                return
            if num < 1 or num > 7:
                await interaction.response.send_message(
                    "⚠️ 題目數量需在 1-7 題",
                    ephemeral=True
                )
                return

            self.callback_view.min_rating = mn
            self.callback_view.max_rating = mx
            self.callback_view.num_problems = num
            self.callback_view._setup_ui()
            new_embed = await self.callback_view._build_embed()
            await interaction.response.edit_message(embed=new_embed, view=self.callback_view)
        except ValueError:
            await interaction.response.send_message(
                "⚠️ 請輸入有效數字",
                ephemeral=True
            )


class DuelAcceptView(ui.View):
    """Duel 接受挑戰視圖"""

    def __init__(self, challenger_name: str, opponent_name: str, duel_info: dict, challenge_key: str):
        super().__init__(timeout=None)
        self.challenger_name = challenger_name
        self.opponent_name = opponent_name
        self.duel_info = duel_info
        self.challenge_key = challenge_key
        self._responded = False

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.name != self.opponent_name:
            await interaction.response.send_message("⚠️ 這不是你的挑戰！", ephemeral=True)
            return False
        return True

    @ui.button(label="✅ 接受挑戰", style=discord.ButtonStyle.success)
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self._responded:
            await interaction.response.send_message("⚠️ 已經有人回應了！", ephemeral=True)
            return
        self._responded = True
        self.stop()

        # === 重新計算時間：從現在開始計時 ===
        current_time = time.time()
        duration_minutes = self.duel_info.get("duration_minutes", 10)
        self.duel_info["start_time"] = current_time
        self.duel_info["end_time"] = current_time + duration_minutes * 60

        data = duel_mod._load_duel()
        data["pending"].pop(self.challenge_key, None)

        # 直接存入 active
        data["active"][self.challenge_key] = self.duel_info
        duel_mod._save_duel(data)

        problems = self.duel_info.get("problems", [])

        # 計算剩餘時間
        remaining_seconds = int(self.duel_info["end_time"] - current_time)
        remaining_mins = remaining_seconds // 60
        remaining_secs = remaining_seconds % 60

        embed = discord.Embed(
            title="⚔️ Duel 進行中！",
            description=(
                f"**{self.challenger_name}** vs **{self.opponent_name}**\n\n"
                f"📝 **題目：** {len(problems)} 題\n"
                f"⏱️ **剩餘時間：** {remaining_mins} 分 {remaining_secs} 秒\n"
                f"🏆 比賽結束後公佈正確題目（不看答案）\n\n"
                f"📊 **記分板**（Bot 會自動更新）"
            ),
            color=0xFF4500
        )

        # 顯示雙方初始分數
        embed.add_field(
            name=f"👤 {self.challenger_name}",
            value="⬜ × " + str(len(problems)),
            inline=True
        )
        embed.add_field(
            name=f"👤 {self.opponent_name}",
            value="⬜ × " + str(len(problems)),
            inline=True
        )

        # 顯示題目連結（新題目，不顯示名稱）
        problem_links = "\n".join([p["url"] for p in problems])
        embed.add_field(
            name="📋 題目列表",
            value=problem_links,
            inline=False
        )

        embed.set_footer(text=f"🤖 Bot 每 30 秒更新記分板")

        for child in self.children:
            child.disabled = True

        # 保存訊息 ID 到 duel_info 以便後續更新
        self.duel_info["update_message_id"] = interaction.message.id
        self.duel_info["update_channel_id"] = interaction.channel.id
        data = duel_mod._load_duel()
        if self.challenge_key in data["active"]:
            data["active"][self.challenge_key] = self.duel_info
            duel_mod._save_duel(data)

        await interaction.response.edit_message(embed=embed, view=self)
        await interaction.followup.send(
            f"{self.challenger_name}、{self.opponent_name} 加油！💪\n"
            f"時間結束後 Bot 會公佈題目名稱，比較解題數量！",
            ephemeral=True
        )


def build_duel_score_embed(duel_info: dict, c_solves: dict, o_solves: dict, remaining_seconds: int) -> discord.Embed:
    """建立動態記分板 embed，顯示誰在什麼時候解了哪題"""
    problems = duel_info.get("problems", [])
    num_problems = len(problems)
    c_count = len(c_solves)
    o_count = len(o_solves)
    start_time = duel_info.get("start_time", time.time())
    duration = duel_info.get("duration_minutes", 10)

    # 計算剩餘時間
    if remaining_seconds <= 0:
        time_str = "時間到！"
    else:
        mins = remaining_seconds // 60
        secs = remaining_seconds % 60
        time_str = f"{mins} 分 {secs} 秒"

    embed = discord.Embed(
        title="⚔️ Duel 進行中！",
        description=(
            f"**{duel_info['challenger_dc']}** vs **{duel_info['opponent_dc']}**\n\n"
            f"📝 **題目：** {num_problems} 題\n"
            f"⏱️ **剩餘時間：** {time_str}"
        ),
        color=0xFF4500
    )

    # 將 UNIX timestamp 轉換為相對時間（比賽開始後過了多久）
    def unix_to_relative(unix_time: int) -> str:
        if unix_time < start_time:
            return "?"
        elapsed = unix_time - int(start_time)
        mins = elapsed // 60
        secs = elapsed % 60
        return f"{mins:02d}:{secs:02d}"

    # 建立 challenger 的解題狀態
    c_lines = [f"**{duel_info['challenger_dc']}**（{c_count}/{num_problems}）"]
    for p in problems:
        idx = p["index"]
        if idx in c_solves:
            t = unix_to_relative(c_solves[idx])
            c_lines.append(f"✅ {idx} - {t}")
        else:
            c_lines.append(f"⬜ {idx}")
    c_status = "\n".join(c_lines)

    # 建立 opponent 的解題狀態
    o_lines = [f"**{duel_info['opponent_dc']}**（{o_count}/{num_problems}）"]
    for p in problems:
        idx = p["index"]
        if idx in o_solves:
            t = unix_to_relative(o_solves[idx])
            o_lines.append(f"✅ {idx} - {t}")
        else:
            o_lines.append(f"⬜ {idx}")
    o_status = "\n".join(o_lines)

    embed.add_field(
        name="👤Challenger",
        value=c_status,
        inline=True
    )
    embed.add_field(
        name="👤Opponent",
        value=o_status,
        inline=True
    )

    # 顯示題目連結
    problem_links = "\n".join([f"{p['index']}: {p['url']}" for p in problems])
    embed.add_field(
        name="📋 題目連結",
        value=problem_links,
        inline=False
    )

    embed.set_footer(text="🤖 Bot 會持續更新記分板")
    return embed


def build_duel_result_embed(duel_info: dict, result: dict) -> discord.Embed:
    """建立 Duel 結果 embed（公佈題目名稱）"""
    problems = duel_info.get("problems", [])
    is_tie = result.get("winner") is None

    if is_tie:
        title = "🤝 Duel 平手！"
        color = 0x808080
    else:
        title = "🏆 Duel 結束！"
        color = 0xFFD700

    embed = discord.Embed(
        title=title,
        description=(
            f"**{duel_info['challenger_dc']}** vs **{duel_info['opponent_dc']}**\n"
        ),
        color=color
    )

    # 顯示分數
    if is_tie:
        c_count = result.get("c_count", 0)
        o_count = result.get("o_count", 0)
        embed.description += f"\n🤝 雙方都解了 {c_count} / {len(problems)} 題"
    else:
        winner = result.get("winner")
        winner_count = result.get("winner_count", 0)
        loser = result.get("loser")
        loser_count = result.get("loser_count", 0)
        embed.description += f"\n🥇 **{winner}** 勝利！（{winner_count} 題）\n🥈 **{loser}**（{loser_count} 題）"

    # 公佈所有題目（顯示名稱）
    for i, p in enumerate(problems, 1):
        embed.add_field(
            name=f"題目 {i}",
            value=f"[{p['name']}]({p['url']}) ⭐{p['rating']}",
            inline=True
        )

    embed.set_footer(text="🤖 比賽結束 | 感謝參與！")
    return embed


# ============================================================
# 角色 Select Menu 系統 (新)
# ============================================================

def load_persistent_selects():
    """載入持久化身份組選單設定"""
    if not os.path.exists("role_selects.json"):
        return {"menus": {}}
    with open("role_selects.json", "r", encoding="utf-8") as f:
        return json.load(f)


def save_persistent_selects(data):
    """儲存持久化身份組選單設定"""
    with open("role_selects.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def chunk_roles_by_letter(roles: list, max_per_page: int = 25) -> list:
    """
    將身份組按字母分組，每組最多 max_per_page 個
    返回 [(letter, [roles]), ...]
    """
    if not roles:
        return []

    # 按名稱排序
    sorted_roles = sorted(roles, key=lambda r: r.name.lower())

    if len(sorted_roles) <= max_per_page:
        return [("A~Z", sorted_roles)]

    # 按首字母分組
    chunks = []
    chunk = []
    current_letter = None

    for role in sorted_roles:
        if not role.name:
            continue
        first_letter = role.name[0].upper()

        # 檢查是否需要換組
        if current_letter is not None and first_letter != current_letter:
            # 換字母了
            if len(chunk) >= 20:  # 接近上限，先儲存
                chunks.append((current_letter, chunk))
                chunk = []
            else:
                # 如果新字母與舊字母在同一組可以容納，保持同一組
                # 檢查 chunk 是否快要滿了
                if len(chunk) >= max_per_page:
                    chunks.append((current_letter, chunk))
                    chunk = []

        chunk.append(role)
        current_letter = first_letter

    if chunk:
        chunks.append((current_letter or "?", chunk))

    # 如果分太多組，合併小的組
    while len(chunks) > 3 and any(len(c[1]) < 5 for c in chunks):
        # 找到最小的組
        min_idx = min(range(len(chunks)), key=lambda i: len(chunks[i][1]))
        if min_idx > 0:
            # 與前一組合併
            chunks[min_idx - 1] = (chunks[min_idx - 1][0], chunks[min_idx - 1][1] + chunks[min_idx][1])
            chunks.pop(min_idx)
        elif len(chunks) > 1:
            # 與後一組合併
            chunks[min_idx + 1] = (chunks[min_idx + 1][0], chunks[min_idx][1] + chunks[min_idx + 1][1])
            chunks.pop(min_idx)

    # 更新字母標記
    final_chunks = []
    for i, (letter, grp) in enumerate(chunks):
        if len(chunks) == 1:
            final_chunks.append(("A~Z", grp))
        else:
            final_chunks.append((letter, grp))
    return final_chunks


class RoleSelectBuilderView(ui.View):
    """管理員建立/管理身份組選單"""

    def __init__(self, bot: Bot, guild: discord.Guild):
        super().__init__(timeout=300)
        self.bot = bot
        self.guild = guild
        self.selected_roles = []
        self.menu_title = "自選身份組"
        self.menu_description = "選擇你想要的身份組"
        self.target_channel = None
        self.role_page = 0
        self.channel_page = 0
        self.role_options = []
        self.all_channels = sorted(guild.text_channels, key=lambda c: c.position)

        # 建立身份組選擇（帶分頁）
        self._build_role_picker()

    def _get_role_options(self):
        return [
            discord.SelectOption(label=role.name, value=str(role.id), emoji="👤")
            for role in self.guild.roles
            if role.name != "@everyone"
            and not role.managed
            and not role.name.startswith("🎨 ")
        ]

    def _build_role_picker(self):
        """建立身份組和頻道選擇（都帶分頁）"""
        all_options = self._get_role_options()
        ITEMS_PER_PAGE = 25
        role_total_pages = max(1, (len(all_options) + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE)
        self.role_options = all_options

        # 頻道分頁
        channel_total = len(self.all_channels)
        channel_total_pages = max(1, (channel_total + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE)

        self.clear_items()

        # ============ 頻道選擇（row=0）============
        ch_start = self.channel_page * ITEMS_PER_PAGE
        ch_end = min(ch_start + ITEMS_PER_PAGE, channel_total)
        ch_options = [
            discord.SelectOption(label=ch.name, value=str(ch.id), emoji="📝")
            for ch in self.all_channels[ch_start:ch_end]
        ]
        channel_select = ui.Select(
            placeholder=f"📢 發送頻道（{self.channel_page + 1}/{channel_total_pages}，共{channel_total}個）",
            options=ch_options,
            row=0
        )
        async def channel_cb(i: discord.Interaction):
            if channel_select.values:
                channel_id = int(channel_select.values[0])
                self.target_channel = self.guild.get_channel(channel_id)
                await i.response.send_message(f"✅ 已選擇頻道：<#{channel_id}>", ephemeral=True)
        channel_select.callback = channel_cb
        self.add_item(channel_select)

        # 頻道分頁按鈕
        if channel_total_pages > 1:
            ch_prev_b = ui.Button(label="◀", row=0, disabled=self.channel_page == 0)
            ch_info_b = ui.Button(label=f"{self.channel_page + 1}/{channel_total_pages}", row=0, disabled=True)
            ch_next_b = ui.Button(label="▶", row=0, disabled=self.channel_page >= channel_total_pages - 1)

            async def ch_prev_cb(i: discord.Interaction):
                self.channel_page -= 1
                self._build_role_picker()
                await i.response.edit_message(view=self)

            async def ch_next_cb(i: discord.Interaction):
                self.channel_page += 1
                self._build_role_picker()
                await i.response.edit_message(view=self)

            ch_prev_b.callback = ch_prev_cb
            ch_next_b.callback = ch_next_cb
            self.add_item(ch_prev_b)
            self.add_item(ch_info_b)
            self.add_item(ch_next_b)

        # ============ 身份組選擇（row=1）============
        role_start = self.role_page * ITEMS_PER_PAGE
        role_end = min(role_start + ITEMS_PER_PAGE, len(all_options))
        role_opts = all_options[role_start:role_end]

        role_select = ui.Select(
            placeholder=f"選擇身份組 ({self.role_page + 1}/{role_total_pages}，共{len(all_options)}個)",
            options=role_opts,
            row=1
        )

        async def role_cb(i: discord.Interaction):
            already_chosen = [str(r.id) for r in self.selected_roles]
            newly_selected = [rid for rid in role_select.values if rid not in already_chosen]
            for rid in newly_selected:
                role = self.guild.get_role(int(rid))
                if role and role not in self.selected_roles:
                    self.selected_roles.append(role)
            await i.response.send_message(
                f"✅ 已選擇 {len(self.selected_roles)} 個身份組",
                ephemeral=True
            )

        role_select.callback = role_cb
        self.add_item(role_select)

        # 身份組分頁按鈕（row=2）
        if role_total_pages > 1:
            role_prev_b = ui.Button(label="◀", row=2, disabled=self.role_page == 0)
            role_info_b = ui.Button(label=f"{self.role_page + 1}/{role_total_pages}", row=2, disabled=True)
            role_next_b = ui.Button(label="▶", row=2, disabled=self.role_page >= role_total_pages - 1)

            async def role_prev_cb(i: discord.Interaction):
                self.role_page -= 1
                self._build_role_picker()
                await i.response.edit_message(view=self)

            async def role_next_cb(i: discord.Interaction):
                self.role_page += 1
                self._build_role_picker()
                await i.response.edit_message(view=self)

            role_prev_b.callback = role_prev_cb
            role_next_b.callback = role_next_cb
            self.add_item(role_prev_b)
            self.add_item(role_info_b)
            self.add_item(role_next_b)

        # ============ 其他按鈕（row=3）============
        title_b = ui.Button(label="✏️ 設定標題", style=discord.ButtonStyle.primary, row=3)
        async def title_cb(i: discord.Interaction):
            modal = RoleSelectTitleModal(self)
            await i.response.send_modal(modal)
        title_b.callback = title_cb
        self.add_item(title_b)

        send_b = ui.Button(label="📨 發送選單", style=discord.ButtonStyle.success, row=3)
        async def send_cb(i: discord.Interaction):
            if not self.selected_roles:
                await i.response.send_message("⚠️ 請先選擇身份組", ephemeral=True)
                return
            channel = self.target_channel if self.target_channel else i.channel
            embed = discord.Embed(
                title=self.menu_title,
                description=self.menu_description,
                color=0x3489da
            )
            embed.set_footer(text="👇 點擊下方選擇身份組 👇")
            view = build_user_role_select(self.selected_roles, self.guild)
            msg = await channel.send(embed=embed, view=view)

            # 儲存
            data = load_persistent_selects()
            data["menus"][str(msg.id)] = {
                "title": self.menu_title,
                "description": self.menu_description,
                "guild_id": self.guild.id,
                "channel_id": channel.id,
                "roles": {str(r.id): r.name for r in self.selected_roles}
            }
            save_persistent_selects(data)

            await i.response.send_message(f"✅ 選單已發送至 <#{channel.id}>", ephemeral=True)
            self.stop()
        send_b.callback = send_cb
        self.add_item(send_b)

        reset_b = ui.Button(label="🔄 重置", style=discord.ButtonStyle.danger, row=3)
        async def reset_cb(i: discord.Interaction):
            self.selected_roles = []
            self.channel_page = 0
            self.role_page = 0
            self._build_role_picker()
            await i.response.edit_message(view=self)

        reset_b.callback = reset_cb
        self.add_item(reset_b)


class RoleSelectView(ui.View):
    """使用者選擇身份組的視圖（用於發送的選單）"""

    def __init__(self, roles: list):
        super().__init__(timeout=None)  # persistent view
        self.roles = roles
        self._build_selects()

    def _build_selects(self):
        """根據角色數量構建 Select（自動分頁）"""
        chunks = chunk_roles_by_letter(self.roles, max_per_page=25)

        for i, (letter, role_group) in enumerate(chunks):
            # 創建封閉的 callback 函數
            role_group_ids = [str(r.id) for r in role_group]

            select = ui.Select(
                placeholder=f"選擇身份組 {letter} ({len(role_group)}個)",
                options=[
                    discord.SelectOption(label=r.name, value=str(r.id), emoji="👤")
                    for r in role_group
                ],
                min_values=0,
                max_values=len(role_group),
                row=i
            )

            async def callback(interaction: discord.Interaction, select=select, group_ids=role_group_ids):
                member = interaction.user
                guild = interaction.guild

                if not guild:
                    await interaction.response.send_message("⚠️ 發生錯誤", ephemeral=True)
                    return

                # 只新增已選的身份組（不移除）
                results = []
                for rid in group_ids:
                    role = guild.get_role(int(rid))
                    if not role:
                        continue

                    role_id_str = str(role.id)
                    is_selected = role_id_str in select.values

                    if is_selected and role not in member.roles:
                        try:
                            await member.add_roles(role)
                            results.append(f"✅ {role.name}")
                        except discord.Forbidden:
                            results.append(f"❌ {role.name} - 無權限")
                        except Exception as e:
                            results.append(f"❌ {role.name} - {e}")

                if results:
                    await interaction.response.send_message(
                        f"✅ 已獲得 {len(results)} 個身份組",
                        ephemeral=True
                    )
                else:
                    await interaction.response.defer()

            select.callback = callback
            self.add_item(select)


def build_user_role_select(roles: list, guild: discord.Guild):
    """為使用者建立內嵌身份組選擇視圖"""
    ITEMS_PER_PAGE = 25
    total_pages = max(1, (len(roles) + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE)

    role_options = [
        discord.SelectOption(label=r.name, value=str(r.id), emoji="👤")
        for r in sorted(roles, key=lambda r: r.name.lower())
    ]

    class UserRoleSelectView(ui.View):
        def __init__(view_self):
            super().__init__(timeout=180)
            view_self.current_page = 0
            view_self.selected = set()
            view_self.roles = roles
            view_self.guild = guild
            view_self._rebuild()

        def _rebuild(view_self):
            view_self.clear_items()
            start = view_self.current_page * ITEMS_PER_PAGE
            end = min(start + ITEMS_PER_PAGE, len(role_options))
            page_opts = role_options[start:end]

            # 取得當前用戶已選的身份組 ID
            try:
                member = view_self.guild.get_member(view_self.guild._state.view_handler.user.id) if hasattr(view_self.guild, '_state') else None
            except:
                member = None

            current_selected = []
            if member:
                current_selected = [str(r.id) for r in member.roles]

            select = ui.Select(
                placeholder=f"選擇身份組 ({view_self.current_page + 1}/{total_pages})",
                options=page_opts,
                min_values=0,
                max_values=len(page_opts),
                row=0
            )

            async def select_cb(i: discord.Interaction):
                member = i.user
                current_role_ids = [str(r.id) for r in member.roles]

                # 檢查每個選項
                results_add = []
                results_remove = []

                for option in page_opts:
                    role = guild.get_role(int(option.value))
                    if not role:
                        continue

                    is_now_selected = option.value in select.values
                    was_selected = option.value in current_role_ids

                    if is_now_selected and not was_selected:
                        # 新增
                        try:
                            await member.add_roles(role)
                            results_add.append(role.name)
                        except Exception as e:
                            print(f"[roleselect] 新增失敗 {role.name}: {e}")
                    elif not is_now_selected and was_selected:
                        # 移除
                        try:
                            await member.remove_roles(role)
                            results_remove.append(role.name)
                        except Exception as e:
                            print(f"[roleselect] 移除失敗 {role.name}: {e}")

                # 發送結果回饋
                if results_add or results_remove:
                    msg_parts = []
                    if results_add:
                        msg_parts.append(f"✅ 已獲得：{', '.join(results_add)}")
                    if results_remove:
                        msg_parts.append(f"🚫 已移除：{', '.join(results_remove)}")
                    await i.response.send_message('\n'.join(msg_parts), ephemeral=True)
                else:
                    await i.response.defer()

            select.callback = select_cb
            view_self.add_item(select)

            # 分頁按鈕
            if total_pages > 1:
                prev_b = ui.Button(label="◀", row=1, disabled=view_self.current_page == 0)
                info_b = ui.Button(label=f"{view_self.current_page + 1}/{total_pages}", row=1, disabled=True)
                next_b = ui.Button(label="▶", row=1, disabled=view_self.current_page >= total_pages - 1)

                async def prev_cb(i: discord.Interaction):
                    view_self.current_page -= 1
                    view_self._rebuild()
                    await i.response.edit_message(view=view_self)

                async def next_cb(i: discord.Interaction):
                    view_self.current_page += 1
                    view_self._rebuild()
                    await i.response.edit_message(view=view_self)

                prev_b.callback = prev_cb
                next_b.callback = next_cb
                view_self.add_item(prev_b)
                view_self.add_item(info_b)
                view_self.add_item(next_b)

            # 關閉按鈕
            close_b = ui.Button(label="❌ 關閉", style=discord.ButtonStyle.secondary, row=2)
            async def close_cb(i: discord.Interaction):
                await i.response.edit_message(
                    embed=discord.Embed(
                        title="已關閉",
                        description="使用 /roleselect 再次開啟",
                        color=0x808080
                    ),
                    view=None
                )
            close_b.callback = close_cb
            view_self.add_item(close_b)

    return UserRoleSelectView()


class RoleSelectTitleModal(ui.Modal, title="設定選單標題"):
    """設定身份組選單的標題與說明"""

    def __init__(self, builder_view: RoleSelectBuilderView):
        super().__init__()
        self.builder_view = builder_view

        # 動態建立 TextInput 以支援預設值
        self.title_input = ui.TextInput(
            label="標題",
            placeholder="例：自選身份組",
            default=builder_view.menu_title,
            required=True,
            max_length=100
        )
        self.description_input = ui.TextInput(
            label="說明",
            placeholder="例：選擇你想要的身份組",
            default=builder_view.menu_description,
            required=True,
            max_length=500
        )

        self.add_item(self.title_input)
        self.add_item(self.description_input)

    async def on_submit(self, interaction: discord.Interaction):
        self.builder_view.menu_title = self.title_input.value
        self.builder_view.menu_description = self.description_input.value
        await interaction.response.send_message(
            f"✅ 已設定！\n標題：{self.title_input.value}\n說明：{self.description_input.value}",
            ephemeral=True
        )


# ============================================================
# 測試 / 臨時用
# ============================================================

class TempSelectView(ui.View):
    """測試用 Select Menu"""

    def __init__(self, options: list):
        super().__init__(timeout=None)
        select = ui.Select(
            placeholder="選擇身份組（可多選）",
            options=options,
            min_values=0,
            max_values=len(options)
        )
        select.callback = self._callback
        self.add_item(select)

    async def _callback(self, interaction: discord.Interaction):
        member = interaction.user
        guild = interaction.guild
        selected = self.children[0].values

        results = []
        for role_id in selected:
            role = guild.get_role(int(role_id))
            if role and role not in member.roles:
                try:
                    await member.add_roles(role)
                    results.append(f"✅ {role.name}")
                except:
                    results.append(f"❌ {role.name}")

        if results:
            await interaction.response.send_message("\n".join(results), ephemeral=True)
        else:
            await interaction.response.defer()