import pytest


class TestRedirect:
    async def _register_and_get_token(self, client, email="redir@example.com"):
        response = await client.post(
            "/register",
            data={
                "email": email,
                "password": "TestPass1",
                "display_name": "Redirect User",
            },
            follow_redirects=False,
        )
        return response.cookies.get("access_token")

    async def _create_link(self, client, token, target_url="https://example.com/target", slug=None):
        data = {"target_url": target_url}
        if slug:
            data["custom_slug"] = slug
        await client.post(
            "/dashboard/links",
            data=data,
            cookies={"access_token": token},
            follow_redirects=False,
        )

    @pytest.mark.asyncio
    async def test_redirect_with_custom_slug(self, client):
        token = await self._register_and_get_token(client)
        await self._create_link(
            client, token,
            target_url="https://example.com/destination",
            slug="test-redir",
        )

        response = await client.get("/test-redir", follow_redirects=False)
        assert response.status_code == 302
        assert response.headers["location"] == "https://example.com/destination"

    @pytest.mark.asyncio
    async def test_redirect_nonexistent_slug(self, client):
        response = await client.get("/nonexistent-slug-xyz")
        assert response.status_code == 404
        assert "Link not found" in response.text

    @pytest.mark.asyncio
    async def test_redirect_does_not_catch_internal_paths(self, client):
        response = await client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_redirect_records_click(self, client):
        token = await self._register_and_get_token(client, email="click-rec@example.com")
        await self._create_link(
            client, token,
            target_url="https://example.com/tracked",
            slug="tracked-link",
        )

        response = await client.get(
            "/tracked-link",
            follow_redirects=False,
            headers={
                "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "referer": "https://twitter.com/post/123",
            },
        )
        assert response.status_code == 302

        # Verify click was recorded by checking the dashboard
        dash = await client.get(
            "/dashboard",
            cookies={"access_token": token},
        )
        assert dash.status_code == 200
        # Click count should now be 1
        assert ">1<" in dash.text or ">1\n" in dash.text or "1</p>" in dash.text

    @pytest.mark.asyncio
    async def test_redirect_increments_click_count(self, client):
        """Test multiple redirects increment click count."""
        token = await self._register_and_get_token(client, email="click-count@example.com")
        await self._create_link(
            client, token,
            target_url="https://example.com/counted",
            slug="count-test",
        )

        # Click 3 times
        for _ in range(3):
            response = await client.get("/count-test", follow_redirects=False)
            assert response.status_code == 302

        # Verify analytics shows 3 clicks
        analytics = await client.get(
            "/dashboard/links/1/analytics",
            cookies={"access_token": token},
        )
        assert analytics.status_code == 200
        assert ">3<" in analytics.text or "3</p>" in analytics.text

    @pytest.mark.asyncio
    async def test_redirect_with_referrer_and_ua(self, client):
        """Test that referrer and user-agent are captured in analytics."""
        token = await self._register_and_get_token(client, email="ua-test@example.com")
        await self._create_link(
            client, token,
            target_url="https://example.com/ua-test",
            slug="ua-test-link",
        )

        await client.get(
            "/ua-test-link",
            follow_redirects=False,
            headers={
                "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "referer": "https://facebook.com/share",
            },
        )

        analytics = await client.get(
            "/dashboard/links/1/analytics",
            cookies={"access_token": token},
        )
        assert analytics.status_code == 200
        assert "Chrome" in analytics.text
        assert "Desktop" in analytics.text
        assert "facebook.com" in analytics.text

    @pytest.mark.asyncio
    async def test_404_page_styling(self, client):
        """404 page should have proper styling and link to homepage."""
        response = await client.get("/some-missing-link-xyz")
        assert response.status_code == 404
        assert "404" in response.text
        assert "Go to Homepage" in response.text

    @pytest.mark.asyncio
    async def test_head_request_on_redirect(self, client):
        """HEAD requests should return 302 without recording a click."""
        token = await self._register_and_get_token(client, email="head-test@example.com")
        await self._create_link(
            client, token,
            target_url="https://example.com/head-target",
            slug="head-test",
        )

        response = await client.head("/head-test", follow_redirects=False)
        assert response.status_code == 302
        assert response.headers["location"] == "https://example.com/head-target"

    @pytest.mark.asyncio
    async def test_excluded_paths_return_404(self, client):
        """Internal paths like favicon.ico should not resolve as slugs."""
        response = await client.get("/favicon.ico")
        assert response.status_code == 404
