# LinkDrip

Phase: DEVELOPMENT

## Project Spec
- **Repo**: https://github.com/arcangelileo/link-drip
- **Idea**: LinkDrip is a short-link management and click analytics platform. Users create shortened URLs with optional custom slugs, track clicks with detailed analytics (referrer, country, device, browser, OS), generate QR codes for any link, and organize links with tags. It targets marketers, small businesses, and creators who need to track link performance across campaigns without paying enterprise prices. Think Bitly/Dub.co but self-hostable and affordable.
- **Target users**: Digital marketers, small business owners, content creators, and agencies who share links across social media, email campaigns, and ads and need to understand click-through performance.
- **Revenue model**: Freemium SaaS — Free tier (50 links, 1,000 clicks/month, basic analytics). Pro tier ($9/mo — unlimited links, 50K clicks/month, full analytics, custom slugs, QR codes, CSV export). Business tier ($29/mo — unlimited everything, API access, team members, custom domains).
- **Tech stack**: Python, FastAPI, SQLite (start simple), Jinja2 + Tailwind CSS, APScheduler, Docker
- **MVP scope**:
  - User registration & login (JWT auth with httponly cookies)
  - Create short links with auto-generated or custom slugs
  - Click tracking with metadata capture (IP → country via free GeoIP, referrer, user-agent parsing)
  - Dashboard showing all links with click counts
  - Per-link analytics page (clicks over time chart, top referrers, countries, devices/browsers)
  - QR code generation for each link
  - Link tagging and filtering
  - Public redirect endpoint (the core short-link resolution)
  - CSV export of click data

## Architecture Decisions
- **Short slug generation**: Use a base62-encoded auto-incrementing ID (6 chars) for generated slugs; allow custom slugs (3-50 chars, alphanumeric + hyphens)
- **Click tracking**: Async — redirect immediately, log click data in background to avoid latency on the redirect
- **GeoIP**: Use a lightweight free IP geolocation approach (ip-api.com free tier or a local MaxMind GeoLite2 DB). Start with ip-api.com for simplicity, cache results
- **User-agent parsing**: Use `user-agents` Python library to extract device, browser, OS
- **Analytics aggregation**: Store raw clicks; compute aggregates on-the-fly for MVP. Add materialized views/caching later if needed
- **QR codes**: Generate server-side with `qrcode` Python library, serve as PNG
- **URL validation**: Validate target URLs on creation (must be valid HTTP/HTTPS URL)
- **Rate limiting**: Basic rate limiting on link creation and redirect endpoints
- **src layout**: `src/app/` with `api/`, `models/`, `schemas/`, `services/`, `templates/` subdirs
- **Auth**: JWT with httponly cookies, bcrypt password hashing
- **DB migrations**: Alembic from the start
- **Background tasks**: APScheduler integrated into FastAPI lifespan
- **Frontend**: Jinja2 templates + Tailwind CSS via CDN + Inter font
- **Config**: Pydantic Settings for env var configuration
- **ORM**: Async SQLAlchemy with aiosqlite
- **Docker**: Multi-stage build with non-root user
- **Tests**: In-memory SQLite + async httpx test client

## Task Backlog
- [x] Create project structure (pyproject.toml, src/app layout, configs)
- [x] Set up FastAPI app skeleton with health check and config
- [x] Set up database models (User, Link, Click) and Alembic migrations
- [ ] Implement user registration and login (JWT auth, httponly cookies)
- [ ] Build auth-protected dashboard layout and base templates (Tailwind CSS)
- [ ] Implement link creation (auto-slug + custom slug, URL validation)
- [ ] Build public redirect endpoint with click tracking
- [ ] Implement click metadata capture (GeoIP, user-agent parsing, referrer)
- [ ] Build per-link analytics page (charts, tables for referrers/countries/devices)
- [ ] Implement QR code generation endpoint
- [ ] Add link tagging, filtering, and search on dashboard
- [ ] Implement CSV export of click data
- [ ] Write comprehensive tests (auth, links, redirects, analytics)
- [ ] Write Dockerfile and docker-compose.yml
- [ ] Write README with setup and deploy instructions

## Progress Log
### Session 1 — IDEATION
- Chose idea: LinkDrip (short-link management + click analytics)
- Created spec and backlog
- Key differentiator: self-hostable, affordable, developer-friendly

### Session 2 — SCAFFOLDING
- Created GitHub repo and pushed initial code
- Set up project structure: pyproject.toml with all dependencies, src/app layout
- Built FastAPI app with health check endpoint and landing page
- Created database models: User, Link, Click (async SQLAlchemy + aiosqlite)
- Configured Alembic for async migrations; generated initial migration
- Built professional landing page with Tailwind CSS (features, pricing sections)
- Set up test infrastructure (in-memory SQLite, async httpx client)
- All tests passing (2/2)

## Known Issues
(none yet)

## Files Structure
```
.gitignore
.env.example
pyproject.toml
alembic.ini
CLAUDE.md
alembic/
  env.py
  script.py.mako
  versions/
    45e161a449ec_initial_tables_users_links_clicks.py
src/
  __init__.py
  app/
    __init__.py
    config.py          # Pydantic Settings configuration
    database.py        # Async SQLAlchemy engine and session
    main.py            # FastAPI app entry point
    api/
      __init__.py
      health.py        # Health check endpoint
      pages.py         # Landing page route
    models/
      __init__.py
      user.py          # User model
      link.py          # Link model
      click.py         # Click model
    schemas/
      __init__.py
    services/
      __init__.py
    templates/
      layouts/
        base.html      # Base template (Tailwind CSS + Inter font)
      pages/
        landing.html   # Public landing page
    static/
      .gitkeep
tests/
  __init__.py
  conftest.py          # Test fixtures (in-memory DB, async client)
  test_health.py       # Health check and landing page tests
```
