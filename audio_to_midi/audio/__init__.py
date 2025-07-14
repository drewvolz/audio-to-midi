"""
Audio Processing Module

This module handles all audio-related functionality including:
- Real-time audio capture from microphone input
- Audio stream management and buffering
- Audio data preprocessing and windowing
- Integration with pitch detection pipeline

The audio system uses PyAudio for cross-platform audio capture with
configurable sample rates, chunk sizes, and input devices.

Example:
    >>> from voice_to_midi.audio import AudioCapture
    >>> capture = AudioCapture(sample_rate=44100, chunk_size=1024)
    >>> capture.start()
    >>> audio_data = capture.get_audio_data()
"""

from .capture import AudioCapture
from .processor import AudioProcessor

__all__ = ["AudioCapture", "AudioProcessor"]
