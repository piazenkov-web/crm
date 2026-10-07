"""Non-destructive HTTP checks. Only creates and archives its own QA fixtures."""
import concurrent.futures
import getpass
import http.cookiejar
import json
import os
import statistics
import time
import urllib.error
import urllib.request

BASE=os.environ.get('CRM_QA_URL','http://144.31.34.131:8080').rstrip('/')
PASSWORD=os.environ.get('CRM_QA_PASSWORD') or getpass.getpass('CRM QA password: ')
jar=http.cookiejar.CookieJar()
http=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
checks=[]
fixtures=[]

def request(path,method='GET',body=None,headers=None,anonymous=False):
    h={'X-CRM-Request':'1',**(headers or {})}
    if isinstance(body,dict):
        body=json.dumps(body).encode()
        h['Content-Type']='application/json'
    req=urllib.request.Request(BASE+path,data=body,headers=h,method=method)
    try:
        r=(urllib.request.urlopen if anonymous else http.open)(req,timeout=20)
    except urllib.error.HTTPError as e:
        r=e
    return r.status,r.read(),dict(r.headers)

def check(name,condition):
    if not condition:
        raise AssertionError(name)
    checks.append(name)

def data(path):
    status,body,_=request('/api/'+path)
    check('GET '+path,status==200)
    return json.loads(body)

try:
    check('anonymous access rejected',request('/api/clients',anonymous=True)[0]==401)
    check('login',request('/api/login','POST',{'password':PASSWORD})[0]==200)
    if BASE.startswith('https://'):
        check('secure session cookie',all(cookie.secure for cookie in jar))
    baseline={e:[x['id'] for x in data(e)] for e in ['clients','tasks','documents']}
    status,body,_=request('/api/clients','POST',{'name':'QA smoke '+str(int(time.time())),'email':'qa@example.com','amount':1234567})
    check('create client',status==200)
    c=json.loads(body); fixtures.append(('clients',c['id']))
    c['stage']='Документы'
    check('update client',request('/api/clients/'+str(c['id']),'PUT',c)[0]==200)
    status,body,_=request('/api/tasks','POST',{'title':'QA smoke task','client_id':c['id'],'due':'2026-10-08'})
    check('create task',status==200)
    t=json.loads(body); fixtures.append(('tasks',t['id']))
    t['status']='Готово'
    check('complete task',request('/api/tasks/'+str(t['id']),'PUT',t)[0]==200)
    check('email rejected',request('/api/clients','POST',{'name':'QA invalid','email':'wrong'})[0]==422)
    check('date rejected',request('/api/tasks','POST',{'title':'QA invalid','due':'20261008'})[0]==422)
    boundary='terra-qa-boundary'
    payload=b'Synthetic CRM QA. No personal data.\n'
    multipart=(f'--{boundary}\r\nContent-Disposition: form-data; name="client_id"\r\n\r\n{c["id"]}\r\n--{boundary}\r\nContent-Disposition: form-data; name="category"\r\n\r\nДругое\r\n--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="qa-smoke.txt"\r\nContent-Type: text/plain\r\n\r\n'.encode()+payload+f'\r\n--{boundary}--\r\n'.encode())
    status,body,_=request('/api/documents','POST',multipart,{'Content-Type':'multipart/form-data; boundary='+boundary})
    check('upload',status==200)
    d=json.loads(body); fixtures.append(('documents',d['id']))
    path='/api/documents/'+str(d['id'])+'/download'
    check('download byte equality',request(path)[1]==payload)
    check('anonymous download rejected',request(path,anonymous=True)[0]==401)
    check('archive client',request('/api/clients/'+str(c['id']),'DELETE')[0]==200)
    check('linked document hidden',request(path)[0]==404)
    check('restore client',request('/api/clients/'+str(c['id'])+'/restore','POST')[0]==200)
    check('linked document restored',request(path)[1]==payload)
    cookie='; '.join(x.name+'='+x.value for x in jar)
    def read_latency(i):
        started=time.perf_counter()
        req=urllib.request.Request(BASE+'/api/clients',headers={'Cookie':cookie})
        with urllib.request.urlopen(req,timeout=20) as r:
            assert r.status==200
            r.read()
        return 1000*(time.perf_counter()-started)
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
        latency=list(pool.map(read_latency,range(50)))
    check('50 reads, concurrency 5',len(latency)==50)
finally:
    for entity,id in reversed(fixtures):
        request(f'/api/{entity}/{id}','DELETE')

for entity,ids in baseline.items():
    check('baseline unchanged: '+entity,[x['id'] for x in data(entity)]==ids)
report=json.dumps({'passed':len(checks),'checks':checks,'requests':50,'concurrency':5,'latency_ms':{'median':round(statistics.median(latency),1),'p95':round(sorted(latency)[47],1),'max':round(max(latency),1)},'cleanup':'Own QA fixtures archived; existing records unchanged'},ensure_ascii=False,indent=2)
if os.environ.get('CRM_QA_REPORT'):
    from pathlib import Path
    Path(os.environ['CRM_QA_REPORT']).write_text(report,encoding='utf-8')
print(report)
