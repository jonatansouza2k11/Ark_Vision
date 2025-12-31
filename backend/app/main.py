# backend/app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import auth, users, video  # ← ADICIONAR video

app = FastAPI(title="YOLO Dashboard API")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rotas
app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(users.router, prefix="/api/v1/users", tags=["users"])
app.include_router(video.router, prefix="", tags=["video"])  # ← ADICIONAR

@app.get("/")
async def root():
    return {"message": "YOLO Dashboard API"}
