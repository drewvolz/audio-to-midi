"""
Custom exceptions for the Voice to MIDI application.

This module defines application-specific exceptions that provide better
error handling and debugging information throughout the system.
"""


class VoiceToMidiError(Exception):
    """Base exception for all Voice to MIDI application errors."""
    pass


class AudioError(VoiceToMidiError):
    """Exception raised for audio-related errors."""
    pass


class MidiError(VoiceToMidiError):
    """Exception raised for MIDI-related errors."""
    pass


class ConfigError(VoiceToMidiError):
    """Exception raised for configuration-related errors."""
    pass


class DeviceError(VoiceToMidiError):
    """Exception raised for device management errors."""
    pass


class PitchDetectionError(VoiceToMidiError):
    """Exception raised for pitch detection errors."""
    pass