"""Entry point for AI Assistant."""

import logging
import sys


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    from ui.tray import run_app

    run_app()


if __name__ == "__main__":
    main()
