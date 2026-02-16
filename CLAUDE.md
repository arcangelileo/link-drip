# LinkDrip

Phase: SCAFFOLDING

## Project Spec
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
- [ ] Create project structure (pyproject.toml, src/app layout, configs)
- [ ] Set up FastAPI app skeleton with health check and config
- [ ] Set up database models (User, Link, Click) and Alembic migrations
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

## Known Issues
(none yet)

## Files Structure
(will be updated as files are created)
