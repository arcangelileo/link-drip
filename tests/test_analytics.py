import datetime

import pytest
from sqlalchemy import select

from src.app.api.analytics import _sanitize_csv_field
from src.app.models.click import Click
from src.app.models.link import Link
from src.app.services.clicks import (
    get_all_clicks_for_export,
    get_click_stats,
    parse_user_agent,
    record_click,
)
from tests.conftest import TestingSessionLocal


class TestUserAgentParsing:
    def test_parse_chrome_windows(self):
        ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        result = parse_user_agent(ua)
        assert "Chrome" in result["browser"]
        assert "Windows" in result["os"]
        assert result["device"] == "Desktop"

    def test_parse_safari_iphone(self):
        ua = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
        result = parse_user_agent(ua)
        assert "Safari" in result["browser"] or "Mobile Safari" in result["browser"]
        assert "iOS" in result["os"]
        assert result["device"] == "Mobile"

    def test_parse_firefox_linux(self):
        ua = "Mozilla/5.0 (X11; Linux x86_64; rv:120.0) Gecko/20100101 Firefox/120.0"
        result = parse_user_agent(ua)
        assert "Firefox" in result["browser"]
        assert "Linux" in result["os"]
        assert result["device"] == "Desktop"

    def test_parse_googlebot(self):
        ua = "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"
        result = parse_user_agent(ua)
        assert result["device"] == "Bot"

    def test_parse_none(self):
        result = parse_user_agent(None)
        assert result["browser"] is None
        assert result["os"] is None
        assert result["device"] is None

    def test_parse_empty(self):
        result = parse_user_agent("")
        # Empty string is treated as falsy, same as None
        assert result["browser"] is None
        assert result["os"] is None
        assert result["device"] is None


class TestRecordClick:
    @pytest.mark.asyncio
    async def test_record_click_basic(self):
        """Test that recording a click creates a Click record and increments count."""
        async with TestingSessionLocal() as db:
            # Create a user and link directly
            from src.app.models.user import User
            from src.app.services.auth import hash_password

            user = User(
                email="click-test@example.com",
                hashed_password=hash_password("TestPass1"),
                display_name="Click Tester",
            )
            db.add(user)
            await db.flush()

            link = Link(
                slug="click-test",
                target_url="https://example.com/click-target",
                user_id=user.id,
                click_count=0,
            )
            db.add(link)
            await db.commit()
            await db.refresh(link)

            # Record a click
            click = await record_click(
                db,
                link,
                ip_address="127.0.0.1",
                referrer="https://twitter.com",
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            )

            assert click.id is not None
            assert click.link_id == link.id
            assert click.referrer == "https://twitter.com"
            assert "Chrome" in click.browser
            assert click.device == "Desktop"

            # Verify click count was incremented
            await db.refresh(link)
            assert link.click_count == 1

    @pytest.mark.asyncio
    async def test_record_multiple_clicks(self):
        """Test multiple clicks increment count correctly."""
        async with TestingSessionLocal() as db:
            from src.app.models.user import User
            from src.app.services.auth import hash_password

            user = User(
                email="multi-click@example.com",
                hashed_password=hash_password("TestPass1"),
                display_name="Multi Click",
            )
            db.add(user)
            await db.flush()

            link = Link(
                slug="multi-click-test",
                target_url="https://example.com/multi",
                user_id=user.id,
                click_count=0,
            )
            db.add(link)
            await db.commit()
            await db.refresh(link)

            for i in range(3):
                await record_click(db, link, f"10.0.0.{i}", None, None)
                await db.refresh(link)

            assert link.click_count == 3


class TestClickStats:
    @pytest.mark.asyncio
    async def test_empty_stats(self):
        """Analytics for a link with no clicks should return zeros and empty lists."""
        async with TestingSessionLocal() as db:
            from src.app.models.user import User
            from src.app.services.auth import hash_password

            user = User(
                email="stats-empty@example.com",
                hashed_password=hash_password("TestPass1"),
                display_name="Stats User",
            )
            db.add(user)
            await db.flush()

            link = Link(
                slug="empty-stats",
                target_url="https://example.com/empty",
                user_id=user.id,
            )
            db.add(link)
            await db.commit()
            await db.refresh(link)

            stats = await get_click_stats(db, link.id)
            assert stats["total_clicks"] == 0
            assert stats["top_countries"] == []
            assert stats["top_browsers"] == []
            assert stats["devices"] == []
            assert stats["recent_clicks"] == []

    @pytest.mark.asyncio
    async def test_stats_with_clicks(self):
        """Analytics should aggregate click data correctly."""
        async with TestingSessionLocal() as db:
            from src.app.models.user import User
            from src.app.services.auth import hash_password

            user = User(
                email="stats-data@example.com",
                hashed_password=hash_password("TestPass1"),
                display_name="Stats Data",
            )
            db.add(user)
            await db.flush()

            link = Link(
                slug="stats-data",
                target_url="https://example.com/stats",
                user_id=user.id,
            )
            db.add(link)
            await db.commit()
            await db.refresh(link)

            # Record clicks with different metadata
            await record_click(
                db, link, "1.1.1.1", "https://twitter.com",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0",
            )
            await record_click(
                db, link, "2.2.2.2", "https://facebook.com",
                "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0) Mobile Safari/604.1",
            )
            await record_click(
                db, link, "3.3.3.3", None,
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0",
            )

            stats = await get_click_stats(db, link.id)
            assert stats["total_clicks"] == 3
            assert len(stats["recent_clicks"]) == 3
            assert len(stats["top_browsers"]) > 0
            assert len(stats["devices"]) > 0


class TestAnalyticsPage:
    async def _register_and_get_token(self, client, email="analytics@example.com"):
        response = await client.post(
            "/register",
            data={
                "email": email,
                "password": "TestPass1",
                "display_name": "Analytics User",
            },
            follow_redirects=False,
        )
        return response.cookies.get("access_token")

    @pytest.mark.asyncio
    async def test_analytics_page_loads(self, client):
        token = await self._register_and_get_token(client)

        # Create a link
        await client.post(
            "/dashboard/links",
            data={
                "target_url": "https://example.com/analytics-test",
                "title": "Analytics Test Link",
                "custom_slug": "ana-test",
            },
            cookies={"access_token": token},
            follow_redirects=False,
        )

        response = await client.get(
            "/dashboard/links/1/analytics",
            cookies={"access_token": token},
        )
        assert response.status_code == 200
        assert "Analytics Test Link" in response.text
        assert "Total Clicks" in response.text
        assert "No clicks yet" in response.text

    @pytest.mark.asyncio
    async def test_analytics_page_requires_auth(self, client):
        response = await client.get("/dashboard/links/1/analytics")
        assert response.status_code in (302, 401, 403)

    @pytest.mark.asyncio
    async def test_analytics_page_wrong_user(self, client):
        # User 1 creates a link
        token1 = await self._register_and_get_token(client, email="owner@example.com")
        await client.post(
            "/dashboard/links",
            data={"target_url": "https://example.com/private"},
            cookies={"access_token": token1},
            follow_redirects=False,
        )

        # User 2 tries to see it
        token2 = await self._register_and_get_token(client, email="hacker@example.com")
        response = await client.get(
            "/dashboard/links/1/analytics",
            cookies={"access_token": token2},
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_analytics_nonexistent_link(self, client):
        token = await self._register_and_get_token(client, email="nolink@example.com")
        response = await client.get(
            "/dashboard/links/999/analytics",
            cookies={"access_token": token},
        )
        assert response.status_code == 404


class TestCSVExport:
    async def _register_and_get_token(self, client, email="export@example.com"):
        response = await client.post(
            "/register",
            data={
                "email": email,
                "password": "TestPass1",
                "display_name": "Export User",
            },
            follow_redirects=False,
        )
        return response.cookies.get("access_token")

    @pytest.mark.asyncio
    async def test_csv_export_empty(self, client):
        token = await self._register_and_get_token(client)

        await client.post(
            "/dashboard/links",
            data={
                "target_url": "https://example.com/export-test",
                "custom_slug": "export-test",
            },
            cookies={"access_token": token},
            follow_redirects=False,
        )

        response = await client.get(
            "/dashboard/links/1/export",
            cookies={"access_token": token},
        )
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/csv; charset=utf-8"
        assert "attachment" in response.headers["content-disposition"]
        assert "export-test" in response.headers["content-disposition"]
        # Should have header row
        content = response.text
        assert "Clicked At" in content
        assert "Country" in content

    @pytest.mark.asyncio
    async def test_csv_export_requires_auth(self, client):
        response = await client.get("/dashboard/links/1/export")
        assert response.status_code in (302, 401, 403)

    @pytest.mark.asyncio
    async def test_csv_export_wrong_user(self, client):
        # User 1 creates a link
        token1 = await self._register_and_get_token(client, email="csvowner@example.com")
        await client.post(
            "/dashboard/links",
            data={"target_url": "https://example.com/csv-private"},
            cookies={"access_token": token1},
            follow_redirects=False,
        )

        # User 2 tries to export
        token2 = await self._register_and_get_token(client, email="csvthief@example.com")
        response = await client.get(
            "/dashboard/links/1/export",
            cookies={"access_token": token2},
        )
        assert response.status_code == 404


class TestQRCode:
    async def _register_and_get_token(self, client, email="qr@example.com"):
        response = await client.post(
            "/register",
            data={
                "email": email,
                "password": "TestPass1",
                "display_name": "QR User",
            },
            follow_redirects=False,
        )
        return response.cookies.get("access_token")

    @pytest.mark.asyncio
    async def test_qr_page_loads(self, client):
        token = await self._register_and_get_token(client)

        await client.post(
            "/dashboard/links",
            data={
                "target_url": "https://example.com/qr-test",
                "title": "QR Test Link",
                "custom_slug": "qr-test",
            },
            cookies={"access_token": token},
            follow_redirects=False,
        )

        response = await client.get(
            "/dashboard/links/1/qr",
            cookies={"access_token": token},
        )
        assert response.status_code == 200
        assert "QR Code" in response.text
        assert "QR Test Link" in response.text
        assert "qr.png" in response.text
        assert "Download PNG" in response.text

    @pytest.mark.asyncio
    async def test_qr_image_returns_png(self, client):
        token = await self._register_and_get_token(client, email="qrimg@example.com")

        await client.post(
            "/dashboard/links",
            data={
                "target_url": "https://example.com/qr-img-test",
                "custom_slug": "qr-img",
            },
            cookies={"access_token": token},
            follow_redirects=False,
        )

        response = await client.get(
            "/dashboard/links/1/qr.png",
            cookies={"access_token": token},
        )
        assert response.status_code == 200
        assert response.headers["content-type"] == "image/png"
        assert "qr-img" in response.headers["content-disposition"]
        # Check PNG magic bytes
        assert response.content[:4] == b"\x89PNG"

    @pytest.mark.asyncio
    async def test_qr_page_requires_auth(self, client):
        response = await client.get("/dashboard/links/1/qr")
        assert response.status_code in (302, 401, 403)

    @pytest.mark.asyncio
    async def test_qr_image_requires_auth(self, client):
        response = await client.get("/dashboard/links/1/qr.png")
        assert response.status_code in (302, 401, 403)

    @pytest.mark.asyncio
    async def test_qr_page_wrong_user(self, client):
        token1 = await self._register_and_get_token(client, email="qrowner@example.com")
        await client.post(
            "/dashboard/links",
            data={"target_url": "https://example.com/qr-private"},
            cookies={"access_token": token1},
            follow_redirects=False,
        )

        token2 = await self._register_and_get_token(client, email="qrthief@example.com")
        response = await client.get(
            "/dashboard/links/1/qr",
            cookies={"access_token": token2},
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_qr_image_wrong_user(self, client):
        token1 = await self._register_and_get_token(client, email="qrimgowner@example.com")
        await client.post(
            "/dashboard/links",
            data={"target_url": "https://example.com/qr-img-private"},
            cookies={"access_token": token1},
            follow_redirects=False,
        )

        token2 = await self._register_and_get_token(client, email="qrimgthief@example.com")
        response = await client.get(
            "/dashboard/links/1/qr.png",
            cookies={"access_token": token2},
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_qr_nonexistent_link(self, client):
        token = await self._register_and_get_token(client, email="qrnolink@example.com")
        response = await client.get(
            "/dashboard/links/999/qr",
            cookies={"access_token": token},
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_qr_image_nonexistent_link(self, client):
        token = await self._register_and_get_token(client, email="qrimgnolink@example.com")
        response = await client.get(
            "/dashboard/links/999/qr.png",
            cookies={"access_token": token},
        )
        assert response.status_code == 404


class TestCSVSanitization:
    """Test CSV injection prevention."""

    def test_sanitize_normal_value(self):
        assert _sanitize_csv_field("hello") == "hello"

    def test_sanitize_empty(self):
        assert _sanitize_csv_field("") == ""

    def test_sanitize_equals(self):
        assert _sanitize_csv_field("=cmd|'/C calc'!A0") == "'=cmd|'/C calc'!A0"

    def test_sanitize_plus(self):
        assert _sanitize_csv_field("+cmd|'/C calc'!A0") == "'+cmd|'/C calc'!A0"

    def test_sanitize_minus(self):
        assert _sanitize_csv_field("-1+1") == "'-1+1"

    def test_sanitize_at(self):
        assert _sanitize_csv_field("@SUM(A1:A2)") == "'@SUM(A1:A2)"

    def test_sanitize_tab(self):
        assert _sanitize_csv_field("\tcmd") == "'\tcmd"


class TestCSVExportWithData:
    """Test CSV export with actual click data."""

    async def _register_and_get_token(self, client, email="csvdata@example.com"):
        response = await client.post(
            "/register",
            data={
                "email": email,
                "password": "TestPass1",
                "display_name": "CSV Data User",
            },
            follow_redirects=False,
        )
        return response.cookies.get("access_token")

    @pytest.mark.asyncio
    async def test_csv_export_with_clicks(self, client):
        token = await self._register_and_get_token(client)

        await client.post(
            "/dashboard/links",
            data={
                "target_url": "https://example.com/csv-data",
                "custom_slug": "csv-data",
            },
            cookies={"access_token": token},
            follow_redirects=False,
        )

        # Generate some clicks
        await client.get(
            "/csv-data",
            follow_redirects=False,
            headers={
                "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0",
                "referer": "https://twitter.com",
            },
        )
        await client.get(
            "/csv-data",
            follow_redirects=False,
            headers={
                "user-agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0) Mobile Safari/604.1",
            },
        )

        response = await client.get(
            "/dashboard/links/1/export",
            cookies={"access_token": token},
        )
        assert response.status_code == 200
        content = response.text
        # Header row + 2 data rows
        lines = [l for l in content.strip().split("\n") if l.strip()]
        assert len(lines) == 3  # header + 2 clicks
        assert "Chrome" in content
        assert "twitter.com" in content


class TestAnalyticsPageWithClicks:
    """Test analytics page rendering with actual click data."""

    async def _register_and_get_token(self, client, email="anaclicks@example.com"):
        response = await client.post(
            "/register",
            data={
                "email": email,
                "password": "TestPass1",
                "display_name": "Analytics Clicks User",
            },
            follow_redirects=False,
        )
        return response.cookies.get("access_token")

    @pytest.mark.asyncio
    async def test_analytics_page_with_click_data(self, client):
        token = await self._register_and_get_token(client)

        await client.post(
            "/dashboard/links",
            data={
                "target_url": "https://example.com/ana-click",
                "title": "Analytics With Clicks",
                "custom_slug": "ana-click",
            },
            cookies={"access_token": token},
            follow_redirects=False,
        )

        # Generate a click with known UA
        await client.get(
            "/ana-click",
            follow_redirects=False,
            headers={
                "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "referer": "https://reddit.com/r/test",
            },
        )

        response = await client.get(
            "/dashboard/links/1/analytics",
            cookies={"access_token": token},
        )
        assert response.status_code == 200
        assert "Analytics With Clicks" in response.text
        # Should show click data instead of empty state
        assert "No clicks yet" not in response.text
        assert "Recent Clicks" in response.text
        assert "Chrome" in response.text
        assert "Desktop" in response.text
        assert "reddit.com" in response.text
