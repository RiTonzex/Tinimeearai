from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from checkin.models import Post

class CheckinAppTests(TestCase):
    def setUp(self):
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
        self.assertContains(resp_blank, 'ค้นหาและตัวกรอง')

        # Search posts
        resp_post = self.client.get(reverse('search') + '?q=ภูเก็ต&type=posts')
        self.assertEqual(resp_post.status_code, 200)
        self.assertContains(resp_post, 'หาดป่าตอง ภูเก็ต')

        # Search accounts
        resp_acc = self.client.get(reverse('search') + '?q=testuser&type=accounts')
        self.assertEqual(resp_acc.status_code, 200)
        self.assertContains(resp_acc, 'testuser')

    def test_advanced_search_and_province_filter(self):
        self.client.login(username='testuser', password='password123')

        # Test Filter by Province
        resp_prov = self.client.get(reverse('search') + '?provinces=ภูเก็ต')
        self.assertEqual(resp_prov.status_code, 200)
        self.assertContains(resp_prov, 'หาดป่าตอง ภูเก็ต')

        # Test Filter by Region (South)
        resp_reg = self.client.get(reverse('search') + '?regions=south')
        self.assertEqual(resp_reg.status_code, 200)
        self.assertContains(resp_reg, 'หาดป่าตอง ภูเก็ต')

        # Test Filter by Date Range (7days)
        resp_date = self.client.get(reverse('search') + '?date_range=7days&sort_by=popular')
        self.assertEqual(resp_date.status_code, 200)
        self.assertContains(resp_date, 'หาดป่าตอง ภูเก็ต')



