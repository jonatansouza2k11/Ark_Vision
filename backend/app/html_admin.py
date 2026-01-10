from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory="backend/templates")


def setup_html_admin(app: FastAPI) -> None:

    @app.get("/admin", response_class=HTMLResponse, include_in_schema=False)
    async def admin_dashboard(request: Request):
        return templates.TemplateResponse(
            "dashboard.html",
            {"request": request, "user": {"username": "admin"}},
        )
