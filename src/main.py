import os
from fastapi import FastAPI, HTTPException
from supabase import create_client, Client
from dotenv import load_dotenv
import re
from fastapi import Query, Path

# Load variables
load_dotenv()

app = FastAPI(title="Anime Metadata API")

# 1. Get your Supabase credentials
# Note: Use the ANON_KEY or SERVICE_ROLE_KEY from your dashboard
url: str = os.getenv("SUPABASE_URL")
key: str = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

# 2. Initialize the Supabase Client
if not url or not key:
    raise ValueError("Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY in .env")

supabase: Client = create_client(url, key)

# 1. SEARCH ROUTE (Higher Priority)
@app.get("/anime/search")
async def search_anime(title: str, limit: int = 10):
    try:
        response = (
            supabase.table("anime_metadata")
            .select("*")
            .ilike("title", f"%{title}%") 
            .limit(limit)
            .execute()
        )
        return response.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/anime/{anime_id}")
async def get_anime_metadata(anime_id: int):
    """
    Fetches anime metadata using the Supabase Client (HTTPS).
    """
    try:
        # 3. Use the Supabase query syntax
        response = (
            supabase.table("anime_metadata")
            .select("*")
            .eq("anime_id", anime_id)
            .single()
            .execute()
        )

        return response.data

    except Exception as e:
        # Check if it's a "Not Found" error from PostgREST
        if "PGRST116" in str(e):
            raise HTTPException(status_code=404, detail="Anime not found")
            
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    

@app.get("/anime/home/recent")
async def get_recent_anime(
    page: int = Query(1, ge=1, description="The page number to fetch"),
    page_size: int = Query(30, ge=1, le=50, description="Items per page")
):
    """
    Fetches ongoing anime with pagination.
    Example: /anime/home/recent?page=1&page_size=8
    """
    try:

        start = (page - 1) * page_size
        end = (page * page_size) - 1

        response = (
            supabase.table("anime_metadata")
            .select("*")
            .eq("year", 2025)
            .eq("status", "Currently Airing")
            .gt("episodes", 2)
            .order("episodes", desc=False)
            .range(start, end) # Use range instead of limit for pagination
            .execute()
        )

        return {
            "page": page,
            "page_size": page_size,
            "results": response.data
        }

    except Exception as e:
        print(f"Error fetching recent anime: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/anime/azlist/{letter}")
async def get_anime_by_letter(
    letter: str = Path(..., description="A single letter from A-Z"),
    page: int = Query(1, ge=1),
    page_size: int = 30
):
    """
    Returns 30 anime starting with the specified letter.
    Strictly validates that the input is a single letter (a-z or A-Z).
    """
    # 1. Validation Logic
    # ^[a-zA-Z]$ means: Start of string, one letter (any case), end of string.
    if not re.match(r"^[a-zA-Z]$", letter):
        raise HTTPException(
            status_code=400, 
            detail="Invalid input. Please provide a single letter between A and Z."
        )

    try:
        search_letter = letter.upper()

        start = (page - 1) * page_size
        end = (page * page_size) - 1

        response = (
            supabase.table("anime_by_letter")
            .select("*")
            .eq("first_letter", search_letter)
            .order("title", desc=False)
            .range(start, end)
            .execute()
        )

        return {
            "letter": search_letter,
            "page": page,
            "results": response.data
        }

    except Exception as e:
        print(f"Directory Error: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
    
@app.get("/anime/debug/test")
async def debug():
    try:
        count = supabase.table("anime_metadata").select("count", count="exact").execute()
        data = supabase.table("anime_metadata").select("*").limit(2).execute()
        return {"count": count.count, "sample": data.data}
    except Exception as e:
        return {"error": str(e)}
