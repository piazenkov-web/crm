import concurrent.futures
import time
import unittest
import test_crm
from fastapi.testclient import TestClient
import app as crm

class FullCRMTests(unittest.TestCase):
    def setUp(self):
        crm.ATTEMPTS.clear()
        self.h = {'X-CRM-Request':'1'}
        self.http = TestClient(crm.app)
        self.assertEqual(self.http.post('/api/login',json={'password':'testing-password-123'}).status_code,200)

    def create(self, entity, body):
        r=self.http.post('/api/'+entity,headers=self.h,json=body)
        self.assertEqual(r.status_code,200,r.text)
        return r.json()

    def client(self):
        return self.create('clients',{'name':'QA Клиент','email':'qa@example.test','phone':'+7 000 000 00 01','manager':'QA'})

    def upload(self,cid,name='report.txt',content=b'QA test',category='Другое'):
        return self.http.post('/api/documents',headers=self.h,data={'client_id':cid,'category':category},files={'file':(name,content)})

    def test_all_endpoints_require_auth(self):
        anon=TestClient(crm.app)
        for method,path in [('GET','clients'),('GET','tasks'),('GET','documents'),('GET','archive'),('GET','me'),('GET','documents/1/download'),('POST','clients'),('PUT','tasks/1'),('DELETE','clients/1'),('POST','clients/1/restore')]:
            with self.subTest(path=path,method=method):
                self.assertEqual(anon.request(method,'/api/'+path,headers=self.h,json={}).status_code,401)

    def test_expired_and_forged_session(self):
        token=self.http.cookies.get('crm_session')
        crm.SESSIONS[token]=time.time()-1
        self.assertEqual(self.http.get('/api/me').status_code,401)
        self.http.cookies.set('crm_session','forged')
        self.assertEqual(self.http.get('/api/me').status_code,401)

    def test_rate_limit(self):
        anon=TestClient(crm.app)
        for _ in range(5):
            self.assertEqual(anon.post('/api/login',json={'password':'incorrect'}).status_code,401)
        self.assertEqual(anon.post('/api/login',json={'password':'incorrect'}).status_code,429)
        crm.ATTEMPTS.clear()

    def test_cookie_and_headers(self):
        response=self.http.post('/api/login',json={'password':'testing-password-123'})
        cookie=response.headers['set-cookie'].lower()
        self.assertIn('httponly',cookie)
        self.assertIn('samesite=strict',cookie)
        response=self.http.get('/api/clients')
        self.assertEqual(response.headers['cache-control'],'no-store')
        self.assertEqual(response.headers['x-content-type-options'],'nosniff')
        self.assertEqual(response.headers['x-frame-options'],'DENY')

    def test_csrf_all_mutations(self):
        for method,path in [('POST','clients'),('PUT','clients/1'),('DELETE','clients/1'),('POST','clients/1/restore'),('POST','documents'),('POST','logout')]:
            with self.subTest(path=path):
                self.assertEqual(self.http.request(method,'/api/'+path,json={}).status_code,403)

    def test_search_and_stage_filter(self):
        c=self.client()
        for q in ['qa клиент','QA@EXAMPLE.TEST','000 00 01']:
            self.assertIn(c,self.http.get('/api/clients',params={'q':q}).json())
        self.assertNotIn(c,self.http.get('/api/clients',params={'q':'not-present-unique'}).json())
        for stage in crm.STAGES:
            c=self.http.put(f"/api/clients/{c['id']}",headers=self.h,json={**c,'stage':stage}).json()
            self.assertIn(c,self.http.get('/api/clients',params={'stage':stage}).json())

    def test_limits_and_nonfinite(self):
        for body in [{'name':'x'*201},{'name':'X','phone':'x'*51},{'name':'X','notes':'x'*10001},{'name':'X','amount':'NaN'},{'name':'X','amount':'Infinity'},{'name':'X','amount':1000000000001}]:
            with self.subTest(body=str(body)[:60]):
                self.assertEqual(self.http.post('/api/clients',headers=self.h,json=body).status_code,422)
        for body in [{'title':'x'*301},{'title':'X','priority':'invalid'},{'title':'X','status':'invalid'},{'title':'X','due':'2026-02-30'}]:
            self.assertEqual(self.http.post('/api/tasks',headers=self.h,json=body).status_code,422)

    def test_email_validation(self):
        self.assertEqual(self.http.post('/api/clients',headers=self.h,json={'name':'QA','email':'not-an-email'}).status_code,422)

    def test_canonical_date_validation(self):
        for due in ['20261008','2026-W41-4']:
            self.assertEqual(self.http.post('/api/tasks',headers=self.h,json={'title':'QA','due':due}).status_code,422)

    def test_unknown_records(self):
        for entity,body in [('clients',{'name':'QA'}),('tasks',{'title':'QA'})]:
            self.assertEqual(self.http.put(f'/api/{entity}/999999',headers=self.h,json=body).status_code,404)
            self.assertEqual(self.http.delete(f'/api/{entity}/999999',headers=self.h).status_code,404)
            self.assertEqual(self.http.post(f'/api/{entity}/999999/restore',headers=self.h).status_code,404)
        self.assertEqual(self.http.delete('/api/evil/1',headers=self.h).status_code,404)

    def test_task_states_and_nullable_client(self):
        t=self.create('tasks',{'title':' QA Task ','due':'2026-10-08'})
        self.assertEqual(t['title'],'QA Task')
        self.assertIsNone(t['client_id'])
        for status in crm.STATUSES:
            for priority in ['Обычный','Высокий','Срочно']:
                t=self.http.put(f"/api/tasks/{t['id']}",headers=self.h,json={**t,'status':status,'priority':priority}).json()
                self.assertEqual(t['status'],status)
                self.assertEqual(t['priority'],priority)

    def test_independent_archives_preserved(self):
        c=self.client()
        a=self.create('tasks',{'title':'Manual archive','client_id':c['id']})
        b=self.create('tasks',{'title':'Cascade archive','client_id':c['id']})
        self.http.delete(f"/api/tasks/{a['id']}",headers=self.h)
        self.http.delete(f"/api/clients/{c['id']}",headers=self.h)
        self.http.post(f"/api/clients/{c['id']}/restore",headers=self.h)
        ids=[t['id'] for t in self.http.get('/api/tasks').json()]
        self.assertNotIn(a['id'],ids)
        self.assertIn(b['id'],ids)

    def test_document_archive_and_client_archive(self):
        c=self.client()
        d=self.upload(c['id']).json()
        self.http.delete(f"/api/documents/{d['id']}",headers=self.h)
        self.assertEqual(self.http.get(f"/api/documents/{d['id']}/download").status_code,404)
        self.http.delete(f"/api/clients/{c['id']}",headers=self.h)
        self.assertEqual(self.http.post(f"/api/documents/{d['id']}/restore",headers=self.h).status_code,404)
        self.http.post(f"/api/clients/{c['id']}/restore",headers=self.h)
        self.assertEqual(self.http.post(f"/api/documents/{d['id']}/restore",headers=self.h).status_code,200)
        self.assertEqual(self.http.get(f"/api/documents/{d['id']}/download").content,b'QA test')

    def test_upload_size_and_cleanup(self):
        c=self.client()
        before=set((crm.DATA/'files').iterdir())
        self.assertEqual(self.upload(c['id'],content=b'x'*(10*1024*1024+1)).status_code,413)
        self.assertEqual(before,set((crm.DATA/'files').iterdir()))
        self.assertEqual(self.upload(c['id'],content=b'x'*(10*1024*1024)).status_code,200)

    def test_document_type_and_category(self):
        c=self.client()
        for name in ['payload.html','payload.js','payload.exe','no-extension']:
            self.assertEqual(self.upload(c['id'],name=name).status_code,422)
        self.assertEqual(self.upload(c['id'],category='Unknown').status_code,422)
        self.assertEqual(self.upload(999999).status_code,404)

    def test_filename_normalization(self):
        c=self.client()
        for name in [r'C:\fakepath\report.txt','../../report.txt']:
            self.assertEqual(self.upload(c['id'],name=name).json()['name'],'report.txt')

    def test_sql_and_html_payload_roundtrip(self):
        name="QA <img src=x onerror=alert(1)> ' OR 1=1 --"
        c=self.create('clients',{'name':name})
        self.assertEqual(c['name'],name)
        self.assertIn(c,self.http.get('/api/clients',params={'q':name}).json())
        self.assertEqual(self.http.get('/health').status_code,200)

    def test_parallel_writes(self):
        def insert(i):
            return self.http.post('/api/clients',headers=self.h,json={'name':f'QA parallel {i}'}).status_code
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            self.assertEqual(list(pool.map(insert,range(24))),[200]*24)

    def test_static_and_traversal(self):
        for path in ['/','/app.js','/style.css','/health']:
            self.assertEqual(self.http.get(path).status_code,200)
        for path in ['/.env','/app.py','/data/crm.sqlite','/%2e%2e/app.py']:
            self.assertEqual(self.http.get(path).status_code,404)

    def test_request_limit_with_and_without_content_length(self):
        self.assertEqual(self.http.post('/api/login',content=b'x',headers={'Content-Length':str(12*1024*1024),'Content-Type':'application/json'}).status_code,413)
        def chunks():
            for _ in range(12):
                yield b'x'*(1024*1024)
        self.assertEqual(self.http.post('/api/login',content=chunks(),headers={'Content-Type':'application/json'}).status_code,413)

    def test_host_cannot_bypass_auth(self):
        anon=TestClient(crm.app)
        for host in ['localhost', 'attacker.example/#', 'attacker.example/?']:
            self.assertEqual(anon.get('/api/clients',headers={'Host':host}).status_code,401)

    def test_archived_client_rejects_new_links(self):
        c=self.client()
        self.http.delete(f"/api/clients/{c['id']}",headers=self.h)
        self.assertEqual(self.upload(c['id']).status_code,404)
        self.assertEqual(self.http.post('/api/tasks',headers=self.h,json={'title':'QA','client_id':c['id']}).status_code,404)

    def test_download_range_and_attachment(self):
        d=self.upload(self.client()['id'],content=b'1234567890').json()
        r=self.http.get(f"/api/documents/{d['id']}/download",headers={'Range':'bytes=0-3'})
        self.assertEqual(r.status_code,206)
        self.assertEqual(r.content,b'1234')
        self.assertIn('attachment',r.headers['content-disposition'])

if __name__=='__main__':
    unittest.main()
