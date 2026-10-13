import asyncio
import httpx

from ..storage.cache import SQLiteCache
from .base import ProviderError

cache = SQLiteCache()


async def get_json(
    url,
    params=None,
    headers=None,
    provider="http",
    ttl=900,
    retries=3,
):
    params = params or {}

    cached = cache.get(provider, url, params)
    if cached is not None:
        return cached, True

    last_error = None

    for attempt in range(retries):
        try:
            async with httpx.AsyncClient(
                timeout=25,
                follow_redirects=True,
            ) as client:

                response = await client.get(
                    url,
                    params=params,
                    headers=headers,
                )

                # Temporary provider/rate-limit failures
                if response.status_code in (408, 429, 500, 502, 503, 504):
                    raise ProviderError(
                        f"{provider} temporary HTTP "
                        f"{response.status_code}: "
                        f"{response.text[:500]}"
                    )

                # Permanent HTTP errors
                if response.status_code >= 400:
                    raise ProviderError(
                        f"{provider} HTTP {response.status_code}: "
                        f"{response.text[:1000]}"
                    )

                try:
                    data = response.json()
                except ValueError:
                    raise ProviderError(
                        f"{provider} returned non-JSON response: "
                        f"{response.text[:1000]}"
                    )

                cache.set(
                    provider,
                    url,
                    params,
                    data,
                    ttl,
                )

                return data, False

        except Exception as exc:
            last_error = exc

            if attempt < retries - 1:
                await asyncio.sleep(2 ** attempt)

    raise ProviderError(
        f"{provider} request failed after {retries} attempts: "
        f"{last_error}"
    )