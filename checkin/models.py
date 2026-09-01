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
    
    # รูปภาพหลัก (หรือรูปแรก) จัดเก็บบน Cloudinary (หรือ Local Media Storage)
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
    
    # แท็ก / หมวดหมู่
    tags = models.CharField(
        max_length=255, 
        blank=True, 
        null=True,
        verbose_name="แท็ก / หมวดหมู่",
        help_text="เช่น คาเฟ่, ภูเขา, ทะเล, จุดชมวิว, พิกัดลับ"
    )

    # ผู้ใช้งานที่กดถูกใจโพสต์
    likes = models.ManyToManyField(
        User,
        related_name='liked_posts',
        blank=True,
        verbose_name="ผู้กดถูกใจ"
    )
    
    views_count = models.PositiveIntegerField(default=0, verbose_name="จำนวนการเข้าชม")
    is_hidden = models.BooleanField(default=False, verbose_name="ซ่อนโพสต์")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="สร้างเมื่อ")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="แก้ไขล่าสุด")

    class Meta:
        ordering = ['-created_at']
        verbose_name = "โพสต์เช็คอิน"
        verbose_name_plural = "โพสต์เช็คอินทั้งหมด"

    def __str__(self):
        user_str = self.user.username if self.user else "Anonymous"
        loc_str = self.location_name or (f"พิกัด ({self.latitude}, {self.longitude})" if self.latitude else "ไม่มีพิกัด")
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

    @property
    def total_comments(self):
        return self.comments.count()

    @property
    def has_multiple_images(self):
        return len(self.get_all_image_urls()) > 1

    def get_image_url(self):
        """
        Helper method สำหรับคืนค่า URL รูปภาพหลักอย่างปลอดภัย
        """
        DEFAULT_IMAGE = "https://images.unsplash.com/photo-1507525428034-b723cf961d3e?w=1000&auto=format&fit=crop&q=80"
        if not self.image:
            return DEFAULT_IMAGE
        
        img_str = str(self.image).strip()
        if not img_str or img_str in ('https://images.unsplash', 'http://images.unsplash'):
            return DEFAULT_IMAGE

        try:
            if hasattr(self.image, 'url'):
                url = str(self.image.url)
                if url.startswith('http://res.cloudinary.com'):
                    url = url.replace('http://', 'https://', 1)
                if url and ('cloudinary' in url or '.jpg' in url or '.png' in url or '.webp' in url):
                    return url
        except Exception:
            pass

        cloud_name = getattr(settings, 'CLOUDINARY_CLOUD_NAME', None) or os.environ.get('CLOUDINARY_CLOUD_NAME')
        if cloud_name and cloud_name not in ('your_cloud_name', 'dummy_cloud_name') and not img_str.startswith('http') and not img_str.startswith('/'):
            clean_path = img_str.lstrip('/')
            return f"https://res.cloudinary.com/{cloud_name}/image/upload/{clean_path}"

        if (img_str.startswith('http://') or img_str.startswith('https://')) and ('.com' in img_str or '.org' in img_str or '.net' in img_str or '.jpg' in img_str or '.png' in img_str or '.webp' in img_str or 'cloudinary' in img_str):
            if img_str.startswith('http://res.cloudinary.com'):
                return img_str.replace('http://', 'https://', 1)
            return img_str

        local_path = os.path.join(settings.MEDIA_ROOT, img_str)
        if not os.path.exists(local_path) and os.path.exists(f"{local_path}.jpg"):
            img_str = f"{img_str}.jpg"

        if os.path.exists(local_path) or os.path.exists(f"{local_path}.jpg"):
            return f"{settings.MEDIA_URL}{img_str}"

        return DEFAULT_IMAGE

    def get_all_image_urls(self):
        """
        คืนค่า List ของ URLs รูปภาพทั้งหมดในโพสต์สำหรับแสดงผลแบบ Carousel
        """
        urls = []
        for post_img in self.images.all():
            url = post_img.get_image_url()
            if url and url not in ('https://images.unsplash', 'http://images.unsplash') and url not in urls:
                urls.append(url)
        
        if not urls:
            primary_url = self.get_image_url()
            if primary_url and primary_url not in ('https://images.unsplash', 'http://images.unsplash'):
                urls.append(primary_url)

        return urls if urls else ["https://images.unsplash.com/photo-1507525428034-b723cf961d3e?w=1000&auto=format&fit=crop&q=80"]


class PostImage(models.Model):
    """
    Model สำหรับเก็บรูปภาพเพิ่มเติมของแต่ละโพสต์ (รองรับ Multi-photo Carousel สไตล์ Instagram)
    """
    post = models.ForeignKey(
        Post,
        on_delete=models.CASCADE,
        related_name='images',
        verbose_name="โพสต์"
    )
    image = CloudinaryField(
        'รูปภาพ',
        folder='tinimeearai_posts',
        overwrite=True,
        resource_type='image'
    )
    order = models.PositiveIntegerField(default=0, verbose_name="ลำดับการแสดงผล")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="สร้างเมื่อ")

    class Meta:
        ordering = ['order', 'id']
        verbose_name = "รูปภาพโพสต์"
        verbose_name_plural = "รูปภาพโพสต์ทั้งหมด"

    def __str__(self):
        return f"รูปภาพของโพสต์ #{self.post_id} (ลำดับ {self.order})"

    def get_image_url(self):
        DEFAULT_IMAGE = "https://images.unsplash.com/photo-1507525428034-b723cf961d3e?w=1000&auto=format&fit=crop&q=80"
        if not self.image:
            return DEFAULT_IMAGE

        img_str = str(self.image).strip()
        if not img_str or img_str in ('https://images.unsplash', 'http://images.unsplash'):
            return DEFAULT_IMAGE

        try:
            if hasattr(self.image, 'url'):
                url = str(self.image.url)
                if url.startswith('http://res.cloudinary.com'):
                    url = url.replace('http://', 'https://', 1)
                if url and ('cloudinary' in url or '.jpg' in url or '.png' in url or '.webp' in url):
                    return url
        except Exception:
            pass

        cloud_name = getattr(settings, 'CLOUDINARY_CLOUD_NAME', None) or os.environ.get('CLOUDINARY_CLOUD_NAME')
        if cloud_name and cloud_name not in ('your_cloud_name', 'dummy_cloud_name') and not img_str.startswith('http') and not img_str.startswith('/'):
            clean_path = img_str.lstrip('/')
            return f"https://res.cloudinary.com/{cloud_name}/image/upload/{clean_path}"

        if (img_str.startswith('http://') or img_str.startswith('https://')) and ('.com' in img_str or '.org' in img_str or '.net' in img_str or '.jpg' in img_str or '.png' in img_str or '.webp' in img_str or 'cloudinary' in img_str):
            if img_str.startswith('http://res.cloudinary.com'):
                return img_str.replace('http://', 'https://', 1)
            return img_str

        local_path = os.path.join(settings.MEDIA_ROOT, img_str)
        if not os.path.exists(local_path) and os.path.exists(f"{local_path}.jpg"):
            img_str = f"{img_str}.jpg"

        if os.path.exists(local_path) or os.path.exists(f"{local_path}.jpg"):
            return f"{settings.MEDIA_URL}{img_str}"

        return DEFAULT_IMAGE


class Comment(models.Model):
    """
    Model สำหรับเก็บข้อมูลความคิดเห็นในแต่ละโพสต์เช็คอิน
    """
    post = models.ForeignKey(
        Post,
        on_delete=models.CASCADE,
        related_name='comments',
        verbose_name="โพสต์"
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='comments',
        verbose_name="ผู้แสดงความคิดเห็น"
    )
    content = models.TextField(
        verbose_name="ข้อความความคิดเห็น"
    )
    likes = models.ManyToManyField(
        User,
        related_name='liked_comments',
        blank=True,
        verbose_name="ผู้กดถูกใจคอมเมนต์"
    )
    is_hidden = models.BooleanField(default=False, verbose_name="ซ่อนความคิดเห็น")
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="เวลาแสดงความคิดเห็น"
    )

    class Meta:
        ordering = ['created_at']
        verbose_name = "ความคิดเห็น"
        verbose_name_plural = "ความคิดเห็นทั้งหมด"

    def __str__(self):
        user_str = self.user.username if self.user else "Anonymous"
        return f"ความคิดเห็นโดย @{user_str} บนโพสต์ #{self.post_id}: {self.content[:30]}"

    @property
    def total_likes(self):
        return self.likes.count()


class Profile(models.Model):
    """
    Model สำหรับเก็บข้อมูลโปรไฟล์เพิ่มเติมของผู้ใช้งาน (Display Name, Bio, Avatar Color)
    """
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profile',
        verbose_name="ผู้ใช้งาน"
    )
    display_name = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name="ชื่อที่แสดง (Display Name)",
        help_text="ชื่อที่ต้องการให้คนอื่นเห็นในโพสต์และคอมเมนต์"
    )
    bio = models.TextField(
        max_length=500,
        blank=True,
        null=True,
        verbose_name="ประวัติโดยย่อ (Bio)",
        help_text="แนะนำตัวเอง สไตล์การท่องเที่ยว หรือคำคมที่ชอบ"
    )
    avatar = CloudinaryField(
        'รูปภาพโปรไฟล์',
        folder='tinimeearai_avatars',
        blank=True,
        null=True,
        overwrite=True,
        resource_type='image'
    )
    avatar_color = models.CharField(
        max_length=50,
        default="from-emerald-500 to-teal-400",
        verbose_name="ธีมสีอวาตาร์"
    )
    is_banned = models.BooleanField(
        default=False,
        verbose_name="ถูกระงับ/แบนบัญชี",
        help_text="หากเปิดใช้งาน ผู้ใช้จะไม่สามารถเข้าสู่ระบบหรือใช้งานระบบได้"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="สร้างเมื่อ")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="แก้ไขล่าสุด")

    def __str__(self):
        return f"Profile of @{self.user.username} ({self.get_display_name()})"

    def get_display_name(self):
        if self.display_name and self.display_name.strip():
            return self.display_name.strip()
        if self.user.first_name and self.user.first_name.strip():
            if self.user.last_name:
                return f"{self.user.first_name} {self.user.last_name}".strip()
            return self.user.first_name.strip()
        return self.user.username

    def get_initial(self):
        name = self.get_display_name()
        return name[:1].upper() if name else "U"

    def get_avatar_url(self):
        if not self.avatar:
            return None
        img_str = str(self.avatar).strip()
        if not img_str:
            return None
        if img_str.startswith('http://') or img_str.startswith('https://'):
            if img_str.startswith('http://res.cloudinary.com'):
                return img_str.replace('http://', 'https://', 1)
            return img_str
        try:
            if hasattr(self.avatar, 'url'):
                url = str(self.avatar.url)
                if url.startswith('http://res.cloudinary.com'):
                    url = url.replace('http://', 'https://', 1)
                if url and not url.endswith('http:/') and not url.endswith('https:/'):
                    return url
        except Exception:
            pass
        cloud_name = getattr(settings, 'CLOUDINARY_CLOUD_NAME', None) or os.environ.get('CLOUDINARY_CLOUD_NAME')
        if cloud_name and cloud_name not in ('your_cloud_name', 'dummy_cloud_name') and not img_str.startswith('/'):
            clean_path = img_str.lstrip('/')
            return f"https://res.cloudinary.com/{cloud_name}/image/upload/{clean_path}"
        return None

    @property
    def followers_count(self):
        return self.user.followers_set.count()

    @property
    def following_count(self):
        return self.user.following_set.count()

    def is_followed_by(self, user):
        if not user or not user.is_authenticated or user == self.user:
            return False
        return self.user.followers_set.filter(follower=user).exists()

    def is_following(self, user):
        if not user or not user.is_authenticated or user == self.user:
            return False
        return self.user.following_set.filter(following=user).exists()


class Follow(models.Model):
    """
    Model สำหรับเก็บข้อมูลการติดตามระหว่างผู้ใช้งาน (Follow / Following)
    """
    follower = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='following_set',
        verbose_name="ผู้กดติดตาม"
    )
    following = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='followers_set',
        verbose_name="ผู้ถูกติดตาม"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="เวลาที่ติดตาม"
    )

    class Meta:
        unique_together = ('follower', 'following')
        ordering = ['-created_at']
        verbose_name = "การติดตาม"
        verbose_name_plural = "การติดตามทั้งหมด"

    def __str__(self):
        return f"@{self.follower.username} follows @{self.following.username}"


class Notification(models.Model):
    """
    Model สำหรับเก็บการแจ้งเตือนต่างๆ (กดไลก์โพสต์, กดไลก์คอมเมนต์, แสดงความคิดเห็น, การติดตาม)
    """
    VERB_CHOICES = [
        ('like_post', 'ถูกใจโพสต์'),
        ('like_comment', 'ถูกใจความคิดเห็น'),
        ('comment_post', 'แสดงความคิดเห็น'),
        ('follow_user', 'เริ่มติดตามคุณ'),
    ]

    recipient = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='notifications',
        verbose_name="ผู้รับการแจ้งเตือน"
    )
    actor = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='actions_made',
        verbose_name="ผู้กระทำ"
    )
    verb = models.CharField(
        max_length=50,
        choices=VERB_CHOICES,
        verbose_name="ประเภทการกระทำ"
    )
    post = models.ForeignKey(
        Post,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='notifications',
        verbose_name="โพสต์ที่เกี่ยวข้อง"
    )
    comment = models.ForeignKey(
        Comment,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='notifications',
        verbose_name="ความคิดเห็นที่เกี่ยวข้อง"
    )
    is_read = models.BooleanField(
        default=False,
        verbose_name="อ่านแล้ว"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="เวลาแจ้งเตือน"
    )

    class Meta:
        ordering = ['-created_at']
        verbose_name = "การแจ้งเตือน"
        verbose_name_plural = "การแจ้งเตือนทั้งหมด"

    def __str__(self):
        return f"Notification for @{self.recipient.username}: @{self.actor.username} {self.verb}"

    def get_time_ago(self):
        from django.utils import timezone
        now = timezone.now()
        diff = now - self.created_at
        seconds = int(diff.total_seconds())
        if seconds < 60:
            return "เมื่อสักครู่"
        elif seconds < 3600:
            return f"{seconds // 60} นาทีที่แล้ว"
        elif seconds < 86400:
            return f"{seconds // 3600} ชม. ที่แล้ว"
        elif seconds < 604800:
            return f"{seconds // 86400} วันที่แล้ว"
        else:
            return f"{seconds // 604800} สัปดาห์ที่แล้ว"

    def get_message(self):
        actor_name = self.actor.profile.get_display_name() if hasattr(self.actor, 'profile') else self.actor.username
        if self.verb == 'like_post':
            loc = f" '{self.post.location_name}'" if self.post and self.post.location_name else ""
            return f"{actor_name} กดถูกใจโพสต์{loc} ของคุณ"
        elif self.verb == 'comment_post':
            text = f": '{self.comment.content[:25]}...'" if self.comment and self.comment.content else ""
            return f"{actor_name} แสดงความคิดเห็นบนโพสต์ของคุณ{text}"
        elif self.verb == 'like_comment':
            text = f": '{self.comment.content[:20]}...'" if self.comment and self.comment.content else ""
            return f"{actor_name} ถูกใจความคิดเห็นของคุณ{text}"
        elif self.verb == 'follow_user':
            return f"{actor_name} เริ่มติดตามคุณ"
        return f"{actor_name} มีการเคลื่อนไหวใหม่"


# Auto create/ensure profile signal
from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=User)
def create_or_save_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance, display_name=instance.first_name or instance.username)
    else:
        if not hasattr(instance, 'profile'):
            Profile.objects.create(user=instance, display_name=instance.first_name or instance.username)


class Report(models.Model):
    """
    Model สำหรับเก็บข้อมูลการรายงานเนื้อหา/ผู้ใช้งาน (Post or Comment Report)
    """
    REASON_CHOICES = [
        ('spam', 'ขยะ / สแปม (Spam)'),
        ('inappropriate', 'เนื้อหาไม่เหมาะสม / ลามกอนาจาร'),
        ('harassment', 'การคุกคาม / ความเกลียดชัง'),
        ('fake_news', 'ข้อมูลเท็จ / หลอกลวง'),
        ('rules_violation', 'ละเมิดกฎชุมชน'),
        ('other', 'อื่นๆ'),
    ]

    STATUS_CHOICES = [
        ('pending', 'รอการตรวจสอบ'),
        ('resolved', 'ดำเนินการเรียบร้อย (ซ่อน/ลบ)'),
        ('dismissed', 'ปฏิเสธรายงาน'),
    ]

    reporter = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='reports_submitted',
        verbose_name="ผู้รายงาน"
    )
    post = models.ForeignKey(
        Post,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reports',
        verbose_name="โพสต์ที่ถูกรายงาน"
    )
    comment = models.ForeignKey(
        Comment,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reports',
        verbose_name="ความคิดเห็นที่ถูกรายงาน"
    )
    reason = models.CharField(
        max_length=50,
        choices=REASON_CHOICES,
        default='other',
        verbose_name="เหตุผลในการรายงาน"
    )
    details = models.TextField(
        blank=True,
        null=True,
        verbose_name="รายละเอียดเพิ่มเติม"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name="สถานะรายงาน"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="เวลาที่รายงาน"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="เวลาที่อัปเดต"
    )

    class Meta:
        ordering = ['-created_at']
        verbose_name = "การรายงาน"
        verbose_name_plural = "การรายงานทั้งหมด"

    def __str__(self):
        item_str = f"โพสต์ #{self.post_id}" if self.post else (f"ความคิดเห็น #{self.comment_id}" if self.comment else "รายการ")
        return f"รายงาน {item_str} โดย @{self.reporter.username} [{self.get_status_display()}]"

