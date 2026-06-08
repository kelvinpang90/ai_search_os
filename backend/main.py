"""Session 4：FastAPI 后端接口（/chat + CORS + 前端静态文件挂载）。"""
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from claude_client import chat

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_methods=['*'],
    allow_headers=['*'],
)


@app.get('/health')
async def health():
    return {'status': 'ok'}


class ChatRequest(BaseModel):
    message: str
    history: list = []


@app.post('/chat')
async def chat_endpoint(req: ChatRequest):
    messages = req.history + [{'role': 'user', 'content': req.message}]
    reply = chat(messages)
    return {'reply': reply}


FRONTEND_DIR = os.path.join(os.path.dirname(__file__), '..', 'frontend')
app.mount('/', StaticFiles(directory=FRONTEND_DIR, html=True), name='static')

# 启动：uvicorn main:app --reload --host 0.0.0.0 --port 8000
