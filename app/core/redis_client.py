"""
Redis client configuration and connection management.

Provides async Redis client for caching and session management.
"""

from typing import Optional

from redis.asyncio import Redis

from app.core.config import settings

# Global Redis client instance
_redis_client: Optional[Redis] = None


async def get_redis_client() -> Redis:
    """
    Get or create Redis client instance.

    Returns:
        Redis: Async Redis client

    Raises:
        ConnectionError: If Redis connection fails
    """
    global _redis_client

    if _redis_client is None:
        _redis_client = Redis.from_url(
            settings.redis_url,
            password=settings.redis_password,
            encoding="utf-8",
            decode_responses=True,
            socket_connect_timeout=5,
            socket_keepalive=True,
            health_check_interval=30,
        )

    return _redis_client


async def close_redis_client() -> None:
    """Close Redis client connection."""
    global _redis_client

    if _redis_client is not None:
        await _redis_client.close()
        _redis_client = None
