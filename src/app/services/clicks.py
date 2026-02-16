import datetime
import logging

import httpx
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from user_agents import parse as parse_ua

from src.app.models.click import Click
from src.app.models.link import Link

logger = logging.getLogger(__name__)

# Simple in-memory cache for GeoIP results to avoid excessive API calls
_geoip_cache: dict[str, dict] = {}
_GEOIP_CACHE_MAX = 5000


async def lookup_geoip(ip_address: str) -> dict:
    """Look up country/city from IP address using ip-api.com (free tier)."""
    if not ip_address or ip_address in ("127.0.0.1", "::1", "testclient"):
        return {"country": None, "city": None}

    if ip_address in _geoip_cache:
        return _geoip_cache[ip_address]

    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(
                f"http://ip-api.com/json/{ip_address}",
                params={"fields": "status,country,city"},
            )
            data = resp.json()
            if data.get("status") == "success":
                result = {
                    "country": data.get("country"),
                    "city": data.get("city"),
                }
            else:
                result = {"country": None, "city": None}
    except Exception:
        logger.debug("GeoIP lookup failed for %s", ip_address)
        result = {"country": None, "city": None}

    # Cache with size limit
    if len(_geoip_cache) < _GEOIP_CACHE_MAX:
        _geoip_cache[ip_address] = result

    return result


def parse_user_agent(ua_string: str | None) -> dict:
    """Parse user-agent string to extract browser, OS, device type."""
    if not ua_string:
        return {"browser": None, "os": None, "device": None}

    ua = parse_ua(ua_string)

    browser = ua.browser.family
    if ua.browser.version_string:
        browser = f"{browser} {ua.browser.version_string}"

    os_name = ua.os.family
    if ua.os.version_string:
        os_name = f"{os_name} {ua.os.version_string}"

    if ua.is_bot:
        device = "Bot"
    elif ua.is_mobile:
        device = "Mobile"
    elif ua.is_tablet:
        device = "Tablet"
    elif ua.is_pc:
        device = "Desktop"
    else:
        device = "Other"

    return {"browser": browser, "os": os_name, "device": device}


async def record_click(
    db: AsyncSession,
    link: Link,
    ip_address: str | None,
    referrer: str | None,
    user_agent: str | None,
) -> Click:
    """Record a click event and increment the link's click counter."""
    # Parse user-agent
    ua_info = parse_user_agent(user_agent)

    # GeoIP lookup
    geo_info = await lookup_geoip(ip_address or "")

    click = Click(
        link_id=link.id,
        ip_address=ip_address,
        country=geo_info["country"],
        city=geo_info["city"],
        referrer=referrer,
        browser=ua_info["browser"],
        os=ua_info["os"],
        device=ua_info["device"],
        user_agent=user_agent,
    )
    db.add(click)

    # Increment click count on the link
    link.click_count = link.click_count + 1

    await db.commit()
    return click


async def get_link_with_owner(db: AsyncSession, link_id: int, user_id: int) -> Link | None:
    """Get a link by ID ensuring it belongs to the given user."""
    result = await db.execute(
        select(Link).where(Link.id == link_id, Link.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def get_click_stats(db: AsyncSession, link_id: int) -> dict:
    """Compute analytics aggregates for a given link."""
    # Total clicks
    total_result = await db.execute(
        select(func.count(Click.id)).where(Click.link_id == link_id)
    )
    total_clicks = total_result.scalar() or 0

    # Clicks by country
    country_result = await db.execute(
        select(Click.country, func.count(Click.id).label("count"))
        .where(Click.link_id == link_id, Click.country.isnot(None))
        .group_by(Click.country)
        .order_by(func.count(Click.id).desc())
        .limit(10)
    )
    top_countries = [{"name": row[0], "count": row[1]} for row in country_result.all()]

    # Clicks by browser
    browser_result = await db.execute(
        select(Click.browser, func.count(Click.id).label("count"))
        .where(Click.link_id == link_id, Click.browser.isnot(None))
        .group_by(Click.browser)
        .order_by(func.count(Click.id).desc())
        .limit(10)
    )
    top_browsers = [{"name": row[0], "count": row[1]} for row in browser_result.all()]

    # Clicks by OS
    os_result = await db.execute(
        select(Click.os, func.count(Click.id).label("count"))
        .where(Click.link_id == link_id, Click.os.isnot(None))
        .group_by(Click.os)
        .order_by(func.count(Click.id).desc())
        .limit(10)
    )
    top_os = [{"name": row[0], "count": row[1]} for row in os_result.all()]

    # Clicks by device
    device_result = await db.execute(
        select(Click.device, func.count(Click.id).label("count"))
        .where(Click.link_id == link_id, Click.device.isnot(None))
        .group_by(Click.device)
        .order_by(func.count(Click.id).desc())
    )
    devices = [{"name": row[0], "count": row[1]} for row in device_result.all()]

    # Clicks by referrer
    referrer_result = await db.execute(
        select(Click.referrer, func.count(Click.id).label("count"))
        .where(Click.link_id == link_id, Click.referrer.isnot(None), Click.referrer != "")
        .group_by(Click.referrer)
        .order_by(func.count(Click.id).desc())
        .limit(10)
    )
    top_referrers = [{"name": row[0], "count": row[1]} for row in referrer_result.all()]

    # Clicks over time (last 30 days, grouped by day)
    thirty_days_ago = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=30)
    daily_result = await db.execute(
        select(
            func.date(Click.clicked_at).label("day"),
            func.count(Click.id).label("count"),
        )
        .where(Click.link_id == link_id, Click.clicked_at >= thirty_days_ago)
        .group_by(func.date(Click.clicked_at))
        .order_by(func.date(Click.clicked_at))
    )
    daily_clicks = [{"date": str(row[0]), "count": row[1]} for row in daily_result.all()]

    # Recent clicks (last 20)
    recent_result = await db.execute(
        select(Click)
        .where(Click.link_id == link_id)
        .order_by(Click.clicked_at.desc())
        .limit(20)
    )
    recent_clicks = recent_result.scalars().all()

    return {
        "total_clicks": total_clicks,
        "top_countries": top_countries,
        "top_browsers": top_browsers,
        "top_os": top_os,
        "devices": devices,
        "top_referrers": top_referrers,
        "daily_clicks": daily_clicks,
        "recent_clicks": recent_clicks,
    }


async def get_all_clicks_for_export(db: AsyncSession, link_id: int) -> list[Click]:
    """Get all clicks for CSV export."""
    result = await db.execute(
        select(Click)
        .where(Click.link_id == link_id)
        .order_by(Click.clicked_at.desc())
    )
    return list(result.scalars().all())
