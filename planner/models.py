from django.db import models
from django.contrib.auth.models import User
from checkin.models import Post


class Collection(models.Model):
    """
    Model สำหรับเก็บข้อมูลคอลเลกชัน / โฟลเดอร์ทริปการเดินทาง
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='collections',
        verbose_name="เจ้าของคอลเลกชัน"
    )
    title = models.CharField(
        max_length=150,
        verbose_name="ชื่อคอลเลกชัน/ทริป"
    )
    description = models.TextField(
        blank=True,
        null=True,
        verbose_name="คำอธิบาย"
    )
    is_public = models.BooleanField(
        default=False,
        verbose_name="เปิดเป็นสาธารณะ"
    )
    cover_image = models.ImageField(
        upload_to='collection_covers/',
        blank=True,
        null=True,
        verbose_name="รูปปกคอลเลกชัน"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="สร้างเมื่อ"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="แก้ไขล่าสุด"
    )

    class Meta:
        ordering = ['-updated_at']
        verbose_name = "คอลเลกชันทริป"
        verbose_name_plural = "คอลเลกชันทริปทั้งหมด"

    def __str__(self):
        visibility = "Public" if self.is_public else "Private"
        return f"{self.title} ({visibility}) - {self.user.username}"

    @property
    def posts_count(self):
        return self.bookmarks.count()

    @property
    def pins_count(self):
        return self.bookmarks.filter(
            post__latitude__isnull=False,
            post__longitude__isnull=False
        ).count()

    def get_cover_image_url(self):
        """
        ดึงรูปหน้าปกของคอลเลกชัน หากมีอัปโหลดใช้รูปอัปโหลด หากไม่มีให้ใช้ออกแบบจากโพสต์แรกในคอลเลกชัน
        """
        if self.cover_image:
            return self.cover_image.url
        DEFAULT_COVER = "https://images.unsplash.com/photo-1488646953014-85cb44e25828?w=800&auto=format&fit=crop&q=80"
        first_bookmark = self.bookmarks.select_related('post').first()
        if first_bookmark and first_bookmark.post:
            return first_bookmark.post.get_image_url()
        return DEFAULT_COVER


class Bookmark(models.Model):
    """
    Model สำหรับเก็บข้อมูลการบันทึกโพสต์ของผู้ใช้ (Bookmark / Saved Post)
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='bookmarks',
        verbose_name="ผู้บันทึก"
    )
    post = models.ForeignKey(
        Post,
        on_delete=models.CASCADE,
        related_name='bookmarks',
        verbose_name="โพสต์ที่บันทึก"
    )
    collection = models.ForeignKey(
        Collection,
        on_delete=models.CASCADE,
        related_name='bookmarks',
        null=True,
        blank=True,
        verbose_name="คอลเลกชัน/ทริป"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="บันทึกเมื่อ"
    )

    class Meta:
        ordering = ['-created_at']
        verbose_name = "โพสต์ที่บันทึก"
        verbose_name_plural = "โพสต์ที่บันทึกทั้งหมด"
        unique_together = ('user', 'post', 'collection')
        indexes = [
            models.Index(fields=['user', 'collection']),
        ]

    def __str__(self):
        col_str = self.collection.title if self.collection else "บันทึกทั่วไป"
        return f"{self.user.username} saved Post #{self.post_id} in {col_str}"
