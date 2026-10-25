import shutil
import sqlite3
from concurrent.futures import ThreadPoolExecutor

import pytest

from deeptrace.storage.database import MIGRATIONS, Database, MigrationError


def test_fresh_replay_and_empty(tmp_path):
    db = Database(tmp_path)
    db.migrate()
    with db.connection() as connection:
        before = connection.execute("SELECT * FROM schema_meta").fetchall()
        assert connection.execute("SELECT COUNT(*) FROM investigations").fetchone()[0] == 0
        assert connection.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
    db.migrate()
    with db.connection() as connection:
        assert before == connection.execute("SELECT * FROM schema_meta").fetchall()
        assert connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok"


def test_foreign_keys_every_connection_and_rollback(tmp_path):
    db = Database(tmp_path)
    db.migrate()
    for _ in range(2):
        with db.connection() as connection:
            assert connection.execute("PRAGMA foreign_keys").fetchone()[0] == 1
            assert connection.execute("PRAGMA busy_timeout").fetchone()[0] == 5000
            connection.execute("CREATE TEMP TABLE parent(id INTEGER PRIMARY KEY)")
            connection.execute("CREATE TEMP TABLE child(id INTEGER REFERENCES parent(id))")
            with pytest.raises(sqlite3.IntegrityError):
                connection.execute("INSERT INTO child VALUES (999)")
    with pytest.raises(RuntimeError), db.transaction() as connection:
        connection.execute("INSERT INTO settings VALUES ('mode', '\"offline\"', 1, '2026-01-01')")
        raise RuntimeError("rollback")
    with db.connection() as connection:
        assert connection.execute("SELECT COUNT(*) FROM settings").fetchone()[0] == 0


def test_tampering_and_newer_schema(tmp_path):
    db = Database(tmp_path)
    db.migrate()
    with db.transaction() as connection:
        connection.execute("UPDATE schema_meta SET checksum='changed'")
    with pytest.raises(MigrationError, match="checksum"):
        db.migrate()
    with db.transaction() as connection:
        connection.execute("INSERT INTO schema_meta VALUES (3, 'now', 'future')")
    with pytest.raises(MigrationError, match="newer"):
        db.migrate()


def test_failed_upgrade_rolls_back_and_backups(tmp_path):
    migrations = tmp_path / "sql"
    shutil.copytree(MIGRATIONS, migrations)
    db = Database(tmp_path / "data")
    db.migrate(migrations)
    (migrations / "003_failure.sql").write_text(
        "CREATE TABLE should_rollback(id INTEGER);\nINVALID SQL;\n", encoding="utf-8"
    )
    with pytest.raises(sqlite3.Error):
        db.migrate(migrations)
    with db.connection() as connection:
        assert not connection.execute(
            "SELECT name FROM sqlite_master WHERE name='should_rollback'"
        ).fetchall()
        assert connection.execute("SELECT MAX(version) FROM schema_meta").fetchone()[0] == 2
    backups = list((db.path.parent / "backups").glob("*.sqlite3"))
    assert len(backups) == 1
    with sqlite3.connect(backups[0]) as connection:
        assert connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok"


def test_settings_reject_secrets(tmp_path):
    db = Database(tmp_path)
    db.migrate()
    with pytest.raises(sqlite3.IntegrityError), db.transaction() as connection:
        connection.execute("INSERT INTO settings VALUES ('api_key', '\"secret\"', 1, 'now')")
    with pytest.raises(sqlite3.IntegrityError), db.transaction() as connection:
        connection.execute("INSERT INTO settings VALUES ('mode', '\"secret\"', 1, 'now')")


def test_concurrent_migration(tmp_path):
    db = Database(tmp_path)
    db.migrate()
    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(lambda _: db.migrate(), range(2)))
    assert db.ready()
