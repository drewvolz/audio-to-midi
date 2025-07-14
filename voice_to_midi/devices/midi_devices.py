"""
MIDI device management for discovering and managing MIDI output ports.

This module provides a unified interface for MIDI device discovery and
management using the mido library.
"""

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import mido

from ..core.exceptions import DeviceError

logger = logging.getLogger(__name__)


@dataclass
class MidiPort:
    """Represents a MIDI output port."""

    index: int
    name: str
    is_virtual: bool = False
    is_available: bool = True

    def __str__(self) -> str:
        status = "virtual" if self.is_virtual else "hardware"
        return f"{self.name} ({status})"


class MidiDeviceManager:
    """
    Manages MIDI output port discovery and configuration.

    This class provides a clean interface for discovering available MIDI
    output ports and managing their properties.

    Example:
        >>> manager = MidiDeviceManager()
        >>> ports = manager.list_output_ports()
        >>> port = manager.get_port_by_name("IAC Driver Bus 1")
        >>> if manager.test_port(port):
        ...     print("Port is working")
    """

    def __init__(self):
        """Initialize the MIDI device manager."""
        self._ports_cache: Optional[List[MidiPort]] = None
        logger.debug("MIDI device manager initialized")

    def list_output_ports(self, refresh: bool = False) -> List[MidiPort]:
        """
        List all available MIDI output ports.

        Args:
            refresh: Force refresh of port list

        Returns:
            List of available MIDI output ports

        Raises:
            DeviceError: If ports cannot be enumerated
        """
        if self._ports_cache is None or refresh:
            self._refresh_ports()

        return self._ports_cache or []

    def list_input_ports(self, refresh: bool = False) -> List[MidiPort]:
        """
        List all available MIDI input ports (for pedal support).

        Args:
            refresh: Force refresh of port list

        Returns:
            List of available MIDI input ports

        Raises:
            DeviceError: If ports cannot be enumerated
        """
        try:
            port_names = mido.get_input_names()
            ports = []

            for i, name in enumerate(port_names):
                port = MidiPort(
                    index=i,
                    name=name,
                    is_virtual=self._is_virtual_port(name),
                    is_available=True,
                )
                ports.append(port)

            logger.debug(f"Found {len(ports)} MIDI input ports")
            return ports

        except Exception as e:
            raise DeviceError(f"Failed to enumerate MIDI input ports: {e}")

    def get_port_by_name(self, name: str) -> Optional[MidiPort]:
        """
        Get MIDI port by name.

        Args:
            name: Port name to search for

        Returns:
            MidiPort if found, None otherwise
        """
        ports = self.list_output_ports()
        for port in ports:
            if port.name == name:
                return port
        return None

    def get_port_by_index(self, index: int) -> Optional[MidiPort]:
        """
        Get MIDI port by index.

        Args:
            index: Port index to search for

        Returns:
            MidiPort if found, None otherwise
        """
        ports = self.list_output_ports()
        if 0 <= index < len(ports):
            return ports[index]
        return None

    def test_port(self, port: MidiPort) -> bool:
        """
        Test if a MIDI port is working.

        Args:
            port: Port to test

        Returns:
            True if port is working, False otherwise
        """
        try:
            # Try to open the port
            with mido.open_output(port.name) as outport:
                # Send a test message (note on followed by note off)
                outport.send(mido.Message("note_on", note=60, velocity=64))
                outport.send(mido.Message("note_off", note=60, velocity=64))

            logger.debug(f"Port test successful: {port.name}")
            return True

        except Exception as e:
            logger.warning(f"Port test failed for {port.name}: {e}")
            return False

    def get_port_info(self, port: MidiPort) -> Dict[str, Any]:
        """
        Get detailed information about a port.

        Args:
            port: Port to get info for

        Returns:
            Dictionary with port information
        """
        return {
            "name": port.name,
            "index": port.index,
            "is_virtual": port.is_virtual,
            "is_available": port.is_available,
            "type": "Virtual" if port.is_virtual else "Hardware",
        }

    def create_virtual_port(self, name: str) -> Optional[MidiPort]:
        """
        Create a virtual MIDI port (platform dependent).

        Args:
            name: Name for the virtual port

        Returns:
            MidiPort if created successfully, None otherwise
        """
        try:
            # Note: Virtual port creation is platform-dependent
            # This is a placeholder implementation
            logger.warning("Virtual port creation not implemented")
            return None

        except Exception as e:
            logger.error(f"Failed to create virtual port {name}: {e}")
            return None

    def _refresh_ports(self) -> None:
        """Refresh the port list."""
        try:
            port_names = mido.get_output_names()
            ports = []

            for i, name in enumerate(port_names):
                port = MidiPort(
                    index=i,
                    name=name,
                    is_virtual=self._is_virtual_port(name),
                    is_available=True,
                )
                ports.append(port)

            self._ports_cache = ports
            logger.info(f"Found {len(ports)} MIDI output ports")

        except Exception as e:
            raise DeviceError(f"Failed to enumerate MIDI ports: {e}")

    def _is_virtual_port(self, name: str) -> bool:
        """
        Determine if a port is virtual based on its name.

        Args:
            name: Port name

        Returns:
            True if port appears to be virtual
        """
        # Common virtual port indicators
        virtual_indicators = [
            "IAC Driver",
            "loopMIDI",
            "MIDI Through",
            "Virtual",
            "Software",
        ]

        return any(indicator in name for indicator in virtual_indicators)

    def refresh_ports(self) -> None:
        """Force refresh of the port list."""
        self._refresh_ports()

    def close(self) -> None:
        """Clean up resources."""
        # mido doesn't require explicit cleanup
        logger.debug("MIDI device manager closed")
