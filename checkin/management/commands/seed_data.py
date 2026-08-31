import os
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.conf import settings
from checkin.models import Post, PostImage
import cloudinary.uploader

class Command(BaseCommand):
    help = 'Create sample posts with images uploaded to Cloudinary'

    def handle(self, *args, **kwargs):
        self.stdout.write('Starting sample posts creation with Cloudinary uploads...')

        # 1. สร้าง Demo User
        demo_user, created = User.objects.get_or_create(username='traveler_demo')
        if created:
            demo_user.set_password('pass1234')
            demo_user.save()
            self.stdout.write('Created User: traveler_demo (password: pass1234)')

        # 2. ข้อมูลสถานที่ท่องเที่ยวตัวอย่างพร้อมรูปภาพ
        sample_places = [
            {
                'key': 'watarun',
                'location_name': 'วัดอรุณราชวรารามราชวรมหาวิหาร (Wat Arun)',
                'caption': 'วิวพระปรางค์วัดอรุณยามเย็นริมแม่น้ำเจ้าพระยา สวยงามตระการตามาก ที่นี่มีมุมถ่ายรูปย้อนแสงสวยสุดๆ แนะนำให้มาช่วง 17.30 น. เป็นต้นไป!',
                'lat': 13.743714,
                'lng': 100.488882,
                'tags': 'วัดอรุณ, แม่น้ำเจ้าพระยา, กรุงเทพ, จุดชมวิว',
                'images': [
                    'https://images.unsplash.com/photo-1528181304800-259b08848526?w=1000&auto=format&fit=crop&q=80',
                    'https://images.unsplash.com/photo-1563492065599-3520f775eeed?w=1000&auto=format&fit=crop&q=80',
                    'https://images.unsplash.com/photo-1508009603885-50cf7c579365?w=1000&auto=format&fit=crop&q=80',
                ]
            },
            {
                'key': 'kiewmaepan',
                'location_name': 'จุดชมวิวกิ่วแม่ปาน ดอยอินทนนท์ เชียงใหม่',
                'caption': 'สัมผัสทะเลหมอกยามเช้าและอากาศหนาว 10 องศา ที่นี่มีอะไรให้ค้นหาเยอะมาก เส้นทางศึกษาธรรมชาติเดินง่าย วิวสันเขาอลังการระดับโลก 🌲⛰️',
                'lat': 18.555776,
                'lng': 98.482025,
                'tags': 'กิ่วแม่ปาน, ดอยอินทนนท์, เชียงใหม่, ภูเขา, ทะเลหมอก',
                'images': [
                    'https://images.unsplash.com/photo-1506665531195-3566af2b4dfa?w=1000&auto=format&fit=crop&q=80',
                    'https://images.unsplash.com/photo-1511895426328-dc8714191300?w=1000&auto=format&fit=crop&q=80',
                    'https://images.unsplash.com/photo-1464822759023-fed622ff2c3b?w=1000&auto=format&fit=crop&q=80',
                ]
            },
            {
                'key': 'railay',
                'location_name': 'หาดไร่เลย์ (Railay Beach) จ.กระบี่',
                'caption': 'หาดทรายขาว น้ำทะเลใสสีมรกต ล้อมรอบด้วยหน้าผาหินปูนสูงตระหง่าน บรรยากาศเงียบสงบ เหมาะกับการพายเรือคายัคและปีนผาเป็นที่สุด 🏖️🛶',
                'lat': 8.011880,
                'lng': 98.837375,
                'tags': 'ไร่เลย์, กระบี่, ทะเล, ถ้ำพระนาง, พายเรือ',
                'images': [
                    'https://images.unsplash.com/photo-1552465011-b4e21bf6e79a?w=1000&auto=format&fit=crop&q=80',
                    'https://images.unsplash.com/photo-1537956965359-7573183d1f57?w=1000&auto=format&fit=crop&q=80',
                    'https://images.unsplash.com/photo-1512343879784-a960bf40e7f2?w=1000&auto=format&fit=crop&q=80',
                ]
            },
            {
                'key': 'khaosok',
                'location_name': 'เขาสก & เขื่อนเชี่ยวหลาน สุราษฎร์ธานี',
                'caption': 'กุ้ยหลินเมืองไทย! นอนแพริมน้ำ ตื่นมาเจอหมอกลอยเหนือน้ำสีเขียวมรกต เงียบสงบ ตัดขาดจากความวุ่นวาย แนะนำสายธรรมชาติต้องมาสักครั้งในชีวิต',
                'lat': 8.977200,
                'lng': 98.820300,
                'tags': 'เขาสก, เขื่อนเชี่ยวหลาน, สุราษฎร์ธานี, ธรรมชาติ, ล่องแพ',
                'images': [
                    'https://images.unsplash.com/photo-1507525428034-b723cf961d3e?w=1000&auto=format&fit=crop&q=80',
                    'https://images.unsplash.com/photo-1518509562904-e7ef99cdcc86?w=1000&auto=format&fit=crop&q=80',
                    'https://images.unsplash.com/photo-1506744038136-46273834b3fb?w=1000&auto=format&fit=crop&q=80',
                ]
            }
        ]

        # Reset sample posts to ensure clean image paths
        Post.objects.filter(location_name__in=[p['location_name'] for p in sample_places]).delete()

        created_count = 0

        for i, data in enumerate(sample_places, start=1):
            cloudinary_image_ids = []
            
            # Upload each image to Cloudinary
            for img_order, img_url in enumerate(data['images'], start=1):
                public_id = f"sample_{data['key']}_{img_order}"
                try:
                    upload_res = cloudinary.uploader.upload(
                        img_url,
                        folder='tinimeearai_posts',
                        public_id=public_id,
                        overwrite=True
                    )
                    cloud_path = upload_res.get('public_id')
                    cloudinary_image_ids.append(cloud_path)
                    self.stdout.write(f"  [Cloudinary] Uploaded {public_id}")
                except Exception as e:
                    self.stdout.write(f"  [Warning] Failed upload {public_id}: {e}")
                    cloudinary_image_ids.append(f"tinimeearai_posts/{public_id}")

            primary_img = cloudinary_image_ids[0] if cloudinary_image_ids else f"tinimeearai_posts/sample_{data['key']}_1"
            
            post = Post.objects.create(
                user=demo_user,
                location_name=data['location_name'],
                caption=data['caption'],
                latitude=data['lat'],
                longitude=data['lng'],
                tags=data.get('tags', ''),
                image=primary_img,
                views_count=18 * i
            )

            # Create PostImage for each photo
            for img_order, cloud_img_id in enumerate(cloudinary_image_ids):
                PostImage.objects.create(
                    post=post,
                    image=cloud_img_id,
                    order=img_order
                )

            created_count += 1
            self.stdout.write(f"Created post: {data['location_name']}")

        self.stdout.write(f'Done! Successfully created {created_count} posts on Cloudinary.')
