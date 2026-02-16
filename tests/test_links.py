import pytest


class TestLinkCreation:
    async def _register_and_get_token(self, client, email="links@example.com"):
        response = await client.post(
            "/register",
            data={
                "email": email,
                "password": "TestPass1",
                "display_name": "Link User",
            },
            follow_redirects=False,
        )
        return response.cookies.get("access_token")

    @pytest.mark.asyncio
    async def test_create_link_auto_slug(self, client):
        token = await self._register_and_get_token(client)

        response = await client.post(
            "/dashboard/links",
            data={"target_url": "https://example.com/long-url"},
            cookies={"access_token": token},
            follow_redirects=False,
        )
        assert response.status_code == 302
        assert response.headers["location"] == "/dashboard"

    @pytest.mark.asyncio
    async def test_create_link_custom_slug(self, client):
        token = await self._register_and_get_token(client)

        response = await client.post(
            "/dashboard/links",
            data={
                "target_url": "https://example.com/custom",
                "custom_slug": "my-link",
            },
            cookies={"access_token": token},
            follow_redirects=False,
        )
        assert response.status_code == 302

    @pytest.mark.asyncio
    async def test_create_link_with_title_and_tags(self, client):
        token = await self._register_and_get_token(client)

        response = await client.post(
            "/dashboard/links",
            data={
                "target_url": "https://example.com/tagged",
                "title": "My Campaign",
                "tags": "marketing, social",
            },
            cookies={"access_token": token},
            follow_redirects=False,
        )
        assert response.status_code == 302

        # Verify link appears on dashboard
        dash = await client.get(
            "/dashboard",
            cookies={"access_token": token},
        )
        assert dash.status_code == 200
        assert "My Campaign" in dash.text
        assert "marketing" in dash.text
        assert "social" in dash.text

    @pytest.mark.asyncio
    async def test_create_link_invalid_url(self, client):
        token = await self._register_and_get_token(client)

        response = await client.post(
            "/dashboard/links",
            data={"target_url": "not-a-url"},
            cookies={"access_token": token},
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_link_ftp_url(self, client):
        token = await self._register_and_get_token(client)

        response = await client.post(
            "/dashboard/links",
            data={"target_url": "ftp://files.example.com/doc"},
            cookies={"access_token": token},
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_link_duplicate_custom_slug(self, client):
        token = await self._register_and_get_token(client)

        # First link
        await client.post(
            "/dashboard/links",
            data={
                "target_url": "https://example.com/first",
                "custom_slug": "unique-slug",
            },
            cookies={"access_token": token},
            follow_redirects=False,
        )

        # Second link with same slug
        response = await client.post(
            "/dashboard/links",
            data={
                "target_url": "https://example.com/second",
                "custom_slug": "unique-slug",
            },
            cookies={"access_token": token},
        )
        assert response.status_code == 409
        assert "already taken" in response.text

    @pytest.mark.asyncio
    async def test_create_link_short_custom_slug(self, client):
        token = await self._register_and_get_token(client)

        response = await client.post(
            "/dashboard/links",
            data={
                "target_url": "https://example.com/test",
                "custom_slug": "ab",
            },
            cookies={"access_token": token},
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_link_unauthenticated(self, client):
        response = await client.post(
            "/dashboard/links",
            data={"target_url": "https://example.com/test"},
        )
        # Should get 401 since no token
        assert response.status_code in (401, 403)


class TestDashboard:
    async def _register_and_get_token(self, client, email="dash@example.com"):
        response = await client.post(
            "/register",
            data={
                "email": email,
                "password": "TestPass1",
                "display_name": "Dash User",
            },
            follow_redirects=False,
        )
        return response.cookies.get("access_token")

    @pytest.mark.asyncio
    async def test_dashboard_requires_auth(self, client):
        response = await client.get("/dashboard")
        assert response.status_code in (401, 403)

    @pytest.mark.asyncio
    async def test_dashboard_empty_state(self, client):
        token = await self._register_and_get_token(client)

        response = await client.get(
            "/dashboard",
            cookies={"access_token": token},
        )
        assert response.status_code == 200
        assert "No links yet" in response.text

    @pytest.mark.asyncio
    async def test_dashboard_shows_links(self, client):
        token = await self._register_and_get_token(client)

        # Create a link
        await client.post(
            "/dashboard/links",
            data={
                "target_url": "https://example.com/shown",
                "title": "Visible Link",
            },
            cookies={"access_token": token},
            follow_redirects=False,
        )

        # Check dashboard
        response = await client.get(
            "/dashboard",
            cookies={"access_token": token},
        )
        assert response.status_code == 200
        assert "Visible Link" in response.text
        assert "example.com/shown" in response.text

    @pytest.mark.asyncio
    async def test_dashboard_search(self, client):
        token = await self._register_and_get_token(client)

        # Create links
        await client.post(
            "/dashboard/links",
            data={
                "target_url": "https://example.com/one",
                "title": "Alpha Link",
            },
            cookies={"access_token": token},
            follow_redirects=False,
        )
        await client.post(
            "/dashboard/links",
            data={
                "target_url": "https://example.com/two",
                "title": "Beta Link",
            },
            cookies={"access_token": token},
            follow_redirects=False,
        )

        # Search for Alpha
        response = await client.get(
            "/dashboard?search=Alpha",
            cookies={"access_token": token},
        )
        assert response.status_code == 200
        assert "Alpha Link" in response.text

    @pytest.mark.asyncio
    async def test_dashboard_filter_by_tag(self, client):
        token = await self._register_and_get_token(client)

        await client.post(
            "/dashboard/links",
            data={
                "target_url": "https://example.com/tagged",
                "title": "Tagged One",
                "tags": "promo",
            },
            cookies={"access_token": token},
            follow_redirects=False,
        )
        await client.post(
            "/dashboard/links",
            data={
                "target_url": "https://example.com/other",
                "title": "Other Link",
                "tags": "social",
            },
            cookies={"access_token": token},
            follow_redirects=False,
        )

        response = await client.get(
            "/dashboard?tag=promo",
            cookies={"access_token": token},
        )
        assert response.status_code == 200
        assert "Tagged One" in response.text


class TestDeleteLink:
    async def _register_and_get_token(self, client, email="del@example.com"):
        response = await client.post(
            "/register",
            data={
                "email": email,
                "password": "TestPass1",
                "display_name": "Del User",
            },
            follow_redirects=False,
        )
        return response.cookies.get("access_token")

    @pytest.mark.asyncio
    async def test_delete_link(self, client):
        token = await self._register_and_get_token(client)

        # Create a link
        await client.post(
            "/dashboard/links",
            data={
                "target_url": "https://example.com/delete-me",
                "title": "Delete Me",
            },
            cookies={"access_token": token},
            follow_redirects=False,
        )

        # Get dashboard to find the link id (it's link id 1 since fresh db)
        response = await client.post(
            "/dashboard/links/1/delete",
            cookies={"access_token": token},
            follow_redirects=False,
        )
        assert response.status_code == 302

    @pytest.mark.asyncio
    async def test_delete_nonexistent_link(self, client):
        token = await self._register_and_get_token(client)

        response = await client.post(
            "/dashboard/links/999/delete",
            cookies={"access_token": token},
        )
        assert response.status_code == 404
