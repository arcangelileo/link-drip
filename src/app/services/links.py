import string

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.models.link import Link

BASE62_CHARS = string.digits + string.ascii_lowercase + string.ascii_uppercase


def encode_base62(num: int) -> str:
    if num == 0:
        return BASE62_CHARS[0]
    result = []
    while num > 0:
        result.append(BASE62_CHARS[num % 62])
        num //= 62
    return "".join(reversed(result))


def generate_slug(link_id: int) -> str:
    slug = encode_base62(link_id + 100000)  # offset to ensure 3+ char slugs
    return slug.ljust(6, "0")[:6] if len(slug) < 6 else slug


async def get_link_by_slug(db: AsyncSession, slug: str) -> Link | None:
    result = await db.execute(select(Link).where(Link.slug == slug))
    return result.scalar_one_or_none()


async def slug_exists(db: AsyncSession, slug: str) -> bool:
    result = await db.execute(select(Link.id).where(Link.slug == slug))
    return result.scalar_one_or_none() is not None


async def create_link(
    db: AsyncSession,
    user_id: int,
    target_url: str,
    custom_slug: str | None = None,
    title: str | None = None,
    tags: str | None = None,
) -> Link:
    if custom_slug:
        slug = custom_slug
    else:
        # Create with placeholder slug, then update with base62-encoded ID
        link = Link(
            slug="__temp__",
            target_url=target_url,
            title=title,
            tags=tags,
            user_id=user_id,
        )
        db.add(link)
        await db.flush()  # Get the ID
        slug = generate_slug(link.id)

        # Ensure uniqueness (very unlikely collision, but be safe)
        while await slug_exists(db, slug):
            slug = slug + "x"

        link.slug = slug
        await db.commit()
        await db.refresh(link)
        return link

    link = Link(
        slug=slug,
        target_url=target_url,
        title=title,
        tags=tags,
        user_id=user_id,
    )
    db.add(link)
    await db.commit()
    await db.refresh(link)
    return link


async def get_user_links(
    db: AsyncSession,
    user_id: int,
    search: str | None = None,
    tag: str | None = None,
) -> list[Link]:
    query = select(Link).where(Link.user_id == user_id)

    if search:
        search_term = f"%{search}%"
        query = query.where(
            (Link.title.ilike(search_term))
            | (Link.slug.ilike(search_term))
            | (Link.target_url.ilike(search_term))
        )

    if tag:
        tag_term = tag.lower().strip()
        query = query.where(Link.tags.ilike(f"%{tag_term}%"))

    query = query.order_by(Link.created_at.desc())
    result = await db.execute(query)
    return list(result.scalars().all())


async def delete_link(db: AsyncSession, link_id: int, user_id: int) -> bool:
    result = await db.execute(
        select(Link).where(Link.id == link_id, Link.user_id == user_id)
    )
    link = result.scalar_one_or_none()
    if link is None:
        return False
    await db.delete(link)
    await db.commit()
    return True
