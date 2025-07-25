"""
Audio to MIDI Translator

A modular real-time voice-to-MIDI conversion application that captures audio from
your microphone, detects pitch, and converts it to MIDI notes.

This package provides a clean, modular architecture with separated concerns:
- CLI interface for user interaction
- Configuration management for settings persistence
- Audio processing for real-time capture and analysis
- MIDI handling for output to external devices/software
- Pitch detection algorithms for frequency analysis
- Device management for audio/MIDI device discovery
- Core application logic with dependency injection

Example:
    Basic usage:
    >>> from audio_to_midi import AudioToMidiApp
    >>> app = AudioToMidiApp()
    >>> app.run()

    CLI usage:
    $ voice-to-midi run
    $ voice-to-midi config
    $ voice-to-midi list-devices
"""

__version__ = "0.2.0"
__author__ = "Audio to MIDI Translator"
__email__ = "user@example.com"

from .core.application import AudioToMidiApp
from .core.exceptions import AudioError, ConfigError, MidiError, AudioToMidiError

__all__ = [
    "AudioToMidiApp",
    "AudioToMidiError",
    "AudioError",
    "MidiError",
    "ConfigError",
]
