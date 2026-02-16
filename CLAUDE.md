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
- [x] Implement user registration and login (JWT auth, httponly cookies)
- [x] Build auth-protected dashboard layout and base templates (Tailwind CSS)
- [x] Implement link creation (auto-slug + custom slug, URL validation)
- [x] Build public redirect endpoint with click tracking
- [x] Implement click metadata capture (GeoIP, user-agent parsing, referrer)
- [x] Build per-link analytics page (charts, tables for referrers/countries/devices)
- [ ] Implement QR code generation endpoint
- [x] Add link tagging, filtering, and search on dashboard
- [x] Implement CSV export of click data
- [x] Write comprehensive tests (auth, links, redirects, analytics)
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

### Session 3 — AUTH, DASHBOARD & LINK CREATION
- Implemented user registration with form validation (email, password strength, display name)
- Implemented login with JWT httponly cookie auth and bcrypt password hashing
- Built auth dependency (get_current_user / get_optional_user) for route protection
- Created professional registration and login pages with Tailwind CSS
- Built auth-protected dashboard with sticky nav, user avatar, and logout
- Implemented link creation with auto-generated base62 slugs and custom slug support
- Full URL validation (http/https only, valid domain required)
- Link tagging (comma-separated), search by title/slug/URL, filter by tag
- Link deletion with confirmation dialog
- Copy-to-clipboard for short URLs
- Empty states and error states throughout
- Create link modal with form validation and error feedback
- All 36 tests passing (auth: 19, health: 2, links: 15)

### Session 4 — REDIRECT, CLICK TRACKING, ANALYTICS & CSV EXPORT
- Built public redirect endpoint (GET /{slug}) that resolves short links to target URLs
- Implemented click tracking inline with redirect — captures IP, referrer, user-agent
- GeoIP integration via ip-api.com with in-memory cache (5000 entries)
- User-agent parsing via `user-agents` library — extracts browser, OS, device type
- Built comprehensive per-link analytics page with Chart.js line chart for clicks over time
- Analytics dashboard shows: total clicks, top countries, referrers, browsers, OS, device breakdown
- Recent clicks table with time, country, browser, OS, device badge, and referrer
- Stats overview cards (total clicks, top country, top browser, top device)
- Empty state for links with no clicks yet
- CSV export endpoint for all click data (downloadable file)
- Custom 404 page for nonexistent short links
- Auth guards on analytics and CSV export (owner-only access)
- All 60 tests passing (analytics: 17, auth: 19, health: 2, links: 15, redirect: 7)

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
    dependencies.py    # Auth dependencies (get_current_user, get_optional_user)
    main.py            # FastAPI app entry point
    api/
      __init__.py
      analytics.py     # Per-link analytics page & CSV export
      auth.py          # Registration, login, logout routes
      dashboard.py     # Dashboard & link CRUD routes
      health.py        # Health check endpoint
      pages.py         # Landing page route
      redirect.py      # Public short-link redirect with click tracking
    models/
      __init__.py      # Model imports (User, Link, Click)
      user.py          # User model
      link.py          # Link model
      click.py         # Click model
    schemas/
      __init__.py
      auth.py          # RegisterRequest, LoginRequest, UserResponse
      link.py          # LinkCreateRequest, LinkResponse
    services/
      __init__.py
      auth.py          # Password hashing, JWT, user CRUD
      clicks.py        # Click recording, GeoIP, UA parsing, analytics aggregation
      links.py         # Slug generation, link CRUD, search/filter
    templates/
      layouts/
        base.html      # Base template (Tailwind CSS + Inter font)
        dashboard.html # Dashboard layout (nav, user menu)
      pages/
        404.html       # Custom 404 page for missing links
        analytics.html # Per-link analytics page (charts, tables)
        dashboard.html # Dashboard page (link list, create modal)
        landing.html   # Public landing page
        login.html     # Login page
        register.html  # Registration page
    static/
      .gitkeep
tests/
  __init__.py
  conftest.py          # Test fixtures (in-memory DB, async client)
  test_analytics.py     # Analytics, click stats, CSV export, UA parsing tests
  test_auth.py         # Auth tests (register, login, logout, JWT)
  test_health.py       # Health check and landing page tests
  test_links.py        # Link creation, dashboard, delete tests
  test_redirect.py     # Redirect, click tracking, 404 tests
```
