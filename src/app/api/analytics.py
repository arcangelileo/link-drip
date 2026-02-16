import csv
import io

import qrcode
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, Response, StreamingResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.config import settings
from src.app.database import get_db
from src.app.dependencies import get_current_user
from src.app.models.user import User
from src.app.services.clicks import (
    get_all_clicks_for_export,
    get_click_stats,
    get_link_with_owner,
)

templates = Jinja2Templates(directory="src/app/templates")
router = APIRouter(tags=["analytics"])


@router.get("/dashboard/links/{link_id}/analytics", response_class=HTMLResponse)
async def link_analytics(
    link_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    link = await get_link_with_owner(db, link_id, user.id)
    if link is None:
        raise HTTPException(status_code=404, detail="Link not found")

    stats = await get_click_stats(db, link_id)
    short_url = f"{settings.app_url}/{link.slug}"

    return templates.TemplateResponse(
        "pages/analytics.html",
        {
            "request": request,
            "user": user,
            "link": link,
            "short_url": short_url,
            "stats": stats,
            "app_url": settings.app_url,
        },
    )


@router.get("/dashboard/links/{link_id}/export")
async def export_clicks_csv(
    link_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    link = await get_link_with_owner(db, link_id, user.id)
    if link is None:
        raise HTTPException(status_code=404, detail="Link not found")

    clicks = await get_all_clicks_for_export(db, link_id)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Clicked At", "IP Address", "Country", "City",
        "Referrer", "Browser", "OS", "Device", "User Agent",
    ])
    for click in clicks:
        writer.writerow([
            click.clicked_at.isoformat() if click.clicked_at else "",
            click.ip_address or "",
            click.country or "",
            click.city or "",
            click.referrer or "",
            click.browser or "",
            click.os or "",
            click.device or "",
            click.user_agent or "",
        ])

    output.seek(0)
    filename = f"linkdrip-{link.slug}-clicks.csv"

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/dashboard/links/{link_id}/qr", response_class=HTMLResponse)
async def link_qr_page(
    link_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    link = await get_link_with_owner(db, link_id, user.id)
    if link is None:
        raise HTTPException(status_code=404, detail="Link not found")

    short_url = f"{settings.app_url}/{link.slug}"

    return templates.TemplateResponse(
        "pages/qr.html",
        {
            "request": request,
            "user": user,
            "link": link,
            "short_url": short_url,
        },
    )


@router.get("/dashboard/links/{link_id}/qr.png")
async def link_qr_image(
    link_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    link = await get_link_with_owner(db, link_id, user.id)
    if link is None:
        raise HTTPException(status_code=404, detail="Link not found")

    short_url = f"{settings.app_url}/{link.slug}"

    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=4,
    )
    qr.add_data(short_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#1e3a8a", back_color="white")

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)

    filename = f"linkdrip-{link.slug}-qr.png"
    return Response(
        content=buf.getvalue(),
        media_type="image/png",
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )
