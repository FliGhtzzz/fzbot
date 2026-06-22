"""
美食搜尋功能模組
使用 OpenStreetMap 的 Nominatim 和 Overpass API 來搜尋附近美食
"""
import requests
import random
from typing import Optional, List, Tuple
import math
import os
import io

try:
    import matplotlib
    matplotlib.use('Agg')  # Non-interactive backend
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False

# Nominatim API（地理編碼）
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
# Overpass API（搜尋附近地點）
OVERPASS_URL = "https://overpass-api.de/api/interpreter"


def geocode(location: str) -> Optional[dict]:
    """
    將地點名稱轉換為座標

    Args:
        location: 地點名稱（如 "台北市"、"新竹科學園區"）

    Returns:
        包含 lat, lon, display_name 的字典，失敗則返回 None
    """
    params = {
        "q": location,
        "format": "json",
        "limit": 1,
        "addressdetails": 1
    }
    headers = {
        "User-Agent": "FZBOT/1.0 (Discord Bot)"
    }

    try:
        resp = requests.get(NOMINATIM_URL, params=params, headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        if not data:
            return None

        return {
            "lat": float(data[0]["lat"]),
            "lon": float(data[0]["lon"]),
            "display_name": data[0].get("display_name", location)
        }
    except Exception as e:
        print(f"[food] Geocode error: {e}")
        return None


def search_nearby_food(lat: float, lon: float, radius: int = 1000, limit: int = 50) -> list:
    """
    在指定座標附近搜尋美食地點

    Args:
        lat: 緯度
        lon: 經度
        radius: 搜尋半徑（公尺），預設 1000m
        limit: 最多回傳數量

    Returns:
        美食地點列表
    """
    # Overpass QL 查詢
    query = f"""
    [out:json][timeout:25];
    (
      node["amenity"~"restaurant|fast_food|cafe|bar|bakery"](around:{radius},{lat},{lon});
      way["amenity"~"restaurant|fast_food|cafe"](around:{radius},{lat},{lon});
    );
    out center;
    """

    headers = {
        "User-Agent": "FZBOT/1.0 (Discord Bot)"
    }

    try:
        resp = requests.get(OVERPASS_URL, params={"data": query}, headers=headers, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        places = []
        for element in data.get("elements", []):
            # 取得座標
            if element["type"] == "node":
                place_lat = element.get("lat")
                place_lon = element.get("lon")
            elif element["type"] == "way" and "center" in element:
                place_lat = element["center"].get("lat")
                place_lon = element["center"].get("lon")
            else:
                continue

            if not place_lat or not place_lon:
                continue

            tags = element.get("tags", {})

            # 取得名稱
            name = tags.get("name", tags.get("name:zh", "（無名稱）"))
            cuisine = tags.get("cuisine", "")
            addr = tags.get("addr:street", "")
            housenumber = tags.get("addr:housenumber", "")
            address = f"{addr} {housenumber}".strip() or "（無地址）"
            amenity = tags.get("amenity", "")
            wheelchair = tags.get("wheelchair", "")

            # 美化類型
            amenity_display = {
                "restaurant": "🍽️ 餐廳",
                "fast_food": "🍔 速食",
                "cafe": "☕ 咖啡廳",
                "bar": "🍺 酒吧",
                "bakery": "🥐 麵包店"
            }.get(amenity, "🍴 一般餐飲")

            places.append({
                "name": name,
                "lat": place_lat,
                "lon": place_lon,
                "cuisine": cuisine,
                "address": address,
                "type": amenity_display,
                "amenity": amenity,
                "wheelchair": wheelchair,
                "tags": tags
            })

        # 隨機排列並限制數量
        random.shuffle(places)
        return places[:limit]

    except Exception as e:
        print(f"[food] Search error: {e}")
        return []


def search_food_by_location(location: str, radius: int = 1000, limit: int = 30) -> dict:
    """
    根據地點名稱搜尋附近美食

    Args:
        location: 地點名稱
        radius: 搜尋半徑（公尺）
        limit: 最多回傳數量

    Returns:
        包含 results, location_info 等資訊的字典
    """
    # 先 geocode
    geo = geocode(location)
    if not geo:
        return {
            "success": False,
            "error": f"找不到「{location}」這個地點，請嘗試更精確的描述"
        }

    # 搜尋美食
    places = search_nearby_food(geo["lat"], geo["lon"], radius, limit)

    return {
        "success": True,
        "location_info": geo,
        "places": places,
        "count": len(places)
    }


def pick_random_food(places: list) -> Optional[dict]:
    """
    從美食列表中隨機選擇一個

    Args:
        places: 美食地點列表

    Returns:
        隨機選擇的美食地點，或 None（如果列表為空）
    """
    if not places:
        return None
    return random.choice(places)


def get_openstreetmap_url(lat: float, lon: float) -> str:
    """取得 OpenStreetMap 的 direct link"""
    return f"https://www.openstreetmap.org/?mlat={lat}&mlon={lon}#map=17/{lat}/{lon}"


# 常見美食類型
CUISINE_OPTIONS = [
    ("全部", ""),
    ("台灣美食", "taiwanese,chinese"),
    ("日式料理", "japanese,sushi"),
    ("韓式料理", "korean"),
    ("美式料理", "american,burger"),
    ("義式料理", "italian,pizza,pasta"),
    ("中式料理", "chinese"),
    ("火鍋", "hotpot"),
    ("速食", "fast_food"),
    ("咖啡廳", "cafe"),
    ("甜點", "dessert,ice_cream"),
]


# 半徑選項（公尺）
RADIUS_OPTIONS = [
    ("500m（近）", 500),
    ("1km", 1000),
    ("2km", 2000),
    ("3km", 3000),
]


# 餐廳類型顏色對照
AMENITY_COLORS = {
    "restaurant": "#FF6B35",   # 橙色
    "fast_food": "#FFA500",    # 金色
    "cafe": "#8B4513",          # 棕色
    "bar": "#9B59B6",           # 紫色
    "bakery": "#D4A574",       # 米色
}


def generate_food_map(places: List[dict], location_name: str = "") -> Optional[io.BytesIO]:
    """
    生成美食地圖圖片

    Args:
        places: 餐廳列表
        location_name: 地點名稱

    Returns:
        BytesIO 物件，可用於發送圖片，失敗返回 None
    """
    if not places or not MATPLOTLIB_AVAILABLE:
        return None

    # 取得座標範圍
    lats = [p["lat"] for p in places]
    lons = [p["lon"] for p in places]

    min_lat, max_lat = min(lats), max(lats)
    min_lon, max_lon = min(lons), max(lons)

    # 計算範圍並留一些緩衝
    lat_range = max(max_lat - min_lat, 0.001)
    lon_range = max(max_lon - min_lon, 0.001)

    padding = 0.1
    y_padding = lat_range * padding
    x_padding = lon_range * padding

    # 創建圖形
    fig, ax = plt.subplots(figsize=(14, 10), facecolor='#2C2F33')
    ax.set_facecolor('#1E1E1E')

    # 繪製每個餐廳
    for i, place in enumerate(places):
        lat = place["lat"]
        lon = place["lon"]
        amenity = place.get("amenity", "")
        color = AMENITY_COLORS.get(amenity, "#FFFFFF")

        # 餐廳標記大小
        size = 100

        # 不同類型用不同形狀
        if amenity == "restaurant":
            marker = "o"
        elif amenity == "fast_food":
            marker = "s"
        elif amenity == "cafe":
            marker = "^"
        elif amenity == "bar":
            marker = "D"
        elif amenity == "bakery":
            marker = "p"
        else:
            marker = "o"

        ax.scatter(lon, lat, c=color, s=size, marker=marker, edgecolors='white', linewidths=0.5, zorder=5)

        # 在位置旁顯示名稱（只顯示前8個字）
        name = place["name"]
        if len(name) > 10:
            name = name[:10] + "..."

        # 避免重疊，根據索引偏移文字位置
        offset_x = (i % 3 - 1) * (lon_range * 0.03)
        offset_y = (i % 3 - 1) * (lat_range * 0.03)

        ax.annotate(
            name,
            (lon + offset_x, lat + offset_y),
            fontsize=6,
            color='#CCCCCC',
            alpha=0.8,
            zorder=10
        )

    # 設定座標軸
    ax.set_xlim(min_lon - x_padding, max_lon + x_padding)
    ax.set_ylim(min_lat - y_padding, max_lat + y_padding)
    ax.set_xlabel('經度 (Longitude)', color='white', fontsize=10)
    ax.set_ylabel('緯度 (Latitude)', color='white', fontsize=10)

    # 標題
    title = f"🍜 附近美食地圖 ({len(places)} 間)"
    if location_name:
        # 簡化地點名稱
        short_name = location_name.split(',')[0] if ',' in location_name else location_name
        title = f"🍜 {short_name} 附近美食地圖 ({len(places)} 間)"

    ax.set_title(title, color='white', fontsize=14, fontweight='bold', pad=15)

    # 網格樣式
    ax.grid(True, alpha=0.2, color='white', linestyle='--')
    ax.tick_params(colors='white')
    for spine in ax.spines.values():
        spine.set_color('#555555')

    # 圖例
    legend_elements = [
        mpatches.Patch(facecolor="#FF6B35", edgecolor='white', label='🍽️ 餐廳'),
        mpatches.Patch(facecolor="#FFA500", edgecolor='white', label='🍔 速食'),
        mpatches.Patch(facecolor="#8B4513", edgecolor='white', label='☕ 咖啡'),
        mpatches.Patch(facecolor="#9B59B6", edgecolor='white', label='🍺 酒吧'),
        mpatches.Patch(facecolor="#D4A574", edgecolor='white', label='🥐 麵包'),
    ]
    ax.legend(handles=legend_elements, loc='upper left', facecolor='#2C2F33',
              edgecolor='white', labelcolor='white', fontsize=9)

    # 調整版面
    plt.tight_layout()

    # 轉換為 BytesIO
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=100, facecolor='#2C2F33', edgecolor='none')
    buf.seek(0)
    plt.close()

    return buf


def generate_food_map_simple(places: List[dict], selected_idx: int = None) -> Optional[io.BytesIO]:
    """
    生成簡化的美食地圖（更緊湊的版本，適合作為 Discord 附件）

    Args:
        places: 餐廳列表
        selected_idx: 被選中的餐廳索引

    Returns:
        BytesIO 物件
    """
    if not places or not MATPLOTLIB_AVAILABLE:
        return None

    lats = [p["lat"] for p in places]
    lons = [p["lon"] for p in places]

    min_lat, max_lat = min(lats), max(lats)
    min_lon, max_lon = min(lons), max(lons)

    lat_range = max(max_lat - min_lat, 0.002)
    lon_range = max(max_lon - min_lon, 0.002)

    # 如果只有一個點，稍微擴大範圍
    if lat_range < 0.002:
        lat_range = 0.005
    if lon_range < 0.002:
        lon_range = 0.005

    fig, ax = plt.subplots(figsize=(12, 9), facecolor='#36393F')
    ax.set_facecolor('#2C2F33')

    # 先畫所有餐廳
    for i, place in enumerate(places):
        lat = place["lat"]
        lon = place["lon"]
        amenity = place.get("amenity", "")
        color = AMENITY_COLORS.get(amenity, "#FFFFFF")

        # 大小
        size = 150 if i == selected_idx else 80
        alpha = 1.0 if i == selected_idx else 0.7

        # 形狀
        markers = {"restaurant": "o", "fast_food": "s", "cafe": "^", "bar": "D", "bakery": "p"}
        marker = markers.get(amenity, "o")

        if i == selected_idx:
            # 選中的用更大、更顯眼的標記
            ax.scatter(lon, lat, c='#FFD700', s=300, marker='*', edgecolors='white', linewidths=2, zorder=10)
            name = place["name"]
            ax.annotate(
                f"★ {name}",
                (lon, lat + lat_range * 0.05),
                fontsize=9,
                color='#FFD700',
                fontweight='bold',
                ha='center',
                zorder=11
            )
        else:
            ax.scatter(lon, lat, c=color, s=size, marker=marker, edgecolors='white', linewidths=0.5, alpha=alpha, zorder=5)

    # 設定範圍
    padding = 0.15
    ax.set_xlim(min_lon - lon_range * padding, max_lon + lon_range * padding)
    ax.set_ylim(min_lat - lat_range * padding, max_lat + lat_range * padding)

    # 隱藏座標軸
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_visible(False)

    # 如果有選中的餐廳，標題顯示它
    title = f"{len(places)} 間美食地點"
    if selected_idx is not None and selected_idx < len(places):
        picked = places[selected_idx]
        title = f"🎲 抽中：{picked['name']}"

    ax.set_title(title, color='white', fontsize=16, fontweight='bold', pad=10)

    # 圖例（在右上角）
    legend_elements = [
        mpatches.Patch(facecolor="#FF6B35", edgecolor='white', label='餐廳'),
        mpatches.Patch(facecolor="#FFA500", edgecolor='white', label='速食'),
        mpatches.Patch(facecolor="#8B4513", edgecolor='white', label='咖啡'),
        mpatches.Patch(facecolor="#9B59B6", edgecolor='white', label='酒吧'),
        mpatches.Patch(facecolor="#D4A574", edgecolor='white', label='麵包'),
    ]
    ax.legend(handles=legend_elements, loc='upper left', facecolor='#36393F',
              edgecolor='#555555', labelcolor='white', fontsize=8, ncol=5,
              bbox_to_anchor=(0, 1.02), framealpha=0.9)

    plt.tight_layout()

    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=100, facecolor='#36393F', edgecolor='none', bbox_inches='tight')
    buf.seek(0)
    plt.close()

    return buf