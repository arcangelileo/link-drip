from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.config import settings
from src.app.database import get_db
from src.app.dependencies import get_current_user
from src.app.models.user import User
from src.app.schemas.link import LinkCreateRequest
from src.app.services.links import (
    create_link,
    delete_link,
    get_user_links,
    slug_exists,
)

templates = Jinja2Templates(directory="src/app/templates")
router = APIRouter(tags=["dashboard"])


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(
    request: Request,
    search: str | None = None,
    tag: str | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    links = await get_user_links(db, user.id, search=search, tag=tag)

    # Build link responses with short URLs
    link_data = []
    all_tags = set()
    for link in links:
        short_url = f"{settings.app_url}/{link.slug}"
        link_data.append({
            "id": link.id,
            "slug": link.slug,
            "target_url": link.target_url,
            "title": link.title,
            "tags": link.tags,
            "click_count": link.click_count,
            "short_url": short_url,
            "created_at": link.created_at,
        })
        if link.tags:
            for t in link.tags.split(","):
                all_tags.add(t.strip())

    return templates.TemplateResponse(
        "pages/dashboard.html",
        {
            "request": request,
            "user": user,
            "links": link_data,
            "all_tags": sorted(all_tags),
            "search": search or "",
            "active_tag": tag or "",
            "app_url": settings.app_url,
        },
    )


@router.post("/dashboard/links")
async def create_link_handler(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    form = await request.form()
    target_url = form.get("target_url", "").strip()
    custom_slug = form.get("custom_slug", "").strip() or None
    title = form.get("title", "").strip() or None
    tags = form.get("tags", "").strip() or None

    try:
        data = LinkCreateRequest(
            target_url=target_url,
            custom_slug=custom_slug,
            title=title,
            tags=tags,
        )
    except ValidationError as e:
        error_messages = [err["msg"] for err in e.errors()]
        # Re-render dashboard with errors
        links = await get_user_links(db, user.id)
        all_tags = set()
        link_data = []
        for link in links:
            short_url = f"{settings.app_url}/{link.slug}"
            link_data.append({
                "id": link.id,
                "slug": link.slug,
                "target_url": link.target_url,
                "title": link.title,
                "tags": link.tags,
                "click_count": link.click_count,
                "short_url": short_url,
                "created_at": link.created_at,
            })
            if link.tags:
                for t in link.tags.split(","):
                    all_tags.add(t.strip())

        return templates.TemplateResponse(
            "pages/dashboard.html",
            {
                "request": request,
                "user": user,
                "links": link_data,
                "all_tags": sorted(all_tags),
                "search": "",
                "active_tag": "",
                "app_url": settings.app_url,
                "form_errors": error_messages,
                "form_data": {
                    "target_url": target_url,
                    "custom_slug": custom_slug or "",
                    "title": title or "",
                    "tags": tags or "",
                },
            },
            status_code=422,
        )

    # Check custom slug uniqueness
    if data.custom_slug and await slug_exists(db, data.custom_slug):
        links = await get_user_links(db, user.id)
        all_tags = set()
        link_data = []
        for link in links:
            short_url = f"{settings.app_url}/{link.slug}"
            link_data.append({
                "id": link.id,
                "slug": link.slug,
                "target_url": link.target_url,
                "title": link.title,
                "tags": link.tags,
                "click_count": link.click_count,
                "short_url": short_url,
                "created_at": link.created_at,
            })
            if link.tags:
                for t in link.tags.split(","):
                    all_tags.add(t.strip())

        return templates.TemplateResponse(
            "pages/dashboard.html",
            {
                "request": request,
                "user": user,
                "links": link_data,
                "all_tags": sorted(all_tags),
                "search": "",
                "active_tag": "",
                "app_url": settings.app_url,
                "form_errors": ["This custom slug is already taken. Please choose another."],
                "form_data": {
                    "target_url": target_url,
                    "custom_slug": custom_slug or "",
                    "title": title or "",
                    "tags": tags or "",
                },
            },
            status_code=409,
        )

    await create_link(
        db,
        user_id=user.id,
        target_url=data.target_url,
        custom_slug=data.custom_slug,
        title=data.title,
        tags=data.tags,
    )

    return RedirectResponse(url="/dashboard", status_code=302)


@router.post("/dashboard/links/{link_id}/delete")
async def delete_link_handler(
    link_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    success = await delete_link(db, link_id, user.id)
    if not success:
        raise HTTPException(status_code=404, detail="Link not found")
    return RedirectResponse(url="/dashboard", status_code=302)
