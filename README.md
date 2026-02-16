# LinkDrip

Short-link management and click analytics platform. Create shortened URLs, track clicks with detailed analytics, generate QR codes, and organize links with tags.

## Features

- **Short Links** — Create shortened URLs with auto-generated or custom slugs
- **Click Analytics** — Track clicks with referrer, country, device, browser, and OS data
- **QR Codes** — Generate downloadable QR codes for any short link
- **Link Tagging** — Organize links with tags and filter on the dashboard
- **CSV Export** — Export all click data for any link
- **GeoIP Lookup** — Automatic country/city detection from visitor IP addresses
- **User-Agent Parsing** — Extract browser, OS, and device type from every click

## Tech Stack

- **Backend:** Python 3.12, FastAPI, SQLAlchemy (async), aiosqlite
- **Frontend:** Jinja2 templates, Tailwind CSS, Chart.js
- **Auth:** JWT with httponly cookies, bcrypt password hashing
- **Database:** SQLite (easily swappable to PostgreSQL)
- **Containerization:** Docker with multi-stage build

## Quick Start

### Prerequisites

- Python 3.11+
- pip

### Local Development

```bash
# Clone the repo
git clone https://github.com/arcangelileo/link-drip.git
cd link-drip

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate   # Windows

# Install dependencies
pip install -e ".[dev]"

# Copy environment config
cp .env.example .env
# Edit .env and set a secure SECRET_KEY

# Run database migrations
alembic upgrade head

# Start the development server
uvicorn src.app.main:app --reload
```

The app will be available at [http://localhost:8000](http://localhost:8000).

### Docker

```bash
# Build and run with Docker Compose
docker compose up -d

# Or build and run manually
docker build -t linkdrip .
docker run -p 8000:8000 -e SECRET_KEY=your-secret-key linkdrip
```

## Configuration

All configuration is via environment variables (or `.env` file):

| Variable | Default | Description |
|---|---|---|
| `APP_NAME` | `LinkDrip` | Application display name |
| `APP_URL` | `http://localhost:8000` | Public URL (used in short links and QR codes) |
| `SECRET_KEY` | `change-me-...` | JWT signing key — **set a strong random value in production** |
| `DATABASE_URL` | `sqlite+aiosqlite:///./linkdrip.db` | Database connection string |
| `DEBUG` | `false` | Enable debug mode |
| `JWT_ALGORITHM` | `HS256` | JWT signing algorithm |
| `JWT_EXPIRATION_MINUTES` | `1440` | JWT token lifetime (default: 24 hours) |

## Running Tests

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run the test suite
pytest

# Run with verbose output
pytest -v
```

Tests use an in-memory SQLite database and require no external services.

## Project Structure

```
src/app/
├── api/           # Route handlers (auth, dashboard, analytics, redirect)
├── models/        # SQLAlchemy models (User, Link, Click)
├── schemas/       # Pydantic request/response schemas
├── services/      # Business logic (auth, links, clicks)
├── templates/     # Jinja2 HTML templates
│   ├── layouts/   # Base and dashboard layouts
│   └── pages/     # Page templates
├── static/        # Static assets
├── config.py      # Pydantic Settings configuration
├── database.py    # Async SQLAlchemy engine and session
├── dependencies.py # Auth dependencies
└── main.py        # FastAPI app entry point
```

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/` | Landing page |
| `GET` | `/health` | Health check |
| `POST` | `/register` | Create account |
| `POST` | `/login` | Log in |
| `GET` | `/logout` | Log out |
| `GET` | `/dashboard` | Link dashboard |
| `POST` | `/dashboard/links` | Create a new short link |
| `POST` | `/dashboard/links/{id}/delete` | Delete a link |
| `GET` | `/dashboard/links/{id}/analytics` | Link analytics page |
| `GET` | `/dashboard/links/{id}/export` | Export clicks as CSV |
| `GET` | `/dashboard/links/{id}/qr` | QR code page |
| `GET` | `/dashboard/links/{id}/qr.png` | QR code image (PNG) |
| `GET` | `/{slug}` | Redirect short link to target URL |

## License

MIT
