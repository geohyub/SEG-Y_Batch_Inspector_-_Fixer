"""Entry point for `python -m segy_toolbox`."""

import sys


def main():
    from segy_toolbox.logging import setup_logging
    setup_logging()

    if len(sys.argv) > 1 and sys.argv[1] == "gui":
        from segy_toolbox.gui.app import main as gui_main
        gui_main()
    else:
        from segy_toolbox.cli import cli
        cli()


if __name__ == "__main__":
    main()
