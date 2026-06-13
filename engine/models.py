import json
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship

from .database import Base, db


def utc_now():
    return datetime.now(UTC)


class GameSave(Base):
    """Represents a saved game state."""

    __tablename__ = "games"
    __table_args__ = (
        Index("ix_games_status_updated", "updated_at"),
    )

    id = db.Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    name = db.Column(String(255), nullable=False, unique=True, index=True)
    description = db.Column(Text, nullable=True)
    created_at = db.Column(DateTime, nullable=False, default=utc_now, index=True)
    updated_at = db.Column(DateTime, nullable=False, default=utc_now, onupdate=utc_now)
    version = db.Column(Integer, default=1)

    game_state_json = db.Column(Text, nullable=False, default="{}")

    players = relationship("Player", back_populates="game_save", cascade="all, delete-orphan")
    fields = relationship("Field", back_populates="game_save", cascade="all, delete-orphan")
    events = relationship("GameEvent", back_populates="game_save", cascade="all, delete-orphan")
    snapshots = relationship("GameStateSnapshot", back_populates="game_save", cascade="all, delete-orphan")
    cards = relationship("Card", back_populates="game_save", cascade="all, delete-orphan")
    settings = relationship("Setting", back_populates="game_save", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<GameSave {self.name}>"

    def to_dict(self):
        """Convert to dictionary for API responses."""
        state = self.get_game_state()
        players = state.get("players", [])
        game = state.get("game", {})
        identity = state.get("identity") or {}
        active_index = int(state.get("active_player_index", 0) or 0) if players else None
        return {
            "id": self.id,
            "game_id": identity.get("game_id"),
            "join_code": identity.get("join_code"),
            "host_id": identity.get("host_id"),
            "name": self.name,
            "description": self.description,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "version": self.version,
            "player_count": len(players),
            "round": game.get("round", 1),
            "turn_number": game.get("turn_number", 1),
            "status": game.get("status", "running"),
            "phase": game.get("phase", "roll"),
            "active_player": players[active_index]["name"] if active_index is not None and active_index < len(players) else None,
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
        self.updated_at = utc_now()


class Player(Base):
    """Represents a player in a saved game."""

    __tablename__ = "players"
    __table_args__ = (
        UniqueConstraint("game_save_id", "player_index", name="uq_players_game_index"),
        UniqueConstraint("game_save_id", "player_id", name="uq_players_game_player_id"),
    )

    id = db.Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    game_save_id = db.Column(String(36), ForeignKey("games.id"), nullable=False, index=True)
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
    __table_args__ = (
        UniqueConstraint("game_save_id", "field_index", name="uq_fields_game_index"),
        UniqueConstraint("game_save_id", "field_id", name="uq_fields_game_field_id"),
        Index("ix_fields_owner", "owner_player_id"),
    )

    id = db.Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    game_save_id = db.Column(String(36), ForeignKey("games.id"), nullable=False, index=True)
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

    __tablename__ = "logs"
    __table_args__ = (
        Index("ix_logs_game_created", "game_save_id", "created_at"),
        Index("ix_logs_game_type", "game_save_id", "event_type"),
    )

    id = db.Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    game_save_id = db.Column(String(36), ForeignKey("games.id"), nullable=False, index=True)
    event_type = db.Column(String(255), nullable=False, index=True)
    severity = db.Column(String(50), nullable=False, default="info", index=True)
    message = db.Column(Text, nullable=False, default="")
    data_json = db.Column(Text, nullable=False, default="{}")
    created_at = db.Column(DateTime, nullable=False, default=utc_now, index=True)

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
            "severity": self.severity,
            "message": self.message,
            "data": self.get_data(),
            "created_at": self.created_at.isoformat(),
        }


class GameStateSnapshot(Base):
    """Stores durable game-state snapshots separate from the game metadata row."""

    __tablename__ = "game_states"
    __table_args__ = (
        Index("ix_game_states_game_created", "game_save_id", "created_at"),
    )

    id = db.Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    game_save_id = db.Column(String(36), ForeignKey("games.id"), nullable=False, index=True)
    version = db.Column(Integer, nullable=False, default=1)
    state_json = db.Column(Text, nullable=False, default="{}")
    created_at = db.Column(DateTime, nullable=False, default=utc_now, index=True)

    game_save = relationship("GameSave", back_populates="snapshots")

    def get_state(self):
        try:
            return json.loads(self.state_json) if self.state_json else {}
        except (json.JSONDecodeError, TypeError):
            return {}

    def set_state(self, state):
        self.state_json = json.dumps(state, ensure_ascii=False)


class Card(Base):
    """Represents a card definition or drawn card persisted for a game."""

    __tablename__ = "cards"
    __table_args__ = (
        Index("ix_cards_game_type", "game_save_id", "card_type"),
        Index("ix_cards_game_pile", "game_save_id", "pile"),
    )

    id = db.Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    game_save_id = db.Column(String(36), ForeignKey("games.id"), nullable=True, index=True)
    card_type = db.Column(String(80), nullable=False, default="gemeinschaft", index=True)
    pile = db.Column(String(40), nullable=False, default="deck", index=True)
    title = db.Column(String(255), nullable=False)
    description = db.Column(Text, nullable=False, default="")
    effect_json = db.Column(Text, nullable=False, default="{}")
    is_active = db.Column(Boolean, nullable=False, default=True)
    created_at = db.Column(DateTime, nullable=False, default=utc_now, index=True)

    game_save = relationship("GameSave", back_populates="cards")

    def get_effect(self):
        try:
            return json.loads(self.effect_json) if self.effect_json else {}
        except (json.JSONDecodeError, TypeError):
            return {}

    def set_effect(self, effect):
        self.effect_json = json.dumps(effect, ensure_ascii=False)


class Setting(Base):
    """Stores per-game release settings and feature flags."""

    __tablename__ = "settings"
    __table_args__ = (
        UniqueConstraint("game_save_id", "key", name="uq_settings_game_key"),
    )

    id = db.Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    game_save_id = db.Column(String(36), ForeignKey("games.id"), nullable=True, index=True)
    key = db.Column(String(120), nullable=False, index=True)
    value = db.Column(Text, nullable=False, default="")
    updated_at = db.Column(DateTime, nullable=False, default=utc_now, onupdate=utc_now)

    game_save = relationship("GameSave", back_populates="settings")
