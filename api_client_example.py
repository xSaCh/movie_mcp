import httpx
import asyncio
from typing import Literal, Optional, Dict, Any, List
from datetime import date

# Base URL for the locally running FastAPI application
BASE_URL = "http://localhost:8000/api"

# --- Pydantic-like models for expected response structures (optional but good for clarity) ---
# These would ideally be shared or derived from your main application's models.py
# For this example, we'll define simplified versions or expect dicts.


async def call_search_tmdb(
    query: str, media_type: Literal["movie", "tv"]
) -> List[Dict[str, Any]]:
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/search", params={"query": query, "type": media_type}
        )
        response.raise_for_status()  # Raise an exception for bad status codes
        return response.json()


async def call_get_tmdb_details(
    media_type: Literal["movie", "tv"], tmdb_id: int
) -> Dict[str, Any]:
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/details/{media_type}/{tmdb_id}")
        response.raise_for_status()
        return response.json()


async def call_get_tmdb_trending(
    media_type: Literal["movie", "tv"], window: Literal["day", "week"]
) -> List[Dict[str, Any]]:
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/trending/{media_type}/{window}")
        response.raise_for_status()
        return response.json()


async def call_discover_tmdb(
    media_type: Literal["movie", "tv"], filters: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    async with httpx.AsyncClient() as client:
        params = filters or {}
        response = await client.get(f"{BASE_URL}/discover/{media_type}", params=params)
        response.raise_for_status()
        return response.json()


async def call_get_watchlist() -> List[Dict[str, Any]]:
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/watchlist")
        response.raise_for_status()
        return response.json()


async def call_add_to_watchlist(film_data: Dict[str, Any]) -> Dict[str, Any]:
    async with httpx.AsyncClient() as client:
        response = await client.post(f"{BASE_URL}/watchlist", json=film_data)
        response.raise_for_status()
        return response.json()


async def call_update_watchlist_item(
    film_id: int, update_data: Dict[str, Any]
) -> Dict[str, Any]:
    async with httpx.AsyncClient() as client:
        response = await client.patch(
            f"{BASE_URL}/watchlist/{film_id}", json=update_data
        )
        response.raise_for_status()
        return response.json()


async def call_delete_watchlist_item(film_id: int) -> None:
    async with httpx.AsyncClient() as client:
        response = await client.delete(f"{BASE_URL}/watchlist/{film_id}")
        response.raise_for_status()
        print(f"Deletion of film {film_id} successful (status: {response.status_code})")


async def main():
    print("--- Testing TMDB Search ---")
    try:
        search_results = await call_search_tmdb(query="Inception", media_type="movie")
        print(
            f"Search for 'Inception (movie)': {search_results[:2]}...\n"
        )  # Print first 2 results
        if search_results:
            inception_id = search_results[0]["film_id"]
            inception_type = search_results[0]["type"]

            print(f"--- Testing TMDB Details for ID: {inception_id} ---")
            details = await call_get_tmdb_details(
                media_type=inception_type, tmdb_id=inception_id
            )
            print(f"Details for '{details.get('title')}': {details}\n")

            print("--- Testing Add to Watchlist ---")
            # Construct a FilmBase like object. Ensure release_date is in YYYY-MM-DD
            # and status is one of the allowed literals.
            film_to_add = {
                "film_id": details["film_id"],
                "title": details["title"],
                "release_date": details["release_date"],
                "type": details["type"],
                "status": "PlanToWatch",
                # "watched_date": None # Optional
            }
            added_film = await call_add_to_watchlist(film_to_add)
            print(f"Added to watchlist: {added_film}\n")

            print("--- Testing Get Watchlist (after add) ---")
            watchlist = await call_get_watchlist()
            print(f"Current Watchlist: {watchlist}\n")

            print(f"--- Testing Update Watchlist Item ID: {inception_id} ---")
            update_payload = {
                "status": "Watched",
                "watched_date": date.today().isoformat(),
            }
            updated_item = await call_update_watchlist_item(
                film_id=inception_id, update_data=update_payload
            )
            print(f"Updated item: {updated_item}\n")

            print("--- Testing Get Watchlist (after update) ---")
            watchlist_after_update = await call_get_watchlist()
            print(f"Current Watchlist: {watchlist_after_update}\n")

            print(f"--- Testing Delete Watchlist Item ID: {inception_id} ---")
            await call_delete_watchlist_item(film_id=inception_id)
            print(f"Attempted deletion of film ID {inception_id}.\n")

            print("--- Testing Get Watchlist (after delete) ---")
            watchlist_after_delete = await call_get_watchlist()
            print(f"Current Watchlist: {watchlist_after_delete}\n")

    except httpx.HTTPStatusError as e:
        print(f"HTTP Error: {e.response.status_code} - {e.response.text}")
    except Exception as e:
        print(f"An error occurred: {e}")

    print("--- Testing TMDB Trending (Movies, Day) ---")
    try:
        trending_movies = await call_get_tmdb_trending(media_type="movie", window="day")
        print(f"Trending movies (day): {trending_movies[:2]}...\n")
    except httpx.HTTPStatusError as e:
        print(f"HTTP Error: {e.response.status_code} - {e.response.text}")
    except Exception as e:
        print(f"An error occurred: {e}")

    print("--- Testing TMDB Discover (Movies, with_genres=28 Action) ---")
    try:
        discover_filters = {"with_genres": "28", "sort_by": "popularity.desc"}
        discovered_movies = await call_discover_tmdb(
            media_type="movie", filters=discover_filters
        )
        print(f"Discovered action movies: {discovered_movies[:2]}...\n")
    except httpx.HTTPStatusError as e:
        print(f"HTTP Error: {e.response.status_code} - {e.response.text}")
    except Exception as e:
        print(f"An error occurred: {e}")


if __name__ == "__main__":
    # Before running, ensure your FastAPI server is running (e.g., uvicorn main:app --reload)
    # and you have set your TMDB_API_KEY environment variable.
    asyncio.run(main())
