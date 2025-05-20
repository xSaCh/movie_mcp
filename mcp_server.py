import httpx
import asyncio
from typing import Literal, Optional, Dict, Any, List
from datetime import date

from mcp.server.fastmcp import FastMCP

# from mcp.model.tool import ToolContext # Uncomment if you need ToolContext for advanced scenarios

# Initialize MCP Server
mcp = FastMCP(
    name="TMDB and Watchlist MCP Server",
    description="Provides tools to interact with TMDB and a local watchlist.",
    tools_module=__name__,  # Automatically discover tools in this module
)

# Base URL for the locally running FastAPI application
FASTAPI_BASE_URL = (
    "http://localhost:8000/api"  # Ensure this matches your FastAPI app's URL
)


# --- Helper for making HTTP requests ---
async def _call_api(
    method: str,
    endpoint: str,
    params: Optional[Dict[str, Any]] = None,
    json_data: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    async with httpx.AsyncClient() as client:
        try:
            url = f"{FASTAPI_BASE_URL}{endpoint}"
            print(f"Making req to {method}, {url}, {params} {json_data}")
            response = await client.request(method, url, params=params, json=json_data)
            response.raise_for_status()  # Raises HTTPStatusError for 4xx/5xx responses
            if response.status_code == 204:  # Handle No Content responses
                return {
                    "status": "success",
                    "message": f"Operation {method} on {endpoint} successful with no content returned.",
                }
            return response.json()
        except httpx.HTTPStatusError as e:
            # Attempt to parse error response from FastAPI if available
            error_detail = e.response.text
            try:
                error_json = e.response.json()
                if isinstance(error_json, dict) and "detail" in error_json:
                    error_detail = error_json["detail"]
            except Exception:
                pass  # Keep original text if JSON parsing fails or no 'detail' field
            return {
                "error": True,
                "status_code": e.response.status_code,
                "detail": error_detail,
            }
        except httpx.RequestError as e:
            return {
                "error": True,
                "status_code": "N/A",
                "detail": f"Request to {e.request.url} failed: {str(e)}",
            }
        except Exception as e:
            return {
                "error": True,
                "status_code": "N/A",
                "detail": f"An unexpected error occurred: {str(e)}",
            }


# --- TMDB Interaction Tools ---


@mcp.tool(name="search_tmdb", description="Search TMDB for movies or TV series.")
async def search_tmdb_tool(query: str, type: Literal["movie", "tv"]) -> Dict[str, Any]:
    """
    Searches TMDB for movies or TV series based on a query.
    Args:
        query: The search query (e.g., movie or series title).
        type: The type of media to search for ('movie' or 'tv').
    Returns:
        A dictionary containing the search results or an error.
    """
    return await _call_api("GET", "/search", params={"query": query, "type": type})


@mcp.tool(
    name="get_tmdb_details",
    description="Get detailed information for a specific movie or TV series from TMDB.",
)
async def get_tmdb_details_tool(
    type: Literal["movie", "tv"], id: int
) -> Dict[str, Any]:
    """
    Fetches detailed information for a given TMDB ID.
    Args:
        type: The type of media ('movie' or 'tv').
        id: The TMDB ID of the movie or series.
    Returns:
        A dictionary containing the detailed media information or an error.
    """
    return await _call_api("GET", f"/details/{type}/{id}")


@mcp.tool(
    name="get_tmdb_trending", description="Get trending movies or TV series from TMDB."
)
async def get_tmdb_trending_tool(
    type: Literal["movie", "tv"], window: Literal["day", "week"]
) -> Dict[str, Any]:
    """
    Fetches trending media from TMDB for a given time window.
    Args:
        type: The type of media ('movie' or 'tv').
        window: The time window for trending items ('day' or 'week').
    Returns:
        A dictionary containing the list of trending media or an error.
    """
    return await _call_api("GET", f"/trending/{type}/{window}")


@mcp.tool(
    name="discover_tmdb_media",
    description="Discover movies or TV series from TMDB based on filters.",
)
async def discover_tmdb_media_tool(
    type: Literal["movie", "tv"], filters: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Discovers media from TMDB based on various filter criteria.
    Args:
        type: The type of media to discover ('movie' or 'tv').
        filters: A dictionary of filter parameters (e.g., {"with_genres": "28", "sort_by": "popularity.desc"}).
    Returns:
        A dictionary containing the list of discovered media or an error.
    """
    return await _call_api("GET", f"/discover/{type}", params=filters)


@mcp.tool(
    name="get_tmdb_genres",
    description="Get the list of official genres for movies or TV series from TMDB.",
)
async def get_tmdb_genres_tool(type: Literal["movie", "tv"]) -> List[Dict[str, Any]]:
    """
    Fetches the list of official genres for a given media type from TMDB.
    Args:
        type: The type of media for which to fetch genres ('movie' or 'tv').
    Returns:
        A list of genres or an error.
    """
    return await _call_api("GET", f"/genres/{type}")


# --- Local Watchlist Interaction Tools ---


@mcp.tool(
    name="get_my_watchlist", description="Retrieve all items from the local watchlist."
)
async def get_my_watchlist_tool() -> Dict[str, Any]:
    """
    Retrieves all films stored in the local watchlist.
    Returns:
        A dictionary containing the list of watchlist items or an error.
    """
    return await _call_api("GET", "/watchlist")


@mcp.tool(
    name="add_to_my_watchlist",
    description="Add a film to the local watchlist by providing only the film_id.",
)
async def add_to_my_watchlist_tool(
    film_id: int, type: Literal["movie", "tv"]
) -> Dict[str, Any]:
    """
    Adds a new film to the local watchlist using the film_id.
    Args:
        film_id: The TMDB ID of the film.
        type: The type of media to search for ('movie' or 'tv').
    Returns:
        A dictionary containing the added film information or an error.
    """
    return await _call_api(
        "POST", "/watchlist", params={"film_id": film_id, "type": type}
    )


@mcp.tool(
    name="update_my_watchlist_item",
    description="Update an item in the local watchlist.",
)
async def update_my_watchlist_item_tool(
    film_id: int,
    status: Optional[
        Literal["PlanToWatch", "Watching", "Watched", "Dropped", "OnHold"]
    ] = None,
    watched_date_str: Optional[
        str
    ] = None,  # Expecting YYYY-MM-DD string, or empty string/None to clear
) -> Dict[str, Any]:
    """
    Updates the status and/or watched date of a film in the local watchlist.
    Args:
        film_id: The ID of the film to update.
        status: The new viewing status (optional).
        watched_date_str: The new watched date (YYYY-MM-DD). Send None or empty string to clear. (optional).
    Returns:
        A dictionary containing the updated film information or an error.
    """
    update_data = {}
    if status:
        update_data["status"] = status

    if watched_date_str is not None:
        update_data["watched_date"] = watched_date_str

    if not update_data:
        return {
            "error": True,
            "status_code": 400,
            "detail": "No update data provided. Please provide status or watched_date.",
        }

    return await _call_api("PATCH", f"/watchlist/{film_id}", json_data=update_data)


@mcp.tool(
    name="delete_from_my_watchlist",
    description="Delete an item from the local watchlist.",
)
async def delete_from_my_watchlist_tool(film_id: int) -> Dict[str, Any]:
    """
    Deletes a film from the local watchlist by its ID.
    Args:
        film_id: The ID of the film to delete.
    Returns:
        A dictionary confirming the deletion or an error.
    """
    return await _call_api("DELETE", f"/watchlist/{film_id}")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(mcp.create_fastapi_app(), host="0.0.0.0", port=8001)
