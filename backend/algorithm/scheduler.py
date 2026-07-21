from __future__ import annotations

import argparse
import threading
from datetime import datetime, timedelta

from algorithm.pipeline import run_pipeline


def run_scheduler(interval_hours: float = 6) -> None:
    interval_seconds = interval_hours * 3600
    stop_event = threading.Event()

    def tick() -> None:
        if stop_event.is_set():
            return
        run_pipeline()
        next_run = datetime.utcnow() + timedelta(hours=interval_hours)
        print(f"[scheduler] next run at: {next_run.isoformat()} UTC")
        timer = threading.Timer(interval_seconds, tick)
        timer.daemon = True
        timer.start()

    try:
        tick()
        stop_event.wait()
    except KeyboardInterrupt:
        stop_event.set()
        print("Scheduler stopped.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run the tag normalization pipeline on a repeating schedule"
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=6,
        metavar="HOURS",
        help="How often to run in hours (default: 6)",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run the pipeline exactly once and exit",
    )
    args = parser.parse_args()

    if args.once:
        run_pipeline()
    else:
        run_scheduler(interval_hours=args.interval)
