from fastapi import FastAPI


def register_root_routes(app: FastAPI) -> None:

    @app.get("/")
    async def root():
        return {
            "message": "YOLO Dashboard API",
            "status": "running",
            "version": "3.0.0",
        }

    @app.get("/api")
    async def api_info():
        return {
            "auth": "/api/v1/auth",
            "users": "/api/v1/users",
            "stream": "/api/v1/stream",
        }
