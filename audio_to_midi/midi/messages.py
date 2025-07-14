"""
MIDI message handling utilities.

This module provides utilities for creating and processing MIDI messages
with proper validation and error handling.
"""

import logging
from typing import Any, Dict

import mido

from ..core.exceptions import MidiError

logger = logging.getLogger(__name__)


class MidiMessageHandler:
    """
    Handles MIDI message creation and processing.

    This class provides utilities for creating various MIDI messages
    with proper validation and error handling.

    Example:
        >>> handler = MidiMessageHandler()
        >>> note_on = handler.create_note_on(60, 64, 0)
        >>> note_off = handler.create_note_off(60, 0, 0)
        >>> is_valid = handler.validate_message(note_on)
    """

    def __init__(self) -> None:
        """Initialize the MIDI message handler."""
        logger.debug("MIDI message handler initialized")

    def create_note_on(
        self, note: int, velocity: int, channel: int = 0
    ) -> mido.Message:
        """
        Create a note on message.

        Args:
            note: MIDI note number (0-127)
            velocity: Note velocity (1-127)
            channel: MIDI channel (0-15)

        Returns:
            MIDI note on message

        Raises:
            MidiError: If parameters are invalid
        """
        self._validate_note(note)
        self._validate_velocity(velocity)
        self._validate_channel(channel)

        try:
            message = mido.Message(
                "note_on", note=note, velocity=velocity, channel=channel
            )
            logger.debug(
                f"Created note on: note={note}, velocity={velocity}, channel={channel}"
            )
            return message
        except Exception as e:
            raise MidiError(f"Failed to create note on message: {e}")

    def create_note_off(
        self, note: int, velocity: int = 0, channel: int = 0
    ) -> mido.Message:
        """
        Create a note off message.

        Args:
            note: MIDI note number (0-127)
            velocity: Release velocity (0-127)
            channel: MIDI channel (0-15)

        Returns:
            MIDI note off message

        Raises:
            MidiError: If parameters are invalid
        """
        self._validate_note(note)
        self._validate_velocity(velocity, allow_zero=True)
        self._validate_channel(channel)

        try:
            message = mido.Message(
                "note_off", note=note, velocity=velocity, channel=channel
            )
            logger.debug(
                f"Created note off: note={note}, velocity={velocity}, channel={channel}"
            )
            return message
        except Exception as e:
            raise MidiError(f"Failed to create note off message: {e}")

    def create_control_change(
        self, control: int, value: int, channel: int = 0
    ) -> mido.Message:
        """
        Create a control change message.

        Args:
            control: Control number (0-127)
            value: Control value (0-127)
            channel: MIDI channel (0-15)

        Returns:
            MIDI control change message

        Raises:
            MidiError: If parameters are invalid
        """
        self._validate_control(control)
        self._validate_value(value)
        self._validate_channel(channel)

        try:
            message = mido.Message(
                "control_change", control=control, value=value, channel=channel
            )
            logger.debug(
                f"Created control change: control={control}, value={value}, channel={channel}"
            )
            return message
        except Exception as e:
            raise MidiError(f"Failed to create control change message: {e}")

    def create_pitch_bend(self, value: int, channel: int = 0) -> mido.Message:
        """
        Create a pitch bend message.

        Args:
            value: Pitch bend value (-8192 to 8191)
            channel: MIDI channel (0-15)

        Returns:
            MIDI pitch bend message

        Raises:
            MidiError: If parameters are invalid
        """
        self._validate_pitch_bend(value)
        self._validate_channel(channel)

        try:
            # Convert from signed to unsigned 14-bit value
            unsigned_value = value + 8192
            message = mido.Message("pitchwheel", pitch=unsigned_value, channel=channel)
            logger.debug(f"Created pitch bend: value={value}, channel={channel}")
            return message
        except Exception as e:
            raise MidiError(f"Failed to create pitch bend message: {e}")

    def create_program_change(self, program: int, channel: int = 0) -> mido.Message:
        """
        Create a program change message.

        Args:
            program: Program number (0-127)
            channel: MIDI channel (0-15)

        Returns:
            MIDI program change message

        Raises:
            MidiError: If parameters are invalid
        """
        self._validate_program(program)
        self._validate_channel(channel)

        try:
            message = mido.Message("program_change", program=program, channel=channel)
            logger.debug(
                f"Created program change: program={program}, channel={channel}"
            )
            return message
        except Exception as e:
            raise MidiError(f"Failed to create program change message: {e}")

    def create_channel_pressure(self, value: int, channel: int = 0) -> mido.Message:
        """
        Create a channel pressure (aftertouch) message.

        Args:
            value: Pressure value (0-127)
            channel: MIDI channel (0-15)

        Returns:
            MIDI channel pressure message

        Raises:
            MidiError: If parameters are invalid
        """
        self._validate_value(value)
        self._validate_channel(channel)

        try:
            message = mido.Message("aftertouch", value=value, channel=channel)
            logger.debug(f"Created channel pressure: value={value}, channel={channel}")
            return message
        except Exception as e:
            raise MidiError(f"Failed to create channel pressure message: {e}")

    def create_system_exclusive(self, data: bytes) -> mido.Message:
        """
        Create a system exclusive message.

        Args:
            data: SysEx data bytes

        Returns:
            MIDI system exclusive message

        Raises:
            MidiError: If data is invalid
        """
        if not isinstance(data, (bytes, bytearray)):
            raise MidiError("SysEx data must be bytes or bytearray")

        try:
            message = mido.Message("sysex", data=data)
            logger.debug(f"Created SysEx message: {len(data)} bytes")
            return message
        except Exception as e:
            raise MidiError(f"Failed to create SysEx message: {e}")

    def validate_message(self, message: mido.Message) -> bool:
        """
        Validate a MIDI message.

        Args:
            message: MIDI message to validate

        Returns:
            True if message is valid

        Raises:
            MidiError: If message is invalid
        """
        if not isinstance(message, mido.Message):
            raise MidiError("Invalid message type")

        try:
            # Check message type
            if message.type not in [
                "note_on",
                "note_off",
                "control_change",
                "pitchwheel",
                "program_change",
                "aftertouch",
                "sysex",
            ]:
                raise MidiError(f"Unsupported message type: {message.type}")

            # Validate message-specific parameters
            if message.type in ["note_on", "note_off"]:
                self._validate_note(message.note)
                self._validate_velocity(
                    message.velocity, allow_zero=(message.type == "note_off")
                )
                self._validate_channel(message.channel)

            elif message.type == "control_change":
                self._validate_control(message.control)
                self._validate_value(message.value)
                self._validate_channel(message.channel)

            elif message.type == "pitchwheel":
                # Pitch wheel values are 0-16383 (14-bit)
                if not (0 <= message.pitch <= 16383):
                    raise MidiError("Pitch wheel value must be between 0 and 16383")
                self._validate_channel(message.channel)

            elif message.type == "program_change":
                self._validate_program(message.program)
                self._validate_channel(message.channel)

            elif message.type == "aftertouch":
                self._validate_value(message.value)
                self._validate_channel(message.channel)

            return True

        except Exception as e:
            raise MidiError(f"Message validation failed: {e}")

    def message_to_dict(self, message: mido.Message) -> Dict[str, Any]:
        """
        Convert MIDI message to dictionary.

        Args:
            message: MIDI message

        Returns:
            Dictionary representation of message
        """
        result = {"type": message.type}

        # Add message-specific fields
        for attr in [
            "note",
            "velocity",
            "control",
            "value",
            "pitch",
            "program",
            "channel",
        ]:
            if hasattr(message, attr):
                result[attr] = getattr(message, attr)

        # Special handling for SysEx
        if message.type == "sysex":
            result["data"] = list(message.data)

        return result

    def dict_to_message(self, data: Dict[str, Any]) -> mido.Message:
        """
        Create MIDI message from dictionary.

        Args:
            data: Dictionary with message data

        Returns:
            MIDI message

        Raises:
            MidiError: If data is invalid
        """
        if "type" not in data:
            raise MidiError("Message type is required")

        message_type = data["type"]

        try:
            if message_type == "note_on":
                return self.create_note_on(
                    data["note"], data["velocity"], data.get("channel", 0)
                )
            elif message_type == "note_off":
                return self.create_note_off(
                    data["note"], data.get("velocity", 0), data.get("channel", 0)
                )
            elif message_type == "control_change":
                return self.create_control_change(
                    data["control"], data["value"], data.get("channel", 0)
                )
            elif message_type == "pitchwheel":
                # Convert from 14-bit unsigned to signed
                signed_value = data["pitch"] - 8192
                return self.create_pitch_bend(signed_value, data.get("channel", 0))
            elif message_type == "program_change":
                return self.create_program_change(
                    data["program"], data.get("channel", 0)
                )
            elif message_type == "aftertouch":
                return self.create_channel_pressure(
                    data["value"], data.get("channel", 0)
                )
            elif message_type == "sysex":
                return self.create_system_exclusive(bytes(data["data"]))
            else:
                raise MidiError(f"Unsupported message type: {message_type}")

        except KeyError as e:
            raise MidiError(f"Missing required field: {e}")

    def _validate_note(self, note: int) -> None:
        """Validate MIDI note number."""
        if not (0 <= note <= 127):
            raise MidiError("MIDI note must be between 0 and 127")

    def _validate_velocity(self, velocity: int, allow_zero: bool = False) -> None:
        """Validate MIDI velocity."""
        min_vel = 0 if allow_zero else 1
        if not (min_vel <= velocity <= 127):
            raise MidiError(f"MIDI velocity must be between {min_vel} and 127")

    def _validate_channel(self, channel: int) -> None:
        """Validate MIDI channel."""
        if not (0 <= channel <= 15):
            raise MidiError("MIDI channel must be between 0 and 15")

    def _validate_control(self, control: int) -> None:
        """Validate MIDI control number."""
        if not (0 <= control <= 127):
            raise MidiError("MIDI control number must be between 0 and 127")

    def _validate_value(self, value: int) -> None:
        """Validate MIDI value."""
        if not (0 <= value <= 127):
            raise MidiError("MIDI value must be between 0 and 127")

    def _validate_pitch_bend(self, value: int) -> None:
        """Validate pitch bend value."""
        if not (-8192 <= value <= 8191):
            raise MidiError("Pitch bend value must be between -8192 and 8191")

    def _validate_program(self, program: int) -> None:
        """Validate MIDI program number."""
        if not (0 <= program <= 127):
            raise MidiError("MIDI program number must be between 0 and 127")

    def get_message_info(self, message: mido.Message) -> Dict[str, Any]:
        """
        Get detailed information about a MIDI message.

        Args:
            message: MIDI message

        Returns:
            Dictionary with message information
        """
        info = self.message_to_dict(message)

        # Add human-readable descriptions
        if message.type == "note_on":
            from ..utils.helpers import midi_note_to_name

            info["note_name"] = midi_note_to_name(message.note)

        elif message.type == "note_off":
            from ..utils.helpers import midi_note_to_name

            info["note_name"] = midi_note_to_name(message.note)

        elif message.type == "control_change":
            # Add common control change names
            cc_names = {
                1: "Modulation",
                7: "Volume",
                10: "Pan",
                11: "Expression",
                64: "Sustain Pedal",
                123: "All Notes Off",
            }
            info["control_name"] = cc_names.get(message.control, "Unknown")

        return info
