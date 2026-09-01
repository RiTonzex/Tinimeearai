import json
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from checkin.models import Post
from .models import Collection, Bookmark


class PlannerAppTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user1 = User.objects.create_user(username='user1', password='password123')
        self.user2 = User.objects.create_user(username='user2', password='password123')
        
        self.post = Post.objects.create(
            user=self.user1,
            location_name='ดอยสุเทพ เชียงใหม่',
            caption='บรรยากาศเช้าวันใหม่บนดอยสุเทพ',
            latitude=18.804900,
            longitude=98.921600
        )

        self.private_collection = Collection.objects.create(
            user=self.user1,
            title='ทริปส่วนตัวเชียงใหม่ 2026',
            description='วางแผนเที่ยวเชียงใหม่',
            is_public=False
        )

        self.public_collection = Collection.objects.create(
            user=self.user1,
            title='ทริปคาเฟ่เชียงใหม่ สาธารณะ',
            description='คาเฟ่สวยๆ',
            is_public=True
        )

    def test_saved_collections_requires_login(self):
        response = self.client.get(reverse('saved_collections'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response.url)

    def test_saved_collections_authenticated(self):
        self.client.login(username='user1', password='password123')
        response = self.client.get(reverse('saved_collections'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'ทริปส่วนตัวเชียงใหม่ 2026')

    def test_create_collection_api(self):
        self.client.login(username='user1', password='password123')
        response = self.client.post(
            reverse('create_collection'),
            data=json.dumps({
                'title': 'ทริปภูเก็ต 2026',
                'description': 'เที่ยวทะเล 3 วัน 2 คืน',
                'is_public': True
            }),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['collection']['title'], 'ทริปภูเก็ต 2026')

        # Check DB
        self.assertTrue(Collection.objects.filter(user=self.user1, title='ทริปภูเก็ต 2026').exists())

    def test_toggle_bookmark_api(self):
        self.client.login(username='user1', password='password123')
        
        # 1. Toggle ON (General Bookmark)
        response = self.client.post(
            reverse('toggle_bookmark'),
            data=json.dumps({'post_id': self.post.id}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['bookmarked'])
        self.assertTrue(data['is_bookmarked_any'])
        self.assertTrue(Bookmark.objects.filter(user=self.user1, post=self.post, collection=None).exists())

        # 2. Toggle ON for Specific Collection
        response = self.client.post(
            reverse('toggle_bookmark'),
            data=json.dumps({'post_id': self.post.id, 'collection_id': self.private_collection.id}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['bookmarked'])
        self.assertTrue(Bookmark.objects.filter(user=self.user1, post=self.post, collection=self.private_collection).exists())

        # 3. Toggle OFF for Specific Collection
        response = self.client.post(
            reverse('toggle_bookmark'),
            data=json.dumps({'post_id': self.post.id, 'collection_id': self.private_collection.id}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertFalse(data['bookmarked'])
        self.assertFalse(Bookmark.objects.filter(user=self.user1, post=self.post, collection=self.private_collection).exists())

    def test_private_collection_permissions(self):
        # Add post to private collection
        Bookmark.objects.create(user=self.user1, post=self.post, collection=self.private_collection)

        # User2 tries to access User1's private collection map & pins -> should be forbidden (403)
        self.client.login(username='user2', password='password123')

        response_map = self.client.get(reverse('trip_map_view', kwargs={'pk': self.private_collection.pk}))
        self.assertEqual(response_map.status_code, 403)

        response_pins = self.client.get(reverse('collection_pins_api', kwargs={'pk': self.private_collection.pk}))
        self.assertEqual(response_pins.status_code, 403)

        # User1 (Owner) accesses private collection -> 200 OK
        self.client.login(username='user1', password='password123')
        
        response_owner_map = self.client.get(reverse('trip_map_view', kwargs={'pk': self.private_collection.pk}))
        self.assertEqual(response_owner_map.status_code, 200)

        response_owner_pins = self.client.get(reverse('collection_pins_api', kwargs={'pk': self.private_collection.pk}))
        self.assertEqual(response_owner_pins.status_code, 200)
        pins_data = response_owner_pins.json()
        self.assertEqual(pins_data['status'], 'ok')
        self.assertEqual(len(pins_data['pins']), 1)
        self.assertEqual(pins_data['pins'][0]['title'], 'ดอยสุเทพ เชียงใหม่')

    def test_public_collection_permissions(self):
        # Add post to public collection
        Bookmark.objects.create(user=self.user1, post=self.post, collection=self.public_collection)

        # User2 accesses User1's public collection map & pins -> 200 OK
        self.client.login(username='user2', password='password123')

        response_map = self.client.get(reverse('trip_map_view', kwargs={'pk': self.public_collection.pk}))
        self.assertEqual(response_map.status_code, 200)

        response_pins = self.client.get(reverse('collection_pins_api', kwargs={'pk': self.public_collection.pk}))
        self.assertEqual(response_pins.status_code, 200)
        pins_data = response_pins.json()
        self.assertEqual(pins_data['status'], 'ok')
        self.assertEqual(len(pins_data['pins']), 1)

    def test_delete_collection_permissions(self):
        # User2 tries to delete User1's collection -> 403
        self.client.login(username='user2', password='password123')
        response = self.client.post(reverse('delete_collection', kwargs={'pk': self.private_collection.pk}))
        self.assertEqual(response.status_code, 403)
        self.assertTrue(Collection.objects.filter(pk=self.private_collection.pk).exists())

        # User1 (Owner) deletes collection -> 200 & deleted from DB
        self.client.login(username='user1', password='password123')
        response_owner = self.client.post(reverse('delete_collection', kwargs={'pk': self.private_collection.pk}))
        self.assertEqual(response_owner.status_code, 200)
        self.assertFalse(Collection.objects.filter(pk=self.private_collection.pk).exists())

    def test_edit_collection_api(self):
        self.client.login(username='user1', password='password123')
        response = self.client.post(
            reverse('edit_collection', kwargs={'pk': self.private_collection.pk}),
            data=json.dumps({
                'title': 'ทริปเชียงใหม่ 2026 แก้ไขแล้ว',
                'description': 'คำอธิบายใหม่',
                'is_public': True
            }),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        self.private_collection.refresh_from_db()
        self.assertEqual(self.private_collection.title, 'ทริปเชียงใหม่ 2026 แก้ไขแล้ว')
        self.assertTrue(self.private_collection.is_public)

