import shutil
import sqlite3

import pytest

from deeptrace.storage.database import MIGRATIONS, Database


@pytest.mark.parametrize("fail", [False, True])
def test_populated_phase1_upgrade_and_rollback(tmp_path, fail):
    migrations = tmp_path / "sql"
    migrations.mkdir()
    shutil.copyfile(MIGRATIONS / "001_foundation.sql", migrations / "001_foundation.sql")
    db = Database(tmp_path / "data")
    db.migrate(migrations)
    with db.transaction() as connection:
        connection.execute(
            "INSERT INTO investigations(id,title,question,created_at,updated_at) "
            "VALUES ('legacy','Saved title','A saved research question','2026','2026')"
        )
    sql = (MIGRATIONS / "002_investigation_workspace.sql").read_text()
    if fail:
        sql += "\nINVALID SQL;\n"
    (migrations / "002_investigation_workspace.sql").write_text(sql)
    if fail:
        with pytest.raises(sqlite3.Error):
            db.migrate(migrations)
    else:
        db.migrate(migrations)
        assert db.ready()
    with db.connection() as connection:
        assert connection.execute("SELECT title FROM investigations").fetchone()[0] == "Saved title"
        assert connection.execute("SELECT MAX(version) FROM schema_meta").fetchone()[0] == (
            1 if fail else 2
        )
        columns = [r[1] for r in connection.execute("PRAGMA table_info(investigations)")]
        assert ("description" in columns) is not fail
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
    backups = list((db.path.parent / "backups").glob("*.sqlite3"))
    assert len(backups) == 1
    with sqlite3.connect(backups[0]) as connection:
        assert connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert connection.execute("SELECT title FROM investigations").fetchone()[0] == "Saved title"
        assert connection.execute("SELECT MAX(version) FROM schema_meta").fetchone()[0] == 1
