# 🧭 ที่นี่มีอะไร (Tinimeearai) - Travel & Check-in Web Application

[![Django 5.0+](https://img.shields.io/badge/Django-5.0+-092E20?style=for-the-badge&logo=django&logoColor=white)](https://www.djangoproject.com/)
[![Tailwind CSS](https://img.shields.io/badge/Tailwind_CSS-38B2AC?style=for-the-badge&logo=tailwind-css&logoColor=white)](https://tailwindcss.com/)
[![Leaflet](https://img.shields.io/badge/Leaflet-199900?style=for-the-badge&logo=Leaflet&logoColor=white)](https://leafletjs.com/)
[![Cloudinary](https://img.shields.io/badge/Cloudinary-3448C5?style=for-the-badge&logo=Cloudinary&logoColor=white)](https://cloudinary.com/)
[![Vercel](https://img.shields.io/badge/Vercel-000000?style=for-the-badge&logo=vercel&logoColor=white)](https://vercel.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-316192?style=for-the-badge&logo=postgresql&logoColor=white)](https://www.postgresql.org/)

เว็บแอปพลิเคชันสายท่องเที่ยวแนวคอมมูนิตี้ (Community Travel & Check-in Platform) สไตล์ Instagram & PWA ที่ให้ผู้ใช้งานแชร์เรื่องราวการเดินทาง ภาพถ่ายความทรงจำ เช็คอินพิกัดตำแหน่งจริงผ่าน **HTML5 Geolocation API** ค้นหาหมุดแผนที่ Leaflet.js พร้อมระบบถูกใจแบบ **Instant Optimistic UI (0ms)**, หน้าต่างความคิดเห็นแบบ **Interactive Drawer**, ระบบแจ้งเตือนแบบ Real-time และพร้อม Deploy สู่ **Vercel Serverless** ทันที

---

## 📁 โครงสร้างโปรเจกต์มาตรฐานสากล (Standard Project Structure)

```text
checkin-web/
├── .env.example                     # ตัวอย่างการตั้งค่า Environment Variables มาตรฐาน
├── .gitignore                       # ละเว้นไฟล์ที่ไม่ควร Commit (Secrets, Virtualenv, Bytecode)
├── README.md                        # เอกสารแนะนำและคู่มือการติดตั้งโปรเจกต์
├── build_files.sh                   # สคริปต์อัตโนมัติสำหรับ Vercel Build Pipeline
├── vercel.json                      # การตั้งค่า Serverless Function & Static Routing สำหรับ Vercel
├── manage.py                        # Django Command-line Utility
├── requirements.txt                 # รายการ Python Packages และ Dependencies
├── myapp/                           # Project Configuration Module
│   ├── __init__.py
│   ├── asgi.py                      # ASGI Entry Point
│   ├── settings.py                  # Production Settings (WhiteNoise, Cloudinary, Neon PostgreSQL)
│   ├── urls.py                      # Main Routing & Error Handlers
│   └── wsgi.py                      # WSGI Entry Point (with app = application for Vercel)
├── checkin/                         # Application Core Module (ที่นี่มีอะไร)
│   ├── __init__.py
│   ├── admin.py                     # Django Admin Model Configurations
│   ├── apps.py                      # Application Metadata Configuration
│   ├── context_processors.py        # Global Context (Unread Notifications Counter)
│   ├── forms.py                     # Secure Form Handling & Validation Rules
│   ├── models.py                    # Data Models (Post, Comment, Profile, Notification)
│   ├── tests.py                     # Comprehensive Unit & Integration Tests (24/24 Passed)
│   ├── urls.py                      # Checkin URL Routing Endpoints
│   ├── views.py                     # Controller & API Views
│   ├── migrations/                  # Database Schema Migrations
│   └── management/                  # Custom Django Management Commands
│       ├── __init__.py
│       └── commands/
│           ├── __init__.py
│           ├── seed_data.py         # Seed realistic sample travel community data
│           └── upload_to_cloudinary.py
├── static/                          # Static Web Assets
│   ├── css/
│   │   └── style.css                # Custom CSS Design System & Glassmorphism Tokens
│   ├── js/
│   │   └── main.js                  # Optimistic UI, Pull-to-Refresh, Swipe Gestures
│   ├── favicon.ico
│   ├── favicon.png
│   └── favicon.svg
└── templates/                       # Django HTML Templates (Modern Dark Glassmorphism)
    ├── 404.html                     # Custom 404 Error Page
    ├── 500.html                     # Custom 500 Error Page
    ├── base.html                    # Master Base Layout (Header, Desktop Left Tab, Mobile Dock)
    └── checkin/                     # App-specific Views
        ├── create_post.html         # Create Post with Live Map, GPS & Camera
        ├── login.html               # Authentication: Sign In
        ├── my_posts.html            # User Footprints & Personal Check-ins
        ├── notifications.html       # Real-time Notifications Center
        ├── post_confirm_delete.html # Post Deletion Confirmation Modal
        ├── post_detail.html         # Post Detail, Google Maps Navigation & Comments Drawer
        ├── post_edit.html           # Edit Post View
        ├── post_list.html           # Explore Feed with Pull-to-Refresh & Community Map
        ├── register.html            # Authentication: Sign Up
        ├── search.html              # Dedicated Instant Search Page with Tags & Filters
        ├── settings.html            # Settings Hub
        ├── settings_about.html      # About Application & Changelog
        ├── settings_data.html       # Data Export & Management
        ├── settings_gps.html        # GPS Calibration & Accuracy Guide
        ├── settings_map.html        # Map Style Customization (Dark, Satellite, Standard)
        ├── settings_password.html   # Password Management
        ├── settings_profile.html    # Profile Edit (Display Name, Bio, Avatar URL)
        └── user_profile.html        # Public User Profile Page
```

---

## 🌟 ฟีเจอร์หลัก (Key Features)

1. **Instant Optimistic UI (0ms)**:
   - กดไลก์โพสต์และคอมเมนต์แล้วหัวใจเปลี่ยนสีแดงทันทีพร้อมตัวเลขเด้ง ไม่ต้องรอ Network Roundtrip
2. **Interactive Instagram-style Comments Drawer**:
   - หน้าต่างคอมเมนต์เลื่อนขึ้นจากล่างจอ พร้อม Handle ดึงลงเพื่อปิด ปักหมุดส่วนหัวและกล่องพิมพ์ข้อความที่เดิม
3. **Pull-to-Refresh Gesture**:
   - รูดดึงลงจากบนสุดของหน้าสำรวจเพื่อรีเฟรชดูโพสต์ใหม่ๆ พร้อมไอคอนหมุนตามแรงนิ้ว
4. **Google Maps Navigation Integration**:
   - เชื่อมต่อไปยัง Google Maps อัตโนมัติด้วยพิกัดจริงเพื่อการนำทางที่แม่นยำ
5. **Real-time Notifications**:
   - แจ้งเตือนเมื่อมีคนมากดถูกใจหรือคอมเมนต์โพสต์ พร้อมกระดิ่งแจ้งเตือนตัวเลขสีแดง
6. **Mobile-First Touch Architecture**:
   - ปัดซ้าย/ขวาเพื่อสลับหน้าระหว่าง *ตั้งค่า <-> สำรวจ <-> ค้นหา* อย่างราบรื่น

---

## 🛠️ Tech Stack

- **Backend**: Python 3.12+, Django 5.0+, SQLite (Local) / PostgreSQL (Neon)
- **Deployment**: Vercel Serverless (`@vercel/python`, `@vercel/static-build`), WhiteNoise
- **Frontend**: Vanilla CSS, Tailwind CSS, Lucide Icons, Leaflet.js (OpenStreetMap)
- **Cloud Media**: Cloudinary (`cloudinary`, `django-cloudinary-storage`)
- **Testing**: Django Test Suite (24 Unit Tests with 100% Pass Rate)

---

## ⚡ วิธีการ Deploy ขึ้น Vercel

1. **Push โค้ดขึ้น GitHub**:
   ```bash
   git add .
   git commit -m "feat: complete checkin web application"
   git push origin main
   ```
2. **สร้างโปรเจกต์บน Vercel**:
   - ไปที่ [vercel.com](https://vercel.com) แล้ว Import GitHub Repository ของคุณ
3. **ตั้งค่า Environment Variables** ใน Vercel Dashboard:
   - `DJANGO_SECRET_KEY` = *รหัสสุ่มความปลอดภัยของคุณ*
   - `DJANGO_DEBUG` = `False`
   - `ALLOWED_HOSTS` = `.vercel.app`
   - `DATABASE_URL` = *URL ฐานข้อมูล PostgreSQL ของคุณ (เช่น Neon / Supabase)*
   - `CLOUDINARY_CLOUD_NAME` = *ชื่อ Cloud Name ของคุณ*
   - `CLOUDINARY_API_KEY` = *API Key จาก Cloudinary*
   - `CLOUDINARY_API_SECRET` = *API Secret จาก Cloudinary*
4. **กดปุ่ม Deploy**: Vercel จะทำการ Build และ Deploy สู่ Production อัตโนมัติทันที

---

## 💻 การรันโปรเจกต์ในเครื่อง (Local Development)

```bash
# 1. ติดตั้ง Dependencies
pip install -r requirements.txt

# 2. คัดลอกและตั้งค่า Environment Variables
cp .env.example .env

# 3. รัน Database Migration
python manage.py migrate

# 4. สร้างข้อมูลตัวอย่าง (Seed Realistic Data)
python manage.py seed_data

# 5. รัน Unit Tests (24 รายการ)
python manage.py test --keepdb

# 6. รันเซิร์ฟเวอร์
python manage.py runserver
```
เข้าใช้งานผ่านเบราว์เซอร์: `http://127.0.0.1:8000/`

---

## 👥 ผู้พัฒนา (Development Team CS69)

- **นายภูพิรัฐ แซ่โค้ว** (รหัสนักศึกษา: `6812732119`)
- **นายสกล มะลิลา** (รหัสนักศึกษา: `6812732124`)
- **นายอานนท์ เพิ่มพูล** (รหัสนักศึกษา: `6812732129`)

