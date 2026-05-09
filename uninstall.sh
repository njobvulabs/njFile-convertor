#!/usr/bin/env bash
set -euo pipefail

# njFile-convertor - Uninstall script

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DESKTOP_FILE="$HOME/.local/share/applications/njfile-convertor.desktop"
ICON_DEST="$HOME/.local/share/icons"
VENV_DIR="${SCRIPT_DIR}/venv"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}========================================${NC}"
echo -e "${CYAN}  njFile-convertor - Uninstall${NC}"
echo -e "${CYAN}========================================${NC}"
echo ""

# Remove desktop entry
echo -n "Removing desktop entry... "
if [ -f "$DESKTOP_FILE" ]; then
    rm "$DESKTOP_FILE"
    echo -e "${GREEN}done${NC}"
else
    echo -e "already gone"
fi

# Remove icons
echo -n "Removing icons... "
REMOVED=false
for ext in svg png; do
    if [ -f "$ICON_DEST/njfile-convertor.$ext" ]; then
        rm "$ICON_DEST/njfile-convertor.$ext"
        REMOVED=true
    fi
done
if [ "$REMOVED" = true ]; then
    echo -e "${GREEN}done${NC}"
else
    echo -e "already gone"
fi

# Remove virtual environment
echo -n "Removing virtual environment... "
if [ -d "$VENV_DIR" ]; then
    rm -rf "$VENV_DIR"
    echo -e "${GREEN}done${NC}"
else
    echo -e "already gone"
fi

# Update desktop database
if command -v update-desktop-database &> /dev/null && [ -d "$HOME/.local/share/applications" ]; then
    update-desktop-database "$HOME/.local/share/applications" 2>/dev/null || true
fi

echo ""
echo -e "${CYAN}========================================${NC}"
echo -e "${GREEN}  Uninstall complete!${NC}"
echo -e "${CYAN}========================================${NC}"
echo ""
echo -e "  The app has been removed from your apps menu."
echo -e "  System packages (ffmpeg, tk, customtkinter) were not removed."
echo -e "  To remove the project files, delete the folder manually."
echo ""
