import requests
import discord
import random

def askprob(mnrating, mxrating, num):
    if num > 20:
        embed = discord.Embed(
            title="Error",
            description="The maximum number of problems that can be requested is 20."
        )
        return embed

    if mxrating <mnrating :
        embed = discord.Embed(
            title="Error",
            description="Maximum rating must be greater than or equal to minimum rating."
        )
        return embed

    url = "https://codeforces.com/api/problemset.problems"

    try:
        response = requests.get(url)
        data = response.json()

        temp = []

        # 遍歷所有題目
        for prob in data['result']['problems']:
            rating = prob.get("rating")
            if rating is not None and mnrating <= rating <= mxrating:
                temp.append({"contestId": prob["contestId"], "index": prob["index"]})

        if len(temp) < num:
            txt = ""
            for i in temp:
                txt += f"https://codeforces.com/problemset/problem/{i['contestId']}/{i['index']}\n"
            embed = discord.Embed(
                title="Error",
                description=f"Not enough problems found within the specified rating range. Only {len(temp)} found:\n{txt}"
            )
            return embed

        rand = random.sample(temp, num)
        txt = ""
        for i in rand:
            txt += f"https://codeforces.com/problemset/problem/{i['contestId']}/{i['index']}\n"

        embed = discord.Embed(title="Here are your problems", description=txt)
        return embed

    except Exception as e:
        embed = discord.Embed(title="Error", description=str(e), color=0x903c3c)
        return embed