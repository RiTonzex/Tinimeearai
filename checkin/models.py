from django.db import models
from django.contrib.auth.models import User
from cloudinary.models import CloudinaryField
from django.conf import settings
import os

class Post(models.Model):
    """
    Model สำหรับเก็บข้อมูลโพสต์การท่องเที่ยวและเช็คอิน "ที่นี่มีอะไร"
    """
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='posts',
        verbose_name="ผู้โพสต์"
    )
    
    # รูปภาพจัดเก็บบน Cloudinary (หรือ Local Media Storage)
    image = CloudinaryField(
        'รูปภาพการเดินทาง',
        folder='tinimeearai_posts',
        overwrite=True,
        resource_type='image'
    )
    
    caption = models.TextField(
        verbose_name="แคปชั่น / รายละเอียดการเดินทาง",
        help_text="บอกเล่าประสบการณ์ ความประทับใจ หรือสิ่งที่น่าสนใจในสถานที่นี้"
    )
    
    location_name = models.CharField(
        max_length=255, 
        blank=True, 
        null=True,
        verbose_name="ชื่อสถานที่ / จุดเช็คอิน",
        help_text="เช่น ดอยอินทนนท์, คาเฟ่ริมหาดพัทยา หรือชื่อสถานที่ที่ตรวจพบ"
    )
    
    # พิกัด Geolocation ที่ได้จาก HTML5 Browser API
    latitude = models.DecimalField(
        max_digits=9, 
        decimal_places=6, 
        null=True, 
        blank=True,
        verbose_name="ละติจูด (Latitude)"
    )
    longitude = models.DecimalField(
        max_digits=9, 
        decimal_places=6, 
        null=True, 
        blank=True,
        verbose_name="ลองจิจูด (Longitude)"
    )
    
    # ผู้ใช้งานที่กดถูกใจโพสต์
    likes = models.ManyToManyField(
        User,
        related_name='liked_posts',
        blank=True,
        verbose_name="ผู้กดถูกใจ"
    )
    
    views_count = models.PositiveIntegerField(default=0, verbose_name="จำนวนการเข้าชม")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="สร้างเมื่อ")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="แก้ไขล่าสุด")

    class Meta:
        ordering = ['-created_at']
        verbose_name = "โพสต์เช็คอิน"
        verbose_name_plural = "โพสต์เช็คอินทั้งหมด"

    def __str__(self):
        user_str = self.user.username if self.user else "Anonymous"
        loc_str = self.location_name or f"พิกัด ({self.latitude}, {self.longitude})" if self.latitude else "ไม่มีพิกัด"
        return f"{user_str} @ {loc_str} - {self.created_at.strftime('%d/%m/%Y %H:%M')}"

    @property
    def has_coordinates(self):
        return self.latitude is not None and self.longitude is not None

    @property
    def google_maps_url(self):
        if self.has_coordinates:
            return f"https://www.google.com/maps/search/?api=1&query={self.latitude},{self.longitude}"
        return None

    @property
    def total_likes(self):
        return self.likes.count()

    def get_image_url(self):
        """
        Helper method สำหรับคืนค่า URL รูปภาพอย่างปลอดภัย (บังคับใช้ HTTPS สำหรับ Cloudinary)
        """
        if not self.image:
            return ""
        
        # 1. พยายามเรียก .url จาก Cloudinary / Storage
        try:
            if hasattr(self.image, 'url'):
                url = str(self.image.url)
                if url.startswith('http://res.cloudinary.com'):
                    url = url.replace('http://', 'https://', 1)
                return url
        except Exception:
            pass

        # 2. กรณีเก็บเป็น String Path
        img_str = str(self.image)
        if img_str.startswith('http://') or img_str.startswith('https://'):
            return img_str.replace('http://', 'https://', 1) if 'cloudinary.com' in img_str else img_str
        
        local_path = os.path.join(settings.MEDIA_ROOT, img_str)
        if not os.path.exists(local_path) and os.path.exists(f"{local_path}.jpg"):
            img_str = f"{img_str}.jpg"

        return f"{settings.MEDIA_URL}{img_str}"
