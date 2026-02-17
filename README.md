# LinkDrip

**Short-link management and click analytics platform.** Create shortened URLs with custom slugs, track every click with detailed analytics, generate QR codes, and organize links with tags. Self-hostable, open-source, and built for marketers, creators, and small businesses.

## Features

- **Short Links** — Create shortened URLs with auto-generated or custom slugs (base62-encoded, 6 characters)
- **Click Analytics** — Track every click with referrer, country, city, device, browser, and OS data
- **Interactive Charts** — Visualize clicks over time with Chart.js line charts
- **QR Codes** — Generate branded, downloadable QR codes (PNG) for any short link
- **Link Tagging** — Organize links with tags and filter/search on the dashboard
- **CSV Export** — Export all click data for any link with CSV injection protection
- **GeoIP Lookup** — Automatic country/city detection via ip-api.com with in-memory caching
- **User-Agent Parsing** — Extract browser, OS, and device type (Desktop/Mobile/Tablet/Bot) from every click
- **Secure Auth** — JWT with httponly cookies and bcrypt password hashing
- **Responsive UI** — Tailwind CSS with Inter font, works on desktop and mobile

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Backend** | Python 3.12, FastAPI, Uvicorn |
| **Database** | SQLite (async via aiosqlite), SQLAlchemy 2.0 |
| **Migrations** | Alembic |
| **Frontend** | Jinja2 templates, Tailwind CSS (CDN), Chart.js |
| **Auth** | JWT (python-jose) + bcrypt (passlib) |
| **QR Codes** | qrcode + Pillow |
| **GeoIP** | ip-api.com (free tier) |
| **Container** | Docker multi-stage build |

## Quick Start

### Docker (recommended)

```bash
# One-liner: build and run
docker compose up -d

# Open in browser
open http://localhost:8000
```

To set a secure secret key:

```bash
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(64))") docker compose up -d
```

### Local Development

```bash
# Clone the repo
git clone https://github.com/arcangelileo/link-drip.git
cd link-drip

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate   # Windows

# Install dependencies (with dev tools)
pip install -e ".[dev]"

# Copy and configure environment
cp .env.example .env
# Edit .env — set a secure SECRET_KEY for production

# Run database migrations
alembic upgrade head

# Start the development server
uvicorn src.app.main:app --reload
```

The app will be available at [http://localhost:8000](http://localhost:8000).

## Configuration

All configuration is via environment variables or a `.env` file:

| Variable | Default | Description |
|----------|---------|-------------|
| `APP_NAME` | `LinkDrip` | Application display name shown in the UI |
| `APP_URL` | `http://localhost:8000` | Public URL used to generate short links and QR codes |
| `SECRET_KEY` | `change-me-...` | JWT signing key — **must be a strong random value in production** |
| `DEBUG` | `false` | Enable debug mode (verbose SQL logging, insecure cookies) |
| `DATABASE_URL` | `sqlite+aiosqlite:///./linkdrip.db` | Async database connection string |
| `JWT_ALGORITHM` | `HS256` | JWT signing algorithm |
| `JWT_EXPIRATION_MINUTES` | `1440` | JWT token lifetime in minutes (default: 24 hours) |

Generate a secure secret key:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(64))"
```

## API Endpoints

### Public

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | Landing page |
| `GET` | `/health` | Health check (`{"status": "healthy"}`) |
| `GET` | `/register` | Registration page |
| `POST` | `/register` | Create account (form: email, password, display_name) |
| `GET` | `/login` | Login page |
| `POST` | `/login` | Log in (form: email, password) |
| `GET` | `/logout` | Log out (clears auth cookie) |
| `GET, HEAD` | `/{slug}` | Redirect short link to target URL (tracks clicks on GET only) |

### Authenticated (requires login)

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/dashboard` | Link dashboard with search and tag filtering |
| `POST` | `/dashboard/links` | Create a new short link |
| `POST` | `/dashboard/links/{id}/delete` | Delete a link |
| `GET` | `/dashboard/links/{id}/analytics` | Per-link analytics page (charts, tables) |
| `GET` | `/dashboard/links/{id}/export` | Export all clicks as CSV |
| `GET` | `/dashboard/links/{id}/qr` | QR code page with preview |
| `GET` | `/dashboard/links/{id}/qr.png` | Download QR code as PNG image |

## Architecture

```
src/app/
├── api/              # Route handlers
│   ├── analytics.py  # Per-link analytics, CSV export, QR code endpoints
│   ├── auth.py       # Registration, login, logout
│   ├── dashboard.py  # Dashboard and link CRUD
│   ├── health.py     # Health check
│   ├── pages.py      # Landing page
│   └── redirect.py   # Public short-link redirect with click tracking
├── models/           # SQLAlchemy ORM models
│   ├── user.py       # User (email, password, plan)
│   ├── link.py       # Link (slug, target_url, tags, click_count)
│   └── click.py      # Click (ip, country, browser, os, device, referrer)
├── schemas/          # Pydantic request validation
│   ├── auth.py       # RegisterRequest, LoginRequest
│   └── link.py       # LinkCreateRequest
├── services/         # Business logic
│   ├── auth.py       # Password hashing, JWT tokens, user CRUD
│   ├── clicks.py     # Click recording, GeoIP, UA parsing, analytics
│   └── links.py      # Slug generation, link CRUD, search/filter
├── templates/        # Jinja2 HTML templates
│   ├── layouts/      # Base and dashboard layouts (Tailwind CSS)
│   └── pages/        # Page templates (landing, dashboard, analytics, etc.)
├── config.py         # Pydantic Settings (env var configuration)
├── database.py       # Async SQLAlchemy engine and session
├── dependencies.py   # Auth dependencies (get_current_user)
└── main.py           # FastAPI app entry point
```

### Key Design Decisions

- **Slug generation**: Base62-encoded auto-incrementing ID (offset by 100,000 for 3+ char minimum), zero-padded to 6 characters. Custom slugs support 3-50 chars, alphanumeric + hyphens.
- **Click tracking**: Clicks are recorded inline during the redirect. HEAD requests (from crawlers/preview tools) return the redirect without recording a click.
- **GeoIP caching**: Successful lookups are cached in-memory (up to 5,000 entries). Failed lookups are not cached so transient errors can be retried.
- **Auth flow**: JWT stored in httponly cookies. Unauthenticated users are redirected to `/login` (not shown a JSON error).
- **CSV security**: All exported fields are sanitized against CSV injection (formula characters `=`, `+`, `-`, `@`, `\t`, `\r` are escaped).
- **Atomic counters**: Click counts use SQL `UPDATE SET click_count = click_count + 1` to prevent race conditions.

## Running Tests

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run the full test suite (91 tests)
pytest

# Run with verbose output
pytest -v

# Run a specific test file
pytest tests/test_auth.py -v
```

Tests use an in-memory SQLite database and require no external services. Test coverage includes:

- **Auth** (19 tests): Registration, login, logout, JWT, password validation, auth redirects
- **Links** (15+ tests): Slug generation, link CRUD, dashboard, search/filter, delete, IDOR protection
- **Redirect** (9 tests): Short-link resolution, click tracking, HEAD requests, 404 handling
- **Analytics** (33 tests): UA parsing, click stats, analytics page, CSV export/sanitization, QR codes

## Docker

### Build and Run

```bash
# Build the image
docker build -t linkdrip .

# Run with a secure secret key
docker run -p 8000:8000 \
  -e SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(64))") \
  -v linkdrip-data:/app/data \
  linkdrip
```

### Docker Compose

```bash
# Start in detached mode
docker compose up -d

# View logs
docker compose logs -f app

# Stop
docker compose down
```

The Docker image uses:
- **Multi-stage build** for a smaller runtime image
- **Non-root user** (`linkdrip`) for security
- **Health check** hitting `/health` every 30 seconds
- **Proxy headers** enabled for running behind a reverse proxy
- **Named volume** for SQLite database persistence

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Install dev dependencies: `pip install -e ".[dev]"`
4. Make your changes
5. Run the test suite: `pytest`
6. Commit and push: `git push origin feature/my-feature`
7. Open a pull request

## License

MIT
