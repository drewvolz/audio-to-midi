"""
Device Management Module

This module handles discovery and management of audio and MIDI devices:
- Audio input device enumeration
- MIDI output port discovery
- Device capability detection
- Device name/index persistence and matching

The device management system provides a unified interface for discovering
and selecting audio/MIDI devices across different platforms.

Example:
    >>> from voice_to_midi.devices import AudioDeviceManager, MidiDeviceManager
    >>> audio_mgr = AudioDeviceManager()
    >>> devices = audio_mgr.list_input_devices()
    >>> midi_mgr = MidiDeviceManager()
    >>> ports = midi_mgr.list_output_ports()
"""

from .audio_devices import AudioDeviceManager
from .midi_devices import MidiDeviceManager

__all__ = ["AudioDeviceManager", "MidiDeviceManager"]
