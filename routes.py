from fastapi import APIRouter, Depends, HTTPException, Request, status as http_status
import sqlite3
from typing import List, Literal, Optional, Dict, Any, Tuple
from datetime import date

from pydantic import BaseModel

import tmdb_client
from db import get_db
from models import (
    FilmBase,
    MetaData,
)  # Genre model is also in models.py but not directly used as input/output here for lists
import httpx

router = APIRouter()

# Pydantic models for API request/response structures


class FilmDetailsResponse(FilmBase):
    meta_data: MetaData
    genres: List[str]


class WatchlistUpdate(BaseModel):
    status: Optional[
        Literal["PlanToWatch", "Watching", "Watched", "Dropped", "OnHold"]
    ] = None
    watched_date: Optional[date] = None


class WatchlistItem(FilmBase):
    # Inherits film_id, title, release_date, type, status, watched_date
    imdb_id: Optional[str] = None
    runtime: Optional[int] = None
    plot: Optional[str] = None
    rating: Optional[float] = None
    poster_url: Optional[str] = None
    genres: Optional[List[str]] = None


# TMDB Passthrough Endpoints


@router.get("/search", response_model=List[FilmBase])
async def search_tmdb(query: str, type: Literal["movie", "tv"]):
    try:
        return await tmdb_client.search(title=query, media_type=type)
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=str(e))


@router.get("/details/{type}/{id}", response_model=FilmDetailsResponse)
async def get_tmdb_details(type: Literal["movie", "tv"], id: int):
    try:
        film_base, meta_data, genres_list = await tmdb_client.get_details(
            media_type=type, tmdb_id=id
        )
        return FilmDetailsResponse(
            **film_base.model_dump(), meta_data=meta_data, genres=genres_list
        )
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=str(e))


@router.get("/trending/{type}/{window}", response_model=List[FilmBase])
async def get_tmdb_trending(
    type: Literal["movie", "tv"], window: Literal["day", "week"]
):
    try:
        return await tmdb_client.get_trending(media_type=type, time_window=window)
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=str(e))


@router.get("/discover/{type}", response_model=List[FilmBase])
async def discover_tmdb(type: Literal["movie", "tv"], request: Request):
    # Convert query params from Request object to a dictionary for the client
    filters: Dict[str, Any] = dict(request.query_params)
    try:
        return await tmdb_client.discover(media_type=type, filters=filters)
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=str(e))


# Watchlist CRUD Endpoints


@router.get("/watchlist", response_model=List[WatchlistItem])
def get_watchlist(db: sqlite3.Connection = Depends(get_db)):
    cursor = db.cursor()
    cursor.execute(
        """
        SELECT
            f.film_id, f.title, f.release_date, f.type, f.status, f.watched_date,
            m.imdb_id, m.runtime, m.plot, m.rating, m.poster_url,
            (SELECT GROUP_CONCAT(g.name) FROM Genre g WHERE g.film_id = f.film_id) as genre_names
        FROM Film f
        LEFT JOIN Meta m ON f.film_id = m.film_id
    """
    )
    items = []
    for row in cursor.fetchall():
        row_dict = dict(row)
        genre_names_str = row_dict.pop("genre_names", None)
        genres_list = genre_names_str.split(",") if genre_names_str else None

        # Ensure release_date and watched_date are parsed correctly if they are strings
        if isinstance(row_dict.get("release_date"), str):
            row_dict["release_date"] = date.fromisoformat(row_dict["release_date"])
        if isinstance(row_dict.get("watched_date"), str):
            row_dict["watched_date"] = date.fromisoformat(row_dict["watched_date"])

        items.append(WatchlistItem(**row_dict, genres=genres_list))
    return items


@router.post(
    "/watchlist", response_model=FilmBase, status_code=http_status.HTTP_201_CREATED
)
def add_to_watchlist(film: FilmBase, db: sqlite3.Connection = Depends(get_db)):
    cursor = db.cursor()
    try:
        cursor.execute(
            "INSERT INTO Film (film_id, title, release_date, type, status, watched_date) VALUES (?, ?, ?, ?, ?, ?)",
            (
                film.film_id,
                film.title,
                film.release_date,
                film.type,
                film.status,
                film.watched_date,
            ),
        )
        # Insert an empty/minimal Meta row
        cursor.execute("INSERT INTO Meta (film_id) VALUES (?)", (film.film_id,))
        # No genres are added by default with this POST, as per "empty Meta/Genre rows"
        db.commit()
    except sqlite3.IntegrityError:  # film_id likely already exists
        db.rollback()
        raise HTTPException(
            status_code=http_status.HTTP_409_CONFLICT,
            detail=f"Film with ID {film.film_id} already in watchlist",
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}",
        )
    return film


@router.patch("/watchlist/{film_id}", response_model=WatchlistItem)
def update_watchlist_item(
    film_id: int, update_data: WatchlistUpdate, db: sqlite3.Connection = Depends(get_db)
):
    cursor = db.cursor()

    # Check if film exists
    cursor.execute("SELECT film_id FROM Film WHERE film_id = ?", (film_id,))
    if not cursor.fetchone():
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"Film with ID {film_id} not found in watchlist",
        )

    fields_to_update = update_data.model_dump(exclude_unset=True)
    if not fields_to_update:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST, detail="No fields to update"
        )

    set_clause = ", ".join([f"{key} = ?" for key in fields_to_update.keys()])
    values = list(fields_to_update.values())
    values.append(film_id)

    try:
        cursor.execute(f"UPDATE Film SET {set_clause} WHERE film_id = ?", tuple(values))
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}",
        )

    # Fetch and return the updated item
    cursor.execute(
        """
        SELECT
            f.film_id, f.title, f.release_date, f.type, f.status, f.watched_date,
            m.imdb_id, m.runtime, m.plot, m.rating, m.poster_url,
            (SELECT GROUP_CONCAT(g.name) FROM Genre g WHERE g.film_id = f.film_id) as genre_names
        FROM Film f
        LEFT JOIN Meta m ON f.film_id = m.film_id
        WHERE f.film_id = ?
    """,
        (film_id,),
    )

    updated_row = cursor.fetchone()
    if (
        not updated_row
    ):  # Should not happen if update was successful and initial check passed
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Updated film not found, this should not happen.",
        )

    row_dict = dict(updated_row)
    genre_names_str = row_dict.pop("genre_names", None)
    genres_list = genre_names_str.split(",") if genre_names_str else None

    if isinstance(row_dict.get("release_date"), str):
        row_dict["release_date"] = date.fromisoformat(row_dict["release_date"])
    if isinstance(row_dict.get("watched_date"), str):
        row_dict["watched_date"] = date.fromisoformat(row_dict["watched_date"])

    return WatchlistItem(**row_dict, genres=genres_list)


@router.delete("/watchlist/{film_id}", status_code=http_status.HTTP_204_NO_CONTENT)
def delete_watchlist_item(film_id: int, db: sqlite3.Connection = Depends(get_db)):
    cursor = db.cursor()

    # Check if film exists before attempting to delete
    cursor.execute("SELECT film_id FROM Film WHERE film_id = ?", (film_id,))
    if not cursor.fetchone():
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"Film with ID {film_id} not found in watchlist",
        )

    try:
        # Delete from child tables first if no ON DELETE CASCADE is set up
        cursor.execute("DELETE FROM Genre WHERE film_id = ?", (film_id,))
        cursor.execute("DELETE FROM Meta WHERE film_id = ?", (film_id,))
        cursor.execute("DELETE FROM Film WHERE film_id = ?", (film_id,))

        if (
            cursor.rowcount == 0
        ):  # Should be caught by the check above, but as a safeguard
            db.rollback()  # Rollback if Film delete affected 0 rows unexpectedly
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"Film with ID {film_id} not found in watchlist for deletion.",
            )
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}",
        )

    return  # FastAPI handles 204 No Content response automatically
