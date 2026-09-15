#!/usr/bin/env bash
set -e

# ==============================================================================
# Antigravity Quota Monitor - Desktop WebApp Installer
# Standalone, native-feeling desktop web application for Linux.
# ==============================================================================

COLOR_RESET="\033[0m"
COLOR_GREEN="\033[1;32m"
COLOR_CYAN="\033[1;36m"
COLOR_YELLOW="\033[1;33m"
COLOR_RED="\033[1;31m"

echo -e "${COLOR_GREEN}"
echo "    _          _   _                      _ _         "
echo "   / \   _ __ | |_(_) __ _ _ __ __ ___   _(_) |_ _   _ "
echo "  / _ \ | '_ \| __| |/ _\` | '__/ _\` \ \ / / | __| | | |"
echo " / ___ \| | | | |_| | (_| | | | (_| |\ V /| | |_| |_| |"
echo "/_/   \_\_| |_|\__|_|\__, |_|  \__,_| \_/ |_|\__|\__, |"
echo "                     |___/                       |___/ "
echo "        QUOTA MONITOR - STANDALONE LINUX APP           "
echo -e "${COLOR_RESET}"
echo -e "${COLOR_CYAN}Installing Antigravity Quota WebApp...${COLOR_RESET}\n"

# 1. Dependency Checks
MISSING_DEPS=()
command -v python3 >/dev/null 2>&1 || MISSING_DEPS+=("python3")
command -v wmctrl >/dev/null 2>&1 || MISSING_DEPS+=("wmctrl")

CHROME_BIN=""
for b in chromium chromium-browser google-chrome-stable google-chrome brave-browser; do
  if command -v "$b" >/dev/null 2>&1; then
    CHROME_BIN="$b"
    break
  fi
done

if [ -z "$CHROME_BIN" ]; then
  MISSING_DEPS+=("chromium (or google-chrome / brave)")
fi

if [ ${#MISSING_DEPS[@]} -gt 0 ]; then
  echo -e "${COLOR_RED}Missing required dependencies:${COLOR_RESET}"
  for dep in "${MISSING_DEPS[@]}"; do
    echo -e "  - $dep"
  done
  echo ""
  echo -e "Install with: ${COLOR_YELLOW}sudo apt install -y chromium python3 wmctrl${COLOR_RESET}"
  exit 1
fi

echo -e "✓ Found Chromium browser: ${COLOR_GREEN}$CHROME_BIN${COLOR_RESET}"
echo -e "✓ Found Python 3: ${COLOR_GREEN}$(python3 --version)${COLOR_RESET}"
echo -e "✓ Found wmctrl: ${COLOR_GREEN}$(which wmctrl)${COLOR_RESET}"

# 2. Setup Directories
INSTALL_DIR="$HOME/.local/share/antigravity-quota-app"
BIN_DIR="$HOME/.local/bin"
ICON_DIR="$HOME/.local/share/icons"
APP_DIR="$HOME/.local/share/applications"

mkdir -p "$INSTALL_DIR"
mkdir -p "$BIN_DIR"
mkdir -p "$ICON_DIR/hicolor/256x256/apps"
mkdir -p "$APP_DIR"

# 3. Copy Application Files
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cp -r "$SCRIPT_DIR/backend" "$INSTALL_DIR/"
cp -r "$SCRIPT_DIR/src" "$INSTALL_DIR/"
cp -r "$SCRIPT_DIR/assets" "$INSTALL_DIR/"

# 4. Setup Python Virtualenv & Dependencies
echo -e "\nSetting up Python environment in ${COLOR_CYAN}$INSTALL_DIR/.venv${COLOR_RESET}..."
if command -v uv >/dev/null 2>&1; then
  uv venv "$INSTALL_DIR/.venv" --quiet
  uv pip install --quiet --python "$INSTALL_DIR/.venv/bin/python" requests rich
elif [ -x "$HOME/.local/bin/uv" ]; then
  "$HOME/.local/bin/uv" venv "$INSTALL_DIR/.venv" --quiet
  "$HOME/.local/bin/uv" pip install --quiet --python "$INSTALL_DIR/.venv/bin/python" requests rich
else
  python3 -m venv "$INSTALL_DIR/.venv"
  "$INSTALL_DIR/.venv/bin/pip" install --quiet requests rich
fi

# 5. Create Binary Launcher
LAUNCHER="$BIN_DIR/antigravity-quota"
printf '#!/usr/bin/env bash\nexport PATH="$HOME/.local/bin:$PATH"\nexec "%s/src/launch.py" "$@"\n' "$INSTALL_DIR" > "$LAUNCHER"
chmod +x "$LAUNCHER"
chmod +x "$INSTALL_DIR/src/launch.py"

# 6. Install Icons
cp "$SCRIPT_DIR/assets/icon.png" "$ICON_DIR/antigravity-quota.png"
cp "$SCRIPT_DIR/assets/icon.png" "$ICON_DIR/hicolor/256x256/apps/antigravity-quota.png"

# 7. Install Desktop Entry
cat <<DESKTOP_EOF > "$APP_DIR/antigravity-quota.desktop"
[Desktop Entry]
Version=1.0
Type=Application
Name=Antigravity Quota
Comment=Antigravity Multi-Account Quota Monitor
Exec=$LAUNCHER
Icon=$ICON_DIR/antigravity-quota.png
Terminal=false
Categories=Development;Utility;
StartupNotify=true
StartupWMClass=AntigravityQuota
DESKTOP_EOF
chmod +x "$APP_DIR/antigravity-quota.desktop"

# Refresh desktop database
if command -v update-desktop-database >/dev/null 2>&1; then
  update-desktop-database "$APP_DIR" 2>/dev/null || true
fi

echo -e "\n${COLOR_GREEN}✓ Installation complete!${COLOR_RESET}\n"
echo -e "You can now launch the app via:"
echo -e "  1. Desktop Menu / App Launcher: Search for ${COLOR_CYAN}Antigravity Quota${COLOR_RESET}"
echo -e "  2. Terminal command: ${COLOR_CYAN}antigravity-quota${COLOR_RESET}\n"
