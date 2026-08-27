import os
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.conf import settings
from checkin.models import Post
import urllib.request

class Command(BaseCommand):
    help = 'สร้างข้อมูลจำลองสำหรับการทดสอบระบบ "ที่นี่มีอะไร" (Tinimeearai)'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.NOTICE('กำลังสร้างข้อมูลจำลอง...'))

        # 1. สร้าง Demo User
        demo_user, created = User.objects.get_or_create(username='traveler_demo')
        if created:
            demo_user.set_password('pass1234')
            demo_user.save()
            self.stdout.write(self.style.SUCCESS('สร้าง User: traveler_demo (รหัสผ่าน: pass1234) สำเร็จ'))

        # 2. ข้อมูลสถานที่ท่องเที่ยวตัวอย่าง
        sample_places = [
            {
                'location_name': 'วัดอรุณราชวรารามราชวรมหาวิหาร (Wat Arun)',
                'caption': 'วิวพระปรางค์วัดอรุณยามเย็นริมแม่น้ำเจ้าพระยา สวยงามตระการตามาก ที่นี่มีมุมถ่ายรูปย้อนแสงสวยสุดๆ แนะนำให้มาช่วง 17.30 น. เป็นต้นไป!',
                'lat': 13.743714,
                'lng': 100.488882,
                'image_url': 'https://images.unsplash.com/photo-1528181304800-259b08848526?w=1000&auto=format&fit=crop&q=80'
            },
            {
                'location_name': 'จุดชมวิวกิ่วแม่ปาน ดอยอินทนนท์ เชียงใหม่',
                'caption': 'สัมผัสทะเลหมอกยามเช้าและอากาศหนาว 10 องศา ที่นี่มีอะไรให้ค้นหาเยอะมาก เส้นทางศึกษาธรรมชาติเดินง่าย วิวสันเขาอลังการระดับโลก 🌲⛰️',
                'lat': 18.555776,
                'lng': 98.482025,
                'image_url': 'https://images.unsplash.com/photo-1506665531195-3566af2b4dfa?w=1000&auto=format&fit=crop&q=80'
            },
            {
                'location_name': 'หาดไร่เลย์ (Railay Beach) จ.กระบี่',
                'caption': 'หาดทรายขาว น้ำทะเลใสสีมรกต ล้อมรอบด้วยหน้าผาหินปูนสูงตระหง่าน บรรยากาศเงียบสงบ เหมาะกับการพายเรือคายัคและปีนผาเป็นที่สุด 🏖️🛶',
                'lat': 8.011880,
                'lng': 98.837375,
                'image_url': 'https://images.unsplash.com/photo-1552465011-b4e21bf6e79a?w=1000&auto=format&fit=crop&q=80'
            },
            {
                'location_name': 'เขาสก & เขื่อนเชี่ยวหลาน สุราษฎร์ธานี',
                'caption': 'กุ้ยหลินเมืองไทย! นอนแพริมน้ำ ตื่นมาเจอหมอกลอยเหนือน้ำสีเขียวมรกต เงียบสงบ ตัดขาดจากความวุ่นวาย แนะนำสายธรรมชาติต้องมาสักครั้งในชีวิต',
                'lat': 8.977200,
                'lng': 98.820300,
                'image_url': 'https://images.unsplash.com/photo-1507525428034-b723cf961d3e?w=1000&auto=format&fit=crop&q=80'
            }
        ]

        # Reset sample posts to ensure clean image paths
        Post.objects.filter(location_name__in=[p['location_name'] for p in sample_places]).delete()

        created_count = 0
        os.makedirs(settings.MEDIA_ROOT, exist_ok=True)

        for i, data in enumerate(sample_places, start=1):
            filename = f"sample_travel_{i}.jpg"
            file_saved_path = filename

            try:
                req = urllib.request.Request(data['image_url'], headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req, timeout=10) as response:
                    img_content = response.read()
                    file_saved_path = default_storage.save(f"tinimeearai_posts/{filename}", ContentFile(img_content))
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"ดาวน์โหลดภาพไม่ได้: {e}"))
                file_saved_path = data['image_url']

            post = Post.objects.create(
                user=demo_user,
                location_name=data['location_name'],
                caption=data['caption'],
                latitude=data['lat'],
                longitude=data['lng'],
                image=file_saved_path,
                views_count=12 * i
            )
            created_count += 1
            self.stdout.write(self.style.SUCCESS(f"สร้างโพสต์: {data['location_name']} สำเร็จ"))

        self.stdout.write(self.style.SUCCESS(f'เสร็จสิ้น! สร้างโพสต์ตัวอย่างทั้งหมด {created_count} รายการ'))
