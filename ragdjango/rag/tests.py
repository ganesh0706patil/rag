from django.test import TestCase, Client
from django.contrib.auth.models import User
from .models import UploadedFile
from django.core.files.uploadedfile import SimpleUploadedFile

class UserAuthTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='testpass')
    
    def test_register_user(self):
        response = self.client.post('/register/', {
            'first_name': 'Test',
            'last_name': 'User',
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password1': 'testpass123',
            'password2': 'testpass123'
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(User.objects.filter(username='newuser').exists())
    
    def test_login_user(self):
        response = self.client.post('/login/', {'username': 'testuser', 'password': 'testpass'})
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.wsgi_request.user.is_authenticated)
    
    def test_logout_user(self):
        self.client.login(username='testuser', password='testpass')
        response = self.client.get('/logout/')
        self.assertEqual(response.status_code, 302)
        self.assertFalse(response.wsgi_request.user.is_authenticated)

class FileUploadTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.client.login(username='testuser', password='testpass')
    
    def test_file_upload(self):
        file = SimpleUploadedFile("test.pdf", b"Dummy content")
        response = self.client.post('/upload/', {'file': file})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(UploadedFile.objects.count(), 1)
    
    def test_file_view(self):
        file = UploadedFile.objects.create(user=self.user, file='test.pdf')
        response = self.client.get('/files/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'test.pdf')
    
    def test_file_delete(self):
        file = UploadedFile.objects.create(user=self.user, file='test.pdf')
        response = self.client.post(f'/delete/{file.id}/')
        self.assertEqual(response.status_code, 302)
        self.assertFalse(UploadedFile.objects.filter(id=file.id).exists())

class SearchQueryTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.client.login(username='testuser', password='testpass')
    
    def test_search_query(self):
        response = self.client.post('/search/', {'query': 'What is financial analysis?'})
        self.assertEqual(response.status_code, 200)
        self.assertIn('response', response.context)
