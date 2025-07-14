"""
MIDI Handling Module

This module provides MIDI output functionality including:
- MIDI port discovery and management
- Note on/off message generation
- MIDI channel and velocity control
- Real-time MIDI output to external devices/software

The MIDI system uses the mido library for cross-platform MIDI support
with automatic port detection and reconnection capabilities.

Example:
    >>> from audio_to_midi.midi import MidiOutput
    >>> midi_out = MidiOutput()
    >>> midi_out.connect('IAC Driver Bus 1')
    >>> midi_out.send_note_on(60, 64)  # Middle C, velocity 64
"""

from .messages import MidiMessageHandler
from .output import MidiOutput

__all__ = ["MidiOutput", "MidiMessageHandler"]
