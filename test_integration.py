#!/usr/bin/env python
"""Integration test script for SpassMonopoly Deluxe database integration."""

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

os.environ.setdefault("DB_HOST", "localhost")
os.environ.setdefault("DB_USER", "root")
os.environ.setdefault("DB_PASSWORD", "")
os.environ.setdefault("DB_NAME", "spassmonopoly_test")
os.environ.setdefault("FLASK_ENV", "testing")

def test_imports():
    """Test that all modules can be imported."""
    print("Testing imports...")
    try:
        from engine.database import init_db, create_tables, db
        print("  ✓ engine.database")
    except Exception as e:
        print(f"  ✗ engine.database: {e}")
        return False

    try:
        from engine.models import GameSave, Player, Field, GameEvent
        print("  ✓ engine.models")
    except Exception as e:
        print(f"  ✗ engine.models: {e}")
        return False

    try:
        from engine.game_save_service import GameSaveService
        print("  ✓ engine.game_save_service")
    except Exception as e:
        print(f"  ✗ engine.game_save_service: {e}")
        return False

    try:
        from engine.state_io import (
            load_game_state,
            save_game_state,
            delete_game_state,
            list_saved_rooms,
        )
        print("  ✓ engine.state_io")
    except Exception as e:
        print(f"  ✗ engine.state_io: {e}")
        return False

    return True


def test_database_setup():
    """Test database setup and table creation."""
    print("\nTesting database setup...")
    try:
        from game import app, db
        from engine.models import GameSave, Player, Field, GameEvent

        with app.app_context():
            db.create_all()
            print("  ✓ Database tables created")
            return True
    except Exception as e:
        print(f"  ✗ Database setup failed: {e}")
        return False


def test_save_operations():
    """Test game save operations."""
    print("\nTesting save operations...")
    try:
        from game import app
        from engine.game_save_service import GameSaveService

        with app.app_context():
            test_state = {
                "app_name": "Spassmonopoly Deluxe",
                "schema_version": 1,
                "players": [
                    {"id": "p1", "name": "Test Player 1", "position": 0},
                ],
                "board": {"fields": []},
            }

            game_save = GameSaveService.create_save("test_save", test_state, "Test save")
            print(f"  ✓ Created save: {game_save.id}")

            loaded_save = GameSaveService.load_save(game_save.id)
            if loaded_save and loaded_save.get_game_state() == test_state:
                print("  ✓ Loaded save correctly")
            else:
                print("  ✗ Loaded save does not match")
                return False

            updated_save = GameSaveService.update_save(game_save.id, {**test_state, "updated": True})
            if updated_save.get_game_state().get("updated"):
                print("  ✓ Updated save correctly")
            else:
                print("  ✗ Update failed")
                return False

            renamed_save = GameSaveService.rename_save(game_save.id, "renamed_test_save")
            if renamed_save.name == "renamed_test_save":
                print("  ✓ Renamed save correctly")
            else:
                print("  ✗ Rename failed")
                return False

            duplicated_save = GameSaveService.duplicate_save(game_save.id, "duplicated_test_save")
            if duplicated_save and duplicated_save.name == "duplicated_test_save":
                print("  ✓ Duplicated save correctly")
            else:
                print("  ✗ Duplicate failed")
                return False

            saves = GameSaveService.list_saves()
            if len(saves) >= 2:
                print(f"  ✓ Listed saves: {len(saves)} found")
            else:
                print("  ✗ List saves returned unexpected count")
                return False

            deleted = GameSaveService.delete_save(game_save.id)
            if deleted:
                print("  ✓ Deleted save correctly")
            else:
                print("  ✗ Delete failed")
                return False

            return True
    except Exception as e:
        print(f"  ✗ Save operations failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_state_io():
    """Test state I/O compatibility layer."""
    print("\nTesting state I/O layer...")
    try:
        from game import app
        from engine.state_io import (
            save_game_state,
            load_game_state,
            has_save_game,
            delete_game_state,
        )

        with app.app_context():
            test_state = {
                "app_name": "Spassmonopoly Deluxe",
                "players": [{"id": "p1", "name": "Test"}],
            }

            saved = save_game_state("test_room", test_state)
            print("  ✓ Saved game state")

            if has_save_game("test_room"):
                print("  ✓ has_save_game returned True")
            else:
                print("  ✗ has_save_game returned False")
                return False

            loaded = load_game_state("test_room")
            if loaded == test_state:
                print("  ✓ Loaded game state correctly")
            else:
                print("  ✗ Loaded state does not match")
                return False

            deleted = delete_game_state("test_room")
            if not has_save_game("test_room"):
                print("  ✓ Deleted game state")
            else:
                print("  ✗ State still exists after delete")
                return False

            return True
    except Exception as e:
        print(f"  ✗ State I/O failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("=" * 60)
    print("SpassMonopoly Deluxe - Database Integration Test Suite")
    print("=" * 60)

    results = []

    if not test_imports():
        print("\n✗ Import tests failed - cannot continue")
        return False

    if not test_database_setup():
        print("\n✗ Database setup failed - cannot continue")
        return False

    if not test_save_operations():
        results.append(("Save Operations", False))
    else:
        results.append(("Save Operations", True))

    if not test_state_io():
        results.append(("State I/O Layer", False))
    else:
        results.append(("State I/O Layer", True))

    print("\n" + "=" * 60)
    print("Test Results:")
    print("=" * 60)
    for test_name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {test_name}")

    all_passed = all(passed for _, passed in results)
    print("=" * 60)
    if all_passed:
        print("✓ All integration tests passed!")
        return True
    else:
        print("✗ Some tests failed")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
