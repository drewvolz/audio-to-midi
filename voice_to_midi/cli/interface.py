"""
CLI interface utilities for enhanced user interaction.

This module provides utilities for creating rich terminal interfaces
using Rich and Questionary libraries.
"""

import logging
from typing import Any, Dict, List, Optional

import questionary
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ..core.exceptions import VoiceToMidiError
from ..devices.audio_devices import AudioDevice
from ..devices.midi_devices import MidiPort

logger = logging.getLogger(__name__)


class CLIInterface:
    """
    Enhanced CLI interface for user interaction.

    This class provides utilities for creating rich terminal interfaces
    with tables, prompts, and interactive selection menus.

    Example:
        >>> cli = CLIInterface()
        >>> devices = cli.select_audio_device(available_devices)
        >>> port = cli.select_midi_port(available_ports)
        >>> cli.display_success("Configuration saved!")
    """

    def __init__(self):
        """Initialize the CLI interface."""
        self.console = Console()
        logger.debug("CLI interface initialized")

    def display_header(self, title: str, subtitle: Optional[str] = None) -> None:
        """
        Display a formatted header.

        Args:
            title: Main title text
            subtitle: Optional subtitle text
        """
        self.console.print()
        self.console.print(f"[bold cyan]{title}[/bold cyan]")
        if subtitle:
            self.console.print(f"[dim]{subtitle}[/dim]")
        self.console.print("=" * len(title), style="cyan")
        self.console.print()

    def display_success(self, message: str) -> None:
        """Display a success message."""
        self.console.print(f"[bold green]✓[/bold green] {message}")

    def display_error(self, message: str) -> None:
        """Display an error message."""
        self.console.print(f"[bold red]✗[/bold red] {message}")

    def display_warning(self, message: str) -> None:
        """Display a warning message."""
        self.console.print(f"[bold yellow]⚠[/bold yellow] {message}")

    def display_info(self, message: str) -> None:
        """Display an info message."""
        self.console.print(f"[bold blue]ℹ[/bold blue] {message}")

    def display_audio_devices(self, devices: List[AudioDevice]) -> None:
        """
        Display a table of audio devices.

        Args:
            devices: List of audio devices to display
        """
        if not devices:
            self.display_warning("No audio input devices found")
            return

        table = Table(title="Available Audio Input Devices", box=box.ROUNDED)
        table.add_column("Index", style="cyan", justify="right")
        table.add_column("Device Name", style="green")
        table.add_column("Channels", style="yellow", justify="center")
        table.add_column("Sample Rate", style="blue", justify="center")
        table.add_column("Default", style="magenta", justify="center")

        for i, device in enumerate(devices):
            default_mark = "✓" if device.is_default else ""
            table.add_row(
                str(i),
                device.name,
                str(device.channels),
                f"{device.sample_rate} Hz",
                default_mark,
            )

        self.console.print(table)

    def display_midi_ports(self, ports: List[MidiPort]) -> None:
        """
        Display a table of MIDI ports.

        Args:
            ports: List of MIDI ports to display
        """
        if not ports:
            self.display_warning("No MIDI output ports found")
            return

        table = Table(title="Available MIDI Output Ports", box=box.ROUNDED)
        table.add_column("Index", style="cyan", justify="right")
        table.add_column("Port Name", style="green")
        table.add_column("Type", style="yellow", justify="center")
        table.add_column("Status", style="blue", justify="center")

        for i, port in enumerate(ports):
            port_type = "Virtual" if port.is_virtual else "Hardware"
            status = "Available" if port.is_available else "Unavailable"
            table.add_row(str(i), port.name, port_type, status)

        self.console.print(table)

    def select_audio_device(
        self,
        devices: List[AudioDevice],
        default_index: Optional[int] = None,
        default_name: Optional[str] = None,
    ) -> Optional[AudioDevice]:
        """
        Interactive audio device selection.

        Args:
            devices: List of available devices
            default_index: Default selection index (fallback)
            default_name: Default selection by device name (preferred)

        Returns:
            Selected AudioDevice or None if cancelled
        """
        if not devices:
            self.display_error("No audio devices available")
            return None

        if len(devices) == 1:
            self.display_info(f"Only one audio device found: {devices[0].name}")
            return devices[0]

        self.display_audio_devices(devices)

        # Create choices for questionary
        choices = []
        for i, device in enumerate(devices):
            default_mark = " (default)" if device.is_default else ""
            choice_text = f"{i}: {device.name}{default_mark}"
            choices.append(questionary.Choice(choice_text, value=i))

        # Set default choice - prefer matching by name over index
        default_choice = 0

        # First try to match by device name (most reliable)
        if default_name:
            for i, device in enumerate(devices):
                if device.name.strip() == default_name.strip():
                    default_choice = i
                    break
        # Fall back to index if name matching fails
        elif default_index is not None and 0 <= default_index < len(devices):
            default_choice = default_index
        # Finally fall back to system default
        elif any(device.is_default for device in devices):
            default_choice = next(
                i for i, device in enumerate(devices) if device.is_default
            )

        try:
            selection = questionary.select(
                "Select audio input device:",
                choices=choices,
                default=choices[default_choice],
            ).ask()

            if selection is None:
                return None

            return devices[selection]

        except (KeyboardInterrupt, EOFError):
            return None

    def select_midi_port(
        self,
        ports: List[MidiPort],
        default_index: Optional[int] = None,
        default_name: Optional[str] = None,
    ) -> Optional[MidiPort]:
        """
        Interactive MIDI port selection.

        Args:
            ports: List of available ports
            default_index: Default selection index

        Returns:
            Selected MidiPort or None if cancelled
        """
        if not ports:
            self.display_error("No MIDI ports available")
            return None

        if len(ports) == 1:
            self.display_info(f"Only one MIDI port found: {ports[0].name}")
            return ports[0]

        self.display_midi_ports(ports)

        # Create choices for questionary
        choices = []
        for i, port in enumerate(ports):
            port_type = " (virtual)" if port.is_virtual else ""
            choice_text = f"{i}: {port.name}{port_type}"
            choices.append(questionary.Choice(choice_text, value=i))

        # Set default choice - prefer matching by name over index
        default_choice = 0

        # First try to match by port name (most reliable)
        if default_name:
            for i, port in enumerate(ports):
                if port.name.strip() == default_name.strip():
                    default_choice = i
                    break
        # Fall back to index if name matching fails
        elif default_index is not None and 0 <= default_index < len(ports):
            default_choice = default_index

        try:
            selection = questionary.select(
                "Select MIDI output port:",
                choices=choices,
                default=choices[default_choice],
            ).ask()

            if selection is None:
                return None

            # Show helpful information about MIDI channels
            self.console.print(
                "\n[dim]💡 Tip: MIDI channels (0-15) can be configured in advanced settings.\n"
                "Most software uses channel 0 by default.[/dim]"
            )

            return ports[selection]

        except (KeyboardInterrupt, EOFError):
            return None

    def configure_audio_settings(
        self, current_settings: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Interactive audio settings configuration.

        Args:
            current_settings: Current audio settings

        Returns:
            Updated settings dictionary
        """
        settings = current_settings.copy()

        self.console.print("[bold]Audio Settings Configuration[/bold]")

        # Sample rate
        sample_rate_choices = [
            questionary.Choice("44.1 kHz (CD quality)", value=44100),
            questionary.Choice("48 kHz (Professional)", value=48000),
            questionary.Choice("22.05 kHz (Lower quality)", value=22050),
        ]

        # Find the default choice that matches the current sample rate
        current_sample_rate = settings.get("sample_rate", 44100)
        default_choice = None
        for choice in sample_rate_choices:
            if choice.value == current_sample_rate:
                default_choice = choice
                break
        if default_choice is None:
            default_choice = sample_rate_choices[0]

        sample_rate = questionary.select(
            "Select sample rate:",
            choices=sample_rate_choices,
            default=default_choice,
        ).ask()

        if sample_rate is not None:
            settings["sample_rate"] = sample_rate

        # Chunk size
        chunk_size_choices = [
            questionary.Choice("512 samples (Low latency)", value=512),
            questionary.Choice("1024 samples (Balanced)", value=1024),
            questionary.Choice("2048 samples (Better low freq)", value=2048),
            questionary.Choice("4096 samples (Best low freq)", value=4096),
        ]

        # Find the default choice that matches the current chunk size
        current_chunk_size = settings.get("chunk_size", 1024)
        default_chunk_choice = None
        for choice in chunk_size_choices:
            if choice.value == current_chunk_size:
                default_chunk_choice = choice
                break
        if default_chunk_choice is None:
            default_chunk_choice = chunk_size_choices[
                1
            ]  # Default to 1024 samples (Balanced)

        chunk_size = questionary.select(
            "Select chunk size (affects latency and frequency resolution):",
            choices=chunk_size_choices,
            default=default_chunk_choice,
        ).ask()

        if chunk_size is not None:
            settings["chunk_size"] = chunk_size

        # Silence threshold
        silence_threshold = questionary.text(
            "Enter silence threshold (0.001-0.1):",
            default=str(settings.get("silence_threshold", 0.01)),
            validate=lambda val: 0.001 <= float(val) <= 0.1,
        ).ask()

        if silence_threshold is not None:
            settings["silence_threshold"] = float(silence_threshold)

        return settings

    def configure_midi_settings(
        self, current_settings: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Interactive MIDI settings configuration.

        Args:
            current_settings: Current MIDI settings

        Returns:
            Updated settings dictionary
        """
        settings = current_settings.copy()

        self.console.print("[bold]MIDI Settings Configuration[/bold]")

        # Show channel information
        self.console.print(
            "\n[dim]MIDI channels allow you to send different instruments to different tracks.\n"
            "Most software defaults to channel 0 (1). Check your receiving software's settings.[/dim]\n"
        )

        # MIDI channel
        def validate_channel(val):
            if not val.strip():
                return False
            try:
                return 0 <= int(val) <= 15
            except ValueError:
                return False

        channel = questionary.text(
            "Enter MIDI channel (0-15):",
            default=str(settings.get("channel", 0)),
            validate=validate_channel,
        ).ask()

        if channel is not None:
            settings["channel"] = int(channel)

        # Velocity
        velocity = questionary.text(
            "Enter default velocity (1-127):",
            default=str(settings.get("velocity", 64)),
            validate=lambda val: val.strip() == ""
            or (val.strip().isdigit() and 1 <= int(val.strip()) <= 127),
        ).ask()

        if velocity is not None:
            settings["velocity"] = int(velocity)

        # Transpose
        transpose = questionary.text(
            "Enter transpose in semitones (-24 to 24):",
            default=str(settings.get("transpose_semitones", 0)),
            validate=lambda val: val.strip() == ""
            or (val.strip().lstrip("-").isdigit() and -24 <= int(val.strip()) <= 24),
        ).ask()

        if transpose is not None:
            settings["transpose_semitones"] = int(transpose)

        # Max MIDI note
        max_note = questionary.text(
            "Enter maximum MIDI note (0-127, for high-note filtering):",
            default=str(settings.get("max_midi_note", 84)),
            validate=lambda val: val.strip() == ""
            or (val.strip().isdigit() and 0 <= int(val.strip()) <= 127),
        ).ask()

        if max_note is not None:
            settings["max_midi_note"] = int(max_note)

        return settings

    def configure_pitch_settings(
        self, current_settings: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Interactive pitch detection settings configuration.

        Args:
            current_settings: Current pitch settings

        Returns:
            Updated settings dictionary
        """
        settings = current_settings.copy()

        self.console.print("[bold]Pitch Detection Settings Configuration[/bold]")

        # Frequency range
        min_freq = questionary.text(
            "Enter minimum frequency (Hz):",
            default=str(settings.get("min_freq", 80.0)),
            validate=lambda val: 0 < float(val) < 2000,
        ).ask()

        if min_freq is not None:
            settings["min_freq"] = float(min_freq)

        max_freq = questionary.text(
            "Enter maximum frequency (Hz):",
            default=str(settings.get("max_freq", 800.0)),
            validate=lambda val: float(val) > settings.get("min_freq", 80.0),
        ).ask()

        if max_freq is not None:
            settings["max_freq"] = float(max_freq)

        # Confidence threshold
        confidence = questionary.text(
            "Enter confidence threshold (0.0-1.0):",
            default=str(settings.get("confidence_threshold", 0.8)),
            validate=lambda val: 0.0 <= float(val) <= 1.0,
        ).ask()

        if confidence is not None:
            settings["confidence_threshold"] = float(confidence)

        return settings

    def display_configuration_summary(self, settings: Dict[str, Any]) -> None:
        """
        Display a summary of current configuration.

        Args:
            settings: Configuration settings to display
        """
        panel_content = []

        # Audio settings
        if "audio" in settings:
            audio = settings["audio"]
            panel_content.append("[bold]Audio Settings:[/bold]")
            panel_content.append(f"  Sample Rate: {audio.get('sample_rate', 'N/A')} Hz")
            panel_content.append(
                f"  Chunk Size: {audio.get('chunk_size', 'N/A')} samples"
            )
            panel_content.append(
                f"  Input Device: {audio.get('input_device_name', 'N/A')}"
            )
            panel_content.append("")

        # MIDI settings
        if "midi" in settings:
            midi = settings["midi"]
            panel_content.append("[bold]MIDI Settings:[/bold]")
            panel_content.append(
                f"  Output Port: {midi.get('output_port_name', 'N/A')}"
            )
            panel_content.append(f"  Channel: {midi.get('channel', 'N/A')}")
            panel_content.append(f"  Velocity: {midi.get('velocity', 'N/A')}")
            panel_content.append(
                f"  Transpose: {midi.get('transpose_semitones', 'N/A')} semitones"
            )
            panel_content.append("")

        # Pitch settings
        if "pitch" in settings:
            pitch = settings["pitch"]
            panel_content.append("[bold]Pitch Detection Settings:[/bold]")
            panel_content.append(
                f"  Frequency Range: {pitch.get('min_freq', 'N/A')}-{pitch.get('max_freq', 'N/A')} Hz"
            )
            panel_content.append(
                f"  Confidence Threshold: {pitch.get('confidence_threshold', 'N/A')}"
            )

        if panel_content:
            content = "\n".join(panel_content)
            panel = Panel(
                content,
                title="[bold]Current Configuration[/bold]",
                border_style="green",
            )
            self.console.print(panel)

    def confirm_action(self, message: str, default: bool = True) -> bool:
        """
        Show a confirmation prompt.

        Args:
            message: Confirmation message
            default: Default choice

        Returns:
            True if confirmed, False otherwise
        """
        try:
            return questionary.confirm(message, default=default).ask()
        except (KeyboardInterrupt, EOFError):
            return False

    def display_pedal_learning_prompt(self) -> None:
        """Display instructions for pedal learning."""
        panel_content = [
            "[bold]Pedal Learning Mode[/bold]",
            "",
            "Please follow these steps:",
            "1. Make sure your MIDI pedal is connected",
            "2. Select the pedal's MIDI input port",
            "3. Press your pedal when prompted",
            "4. The app will detect and save the pedal configuration",
            "",
            "[yellow]Note: This is useful for MuseScore's 'Real-time (foot pedal)' mode[/yellow]",
        ]

        content = "\n".join(panel_content)
        panel = Panel(
            content, title="[bold]MIDI Pedal Configuration[/bold]", border_style="cyan"
        )
        self.console.print(panel)

    def display_status(
        self, frequency: float, note_name: str, midi_note: int, confidence: float
    ) -> None:
        """
        Display current status information.

        Args:
            frequency: Current frequency
            note_name: Current note name
            midi_note: Current MIDI note
            confidence: Detection confidence (unused in display)
        """
        status_text = (
            f"[bold cyan]Note:[/bold cyan] {note_name} | "
            f"[bold magenta]MIDI:[/bold magenta] {midi_note} | "
            f"[bold yellow]Frequency:[/bold yellow] {frequency:.1f} Hz"
        )

        # Print status with newline
        self.console.print(status_text)

    def clear_line(self) -> None:
        """Clear the current line."""
        self.console.print("\r" + " " * 80 + "\r", end="")

    def wait_for_interrupt(self) -> None:
        """Display waiting message and wait for keyboard interrupt."""
        try:
            self.console.print("[bold yellow]Press Ctrl+C to stop[/bold yellow]")
            while True:
                import time

                time.sleep(0.1)
        except KeyboardInterrupt:
            self.console.print("\n[bold yellow]Stopping...[/bold yellow]")

    def display_error_panel(self, error: Exception) -> None:
        """
        Display an error in a panel.

        Args:
            error: Exception to display
        """
        error_content = [
            f"[bold red]Error:[/bold red] {type(error).__name__}",
            f"[red]{str(error)}[/red]",
        ]

        if isinstance(error, VoiceToMidiError):
            error_content.append("")
            error_content.append(
                "[yellow]Please check your configuration and try again.[/yellow]"
            )

        content = "\n".join(error_content)
        panel = Panel(content, title="[bold red]Error[/bold red]", border_style="red")
        self.console.print(panel)

    def display_help_panel(self) -> None:
        """Display help information."""
        help_content = [
            "[bold]Available Commands:[/bold]",
            "",
            "[cyan]run[/cyan] - Start the voice-to-MIDI application",
            "[cyan]config[/cyan] - Configure devices and settings",
            "[cyan]list-devices[/cyan] - Show available audio and MIDI devices",
            "[cyan]show-config[/cyan] - Display current configuration",
            "[cyan]reset-config[/cyan] - Reset configuration to defaults",
            "",
            "[bold]Common Options:[/bold]",
            "[yellow]-c, --choose-devices[/yellow] - Force device selection",
            "[yellow]-t, --transpose[/yellow] - Transpose output in semitones",
            "[yellow]--min-freq[/yellow] - Set minimum frequency for detection",
            "[yellow]--chunk-size[/yellow] - Set audio chunk size",
            "",
            "[bold]For more help:[/bold]",
            "Use [cyan]voice-to-midi COMMAND --help[/cyan] for command-specific help",
        ]

        content = "\n".join(help_content)
        panel = Panel(
            content, title="[bold]Voice to MIDI Help[/bold]", border_style="blue"
        )
        self.console.print(panel)
