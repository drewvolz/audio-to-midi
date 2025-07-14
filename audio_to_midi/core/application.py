"""
Main application class for the Voice to MIDI translator.

This module contains the core application logic that orchestrates all other
modules and manages the main processing pipeline.
"""

import logging
import queue
import threading
import time
from typing import Callable, Optional

from ..config import ConfigManager, Settings
from ..core.exceptions import AudioError, MidiError, VoiceToMidiError
from ..utils.helpers import setup_logging

logger = logging.getLogger(__name__)


class VoiceToMidiApp:
    """
    Main application class that orchestrates the voice-to-MIDI conversion pipeline.

    This class manages the lifecycle of the application, coordinates between
    different modules, and provides the main API for starting/stopping the
    voice-to-MIDI conversion process.

    The application follows a modular architecture with dependency injection
    to allow for easy testing and extensibility.

    Example:
        >>> app = VoiceToMidiApp()
        >>> app.load_config()
        >>> app.configure_devices()
        >>> app.start()
        >>> # ... application runs ...
        >>> app.stop()
    """

    def __init__(self, config_path: Optional[str] = None) -> None:
        """
        Initialize the Voice to MIDI application.

        Args:
            config_path: Path to configuration file (optional)
        """
        self.config_manager = ConfigManager(config_path)
        self.settings: Optional[Settings] = None

        # Module instances (injected dependencies)
        self.audio_capture = None
        self.audio_processor = None
        self.pitch_detector = None
        self.midi_output = None
        self.audio_device_manager = None
        self.midi_device_manager = None

        # Runtime state
        self.is_running = False
        self.threads: list = []
        self.queues: dict = {
            "audio": queue.Queue(),
            "pitch": queue.Queue(),
            "midi": queue.Queue(),
        }

        # Event handlers
        self.on_note_change: Optional[Callable] = None
        self.on_frequency_change: Optional[Callable] = None
        self.on_error: Optional[Callable] = None

        # Current state
        self.current_frequency = 0.0
        self.current_note = None
        self.current_confidence = 0.0
        self.last_midi_note = None

        # Robust note detection state
        self.last_pitch = None
        self.last_pitch_time = 0
        self.stable_pitch = None
        self.stable_pitch_time = 0
        self.silence_start_time = None

        # Setup logging
        setup_logging()
        logger.info("Voice to MIDI application initialized")

    def load_config(self) -> Settings:
        """
        Load configuration from file.

        Returns:
            Loaded settings

        Raises:
            VoiceToMidiError: If configuration cannot be loaded
        """
        try:
            self.settings = self.config_manager.load()
            logger.info("Configuration loaded successfully")
            return self.settings
        except Exception as e:
            raise VoiceToMidiError(f"Failed to load configuration: {e}")

    def save_config(self) -> None:
        """
        Save current configuration to file.

        Raises:
            VoiceToMidiError: If configuration cannot be saved
        """
        try:
            self.config_manager.save()
            logger.info("Configuration saved successfully")
        except Exception as e:
            raise VoiceToMidiError(f"Failed to save configuration: {e}")

    def inject_dependencies(self, **modules: object) -> None:
        """
        Inject module dependencies.

        Args:
            **modules: Module instances to inject
        """
        for name, module in modules.items():
            if hasattr(self, name):
                setattr(self, name, module)
                logger.debug(f"Injected dependency: {name}")

    def configure_devices(self, force_selection: bool = False) -> None:
        """
        Configure audio and MIDI devices.

        Args:
            force_selection: Force device selection even if saved config exists

        Raises:
            VoiceToMidiError: If devices cannot be configured
        """
        if not self.settings:
            raise VoiceToMidiError(
                "Configuration must be loaded before configuring devices"
            )
        settings = self.settings  # type: ignore[assignment]

        if not self.audio_device_manager or not self.midi_device_manager:
            raise VoiceToMidiError(
                "Device managers must be injected before configuring devices"
            )

        try:
            # Configure audio device
            if force_selection or not settings.audio.input_device_name:
                devices = self.audio_device_manager.list_input_devices()
                if not devices:
                    raise VoiceToMidiError("No audio input devices found")

                # For now, use the first device or saved device
                if settings.audio.input_device_name:
                    device = self.audio_device_manager.get_device_by_name(
                        settings.audio.input_device_name
                    )
                else:
                    device = devices[0]

                settings.audio.input_device_index = device.index
                settings.audio.input_device_name = device.name
                logger.info(f"Audio device configured: {device.name}")

            # Configure MIDI device
            if force_selection or not settings.midi.output_port_name:
                ports = self.midi_device_manager.list_output_ports()
                if not ports:
                    raise VoiceToMidiError("No MIDI output ports found")

                # For now, use the first port or saved port
                if settings.midi.output_port_name:
                    port = self.midi_device_manager.get_port_by_name(
                        settings.midi.output_port_name
                    )
                else:
                    port = ports[0]

                settings.midi.output_port_index = port.index
                settings.midi.output_port_name = port.name
                logger.info(f"MIDI device configured: {port.name}")

        except Exception as e:
            raise VoiceToMidiError(f"Failed to configure devices: {e}")

    def start(self) -> None:
        """
        Start the voice-to-MIDI conversion process.

        Raises:
            VoiceToMidiError: If application cannot be started
        """
        if self.is_running:
            logger.warning("Application is already running")
            return

        if not self.settings:
            raise VoiceToMidiError("Configuration must be loaded before starting")

        if not all(
            [
                self.audio_capture,
                self.audio_processor,
                self.pitch_detector,
                self.midi_output,
            ]
        ):
            raise VoiceToMidiError("All modules must be injected before starting")

        try:
            # Initialize modules with current settings
            self._initialize_modules()

            # Start processing threads
            self.is_running = True
            self._start_threads()

            logger.info("Voice to MIDI application started")

        except Exception as e:
            self.is_running = False
            raise VoiceToMidiError(f"Failed to start application: {e}")

    def stop(self) -> None:
        """Stop the voice-to-MIDI conversion process."""
        if not self.is_running:
            logger.warning("Application is not running")
            return

        logger.info("Stopping voice to MIDI application")
        self.is_running = False

        # Stop all threads
        for thread in self.threads:
            if thread.is_alive():
                thread.join(timeout=1.0)

        self.threads.clear()

        # Clean up modules
        self._cleanup_modules()

        logger.info("Voice to MIDI application stopped")

    def run(self) -> None:
        """
        Run the application (blocking).

        This method starts the application and blocks until it's stopped
        (e.g., by keyboard interrupt).
        """
        try:
            self.start()

            while self.is_running:
                time.sleep(0.1)

        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt")
        except Exception as e:
            logger.error(f"Application error: {e}")
            if self.on_error:
                self.on_error(e)
        finally:
            self.stop()

    def _initialize_modules(self) -> None:
        """Initialize all modules with current settings."""
        if self.settings is None:
            raise VoiceToMidiError(
                "Configuration must be loaded before initializing modules"
            )
        settings = self.settings
        if self.audio_capture is None:
            raise VoiceToMidiError("Audio capture module not injected")
        if self.audio_processor is None:
            raise VoiceToMidiError("Audio processor module not injected")
        if self.pitch_detector is None:
            raise VoiceToMidiError("Pitch detector module not injected")
        if self.midi_output is None:
            raise VoiceToMidiError("MIDI output module not injected")
        # Initialize audio capture
        self.audio_capture.configure(
            sample_rate=settings.audio.sample_rate,
            chunk_size=settings.audio.chunk_size,
            channels=settings.audio.channels,
            device_index=settings.audio.input_device_index,
        )
        # Initialize audio processor
        self.audio_processor.configure(
            sample_rate=settings.audio.sample_rate,
            silence_threshold=settings.audio.silence_threshold,
        )
        # Initialize pitch detector
        self.pitch_detector.configure(
            sample_rate=settings.audio.sample_rate,
            min_freq=settings.pitch.min_freq,
            max_freq=settings.pitch.max_freq,
            confidence_threshold=settings.pitch.confidence_threshold,
        )
        # Configure smoothing for more stable pitch detection
        self.pitch_detector.set_smoothing(enabled=False)
        # Initialize MIDI output
        self.midi_output.configure(
            port_name=settings.midi.output_port_name,
            channel=settings.midi.channel,
            velocity=settings.midi.velocity,
        )
        # Connect to MIDI output
        if not self.midi_output.connect():
            logger.warning(
                f"Failed to connect to MIDI port: {settings.midi.output_port_name}"
            )

    def _start_threads(self) -> None:
        """Start all processing threads."""
        # Audio capture thread
        audio_thread = threading.Thread(
            target=self._audio_capture_loop, name="AudioCapture", daemon=True
        )
        audio_thread.start()
        self.threads.append(audio_thread)

        # Audio processing thread
        processing_thread = threading.Thread(
            target=self._audio_processing_loop, name="AudioProcessing", daemon=True
        )
        processing_thread.start()
        self.threads.append(processing_thread)

        # MIDI output thread
        midi_thread = threading.Thread(
            target=self._midi_output_loop, name="MidiOutput", daemon=True
        )
        midi_thread.start()
        self.threads.append(midi_thread)

    def _audio_capture_loop(self) -> None:
        """Audio capture processing loop."""
        logger.info("Audio capture loop started")
        try:
            if self.audio_capture is None:
                logger.error("Audio capture module not injected")
                return
            self.audio_capture.start()
            logger.info("Audio capture started successfully")

            while self.is_running:
                try:
                    audio_data = self.audio_capture.get_audio_data(timeout=0.1)
                    if audio_data is not None:
                        self.queues["audio"].put(audio_data)
                except queue.Empty:
                    continue
                except Exception as e:
                    logger.error(f"Audio capture error: {e}")
                    if self.on_error:
                        self.on_error(AudioError(f"Audio capture error: {e}"))
                    break

        except Exception as e:
            logger.error(f"Audio capture loop error: {e}")
            if self.on_error:
                self.on_error(AudioError(f"Audio capture loop error: {e}"))
        finally:
            if self.audio_capture is not None:
                self.audio_capture.stop()

    def _audio_processing_loop(self) -> None:
        """Audio processing and pitch detection loop."""
        logger.info("Audio processing loop started")
        try:
            if self.audio_processor is None or self.pitch_detector is None:
                logger.error("Audio processor or pitch detector module not injected")
                return
            while self.is_running:
                try:
                    audio_data = self.queues["audio"].get(timeout=0.1)

                    # Process audio data
                    processed_data = self.audio_processor.process(audio_data)

                    # Detect pitch
                    frequency, confidence = self.pitch_detector.detect_pitch(
                        processed_data
                    )

                    # Update current state
                    self.current_frequency = frequency or 0.0
                    self.current_confidence = confidence
                    current_time = time.time()

                    # Note detection algorithm with silence detection
                    if frequency is None or (
                        self.settings is not None
                        and confidence < self.settings.pitch.confidence_threshold
                    ):
                        if self.current_note is not None:
                            if self.silence_start_time is None:
                                self.silence_start_time = current_time
                            elif (
                                self.settings is not None
                                and current_time - self.silence_start_time
                                >= self.settings.pitch.silence_release_time
                            ):
                                # Send note off
                                self.queues["midi"].put(
                                    {"note": None, "frequency": 0.0, "confidence": 0.0}
                                )
                                self.current_note = None
                                if self.on_note_change:
                                    self.on_note_change(None, 0.0, 0.0)
                        continue
                    else:
                        self.silence_start_time = None

                    midi_note = self._frequency_to_midi_note(frequency)
                    logger.debug(
                        f"Frequency {frequency:.1f} Hz -> MIDI note {midi_note}"
                    )

                    # Debounce: Only trigger if pitch is stable for debounce_time and differs by min_semitone_diff
                    if self.last_pitch is None or (
                        self.settings is not None
                        and abs(midi_note - self.last_pitch)
                        >= self.settings.pitch.min_semitone_diff
                    ):
                        self.stable_pitch = midi_note
                        self.stable_pitch_time = current_time
                        logger.debug(
                            f"Reset stable pitch to {midi_note}, last_pitch was {self.last_pitch}"
                        )
                    elif midi_note == self.stable_pitch and (
                        current_time - self.stable_pitch_time
                    ) >= (
                        self.settings.pitch.debounce_time
                        if self.settings is not None
                        else 0
                    ):
                        # Only send note if it's different from the current note and held for min_note_duration
                        if (
                            self.current_note is None or midi_note != self.current_note
                        ) and (current_time - self.stable_pitch_time) >= (
                            self.settings.pitch.min_note_duration
                            if self.settings is not None
                            else 0
                        ):
                            # Send new note
                            self.current_note = midi_note
                            logger.debug(f"Sending MIDI note: {midi_note}")
                            self.queues["midi"].put(
                                {
                                    "note": midi_note,
                                    "frequency": frequency,
                                    "confidence": confidence,
                                }
                            )

                            if self.on_note_change:
                                self.on_note_change(midi_note, frequency, confidence)
                        else:
                            logger.debug(
                                f"Not sending note {midi_note}: current_note={self.current_note}, time_held={current_time - self.stable_pitch_time:.3f}"
                            )
                    else:
                        logger.debug(
                            f"Note {midi_note} not stable yet: stable_pitch={self.stable_pitch}, time_since_stable={current_time - self.stable_pitch_time:.3f}"
                        )

                    self.last_pitch = midi_note
                    self.last_pitch_time = current_time

                    # Call frequency change handler
                    if self.on_frequency_change:
                        self.on_frequency_change(self.current_frequency, confidence)

                except queue.Empty:
                    continue
                except Exception as e:
                    logger.error(f"Audio processing error: {e}")
                    if self.on_error:
                        self.on_error(VoiceToMidiError(f"Audio processing error: {e}"))
                    break

        except Exception as e:
            logger.error(f"Audio processing loop error: {e}")
            if self.on_error:
                self.on_error(VoiceToMidiError(f"Audio processing loop error: {e}"))

    def _midi_output_loop(self) -> None:
        """MIDI output processing loop."""
        try:
            while self.is_running:
                try:
                    midi_data = self.queues["midi"].get(timeout=0.1)

                    note = midi_data["note"]

                    if note is not None:
                        # Send note off for previous note first
                        if self.last_midi_note is not None:
                            self.midi_output.send_note_off(self.last_midi_note)
                            logger.debug(f"MIDI note off sent: {self.last_midi_note}")

                        # Send note on for new note
                        success = self.midi_output.send_note_on(note)
                        if success:
                            logger.debug(f"MIDI note on sent: {note}")
                            self.last_midi_note = note
                        else:
                            logger.warning(f"Failed to send MIDI note on: {note}")
                    else:
                        # Send note off for current note
                        if self.last_midi_note is not None:
                            self.midi_output.send_note_off(self.last_midi_note)
                            logger.debug(f"MIDI note off sent: {self.last_midi_note}")
                            self.last_midi_note = None

                except queue.Empty:
                    continue
                except Exception as e:
                    logger.error(f"MIDI output error: {e}")
                    if self.on_error:
                        self.on_error(MidiError(f"MIDI output error: {e}"))
                    break

        except Exception as e:
            logger.error(f"MIDI output loop error: {e}")
            if self.on_error:
                self.on_error(MidiError(f"MIDI output loop error: {e}"))

    def _cleanup_modules(self) -> None:
        """Clean up all modules."""
        if self.audio_capture:
            self.audio_capture.stop()
        if self.midi_output:
            self.midi_output.close()

    def _frequency_to_midi_note(self, frequency: float) -> int:
        """Convert frequency to MIDI note with transpose."""
        from ..utils.helpers import frequency_to_midi_note

        if self.settings is None:
            raise VoiceToMidiError(
                "Configuration must be loaded before converting frequency to MIDI note"
            )
        return frequency_to_midi_note(frequency, self.settings.midi.transpose_semitones)

    @property
    def is_configured(self) -> bool:
        """Check if application is properly configured."""
        return (
            self.settings is not None
            and self.settings.audio.input_device_name is not None
            and self.settings.midi.output_port_name is not None
        )
