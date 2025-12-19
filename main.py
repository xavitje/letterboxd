from fastapi import FastAPI, Request, Depends, HTTPException, status, Form, UploadFile, File, BackgroundTasks
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from datetime import timedelta
import requests
from requests import Response
import os
import csv
import io
from dotenv import load_dotenv

from models import User, MovieItem, UserMovie, Review, CustomList, get_db, init_db
from auth import (
    get_password_hash,
    authenticate_user,
    create_access_token,
    get_current_user_from_cookie,
    get_current_user_required,
    ACCESS_TOKEN_EXPIRE_MINUTES
)

load_dotenv()

# Initialize FastAPI app
app = FastAPI(title="MovieSpace")
templates = Jinja2Templates(directory="templates")

# TMDB API Configuration
TMDB_API_KEY = os.getenv("TMDB_API_KEY")
TMDB_BASE_URL = "https://api.themoviedb.org/3"
TMDB_IMAGE_BASE_URL = "https://image.tmdb.org/t/p/w500"

# Initialize database
init_db()


# Helper function to call TMDB API
def tmdb_request(endpoint: str, params: dict = None):
    """Helper functie voor TMDB API calls"""
    if params is None:
        params = {}
    params["api_key"] = TMDB_API_KEY

    try:
        response = requests.get(f"{TMDB_BASE_URL}{endpoint}", params=params)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"TMDB API Error: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"TMDB API Exception: {e}")
        return None


# Home Page - Popular & Now Playing
@app.get("/", response_class=HTMLResponse)
async def home(request: Request, db: Session = Depends(get_db)):
    """Home pagina met populaire en nu draaiende films"""
    user = get_current_user_from_cookie(request, db)

    popular_movies = tmdb_request("/movie/popular")
    now_playing_movies = tmdb_request("/movie/now_playing")

    return templates.TemplateResponse("index.html", {
        "request": request,
        "user": user,
        "popular_movies": popular_movies.get("results", []) if popular_movies else [],
        "now_playing_movies": now_playing_movies.get("results", []) if now_playing_movies else [],
        "image_base_url": TMDB_IMAGE_BASE_URL
    })

@app.get("/sitemap.xml")
async def sitemap(db: Session = Depends(get_db)):
    base_url = "https://movie.drissi.store"
    
    # 1. Statische pagina's
    static_pages = ["/", "/search", "/login", "/register"]
    
    # 2. Dynamische pagina's (alle films uit je database)
    movies = db.query(MovieItem).all()
    
    xml_content = '<?xml version="1.0" encoding="UTF-8"?>'
    xml_content += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
    
    # Statische URLs toevoegen
    for page in static_pages:
        xml_content += f"""
        <url>
            <loc>{base_url}{page}</loc>
            <changefreq>daily</changefreq>
            <priority>0.8</priority>
        </url>"""
    
    # Film detail pagina's toevoegen
    for movie in movies:
        xml_content += f"""
        <url>
            <loc>{base_url}/movie/{movie.tmdb_id}</loc>
            <changefreq>weekly</changefreq>
            <priority>0.6</priority>
        </url>"""
        
    xml_content += "</urlset>"
    
    return Response(content=xml_content, media_type="application/xml")
    
# Search & Filter Page
@app.get("/search", response_class=HTMLResponse)
async def search_page(
    request: Request,
    query: str = "",
    genre: str = "",
    year: str = "",
    language: str = "",
    sort_by: str = "popularity.desc",
    db: Session = Depends(get_db)
):
    """Zoek- en filterpagina"""
    user = get_current_user_from_cookie(request, db)

    # Get genres list
    genres_data = tmdb_request("/genre/movie/list")
    genres = genres_data.get("genres", []) if genres_data else []

    movies = []

    # Determine if we have any search criteria
    has_criteria = query or genre or year or language

    if query:
        # Text search - maar pas wel filters toe
        search_params = {"query": query}
        if year:
            search_params["year"] = year

        search_results = tmdb_request("/search/movie", search_params)
        all_movies = search_results.get(
            "results", []) if search_results else []

        # Handmatig filteren op genre en taal als die zijn ingesteld
        movies = all_movies
        if genre:
            movies = [m for m in movies if genre in [
                str(g) for g in m.get("genre_ids", [])]]
        if language:
            movies = [m for m in movies if m.get(
                "original_language") == language]

        # Sorteer indien nodig
        if sort_by == "popularity.desc":
            movies.sort(key=lambda x: x.get("popularity", 0), reverse=True)
        elif sort_by == "popularity.asc":
            movies.sort(key=lambda x: x.get("popularity", 0))
        elif sort_by == "vote_average.desc":
            movies.sort(key=lambda x: x.get("vote_average", 0), reverse=True)
        elif sort_by == "vote_average.asc":
            movies.sort(key=lambda x: x.get("vote_average", 0))
        elif sort_by == "release_date.desc":
            movies.sort(key=lambda x: x.get("release_date", ""), reverse=True)
        elif sort_by == "release_date.asc":
            movies.sort(key=lambda x: x.get("release_date", ""))
    else:
        # Discover with filters - altijd tonen zelfs zonder criteria
        params = {"sort_by": sort_by}
        if genre:
            params["with_genres"] = genre
        if year:
            params["primary_release_year"] = year
        if language:
            params["with_original_language"] = language

        discover_results = tmdb_request("/discover/movie", params)
        movies = discover_results.get(
            "results", []) if discover_results else []

    return templates.TemplateResponse("search.html", {
        "request": request,
        "user": user,
        "movies": movies,
        "genres": genres,
        "image_base_url": TMDB_IMAGE_BASE_URL,
        "query": query,
        "selected_genre": genre,
        "selected_year": year,
        "selected_language": language,
        "selected_sort": sort_by,
        "has_criteria": has_criteria
    })


# Movie Detail Page
@app.get("/movie/{movie_id}", response_class=HTMLResponse)
async def movie_detail(request: Request, movie_id: int, db: Session = Depends(get_db)):
    """Film detailpagina"""
    user = get_current_user_from_cookie(request, db)

    # Get movie details
    movie = tmdb_request(f"/movie/{movie_id}")
    if not movie:
        raise HTTPException(status_code=404, detail="Movie not found")

    # Get videos (trailers)
    videos = tmdb_request(f"/movie/{movie_id}/videos")
    trailer = None
    if videos and videos.get("results"):
        # Find YouTube trailer
        for video in videos["results"]:
            if video["type"] == "Trailer" and video["site"] == "YouTube":
                trailer = video["key"]
                break

    # Get local reviews
    reviews = db.query(Review).filter(Review.tmdb_id == movie_id).all()

    # Check user's list status and get custom lists
    user_status = None
    custom_lists = []
    if user:
        movie_item = db.query(MovieItem).filter(
            MovieItem.tmdb_id == movie_id).first()
        if movie_item:
            user_movie = db.query(UserMovie).filter(
                UserMovie.user_id == user.id,
                UserMovie.movie_id == movie_item.id
            ).first()
            if user_movie:
                user_status = user_movie.status

        # Get user's custom lists
        custom_lists = db.query(CustomList).filter(
            CustomList.user_id == user.id).all()

    return templates.TemplateResponse("movie_detail.html", {
        "request": request,
        "user": user,
        "movie": movie,
        "trailer": trailer,
        "reviews": reviews,
        "user_status": user_status,
        "custom_lists": custom_lists,
        "image_base_url": TMDB_IMAGE_BASE_URL
    })


# Add movie to list
@app.post("/movie/{movie_id}/add-to-list")
async def add_to_list(
    movie_id: int,
    status: str = Form(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_required)
):
    """Voeg film toe aan lijst"""
    # Get movie details from TMDB
    movie = tmdb_request(f"/movie/{movie_id}")
    if not movie:
        raise HTTPException(status_code=404, detail="Movie not found")

    # Find or create movie item
    movie_item = db.query(MovieItem).filter(
        MovieItem.tmdb_id == movie_id).first()
    if not movie_item:
        movie_item = MovieItem(
            tmdb_id=movie_id,
            title=movie["title"],
            poster_path=movie.get("poster_path")
        )
        db.add(movie_item)
        db.commit()
        db.refresh(movie_item)

    # Check if already in list
    user_movie = db.query(UserMovie).filter(
        UserMovie.user_id == user.id,
        UserMovie.movie_id == movie_item.id
    ).first()

    if user_movie:
        # Update status
        user_movie.status = status
    else:
        # Create new entry
        user_movie = UserMovie(
            user_id=user.id, movie_id=movie_item.id, status=status)
        db.add(user_movie)

    db.commit()
    return RedirectResponse(url=f"/movie/{movie_id}", status_code=303)


# Remove movie from list
@app.post("/movie/{movie_id}/remove-from-list")
async def remove_from_list(
    movie_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_required)
):
    """Verwijder film van lijst"""
    movie_item = db.query(MovieItem).filter(
        MovieItem.tmdb_id == movie_id).first()
    if movie_item:
        user_movie = db.query(UserMovie).filter(
            UserMovie.user_id == user.id,
            UserMovie.movie_id == movie_item.id
        ).first()
        if user_movie:
            db.delete(user_movie)
            db.commit()

    return RedirectResponse(url=f"/movie/{movie_id}", status_code=303)


# Add review
@app.post("/movie/{movie_id}/review")
async def add_review(
    movie_id: int,
    rating: float = Form(...),
    review_text: str = Form(""),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_required)
):
    """Voeg review toe"""
    # Check if user already reviewed this movie
    existing_review = db.query(Review).filter(
        Review.user_id == user.id,
        Review.tmdb_id == movie_id
    ).first()

    if existing_review:
        # Update existing review
        existing_review.rating = rating
        existing_review.review_text = review_text
    else:
        # Create new review
        review = Review(
            user_id=user.id,
            tmdb_id=movie_id,
            rating=rating,
            review_text=review_text
        )
        db.add(review)

    db.commit()
    return RedirectResponse(url=f"/movie/{movie_id}", status_code=303)


# Profile Page
@app.get("/profile", response_class=HTMLResponse)
async def profile(request: Request, db: Session = Depends(get_db)):
    """Profiel pagina"""
    user = get_current_user_required(request, db)

    # Get user's lists (limit to first 20 for performance)
    watchlist_items = db.query(UserMovie).filter(
        UserMovie.user_id == user.id,
        UserMovie.status == "watchlist"
    ).limit(20).all()

    watched_items = db.query(UserMovie).filter(
        UserMovie.user_id == user.id,
        UserMovie.status == "watched"
    ).limit(20).all()

    # Use cached data from MovieItem table
    watchlist = []
    for um in watchlist_items:
        watchlist.append({
            "id": um.movie.tmdb_id,
            "title": um.movie.title,
            "poster_path": um.movie.poster_path,
            "vote_average": 0  # Default value
        })

    watched = []
    for um in watched_items:
        watched.append({
            "id": um.movie.tmdb_id,
            "title": um.movie.title,
            "poster_path": um.movie.poster_path,
            "vote_average": 0  # Default value
        })

    # Get user's reviews (limit to 10 most recent)
    reviews = db.query(Review).filter(
        Review.user_id == user.id
    ).order_by(Review.created_at.desc()).limit(10).all()

    reviews_with_movies = []
    for review in reviews:
        # Find movie in database
        movie_item = db.query(MovieItem).filter(
            MovieItem.tmdb_id == review.tmdb_id
        ).first()

        if movie_item:
            reviews_with_movies.append({
                "movie": {
                    "id": movie_item.tmdb_id,
                    "title": movie_item.title,
                    "poster_path": movie_item.poster_path
                },
                "review": review
            })

    return templates.TemplateResponse("profile.html", {
        "request": request,
        "user": user,
        "watchlist": watchlist,
        "watched": watched,
        "reviews": reviews_with_movies,
        "image_base_url": TMDB_IMAGE_BASE_URL
    })


# Login Page
@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, db: Session = Depends(get_db)):
    """Login pagina"""
    user = get_current_user_from_cookie(request, db)
    if user:
        return RedirectResponse(url="/", status_code=303)

    return templates.TemplateResponse("login.html", {
        "request": request,
        "user": None
    })


# Login Handler
@app.post("/login")
async def login(
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    """Login handler"""
    user = authenticate_user(db, username, password)
    if not user:
        return templates.TemplateResponse("login.html", {
            "request": {},
            "user": None,
            "error": "Ongeldige gebruikersnaam of wachtwoord"
        }, status_code=400)

    # Create access token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )

    # Set cookie and redirect
    response = RedirectResponse(url="/", status_code=303)
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        samesite="lax"
    )
    return response


# Register Page
@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request, db: Session = Depends(get_db)):
    """Registratie pagina"""
    user = get_current_user_from_cookie(request, db)
    if user:
        return RedirectResponse(url="/", status_code=303)

    return templates.TemplateResponse("register.html", {
        "request": request,
        "user": None
    })


# Register Handler
@app.post("/register")
async def register(
    request: Request,
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    """Registratie handler"""
    # Check if username exists
    existing_user = db.query(User).filter(User.username == username).first()
    if existing_user:
        return templates.TemplateResponse("register.html", {
            "request": request,
            "user": None,
            "error": "Gebruikersnaam is al in gebruik"
        }, status_code=400)

    # Check if email exists
    existing_email = db.query(User).filter(User.email == email).first()
    if existing_email:
        return templates.TemplateResponse("register.html", {
            "request": request,
            "user": None,
            "error": "Email is al in gebruik"
        }, status_code=400)

    # Create new user
    hashed_password = get_password_hash(password)
    new_user = User(username=username, email=email,
                    hashed_password=hashed_password)
    db.add(new_user)
    db.commit()

    # Auto-login after registration
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": new_user.username}, expires_delta=access_token_expires
    )

    response = RedirectResponse(url="/", status_code=303)
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        samesite="lax"
    )
    return response


# Logout
@app.get("/logout")
async def logout():
    """Logout handler"""
    response = RedirectResponse(url="/", status_code=303)
    response.delete_cookie(key="access_token")
    return response


# Custom Lists Management
@app.get("/lists", response_class=HTMLResponse)
async def lists_page(request: Request, db: Session = Depends(get_db)):
    """Pagina met alle custom lists van de gebruiker"""
    user = get_current_user_required(request, db)

    # Get all custom lists
    custom_lists = db.query(CustomList).filter(
        CustomList.user_id == user.id).all()

    # Get movies for each list (optimized - only load preview + count)
    lists_with_movies = []
    for custom_list in custom_lists:
        # Count total movies
        total_count = db.query(UserMovie).filter(
            UserMovie.custom_list_id == custom_list.id
        ).count()

        # Only load first 4 movies for preview
        user_movies = db.query(UserMovie).filter(
            UserMovie.custom_list_id == custom_list.id
        ).limit(4).all()

        movies = []
        for um in user_movies:
            movie_data = tmdb_request(f"/movie/{um.movie.tmdb_id}")
            if movie_data:
                movies.append(movie_data)

        lists_with_movies.append({
            "list": custom_list,
            "movies": movies,
            "count": total_count
        })

    return templates.TemplateResponse("lists.html", {
        "request": request,
        "user": user,
        "lists": lists_with_movies,
        "image_base_url": TMDB_IMAGE_BASE_URL
    })


@app.post("/lists/create")
async def create_list(
    name: str = Form(...),
    description: str = Form(""),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_required)
):
    """Maak een nieuwe custom list"""
    new_list = CustomList(
        user_id=user.id,
        name=name,
        description=description
    )
    db.add(new_list)
    db.commit()
    return RedirectResponse(url="/lists", status_code=303)


@app.get("/lists/{list_id}", response_class=HTMLResponse)
async def view_list(request: Request, list_id: int, page: int = 1, db: Session = Depends(get_db)):
    """Bekijk een specifieke custom list met pagination"""
    user = get_current_user_required(request, db)

    custom_list = db.query(CustomList).filter(
        CustomList.id == list_id,
        CustomList.user_id == user.id
    ).first()

    if not custom_list:
        raise HTTPException(status_code=404, detail="List not found")

    # Pagination settings
    per_page = 20
    offset = (page - 1) * per_page

    # Get total count
    total_movies = db.query(UserMovie).filter(
        UserMovie.custom_list_id == list_id
    ).count()

    total_pages = (total_movies + per_page - 1) // per_page  # Ceiling division

    # Get only movies for current page
    user_movies = db.query(UserMovie).filter(
        UserMovie.custom_list_id == list_id
    ).offset(offset).limit(per_page).all()

    # Batch load movies efficiently
    movies = []
    tmdb_ids = [um.movie.tmdb_id for um in user_movies]

    # Use cached data from MovieItem table when possible
    for um in user_movies:
        # First try to use cached data
        movie_data = {
            "id": um.movie.tmdb_id,
            "title": um.movie.title,
            "poster_path": um.movie.poster_path
        }

        # Only fetch full details if needed (you can make this optional)
        # For performance, we'll just use the cached data
        movies.append(movie_data)

    return templates.TemplateResponse("list_detail.html", {
        "request": request,
        "user": user,
        "list": custom_list,
        "movies": movies,
        "image_base_url": TMDB_IMAGE_BASE_URL,
        "current_page": page,
        "total_pages": total_pages,
        "total_movies": total_movies
    })


@app.post("/lists/{list_id}/add-movie/{movie_id}")
async def add_movie_to_list(
    list_id: int,
    movie_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_required)
):
    """Voeg film toe aan custom list"""
    # Verify list ownership
    custom_list = db.query(CustomList).filter(
        CustomList.id == list_id,
        CustomList.user_id == user.id
    ).first()

    if not custom_list:
        raise HTTPException(status_code=404, detail="List not found")

    # Get movie details from TMDB
    movie = tmdb_request(f"/movie/{movie_id}")
    if not movie:
        raise HTTPException(status_code=404, detail="Movie not found")

    # Find or create movie item
    movie_item = db.query(MovieItem).filter(
        MovieItem.tmdb_id == movie_id).first()
    if not movie_item:
        movie_item = MovieItem(
            tmdb_id=movie_id,
            title=movie["title"],
            poster_path=movie.get("poster_path")
        )
        db.add(movie_item)
        db.commit()
        db.refresh(movie_item)

    # Check if already in list
    existing = db.query(UserMovie).filter(
        UserMovie.user_id == user.id,
        UserMovie.movie_id == movie_item.id,
        UserMovie.custom_list_id == list_id
    ).first()

    if not existing:
        user_movie = UserMovie(
            user_id=user.id,
            movie_id=movie_item.id,
            status="custom",
            custom_list_id=list_id
        )
        db.add(user_movie)
        db.commit()

    return RedirectResponse(url=f"/lists/{list_id}", status_code=303)


@app.post("/lists/{list_id}/delete")
async def delete_list(
    list_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_required)
):
    """Verwijder een custom list"""
    custom_list = db.query(CustomList).filter(
        CustomList.id == list_id,
        CustomList.user_id == user.id
    ).first()

    if custom_list:
        db.delete(custom_list)
        db.commit()

    return RedirectResponse(url="/lists", status_code=303)


# Import functionality
@app.get("/import", response_class=HTMLResponse)
async def import_page(request: Request, db: Session = Depends(get_db)):
    """Import pagina"""
    user = get_current_user_required(request, db)

    # Get user's custom lists for selection
    custom_lists = db.query(CustomList).filter(
        CustomList.user_id == user.id).all()

    return templates.TemplateResponse("import.html", {
        "request": request,
        "user": user,
        "custom_lists": custom_lists
    })


def process_import_background(csv_data: list, import_type: str, target: str, user_id: int, custom_list_id: int = None):
    """Achtergrond taak voor het importeren van films"""
    from models import get_db

    db = next(get_db())

    imported_count = 0
    skipped_count = 0
    error_count = 0
    batch_size = 20
    batch_count = 0

    try:
        for idx, row in enumerate(csv_data):
            try:
                title = None
                year = None

                if import_type == 'letterboxd':
                    title = row.get('Name')
                    year = row.get('Year')
                elif import_type == 'imdb':
                    title = row.get('Title') or row.get('title')
                    year = row.get('Year') or row.get('year')

                if not title:
                    skipped_count += 1
                    continue

                # Search movie on TMDB
                search_query = f"{title} {year}" if year else title
                search_results = tmdb_request("/search/movie", {"query": search_query})

                if not search_results or not search_results.get('results'):
                    skipped_count += 1
                    continue

                # Take first result
                movie = search_results['results'][0]
                movie_id = movie['id']

                # Find or create movie item
                movie_item = db.query(MovieItem).filter(MovieItem.tmdb_id == movie_id).first()
                if not movie_item:
                    movie_item = MovieItem(
                        tmdb_id=movie_id,
                        title=movie['title'],
                        poster_path=movie.get('poster_path')
                    )
                    db.add(movie_item)
                    db.flush()

                # Check if already exists
                existing = db.query(UserMovie).filter(
                    UserMovie.user_id == user_id,
                    UserMovie.movie_id == movie_item.id,
                    UserMovie.status == target if target in ['watchlist', 'watched'] else 'custom',
                    UserMovie.custom_list_id == custom_list_id
                ).first()

                if not existing:
                    user_movie = UserMovie(
                        user_id=user_id,
                        movie_id=movie_item.id,
                        status=target if target in ['watchlist', 'watched'] else 'custom',
                        custom_list_id=custom_list_id
                    )
                    db.add(user_movie)
                    imported_count += 1
                else:
                    skipped_count += 1

                # Batch commit elke 20 items
                batch_count += 1
                if batch_count >= batch_size:
                    db.commit()
                    batch_count = 0

            except Exception as e:
                error_count += 1
                print(f"Error importing '{title}': {str(e)}")
                continue

        # Final commit voor resterende items
        db.commit()

        print(f"Import voltooid: {imported_count} geïmporteerd, {skipped_count} overgeslagen, {error_count} errors")

    except Exception as e:
        print(f"Fatal error in background import: {str(e)}")
        db.rollback()
    finally:
        db.close()


@app.post("/import/csv")
async def import_csv(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    import_type: str = Form(...),
    target: str = Form(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_required)
):
    """Import CSV bestand (Letterboxd of IMDb) - Asynchroon via background task"""

    # Read CSV file
    contents = await file.read()
    text = contents.decode('utf-8')
    csv_reader = list(csv.DictReader(io.StringIO(text)))

    total_rows = len(csv_reader)

    # Limit voor veiligheid
    MAX_IMPORT = 2000
    if total_rows > MAX_IMPORT:
        raise HTTPException(
            status_code=400,
            detail=f"Te veel films ({total_rows}). Maximum is {MAX_IMPORT}. Split je lijst op in kleinere bestanden."
        )

    # Determine target
    custom_list_id = None
    if target not in ['watchlist', 'watched']:
        custom_list_id = int(target)

    # Start background task
    background_tasks.add_task(
        process_import_background,
        csv_reader,
        import_type,
        target,
        user.id,
        custom_list_id
    )

    # Redirect immediately with processing message
    message = f"Import gestart voor {total_rows} films. Dit kan enkele minuten duren. Ververs de pagina om resultaten te zien."

    if custom_list_id:
        return RedirectResponse(url=f"/lists/{custom_list_id}?msg={message}", status_code=303)
    else:
        return RedirectResponse(url=f"/profile?msg={message}", status_code=303)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
