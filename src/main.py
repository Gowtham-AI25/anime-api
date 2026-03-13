import os
from fastapi import FastAPI, HTTPException
from supabase import create_client, Client
from dotenv import load_dotenv
import re
from fastapi import Query, Path
from fastapi.middleware.cors import CORSMiddleware  # 1. Import the middleware


# Load variables
load_dotenv()

app = FastAPI()

# 2. Define who is allowed to talk to your API
origins = [
    "http://127.0.0.1:5500",  # Your local Live Server
    "http://localhost:5500",   # Sometimes browsers use 'localhost' instead
    "https://your-app-name.onrender.com", # Add your Render URL here for later
]

# 3. Add the middleware to your app
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],  # Allows GET, POST, etc.
    allow_headers=["*"],  # Allows all headers
)

# ... your existing routes below ...

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
async def debug_supabase():
    try:
        # Test 1: Does table exist + row count?
        count_response = supabase.table("anime_metadata").select("count", count="exact").execute()
        
        # Test 2: Get first 3 rows
        sample_data = supabase.table("anime_metadata").select("*").limit(3).execute()
        
        # Test 3: Your exact search logic
        search_test = supabase.table("anime_metadata").ilike("title", "%naruto%").limit(1).execute()
        
        # Test 4: Check your other table
        az_count = supabase.table("anime_by_letter").select("count", count="exact").execute()
        
        return {
            "anime_metadata_table": {
                "total_rows": count_response.count,
                "sample_data": sample_data.data[:1]  # First row only
            },
            "anime_by_letter_table": {
                "total_rows": az_count.count
            },
            "search_test_naruto": search_test.data,
            "connection": "✅ WORKING",
            "service_role_key": "✅ SET" if key else "❌ MISSING"
        }
    except Exception as e:
        return {
            "error": str(e),
            "error_type": str(type(e).__name__)
        }

@app.get("/anime/home/trending")
async def get_trending_anime(
    page: int = Query(1, ge=1, description="The page number to fetch"),
    page_size: int = Query(30, ge=1, le=50, description="Items per page")
):
    """
    Fetches the highest-rated anime (trending) based on score.
    """
    try:
        # Calculate pagination range
        start = (page - 1) * page_size
        end = (page * page_size) - 1

        # Query Supabase: Sort by 'score' descending
        # We also filter where score is not null to ensure quality results
        response = (
            supabase.table("anime_metadata")
            .select("*")
            .not_.is_("score", "null")
            .order("score", desc=True)
            .range(start, end)
            .execute()
        )

        return {
            "page": page,
            "page_size": page_size,
            "results": response.data
        }

    except Exception as e:
        print(f"Error fetching trending anime: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch trending anime")
    

@app.get("/anime/home/home_content")
async def get_home_layout():
    """
    Aggregator endpoint for the Home Page.
    Returns 8 'Fresh' (Recent 2025) and 4 'Trending' (Top Rated) anime.
    """
    try:
        # 1. Fetch Fresh
        fresh_res = (
            supabase.table("anime_metadata")
            .select("*, anime_genres(genre)")
            .eq("year", 2025)
            .limit(8)
            .execute()
        )

        # 2. Fetch Trending
        trending_res = (
            supabase.table("anime_metadata")
            .select("*, anime_genres(genre)")
            .not_.is_("score", "null")
            .order("score", desc=True)
            .limit(4)
            .execute()
        )

        # Transformation Function
        def transform_anime(anime_list):
            for anime in anime_list:
                # Extract just the string from the list of objects
                if "anime_genres" in anime:
                    anime["genres"] = [g["genre"] for g in anime["anime_genres"]]
                    # Clean up the old nested key
                    del anime["anime_genres"]
            return anime_list

        return {
            "fresh": transform_anime(fresh_res.data),
            "trending": transform_anime(trending_res.data)
        }
    except Exception as e:
        print(f"Home Aggregator Error: {e}")
        raise HTTPException(status_code=500, detail="Failed to load home screen data")