"""
Utility functions and helpers for the Voice to MIDI application.

This module provides common utility functions used across the application
including logging setup, validation, and mathematical helpers.
"""

import logging
import sys
from typing import Optional

import numpy as np


def setup_logging(level: str = "INFO", format_string: Optional[str] = None) -> None:
    """
    Configure logging for the application.

    Args:
        level: Logging level ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL')
        format_string: Custom format string for log messages
    """
    if format_string is None:
        format_string = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    logging.basicConfig(
        level=getattr(logging, level.upper()), format=format_string, stream=sys.stdout
    )


def validate_frequency_range(min_freq: float, max_freq: float) -> bool:
    """
    Validate a frequency range.

    Args:
        min_freq: Minimum frequency in Hz
        max_freq: Maximum frequency in Hz

    Returns:
        True if range is valid

    Raises:
        ValueError: If range is invalid
    """
    if min_freq <= 0:
        raise ValueError("Minimum frequency must be positive")
    if max_freq <= min_freq:
        raise ValueError("Maximum frequency must be greater than minimum frequency")
    return True


def frequency_to_midi_note(frequency: float, transpose: int = 0) -> int:
    """
    Convert frequency to MIDI note number.

    Args:
        frequency: Frequency in Hz
        transpose: Transpose in semitones

    Returns:
        MIDI note number (0-127)
    """
    if frequency <= 0:
        raise ValueError("Frequency must be positive")

    # Calculate MIDI note using A4 = 440 Hz as reference (MIDI note 69)
    midi_note = int(round(12 * np.log2(frequency / 440) + 69))
    midi_note += transpose

    # Clamp to valid MIDI range
    return max(0, min(127, midi_note))


def frequency_to_note_name(frequency: float, transpose: int = 0) -> str:
    """
    Convert frequency to note name.

    Args:
        frequency: Frequency in Hz
        transpose: Transpose in semitones

    Returns:
        Note name (e.g., 'C4', 'A#3')
    """
    if frequency <= 0:
        return "None"

    midi_note = frequency_to_midi_note(frequency, transpose)
    return midi_note_to_name(midi_note)


def midi_note_to_name(note_number: int) -> str:
    """
    Convert MIDI note number to note name.

    Args:
        note_number: MIDI note number (0-127)

    Returns:
        Note name (e.g., 'C4', 'A#3')
    """
    if not (0 <= note_number <= 127):
        return "None"

    note_names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
    octave = (note_number // 12) - 1
    note_name = note_names[note_number % 12]
    return f"{note_name}{octave}"


def validate_midi_range(note: int, min_note: int = 0, max_note: int = 127) -> bool:
    """
    Validate MIDI note is within specified range.

    Args:
        note: MIDI note number
        min_note: Minimum allowed note
        max_note: Maximum allowed note

    Returns:
        True if note is in range
    """
    return min_note <= note <= max_note


def clamp(value: float, min_value: float, max_value: float) -> float:
    """
    Clamp value to specified range.

    Args:
        value: Value to clamp
        min_value: Minimum value
        max_value: Maximum value

    Returns:
        Clamped value
    """
    return max(min_value, min(max_value, value))


def db_to_linear(db: float) -> float:
    """
    Convert decibel value to linear scale.

    Args:
        db: Decibel value

    Returns:
        Linear value
    """
    return 10 ** (db / 20)


def linear_to_db(linear: float) -> float:
    """
    Convert linear value to decibels.

    Args:
        linear: Linear value

    Returns:
        Decibel value
    """
    if linear <= 0:
        return -float("inf")
    return 20 * np.log10(linear)


def smooth_value(current: float, target: float, smoothing: float = 0.1) -> float:
    """
    Apply exponential smoothing to a value.

    Args:
        current: Current value
        target: Target value
        smoothing: Smoothing factor (0-1, higher = more smoothing)

    Returns:
        Smoothed value
    """
    return current + (target - current) * (1 - smoothing)
