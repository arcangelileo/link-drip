from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.database import get_db
from src.app.services.clicks import record_click
from src.app.services.links import get_link_by_slug

templates = Jinja2Templates(directory="src/app/templates")
router = APIRouter(tags=["redirect"])


@router.get("/{slug}")
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
    }
    if slug in internal_paths:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Not found")

    link = await get_link_by_slug(db, slug)
    if link is None:
        return templates.TemplateResponse(
            "pages/404.html",
            {"request": request},
            status_code=404,
        )

    # Capture metadata
    ip_address = request.client.host if request.client else None
    referrer = request.headers.get("referer")
    user_agent = request.headers.get("user-agent")

    # Record click inline — the 302 redirect is returned immediately to the browser
    # regardless, so the click recording latency doesn't affect UX
    await record_click(db, link, ip_address, referrer, user_agent)

    return RedirectResponse(url=link.target_url, status_code=302)
