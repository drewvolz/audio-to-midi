"""
Configuration Management Module

This module handles all configuration-related functionality including:
- Loading and saving user preferences
- Device settings persistence
- Audio/MIDI parameter management
- Validation and default values

The configuration system uses JSON files for persistence and provides
a clean API for accessing settings throughout the application.

Example:
    >>> from audio_to_midi.config import ConfigManager
    >>> config = ConfigManager()
    >>> config.load()
    >>> config.get_audio_device()
    'Built-in Microphone'
"""

from .manager import ConfigManager
from .settings import Settings

__all__ = ["ConfigManager", "Settings"]
