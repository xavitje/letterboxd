from sqlalchemy import create_engine, Column, Integer, String, Float, ForeignKey, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user_movies = relationship("UserMovie", back_populates="user", cascade="all, delete-orphan")
    reviews = relationship("Review", back_populates="user", cascade="all, delete-orphan")
    custom_lists = relationship("CustomList", back_populates="user", cascade="all, delete-orphan")


class MovieItem(Base):
    __tablename__ = "movie_items"

    id = Column(Integer, primary_key=True, index=True)
    tmdb_id = Column(Integer, unique=True, index=True, nullable=False)
    title = Column(String, nullable=False)
    poster_path = Column(String)
    added_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user_movies = relationship("UserMovie", back_populates="movie", cascade="all, delete-orphan")


class UserMovie(Base):
    __tablename__ = "user_movies"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    movie_id = Column(Integer, ForeignKey("movie_items.id"), nullable=False)
    status = Column(String, nullable=False)  # 'watchlist', 'watched'
    custom_list_id = Column(Integer, ForeignKey("custom_lists.id"), nullable=True)
    added_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="user_movies")
    movie = relationship("MovieItem", back_populates="user_movies")
    custom_list = relationship("CustomList", back_populates="movies")


class Review(Base):
    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    tmdb_id = Column(Integer, nullable=False, index=True)
    rating = Column(Float, nullable=False)  # 1-10
    review_text = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="reviews")
class CustomList(Base):
    __tablename__ = "custom_lists"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="custom_lists")
    movies = relationship("UserMovie", back_populates="custom_list", cascade="all, delete-orphan")




# Database setup
engine = create_engine("sqlite:///./moviespace.db", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def migrate_database():
    """Migreer database schema voor custom lists"""
    import sqlite3

    conn = sqlite3.connect('moviespace.db')
    cursor = conn.cursor()

    try:
        # Check if custom_list_id column exists
        cursor.execute("PRAGMA table_info(user_movies)")
        columns = [column[1] for column in cursor.fetchall()]

        if 'custom_list_id' not in columns:
            print("Migrating database: Adding custom_list_id column...")
            cursor.execute("ALTER TABLE user_movies ADD COLUMN custom_list_id INTEGER")
            conn.commit()
            print("Migration complete!")

        # Check if custom_lists table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='custom_lists'")
        if not cursor.fetchone():
            print("Creating custom_lists table...")
            Base.metadata.create_all(bind=engine)
            print("custom_lists table created!")

    except Exception as e:
        print(f"Migration error: {e}")
    finally:
        conn.close()

def init_db():
    Base.metadata.create_all(bind=engine)
    migrate_database()
