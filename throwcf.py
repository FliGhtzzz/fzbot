import requests
import discord
import random
import json
file = open("link.json", "r")
link_data = json.load(file)
file.close()


def askprob(mnrating, mxrating, num, solved, linktxt):
    if num > 50:
        embed = discord.Embed(
            title="Error",
            description="The maximum number of problems that can be requested is 50."
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
        if solved: 
            urlpro = "https://codeforces.com/api/user.status?handle=" + link_data[i]["codeforces.handle"] 
            try:
                responsepro = requests.get(urlpro)
                datapro = responsepro.json()
                
                for prob in data['result']['problems']:
                    rating = prob.get("rating")
                if rating is not None and mnrating <= rating <= mxrating:
                    if solved:
                        for sub in datapro['result']:
                            if not (sub['verdict'] == "OK" and sub['problem']['contestId'] == prob['contestId'] and sub['problem']['index'] == prob['index']):
                                temp.append({"contestId": prob["contestId"], "index": prob["index"]})
                    else:
                        temp.append({"contestId": prob["contestId"], "index": prob["index"]})

            except Exception as e:
                embed = discord.Embed(title="Error", description=str(e)+"", color=0x903c3c)
                return embed
        # 遍歷所有題目

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

        embed = discord.Embed(title="Here are your problems", description=txt+'\n'+linktxt)
        return embed

    except Exception as e:
        embed = discord.Embed(title="Error", description=str(e), color=0x903c3c)
        return embed