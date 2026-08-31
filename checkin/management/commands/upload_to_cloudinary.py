import os
from pathlib import Path
from django.core.management.base import BaseCommand
from django.conf import settings
from checkin.models import Post
import cloudinary
import cloudinary.uploader

class Command(BaseCommand):
    help = 'Upload images from local media directory to Cloudinary and update database records.'

    def add_arguments(self, parser):
        parser.add_argument('--cloud_name', type=str, help='Cloudinary Cloud Name')
        parser.add_argument('--api_key', type=str, help='Cloudinary API Key')
        parser.add_argument('--api_secret', type=str, help='Cloudinary API Secret')

    def handle(self, *args, **options):
        # 1. ตรวจสอบ Cloudinary Credentials
        cloud_name = options.get('cloud_name') or os.environ.get('CLOUDINARY_CLOUD_NAME') or settings.CLOUDINARY_STORAGE.get('CLOUD_NAME')
        api_key = options.get('api_key') or os.environ.get('CLOUDINARY_API_KEY') or settings.CLOUDINARY_STORAGE.get('API_KEY')
        api_secret = options.get('api_secret') or os.environ.get('CLOUDINARY_API_SECRET') or settings.CLOUDINARY_STORAGE.get('API_SECRET')

        if not cloud_name or cloud_name in ('your_cloud_name', 'dummy_cloud_name'):
            self.stdout.write(self.style.ERROR('[ERROR] Missing Cloudinary Credentials!'))
            self.stdout.write(self.style.WARNING(
                'Please set CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, and CLOUDINARY_API_SECRET in .env file\n'
                'or pass them via command line arguments:\n'
                'python manage.py upload_to_cloudinary --cloud_name="<YOUR_NAME>" --api_key="<YOUR_KEY>" --api_secret="<YOUR_SECRET>"'
            ))
            return

        # กำหนดค่า Config ให้ Cloudinary SDK
        cloudinary.config(
            cloud_name=cloud_name,
            api_key=api_key,
            api_secret=api_secret,
            secure=True
        )

        self.stdout.write(self.style.NOTICE(f'[*] Connecting to Cloudinary: {cloud_name}...'))

        posts = Post.objects.all()
        if not posts.exists():
            self.stdout.write(self.style.WARNING('No posts found in database.'))
            return

        success_count = 0
        media_root = Path(settings.MEDIA_ROOT)

        for post in posts:
            img_str = str(post.image) if post.image else ""
            
            # ข้ามถ้าเป็น Cloudinary URL เต็มแล้ว
            if 'cloudinary.com' in img_str:
                self.stdout.write(self.style.NOTICE(f'[SKIP] "{post.location_name}" (Already on Cloudinary)'))
                continue

            # หาไฟล์บน Local Disk
            local_file_path = None
            possible_paths = [
                media_root / img_str,
                media_root / f"{img_str}.jpg",
                media_root / "tinimeearai_posts" / Path(img_str).name,
                media_root / "tinimeearai_posts" / f"{Path(img_str).name}.jpg",
            ]

            for p in possible_paths:
                if p.exists() and p.is_file():
                    local_file_path = p
                    break

            if local_file_path:
                self.stdout.write(self.style.NOTICE(f'[UPLOADING] {local_file_path.name} -> Cloudinary...'))
                try:
                    upload_result = cloudinary.uploader.upload(
                        str(local_file_path),
                        folder="tinimeearai_posts",
                        use_filename=True,
                        unique_filename=True,
                        resource_type="image"
                    )

                    public_id = upload_result.get('public_id')
                    secure_url = upload_result.get('secure_url')

                    # อัปเดต Model
                    post.image = public_id
                    post.save(update_fields=['image'])
                    success_count += 1

                    self.stdout.write(self.style.SUCCESS(
                        f'[SUCCESS] "{post.location_name}"\n'
                        f'   Public ID: {public_id}\n'
                        f'   URL: {secure_url}'
                    ))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'[FAILED] "{post.location_name}": {e}'))
            else:
                self.stdout.write(self.style.WARNING(f'[NOT FOUND] Local file for: "{post.location_name}" (path: {img_str})'))

        self.stdout.write(self.style.SUCCESS(
            f'\n[COMPLETED] Uploaded {success_count}/{posts.count()} images to Cloudinary successfully.'
        ))
