"""
Main entry point for the Voice to MIDI application.

This module provides the main entry point that handles system dependency
checking and launches the CLI interface.
"""

import logging
import sys

from .cli.commands import cli
from .utils.helpers import setup_logging


def check_system_dependencies() -> list:
    """
    Check for required system dependencies.

    Returns:
        List of missing dependencies
    """
    missing = []

    # Check for tkinter
    try:
        import tkinter  # noqa: F401
    except ImportError:
        missing.append("tkinter")

    # Check for pyaudio
    try:
        import pyaudio  # noqa: F401
    except ImportError:
        missing.append("pyaudio")

    return missing


def display_dependency_error(missing_deps: list) -> None:
    """
    Display system dependency installation instructions.

    Args:
        missing_deps: List of missing dependencies
    """
    print("\nERROR: The following required Python modules could not be imported:")
    for dep in missing_deps:
        print(f"  - {dep}")

    print(
        "\nThis usually means you are missing system libraries (PortAudio and/or Tcl/Tk).\n"
    )
    print("To fix this, install the required system libraries for your OS:")
    print("\nmacOS:")
    print("  brew install portaudio tcl-tk")
    print("\nUbuntu/Debian:")
    print("  sudo apt-get update")
    print("  sudo apt-get install portaudio19-dev tk-dev")
    print("\nFedora:")
    print("  sudo dnf install portaudio-devel tk-devel")
    print("\nAfter installing, re-run your command.")


def main() -> None:
    """Main entry point for the Voice to MIDI application."""
    # Check system dependencies first
    missing_deps = check_system_dependencies()
    if missing_deps:
        display_dependency_error(missing_deps)
        sys.exit(1)

    # Setup basic logging
    setup_logging()

    try:
        # Launch CLI
        cli()
    except KeyboardInterrupt:
        print("\nApplication interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.exception("Unexpected error in main")
        print(f"\nUnexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
