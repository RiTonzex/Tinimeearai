import os
from django.core.management.base import BaseCommand
from django.conf import settings
from checkin.models import Post, PostImage, Profile
from checkin.utils import extract_cloudinary_public_id
import cloudinary
import cloudinary.api
import cloudinary.uploader

class Command(BaseCommand):
    help = 'Scan Cloudinary for orphaned / unused images and clean them up to free storage.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Only scan and report unused images without actually deleting them.'
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Delete ALL application images from Cloudinary completely (wipe clean).'
        )
        parser.add_argument(
            '--folder',
            type=str,
            default=None,
            help='Specific Cloudinary folder prefix to scan (e.g. tinimeearai_posts or tinimeearai_avatars).'
        )

    def handle(self, *args, **options):
        dry_run = options.get('dry_run', False)
        delete_all = options.get('all', False)
        folder_prefix = options.get('folder')

        cloud_name = os.environ.get('CLOUDINARY_CLOUD_NAME') or settings.CLOUDINARY_STORAGE.get('CLOUD_NAME')
        api_key = os.environ.get('CLOUDINARY_API_KEY') or settings.CLOUDINARY_STORAGE.get('API_KEY')
        api_secret = os.environ.get('CLOUDINARY_API_SECRET') or settings.CLOUDINARY_STORAGE.get('API_SECRET')

        if not cloud_name or cloud_name in ('your_cloud_name', 'dummy_cloud_name'):
            self.stdout.write(self.style.ERROR('[ERROR] Cloudinary credentials are not configured!'))
            return

        cloudinary.config(
            cloud_name=cloud_name,
            api_key=api_key,
            api_secret=api_secret,
            secure=True
        )

        self.stdout.write(self.style.NOTICE(f'[*] Connected to Cloudinary ({cloud_name})'))

        active_ids = set()
        if not delete_all:
            self.stdout.write('[*] Collecting active image IDs from database...')
            for post in Post.objects.all():
                pid = extract_cloudinary_public_id(post.image)
                if pid:
                    active_ids.add(pid)

            for post_img in PostImage.objects.all():
                pid = extract_cloudinary_public_id(post_img.image)
                if pid:
                    active_ids.add(pid)

            for profile in Profile.objects.all():
                pid = extract_cloudinary_public_id(profile.avatar)
                if pid:
                    active_ids.add(pid)

            self.stdout.write(self.style.SUCCESS(f'[OK] Found {len(active_ids)} active image(s) referenced in database.'))
        else:
            self.stdout.write(self.style.WARNING('[!] --all flag detected: Targeting ALL application images for full wipe!'))

        # 2. ค้นหารูปทั้งหมดบน Cloudinary
        self.stdout.write('[*] Fetching media assets from Cloudinary...')
        all_cloudinary_resources = []
        next_cursor = None

        while True:
            params = {
                'resource_type': 'image',
                'type': 'upload',
                'max_results': 500,
            }
            if folder_prefix:
                params['prefix'] = folder_prefix
            if next_cursor:
                params['next_cursor'] = next_cursor

            try:
                result = cloudinary.api.resources(**params)
                resources = result.get('resources', [])
                all_cloudinary_resources.extend(resources)
                next_cursor = result.get('next_cursor')
                if not next_cursor:
                    break
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'[ERROR] Failed to query Cloudinary API: {e}'))
                return

        self.stdout.write(self.style.NOTICE(f'[*] Total assets on Cloudinary: {len(all_cloudinary_resources)}'))

        # 3. ตรวจสอบว่ารูปใดบ้างที่ไม่ได้อยู่ใน active_ids
        orphaned_resources = []
        for res in all_cloudinary_resources:
            public_id = res.get('public_id', '')
            # ข้ามรูปตัวอย่างเริ่มต้นของ Cloudinary เช่น samples/ หรือ cld-sample
            if not folder_prefix and (public_id.startswith('samples/') or public_id.startswith('cld-sample') or public_id == 'main-sample'):
                continue

            if public_id not in active_ids:
                orphaned_resources.append(res)

        if not orphaned_resources:
            self.stdout.write(self.style.SUCCESS('[OK] Great! No orphaned/unused images found in Cloudinary.'))
            return

        self.stdout.write(self.style.WARNING(
            f'\n[!] Found {len(orphaned_resources)} unused / duplicate image(s) on Cloudinary:'
        ))

        total_bytes = 0
        for res in orphaned_resources:
            pid = res.get('public_id')
            size_kb = round(res.get('bytes', 0) / 1024, 1)
            total_bytes += res.get('bytes', 0)
            self.stdout.write(f'  - {pid} ({size_kb} KB)')

        total_mb = round(total_bytes / (1024 * 1024), 2)
        self.stdout.write(f'\nTotal reclaimable storage: {total_mb} MB ({len(orphaned_resources)} files)')

        if dry_run:
            self.stdout.write(self.style.NOTICE('\n[DRY-RUN] No images were deleted. Run without --dry-run to delete them.'))
            return

        # 4. สั่งลบรูปที่ไม่ได้ใช้
        self.stdout.write(self.style.NOTICE('\n[*] Deleting orphaned images from Cloudinary...'))
        deleted_count = 0
        for res in orphaned_resources:
            pid = res.get('public_id')
            try:
                del_res = cloudinary.uploader.destroy(pid, invalidate=True)
                if del_res.get('result') in ('ok', 'not found'):
                    deleted_count += 1
                    self.stdout.write(self.style.SUCCESS(f'  [DELETED] {pid}'))
                else:
                    self.stdout.write(self.style.WARNING(f'  [SKIPPED] {pid}: {del_res.get("result")}'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'  [ERROR] {pid}: {e}'))

        self.stdout.write(self.style.SUCCESS(
            f'\n[COMPLETED] Successfully cleaned up {deleted_count}/{len(orphaned_resources)} files ({total_mb} MB freed).'
        ))
