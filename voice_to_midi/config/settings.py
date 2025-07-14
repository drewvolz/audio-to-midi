"""
Settings schema and validation for the Voice to MIDI application.

This module defines the structure and validation rules for all configuration
settings, providing type safety and default values.
"""

import os
from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class AudioSettings:
    """Audio-related configuration settings."""

    sample_rate: int = 44100
    chunk_size: int = 1024
    channels: int = 1
    input_device_index: Optional[int] = None
    input_device_name: Optional[str] = None
    silence_threshold: float = 0.01

    def validate(self) -> None:
        """Validate audio settings."""
        if self.sample_rate <= 0:
            raise ValueError("Sample rate must be positive")
        if self.chunk_size <= 0:
            raise ValueError("Chunk size must be positive")
        if self.channels <= 0:
            raise ValueError("Channels must be positive")
        if self.silence_threshold < 0:
            raise ValueError("Silence threshold must be non-negative")


@dataclass
class MidiSettings:
    """MIDI-related configuration settings."""

    output_port_index: Optional[int] = None
    output_port_name: Optional[str] = None
    channel: int = 0
    velocity: int = 64
    transpose_semitones: int = 0
    max_midi_note: int = 84

    def validate(self) -> None:
        """Validate MIDI settings."""
        if not (0 <= self.channel <= 15):
            raise ValueError("MIDI channel must be between 0 and 15")
        if not (1 <= self.velocity <= 127):
            raise ValueError("MIDI velocity must be between 1 and 127")
        if not (-24 <= self.transpose_semitones <= 24):
            raise ValueError("Transpose must be between -24 and 24 semitones")
        if not (0 <= self.max_midi_note <= 127):
            raise ValueError("Max MIDI note must be between 0 and 127")


@dataclass
class PitchSettings:
    """Pitch detection configuration settings."""

    min_freq: float = 80.0
    max_freq: float = 800.0
    confidence_threshold: float = 0.8
    min_semitone_diff: int = 1
    debounce_time: float = 0.08
    min_note_duration: float = 0.20
    silence_release_time: float = 0.1

    def validate(self) -> None:
        """Validate pitch detection settings."""
        if self.min_freq <= 0:
            raise ValueError("Minimum frequency must be positive")
        if self.max_freq <= self.min_freq:
            raise ValueError("Maximum frequency must be greater than minimum")
        if not (0 <= self.confidence_threshold <= 1):
            raise ValueError("Confidence threshold must be between 0 and 1")
        if self.min_semitone_diff < 0:
            raise ValueError("Minimum semitone difference must be non-negative")
        if self.debounce_time < 0:
            raise ValueError("Debounce time must be non-negative")
        if self.min_note_duration < 0:
            raise ValueError("Minimum note duration must be non-negative")
        if self.silence_release_time < 0:
            raise ValueError("Silence release time must be non-negative")


@dataclass
class PedalSettings:
    """Pedal configuration settings."""

    port: Optional[str] = None
    message: Optional[Dict[str, Any]] = None

    def validate(self) -> None:
        """Validate pedal settings."""
        if self.message is not None:
            required_keys = {"type"}
            if not all(key in self.message for key in required_keys):
                raise ValueError("Pedal message must contain 'type' key")


@dataclass
class Settings:
    """Complete application settings."""

    audio: AudioSettings = field(default_factory=AudioSettings)
    midi: MidiSettings = field(default_factory=MidiSettings)
    pitch: PitchSettings = field(default_factory=PitchSettings)
    pedal: PedalSettings = field(default_factory=PedalSettings)

    def validate(self) -> None:
        """Validate all settings."""
        self.audio.validate()
        self.midi.validate()
        self.pitch.validate()
        self.pedal.validate()

    def to_dict(self) -> Dict[str, Any]:
        """Convert settings to dictionary for JSON serialization."""
        return {
            "audio": {
                "sample_rate": self.audio.sample_rate,
                "chunk_size": self.audio.chunk_size,
                "channels": self.audio.channels,
                "input_device_index": self.audio.input_device_index,
                "input_device_name": self.audio.input_device_name,
                "silence_threshold": self.audio.silence_threshold,
            },
            "midi": {
                "output_port_index": self.midi.output_port_index,
                "output_port_name": self.midi.output_port_name,
                "channel": self.midi.channel,
                "velocity": self.midi.velocity,
                "transpose_semitones": self.midi.transpose_semitones,
                "max_midi_note": self.midi.max_midi_note,
            },
            "pitch": {
                "min_freq": self.pitch.min_freq,
                "max_freq": self.pitch.max_freq,
                "confidence_threshold": self.pitch.confidence_threshold,
                "min_semitone_diff": self.pitch.min_semitone_diff,
                "debounce_time": self.pitch.debounce_time,
                "min_note_duration": self.pitch.min_note_duration,
                "silence_release_time": self.pitch.silence_release_time,
            },
            "pedal": {
                "port": self.pedal.port,
                "message": self.pedal.message,
            },
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Settings":
        """Create settings from dictionary (JSON deserialization)."""
        settings = cls()

        if "audio" in data:
            audio_data = data["audio"]
            settings.audio = AudioSettings(
                sample_rate=audio_data.get("sample_rate", 44100),
                chunk_size=audio_data.get("chunk_size", 1024),
                channels=audio_data.get("channels", 1),
                input_device_index=audio_data.get("input_device_index"),
                input_device_name=audio_data.get("input_device_name"),
                silence_threshold=audio_data.get("silence_threshold", 0.01),
            )

        if "midi" in data:
            midi_data = data["midi"]
            settings.midi = MidiSettings(
                output_port_index=midi_data.get("output_port_index"),
                output_port_name=midi_data.get("output_port_name"),
                channel=midi_data.get("channel", 0),
                velocity=midi_data.get("velocity", 64),
                transpose_semitones=midi_data.get("transpose_semitones", 0),
                max_midi_note=midi_data.get("max_midi_note", 84),
            )

        if "pitch" in data:
            pitch_data = data["pitch"]
            settings.pitch = PitchSettings(
                min_freq=pitch_data.get("min_freq", 80.0),
                max_freq=pitch_data.get("max_freq", 800.0),
                confidence_threshold=pitch_data.get("confidence_threshold", 0.8),
                min_semitone_diff=pitch_data.get("min_semitone_diff", 1),
                debounce_time=pitch_data.get("debounce_time", 0.08),
                min_note_duration=pitch_data.get("min_note_duration", 0.20),
                silence_release_time=pitch_data.get("silence_release_time", 0.1),
            )

        if "pedal" in data:
            pedal_data = data["pedal"]
            settings.pedal = PedalSettings(
                port=pedal_data.get("port"),
                message=pedal_data.get("message"),
            )

        return settings


# Default configuration file path
DEFAULT_CONFIG_PATH = os.path.expanduser("~/.voice_to_midi_config.json")
