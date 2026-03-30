# 導入Discord.py模組
import discord
import requests
import linkcf 
import json
import os
import cfrating
import throwcf
# 導入commands指令模組
from discord.ext import commands
from discord.app_commands import Choice

with open("secret.json") as f:
    config = json.load(f)


token = config["token"]


def get_user_info(handle):
    url = "https://codeforces.com/api/user.info"
    params = {
        "handles": handle
    }
    
    try:
        response = requests.get(url, params=params)
        data = response.json()
        
        if data["status"] == "OK":
            user = data["result"][0]
            embed =discord.Embed(title="**" + user.get("handle") + "**", url="https://codeforces.com/profile/" + user.get("handle"), color=0x48c750)
            embed.set_thumbnail(url=user.get("avatar"))
            embed.set_footer(text="Rating: " + str(user.get("rating")) + " \nMax Rating: " + str(user.get("maxRating")) + "\nRank: " + str(user.get("rank")) + "\nMax Rank: " + str(user.get("maxRank")))
            return embed
        else:
            embed = discord.Embed(title="Error", description=data["comment"], color=0x903c3c)
            return embed

    
    except Exception as e:
        embed = discord.Embed(title="Error", description=str(e), color=0x903c3c)
        return embed

# intents是要求機器人的權限
intents = discord.Intents.all()
# command_prefix是前綴符號，可以自由選擇($, #, &...)
bot = commands.Bot(command_prefix = "%", intents = intents)

@bot.event
# 當機器人完成啟動
async def on_ready():
    slash = await bot.tree.sync()
    print(f"目前登入身份 --> {bot.user}")
    print(f"載入 {len(slash)} 個斜線指令")
    FILENAME = "link.json"
    if not os.path.exists(FILENAME):
        with open(FILENAME, "w") as f:
            json.dump({}, f, indent=4)


@bot.tree.command(name="mobai")
async def mobai(interaction: discord.Interaction, usr: discord.User):
    await interaction.response.send_message(f"{usr.mention} orz :place_of_worship:!")

#   @bot.tree.command(name="link")
# async def link(interaction: discord.Interaction):
#     await interaction.response.send_message()


@bot.tree.command(name="searchcf")
async def searchcf(interaction: discord.Interaction, cfhandle: str):
    data = get_user_info(cfhandle)  
    await interaction.response.send_message(embed=data)
    
@bot.tree.command(name="help")
async def cnttocf(interaction: discord.Interaction):
    des={help : "指令列表\n mobai <使用者> : 膜拜<使用者> \n searchcf <Codeforces帳號> : 搜尋Codeforces帳號資訊\n cnttocf <Codeforces帳號> : 將Discord帳號與Codeforces帳號連結(需用vercf驗證) \n vercf : 驗證連結Codeforces帳號"}
    embed=discord.Embed(title="**指令列表**", description=des)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="cnttocf")
async def cnttocf(interaction: discord.Interaction, cfhandle: str):
    data = linkcf.askforcf(interaction.user.name, cfhandle)
    await interaction.response.send_message(data+ "\nUse vercf command to verify your account after submitting code to the specified problem.", ephemeral=True  )

@bot.tree.command(name="vercf")
async def vercf(interaction: discord.Interaction):
    data = linkcf.vertifycf(interaction.user.name)
    await interaction.response.send_message(data, ephemeral=True)
    
@bot.tree.command(name="ratingcf")
async def ratingcf(interaction: discord.Interaction, cfhandle: str):
    await interaction.response.defer()
    data = cfrating.rating(cfhandle)
    if isinstance(data, str):
        await interaction.followup.send(data)
    else:
        await interaction.followup.send(file=data)
    
@bot.tree.command(name="cfprob")
async def cfprob(interaction: discord.Interaction, mnrating : int, mxrating : int, howmany : int):
    await interaction.response.defer()
    data = throwcf.askprob(
        mnrating,
        mxrating,
        howmany
    )
    if isinstance(data, str):
        await interaction.followup.send(embed=data)
    else:
        await interaction.followup.send(embed=data)
bot.run(token)