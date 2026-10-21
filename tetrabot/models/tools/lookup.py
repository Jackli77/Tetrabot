"""The lookup tools: weather, Wikipedia, web search and time.

Every tool here is a thin, well-behaved wrapper around a public API.  None
of them needs an API key, so the bot works out of the box.

They all share the same shape: build a URL, fetch it, turn the answer into
a small dictionary, and return it.  A failure raises :class:`ToolError`,
which the caller turns into a message the model can relay.
"""
from __future__ import annotations

from datetime import datetime
from datetime import timezone as dt_timezone
from typing import Any
from urllib.parse import quote

import aiohttp

from tetrabot.models.tools.base import ToolError, ToolResult

#: The User-Agent sent with every request — the public APIs ask for one.
USER_AGENT = "Tetrabot/1.0 (Discord bot; https://github.com/)"

#: How long a lookup may take, in seconds.
LOOKUP_TIMEOUT = 12

#: The Wikipedia editions the bot can search.
WIKIPEDIA_LANGUAGES = {
    "fr": "fr.wikipedia.org",
    "en": "en.wikipedia.org",
    "de": "de.wikipedia.org",
    "es": "es.wikipedia.org",
    "it": "it.wikipedia.org",
}

#: WMO weather codes -> a short description, for the forecast.
WEATHER_CODES = {
    0: "clear sky", 1: "mainly clear", 2: "partly cloudy", 3: "overcast",
    45: "fog", 48: "rime fog", 51: "light drizzle", 53: "drizzle",
    55: "dense drizzle", 61: "light rain", 63: "rain", 65: "heavy rain",
    71: "light snow", 73: "snow", 75: "heavy snow", 77: "snow grains",
    80: "light showers", 81: "showers", 82: "violent showers",
    85: "snow showers", 86: "heavy snow showers",
    95: "thunderstorm", 96: "thunderstorm with hail", 99: "severe thunderstorm",
}


async def _fetch_json(
    session: aiohttp.ClientSession, url: str, params: dict[str, Any] | None = None
) -> Any:
    """Fetch a URL and decode its JSON body.

    Some services answer ``202 Accepted`` with a perfectly valid body, so
    every 2xx status is accepted.
    """
    try:
        async with session.get(url, params=params) as response:
            if not 200 <= response.status < 300:
                body = (await response.text())[:200]
                raise ToolError(f"the service answered {response.status}: {body}")
            try:
                return await response.json(content_type=None)
            except Exception as exc:  # noqa: BLE001 - malformed body
                raise ToolError(f"the service returned an unreadable answer: {exc}") from exc
    except aiohttp.ClientError as exc:
        raise ToolError(f"could not reach the service: {exc}") from exc
    except TimeoutError as exc:
        raise ToolError("the service took too long to answer") from exc


async def _fetch_text(
    session: aiohttp.ClientSession, url: str, params: dict[str, Any] | None = None
) -> str:
    """Fetch a URL and return its body as text."""
    try:
        async with session.get(url, params=params) as response:
            if not 200 <= response.status < 300:
                body = (await response.text())[:200]
                raise ToolError(f"the service answered {response.status}: {body}")
            return await response.text()
    except aiohttp.ClientError as exc:
        raise ToolError(f"could not reach the service: {exc}") from exc
    except TimeoutError as exc:
        raise ToolError("the service took too long to answer") from exc


def _clean_html(text: str) -> str:
    """Remove the little HTML tags Wikipedia puts in its snippets."""
    import re

    return re.sub(r"<[^>]+>", "", text or "").strip()


async def search_wikipedia(query: str, language: str = "fr", limit: int = 3) -> ToolResult:
    """Look a topic up on Wikipedia.

    Returns the summary of the best matching article, plus a few other
    matches so the model can pick the right one.
    """
    query = (query or "").strip()
    if not query:
        raise ToolError("no query was given")

    language = (language or "fr").lower()[:2]
    host = WIKIPEDIA_LANGUAGES.get(language)
    if host is None:
        raise ToolError(
            f"unsupported language {language!r}; use one of "
            + ", ".join(sorted(WIKIPEDIA_LANGUAGES))
        )

    timeout = aiohttp.ClientTimeout(total=LOOKUP_TIMEOUT)
    headers = {"User-Agent": USER_AGENT}
    async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
        # The search tells us the exact title of the best article...
        search_url = f"https://{host}/w/api.php"
        search = await _fetch_json(
            session,
            search_url,
            {
                "action": "query",
                "list": "search",
                "srsearch": query,
                "format": "json",
                "srlimit": max(1, min(limit, 5)),
            },
        )
        hits = (search.get("query") or {}).get("search") or []
        if not hits:
            return ToolResult(
                ok=True,
                data={"found": False, "message": f"no Wikipedia article about {query!r}"},
                source=f"{host}",
            )

        titles = [hit["title"] for hit in hits]
        # ...and the extracts give us the actual text.
        extracts = await _fetch_json(
            session,
            f"https://{host}/w/api.php",
            {
                "action": "query",
                "prop": "extracts",
                "explaintext": 1,
                "exintro": 1,
                "format": "json",
                "titles": "|".join(titles),
            },
        )
        pages = (extracts.get("query") or {}).get("pages") or {}
        articles = []
        for page in pages.values():
            if "missing" in page:
                continue
            articles.append(
                {
                    "title": page.get("title"),
                    "summary": (page.get("extract") or "").strip(),
                    "url": f"https://{host}/wiki/{quote(page.get('title', '').replace(' ', '_'))}",
                }
            )
        # Keep the order of the search results.
        order = {title: index for index, title in enumerate(titles)}
        articles.sort(key=lambda item: order.get(item["title"], 99))

    if not articles:
        return ToolResult(
            ok=True,
            data={"found": False, "message": f"no Wikipedia article about {query!r}"},
            source=host,
        )

    best = articles[0]
    return ToolResult(
        ok=True,
        data={
            "found": True,
            "title": best["title"],
            "summary": best["summary"],
            "url": best["url"],
            "other_matches": [a["title"] for a in articles[1:]],
        },
        source=f"https://{host}",
    )


async def search_web(query: str) -> ToolResult:
    """Look a quick fact up on the web.

    Uses DuckDuckGo's instant answers, which are short and factual — perfect
    for definitions, dates and trivia.
    """
    query = (query or "").strip()
    if not query:
        raise ToolError("no query was given")

    timeout = aiohttp.ClientTimeout(total=LOOKUP_TIMEOUT)
    headers = {"User-Agent": USER_AGENT}
    async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
        data = await _fetch_json(
            session,
            "https://api.duckduckgo.com/",
            {"q": query, "format": "json", "no_html": 1, "skip_disambig": 1},
        )

    abstract = (data.get("AbstractText") or "").strip()
    if not abstract:
        # No instant answer: fall back to the related topics.
        topics = []
        for topic in (data.get("RelatedTopics") or [])[:5]:
            if topic.get("Text"):
                topics.append(topic["Text"])
            for sub in (topic.get("Topics") or [])[:3]:
                if sub.get("Text"):
                    topics.append(sub["Text"])
        if not topics:
            return ToolResult(
                ok=True,
                data={
                    "found": False,
                    "message": f"no quick answer for {query!r}; try another wording",
                },
                source="duckduckgo",
            )
        return ToolResult(
            ok=True,
            data={"found": True, "results": topics[:5]},
            source="duckduckgo",
        )

    return ToolResult(
        ok=True,
        data={
            "found": True,
            "answer": abstract,
            "url": data.get("AbstractURL") or "",
            "heading": data.get("Heading") or "",
        },
        source="duckduckgo",
    )


async def get_weather(city: str) -> ToolResult:
    """The current weather and the forecast for a city.

    Uses Open-Meteo, which needs no API key.
    """
    city = (city or "").strip()
    if not city:
        raise ToolError("no city was given")

    timeout = aiohttp.ClientTimeout(total=LOOKUP_TIMEOUT)
    headers = {"User-Agent": USER_AGENT}
    async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
        # A city name is turned into coordinates...
        places = await _fetch_json(
            session,
            "https://geocoding-api.open-meteo.com/v1/search",
            {"name": city, "count": 1, "language": "fr", "format": "json"},
        )
        results = places.get("results") or []
        if not results:
            return ToolResult(
                ok=True,
                data={"found": False, "message": f"unknown city {city!r}"},
                source="open-meteo",
            )
        place = results[0]

        # ...and the coordinates into the actual weather.
        forecast = await _fetch_json(
            session,
            "https://api.open-meteo.com/v1/forecast",
            {
                "latitude": place["latitude"],
                "longitude": place["longitude"],
                "current": "temperature_2m,apparent_temperature,weather_code,wind_speed_10m,relative_humidity_2m",
                "daily": "temperature_2m_max,temperature_2m_min,weather_code",
                "forecast_days": 3,
                "timezone": "auto",
            },
        )

    current = forecast.get("current") or {}
    code = current.get("weather_code")
    daily = forecast.get("daily") or {}
    days = []
    times = daily.get("time") or []
    for index, day in enumerate(times):
        days.append(
            {
                "date": day,
                "max_c": (daily.get("temperature_2m_max") or [None] * (index + 1))[index],
                "min_c": (daily.get("temperature_2m_min") or [None] * (index + 1))[index],
                "sky": WEATHER_CODES.get(
                    (daily.get("weather_code") or [0] * (index + 1))[index], "unknown"
                ),
            }
        )

    return ToolResult(
        ok=True,
        data={
            "found": True,
            "city": place.get("name", city),
            "country": place.get("country", ""),
            "timezone": place.get("timezone", ""),
            "now": {
                "temperature_c": current.get("temperature_2m"),
                "feels_like_c": current.get("apparent_temperature"),
                "sky": WEATHER_CODES.get(code, "unknown"),
                "wind_kmh": current.get("wind_speed_10m"),
                "humidity_percent": current.get("relative_humidity_2m"),
            },
            "forecast": days,
        },
        source="open-meteo",
    )


async def get_datetime(timezone: str = "UTC") -> ToolResult:
    """The current date and time.

    The model has no idea what day it is, so this is how it can answer
    "what's today's date" or reason about "yesterday".
    """
    zone = (timezone or "UTC").strip()
    if not zone:
        zone = "UTC"

    now = datetime.now(dt_timezone.utc)
    offset_hours = 0
    label = "UTC"
    if zone.upper() != "UTC":
        try:
            from zoneinfo import ZoneInfo

            local = now.astimezone(ZoneInfo(zone))
            offset = local.utcoffset()
            offset_hours = offset.total_seconds() / 3600 if offset else 0
            label = zone
            now = local
        except Exception:
            # Unknown timezone: fall back to UTC rather than failing.
            now = datetime.now(dt_timezone.utc)
            label = "UTC"

    return ToolResult(
        ok=True,
        data={
            "date": now.strftime("%Y-%m-%d"),
            "time": now.strftime("%H:%M:%S"),
            "iso": now.isoformat(),
            "timezone": label,
            "utc_offset_hours": offset_hours,
            "weekday": now.strftime("%A"),
        },
        source="system clock",
    )


__all__ = [
    "LOOKUP_TIMEOUT",
    "USER_AGENT",
    "WEATHER_CODES",
    "WIKIPEDIA_LANGUAGES",
    "get_datetime",
    "get_weather",
    "search_web",
    "search_wikipedia",
]
