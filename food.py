"""
美食搜尋功能模組
使用 OpenStreetMap 的 Nominatim 和 Overpass API 來搜尋附近美食
"""
import requests
import random
from typing import Optional

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