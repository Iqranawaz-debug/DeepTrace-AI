import shutil
import sqlite3

import pytest

from deeptrace.storage.database import MIGRATIONS, Database

PHASE3 = ("001_foundation.sql", "002_investigation_workspace.sql", "003_evidence_collection.sql")


@pytest.mark.parametrize("fail", [False, True])
def test_populated_phase3_upgrade_and_atomic_rollback(tmp_path, fail):
    migration_dir = tmp_path / "sql"
    migration_dir.mkdir()
    for name in PHASE3:
        shutil.copyfile(MIGRATIONS / name, migration_dir / name)
    db = Database(tmp_path / "data")
    db.migrate(migration_dir)
    with db.transaction() as con:
        con.execute(
            "INSERT INTO investigations(id,title,question,created_at,updated_at) "
            "VALUES ('inv','Synthetic title','Synthetic question','2026','2026')"
        )
        con.execute(
            "INSERT INTO runs(id,investigation_id,status,mode,plan_revision,config_snapshot_json,"
            "question_snapshot,created_at) "
            "VALUES ('run','inv','completed','mock',0,'{}','q','2026')"
        )
        con.execute(
            "INSERT INTO sources(id,investigation_id,run_id,origin,original_url,canonical_url,"
            "status,extracted_text,text_sha256) VALUES ('src','inv','run','mock','https://f.example/',"
            "'https://f.example/','fetched','Saved text','h')"
        )
        con.execute(
            "INSERT INTO passages(id,investigation_id,source_id,display_id,ordinal,text,"
            "start_offset,end_offset,extraction_version,text_sha256,extracted_at) "
            "VALUES ('p','inv','src','P-0001',1,'Saved text',0,10,'v1','h','2026')"
        )
        before = [con.execute(f"SELECT * FROM {t}").fetchall() for t in ("sources", "passages")]
    for name in ("004_saved_urls.sql", "005_evidence_synthesis.sql"):
        sql = (MIGRATIONS / name).read_bytes()
        broken = fail and name.startswith("005")
        (migration_dir / name).write_bytes(sql + (b"\nINVALID SQL;\n" if broken else b""))
    if fail:
        with pytest.raises(sqlite3.Error):
            db.migrate(migration_dir)
    else:
        db.migrate(migration_dir)
        assert not db.ready()  # This fixture intentionally stops at historical schema 005.
    with db.connection() as con:
        after = [con.execute(f"SELECT * FROM {t}").fetchall() for t in ("sources", "passages")]
        assert after == before
        # Pending migrations apply as one transaction: a failing 005 also rolls back 004.
        assert con.execute("SELECT MAX(version) FROM schema_meta").fetchone()[0] == (
            3 if fail else 5
        )
        tables = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        assert ("report_versions" in tables) is not fail
        assert ("saved_urls" in tables) is not fail
        assert con.execute("PRAGMA foreign_key_check").fetchall() == []
        assert con.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    assert len(list((db.path.parent / "backups").glob("before-4-*.sqlite3"))) == 1
