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
    >>> from voice_to_midi.core import VoiceToMidiApp
    >>> app = VoiceToMidiApp()
    >>> app.configure_devices()
    >>> app.start()
"""

from .application import VoiceToMidiApp
from .exceptions import AudioError, ConfigError, MidiError, VoiceToMidiError

__all__ = [
    "VoiceToMidiApp",
    "VoiceToMidiError",
    "AudioError",
    "MidiError",
    "ConfigError",
]
