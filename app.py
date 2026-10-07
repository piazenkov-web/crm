import hashlib
import hmac
import os
import secrets
import sqlite3
import threading
import time
from contextlib import contextmanager
from pathlib import Path

from fastapi import FastAPI, Request, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

DATA = Path(os.getenv('DATA_DIR', 'data'))
DATA.mkdir(parents=True, exist_ok=True)
(DATA / 'files').mkdir(exist_ok=True)
DB = DATA / 'crm.sqlite'
PASSWORD = os.environ['CRM_PASSWORD']
SALT = secrets.token_bytes(32)
PASSWORD_HASH = hashlib.pbkdf2_hmac('sha256', PASSWORD.encode(), SALT, 200000)
SESSIONS = {}
ATTEMPTS = {}
LOCK = threading.Lock()
STAGES = ['Новый лид', 'В работе', 'Документы', 'В банке', 'Одобрено', 'Сделка', 'Отказ']
STATUSES = ['Новая', 'В работе', 'Готово']
app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

@contextmanager
def db():
    con = sqlite3.connect(DB, timeout=15)
    con.row_factory = sqlite3.Row
    con.execute('PRAGMA foreign_keys=ON')
    try:
        with con:
            yield con
    finally:
        con.close()

with db() as c:
    c.executescript('''
    PRAGMA journal_mode=WAL;
    CREATE TABLE IF NOT EXISTS clients(id INTEGER PRIMARY KEY, name TEXT NOT NULL, phone TEXT NOT NULL DEFAULT '', email TEXT NOT NULL DEFAULT '', stage TEXT NOT NULL, manager TEXT NOT NULL DEFAULT '', amount REAL NOT NULL DEFAULT 0, notes TEXT NOT NULL DEFAULT '', created TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, deleted INTEGER NOT NULL DEFAULT 0);
    CREATE TABLE IF NOT EXISTS tasks(id INTEGER PRIMARY KEY, title TEXT NOT NULL, client_id INTEGER REFERENCES clients(id), due TEXT NOT NULL DEFAULT '', priority TEXT NOT NULL, status TEXT NOT NULL, notes TEXT NOT NULL DEFAULT '', created TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, deleted INTEGER NOT NULL DEFAULT 0);
    CREATE TABLE IF NOT EXISTS documents(id INTEGER PRIMARY KEY, client_id INTEGER NOT NULL REFERENCES clients(id), name TEXT NOT NULL, storage TEXT NOT NULL UNIQUE, size INTEGER NOT NULL, category TEXT NOT NULL, created TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, deleted INTEGER NOT NULL DEFAULT 0);
    ''')

@app.middleware('http')
async def auth(request: Request, call_next):
    if request.url.path.startswith('/api/') and request.url.path != '/api/login':
        token = request.cookies.get('crm_session', '')
        with LOCK:
            expires = SESSIONS.get(token, 0)
        if expires < time.time():
            return JSONResponse({'detail': 'Войдите в систему'}, status_code=401)
        if request.method not in ('GET', 'HEAD') and request.headers.get('x-crm-request') != '1':
            return JSONResponse({'detail': 'Недопустимый запрос'}, status_code=403)
    response = await call_next(request)
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['Referrer-Policy'] = 'no-referrer'
    response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
    if request.url.path.startswith('/api/'):
        response.headers['Cache-Control'] = 'no-store'
    return response

class Login(BaseModel):
    password: str = Field(max_length=256)

@app.post('/api/login')
def login(body: Login, request: Request):
    ip = request.client.host
    now = time.time()
    with LOCK:
        ATTEMPTS[ip] = [t for t in ATTEMPTS.get(ip, []) if t > now - 60]
        if len(ATTEMPTS[ip]) >= 5:
            raise HTTPException(429, 'Слишком много попыток. Подождите минуту.')
        ATTEMPTS[ip].append(now)
    candidate = hashlib.pbkdf2_hmac('sha256', body.password.encode(), SALT, 200000)
    if not hmac.compare_digest(candidate, PASSWORD_HASH):
        raise HTTPException(401, 'Неверный пароль')
    token = secrets.token_urlsafe(32)
    with LOCK:
        for key in list(SESSIONS):
            if SESSIONS[key] < now:
                del SESSIONS[key]
        SESSIONS[token] = now + 43200
        ATTEMPTS.pop(ip, None)
    response = JSONResponse({'ok': True})
    response.set_cookie('crm_session', token, httponly=True, samesite='strict', max_age=43200, secure=request.url.scheme == 'https')
    return response

@app.post('/api/logout')
def logout(request: Request):
    with LOCK:
        SESSIONS.pop(request.cookies.get('crm_session', ''), None)
    response = JSONResponse({'ok': True})
    response.delete_cookie('crm_session')
    return response

@app.get('/api/me')
def me():
    return {'name': 'Администратор', 'stages': STAGES}

class Client(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    phone: str = Field(default='', max_length=50)
    email: str = Field(default='', max_length=200)
    stage: str = 'Новый лид'
    manager: str = Field(default='', max_length=100)
    amount: float = Field(default=0, ge=0, le=1e12, allow_inf_nan=False)
    notes: str = Field(default='', max_length=10000)

class Task(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    client_id: int | None = None
    due: str = ''
    priority: str = 'Обычный'
    status: str = 'Новая'
    notes: str = Field(default='', max_length=10000)

def client_exists(c, client_id):
    if not c.execute('SELECT id FROM clients WHERE id=? AND deleted=0', (client_id,)).fetchone():
        raise HTTPException(404, 'Клиент не найден')

@app.get('/api/clients')
def clients(q: str = '', stage: str = ''):
    with db() as c:
        rows = [dict(r) for r in c.execute('SELECT * FROM clients WHERE deleted=0 ORDER BY id DESC')]
    query = q.casefold().strip()
    return [r for r in rows if (not stage or r['stage'] == stage) and (not query or query in ' '.join(str(r[k]) for k in ('name','phone','email','manager')).casefold())]

@app.get('/api/tasks')
def tasks():
    with db() as c:
        return [dict(r) for r in c.execute('SELECT t.*, c.name client_name FROM tasks t LEFT JOIN clients c ON c.id=t.client_id WHERE t.deleted=0 ORDER BY t.id DESC')]

@app.get('/api/documents')
def documents():
    with db() as c:
        return [dict(r) for r in c.execute('SELECT d.id,d.client_id,d.name,d.size,d.category,d.created,c.name client_name FROM documents d JOIN clients c ON c.id=d.client_id WHERE d.deleted=0 AND c.deleted=0 ORDER BY d.id DESC')]

@app.get('/api/archive')
def archived():
    with db() as c:
        result = []
        for entity, title in [('clients','name'),('tasks','title'),('documents','name')]:
            result.extend({'entity': entity, 'id': r['id'], 'name': r[title]} for r in c.execute(f'SELECT * FROM {entity} WHERE deleted=1 ORDER BY id DESC'))
        return result

@app.post('/api/{entity}/{id}/restore')
def restore(entity: str, id: int):
    if entity not in ('clients', 'tasks', 'documents'):
        raise HTTPException(404)
    with db() as c:
        row = c.execute(f'SELECT * FROM {entity} WHERE id=? AND deleted=1', (id,)).fetchone()
        if not row:
            raise HTTPException(404, 'Запись не найдена')
        if entity != 'clients' and row['client_id'] is not None:
            client_exists(c, row['client_id'])
        c.execute(f'UPDATE {entity} SET deleted=0 WHERE id=?', (id,))
        if entity == 'clients':
            c.execute('UPDATE tasks SET deleted=0 WHERE client_id=? AND deleted=2', (id,))
    return {'ok': True}

def save(table, body, id=None):
    values = body.model_dump()
    main = 'name' if table == 'clients' else 'title'
    values[main] = values[main].strip()
    if not values[main]:
        raise HTTPException(422, 'Название не может быть пустым')
    if table == 'clients' and values['stage'] not in STAGES:
        raise HTTPException(422, 'Неизвестный этап')
    if table == 'tasks':
        if values['status'] not in STATUSES or values['priority'] not in ['Обычный', 'Высокий', 'Срочно']:
            raise HTTPException(422, 'Неизвестный статус или приоритет')
        if values['due']:
            from datetime import date
            try:
                date.fromisoformat(values['due'])
            except ValueError:
                raise HTTPException(422, 'Неверная дата')
    with db() as c:
        if table == 'tasks' and values['client_id'] is not None:
            client_exists(c, values['client_id'])
        if id is None:
            cur = c.execute(f"INSERT INTO {table} ({','.join(values)}) VALUES ({','.join('?' for _ in values)})", tuple(values.values()))
            id = cur.lastrowid
        else:
            cur = c.execute(f"UPDATE {table} SET {','.join(k+'=?' for k in values)} WHERE id=? AND deleted=0", (*values.values(), id))
            if not cur.rowcount:
                raise HTTPException(404, 'Запись не найдена')
        return dict(c.execute(f'SELECT * FROM {table} WHERE id=?', (id,)).fetchone())

@app.post('/api/clients')
def create_client(body: Client):
    return save('clients', body)

@app.put('/api/clients/{id}')
def update_client(id: int, body: Client):
    return save('clients', body, id)

@app.post('/api/tasks')
def create_task(body: Task):
    return save('tasks', body)

@app.put('/api/tasks/{id}')
def update_task(id: int, body: Task):
    return save('tasks', body, id)

@app.delete('/api/{entity}/{id}')
def archive(entity: str, id: int):
    if entity not in ('clients', 'tasks', 'documents'):
        raise HTTPException(404)
    with db() as c:
        cur = c.execute(f'UPDATE {entity} SET deleted=1 WHERE id=? AND deleted=0', (id,))
        if not cur.rowcount:
            raise HTTPException(404, 'Запись не найдена')
        if entity == 'clients':
            c.execute('UPDATE tasks SET deleted=2 WHERE client_id=? AND deleted=0', (id,))
    return {'ok': True}

@app.post('/api/documents')
async def upload(client_id: int = Form(...), category: str = Form('Другое', max_length=100), file: UploadFile = File(...)):
    with db() as c:
        client_exists(c, client_id)
    name = (file.filename or 'document').replace('\\', '/').split('/')[-1][:200]
    if Path(name).suffix.lower() not in {'.pdf','.doc','.docx','.xls','.xlsx','.png','.jpg','.jpeg','.txt'}:
        raise HTTPException(422, 'Поддерживаются PDF, Word, Excel, изображения и TXT')
    storage = secrets.token_hex(24)
    path = DATA / 'files' / storage
    size = 0
    try:
        with path.open('wb') as out:
            while chunk := await file.read(65536):
                size += len(chunk)
                if size > 10 * 1024 * 1024:
                    raise HTTPException(413, 'Максимальный размер файла — 10 МБ')
                out.write(chunk)
        if not size:
            raise HTTPException(422, 'Файл пустой')
        with db() as c:
            client_exists(c, client_id)
            cur = c.execute('INSERT INTO documents(client_id,name,storage,size,category) VALUES(?,?,?,?,?)', (client_id,name,storage,size,category))
            id = cur.lastrowid
    except Exception:
        path.unlink(missing_ok=True)
        raise
    finally:
        await file.close()
    return {'id': id, 'name': name}

@app.get('/api/documents/{id}/download')
def download(id: int):
    with db() as c:
        row = c.execute('SELECT d.* FROM documents d JOIN clients c ON c.id=d.client_id WHERE d.id=? AND d.deleted=0 AND c.deleted=0', (id,)).fetchone()
    if not row:
        raise HTTPException(404, 'Документ не найден')
    return FileResponse(DATA / 'files' / row['storage'], filename=row['name'], media_type='application/octet-stream')

@app.get('/health')
def health():
    with db() as c:
        c.execute('SELECT 1').fetchone()
    return {'status': 'ok'}

app.mount('/', StaticFiles(directory='static', html=True), name='static')
