from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.database import get_db
from src.app.services.clicks import record_click
from src.app.services.links import get_link_by_slug

templates = Jinja2Templates(directory="src/app/templates")
router = APIRouter(tags=["redirect"])


@router.api_route("/{slug}", methods=["GET", "HEAD"])
async def redirect_to_target(
    slug: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Public redirect endpoint — resolves short link and tracks click."""
    # Exclude known internal paths so we don't catch them
    internal_paths = {
        "dashboard", "login", "register", "logout",
        "health", "static", "docs", "openapi.json", "redoc",
        "favicon.ico", "robots.txt", "sitemap.xml",
    }
    if slug in internal_paths:
        return templates.TemplateResponse(
            "pages/404.html",
            {"request": request},
            status_code=404,
        )

    link = await get_link_by_slug(db, slug)
    if link is None:
        return templates.TemplateResponse(
            "pages/404.html",
            {"request": request},
            status_code=404,
        )

    # Only record clicks for GET requests — HEAD requests from crawlers/preview
    # tools should not inflate click counts
    if request.method == "GET":
        ip_address = request.client.host if request.client else None
        referrer = request.headers.get("referer")
        user_agent = request.headers.get("user-agent")
        await record_click(db, link, ip_address, referrer, user_agent)

    return RedirectResponse(url=link.target_url, status_code=302)
