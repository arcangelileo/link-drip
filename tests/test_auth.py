import pytest

from src.app.services.auth import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


class TestPasswordHashing:
    def test_hash_and_verify(self):
        password = "MyP@ssw0rd"
        hashed = hash_password(password)
        assert hashed != password
        assert verify_password(password, hashed)

    def test_wrong_password(self):
        hashed = hash_password("CorrectPass1")
        assert not verify_password("WrongPass1", hashed)


class TestJWT:
    def test_create_and_decode_token(self):
        user_id = 42
        token = create_access_token(user_id)
        decoded = decode_access_token(token)
        assert decoded == user_id

    def test_invalid_token(self):
        assert decode_access_token("invalid.token.here") is None

    def test_empty_token(self):
        assert decode_access_token("") is None


class TestRegister:
    @pytest.mark.asyncio
    async def test_register_success(self, client):
        response = await client.post(
            "/register",
            data={
                "email": "test@example.com",
                "password": "TestPass1",
                "display_name": "Test User",
            },
            follow_redirects=False,
        )
        assert response.status_code == 302
        assert response.headers["location"] == "/dashboard"
        assert "access_token" in response.cookies

    @pytest.mark.asyncio
    async def test_register_weak_password(self, client):
        response = await client.post(
            "/register",
            data={
                "email": "test@example.com",
                "password": "weak",
                "display_name": "Test User",
            },
        )
        assert response.status_code == 422
        assert "8 characters" in response.text

    @pytest.mark.asyncio
    async def test_register_no_uppercase(self, client):
        response = await client.post(
            "/register",
            data={
                "email": "test@example.com",
                "password": "lowercase1",
                "display_name": "Test User",
            },
        )
        assert response.status_code == 422
        assert "uppercase" in response.text

    @pytest.mark.asyncio
    async def test_register_duplicate_email(self, client):
        # First registration
        await client.post(
            "/register",
            data={
                "email": "dupe@example.com",
                "password": "TestPass1",
                "display_name": "First User",
            },
            follow_redirects=False,
        )
        # Second registration with same email
        response = await client.post(
            "/register",
            data={
                "email": "dupe@example.com",
                "password": "TestPass1",
                "display_name": "Second User",
            },
        )
        assert response.status_code == 409
        assert "already exists" in response.text

    @pytest.mark.asyncio
    async def test_register_invalid_email(self, client):
        response = await client.post(
            "/register",
            data={
                "email": "not-an-email",
                "password": "TestPass1",
                "display_name": "Test User",
            },
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_register_short_display_name(self, client):
        response = await client.post(
            "/register",
            data={
                "email": "test@example.com",
                "password": "TestPass1",
                "display_name": "A",
            },
        )
        assert response.status_code == 422
        assert "2 characters" in response.text

    @pytest.mark.asyncio
    async def test_register_page_get(self, client):
        response = await client.get("/register")
        assert response.status_code == 200
        assert "Create your account" in response.text


class TestLogin:
    @pytest.mark.asyncio
    async def test_login_success(self, client):
        # Register first
        await client.post(
            "/register",
            data={
                "email": "login@example.com",
                "password": "TestPass1",
                "display_name": "Login User",
            },
            follow_redirects=False,
        )
        # Login
        response = await client.post(
            "/login",
            data={"email": "login@example.com", "password": "TestPass1"},
            follow_redirects=False,
        )
        assert response.status_code == 302
        assert response.headers["location"] == "/dashboard"
        assert "access_token" in response.cookies

    @pytest.mark.asyncio
    async def test_login_wrong_password(self, client):
        await client.post(
            "/register",
            data={
                "email": "login2@example.com",
                "password": "TestPass1",
                "display_name": "Login User",
            },
            follow_redirects=False,
        )
        response = await client.post(
            "/login",
            data={"email": "login2@example.com", "password": "WrongPass1"},
        )
        assert response.status_code == 401
        assert "Invalid email or password" in response.text

    @pytest.mark.asyncio
    async def test_login_nonexistent_email(self, client):
        response = await client.post(
            "/login",
            data={"email": "nobody@example.com", "password": "TestPass1"},
        )
        assert response.status_code == 401
        assert "Invalid email or password" in response.text

    @pytest.mark.asyncio
    async def test_login_page_get(self, client):
        response = await client.get("/login")
        assert response.status_code == 200
        assert "Welcome back" in response.text


class TestLogout:
    @pytest.mark.asyncio
    async def test_logout(self, client):
        response = await client.get("/logout", follow_redirects=False)
        assert response.status_code == 302
        assert response.headers["location"] == "/"


class TestAuthRedirects:
    @pytest.mark.asyncio
    async def test_register_redirects_when_logged_in(self, client):
        # Register and capture cookie
        reg_response = await client.post(
            "/register",
            data={
                "email": "redir@example.com",
                "password": "TestPass1",
                "display_name": "Redir User",
            },
            follow_redirects=False,
        )
        token = reg_response.cookies.get("access_token")

        # Visit register page while logged in
        response = await client.get(
            "/register",
            cookies={"access_token": token},
            follow_redirects=False,
        )
        assert response.status_code == 302
        assert response.headers["location"] == "/dashboard"

    @pytest.mark.asyncio
    async def test_login_redirects_when_logged_in(self, client):
        reg_response = await client.post(
            "/register",
            data={
                "email": "redir2@example.com",
                "password": "TestPass1",
                "display_name": "Redir User",
            },
            follow_redirects=False,
        )
        token = reg_response.cookies.get("access_token")

        response = await client.get(
            "/login",
            cookies={"access_token": token},
            follow_redirects=False,
        )
        assert response.status_code == 302
        assert response.headers["location"] == "/dashboard"
