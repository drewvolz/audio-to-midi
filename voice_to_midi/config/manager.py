"""
Configuration manager for loading, saving, and managing application settings.

This module provides a centralized way to handle all configuration operations
including file I/O, validation, and default value management.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

from ..core.exceptions import ConfigError
from .settings import DEFAULT_CONFIG_PATH, Settings

logger = logging.getLogger(__name__)


class ConfigManager:
    """
    Manages application configuration including loading, saving, and validation.

    The ConfigManager handles all configuration persistence and provides a clean
    interface for accessing and modifying application settings.

    Example:
        >>> config = ConfigManager()
        >>> config.load()
        >>> settings = config.get_settings()
        >>> settings.audio.sample_rate = 48000
        >>> config.save()
    """

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize configuration manager.

        Args:
            config_path: Path to configuration file. If None, uses default path.
        """
        self.config_path = Path(config_path or DEFAULT_CONFIG_PATH)
        self._settings = Settings()
        self._loaded = False

    def load(self) -> Settings:
        """
        Load configuration from file.

        Returns:
            Settings object with loaded configuration.

        Raises:
            ConfigError: If configuration file is invalid or cannot be read.
        """
        if not self.config_path.exists():
            logger.info(f"Config file not found at {self.config_path}, using defaults")
            self._settings = Settings()
            self._loaded = True
            return self._settings

        try:
            with open(self.config_path) as f:
                data = json.load(f)

            # Handle legacy format compatibility
            if self._is_legacy_format(data):
                logger.info("Converting legacy configuration format")
                data = self._convert_legacy_format(data)

            self._settings = Settings.from_dict(data)
            self._settings.validate()
            self._loaded = True

            logger.info(f"Configuration loaded from {self.config_path}")
            return self._settings

        except (json.JSONDecodeError, ValueError) as e:
            raise ConfigError(f"Invalid configuration file: {e}")
        except Exception as e:
            raise ConfigError(f"Failed to load configuration: {e}")

    def save(self) -> None:
        """
        Save current configuration to file.

        Raises:
            ConfigError: If configuration cannot be saved.
        """
        if not self._loaded:
            raise ConfigError("Cannot save configuration that hasn't been loaded")

        try:
            # Ensure directory exists
            self.config_path.parent.mkdir(parents=True, exist_ok=True)

            # Validate before saving
            self._settings.validate()

            with open(self.config_path, "w") as f:
                json.dump(self._settings.to_dict(), f, indent=2)

            logger.info(f"Configuration saved to {self.config_path}")

        except Exception as e:
            raise ConfigError(f"Failed to save configuration: {e}")

    def get_settings(self) -> Settings:
        """
        Get current settings.

        Returns:
            Current Settings object.

        Raises:
            ConfigError: If configuration hasn't been loaded.
        """
        if not self._loaded:
            raise ConfigError("Configuration must be loaded before accessing settings")
        return self._settings

    def update_settings(self, **kwargs) -> None:
        """
        Update settings with new values.

        Args:
            **kwargs: Settings to update in dot notation (e.g., audio_sample_rate=48000)
        """
        if not self._loaded:
            raise ConfigError("Configuration must be loaded before updating settings")

        for key, value in kwargs.items():
            self._update_nested_setting(key, value)

    def reset_to_defaults(self) -> None:
        """Reset all settings to default values."""
        self._settings = Settings()
        self._loaded = True
        logger.info("Configuration reset to defaults")

    def delete_config_file(self) -> None:
        """
        Delete the configuration file.

        Raises:
            ConfigError: If file cannot be deleted.
        """
        try:
            if self.config_path.exists():
                self.config_path.unlink()
                logger.info(f"Configuration file deleted: {self.config_path}")
            else:
                logger.warning(f"Configuration file not found: {self.config_path}")
        except Exception as e:
            raise ConfigError(f"Failed to delete configuration file: {e}")

    def _is_legacy_format(self, data: Dict[str, Any]) -> bool:
        """Check if configuration is in legacy format."""
        legacy_keys = {
            "audio_index",
            "audio_name",
            "midi_index",
            "midi_name",
            "transpose",
            "min_freq",
            "chunk_size",
            "max_midi_note",
            "pedal_port",
            "pedal_message",
        }
        return any(key in data for key in legacy_keys)

    def _convert_legacy_format(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert legacy configuration format to new format."""
        new_format = {
            "audio": {
                "input_device_index": data.get("audio_index"),
                "input_device_name": data.get("audio_name"),
                "chunk_size": data.get("chunk_size", 1024),
            },
            "midi": {
                "output_port_index": data.get("midi_index"),
                "output_port_name": data.get("midi_name"),
                "transpose_semitones": data.get("transpose", 0),
                "max_midi_note": data.get("max_midi_note", 84),
            },
            "pitch": {
                "min_freq": data.get("min_freq", 80.0),
            },
            "pedal": {
                "port": data.get("pedal_port"),
                "message": data.get("pedal_message"),
            },
        }
        return new_format

    def _update_nested_setting(self, key: str, value: Any) -> None:
        """Update a nested setting using dot notation."""
        parts = key.split("_", 1)
        if len(parts) != 2:
            raise ConfigError(f"Invalid setting key format: {key}")

        section, setting = parts

        if hasattr(self._settings, section):
            section_obj = getattr(self._settings, section)
            if hasattr(section_obj, setting):
                setattr(section_obj, setting, value)
            else:
                raise ConfigError(f"Unknown setting: {key}")
        else:
            raise ConfigError(f"Unknown section: {section}")

    @property
    def is_loaded(self) -> bool:
        """Check if configuration has been loaded."""
        return self._loaded

    @property
    def config_exists(self) -> bool:
        """Check if configuration file exists."""
        return self.config_path.exists()
