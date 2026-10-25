import argparse
import logging

import uvicorn

from deeptrace.config import Settings
from deeptrace.main import create_app
from deeptrace.storage.database import Database


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["serve", "migrate"])
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    try:
        settings = Settings()
        if args.command == "migrate":
            Database(settings.data_dir).migrate()
            print("Database migrations verified.")
        else:
            uvicorn.run(
                create_app(settings), host=settings.host, port=settings.port, access_log=False
            )
    except Exception:
        print("Startup failed. Check local configuration and migration history.")
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
