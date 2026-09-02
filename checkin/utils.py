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


def extract_cloudinary_public_id(asset_or_url):
    """
    ดึง public_id จาก CloudinaryResource, URL หรือสตริง path อย่างถูกต้อง
    """
    if not asset_or_url:
        return None

    raw_val = str(asset_or_url).strip()
    if not raw_val or 'unsplash.com' in raw_val:
        return None

    # กรณีเป็น CloudinaryResource หรือ object ที่มี public_id attribute
    if hasattr(asset_or_url, 'public_id') and asset_or_url.public_id:
        return str(asset_or_url.public_id).strip()

    # กรณีเป็น URL เต็มของ Cloudinary เช่น:
    # https://res.cloudinary.com/<cloud>/image/upload/v1234567/tinimeearai_posts/xyz.jpg
    # https://res.cloudinary.com/<cloud>/image/upload/tinimeearai_posts/xyz
    if 'cloudinary.com' in raw_val:
        import re
        match = re.search(r'/upload/(?:v\d+/)?(.*?)(?:\.[a-zA-Z0-9]+)?$', raw_val)
        if match:
            return match.group(1)

    # กรณีเป็น relative path เช่น tinimeearai_posts/sample_watarun_1 หรือ wtvxbemjx0kvdch8ymm5
    if not raw_val.startswith('http://') and not raw_val.startswith('https://') and not raw_val.startswith('/'):
        import re
        return re.sub(r'\.[a-zA-Z0-9]+$', '', raw_val)

    return None


def delete_cloudinary_asset(asset_or_url):
    """
    ส่งคำสั่งลบไฟล์รูปภาพออกจาก Cloudinary โดยอัตโนมัติ (destroy API)
    คืนค่า True หากลบสำเร็จ, False หากไม่สำเร็จหรือไม่ใช่รูปภาพ Cloudinary
    """
    public_id = extract_cloudinary_public_id(asset_or_url)
    if not public_id:
        return False

    try:
        import cloudinary.uploader
        res = cloudinary.uploader.destroy(public_id, invalidate=True)
        return res.get('result') in ('ok', 'not found')
    except Exception:
        return False


def validate_image_file(file_obj, max_size_mb=15):
    """
    ตรวจสอบความปลอดภัยของไฟล์รูปภาพ:
    1. ตรวจสอบนามสกุลไฟล์ที่อนุญาต (jpg, jpeg, png, webp, gif, heic)
    2. ตรวจสอบขนาดไฟล์ไม่ให้เกินขนาดที่กำหนด
    คืนค่า (is_valid: bool, error_message: str | None)
    """
    if not file_obj:
        return False, "ไม่พบไฟล์รูปภาพ"

    ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp', '.gif', '.heic'}
    
    file_name = getattr(file_obj, 'name', '')
    if file_name:
        import os
        _, ext = os.path.splitext(file_name.lower())
        if ext not in ALLOWED_EXTENSIONS:
            return False, f"รูปแบบไฟล์ {ext} ไม่ถูกต้อง กรุณาอัปโหลดไฟล์รูปภาพ (JPG, PNG, WEBP, GIF)"

    file_size = getattr(file_obj, 'size', 0)
    max_bytes = max_size_mb * 1024 * 1024
    if file_size > max_bytes:
        return False, f"ขนาดไฟล์ ({round(file_size / (1024 * 1024), 1)} MB) เกินขีดจำกัดที่กำหนด ({max_size_mb} MB)"

    return True, None


def upload_post_image_dedup(file_obj, folder="tinimeearai_posts"):
    """
    แนวทางที่ 1 (Deduplication ด้วย Content Hash):
    คำนวณ MD5 Hash ของเนื้อหาไฟล์รูปภาพก่อนอัปโหลด เพื่อให้รูปภาพที่เหมือนกัน 100%
    ใช้ public_id เดียวกันเสมอ ไม่สร้างไฟล์ซ้ำบน Cloudinary และประหยัดพื้นที่
    """
    if not file_obj:
        return None

    import os
    from django.conf import settings
    import hashlib

    cloud_key = getattr(settings, 'CLOUDINARY_API_KEY', None) or os.environ.get('CLOUDINARY_API_KEY')
    use_cloud = cloud_key and cloud_key not in ('your_api_key', 'dummy_key', 'dummy_api_key')

    if not use_cloud:
        # หากอยู่ในโหมด Local หรือ Test ให้ส่งไฟล์กลับไปให้ Django FileStorage จัดการตามปกติ
        return file_obj

    try:
        file_bytes = file_obj.read()
        file_hash = hashlib.md5(file_bytes).hexdigest()
        file_obj.seek(0)

        import cloudinary.uploader
        upload_result = cloudinary.uploader.upload(
            file_obj,
            folder=folder,
            public_id=f"post_{file_hash}",
            overwrite=True,
            unique_filename=False,
            resource_type="image"
        )
        return upload_result.get('public_id')
    except Exception:
        file_obj.seek(0)
        return file_obj


def upload_user_avatar(file_obj, user_id, folder="tinimeearai_avatars"):
    """
    แนวทางที่ 2 (ผูกชื่อไฟล์ตาม User ID):
    ตั้งชื่อไฟล์ Avatar ให้ตรงกับรหัสผู้ใช้ เช่น tinimeearai_avatars/avatar_user_{user_id}
    เมื่อเปลี่ยนรูปใหม่ รูปใหม่จะเข้าไปทับที่เดิมทันที พร้อมสั่ง Invalidate CDN Cache
    """
    if not file_obj:
        return None

    import os
    from django.conf import settings

    cloud_key = getattr(settings, 'CLOUDINARY_API_KEY', None) or os.environ.get('CLOUDINARY_API_KEY')
    use_cloud = cloud_key and cloud_key not in ('your_api_key', 'dummy_key', 'dummy_api_key')

    if not use_cloud:
        return file_obj

    try:
        import cloudinary.uploader
        public_id = f"avatar_user_{user_id}"
        upload_result = cloudinary.uploader.upload(
            file_obj,
            folder=folder,
            public_id=public_id,
            overwrite=True,
            unique_filename=False,
            invalidate=True,
            resource_type="image"
        )
        return upload_result.get('public_id')
    except Exception:
        if hasattr(file_obj, 'seek'):
            file_obj.seek(0)
        return file_obj


