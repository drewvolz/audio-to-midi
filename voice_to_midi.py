#!/usr/bin/env python3
"""
Real-time Voice to MIDI Translator

This application captures audio from your microphone, detects pitch in real-time,
and converts it to MIDI notes that can be sent to any MIDI-compatible software or hardware.
"""

import sys
import click
from rich.console import Console
from rich.prompt import Prompt, IntPrompt
from rich.table import Table
from rich.panel import Panel
from rich import box
import questionary
import mido

# --- System Dependency Check ---
missing = []
try:
    import tkinter as tk
except ImportError:
    missing.append('tkinter')
try:
    import pyaudio
except ImportError:
    missing.append('pyaudio')

if missing:
    print("\nERROR: The following required Python modules could not be imported:")
    for m in missing:
        print(f"  - {m}")
    print("\nThis usually means you are missing system libraries (PortAudio and/or Tcl/Tk).\n")
    print("To fix this, install the required system libraries for your OS:")
    print("\nmacOS:")
    print("  brew install portaudio tcl-tk")
    print("\nUbuntu/Debian:")
    print("  sudo apt-get update")
    print("  sudo apt-get install portaudio19-dev tk-dev")
    print("\nFedora:")
    print("  sudo dnf install portaudio-devel tk-devel")
    print("\nAfter installing, re-run your command.")
    sys.exit(1)

import numpy as np
import librosa
import mido
import threading
import time
import queue
import scipy.signal as signal
from collections import deque
import logging
import os
import json
import pyaudio
# Remove: import sounddevice as sd

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

CONFIG_PATH = os.path.expanduser("~/.voice_to_midi_config.json")

def load_config():
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, 'r') as f:
                config = json.load(f)
                config.setdefault('max_midi_note', 84)
                return config
        except Exception:
            return {}
    return {}

def save_config(audio_index, midi_index, transpose, min_freq, chunk_size, audio_name=None, midi_name=None, pedal_port=None, pedal_message=None, max_midi_note=84):
    try:
        with open(CONFIG_PATH, 'w') as f:
            json.dump({
                'audio_index': audio_index,
                'audio_name': audio_name,
                'midi_index': midi_index,
                'midi_name': midi_name,
                'transpose': transpose,
                'min_freq': min_freq,
                'chunk_size': chunk_size,
                'pedal_port': pedal_port,
                'pedal_message': pedal_message,
                'max_midi_note': max_midi_note,
            }, f)
    except Exception:
        pass

def learn_pedal():
    # List MIDI input ports
    in_ports = mido.get_input_names()
    if not in_ports:
        click.secho("No MIDI input ports found for pedal.", fg="red")
        return None, None
    pedal_port = questionary.select(
        "Select your pedal's MIDI input port:",
        choices=[questionary.Choice(p, value=p) for p in in_ports],
        default=in_ports[0] if in_ports else None
    ).ask()
    if pedal_port is None:
        click.secho("Pedal port selection cancelled.", fg="yellow")
        return None, None
    click.secho("Press your pedal now to configure it...", fg="cyan")
    with mido.open_input(pedal_port) as port:
        msg = port.receive()
        click.secho(f"Detected pedal message: {msg.type} {getattr(msg, 'note', getattr(msg, 'control', ''))}", fg="green")
        # Save only the relevant info
        pedal_message = {
            'type': msg.type,
            'note': getattr(msg, 'note', None),
            'control': getattr(msg, 'control', None),
            'value': getattr(msg, 'value', None)
        }
        return pedal_port, pedal_message

class VoiceToMidi:
    console = Console()

    def __init__(self, force_choose_devices=False, transpose_semitones=None, min_freq=None, chunk_size=None):
        self.audio = pyaudio.PyAudio()
        self.midi_out = None
        self.is_running = False
        self.audio_queue = queue.Queue()
        self.midi_queue = queue.Queue()
        
        # Audio settings
        self.sample_rate = 44100
        self.chunk_size = 1024
        self.channels = 1
        self.input_device_index = None
        self.input_device_name = None
        self.midi_port_index = None
        self.midi_port_name = None
        
        # Pitch detection settings
        self.min_freq = 80  # Hz
        self.max_freq = 800  # Hz
        self.confidence_threshold = 0.8
        self.silence_threshold = 0.01
        
        # MIDI settings
        self.midi_channel = 0
        self.current_note = None
        self.note_velocity = 64
        self.transpose_semitones = 0
        
        # Display settings
        self.current_note_name = "None"
        self.current_frequency = 0.0
        self.current_midi_note = None
        
        # --- New: Debounce and smoothing thresholds ---
        self.min_semitone_diff = 1
        self.debounce_time = 0.08
        self.min_note_duration = 0.08
        self.silence_release_time = 0.1
        
        # Load config
        self.config = load_config()
        self.force_choose_devices = force_choose_devices
        # Set from config or CLI
        if transpose_semitones is not None:
            self.transpose_semitones = transpose_semitones
        elif 'transpose' in self.config:
            self.transpose_semitones = self.config['transpose']
        if min_freq is not None:
            self.min_freq = min_freq
        elif 'min_freq' in self.config:
            self.min_freq = self.config['min_freq']
        if chunk_size is not None:
            self.chunk_size = chunk_size
        elif 'chunk_size' in self.config:
            self.chunk_size = self.config['chunk_size']
        self.max_midi_note = self.config.get('max_midi_note', 84)

    def list_midi_ports(self, show_table=True):
        """List available MIDI output ports"""
        ports = mido.get_output_names()
        if not ports:
            self.console.print("[bold red]No MIDI output ports available[/bold red]")
            return None
        if show_table:
            table = Table(title="Available MIDI Output Ports", box=box.ROUNDED)
            table.add_column("Index", style="cyan", justify="right")
            table.add_column("Port Name", style="green")
            for i, port in enumerate(ports):
                table.add_row(str(i), port)
            self.console.print(table)
        return ports
    
    def select_midi_port(self, force_select=False):
        force_select = force_select or self.force_choose_devices
        ports = self.list_midi_ports(show_table=force_select)
        if not ports:
            return None
        config_name = self.config.get('midi_name')
        config_index = self.config.get('midi_index')
        # Try to use config by name first, then index
        if not force_select:
            idx = None
            if config_name and config_name in ports:
                idx = ports.index(config_name)
            elif config_index is not None and 0 <= config_index < len(ports):
                idx = config_index
            if idx is not None:
                name = ports[idx]
                self.midi_port_index = idx
                self.midi_port_name = name
                return name  # Silent, no prompt
        if len(ports) == 1:
            self.console.print(f"[bold green]Only one MIDI port found. Using:[/bold green] {ports[0]}")
            self.midi_port_index = 0
            self.midi_port_name = ports[0]
            return ports[0]
        # Interactive selection with questionary
        choices = [questionary.Choice(f"{i}: {port}", value=i) for i, port in enumerate(ports)]
        idx = questionary.select(
            "Select MIDI output port:",
            choices=choices,
            default=0
        ).ask()
        if idx is None:
            self.console.print("\n[bold yellow]Exiting...[/bold yellow]")
            return None
        self.midi_port_index = idx
        self.midi_port_name = ports[idx]
        return ports[idx]
    
    def select_microphone(self, force_select=False):
        force_select = force_select or self.force_choose_devices
        info = self.audio.get_host_api_info_by_index(0)
        num_devices = info.get('deviceCount')
        input_devices = []
        for i in range(num_devices):
            dev = self.audio.get_device_info_by_host_api_device_index(0, i)
            if dev.get('maxInputChannels') > 0:
                input_devices.append((i, dev.get('name')))
        if not input_devices:
            self.console.print("[bold red]No audio input devices found![/bold red]")
            sys.exit(1)
        config_name = self.config.get('audio_name')
        config_index = self.config.get('audio_index')
        # Try to use config by name first, then index
        if not force_select:
            idx = None
            names = [name for _, name in input_devices]
            if config_name and config_name in names:
                idx = names.index(config_name)
            elif config_index is not None and 0 <= config_index < len(input_devices):
                idx = config_index
            if idx is not None:
                name = input_devices[idx][1]
                self.input_device_index = input_devices[idx][0]
                self.input_device_name = name
                return  # Silent, no prompt
        if force_select:
            table = Table(title="Available Audio Input Devices", box=box.ROUNDED)
            table.add_column("Index", style="cyan", justify="right")
            table.add_column("Device Name", style="green")
            for idx, (i, name) in enumerate(input_devices):
                table.add_row(str(idx), name)
            self.console.print(table)
        # Interactive selection with questionary
        choices = [questionary.Choice(f"{idx}: {name}", value=idx) for idx, (i, name) in enumerate(input_devices)]
        idx = questionary.select(
            "Select audio input device:",
            choices=choices,
            default=0
        ).ask()
        if idx is None:
            self.console.print("\n[bold yellow]Exiting...[/bold yellow]")
            sys.exit(1)
        self.input_device_index = input_devices[idx][0]
        self.input_device_name = input_devices[idx][1]

    def start_processing(self, midi_port_name=None):
        """Start the audio processing and MIDI generation"""
        if not midi_port_name:
            midi_port_name = self.select_midi_port()
            
        if not midi_port_name:
            return False
            
        try:
            self.midi_out = mido.open_output(midi_port_name)
            self.is_running = True
            
            self.console.print(f"[bold green]Connected to MIDI port:[/bold green] {midi_port_name}")
            self.console.print("[bold yellow]Press Ctrl+C to stop[/bold yellow]")
            
            # Start audio capture thread
            self.audio_thread = threading.Thread(target=self.audio_capture, daemon=True)
            self.audio_thread.start()
            
            # Start MIDI processing thread
            self.midi_thread = threading.Thread(target=self.midi_processor, daemon=True)
            self.midi_thread.start()
            
            # Start display thread
            self.display_thread = threading.Thread(target=self.update_display, daemon=True)
            self.display_thread.start()
            
            logger.info("Started voice-to-MIDI processing")
            return True
            
        except Exception as e:
            self.console.print(f"[bold red]Failed to start processing:[/bold red] {str(e)}")
            logger.error(f"Failed to start processing: {e}")
            return False
            
    def stop_processing(self):
        """Stop the audio processing and MIDI generation"""
        self.is_running = False
        
        if self.midi_out:
            # Send note off for current note
            if self.current_note is not None:
                self.midi_out.send(mido.Message('note_off', note=self.current_note, 
                                              channel=self.midi_channel))
                self.current_note = None
            
            self.midi_out.close()
            self.midi_out = None
        
        logger.info("Stopped voice-to-MIDI processing")
        
    def audio_capture(self):
        """Capture audio from microphone using pyaudio"""
        try:
            stream = self.audio.open(
                format=pyaudio.paFloat32,
                channels=self.channels,
                rate=self.sample_rate,
                input=True,
                frames_per_buffer=self.chunk_size,
                input_device_index=self.input_device_index
            )
            
            logger.info("Audio capture started")
            
            while self.is_running:
                try:
                    data = stream.read(self.chunk_size, exception_on_overflow=False)
                    audio_data = np.frombuffer(data, dtype=np.float32)
                    self.audio_queue.put(audio_data)
                except Exception as e:
                    logger.error(f"Audio capture error: {e}")
                    break
            
            stream.stop_stream()
            stream.close()
            logger.info("Audio capture stopped")
            
        except Exception as e:
            logger.error(f"Failed to start audio capture: {e}")
            
    def detect_pitch(self, audio_data):
        """Detect pitch from audio data using autocorrelation, with octave correction"""
        # Apply window function
        window = np.hanning(len(audio_data))
        audio_data = audio_data * window
        
        # Check if audio is above silence threshold
        if np.max(np.abs(audio_data)) < self.silence_threshold:
            return None, 0.0
        
        # Autocorrelation for pitch detection
        autocorr = np.correlate(audio_data, audio_data, mode='full')
        autocorr = autocorr[len(autocorr)//2:]
        
        # Find peaks in autocorrelation
        peaks, properties = signal.find_peaks(autocorr, height=np.max(autocorr) * 0.1)
        if len(peaks) == 0:
            return None, 0.0
        
        # Find the first significant peak (fundamental frequency)
        for peak in peaks:
            if peak > 0:
                freq = self.sample_rate / peak
                if self.min_freq <= freq <= self.max_freq:
                    # Octave correction: check if a peak at half the lag (double freq) is also strong
                    half_peak = int(peak / 2)
                    if half_peak > 0 and half_peak in peaks:
                        freq2 = self.sample_rate / half_peak
                        if self.min_freq <= freq2 <= self.max_freq:
                            # Compare peak heights
                            if autocorr[half_peak] > 0.8 * autocorr[peak]:
                                # Prefer the higher-frequency (true) pitch
                                confidence = autocorr[half_peak] / np.max(autocorr)
                                return freq2, confidence
                    # Calculate confidence based on peak height
                    confidence = autocorr[peak] / np.max(autocorr)
                    return freq, confidence
        return None, 0.0
        
    def freq_to_midi_note(self, frequency):
        """Convert frequency to MIDI note number, with transpose"""
        if frequency <= 0:
            return None
        midi_note = int(round(12 * np.log2(frequency / 440) + 69 + 12))  # Add 12 to fix octave
        midi_note += self.transpose_semitones
        return midi_note
        
    def midi_note_to_name(self, note_number):
        """Convert MIDI note number to note name"""
        if note_number is None:
            return "None"
        note_names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
        octave = (note_number // 12) - 1
        note_name = note_names[note_number % 12]
        return f"{note_name}{octave}"
        
    def midi_processor(self):
        """Process audio data and generate MIDI notes with debounce and smoothing"""
        logger.info("MIDI processor started")
        
        last_note = None
        last_note_time = 0
        last_pitch = None
        last_pitch_time = 0
        note_on_time = 0
        silence_start_time = None
        last_confidence = 0
        stable_pitch = None
        stable_pitch_time = 0
        
        while self.is_running:
            try:
                audio_data = self.audio_queue.get(timeout=0.1)
                now = time.time()
                frequency, confidence = self.detect_pitch(audio_data)
                
                # Silence detection
                if frequency is None or confidence < self.confidence_threshold:
                    if self.current_note is not None:
                        if silence_start_time is None:
                            silence_start_time = now
                        elif now - silence_start_time >= self.silence_release_time:
                            self.midi_out.send(mido.Message('note_off', note=self.current_note, channel=self.midi_channel))
                            self.current_note = None
                            self.midi_queue.put({
                                'note': None,
                                'note_name': "None",
                                'frequency': 0,
                                'confidence': 0
                            })
                    continue
                else:
                    silence_start_time = None
                
                midi_note = self.freq_to_midi_note(frequency)
                
                # Debounce: Only trigger if pitch is stable for debounce_time and differs by min_semitone_diff
                if last_pitch is None or abs(midi_note - last_pitch) >= self.min_semitone_diff:
                    stable_pitch = midi_note
                    stable_pitch_time = now
                elif midi_note == stable_pitch and (now - stable_pitch_time) >= self.debounce_time:
                    # Only send note if it's different from the current note and held for min_note_duration
                    if (self.current_note is None or midi_note != self.current_note) and (now - stable_pitch_time) >= self.min_note_duration:
                        # Send note off for previous note
                        if self.current_note is not None:
                            self.midi_out.send(mido.Message('note_off', note=self.current_note, channel=self.midi_channel))
                        # Send note on for new note
                        self.current_note = midi_note
                        self.midi_out.send(mido.Message('note_on', note=midi_note, velocity=self.note_velocity, channel=self.midi_channel))
                        self.midi_queue.put({
                            'note': midi_note,
                            'note_name': self.midi_note_to_name(midi_note),
                            'frequency': frequency,
                            'confidence': confidence
                        })
                        note_on_time = now
                last_pitch = midi_note
                last_pitch_time = now
                
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"MIDI processing error: {e}")
                break
        logger.info("MIDI processor stopped")
        
    def update_display(self):
        """Update display with current note and frequency and debug info"""
        while self.is_running:
            try:
                # Get latest MIDI data
                midi_data = self.midi_queue.get_nowait()
                
                # Update display variables
                self.current_note_name = midi_data['note_name']
                self.current_frequency = midi_data['frequency']
                self.current_midi_note = midi_data['note']
                
                # Debug print: frequency and MIDI note (with newline)
                self.console.print(f"[bold cyan]Current Note:[/bold cyan] {self.current_note_name} | [bold magenta]MIDI:[/bold magenta] {self.current_midi_note} | [bold yellow]Frequency:[/bold yellow] {self.current_frequency:.1f} Hz", style="bold")
                # Warn if MIDI note is outside typical vocal range
                if self.current_midi_note is not None and (self.current_midi_note < 48 or self.current_midi_note > self.max_midi_note):
                    self.console.print("[yellow]Warning: Detected MIDI note is outside a typical vocal range. If you have to sing an octave higher or lower, try using the [bold]-t/--transpose[/bold] option (e.g. -t -12 for one octave down).[/yellow]")
                
            except queue.Empty:
                pass
            time.sleep(0.1)  # Update 10 times per second
        
    def get_selected_audio_index(self):
        # Find the index in the filtered list for config persistence
        info = self.audio.get_host_api_info_by_index(0)
        num_devices = info.get('deviceCount')
        input_devices = []
        for i in range(num_devices):
            dev = self.audio.get_device_info_by_host_api_device_index(0, i)
            if dev.get('maxInputChannels') > 0:
                input_devices.append((i, dev.get('name')))
        for idx, (i, name) in enumerate(input_devices):
            if i == self.input_device_index:
                return idx
        return 0

    def run(self, midi_port=None):
        """Run the application (invoked by Click)"""
        try:
            self.console.print(f"[bold magenta]Transpose:[/bold magenta] {self.transpose_semitones} semitones")
            self.console.print(f"[bold magenta]Min frequency:[/bold magenta] {self.min_freq} Hz")
            self.console.print(f"[bold magenta]Chunk size:[/bold magenta] {self.chunk_size}")
            self.console.print()
            if self.input_device_index is not None and self.midi_port_index is not None:
                save_config(
                    audio_index=self.get_selected_audio_index(),
                    midi_index=self.midi_port_index,
                    transpose=self.transpose_semitones,
                    min_freq=self.min_freq,
                    chunk_size=self.chunk_size,
                    audio_name=self.input_device_name,
                    midi_name=self.midi_port_name,
                    max_midi_note=self.max_midi_note
                )
            if not self.start_processing(midi_port):
                return
            while self.is_running:
                time.sleep(0.1)
        except KeyboardInterrupt:
            self.console.print("\n[bold yellow]Stopping...[/bold yellow]")
            self.stop_processing()

def main():
    """Main entry point with Click CLI"""
    cli()

@click.group(context_settings={"help_option_names": ["-h", "--help"]})
@click.version_option('0.0.1')
def cli():
    """
    🎤 Voice to MIDI Translator 🎹
    
    Real-time voice-to-MIDI conversion with beautiful CLI and GUI.
    """
    pass

@cli.command("run", short_help="Start the Voice to MIDI app")
@click.option("-c", "--choose-devices", is_flag=True, help="Choose audio and MIDI devices at startup")
@click.option("-t", "--transpose", type=int, default=None, help="Transpose output in semitones (e.g. -12 for one octave down)")
@click.option("--min-freq", type=int, default=None, help="Minimum frequency for pitch detection (Hz, e.g. 50)")
@click.option("--chunk-size", type=int, default=None, help="Audio chunk size (e.g. 1024, 2048, 4096)")
def run_app(choose_devices, transpose, min_freq, chunk_size):
    """Start the Voice to MIDI app with optional device/config selection."""
    app = VoiceToMidi(force_choose_devices=choose_devices, transpose_semitones=transpose, min_freq=min_freq, chunk_size=chunk_size)
    # Only prompt for device selection if -c or config is missing/incomplete
    config = app.config
    config_ok = (
        config.get('audio_name') is not None and
        config.get('midi_name') is not None and
        config.get('audio_index') is not None and
        config.get('midi_index') is not None
    )
    if not choose_devices and config_ok:
        # Use config silently
        app.input_device_index = None  # Will be set in select_microphone
        app.midi_port_index = None     # Will be set in select_midi_port
        app.input_device_name = config['audio_name']
        app.midi_port_name = config['midi_name']
        app.force_choose_devices = False
        # Select devices by config, but don't prompt
        app.select_microphone(force_select=False)
        midi_port = app.select_midi_port(force_select=False)
        # Show the selected input and output to the user
        click.secho(f"Using input: {app.input_device_name}", fg="green")
        click.secho(f"Using MIDI output: {app.midi_port_name}", fg="green")
    else:
        click.secho("\nVoice to MIDI Translator", fg="cyan", bold=True)
        click.secho("=" * 30, fg="cyan")
        click.secho("This application captures your voice and converts it to MIDI notes in real-time.", fg="white")
        click.secho("Make sure you have a microphone connected and MIDI output configured.\n", fg="white")
        app.force_choose_devices = True
        app.select_microphone(force_select=True)
        midi_port = app.select_midi_port(force_select=True)
    if app.input_device_index is not None and app.midi_port_index is not None:
        save_config(
            audio_index=app.get_selected_audio_index(),
            midi_index=app.midi_port_index,
            transpose=app.transpose_semitones,
            min_freq=app.min_freq,
            chunk_size=app.chunk_size,
            audio_name=app.input_device_name,
            midi_name=app.midi_port_name,
            max_midi_note=app.max_midi_note
        )
    app.run(midi_port=midi_port)

@cli.command("config", short_help="Interactively choose and save devices/settings, including pedal setup")
@click.option("-t", "--transpose", type=int, default=None, help="Transpose output in semitones (e.g. -12 for one octave down)")
@click.option("--min-freq", type=int, default=None, help="Minimum frequency for pitch detection (Hz, e.g. 50)")
@click.option("--chunk-size", type=int, default=None, help="Audio chunk size (e.g. 1024, 2048, 4096)")
@click.option("--pedal", is_flag=True, help="Configure a MIDI pedal for note duration control")
@click.option('--max-midi-note', type=int, default=None, help='Maximum MIDI note to allow (high-note gate, e.g. 84 for C6)')
def config_cmd(transpose, min_freq, chunk_size, pedal, max_midi_note):
    """
    Interactively choose and save your audio input, MIDI output, and pedal settings.
    
    Use this command to:
    - Change your audio or MIDI devices
    - Configure or re-learn a MIDI pedal for real-time note duration control (e.g., for MuseScore's "Real-time (foot pedal)" mode)
    - Adjust transpose, minimum frequency, or chunk size
    - Set the maximum MIDI note allowed (high-note gate, e.g. 84 for C6)
    
    Run this command and follow the prompts to update your configuration.
    """
    click.secho("\n[Config] Choose your audio and MIDI devices and settings:", fg="cyan", bold=True)
    app = VoiceToMidi(force_choose_devices=True, transpose_semitones=transpose, min_freq=min_freq, chunk_size=chunk_size)
    # Use saved indices as defaults if available
    audio_default = app.config.get('audio_index', 0)
    midi_default = app.config.get('midi_index', 0)
    # Patch select_microphone and select_midi_port to accept a default index
    def select_microphone_with_default(self, force_select=False, default_index=0):
        force_select = force_select or self.force_choose_devices
        info = self.audio.get_host_api_info_by_index(0)
        num_devices = info.get('deviceCount')
        input_devices = []
        for i in range(num_devices):
            dev = self.audio.get_device_info_by_host_api_device_index(0, i)
            if dev.get('maxInputChannels') > 0:
                input_devices.append((i, dev.get('name')))
        if not input_devices:
            self.console.print("[bold red]No audio input devices found![/bold red]")
            sys.exit(1)
        if force_select:
            table = Table(title="Available Audio Input Devices", box=box.ROUNDED)
            table.add_column("Index", style="cyan", justify="right")
            table.add_column("Device Name", style="green")
            for idx, (i, name) in enumerate(input_devices):
                table.add_row(str(idx), name)
            self.console.print(table)
            choices = [questionary.Choice(f"{idx}: {name}", value=idx) for idx, (i, name) in enumerate(input_devices)]
            idx = questionary.select(
                "Select audio input device:",
                choices=choices,
                default=default_index if 0 <= default_index < len(choices) else 0
            ).ask()
            if idx is None:
                self.console.print("\n[bold yellow]Exiting...[/bold yellow]")
                sys.exit(1)
            self.input_device_index = input_devices[idx][0]
            self.input_device_name = input_devices[idx][1]
            return
        # fallback to original logic for silent mode
        config_name = self.config.get('audio_name')
        config_index = self.config.get('audio_index')
        idx = None
        names = [name for _, name in input_devices]
        if config_name and config_name in names:
            idx = names.index(config_name)
        elif config_index is not None and 0 <= config_index < len(input_devices):
            idx = config_index
        if idx is not None:
            name = input_devices[idx][1]
            self.input_device_index = input_devices[idx][0]
            self.input_device_name = name
            return
    def select_midi_port_with_default(self, force_select=False, default_index=0):
        force_select = force_select or self.force_choose_devices
        ports = self.list_midi_ports(show_table=force_select)
        if not ports:
            return None
        if force_select:
            choices = [questionary.Choice(f"{i}: {port}", value=i) for i, port in enumerate(ports)]
            idx = questionary.select(
                "Select MIDI output port:",
                choices=choices,
                default=default_index if 0 <= default_index < len(choices) else 0
            ).ask()
            if idx is None:
                self.console.print("\n[bold yellow]Exiting...[/bold yellow]")
                return None
            self.midi_port_index = idx
            self.midi_port_name = ports[idx]
            return ports[idx]
        # fallback to original logic for silent mode
        config_name = self.config.get('midi_name')
        config_index = self.config.get('midi_index')
        idx = None
        if config_name and config_name in ports:
            idx = ports.index(config_name)
        elif config_index is not None and 0 <= config_index < len(ports):
            idx = config_index
        if idx is not None:
            name = ports[idx]
            self.midi_port_index = idx
            self.midi_port_name = name
            return name
    # Use the patched methods for config
    import types
    app.select_microphone = types.MethodType(select_microphone_with_default, app)
    app.select_midi_port = types.MethodType(select_midi_port_with_default, app)
    app.select_microphone(force_select=True, default_index=audio_default)
    midi_port = app.select_midi_port(force_select=True, default_index=midi_default)
    pedal_port = None
    pedal_message = None
    if pedal:
        pedal_port, pedal_message = learn_pedal()
    if app.input_device_index is not None and app.midi_port_index is not None:
        save_config(
            audio_index=app.get_selected_audio_index(),
            midi_index=app.midi_port_index,
            transpose=app.transpose_semitones,
            min_freq=app.min_freq,
            chunk_size=app.chunk_size,
            audio_name=app.input_device_name,
            midi_name=app.midi_port_name,
            pedal_port=pedal_port,
            pedal_message=pedal_message,
            max_midi_note=max_midi_note if max_midi_note is not None else app.max_midi_note
        )
        click.secho("\n[Config] Devices and settings saved!", fg="green", bold=True)
    else:
        click.secho("\n[Config] Device selection cancelled.", fg="yellow", bold=True)

@cli.command("list-devices", short_help="List available audio and MIDI devices")
def list_devices():
    """Show all available audio input and MIDI output devices."""
    import pyaudio
    import mido
    click.secho("\nAudio Input Devices:", fg="yellow", bold=True)
    audio = pyaudio.PyAudio()
    info = audio.get_host_api_info_by_index(0)
    num_devices = info.get('deviceCount')
    for i in range(num_devices):
        dev = audio.get_device_info_by_host_api_device_index(0, i)
        if dev.get('maxInputChannels') > 0:
            click.secho(f"  {i}: {dev.get('name')}", fg="green")
    audio.terminate()
    click.secho("\nMIDI Output Ports:", fg="yellow", bold=True)
    ports = mido.get_output_names()
    for i, port in enumerate(ports):
        click.secho(f"  {i}: {port}", fg="green")

@cli.command("show-config", short_help="Show current saved config")
def show_config():
    """Print the current saved config (device selections, transpose, etc)."""
    config = load_config()
    if not config:
        click.secho("No config found.", fg="red")
        return
    click.secho("Current config:", fg="yellow", bold=True)
    for k, v in config.items():
        click.secho(f"  {k}: {v}", fg="green")

@cli.command("reset-config", short_help="Clear saved config and force re-selection")
def reset_config():
    """Delete the saved config file to force device/config re-selection next run."""
    import os
    if os.path.exists(CONFIG_PATH):
        os.remove(CONFIG_PATH)
        click.secho("Config file deleted. You will be prompted to select devices next time.", fg="green")
    else:
        click.secho("No config file found.", fg="yellow")

import numpy as np
# Remove: import sounddevice as sd

KEYBOARD_PROFILE_PATH = os.path.expanduser("~/.voice_to_midi_keyboard_profile.npy")

@cli.command("sample-keyboard-noise", short_help="Record your keyboard click noise profile for filtering.")
def sample_keyboard_noise():
    """
    Record a variety of mechanical keyboard clicks (letters, numbers, symbols) and save their spectral profile for filtering.
    """
    duration = 10  # seconds
    samplerate = 44100
    chunk_size = 2048
    channels = 1
    click.secho("\n[Keyboard Noise Sampling]", fg="cyan", bold=True)
    click.secho("Please type the following sequence repeatedly for the next 10 seconds:", fg="yellow")
    click.secho("The quick brown fox jumps over the lazy dog 1234567890 !@#$%^&*()", fg="yellow", bold=True)
    click.secho("Try to press as many different keys as possible, including letters, numbers, and symbols.", fg="yellow")
    click.secho("Recording will start in 2 seconds. Get ready!", fg="yellow")
    import time
    time.sleep(2)
    click.secho("Recording... Type now!", fg="green", bold=True)
    p = pyaudio.PyAudio()
    stream = p.open(format=pyaudio.paFloat32, channels=channels, rate=samplerate, input=True, frames_per_buffer=chunk_size)
    frames = []
    for _ in range(0, int(samplerate / chunk_size * duration)):
        data = stream.read(chunk_size, exception_on_overflow=False)
        frame = np.frombuffer(data, dtype=np.float32)
        frames.append(frame)
    stream.stop_stream()
    stream.close()
    p.terminate()
    click.secho("Recording complete. Analyzing...", fg="cyan")
    # Compute FFT magnitude for each frame
    spectra = [np.abs(np.fft.rfft(frame)) for frame in frames]
    avg_spectrum = np.mean(spectra, axis=0)
    np.save(KEYBOARD_PROFILE_PATH, avg_spectrum)
    click.secho(f"Keyboard noise profile saved to {KEYBOARD_PROFILE_PATH}", fg="green")

if __name__ == "__main__":
    main() 