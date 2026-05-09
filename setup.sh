#!/usr/bin/env bash
set -euo pipefail

# njFile-convertor - Cross-distro setup script

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_NAME="njFile-convertor"
VENV_DIR="${SCRIPT_DIR}/venv"
EXEC_PATH="${VENV_DIR}/bin/python ${SCRIPT_DIR}/main.py"
DESKTOP_FILE="$HOME/.local/share/applications/njfile-convertor.desktop"
ICON_SRC_SVG="${SCRIPT_DIR}/njfile-convertor.svg"
ICON_SRC_PNG="${SCRIPT_DIR}/njfile-convertor.png"
ICON_DEST="$HOME/.local/share/icons"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}========================================${NC}"
echo -e "${CYAN}  ${APP_NAME} Setup${NC}"
echo -e "${CYAN}========================================${NC}"
echo ""

# Step 1: Check Python 3
echo -e "${YELLOW}[1/7]${NC} Checking Python 3..."
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version 2>&1)
    echo -e "  ${GREEN}Found:${NC} ${PYTHON_VERSION}"
else
    echo -e "  ${RED}Python 3 not found!${NC}"
    echo ""
    echo -e "  Install Python 3 first:"
    echo -e "  ${CYAN}Arch:     ${NC}sudo pacman -S python"
    echo -e "  ${CYAN}Debian:   ${NC}sudo apt install python3"
    echo -e "  ${CYAN}Fedora:   ${NC}sudo dnf install python3"
    echo ""
    exit 1
fi

# Step 2: Detect distro
echo -e "${YELLOW}[2/7]${NC} Detecting distribution..."
if [ -f /etc/os-release ]; then
    DISTRO=$(. /etc/os-release && echo "$ID")
else
    echo -e "  ${RED}Cannot detect distribution.${NC}"
    echo -e "  ${YELLOW}Ensure /etc/os-release exists.${NC}"
    exit 1
fi

echo -e "  ${GREEN}Detected:${NC} ${DISTRO}"

case "$DISTRO" in
    arch)
        PKG_MANAGER="pacman"
        INSTALL_CMD="sudo pacman -S --noconfirm --needed"
        FFMPEG_PKG="ffmpeg"
        TK_PKG="tk"
        ZENITY_PKG="zenity"
        ;;
    ubuntu|debian|linuxmint|pop|elementary|zorin)
        PKG_MANAGER="apt"
        INSTALL_CMD="sudo apt install -y"
        FFMPEG_PKG="ffmpeg"
        TK_PKG="python3-tk"
        ZENITY_PKG="zenity"
        ;;
    fedora|rhel|centos|rocky|alma)
        PKG_MANAGER="dnf"
        INSTALL_CMD="sudo dnf install -y"
        FFMPEG_PKG="ffmpeg"
        TK_PKG="python3-tkinter"
        ZENITY_PKG="zenity"
        ;;
    *)
        echo -e "  ${RED}Unsupported distribution: ${DISTRO}${NC}"
        echo -e "  ${YELLOW}Supported: Arch, Debian/Ubuntu, Fedora-based${NC}"
        echo ""
        echo -e "  Install these packages manually:"
        echo -e "    - ffmpeg"
        echo -e "    - python3-tk (or tk package for your distro)"
        exit 1
        ;;
esac

# Step 3: Install system dependencies
echo -e "${YELLOW}[3/7]${NC} Checking system dependencies..."

DEPS_OK=true

# Check ffmpeg
if command -v ffmpeg &> /dev/null; then
    echo -e "  ${GREEN}ffmpeg:${NC} already installed ($(ffmpeg -version 2>&1 | head -1 | cut -d' ' -f3))"
else
    DEPS_OK=false
    echo -e "  ${YELLOW}ffmpeg:${NC} not found, installing..."
    if ! $INSTALL_CMD $FFMPEG_PKG; then
        echo -e "  ${RED}Failed to install ffmpeg.${NC}"
        exit 1
    fi
    echo -e "  ${GREEN}ffmpeg:${NC} installed."
fi

# Check tkinter
case "$DISTRO" in
    arch)
        if pacman -Q tk &> /dev/null; then
            echo -e "  ${GREEN}tk:${NC} already installed ($(pacman -Q tk | awk '{print $2}'))"
        else
            DEPS_OK=false
            echo -e "  ${YELLOW}tk:${NC} not found, installing..."
            if ! $INSTALL_CMD $TK_PKG; then
                echo -e "  ${RED}Failed to install tk.${NC}"
                exit 1
            fi
            echo -e "  ${GREEN}tk:${NC} installed."
        fi
        ;;
    ubuntu|debian|linuxmint|pop|elementary|zorin)
        if dpkg -l python3-tk &> /dev/null; then
            echo -e "  ${GREEN}python3-tk:${NC} already installed"
        else
            DEPS_OK=false
            echo -e "  ${YELLOW}python3-tk:${NC} not found, installing..."
            if ! $INSTALL_CMD $TK_PKG; then
                echo -e "  ${RED}Failed to install python3-tk.${NC}"
                exit 1
            fi
            echo -e "  ${GREEN}python3-tk:${NC} installed."
        fi
        ;;
    fedora|rhel|centos|rocky|alma)
        if rpm -q python3-tkinter &> /dev/null; then
            echo -e "  ${GREEN}python3-tkinter:${NC} already installed"
        else
            DEPS_OK=false
            echo -e "  ${YELLOW}python3-tkinter:${NC} not found, installing..."
            if ! $INSTALL_CMD $TK_PKG; then
                echo -e "  ${RED}Failed to install python3-tkinter.${NC}"
                exit 1
            fi
            echo -e "  ${GREEN}python3-tkinter:${NC} installed."
        fi
        ;;
esac

# Check zenity (native file dialogs)
if command -v zenity &> /dev/null; then
    echo -e "  ${GREEN}zenity:${NC} already installed ($(zenity --version))"
else
    DEPS_OK=false
    echo -e "  ${YELLOW}zenity:${NC} not found, installing..."
    if ! $INSTALL_CMD $ZENITY_PKG; then
        echo -e "  ${YELLOW}zenity:${NC} optional install failed (will use fallback dialogs)."
    else
        echo -e "  ${GREEN}zenity:${NC} installed."
    fi
fi

if [ "$DEPS_OK" = true ]; then
    echo -e "  ${GREEN}All dependencies are already satisfied.${NC}"
else
    echo -e "  ${GREEN}Dependencies installed successfully.${NC}"
fi

# Step 4: Create virtual environment and install pip packages
echo -e "${YELLOW}[4/7]${NC} Setting up Python virtual environment..."

# Try to ensure pip/venv are available
if ! python3 -m venv --help &>/dev/null; then
    echo -e "  ${YELLOW}python3-venv not found, installing...${NC}"
    case "$DISTRO" in
        arch|manjaro)
            sudo pacman -S --noconfirm --needed python-virtualenv
            ;;
        ubuntu|debian|linuxmint|pop|elementary|zorin)
            sudo apt install -y python3-venv python3-pip
            ;;
        fedora|rhel|centos|rocky|alma)
            sudo dnf install -y python3-virtualenv python3-pip
            ;;
    esac
fi

python3 -m venv "$VENV_DIR"
echo -e "  ${GREEN}Virtual environment created at ${VENV_DIR}.${NC}"

echo -n "  Installing Python packages..."
"$VENV_DIR/bin/pip" install -q -r "$SCRIPT_DIR/requirements.txt"
echo -e "  ${GREEN} done.${NC}"

# Always re-link the desktop Exec to the venv python
EXEC_PATH="${VENV_DIR}/bin/python ${SCRIPT_DIR}/main.py"

# Step 5: Ensure main.py has shebang and is executable
echo -e "${YELLOW}[5/7]${NC} Preparing main.py..."
if [ -f "${SCRIPT_DIR}/main.py" ]; then
    FIRST_LINE=$(head -n 1 "${SCRIPT_DIR}/main.py")
    if [[ "$FIRST_LINE" != "#!/usr/bin/env python3"* ]]; then
        TEMP_FILE=$(mktemp)
        echo '#!/usr/bin/env python3' > "$TEMP_FILE"
        cat "${SCRIPT_DIR}/main.py" >> "$TEMP_FILE"
        mv "$TEMP_FILE" "${SCRIPT_DIR}/main.py"
        echo -e "  ${GREEN}Added shebang line.${NC}"
    else
        echo -e "  ${GREEN}Shebang already present.${NC}"
    fi
    chmod +x "${SCRIPT_DIR}/main.py"
    echo -e "  ${GREEN}Made main.py executable.${NC}"
else
    echo -e "  ${RED}main.py not found at: ${SCRIPT_DIR}/main.py${NC}"
    exit 1
fi

# Step 6: Install icon
echo -e "${YELLOW}[6/7]${NC} Installing app icon..."
mkdir -p "$ICON_DEST"
ICON_INSTALLED=false
if [ -f "$ICON_SRC_SVG" ]; then
    cp "$ICON_SRC_SVG" "$ICON_DEST/njfile-convertor.svg"
    echo -e "  ${GREEN}SVG icon installed.${NC}"
    ICON_INSTALLED=true
fi
if [ -f "$ICON_SRC_PNG" ]; then
    cp "$ICON_SRC_PNG" "$ICON_DEST/njfile-convertor.png"
    echo -e "  ${GREEN}PNG icon installed.${NC}"
    ICON_INSTALLED=true
fi
if [ "$ICON_INSTALLED" = false ]; then
    echo -e "  ${YELLOW}No icon files found, skipping.${NC}"
fi

# Step 7: Create .desktop file
echo -e "${YELLOW}[7/7]${NC} Creating desktop entry..."
mkdir -p "$HOME/.local/share/applications"

cat > "$DESKTOP_FILE" << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=njFile-convertor
GenericName=File Converter
Comment=Video and Audio File Converter using ffmpeg
Exec=${VENV_DIR}/bin/python ${SCRIPT_DIR}/main.py
Icon=${ICON_DEST}/njfile-convertor
Terminal=false
Categories=AudioVideo;AudioVideoEditing;Utility;
Keywords=converter;ffmpeg;video;audio;mp4;mp3;mkv;
StartupWMClass=njFile-convertor
EOF

echo -e "  ${GREEN}Desktop entry created:${NC} ${DESKTOP_FILE}"

# Update desktop database
if command -v update-desktop-database &> /dev/null; then
    update-desktop-database "$HOME/.local/share/applications" 2>/dev/null || true
fi

echo ""
echo -e "${CYAN}========================================${NC}"
echo -e "${GREEN}  Setup complete!${NC}"
echo -e "${CYAN}========================================${NC}"
echo ""
echo -e "  Find ${GREEN}${APP_NAME}${NC} in your application menu."
echo -e "  Or run directly: ${CYAN}${VENV_DIR}/bin/python ${SCRIPT_DIR}/main.py${NC}"
echo -e "  Or activate venv first: ${CYAN}source ${VENV_DIR}/bin/activate && python main.py${NC}"
echo ""
echo -e "  To uninstall, run: ${CYAN}bash ${SCRIPT_DIR}/uninstall.sh${NC}"
echo ""
