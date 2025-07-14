# Audio to MIDI Converter

A real-time voice/audio/sound to MIDI translator that captures audio from your microphone, detects pitch using autocorrelation algorithms, and converts it to MIDI that can be sent to any MIDI-compatible software or hardware. Very experimental.

## Features

- **Real-time pitch detection** using autocorrelation algorithm with low latency
- **Intelligent device management** with persistent settings and beautiful TUI selection
- **Native GUI** built with tkinter for easy control and monitoring
- **MIDI output** to any MIDI-compatible device or software
- **Adjustable sensitivity** and velocity controls for fine-tuning
- **Live frequency and note display** with real-time feedback
- **Pedal support** for hands-free operation and note duration control (experimental)

## Quick Start

### 1. Install System Dependencies

This project requires some system libraries **before** installing Python dependencies:

#### macOS

```sh
brew install portaudio tcl-tk
```

#### Ubuntu/Debian

```sh
sudo apt-get update
sudo apt-get install portaudio19-dev tk-dev
```

#### Fedora

```sh
sudo dnf install portaudio-devel tk-devel
```

### 2. Install and Run

```bash
# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone and setup the project
cd audio-to-midi
uv sync

# Run the application
uv run python audio_to_midi.py run
```

On first run, you'll be prompted with a beautiful interactive interface to select your audio input and MIDI output devices. Your choices are automatically saved for future use.

## Device Selection and Persistence

- **First run**: You will be prompted to select your audio input (microphone) and MIDI output device using a beautiful interactive TUI.
- **After first run**: The app will start silently with your last-used devices/settings—no prompts, no menus.
- **To change devices/settings** at any time:

  - Run with `-c` or `--choose-devices`:

        uv run python audio_to_midi.py run -c

    This will show the device selection menus and save your new choices as the new defaults.

  - Or use the config command to change devices/settings without starting the app:

        uv run python audio_to_midi.py config

- Your choices are saved to `~/.audio_to_midi_config.json` and will be used next time.
- If your device list changes (e.g., you unplug/replug a mic), the app will match by device name, not just position, so your preferences are robust.

This makes it fast to launch with your preferred setup, but easy to change at any time, and the interface is visually enhanced for clarity and ease of use.

---

## Pedal Configuration for Real-time Control

You can use a MIDI pedal (such as a footswitch) to control note duration in real-time, which is especially useful for MuseScore's "Real-time (foot pedal)" MIDI input mode or similar DAW workflows.

### How to Configure or Change Pedal Settings

- To set up or change your pedal, run:

      uv run python audio_to_midi.py config

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

## Using a Virtual MIDI Port to Connect to MuseScore or Other MIDI Software

To send MIDI notes from your audio to any MIDI-compatible software (like MuseScore, GarageBand, Logic, Ableton, etc.), you need to set up a **virtual MIDI port**. This lets your app act like a MIDI keyboard for other programs.

### macOS: IAC Driver

1. Open **Audio MIDI Setup** (in Applications > Utilities).
2. Go to **Window > Show MIDI Studio**.
3. Double-click the **IAC Driver** icon.
4. In the IAC Driver window, check **"Device is online"**.
5. (Optional) Add a new port (e.g., "AudioToMidi").
6. Close the window.

When you run this app, you should see the IAC port (e.g., "IAC Driver Bus 1" or your custom name) as a MIDI output. Select it.

In **MuseScore** (or your DAW):

- Go to **Preferences > I/O** (or MIDI settings)
- Set the MIDI input to your IAC port
- Now, when you sing, MuseScore will receive MIDI notes as if you were playing a keyboard!

### Windows: loopMIDI

1. Download and install [loopMIDI](https://www.tobias-erichsen.de/software/loopmidi.html)
2. Create a new virtual port (e.g., "AudioToMidi")
3. Select this port in your app and in your MIDI software as input

### Linux: aconnect or QJackCtl

- Use `aconnect` or `qjackctl` to create and route virtual MIDI ports
- Set your app to output to the virtual port, and your MIDI software to receive from it

## Usage

- **Launch the application**: Run `uv run voice-to-midi run`
  - If you have saved settings, the app will start silently with your last-used devices.
  - To change devices, run with `-c` or `--choose-devices`.
- **Configure devices/settings**:
  - **Basic configuration** (audio input + MIDI output): `uv run voice-to-midi config`
  - **Advanced configuration** (all settings): `uv run voice-to-midi config --advanced`
  - **Specific settings**: `uv run voice-to-midi config --audio` (or `--midi`, `--pitch`, `--pedal`)
- **Other commands**:

  - **List devices**: `uv run voice-to-midi list`
  - **Show current config**: `uv run voice-to-midi show`
  - **Reset config**: `uv run voice-to-midi reset`

- **Select MIDI output**: Choose your desired MIDI output port from the dropdown (on first run or when changing devices)
- **Adjust settings**:
  - **Sensitivity**: Controls how sensitive the pitch detection is (0.1-1.0)
  - **Velocity**: Sets the MIDI note velocity (1-127)
- **Start processing**: Click "Start" to begin voice-to-MIDI conversion
- **Sing or hum**: The application will detect your voice pitch and convert it to MIDI notes
- **Monitor**: Watch the current note and frequency display in real-time

## Requirements

- Python 3.8 or higher
- Microphone input
- MIDI output device or software (optional, for testing)

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

Note that lower notes appear to not have a high confidence level when being detected.

### High Latency

1. Reduce chunk size in the code (may affect pitch detection accuracy)
2. Close other audio applications
3. Check system audio settings

### Poor Pitch Detection

1. Adjust sensitivity
2. Ensure quiet environment
3. Use clear, sustained notes
4. Check microphone quality
5. **If low notes are not detected:** Increase the chunk size (e.g., to 2048 or 4096) in the config. Smaller chunk sizes cannot resolve low frequencies. See the Technical Details section for more info.
6. **If you see spurious high notes (e.g., F#6, G6) from keyboard clicks:** Set a maximum MIDI note (high-note gate) in the config to ignore notes above your vocal range. Example: --max-midi-note 84 (C6).

## Development

### Project Structure

```
audio-to-midi/
├── pyproject.toml
├── audio_to_midi.py
├── README.md
└── tests/
```

### Dependencies

- **sounddevice**: Audio capture and playback (replaces pyaudio for better compatibility)
- **numpy**: Numerical computing
- **librosa**: Audio analysis (future enhancements)
- **mido**: MIDI I/O
- **scipy**: Signal processing
- **tkinter**: GUI framework

### Contributing

Thank you for your interest in contributing to this project. Contributions are welcome in the form of issues and pull requests.

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run linter and formatter
5. Add tests if applicable
6. Submit a pull request
