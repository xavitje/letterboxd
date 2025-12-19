# 🎬 MovieSpace

Een moderne film tracking webapplicatie gebouwd met FastAPI, SQLAlchemy en Tailwind CSS.

## ✨ Features

- 🔐 **Authenticatie**: Volledige user registratie en login systeem
- 🎥 **Film Database**: Integratie met TMDB API voor films, posters en trailers
- 📋 **Watchlist & Gekeken**: Beheer je persoonlijke filmlijsten
- ⭐ **Reviews & Ratings**: Schrijf reviews en geef ratings aan films
- 🔍 **Geavanceerd Zoeken**: Filter op genre, jaar, taal en sorteer op verschillende criteria
- 🎨 **Modern Design**: Dark-mode interface geïnspireerd door Letterboxd

## 🚀 Installatie

### 1. Clone de repository en navigeer naar de folder

```bash
cd MovieSpace
```

### 2. Installeer de dependencies

```bash
pip install -r requirements.txt
```

### 3. TMDB API Key

Ga naar [https://www.themoviedb.org/settings/api](https://www.themoviedb.org/settings/api) en maak een gratis API key aan.

### 4. Configureer het .env bestand

Open het `.env` bestand en voeg je TMDB API key toe:

```env
TMDB_API_KEY=jouw_tmdb_api_key_hier
SECRET_KEY=een_veilige_random_string_voor_jwt_tokens
DATABASE_URL=sqlite:///./moviespace.db
```

Voor de SECRET_KEY kun je een random string genereren met Python:

```python
import secrets
print(secrets.token_urlsafe(32))
```

### 5. Start de applicatie

```bash
python main.py
```

Of met uvicorn:

```bash
uvicorn main:app --reload
```

### 6. Open de applicatie

Ga naar [http://localhost:8000](http://localhost:8000) in je browser.

## 📁 Projectstructuur

```
MovieSpace/
│
├── main.py                 # FastAPI applicatie en routes
├── models.py              # SQLAlchemy database modellen
├── auth.py                # Authenticatie logica
├── .env                   # Environment variabelen
├── requirements.txt       # Python dependencies
│
└── templates/             # Jinja2 templates
    ├── base.html          # Base template met navbar
    ├── index.html         # Home pagina
    ├── search.html        # Zoek & filter pagina
    ├── movie_detail.html  # Film detailpagina
    ├── profile.html       # Gebruikersprofiel
    ├── login.html         # Login pagina
    └── register.html      # Registratie pagina
```

## 🎯 Gebruik

1. **Registreer een account** op de registratiepagina
2. **Log in** met je credentials
3. **Verken films** op de home pagina (Popular & Now Playing)
4. **Zoek films** met filters op genre, jaar, taal en sorteer opties
5. **Bekijk film details** inclusief trailer en gebruikersreviews
6. **Voeg films toe** aan je Watchlist of markeer als Gekeken
7. **Schrijf reviews** en geef ratings aan films
8. **Bekijk je profiel** met al je lijsten en reviews

## 🛠️ Tech Stack

- **Backend**: FastAPI (Python)
- **Database**: SQLite met SQLAlchemy ORM
- **Frontend**: Jinja2 Templates + Tailwind CSS
- **API**: TMDB (The Movie Database)
- **Authenticatie**: JWT tokens via cookies
- **Server**: Uvicorn

## 📊 Database Schema

- **Users**: Gebruikers met username, email, hashed_password
- **MovieItems**: Films opgeslagen met tmdb_id, title, poster_path
- **UserMovies**: Koppeltabel voor lijsten (watchlist, watched)
- **Reviews**: Gebruikersreviews met rating (1-10) en tekst

## 🔑 Belangrijke Functies

### Authenticatie
- Registratie met username, email en wachtwoord
- Login met OAuth2 password flow
- JWT tokens opgeslagen in HTTP-only cookies
- Bcrypt password hashing

### Film Features
- TMDB API integratie voor real-time filmdata
- YouTube trailer embedding
- Film posters via TMDB image URLs
- Genres, release dates, runtime info

### User Features
- Persoonlijke Watchlist
- Gekeken lijst
- Reviews met ratings (1-10 schaal)
- Profiel overzicht met statistieken

## 📝 Licentie

Dit is een educatief project. Filmdata wordt geleverd door TMDB API.

## 🙏 Credits

- Film data: [The Movie Database (TMDB)](https://www.themoviedb.org/)
- Design inspiratie: Letterboxd
- Framework: FastAPI
- Styling: Tailwind CSS
