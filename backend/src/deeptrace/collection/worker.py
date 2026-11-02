"""One lifespan-managed worker. Never performs network work inside transactions."""

import importlib
import json
import os
import threading
import time
from functools import partial
from typing import Any, BinaryIO

from deeptrace.collection.fetcher import Fetcher
from deeptrace.collection.parser_process import parse
from deeptrace.collection.policy import CollectionError
from deeptrace.storage.collection_repository import CollectionRepository


class Worker:
    def __init__(self, repository: CollectionRepository, fetcher: Fetcher, research: Any = None):
        self.repo, self.fetcher, self.research = repository, fetcher, research
        self.stop_event = threading.Event()
        self.thread = threading.Thread(target=self.loop, name="collection-worker", daemon=True)
        self.lock: BinaryIO | None = None

    def start(self) -> None:
        # Windows OS lock prevents a second app process from recovering a live run.
        self.lock = open(self.repo.db.path.parent / "collection.lock", "a+b")
        self.lock.seek(0)
        if os.name == "nt":
            import msvcrt

            try:
                msvcrt.locking(self.lock.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError:
                self.lock.close()
                raise RuntimeError("Another collection worker owns this data directory") from None
        else:
            fcntl = importlib.import_module("fcntl")

            fcntl.flock(self.lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        self.repo.recover()
        self.thread.start()

    def close(self) -> None:
        self.stop_event.set()
        self.thread.join(timeout=20)
        if self.thread.is_alive():
            raise RuntimeError("Collection worker did not stop within its deadline")
        if self.lock:
            self.lock.close()

    def loop(self) -> None:
        while not self.stop_event.wait(0.1):
            run = None
            try:
                run = self.repo.claim()
                if run is None:
                    continue
                if (
                    self.research is not None
                    and json.loads(run["config_snapshot_json"]).get("scope")
                    != "evidence_collection"
                ):
                    self.research.execute(run, self.stop_event)
                    continue
                failed = False
                begin = time.monotonic()
                for number, url in enumerate(json.loads(run["config_snapshot_json"])["urls"], 1):
                    if self.stop_event.is_set():
                        self.repo.finish(run["id"], "interrupted")
                        break
                    if self.repo.stopped(run["id"]):
                        self.repo.finish(run["id"], "cancelled")
                        break
                    if time.monotonic() - begin > 1200:
                        self.repo.finish(run["id"], "budget_reached")
                        break
                    result = None
                    final = url
                    failure = None
                    try:
                        fetcher = Fetcher(
                            self.fetcher.transport,
                            partial(self.permitted, run["id"]),
                        )
                        final, body, mime = fetcher.fetch(url)
                        result = parse(body, mime)
                        failed |= result.status == "partial"
                    except CollectionError as exc:
                        failure = exc.code
                        failed = True
                    except Exception:
                        failure = "collection_failed"
                        failed = True
                    if self.stop_event.is_set() or self.repo.stopped(run["id"]):
                        self.repo.finish(
                            run["id"], "interrupted" if self.stop_event.is_set() else "cancelled"
                        )
                        break
                    self.repo.save_source(run, url, final, result, failure, number)
                else:
                    self.repo.finish(
                        run["id"],
                        "cancelled"
                        if self.repo.stopped(run["id"])
                        else "failed"
                        if failed
                        else "completed",
                        "partial_collection" if failed else None,
                    )
            except Exception:
                # Never leave an orphaned running run: persist an honest failure and keep
                # serving. If even that write fails, stop; restart recovery marks it
                # interrupted and retains saved checkpoints.
                try:
                    if run is not None:
                        self.repo.finish(run["id"], "failed", "worker_failure")
                except Exception:
                    self.stop_event.set()

    def permitted(self, run_id: str) -> bool:
        return (
            self.fetcher.allowed()
            and not self.stop_event.is_set()
            and not self.repo.stopped(run_id)
        )
