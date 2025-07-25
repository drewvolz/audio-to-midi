"""
Utilities Module

This module provides common utility functions and helpers used across the application:
- Mathematical helpers for audio processing
- Logging configuration and utilities
- Common validation functions
- System compatibility helpers

Example:
    >>> from audio_to_midi.utils import setup_logging, validate_frequency_range
    >>> setup_logging(level='INFO')
    >>> validate_frequency_range(80, 800)
    True
"""

from .helpers import frequency_to_note_name, setup_logging, validate_frequency_range

__all__ = ["setup_logging", "validate_frequency_range", "frequency_to_note_name"]
