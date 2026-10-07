import os
import tempfile
import unittest

os.environ['DATA_DIR'] = tempfile.mkdtemp(prefix='terra-test-')
os.environ['CRM_PASSWORD'] = 'testing-password-123'
from fastapi.testclient import TestClient
from app import app

class CRMTests(unittest.TestCase):
    def setUp(self):
        self.http = TestClient(app)
        self.headers = {'X-CRM-Request': '1'}
        self.http.post('/api/login', json={'password': os.environ['CRM_PASSWORD']})

    def test_access(self):
        anon = TestClient(app)
        self.assertEqual(anon.get('/api/clients').status_code, 401)
        self.assertEqual(anon.post('/api/login', json={'password':'wrong'}).status_code, 401)
        self.assertEqual(self.http.post('/api/clients', json={'name':'Blocked'}).status_code, 403)

    def test_client_task_document_and_restore(self):
        h = self.headers
        c = self.http.post('/api/clients', headers=h, json={'name':'Тестовый клиент', 'phone':'+7 000 000 00 00'}).json()
        cid = c['id']
        t = self.http.post('/api/tasks', headers=h, json={'title':'Собрать документы','client_id':cid,'due':'2026-10-08'}).json()
        self.assertIn(c, self.http.get('/api/clients',params={'q':'тестовый'}).json())
        c['stage']='Документы'
        self.assertEqual(self.http.put(f'/api/clients/{cid}',headers=h,json=c).json()['stage'], 'Документы')
        t['status']='Готово'
        self.assertEqual(self.http.put(f"/api/tasks/{t['id']}",headers=h,json=t).json()['status'], 'Готово')
        content=b'CRM test document'
        d = self.http.post('/api/documents',headers=h,data={'client_id':cid,'category':'Другое'},files={'file':('test.txt',content,'text/plain')}).json()
        self.assertEqual(self.http.get(f"/api/documents/{d['id']}/download").content,content)
        self.assertEqual(TestClient(app).get(f"/api/documents/{d['id']}/download").status_code,401)
        self.http.delete(f'/api/clients/{cid}',headers=h)
        self.assertEqual(self.http.get(f"/api/documents/{d['id']}/download").status_code,404)
        self.assertFalse(any(x['id']==t['id'] for x in self.http.get('/api/tasks').json()))
        self.http.post(f'/api/clients/{cid}/restore',headers=h)
        self.assertTrue(any(x['id']==t['id'] for x in self.http.get('/api/tasks').json()))
        self.assertEqual(self.http.get(f"/api/documents/{d['id']}/download").content,content)

    def test_validation(self):
        h=self.headers
        for body in [{'name':'   '},{'name':'X','stage':'bogus'},{'name':'X','amount':-1}]:
            self.assertEqual(self.http.post('/api/clients',headers=h,json=body).status_code,422)
        self.assertEqual(self.http.post('/api/tasks',headers=h,json={'title':'X','client_id':999999}).status_code,404)
        self.assertEqual(self.http.post('/api/tasks',headers=h,json={'title':'X','due':'bad-date'}).status_code,422)
        c=self.http.post('/api/clients',headers=h,json={'name':'Upload test'}).json()
        self.assertEqual(self.http.post('/api/documents',headers=h,data={'client_id':c['id']},files={'file':('bad.html',b'<html>')}).status_code,422)
        self.assertEqual(self.http.post('/api/documents',headers=h,data={'client_id':c['id']},files={'file':('empty.txt',b'')}).status_code,422)

    def test_logout(self):
        self.http.post('/api/logout',headers=self.headers)
        self.assertEqual(self.http.get('/api/me').status_code,401)

if __name__ == '__main__':
    unittest.main()
