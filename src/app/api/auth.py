from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.config import settings
from src.app.database import get_db
from src.app.dependencies import get_optional_user
from src.app.models.user import User
from src.app.schemas.auth import LoginRequest, RegisterRequest
from src.app.services.auth import (
    authenticate_user,
    create_access_token,
    create_user,
    get_user_by_email,
)


def _set_auth_cookie(response, token: str) -> None:
    """Set the access_token cookie with appropriate security settings."""
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        samesite="lax",
        secure=not settings.debug,
        max_age=60 * 60 * 24,  # 24 hours
    )


templates = Jinja2Templates(directory="src/app/templates")
router = APIRouter(tags=["auth"])


@router.get("/register", response_class=HTMLResponse)
async def register_page(
    request: Request,
    user: User | None = Depends(get_optional_user),
):
    if user:
        return RedirectResponse(url="/dashboard", status_code=302)
    return templates.TemplateResponse("pages/register.html", {"request": request})


@router.post("/register")
async def register(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    form = await request.form()
    email = form.get("email", "").strip()
    password = form.get("password", "")
    display_name = form.get("display_name", "").strip()

    # Validate input
    errors = []
    try:
        data = RegisterRequest(email=email, password=password, display_name=display_name)
    except ValidationError as e:
        for err in e.errors():
            field = err["loc"][-1] if err["loc"] else "unknown"
            errors.append({"field": field, "message": err["msg"]})
        return templates.TemplateResponse(
            "pages/register.html",
            {
                "request": request,
                "errors": errors,
                "email": email,
                "display_name": display_name,
            },
            status_code=422,
        )

    # Check if email already exists
    existing = await get_user_by_email(db, data.email)
    if existing:
        return templates.TemplateResponse(
            "pages/register.html",
            {
                "request": request,
                "errors": [{"field": "email", "message": "An account with this email already exists"}],
                "email": email,
                "display_name": display_name,
            },
            status_code=409,
        )

    user = await create_user(db, data.email, data.password, data.display_name)
    token = create_access_token(user.id)

    response = RedirectResponse(url="/dashboard", status_code=302)
    _set_auth_cookie(response, token)
    return response


@router.get("/login", response_class=HTMLResponse)
async def login_page(
    request: Request,
    user: User | None = Depends(get_optional_user),
):
    if user:
        return RedirectResponse(url="/dashboard", status_code=302)
    return templates.TemplateResponse("pages/login.html", {"request": request})


@router.post("/login")
async def login(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    form = await request.form()
    email = form.get("email", "").strip()
    password = form.get("password", "")

    errors = []
    try:
        data = LoginRequest(email=email, password=password)
    except ValidationError as e:
        for err in e.errors():
            field = err["loc"][-1] if err["loc"] else "unknown"
            errors.append({"field": field, "message": err["msg"]})
        return templates.TemplateResponse(
            "pages/login.html",
            {"request": request, "errors": errors, "email": email},
            status_code=422,
        )

    user = await authenticate_user(db, data.email, data.password)
    if user is None:
        return templates.TemplateResponse(
            "pages/login.html",
            {
                "request": request,
                "errors": [{"field": "general", "message": "Invalid email or password"}],
                "email": email,
            },
            status_code=401,
        )

    token = create_access_token(user.id)

    response = RedirectResponse(url="/dashboard", status_code=302)
    _set_auth_cookie(response, token)
    return response


@router.get("/logout")
async def logout():
    response = RedirectResponse(url="/", status_code=302)
    response.delete_cookie("access_token")
    return response
