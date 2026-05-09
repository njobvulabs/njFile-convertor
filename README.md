# njFile-convertor

A modern file converter for videos and audio backed by ffmpeg, with both CLI and GUI interfaces built with CustomTkinter.

## Features

- **Video to Video**: Convert between mp4, avi, mkv, mov, webm, flv, wmv, m4v
- **Audio to Audio**: Convert between mp3, wav, aac, flac, ogg, m4a, wma
- **Video to Audio**: Extract audio tracks from video files
- **Batch Conversion**: Convert multiple files at once with queue management
- **Drag & Drop Files**: Drop files from your file manager directly onto the app
- **Drag & Drop Queue**: Drag files to reorder the conversion queue
- **Per-File Format Override**: Double-click any queued file to override its output format
- **File Metadata Viewer**: Select a file in the queue to see its codec, resolution, bitrate, duration, FPS, and audio info
- **Error Details**: Failed conversions show the FFmpeg error message directly in the queue
- **Watch Folder**: Auto-convert files dropped into a monitored directory
- **Dark & Light Theme**: Toggle between themes, persisted across sessions
- **Settings Persistence**: Quality, format, output directory, theme, and window geometry are saved and restored
- **Conversion History**: Track all past conversions with re-convert and CSV export
- **Keyboard Shortcuts**: Ctrl+O (add files), Ctrl+V (start), Delete (remove), Escape (stop)
- **Quality/Settings Control**: Adjust CRF quality, resolution, sample rate, audio channels
- **History Export**: Export conversion history to CSV

## Requirements

- Python 3.6+
- ffmpeg
- CustomTkinter (installed via pip, handled by setup script)
- tk/tcl (system package for GUI mode)

## Installation

### Quick Setup (Recommended)

Run the setup script. It works on **Arch**, **Debian/Ubuntu**, and **Fedora**-based distros:

```bash
git clone https://github.com/njobvulabs/njFile-convertor.git
cd njFile-convertor
./setup.sh
```

The setup script will:
- Check for Python 3 and install system dependencies (ffmpeg, tk)
- Create a Python virtual environment in the project folder
- Install pip dependencies (customtkinter, tkinterdnd2, Pillow)
- Add `njFile-convertor` to your application menu

### Manual Installation

```bash
cd /home/njobvu/Projects/njFile-convertor

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt

# System dependencies:
# Arch:     sudo pacman -S ffmpeg tk
# Debian:   sudo apt install ffmpeg python3-tk
# Fedora:   sudo dnf install ffmpeg python3-tkinter
```

### Uninstall

```bash
./uninstall.sh
```

Removes: desktop entry, app icons, virtual environment.

## Usage

### GUI Mode (Default)

From the app menu, or:

```bash
python main.py
# or with explicit flag
python main.py --gui
```

The GUI provides:
- Native file dialogs or drag-and-drop from file manager (zenity/kdialog fallback)
- File metadata panel — select any file to see codec, resolution, bitrate, etc.
- Per-file format override — double-click a queued file to change its format
- Output format, quality, resolution, and audio settings
- Output directory and filename pattern selection
- Drag-to-reorder conversion queue
- Progress bar with pause/stop controls
- Retry failed conversions with visible error messages

### CLI Mode

```bash
python main.py --cli
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

## Keyboard Shortcuts

| Shortcut | Action |
|---|---|
| `Ctrl+O` | Add files to queue |
| `Ctrl+V` | Start conversion |
| `Delete` | Remove selected files |
| `Escape` | Stop conversion |

## Supported Formats

### Video Formats
MP4, AVI, MKV, MOV, WebM, FLV, WMV, M4V

### Audio Formats
MP3, WAV, AAC, FLAC, OGG, M4A, WMA

## How It Works

The converter uses Python's `subprocess` module to call ffmpeg directly:
- Uses appropriate codecs for each format
- Parses ffmpeg output to show progress
- Handles errors gracefully

## Project Structure

```
njFile-convertor/
├── main.py              # Entry point (CLI/GUI selection)
├── converter.py         # Core conversion logic
├── cli.py               # Command-line interface
├── gui.py               # Graphical interface (CustomTkinter)
├── setup.sh             # Cross-distro installer
├── uninstall.sh         # Remove from apps menu
├── venv/                # Python virtual environment (created by setup)
├── njfile-convertor.svg # Application icon
├── njfile-convertor.png # Application icon (fallback)
├── requirements.txt     # Python dependencies
├── settings.json        # Persisted settings (created on first run)
├── history.json         # Conversion history (created on first run)
└── README.md            # This file
```

## Troubleshooting

**"ffmpeg not found" error:**
- Ensure ffmpeg is installed: `sudo pacman -S ffmpeg` or `sudo apt install ffmpeg`

**App icon in menu doesn't open anything:**
- Re-run `./setup.sh` to recreate the virtual environment and fix the launcher path

**GUI fails with "customtkinter not found":**
- Activate the venv: `source venv/bin/activate` then run `pip install -r requirements.txt`

**GUI fails with "no display":**
- This is expected when running over SSH without X forwarding. Use `--cli` mode instead.

**Conversion fails:**
- Check that input file is not corrupted
- Verify output format is supported
- Check available disk space

## License

MIT License (free to use and modify)
