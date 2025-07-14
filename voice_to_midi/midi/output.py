"""
MIDI output module for sending MIDI messages to external devices/software.

This module handles MIDI output including note on/off messages, channel
management, and connection handling with automatic reconnection.
"""

import logging
import threading
import time
from typing import Callable, Optional, Set

import mido

from ..core.exceptions import MidiError
from .messages import MidiMessageHandler

logger = logging.getLogger(__name__)


class MidiOutput:
    """
    Handles MIDI output to external devices and software.

    This class manages MIDI connections and provides a clean interface for
    sending MIDI messages with automatic reconnection and error handling.

    Example:
        >>> midi_out = MidiOutput()
        >>> midi_out.configure(port_name="IAC Driver Bus 1", channel=0)
        >>> midi_out.connect()
        >>> midi_out.send_note_on(60, 64)  # Middle C
        >>> midi_out.send_note_off(60)
        >>> midi_out.close()
    """

    def __init__(self):
        """Initialize the MIDI output."""
        self.port_name: Optional[str] = None
        self.channel = 0
        self.velocity = 64
        self.transpose = 0

        # Connection state
        self._output_port: Optional[mido.ports.BaseOutput] = None
        self._is_connected = False
        self._connection_lock = threading.Lock()

        # Message handling
        self.message_handler = MidiMessageHandler()

        # Note tracking
        self._active_notes: Set[int] = set()
        self._note_lock = threading.Lock()

        # Callbacks
        self.on_connect: Optional[Callable] = None
        self.on_disconnect: Optional[Callable] = None
        self.on_error: Optional[Callable] = None

        # Auto-reconnect
        self.auto_reconnect = True
        self._reconnect_thread: Optional[threading.Thread] = None
        self._should_reconnect = False

        logger.debug("MIDI output initialized")

    def configure(
        self, port_name: str, channel: int = 0, velocity: int = 64, transpose: int = 0
    ) -> None:
        """
        Configure MIDI output parameters.

        Args:
            port_name: MIDI port name to connect to
            channel: MIDI channel (0-15)
            velocity: Default note velocity (1-127)
            transpose: Transpose in semitones

        Raises:
            MidiError: If configuration is invalid
        """
        if not (0 <= channel <= 15):
            raise MidiError("MIDI channel must be between 0 and 15")
        if not (1 <= velocity <= 127):
            raise MidiError("MIDI velocity must be between 1 and 127")
        if not (-24 <= transpose <= 24):
            raise MidiError("Transpose must be between -24 and 24 semitones")

        self.port_name = port_name
        self.channel = channel
        self.velocity = velocity
        self.transpose = transpose

        logger.info(f"MIDI output configured: {port_name}, channel {channel}")

    def connect(self) -> bool:
        """
        Connect to the MIDI output port.

        Returns:
            True if connected successfully, False otherwise
        """
        with self._connection_lock:
            if self._is_connected:
                logger.warning("Already connected to MIDI port")
                return True

            if not self.port_name:
                raise MidiError("Port name must be configured before connecting")

            try:
                self._output_port = mido.open_output(self.port_name)
                self._is_connected = True

                logger.info(f"Connected to MIDI port: {self.port_name}")

                if self.on_connect:
                    self.on_connect()

                return True

            except Exception as e:
                logger.error(f"Failed to connect to MIDI port {self.port_name}: {e}")
                if self.on_error:
                    self.on_error(MidiError(f"Connection failed: {e}"))

                # Start auto-reconnect if enabled
                if self.auto_reconnect:
                    self._start_reconnect_thread()

                return False

    def disconnect(self) -> None:
        """Disconnect from the MIDI output port."""
        with self._connection_lock:
            if not self._is_connected:
                logger.warning("Not connected to MIDI port")
                return

            # Stop auto-reconnect
            self._should_reconnect = False

            # Send all notes off
            self.send_all_notes_off()

            # Close the port
            if self._output_port:
                try:
                    self._output_port.close()
                    logger.info(f"Disconnected from MIDI port: {self.port_name}")
                except Exception as e:
                    logger.error(f"Error closing MIDI port: {e}")
                finally:
                    self._output_port = None

            self._is_connected = False

            if self.on_disconnect:
                self.on_disconnect()

    def send_note_on(self, note: int, velocity: Optional[int] = None) -> bool:
        """
        Send a note on message.

        Args:
            note: MIDI note number (0-127)
            velocity: Note velocity (1-127, None for default)

        Returns:
            True if message sent successfully
        """
        if not self._is_connected:
            logger.warning("Cannot send note on: not connected")
            return False

        # Apply transpose
        transposed_note = note + self.transpose
        if not (0 <= transposed_note <= 127):
            logger.warning(f"Transposed note {transposed_note} out of range")
            return False

        # Use default velocity if not specified
        if velocity is None:
            velocity = self.velocity

        try:
            # Send note off for previous note if it's still active
            with self._note_lock:
                if transposed_note in self._active_notes:
                    self._send_note_off_internal(transposed_note)

                # Send note on
                message = self.message_handler.create_note_on(
                    transposed_note, velocity, self.channel
                )
                self._output_port.send(message)

                self._active_notes.add(transposed_note)

            logger.debug(f"Note on: {transposed_note} (velocity {velocity})")
            return True

        except Exception as e:
            logger.error(f"Failed to send note on: {e}")
            if self.on_error:
                self.on_error(MidiError(f"Failed to send note on: {e}"))
            self._handle_connection_error()
            return False

    def send_note_off(self, note: int) -> bool:
        """
        Send a note off message.

        Args:
            note: MIDI note number (0-127)

        Returns:
            True if message sent successfully
        """
        if not self._is_connected:
            logger.warning("Cannot send note off: not connected")
            return False

        # Apply transpose
        transposed_note = note + self.transpose
        if not (0 <= transposed_note <= 127):
            logger.warning(f"Transposed note {transposed_note} out of range")
            return False

        return self._send_note_off_internal(transposed_note)

    def _send_note_off_internal(self, note: int) -> bool:
        """Internal note off implementation."""
        try:
            message = self.message_handler.create_note_off(note, 0, self.channel)
            self._output_port.send(message)

            with self._note_lock:
                self._active_notes.discard(note)

            logger.debug(f"Note off: {note}")
            return True

        except Exception as e:
            logger.error(f"Failed to send note off: {e}")
            if self.on_error:
                self.on_error(MidiError(f"Failed to send note off: {e}"))
            self._handle_connection_error()
            return False

    def send_all_notes_off(self) -> bool:
        """
        Send all notes off message.

        Returns:
            True if message sent successfully
        """
        if not self._is_connected:
            logger.warning("Cannot send all notes off: not connected")
            return False

        try:
            # Send note off for all active notes
            with self._note_lock:
                for note in list(self._active_notes):
                    self._send_note_off_internal(note)

            # Send all notes off control change
            message = self.message_handler.create_control_change(
                123,
                0,
                self.channel,  # All notes off
            )
            self._output_port.send(message)

            logger.debug("All notes off sent")
            return True

        except Exception as e:
            logger.error(f"Failed to send all notes off: {e}")
            if self.on_error:
                self.on_error(MidiError(f"Failed to send all notes off: {e}"))
            self._handle_connection_error()
            return False

    def send_control_change(self, control: int, value: int) -> bool:
        """
        Send a control change message.

        Args:
            control: Control number (0-127)
            value: Control value (0-127)

        Returns:
            True if message sent successfully
        """
        if not self._is_connected:
            logger.warning("Cannot send control change: not connected")
            return False

        try:
            message = self.message_handler.create_control_change(
                control, value, self.channel
            )
            self._output_port.send(message)

            logger.debug(f"Control change: {control} = {value}")
            return True

        except Exception as e:
            logger.error(f"Failed to send control change: {e}")
            if self.on_error:
                self.on_error(MidiError(f"Failed to send control change: {e}"))
            self._handle_connection_error()
            return False

    def send_pitch_bend(self, value: int) -> bool:
        """
        Send a pitch bend message.

        Args:
            value: Pitch bend value (-8192 to 8191)

        Returns:
            True if message sent successfully
        """
        if not self._is_connected:
            logger.warning("Cannot send pitch bend: not connected")
            return False

        try:
            message = self.message_handler.create_pitch_bend(value, self.channel)
            self._output_port.send(message)

            logger.debug(f"Pitch bend: {value}")
            return True

        except Exception as e:
            logger.error(f"Failed to send pitch bend: {e}")
            if self.on_error:
                self.on_error(MidiError(f"Failed to send pitch bend: {e}"))
            self._handle_connection_error()
            return False

    def _handle_connection_error(self) -> None:
        """Handle connection errors and attempt reconnection."""
        if self._is_connected:
            logger.warning("MIDI connection lost")
            self._is_connected = False

            if self.on_disconnect:
                self.on_disconnect()

            # Start auto-reconnect if enabled
            if self.auto_reconnect:
                self._start_reconnect_thread()

    def _start_reconnect_thread(self) -> None:
        """Start the auto-reconnect thread."""
        if self._reconnect_thread and self._reconnect_thread.is_alive():
            return

        self._should_reconnect = True
        self._reconnect_thread = threading.Thread(
            target=self._reconnect_loop, name="MidiReconnect", daemon=True
        )
        self._reconnect_thread.start()

    def _reconnect_loop(self) -> None:
        """Auto-reconnect loop."""
        logger.info("Starting MIDI auto-reconnect")

        while self._should_reconnect and not self._is_connected:
            try:
                time.sleep(2.0)  # Wait before retry

                if not self._should_reconnect:
                    break

                logger.info("Attempting to reconnect to MIDI port")
                if self.connect():
                    logger.info("MIDI reconnection successful")
                    break

            except Exception as e:
                logger.debug(f"Reconnection attempt failed: {e}")

        logger.info("MIDI auto-reconnect stopped")

    def close(self) -> None:
        """Close the MIDI output and clean up resources."""
        self._should_reconnect = False
        self.disconnect()

        # Wait for reconnect thread to finish
        if self._reconnect_thread and self._reconnect_thread.is_alive():
            self._reconnect_thread.join(timeout=1.0)

        logger.debug("MIDI output closed")

    @property
    def is_connected(self) -> bool:
        """Check if connected to MIDI port."""
        return self._is_connected

    @property
    def active_notes(self) -> Set[int]:
        """Get currently active notes."""
        with self._note_lock:
            return self._active_notes.copy()

    def get_connection_info(self) -> dict:
        """
        Get information about the MIDI connection.

        Returns:
            Dictionary with connection information
        """
        return {
            "port_name": self.port_name,
            "channel": self.channel,
            "velocity": self.velocity,
            "transpose": self.transpose,
            "is_connected": self._is_connected,
            "active_notes": len(self._active_notes),
            "auto_reconnect": self.auto_reconnect,
        }

    def __del__(self):
        """Destructor to clean up resources."""
        self.close()
