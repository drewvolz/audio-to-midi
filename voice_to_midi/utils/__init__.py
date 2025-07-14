"""
Utilities Module

This module provides common utility functions and helpers used across the application:
- Mathematical helpers for audio processing
- Logging configuration and utilities
- Common validation functions
- System compatibility helpers

Example:
    >>> from voice_to_midi.utils import setup_logging, validate_frequency_range
    >>> setup_logging(level='INFO')
    >>> validate_frequency_range(80, 800)
    True
"""

from .helpers import setup_logging, validate_frequency_range, frequency_to_note_name

__all__ = ["setup_logging", "validate_frequency_range", "frequency_to_note_name"]