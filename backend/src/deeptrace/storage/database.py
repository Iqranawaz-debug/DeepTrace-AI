"""Short transactions and serialized, checksummed migrations."""

import hashlib
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

MIGRATIONS = Path(__file__).parent / "migrations"


class MigrationError(RuntimeError):
    pass


class Database:
    def __init__(self, directory: Path) -> None:
        self.path = directory / "deeptrace.sqlite3"

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.path, timeout=5, isolation_level=None)
        try:
            connection.execute("PRAGMA foreign_keys=ON")
            connection.execute("PRAGMA busy_timeout=5000")
            yield connection
        finally:
            connection.close()

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        with self.connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                yield connection
                connection.commit()
            except BaseException:
                connection.rollback()
                raise

    def migrate(self, migrations: Path = MIGRATIONS) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        files = sorted(migrations.glob("[0-9][0-9][0-9]_*.sql"))
        versions = [int(file.name[:3]) for file in files]
        if versions != list(range(1, len(files) + 1)) or not files:
            raise MigrationError("Invalid migration sequence")
        with self.connection() as connection:
            if connection.execute("PRAGMA journal_mode=WAL").fetchone()[0] != "wal":
                raise MigrationError("WAL unavailable")
        with self.transaction() as connection:
            connection.execute("""CREATE TABLE IF NOT EXISTS schema_meta (
                version INTEGER PRIMARY KEY CHECK (version > 0),
                applied_at TEXT NOT NULL, checksum TEXT NOT NULL)""")
            applied = dict(connection.execute("SELECT version, checksum FROM schema_meta"))
            if sorted(applied) != list(range(1, len(applied) + 1)):
                raise MigrationError("Noncontiguous migration history")
            if any(version not in versions for version in applied):
                raise MigrationError("Database schema is newer than this application")
            for version, file in zip(versions, files, strict=True):
                raw = file.read_bytes()
                checksum = hashlib.sha256(raw).hexdigest()
                if version in applied:
                    if applied[version] != checksum:
                        raise MigrationError("Applied migration checksum mismatch")
                    continue
                # Back up committed state while the write lock excludes competing migrations.
                if applied:
                    backup_dir = self.path.parent / "backups"
                    backup_dir.mkdir(exist_ok=True)
                    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%f")
                    with self.connection() as source:
                        backup = sqlite3.connect(backup_dir / f"before-{version}-{stamp}.sqlite3")
                        try:
                            source.backup(backup)
                        finally:
                            backup.close()
                statement = ""
                for line in raw.decode("utf-8").splitlines(keepends=True):
                    statement += line
                    if sqlite3.complete_statement(statement):
                        connection.execute(statement)
                        statement = ""
                if statement.strip():
                    raise MigrationError("Incomplete migration SQL")
                connection.execute(
                    "INSERT INTO schema_meta VALUES (?, ?, ?)",
                    (version, datetime.now(UTC).isoformat(), checksum),
                )

    def ready(self) -> bool:
        with self.connection() as connection:
            return bool(
                connection.execute("SELECT MAX(version) FROM schema_meta").fetchone()[0]
                == len(list(MIGRATIONS.glob("[0-9][0-9][0-9]_*.sql")))
            )
