# 🧭 ที่นี่มีอะไร (Tinimeearai) - Travel & Check-in Web Application

เว็บแอปพลิเคชันสายท่องเที่ยวแนวคอมมูนิตี้ ที่ให้ผู้ใช้งานแชร์ประสบการณ์ ถ่ายทอดภาพถ่าย บันทึกความทรงจำ และเช็คอินพิกัดตำแหน่งจริงผ่าน **HTML5 Geolocation API** พร้อมจัดการรูปภาพบน **Cloudinary** รองรับการแสดงผลบน **สมาร์ตโฟน (Mobile-first PWA)** และพร้อม Deploy ขึ้น **Vercel** ทันที

---

## 📱 ประสบการณ์การใช้งานบนโทรศัพท์มือถือ (Mobile-First Experience)

- **Native App Feel**: มี Bottom Navigation Bar พร้อมปุ่มเปิดกล้องถ่ายภาพขนาดใหญ่ตรงกลาง
- **Safe Area Support**: รองรับขอบจอ Notch, Dynamic Island และ Home Indicator ของ iPhone (`viewport-fit=cover`, `env(safe-area-inset-bottom)`)
- **Live Geolocation & Camera**: สลับเปิดกล้องหลังมือถือ (`accept="image/*" capture="environment"`) และดึงพิกัด GPS ความแม่นยำสูงพร้อมลากหมุดบนแผนที่ได้สะดวกด้วยนิ้วสัมผัส
- **Touch-Friendly**: ออกแบบขนาดปุ่มและช่องกรอกตามมาตรฐาน Human Interface Guidelines (ขั้นต่ำ 44x44px)

---

## 🛠️ Tech Stack

- **Backend**: Python 3.12+, Django, SQLite / PostgreSQL (`dj-database-url`)
- **Serverless & Static**: Vercel (`@vercel/python`), WhiteNoise
- **Frontend**: Tailwind CSS, Vanilla JS, Lucide Icons, Leaflet.js (OpenStreetMap)
- **Cloud Storage**: Cloudinary (`cloudinary`, `django-cloudinary-storage`)
- **Security**: CSRF Protection, XSS Prevention (`json_script`), Strict Image Upload Validation

---

## ⚡ ขั้นตอนการ Deploy ขึ้น Vercel

### วิธีที่ 1: Deploy ผ่าน GitHub (แนะนำ & ง่ายที่สุด)

1. Push โค้ดทั้งหมดขึ้น **GitHub Repository**
2. ไปที่ [vercel.com](https://vercel.com) -> คลิก **Add New Project** -> เลือก GitHub Repository ของคุณ
3. ในส่วน **Environment Variables** บนหน้า Vercel Dashboard ให้เพิ่มตัวแปรต่อไปนี้:
   - `DJANGO_SECRET_KEY` = สุ่มคีย์ความปลอดภัยยาวๆ
   - `DJANGO_DEBUG` = `False`
   - `CLOUDINARY_CLOUD_NAME` = ชื่อ Cloud ของคุณ
   - `CLOUDINARY_API_KEY` = API Key จาก Cloudinary
   - `CLOUDINARY_API_SECRET` = API Secret จาก Cloudinary
   - `DATABASE_URL` = *(ตัวเลือก)* URL ของฐานข้อมูล PostgreSQL จาก **Neon**, **Supabase** หรือ **Vercel Postgres**
4. กดปุ่ม **Deploy** แล้วรอระบบ Build เสร็จสิ้น พร้อมเข้าใช้งานผ่านโดเมน `https://your-project.vercel.app`

---

## 💻 การติดตั้งและทดสอบในเครื่อง (Local Development)

```bash
# 1. ติดตั้ง Dependencies
pip install -r requirements.txt

# 2. ตั้งค่า .env
cp .env.example .env

# 3. รัน Migration และสร้างข้อมูลตัวอย่าง
python manage.py migrate
python manage.py seed_data

# 4. รันเซิร์ฟเวอร์
python manage.py runserver
```
เข้าใช้งานผ่านเบราว์เซอร์: `http://127.0.0.1:8000/` (เข้าสู่ระบบด้วย `traveler_demo` / `pass1234`)
