import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import func, text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from .database import db
from .models import Field, GameEvent, GameSave, Player


class GameSaveService:
    """Service layer for game save operations with transaction support."""

    @staticmethod
    def create_save(name: str, game_state: Dict[str, Any], description: str = "") -> GameSave:
        """Create a new game save.

        Args:
            name: Unique name for the save
            game_state: Complete game state dictionary
            description: Optional description

        Returns:
            GameSave instance

        Raises:
            ValueError: If name already exists
            SQLAlchemyError: On database error
        """
        try:
            existing = db.session.query(GameSave).filter_by(name=name).first()
            if existing:
                raise ValueError(f"Save name '{name}' already exists")

            game_save = GameSave(name=name, description=description)
            game_save.set_game_state(game_state)

            db.session.add(game_save)
            db.session.commit()
            return game_save

        except IntegrityError as e:
            db.session.rollback()
            raise ValueError(f"Save name '{name}' already exists") from e
        except SQLAlchemyError as e:
            db.session.rollback()
            raise ValueError(f"Database error creating save: {str(e)}") from e

    @staticmethod
    def load_save(save_id: str) -> Optional[GameSave]:
        """Load a game save by ID.

        Args:
            save_id: ID of the save to load

        Returns:
            GameSave instance or None if not found
        """
        return db.session.query(GameSave).filter_by(id=save_id).first()

    @staticmethod
    def load_save_by_name(name: str) -> Optional[GameSave]:
        """Load a game save by name.

        Args:
            name: Name of the save

        Returns:
            GameSave instance or None if not found
        """
        return db.session.query(GameSave).filter_by(name=name).first()

    @staticmethod
    def get_game_state(save_id: str) -> Optional[Dict[str, Any]]:
        """Get the game state for a save by ID or save name.

        Args:
            save_id: ID or name of the save

        Returns:
            Game state dictionary or None
        """
        game_save = GameSaveService.load_save(save_id) or GameSaveService.load_save_by_name(save_id)
        if not game_save:
            return None
        return game_save.get_game_state()

    @staticmethod
    def update_save(save_id: str, game_state: Dict[str, Any]) -> Optional[GameSave]:
        """Update an existing game save with new state.

        Args:
            save_id: ID of the save to update
            game_state: New game state

        Returns:
            Updated GameSave instance or None

        Raises:
            SQLAlchemyError: On database error
        """
        try:
            game_save = GameSaveService.load_save(save_id)
            if not game_save:
                return None

            game_save.set_game_state(game_state)
            db.session.commit()
            return game_save

        except SQLAlchemyError as e:
            db.session.rollback()
            raise ValueError(f"Database error updating save: {str(e)}") from e

    @staticmethod
    def delete_save(save_id: str) -> bool:
        """Delete a game save.

        Args:
            save_id: ID of the save to delete

        Returns:
            True if deleted, False if not found

        Raises:
            SQLAlchemyError: On database error
        """
        try:
            game_save = GameSaveService.load_save(save_id)
            if not game_save:
                return False

            db.session.delete(game_save)
            db.session.commit()
            return True

        except SQLAlchemyError as e:
            db.session.rollback()
            raise ValueError(f"Database error deleting save: {str(e)}") from e

    @staticmethod
    def list_saves() -> List[GameSave]:
        """List all game saves ordered by update date.

        Returns:
            List of GameSave instances
        """
        return (
            db.session.query(GameSave)
            .order_by(GameSave.updated_at.desc())
            .all()
        )

    @staticmethod
    def rename_save(save_id: str, new_name: str) -> Optional[GameSave]:
        """Rename a game save.

        Args:
            save_id: ID of the save
            new_name: New name for the save

        Returns:
            Updated GameSave or None if not found

        Raises:
            ValueError: If new name already exists
            SQLAlchemyError: On database error
        """
        try:
            game_save = GameSaveService.load_save(save_id)
            if not game_save:
                return None

            existing = db.session.query(GameSave).filter_by(name=new_name).first()
            if existing and existing.id != save_id:
                raise ValueError(f"Save name '{new_name}' already exists")

            game_save.name = new_name
            db.session.commit()
            return game_save

        except IntegrityError as e:
            db.session.rollback()
            raise ValueError(f"Save name '{new_name}' already exists") from e
        except SQLAlchemyError as e:
            db.session.rollback()
            raise ValueError(f"Database error renaming save: {str(e)}") from e

    @staticmethod
    def duplicate_save(save_id: str, new_name: str) -> Optional[GameSave]:
        """Create a duplicate of an existing game save.

        Args:
            save_id: ID of the save to duplicate
            new_name: Name for the new save

        Returns:
            New GameSave instance or None if source not found

        Raises:
            ValueError: If new name already exists
            SQLAlchemyError: On database error
        """
        try:
            source_save = GameSaveService.load_save(save_id)
            if not source_save:
                return None

            existing = db.session.query(GameSave).filter_by(name=new_name).first()
            if existing:
                raise ValueError(f"Save name '{new_name}' already exists")

            new_save = GameSave(
                name=new_name,
                description=f"Copy of {source_save.name}",
            )
            new_save.set_game_state(source_save.get_game_state())

            db.session.add(new_save)
            db.session.commit()
            return new_save

        except IntegrityError as e:
            db.session.rollback()
            raise ValueError(f"Save name '{new_name}' already exists") from e
        except SQLAlchemyError as e:
            db.session.rollback()
            raise ValueError(f"Database error duplicating save: {str(e)}") from e

    @staticmethod
    def add_event(save_id: str, event_type: str, event_data: Dict[str, Any]) -> Optional[GameEvent]:
        """Add an event to the game event log.

        Args:
            save_id: ID of the save
            event_type: Type of event
            event_data: Event data

        Returns:
            GameEvent instance or None if save not found

        Raises:
            SQLAlchemyError: On database error
        """
        try:
            game_save = GameSaveService.load_save(save_id)
            if not game_save:
                return None

            event = GameEvent(game_save_id=save_id, event_type=event_type)
            event.set_data(event_data)

            db.session.add(event)
            db.session.commit()
            return event

        except SQLAlchemyError as e:
            db.session.rollback()
            raise ValueError(f"Database error adding event: {str(e)}") from e

    @staticmethod
    def check_connection() -> bool:
        """Check if database connection is available.

        Returns:
            True if connection is healthy, False otherwise
        """
        try:
            db.session.execute(text("SELECT 1"))
            return True
        except Exception:
            return False
