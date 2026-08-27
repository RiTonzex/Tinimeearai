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

    def test_post_list_view(self):
        response = self.client.get(reverse('post_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'หาดป่าตอง ภูเก็ต')

    def test_post_detail_view(self):
        response = self.client.get(reverse('post_detail', kwargs={'pk': self.post.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'หาดป่าตอง ภูเก็ต')

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
        response = self.client.get(reverse('api_posts'))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'ok')
        self.assertTrue(len(data['posts']) >= 1)
