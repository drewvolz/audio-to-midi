"""
CLI Interface Module

This module provides the command-line interface for the Audio to MIDI application
using Click for command parsing and Rich/Questionary for enhanced user interaction.

The CLI is organized into logical commands:
- run: Start the voice-to-MIDI application
- config: Configure devices and settings
- list-devices: Show available audio/MIDI devices
- show-config: Display current configuration
- reset-config: Clear saved configuration

Example:
    $ voice-to-midi run --transpose -12
    $ voice-to-midi config --pedal
    $ voice-to-midi list-devices
"""

from .commands import cli

__all__ = ["cli"]
