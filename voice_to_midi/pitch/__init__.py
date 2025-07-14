"""
Pitch Detection Module

This module implements pitch detection algorithms for real-time frequency analysis:
- Autocorrelation-based pitch detection
- Frequency-to-MIDI note conversion
- Confidence scoring and filtering
- Octave correction and harmonics handling

The pitch detection system is optimized for vocal input with configurable
frequency ranges, confidence thresholds, and smoothing parameters.

Example:
    >>> from voice_to_midi.pitch import PitchDetector
    >>> detector = PitchDetector(min_freq=80, max_freq=800)
    >>> frequency, confidence = detector.detect_pitch(audio_data)
    >>> midi_note = detector.frequency_to_midi(frequency)
"""

from .detector import PitchDetector
from .analyzer import PitchAnalyzer

__all__ = ["PitchDetector", "PitchAnalyzer"]