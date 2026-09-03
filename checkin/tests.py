from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from checkin.models import Post, Province, Badge

class CheckinAppTests(TestCase):
    def setUp(self):
        # Seed essential test provinces and badges
        Province.objects.get_or_create(
            name_th='ภูเก็ต',
            defaults={'name_en': 'Phuket', 'svg_id': 'TH-83', 'region': 'ภาคใต้'}
        )
        Province.objects.get_or_create(
            name_th='เชียงใหม่',
            defaults={'name_en': 'Chiang Mai', 'svg_id': 'TH-50', 'region': 'ภาคเหนือ'}
        )
        Province.objects.get_or_create(
            name_th='กรุงเทพมหานคร',
            defaults={'name_en': 'Bangkok', 'svg_id': 'TH-10', 'region': 'ภาคกลาง'}
        )

        Badge.objects.get_or_create(
            code='first_checkin',
            defaults={
                'name': 'ก้าวแรกสู่นักเดินทาง',
                'description': 'โพสต์เช็คอินครั้งแรก',
                'icon': '🎯',
                'criteria_type': 'POST_COUNT',
                'criteria_config': {'min_count': 1}
            }
        )
        Badge.objects.get_or_create(
            code='cafe_hopper',
            defaults={
                'name': 'Cafe Hopper',
                'description': 'เช็คอินคาเฟ่ครบ 2 ครั้ง',
                'icon': '☕',
                'criteria_type': 'TAG_COUNT',
                'criteria_config': {'tag': 'คาเฟ่', 'min_count': 2}
            }
        )

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
        self.assertTrue(self.user.profile.display_name == 'พี่ต๊ะ สายชิล')

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
        self.assertContains(resp_blank, 'ค้นหา')

        # Search posts
        resp_post = self.client.get(reverse('search') + '?q=ภูเก็ต&type=posts')
        self.assertEqual(resp_post.status_code, 200)
        self.assertContains(resp_post, 'หาดป่าตอง ภูเก็ต')

        # Search accounts
        resp_acc = self.client.get(reverse('search') + '?q=testuser&type=accounts')
        self.assertEqual(resp_acc.status_code, 200)
        self.assertContains(resp_acc, 'testuser')

    def test_admin_dashboard_and_moderation(self):
        # Create staff user
        staff_user = User.objects.create_superuser(username='adminstaff', password='adminpassword')
        
        # Non-staff user access redirect
        self.client.login(username='testuser', password='password123')
        resp_denied = self.client.get(reverse('admin_dashboard'))
        self.assertEqual(resp_denied.status_code, 302)

        # Staff user access
        self.client.login(username='adminstaff', password='adminpassword')
        resp_admin = self.client.get(reverse('admin_dashboard'))
        self.assertEqual(resp_admin.status_code, 200)
        self.assertContains(resp_admin, 'Admin Dashboard')

        # Test submit report
        self.client.login(username='testuser', password='password123')
        resp_report = self.client.post(reverse('report_item'), {
            'item_type': 'post',
            'item_id': self.post.id,
            'reason': 'spam',
            'details': 'เนื้อหาสแปมทดสอบ'
        })
        self.assertEqual(resp_report.status_code, 302)
        
        from checkin.models import Report
        report = Report.objects.filter(post=self.post).first()
        self.assertIsNotNone(report)
        self.assertEqual(report.status, 'pending')

        # Staff resolve report (hide content)
        self.client.login(username='adminstaff', password='adminpassword')
        resp_resolve = self.client.post(reverse('admin_resolve_report', kwargs={'report_id': report.id}), {
            'action': 'hide'
        })
        self.assertEqual(resp_resolve.status_code, 302)
        report.refresh_from_db()
        self.assertEqual(report.status, 'resolved')
        self.post.refresh_from_db()
        self.assertTrue(self.post.is_hidden)

        # Staff toggle ban user
        resp_ban = self.client.post(reverse('admin_toggle_ban_user', kwargs={'user_id': self.user.id}))
        self.assertEqual(resp_ban.status_code, 302)
        self.user.profile.refresh_from_db()
        self.assertTrue(self.user.profile.is_banned)

        # Banned user cannot login
        self.client.logout()
        resp_login_banned = self.client.post(reverse('login'), {'username': 'testuser', 'password': 'password123'}, follow=True)
        self.assertContains(resp_login_banned, 'ถูกระงับการใช้งาน')

        # Test user pagination in admin dashboard (10 per page)
        for i in range(15):
            User.objects.create_user(username=f'pageuser{i}', password='password123')
        self.client.login(username='adminstaff', password='adminpassword')
        resp_page1 = self.client.get(reverse('admin_dashboard'))
        self.assertEqual(resp_page1.status_code, 200)
        self.assertEqual(len(resp_page1.context['users_list']), 10)
        self.assertTrue(resp_page1.context['users_page'].has_next())

        resp_page2 = self.client.get(reverse('admin_dashboard') + '?user_page=2')
        self.assertEqual(resp_page2.status_code, 200)
        self.assertTrue(len(resp_page2.context['users_list']) >= 5)

        # Test user search
        resp_search = self.client.get(reverse('admin_dashboard') + '?user_q=pageuser3')
        self.assertEqual(resp_search.status_code, 200)
        self.assertEqual(len(resp_search.context['users_list']), 1)
        self.assertEqual(resp_search.context['users_list'][0].username, 'pageuser3')

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

    def test_haversine_and_weather_utils(self):
        from checkin.utils import calculate_haversine_distance, get_live_weather
        
        # Test Bangkok to Phuket distance (~690 km)
        bkk_lat, bkk_lng = 13.7563, 100.5018
        hkt_lat, hkt_lng = 7.8804, 98.3923
        dist = calculate_haversine_distance(bkk_lat, bkk_lng, hkt_lat, hkt_lng)
        self.assertIsNotNone(dist)
        self.assertTrue(680 <= dist <= 710)

        # Test feed response with user coordinates (lat/lng)
        self.client.login(username='testuser', password='password123')
        resp = self.client.get(reverse('post_list') + f'?lat={bkk_lat}&lng={bkk_lng}&nearby=1')
        self.assertEqual(resp.status_code, 200)

    def test_create_and_update_place_review(self):
        self.client.login(username='testuser', password='password123')
        
        # Create new review
        res = self.client.post(
            reverse('save_review_api'),
            data={'post_id': self.post.pk, 'score': 5, 'aspect_scenery': 4, 'aspect_transport': 5, 'review_text': 'บรรยากาศดีมากๆ'},
            content_type='application/json'
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data['status'], 'success')
        self.assertTrue(data['created'])
        self.assertEqual(data['avg_rating'], 5.0)
        self.assertEqual(data['review_count'], 1)

        self.post.refresh_from_db()
        self.assertEqual(self.post.avg_rating, 5.0)
        self.assertEqual(self.post.review_count, 1)

        # Update existing review (score 3)
        res_update = self.client.post(
            reverse('save_review_api'),
            data={'post_id': self.post.pk, 'score': 3, 'aspect_scenery': 3, 'aspect_transport': 2, 'review_text': 'บรรยากาศปานกลาง'},
            content_type='application/json'
        )
        self.assertEqual(res_update.status_code, 200)
        data_update = res_update.json()
        self.assertFalse(data_update['created'])
        self.assertEqual(data_update['avg_rating'], 3.0)

        from checkin.models import PlaceReview
        self.assertEqual(PlaceReview.objects.filter(post=self.post).count(), 1)

    def test_multiple_reviews_and_avg_rating_recalculation(self):
        other_user = User.objects.create_user(username='reviewer2', password='password123')
        from checkin.models import PlaceReview

        # User 1 rates 5
        PlaceReview.objects.create(user=self.user, post=self.post, score=5)
        # User 2 rates 3
        PlaceReview.objects.create(user=other_user, post=self.post, score=3)

        self.post.refresh_from_db()
        self.assertEqual(self.post.avg_rating, 4.0)
        self.assertEqual(self.post.review_count, 2)

    def test_delete_place_review_permission_and_recalculation(self):
        from checkin.models import PlaceReview
        review = PlaceReview.objects.create(user=self.user, post=self.post, score=5)
        
        other_user = User.objects.create_user(username='other_user', password='password123')
        self.client.login(username='other_user', password='password123')

        # Other user trying to delete testuser's review -> 403
        del_res_unauth = self.client.post(reverse('delete_review_api', kwargs={'pk': review.pk}))
        self.assertEqual(del_res_unauth.status_code, 403)

        # Owner deleting review -> 200
        self.client.login(username='testuser', password='password123')
        del_res = self.client.post(reverse('delete_review_api', kwargs={'pk': review.pk}))
        self.assertEqual(del_res.status_code, 200)

        self.post.refresh_from_db()
        self.assertEqual(self.post.avg_rating, 0.0)
        self.assertEqual(self.post.review_count, 0)

    def test_top_rated_sorting(self):
        # Create post 2 with lower rating
        post2 = Post.objects.create(
            user=self.user,
            location_name='ดอยสุเทพ เชียงใหม่',
            caption='วิวสวยงามมาก',
            latitude=18.804800,
            longitude=98.921600,
            image='tinimeearai_posts/test2.jpg'
        )

        from checkin.models import PlaceReview
        PlaceReview.objects.create(user=self.user, post=self.post, score=5)
        PlaceReview.objects.create(user=self.user, post=post2, score=2)

        self.client.login(username='testuser', password='password123')
        response = self.client.get(reverse('post_list') + '?feed=top_rated')
        self.assertEqual(response.status_code, 200)
        posts_in_context = response.context['posts']
        self.assertEqual(posts_in_context[0].pk, self.post.pk)
        self.assertEqual(posts_in_context[1].pk, post2.pk)

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

    def test_report_comment(self):
        from checkin.models import Comment, Report
        other_user = User.objects.create_user(username='commenter', password='password123')
        comment = Comment.objects.create(post=self.post, user=other_user, content='ข้อความที่ไม่เหมาะสม')

        self.client.login(username='testuser', password='password123')
        response = self.client.post(reverse('report_item'), {
            'item_type': 'comment',
            'item_id': comment.id,
            'reason': 'harassment',
            'details': 'ใช้คำหยาบคาย'
        }, HTTP_X_REQUESTED_WITH='XMLHttpRequest')

        self.assertEqual(response.status_code, 200)
        self.assertTrue(Report.objects.filter(reporter=self.user, comment=comment, status='pending').exists())

    def test_report_user_profile(self):
        from checkin.models import Report
        bad_user = User.objects.create_user(username='spammer', password='password123')

        self.client.login(username='testuser', password='password123')
        response = self.client.post(reverse('report_item'), {
            'item_type': 'user',
            'item_id': bad_user.id,
            'reason': 'spam',
            'details': 'ส่งข้อความสแปมรบกวน'
        }, HTTP_X_REQUESTED_WITH='XMLHttpRequest')

        self.assertEqual(response.status_code, 200)
        self.assertTrue(Report.objects.filter(reporter=self.user, reported_user=bad_user, status='pending').exists())

    def test_cannot_report_self_profile(self):
        self.client.login(username='testuser', password='password123')
        response = self.client.post(reverse('report_item'), {
            'item_type': 'user',
            'item_id': self.user.id,
            'reason': 'other',
            'details': 'report myself'
        }, HTTP_X_REQUESTED_WITH='XMLHttpRequest')

        self.assertEqual(response.status_code, 400)

    def test_admin_resolve_user_report(self):
        from checkin.models import Report
        admin_user = User.objects.create_superuser(username='adminboss', password='password123', email='admin@test.com')
        bad_user = User.objects.create_user(username='rulebreaker', password='password123')
        report = Report.objects.create(
            reporter=self.user,
            reported_user=bad_user,
            reason='rules_violation',
            status='pending'
        )

        self.client.login(username='adminboss', password='password123')
        response = self.client.post(reverse('admin_resolve_report', kwargs={'report_id': report.id}), {
            'action': 'hide'
        }, HTTP_X_REQUESTED_WITH='XMLHttpRequest')

        self.assertEqual(response.status_code, 200)
        report.refresh_from_db()
        self.assertEqual(report.status, 'resolved')
        bad_user.profile.refresh_from_db()
        self.assertTrue(bad_user.profile.is_banned)

    def test_hidden_comment_not_visible_to_regular_users(self):
        from checkin.models import Comment, Report
        other_user = User.objects.create_user(username='spammer2', password='password123')
        comment = Comment.objects.create(post=self.post, user=other_user, content='สแปมที่ถูกแอดมินซ่อน')
        
        # Admin hides the comment
        comment.is_hidden = True
        comment.save()

        # Check total_comments ignores hidden
        self.assertEqual(self.post.total_comments, 0)

        # Regular user visits post_detail -> comment should not be in context
        self.client.login(username='testuser', password='password123')
        response = self.client.get(reverse('post_detail', kwargs={'pk': self.post.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('สแปมที่ถูกแอดมินซ่อน', response.content.decode('utf-8'))

        # Admin user visits post_detail -> hidden comment is also excluded from post discussion
        admin_user = User.objects.create_superuser(username='adminboss2', password='password123', email='admin2@test.com')
        self.client.login(username='adminboss2', password='password123')
        response_admin = self.client.get(reverse('post_detail', kwargs={'pk': self.post.pk}))
        self.assertEqual(response_admin.status_code, 200)
        self.assertNotIn('สแปมที่ถูกแอดมินซ่อน', response_admin.content.decode('utf-8'))

    def test_forgot_password_request_otp_success(self):
        from checkin.models import PasswordResetOTP
        from django.core import mail
        user_with_email = User.objects.create_user(username='travellover', password='password123', email='travel@example.com')
        
        response = self.client.post(reverse('forgot_password'), {
            'identifier': 'travel@example.com'
        })
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('verify_reset_otp'), response.url)

        # Check OTP created in DB
        otp = PasswordResetOTP.objects.filter(user=user_with_email, email='travel@example.com').first()
        self.assertIsNotNone(otp)
        self.assertEqual(len(otp.otp_code), 6)
        self.assertTrue(otp.is_valid())

        # Check email sent
        self.assertGreaterEqual(len(mail.outbox), 1)
        self.assertIn(otp.otp_code, mail.outbox[-1].body)

    def test_forgot_password_no_email_fails(self):
        user_no_email = User.objects.create_user(username='noemailuser', password='password123', email='')
        response = self.client.post(reverse('forgot_password'), {
            'identifier': 'noemailuser'
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'ยังไม่ได้ระบุอีเมล')

    def test_verify_reset_otp_success(self):
        from checkin.models import PasswordResetOTP
        user = User.objects.create_user(username='resetuser', password='oldpassword123', email='reset@example.com')
        otp = PasswordResetOTP.create_otp_for_user(user, 'reset@example.com')

        # Set session
        session = self.client.session
        session['reset_user_id'] = user.id
        session['reset_masked_email'] = 'r***t@example.com'
        session.save()

        response = self.client.post(reverse('verify_reset_otp'), {
            'otp_code': otp.otp_code,
        })
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('set_new_password'), response.url)

        # Verify OTP marked as used
        otp.refresh_from_db()
        self.assertTrue(otp.is_used)

        # Step 3: Set new password
        response2 = self.client.post(reverse('set_new_password'), {
            'new_password1': 'newpassword123',
            'new_password2': 'newpassword123'
        })
        self.assertEqual(response2.status_code, 302)
        self.assertIn(reverse('login'), response2.url)

        # Verify password changed
        user.refresh_from_db()
        self.assertTrue(user.check_password('newpassword123'))

    def test_verify_reset_otp_invalid_code_fails(self):
        from checkin.models import PasswordResetOTP
        user = User.objects.create_user(username='resetuser2', password='oldpassword123', email='reset2@example.com')
        otp = PasswordResetOTP.create_otp_for_user(user, 'reset2@example.com')

        session = self.client.session
        session['reset_user_id'] = user.id
        session.save()

        response = self.client.post(reverse('verify_reset_otp'), {
            'otp_code': '000000',
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'ไม่ถูกต้อง')

    def test_verify_reset_otp_expired_fails(self):
        from checkin.models import PasswordResetOTP
        from django.utils import timezone
        import datetime
        user = User.objects.create_user(username='expireduser', password='oldpassword123', email='expired@example.com')
        otp = PasswordResetOTP.create_otp_for_user(user, 'expired@example.com')
        # Manually set created_at back by 200 seconds (beyond 180s threshold)
        PasswordResetOTP.objects.filter(id=otp.id).update(created_at=timezone.now() - datetime.timedelta(seconds=200))

        session = self.client.session
        session['reset_user_id'] = user.id
        session.save()

        response = self.client.post(reverse('verify_reset_otp'), {
            'otp_code': otp.otp_code,
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'หมดอายุ')

    def test_verify_reset_otp_max_attempts_lockout(self):
        from checkin.models import PasswordResetOTP
        user = User.objects.create_user(username='lockoutuser', password='oldpassword123', email='lockout@example.com')
        otp = PasswordResetOTP.create_otp_for_user(user, 'lockout@example.com')
        otp.attempts = 5
        otp.save()

        session = self.client.session
        session['reset_user_id'] = user.id
        session.save()

        response = self.client.post(reverse('verify_reset_otp'), {
            'otp_code': otp.otp_code,
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'เกิน 5 ครั้ง')

    def test_verify_reset_otp_ajax_success(self):
        from checkin.models import PasswordResetOTP
        user = User.objects.create_user(username='ajaxuser', password='oldpassword123', email='ajax@example.com')
        otp = PasswordResetOTP.create_otp_for_user(user, 'ajax@example.com')

        session = self.client.session
        session['reset_user_id'] = user.id
        session.save()

        response = self.client.post(
            reverse('verify_reset_otp'),
            data={'otp_code': otp.otp_code},
            content_type='application/json',
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json().get('success'))

    def test_resend_reset_otp_api_success(self):
        from checkin.models import PasswordResetOTP
        user = User.objects.create_user(username='resenduser', password='oldpassword123', email='resend@example.com')
        otp = PasswordResetOTP.create_otp_for_user(user, 'resend@example.com')

        session = self.client.session
        session['reset_user_id'] = user.id
        session.save()

        response = self.client.post(
            reverse('resend_reset_otp'),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json().get('success'))
        # Ensure previous OTP was invalidated and new OTP generated
        otp.refresh_from_db()
        self.assertTrue(otp.is_used)

    def test_set_new_password_without_otp_fails(self):
        response = self.client.get(reverse('set_new_password'))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('forgot_password'), response.url)

    def test_delete_account_success(self):
        del_user = User.objects.create_user(username='byebyeuser', password='password123')
        self.client.login(username='byebyeuser', password='password123')

        response = self.client.post(reverse('delete_account'), {
            'password': 'password123',
            'confirmation_text': 'ลบบัญชี'
        })
        self.assertEqual(response.status_code, 302)
        self.assertFalse(User.objects.filter(username='byebyeuser').exists())

    def test_delete_account_invalid_password_fails(self):
        keep_user = User.objects.create_user(username='stayuser', password='password123')
        self.client.login(username='stayuser', password='password123')

        response = self.client.post(reverse('delete_account'), {
            'password': 'wrongpassword',
            'confirmation_text': 'ลบบัญชี'
        })
        self.assertEqual(response.status_code, 200)
        self.assertTrue(User.objects.filter(username='stayuser').exists())

    def test_pwa_offline_page(self):
        response = self.client.get(reverse('offline'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'คุณกำลังออฟไลน์')

    def test_pwa_manifest_route(self):
        response = self.client.get('/manifest.json')
        self.assertIn(response.status_code, (200, 301, 302))

    def test_pwa_service_worker_route(self):
        response = self.client.get('/sw.js')
        self.assertIn(response.status_code, (200, 301, 302))

    def test_member_login_success(self):
        response = self.client.post(reverse('login'), {
            'username': 'testuser',
            'password': 'password123'
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('post_list'))

    def test_admin_cannot_login_through_member_portal(self):
        admin_user = User.objects.create_superuser(username='superadmin', password='adminpassword123', email='admin@test.com')
        response = self.client.post(reverse('login'), {
            'username': 'superadmin',
            'password': 'adminpassword123'
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'ชื่อผู้ใช้/อีเมล หรือรหัสผ่านไม่ถูกต้อง')

    def test_member_cannot_login_through_admin_portal(self):
        response = self.client.post(reverse('admin_login'), {
            'username': 'testuser',
            'password': 'password123'
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'สิทธิ์การเข้าถึงถูกปฏิเสธ: หน้านี้สำหรับผู้ดูแลระบบเท่านั้น')

    def test_admin_login_success_through_admin_portal(self):
        admin_user = User.objects.create_superuser(username='portal_admin', password='adminpassword123', email='padmin@test.com')
        response = self.client.post(reverse('admin_login'), {
            'username': 'portal_admin',
            'password': 'adminpassword123'
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('admin_dashboard'))

    def test_user_follows_api(self):
        other_user = User.objects.create_user(username='otheruser', password='password123')
        from checkin.models import Follow
        Follow.objects.create(follower=self.user, following=other_user)

        self.client.login(username='testuser', password='password123')
        response = self.client.get(reverse('user_follows_api', kwargs={'username': 'otheruser'}))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'ok')
        self.assertEqual(data['followers_count'], 1)
        self.assertEqual(data['followers'][0]['username'], 'testuser')







