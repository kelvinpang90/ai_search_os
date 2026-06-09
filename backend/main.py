"""Session 4+6：FastAPI 后端接口（/chat + /auth/login + /config + 限速）。"""
import os
import time

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from auth import (
    create_token,
    failed_attempts,
    pwd_context,
    verify_recaptcha,
    verify_token,
)
from claude_client import chat
from db.crm import crm_query

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_methods=['*'],
    allow_headers=['*'],
)

# per-user_id 限速记录（内存，进程重启清零）
last_query: dict[str, float] = {}
RATE_LIMIT_SEC = 20


# ──────────────────────────── 公共接口 ────────────────────────────

@app.get('/health')
async def health():
    return {'status': 'ok'}


@app.get('/config')
async def config():
    """向前端暴露 reCAPTCHA Site Key（不暴露 Secret Key）。"""
    return {'recaptcha_site_key': os.getenv('RECAPTCHA_SITE_KEY', '')}


# ──────────────────────────── 登录接口 ────────────────────────────

@app.post('/auth/login')
async def login(body: dict, request: Request):
    ip = request.client.host
    email = body.get('email', '').strip().lower()
    password = body.get('password', '')
    recaptcha_token = body.get('recaptcha_token')

    # 连续失败 3 次后要求通过 reCAPTCHA
    if failed_attempts.get(ip, 0) >= 3:
        if not recaptcha_token:
            raise HTTPException(403, detail='need_recaptcha')
        if not await verify_recaptcha(recaptcha_token):
            raise HTTPException(403, detail='recaptcha_failed')

    # 查 CRM 用户（password_hash 仅登录接口内可访问）
    rows = crm_query(
        'SELECT id, name, email, role, password_hash FROM users'
        ' WHERE email = %s AND is_active = 1',
        (email,),
    )

    user = rows[0] if rows else None
    if not user or not pwd_context.verify(password, user['password_hash']):
        failed_attempts[ip] = failed_attempts.get(ip, 0) + 1
        need_captcha = failed_attempts[ip] >= 3
        raise HTTPException(
            401,
            detail='need_recaptcha' if need_captcha else 'invalid_credentials',
        )

    failed_attempts.pop(ip, None)  # 登录成功，重置失败计数
    token = create_token(str(user['id']), user['email'], user['role'])
    return {'token': token, 'name': user['name'], 'role': user['role']}


# ──────────────────────────── 对话接口 ────────────────────────────

class ChatRequest(BaseModel):
    message: str
    history: list = []


@app.post('/chat')
async def chat_endpoint(
    req: ChatRequest,
    authorization: str = Header(None),
):
    # 1. Token 验证
    if not authorization or not authorization.startswith('Bearer '):
        raise HTTPException(401, detail='unauthorized')
    payload = verify_token(authorization[7:])
    if not payload:
        raise HTTPException(401, detail='token_expired')

    # 2. 限速：同一用户 20 秒内只允许一次查询
    user_id = payload['sub']
    now = time.time()
    if now - last_query.get(user_id, 0) < RATE_LIMIT_SEC:
        raise HTTPException(429, detail='query_too_frequent')
    last_query[user_id] = now

    messages = req.history + [{'role': 'user', 'content': req.message}]
    reply = chat(messages)
    return {'reply': reply}


# ──────────────────────────── 静态文件 ────────────────────────────

FRONTEND_DIR = os.path.join(os.path.dirname(__file__), '..', 'frontend')
app.mount('/', StaticFiles(directory=FRONTEND_DIR, html=True), name='static')

# 启动：uvicorn main:app --reload --host 0.0.0.0 --port 8000
