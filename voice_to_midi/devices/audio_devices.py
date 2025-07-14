"""
Audio device management for discovering and managing audio input devices.

This module provides a unified interface for audio device discovery and
management across different platforms using PyAudio.
"""

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import pyaudio

from ..core.exceptions import DeviceError

logger = logging.getLogger(__name__)


@dataclass
class AudioDevice:
    """Represents an audio input device."""

    index: int
    name: str
    channels: int
    sample_rate: int
    is_default: bool = False

    def __str__(self) -> str:
        return f"{self.name} ({self.channels} channels, {self.sample_rate} Hz)"


class AudioDeviceManager:
    """
    Manages audio input device discovery and configuration.

    This class provides a clean interface for discovering available audio
    input devices and managing their properties.

    Example:
        >>> manager = AudioDeviceManager()
        >>> devices = manager.list_input_devices()
        >>> device = manager.get_device_by_name("Built-in Microphone")
        >>> if manager.test_device(device):
        ...     print("Device is working")
    """

    def __init__(self):
        """Initialize the audio device manager."""
        self._audio = None
        self._devices_cache: Optional[List[AudioDevice]] = None
        self._initialize_audio()

    def _initialize_audio(self) -> None:
        """Initialize PyAudio."""
        try:
            self._audio = pyaudio.PyAudio()
            logger.debug("PyAudio initialized successfully")
        except Exception as e:
            raise DeviceError(f"Failed to initialize PyAudio: {e}")

    def list_input_devices(self, refresh: bool = False) -> List[AudioDevice]:
        """
        List all available audio input devices.

        Args:
            refresh: Force refresh of device list

        Returns:
            List of available audio input devices

        Raises:
            DeviceError: If devices cannot be enumerated
        """
        if self._devices_cache is None or refresh:
            self._refresh_devices()

        return self._devices_cache or []

    def get_device_by_name(self, name: str) -> Optional[AudioDevice]:
        """
        Get audio device by name.

        Args:
            name: Device name to search for

        Returns:
            AudioDevice if found, None otherwise
        """
        devices = self.list_input_devices()
        for device in devices:
            if device.name == name:
                return device
        return None

    def get_device_by_index(self, index: int) -> Optional[AudioDevice]:
        """
        Get audio device by index.

        Args:
            index: Device index to search for

        Returns:
            AudioDevice if found, None otherwise
        """
        devices = self.list_input_devices()
        for device in devices:
            if device.index == index:
                return device
        return None

    def get_default_device(self) -> Optional[AudioDevice]:
        """
        Get the default audio input device.

        Returns:
            Default AudioDevice if available, None otherwise
        """
        devices = self.list_input_devices()
        for device in devices:
            if device.is_default:
                return device

        # If no default is marked, return the first device
        return devices[0] if devices else None

    def test_device(self, device: AudioDevice, duration: float = 1.0) -> bool:
        """
        Test if an audio device is working.

        Args:
            device: Device to test
            duration: Test duration in seconds

        Returns:
            True if device is working, False otherwise
        """
        try:
            stream = self._audio.open(
                format=pyaudio.paFloat32,
                channels=1,
                rate=device.sample_rate,
                input=True,
                input_device_index=device.index,
                frames_per_buffer=1024,
            )

            # Try to read a small amount of data
            stream.read(int(device.sample_rate * duration), exception_on_overflow=False)

            stream.stop_stream()
            stream.close()

            logger.debug(f"Device test successful: {device.name}")
            return True

        except Exception as e:
            logger.warning(f"Device test failed for {device.name}: {e}")
            return False

    def get_device_info(self, device: AudioDevice) -> Dict[str, Any]:
        """
        Get detailed information about a device.

        Args:
            device: Device to get info for

        Returns:
            Dictionary with device information
        """
        try:
            info = self._audio.get_device_info_by_index(device.index)
            return {
                "name": info.get("name", "Unknown"),
                "index": device.index,
                "channels": info.get("maxInputChannels", 0),
                "sample_rate": info.get("defaultSampleRate", 44100),
                "low_latency": info.get("defaultLowInputLatency", 0),
                "high_latency": info.get("defaultHighInputLatency", 0),
                "host_api": info.get("hostApi", 0),
            }
        except Exception as e:
            logger.error(f"Failed to get device info for {device.name}: {e}")
            return {}

    def _refresh_devices(self) -> None:
        """Refresh the device list."""
        if not self._audio:
            raise DeviceError("PyAudio not initialized")

        try:
            devices = []
            device_count = self._audio.get_device_count()
            default_device_index = self._audio.get_default_input_device_info().get(
                "index", -1
            )

            for i in range(device_count):
                try:
                    info = self._audio.get_device_info_by_index(i)

                    # Only include devices with input channels
                    if info.get("maxInputChannels", 0) > 0:
                        device = AudioDevice(
                            index=i,
                            name=info.get("name", f"Device {i}"),
                            channels=info.get("maxInputChannels", 1),
                            sample_rate=int(info.get("defaultSampleRate", 44100)),
                            is_default=(i == default_device_index),
                        )
                        devices.append(device)

                except Exception as e:
                    logger.warning(f"Failed to get info for device {i}: {e}")
                    continue

            self._devices_cache = devices
            logger.info(f"Found {len(devices)} audio input devices")

        except Exception as e:
            raise DeviceError(f"Failed to enumerate audio devices: {e}")

    def close(self) -> None:
        """Clean up resources."""
        if self._audio:
            self._audio.terminate()
            self._audio = None
            logger.debug("PyAudio terminated")

    def __del__(self):
        """Destructor to clean up resources."""
        self.close()
