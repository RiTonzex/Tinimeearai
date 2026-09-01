import math
import requests
from django.core.cache import cache

# WMO Weather interpretation codes (WW) mapping from Open-Meteo API
WMO_WEATHER_MAP = {
    0: {'icon': '☀️', 'desc': 'ท้องฟ้าแจ่มใส'},
    1: {'icon': '🌤️', 'desc': 'แจ่มใสเป็นส่วนใหญ่'},
    2: {'icon': '⛅', 'desc': 'มีเมฆบางส่วน'},
    3: {'icon': '☁️', 'desc': 'มีเมฆมาก'},
    45: {'icon': '🌫️', 'desc': 'มีหมอก'},
    48: {'icon': '🌫️', 'desc': 'มีหมอกน้ำค้าง'},
    51: {'icon': '🌦️', 'desc': 'ฝนละอองเบาๆ'},
    53: {'icon': '🌦️', 'desc': 'ฝนละอองปานกลาง'},
    55: {'icon': '🌧️', 'desc': 'ฝนละอองหนาแน่น'},
    61: {'icon': '🌧️', 'desc': 'ฝนตกเล็กน้อย'},
    63: {'icon': '🌧️', 'desc': 'ฝนตกปานกลาง'},
    65: {'icon': '🌧️', 'desc': 'ฝนตกหนัก'},
    80: {'icon': '🌦️', 'desc': 'ฝนซ่าเล็กน้อย'},
    81: {'icon': '🌧️', 'desc': 'ฝนซ่าปานกลาง'},
    82: {'icon': '⛈️', 'desc': 'ฝนซ่าหนักมาก'},
    95: {'icon': '⛈️', 'desc': 'พายุฝนฟ้าคะนอง'},
    96: {'icon': '⛈️', 'desc': 'พายุฝนฟ้าคะนองร่วมกับลูกเห็บ'},
    99: {'icon': '⛈️', 'desc': 'พายุฝนฟ้าคะนองอย่างรุนแรง'}
}

def calculate_haversine_distance(lat1, lon1, lat2, lon2):
    """
    คำนวณระยะทางตามเส้นโค้งพื้นผิวโลก (Haversine Formula)
    คืนค่าระยะทางเป็นกิโลเมตร (km) ทศนิยม 1 ตำแหน่ง
    """
    try:
        lat1, lon1, lat2, lon2 = float(lat1), float(lon1), float(lat2), float(lon2)
    except (ValueError, TypeError):
        return None

    # รัศมีของโลกเฉลี่ย (Earth Radius = 6,371 km)
    R = 6371.0

    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    distance = R * c

    return round(distance, 1)

def get_live_weather(lat, lon):
    """
    ดึงข้อมูลสภาพอากาศสดและอุณหภูมิ ณ พิกัดละติจูด/ลองจิจูด จาก Open-Meteo REST API (ฟรี ไม่ต้องใช้ API Key)
    ใช้ Django Cache บันทึกผลลัพธ์เป็นเวลา 15 นาที (900 วินาที)
    """
    try:
        lat_f = round(float(lat), 3)
        lon_f = round(float(lon), 3)
    except (ValueError, TypeError):
        return None

    cache_key = f"open_meteo_weather_{lat_f}_{lon_f}"
    cached_weather = cache.get(cache_key)
    if cached_weather:
        return cached_weather

    url = f"https://api.open-meteo.com/v1/forecast?latitude={lat_f}&longitude={lon_f}&current_weather=true"
    try:
        response = requests.get(url, timeout=3)
        if response.status_code == 200:
            data = response.json()
            current = data.get('current_weather', {})
            temp = round(current.get('temperature', 0))
            code = current.get('weathercode', 0)
            
            weather_info = WMO_WEATHER_MAP.get(code, {'icon': '🌡️', 'desc': 'สภาพอากาศสด'})
            result = {
                'temp': temp,
                'description': weather_info['desc'],
                'icon': weather_info['icon'],
                'display': f"{weather_info['icon']} {temp}°C {weather_info['desc']}"
            }
            cache.set(cache_key, result, timeout=900)  # 15 mins cache
            return result
    except Exception:
        pass

    return None
