"""Session 6：JWT 认证 + reCAPTCHA 校验辅助模块。"""
import os
from datetime import datetime, timedelta

import httpx
from jose import JWTError, jwt
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto')

JWT_SECRET = os.getenv('JWT_SECRET', '')
JWT_EXPIRE_HOURS = int(os.getenv('JWT_EXPIRE_HOURS', 24))
RECAPTCHA_SECRET = os.getenv('RECAPTCHA_SECRET_KEY', '')

# 内存中记录各 IP 的连续失败次数；进程重启后清零
failed_attempts: dict[str, int] = {}


def create_token(user_id: str, email: str, role: str) -> str:
    payload = {
        'sub': user_id,
        'email': email,
        'role': role,
        'exp': datetime.utcnow() + timedelta(hours=JWT_EXPIRE_HOURS),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm='HS256')


def verify_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
    except JWTError:
        return None


async def verify_recaptcha(token: str) -> bool:
    """调用 Google reCAPTCHA v3 验证接口。未配置 secret 时本地开发直接放行。
    v3 返回 score（0.0-1.0），>= 0.5 视为人类操作。
    """
    if not RECAPTCHA_SECRET:
        return True
    async with httpx.AsyncClient() as client:
        r = await client.post(
            'https://www.google.com/recaptcha/api/siteverify',
            data={'secret': RECAPTCHA_SECRET, 'response': token},
        )
        data = r.json()
        return data.get('success', False) and data.get('score', 0) >= 0.5
