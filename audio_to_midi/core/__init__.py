"""
Core Application Module

This module contains the main application logic and orchestrates all other modules:
- Main application class with dependency injection
- Application lifecycle management
- Inter-module communication and coordination
- Error handling and logging

The core module provides the main entry point and coordinates the audio capture,
pitch detection, and MIDI output pipeline.

Example:
    >>> from audio_to_midi.core import AudioToMidiApp
    >>> app = AudioToMidiApp()
    >>> app.configure_devices()
    >>> app.start()
"""

from .application import AudioToMidiApp
from .exceptions import AudioError, ConfigError, MidiError, AudioToMidiError

__all__ = [
    "AudioToMidiApp",
    "AudioToMidiError",
    "AudioError",
    "MidiError",
    "ConfigError",
]
