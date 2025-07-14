"""
CLI commands for the Voice to MIDI application.

This module defines all CLI commands using Click with enhanced error handling,
validation, and user interaction through Rich interfaces.
"""

import logging
import sys
from typing import Optional
import click
from rich.console import Console

from ..core.application import VoiceToMidiApp
from ..core.exceptions import VoiceToMidiError, ConfigError
from ..config import ConfigManager
from ..devices.audio_devices import AudioDeviceManager
from ..devices.midi_devices import MidiDeviceManager
from ..audio.capture import AudioCapture
from ..audio.processor import AudioProcessor
from ..pitch.detector import PitchDetector
from ..midi.output import MidiOutput
from .interface import CLIInterface


logger = logging.getLogger(__name__)
console = Console()


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
@click.version_option(version="0.2.0")
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose logging")
def cli(verbose):
    """
    🎤 Voice to MIDI Translator 🎹
    
    Real-time voice-to-MIDI conversion with beautiful CLI interface.
    
    This application captures audio from your microphone, detects pitch in real-time,
    and converts it to MIDI notes that can be sent to any MIDI-compatible software.
    
    Examples:
        voice-to-midi run                    # Start with saved settings
        voice-to-midi run -c                 # Force device selection
        voice-to-midi config                 # Configure devices and settings
        voice-to-midi list-devices           # Show available devices
    """
    # Configure logging
    from ..utils.helpers import setup_logging
    level = "DEBUG" if verbose else "INFO"
    setup_logging(level)
    
    logger.info("Voice to MIDI application starting")


@cli.command("run")
@click.option("-c", "--choose-devices", is_flag=True, 
              help="Force device selection at startup")
@click.option("-t", "--transpose", type=int, 
              help="Transpose output in semitones (e.g., -12 for one octave down)")
@click.option("--min-freq", type=float,
              help="Minimum frequency for pitch detection (Hz)")
@click.option("--max-freq", type=float,
              help="Maximum frequency for pitch detection (Hz)")
@click.option("--chunk-size", type=click.Choice(["512", "1024", "2048", "4096"]),
              help="Audio chunk size (affects latency and frequency resolution)")
@click.option("--confidence", type=float,
              help="Confidence threshold for pitch detection (0.0-1.0)")
@click.option("--config-path", type=click.Path(),
              help="Path to configuration file")
def run_app(choose_devices, transpose, min_freq, max_freq, chunk_size, 
            confidence, config_path):
    """
    Start the Voice to MIDI application.
    
    This command starts the real-time voice-to-MIDI conversion process.
    If you have saved settings, the app will start with those settings.
    Use -c/--choose-devices to force device selection.
    
    Examples:
        voice-to-midi run                    # Start with saved settings
        voice-to-midi run -c                 # Force device selection
        voice-to-midi run -t -12             # Transpose down one octave
        voice-to-midi run --chunk-size 2048  # Use larger chunk size
    """
    cli_interface = CLIInterface()
    
    try:
        # Create and configure application
        app = VoiceToMidiApp(config_path)
        
        # Load configuration
        try:
            settings = app.load_config()
        except ConfigError as e:
            cli_interface.display_error(f"Configuration error: {e}")
            sys.exit(1)
        
        # Override settings with command line options
        if transpose is not None:
            settings.midi.transpose_semitones = transpose
        if min_freq is not None:
            settings.pitch.min_freq = min_freq
        if max_freq is not None:
            settings.pitch.max_freq = max_freq
        if chunk_size is not None:
            settings.audio.chunk_size = int(chunk_size)
        if confidence is not None:
            settings.pitch.confidence_threshold = confidence
        
        # Create and inject dependencies
        audio_device_manager = AudioDeviceManager()
        midi_device_manager = MidiDeviceManager()
        audio_capture = AudioCapture()
        audio_processor = AudioProcessor()
        pitch_detector = PitchDetector()
        midi_output = MidiOutput()
        
        app.inject_dependencies(
            audio_device_manager=audio_device_manager,
            midi_device_manager=midi_device_manager,
            audio_capture=audio_capture,
            audio_processor=audio_processor,
            pitch_detector=pitch_detector,
            midi_output=midi_output
        )
        
        # Configure devices
        try:
            if choose_devices or not app.is_configured:
                cli_interface.display_header(
                    "Voice to MIDI Translator",
                    "Configure your audio and MIDI devices"
                )
                
                # Select audio device
                audio_devices = audio_device_manager.list_input_devices()
                audio_device = cli_interface.select_audio_device(audio_devices)
                if not audio_device:
                    cli_interface.display_error("Audio device selection cancelled")
                    sys.exit(1)
                
                settings.audio.input_device_index = audio_device.index
                settings.audio.input_device_name = audio_device.name
                
                # Select MIDI port
                midi_ports = midi_device_manager.list_output_ports()
                midi_port = cli_interface.select_midi_port(midi_ports)
                if not midi_port:
                    cli_interface.display_error("MIDI port selection cancelled")
                    sys.exit(1)
                
                settings.midi.output_port_index = midi_port.index
                settings.midi.output_port_name = midi_port.name
                
                # Save configuration
                app.save_config()
                cli_interface.display_success("Configuration saved")
            else:
                cli_interface.display_info(f"Using audio device: {settings.audio.input_device_name}")
                cli_interface.display_info(f"Using MIDI port: {settings.midi.output_port_name}")
                
        except Exception as e:
            cli_interface.display_error(f"Device configuration failed: {e}")
            sys.exit(1)
        
        # Display settings
        cli_interface.display_configuration_summary(settings.to_dict())
        
        # Set up event handlers
        def on_note_change(note, frequency, confidence):
            from ..utils.helpers import midi_note_to_name
            note_name = midi_note_to_name(note) if note else "None"
            cli_interface.display_status(frequency, note_name, note or 0, confidence)
        
        def on_error(error):
            cli_interface.display_error_panel(error)
        
        app.on_note_change = on_note_change
        app.on_error = on_error
        
        # Start the application
        cli_interface.display_header("Starting Voice to MIDI Conversion")
        cli_interface.display_info("Speak or sing into your microphone...")
        
        app.run()
        
    except KeyboardInterrupt:
        cli_interface.display_info("Application stopped by user")
    except VoiceToMidiError as e:
        cli_interface.display_error_panel(e)
        sys.exit(1)
    except Exception as e:
        cli_interface.display_error(f"Unexpected error: {e}")
        logger.exception("Unexpected error in run command")
        sys.exit(1)
    finally:
        # Clean up
        try:
            if 'audio_device_manager' in locals():
                audio_device_manager.close()
            if 'midi_device_manager' in locals():
                midi_device_manager.close()
        except:
            pass


@cli.command("config")
@click.option("--pedal", is_flag=True, help="Configure MIDI pedal")
@click.option("--audio", is_flag=True, help="Configure audio settings")
@click.option("--midi", is_flag=True, help="Configure MIDI settings")
@click.option("--pitch", is_flag=True, help="Configure pitch detection settings")
@click.option("--config-path", type=click.Path(),
              help="Path to configuration file")
def config_command(pedal, audio, midi, pitch, config_path):
    """
    Configure devices and settings.
    
    This command allows you to interactively configure your audio input device,
    MIDI output port, and various settings. You can also configure a MIDI pedal
    for real-time note control.
    
    Examples:
        voice-to-midi config           # Configure all settings
        voice-to-midi config --pedal   # Configure MIDI pedal only
        voice-to-midi config --audio   # Configure audio settings only
    """
    cli_interface = CLIInterface()
    
    try:
        # Create configuration manager
        config_manager = ConfigManager(config_path)
        
        # Load current configuration
        try:
            settings = config_manager.load()
        except ConfigError as e:
            cli_interface.display_warning(f"Configuration error: {e}")
            settings = config_manager.get_settings()
        
        # Create device managers
        audio_device_manager = AudioDeviceManager()
        midi_device_manager = MidiDeviceManager()
        
        cli_interface.display_header("Voice to MIDI Configuration")
        
        # Configure devices if not specific section requested
        if not any([pedal, audio, midi, pitch]):
            # Configure audio device
            audio_devices = audio_device_manager.list_input_devices()
            audio_device = cli_interface.select_audio_device(audio_devices)
            if audio_device:
                settings.audio.input_device_index = audio_device.index
                settings.audio.input_device_name = audio_device.name
                cli_interface.display_success(f"Audio device set to: {audio_device.name}")
            
            # Configure MIDI port
            midi_ports = midi_device_manager.list_output_ports()
            midi_port = cli_interface.select_midi_port(midi_ports)
            if midi_port:
                settings.midi.output_port_index = midi_port.index
                settings.midi.output_port_name = midi_port.name
                cli_interface.display_success(f"MIDI port set to: {midi_port.name}")
        
        # Configure specific sections
        if audio or not any([pedal, midi, pitch]):
            audio_settings = cli_interface.configure_audio_settings(settings.audio.__dict__)
            for key, value in audio_settings.items():
                if hasattr(settings.audio, key):
                    setattr(settings.audio, key, value)
            cli_interface.display_success("Audio settings updated")
        
        if midi or not any([pedal, audio, pitch]):
            midi_settings = cli_interface.configure_midi_settings(settings.midi.__dict__)
            for key, value in midi_settings.items():
                if hasattr(settings.midi, key):
                    setattr(settings.midi, key, value)
            cli_interface.display_success("MIDI settings updated")
        
        if pitch or not any([pedal, audio, midi]):
            pitch_settings = cli_interface.configure_pitch_settings(settings.pitch.__dict__)
            for key, value in pitch_settings.items():
                if hasattr(settings.pitch, key):
                    setattr(settings.pitch, key, value)
            cli_interface.display_success("Pitch detection settings updated")
        
        if pedal:
            cli_interface.display_pedal_learning_prompt()
            # TODO: Implement pedal learning
            cli_interface.display_info("Pedal configuration not yet implemented")
        
        # Save configuration
        config_manager.save()
        cli_interface.display_success("Configuration saved successfully")
        
        # Display summary
        cli_interface.display_configuration_summary(settings.to_dict())
        
    except Exception as e:
        cli_interface.display_error_panel(e)
        logger.exception("Error in config command")
        sys.exit(1)
    finally:
        # Clean up
        try:
            if 'audio_device_manager' in locals():
                audio_device_manager.close()
            if 'midi_device_manager' in locals():
                midi_device_manager.close()
        except:
            pass


@cli.command("list-devices")
def list_devices():
    """
    Show available audio and MIDI devices.
    
    This command displays all available audio input devices and MIDI output ports
    on your system. Use this to see what devices are available for configuration.
    """
    cli_interface = CLIInterface()
    
    try:
        # Create device managers
        audio_device_manager = AudioDeviceManager()
        midi_device_manager = MidiDeviceManager()
        
        cli_interface.display_header("Available Devices")
        
        # Display audio devices
        audio_devices = audio_device_manager.list_input_devices()
        cli_interface.display_audio_devices(audio_devices)
        
        console.print()
        
        # Display MIDI ports
        midi_ports = midi_device_manager.list_output_ports()
        cli_interface.display_midi_ports(midi_ports)
        
    except Exception as e:
        cli_interface.display_error_panel(e)
        logger.exception("Error in list-devices command")
        sys.exit(1)
    finally:
        # Clean up
        try:
            if 'audio_device_manager' in locals():
                audio_device_manager.close()
            if 'midi_device_manager' in locals():
                midi_device_manager.close()
        except:
            pass


@cli.command("show-config")
@click.option("--config-path", type=click.Path(),
              help="Path to configuration file")
def show_config(config_path):
    """
    Display current configuration.
    
    This command shows your current saved configuration including device
    selections, audio settings, MIDI settings, and pitch detection parameters.
    """
    cli_interface = CLIInterface()
    
    try:
        config_manager = ConfigManager(config_path)
        
        if not config_manager.config_exists:
            cli_interface.display_warning("No configuration file found")
            return
        
        settings = config_manager.load()
        cli_interface.display_configuration_summary(settings.to_dict())
        
    except Exception as e:
        cli_interface.display_error_panel(e)
        logger.exception("Error in show-config command")
        sys.exit(1)


@cli.command("reset-config")
@click.option("--config-path", type=click.Path(),
              help="Path to configuration file")
def reset_config(config_path):
    """
    Reset configuration to defaults.
    
    This command deletes your saved configuration file, forcing the application
    to use default settings and prompting for device selection on next run.
    """
    cli_interface = CLIInterface()
    
    try:
        config_manager = ConfigManager(config_path)
        
        if not config_manager.config_exists:
            cli_interface.display_warning("No configuration file found")
            return
        
        if cli_interface.confirm_action("Are you sure you want to reset the configuration?"):
            config_manager.delete_config_file()
            cli_interface.display_success("Configuration reset successfully")
            cli_interface.display_info("You will be prompted to select devices on next run")
        else:
            cli_interface.display_info("Configuration reset cancelled")
            
    except Exception as e:
        cli_interface.display_error_panel(e)
        logger.exception("Error in reset-config command")
        sys.exit(1)


@cli.command("help")
def help_command():
    """
    Show detailed help information.
    
    This command provides comprehensive help information about using the
    Voice to MIDI application, including examples and troubleshooting tips.
    """
    cli_interface = CLIInterface()
    cli_interface.display_help_panel()


if __name__ == "__main__":
    cli()