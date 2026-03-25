"""Entry point for AI Assistant."""

import logging
import sys
from pathlib import Path


def main():
    # Log to file so errors are visible even when running as .exe (no console)
    log_dir = Path.home() / ".ai-assistant"
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / "assistant.log"

    handlers = [
        logging.FileHandler(log_file, encoding="utf-8"),
    ]
    # Also log to console if available (dev mode)
    try:
        if sys.stdout and sys.stdout.writable():
            handlers.append(logging.StreamHandler(sys.stdout))
    except Exception:
        pass

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=handlers,
    )

    logger = logging.getLogger(__name__)
    logger.info("=== AI Assistant starting ===")

    try:
        from ui.tray import run_app
        run_app()
    except Exception:
        logger.exception("Fatal error on startup")
        raise


if __name__ == "__main__":
    main()
