from typing import Dict, List, Literal, Optional
from datetime import date
from pydantic import BaseModel


class FilmBase(BaseModel):
    film_id: int
    title: str
    release_date: Optional[date] = None
    type: Literal["movie", "series"]
    status: Literal["PlanToWatch", "Watching", "Watched", "Dropped", "OnHold"]
    watched_date: Optional[date] = None


class FilmBaseResponse(FilmBase):
    overview: str = ""
    genres_ids: Optional[List[int]] = None
    popularity: Optional[float] = None


class MetaData(BaseModel):
    imdb_id: Optional[str] = None
    runtime: Optional[int] = None
    plot: Optional[str] = None
    rating: Optional[float] = None
    poster_url: Optional[str] = None


class Genre(BaseModel):
    id: int
    name: str
