from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from backend.dependencies import limiter
from backend.app.security_headers import apply_security_headers


def setup_middleware(app: FastAPI) -> None:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:8000",
            "http://localhost:3000",
            "http://127.0.0.1:8000",
            "http://127.0.0.1:3000",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.state.limiter = limiter

    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        response = await call_next(request)
        apply_security_headers(request, response)
        return response
