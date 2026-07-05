from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, PrimaryKeyConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from database import Base

class User(Base):
    __tablename__ = "users"

    spotify_id = Column(String(255), primary_key=True)
    created_at = Column(DateTime, server_default=func.now())
    last_scan_at = Column(DateTime, nullable=True)
    next_scan_allowed_at = Column(DateTime, nullable=True)

    # Relacionamento para aceder aos artistas do utilizador facilmente
    artists = relationship("UserArtist", back_populates="user", cascade="all, delete-orphan")


class Artist(Base):
    __tablename__ = "artists"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), unique=True, nullable=False)
    genres = Column(String(510), nullable=True)


class UserArtist(Base):
    __tablename__ = "user_artists"

    spotify_id = Column(String(255), ForeignKey("users.spotify_id", ondelete="CASCADE"))
    artist_id = Column(Integer, ForeignKey("artists.id", ondelete="CASCADE"))
    added_at = Column(DateTime, server_default=func.now())

    # Configuração da chave primária composta
    __table_args__ = (
        PrimaryKeyConstraint('spotify_id', 'artist_id'),
    )

    user = relationship("User", back_populates="artists")
    artist = relationship("Artist")


# Tabela para armazenar playlists geradas para cada utilizador
class GeneratedPlaylist(Base):
    __tablename__ = "generated_playlists"

    id = Column(Integer, primary_key=True, autoincrement=True)
    spotify_id = Column(String(255), ForeignKey("users.spotify_id", ondelete="CASCADE"), nullable=False)
    playlist_spotify_id = Column(String(255), unique=True, nullable=False) # Igual ao main.py
    name = Column(String(255), nullable=False)                             # Igual ao main.py
    url = Column(String(510), nullable=False)                              # Igual ao main.py
    created_at = Column(DateTime, server_default=func.now())

    user = relationship("User")