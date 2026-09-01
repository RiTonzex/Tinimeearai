from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from checkin.models import Post
import sys
sys.path.append('C:/Users/user/.gemini/antigravity-ide/brain/28862728-01d7-4353-adec-e830d56eae93/scratch')
import seed_provinces_and_badges

class CheckinAppTests(TestCase):
    def setUp(self):
        seed_provinces_and_badges.seed_provinces()
        seed_provinces_and_badges.seed_badges()
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='password123')
        self.post = Post.objects.create(
            user=self.user,
            location_name='หาดป่าตอง ภูเก็ต',
            caption='ทะเลสวยงามมาก น้ำใส ท้องฟ้าแจ่มใส',
            latitude=7.897800,
            longitude=98.298000,
            image='tinimeearai_posts/test.jpg'
        )

    def test_post_list_requires_login(self):
        response = self.client.get(reverse('post_list'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response.url)

    def test_post_list_authenticated(self):
        self.client.login(username='testuser', password='password123')
        response = self.client.get(reverse('post_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'หาดป่าตอง ภูเก็ต')

    def test_post_detail_requires_login(self):
        response = self.client.get(reverse('post_detail', kwargs={'pk': self.post.pk}))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response.url)

    def test_post_detail_authenticated(self):
        self.client.login(username='testuser', password='password123')
        response = self.client.get(reverse('post_detail', kwargs={'pk': self.post.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'หาดป่าตอง ภูเก็ต')

    def test_settings_view_requires_login(self):
        response = self.client.get(reverse('settings'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response.url)

    def test_settings_view_authenticated(self):
        self.client.login(username='testuser', password='password123')
        response = self.client.get(reverse('settings'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'ตั้งค่า')
        self.assertContains(response, 'testuser')

    def test_create_post_requires_login(self):
        response = self.client.get(reverse('create_post'))
        self.assertEqual(response.status_code, 302)  # Redirects to login

    def test_create_post_authenticated(self):
        self.client.login(username='testuser', password='password123')
        response = self.client.get(reverse('create_post'))
        self.assertEqual(response.status_code, 200)

    def test_toggle_like(self):
        self.client.login(username='testuser', password='password123')
        response = self.client.post(reverse('toggle_like', kwargs={'pk': self.post.pk}))
        self.assertEqual(response.status_code, 302)
        self.post.refresh_from_db()
        self.assertEqual(self.post.total_likes, 1)

    def test_api_posts(self):
        self.client.login(username='testuser', password='password123')
        response = self.client.get(reverse('api_posts'))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'ok')
        self.assertTrue(len(data['posts']) >= 1)

    def test_registration_short_password_thai_error(self):
        response = self.client.post(reverse('register'), {
            'username': 'newuser1',
            'password': '123',
            'password_confirm': '123'
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'รหัสผ่านต้องมีความยาวอย่างน้อย 8 ตัวอักษร')

    def test_registration_mismatch_password_thai_error(self):
        response = self.client.post(reverse('register'), {
            'username': 'newuser2',
            'password': 'password1234',
            'password_confirm': 'mismatch5678'
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'รหัสผ่านและยืนยันรหัสผ่านไม่ตรงกัน')

    def test_registration_numeric_password_thai_error(self):
        response = self.client.post(reverse('register'), {
            'username': 'newuser3',
            'password': '987654321',
            'password_confirm': '987654321'
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'รหัสผ่านต้องไม่เป็นตัวเลขเพียงอย่างเดียว')

    def test_registration_success(self):
        response = self.client.post(reverse('register'), {
            'username': 'gooduser',
            'password': 'good_password123',
            'password_confirm': 'good_password123'
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(User.objects.filter(username='gooduser').exists())

    def test_settings_update_profile(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        self.client.login(username='testuser', password='password123')
        avatar_file = SimpleUploadedFile(
            name='test_avatar.jpg',
            content=b'\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff\x21\xf9\x04\x01\x00\x00\x00\x00\x2c\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02\x44\x01\x00\x3b',
            content_type='image/jpeg'
        )
        response = self.client.post(reverse('settings_profile'), {
            'avatar': avatar_file,
            'display_name': 'พี่ต๊ะ สายชิล',
            'bio': 'ชอบถ่ายรูปและปักหมุดคาเฟ่ ☕',
            'first_name': 'Somchai',
            'last_name': 'Traveler',
            'email': 'somchai@example.com'
        })
        self.assertEqual(response.status_code, 302)
        self.user.refresh_from_db()
        self.assertEqual(self.user.profile.display_name, 'พี่ต๊ะ สายชิล')
        self.assertEqual(self.user.profile.bio, 'ชอบถ่ายรูปและปักหมุดคาเฟ่ ☕')
        self.assertEqual(self.user.first_name, 'Somchai')
        self.assertEqual(self.user.email, 'somchai@example.com')
        self.assertTrue(bool(self.user.profile.avatar))

    def test_user_public_profile_view(self):
        self.client.login(username='testuser', password='password123')
        response = self.client.get(reverse('user_profile', kwargs={'username': 'testuser'}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'testuser')
        self.assertContains(response, 'หาดป่าตอง ภูเก็ต')

    def test_settings_change_password_page(self):
        self.client.login(username='testuser', password='password123')
        # GET page
        response = self.client.get(reverse('settings_password'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'ความปลอดภัยและรหัสผ่าน')
        self.assertContains(response, 'รหัสผ่านปัจจุบัน')
        self.assertContains(response, 'เปลี่ยนรหัสผ่านใหม่')

        # POST change password
        post_response = self.client.post(reverse('settings_password'), {
            'old_password': 'password123',
            'new_password1': 'newSecurePass888',
            'new_password2': 'newSecurePass888'
        })
        self.assertEqual(post_response.status_code, 302)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('newSecurePass888'))

    def test_settings_subpages(self):
        self.client.login(username='testuser', password='password123')
        for view_name in ['settings_gps', 'settings_map', 'settings_data', 'settings_about']:
            resp = self.client.get(reverse(view_name))
            self.assertEqual(resp.status_code, 200)

    def test_export_user_data(self):
        self.client.login(username='testuser', password='password123')
        response = self.client.get(reverse('export_user_data'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('tinimeearai_backup_testuser.json', response['Content-Disposition'])
        data = response.json()
        self.assertEqual(data['username'], 'testuser')
        self.assertEqual(len(data['posts']), 1)

    def test_add_comment(self):
        self.client.login(username='testuser', password='password123')
        response = self.client.post(reverse('add_comment', kwargs={'pk': self.post.pk}), {
            'content': 'โคตรเฟี้ยววว มุมถ่ายรูปอย่างตึง 🔥'
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.post.comments.count(), 1)
        comment = self.post.comments.first()
        self.assertEqual(comment.user, self.user)
        self.assertEqual(comment.content, 'โคตรเฟี้ยววว มุมถ่ายรูปอย่างตึง 🔥')

    def test_delete_own_comment(self):
        from checkin.models import Comment
        comment = Comment.objects.create(post=self.post, user=self.user, content='อยากลองไปจังคับ')
        self.client.login(username='testuser', password='password123')
        response = self.client.get(reverse('delete_comment', kwargs={'pk': self.post.pk, 'comment_id': comment.pk}))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Comment.objects.filter(pk=comment.pk).exists())

    def test_toggle_comment_like(self):
        from checkin.models import Comment
        comment = Comment.objects.create(post=self.post, user=self.user, content='โคตรเฟี้ยววว')
        self.client.login(username='testuser', password='password123')
        
        # Like
        response = self.client.post(
            reverse('toggle_comment_like', kwargs={'pk': self.post.pk, 'comment_id': comment.pk}),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['liked'], True)
        self.assertEqual(response.json()['total_likes'], 1)
        self.assertTrue(comment.likes.filter(id=self.user.id).exists())

        # Unlike
        response2 = self.client.post(
            reverse('toggle_comment_like', kwargs={'pk': self.post.pk, 'comment_id': comment.pk}),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(response2.status_code, 200)
        self.assertEqual(response2.json()['liked'], False)
        self.assertEqual(response2.json()['total_likes'], 0)
        self.assertFalse(comment.likes.filter(id=self.user.id).exists())

    def test_notification_flow(self):
        from checkin.models import Notification, Comment
        other_user = User.objects.create_user(username='otheruser', password='password123')
        self.client.login(username='otheruser', password='password123')

        # Other user likes testuser's post
        self.client.post(reverse('toggle_like', kwargs={'pk': self.post.pk}))
        self.assertTrue(Notification.objects.filter(recipient=self.user, verb='like_post', actor=other_user).exists())

        # Other user comments on testuser's post
        self.client.post(reverse('add_comment', kwargs={'pk': self.post.pk}), {'content': 'สุดจัดปลัดบอก!'})
        comment_notif = Notification.objects.filter(recipient=self.user, verb='comment_post', actor=other_user).first()
        self.assertIsNotNone(comment_notif)

        # Login as testuser to view notifications
        self.client.login(username='testuser', password='password123')
        resp = self.client.get(reverse('notifications'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'การแจ้งเตือน')

        # Mark single notification as read
        read_resp = self.client.get(reverse('mark_notification_read', kwargs={'pk': comment_notif.pk}))
        self.assertEqual(read_resp.status_code, 302)
        comment_notif.refresh_from_db()
        self.assertTrue(comment_notif.is_read)

        # Mark all read
        all_read_resp = self.client.post(reverse('mark_all_notifications_read'), HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(all_read_resp.status_code, 200)
        self.assertEqual(Notification.objects.filter(recipient=self.user, is_read=False).count(), 0)

    def test_search_view_posts_and_accounts(self):
        self.client.login(username='testuser', password='password123')
        
        # Search blank
        resp_blank = self.client.get(reverse('search'))
        self.assertEqual(resp_blank.status_code, 200)
        self.assertContains(resp_blank, 'ค้นพบสถานที่หรือเพื่อนใหม่')

        # Search posts
        resp_post = self.client.get(reverse('search') + '?q=ภูเก็ต&type=posts')
        self.assertEqual(resp_post.status_code, 200)
        self.assertContains(resp_post, 'หาดป่าตอง ภูเก็ต')

        # Search accounts
        resp_acc = self.client.get(reverse('search') + '?q=testuser&type=accounts')
        self.assertEqual(resp_acc.status_code, 200)
        self.assertContains(resp_acc, 'testuser')

    def test_user_search_api(self):
        friend = User.objects.create_user(username='friend_user', password='password123')
        self.client.login(username='testuser', password='password123')
        
        response = self.client.get(reverse('user_search_api') + '?q=friend')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'ok')
        self.assertEqual(len(data['users']), 1)
        self.assertEqual(data['users'][0]['username'], 'friend_user')

    from unittest.mock import patch

    @patch('cloudinary.uploader.upload_resource', return_value='tinimeearai_posts/test.jpg')
    def test_create_post_with_tagged_users_and_notifications(self, mock_upload):
        from checkin.models import Notification
        from django.core.files.uploadedfile import SimpleUploadedFile
        friend1 = User.objects.create_user(username='friend1', password='password123')
        friend2 = User.objects.create_user(username='friend2', password='password123')
        self.client.login(username='testuser', password='password123')

        small_png = (
            b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4'
            b'\x00\x00\x00\rIDATx\x9cc\xf8\xff\xff?\x03\x00\x05\xfe\x02\xfe\xa7\x35\x81\x84\x00\x00\x00\x00IEND\xaeB`\x82'
        )
        img = SimpleUploadedFile("test_tag.png", small_png, content_type="image/png")

        response = self.client.post(reverse('create_post'), {
            'location_name': 'เกาะพีพี',
            'caption': 'ทริปดำน้ำสุดฟินกับแก๊งเพื่อน',
            'image': img,
            'tagged_user_ids': [friend1.id, friend2.id]
        })
        self.assertEqual(response.status_code, 302)
        
        new_post = Post.objects.filter(location_name='เกาะพีพี').first()
        self.assertIsNotNone(new_post)
        self.assertEqual(new_post.tagged_users.count(), 2)
        self.assertTrue(new_post.tagged_users.filter(id=friend1.id).exists())

        # Check notifications generated for friend1 and friend2
        self.assertTrue(Notification.objects.filter(recipient=friend1, verb='post_tagged', actor=self.user, post=new_post).exists())
        self.assertTrue(Notification.objects.filter(recipient=friend2, verb='post_tagged', actor=self.user, post=new_post).exists())

    def test_edit_post_tagged_users_diff_notifications(self):
        from checkin.models import Notification
        friend1 = User.objects.create_user(username='friend_a', password='password123')
        friend2 = User.objects.create_user(username='friend_b', password='password123')
        self.post.tagged_users.add(friend1)
        
        self.client.login(username='testuser', password='password123')

        # Edit post, keep friend1, add friend2
        response = self.client.post(reverse('post_edit', kwargs={'pk': self.post.pk}), {
            'location_name': self.post.location_name,
            'caption': 'แก้ไขข้อความเพิ่มเติม',
            'tagged_user_ids': [friend1.id, friend2.id]
        })
        self.assertEqual(response.status_code, 302)

        # friend2 should get notification, but friend1 should NOT get a new duplicate notification
        self.assertFalse(Notification.objects.filter(recipient=friend1, verb='post_tagged', post=self.post).exists())
        self.assertTrue(Notification.objects.filter(recipient=friend2, verb='post_tagged', post=self.post).exists())

    def test_profile_tagged_posts_query(self):
        friend = User.objects.create_user(username='tagged_friend', password='password123')
        self.post.tagged_users.add(friend)

        self.client.login(username='tagged_friend', password='password123')
        response = self.client.get(reverse('user_profile', kwargs={'username': 'tagged_friend'}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'ถูกแท็ก (1)')

    def test_user_footprint_api(self):
        from checkin.models import Province
        prov_phuket = Province.objects.filter(svg_id='TH-83').first()
        if prov_phuket:
            self.post.province = prov_phuket
            self.post.save()

        self.client.login(username='testuser', password='password123')
        response = self.client.get(reverse('user_footprint_api', kwargs={'username': 'testuser'}))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'ok')
        self.assertIn('TH-83', data['visited'])
        self.assertEqual(data['visited_count'], 1)

    def test_badge_evaluation_and_unlock(self):
        from checkin.models import Badge, UserBadge, Notification
        from checkin.views import evaluate_badges_for_user

        # Create sample post for Cafe Hopper & First Step
        Post.objects.create(
            user=self.user,
            location_name='คาเฟ่ อเมซอน เชียงใหม่',
            caption='จิบกาแฟสดบรรยากาศธรรมชาติ #คาเฟ่',
            tags='คาเฟ่, ธรรมชาติ',
            image='tinimeearai_posts/test.jpg'
        )
        Post.objects.create(
            user=self.user,
            location_name='Starbucks คาเฟ่ กรุงเทพ',
            caption='คาเฟ่สวยงาม #คาเฟ่',
            tags='คาเฟ่',
            image='tinimeearai_posts/test.jpg'
        )

        unlocked = evaluate_badges_for_user(self.user)
        self.assertTrue(UserBadge.objects.filter(user=self.user, badge__code='first_checkin').exists())
        self.assertTrue(UserBadge.objects.filter(user=self.user, badge__code='cafe_hopper').exists())
        self.assertTrue(Notification.objects.filter(recipient=self.user, verb='badge_unlocked').exists())

    def test_duplicate_badge_prevention(self):
        from checkin.models import Badge, UserBadge
        from checkin.views import evaluate_badges_for_user

        evaluate_badges_for_user(self.user)
        initial_badge_count = UserBadge.objects.filter(user=self.user).count()

        # Re-evaluate
        evaluate_badges_for_user(self.user)
        self.assertEqual(UserBadge.objects.filter(user=self.user).count(), initial_badge_count)

    def test_user_badges_api(self):
        from checkin.views import evaluate_badges_for_user
        evaluate_badges_for_user(self.user)

        self.client.login(username='testuser', password='password123')
        response = self.client.get(reverse('user_badges_api', kwargs={'username': 'testuser'}))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'ok')
        self.assertTrue(data['unlocked_count'] >= 1)
        self.assertTrue(len(data['badges']) >= 1)


