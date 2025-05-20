import httpx
import asyncio
import time
from typing import Literal, List, Tuple, Dict, Any, Optional
from pydantic_settings import BaseSettings
from pydantic import BaseModel, Field, HttpUrl, validator
from datetime import date, datetime

from models import FilmBase, MetaData


class TMDBSettings(BaseSettings):
    tmdb_api_key: str = Field(..., env="TMDB_API_KEY")
    tmdb_base_url: HttpUrl = Field("https://api.themoviedb.org/3", env="TMDB_BASE_URL")

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = TMDBSettings()

# Basic rate limiting state
RATE_LIMIT_REMAINING = 30  # Default based on TMDB docs, will be updated by headers
RATE_LIMIT_RESET_TIME = 0


async def _handle_rate_limit(response: httpx.Response):
    global RATE_LIMIT_REMAINING, RATE_LIMIT_RESET_TIME
    if "x-ratelimit-remaining" in response.headers:
        RATE_LIMIT_REMAINING = int(response.headers["x-ratelimit-remaining"])
    if "x-ratelimit-reset" in response.headers:
        RATE_LIMIT_RESET_TIME = int(response.headers["x-ratelimit-reset"])

    if RATE_LIMIT_REMAINING <= 1:  # Leave a small buffer
        wait_time = max(0, RATE_LIMIT_RESET_TIME - time.time())
        if wait_time > 0:
            print(f"Rate limit approaching. Waiting for {wait_time:.2f} seconds.")
            await asyncio.sleep(wait_time)


async def _make_request(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    params: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    params = params or {}
    params["api_key"] = settings.tmdb_api_key

    await _handle_rate_limit(httpx.Response(200))  # Check before making a request

    response = await client.request(method, url, params=params)

    await _handle_rate_limit(response)  # Update after making a request

    if response.status_code != 200:
        response.raise_for_status()  # Raises HTTPStatusError for 4xx/5xx
    return response.json()


def _parse_release_date(release_date_str: Optional[str]) -> Optional[date]:
    if not release_date_str:
        return None
    try:
        return datetime.strptime(release_date_str, "%Y-%m-%d").date()
    except ValueError:
        return None  # Or handle error as appropriate


def _map_tmdb_to_filmbase(
    item: Dict[str, Any], media_type: Literal["movie", "tv"]
) -> FilmBase:
    title_key = "title" if media_type == "movie" else "name"
    release_date_key = "release_date" if media_type == "movie" else "first_air_date"
    return FilmBase(
        film_id=item["id"],
        title=item.get(title_key, "N/A"),
        release_date=_parse_release_date(item.get(release_date_key)),
        type="movie" if media_type == "movie" else "series",
        status="PlanToWatch",  # Default status
    )


async def search(title: str, media_type: Literal["movie", "tv"]) -> List[FilmBase]:
    async with httpx.AsyncClient(base_url=str(settings.tmdb_base_url)) as client:
        endpoint = f"/search/{media_type}"
        data = await _make_request(client, "GET", endpoint, params={"query": title})
        return [
            _map_tmdb_to_filmbase(item, media_type) for item in data.get("results", [])
        ]


async def get_details(
    media_type: Literal["movie", "tv"], tmdb_id: int
) -> Tuple[FilmBase, MetaData, List[str]]:
    async with httpx.AsyncClient(base_url=str(settings.tmdb_base_url)) as client:
        endpoint = f"/{media_type}/{tmdb_id}"
        details_data = await _make_request(
            client,
            "GET",
            endpoint,
            params={"append_to_response": "credits,external_ids"},
        )

        film_base = _map_tmdb_to_filmbase(details_data, media_type)

        imdb_id = details_data.get("external_ids", {}).get("imdb_id")
        runtime = (
            details_data.get("runtime")
            if media_type == "movie"
            else (
                details_data.get("episode_run_time", [None])[0]
                if details_data.get("episode_run_time")
                else None
            )
        )

        meta_data = MetaData(
            imdb_id=imdb_id,
            runtime=runtime,
            plot=details_data.get("overview"),
            rating=details_data.get("vote_average"),
            poster_url=(
                f"https://image.tmdb.org/t/p/w500{details_data.get('poster_path')}"
                if details_data.get("poster_path")
                else None
            ),
        )

        genres = [genre["name"] for genre in details_data.get("genres", [])]

        return film_base, meta_data, genres


async def get_trending(
    media_type: Literal["movie", "tv"], time_window: Literal["day", "week"]
) -> List[FilmBase]:
    async with httpx.AsyncClient(base_url=str(settings.tmdb_base_url)) as client:
        endpoint = f"/trending/{media_type}/{time_window}"
        data = await _make_request(client, "GET", endpoint)
        return [
            _map_tmdb_to_filmbase(item, media_type) for item in data.get("results", [])
        ]


async def discover(
    media_type: Literal["movie", "tv"], filters: Dict[str, Any]
) -> List[FilmBase]:
    async with httpx.AsyncClient(base_url=str(settings.tmdb_base_url)) as client:
        endpoint = f"/discover/{media_type}"
        # TMDB uses comma-separated strings for some filters like 'with_genres'
        processed_filters = {}
        for key, value in filters.items():
            if isinstance(value, list):
                processed_filters[key] = ",".join(map(str, value))
            else:
                processed_filters[key] = value

        data = await _make_request(client, "GET", endpoint, params=processed_filters)
        return [
            _map_tmdb_to_filmbase(item, media_type) for item in data.get("results", [])
        ]
