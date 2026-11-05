import asyncio
import logging
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from bird_worker.runtime import STATE, run


if __name__ == "__main__":
    if "--health" in sys.argv:
        try:
            healthy = time.time() - float((STATE / "heartbeat").read_text()) < 30
        except (OSError, ValueError):
            healthy = False
        raise SystemExit(0 if healthy else 1)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
    logging.getLogger("aio_pika").setLevel(logging.WARNING)
    logging.getLogger("aiormq").setLevel(logging.WARNING)
    asyncio.run(run())
