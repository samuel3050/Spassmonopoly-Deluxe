import json
from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import relationship

from .database import Base, db


class GameSave(Base):
    """Represents a saved game state."""

    __tablename__ = "game_saves"

    id = db.Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    name = db.Column(String(255), nullable=False, unique=True, index=True)
    description = db.Column(Text, nullable=True)
    created_at = db.Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    updated_at = db.Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    version = db.Column(Integer, default=1)

    game_state_json = db.Column(Text, nullable=False, default="{}")

    players = relationship("Player", back_populates="game_save", cascade="all, delete-orphan")
    fields = relationship("Field", back_populates="game_save", cascade="all, delete-orphan")
    events = relationship("GameEvent", back_populates="game_save", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<GameSave {self.name}>"

    def to_dict(self):
        """Convert to dictionary for API responses."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "version": self.version,
        }

    def get_game_state(self):
        """Parse and return the game state JSON."""
        try:
            return json.loads(self.game_state_json) if self.game_state_json else {}
        except (json.JSONDecodeError, TypeError):
            return {}

    def set_game_state(self, state):
        """Store the game state as JSON."""
        self.game_state_json = json.dumps(state, ensure_ascii=False)
        self.updated_at = datetime.utcnow()


class Player(Base):
    """Represents a player in a saved game."""

    __tablename__ = "players"

    id = db.Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    game_save_id = db.Column(String(36), ForeignKey("game_saves.id"), nullable=False, index=True)
    player_index = db.Column(Integer, nullable=False)
    player_id = db.Column(String(36), nullable=False)
    name = db.Column(String(255), nullable=False)
    position = db.Column(Integer, default=0)
    action_points = db.Column(Integer, default=0)
    total_steps = db.Column(Integer, default=0)
    status = db.Column(String(50), default="active")

    game_save = relationship("GameSave", back_populates="players")

    def __repr__(self):
        return f"<Player {self.name}>"

    def to_dict(self):
        """Convert to dictionary."""
        return {
            "id": self.player_id,
            "name": self.name,
            "position": self.position,
            "action_points": self.action_points,
            "total_steps": self.total_steps,
            "status": self.status,
        }


class Field(Base):
    """Represents a field on the board in a saved game."""

    __tablename__ = "fields"

    id = db.Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    game_save_id = db.Column(String(36), ForeignKey("game_saves.id"), nullable=False, index=True)
    field_index = db.Column(Integer, nullable=False)
    field_id = db.Column(String(255), nullable=False)
    owner_player_id = db.Column(String(36), nullable=True)
    properties_json = db.Column(Text, nullable=False, default="{}")

    game_save = relationship("GameSave", back_populates="fields")

    def __repr__(self):
        return f"<Field {self.field_id}>"

    def get_properties(self):
        """Parse and return the properties JSON."""
        try:
            return json.loads(self.properties_json) if self.properties_json else {}
        except (json.JSONDecodeError, TypeError):
            return {}

    def set_properties(self, properties):
        """Store properties as JSON."""
        self.properties_json = json.dumps(properties, ensure_ascii=False)

    def to_dict(self):
        """Convert to dictionary."""
        props = self.get_properties()
        return {
            **props,
            "feld_id": self.field_id,
            "owner_player_id": self.owner_player_id,
        }


class GameEvent(Base):
    """Represents an event that occurred in a game."""

    __tablename__ = "game_events"

    id = db.Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    game_save_id = db.Column(String(36), ForeignKey("game_saves.id"), nullable=False, index=True)
    event_type = db.Column(String(255), nullable=False, index=True)
    data_json = db.Column(Text, nullable=False, default="{}")
    created_at = db.Column(DateTime, nullable=False, default=datetime.utcnow, index=True)

    game_save = relationship("GameSave", back_populates="events")

    def __repr__(self):
        return f"<GameEvent {self.event_type}>"

    def get_data(self):
        """Parse and return the event data JSON."""
        try:
            return json.loads(self.data_json) if self.data_json else {}
        except (json.JSONDecodeError, TypeError):
            return {}

    def set_data(self, data):
        """Store event data as JSON."""
        self.data_json = json.dumps(data, ensure_ascii=False)

    def to_dict(self):
        """Convert to dictionary."""
        return {
            "id": self.id,
            "event_type": self.event_type,
            "data": self.get_data(),
            "created_at": self.created_at.isoformat(),
        }
