import matplotlib.pyplot as plt
import discord
import requests
import datetime
import io
import matplotlib.dates as mdates

def rating(cfhandle): 
    url = f"https://codeforces.com/api/user.rating?handle={cfhandle}"
    
    try:
        response = requests.get(url)
        data = response.json()
        if data["status"] != "OK":
            return f"Error : {data['comment']}"
        
        results = data["result"]
        if not results:
            return "Error : No contest history found."

        x = [datetime.datetime.fromtimestamp(i["ratingUpdateTimeSeconds"]) for i in results]
        y = [i["newRating"] for i in results]
        current_rating = y[-1]
        mx = max(y)

    except Exception as e:
        return f"Error : {e}"

    # 設定畫布比例與背景色
    fig, ax = plt.subplots(figsize=(10, 6), facecolor='#fdfdfd')
    ax.set_facecolor('#fdfdfd')

    # ✅ 精準的 Codeforces 等級顏色
    ranks = [
        (0, 1200, '#CCCCCC'),      # Newbie (Gray)
        (1200, 1400, '#77FF77'),   # Pupil (Green)
        (1400, 1600, '#77DDBB'),   # Specialist (Cyan)
        (1600, 1900, '#AAAAFF'),   # Expert (Blue)
        (1900, 2100, '#FF88FF'),   # Candidate Master (Violet)
        (2100, 2300, '#FFCC88'),   # Master (Orange)
        (2300, 2400, '#FFBB55'),   # International Master (Orange)
        (2400, 2600, '#FF7777'),   # Grandmaster (Red)
        (2600, 3000, '#FF3333'),   # International Grandmaster (Red)
        (3000, 5000, '#AA0000'),   # Legendary Grandmaster (Dark Red)
    ]

    for low, high, color in ranks:
        ax.axhspan(low, high, facecolor=color, alpha=0.8, zorder=0)

    ax.plot(x, y, color='#EDC240', linewidth=1.5, zorder=2)
    ax.scatter(x, y, facecolors='#FFFFFF', edgecolors='#EDC240', s=30, zorder=3)

    ax.set_title(f"Rating of {cfhandle} : {current_rating}", loc='left', fontsize=16, fontweight='bold', color='#445')
    ax.set_ylim(min(y) - 200 if min(y) > 200 else 0, mx + 200)

    ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %Y'))
    plt.xticks(rotation=0)
    ax.grid(True, color='white', linestyle='-', linewidth=1, alpha=0.5)
    for spine in ax.spines.values():
        spine.set_visible(False)

    plt.tight_layout()

    # 存到記憶體
    buffer = io.BytesIO()
    plt.savefig(buffer, format='png', dpi=120)
    buffer.seek(0)
    plt.close()

    return discord.File(fp=buffer, filename=f"{cfhandle}_rating.png")