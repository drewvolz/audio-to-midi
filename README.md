# Voice to MIDI Translator

## Device Selection and Persistence

- **First run**: You will be prompted to select your audio input (microphone) and MIDI output device using a beautiful interactive TUI.
- **After first run**: The app will start silently with your last-used devices/settings—no prompts, no menus.
- **To change devices/settings** at any time:
  - Run with `-c` or `--choose-devices`:

        uv run python voice_to_midi.py run -c

    This will show the device selection menus and save your new choices as the new defaults.
  - Or use the config command to change devices/settings without starting the app:

        uv run python voice_to_midi.py config

- Your choices are saved to `~/.voice_to_midi_config.json` and will be used next time.
- If your device list changes (e.g., you unplug/replug a mic), the app will match by device name, not just position, so your preferences are robust.

This makes it fast to launch with your preferred setup, but easy to change at any time, and the interface is visually enhanced for clarity and ease of use.

---

## Pedal Configuration for Real-time Control

You can use a MIDI pedal (such as a footswitch) to control note duration in real-time, which is especially useful for MuseScore's "Real-time (foot pedal)" MIDI input mode or similar DAW workflows.

### How to Configure or Change Pedal Settings

- To set up or change your pedal, run:

      uv run python voice_to_midi.py config

- When prompted, select your pedal's MIDI input port.
- Press your pedal when asked to "learn" the pedal's MIDI message. The app will detect and save the message for future use.
- Your pedal configuration is saved and will be used automatically next time.

### To Re-learn or Change the Pedal
- Simply run the `config` command again and follow the prompts to select a different pedal port or re-learn the pedal message.

### Troubleshooting
- If your pedal is not detected, ensure it is plugged in and recognized by your system.
- If you change pedals or ports, re-run the configuration to update the saved settings.
- The pedal can be used to control note on/off events in real-time, making it ideal for hands-free operation in scoring software.

---

## System Requirements (Must Install Before Using uv/uvx)

This project requires some system libraries to be installed on your machine **before** you use `uv` or `uvx` to install Python dependencies. These are needed for audio and GUI support.

### macOS
```sh
brew install portaudio tcl-tk
```

### Ubuntu/Debian
```sh
sudo apt-get update
sudo apt-get install portaudio19-dev tk-dev
```

### Fedora
```sh
sudo dnf install portaudio-devel tk-devel
```

---

## Using a Virtual MIDI Port to Connect to MuseScore or Other MIDI Software

To send MIDI notes from your voice to any MIDI-compatible software (like MuseScore, GarageBand, Logic, Ableton, etc.), you need to set up a **virtual MIDI port**. This lets your app act like a MIDI keyboard for other programs.

### macOS: IAC Driver
1. Open **Audio MIDI Setup** (in Applications > Utilities).
2. Go to **Window > Show MIDI Studio**.
3. Double-click the **IAC Driver** icon.
4. In the IAC Driver window, check **"Device is online"**.
5. (Optional) Add a new port (e.g., "VoiceToMidi").
6. Close the window.

When you run this app, you should see the IAC port (e.g., "IAC Driver Bus 1" or your custom name) as a MIDI output. Select it.

In **MuseScore** (or your DAW):
- Go to **Preferences > I/O** (or MIDI settings)
- Set the MIDI input to your IAC port
- Now, when you sing, MuseScore will receive MIDI notes as if you were playing a keyboard!

### Windows: loopMIDI
1. Download and install [loopMIDI](https://www.tobias-erichsen.de/software/loopmidi.html)
2. Create a new virtual port (e.g., "VoiceToMidi")
3. Select this port in your app and in your MIDI software as input

### Linux: aconnect or QJackCtl
- Use `aconnect` or `qjackctl` to create and route virtual MIDI ports
- Set your app to output to the virtual port, and your MIDI software to receive from it

---

A real-time voice-to-MIDI translation application that captures audio from your microphone, detects pitch, and converts it to MIDI notes that can be sent to any MIDI-compatible software or hardware.

## Features

- **Real-time pitch detection** using autocorrelation algorithm
- **Low-latency audio processing** for responsive performance
- **Native GUI** built with tkinter for easy control
- **MIDI output** to any MIDI-compatible device or software
- **Adjustable sensitivity** and velocity controls
- **Live frequency and note display**

## Requirements

- Python 3.8 or higher
- Microphone input
- MIDI output device or software (optional, for testing)

### System Dependencies

The application uses `pyaudio` and `tkinter`, which require the PortAudio and Tcl/Tk libraries:

- **macOS**: `brew install portaudio tcl-tk`
- **Ubuntu/Debian**: `sudo apt-get install portaudio19-dev tk-dev`
- **Fedora**: `sudo dnf install portaudio-devel tk-devel`

## Quick Start

### 1. Install uv (if not already installed)

```bash
# On macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Or using pip
pip install uv
```

### 2. Clone and setup the project

```bash
# Navigate to the project directory
cd voice-to-midi

# Install dependencies using uv
uv sync

# Activate the virtual environment
uv run python voice_to_midi.py
```

### 3. Alternative setup with pip

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the application
python voice_to_midi.py
```

## Usage

- **Launch the application**: Run `uv run python voice_to_midi.py run`
  - If you have saved settings, the app will start silently with your last-used devices.
  - To change devices, run with `-c` or `--choose-devices`.
- **Configure devices/settings only** (no app start):

      uv run python voice_to_midi.py config --max-midi-note 84

- **Select MIDI output**: Choose your desired MIDI output port from the dropdown (on first run or when changing devices)
- **Adjust settings**: 
  - **Sensitivity**: Controls how sensitive the pitch detection is (0.1-1.0)
  - **Velocity**: Sets the MIDI note velocity (1-127)
- **Start processing**: Click "Start" to begin voice-to-MIDI conversion
- **Sing or hum**: The application will detect your voice pitch and convert it to MIDI notes
- **Monitor**: Watch the current note and frequency display in real-time

## MIDI Output Setup

### Virtual MIDI Port (macOS)

1. Install a virtual MIDI driver like "IAC Driver" or "LoopMIDI"
2. Create a virtual MIDI port
3. Select the virtual port in the application
4. Connect to your DAW or MIDI software

### Windows

1. Install a virtual MIDI driver like "loopMIDI" or "rtmidi"
2. Create a virtual MIDI port
3. Select the virtual port in the application

### Linux

1. Install ALSA MIDI utilities: `sudo apt-get install alsa-utils`
2. Create a virtual MIDI port: `aconnect -o`
3. Select the virtual port in the application

## Technical Details

### Audio Processing

- **Sample Rate**: 44.1 kHz
- **Chunk Size**: 1024 samples (default, adjustable)
- **Channels**: Mono
- **Format**: 32-bit float

**Note:**
- The **chunk size** determines the lowest frequency that can be detected. Larger chunk sizes allow detection of lower notes, but increase latency. For example:
    - 1024: ~215 Hz lowest
    - 2048: ~107 Hz lowest
    - 4096: ~53 Hz lowest
- For full vocal range, use 2048 or 4096. If you need lower latency and only higher notes, use a smaller chunk size.
- **High-note gate**: You can set a maximum MIDI note (e.g., 84 for C6) to ignore spurious high-frequency detections, such as those from mechanical keyboard clicks. Use the --max-midi-note option in the config command.

### Pitch Detection

- **Algorithm**: Autocorrelation with peak detection
- **Frequency Range**: 80 Hz - 800 Hz (E2 - G5)
- **Confidence Threshold**: Adjustable via GUI
- **Silence Detection**: Automatic silence filtering

### MIDI Output

- **Channel**: 0 (default)
- **Note Range**: E2 (MIDI note 40) to G5 (MIDI note 67)
- **Velocity**: Adjustable (1-127)
- **Note On/Off**: Automatic based on pitch detection

## Troubleshooting

### No Audio Input

1. Check microphone permissions
2. Ensure microphone is selected as default input
3. Test microphone in system settings

### No MIDI Output

1. Install a virtual MIDI driver
2. Check if MIDI ports are available
3. Restart the application after installing MIDI drivers

### High Latency

1. Reduce chunk size in the code (may affect pitch detection accuracy)
2. Close other audio applications
3. Check system audio settings

### Poor Pitch Detection

1. Adjust sensitivity slider
2. Ensure quiet environment
3. Use clear, sustained notes
4. Check microphone quality
5. **If low notes are not detected:** Increase the chunk size (e.g., to 2048 or 4096) in the config. Smaller chunk sizes cannot resolve low frequencies. See the Technical Details section for more info.
5. **If you see spurious high notes (e.g., F#6, G6) from keyboard clicks:** Set a maximum MIDI note (high-note gate) in the config to ignore notes above your vocal range. Example: --max-midi-note 84 (C6).

## Development

### Project Structure

```
voice-to-midi/
├── pyproject.toml          # Project configuration and dependencies
├── voice_to_midi.py        # Main application
├── README.md              # This file
└── tests/                 # Test files (future)
```

### Dependencies

- **sounddevice**: Audio capture and playback (replaces pyaudio for better compatibility)
- **numpy**: Numerical computing
- **librosa**: Audio analysis (future enhancements)
- **mido**: MIDI I/O
- **scipy**: Signal processing
- **tkinter**: GUI framework

### Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is open source and available under the MIT License.

## Acknowledgments

- Built with Python and tkinter
- Uses autocorrelation for pitch detection
- MIDI handling via mido library
- Audio processing with PyAudio 