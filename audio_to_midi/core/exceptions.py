"""
Custom exceptions for the Audio to MIDI application.

This module defines application-specific exceptions that provide better
error handling and debugging information throughout the system.
"""


class AudioToMidiError(Exception):
    """Base exception for all Audio to MIDI application errors."""

    pass


class AudioError(AudioToMidiError):
    """Exception raised for audio-related errors."""

    pass


class MidiError(AudioToMidiError):
    """Exception raised for MIDI-related errors."""

    pass


class ConfigError(AudioToMidiError):
    """Exception raised for configuration-related errors."""

    pass


class DeviceError(AudioToMidiError):
    """Exception raised for device management errors."""

    pass


class PitchDetectionError(AudioToMidiError):
    """Exception raised for pitch detection errors."""

    pass
