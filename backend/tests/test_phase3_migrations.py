import shutil
import sqlite3

import pytest

from deeptrace.storage.database import MIGRATIONS, Database


@pytest.mark.parametrize("fail", [False, True])
def test_populated_phase2_upgrade_and_atomic_rollback(tmp_path, fail):
    migration_dir = tmp_path / "sql"
    migration_dir.mkdir()
    for name in ("001_foundation.sql", "002_investigation_workspace.sql"):
        shutil.copyfile(MIGRATIONS / name, migration_dir / name)
    db = Database(tmp_path / "data")
    db.migrate(migration_dir)
    with db.transaction() as con:
        con.execute(
            "INSERT INTO investigations(id,title,question,created_at,updated_at) "
            "VALUES ('legacy','Synthetic preserved title','Synthetic question','2026','2026')"
        )
        before = con.execute("SELECT * FROM investigations").fetchall()
        old_checksums = con.execute("SELECT version,checksum FROM schema_meta").fetchall()
    sql = (MIGRATIONS / "003_evidence_collection.sql").read_bytes()
    (migration_dir / "003_evidence_collection.sql").write_bytes(
        sql + (b"\nINVALID SQL;\n" if fail else b"")
    )
    if fail:
        with pytest.raises(sqlite3.Error):
            db.migrate(migration_dir)
    else:
        db.migrate(migration_dir)
        assert not db.ready()  # This fixture intentionally stops at historical schema 003.
    with db.connection() as con:
        assert con.execute("SELECT * FROM investigations").fetchall() == before
        assert (
            con.execute("SELECT version,checksum FROM schema_meta WHERE version<3").fetchall()
            == old_checksums
        )
        assert con.execute("SELECT MAX(version) FROM schema_meta").fetchone()[0] == (
            2 if fail else 3
        )
        assert (
            bool(con.execute("SELECT name FROM sqlite_master WHERE name='sources'").fetchone())
            is not fail
        )
        assert con.execute("PRAGMA foreign_key_check").fetchall() == []
        assert con.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    backup = list((db.path.parent / "backups").glob("before-3-*.sqlite3"))
    assert len(backup) == 1
    with sqlite3.connect(backup[0]) as con:
        assert con.execute("SELECT * FROM investigations").fetchall() == before
        assert con.execute("SELECT MAX(version) FROM schema_meta").fetchone()[0] == 2
        assert con.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
