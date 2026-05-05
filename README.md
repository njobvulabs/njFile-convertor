# njFile-convertor

A simple yet powerful file converter for videos and audio using ffmpeg. Supports both CLI and GUI interfaces.

## Features

- **Video to Video**: Convert between mp4, avi, mkv, mov, webm, flv, wmv, m4v
- **Audio to Audio**: Convert between mp3, wav, aac, flac, ogg, m4a, wma
- **Video to Audio**: Extract audio tracks from video files
- **Batch Conversion**: Convert multiple files at once
- **Progress Tracking**: Visual progress bar during conversion
- **Both CLI and GUI**: Use from terminal or with a graphical interface

## Requirements

- Python 3.6+
- ffmpeg (already installed at `/usr/bin/ffmpeg`)
- tkinter (for GUI mode, usually built-in)

### Install tkinter (if needed)
```bash
sudo apt install python3-tk  # For Debian/Ubuntu
```

## Installation

### Quick Setup (Recommended)

Clone the repository and run the setup script. It works on **Arch**, **Debian/Ubuntu**, and **Fedora**-based distros:

```bash
git clone https://github.com/njobvulabs/njFile-convertor.git
cd njFile-convertor
./setup.sh
```

The setup script will:
- Check for Python 3
- Install system dependencies (`ffmpeg`, `tkinter`) automatically
- Add `njFile-convertor` to your application menu

### Manual Installation

```bash
cd /home/njobvu/Projects/njFile-convertor
# No pip install needed - all dependencies are built-in!

# System dependencies (install manually if you prefer):
# Arch:     sudo pacman -S ffmpeg tk
# Debian:   sudo apt install ffmpeg python3-tk
# Fedora:   sudo dnf install ffmpeg python3-tkinter
```

### Uninstall

Remove from apps menu:
```bash
./uninstall.sh
```

## Usage

### GUI Mode (Default)
```bash
python main.py
# or
python main.py --gui
```

The GUI provides:
- File browser to add multiple files
- Dropdown to select output format
- Output directory selection
- Progress bar and conversion log

### CLI Mode
```bash
python main.py --cli
# or directly
python cli.py
```

#### CLI Examples

**Convert a single file:**
```bash
python main.py --cli -i input.mp4 -o output.mkv
```

**Convert video to audio:**
```bash
python main.py --cli -i video.mp4 -o audio.mp3
```

**Batch convert multiple files:**
```bash
python main.py --cli -i file1.mp4 file2.avi -o ./output --format mkv
```

**Show supported formats:**
```bash
python main.py --cli --formats
```

## Supported Formats

### Video Formats
- MP4, AVI, MKV, MOV, WebM, FLV, WMV, M4V

### Audio Formats
- MP3, WAV, AAC, FLAC, OGG, M4A, WMA

## How It Works

The converter uses Python's `subprocess` module to call ffmpeg directly:
- No additional Python packages required
- Uses appropriate codecs for each format
- Parses ffmpeg output to show progress
- Handles errors gracefully

## Project Structure

```
njFile-convertor/
├── main.py              # Entry point (CLI/GUI selection)
├── converter.py         # Core conversion logic
├── cli.py              # Command-line interface
├── gui.py              # Graphical interface (tkinter)
├── setup.sh            # Cross-distro installer (Arch/Debian/Fedora)
├── uninstall.sh        # Remove from apps menu
├── njfile-convertor.svg# Application icon
├── requirements.txt    # Dependencies (all built-in!)
└── README.md          # This file
```

## Troubleshooting

**"ffmpeg not found" error:**
- Ensure ffmpeg is installed: `sudo apt install ffmpeg`

**GUI doesn't open:**
- Install tkinter: `sudo apt install python3-tk`

**Conversion fails:**
- Check that input file is not corrupted
- Verify output format is supported
- Check available disk space

## License

MIT License (free to use and modify)
