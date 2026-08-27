# 🧭 ที่นี่มีอะไร (Tinimeearai) - Travel & Check-in Web Application

เว็บแอปพลิเคชันสายท่องเที่ยวแนวคอมมูนิตี้ ที่ให้ผู้ใช้งานแชร์ประสบการณ์ ถ่ายทอดภาพถ่าย บันทึกความทรงจำ และเช็คอินพิกัดตำแหน่งจริงผ่าน **HTML5 Geolocation API** พร้อมจัดการรูปภาพบน **Cloudinary** รองรับการแสดงผลบน **สมาร์ตโฟน (Mobile-first PWA)** และพร้อม Deploy ขึ้น **Vercel Serverless** ทันที

---

## 📁 โครงสร้างโปรเจกต์ตามหลักสากล (Project Directory Structure)

```text
checkin-web/
├── .env.example              # ตัวอย่าง Environment Variables มาตรฐาน
├── .gitignore                # Git Ignore มาตรฐานสากลสำหรับ Python & Django & Vercel
├── README.md                 # เอกสารแนะนำและคู่มือการติดตั้งภาษาไทย
├── build_files.sh            # Build script สำหรับ Vercel Deployment
├── vercel.json               # การตั้งค่า Vercel Routing & Serverless Python Function
├── manage.py                 # Django CLI Management Script
├── requirements.txt          # Python Dependencies
├── myapp/                    # Core Django Project Module
│   ├── __init__.py
│   ├── asgi.py
│   ├── settings.py           # Production-ready Settings (WhiteNoise, Cloudinary, Neon/Postgres)
│   ├── urls.py               # Main URL Routing
│   └── wsgi.py               # WSGI Entry Point (with app = application)
├── checkin/                  # Django Application (ที่นี่มีอะไร)
│   ├── __init__.py
│   ├── admin.py              # Model Admin Customization
│   ├── apps.py               # App Configuration
│   ├── forms.py              # Django Forms & File Validation
│   ├── models.py             # Post Model with Cloudinary & GPS fields
│   ├── tests.py              # Unit & Integration Tests
│   ├── urls.py               # App URL Routing
│   ├── views.py              # App Views & APIs
│   ├── migrations/           # Database Migrations
│   └── management/           # Django Management Commands
│       ├── __init__.py
│       └── commands/
│           ├── __init__.py
│           ├── seed_data.py
│           └── upload_to_cloudinary.py
├── static/                   # Source Static Assets
│   ├── css/
│   │   └── style.css
│   ├── js/
│   │   └── main.js
│   └── favicon.svg
└── templates/                # HTML Templates (Tailwind + Leaflet)
    ├── 404.html              # Custom 404 Not Found Page
    ├── 500.html              # Custom 500 Server Error Page
    ├── base.html             # Base Layout (Header, Dock, Toast, Leaflet)
    └── checkin/
        ├── create_post.html
        ├── login.html
        ├── my_posts.html
        ├── post_confirm_delete.html
        ├── post_detail.html
        ├── post_edit.html
        ├── post_list.html
        └── register.html
```

---

## 📱 ประสบการณ์การใช้งานบนโทรศัพท์มือถือ (Mobile-First Experience)

- **Native App Feel**: มี Bottom Navigation Bar พร้อมปุ่มเปิดกล้องถ่ายภาพขนาดใหญ่ตรงกลาง
- **Safe Area Support**: รองรับขอบจอ Notch, Dynamic Island และ Home Indicator ของ iPhone (`viewport-fit=cover`, `env(safe-area-inset-bottom)`)
- **Live Geolocation & Camera**: สลับเปิดกล้องหลังมือถือ (`accept="image/*" capture="environment"`) และดึงพิกัด GPS ความแม่นยำสูงพร้อมลากหมุดบนแผนที่ได้สะดวกด้วยนิ้วสัมผัส
- **Touch-Friendly**: ออกแบบขนาดปุ่มและช่องกรอกตามมาตรฐาน Human Interface Guidelines (ขั้นต่ำ 44x44px)

---

## 🛠️ Tech Stack

- **Backend**: Python 3.12+, Django 5+, SQLite / PostgreSQL (`dj-database-url`)
- **Serverless & Static**: Vercel (`@vercel/python`, `@vercel/static-build`), WhiteNoise
- **Frontend**: Tailwind CSS, Vanilla JS, Lucide Icons, Leaflet.js (OpenStreetMap)
- **Cloud Storage**: Cloudinary (`cloudinary`, `django-cloudinary-storage`)
- **Security**: CSRF Protection, XSS Prevention (`json_script`), Strict Image Upload Validation

---

## ⚡ ขั้นตอนการ Deploy ขึ้น Vercel

### วิธี Deploy ผ่าน GitHub

1. Push โค้ดทั้งหมดขึ้น **GitHub Repository**
2. ไปที่ [vercel.com](https://vercel.com) -> คลิก **Add New Project** -> เลือก GitHub Repository ของคุณ
3. ในส่วน **Environment Variables** บนหน้า Vercel Dashboard ให้เพิ่มตัวแปรต่อไปนี้:
   - `DJANGO_SECRET_KEY` = สุ่มคีย์ความปลอดภัยยาวๆ
   - `DJANGO_DEBUG` = `False`
   - `CLOUDINARY_CLOUD_NAME` = ชื่อ Cloud ของคุณ
   - `CLOUDINARY_API_KEY` = API Key จาก Cloudinary
   - `CLOUDINARY_API_SECRET` = API Secret จาก Cloudinary
   - `DATABASE_URL` = *(แนะนำสำหรับ Production)* URL ของฐานข้อมูล PostgreSQL จาก **Neon**, **Supabase** หรือ **Vercel Postgres**
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

# 4. รัน Unit Tests เพื่อตรวจความถูกต้อง
python manage.py test

# 5. รันเซิร์ฟเวอร์
python manage.py runserver
```

เข้าใช้งานผ่านเบราว์เซอร์: `http://127.0.0.1:8000/` (เข้าสู่ระบบด้วยผู้ใช้ตัวอย่าง `traveler_demo` / รหัสผ่าน `pass1234`)
