from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import HTTPException
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from src.app.api.analytics import router as analytics_router
from src.app.api.auth import router as auth_router
from src.app.api.dashboard import router as dashboard_router
from src.app.api.health import router as health_router
from src.app.api.pages import router as pages_router
from src.app.api.redirect import router as redirect_router
from src.app.config import settings
from src.app.database import Base, engine
from src.app.dependencies import AuthRedirect
from src.app.models import Click, Link, User  # noqa: F401 — register models


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables on startup (dev convenience; Alembic handles prod migrations)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    lifespan=lifespan,
)


_templates = Jinja2Templates(directory="src/app/templates")


@app.exception_handler(AuthRedirect)
async def auth_redirect_handler(request: Request, exc: AuthRedirect):
    """Redirect unauthenticated users to the login page."""
    return RedirectResponse(url="/login", status_code=302)


@app.exception_handler(404)
async def not_found_handler(request: Request, exc: HTTPException):
    """Show styled 404 page for browser requests, JSON for API clients."""
    accept = request.headers.get("accept", "")
    if "text/html" in accept:
        return _templates.TemplateResponse(
            "pages/404.html",
            {"request": request},
            status_code=404,
        )
    return JSONResponse(status_code=404, content={"detail": "Not found"})


app.mount("/static", StaticFiles(directory="src/app/static"), name="static")

app.include_router(health_router)
app.include_router(pages_router)
app.include_router(auth_router)
app.include_router(dashboard_router)
app.include_router(analytics_router)
# Redirect router MUST be last — it has a catch-all /{slug} pattern
app.include_router(redirect_router)
