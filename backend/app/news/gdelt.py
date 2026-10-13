from ..providers.http import get_json


async def search_news(symbol, company_name=None, max_records=25):
    symbol = symbol.strip().upper()

    query = (
        f'"{company_name}"'
        if company_name
        else symbol
    )

    params = {
        "query": query,
        "mode": "artlist",
        "format": "json",
        "maxrecords": max_records,
        "sort": "datedesc",
    }

    data, _ = await get_json(
        "https://api.gdeltproject.org/api/v2/doc/doc",
        params,
        provider="gdelt",
        ttl=900,
    )

    if not isinstance(data, dict):
        return []

    articles = data.get("articles", [])

    if not isinstance(articles, list):
        return []

    return articles