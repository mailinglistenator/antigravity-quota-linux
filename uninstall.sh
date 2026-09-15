#!/usr/bin/env bash
set -e

COLOR_RESET="\033[0m"
COLOR_YELLOW="\033[1;33m"
COLOR_GREEN="\033[1;32m"

echo -e "${COLOR_YELLOW}Uninstalling Antigravity Quota WebApp...${COLOR_RESET}"

rm -rf "$HOME/.local/share/antigravity-quota-app"
rm -f "$HOME/.local/bin/antigravity-quota"
rm -f "$HOME/.local/share/applications/antigravity-quota.desktop"
rm -f "$HOME/.local/share/icons/antigravity-quota.png"
rm -f "$HOME/.local/share/icons/hicolor/256x256/apps/antigravity-quota.png"

if command -v update-desktop-database >/dev/null 2>&1; then
  update-desktop-database "$HOME/.local/share/applications" 2>/dev/null || true
fi

echo -e "${COLOR_GREEN}✓ Successfully uninstalled Antigravity Quota WebApp.${COLOR_RESET}"
