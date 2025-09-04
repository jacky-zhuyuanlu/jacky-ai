from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

app = FastAPI(title="Retell AI 商用仿站 API", docs_url="/api/retell/docs", openapi_url="/api/retell/openapi.json")

# 允许所有来源跨域，便于前端本地开发
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class User(BaseModel):
    username: str
    password: str

# 健康检查
@app.get("/api/retell/health")
def health():
    return {"status": "ok"}

# 用户注册（示例，实际应接数据库）
@app.post("/api/retell/register")
def register(user: User):
    # TODO: 实际注册逻辑
    return {"msg": f"用户 {user.username} 注册成功（示例）"}

# 用户登录（示例，实际应接数据库）
@app.post("/api/retell/login")
def login(user: User):
    # TODO: 实际登录逻辑
    if user.username == "admin" and user.password == "admin":
        return {"msg": "登录成功", "token": "demo-token"}
    raise HTTPException(status_code=401, detail="用户名或密码错误")
